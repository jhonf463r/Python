# CHAT-ARCH-2026-10-13-266 — Observation approval is not an audit release; respect the existing Owner gate

- **Episode ID:** CHAT-ARCH-2026-10-13-266
- **Reported time (America/Bogota):** 2026-10-13, 18:31–18:34 (coordinator public-source follow-up)
- **Public source baseline:** current `main` observed at `17a7a0b7275ceac5dd3f040a57c8336389f3bac1` before this write
- **Input:** Entry 265 follow-up; direct public-main reads of Control Center QML/viewmodel/tests and RQ224
- **Classification:** `OBSERVATION_PERMISSION_UI_IS_NOT_AUDIT_GATE_RELEASE_OR_MUTATION_AUTHORITY`
- **Posture:** local M0A `KEEP_BLOCKED`; public static design only
- **New edge:** `AUDIT_READ_RELEASE_AUTHORITY_MUST_NOT_BE_INFERRED_FROM_OBSERVATION_APPROVAL`

## 1. Material distinction confirmed in existing sources

Public main provides a Control Center action named `approve_observation_permission`. Its QML button is explicitly labelled “Permitir observacion”; the viewmodel's `_grant_pending_observation_permission` path and its tests use the specific scope `observe_window_content:codex`.

This is not direct evidence that the action releases an active `assistant_kind="audit"` operational block, establishes an MCP server/checkout identity, or grants repository-read access. Do not reinterpret an observation grant as a general read permission. The audit tool gate separately evaluates applicable active `OperationalBlockRecord` entries and required permission gates.

Sources:
- [ControlCenterPage.qml](https://github.com/jhonf463r/Python/blob/17a7a0b7275ceac5dd3f040a57c8336389f3bac1/IABV_v1.5/src/iabv_v15/ui/qml/pages/ControlCenterPage.qml)
- [control_center_viewmodel.py](https://github.com/jhonf463r/Python/blob/17a7a0b7275ceac5dd3f040a57c8336389f3bac1/IABV_v1.5/src/iabv_v15/ui/viewmodels/control_center_viewmodel.py)
- [test_control_center_viewmodel.py](https://github.com/jhonf463r/Python/blob/17a7a0b7275ceac5dd3f040a57c8336389f3bac1/IABV_v1.5/tests/test_control_center_viewmodel.py)
- [RQ224 trusted-source adjudication / Owner gate](https://github.com/jhonf463r/Python/blob/17a7a0b7275ceac5dd3f040a57c8336389f3bac1/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-224-rq224-static-trust-source-adjudication-and-owner-gate.md)

## 2. Preserve the scope of Entries 218–224

Entries 218–224 concern a first-tranche policy for **mutation authority**. They record explicit Owner-approval requirements bound to operation/resource/scope, fail-closed semantics, and no push in tranche one; they also state that a trusted Owner identity/receipt source was not found in the bounded mutation paths. RQ224 leaves the threat model and any further bounded identity/authority investigation behind an explicit Owner gate.

Those decisions must not be silently repurposed into an implementation authorization for a new diagnostic/grant API. Nor should the open mutation identity investigation cause this separate read-only audit problem to expand into an unbounded security audit.

The current M0A source-read gate is a separate operational precondition. Owner consent to inspect read-only remains reported, but neither the observation action nor mutation-authority records themselves prove that the active local governance block was released.

## 3. Correct next static task

Codex/coordinator may continue only on the pinned published source and existing documented paths:

1. Trace the current audit gate and the exact Control Center/WorldModel permission-action wiring already identified; determine whether any existing, already-supported control-plane action explicitly resolves an applicable audit block or authorizes a read-only checkout inspection.
2. Treat `approve_observation_permission` as observation-only unless direct source evidence shows otherwise.
3. If no existing path explicitly performs that action, specify the minimum contract for a narrow diagnostic and a separate bounded decision; do not implement a release route, invent a trust anchor, expand into the RQ224 identity subsystem, or modify the dirty local checkout.
4. State exactly which policy/authority decision is missing and stop at the existing Owner gate if resolving it would require a newly authorized identity/authority investigation.

The diagnostic must reveal only applicable block metadata. Its result must not itself grant access. A scoped decision must bind the exact server and workspace/checkout, operation class, explicit allowlisted paths, expiry and authority provenance. Unknown, mismatched, stale, denied or unavailable state stays blocked.

## 4. Adjudication

- `approve_observation_permission` exists in the inspected public UI path: **PROVEN_BY_SOURCE**.
- That action grants the specific Codex window-observation scope in the inspected tests: **PROVEN_BY_SOURCE**.
- It releases the audit-reader operational block or authenticates the local checkout target: **NOT PROVEN**.
- A dedicated narrow audit-block diagnostic/scoped grant operation: **NOT FOUND IN THE INSPECTED PUBLIC PATHS; global absence not claimed**.
- Local M0A identity/content and any live gate payload: **UNPROVEN**.
- Continue bounded public static design; do not retry or bypass local source readers. `KEEP_BLOCKED`.

No source/runtime/worktree/permission changes were made.
