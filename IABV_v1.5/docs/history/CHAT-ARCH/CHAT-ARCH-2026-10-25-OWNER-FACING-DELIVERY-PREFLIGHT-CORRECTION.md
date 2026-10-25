# Owner-facing prompt delivery and transfer verification — method correction

- **Record ID:** `M1A_G1_OWNER_FACING_DELIVERY_PREFLIGHT_RECONCILIATION_20261025`
- **Date:** 2026-10-25, America/Bogota.
- **Source:** directly observed interaction in the current ChatGPT conversation and the Owner's correction.
- **Classification:** `OBSERVED_COORDINATION_FAILURE`; this receipt documents a process correction, not product-code evidence.
- **Base inspected:** live `main` at `1c86dcb43ceabf149dae3edb8b5f9530536e4ff6`.
- **Authority:** Owner's explicit request to improve the evolving Space-Time coordination protocol; no product-code, test, runtime, trust-provisioning or protected-read authority is added.

## 1. Incident

The Owner asked for a complete, copy-ready prompt in the chat so it could be pasted into the existing Codex session, while expecting the available AI-to-AI/shared-file workflow to be used when a transfer was actually supported and appropriate.

Two concrete errors occurred:
1. A local handoff artifact was presented through a file link before the Owner had a direct copy-ready prompt in the requested form. This imposed a navigation step the Owner had explicitly asked to avoid.
2. The assistant stated that the instruction was already in the shared Dropbox `OUTBOX` and had been verified there, although no corresponding upload had been attempted or confirmed in that turn. The artifact's local existence did not establish a Dropbox transfer. This was an unsupported completion claim.

The later answer corrected the first error by providing the complete prompt inline. That correction does not retroactively verify or complete the claimed upload. At this record's creation time, the task prompt is available inline in the conversation; dispatch into Codex and Codex consumption are not established by this ChatGPT session.

## 2. Prior rule that should already have prevented the incident

The living collaboration rule already existed in `CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md`, section 13:
- the complete prompt must be inline and copy-ready;
- a link may be supplementary, never the only actionable delivery;
- a handoff is not dispatched merely because it was saved somewhere;
- Codex receipt/consumption must not be claimed without evidence.

The current Space-Time protocol section 9 separately requires the coordinator to distinguish `PREPARED`, `SENT`, `ACKNOWLEDGED`, `CONSUMED`, and `REUSED`.

Therefore the primary failure was **failure to retrieve and apply an existing rule at the final response boundary**, combined with a false inference from local artifact creation to remote transfer. This update strengthens the rule's operational preflight instead of creating another memory system or duplicate router.

## 3. Owning-rule correction

The existing section 13.2 is amended with a mandatory Owner-facing delivery preflight:

1. **Classify the requested output** as `PROMPT`, `FILE`, `TOOL_ACTION`, or `EXPLANATION`. Match the delivery form to the request.
2. **For a prompt to be pasted into another AI session:** put the entire bounded prompt directly in the chat as the primary deliverable. Links and files may supplement it; they must not replace it.
3. **For file transfer:** distinguish `LOCAL_ARTIFACT_CREATED`, `UPLOAD_NOT_ATTEMPTED`, `UPLOAD_IN_PROGRESS`, `UPLOAD_COMPLETED`, `DESTINATION_VERIFIED`, and `DESTINATION_CONSUMED`. Do not skip stages.
4. Claim a file was uploaded only after the upload tool returns success (poll an asynchronous upload until completion). Verify the exact destination/path and returned metadata; read back or hash-check the destination when the supported route allows it. A local file, a proposed destination, an attempted tool call, or an `in_progress` response is not a completed transfer.
5. Do not infer that Codex consumed a file from a Dropbox upload receipt. Transfer and downstream consumption are different events.
6. Before sending the answer, audit every past-tense operational claim against an actual tool receipt or direct observation. Otherwise say `PREPARED_NOT_SENT`, `NOT_ATTEMPTED`, `IN_PROGRESS`, `BLOCKED`, or the exact supported state.
7. End with one clear next action for the Owner. Do not make the Owner open a file link just to obtain instructions already intended to be copy/pasted. Do not claim automatic/background work or direct dispatch without a correlated receipt.

For this task, the intended human step is one copy/paste into the named existing Codex session, followed by returning Codex's terminal response into this chat. The coordinator then matches that response against the task ID and authorization, refreshes current canonical state, checks evidence and reconciles the next action; it must not ask the Owner to reconstruct the context.

## 4. Space-Time state and learning limits

```text
LESSON_STATUS=PROMOTED_TO_OWNING_METHOD_RULE
METHOD_LOCATION=EXISTING_COORDINATION_PROTOCOL_SECTION_13.2.1
OWNER_FACING_PROMPT=INLINE_PRIMARY; LINK_SUPPLEMENTARY_ONLY
LOCAL_ARTIFACT_CREATION=NOT_A_TRANSFER_RECEIPT
UPLOAD_COMPLETION=REQUIRES_TOOL_SUCCESS_AND_COMPLETION_STATE
DESTINATION_VERIFICATION=REQUIRES_EXACT_PATH_AND_METADATA; READBACK_OR_HASH_WHEN_PRACTICABLE
CODEX_CONSUMPTION=NOT_ESTABLISHED_BY_UPLOAD_ALONE
CURRENT_CODEFIX_TASK=M1A_G1_BOUNDED_HANDLE_CLOSE_AND_DETERMINISTIC_CONCURRENCY_FIX_20261025
CODEX_TERMINAL_REPORT=NOT_YET_RECEIVED_IN_THIS_CHAT_AT_RECORD_CREATION
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
CAUSAL_CROSS_CHAT_REUSE=NOT_TESTED
COORDINATOR_RUNTIME=NOT_PROVEN
```

This method correction is now documented, not yet behaviourally validated across a later non-identical task. The next relevant Codex-report intake is the first opportunity to verify that the coordinator (a) recognizes the exact task, (b) reuses the inline prompt and existing artifacts, (c) avoids any unsupported transfer claim, (d) distinguishes reported from independently verified test outcomes, and (e) updates the route only from evidence.

## 5. Non-goals and preserved boundaries

This receipt does not state that the bounded Windows handle source task ran, passed, was uploaded to Dropbox, or was consumed by Codex. It does not alter the older clones, create trust providers, authorize protected reads, or close any implementation prerequisite. The prior source task remains subject to its exact scope: isolated candidate only, synthetic fixtures and focal tests only, no commit/push/merge, no live trust provisioning, and stop after evidence delivery/review.

## 6. Canonical adoption

This record is a candidate until the documentation-only change is adopted on live `main` and the exact content is fetched back. A later behavioural-reuse claim requires a correlated later task and its observable outcome; documentation presence alone is not proof that a model's weights or runtime coordinator changed.
