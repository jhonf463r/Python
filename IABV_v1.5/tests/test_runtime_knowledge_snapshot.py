"""
Test Runtime Knowledge Layer Snapshot (P0.158)

Minimal tests to verify:
- Snapshot export exists and is read-only
- Reflects runtime state without modifying it
- No authority duplication
"""

import json
from pathlib import Path
import pytest


def test_runtime_knowledge_snapshot_exists():
    """Test that the snapshot export function exists and is importable."""
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_runtime_knowledge_snapshot,
        export_compact_runtime_dossier,
    )
    assert callable(export_runtime_knowledge_snapshot)
    assert callable(export_compact_runtime_dossier)


def test_runtime_knowledge_snapshot_is_read_only(workspace_root):
    """Test that snapshot export is read-only and does not modify state."""
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_runtime_knowledge_snapshot,
    )
    
    # Get initial state
    runtime_organs_path = Path(workspace_root) / "data" / "evolution" / "runtime_organs" / "latest.json"
    initial_mtime = None
    if runtime_organs_path.exists():
        initial_mtime = runtime_organs_path.stat().st_mtime
    
    # Export snapshot (should not modify anything)
    snapshot = export_runtime_knowledge_snapshot(workspace_root)
    
    # Verify file was not modified
    if runtime_organs_path.exists() and initial_mtime:
        current_mtime = runtime_organs_path.stat().st_mtime
        assert current_mtime == initial_mtime, "Snapshot export modified runtime state"
    
    # Verify snapshot structure
    assert "timestamp" in snapshot
    assert "workspace_root" in snapshot
    assert "runtime_organ_state" in snapshot
    assert "portable_context_summary" in snapshot
    assert "evidence_sources" in snapshot


def test_runtime_knowledge_snapshot_structure(workspace_root):
    """Test that snapshot has correct structure even when data is unavailable."""
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_runtime_knowledge_snapshot,
    )
    
    snapshot = export_runtime_knowledge_snapshot(workspace_root)
    
    # Verify top-level keys
    assert isinstance(snapshot, dict)
    assert "timestamp" in snapshot
    assert "runtime_organ_state" in snapshot
    assert "portable_context_summary" in snapshot
    assert "evidence_sources" in snapshot
    
    # Verify runtime_organ_state structure
    assert isinstance(snapshot["runtime_organ_state"], dict)
    assert "status" in snapshot["runtime_organ_state"]
    assert "organ_count" in snapshot["runtime_organ_state"]
    
    # Verify portable_context_summary structure
    assert isinstance(snapshot["portable_context_summary"], dict)
    assert "status" in snapshot["portable_context_summary"]


def test_compact_runtime_dossier(workspace_root):
    """Test that compact dossier provides minimal health indicators."""
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_compact_runtime_dossier,
    )
    
    dossier = export_compact_runtime_dossier(workspace_root)
    
    # Verify structure
    assert isinstance(dossier, dict)
    assert "timestamp" in dossier
    assert "total_organs" in dossier
    assert "active_organs" in dossier
    assert "heavy_active_organs" in dossier
    assert "organs_with_recent_work" in dossier
    assert "degraded_organs" in dossier
    assert "evidence_sources" in dossier
    
    # Verify types
    assert isinstance(dossier["total_organs"], int)
    assert isinstance(dossier["active_organs"], int)
    assert isinstance(dossier["heavy_active_organs"], int)
    assert isinstance(dossier["organs_with_recent_work"], int)
    assert isinstance(dossier["degraded_organs"], int)
    assert isinstance(dossier["evidence_sources"], list)


def test_no_authority_duplication():
    """Test that snapshot layer does not introduce decision authority.
    
    The snapshot layer should only export data, not make decisions
    or modify system behavior.
    """
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_runtime_knowledge_snapshot,
        export_compact_runtime_dossier,
    )
    
    # Verify functions are pure (no side effects)
    # They should not modify any global state
    # They should not call any decision-making services
    
    # Check that the module does not import decision-making services
    import iabv_v15.services.evolution.runtime_knowledge_snapshot as snapshot_module
    source = snapshot_module.__file__
    source_content = Path(source).read_text(encoding="utf-8")
    
    # Should not import decision-making services
    assert "strategy_selector" not in source_content.lower()
    assert "experiment_lab" not in source_content.lower()
    assert "autonomous_evolution" not in source_content.lower()
    
    # Should not have write operations
    assert ".write(" not in source_content
    assert ".save(" not in source_content
    assert "commit" not in source_content.lower()


@pytest.fixture
def workspace_root():
    """Provide workspace root for tests."""
    return Path(__file__).parent.parent.parent
