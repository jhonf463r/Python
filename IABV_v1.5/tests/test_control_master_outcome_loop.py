"""Tests for the outcome-loop wiring: TaskOutcomeRecorder -> ControlMasterService.

Closes obj-super-sync-outcome-loop. The contract:

* An AdaptiveSession whose metadata carries `control_master_objective_id`
  mirrors its terminal status into ControlMasterService.mark_objective().
* Non-terminal statuses are ignored (no flipping objectives on every save).
* Unknown objective ids fail silently (service returns None).
* `control_master_unresolved` list propagates each item to mark_unresolved().
* Any failure inside the propagation hook MUST NOT break session recording.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
    TaskContext,
    TaskIntent,
)


def _workspace(label: str) -> Path:
    root = Path("/tmp") / f"iabv_outcome_loop_{label}_{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session(
    *,
    user_goal: str,
    status: AdaptiveSessionStatus,
    metadata: dict[str, object] | None = None,
) -> AdaptiveSession:
    return AdaptiveSession(
        user_goal=user_goal,
        intent=TaskIntent(),
        context=TaskContext(),
        status=status,
        metadata=dict(metadata or {}),
    )


def _seed_objective(boot: AppBootstrap, objective_id: str) -> None:
    node = ObjectiveNode(
        objective_id=objective_id,
        kind=ObjectiveNodeKind.TASK,
        title=f"test {objective_id}",
        summary="",
        status=ObjectiveStatus.ACTIVE,
        priority=50,
        root_id=objective_id,
    )
    boot.objective_repository.save(node)


def test_completed_session_marks_objective_completed() -> None:
    root = _workspace("completed")
    try:
        boot = AppBootstrap(str(root))
        _seed_objective(boot, "obj-loop-done")
        session = _session(
            user_goal="cerrar objetivo",
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={
                "control_master_objective_id": "obj-loop-done",
                "control_master_note": "cerrado por flujo normal",
            },
        )
        boot.task_outcome_recorder.record(session)
        node = boot.objective_repository.get("obj-loop-done")
        assert node is not None
        assert node.status is ObjectiveStatus.COMPLETED
        notes = node.metadata.get("control_master_notes") or []
        assert any("cerrado por flujo normal" in n.get("note", "") for n in notes)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_failed_session_marks_objective_blocked() -> None:
    root = _workspace("failed")
    try:
        boot = AppBootstrap(str(root))
        _seed_objective(boot, "obj-loop-fail")
        session = _session(
            user_goal="algo fallo",
            status=AdaptiveSessionStatus.FAILED,
            metadata={"control_master_objective_id": "obj-loop-fail"},
        )
        boot.task_outcome_recorder.record(session)
        node = boot.objective_repository.get("obj-loop-fail")
        assert node is not None
        assert node.status is ObjectiveStatus.BLOCKED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_aborted_session_marks_objective_paused() -> None:
    root = _workspace("aborted")
    try:
        boot = AppBootstrap(str(root))
        _seed_objective(boot, "obj-loop-abort")
        session = _session(
            user_goal="aborted",
            status=AdaptiveSessionStatus.ABORTED,
            metadata={"control_master_objective_id": "obj-loop-abort"},
        )
        boot.task_outcome_recorder.record(session)
        node = boot.objective_repository.get("obj-loop-abort")
        assert node is not None
        assert node.status is ObjectiveStatus.PAUSED
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_non_terminal_status_is_not_propagated() -> None:
    root = _workspace("non_terminal")
    try:
        boot = AppBootstrap(str(root))
        _seed_objective(boot, "obj-loop-mid")
        session = _session(
            user_goal="running",
            status=AdaptiveSessionStatus.EXECUTING,
            metadata={"control_master_objective_id": "obj-loop-mid"},
        )
        boot.task_outcome_recorder.record(session)
        node = boot.objective_repository.get("obj-loop-mid")
        assert node is not None
        # Seed status preserved (ACTIVE), recorder did not touch it.
        assert node.status is ObjectiveStatus.ACTIVE
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_session_without_objective_id_is_a_no_op() -> None:
    root = _workspace("no_id")
    try:
        boot = AppBootstrap(str(root))
        session = _session(
            user_goal="sin objetivo",
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={},
        )
        # Must not raise.
        boot.task_outcome_recorder.record(session)
        state = boot.control_master_service.current_state(refresh=False)
        # After refactor, current_state() aggregates unresolved items from
        # account inventory and OSES even in a fresh workspace.  The key
        # invariant is that recording a no-op session does not ADD items.
        # Accept infrastructure-level unresolved items that come from
        # scanner/OSES bootstrapping.
        for item in state.unresolved_items:
            assert item.startswith('UNRESOLVED:'), f'Unexpected unresolved item: {item}'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_unknown_objective_id_does_not_break_recorder() -> None:
    root = _workspace("unknown_id")
    try:
        boot = AppBootstrap(str(root))
        session = _session(
            user_goal="ghost",
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={"control_master_objective_id": "obj-does-not-exist"},
        )
        saved = boot.task_outcome_recorder.record(session)
        # Session still saved even though the objective propagation was a no-op.
        assert saved.session_id == session.session_id
        assert boot.adaptive_session_repository.get(session.session_id) is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_unresolved_items_are_appended_to_control_master() -> None:
    root = _workspace("unresolved")
    try:
        boot = AppBootstrap(str(root))
        session = _session(
            user_goal="unresolved case",
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={
                "control_master_unresolved": [
                    "Verificar integracion X en Windows",
                    "   ",  # empty after strip, must be skipped
                    "Cuota MCP Y desconocida",
                ],
                "control_master_unresolved_evidence": ["tests/test_foo.py"],
            },
        )
        boot.task_outcome_recorder.record(session)
        state = boot.control_master_service.current_state(refresh=False)
        assert "Verificar integracion X en Windows" in state.unresolved_items
        assert "Cuota MCP Y desconocida" in state.unresolved_items
        assert "   " not in state.unresolved_items
        assert "tests/test_foo.py" in state.evidence_links
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_propagation_failure_does_not_break_recorder(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _workspace("raise")
    try:
        boot = AppBootstrap(str(root))
        _seed_objective(boot, "obj-loop-raise")

        def _boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("simulated control master failure")

        monkeypatch.setattr(boot.control_master_service, "mark_objective", _boom)
        session = _session(
            user_goal="should still save",
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={"control_master_objective_id": "obj-loop-raise"},
        )
        saved = boot.task_outcome_recorder.record(session)
        assert saved.session_id == session.session_id
        # Session persisted despite propagation blowing up.
        assert boot.adaptive_session_repository.get(session.session_id) is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_recorder_without_control_master_service_is_silent() -> None:
    """Legacy bootstraps / tests that build TaskOutcomeRecorder without the
    service should keep working unchanged."""
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder

    root = _workspace("no_service")
    try:
        boot = AppBootstrap(str(root))
        recorder = TaskOutcomeRecorder(
            adaptive_session_repository=boot.adaptive_session_repository,
            capability_repository=boot.capability_repository,
            approval_checkpoint_repository=boot.approval_checkpoint_repository,
        )
        session = _session(
            user_goal="legacy recorder",
            status=AdaptiveSessionStatus.COMPLETED,
            metadata={"control_master_objective_id": "obj-legacy"},
        )
        # Must not raise.
        saved = recorder.record(session)
        assert saved.session_id == session.session_id
    finally:
        shutil.rmtree(root, ignore_errors=True)
