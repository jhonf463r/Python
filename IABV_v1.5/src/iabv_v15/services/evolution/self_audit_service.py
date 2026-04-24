"""SelfAuditService — autoauditoría operativa read-only.

Consolida en un `SelfAuditSnapshot` la revisión viva de:
- disponibilidad declarada de las tools del `ToolRegistry` (dry-check);
- coherencia entre `EnvironmentSelfModel` y el `WorldModelSnapshot`;
- issues live del `OperationalSelfExaminationService` + del último
  `PortableContextPackage`.

Contratos que preserva (AGENTS.md):
- NO es otro cerebro: no decide rutas, no toca red, no llama a proveedores.
- NO duplica `PerceptionSnapshot`: sólo lee lo que ya existe.
- NO reemplaza `EnvironmentSelfModel`, `WorldModelSnapshot` o
  `UniversalPerceptionSignal`; los compara.
- Sin side effects en el sistema vivo más allá de la persistencia del
  snapshot propio en `data/evolution/self_audit/`.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from iabv_v15.domain.models import (
    EnvironmentMatchResult,
    EnvironmentSelfModel,
    PortableContextPackage,
    SelfAuditSnapshot,
    SelfExaminationSnapshot,
    ToolCard,
    ToolCheckResult,
    WorldModelSnapshot,
)
from iabv_v15.services.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


_MAX_PENDING_ISSUES = 20
_MAX_SUMMARY_CHARS = 1500


class SelfAuditService:
    """Servicio síncrono, read-only, que produce un `SelfAuditSnapshot`."""

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        environment_self_model_provider: Callable[[], EnvironmentSelfModel | None],
        world_model_service: Any,
        operational_self_examination_service: Any,
        portable_context_service: Any,
        clock: Callable[[], datetime] | None = None,
        storage_root: Path | str | None = None,
        workspace_root: Path | str | None = None,
        token_rotation_ledger: Any | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self._environment_provider = environment_self_model_provider
        self.world_model_service = world_model_service
        self.operational_self_examination_service = operational_self_examination_service
        self.portable_context_service = portable_context_service
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        # Capa 2.2 — dep opcional. Cada ``run()`` alimenta el ledger con
        # probe_ok / probe_failed por los tool_ids auth-bearing para que
        # ``OperationalSelfExaminationService`` pueda proyectar rotaciones
        # proactivas sin que el usuario lo note.
        self.token_rotation_ledger: Any | None = token_rotation_ledger
        resolved_root: Path | None
        if storage_root is not None:
            resolved_root = Path(storage_root)
        elif workspace_root is not None:
            # Convención idéntica al resto de services de evolution:
            # `data/evolution/<nombre>` bajo el `workspace_root`.
            resolved_root = Path(workspace_root) / "data" / "evolution" / "self_audit"
        else:
            resolved_root = None
        self._storage_root: Path | None = resolved_root

    # ------------------------------------------------------------------
    # API pública

    def run(self, *, reason: str | None = None) -> SelfAuditSnapshot:
        """Ejecuta la auditoría y persiste el snapshot resultante."""

        generated_at = self._clock()

        tool_checks = self._collect_tool_checks()
        environment = self._safe(self._environment_provider, default=None)
        world_model = self._safe(self._current_world_model, default=None)
        environment_match = self._compare_environment_vs_world(environment, world_model)
        pending_issues = self._collect_pending_issues()
        world_model_digest = self._world_model_digest(world_model)

        summary_markdown = self._build_summary(
            generated_at=generated_at,
            reason=reason,
            tool_checks=tool_checks,
            environment_match=environment_match,
            pending_issues=pending_issues,
        )

        snapshot = SelfAuditSnapshot(
            generated_at=generated_at,
            reason=reason,
            tool_checks=list(tool_checks),
            environment_match=environment_match,
            pending_issues=list(pending_issues),
            world_model_digest=dict(world_model_digest),
            summary_markdown=summary_markdown,
        )
        self._persist(snapshot)
        self._feed_token_rotation_ledger(tool_checks=tool_checks, observed_at=generated_at)
        return snapshot

    # ------------------------------------------------------------------
    # Capa 2.2 — feed de TokenRotationLedger
    #
    # Solo los tool_ids auth-bearing cuentan para rotacion de tokens.
    # ``github_api``/``devin_api`` ya persisten 200 OK o 401 en su
    # ``ToolCheckResult`` cuando ``is_available`` corre contra el
    # endpoint real. El feed es best-effort: si el ledger falta o tira
    # excepcion, el audit no se rompe.
    _AUTH_BEARING_TOOL_IDS: frozenset[str] = frozenset({'github_api', 'devin_api'})

    def _feed_token_rotation_ledger(
        self,
        *,
        tool_checks: list[ToolCheckResult],
        observed_at: datetime,
    ) -> None:
        ledger = getattr(self, 'token_rotation_ledger', None)
        if ledger is None or not hasattr(ledger, 'record_probe'):
            return
        for check in tool_checks:
            tool_id = str(getattr(check, 'tool_id', '') or '').strip()
            if tool_id not in self._AUTH_BEARING_TOOL_IDS:
                continue
            try:
                ledger.record_probe(
                    tool_id,
                    ok=bool(getattr(check, 'available', False)),
                    reason=str(getattr(check, 'reason', '') or '') or None,
                    observed_at=observed_at,
                    metadata={'status': str(getattr(check, 'status', '') or '')},
                )
            except Exception as exc:  # pragma: no cover - defensa
                logger.warning(
                    'TokenRotationLedger feed fallo para %s: %s', tool_id, exc
                )

    # ------------------------------------------------------------------
    # Tool checks

    def _collect_tool_checks(self) -> list[ToolCheckResult]:
        cards = self._safe(self.tool_registry.list_cards, default=[]) or []
        results: list[ToolCheckResult] = []
        for card in cards:
            if not isinstance(card, ToolCard):
                continue
            fresh = self._safe(self.tool_registry.refresh_card, card, default=card) or card
            try:
                result = fresh.dry_check()
            except Exception as exc:  # pragma: no cover - defensa
                logger.warning("dry_check falló para %s: %s", fresh.tool_id, exc)
                result = ToolCheckResult(
                    tool_id=fresh.tool_id,
                    available=False,
                    status="blocked",
                    reason=f"dry_check_exception: {exc}",
                    evidence={"adapter_key": fresh.adapter_key},
                )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Environment vs WorldModel

    def _current_world_model(self) -> WorldModelSnapshot | None:
        svc = self.world_model_service
        if svc is None:
            return None
        # La capa P1 expone `current_model`; algunos fakes exponen
        # `get_current_snapshot`. Soportamos ambos sin forzar contrato nuevo.
        getter = getattr(svc, "current_model", None) or getattr(svc, "get_current_snapshot", None)
        if getter is None:
            return None
        return getter()

    def _compare_environment_vs_world(
        self,
        environment: EnvironmentSelfModel | None,
        world_model: WorldModelSnapshot | None,
    ) -> EnvironmentMatchResult:
        env_digest = self._digest_of(environment)
        world_digest = self._digest_of(world_model)

        if environment is None and world_model is None:
            return EnvironmentMatchResult(
                matched=False,
                mismatches=["no hay EnvironmentSelfModel ni WorldModelSnapshot disponibles"],
                environment_digest=env_digest,
                world_model_digest=world_digest,
            )
        if environment is None:
            return EnvironmentMatchResult(
                matched=False,
                mismatches=["EnvironmentSelfModel ausente; no se puede comparar con WorldModel"],
                environment_digest=env_digest,
                world_model_digest=world_digest,
            )
        if world_model is None:
            return EnvironmentMatchResult(
                matched=False,
                mismatches=["WorldModelSnapshot ausente; no se puede comparar con EnvironmentSelfModel"],
                environment_digest=env_digest,
                world_model_digest=world_digest,
            )

        mismatches: list[str] = []

        env_tools = {
            str(entry.get("tool_id") or "").strip()
            for entry in (environment.available_tools or [])
            if isinstance(entry, dict) and str(entry.get("tool_id") or "").strip()
        }
        env_missing = {
            str(entry.get("tool_id") or "").strip()
            for entry in (environment.missing_tools or [])
            if isinstance(entry, dict) and str(entry.get("tool_id") or "").strip()
        }
        world_live_tools = {
            str(getattr(live, "tool_id", "") or "").strip()
            for live in (world_model.tool_live_status or [])
            if str(getattr(live, "tool_id", "") or "").strip()
        }

        for tool_id in sorted(env_tools - world_live_tools):
            mismatches.append(
                f"tool '{tool_id}' declarada como disponible en EnvironmentSelfModel pero "
                "sin entrada viva en WorldModelSnapshot.tool_live_status"
            )
        for tool_id in sorted(env_missing & world_live_tools):
            # World dice que la tool está viva, pero el env la tiene como missing.
            live_entry = next(
                (
                    live
                    for live in (world_model.tool_live_status or [])
                    if str(getattr(live, "tool_id", "") or "").strip() == tool_id
                ),
                None,
            )
            if live_entry is None or bool(getattr(live_entry, "available", False)):
                mismatches.append(
                    f"tool '{tool_id}' marcada como missing en EnvironmentSelfModel pero "
                    "aparece como viva en WorldModelSnapshot"
                )

        env_scan = str(getattr(environment, "scan_status", "") or "").strip()
        if env_scan in {"bootstrapping", "failed", "degraded"}:
            mismatches.append(
                f"EnvironmentSelfModel.scan_status='{env_scan}' indica que el escaneo "
                "del entorno aún no es confiable"
            )

        network = getattr(world_model, "network_status", None)
        if network is not None and not bool(getattr(network, "connected", False)):
            mismatches.append(
                "WorldModelSnapshot.network_status.connected=False; rutas externas bloqueadas"
            )

        return EnvironmentMatchResult(
            matched=not mismatches,
            mismatches=mismatches,
            environment_digest=env_digest,
            world_model_digest=world_digest,
        )

    def _digest_of(self, value: Any) -> str:
        if value is None:
            return ""
        try:
            if hasattr(value, "model_dump_json"):
                payload = value.model_dump_json()
            elif hasattr(value, "model_dump"):
                payload = json.dumps(value.model_dump(mode="json"), sort_keys=True, default=str)
            else:
                payload = json.dumps(value, sort_keys=True, default=str)
        except Exception:  # pragma: no cover - defensa
            payload = str(value)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Pending issues (self-examination live + portable_context package)

    # ── Patrones aprendidos por el programa ──
    # Cada patron es un error que el programa cometio y aprendio a detectar.
    LEARNED_PATTERNS: list[dict[str, str]] = [
        {
            'id': 'QML_DUPLICATE_SIGNAL',
            'category': 'qml',
            'severity': 'error',
            'title': 'QML: property auto-genera signal Changed',
            'description': (
                'En QML, declarar "property string X" auto-genera "signal XChanged()". '
                'Si tambien se declara "signal XChanged(type param)" explicitamente, '
                'QML rechaza el tipo completo con "Duplicate signal name" y el '
                'componente no se carga. Solucion: eliminar la declaracion explicita '
                'del signal y usar la property directamente en los handlers.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['ChatToolbar.qml'],
        },
        {
            'id': 'PYDANTIC_NO_ARBITRARY_FIELDS',
            'category': 'python',
            'severity': 'error',
            'title': 'Pydantic: no permite campos arbitrarios en modelos',
            'description': (
                'Los modelos Pydantic (como ToolCard) no permiten asignar campos '
                'que no estan declarados en la clase. "card.detection_evidence = {}" '
                'lanza ValueError. Solucion: usar card.metadata (dict existente) '
                'para guardar datos dinamicos, o declarar el campo en el modelo.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['tool_adapters.py'],
        },
        {
            'id': 'GPU_METACOGNITION_REQUIRED',
            'category': 'metacognition',
            'severity': 'critical',
            'title': 'El programa DEBE verificar que GPU usa Ollama realmente',
            'description': (
                'En laptops con 2 GPUs (Intel integrada + NVIDIA discreta), Ollama puede '
                'usar la GPU equivocada. El programa debe: '
                '1) Detectar GPUs fisicas con nvidia-smi -L, '
                '2) Verificar con ollama ps que el modelo corre 100% GPU (no CPU/GPU split), '
                '3) Si un modelo dice "61%/39% CPU/GPU" = NO CABE en GPU, descargar automaticamente, '
                '4) Si el disco llega a 100% durante inferencia = modelo NO esta en GPU, '
                '5) NUNCA reportar "GPU activa" basandose solo en nvidia-smi utilization — '
                'cruzar SIEMPRE con ollama ps y con lo que el usuario ve en Task Manager. '
                'Servicio: gpu_health_service.introspect_gpu()'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['services/gpu_health_service.py'],
        },
        {
            'id': 'NVIDIA_SMI_UNRELIABLE',
            'category': 'hardware',
            'severity': 'high',
            'title': 'nvidia-smi reporta picos falsos — usar ollama ps',
            'description': (
                'nvidia-smi captura utilizacion GPU en milisegundos, que no refleja '
                'el uso real visible en el Administrador de Tareas de Windows (promedia por segundo). '
                'Durante benchmarks con carga/descarga de modelos, nvidia-smi puede reportar 86-98% '
                'GPU mientras el usuario ve <15% en Task Manager y disco al 100%. '
                'LA VERDAD ABSOLUTA es `ollama ps` que muestra el % real CPU/GPU: '
                '"100% GPU" = modelo cabe en VRAM, "61%/39% CPU/GPU" = modelo NO cabe. '
                'Regla: NUNCA confiar solo en nvidia-smi para reportar uso de GPU. '
                'Siempre cruzar con ollama ps y con lo que el usuario ve.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['services/gpu_health_service.py', 'infra/mcp/self_update_tools.py'],
        },
        {
            'id': 'GPU_MODEL_BENCHMARK_RTX4050',
            'category': 'hardware',
            'severity': 'info',
            'title': 'GPU Benchmark: RTX 4050 Laptop (6GB VRAM)',
            'description': (
                'TEST REAL 2026-04-23 con nvidia-smi en RTX 4050 Laptop (6GB VRAM, driver 576.02): '
                'gemma3:4b = 53.0 tok/s (MEJOR, 4.35GB VRAM, GPU 44% peak, 36C) CONFIRMADO GPU=SI, '
                'qwen2.5-coder:7b = 34.8 tok/s (4.92GB VRAM, GPU 96% peak, 36C) CONFIRMADO GPU=SI, '
                'qwen3:8b = 33.0 tok/s (5.95GB VRAM, GPU 97% peak, 36C) CONFIRMADO GPU=SI — cabe justo, '
                'gpt-oss:20b = 15.3 tok/s (5.56GB VRAM parcial, GPU 67% peak, 36C) CONFIRMADO GPU=SI parcial. '
                'TODOS los modelos usan GPU. Auto-deteccion: _auto_detect_best_ollama_model() '
                'lee data/gpu_benchmark_real.json si existe, sino usa nvidia-smi para estimar. '
                'Config: OLLAMA_FLASH_ATTENTION=1, OLLAMA_NUM_PARALLEL=1, OLLAMA_GPU_OVERHEAD=256.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['infra/config.py', 'scripts/start_iabv.ps1'],
        },
        {
            'id': 'THREADPOOL_UI_BLOCK',
            'category': 'python',
            'severity': 'error',
            'title': 'Python: with ThreadPoolExecutor bloquea hilo de UI al salir',
            'description': (
                'Usar "with ThreadPoolExecutor() as pool" en el hilo principal de '
                'la UI causa que pool.shutdown(wait=True) bloquee al salir del with, '
                'incluso si future.result(timeout=N) ya lanzo TimeoutError. '
                'Solucion: usar threading.Thread + threading.Event para timeout '
                'sin bloquear el hilo de UI al finalizar.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['control_center_viewmodel.py'],
        },
        {
            'id': 'WORKING_FLAG_STUCK',
            'category': 'ui',
            'severity': 'error',
            'title': 'UI: _working=True puede quedar stuck si worker() falla',
            'description': (
                'Si el worker thread de sendChat lanza una excepcion no capturada '
                'o si el signal taskFailed/taskResolved no se emite correctamente, '
                '_working queda en True y el chat rechaza todos los mensajes. '
                'Solucion: agregar timeout de seguridad que resetee _working si '
                'lleva mas de 60 segundos en True.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['control_center_viewmodel.py'],
        },
        {
            'id': 'COMPONENTS_NOT_INTEGRATED',
            'category': 'ui',
            'severity': 'warning',
            'title': 'UI: crear componentes no es suficiente, hay que integrarlos',
            'description': (
                'Crear archivos QML de componentes (ChatToolbar.qml, etc.) no los '
                'hace visibles automaticamente. Hay que instanciarlos explicitamente '
                'en la pagina principal (ControlCenterPage.qml) con bindings a las '
                'properties del ViewModel. Siempre verificar que el componente se '
                'usa en la pagina, no solo que existe como archivo.'
            ),
            'first_seen': '2026-04-23',
            'affected_files': ['ControlCenterPage.qml'],
        },
    ]

    def _collect_pending_issues(self) -> list[str]:
        # Include UI validation issues from ControlCenterViewModel
        try:
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            if hasattr(ControlCenterViewModel, '_validate_ui_reflects_reality'):
                pass  # Method exists - good
            else:
                return ['UI: ControlCenterViewModel no tiene _validate_ui_reflects_reality - la interfaz no se auto-valida']
        except ImportError:
            pass

        items: list[str] = []
        seen: set[str] = set()

        # Incluir patrones aprendidos como issues pendientes de verificacion
        for pattern in self.LEARNED_PATTERNS:
            key = f"LEARNED:{pattern['id']}"
            if key not in seen:
                seen.add(key)
                items.append(f"[{pattern['severity']}] {pattern['title']}")
            if len(items) >= _MAX_PENDING_ISSUES:
                break

        review = self._safe(self._current_review, default=None)
        if review is not None:
            for finding in list(getattr(review, "findings", []) or []):
                title = str(getattr(finding, "title", "") or "").strip()
                if title and title not in seen:
                    seen.add(title)
                    items.append(title)
                if len(items) >= _MAX_PENDING_ISSUES:
                    break
            for risk in list(getattr(review, "unresolved_risks", []) or []):
                text = str(risk or "").strip()
                if text and text not in seen:
                    seen.add(text)
                    items.append(text)
                if len(items) >= _MAX_PENDING_ISSUES:
                    break

        package = self._safe(self._current_portable_package, default=None)
        if package is not None and len(items) < _MAX_PENDING_ISSUES:
            for section in list(getattr(package, "sections", []) or []):
                section_id = str(getattr(section, "section_id", "") or "").lower()
                if "pending" not in section_id and "risk" not in section_id and "unresolved" not in section_id:
                    continue
                for entry in list(getattr(section, "items", []) or []):
                    if not isinstance(entry, dict):
                        continue
                    text = str(entry.get("title") or entry.get("summary") or "").strip()
                    if text and text not in seen:
                        seen.add(text)
                        items.append(text)
                    if len(items) >= _MAX_PENDING_ISSUES:
                        break
                if len(items) >= _MAX_PENDING_ISSUES:
                    break
            for risk in list(getattr(package, "unresolved_fields", []) or []):
                if len(items) >= _MAX_PENDING_ISSUES:
                    break
                text = str(risk or "").strip()
                if text and text not in seen:
                    seen.add(text)
                    items.append(text)

        return items

    def _current_review(self) -> SelfExaminationSnapshot | None:
        svc = self.operational_self_examination_service
        if svc is None:
            return None
        getter = getattr(svc, "current_review", None) or getattr(svc, "current", None)
        if getter is None:
            return None
        try:
            return getter(refresh=False)
        except TypeError:
            # current_review accepts refresh kw; retry without args.
            return getter()

    def _current_portable_package(self) -> PortableContextPackage | None:
        svc = self.portable_context_service
        if svc is None:
            return None
        getter = getattr(svc, "current_package", None)
        if getter is None:
            return None
        try:
            return getter(refresh=False)
        except TypeError:
            return getter()

    # ------------------------------------------------------------------
    # WorldModel digest para el snapshot

    def _world_model_digest(self, world_model: WorldModelSnapshot | None) -> dict[str, Any]:
        if world_model is None:
            return {"available": False}
        network = getattr(world_model, "network_status", None)
        blocks = list(getattr(world_model, "block_records", []) or [])
        gates = list(getattr(world_model, "permission_gates", []) or [])
        live_tools = list(getattr(world_model, "tool_live_status", []) or [])
        focused = getattr(world_model, "focused_window", None)
        return {
            "available": True,
            "snapshot_id": getattr(world_model, "snapshot_id", ""),
            "freshness_ms": int(getattr(world_model, "freshness_ms", 0) or 0),
            "confidence": float(getattr(world_model, "confidence", 0.0) or 0.0),
            "active_window_count": len(getattr(world_model, "active_windows", []) or []),
            "focused_window_title": getattr(focused, "title", "") if focused is not None else "",
            "tool_live_count": len(live_tools),
            "tool_live_ids": sorted(
                {
                    str(getattr(live, "tool_id", "") or "").strip()
                    for live in live_tools
                    if str(getattr(live, "tool_id", "") or "").strip()
                }
            ),
            "network_connected": bool(getattr(network, "connected", False)) if network is not None else False,
            "network_status": str(getattr(network, "status", "") or "") if network is not None else "",
            "active_block_count": sum(
                1 for b in blocks if str(getattr(b, "status", "active") or "active") == "active"
            ),
            "pending_permission_gates": [
                str(getattr(g, "assistant_kind", "") or "").strip() or "*"
                for g in gates
                if str(getattr(g, "status", "") or "") == "requerido" and not bool(getattr(g, "granted", False))
            ],
        }

    # ------------------------------------------------------------------
    # Summary markdown (<=1500 chars)

    def _build_summary(
        self,
        *,
        generated_at: datetime,
        reason: str | None,
        tool_checks: list[ToolCheckResult],
        environment_match: EnvironmentMatchResult,
        pending_issues: list[str],
    ) -> str:
        ok = [r for r in tool_checks if r.status == "ready"]
        bad = [r for r in tool_checks if r.status != "ready"]
        reason_line = f"Razón: {reason}" if reason else "Razón: n/a"
        lines: list[str] = [
            "# Auditoría operativa — IABV v1.5",
            f"- Generado: {generated_at.isoformat()}",
            f"- {reason_line}",
            f"- Tools OK: {len(ok)} / {len(tool_checks)}",
        ]
        if bad:
            lines.append("## Tools con problema")
            for r in bad[:5]:
                reason_txt = f" — {r.reason}" if r.reason else ""
                lines.append(f"- `{r.tool_id}` [{r.status}]{reason_txt}")
        lines.append("## Entorno vs WorldModel")
        if environment_match.matched:
            lines.append("- Match OK: EnvironmentSelfModel y WorldModelSnapshot son coherentes.")
        else:
            for mismatch in environment_match.mismatches[:5]:
                lines.append(f"- {mismatch}")
        lines.append("## Pendientes top-5")
        if pending_issues:
            for item in pending_issues[:5]:
                lines.append(f"- {item}")
        else:
            lines.append("- (ninguno reportado)")

        summary = "\n".join(lines)
        if len(summary) > _MAX_SUMMARY_CHARS:
            summary = summary[: _MAX_SUMMARY_CHARS - 3] + "..."
        return summary

    # ------------------------------------------------------------------
    # Persistencia

    def _persist(self, snapshot: SelfAuditSnapshot) -> None:
        root = self._resolve_storage_root()
        if root is None:
            return
        try:
            root.mkdir(parents=True, exist_ok=True)
            history_dir = root / "history"
            history_dir.mkdir(parents=True, exist_ok=True)

            payload = _to_jsonable(snapshot)
            latest_json = root / "latest.json"
            latest_md = root / "latest.md"
            latest_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            latest_md.write_text(snapshot.summary_markdown, encoding="utf-8")

            stamp = snapshot.generated_at.strftime("%Y%m%dT%H%M%S%fZ")
            history_file = history_dir / f"{stamp}.json"
            history_file.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - defensa IO
            logger.warning("No pude persistir SelfAuditSnapshot: %s", exc)

    def _resolve_storage_root(self) -> Path | None:
        return self._storage_root

    # ------------------------------------------------------------------
    # Helpers

    @staticmethod
    def _safe(fn, /, *args, default=None, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensa
            logger.warning("self_audit helper falló (%s): %s", getattr(fn, "__name__", fn), exc)
            return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
