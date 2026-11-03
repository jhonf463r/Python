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


def _viewmodel(*, github_remote_service: Any) -> EvolutionCenterViewModel:
    return EvolutionCenterViewModel(
        dossier_repository=_EmptyRepository(),  # type: ignore[arg-type]
        hidden_incident_repository=_EmptyRepository(),  # type: ignore[arg-type]
        evolution_review_service=_EmptyEvolutionReviewService(),  # type: ignore[arg-type]
        incident_packet_service=None,  # type: ignore[arg-type]
        self_check_orchestrator=None,  # type: ignore[arg-type]
        github_remote_service=github_remote_service,
    )


def test_evolution_center_viewmodel_imports_without_app_bootstrap() -> None:
    assert EvolutionCenterViewModel.__name__ == "EvolutionCenterViewModel"


def test_refresh_does_not_publish_and_manual_action_uses_fake_remote_service() -> None:
    completed = threading.Event()
    calls: list[dict[str, object]] = []
    fake_result = {
        "success": True,
        "branch": "feature/viewmodel-import-regression",
        "base": "main",
        "pr_number": 421,
        "pr_url": "https://example.invalid/pull/421",
        "pushed": False,
    }

    class _FakeGitHubRemoteService:
        def publish_branch_as_pr(self, **kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            completed.set()
            return dict(fake_result)

    viewmodel = _viewmodel(github_remote_service=_FakeGitHubRemoteService())

    # A normal refresh must not trigger the manually requested action.
    viewmodel.refresh()
    assert calls == []

    # Exercise the existing manual ViewModel action with a fake service only.
    viewmodel.publishBranchAsPR(
        "feature/viewmodel-import-regression",
        "ViewModel import regression",
        "synthetic body",
        "main",
        3,
        True,
    )
    assert completed.wait(timeout=5.0), "the fake remote service was not invoked"
    assert calls == [{
        "branch": "feature/viewmodel-import-regression",
        "title": "ViewModel import regression",
        "body": "synthetic body",
        "base": "main",
        "diff_lines": 3,
        "draft": True,
    }]

    # Apply a synthetic response; no network or GitHub write occurs.
    viewmodel._apply_result("publish_pr", fake_result)
    assert "PR #421" in viewmodel.get_publish_pr_status()
    assert "example.invalid/pull/421" in viewmodel.get_publish_pr_status()
    assert viewmodel.get_working() is False
    assert calls == [{
        "branch": "feature/viewmodel-import-regression",
        "title": "ViewModel import regression",
        "body": "synthetic body",
        "base": "main",
        "diff_lines": 3,
        "draft": True,
    }]
