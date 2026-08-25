"""Control Master CLI subcommands.

Read / write the live Control Master layer without booting the UI. Meant
for any AI session (Codex, ChatGPT, Devin, Claude) that needs to arrive
synchronized without pasting chat history:

    PYTHONPATH=src python -m iabv_v15 cm export-digest
    PYTHONPATH=src python -m iabv_v15 cm export-digest --format markdown
    PYTHONPATH=src python -m iabv_v15 cm set-vision "nueva vision"
    PYTHONPATH=src python -m iabv_v15 cm add-objective --id obj-foo --title "..." --status active
    PYTHONPATH=src python -m iabv_v15 cm record-decision --summary "..." --reason "..."
    PYTHONPATH=src python -m iabv_v15 cm mark-objective obj-foo completed
    PYTHONPATH=src python -m iabv_v15 cm mark-unresolved "texto del unresolved"

All write operations go through ControlMasterService / ObjectiveRepository
so the system stays the single source of truth. AGENTS.md's
"no crear otro cerebro" contract is preserved: this module never reasons,
it only dispatches calls to services that already exist.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _bootstrap(workspace: str | None) -> Any:
    from iabv_v15.bootstrap import AppBootstrap

    root = workspace or str(Path.cwd())
    return AppBootstrap(root)


def _format_digest_markdown(digest: dict[str, Any]) -> str:
    lines: list[str] = []
    version = digest.get("version") or "control_master"
    lines.append(f"# Control Maestro digest ({version})")
    lines.append("")
    vision = str(digest.get("current_vision") or "").strip()
    if vision:
        lines.append(f"**Vision:** {vision}")
        lines.append("")
    rules = digest.get("rules_brief") or []
    if rules:
        lines.append(f"## Reglas ({len(rules)})")
        for rule in rules:
            lines.append(f"- {rule}")
        lines.append("")
    active = digest.get("active_objectives_brief") or []
    if active:
        lines.append("## Objetivos activos")
        for item in active:
            lines.append(f"- {item}")
        lines.append("")
    backlog = digest.get("top_backlog") or []
    if backlog:
        lines.append("## Backlog")
        for item in backlog:
            lines.append(f"- {item}")
        lines.append("")
    decisions = digest.get("recent_decisions_brief") or []
    if decisions:
        lines.append("## Decisiones recientes")
        for item in decisions:
            lines.append(f"- {item}")
        lines.append("")
    risks = digest.get("current_risks") or []
    if risks:
        lines.append("## Riesgos actuales")
        for item in risks:
            lines.append(f"- {item}")
        lines.append("")
    unresolved = digest.get("unresolved") or []
    if unresolved:
        lines.append("## UNRESOLVED")
        for item in unresolved:
            lines.append(f"- {item}")
        lines.append("")
    tests = str(digest.get("tests_state_brief") or "").strip()
    if tests:
        lines.append(f"**Tests:** {tests}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_export_digest(args: argparse.Namespace) -> int:
    boot = _bootstrap(args.workspace)
    digest = boot.export_control_master_digest(refresh=args.refresh)
    if args.format == "markdown":
        sys.stdout.write(_format_digest_markdown(digest))
    else:
        json.dump(digest, sys.stdout, indent=2, ensure_ascii=False, default=str)
        sys.stdout.write("\n")
    return 0


def cmd_set_vision(args: argparse.Namespace) -> int:
    boot = _bootstrap(args.workspace)
    state = boot.control_master_service.set_vision(
        args.vision,
        evidence=list(args.evidence or []),
    )
    print(f"vision set (last_updated={state.last_updated.isoformat()})")
    return 0


def cmd_add_objective(args: argparse.Namespace) -> int:
    from iabv_v15.domain.models import (
        ObjectiveNode,
        ObjectiveNodeKind,
        ObjectiveStatus,
        utc_now,
    )

    boot = _bootstrap(args.workspace)
    repo = boot.objective_repository

    try:
        kind = ObjectiveNodeKind(args.kind)
    except ValueError:
        print(f"error: unknown kind '{args.kind}'", file=sys.stderr)
        return 2
    try:
        status = ObjectiveStatus(args.status)
    except ValueError:
        print(f"error: unknown status '{args.status}'", file=sys.stderr)
        return 2

    objective_id = args.id
    existing = repo.get(objective_id) if objective_id else None
    if existing is not None:
        node = existing.model_copy(
            update={
                "title": args.title,
                "summary": args.summary or "",
                "kind": kind,
                "status": status,
                "priority": args.priority,
                "parent_id": args.parent_id,
                "root_id": args.root_id or existing.root_id or objective_id,
                "tags": list(args.tag or []) or existing.tags,
                "updated_at_utc": utc_now(),
            }
        )
        action = "updated"
    else:
        kwargs: dict[str, Any] = {
            "kind": kind,
            "title": args.title,
            "summary": args.summary or "",
            "status": status,
            "priority": args.priority,
            "parent_id": args.parent_id,
            "tags": list(args.tag or []),
        }
        if objective_id:
            kwargs["objective_id"] = objective_id
            kwargs["root_id"] = args.root_id or objective_id
        elif args.root_id:
            kwargs["root_id"] = args.root_id
        node = ObjectiveNode(**kwargs)
        action = "created"
    saved = repo.save(node)
    print(f"objective {action}: {saved.objective_id} ({saved.status.value})")
    return 0


def cmd_mark_objective(args: argparse.Namespace) -> int:
    boot = _bootstrap(args.workspace)
    updated = boot.control_master_service.mark_objective(
        args.objective_id,
        args.status,
        note=args.note or "",
    )
    if updated is None:
        print(
            f"error: objective '{args.objective_id}' not found or status '{args.status}' invalid",
            file=sys.stderr,
        )
        return 1
    print(f"objective {updated.objective_id} -> {updated.status.value}")
    return 0


def cmd_record_decision(args: argparse.Namespace) -> int:
    from iabv_v15.domain.models import ControlDecision, ControlDecisionStatus

    boot = _bootstrap(args.workspace)
    try:
        status = ControlDecisionStatus(args.status)
    except ValueError:
        print(f"error: unknown decision status '{args.status}'", file=sys.stderr)
        return 2
    decision_kwargs: dict[str, Any] = {
        "summary": args.summary,
        "reason": args.reason or "",
        "impact": args.impact or "",
        "status": status,
        "affected_modules": list(args.affected_module or []),
        "evidence": list(args.evidence or []),
        "linked_tests": list(args.linked_test or []),
        "related_objective_ids": list(args.related_objective or []),
        "related_rule_ids": list(args.related_rule or []),
    }
    if args.id:
        decision_kwargs["decision_id"] = args.id
    decision = ControlDecision(**decision_kwargs)
    saved = boot.control_master_service.record_decision(decision)
    print(f"decision recorded: {saved.decision_id} ({saved.status.value})")
    return 0


def cmd_mark_unresolved(args: argparse.Namespace) -> int:
    boot = _bootstrap(args.workspace)
    state = boot.control_master_service.mark_unresolved(
        args.item,
        evidence=list(args.evidence or []),
    )
    print(f"unresolved recorded (total={len(state.unresolved_items)})")
    return 0


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    parser = parser or argparse.ArgumentParser(prog="iabv_v15 cm")
    parser.add_argument(
        "--workspace",
        default=None,
        help="Workspace root (default: current working directory).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export-digest", help="Print the ControlMasterDigest.")
    p_export.add_argument(
        "--format", choices=["json", "markdown"], default="json"
    )
    p_export.add_argument(
        "--refresh",
        action="store_true",
        help="Skip the saved base state (use only when you want a live projection, may drop persisted current_vision/tests/metadata).",
    )
    p_export.set_defaults(func=cmd_export_digest)

    p_vision = sub.add_parser("set-vision", help="Update the active vision.")
    p_vision.add_argument("vision")
    p_vision.add_argument("--evidence", action="append", help="Evidence reference (repeatable).")
    p_vision.set_defaults(func=cmd_set_vision)

    p_add_obj = sub.add_parser("add-objective", help="Create or update an objective node.")
    p_add_obj.add_argument("--id", default=None, help="Stable objective_id (recommended for idempotent seeding).")
    p_add_obj.add_argument("--title", required=True)
    p_add_obj.add_argument("--summary", default="")
    p_add_obj.add_argument("--kind", default="objective", choices=["objective", "project", "task", "subtask"])
    p_add_obj.add_argument("--status", default="active", choices=["pending", "active", "blocked", "completed", "paused"])
    p_add_obj.add_argument("--priority", type=int, default=50)
    p_add_obj.add_argument("--parent-id", default=None)
    p_add_obj.add_argument("--root-id", default=None)
    p_add_obj.add_argument("--tag", action="append", help="Tag (repeatable).")
    p_add_obj.set_defaults(func=cmd_add_objective)

    p_mark = sub.add_parser("mark-objective", help="Change the status of an existing objective.")
    p_mark.add_argument("objective_id")
    p_mark.add_argument("status", choices=["pending", "active", "blocked", "completed", "paused", "discarded"])
    p_mark.add_argument("--note", default="")
    p_mark.set_defaults(func=cmd_mark_objective)

    p_decision = sub.add_parser("record-decision", help="Record a ControlDecision.")
    p_decision.add_argument("--id", default=None, help="Stable decision_id.")
    p_decision.add_argument("--summary", required=True)
    p_decision.add_argument("--reason", default="")
    p_decision.add_argument("--impact", default="")
    p_decision.add_argument("--status", default="accepted", choices=["proposed", "accepted", "implemented", "reverted"])
    p_decision.add_argument("--affected-module", action="append")
    p_decision.add_argument("--evidence", action="append")
    p_decision.add_argument("--linked-test", action="append")
    p_decision.add_argument("--related-objective", action="append")
    p_decision.add_argument("--related-rule", action="append")
    p_decision.set_defaults(func=cmd_record_decision)

    p_unresolved = sub.add_parser("mark-unresolved", help="Append an item to unresolved_items.")
    p_unresolved.add_argument("item")
    p_unresolved.add_argument("--evidence", action="append")
    p_unresolved.set_defaults(func=cmd_mark_unresolved)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
