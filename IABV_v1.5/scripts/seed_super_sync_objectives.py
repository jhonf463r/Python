"""Seed the ControlMaster layer with the three "super sincronia" gaps as
real objectives, plus the governing decision. Idempotent: running twice
updates in place instead of duplicating.

Run from repo root:

    PYTHONPATH=IABV_v1.5/src python3 IABV_v1.5/scripts/seed_super_sync_objectives.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    ControlDecision,
    ControlDecisionStatus,
    ObjectiveNode,
    ObjectiveNodeKind,
    ObjectiveStatus,
)

ROOT_ID = "obj-control-master-super-sync"

OBJECTIVES: list[dict[str, object]] = [
    {
        "objective_id": ROOT_ID,
        "kind": ObjectiveNodeKind.OBJECTIVE,
        "title": "Capa Control Maestro: super sincronia entre sesiones",
        "summary": (
            "Garantizar que cualquier IA (Codex, ChatGPT, Devin, Claude) que "
            "tome el proyecto pueda leer y escribir el estado real sin pegar "
            "historial de chat. Usa ControlMasterDigest como unica fuente "
            "compacta de verdad."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 10,
    },
    {
        "objective_id": "obj-super-sync-cli-export",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Exponer un CLI para exportar el ControlMasterDigest",
        "summary": (
            "Hoy AppBootstrap.export_control_master_digest() existe pero solo "
            "es invocable desde codigo. Falta un entrypoint tipo "
            "'python -m iabv_v15 export-digest' que escupa el digest como "
            "JSON/markdown para pegarlo a cualquier IA externa."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 20,
        "tags": ["control-master", "cli", "super-sync"],
    },
    {
        "objective_id": "obj-super-sync-write-bridge",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Puente de escritura: UI/CLI sobre ControlMasterService",
        "summary": (
            "Las IAs solo pueden leer el control maestro. Para 'agregar tareas "
            "pendientes' desde cualquier sesion falta affordance en UI y CLI "
            "que llame add_objective / record_decision / mark_unresolved. Los "
            "metodos del servicio ya existen; falta el camino desde fuera."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 25,
        "tags": ["control-master", "ui", "cli", "super-sync"],
    },
    {
        "objective_id": "obj-super-sync-outcome-loop",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Cierre de loop: TaskOutcomeRecorder -> ControlMasterService",
        "summary": (
            "Hoy cuando una sesion completa un objetivo o marca UNRESOLVED "
            "nada lo registra automaticamente en el control maestro. Conectar "
            "TaskOutcomeRecorder con mark_objective(completed) / "
            "mark_unresolved para cerrar el loop de aprendizaje sin "
            "intervencion humana."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 30,
        "tags": ["control-master", "learning", "super-sync"],
    },
]

DECISION = ControlDecision(
    decision_id="dec-self-governance-via-control-master",
    summary=(
        "Los tres gaps de super sincronia se registran como objetivos "
        "reales dentro del propio ControlMasterService, sin codigo nuevo. "
        "El sistema se gobierna a si mismo."
    ),
    reason=(
        "El usuario pidio que cualquier sesion futura vea donde vamos y que "
        "falta. La infraestructura ya estaba: falta usarla. Registrar los "
        "gaps como objetivos persistidos es el camino minimo que preserva "
        "arquitectura y no inventa otro cerebro."
    ),
    impact=(
        "Cualquier sesion que consuma ControlMasterDigest vera estos "
        "objetivos en active_objectives_brief. No hay cambios de codigo."
    ),
    affected_modules=[
        "services/evolution/control_master_service",
        "infra/persistence/objective_repository",
    ],
    status=ControlDecisionStatus.ACCEPTED,
    evidence=[
        "https://github.com/jhonf463r/Python/pull/14",
        "https://github.com/jhonf463r/Python/pull/17",
        "https://github.com/jhonf463r/Python/pull/20",
    ],
    related_objective_ids=[
        ROOT_ID,
        "obj-super-sync-cli-export",
        "obj-super-sync-write-bridge",
        "obj-super-sync-outcome-loop",
    ],
)

VISION = (
    "IABV v1.5 local-first con Control Maestro vivo: ControlMasterDigest "
    "como unica fuente compacta para que cualquier IA (Codex, ChatGPT, "
    "Devin, Claude) arranque sincronica sin pegar historial. Super "
    "sincronia = lectura automatica al entrar + escritura estructurada al "
    "cerrar cada sesion."
)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    print(f"Bootstrapping AppBootstrap at {repo_root} ...")
    boot = AppBootstrap(str(repo_root))

    service = boot.control_master_service
    repo = boot.objective_repository

    for payload in OBJECTIVES:
        objective_id = payload["objective_id"]
        existing = repo.get(objective_id)
        if existing is not None:
            update = {
                "title": payload["title"],
                "summary": payload["summary"],
                "status": payload["status"],
                "priority": payload["priority"],
                "kind": payload["kind"],
                "parent_id": payload.get("parent_id"),
                "root_id": payload.get("root_id") or existing.root_id or objective_id,
                "tags": list(payload.get("tags", [])),
            }
            node = existing.model_copy(update=update)
            print(f"  updating objective {objective_id}")
        else:
            node = ObjectiveNode(
                objective_id=objective_id,
                kind=payload["kind"],
                title=payload["title"],
                summary=payload["summary"],
                parent_id=payload.get("parent_id"),
                root_id=payload.get("root_id") or objective_id,
                priority=payload["priority"],
                status=payload["status"],
                tags=list(payload.get("tags", [])),
            )
            print(f"  creating objective {objective_id}")
        repo.save(node)

    print(f"Recording governing decision ...")
    service.record_decision(DECISION)

    # set_vision() must run AFTER objective seeding so save_state() snapshots
    # the already-projected active objectives into latest.json.
    print(f"Setting vision ...")
    service.set_vision(VISION)

    print("Refreshing digest ...")
    digest = boot.export_control_master_digest()
    print("---- digest brief ----")
    print(f"vision: {digest.get('current_vision')}")
    print(f"rules: {len(digest.get('rules_brief') or [])}")
    print(f"active_objectives: {digest.get('active_objectives_brief') or []}")
    print(f"top_backlog: {digest.get('top_backlog') or []}")
    print(f"unresolved: {digest.get('unresolved') or []}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
