# IABV v1.5 — Communication-Aware Frontier Search
DATE=2026-10-17
STATUS=PROPOSED_METHOD_DELTA / NOT_RUNTIME_PROVEN
GOVERNANCE=KEEP_BLOCKED
SCOPE=Objective-conditioned discovery, communication-path diagnosis, temporal-causal reasoning, adaptive search, cross-IA continuity, epistemic calibration
CANONICALITY=Proposed addition to the existing continuity/memory protocol; not a new memory store, brain, router, runtime component, or implementation authorization.

## 1. Purpose

Improve the search for solutions that repeatedly remain unresolved by treating communication, missing delivery, retrieval failures, context loss, and failed handoffs as observations in the same temporal-causal reasoning process. The goal is to find the first broken causal edge, reduce uncertainty with the smallest discriminating action, and turn verified outcomes into reusable method knowledge.

This extends the existing temporal-causal synthesis method. It does not claim that a complete space-time algorithm or runtime metacognitive loop has been implemented.

## 2. Core loop

`OBJECTIVE + CURRENT CONTEXT
→ SPACE/TIME/IDENTITY ANCHOR
→ CURRENT VERIFIED TRUTH + EVIDENCE PROVENANCE
→ ROUTE/COMMUNICATION GRAPH
→ HYPOTHESES + UNCERTAINTY
→ FIRST OPEN/BROKEN CAUSAL EDGE
→ CAPABILITY-FIT ACTOR + AUTHORIZED DISCRIMINATING ACTION
→ OBSERVED RESULT
→ INDEPENDENT VERIFICATION
→ EXPECTED-vs-ACTUAL DELTA
→ RECONCILIATION
→ REUSABLE KNOWLEDGE/METHOD/ROUTING DELTA
→ PERSISTENCE
→ LATER DECISION REUSE
→ OUTCOME/CALIBRATION CHECK
→ RECURSE`

A message being drafted, a path being configured, a file being persisted, or an agent reporting success is not evidence that the end-to-end route worked. Keep the evidence stages distinct:
`DEFINED → WIRED → INVOKED → OBSERVED → VERIFIED → CAUSALLY ATTRIBUTED → REUSED`.
Only claim the strongest stage supported by evidence.

## 3. Space-time representation

For every material attempt, preserve enough provenance to reconstruct:

- **Space/identity:** project, source repository, branch and commit, workspace/runtime when known, destination, tool/agent, session/task/attempt, permissions, and the evidence domain being inspected.
- **Time/order:** observation timestamp and source, prior state, dispatch/request order, later events, and causal predecessors. A timestamp alone does not establish causality.
- **Epistemic state:** declared, observed, inferred, hypothesized, effective, or unknown; confidence and what would falsify the claim.
- **Goal relation:** objective, success condition, active blocker/frontier, and why this action is the next useful step.

Never conflate public GitHub state, a local checkout, a dirty worktree, a report supplied by an owner/reviewer, a tool response, and runtime behavior. Likewise, absence from one search surface is not global nonexistence.

## 4. Communication failures are evidence

When an expected communication or artifact path fails, record the failure itself as a system observation. Do not require the user to successfully relay another prompt before diagnosing a route that can be checked using available authorized tools.

Reconstruct the route at the relevant boundaries, for example:
`intent → target identity → capability/access check → request accepted → dispatch created → context/input delivered → actor/tool invoked → operation performed → result returned → origin/correlation verified → result consumed → future decision affected`.

At each edge, classify the strongest evidence actually available. Locate the first unresolved edge and retain downstream consequences that may reveal a broader failure class. Do not report a downstream success merely because an upstream component or adapter exists.

Classify failures separately, including:
- wrong or ambiguous resource/branch/commit/session identity;
- search-surface or retrieval-scope limitation;
- missing bytes/attachment/context at the receiving actor;
- missing capability or unavailable tool;
- authorization/governance denial;
- transport, invocation, timeout, or return-path failure;
- missing correlation/provenance or incomplete validation;
- result persisted but not consumed by a later decision;
- result consumed but no independently demonstrated beneficial change.

These are hypotheses until supported by observations. Use `NOT_FOUND` only for the bounded search performed; use `UNRESOLVED` when the evidence does not decide the claim; use `UNPROVEN` for capability/runtime claims lacking proof.

## 5. Adaptive search instead of repetitive attempts

For each unresolved objective:

1. Restate the desired outcome and current canonical truth without reopening decisions already settled.
2. Enumerate the materially different hypotheses, including source/identity mistakes, stale local references, access boundaries, missing transfer, capability mismatch, correlation loss, and consumer/reuse failure where relevant.
3. Identify the first causal edge whose state would discriminate those hypotheses.
4. Select the smallest authorized read-only check with the highest expected information gain, matched to an actor/tool that can actually observe that edge.
5. Execute only within the authorized scope; capture source identity, exact observation, limitations, and the next condition.
6. Reconcile expected versus actual. Retry only if the evidence, hypothesis, scope, or available capability changes—not as a blind repetition.
7. Preserve negative knowledge with its search boundary, sources/ref/commit, exact result, excluded claims, expiry/reopen condition, and next discriminating action.

Prefer connector/tool-assisted retrieval over asking the Owner to manually investigate or relay content when the tool route is available and authorized. Do not imply that one actor's attachment automatically exists in another actor's conversation; use an explicit, verified handoff path. Never bypass an access or governance denial to improve information gain.

## 6. Metacognitive checks

Before accepting a diagnosis, explicitly test for:
- **confirmation bias:** what evidence would contradict the preferred explanation?
- **premature closure:** are alternative causes still observationally equivalent?
- **scope error:** was the right repository, branch, workspace, session, date, or evidence domain checked?
- **recency/continuity drift:** is an old state being presented as current, or a closed decision being reopened without new evidence?
- **causal overclaim:** does the evidence show only existence/wiring/persistence, or actual invocation, effect, verification, and reuse?
- **count/schema inconsistency:** do row counts, totals, unique IDs, column meanings, hashes, and claims reconcile?
- **reviewer disagreement:** is it substantive evidence, a source/scope discrepancy, or an arithmetic/methodology error?
- **method failure:** has the same unsuccessful search or unsupported inference recurred, and what protocol change prevents recurrence?

State uncertainty and falsifiers; do not manufacture certainty by assigning precise numbers to uncalibrated confidence.

## 7. Learning and closure contract

A communication/search episode is not a learning event merely because its report was saved. A reusable method delta should contain:

- objective and scope;
- source/identity/time anchors;
- evidence and provenance labels;
- initial hypothesis/frontier and uncertainty;
- authorized discriminating action;
- observed result and independent verification;
- expected-versus-actual delta;
- reconciled conclusion and residual unknowns;
- specific method/routing rule changed;
- later decision or test expected to reuse the rule;
- outcome check that can confirm or falsify the change.

Use the existing canonical memory and continuity organs. Do not create another store solely to hold this method. Learning remains `PROPOSED/UNPROVEN` until a later traced decision demonstrates correct reuse and an attributable improvement, or explicitly records that improvement was not demonstrated.

## 8. Minimal acceptance criteria for future proof

This method can be considered operationally demonstrated for a bounded case only when evidence shows:
1. a real unresolved communication/search objective and anchored initial state;
2. at least two plausible hypotheses with a discriminating difference;
3. a permitted action selected from that difference rather than repetitive trial-and-error;
4. an observed result with independently checkable provenance;
5. reconciliation that identifies the correct causal edge without overclaiming;
6. a persisted method delta in canonical continuity;
7. a later decision that retrieves and applies the delta;
8. a before/after outcome comparison or explicit finding that improvement remains unproven.

This is a bounded acceptance criterion, not blanket proof of full cognitive symbiosis or universal autonomous learning.

## 9. Application to the active IABV/R10 context

A prior local `git show`/search failure must not be promoted into a claim that a remote commit or artifact does not exist. Check the exact canonical repository and ref, then inspect the remote source through an authorized connector before assigning `NOT_FOUND`. Conversely, remote source availability does not prove ZIP byte hashes, local worktree state, or runtime behavior.

The recent R10 reconciliation is an active example of the method: remote source existence was confirmed; byte hashes remained unverified; T205 was re-opened because barrier scope was underspecified; and v0.7.5 remains blocked. This document does not decide or repair R10 contract rows.

## 10. Governance and writeback

- `GOVERNANCE = KEEP_BLOCKED`.
- Documentary method specification only. This commit does not authorize implementation, code edits, tests, builds, runtime, dispatcher activation, Packages B–E, M0A, or `data/`/SQLite access.
- Do not create R10 v0.7.5 from this method delta or treat it as an input replacement for the missing original Claude report.
- Preserve PR #467 as Draft/open/unmerged and preserve `handoff/r10-v074-review-20261017`.
- Canonical writeback must link this record from the memory protocol and front doors, then verify the new commit and all updated links.

## 11. Canonical foundations

- [Metacognitive Deduction / Temporal-Causal Synthesis](METACOGNITIVE-DEDUCTION-2026-09-12.md)
- [Cross-Chat Symbiosis / Causal-Learning Reconciliation](CHAT-ARCH-2026-09-17-004-cross-chat-symbiosis-reconciliation.md)
- [Memory Operating Protocol](MEMORY-OPERATING-PROTOCOL.md)
