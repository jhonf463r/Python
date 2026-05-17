"""P0.29 tests: Test Governance Observability and ControlMaster Test State.

Verifies:
1. audit_tools.run_pytest() persists compact TestEvidence when requested.
2. SelfAuditService reports tests_observed=true with fresh evidence.
3. ControlMaster markdown renders current_tests_state.
4. PortableContextService includes compact test_evidence section.
5. pytest does NOT run automatically during startup / UI init.
6. load_latest_test_evidence returns None for stale evidence.
7. platform_pending P0.29 JSON validates.
"""
from __future__ import annotations

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from iabv_v15.infra.mcp.audit_tools import (
    _persist_test_evidence,
    load_latest_test_evidence,
    run_pytest,
)


# ── helpers ──────────────────────────────────────────────────────────────

def _fake_subprocess_runner(
    *,
    passed: int = 5,
    failed: int = 0,
    errors: int = 0,
    returncode: int = 0,
    duration: float = 1.5,
):
    """Return a SubprocessRunner that fakes a pytest summary line."""
    summary = f"{passed} passed"
    if failed:
        summary += f", {failed} failed"
    if errors:
        summary += f", {errors} errors"
    summary += f" in {duration}s"

    def runner(*, cmd, cwd, env, timeout_s):
        return SimpleNamespace(
            returncode=returncode,
            stdout=summary,
            stderr="",
            duration_s=duration,
            timed_out=False,
        )
    return runner


def _write_fresh_evidence(tmpdir: str, *, passed: int = 10, failed: int = 0, errors: int = 0) -> Path:
    """Write a fresh TestEvidence JSON to the expected path."""
    evidence_dir = Path(tmpdir) / "data" / "evolution" / "test_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "evidence_id": "test-eid-001",
        "command": "python -m pytest tests/ -q",
        "suite": "tests/",
        "keyword": "",
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "duration_s": 2.5,
        "returncode": 0 if failed == 0 and errors == 0 else 1,
        "timed_out": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "linked_pending_task": "p029",
        "changed_files": ["models.py"],
        "metadata": {},
    }
    latest = evidence_dir / "latest.json"
    latest.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return latest


# ── Test 1: run_pytest persists evidence when persist_evidence=True ──────

def test_run_pytest_persists_evidence_when_requested() -> None:
    """run_pytest(persist_evidence=True) must write latest.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = _fake_subprocess_runner(passed=8, failed=1)
        # Create a minimal src dir so run_pytest doesn't fail on path checks
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        result = run_pytest(
            tmpdir,
            runner=runner,
            persist_evidence=True,
            linked_pending_task="p029_test",
            changed_files=["file_a.py", "file_b.py"],
        )

        assert result["passed"] == 8
        assert result["failed"] == 1

        evidence_path = Path(tmpdir) / "data" / "evolution" / "test_evidence" / "latest.json"
        assert evidence_path.exists(), "latest.json must exist after persist_evidence=True"

        data = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert data["passed"] == 8
        assert data["failed"] == 1
        assert data["linked_pending_task"] == "p029_test"
        assert "file_a.py" in data["changed_files"]
        assert data["timestamp"]  # must be non-empty


def test_run_pytest_does_not_persist_without_flag() -> None:
    """run_pytest() without persist_evidence must NOT write latest.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = _fake_subprocess_runner(passed=3)
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        run_pytest(tmpdir, runner=runner)

        evidence_path = Path(tmpdir) / "data" / "evolution" / "test_evidence" / "latest.json"
        assert not evidence_path.exists(), "latest.json must NOT exist without persist_evidence"


# ── Test 2: SelfAuditService reports tests_observed=true ─────────────────

def test_self_audit_tests_observed_true_with_evidence() -> None:
    """SelfAuditService._build_cross_source_truth() must set
    tests_observed=true when fresh TestEvidence exists."""
    from iabv_v15.services.evolution.self_audit_service import SelfAuditService

    with tempfile.TemporaryDirectory() as tmpdir:
        _write_fresh_evidence(tmpdir, passed=10, failed=0)

        # _storage_root should be data/evolution/self_audit (3 levels below workspace)
        storage_root = Path(tmpdir) / "data" / "evolution" / "self_audit"
        storage_root.mkdir(parents=True, exist_ok=True)

        import types
        svc = SimpleNamespace(_storage_root=storage_root)
        svc._load_latest_test_evidence = types.MethodType(
            SelfAuditService._load_latest_test_evidence, svc,
        )
        result = SelfAuditService._build_cross_source_truth(
            svc,
            environment=None,
            world_model=None,
            pending_issues=[],
            world_model_digest={},
        )

        assert result["tests_observed"] is True
        assert "test_evidence_summary" in result
        summary = result["test_evidence_summary"]
        assert summary["passed"] == 10
        assert summary["failed"] == 0
        assert summary["errors"] == 0


def test_self_audit_tests_observed_false_without_evidence() -> None:
    """SelfAuditService._build_cross_source_truth() must set
    tests_observed=false when no TestEvidence exists."""
    from iabv_v15.services.evolution.self_audit_service import SelfAuditService

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_root = Path(tmpdir) / "data" / "evolution" / "self_audit"
        storage_root.mkdir(parents=True, exist_ok=True)

        import types
        svc = SimpleNamespace(_storage_root=storage_root)
        svc._load_latest_test_evidence = types.MethodType(
            SelfAuditService._load_latest_test_evidence, svc,
        )
        result = SelfAuditService._build_cross_source_truth(
            svc,
            environment=None,
            world_model=None,
            pending_issues=[],
            world_model_digest={},
        )

        assert result["tests_observed"] is False
        assert "test_evidence_summary" not in result


# ── Test 3: ControlMaster markdown renders test state ─────────────────────

def test_control_master_markdown_renders_tests_state() -> None:
    """render_state_markdown() must include current_tests_state when
    populated."""
    from iabv_v15.infra.persistence.control_master_repository import (
        render_state_markdown,
    )
    from iabv_v15.domain.models import ControlMasterState

    state = ControlMasterState(
        current_tests_state={
            "health": "green",
            "passed": 10,
            "failed": 0,
            "errors": 0,
            "suite": "tests/",
            "timestamp": "2026-05-16T12:00:00+00:00",
        },
    )
    md = render_state_markdown(state)
    # The markdown renders current_tests_state as key-value pairs
    assert "passed" in md or "10" in md
    assert "health" in md or "green" in md


# ── Test 4: PortableContext includes compact test_evidence section ────────

def test_portable_context_includes_test_evidence_section() -> None:
    """PortableContextService._test_evidence_section() must produce a
    section with test counts and no logs/PII."""
    from iabv_v15.services.evolution.portable_context_service import (
        PortableContextService,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _write_fresh_evidence(tmpdir, passed=7, failed=2, errors=1)

        import types
        svc = SimpleNamespace(workspace_root=tmpdir)
        svc._section = types.MethodType(PortableContextService._section, svc)
        svc._load_test_evidence = types.MethodType(
            PortableContextService._load_test_evidence, svc,
        )
        section = PortableContextService._test_evidence_section(
            svc, now=datetime.now(timezone.utc),
        )

        assert section.section_id == "test_evidence"
        assert "7" in section.summary  # passed count
        assert "2" in section.summary  # failed count
        # Must not contain logs or PII
        items_str = json.dumps(section.items)
        assert "output_tail" not in items_str
        assert "stderr" not in items_str


def test_portable_context_no_evidence_returns_unresolved() -> None:
    """Without evidence, the section must flag UNRESOLVED."""
    from iabv_v15.services.evolution.portable_context_service import (
        PortableContextService,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        import types
        svc = SimpleNamespace(workspace_root=tmpdir)
        svc._section = types.MethodType(PortableContextService._section, svc)
        svc._load_test_evidence = types.MethodType(
            PortableContextService._load_test_evidence, svc,
        )
        section = PortableContextService._test_evidence_section(
            svc, now=datetime.now(timezone.utc),
        )

        assert section.section_id == "test_evidence"
        assert "no_recent_evidence" in section.summary or section.confidence == 0.0
        assert any("UNRESOLVED" in u for u in section.unresolved_fields)


# ── Test 5: pytest does NOT auto-run during startup ───────────────────────

def test_no_pytest_auto_run_during_startup() -> None:
    """Importing core services and models must NOT trigger pytest execution.
    This ensures startup/UI init does not auto-run the test suite."""
    import subprocess
    import sys

    code = (
        "import iabv_v15.domain.models; "
        "import iabv_v15.infra.mcp.audit_tools; "
        "print('OK')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "PYTHONPATH": str(
                Path(__file__).resolve().parent.parent / "src"
            ),
            "PATH": "/usr/bin:/bin",
        },
    )
    assert "OK" in result.stdout
    assert result.returncode == 0


# ── Test 6: stale evidence returns None ───────────────────────────────────

def test_stale_evidence_returns_none() -> None:
    """load_latest_test_evidence must return None for evidence older than
    max_age_s."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evidence_dir = Path(tmpdir) / "data" / "evolution" / "test_evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        old_ts = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        evidence = {
            "evidence_id": "old-001",
            "passed": 5,
            "failed": 0,
            "errors": 0,
            "timestamp": old_ts,
        }
        (evidence_dir / "latest.json").write_text(
            json.dumps(evidence), encoding="utf-8",
        )

        result = load_latest_test_evidence(tmpdir)
        assert result is None, "Stale evidence must return None"


def test_fresh_evidence_loads_correctly() -> None:
    """load_latest_test_evidence must return data for fresh evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_fresh_evidence(tmpdir, passed=12, failed=0)

        result = load_latest_test_evidence(tmpdir)
        assert result is not None
        assert result["passed"] == 12


# ── Test 7: platform_pending P0.29 JSON validates ────────────────────────

def test_platform_pending_p029_json_validates() -> None:
    """Platform pending JSON must validate with PlatformPendingTask."""
    from iabv_v15.domain.models import PlatformPendingTask

    json_path = (
        Path(__file__).resolve().parent.parent
        / "data" / "evolution" / "platform_pending"
        / "task_metacognition_test_governance_p029.json"
    )
    assert json_path.exists(), f"Missing {json_path}"
    raw = json_path.read_text(encoding="utf-8")
    task = PlatformPendingTask.model_validate_json(raw)
    assert task.id == "metacognition_test_governance_p029"
    assert "P0.29" in task.title


# ── Test 8: TestEvidence model validates ──────────────────────────────────

def test_test_evidence_model_validates() -> None:
    """TestEvidence model must accept valid data and enforce defaults."""
    from iabv_v15.domain.models import TestEvidence

    ev = TestEvidence(
        command="python -m pytest tests/ -q",
        suite="tests/",
        passed=10,
        failed=1,
        errors=0,
        duration_s=3.5,
    )
    assert ev.passed == 10
    assert ev.failed == 1
    assert ev.evidence_id  # auto-generated
    assert ev.timestamp  # auto-generated
    assert ev.changed_files == []
    assert ev.linked_pending_task == ""
