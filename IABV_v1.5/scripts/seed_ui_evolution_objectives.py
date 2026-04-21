"""Seed del ControlMaster con el objetivo de evolucion de la UI de IABV.

El usuario identifico que la forma en que Devin UI se comunica con el humano
(paneles de secrets seguros, citations clickeables a archivos/lineas, botones
de choice en las preguntas, recordings/screenshots embebidos, links directos
a PRs/CI en vez de URLs pegadas) es un patron valioso y pidio que quede
sembrado como objetivo vivo dentro del propio Control Master para que futuras
sesiones (humanas o IA) lo trabajen guiadas por evidencia real.

Este seed NO implementa UI. Solo registra el objetivo + children como datos
en el ControlMasterService. El `EvolutionCenterViewModel` ya los va a ver.

Idempotente: correr dos veces no duplica, actualiza en lugar.

Run from repo root:

    PYTHONPATH=IABV_v1.5/src python3 IABV_v1.5/scripts/seed_ui_evolution_objectives.py
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

ROOT_ID = "obj-ui-evolution-devin-parity"

OBJECTIVES: list[dict[str, object]] = [
    {
        "objective_id": ROOT_ID,
        "kind": ObjectiveNodeKind.OBJECTIVE,
        "title": "Evolucion de la UI: paridad conversacional con Devin",
        "summary": (
            "Que el humano pueda llevar a IABV a resolver tareas sin salir "
            "del programa. La UI debe soportar los patrones que ya usa Devin "
            "con el humano: pedir secrets sin copiar/pegar, citar archivos "
            "y lineas con un click, ofrecer opciones interactivas en las "
            "preguntas, embeber recordings/screenshots, y enlazar PRs/CI "
            "directamente en vez de pegar URLs sueltas."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 15,
        "tags": ["ui", "evolution", "conversation", "devin-parity"],
    },
    {
        "objective_id": "obj-ui-evolution-secrets-panel",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Panel seguro de secrets en UI",
        "summary": (
            "Hoy los secrets (DEVIN_API_KEY, GITHUB_TOKEN_IABV, etc.) se "
            "configuran fuera de IABV (env, archivos, PowerShell). La UI "
            "debe tener un panel que pida el secret, lo valide (ping real "
            "al servicio correspondiente), lo guarde en el secret store del "
            "OS (no en archivos de proyecto), y muestre estado vivo "
            "(presente / valido / scope OK). Respeta la capa existente: "
            "no crea otro cerebro, solo es affordance de UI sobre lo que "
            "ya decide ToolTeachService / AutonomyGovernancePolicy."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 20,
        "tags": ["ui", "secrets", "security"],
    },
    {
        "objective_id": "obj-ui-evolution-file-citations",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Citations clickeables a archivos y lineas",
        "summary": (
            "Cuando IABV responde 'el bug esta en X', la UI debe permitir "
            "abrir el archivo y la linea con un click (como <ref_file> y "
            "<ref_snippet> de Devin). Esto reemplaza el patron de pegar "
            "rutas absolutas como texto. Requiere parser de respuestas + "
            "componente QML clickeable que abra el editor preferido del "
            "usuario (VSCode, PyCharm) o la vista interna de IABV."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 25,
        "tags": ["ui", "citations", "developer-experience"],
    },
    {
        "objective_id": "obj-ui-evolution-option-buttons",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Botones de choice en preguntas interactivas",
        "summary": (
            "Cuando IABV pregunta al humano algo con respuestas discretas "
            "('auto-merge si/no?', 'cual ruta preferis?'), la UI debe "
            "mostrar botones clickeables + 'Otra...' como free-text. Hoy "
            "se responde todo con texto libre. Esto reduce friccion y "
            "evita ambiguedad. Requiere schema de 'respuesta estructurada' "
            "en el protocolo de conversacion interno + componente QML."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 30,
        "tags": ["ui", "conversation", "interaction"],
    },
    {
        "objective_id": "obj-ui-evolution-recordings",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Embeber recordings y screenshots en el dialogo",
        "summary": (
            "Cuando IABV valida algo visual (UI de terceros, resultado de "
            "una herramienta), la UI debe embeber el screenshot o el video "
            "en el mismo hilo de conversacion, no como archivo aparte. "
            "Require integracion con el WorldModelService que ya captura "
            "snapshots + componente QML que embeba media inline."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 35,
        "tags": ["ui", "media", "observability"],
    },
    {
        "objective_id": "obj-ui-evolution-pr-ci-links",
        "kind": ObjectiveNodeKind.TASK,
        "parent_id": ROOT_ID,
        "root_id": ROOT_ID,
        "title": "Links vivos a PRs y CI en lugar de URLs pegadas",
        "summary": (
            "Cuando IABV crea un PR o consulta CI (via GitHubApiToolAdapter), "
            "la UI debe mostrar una card clickeable con estado vivo (open / "
            "merged / ci_green / ci_red) que se refresque via polling al "
            "endpoint real, no una URL texto. Cierra el loop de la "
            "capacidad que agrega el GitHubApiToolAdapter."
        ),
        "status": ObjectiveStatus.ACTIVE,
        "priority": 40,
        "tags": ["ui", "github", "live-state"],
    },
]

DECISION = ControlDecision(
    decision_id="dec-ui-evolution-devin-parity",
    summary=(
        "La UI de IABV debe evolucionar hacia paridad conversacional con "
        "Devin: secrets seguros, citations clickeables, opciones "
        "interactivas, media embebida, links vivos a PRs/CI. Se registra "
        "como objetivo vivo en ControlMaster para que futuras sesiones lo "
        "trabajen guiadas por evidencia."
    ),
    reason=(
        "El usuario observo los patrones de Devin UI y los valida como "
        "utiles. La evolucion gobernada de la UI esta prevista en la "
        "arquitectura (EvolutionCenterViewModel). Sembrar el objetivo es "
        "el paso minimo que preserva la capa: no inventa otro cerebro, "
        "no escribe UI todavia, solo deja el norte visible."
    ),
    impact=(
        "Cualquier sesion que consuma ControlMasterDigest vera este "
        "objetivo en active_objectives_brief. El EvolutionCenterViewModel "
        "lo expone en la UI actual. Ningun cambio de codigo ejecutable."
    ),
    affected_modules=[
        "services/evolution/control_master_service",
        "ui/viewmodels/evolution_center_viewmodel",
    ],
    status=ControlDecisionStatus.ACCEPTED,
    evidence=[
        "https://github.com/jhonf463r/Python/pull/92",
        "https://github.com/jhonf463r/Python/pull/93",
    ],
    related_objective_ids=[
        ROOT_ID,
        "obj-ui-evolution-secrets-panel",
        "obj-ui-evolution-file-citations",
        "obj-ui-evolution-option-buttons",
        "obj-ui-evolution-recordings",
        "obj-ui-evolution-pr-ci-links",
    ],
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

    print("Recording governing decision ...")
    service.record_decision(DECISION)

    print("Refreshing digest ...")
    digest = boot.export_control_master_digest()
    print("---- digest brief ----")
    print(f"active_objectives: {digest.get('active_objectives_brief') or []}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
