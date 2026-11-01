from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from iabv_v15.domain.models import ControlMasterState
from iabv_v15.services.evolution.control_master_signal_projector import (
    ControlMasterSignalProjector,
)


def _state() -> ControlMasterState:
    return ControlMasterState(
        state_id="state-2026-10-31-a",
        active_objective_ids=["obj-control-master-super-sync"],
        last_updated=datetime(2026, 10, 31, 20, 0, tzinfo=timezone.utc),
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
        observed_at_utc=datetime(2026, 10, 31, 20, 1, tzinfo=timezone.utc),
    )

    assert signal["signal_status"] == "AVAILABLE"
    assert signal["queue"]["status"] == "NON_EMPTY_QUEUE"
    assert signal["queue"]["items"] == [{
        "item_id": "item-" + __import__("hashlib").sha256(
            b"objective:obj-control-master-super-sync"
        ).hexdigest()[:24],
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


def test_empty_queue_is_distinct_from_unavailable() -> None:
    empty = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[],
        observed_at_utc=datetime(2026, 10, 31, 20, 1, tzinfo=timezone.utc),
    )
    unavailable = ControlMasterSignalProjector.project(
        state=_state(),
        work_queue=[],
        source_errors=("OBJECTIVES_READ_FAILED:active",),
        observed_at_utc=datetime(2026, 10, 31, 20, 1, tzinfo=timezone.utc),
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
        observed_at_utc=datetime(2026, 10, 31, 20, 1, tzinfo=timezone.utc),
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
    signal["counts"]["active_objectives"] = 999
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
