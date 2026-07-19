"""Minimal test for SystemIdentityRegistry integration.

This test validates that:
1. The registry can be instantiated
2. It scans the actual codebase
3. It returns coherent subsystem data
4. ControlCenterViewModel can consume the registry data
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from iabv_v15.services.system_identity_registry import (
    SystemIdentityRegistry,
    SubsystemStatus,
    ComponentCategory,
)


def test_registry_instantiation():
    """Test that SystemIdentityRegistry can be instantiated."""
    registry = SystemIdentityRegistry()
    assert registry is not None
    assert registry.workspace_root is not None
    print("✓ Registry instantiation works")


def test_registry_scan():
    """Test that registry scans the codebase and returns subsystems."""
    registry = SystemIdentityRegistry()
    snapshot = registry.current_snapshot(force_refresh=True)
    
    assert snapshot is not None
    assert snapshot.canonical_root is not None
    assert len(snapshot.canonical_root) > 0
    assert snapshot.total_subsystems > 0
    
    print(f"✓ Registry scanned {snapshot.total_subsystems} subsystems")
    print(f"  Canonical root: {snapshot.canonical_root}")
    print(f"  Global health: {snapshot.global_health}")


def test_registry_subsystem_evidence():
    """Test that subsystems have evidence based on actual files."""
    registry = SystemIdentityRegistry()
    snapshot = registry.current_snapshot(force_refresh=True)
    
    for name, subsystem in snapshot.subsystems.items():
        # Every subsystem must have a file path
        assert subsystem.file_path is not None
        assert len(subsystem.file_path) > 0
        
        # Every subsystem must have evidence
        assert subsystem.evidence is not None
        assert len(subsystem.evidence) > 0
        
        # File should exist
        file_path = Path(subsystem.file_path)
        if file_path.exists():
            # Evidence should mention file size
            assert "KB" in subsystem.evidence or "exists" in subsystem.evidence.lower()
        
        print(f"✓ {name}: {subsystem.status} ({subsystem.maturity_pct}%) - {subsystem.evidence[:50]}...")


def test_registry_classification():
    """Test that subsystem classification is coherent."""
    registry = SystemIdentityRegistry()
    snapshot = registry.current_snapshot(force_refresh=True)
    
    # Count by status
    status_counts = {}
    for subsystem in snapshot.subsystems.values():
        status = subsystem.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"✓ Classification summary:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # Verify that global health matches the classification
    if snapshot.partial_subsystems == 0:
        assert snapshot.global_health == "healthy"
    elif snapshot.partial_subsystems <= snapshot.live_subsystems * 0.3:
        assert snapshot.global_health == "mostly_healthy"
    else:
        assert snapshot.global_health == "degraded"
    
    print(f"✓ Global health ({snapshot.global_health}) matches classification")


def test_registry_ui_summary():
    """Test that get_summary_for_ui returns UI-consumable data."""
    registry = SystemIdentityRegistry()
    summary = registry.get_summary_for_ui()
    
    assert summary is not None
    assert "canonical_root" in summary
    assert "global_health" in summary
    assert "total_subsystems" in summary
    assert "live_subsystems" in summary
    assert "partial_subsystems" in summary
    assert "subsystems" in summary
    
    # Verify subsystems have UI-required fields
    for subsystem in summary["subsystems"]:
        assert "name" in subsystem
        assert "category" in subsystem
        assert "file_path" in subsystem
        assert "status" in subsystem
        assert "maturity_pct" in subsystem
        assert "evidence" in subsystem
    
    print(f"✓ UI summary is valid with {len(summary['subsystems'])} subsystems")


def test_registry_no_ghost_components():
    """Test that registry doesn't include non-existent components."""
    registry = SystemIdentityRegistry()
    snapshot = registry.current_snapshot(force_refresh=True)
    
    for name, subsystem in snapshot.subsystems.items():
        file_path = Path(subsystem.file_path)
        # If the file doesn't exist, it should be marked as DESCONECTADO or similar
        if not file_path.exists():
            assert subsystem.status in [
                SubsystemStatus.DESCONECTADO,
                SubsystemStatus.HISTORICO,
            ], f"{name} has non-existent file but status is {subsystem.status}"
    
    print("✓ No ghost components with non-existent files")


if __name__ == "__main__":
    print("Running SystemIdentityRegistry integration tests...\n")
    
    test_registry_instantiation()
    test_registry_scan()
    test_registry_subsystem_evidence()
    test_registry_classification()
    test_registry_ui_summary()
    test_registry_no_ghost_components()
    
    print("\n✅ All tests passed")
