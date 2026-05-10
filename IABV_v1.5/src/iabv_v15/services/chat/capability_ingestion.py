"""Detecta menciones de capacidades y directivas operativas en el chat.

El problema que resuelve: cuando el usuario escribe algo como "tengo GPU" o
"tengo instalado qwen", o cuando fija una regla como "usa una sola ventana",
el chat responde con la heuristica del momento y el dato se pierde en memoria.
Este servicio persiste cada mencion a disco
(`data/chat_research_backlog/<session>.jsonl`) para que:

1. Quede registro durable aun si cerras la UI.
2. `OperationalSelfExaminationService` y `ExperimentLab` puedan leerlo
   despues y proponer pruebas reales (ej: medir si la GPU acelera un modelo
   local, o si el replay visual reconstruye lo que ve el usuario).
3. El mismo chat pueda responder al usuario "ya lo anote como tarea, ese
   dato no se me pierde" en vez de silenciarlo.

Este servicio NO decide rutas ni modifica contratos de P1-P4. Solo detecta y
persiste. El consumo de la cola queda para capas posteriores.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CapabilityPattern:
    """Patron regex + metadata asociada."""

    kind: str
    label: str
    pattern: re.Pattern[str]
    research_hint: str
    requires_possession_marker: bool = True


@dataclass(frozen=True)
class CapabilityDetection:
    """Una mencion detectada en un mensaje del usuario."""

    kind: str
    label: str
    matched_text: str
    research_hint: str


@dataclass(frozen=True)
class CapabilityResearchEntry:
    """Registro persistido en el backlog de investigacion."""

    session_id: str
    detected_at_utc: str
    kind: str
    label: str
    matched_text: str
    research_hint: str
    raw_message: str
    status: str = 'open'


# Verbos / frases que indican que el usuario esta declarando una capacidad
# propia o su ausencia. Sin este filtro, "gpu" en cualquier contexto generaria
# ruido. Con el filtro, solo disparamos cuando el usuario afirma algo sobre
# su entorno.
_POSSESSION_MARKERS = (
    'tengo', 'cuento con', 'dispongo', 'mi ', 'mi\n', 'mi\t', 'uso ',
    'instale', 'instalo', 'tengo instalado', 'tengo instalada',
    'puedo usar', 'ya uso', 'estoy usando', 'esta instalado',
    'esta instalada', 'esta corriendo', 'corre en', 'corre localmente',
    'tengo una', 'tengo un ',
)


def _build_patterns() -> tuple[CapabilityPattern, ...]:
    return (
        CapabilityPattern(
            kind='hardware_gpu',
            label='GPU disponible (sin benchmark)',
            pattern=re.compile(
                r'\b(gpu|cuda|vram|rtx\s*\d{3,4}|gtx\s*\d{3,4}|radeon|nvidia|rocm|tensor\s*cores?)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Medir si esta GPU acelera inferencia local (Ollama / llama.cpp) '
                'vs CPU, y registrar el mejor modelo segun tokens/segundo.'
            ),
        ),
        CapabilityPattern(
            kind='local_model',
            label='Modelo local mencionado',
            pattern=re.compile(
                r'\b(llama\s*\d+|qwen\s*\d+|qwen3|gemma\s*\d+|mistral|mixtral|phi\s*\d+|deepseek|codellama|nous|hermes)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Probar el modelo contra la ruta default del StrategySelector y '
                'comparar latencia, calidad de respuesta y exactitud de intent.'
            ),
        ),
        CapabilityPattern(
            kind='external_account',
            label='Cuenta o acceso externo mencionado',
            pattern=re.compile(
                r'\b(codex|claude|chatgpt|devin|anthropic|openai|github|copilot|cursor|aider)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Verificar en el ToolRegistry si la cuenta ya esta conectada y, si '
                'no, pedir credencial. Si lo esta, correr probe_assistant_login y '
                'registrar latencia en ExperimentLab.'
            ),
        ),
        CapabilityPattern(
            kind='local_runtime',
            label='Runtime local mencionado',
            pattern=re.compile(
                r'\b(docker|wsl2?|conda|miniconda|anaconda|node\s*(js)?|pnpm|yarn|poetry|uv\s*pip)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Agregar el runtime al ToolRegistry si no esta, y documentar su '
                'version para que las rutas que lo necesiten lo declaren.'
            ),
        ),
        CapabilityPattern(
            kind='operational_autonomy_contract',
            label='Contrato operativo de autonomia',
            pattern=re.compile(
                r'\b(autonom[oa]|asistente\s+maestro|toda\s+mi\s+laptop|una\s+sola\s+ventana|'
                r'unica\s+ventana|sin\s+powershell|por\s+la\s+interfaz|se\s+valga\s+por\s+si\s+solo|'
                r'coordinador\s+central)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Validar que la UI, el Control Master, OSES y el ciclo de validacion '
                'convierten este contrato en acciones visibles sin pedir terminal al usuario.'
            ),
            requires_possession_marker=False,
        ),
        CapabilityPattern(
            kind='operational_visual_replay',
            label='Replay visual y percepcion guiada',
            pattern=re.compile(
                r'\b(replay\s+visual|mostrar(?:me)?\s+visualmente|lo\s+que\s+ves|que\s+ve\s+el\s+programa|'
                r'captura(?:r)?\s+(?:vista|pantalla)|metadatos|etiquetas|bbox|hacer\s+clic|'
                r'navegar\s+bien|verificacion\s+visual)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Medir si WorldModel, captura visual, anotaciones y replay reconstruyen '
                'lo que ve el usuario con coordenadas accionables y evidencia revisable.'
            ),
            requires_possession_marker=False,
        ),
        CapabilityPattern(
            kind='operational_context_hygiene',
            label='Higiene de contexto y reinicio cognitivo',
            pattern=re.compile(
                r'\b(reiniciar\s+(?:el\s+)?chat|vaciar\s+(?:el\s+)?chat|limpiar\s+contexto|'
                r'contexto\s+limpio|perdiendo\s+(?:su\s+)?logica|sesgo\s+heredado|'
                r'reset(?:ear)?\s+contexto|chat\s+limpio)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Definir metricas testeables para detectar degradacion de coherencia, '
                'recomendar compactacion/reinicio y preservar solo contexto portable valido.'
            ),
            requires_possession_marker=False,
        ),
        CapabilityPattern(
            kind='operational_self_testing',
            label='Auto-test de algoritmos, rendimiento y razonamiento',
            pattern=re.compile(
                r'\b(test(?:ea|ear|eo|s)?\s+(?:los\s+)?algoritmos|configuraciones|rendimiento|'
                r'razonamiento|variables\s+testeables|pruebas\s+periodicas|autoexaminarse|'
                r'cuando\s+reiniciar|cambiar\s+configuraciones|mediciones)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Usar AutonomousValidationCycle, ExperimentLab y OSES para probar '
                'configuraciones de rendimiento/razonamiento durante ventanas de descanso.'
            ),
            requires_possession_marker=False,
        ),
        CapabilityPattern(
            kind='operational_cross_device_universal',
            label='Portabilidad universal multi-dispositivo',
            pattern=re.compile(
                r'\b(universal|diferentes\s+dispositivos|multi[-\s]?dispositivo|sistema\s+operativo|'
                r'otro\s+dispositivo|portab(?:le|ilidad)|entorno\s+nuevo|recipiente)\b',
                re.IGNORECASE,
            ),
            research_hint=(
                'Convertir la mejora en contrato portable: no depender de rutas, ventanas, '
                'hardware o cuentas especificas de una sola maquina.'
            ),
            requires_possession_marker=False,
        ),
    )


class ChatCapabilityIngestionService:
    """Detecta menciones y escribe entries append-only al backlog de investigacion."""

    BACKLOG_SUBDIR = Path('chat_research_backlog')
    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        data_root: str | Path,
        patterns: Iterable[CapabilityPattern] | None = None,
        clock: callable | None = None,
    ) -> None:
        self._data_root = Path(data_root)
        self._patterns = tuple(patterns) if patterns is not None else _build_patterns()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Deteccion pura (sin side-effects, facil de testear)
    # ------------------------------------------------------------------
    def detect(self, message: str) -> list[CapabilityDetection]:
        if not message:
            return []
        normalized = message.strip()
        if not normalized:
            return []
        lowered = normalized.lower()
        has_possession_marker = any(marker in lowered for marker in _POSSESSION_MARKERS)
        detections: list[CapabilityDetection] = []
        seen: set[tuple[str, str]] = set()
        for pattern in self._patterns:
            if pattern.requires_possession_marker and not has_possession_marker:
                continue
            for match in pattern.pattern.finditer(normalized):
                matched = match.group(0).strip()
                key = (pattern.kind, matched.lower())
                if key in seen:
                    continue
                seen.add(key)
                detections.append(
                    CapabilityDetection(
                        kind=pattern.kind,
                        label=pattern.label,
                        matched_text=matched,
                        research_hint=pattern.research_hint,
                    )
                )
        return detections

    # ------------------------------------------------------------------
    # Persistencia append-only
    # ------------------------------------------------------------------
    def record(
        self,
        detections: Iterable[CapabilityDetection],
        *,
        session_id: str,
        raw_message: str,
    ) -> list[CapabilityResearchEntry]:
        items = list(detections)
        if not items:
            return []
        backlog_dir = self._data_root / self.BACKLOG_SUBDIR
        backlog_dir.mkdir(parents=True, exist_ok=True)
        safe_session = _sanitize_session_id(session_id)
        target = backlog_dir / f'{safe_session}.jsonl'
        now_iso = self._clock().astimezone(timezone.utc).isoformat()
        entries: list[CapabilityResearchEntry] = []
        with self._lock:
            with target.open('a', encoding='utf-8') as handle:
                for detection in items:
                    entry = CapabilityResearchEntry(
                        session_id=safe_session,
                        detected_at_utc=now_iso,
                        kind=detection.kind,
                        label=detection.label,
                        matched_text=detection.matched_text,
                        research_hint=detection.research_hint,
                        raw_message=raw_message,
                    )
                    record = {
                        'schema_version': self.SCHEMA_VERSION,
                        'session_id': entry.session_id,
                        'detected_at_utc': entry.detected_at_utc,
                        'kind': entry.kind,
                        'label': entry.label,
                        'matched_text': entry.matched_text,
                        'research_hint': entry.research_hint,
                        'raw_message': entry.raw_message,
                        'status': entry.status,
                    }
                    handle.write(json.dumps(record, ensure_ascii=False) + '\n')
                    entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # Conveniencia: detect + record en un paso
    # ------------------------------------------------------------------
    def ingest(
        self,
        message: str,
        *,
        session_id: str,
    ) -> list[CapabilityResearchEntry]:
        detections = self.detect(message)
        if not detections:
            return []
        return self.record(detections, session_id=session_id, raw_message=message)

    # ------------------------------------------------------------------
    # Lectura del backlog (para UI y para OSES posterior)
    # ------------------------------------------------------------------
    def list_entries(
        self,
        *,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[CapabilityResearchEntry]:
        backlog_dir = self._data_root / self.BACKLOG_SUBDIR
        if not backlog_dir.exists():
            return []
        files: list[Path]
        if session_id is not None:
            candidate = backlog_dir / f'{_sanitize_session_id(session_id)}.jsonl'
            files = [candidate] if candidate.exists() else []
        else:
            files = sorted(backlog_dir.glob('*.jsonl'))
        collected: list[CapabilityResearchEntry] = []
        for path in files:
            try:
                with path.open('r', encoding='utf-8') as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        collected.append(
                            CapabilityResearchEntry(
                                session_id=str(payload.get('session_id') or ''),
                                detected_at_utc=str(payload.get('detected_at_utc') or ''),
                                kind=str(payload.get('kind') or ''),
                                label=str(payload.get('label') or ''),
                                matched_text=str(payload.get('matched_text') or ''),
                                research_hint=str(payload.get('research_hint') or ''),
                                raw_message=str(payload.get('raw_message') or ''),
                                status=str(payload.get('status') or 'open'),
                            )
                        )
            except OSError:
                continue
        collected.sort(key=lambda item: item.detected_at_utc, reverse=True)
        if limit > 0:
            return collected[:limit]
        return collected


def _sanitize_session_id(session_id: str) -> str:
    cleaned = ''.join(ch if ch.isalnum() or ch in {'-', '_'} else '_' for ch in (session_id or 'default'))
    cleaned = cleaned.strip('_')
    return cleaned or 'default'
