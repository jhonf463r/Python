"""Tests del SelfAuditService (Frente 2 — IABV v1.5).

Cubre:
- Shape del `SelfAuditSnapshot` (contratos frozen + campos esperados).
- Detección de mismatches concretos entre `EnvironmentSelfModel` y
  `WorldModelSnapshot` (tool viva / tool missing / network desconectada
  / scan_status degradado).
- Persistencia: `data/evolution/self_audit/{latest.json, latest.md,
  history/<ISO>.json}` bajo un workspace temporal.
- Fallbacks seguros cuando los services o el ToolCard fallan
  (no debe crashear; el snapshot sigue siendo producido).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    EnvironmentMatchResult,
    EnvironmentSelfModel,
    NetworkStatusSnapshot,
    PortableContextPackage,
    PortableContextSection,
    SelfAuditSnapshot,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    ToolCard,
    ToolCheckResult,
    ToolLiveStatus,
    ToolType,
    ToolValidationStatus,
    WorldModelSnapshot,
)
from iabv_v15.services.evolution.self_audit_service import SelfAuditService


# ---------------------------------------------------------------------------
# Fakes mínimos: los services reales se reemplazan por objetos que exponen
# sólo los getters que el SelfAuditService necesita.


class _FakeToolRegistry:
    def __init__(self, cards: list[ToolCard]) -> None:
        self._cards = list(cards)

    def list_cards(self) -> list[ToolCard]:
        return list(self._cards)

    def refresh_card(self, card: ToolCard, *, force: bool = False, max_age_seconds: float | None = None) -> ToolCard:
        # Tests quieren un refresh idempotente: devolver el card como está.
        return card


class _FakeWorldModelService:
    def __init__(self, snapshot: WorldModelSnapshot | None) -> None:
        self._snapshot = snapshot

    def current_model(self) -> WorldModelSnapshot | None:
        return self._snapshot


class _FakeSelfExamService:
    def __init__(self, review: SelfExaminationSnapshot | None) -> None:
        self._review = review

    def current_review(self, *, refresh: bool = False) -> SelfExaminationSnapshot | None:
        return self._review


class _FakePortableContextService:
    def __init__(self, package: PortableContextPackage | None) -> None:
        self._package = package

    def current_package(self, *, refresh: bool = False, max_age_seconds: int = 300) -> PortableContextPackage | None:
        return self._package


# ---------------------------------------------------------------------------
# Builders


def _card(
    tool_id: str,
    *,
    available: bool = True,
    adapter_key: str = "local_adapter",
) -> ToolCard:
    return ToolCard(
        tool_id=tool_id,
        title=tool_id,
        tool_type=ToolType.SHELL,
        adapter_key=adapter_key,
        validation_status=ToolValidationStatus.APPROVED if available else ToolValidationStatus.UNVALIDATED,
        available=available,
    )


def _env(
    *,
    available_ids: list[str] | None = None,
    missing_ids: list[str] | None = None,
    scan_status: str = "ready",
) -> EnvironmentSelfModel:
    return EnvironmentSelfModel(
        environment_id="test-env",
        known_environment=True,
        scan_status=scan_status,
        available_tools=[{"tool_id": t} for t in (available_ids or [])],
        missing_tools=[{"tool_id": t} for t in (missing_ids or [])],
    )


def _world(
    *,
    live_ids: list[str] | None = None,
    connected: bool = True,
) -> WorldModelSnapshot:
    return WorldModelSnapshot(
        tool_live_status=[
            ToolLiveStatus(tool_id=t, available=True)
            for t in (live_ids or [])
        ],
        network_status=NetworkStatusSnapshot(
            connected=connected,
            status="ok" if connected else "offline",
        ),
    )


def _make_service(
    tmp_path: Path,
    *,
    cards: list[ToolCard] | None = None,
    environment: EnvironmentSelfModel | None = None,
    world_model: WorldModelSnapshot | None = None,
    review: SelfExaminationSnapshot | None = None,
    package: PortableContextPackage | None = None,
    clock: datetime | None = None,
) -> SelfAuditService:
    fixed_clock = clock or datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    return SelfAuditService(
        tool_registry=_FakeToolRegistry(cards or []),
        environment_self_model_provider=lambda: environment,
        world_model_service=_FakeWorldModelService(world_model),
        operational_self_examination_service=_FakeSelfExamService(review),
        portable_context_service=_FakePortableContextService(package),
        clock=lambda: fixed_clock,
        workspace_root=tmp_path,
    )


# ---------------------------------------------------------------------------
# Tests


def test_run_returns_frozen_snapshot_with_expected_shape(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        cards=[_card("codex", available=True), _card("chatgpt_web", available=False)],
        environment=_env(available_ids=["codex"], missing_ids=["chatgpt_web"]),
        world_model=_world(live_ids=["codex", "chatgpt_web"]),
    )

    snapshot = svc.run(reason="unit_test")

    assert isinstance(snapshot, SelfAuditSnapshot)
    with pytest.raises((AttributeError, Exception)):
        snapshot.reason = "mutated"  # frozen dataclass → no mutable.
    assert snapshot.reason == "unit_test"
    assert isinstance(snapshot.environment_match, EnvironmentMatchResult)
    assert len(snapshot.tool_checks) == 2
    assert {r.tool_id for r in snapshot.tool_checks} == {"codex", "chatgpt_web"}
    ok = [r for r in snapshot.tool_checks if r.status == "ready"]
    missing = [r for r in snapshot.tool_checks if r.status == "missing"]
    assert [r.tool_id for r in ok] == ["codex"]
    assert [r.tool_id for r in missing] == ["chatgpt_web"]
    assert all(isinstance(r, ToolCheckResult) for r in snapshot.tool_checks)
    assert snapshot.world_model_digest.get("available") is True
    assert "codex" in snapshot.world_model_digest.get("tool_live_ids", [])


def test_environment_matches_when_world_reflects_available_and_missing(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        cards=[],
        environment=_env(available_ids=["codex"], missing_ids=["chatgpt_web"], scan_status="ready"),
        world_model=_world(live_ids=["codex"], connected=True),
    )

    snapshot = svc.run(reason="match_ok")

    assert snapshot.environment_match.matched is True
    assert snapshot.environment_match.mismatches == []
    assert snapshot.environment_match.environment_digest
    assert snapshot.environment_match.world_model_digest


def test_environment_mismatch_when_env_available_but_world_missing(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        environment=_env(available_ids=["codex"]),
        world_model=_world(live_ids=[]),
    )

    snapshot = svc.run()

    assert snapshot.environment_match.matched is False
    assert any("codex" in m for m in snapshot.environment_match.mismatches)


def test_environment_mismatch_when_network_disconnected(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        environment=_env(),
        world_model=_world(connected=False),
    )

    snapshot = svc.run()

    assert snapshot.environment_match.matched is False
    assert any("network" in m.lower() or "desconect" in m.lower() for m in snapshot.environment_match.mismatches)


def test_environment_mismatch_when_scan_status_degraded(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        environment=_env(scan_status="bootstrapping"),
        world_model=_world(),
    )

    snapshot = svc.run()

    assert snapshot.environment_match.matched is False
    assert any("scan_status" in m for m in snapshot.environment_match.mismatches)


def test_pending_issues_combines_self_exam_and_portable_context(tmp_path: Path) -> None:
    review = SelfExaminationSnapshot(
        findings=[
            SelfExaminationFinding(title="patrón repetido A", description="x"),
            SelfExaminationFinding(title="patrón repetido B", description="y"),
        ],
        unresolved_risks=["riesgo live 1"],
    )
    package = PortableContextPackage(
        sections=[
            PortableContextSection(
                section_id="pending_issues",
                items=[
                    {"title": "issue portable 1"},
                    {"title": "issue portable 2"},
                ],
            )
        ],
        unresolved_fields=["portable_unresolved_X"],
    )
    svc = _make_service(
        tmp_path,
        environment=_env(),
        world_model=_world(),
        review=review,
        package=package,
    )

    snapshot = svc.run()
    pending = snapshot.pending_issues

    assert "patrón repetido A" in pending
    assert "patrón repetido B" in pending
    assert "riesgo live 1" in pending
    assert "issue portable 1" in pending
    assert "issue portable 2" in pending
    assert "portable_unresolved_X" in pending


def test_summary_markdown_includes_tool_counts_and_bounded_length(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        cards=[_card("t_ok", available=True), _card("t_bad", available=False)],
        environment=_env(),
        world_model=_world(),
    )

    snapshot = svc.run(reason="bounds")

    md = snapshot.summary_markdown
    assert "Auditoría operativa" in md
    assert "Tools OK" in md
    assert "bounds" in md
    assert len(md) <= 1500


def test_persistence_writes_latest_and_history(tmp_path: Path) -> None:
    svc = _make_service(
        tmp_path,
        cards=[_card("codex")],
        environment=_env(available_ids=["codex"]),
        world_model=_world(live_ids=["codex"]),
    )

    snapshot = svc.run(reason="persist_probe")

    root = tmp_path / "data" / "evolution" / "self_audit"
    latest_json = root / "latest.json"
    latest_md = root / "latest.md"
    history_dir = root / "history"
    assert latest_json.exists()
    assert latest_md.exists()
    assert history_dir.is_dir()
    history_files = list(history_dir.glob("*.json"))
    assert len(history_files) == 1

    payload = json.loads(latest_json.read_text(encoding="utf-8"))
    assert payload["reason"] == "persist_probe"
    assert payload["tool_checks"][0]["tool_id"] == "codex"
    assert latest_md.read_text(encoding="utf-8") == snapshot.summary_markdown


def test_history_accumulates_multiple_runs(tmp_path: Path) -> None:
    clock_values = [
        datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
    ]
    i = {"n": 0}

    def _clock() -> datetime:
        v = clock_values[i["n"]]
        i["n"] = min(i["n"] + 1, len(clock_values) - 1)
        return v

    svc = SelfAuditService(
        tool_registry=_FakeToolRegistry([]),
        environment_self_model_provider=lambda: _env(),
        world_model_service=_FakeWorldModelService(_world()),
        operational_self_examination_service=_FakeSelfExamService(None),
        portable_context_service=_FakePortableContextService(None),
        clock=_clock,
        workspace_root=tmp_path,
    )
    svc.run(reason="run_1")
    svc.run(reason="run_2")

    history = list((tmp_path / "data" / "evolution" / "self_audit" / "history").glob("*.json"))
    assert len(history) == 2


def test_service_survives_missing_services(tmp_path: Path) -> None:
    svc = SelfAuditService(
        tool_registry=_FakeToolRegistry([]),
        environment_self_model_provider=lambda: None,
        world_model_service=None,
        operational_self_examination_service=None,
        portable_context_service=None,
        workspace_root=tmp_path,
    )

    snapshot = svc.run(reason="degraded")

    assert isinstance(snapshot, SelfAuditSnapshot)
    assert snapshot.tool_checks == []
    assert snapshot.environment_match.matched is False
    assert snapshot.world_model_digest.get("available") is False


def test_toolcard_dry_check_available_returns_ready() -> None:
    card = _card("codex", available=True)
    result = card.dry_check()
    assert isinstance(result, ToolCheckResult)
    assert result.tool_id == "codex"
    assert result.available is True
    assert result.status == "ready"
    assert result.evidence["adapter_key"] == "local_adapter"


def test_toolcard_dry_check_unavailable_returns_missing() -> None:
    card = _card("codex", available=False)
    result = card.dry_check()
    assert result.available is False
    assert result.status == "missing"
    assert result.reason is not None
