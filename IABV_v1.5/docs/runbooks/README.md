# IABV v1.5 — Capability and technical runbook catalog

This is a discovery index, not a task router, permission store, or proof that a session has consumed a capability. Methods are documented unless a runbook explicitly supplies verified automation and tests.

## Current case-specific product design
- [BURVE — María: Luz que acompaña, four-face design case](../product-design/BURVE-MARIA-LUZ-QUE-ACOMPANA-FOUR-FACE-DESIGN-CASE.md) — recovered product facts, source assets, two-pair face hypothesis, market/perception evidence, design constraints and next action.
  - Capability ID: `BURVE_FOUR_FACE_LANTERN_DESIGN`; this case only.
  - Original source: [owner-supplied trapezoidal panel SVG](../product-design/assets/1FarolPVirgen3-owner-source.svg).

## Reusable manufacturing / digital fabrication
- [Laser-cut vector topology and manufacturability](./laser-cut-vector-topology-skill.md) — SVG/DXF/CAM semantics, retained stock, cutouts, dropped slugs, kerf, bridges, opaque engraved faces and release gates.
  - Capability ID: `LASER_VECTOR_TOPOLOGY`; reusable across laser-cut projects.
  - Learning receipt: [BURVE technical knowledge absorption](../history/CHAT-ARCH/CHAT-ARCH-2026-10-31-LASER-CUT-VECTOR-TOPOLOGY-KNOWLEDGE-ABSORPTION.md).

## IABV operational / audit tools
- [Audit Tools MCP — Operational Runbook](./audit-tools-runbook.md) — existing five audit tools for bounded workspace observation, test execution and read-only Git state, subject to current governance gates.
  - Capability ID: `IABV_AUDIT_TOOLS`; do not infer permission to start runtime or run tests.

## Capability metadata contract
Each capability must declare: `CAPABILITY_ID`, version, domain/triggers, canonical source, case-specific vs reusable scope, inputs/outputs, constraints/stop conditions, dependencies/compatibility, supersedes lineage, and evidence state.

### Precedence and coexistence
1. Live `CURRENT-STATE.md` controls current route, permissions and stop conditions.
2. Explicit current Owner decisions and primary artifacts control product requirements and geometry.
3. Case-specific dossier controls the interpretation/status of its own product artifacts.
4. UAAL methods govern reasoning, continuity, evidence and handoffs.
5. Reusable domain skills provide methods; they cannot override Owner geometry or authorization.
6. Historical receipts are evidence/history, not active instructions unless the live route reactivates them.

Do not merge incompatible geometries or create duplicate coordinators, registries or memory stores. Reconcile any conflict explicitly.

## Activation protocol
Refresh the exact live branch/commit; read CURRENT-STATE; match the objective to capability triggers; retrieve and activate only relevant canonical sources; record the exact revision and changed decision; verify outcome. Keep the evidence ladder separate:
`MEMORY_RETRIEVED → METHOD_ACTIVATED → METHOD_APPLIED → OUTCOME_VERIFIED → LATER_CAUSAL_REUSE`.
A link, file, commit or open PR proves persistence, not consumption. A branch-only route is not yet a main-branch route.
