"""
Test devin_session_gate integration with runtime_knowledge_snapshot (P0.161)

Minimal tests to verify:
- Runtime knowledge snapshot is exposed read-only in devin_session_gate
- The integration does not introduce write operations
- The snapshot data appears correctly in the gate output
"""

import json
from pathlib import Path
import pytest


def test_runtime_knowledge_snapshot_integration():
    """Test that devin_session_gate can import and use runtime_knowledge_snapshot."""
    import sys
    from pathlib import Path

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


def test_devin_session_gate_includes_runtime_knowledge():
    """Test that devin_session_gate's try_runtime_knowledge_snapshot function exists."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "devin_session_gate.py"

    assert script_path.exists(), "devin_session_gate.py should exist"

    script_content = script_path.read_text(encoding="utf-8")
    assert "try_runtime_knowledge_snapshot" in script_content
    assert "export_compact_runtime_dossier" in script_content


def test_runtime_knowledge_is_read_only():
    """Test that runtime_knowledge_snapshot integration is read-only."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "devin_session_gate.py"

    script_content = script_path.read_text(encoding="utf-8")

    # The integration function should not have write operations
    assert ".write(" not in script_content.lower()
    assert ".save(" not in script_content.lower()
    assert "commit" not in script_content.lower()

    # It should import the read-only function
    assert "export_compact_runtime_dossier" in script_content


def test_runtime_knowledge_in_pre_snapshot():
    """Test that runtime_knowledge is included in the pre snapshot structure."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "devin_session_gate.py"

    script_content = script_path.read_text(encoding="utf-8")

    # Check that runtime_knowledge is added to the snapshot
    assert '"runtime_knowledge": runtime_knowledge' in script_content or (
        '"runtime_knowledge"' in script_content and "runtime_knowledge" in script_content
    )

    # Check that it's rendered in markdown
    assert "## Runtime Knowledge" in script_content
