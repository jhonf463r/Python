from __future__ import annotations

import threading
from typing import Any

import pytest

pytest.importorskip("PySide6")

# Deliberately import the ViewModel directly at module collection time.
# Do not import AppBootstrap here: the regression is the direct-import cycle.
from iabv_v15.ui.viewmodels.evolution_center_viewmodel import EvolutionCenterViewModel


class _EmptyRepository:
    def list_recent(self, *, limit: int = 0) -> list[Any]:
        return []


class _EmptyEvolutionReviewService:
    def build_project_health(self) -> None:
        return None

    def build_improvement_backlog(self, limit: int = 8) -> list[Any]:
        return []


def test_evolution_center_viewmodel_imports_without_app_bootstrap() -> None:
    assert EvolutionCenterViewModel.__name__ == "EvolutionCenterViewModel"


def test_refresh_does_not_publish_and_manual_action_uses_injected_action() -> None:
    completed = threading.Event()
    calls: list[dict[str, object]] = []

    def fake_publish_action(*, refresh: bool = False) -> dict[str, object]:
        calls.append({"refresh": refresh})
        result = {
            "status": "PUBLISHED",
            "branch": "control-master-test-only",
            "commit_sha": "b" * 40,
            "main_modified": False,
            "force_push": False,
        }
        completed.set()
        return result

    viewmodel = EvolutionCenterViewModel(
        dossier_repository=_EmptyRepository(),  # type: ignore[arg-type]
        hidden_incident_repository=_EmptyRepository(),  # type: ignore[arg-type]
        evolution_review_service=_EmptyEvolutionReviewService(),  # type: ignore[arg-type]
        incident_packet_service=None,  # type: ignore[arg-type]
        self_check_orchestrator=None,  # type: ignore[arg-type]
        control_master_signal_publish_action=fake_publish_action,
    )

    # A normal refresh must never trigger the explicit publication action.
    viewmodel.refresh()
    assert calls == []

    # Only the explicit ViewModel slot invokes the injected fake action.
    viewmodel.publishControlMasterSignal()
    assert completed.wait(timeout=5.0), "the injected fake action was not invoked"
    assert calls == [{"refresh": False}]

    # Apply a synthetic result directly; no real publisher or Git operation runs.
    viewmodel._apply_result("publish_control_master_signal", {
        "status": "PUBLISHED",
        "branch": "control-master-test-only",
        "commit_sha": "b" * 40,
        "main_modified": False,
        "force_push": False,
    })

    status = viewmodel.get_control_master_signal_publish_status()
    assert "control-master-test-only" in status
    assert "bbbbbbbb" in status
    assert viewmodel.get_working() is False
    assert calls == [{"refresh": False}]
