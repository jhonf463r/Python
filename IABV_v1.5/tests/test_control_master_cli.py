"""Tests for the Control Master CLI (python -m iabv_v15 cm ...)."""
from __future__ import annotations

import io
import json
import shutil
import uuid
from pathlib import Path

import pytest

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.cli.control_master import main as cm_main


def _workspace(label: str) -> Path:
    root = Path("/tmp") / f"iabv_cm_cli_{label}_{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_export_digest_json_outputs_persisted_vision(capsys: pytest.CaptureFixture[str]) -> None:
    root = _workspace("export_json")
    try:
        boot = AppBootstrap(str(root))
        boot.control_master_service.set_vision("Vision persistida CLI")
        rc = cm_main(["--workspace", str(root), "export-digest", "--format", "json"])
        assert rc == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["current_vision"] == "Vision persistida CLI"
        assert "rules_brief" in payload
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_export_digest_markdown_contains_vision_heading(capsys: pytest.CaptureFixture[str]) -> None:
    root = _workspace("export_md")
    try:
        boot = AppBootstrap(str(root))
        boot.control_master_service.set_vision("Vision markdown")
        rc = cm_main(["--workspace", str(root), "export-digest", "--format", "markdown"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "# Control Maestro digest" in out
        assert "Vision markdown" in out
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_set_vision_persists_value(capsys: pytest.CaptureFixture[str]) -> None:
    root = _workspace("set_vision")
    try:
        rc = cm_main(["--workspace", str(root), "set-vision", "Nueva vision CLI"])
        assert rc == 0
        boot = AppBootstrap(str(root))
        state = boot.control_master_service.current_state(refresh=False)
        assert state.current_vision == "Nueva vision CLI"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_add_objective_and_mark_it_completed() -> None:
    root = _workspace("add_objective")
    try:
        rc = cm_main(
            [
                "--workspace",
                str(root),
                "add-objective",
                "--id",
                "obj-cli-demo",
                "--title",
                "Objetivo CLI demo",
                "--summary",
                "Creado por la CLI",
                "--status",
                "active",
                "--tag",
                "cli",
                "--tag",
                "demo",
            ]
        )
        assert rc == 0
        boot = AppBootstrap(str(root))
        node = boot.objective_repository.get("obj-cli-demo")
        assert node is not None
        assert node.title == "Objetivo CLI demo"
        assert node.status.value == "active"
        assert set(node.tags) == {"cli", "demo"}

        rc = cm_main(
            [
                "--workspace",
                str(root),
                "mark-objective",
                "obj-cli-demo",
                "completed",
                "--note",
                "cerrado desde CLI",
            ]
        )
        assert rc == 0
        node = boot.objective_repository.get("obj-cli-demo")
        assert node is not None
        assert node.status.value == "completed"
        notes = node.metadata.get("control_master_notes") or []
        assert any("cerrado desde CLI" in n.get("note", "") for n in notes)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_add_objective_is_idempotent_on_same_id() -> None:
    root = _workspace("idempotent")
    try:
        cm_main(
            [
                "--workspace",
                str(root),
                "add-objective",
                "--id",
                "obj-repeat",
                "--title",
                "primera version",
                "--status",
                "active",
            ]
        )
        cm_main(
            [
                "--workspace",
                str(root),
                "add-objective",
                "--id",
                "obj-repeat",
                "--title",
                "segunda version",
                "--status",
                "paused",
            ]
        )
        boot = AppBootstrap(str(root))
        node = boot.objective_repository.get("obj-repeat")
        assert node is not None
        assert node.title == "segunda version"
        assert node.status.value == "paused"
        # The update path MUST refresh updated_at_utc so
        # ObjectiveRepository.list_recent() (ORDER BY updated_at_utc DESC)
        # surfaces just-edited objectives. See Devin Review finding on PR #23.
        assert node.updated_at_utc > node.created_at_utc
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_record_decision_persists_with_related_objective() -> None:
    root = _workspace("decision")
    try:
        rc = cm_main(
            [
                "--workspace",
                str(root),
                "record-decision",
                "--id",
                "dec-cli-demo",
                "--summary",
                "Decision de prueba",
                "--reason",
                "probar CLI",
                "--status",
                "accepted",
                "--related-objective",
                "obj-cli-demo",
                "--evidence",
                "PR#20",
            ]
        )
        assert rc == 0
        boot = AppBootstrap(str(root))
        decision = boot.control_master_service.get_decision("dec-cli-demo")
        assert decision is not None
        assert decision.summary == "Decision de prueba"
        assert decision.status.value == "accepted"
        assert "obj-cli-demo" in decision.related_objective_ids
        assert "PR#20" in decision.evidence
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_mark_unresolved_appends_item() -> None:
    root = _workspace("unresolved")
    try:
        rc = cm_main(
            [
                "--workspace",
                str(root),
                "mark-unresolved",
                "Verificar X en Windows",
                "--evidence",
                "AGENTS.md",
            ]
        )
        assert rc == 0
        boot = AppBootstrap(str(root))
        state = boot.control_master_service.current_state(refresh=False)
        assert "Verificar X en Windows" in state.unresolved_items
        assert "AGENTS.md" in state.evidence_links
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_mark_objective_missing_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    root = _workspace("mark_missing")
    try:
        rc = cm_main(
            ["--workspace", str(root), "mark-objective", "obj-does-not-exist", "completed"]
        )
        assert rc == 1
        err = capsys.readouterr().err
        assert "not found" in err
    finally:
        shutil.rmtree(root, ignore_errors=True)
