"""
Test Organism State Snapshot - Unified Read-Only View (P0.165)

Tests to verify:
- The snapshot is read-only and does not introduce write operations
- The snapshot reuses existing services without duplication
- The snapshot provides a unified view of the organism
- Evidence sources are tracked for traceability
"""

import json
from pathlib import Path
import pytest


def test_organism_state_snapshot_is_read_only():
    """Test that organism_state_snapshot is read-only."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script_path = root / "src" / "iabv_v15" / "services" / "evolution" / "organism_state_snapshot.py"

    script_content = script_path.read_text(encoding="utf-8")

    # The snapshot should not have write operations
    assert ".write(" not in script_content.lower()
    assert ".save(" not in script_content.lower()
    assert "commit" not in script_content.lower()
    assert "repository.save" not in script_content.lower()
    assert "repository.upsert" not in script_content.lower()

    # It should import read-only functions
    assert "export_runtime_knowledge_snapshot" in script_content


def test_organism_state_snapshot_structure():
    """Test that the snapshot has the expected structure."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)

        assert isinstance(snapshot, dict)
        assert "timestamp" in snapshot
        assert "workspace_root" in snapshot
        assert "runtime_knowledge" in snapshot
        assert "self_examination" in snapshot
        assert "world_model" in snapshot
        assert "control_master" in snapshot
        assert "operational_learning" in snapshot
        assert "evidence_sources" in snapshot
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_organism_state_snapshot_reuses_existing_services():
    """Test that the snapshot reuses existing services."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script_path = root / "src" / "iabv_v15" / "services" / "evolution" / "organism_state_snapshot.py"

    script_content = script_path.read_text(encoding="utf-8")

    # Should import existing services, not create new ones
    assert "runtime_knowledge_snapshot" in script_content
    # Services should only appear as parameter types in docstrings, not as imports
    lines = script_content.splitlines()
    import_lines = [l for l in lines if l.strip().startswith("import") or l.strip().startswith("from")]
    for line in import_lines:
        assert "PortableContextService" not in line
        assert "OperationalSelfExaminationService" not in line
        assert "WorldModelService" not in line
        assert "ControlMasterService" not in line
        assert "ExperimentLab" not in line


def test_organism_state_snapshot_tracks_evidence_sources():
    """Test that evidence sources are tracked."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)

        assert "evidence_sources" in snapshot
        assert isinstance(snapshot["evidence_sources"], list)
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_organism_state_markdown_render():
    """Test that the snapshot can be rendered as markdown."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
            render_organism_state_markdown,
        )

        snapshot = export_organism_state_snapshot(root)
        markdown = render_organism_state_markdown(snapshot)

        assert isinstance(markdown, str)
        assert "# IABV Organism State Snapshot" in markdown
        assert "## Runtime Knowledge" in markdown
        assert "## Self Examination" in markdown
        assert "## World Model" in markdown
        assert "## Control Master" in markdown
        assert "## Operational Learning" in markdown
        assert "## Evidence Sources" in markdown
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_organism_state_snapshot_no_duplicate_authority():
    """Test that the snapshot does not introduce duplicate authority."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script_path = root / "src" / "iabv_v15" / "services" / "evolution" / "organism_state_snapshot.py"

    script_content = script_path.read_text(encoding="utf-8")

    # Should not have decision-making logic (excluding docstrings)
    lines = script_content.splitlines()
    code_lines = [l for l in lines if not l.strip().startswith('"""') and not l.strip().startswith("#")]
    code_text = "\n".join(code_lines)
    assert "decide" not in code_text.lower()
    assert "route" not in code_text.lower()
    assert "orchestrate" not in code_text.lower()
    assert "select" not in code_text.lower()

    # Should not have memory/storage operations (excluding docstrings)
    assert "memory_delta" not in code_text.lower()  # This is from runtime_organ_state, ok
    assert "storage" not in code_text.lower()
    assert "repository.save" not in code_text.lower()
    assert "repository.upsert" not in code_text.lower()

    # Should be clearly documented as read-only
    assert "read-only" in script_content.lower()
    assert "observability" in script_content.lower()


def test_organism_state_snapshot_fallback_behavior():
    """Test that the snapshot falls back to file reading when services are not provided."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        # Call without services - should use file fallbacks
        snapshot = export_organism_state_snapshot(root)

        # Should still return a valid structure
        assert isinstance(snapshot, dict)
        assert "runtime_knowledge" in snapshot
        assert "self_examination" in snapshot
        assert "world_model" in snapshot
        assert "control_master" in snapshot
        assert "operational_learning" in snapshot

        # Each section should have a status (runtime_knowledge has nested status)
        assert "status" in snapshot["self_examination"]
        assert "status" in snapshot["world_model"]
        assert "status" in snapshot["control_master"]
        assert "status" in snapshot["operational_learning"]
        # runtime_knowledge has nested status fields
        assert "runtime_organ_state" in snapshot["runtime_knowledge"]
        assert "portable_context_summary" in snapshot["runtime_knowledge"]
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass
