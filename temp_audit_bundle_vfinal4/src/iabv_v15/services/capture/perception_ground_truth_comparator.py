"""Compara la perception que IABV genera contra el ground truth local.

Este servicio implementa el frente F3.3 del PC3. El objetivo es poder
verificar, desde afuera (vía MCP), si lo que ``UniversalPerceptionService``
"ve" coincide con lo que realmente está en la laptop del usuario:

* ``window_title`` declarado por la perception vs ventana real presente
  en ``WorldModelSnapshot.active_windows`` / ``focused_window``.
* ``capture_available`` vs disponibilidad real de screenshot provider.
* ``dom_available`` / ``login_detected`` vs evidencias que el
  WorldModel puede corroborar.

No duplica contratos (no reemplaza ``UniversalPerceptionSignal`` ni
``WorldModelSnapshot``): sólo los observa. No toma decisiones de ruta.

El servicio es puramente funcional: no escribe estado, no abre browser,
no consume red. Funciona degradado si falta ground truth: reporta
``ground_truth_unavailable`` como evidence y sigue comparando lo que sí
puede.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contratos livianos (protocol-lite) para testabilidad

class _PerceptionServiceLike(Protocol):
    """Subconjunto usado por el comparador (``build_signal``)."""

    def build_signal(self, **kwargs: Any) -> Any:  # pragma: no cover - protocolo
        ...


# ---------------------------------------------------------------------------
# DTOs de salida (puros, sin Pydantic para aligerar el payload MCP)


@dataclass(frozen=True)
class PerceptionMismatch:
    """Diferencia puntual detectada entre perception y ground truth."""

    field: str
    perceived: Any
    actual: Any
    severity: str  # "critical" | "warning" | "info"
    detail: str = ""


@dataclass
class PerceptionGroundTruthComparison:
    """Resultado normalizado de la comparación.

    ``perception_json`` y ``ground_truth_json`` son representaciones
    JSON-ready (vía ``model_dump`` si vienen de Pydantic, o ``asdict``
    equivalente). ``mismatches`` lista diferencias rankeadas por severity.
    """

    tool_id: str = ""
    window_title: str = ""
    perception_json: dict[str, Any] = field(default_factory=dict)
    ground_truth_json: dict[str, Any] = field(default_factory=dict)
    mismatches: list[PerceptionMismatch] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    detail: str = ""
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Severidades (exportadas para tests y el caller)


SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


# ---------------------------------------------------------------------------
# Servicio


class PerceptionGroundTruthComparator:
    """Compara perception vs ground truth para una ventana objetivo.

    Parameters
    ----------
    universal_perception_service:
        instancia real o fake de ``UniversalPerceptionService``. Sólo se
        usa ``build_signal``.
    world_model_provider:
        callable que devuelve el ``WorldModelSnapshot`` actual. Se
        inyecta así (en vez de pasar el service entero) para que el
        comparador pueda trabajar con un snapshot puro o con el service
        real indistintamente. Si la callable devuelve ``None``, se
        degrada a "ground_truth_unavailable".
    screenshot_provider:
        opcional. Cualquier objeto con método ``capture_main_window()``
        o ``.available``; sólo se consulta para ver si la captura está
        disponible; no se usa el PNG en sí.
    clock:
        ``time.perf_counter`` por defecto; inyectable para tests.
    """

    def __init__(
        self,
        *,
        universal_perception_service: _PerceptionServiceLike | None,
        world_model_provider: Callable[[], Any] | None,
        screenshot_provider: Any = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._perception_service = universal_perception_service
        self._world_model_provider = world_model_provider
        self._screenshot_provider = screenshot_provider
        self._clock = clock

    # ------------------------------------------------------------------
    # API pública

    def compare(
        self,
        window_title: str,
        *,
        tool_id: str = "",
        assistant_kind: str = "",
        site_id: str = "",
    ) -> PerceptionGroundTruthComparison:
        """Compara perception vs ground truth para ``window_title``.

        Nunca raisea: ante fallo devuelve un ``PerceptionGroundTruthComparison``
        con ``error`` tipado.
        """

        t0 = self._clock()
        title = (window_title or "").strip()
        if not title:
            return PerceptionGroundTruthComparison(
                window_title=str(window_title or ""),
                error="invalid_window_title",
                detail="`window_title` no puede estar vacío.",
                duration_ms=_elapsed_ms(self._clock, t0),
            )

        perception_json: dict[str, Any] = {}
        perception_error: str | None = None
        if self._perception_service is None:
            perception_error = "perception_service_unavailable"
        else:
            try:
                signal = self._perception_service.build_signal(
                    tool_id=tool_id,
                    assistant_kind=assistant_kind,
                    site_id=site_id,
                )
                perception_json = _to_json(signal)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("perception.build_signal falló")
                perception_error = "build_signal_raised"
                perception_json = {"error": f"{type(exc).__name__}: {exc}"}

        ground_truth_json, gt_window = self._collect_ground_truth(title)

        evidence: dict[str, Any] = {
            "ground_truth_window_matched": gt_window is not None,
            "screenshot_provider_present": self._screenshot_provider is not None,
        }
        if perception_error is not None:
            evidence["perception_error"] = perception_error

        mismatches = self._diff_fields(
            title=title,
            perception=perception_json,
            ground_truth=ground_truth_json,
            gt_window=gt_window,
        )

        return PerceptionGroundTruthComparison(
            tool_id=str(tool_id or ""),
            window_title=title,
            perception_json=perception_json,
            ground_truth_json=ground_truth_json,
            mismatches=mismatches,
            evidence=evidence,
            error=perception_error,
            detail="",
            duration_ms=_elapsed_ms(self._clock, t0),
        )

    # ------------------------------------------------------------------
    # Ground truth

    def _collect_ground_truth(
        self, title: str
    ) -> tuple[dict[str, Any], Any]:
        if self._world_model_provider is None:
            return ({"error": "world_model_provider_unavailable"}, None)

        try:
            snapshot = self._world_model_provider()
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("world_model_provider falló")
            return ({"error": "world_model_raised", "detail": str(exc)}, None)

        if snapshot is None:
            return ({"error": "world_model_unavailable"}, None)

        snapshot_json = _to_json(snapshot)

        # Normalizamos la vista de ground truth quedándonos con lo útil.
        focused = snapshot_json.get("focused_window") if isinstance(snapshot_json, dict) else None
        active_windows_raw = []
        if isinstance(snapshot_json, dict):
            active_windows_raw = snapshot_json.get("active_windows") or []

        # Intentamos matchear por título (case-insensitive substring) —
        # preferimos la focused si matchea; si no, la primera active que
        # matchee.
        gt_window: dict[str, Any] | None = None
        if isinstance(focused, dict) and _title_matches(focused.get("title"), title):
            gt_window = focused
        else:
            for w in active_windows_raw:
                if isinstance(w, dict) and _title_matches(w.get("title"), title):
                    gt_window = w
                    break

        compact: dict[str, Any] = {
            "focused_window": focused,
            "active_windows": active_windows_raw,
            "matched_window": gt_window,
            "network_connected": _dig(snapshot_json, "network_status", "connected"),
        }
        return compact, gt_window

    # ------------------------------------------------------------------
    # Diff

    def _diff_fields(
        self,
        *,
        title: str,
        perception: dict[str, Any],
        ground_truth: dict[str, Any],
        gt_window: Any,
    ) -> list[PerceptionMismatch]:
        mismatches: list[PerceptionMismatch] = []

        # 1) window_title
        perceived_title = str(
            perception.get("latest_title")
            or _dig(perception, "metadata", "latest_title")
            or ""
        )
        gt_title = ""
        if isinstance(gt_window, dict):
            gt_title = str(gt_window.get("title") or "")
        if gt_title:
            if perceived_title and not _title_matches(perceived_title, title) and not _title_matches(perceived_title, gt_title):
                mismatches.append(
                    PerceptionMismatch(
                        field="window_title",
                        perceived=perceived_title,
                        actual=gt_title,
                        severity=SEVERITY_CRITICAL,
                        detail="La perception declara un título que no coincide con la ventana observada.",
                    )
                )
        elif gt_window is None:
            # Sin window matching: reportamos como warning, no como critical.
            mismatches.append(
                PerceptionMismatch(
                    field="window_title",
                    perceived=perceived_title,
                    actual=None,
                    severity=SEVERITY_WARNING,
                    detail=f"No se encontró ventana con título '{title}' en el WorldModel.",
                )
            )

        # 2) capture_available vs screenshot_provider
        capture_available = bool(perception.get("capture_available"))
        screenshot_declared = self._screenshot_provider_available()
        if capture_available and not screenshot_declared:
            mismatches.append(
                PerceptionMismatch(
                    field="capture_available",
                    perceived=True,
                    actual=False,
                    severity=SEVERITY_WARNING,
                    detail="Perception declara capture disponible pero no hay screenshot provider.",
                )
            )

        # 3) dom_available vs focused browser-like window
        dom_available = bool(perception.get("dom_available"))
        if dom_available and isinstance(gt_window, dict):
            app_name = str(gt_window.get("app_name") or "").lower()
            title_l = str(gt_window.get("title") or "").lower()
            looks_like_browser = (
                "chrome" in app_name
                or "edge" in app_name
                or "firefox" in app_name
                or "brave" in app_name
                or "browser" in app_name
                or "chrome" in title_l
                or "mozilla" in title_l
            )
            if not looks_like_browser:
                mismatches.append(
                    PerceptionMismatch(
                        field="dom_available",
                        perceived=True,
                        actual=False,
                        severity=SEVERITY_WARNING,
                        detail="Perception declara DOM disponible, pero la ventana matcheada no parece un browser.",
                    )
                )

        # 4) login_detected sin evidencia URL
        login_detected = bool(perception.get("login_detected"))
        if login_detected:
            latest_url = str(perception.get("latest_url") or "")
            if not latest_url:
                mismatches.append(
                    PerceptionMismatch(
                        field="login_detected",
                        perceived=True,
                        actual=None,
                        severity=SEVERITY_INFO,
                        detail="Login detectado sin URL de evidencia en la perception.",
                    )
                )

        # 5) focused consistency: si perception trae focused=True en
        #    metadata pero WorldModel no reporta focused_window matching,
        #    marcar info.
        perceived_focused = _dig(perception, "metadata", "focused")
        if perceived_focused is True and gt_window is not None:
            if not bool(gt_window.get("focused")):
                mismatches.append(
                    PerceptionMismatch(
                        field="focused",
                        perceived=True,
                        actual=False,
                        severity=SEVERITY_INFO,
                        detail="Perception declara focused=True, pero la ventana matcheada no está focuseada.",
                    )
                )

        # Ordenamos por severity (critical > warning > info) para que el
        # consumidor vea lo importante primero.
        severity_order = {
            SEVERITY_CRITICAL: 0,
            SEVERITY_WARNING: 1,
            SEVERITY_INFO: 2,
        }
        mismatches.sort(key=lambda m: severity_order.get(m.severity, 99))
        # Silencia ground_truth vacío
        _ = ground_truth  # reservado por si se usa en el futuro
        return mismatches

    def _screenshot_provider_available(self) -> bool:
        prov = self._screenshot_provider
        if prov is None:
            return False
        flag = getattr(prov, "available", None)
        if flag is None:
            return True
        try:
            return bool(flag)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Helpers


def _to_json(value: Any) -> dict[str, Any]:
    """Intenta convertir un Pydantic/dataclass a dict JSON-ready.

    Si falla, devuelve ``{}`` en vez de romper. El comparador no quiere
    propagar errores de serialización a la MCP tool.
    """

    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump(mode="json")
        except TypeError:
            dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {"value": dumped}
    if isinstance(value, dict):
        return dict(value)
    try:
        from dataclasses import asdict, is_dataclass

        if is_dataclass(value):
            return asdict(value)
    except Exception:
        pass
    return {"repr": repr(value)}


def _title_matches(candidate: Any, target: str) -> bool:
    if not target:
        return False
    if not candidate:
        return False
    return str(target).strip().lower() in str(candidate).strip().lower()


def _dig(mapping: Any, *path: str) -> Any:
    cur: Any = mapping
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
        if cur is None:
            return None
    return cur


def _elapsed_ms(clock: Callable[[], float], t0: float) -> int:
    try:
        return int(max(0.0, (clock() - t0) * 1000.0))
    except Exception:
        return 0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "PerceptionGroundTruthComparator",
    "PerceptionGroundTruthComparison",
    "PerceptionMismatch",
    "SEVERITY_CRITICAL",
    "SEVERITY_INFO",
    "SEVERITY_WARNING",
]
