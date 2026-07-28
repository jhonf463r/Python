"""P0.136A Agent Session Gate.

Operational script for agent coordination.  It does not decide runtime routes
and it does not mutate source code.  It builds a compact briefing before an
agent session and verifies a delivery after a session.
"""
from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_FORBIDDEN_PATTERNS = [
    "CodeKnowledgeGraph",
    "ScientificEngine",
    "UniversalObserver",
    "CodeASTExtractor",
    "SelfUnderstandingEngine",
    "UniversalReasoningEngine",
    "another brain",
    "new orchestrator",
]

TASK_STATE_NOT_STARTED = {"PENDING", "NOT_STARTED"}
VERIFICATION_NOT_STARTED = {"CODE_NOT_STARTED", "AUDITED_PENDING_IMPLEMENTATION"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def safe_read_text(path: Path, limit_chars: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if limit_chars and len(text) > limit_chars:
        return text[:limit_chars]
    return text


def safe_read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_platform_pending(root: Path) -> list[dict[str, Any]]:
    pending_dir = root / "data" / "evolution" / "platform_pending"
    tasks: list[dict[str, Any]] = []
    if not pending_dir.exists():
        return tasks
    for path in sorted(pending_dir.glob("*.json")):
        data = safe_read_json(path)
        data["_path"] = str(path.relative_to(root))
        tasks.append(data)
    return tasks


def load_optional_context(root: Path) -> dict[str, Any]:
    return {
        "portable_context_available": (root / "data" / "evolution" / "portable_context" / "latest.json").exists(),
        "self_examination_available": (root / "data" / "evolution" / "self_examination" / "latest.json").exists(),
        "portable_context": safe_read_json(root / "data" / "evolution" / "portable_context" / "latest.json")
        if (root / "data" / "evolution" / "portable_context" / "latest.json").exists()
        else {},
        "self_examination": safe_read_json(root / "data" / "evolution" / "self_examination" / "latest.json")
        if (root / "data" / "evolution" / "self_examination" / "latest.json").exists()
        else {},
    }


def collect_bootstrap_services(root: Path) -> list[str]:
    text = safe_read_text(root / "src" / "iabv_v15" / "bootstrap.py")
    services = sorted(set(re.findall(r"\bself\.([A-Za-z_][A-Za-z0-9_]*)\s*=", text)))
    return services


def recent_audits(root: Path, limit: int = 10) -> list[dict[str, Any]]:
    audit_dir = root / "docs" / "audits"
    if not audit_dir.exists():
        return []
    files = sorted(audit_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    return [
        {
            "path": str(path.relative_to(root)),
            "name": path.name,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "size": path.stat().st_size,
        }
        for path in files
    ]


def _task_blob(task: dict[str, Any]) -> str:
    parts = [
        str(task.get("id", "")),
        str(task.get("title", "")),
        str(task.get("description", "")),
        str(task.get("reason", "")),
        str(task.get("category", "")),
    ]
    return " ".join(parts).lower()


def _task_primary_blob(task: dict[str, Any]) -> str:
    return " ".join([
        str(task.get("id", "")),
        str(task.get("title", "")),
        str(task.get("category", "")),
    ]).lower()


def infer_code_evidence_for_task(root: Path, task: dict[str, Any]) -> list[str]:
    """Return lightweight evidence that task already has code in the repo."""
    blob = _task_blob(task)
    primary_blob = _task_primary_blob(task)
    evidence: list[str] = []
    if "metacognitive_audit_control_master" in primary_blob or "session_gate" in primary_blob:
        script = root / "scripts" / "devin_session_gate.py"
        if script.exists():
            evidence.append(str(script.relative_to(root)))
        return evidence

    checks = [
        (
            ("artifact_lifecycle", "storage_lifecycle", "artifact lifecycle"),
            root / "src" / "iabv_v15" / "services" / "evolution" / "artifact_lifecycle_service.py",
            "ArtifactLifecycleService",
        ),
        (
            ("agent_delivery", "agent delivery", "delivery audit"),
            root / "src" / "iabv_v15" / "services" / "evolution" / "code_audit_trail.py",
            "record_agent_delivery",
        ),
        (
            ("algorithm_fitness", "fitness algorit", "fitness self-observation"),
            root / "src" / "iabv_v15" / "services" / "evolution" / "algorithm_fitness_contract.py",
            "AlgorithmFitnessContract",
        ),
        (
            ("runtime_organ", "organ matrix", "runtime organ"),
            root / "src" / "iabv_v15" / "services" / "evolution" / "portable_context_service.py",
            "runtime_organ_matrix",
        ),
    ]

    for needles, path, symbol in checks:
        if any(needle in primary_blob for needle in needles) and path.exists():
            text = safe_read_text(path, limit_chars=1_000_000)
            if symbol in text or symbol.lower() in text.lower():
                evidence.append(f"{path.relative_to(root)}::{symbol}")
            else:
                evidence.append(str(path.relative_to(root)))
    return evidence


def summarize_platform_pending(root: Path, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(t.get("status", "UNKNOWN")) for t in tasks)
    verification_counts = Counter(str(t.get("verification_status", "UNKNOWN")) for t in tasks)
    priority_counts = Counter(str(t.get("priority", "UNKNOWN")) for t in tasks)
    stale_or_partial: list[dict[str, Any]] = []
    needs_live_proof: list[dict[str, Any]] = []

    for task in tasks:
        status = str(task.get("status", "")).upper()
        verification = str(task.get("verification_status", "")).upper()
        evidence = infer_code_evidence_for_task(root, task)
        inferred_state = ""
        if evidence and (status in TASK_STATE_NOT_STARTED or verification in VERIFICATION_NOT_STARTED):
            inferred_state = "STALE_OR_PARTIAL"
        elif "PENDING_LIVE_PROOF" in verification or "LIVE_PROOF" in str(task.get("next_action", "")).upper():
            inferred_state = "NEEDS_LIVE_PROOF"

        if inferred_state == "STALE_OR_PARTIAL":
            stale_or_partial.append({
                "id": task.get("id", ""),
                "title": task.get("title", ""),
                "declared_status": task.get("status", ""),
                "verification_status": task.get("verification_status", ""),
                "inferred_state": inferred_state,
                "evidence": evidence,
                "path": task.get("_path", ""),
            })
        elif inferred_state == "NEEDS_LIVE_PROOF":
            needs_live_proof.append({
                "id": task.get("id", ""),
                "title": task.get("title", ""),
                "declared_status": task.get("status", ""),
                "verification_status": task.get("verification_status", ""),
                "inferred_state": inferred_state,
                "path": task.get("_path", ""),
            })

    active = [
        {
            "id": t.get("id", ""),
            "title": t.get("title", ""),
            "priority": t.get("priority", ""),
            "status": t.get("status", ""),
            "next_action": t.get("next_action", ""),
        }
        for t in tasks
        if str(t.get("status", "")).upper() in {"PENDING", "READY_FOR_NEXT_SLICE", "ACTIVE"}
    ]
    active.sort(key=lambda t: (str(t.get("priority")) != "critical", str(t.get("id"))))

    return {
        "total": len(tasks),
        "status_counts": dict(status_counts),
        "verification_counts": dict(verification_counts),
        "priority_counts": dict(priority_counts),
        "active_objectives": active[:8],
        "stale_or_partial_tasks": stale_or_partial[:20],
        "needs_live_proof": needs_live_proof[:20],
    }


def detect_duplicate_definitions(root: Path) -> list[dict[str, Any]]:
    """Detect high-signal duplicate function definitions in source files."""
    findings: list[dict[str, Any]] = []
    target_files = [
        root / "src" / "iabv_v15" / "services" / "evolution" / "operational_self_examination_service.py",
    ]
    for path in target_files:
        if not path.exists():
            continue
        names: dict[str, list[int]] = {}
        for idx, line in enumerate(safe_read_text(path).splitlines(), start=1):
            match = re.match(r"\s+def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
            if match:
                names.setdefault(match.group(1), []).append(idx)
        for name, lines in names.items():
            if len(lines) > 1:
                findings.append({
                    "kind": "DUPLICATED",
                    "symbol": name,
                    "path": str(path.relative_to(root)),
                    "lines": lines,
                    "unresolved": f"UNRESOLVED:duplicate_definition:{name}",
                })
    return findings


def existing_organs(root: Path, bootstrap_services: list[str]) -> dict[str, Any]:
    key_files = {
        "AlgorithmFitnessContract": "src/iabv_v15/services/evolution/algorithm_fitness_contract.py",
        "CodeAuditTrail": "src/iabv_v15/services/evolution/code_audit_trail.py",
        "ArtifactLifecycleService": "src/iabv_v15/services/evolution/artifact_lifecycle_service.py",
        "OperationalSelfExaminationService": "src/iabv_v15/services/evolution/operational_self_examination_service.py",
        "PortableContextService": "src/iabv_v15/services/evolution/portable_context_service.py",
        "PlatformPendingQueue": "src/iabv_v15/services/evolution/platform_pending_queue.py",
    }
    bootstrap_text = safe_read_text(root / "src" / "iabv_v15" / "bootstrap.py", limit_chars=2_000_000).lower()
    return {
        "bootstrap_service_count": len(bootstrap_services),
        "bootstrap_services_sample": bootstrap_services[:80],
        "key_organs": {
            name: {
                "path": path,
                "exists": (root / path).exists(),
                "wired_hint": (
                    any(name.lower().replace("service", "") in service.lower() for service in bootstrap_services)
                    or name.lower() in bootstrap_text
                    or Path(path).stem.lower() in bootstrap_text
                ),
            }
            for name, path in key_files.items()
        },
    }


def try_algorithm_fitness(root: Path) -> tuple[dict[str, Any], list[str]]:
    unresolved: list[str] = []
    try:
        sys.path.insert(0, str(root / "src"))
        import iabv_v15.services.evolution.algorithm_fitness_contract as fitness_contract

        if os.environ.get("IABV_GATE_DEEP_FITNESS", "").strip() != "1":
            return {
                "available": True,
                "mode": "import_only",
                "contract": getattr(fitness_contract, "__name__", "algorithm_fitness_contract"),
                "note": "Set IABV_GATE_DEEP_FITNESS=1 for full matrix scan.",
            }, unresolved

        matrix = fitness_contract.build_algorithm_observation_matrix(
            workspace_root=str(root),
            src_dir=str(root / "src" / "iabv_v15"),
        )
        return {
            "available": True,
            "mode": "deep_scan",
            "total_algorithms": matrix.get("total_algorithms", 0),
            "by_capability_area": matrix.get("by_capability_area", {}),
        }, unresolved
    except Exception as exc:
        unresolved.append(f"UNRESOLVED:algorithm_fitness_unavailable:{str(exc)[:160]}")
        return {"available": False, "error": str(exc)[:200]}, unresolved
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def try_organism_state_snapshot(root: Path) -> dict[str, Any]:
    """Read-only organism state snapshot for observability."""
    try:
        sys.path.insert(0, str(root / "src"))
        from iabv_v15.services.evolution.organism_state_snapshot import (
            export_organism_state_snapshot,
        )

        snapshot = export_organism_state_snapshot(root)
        return {
            "available": True,
            "snapshot": snapshot,
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc)[:200],
        }
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def build_pre_snapshot(root: Path, agent: str) -> dict[str, Any]:
    tasks = load_platform_pending(root)
    context = load_optional_context(root)
    bootstrap_services = collect_bootstrap_services(root)
    pending_summary = summarize_platform_pending(root, tasks)
    duplicates = detect_duplicate_definitions(root)
    fitness, unresolved = try_algorithm_fitness(root)
    organism_state = try_organism_state_snapshot(root)
    if not context["portable_context_available"]:
        unresolved.append("UNRESOLVED:portable_context_latest_missing")
    if not context["self_examination_available"]:
        unresolved.append("UNRESOLVED:self_examination_latest_missing")

    human_review_required = bool(duplicates)
    recommended_next_action = "Run post-session verification only after implementing the active objective."
    if pending_summary["stale_or_partial_tasks"]:
        recommended_next_action = (
            "Reconcile stale/partial platform_pending tasks before creating new organs. "
            "Do not delete history; mark state with evidence."
        )
    elif pending_summary["active_objectives"]:
        recommended_next_action = str(pending_summary["active_objectives"][0].get("next_action", ""))[:500]

    snapshot = {
        "generated_at": utc_now(),
        "agent": agent,
        "mode": "pre",
        "active_objectives": pending_summary["active_objectives"],
        "platform_pending_summary": {
            "total": pending_summary["total"],
            "status_counts": pending_summary["status_counts"],
            "verification_counts": pending_summary["verification_counts"],
            "priority_counts": pending_summary["priority_counts"],
        },
        "stale_or_partial_tasks": pending_summary["stale_or_partial_tasks"],
        "needs_live_proof": pending_summary["needs_live_proof"],
        "existing_organs": existing_organs(root, bootstrap_services),
        "duplicate_risks": duplicates,
        "algorithm_fitness": fitness,
        "organism_state": organism_state,
        "recent_audits": recent_audits(root),
        "forbidden_patterns": DEFAULT_FORBIDDEN_PATTERNS,
        "recommended_next_action": recommended_next_action,
        "human_review_required": human_review_required,
        "unresolved": unresolved,
    }
    return snapshot


def render_pre_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# IABV Agent Session Gate - PRE",
        "",
        f"- Generated: {snapshot['generated_at']}",
        f"- Agent: {snapshot['agent']}",
        f"- Human review required: {snapshot['human_review_required']}",
        "",
        "## Next Action",
        snapshot.get("recommended_next_action") or "No recommended action found.",
        "",
        "## Active Objectives",
    ]
    for item in snapshot.get("active_objectives", [])[:8]:
        lines.append(f"- {item.get('id')}: {item.get('title')} [{item.get('status')}/{item.get('priority')}]")
    if not snapshot.get("active_objectives"):
        lines.append("- none")

    lines.extend(["", "## Stale Or Partial Tasks"])
    for item in snapshot.get("stale_or_partial_tasks", [])[:10]:
        evidence = "; ".join(item.get("evidence") or [])
        lines.append(f"- {item.get('id')}: {item.get('inferred_state')} ({item.get('declared_status')}/{item.get('verification_status')}) evidence={evidence}")
    if not snapshot.get("stale_or_partial_tasks"):
        lines.append("- none")

    lines.extend(["", "## Duplicate Risks"])
    for item in snapshot.get("duplicate_risks", [])[:10]:
        lines.append(f"- {item.get('symbol')} in {item.get('path')} lines={item.get('lines')}")
    if not snapshot.get("duplicate_risks"):
        lines.append("- none")

    lines.extend(["", "## Existing Organs"])
    for name, info in (snapshot.get("existing_organs", {}).get("key_organs") or {}).items():
        lines.append(f"- {name}: exists={info.get('exists')} wired_hint={info.get('wired_hint')} path={info.get('path')}")

    lines.extend(["", "## Organism State Snapshot"])
    org_state = snapshot.get("organism_state", {})
    if org_state.get("available"):
        snapshot_data = org_state.get("snapshot", {})
        lines.append(f"- Status: available")
        lines.append(f"- Timestamp: {snapshot_data.get('timestamp', 'unknown')}")
        lines.append(f"- Evidence sources: {', '.join(snapshot_data.get('evidence_sources', []))}")
        lines.extend(["", "### Runtime Knowledge"])
        rk = snapshot_data.get("runtime_knowledge", {})
        lines.append(f"- Runtime organs: {rk.get('runtime_organ_state', {}).get('status', 'unknown')}")
        lines.append(f"- Portable context: {rk.get('portable_context_summary', {}).get('status', 'unknown')}")
        lines.extend(["", "### Self Examination"])
        se = snapshot_data.get("self_examination", {})
        lines.append(f"- Status: {se.get('status', 'unknown')}")
        if se.get("status") == "ok":
            lines.append(f"- Source: {se.get('source', 'unknown')}")
            lines.append(f"- Findings: {se.get('findings_count', 0)}")
            if se.get("source") == "file_fallback":
                lines.append(f"- Stale-capable: {se.get('stale_capable', False)}")
                lines.append(f"- Age: {se.get('age_seconds', 0):.0f}s")
        lines.extend(["", "### World Model"])
        wm = snapshot_data.get("world_model", {})
        lines.append(f"- Status: {wm.get('status', 'unknown')}")
        if wm.get("status") == "ok":
            lines.append(f"- Source: {wm.get('source', 'unknown')}")
            lines.append(f"- Windows: {wm.get('windows_count', 0)}")
            lines.append(f"- Tools: {wm.get('tools_count', 0)}")
            if wm.get("source") == "file_fallback":
                lines.append(f"- Stale-capable: {wm.get('stale_capable', False)}")
                lines.append(f"- Age: {wm.get('age_seconds', 0):.0f}s")
        lines.extend(["", "### Control Master"])
        cm = snapshot_data.get("control_master", {})
        lines.append(f"- Status: {cm.get('status', 'unknown')}")
        if cm.get("status") == "ok":
            lines.append(f"- Source: {cm.get('source', 'unknown')}")
            lines.append(f"- Active objectives: {cm.get('active_objectives_count', 0)}")
            if cm.get("source") == "file_fallback":
                lines.append(f"- Stale-capable: {cm.get('stale_capable', False)}")
                lines.append(f"- Age: {cm.get('age_seconds', 0):.0f}s")
        lines.extend(["", "### Operational Learning"])
        ol = snapshot_data.get("operational_learning", {})
        lines.append(f"- Status: {ol.get('status', 'unknown')}")
        if ol.get("status") == "ok":
            lines.append(f"- Source: {ol.get('source', 'unknown')}")
            lines.append(f"- Recent runs: {ol.get('recent_runs_count', 0)}")
            if ol.get("source") == "file_fallback":
                lines.append(f"- Stale-capable: {ol.get('stale_capable', False)}")
                lines.append(f"- Age: {ol.get('age_seconds', 0):.0f}s")
    else:
        lines.append(f"- Status: unavailable")
        if org_state.get("error"):
            lines.append(f"- Error: {org_state.get('error')}")

    lines.extend(["", "## Forbidden To Create"])
    for pattern in snapshot.get("forbidden_patterns", []):
        lines.append(f"- {pattern}")

    lines.extend(["", "## Unresolved"])
    for item in snapshot.get("unresolved", []):
        lines.append(f"- {item}")
    if not snapshot.get("unresolved"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def run_pre(root: Path, agent: str) -> dict[str, Any]:
    snapshot = build_pre_snapshot(root, agent)
    out_dir = root / "data" / "evolution" / "agent_session_gate"
    write_json(out_dir / "latest.json", snapshot)
    write_text(out_dir / "latest.md", render_pre_markdown(snapshot))
    return snapshot


def normalize_file_arg(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def extract_classes(path: Path) -> list[str]:
    return re.findall(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b", safe_read_text(path), flags=re.MULTILINE)


def find_class_occurrences(root: Path, class_name: str) -> list[str]:
    occurrences: list[str] = []
    for base in [root / "src" / "iabv_v15", root / "scripts"]:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = safe_read_text(path)
            if re.search(rf"^\s*class\s+{re.escape(class_name)}\b", text, flags=re.MULTILINE):
                occurrences.append(str(path.relative_to(root)))
    return sorted(set(occurrences))


def compile_python(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "status": "missing", "ok": False, "error": "file_missing"}
    try:
        py_compile.compile(str(path), doraise=True)
        return {"path": str(path), "status": "compiled", "ok": True}
    except Exception as exc:
        return {"path": str(path), "status": "compile_failed", "ok": False, "error": str(exc)}


def build_post_snapshot(root: Path, agent: str, files: list[str]) -> dict[str, Any]:
    normalized = [normalize_file_arg(root, item) for item in files]
    bootstrap_text = safe_read_text(root / "src" / "iabv_v15" / "bootstrap.py", limit_chars=2_000_000)
    file_results: list[dict[str, Any]] = []
    claims_without_wiring: list[str] = []
    architecture_violations: list[str] = []
    new_modules: list[str] = []
    duplicate_class_risks: list[dict[str, Any]] = []
    human_review_required = False
    verdict = "ready"

    # Cargar snapshot PRE para validación cruzada
    pre_snapshot = safe_read_json(root / "data" / "evolution" / "agent_session_gate" / "latest.json")
    theory_validation: dict[str, Any] = {
        "pre_available": bool(pre_snapshot and "_read_error" not in pre_snapshot),
        "pre_theory": {},
        "post_reality": {},
        "divergences": [],
    }

    if theory_validation["pre_available"]:
        # Extraer teoría previa
        theory_validation["pre_theory"] = {
            "recommended_next_action": pre_snapshot.get("recommended_next_action", ""),
            "stale_or_partial_count": len(pre_snapshot.get("stale_or_partial_tasks", [])),
            "active_objectives_count": len(pre_snapshot.get("active_objectives", [])),
            "duplicate_risks_count": len(pre_snapshot.get("duplicate_risks", [])),
            "human_review_required": pre_snapshot.get("human_review_required", False),
        }

        # Comparar con realidad posterior
        theory_validation["post_reality"] = {
            "files_touched_count": len(normalized),
            "verdict": verdict,
            "duplicate_class_risks_count": len(duplicate_class_risks),
            "claims_without_wiring_count": len(claims_without_wiring),
            "human_review_required_post": human_review_required,
        }

        # Detectar divergencias
        divergences: list[str] = []
        if theory_validation["pre_theory"]["duplicate_risks_count"] > 0 and len(duplicate_class_risks) == 0:
            divergences.append("PRE reportó duplicate risks pero POST no detectó nuevos - posible mejora o falso positivo")
        if theory_validation["pre_theory"]["human_review_required"] and not human_review_required:
            divergences.append("PRE requería human review pero POST no lo requiere - posible corrección")
        if theory_validation["pre_theory"]["stale_or_partial_count"] > 0 and verdict == "ready":
            divergences.append("PRE reportó stale/partial tasks pero sesión completó con verdict ready - posible reconciliación exitosa")

        theory_validation["divergences"] = divergences

    for path in normalized:
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        result: dict[str, Any] = {"path": rel, "exists": path.exists()}
        if path.suffix == ".py":
            result["compile"] = compile_python(path)
            if not result["compile"]["ok"]:
                verdict = "rejected"

            classes = extract_classes(path)
            result["classes"] = classes
            for class_name in classes:
                occurrences = [p for p in find_class_occurrences(root, class_name) if p != rel]
                if occurrences:
                    duplicate_class_risks.append({
                        "class_name": class_name,
                        "path": rel,
                        "other_occurrences": occurrences[:8],
                    })
            if "\\services\\" in str(path).lower() or "/services/" in str(path).lower():
                service_classes = [name for name in classes if name.endswith("Service")]
                for class_name in service_classes:
                    if class_name not in bootstrap_text and path.stem not in bootstrap_text:
                        claims_without_wiring.append(f"UNRESOLVED:bootstrap_wiring_required:{rel}:{class_name}")
                        new_modules.append(rel)

        if rel.replace("\\", "/").endswith("src/iabv_v15/domain/models.py") or rel.replace("\\", "/") == "src/iabv_v15/domain/models.py":
            human_review_required = True
            architecture_violations.append("HUMAN_REVIEW_REQUIRED:domain_models_touched")

        file_results.append(result)

    if duplicate_class_risks:
        architecture_violations.append("UNRESOLVED:duplicate_class_risk")
    if human_review_required and verdict == "ready":
        verdict = "human_review_required"
    if claims_without_wiring and verdict == "ready":
        verdict = "partial"

    code_audit_result: dict[str, Any] = {"recorded": False}
    try:
        sys.path.insert(0, str(root / "src"))
        from iabv_v15.services.evolution.code_audit_trail import CodeAuditTrail

        trail = CodeAuditTrail(data_root=root / "data")
        code_audit_result = trail.record_agent_delivery(
            agent_name=agent,
            claimed_tasks=["Agent session post verification"],
            files_touched=[str(p.relative_to(root)) if p.is_relative_to(root) else str(p) for p in normalized],
            new_modules=new_modules,
            productive_call_sites=[],
            tests_added=[],
            tests_run=[],
            claims_without_wiring=claims_without_wiring,
            architecture_violations=architecture_violations,
            verdict=verdict,
            environment="windows_native" if os.name == "nt" else "unknown",
        )
        code_audit_result = {"recorded": True, "round": code_audit_result}
    except Exception as exc:
        code_audit_result = {"recorded": False, "error": str(exc)[:300]}
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass

    return {
        "generated_at": utc_now(),
        "agent": agent,
        "mode": "post",
        "files": [str(p.relative_to(root)) if p.is_relative_to(root) else str(p) for p in normalized],
        "file_results": file_results,
        "duplicate_class_risks": duplicate_class_risks,
        "claims_without_wiring": claims_without_wiring,
        "architecture_violations": architecture_violations,
        "human_review_required": human_review_required,
        "verdict": verdict,
        "code_audit_trail": code_audit_result,
        "theory_validation": theory_validation,
    }


def render_post_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# IABV Agent Session Gate - POST",
        "",
        f"- Generated: {snapshot['generated_at']}",
        f"- Agent: {snapshot['agent']}",
        f"- Verdict: {snapshot['verdict']}",
        f"- Human review required: {snapshot['human_review_required']}",
        "",
        "## Files",
    ]
    for item in snapshot.get("file_results", []):
        compile_status = item.get("compile", {}).get("status", "not_python")
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} compile={compile_status}")

    lines.extend(["", "## Risks"])
    for item in snapshot.get("claims_without_wiring", []):
        lines.append(f"- {item}")
    for item in snapshot.get("architecture_violations", []):
        lines.append(f"- {item}")
    for item in snapshot.get("duplicate_class_risks", []):
        lines.append(f"- duplicate class {item.get('class_name')} in {item.get('path')} also={item.get('other_occurrences')}")
    if not snapshot.get("claims_without_wiring") and not snapshot.get("architecture_violations") and not snapshot.get("duplicate_class_risks"):
        lines.append("- none")

    lines.extend(["", "## CodeAuditTrail"])
    lines.append(f"- recorded={snapshot.get('code_audit_trail', {}).get('recorded')}")
    if snapshot.get("code_audit_trail", {}).get("error"):
        lines.append(f"- error={snapshot['code_audit_trail']['error']}")
    return "\n".join(lines) + "\n"


def run_post(root: Path, agent: str, files: list[str]) -> dict[str, Any]:
    snapshot = build_post_snapshot(root, agent, files)
    out_dir = root / "data" / "evolution" / "agent_session_gate"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out_dir / "latest_post.json", snapshot)
    write_text(out_dir / "latest_post.md", render_post_markdown(snapshot))
    write_json(out_dir / f"post_{stamp}.json", snapshot)
    return snapshot


def run_status(root: Path) -> dict[str, Any]:
    pre = safe_read_json(root / "data" / "evolution" / "agent_session_gate" / "latest.json")
    post = safe_read_json(root / "data" / "evolution" / "agent_session_gate" / "latest_post.json")
    return {
        "generated_at": utc_now(),
        "mode": "status",
        "pre_available": bool(pre and "_read_error" not in pre),
        "post_available": bool(post and "_read_error" not in post),
        "latest_pre": pre,
        "latest_post": post,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IABV agent session gate")
    parser.add_argument("--root", default=str(workspace_root_from_here()), help="Workspace root")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("pre", help="Generate pre-session briefing")
    pre.add_argument("--agent", default="devin")

    post = sub.add_parser("post", help="Verify files after agent session")
    post.add_argument("--agent", default="devin")
    post.add_argument("--files", nargs="+", required=True)

    sub.add_parser("status", help="Print latest gate status")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "pre":
        snapshot = run_pre(root, args.agent)
        print(render_pre_markdown(snapshot))
        return 0
    if args.command == "post":
        snapshot = run_post(root, args.agent, args.files)
        print(render_post_markdown(snapshot))
        return 1 if snapshot["verdict"] == "rejected" else 0
    if args.command == "status":
        print(json.dumps(run_status(root), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
