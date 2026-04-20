"""EmbodimentViolationDetector — PCS v1, PR E.

Detector read-only que observa las interacciones pregunta→tools de un
asistente externo y reporta como violaciones las preguntas que matchean
un sensor propio de IABV (según ``embodiment_manifest``) pero fueron
respondidas sin llamar a la tool del cuerpo correspondiente.

Contratos relevantes:
- ``EmbodimentViolationRecord`` y ``EmbodimentViolationKind`` viven en
  ``iabv_v15.domain.models``; este servicio sólo los construye.
- El manifest sigue siendo la fuente de verdad pública
  (``server.embodiment_manifest``). Acá replicamos un subset literal
  como tabla interna para evitar acoplar el detector al registry de
  FastMCP: el detector debe poder correrse sin levantar el MCP server.
- PCS v1 declara ``handshake_required=False``: el detector NO bloquea;
  sólo acumula evidencia para ``metadata['embodiment_violations']`` del
  snapshot de autoexaminación y para consulta read-only vía MCP.

Heurística v1 sin ML:
- match literal case-insensitive (``any(keyword in question_lower)``);
- si ningún keyword matchea → no hay violación (silencio informado);
- si matchea y el ``expected_tool_id`` está en ``tool_ids_used`` →
  no hay violación (el cuerpo fue usado);
- si matchea y NO está → violación ``SENSOR_BYPASS`` con severidad LOW.
"""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any, Deque

from iabv_v15.domain.models import (
    EmbodimentViolationKind,
    EmbodimentViolationRecord,
    IssueSeverity,
    utc_now,
)


# Subset literal del ``sensor_before_question`` que expone la MCP tool
# ``embodiment_manifest``. Cada entrada es ``(keywords, expected_tool_id)``.
# Se mantiene desacoplado del FastMCP registry a propósito: si la tool
# ``embodiment_manifest`` gana nuevos sensores, este detector puede
# extenderse sin depender del MCP server en runtime. Cubre las 14
# entradas del manifest con ≥8 categorías heurísticas.
#
# ORDEN IMPORTA: el match es first-wins por substring. Las entradas más
# específicas deben ir antes que las genéricas. Ejemplo crítico:
# ``list_open_windows`` usa keywords como ``'ventanas abiertas'`` que
# contienen la keyword corta ``'ventana'`` de ``world_model_snapshot``;
# si world_model viene primero, list_open_windows queda inaccesible y
# el detector marcaría SENSOR_BYPASS justo cuando el asistente usó la
# tool correcta del manifest. Mantener las entradas específicas arriba.
_SENSOR_TABLE: tuple[tuple[tuple[str, ...], str], ...] = (
    # list_open_windows — ventanas abiertas (ANTES de world_model_snapshot,
    # ver nota de ordering arriba).
    (('ventanas abiertas', 'que ventanas', 'qué ventanas', 'listar ventanas', 'cuales ventanas', 'cuáles ventanas'), 'list_open_windows'),
    # list_running_processes — procesos corriendo (específico antes que nada).
    (('procesos corriendo', 'que procesos', 'qué procesos', 'listar procesos', 'proceso activo', 'procesos activos'), 'list_running_processes'),
    # world_model_snapshot — ventanas/foco/pantalla/escritorio a nivel general.
    (('ventana', 'foco', 'pantalla', 'escritorio'), 'world_model_snapshot'),
    # self_examination_current — bloqueos, degradaciones, fallas del sistema.
    (('bloqueo', 'degrada', 'falla', 'error', 'salud del sistema', 'salud operativa'), 'self_examination_current'),
    # run_pytest — tests, suite, pytest.
    (('pytest', 'suite de pruebas', 'correr tests', 'corre tests', 'correr pruebas', 'pruebas pasan', 'tests pasan'), 'run_pytest'),
    # read_repo_file — contenido de archivo, leer archivo, código fuente.
    (('leer archivo', 'contenido del archivo', 'contenido de archivo', 'codigo fuente', 'código fuente', 'abrir archivo'), 'read_repo_file'),
    # list_repo_directory — listar directorio, ver carpeta.
    (('listar directorio', 'listar carpeta', 'ver carpeta', 'contenido de directorio', 'contenido del directorio', 'ls '), 'list_repo_directory'),
    # read_clipboard — clipboard del usuario.
    (('clipboard', 'portapapeles'), 'read_clipboard'),
    # dump_qml_tree — arbol QML / UI.
    (('qml', 'arbol qml', 'árbol qml', 'arbol ui', 'árbol ui'), 'dump_qml_tree'),
    # chatgpt_web_capture — captura DOM de ChatGPT (antes que probe login).
    (('captura dom', 'dom de chatgpt', 'capturar chatgpt'), 'chatgpt_web_capture'),
    # probe_assistant_login — login/sesion/autenticacion de asistente.
    (('login', 'sesion', 'sesión', 'autenticad', 'logueado'), 'probe_assistant_login'),
    # run_self_audit — auditoría global.
    (('auditoria', 'auditoría', 'auditate', 'auditar'), 'run_self_audit'),
    # portable_context_get — contexto portable.
    (('contexto portable', 'portable context', 'paquete portable'), 'portable_context_get'),
    # git_status_and_log — historia de git.
    (('git status', 'git log', 'historia de git', 'historial de git', 'estado del repo'), 'git_status_and_log'),
)


def _match_sensor(question: str) -> tuple[str, str] | None:
    """Devuelve ``(matched_sensor, expected_tool_id)`` o ``None``.

    El ``matched_sensor`` es la primera palabra clave que disparó el
    match; sirve como evidencia humana en el record. Si ninguna entrada
    matchea, no hay violación posible.
    """

    if not question:
        return None
    question_lower = question.lower()
    for keywords, expected_tool_id in _SENSOR_TABLE:
        for keyword in keywords:
            if keyword in question_lower:
                return keyword, expected_tool_id
    return None


class EmbodimentViolationDetector:
    """Buffer por-sesión + heurística literal pregunta→tool.

    Uso típico:
        detector = EmbodimentViolationDetector(maxlen=50)
        detector.record_interaction(
            session_id='sess-A',
            question_text='¿qué ventanas están abiertas ahora?',
            tool_ids_used=['web_search'],
            assistant_kind='chatgpt',
        )
        violations = detector.detect(session_id='sess-A')
        # o globalmente:
        violations = detector.snapshot()
    """

    def __init__(self, *, maxlen: int = 50) -> None:
        if maxlen <= 0:
            raise ValueError('maxlen debe ser > 0')
        self._maxlen = int(maxlen)
        self._buffers: dict[str, Deque[dict[str, Any]]] = {}
        self._lock = Lock()

    @property
    def maxlen(self) -> int:
        return self._maxlen

    def record_interaction(
        self,
        *,
        session_id: str,
        question_text: str,
        tool_ids_used: list[str],
        assistant_kind: str = '',
        trace_id: str = '',
    ) -> None:
        """Guarda una interacción en el buffer por ``session_id``.

        No evalúa violaciones acá: sólo acumula. La evaluación vive en
        ``detect`` / ``snapshot`` para permitir re-evaluación si la
        tabla de sensores cambia.
        """

        session_key = str(session_id or '')
        entry = {
            'session_id': session_key,
            'question_text': str(question_text or ''),
            'tool_ids_used': [str(tid) for tid in (tool_ids_used or [])],
            'assistant_kind': str(assistant_kind or ''),
            'trace_id': str(trace_id or ''),
            'recorded_at_utc': utc_now(),
        }
        with self._lock:
            buffer = self._buffers.get(session_key)
            if buffer is None:
                buffer = deque(maxlen=self._maxlen)
                self._buffers[session_key] = buffer
            buffer.append(entry)

    def detect(self, *, session_id: str) -> list[EmbodimentViolationRecord]:
        """Devuelve violaciones detectadas en el buffer de una sesión."""

        session_key = str(session_id or '')
        with self._lock:
            buffer = self._buffers.get(session_key)
            entries = list(buffer) if buffer is not None else []
        return [record for record in (self._evaluate(entry) for entry in entries) if record is not None]

    def snapshot(
        self,
        *,
        session_id: str | None = None,
    ) -> list[EmbodimentViolationRecord]:
        """Devuelve violaciones; si ``session_id`` es None, para todas las sesiones."""

        if session_id is not None:
            return self.detect(session_id=session_id)
        with self._lock:
            entries: list[dict[str, Any]] = []
            for buffer in self._buffers.values():
                entries.extend(buffer)
        return [record for record in (self._evaluate(entry) for entry in entries) if record is not None]

    def clear(self, *, session_id: str | None = None) -> None:
        """Borra buffers. Útil en tests; NO lo llama el flujo productivo."""

        with self._lock:
            if session_id is None:
                self._buffers.clear()
            else:
                self._buffers.pop(str(session_id or ''), None)

    # ------------------------------------------------------------------
    # Internals

    def _evaluate(self, entry: dict[str, Any]) -> EmbodimentViolationRecord | None:
        question_text = entry.get('question_text') or ''
        matched = _match_sensor(question_text)
        if matched is None:
            return None
        matched_sensor, expected_tool_id = matched
        tool_ids_used = list(entry.get('tool_ids_used') or [])
        if expected_tool_id in tool_ids_used:
            return None
        return EmbodimentViolationRecord(
            session_id=str(entry.get('session_id') or ''),
            assistant_kind=str(entry.get('assistant_kind') or ''),
            trace_id=str(entry.get('trace_id') or ''),
            question_text=question_text,
            matched_sensor=matched_sensor,
            expected_tool_id=expected_tool_id,
            tool_ids_used=tool_ids_used,
            violation_kind=EmbodimentViolationKind.SENSOR_BYPASS,
            severity=IssueSeverity.LOW,
            reasoning=(
                f'La pregunta matchea el sensor "{matched_sensor}" cubierto por '
                f'la tool "{expected_tool_id}" (declarada en embodiment_manifest), '
                f'pero el asistente no la llamó; usó {tool_ids_used or "(ninguna tool del cuerpo)"}.'
            ),
            evidence_refs=[f'embodiment_manifest:{expected_tool_id}'],
            metadata={
                'detector_version': 'pcs-v1',
                'match_keyword': matched_sensor,
            },
        )
