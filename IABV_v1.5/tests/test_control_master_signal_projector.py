from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from iabv_v15.domain.models import ControlMasterState
from iabv_v15.services.evolution.control_master_signal_projector import (
    ControlMasterSignalProjector,
)


def _state() -> ControlMasterState:
    return ControlMasterState(
        state_id="state-2026-10-31-a",
        active_objective_ids=["obj-control-master-super-sync"],
        last_updated=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


def test_projection_excludes_free_text_and_local_evidence() -> None:
    queue = [{
        "id": "objective:obj-control-master-super-sync",
        "title": "PRIVATE TITLE MUST NOT LEAVE THE WORKSPACE",
        "status": "active",
        "source": "objective_repository",
        "priority_score": 80,
        "priority_label": "high",
        "next_action": "PRIVATE NEXT ACTION",
        "reason": "PRIVATE REASON",
        "evidence_refs": ["C:/Python/private.txt"],
    }]

    signal = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=queue,
        observed_at_utc=datetime.now(timezone.utc),
    )

    assert signal["signal_status"] == "AVAILABLE"
    assert signal["queue"]["status"] == "NON_EMPTY_QUEUE"
    assert signal["queue"]["items"] == [{
        "item_id": "queue-item-01",
        "status": "active",
        "source": "objective_repository",
        "priority_label": "high",
        "priority_score": 80,
    }]
    serialized = str(signal)
    assert "PRIVATE" not in serialized
    assert "C:/Python" not in serialized
    assert "evidence_refs" not in serialized
    assert "obj-control-master-super-sync" not in serialized
    assert "queue-item-01" in serialized


def test_empty_queue_is_distinct_from_unavailable() -> None:
    empty = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[],
        observed_at_utc=datetime.now(timezone.utc),
    )
    unavailable = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[],
        source_errors=("OBJECTIVES_READ_FAILED:active",),
        observed_at_utc=datetime.now(timezone.utc),
    )

    assert empty["signal_status"] == "EMPTY_QUEUE"
    assert unavailable["signal_status"] == "UNAVAILABLE"
    assert unavailable["queue"]["item_count"] is None
    assert unavailable["queue"]["items"] == []


def test_unportable_queue_item_fails_closed() -> None:
    signal = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[{
            "id": "objective:unsafe id",
            "status": "active",
            "source": "objective_repository",
            "priority_score": 50,
            "priority_label": "medium",
        }],
        observed_at_utc=datetime.now(timezone.utc),
    )
    assert signal["signal_status"] == "UNAVAILABLE"
    assert signal["reason_codes"] == ["QUEUE_ITEM_NOT_PORTABLE"]


def test_publisher_will_not_publish_unavailable_signal() -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    signal = ControlMasterSignalProjector.unavailable("SOURCE_READ_FAILED")
    result = ControlMasterSignalPublisher().publish(signal)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "SIGNAL_NOT_AVAILABLE"


def test_publisher_accepts_current_integral_signal_shape_without_writing() -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    signal = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[{
            "id": "objective:obj-control-master-super-sync",
            "title": "not included in the payload",
            "status": "active",
            "source": "objective_repository",
            "priority_score": 80,
            "priority_label": "critical",
        }],
    )
    assert ControlMasterSignalPublisher._validate_signal(signal) is None


def test_publisher_rejects_signal_after_content_tampering() -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    signal = ControlMasterSignalProjector.project(state=_state(), work_queue=[])
    signal["counts"]["queue_items_published"] = 999
    assert ControlMasterSignalPublisher._validate_signal(signal) == "SIGNAL_HASH_MISMATCH"


def test_publisher_rejects_signal_id_mismatch_even_with_recomputed_content_hash() -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    signal = ControlMasterSignalProjector.project(state=_state(), work_queue=[])
    signal["signal_id"] = "cms-" + ("0" * 24)
    unhashed = {key: value for key, value in signal.items() if key != "content_sha256"}
    canonical = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    signal["content_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert ControlMasterSignalPublisher._validate_signal(signal) == "SIGNAL_ID_HASH_MISMATCH"


def test_projection_counts_only_items_present_in_verified_payload() -> None:
    signal = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[{
            "id": "objective:obj-control-master-super-sync",
            "status": "active",
            "source": "objective_repository",
            "priority_score": 80,
            "priority_label": "high",
        }],
    )
    assert signal["counts"] == {"queue_items_published": 1}


def test_publisher_blocks_unhashable_malformed_status_without_transport() -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    signal = ControlMasterSignalProjector.project(state=_state(), work_queue=[])
    signal["signal_status"] = []
    result = ControlMasterSignalPublisher().publish(signal)

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "SIGNAL_VALIDATION_FAILED"


def test_projection_rejects_unhashable_source_value_without_raising() -> None:
    signal = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[{
            "id": "objective:obj-control-master-super-sync",
            "status": "active",
            "source": ["objective_repository"],
            "priority_score": 80,
            "priority_label": "high",
        }],
    )
    assert signal["signal_status"] == "UNAVAILABLE"
    assert signal["reason_codes"] == ["QUEUE_ITEM_NOT_PORTABLE"]


def test_publisher_rejects_non_directory_path_component(tmp_path) -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    checkout = tmp_path / "clone"
    checkout.mkdir()
    (checkout / "IABV_v1.5").write_text("not a directory", encoding="utf-8")

    try:
        ControlMasterSignalPublisher._safe_signal_target(checkout)
    except RuntimeError as exc:
        assert str(exc) == "SIGNAL_PATH_COMPONENT_NOT_DIRECTORY"
    else:
        raise AssertionError("publisher must reject a non-directory signal path component")


def test_projection_timestamp_is_observation_not_persisted_modification_time() -> None:
    observed = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    persisted_modified = observed - timedelta(days=120)
    state = _state().model_copy(update={"last_updated": persisted_modified})

    signal = ControlMasterSignalProjector.project(
        state=state,
        work_queue=[],
        observed_at_utc=observed,
    )

    assert signal["source"]["state_observed_at_utc"] == observed.isoformat()
    assert signal["source"]["state_observed_at_utc"] != persisted_modified.isoformat()


def test_publisher_rejects_public_branch_with_non_signal_tree_changes() -> None:
    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    signal_path = "IABV_v1.5/data/evolution/control_master/shared_signal.json"
    assert ControlMasterSignalPublisher._public_branch_delta_is_allowlisted([])
    assert ControlMasterSignalPublisher._public_branch_delta_is_allowlisted([signal_path])
    assert not ControlMasterSignalPublisher._public_branch_delta_is_allowlisted(["README.md"])
    assert not ControlMasterSignalPublisher._public_branch_delta_is_allowlisted(
        [signal_path, "README.md"]
    )


def test_publisher_verifies_exact_remote_ref_commit_and_content(
    tmp_path, monkeypatch
) -> None:
    from types import SimpleNamespace

    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    publisher = ControlMasterSignalPublisher()
    expected_commit = "a" * 40
    expected_content = '{"signal_status":"AVAILABLE"}\\n'
    remote_ref = "refs/heads/control-master-live"
    commands: list[list[str]] = []

    def fake_run(args, *, cwd=None, allow_returncodes=(0,)):
        commands.append(list(args))
        if args[0] == "ls-remote":
            return SimpleNamespace(stdout=f"{expected_commit}\\t{remote_ref}\\n")
        if args[0] == "fetch":
            return SimpleNamespace(stdout="")
        if args[0] == "rev-parse":
            return SimpleNamespace(stdout=f"{expected_commit}\\n")
        if args[0] == "show":
            return SimpleNamespace(stdout=expected_content)
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr(publisher, "_run_git", fake_run)

    result = publisher._verify_remote_publication(
        checkout=tmp_path,
        expected_commit=expected_commit,
        expected_content=expected_content,
    )

    assert result is None
    assert any(command[0] == "fetch" for command in commands)
    assert any(command[0] == "show" for command in commands)


def test_publisher_reports_remote_content_mismatch_after_push(
    tmp_path, monkeypatch
) -> None:
    from types import SimpleNamespace

    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    publisher = ControlMasterSignalPublisher()
    expected_commit = "b" * 40
    remote_ref = "refs/heads/control-master-live"

    def fake_run(args, *, cwd=None, allow_returncodes=(0,)):
        if args[0] == "ls-remote":
            return SimpleNamespace(stdout=f"{expected_commit}\\t{remote_ref}\\n")
        if args[0] == "fetch":
            return SimpleNamespace(stdout="")
        if args[0] == "rev-parse":
            return SimpleNamespace(stdout=f"{expected_commit}\\n")
        if args[0] == "show":
            return SimpleNamespace(stdout='{"signal_status":"DIFFERENT"}\\n')
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr(publisher, "_run_git", fake_run)

    result = publisher._verify_remote_publication(
        checkout=tmp_path,
        expected_commit=expected_commit,
        expected_content='{"signal_status":"AVAILABLE"}\\n',
    )

    assert result == "REMOTE_CONTENT_MISMATCH"


def test_publisher_reports_remote_head_mismatch_after_push(
    tmp_path, monkeypatch
) -> None:
    from types import SimpleNamespace

    from iabv_v15.services.evolution.control_master_signal_publisher import (
        ControlMasterSignalPublisher,
    )

    publisher = ControlMasterSignalPublisher()
    remote_ref = "refs/heads/control-master-live"
    commands: list[list[str]] = []

    def fake_run(args, *, cwd=None, allow_returncodes=(0,)):
        commands.append(list(args))
        if args[0] == "ls-remote":
            return SimpleNamespace(stdout=f"{'c' * 40}\\t{remote_ref}\\n")
        raise AssertionError(f"Unexpected git command after mismatched head: {args}")

    monkeypatch.setattr(publisher, "_run_git", fake_run)

    result = publisher._verify_remote_publication(
        checkout=tmp_path,
        expected_commit="d" * 40,
        expected_content="{}\\n",
    )

    assert result == "REMOTE_HEAD_MISMATCH"
    assert len(commands) == 1
