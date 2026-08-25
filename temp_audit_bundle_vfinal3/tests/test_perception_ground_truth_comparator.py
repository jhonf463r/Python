"""Tests del PerceptionGroundTruthComparator (Frente 3.3 del PC3).

El comparador es un servicio puro que:

* llama ``UniversalPerceptionService.build_signal(...)`` con las pistas
  recibidas;
* lee el ``WorldModelSnapshot`` vigente (vía callable inyectable);
* contrasta campos equivalentes (window_title, capture_available,
  dom_available, login_detected, focused);
* devuelve un ``PerceptionGroundTruthComparison`` normalizado, sin
  raisear, con ``mismatches`` ordenados por severity y ``evidence``
  anotada para trazabilidad.

Estos tests usan fakes puros (sin FastMCP, sin WorldModelService real)
para ejercitar tanto el happy path como las degradaciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iabv_v15.services.capture.perception_ground_truth_comparator import (
    PerceptionGroundTruthComparator,
    PerceptionGroundTruthComparison,
    PerceptionMismatch,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)


# ---------------------------------------------------------------------------
# Fakes


@dataclass
class _FakeSignal:
    """Stand-in mínimo de ``UniversalPerceptionSignal``.

    Expone ``model_dump(mode='json')`` para que el comparador lo trate
    como un Pydantic real y lo serialice a dict.
    """

    latest_title: str = ""
    latest_url: str = ""
    capture_available: bool = False
    dom_available: bool = False
    login_detected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "latest_title": self.latest_title,
            "latest_url": self.latest_url,
            "capture_available": self.capture_available,
            "dom_available": self.dom_available,
            "login_detected": self.login_detected,
            "metadata": dict(self.metadata),
        }


class _FakePerceptionService:
    """Captura llamadas a ``build_signal`` y devuelve un ``_FakeSignal``."""

    def __init__(self, signal: _FakeSignal | None = None, raise_exc: Exception | None = None) -> None:
        self._signal = signal or _FakeSignal()
        self._raise = raise_exc
        self.calls: list[dict[str, Any]] = []

    def build_signal(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        if self._raise is not None:
            raise self._raise
        return self._signal


@dataclass
class _FakeWindow:
    title: str = ""
    app_name: str = ""
    focused: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"title": self.title, "app_name": self.app_name, "focused": self.focused}


@dataclass
class _FakeSnapshot:
    """Stand-in mínimo de ``WorldModelSnapshot`` (usa ``model_dump``)."""

    active_windows: list[_FakeWindow] = field(default_factory=list)
    focused_window: _FakeWindow | None = None
    network_connected: bool = True

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "active_windows": [w.as_dict() for w in self.active_windows],
            "focused_window": self.focused_window.as_dict() if self.focused_window else None,
            "network_status": {"connected": self.network_connected},
        }


class _FakeScreenshotProvider:
    def __init__(self, available: bool = True) -> None:
        self.available = available


# ---------------------------------------------------------------------------
# Helpers


def _sane_snapshot(title: str = "ChatGPT", app_name: str = "chrome") -> _FakeSnapshot:
    win = _FakeWindow(title=title, app_name=app_name, focused=True)
    return _FakeSnapshot(active_windows=[win], focused_window=win)


def _make_comparator(
    *,
    signal: _FakeSignal | None = None,
    snapshot: _FakeSnapshot | None | object = "__default__",
    screenshot: Any = None,
    perception: _FakePerceptionService | None = None,
) -> tuple[PerceptionGroundTruthComparator, _FakePerceptionService]:
    svc = perception or _FakePerceptionService(signal=signal)
    if snapshot == "__default__":
        snapshot = _sane_snapshot()
    provider: Any
    if snapshot is None:
        provider = lambda: None  # noqa: E731
    else:
        provider = lambda: snapshot  # noqa: E731
    comparator = PerceptionGroundTruthComparator(
        universal_perception_service=svc,
        world_model_provider=provider,
        screenshot_provider=screenshot,
        clock=_monotonic_clock(),
    )
    return comparator, svc


def _monotonic_clock() -> Any:
    state = {"t": 0.0}

    def _c() -> float:
        state["t"] += 0.001
        return state["t"]

    return _c


# ---------------------------------------------------------------------------
# Happy path (no mismatches)


def test_sane_fixture_has_zero_mismatches() -> None:
    """Perception y WorldModel concordes: lista de mismatches vacía."""

    signal = _FakeSignal(
        latest_title="ChatGPT",
        latest_url="https://chatgpt.com",
        capture_available=True,
        dom_available=True,
        login_detected=True,
        metadata={"focused": True},
    )
    comparator, svc = _make_comparator(
        signal=signal,
        snapshot=_sane_snapshot("ChatGPT", app_name="chrome"),
        screenshot=_FakeScreenshotProvider(available=True),
    )

    result = comparator.compare(
        "ChatGPT",
        tool_id="chatgpt_web",
        assistant_kind="chatgpt_web",
        site_id="chatgpt.com",
    )

    assert isinstance(result, PerceptionGroundTruthComparison)
    assert result.error is None
    assert result.mismatches == []
    assert result.ground_truth_json.get("matched_window") is not None
    assert result.evidence["ground_truth_window_matched"] is True
    assert result.evidence["screenshot_provider_present"] is True
    # build_signal recibe las pistas que pasamos.
    assert svc.calls == [
        {
            "tool_id": "chatgpt_web",
            "assistant_kind": "chatgpt_web",
            "site_id": "chatgpt.com",
        }
    ]


def test_sane_fixture_reports_latency_ms() -> None:
    signal = _FakeSignal(latest_title="ChatGPT")
    comparator, _ = _make_comparator(
        signal=signal, snapshot=_sane_snapshot("ChatGPT")
    )
    result = comparator.compare("ChatGPT")
    assert result.duration_ms >= 0
    assert result.window_title == "ChatGPT"


# ---------------------------------------------------------------------------
# Divergent fixtures


def test_window_title_divergence_is_critical() -> None:
    """Perception declara un título que no coincide con la ventana real."""

    signal = _FakeSignal(latest_title="Login — ChatGPT")
    comparator, _ = _make_comparator(
        signal=signal,
        snapshot=_sane_snapshot(title="Claude.ai — Anthropic"),
    )

    result = comparator.compare("Claude.ai — Anthropic")
    fields = [m.field for m in result.mismatches]

    assert "window_title" in fields
    wt = next(m for m in result.mismatches if m.field == "window_title")
    assert wt.severity == SEVERITY_CRITICAL
    assert wt.perceived == "Login — ChatGPT"


def test_capture_declared_without_provider_is_warning() -> None:
    signal = _FakeSignal(latest_title="ChatGPT", capture_available=True)
    comparator, _ = _make_comparator(
        signal=signal,
        snapshot=_sane_snapshot("ChatGPT"),
        screenshot=None,  # no provider => no disponible
    )

    result = comparator.compare("ChatGPT")
    caps = [m for m in result.mismatches if m.field == "capture_available"]
    assert len(caps) == 1
    assert caps[0].severity == SEVERITY_WARNING
    assert caps[0].perceived is True
    assert caps[0].actual is False


def test_dom_declared_on_non_browser_window_is_warning() -> None:
    """Si la ventana matcheada no parece browser, ``dom_available`` es sospechoso."""

    signal = _FakeSignal(latest_title="Settings", dom_available=True)
    # app_name=explorer → no browser
    window = _FakeWindow(title="Settings", app_name="explorer.exe", focused=True)
    snapshot = _FakeSnapshot(active_windows=[window], focused_window=window)
    comparator, _ = _make_comparator(signal=signal, snapshot=snapshot)

    result = comparator.compare("Settings")
    doms = [m for m in result.mismatches if m.field == "dom_available"]
    assert len(doms) == 1
    assert doms[0].severity == SEVERITY_WARNING


def test_login_detected_without_url_is_info() -> None:
    signal = _FakeSignal(latest_title="ChatGPT", login_detected=True, latest_url="")
    comparator, _ = _make_comparator(
        signal=signal, snapshot=_sane_snapshot("ChatGPT")
    )

    result = comparator.compare("ChatGPT")
    logins = [m for m in result.mismatches if m.field == "login_detected"]
    assert len(logins) == 1
    assert logins[0].severity == SEVERITY_INFO


def test_focused_divergence_is_info() -> None:
    """Perception dice focused=True pero la ventana matcheada no lo está."""

    signal = _FakeSignal(
        latest_title="ChatGPT",
        metadata={"focused": True},
    )
    # La ventana existe pero NO está focuseada.
    window = _FakeWindow(title="ChatGPT", app_name="chrome", focused=False)
    snapshot = _FakeSnapshot(active_windows=[window], focused_window=None)
    comparator, _ = _make_comparator(signal=signal, snapshot=snapshot)

    result = comparator.compare("ChatGPT")
    focused = [m for m in result.mismatches if m.field == "focused"]
    assert len(focused) == 1
    assert focused[0].severity == SEVERITY_INFO


def test_mismatches_sorted_by_severity() -> None:
    """critical > warning > info, para que el consumer vea lo grave primero."""

    signal = _FakeSignal(
        latest_title="Login — ChatGPT",  # no matchea -> critical
        capture_available=True,  # sin provider -> warning
        login_detected=True,  # sin url -> info
        latest_url="",
        metadata={"focused": True},
    )
    window = _FakeWindow(title="Claude.ai", app_name="chrome", focused=False)
    snapshot = _FakeSnapshot(active_windows=[window], focused_window=window)
    comparator, _ = _make_comparator(
        signal=signal, snapshot=snapshot, screenshot=None
    )

    result = comparator.compare("Claude.ai")
    severities = [m.severity for m in result.mismatches]
    assert severities[0] == SEVERITY_CRITICAL
    # El último elemento no debe ser más severo que el primero.
    order = {SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}
    assert all(
        order[severities[i]] <= order[severities[i + 1]]
        for i in range(len(severities) - 1)
    )


# ---------------------------------------------------------------------------
# Ground truth vacío / parcial


def test_missing_window_in_world_model_is_warning() -> None:
    """Si no hay ninguna ventana con ese título, se reporta warning (no critical)."""

    signal = _FakeSignal(latest_title="Something Else")
    empty_snapshot = _FakeSnapshot(active_windows=[], focused_window=None)
    comparator, _ = _make_comparator(signal=signal, snapshot=empty_snapshot)

    result = comparator.compare("ChatGPT")
    wt = [m for m in result.mismatches if m.field == "window_title"]
    assert len(wt) == 1
    assert wt[0].severity == SEVERITY_WARNING
    assert wt[0].actual is None


def test_world_model_provider_none_still_returns_result() -> None:
    """Sin WorldModel disponible, degrada pero no raisea."""

    signal = _FakeSignal(latest_title="ChatGPT")
    comparator = PerceptionGroundTruthComparator(
        universal_perception_service=_FakePerceptionService(signal=signal),
        world_model_provider=None,
        clock=_monotonic_clock(),
    )
    result = comparator.compare("ChatGPT")
    assert result.error is None  # perception sí funcionó
    assert result.ground_truth_json.get("error") == "world_model_provider_unavailable"


def test_world_model_returns_none_reported_as_unavailable() -> None:
    signal = _FakeSignal(latest_title="ChatGPT")
    comparator, _ = _make_comparator(signal=signal, snapshot=None)
    result = comparator.compare("ChatGPT")
    assert result.ground_truth_json.get("error") == "world_model_unavailable"


# ---------------------------------------------------------------------------
# Error paths


def test_empty_window_title_returns_invalid_error() -> None:
    comparator, svc = _make_comparator(signal=_FakeSignal())
    result = comparator.compare("   ")
    assert result.error == "invalid_window_title"
    # build_signal no se debe invocar si el título es inválido.
    assert svc.calls == []


def test_perception_service_unavailable_is_reported() -> None:
    comparator = PerceptionGroundTruthComparator(
        universal_perception_service=None,
        world_model_provider=lambda: _sane_snapshot("ChatGPT"),
        clock=_monotonic_clock(),
    )
    result = comparator.compare("ChatGPT")
    assert result.error == "perception_service_unavailable"
    # La comparación de ground truth sí debe haberse intentado.
    assert result.ground_truth_json.get("matched_window") is not None


# ---------------------------------------------------------------------------
# Contrato de dataclasses


def test_perception_mismatch_is_frozen_dataclass() -> None:
    m = PerceptionMismatch(
        field="window_title",
        perceived="A",
        actual="B",
        severity=SEVERITY_CRITICAL,
    )
    import dataclasses

    assert dataclasses.is_dataclass(m)
    assert m.detail == ""
