# CHAT-ARCH-2026-10-07-137 — CAPABILITY → REALIZATION EMPTY-SET CONTRACT AUDIT

## PROVENANCE

Input: Independent Sonnet/Claude static audit received 2026-10-07.

Source-bearing executable baseline:
07ebffc8f866fc99a3f78091dcd1edd456a0da00
Tree:
f0e1294982479426b140eab21f16f2f839504413

Current documentation main at reconciliation start:
1bd250bb87678487eff04a439dd28775d1f11864

No runtime, tests, or executable-source modifications were performed in this reconciliation.

## VERIFIED FINDINGS

Sonnet/Claude independently confirmed the capability-aware realization design up to the final closure gate and identified one first-open contract edge:

capability-eligible realization set = ∅ → explicit defer/fail-closed outcome

Verified escape paths include:
- ToolRegistry fallback to assistant family / lexical match / first card;
- SynapticRouter-derived authoritative selection;
- preferred external selection;
- explicit assistant family fallback;
- selector empty-candidate behavior followed by suggested-tool resurrection;
- permissive handling of an empty allowed_tool_ids intersection;
- later re-resolution in preview/execute paths.

Therefore an empty eligible set cannot be represented as no restriction.

## ADDITIONAL DIRECT SOURCE RECONCILIATION

Direct source inspection of the same executable baseline found:

- ToolTaskStatus.DEFERRED = deferred already exists in domain/models.py.
- A search for ToolTaskStatus.DEFERRED found no current runtime consumer in the inspected source.
- ModeSelectionDecision currently has selected_tool_id="" and selected_mode=FALLBACK, but that empty selection is not a closed defer contract because build_task_from_request() currently resurrects suggested_tool_id with selection.selected_tool_id or suggested_tool_id.
- execute_task() already has a structured missing-tool result path, but it occurs after registry resolution and therefore cannot serve as the upstream capability-empty decision contract.
- ToolTaskStatus.DEFERRED is therefore a reusable existing domain state, but defined ≠ wired: its semantic propagation from selection is not established.

## DESIGN CONSEQUENCES

1. Do not create a new universal routing organ.
2. Do not create a new task-status enum solely for this gap.
3. First determine the smallest existing-domain composition that lets capability-constrained selection produce an explicit no-realization outcome and propagate it into ToolTaskStatus.DEFERRED (or an already existing equivalent) without allowing suggestion, Synaptic, preference, registry lexical fallback or first-card fallback to resurrect an ineligible tool.
4. Keep required_capability_ids stable and separate from readiness snapshot and candidate-set state.
5. Keep multi-ID flat requirements conjunctive unless a separate explicit alternative contract is proven.
6. The unresolved per-task capability grouping and the circular tools.local.* readiness/realization relation remain dependent design questions; do not broaden into a general capability taxonomy before the empty-set boundary is closed.

## METHOD DELTA

New reusable invariant:
capability-constrained empty set ≠ unconstrained selection

A failed capability gate must be an explicit governed outcome that survives every downstream fallback boundary.

Existing enum discovery adds:
existing domain status can be candidate for reuse, but its runtime consumption must be proven before treating it as the solution.

## ROUTING DELTA

Current first-open contract edge:
capability-eligible candidate set = ∅ → explicit typed/deferred outcome → no fallback resurrection

Next actor:
CODEX

Capability:
minimal static contract archaeology for empty-set/defer propagation and fail-closed routing, using existing domain state only

No implementation or runtime authorization yet.

## CLASSIFICATION

STATIC / INDEPENDENTLY AUDITED / DESIGN OPEN / SINGLE FIRST-OPEN EDGE
