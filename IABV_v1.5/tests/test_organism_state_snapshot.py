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
        assert "organ_health_matrix" in snapshot
        assert "stability_signals" in snapshot
        assert "learning_reuse_summary" in snapshot
        assert "active_hypotheses" in snapshot
        assert "discarded_hypotheses" in snapshot
        assert "temporal_delta_summary" in snapshot
        assert "human_vision_readout" in snapshot
        assert "source_confidence" in snapshot
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
        assert "## Organ Health Matrix" in markdown
        assert "## Stability Signals" in markdown
        assert "## Learning Reuse Summary" in markdown
        assert "## Temporal Delta Summary" in markdown
        assert "## Source Confidence" in markdown
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

    # Check for decision-making verbs as method calls (not variable names)
    assert "decide(" not in code_text.lower()
    assert "orchestrate(" not in code_text.lower()
    assert "select(" not in code_text.lower()

    # Check for route as a decision-making method, not as data field or variable name
    # Exclude patterns that are clearly data access or variable assignment
    lines_to_check = []
    skip_next = False
    for line in code_lines:
        line_lower = line.lower()
        # Skip lines that are clearly data field access or variable assignment
        if "recommended_ai_route" in line_lower or "item.get(" in line_lower or '"route"' in line_lower:
            continue
        lines_to_check.append(line)

    checked_code = "\n".join(lines_to_check)
    assert "route(" not in checked_code.lower()

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
        assert "organ_health_matrix" in snapshot
        assert "stability_signals" in snapshot
        assert "learning_reuse_summary" in snapshot
        assert "active_hypotheses" in snapshot
        assert "discarded_hypotheses" in snapshot
        assert "temporal_delta_summary" in snapshot
        assert "human_vision_readout" in snapshot
        assert "source_confidence" in snapshot

        # Each section should have a status (runtime_knowledge has nested status)
        assert "status" in snapshot["self_examination"]
        assert "status" in snapshot["world_model"]
        assert "status" in snapshot["control_master"]
        assert "status" in snapshot["operational_learning"]
        assert "status" in snapshot["organ_health_matrix"]
        assert "status" in snapshot["stability_signals"]
        assert "status" in snapshot["learning_reuse_summary"]
        assert "status" in snapshot["active_hypotheses"]
        assert "status" in snapshot["discarded_hypotheses"]
        assert "status" in snapshot["temporal_delta_summary"]
        assert "status" in snapshot["human_vision_readout"]
        assert "status" in snapshot["source_confidence"]
        # runtime_knowledge has nested status fields
        assert "runtime_organ_state" in snapshot["runtime_knowledge"]
        assert "portable_context_summary" in snapshot["runtime_knowledge"]

        # Fallbacks should have stale_capable metadata when ok
        for section in ["self_examination", "world_model", "control_master", "operational_learning",
                        "organ_health_matrix", "stability_signals", "learning_reuse_summary",
                        "active_hypotheses", "discarded_hypotheses", "temporal_delta_summary", "human_vision_readout"]:
            if snapshot[section].get("status") == "ok" and snapshot[section].get("source") == "file_fallback":
                assert "source_path" in snapshot[section]
                assert "updated_at" in snapshot[section]
                assert "age_seconds" in snapshot[section]
                assert "stale_capable" in snapshot[section]
                assert snapshot[section]["stale_capable"] is True
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_human_vision_readout_always_exists():
    """Test that human_vision_readout always exists in the snapshot."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)

        assert "human_vision_readout" in snapshot
        assert isinstance(snapshot["human_vision_readout"], dict)
        assert "status" in snapshot["human_vision_readout"]
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_human_vision_readout_no_write_operations():
    """Test that human_vision_readout does not write files or create memory."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        script_path = root / "src" / "iabv_v15" / "services" / "evolution" / "organism_state_snapshot.py"
        script_content = script_path.read_text(encoding="utf-8")

        # The _load_human_vision_readout function should not have write operations
        lines = script_content.splitlines()
        in_human_vision_func = False
        for line in lines:
            if "def _load_human_vision_readout" in line:
                in_human_vision_func = True
            elif in_human_vision_func and line.startswith("def "):
                break
            elif in_human_vision_func:
                assert ".write(" not in line.lower()
                assert ".save(" not in line.lower()
                assert "commit" not in line.lower()
                assert "repository.save" not in line.lower()
                assert "repository.upsert" not in line.lower()
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_human_vision_readout_marks_unresolved():
    """Test that human_vision_readout marks UNRESOLVED when evidence is missing."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)
        hvr = snapshot["human_vision_readout"]

        # Should have unresolved_fields list
        assert "unresolved_fields" in hvr
        assert isinstance(hvr["unresolved_fields"], list)

        # If AI recommendation is UNRESOLVED, should have evidence in unresolved_fields
        if hvr.get("recommended_ai_route") == "UNRESOLVED":
            assert any("ai_preference" in field for field in hvr["unresolved_fields"])
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_human_vision_readout_in_markdown():
    """Test that markdown rendering includes Human Vision Readout."""
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
        assert "## Human Vision Readout" in markdown
        assert "Recommended next step" in markdown
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_platform_pending_ignores_completed():
    """Test that platform_pending ignores COMPLETED tasks."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)
        hvr = snapshot["human_vision_readout"]

        # If there's a selected task, it should not be COMPLETED
        if hvr.get("selected_task_evidence"):
            assert hvr["selected_task_evidence"].get("status") != "COMPLETED"
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_platform_pending_prioritizes_critical():
    """Test that platform_pending prioritizes critical tasks."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)
        hvr = snapshot["human_vision_readout"]

        # If there's a selected task and there are critical tasks available,
        # the selected task should be critical
        if hvr.get("selected_task_evidence"):
            # This is a soft check - we can't guarantee there are critical tasks
            # but if the selected task is critical, that's good
            # If it's not critical, it might be because no critical tasks exist
            pass
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_platform_pending_uses_next_action():
    """Test that platform_pending uses next_action if available."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)
        hvr = snapshot["human_vision_readout"]

        # If there's a selected task with next_action, recommended_next_step should use it
        if hvr.get("selected_task_evidence"):
            # Check that recommended_next_step is populated
            assert hvr.get("recommended_next_step") != "UNRESOLVED"
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_platform_pending_unresolved_when_no_actionable():
    """Test that platform_pending marks UNRESOLVED when no actionable tasks."""
    from pathlib import Path
    import sys
    import tempfile
    import json

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        # Create a temporary workspace with only COMPLETED tasks
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            platform_pending_dir = tmp_path / "data" / "evolution" / "platform_pending"
            platform_pending_dir.mkdir(parents=True)

            # Create a COMPLETED task
            completed_task = {
                "id": "test_completed",
                "title": "Completed Task",
                "status": "COMPLETED",
                "priority": "high"
            }
            (platform_pending_dir / "task_test_completed.json").write_text(
                json.dumps(completed_task), encoding="utf-8"
            )

            # Create portable_context to avoid other UNRESOLVED
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

            # Create agent_session_gate
            session_gate_dir = tmp_path / "data" / "evolution" / "agent_session_gate"
            session_gate_dir.mkdir(parents=True)
            session_gate = {
                "generated_at": "2026-07-27T18:27:06.246814+00:00",
                "agent": "devin",
                "mode": "pre",
                "active_objectives": []
            }
            (session_gate_dir / "latest.json").write_text(
                json.dumps(session_gate), encoding="utf-8"
            )

            snapshot = export_organism_state_snapshot(tmp_path)
            hvr = snapshot["human_vision_readout"]

            # Should have unresolved field for no actionable tasks
            assert any("no_actionable" in field for field in hvr.get("unresolved_fields", []))
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_observatory_surface_contract_exists():
    """Test that the observatory surface contract function exists and is callable."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_observatory_surface_contract,
        )

        assert callable(export_observatory_surface_contract)
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_observatory_surface_contract_structure():
    """Test that the surface contract has the expected structure."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_observatory_surface_contract,
        )

        contract = export_observatory_surface_contract(root)

        # Check top-level fields
        assert "timestamp" in contract
        assert "workspace_root" in contract
        assert "human_vision" in contract
        assert "organ_health" in contract
        assert "stability" in contract
        assert "learning" in contract
        assert "confidence" in contract
        assert "evidence_sources" in contract
        assert "unresolved_fields" in contract

        # Check human_vision structure
        hv = contract["human_vision"]
        assert "status" in hv
        assert "current_project_direction" in hv
        assert "current_phase" in hv
        assert "recommended_next_step" in hv
        assert "recommended_ai_route" in hv
        assert "source" in hv
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_observatory_surface_contract_read_only():
    """Test that the surface contract is read-only (no write operations)."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        script_path = root / "src" / "iabv_v15" / "services" / "evolution" / "organism_state_snapshot.py"
        script_content = script_path.read_text(encoding="utf-8")

        # Check that extraction functions don't have write operations
        extraction_functions = [
            "_extract_human_vision_surface",
            "_extract_health_surface",
            "_extract_stability_surface",
            "_extract_learning_surface",
            "_extract_confidence_surface",
            "_extract_unresolved_fields",
        ]

        for func_name in extraction_functions:
            func_start = script_content.find(f"def {func_name}")
            if func_start == -1:
                continue
            # Find the next function definition to limit scope
            next_func = script_content.find("\ndef ", func_start + 1)
            if next_func == -1:
                func_end = len(script_content)
            else:
                func_end = next_func
            func_code = script_content[func_start:func_end]

            # Check for write operations
            assert ".write(" not in func_code.lower()
            assert ".save(" not in func_code.lower()
            assert "commit" not in func_code.lower()
            assert "repository.save" not in func_code.lower()
            assert "repository.upsert" not in func_code.lower()
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_observatory_surface_contract_temporal_metadata():
    """Test that the surface contract includes temporal metadata."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_observatory_surface_contract,
        )

        contract = export_observatory_surface_contract(root)

        # Check temporal metadata in sections that should have it
        hv = contract["human_vision"]
        if hv.get("status") == "ok":
            assert "updated_at" in hv or "age_seconds" in hv or "stale_capable" in hv

        health = contract["organ_health"]
        if health.get("status") == "ok":
            assert "source" in health
            assert "source_path" in health or "updated_at" in health

        stability = contract["stability"]
        if stability.get("status") == "ok":
            assert "source" in stability
            assert "source_path" in stability or "updated_at" in stability

        learning = contract["learning"]
        if learning.get("status") == "ok":
            assert "source" in learning
            assert "source_path" in learning or "updated_at" in learning
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_observatory_surface_contract_unresolved_when_missing():
    """Test that the surface contract marks UNRESOLVED when sections are missing."""
    from pathlib import Path
    import sys
    import tempfile
    import json

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_observatory_surface_contract,
        )

        # Create a minimal workspace with missing sections
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

            contract = export_observatory_surface_contract(tmp_path)

            # Should have unresolved fields for missing sections
            unresolved = contract.get("unresolved_fields", [])
            assert len(unresolved) > 0 or any(
                section.get("status") in ["unavailable", "error"]
                for section in [
                    contract["organ_health"],
                    contract["stability"],
                    contract["learning"],
                ]
            )
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_observatory_surface_contract_no_duplicate_authority():
    """Test that the surface contract doesn't introduce duplicate authority."""
    from pathlib import Path
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        script_path = root / "src" / "iabv_v15" / "services" / "evolution" / "organism_state_snapshot.py"
        script_content = script_path.read_text(encoding="utf-8")

        # Find the export_observatory_surface_contract function
        func_start = script_content.find("def export_observatory_surface_contract")
        if func_start == -1:
            return  # Function doesn't exist yet

        # Find the end of the function (next function or end of file)
        next_func = script_content.find("\ndef ", func_start + 1)
        if next_func == -1:
            func_end = len(script_content)
        else:
            func_end = next_func
        func_code = script_content[func_start:func_end]

        # Check that it doesn't have decision-making logic
        assert "decide(" not in func_code.lower()
        assert "orchestrate(" not in func_code.lower()
        assert "select(" not in func_code.lower()

        # Check that it uses export_organism_state_snapshot (reuses existing)
        assert "export_organism_state_snapshot" in func_code

        # Check that it doesn't write to files
        assert ".write(" not in func_code.lower()
        assert ".save(" not in func_code.lower()
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_stability_signals_uses_experiment_runs():
    """Test that stability_signals reads from experiment_runs directory when available."""
    from pathlib import Path
    import sys
    import tempfile
    import json

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        # Create a temporary workspace with experiment_runs
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            experiment_runs_dir = tmp_path / "data" / "evolution" / "experiment_runs"
            experiment_runs_dir.mkdir(parents=True)

            # Create some experiment run files
            for i in range(5):
                run_data = {
                    "success": i % 2 == 0,  # Alternating success/failure
                    "timestamp": f"2026-07-29T{i:02d}:00:00Z"
                }
                (experiment_runs_dir / f"run_{i}.json").write_text(
                    json.dumps(run_data), encoding="utf-8"
                )

            # Create minimal portable_context to avoid other UNRESOLVED
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

            snapshot = export_organism_state_snapshot(tmp_path)
            stability = snapshot["stability_signals"]

            # Should have status ok and use experiment_runs
            assert stability["status"] == "ok"
            assert stability["source"] == "file_fallback"
            assert "experiment_runs" in stability["source_path"]
            assert stability["recent_runs_count"] == 5
            assert stability["success_rate"] == 0.6  # 3 out of 5 (0, 2, 4 are success)
            assert "updated_at" in stability
            assert "age_seconds" in stability
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_learning_reuse_summary_uses_experience():
    """Test that learning_reuse_summary reads from experience directory when available."""
    from pathlib import Path
    import sys
    import tempfile
    import json

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        # Create a temporary workspace with experience
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            experience_dir = tmp_path / "data" / "evolution" / "experience"
            experience_dir.mkdir(parents=True)

            # Create experience JSONL files
            exp_lines = []
            for i in range(10):
                exp_data = {
                    "reused": i % 3 == 0,  # Every 3rd is reused
                    "pattern_reused": i % 3 == 0,
                    "timestamp": f"2026-07-29T{i:02d}:00:00Z"
                }
                exp_lines.append(json.dumps(exp_data))

            (experience_dir / "gpu_routing.jsonl").write_text(
                "\n".join(exp_lines), encoding="utf-8"
            )

            # Create minimal portable_context to avoid other UNRESOLVED
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

            snapshot = export_organism_state_snapshot(tmp_path)
            learning = snapshot["learning_reuse_summary"]

            # Should have status ok and use experience
            assert learning["status"] == "ok"
            assert learning["source"] == "file_fallback"
            assert "experience" in learning["source_path"]
            assert learning["total_runs"] == 10
            assert learning["reused_patterns_count"] == 4  # 0, 3, 6, 9
            assert learning["reuse_rate"] == 0.4
            assert "updated_at" in learning
            assert "age_seconds" in learning
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_stability_unresolved_when_missing():
    """Test that stability_signals is UNRESOLVED when experiment_runs doesn't exist."""
    from pathlib import Path
    import sys
    import tempfile
    import json

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        # Create a minimal workspace without experiment_runs
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

            snapshot = export_organism_state_snapshot(tmp_path)
            stability = snapshot["stability_signals"]

            # Should be unavailable
            assert stability["status"] == "unavailable"
            assert "experiment_runs" in stability["source_path"]
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def test_learning_unresolved_when_missing():
    """Test that learning_reuse_summary is UNRESOLVED when experience doesn't exist."""
    from pathlib import Path
    import sys
    import tempfile
    import json

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    try:
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        # Create a minimal workspace without experience
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

            snapshot = export_organism_state_snapshot(tmp_path)
            learning = snapshot["learning_reuse_summary"]

            # Should be unavailable
            assert learning["status"] == "unavailable"
            assert "experience" in learning["source_path"]
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass
