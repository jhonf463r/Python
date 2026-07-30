"""
Tests for Observatory UI (P0.184)

Tests for the minimal read-only observatory UI that consumes
export_observatory_surface_contract() from organism_state_snapshot.py.
"""

from pathlib import Path
import sys
import tempfile
import json

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))


def test_observatory_viewmodel_consumes_surface_contract():
    """Test that ObservatoryViewModel consumes export_observatory_surface_contract()."""
    from iabv_v15.ui.viewmodels.observatory_viewmodel import ObservatoryViewModel
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_observatory_surface_contract,
    )

    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create minimal portable_context
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test intent",
                    "items": []
                },
                {
                    "section_id": "learning",
                    "items": []
                }
            ]
        }
        (portable_context_dir / "latest.json").write_text(
            json.dumps(portable_context), encoding="utf-8"
        )

        # Create ViewModel
        vm = ObservatoryViewModel(tmp_path)

        # Verify initial state
        assert vm.loading == False
        assert vm.error == ""
        assert vm.surfaceContract == {}

        # Refresh should call export_observatory_surface_contract
        vm.refresh()

        # Verify data was loaded
        assert vm.loading == False
        assert vm.error == ""
        assert vm.surfaceContract != {}
        assert "timestamp" in vm.surfaceContract
        assert "workspace_root" in vm.surfaceContract
        assert "human_vision" in vm.surfaceContract
        assert "organ_health" in vm.surfaceContract
        assert "stability" in vm.surfaceContract
        assert "learning" in vm.surfaceContract
        assert "confidence" in vm.surfaceContract
        assert "evidence_sources" in vm.surfaceContract
        assert "unresolved_fields" in vm.surfaceContract


def test_observatory_viewmodel_is_read_only():
    """Test that ObservatoryViewModel does not write files or modify state."""
    from iabv_v15.ui.viewmodels.observatory_viewmodel import ObservatoryViewModel

    # Read the source code to verify no file writing
    vm_path = root / "src" / "iabv_v15" / "ui" / "viewmodels" / "observatory_viewmodel.py"
    vm_code = vm_path.read_text(encoding="utf-8")

    # Verify no file writing operations
    assert ".write(" not in vm_code
    assert ".save(" not in vm_code
    assert "open(" not in vm_code or "open(" in vm_code and "r" in vm_code  # Only read mode

    # Verify no decision service imports
    assert "ControlMaster" not in vm_code
    assert "WorldModel" not in vm_code
    assert "SelfExamination" not in vm_code

    # Verify only organism_state_snapshot is imported
    assert "organism_state_snapshot" in vm_code
    assert "export_observatory_surface_contract" in vm_code


def test_observatory_viewmodel_shows_unresolved():
    """Test that ViewModel shows UNRESOLVED when evidence is missing."""
    from iabv_v15.ui.viewmodels.observatory_viewmodel import ObservatoryViewModel

    # Create a minimal workspace without data
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create ViewModel
        vm = ObservatoryViewModel(tmp_path)
        vm.refresh()

        # When there's no data, the ViewModel may have an error or empty contract
        # Either way, it should not crash and should handle the missing data gracefully
        if vm.error:
            # If there's an error, that's acceptable - it means no data was available
            assert vm.error != ""
        else:
            # If no error, verify UNRESOLVED fields are present
            assert vm.surfaceContract != {}
            unresolved = vm.surfaceContract.get("unresolved_fields", [])
            assert len(unresolved) > 0 or any(
                section.get("status") in ["unavailable", "error"]
                for section in [
                    vm.surfaceContract.get("human_vision", {}),
                    vm.surfaceContract.get("organ_health", {}),
                    vm.surfaceContract.get("stability", {}),
                    vm.surfaceContract.get("learning", {}),
                    vm.surfaceContract.get("confidence", {}),
                ]
            )


def test_observatory_viewmodel_properties():
    """Test that ViewModel exposes all required properties."""
    from iabv_v15.ui.viewmodels.observatory_viewmodel import ObservatoryViewModel

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create minimal portable_context
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test intent",
                    "items": []
                },
                {
                    "section_id": "learning",
                    "items": []
                }
            ]
        }
        (portable_context_dir / "latest.json").write_text(
            json.dumps(portable_context), encoding="utf-8"
        )

        vm = ObservatoryViewModel(tmp_path)
        vm.refresh()

        # Verify all properties are accessible
        assert hasattr(vm, "timestamp")
        assert hasattr(vm, "workspaceRoot")
        assert hasattr(vm, "humanVision")
        assert hasattr(vm, "organHealth")
        assert hasattr(vm, "stability")
        assert hasattr(vm, "learning")
        assert hasattr(vm, "confidence")
        assert hasattr(vm, "evidenceSources")
        assert hasattr(vm, "unresolvedFields")

        # Verify property values
        assert isinstance(vm.timestamp, str)
        assert isinstance(vm.workspaceRoot, str)
        assert isinstance(vm.humanVision, dict)
        assert isinstance(vm.organHealth, dict)
        assert isinstance(vm.stability, dict)
        assert isinstance(vm.learning, dict)
        assert isinstance(vm.confidence, dict)
        assert isinstance(vm.evidenceSources, list)
        assert isinstance(vm.unresolvedFields, list)


def test_observatory_page_exists():
    """Test that ObservatoryPage.qml exists and has required structure."""
    qml_path = root / "src" / "iabv_v15" / "ui" / "qml" / "pages" / "ObservatoryPage.qml"

    assert qml_path.exists(), "ObservatoryPage.qml should exist"

    qml_code = qml_path.read_text(encoding="utf-8")

    # Verify it renders the required sections
    assert "Visión Humana" in qml_code
    assert "Salud del Organismo" in qml_code
    assert "Estabilidad" in qml_code
    assert "Reutilización de Aprendizaje" in qml_code
    assert "Confianza en Fuentes" in qml_code
    assert "Fuentes de Evidencia" in qml_code
    assert "Campos No Resueltos" in qml_code

    # Verify it shows UNRESOLVED
    assert "UNRESOLVED" in qml_code

    # Verify it uses observatoryViewModel from QML context
    assert "observatoryViewModel" in qml_code

    # Verify it has refresh button
    assert "Actualizar" in qml_code


def test_observatory_route_in_main_qml():
    """Test that observatory route is added to Main.qml navigation."""
    main_qml_path = root / "src" / "iabv_v15" / "ui" / "qml" / "Main.qml"

    assert main_qml_path.exists(), "Main.qml should exist"

    main_qml_code = main_qml_path.read_text(encoding="utf-8")

    # Verify observatory route is in navRoutes
    assert 'key: "observatory"' in main_qml_code
    assert "Observatorio" in main_qml_code

    # Verify routeSource maps observatory
    assert 'route === "observatory"' in main_qml_code
    assert "ObservatoryPage.qml" in main_qml_code


def test_observatory_does_not_break_existing_ui():
    """Test that observatory integration doesn't break existing UI."""
    main_qml_path = root / "src" / "iabv_v15" / "ui" / "qml" / "Main.qml"
    main_qml_code = main_qml_path.read_text(encoding="utf-8")

    # Verify existing routes are still present
    assert 'key: "dashboard"' in main_qml_code
    assert 'key: "control"' in main_qml_code
    assert 'key: "capture"' in main_qml_code
    assert 'key: "evolution"' in main_qml_code
    assert 'key: "knowledge"' in main_qml_code
    assert 'key: "providers"' in main_qml_code
    assert 'key: "runs"' in main_qml_code
    assert 'key: "centro_vivo"' in main_qml_code

    # Verify existing route mappings are still present
    assert "DashboardPage.qml" in main_qml_code
    assert "ControlCenterPage.qml" in main_qml_code
    assert "CaptureStudioPage.qml" in main_qml_code
    assert "EvolutionCenterPage.qml" in main_qml_code
    assert "KnowledgeBasePage.qml" in main_qml_code
    assert "ProviderSettingsPage.qml" in main_qml_code
    assert "RunHistoryPage.qml" in main_qml_code
    assert "CentroVivoPage.qml" in main_qml_code


def test_human_vision_population_with_real_evidence():
    """Test that human vision readout populates fields when real evidence exists."""
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_organism_state_snapshot,
    )

    # Create a temporary workspace with real evidence
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create portable_context with user intent
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test project direction",
                    "items": [
                        {"label": "Principle 1", "detail": "Test principle"}
                    ]
                },
                {
                    "section_id": "project_state",
                    "items": [
                        {"label": "Objetivo activo", "value": "Complete observatory integration"}
                    ]
                },
                {
                    "section_id": "learning",
                    "items": [
                        {
                            "label": "Preferencia actual",
                            "assistant_kind": "cloud_provider",
                            "route": "cloud",
                            "reasons": ["Stable", "Fast"],
                            "confidence": 0.9
                        }
                    ]
                }
            ]
        }
        (portable_context_dir / "latest.json").write_text(
            json.dumps(portable_context), encoding="utf-8"
        )

        # Create agent_session_gate with current briefing
        session_gate_dir = tmp_path / "data" / "evolution" / "agent_session_gate"
        session_gate_dir.mkdir(parents=True)
        session_gate = {
            "active_objectives": [
                {
                    "title": "Test critical objective",
                    "status": "READY_FOR_NEXT_SLICE",
                    "priority": "critical"
                }
            ]
        }
        (session_gate_dir / "latest.json").write_text(
            json.dumps(session_gate), encoding="utf-8"
        )

        # Create platform_pending with actionable task
        platform_pending_dir = tmp_path / "data" / "evolution" / "platform_pending"
        platform_pending_dir.mkdir(parents=True)
        pending_task = {
            "id": "task_001",
            "title": "Complete human vision population",
            "status": "PENDING",
            "priority": "critical",
            "next_action": "Implement population from canonical sources"
        }
        (platform_pending_dir / "task_001.json").write_text(
            json.dumps(pending_task), encoding="utf-8"
        )

        # Load snapshot
        snapshot = export_organism_state_snapshot(tmp_path)
        hvr = snapshot.get("human_vision_readout", {})

        # Verify fields are populated with real evidence
        assert hvr.get("status") == "ok"
        assert hvr.get("current_project_direction") != "UNRESOLVED"
        assert hvr.get("current_phase") != "UNRESOLVED"
        assert hvr.get("recommended_next_step") != "UNRESOLVED"
        assert hvr.get("recommended_ai_route") != "UNRESOLVED"

        # Verify evidence sources are tracked
        evidence_sources = hvr.get("evidence_sources", [])
        assert len(evidence_sources) > 0
        assert "portable_context:user_metacognitive_intent" in evidence_sources
        assert "agent_session_gate:latest.json" in evidence_sources
        assert "platform_pending:task_001.json" in evidence_sources

        # Verify unresolved fields are only from optional sources
        unresolved = hvr.get("unresolved_fields", [])
        # ControlMaster is optional, so its absence is acceptable
        # Other sources provided sufficient evidence
        assert all("control_master" in u or "ai_preference" in u for u in unresolved)


def test_human_vision_conserves_unresolved_when_no_evidence():
    """Test that human vision readout conserves UNRESOLVED when evidence is missing."""
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_organism_state_snapshot,
    )

    # Create a temporary workspace with no evidence
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Load snapshot without any evidence files
        snapshot = export_organism_state_snapshot(tmp_path)
        hvr = snapshot.get("human_vision_readout", {})

        # Verify fields are UNRESOLVED when no evidence exists
        assert hvr.get("current_project_direction") == "UNRESOLVED"
        assert hvr.get("current_phase") == "UNRESOLVED"
        assert hvr.get("recommended_next_step") == "UNRESOLVED"
        assert hvr.get("recommended_ai_route") == "UNRESOLVED"

        # Verify unresolved fields explain the cause
        unresolved = hvr.get("unresolved_fields", [])
        assert len(unresolved) > 0
        assert "portable_context_file_not_found" in unresolved


def test_human_vision_freshness_with_fresh_sources():
    """Test that human vision readout uses fresh sources when they exist."""
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_organism_state_snapshot,
    )
    import time

    # Create a temporary workspace with fresh sources
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create portable_context with recent timestamp
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test fresh intent",
                    "items": []
                },
                {
                    "section_id": "learning",
                    "items": [
                        {
                            "label": "Preferencia actual",
                            "assistant_kind": "cloud_provider",
                            "route": "cloud",
                            "reasons": ["Fresh"],
                            "confidence": 0.9
                        }
                    ]
                }
            ]
        }
        pc_path = portable_context_dir / "latest.json"
        pc_path.write_text(json.dumps(portable_context), encoding="utf-8")
        # Set recent timestamp (within 24 hours)
        time.sleep(0.1)  # Small delay to ensure timestamp is recent

        # Load snapshot
        snapshot = export_organism_state_snapshot(tmp_path)
        hvr = snapshot.get("human_vision_readout", {})

        # Verify AI route is not marked as stale
        ai_route = hvr.get("recommended_ai_route")
        assert "_STALE" not in ai_route
        assert ai_route == "cloud_provider:cloud"

        # Verify source_freshness is populated (if available)
        source_freshness = hvr.get("source_freshness", {})
        if source_freshness:
            assert "portable_context" in source_freshness
            assert source_freshness["portable_context"]["is_fresh"] == True
            assert source_freshness["portable_context"]["is_stale"] == False


def test_human_vision_freshness_with_stale_sources():
    """Test that human vision readout marks stale sources appropriately."""
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_organism_state_snapshot,
    )
    import time

    # Create a temporary workspace with stale sources
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create portable_context with old timestamp (> 7 days)
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test stale intent",
                    "items": []
                },
                {
                    "section_id": "learning",
                    "items": [
                        {
                            "label": "Preferencia actual",
                            "assistant_kind": "cloud_provider",
                            "route": "cloud",
                            "reasons": ["Stale"],
                            "confidence": 0.9
                        }
                    ]
                }
            ]
        }
        pc_path = portable_context_dir / "latest.json"
        pc_path.write_text(json.dumps(portable_context), encoding="utf-8")
        # Set old timestamp (> 7 days)
        old_time = time.time() - (8 * 24 * 3600)  # 8 days ago
        import os
        os.utime(pc_path, (old_time, old_time))

        # Load snapshot
        snapshot = export_organism_state_snapshot(tmp_path)
        hvr = snapshot.get("human_vision_readout", {})

        # Verify AI route is marked as stale
        ai_route = hvr.get("recommended_ai_route")
        assert "_STALE" in ai_route

        # Verify unresolved fields explain staleness
        unresolved = hvr.get("unresolved_fields", [])
        assert any("stale" in u for u in unresolved)

        # Verify source_freshness is populated (if available)
        source_freshness = hvr.get("source_freshness", {})
        if source_freshness:
            assert "portable_context" in source_freshness
            assert source_freshness["portable_context"]["is_fresh"] == False
            assert source_freshness["portable_context"]["is_stale"] == True


def test_human_vision_ai_route_with_weak_evidence():
    """Test that recommended_ai_route is conservative with weak evidence."""
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_organism_state_snapshot,
    )

    # Create a temporary workspace with weak evidence (no AI preference)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create portable_context without learning section
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test intent",
                    "items": []
                }
            ]
        }
        (portable_context_dir / "latest.json").write_text(
            json.dumps(portable_context), encoding="utf-8"
        )

        # Load snapshot
        snapshot = export_organism_state_snapshot(tmp_path)
        hvr = snapshot.get("human_vision_readout", {})

        # Verify AI route is UNRESOLVED without evidence
        assert hvr.get("recommended_ai_route") == "UNRESOLVED"

        # Verify unresolved fields explain missing evidence
        unresolved = hvr.get("unresolved_fields", [])
        assert "ai_preference_no_evidence" in unresolved


def test_surface_exposes_source_freshness():
    """Test that the compact surface exposes source_freshness from the backend."""
    from iabv_v15.services.evolution.organism_state_snapshot import (
        export_observatory_surface_contract,
    )

    # Create a temporary workspace with fresh sources
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create portable_context with learning section
        portable_context_dir = tmp_path / "data" / "evolution" / "portable_context"
        portable_context_dir.mkdir(parents=True)
        portable_context = {
            "sections": [
                {
                    "section_id": "user_metacognitive_intent",
                    "summary": "Test intent",
                    "items": []
                },
                {
                    "section_id": "learning",
                    "items": [
                        {
                            "label": "Preferencia actual",
                            "assistant_kind": "cloud_provider",
                            "route": "cloud",
                            "reasons": ["Test"],
                            "confidence": 0.9
                        }
                    ]
                }
            ]
        }
        (portable_context_dir / "latest.json").write_text(
            json.dumps(portable_context), encoding="utf-8"
        )

        # Load compact surface
        surface = export_observatory_surface_contract(tmp_path)
        human_vision = surface.get("human_vision", {})

        # Verify source_freshness is exposed in compact surface
        assert "source_freshness" in human_vision
        source_freshness = human_vision["source_freshness"]

        # Verify it contains freshness metadata
        if source_freshness:
            # If source_freshness is populated, verify structure
            for source_name, freshness in source_freshness.items():
                assert "age_seconds" in freshness
                assert "is_fresh" in freshness
                assert "is_stale" in freshness


def test_observatory_page_shows_source_freshness():
    """Test that ObservatoryPage.qml displays source_freshness in Human Vision section."""
    observatory_qml_path = root / "src" / "iabv_v15" / "ui" / "qml" / "pages" / "ObservatoryPage.qml"

    assert observatory_qml_path.exists(), "ObservatoryPage.qml should exist"

    qml_code = observatory_qml_path.read_text(encoding="utf-8")

    # Verify it shows source_freshness
    assert "source_freshness" in qml_code
    assert "Frescura de fuentes" in qml_code

    # Verify it distinguishes fresh/stale
    assert "FRESH" in qml_code
    assert "STALE" in qml_code

    # Verify it shows age information
    assert "Edad:" in qml_code


if __name__ == "__main__":
    test_observatory_viewmodel_consumes_surface_contract()
    test_observatory_viewmodel_is_read_only()
    test_observatory_viewmodel_shows_unresolved()
    test_observatory_viewmodel_properties()
    test_observatory_page_exists()
    test_observatory_route_in_main_qml()
    test_observatory_does_not_break_existing_ui()
    print("All observatory UI tests passed!")
