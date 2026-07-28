"""
Test devin_session_gate integration with runtime_knowledge_snapshot (P0.161, P0.162b)

Hardened tests to verify:
- Runtime knowledge snapshot is exposed read-only in devin_session_gate
- The integration executes build_pre_snapshot() and render_pre_markdown() for real
- The snapshot data appears correctly in the gate output
- The read-only semantics are clear: try_runtime_knowledge_snapshot() is read-only,
  but run_pre() writes gate snapshots (accepted behavior)
"""

import json
from pathlib import Path
import pytest
import sys


def test_runtime_knowledge_snapshot_integration_real():
    """Test that devin_session_gate can import and use runtime_knowledge_snapshot."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
            export_compact_runtime_dossier,
        )

        dossier = export_compact_runtime_dossier(root)

        assert isinstance(dossier, dict)
        assert "timestamp" in dossier
        assert "total_organs" in dossier
        assert "active_organs" in dossier
        assert "evidence_sources" in dossier
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_build_pre_snapshot_includes_runtime_knowledge():
    """Test that build_pre_snapshot() actually includes runtime_knowledge."""
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "devin_session_gate.py"

    assert script_path.exists(), "devin_session_gate.py should exist"

    sys.path.insert(0, str(root / "scripts"))
    try:
        import devin_session_gate as gate

        snapshot = gate.build_pre_snapshot(root, "devin")

        assert isinstance(snapshot, dict)
        assert "runtime_knowledge" in snapshot
        assert isinstance(snapshot["runtime_knowledge"], dict)

        rk = snapshot["runtime_knowledge"]
        assert "available" in rk

        if rk["available"]:
            assert "dossier" in rk
            dossier = rk["dossier"]
            assert isinstance(dossier, dict)
            assert "total_organs" in dossier
            assert "active_organs" in dossier
            assert "heavy_active_organs" in dossier
            assert "degraded_organs" in dossier
            assert "evidence_sources" in dossier
    finally:
        try:
            sys.path.remove(str(root / "scripts"))
        except ValueError:
            pass


def test_render_pre_markdown_shows_runtime_knowledge():
    """Test that render_pre_markdown() shows the Runtime Knowledge section."""
    root = Path(__file__).resolve().parents[1]

    sys.path.insert(0, str(root / "scripts"))
    try:
        import devin_session_gate as gate

        snapshot = gate.build_pre_snapshot(root, "devin")
        markdown = gate.render_pre_markdown(snapshot)

        assert isinstance(markdown, str)
        assert "## Runtime Knowledge" in markdown

        if snapshot["runtime_knowledge"].get("available"):
            dossier = snapshot["runtime_knowledge"]["dossier"]
            assert "total_organs" in markdown
            assert "active_organs" in markdown
            assert "heavy_active_organs" in markdown
            assert "degraded_organs" in markdown
            assert "evidence_sources" in markdown
    finally:
        try:
            sys.path.remove(str(root / "scripts"))
        except ValueError:
            pass


def test_try_runtime_knowledge_snapshot_is_read_only():
    """Test that try_runtime_knowledge_snapshot() is read-only."""
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "devin_session_gate.py"

    script_content = script_path.read_text(encoding="utf-8")

    # The try_runtime_knowledge_snapshot function should not have write operations
    lines = script_content.splitlines()
    in_function = False
    function_lines = []

    for line in lines:
        if "def try_runtime_knowledge_snapshot" in line:
            in_function = True
        elif in_function:
            if line and not line.startswith(" ") and not line.startswith("\t"):
                break
            function_lines.append(line)

    function_code = "\n".join(function_lines)

    assert ".write(" not in function_code.lower()
    assert ".save(" not in function_code.lower()
    assert "commit" not in function_code.lower()

    # It should import the read-only function
    assert "export_compact_runtime_dossier" in function_code


def test_gate_run_pre_writes_own_snapshots():
    """Test that run_pre() writes gate snapshots (accepted behavior)."""
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "devin_session_gate.py"

    script_content = script_path.read_text(encoding="utf-8")

    # run_pre() is expected to write snapshots - this is gate's own behavior
    assert "def run_pre" in script_content
    assert "write_json" in script_content
    assert "write_text" in script_content

    # This is acceptable - the gate writes its own operational snapshots
    # The runtime_knowledge integration itself remains read-only
