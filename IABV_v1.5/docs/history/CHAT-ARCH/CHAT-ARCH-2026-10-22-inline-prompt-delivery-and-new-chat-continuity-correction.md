# Episode record — inline prompt delivery and new-chat continuity correction

- Episode date: 2026-10-22, America/Bogota.
- Type: owner correction, workflow failure and process repair.
- Primary outcome: `GOVERNED_IABV_CODEX_BRIDGE`.
- Active task: `M1A_G1_G3_AUTHORITY_ROUTE_CANDIDATE_IMPLEMENTATION`.
- Provenance: direct Owner message in this conversation; the following account is the coordinator's reconciliation of observed behavior and current public GitHub state.
- Status: `DOCUMENTED`; the updated rule must still be demonstrated by correct future behavior before calling cross-chat reuse proven.

## 1. Owner correction

The Owner explicitly said that, whenever a task requires work in another AI session, the assistant must provide the complete copy-ready prompt in the current ChatGPT answer. It is not acceptable to send the Owner to a GitHub page or another page merely to retrieve, reconstruct or copy a prompt. The project goal is to reduce manual orchestration, preserve understandable communication, and speed up development.

## 2. What went wrong

The coordinator prepared and persisted the G1–G3 Codex handoff on GitHub, then instructed the Owner to open that external page and copy the prompt. This transferred avoidable retrieval work back to the Owner and contradicted the stated collaboration goal. A further attempt initially used an incorrect branch name in the prompt even though the actual remote branch had to be verified. This was a routing/evidence defect, not Owner failure.

The prompt was not dispatched from ChatGPT: no connected action to the existing Codex UI has been used, and no Codex execution receipt has been received. Saving an artifact to GitHub must never be described as dispatch or execution.

## 3. Corrected destination and candidate facts

- Recipient: **Codex — existing UI/session**.
- Repository: `jhonf463r/Python`.
- Source base: `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db`.
- Verified empty candidate branch: `m1a-g1-g3-governance-route-candidate-20261022`.
- Candidate compare at verification: `identical`, ahead by 0, behind by 0; branch initially equals the pinned base. No product source changes were made by the coordinator.
- Handoff document: `CHAT-ARCH-2026-10-22-M1A-G1-G3-governance-route-candidate-implementation-handoff.md`; its complete prompt is duplicated inline in the corresponding assistant response, and the document remains supplemental provenance/canonical storage.
- Owner's authorization: bounded G1–G3 candidate implementation only.
- Restrictions remain: no access to the Owner's pre-existing/dirty checkout, `data/`, SQLite, secrets, credentials or `.env`; no tests/builds/runtime/process launches/real transport; no merge/deploy; no protected read or operational block release.

## 4. Permanent interaction contract for relevant project turns

1. At new-chat startup, restore `CURRENT-STATE.md`, the coordination protocol, the active handoff and only the relevant evidence sources. Do not ask the Owner to repeat a decision already recorded.
2. Name the exact recipient/session, active task, and what we are trying to achieve in plain language.
3. When another AI session must act and no direct dispatch tool is available, write the **entire self-contained prompt inline in the same ChatGPT response**, preferably in one copyable block. Never make a link the only way to retrieve it.
4. Ask the Owner for only the unavoidable manual step: copy the prompt from this chat and paste it into the named existing AI UI. Do not ask the Owner to navigate GitHub, merge files, set up a branch or perform terminal operations where the authorized connected tool can do that work.
5. Links may be supplementary evidence for inspection, but are not the prompt-delivery mechanism.
6. State truthfully whether a prompt is prepared, delivered by the Owner, dispatched through a verified tool, consumed by the agent, or answered. These states are not interchangeable.
7. If the recipient cannot use the pinned isolated candidate with available tools, tell the Owner the exact capability limitation and return the task to the coordinator; do not improvise admin commands or bypass gates.
8. After the agent responds, the coordinator retrieves/reconciles the result, fetches back material writes, updates the canonical route and entry-point indexes, and reports only evidence-supported progress.

## 5. Corrected next action

Provide the complete G1–G3 implementation prompt directly in the ChatGPT response addressed to Codex's existing UI/session. The prompt directs Codex to use the pinned public source/verified candidate branch, determine whether real G1 trusted principal/root, G2 publisher/catalogue/producer/revocation authority, and G3 versioned operation-to-target resolver can be evidenced, and implement only supported primitives. It must stop and state exact dependencies if any real authority primitive is absent.

No further route inventory or repeat contract review is justified unless new, discriminating evidence changes the preconditions.

## 6. Required truth state

```text
OWNER_CORRECTION=ACCEPTED_AND_RECORDED
PROMPT_DELIVERY=INLINE_IN_CHAT_REQUIRED
GITHUB_HANDOFF=SUPPLEMENTAL_STORAGE_NOT_SOLE_DELIVERY
DESTINATION=CODEX_EXISTING_UI_SESSION
CODEX_PROMPT_DISPATCHED=NO
CODEX_EXECUTION=NOT_CONFIRMED
CANDIDATE_BRANCH=m1a-g1-g3-governance-route-candidate-20261022
BASE_MAIN_SHA=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
IMPLEMENTATION=AUTHORIZED_FOR_ISOLATED_CANDIDATE_ONLY
GOVERNANCE=KEEP_BLOCKED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
COORDINATION_RULE=DOCUMENTED; CAUSAL_REUSE_NOT_YET_PROVEN
```
