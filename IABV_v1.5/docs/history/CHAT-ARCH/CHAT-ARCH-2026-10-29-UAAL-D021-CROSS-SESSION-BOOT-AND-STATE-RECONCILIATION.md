# UAAL-D021 — Cross-session boot, state reconciliation and causal reuse

**Date:** 2026-10-29  
**Parent:** UAAL-D019 — Space-Time Anti-Loop and First-Open Causal Frontier; UAAL-D020 — Verified Progress Utility and Strategy Switch  
**Scope:** shared external memory across participating ChatGPT/Codex/other AI sessions  
**Status:** `DOCUMENTED_METHOD; AUTOMATIC_ENFORCEMENT_NOT_PROVEN; LATER_CAUSAL_REUSE_VERIFIED_FOR_TWO_NON_IDENTICAL_TASKS_WITHIN_CONTINUING_SESSION; INDEPENDENT_SESSION_EXPLICIT_RETRIEVAL_AND_METHOD_APPLICATION_VERIFIED_FOR_ONE_BOUNDED_TASK; AUTOMATIC_CROSS_SESSION_BOOT_NOT_PROVEN; GENERALIZATION_NOT_TESTED`

**Owner-input control status (2026-10-31):** `OWNER_KNOWN_INPUT_LEDGER_AND_NO_REPEAT_GATE=DOCUMENTED_AND_CANONICALLY_ADOPTED`; `POST_ADOPTION_FORMAL_INDEPENDENT_CAUSAL_REUSE=PENDING`; `POST_ADOPTION_APPLICATION=ONE_PARTIAL_REPORTED_WITH_LIMITATIONS`; `CAUSAL_ATTRIBUTION=NOT_ISOLATED`. The [post-adoption Owner-input reuse validation receipt](./CHAT-ARCH-2026-10-31-UAAL-D021-OWNER-INPUT-REUSE-VALIDATION-RECEIPT.md) records one separately reported application and its limitations. The earlier D021 reuse receipts predate §6B.1 and must not be misrepresented as tests of this later addition.

**Reuse evidence boundary:** the first two bounded receipts document applications within the prior continuing conversation. The [independent second-session receipt](./CHAT-ARCH-2026-10-29-UAAL-D021-SECOND-SESSION-REUSE-RECEIPT.md) records one separately opened ChatGPT session that explicitly retrieved the canonical sources and applied the method. This verifies the explicit retrieval path for that bounded task only. Automatic delivery/boot into arbitrary future chats remains `NOT_PROVEN`, generalization remains `NOT_TESTED`, and this result does not authorize technical bootstrap.

The post-adoption §6B.1 receipt is deliberately classified as a limited reported application, not causal reuse: the task prompt explicitly instructed the session to apply the rule and the session disclosed pre-existing conversation/memory context. Keep automatic boot, isolated causal attribution and generalization unproven.

**Coordinator clarification (2026-10-31):** the evidence is not “zero application.” One later session's application was separately reported and its GitHub revision/canonical state were corroborated by the coordinator, but the participant's internal retrieval/application trace was not independently available and the prompt itself directed use of §6B.1 while pre-existing context was present. Therefore record `ONE_PARTIAL_REPORTED_WITH_LIMITATIONS`; do not promote it to causal reuse, independent attribution, automatic boot, runtime enforcement or generalization. The no-repeat control remains adopted and must still be applied from canonical history before Owner-dependent questions.

**M1A gate contract (scope-preserving clarification):** G1 requires an authenticated Owner/governance principal and mandate, an independent trust anchor, the issuer-to-reader/server trust chain, and Owner-to-Windows-principal binding. G2 requires an authorized catalogue publisher, producer-class policy, integrity/version lifecycle and authoritative revocation. G3 remains the versioned server-side operation-to-target resolver bound to real registered call sites. Separately, the integrated read path must prove that the authorization decision and consumed native handle refer to the same identity-bound object. These criteria do not close G4–G8 or authorize implementation, protected reads, tests, build or runtime.

**Dual-track scope:** the current wait is limited to the M1A/G1 authority and root-provenance dependency. It is not a project-wide IABV stop. Apply D019's independent-progress lane only when a current Owner objective and its own authorization support a concrete task; no automatic follow-on is created.

**Pre-search context baseline (2026-10-29):** [the baseline receipt](./CHAT-ARCH-2026-10-29-UAAL-D021-PRE-SEARCH-CONTEXT-BASELINE-RECEIPT.md) records a supplied transcript whose author reports IABV-specific context before new searches in that conversation. The underlying initial-context payload and its source attribution were not independently available. Classify this as `PRE_SEARCH_CONTEXT_AVAILABILITY=LIMITED_EVIDENCE_FROM_SUBMITTED_TRANSCRIPT; SOURCE_PROVENANCE=UNKNOWN`; it does not prove that GitHub memory loaded automatically. Keep `AUTOMATIC_CROSS_SESSION_BOOT=NOT_PROVEN` and `GENERALIZATION=NOT_TESTED`.

**First later-task application:** [UAAL-D021 first reuse receipt](./CHAT-ARCH-2026-10-29-UAAL-D021-FIRST-LATER-TASK-REUSE-RECEIPT.md). This is one bounded demonstration, not proof of universal automatic boot or repeatability.  
**Baseline observed while preparing this revision:** `main=79ab8c50eaa7518120d5ebed9db4747d395a21cb`

## 1. Diagnosis: the algorithm existed, but its control loop did not reliably execute

This is not a case where the project needed another abstract principle. D019 already describes the anti-loop and first-open causal frontier; D020 adds utility ranking, a strategy reset after two preparation-only steps, and a material causal delta before a third attempt. The observed failure is between the written policy and the session startup/action-control path:

1. **No guaranteed activation.** A saved GitHub document does not automatically enter a new chat's context. Each participating session must fetch it through an actually available connector/tool or receive a short handoff. A link, commit, previous session or the phrase “shared metacognition” is not proof of retrieval or application.
2. **The route contradicted live reality.** At the baseline above, the top of `CURRENT-STATE.md` and four continuity front doors still said M1B was local/unpublished, while live PR #555 was already open, draft and contained the candidate source. The protocol required live reconciliation, but the operational entry point itself supplied stale instructions. That is a control-plane defect.
3. **Historical state was copied as current state.** Large, append-heavy files made time-specific handoffs look like active directives. Repeating the same block across front doors multiplied drift rather than providing continuity.
4. **The canonical record was hard to fetch consistently.** `CURRENT-STATE.md` is over one megabyte; the normal file-content call returned an empty body in this audit, while a blob-by-SHA retrieval returned the bytes. Readers must distinguish “file exists”, “file content was actually retrieved”, and “exact revision was reconciled”.
5. **The success condition stopped at documentation.** Method retrieval and a better current record do not prove automatic enforcement, model-weight learning, a working coordinator runtime or causal reuse in a later task. The protocol says this, but there was no compact session receipt that made these statuses unavoidable.

These observations are evidence of a continuity/control-plane defect, not evidence that the model is continuously conscious or that all sessions share a single internal state.

## 2. Design objective

Create a low-friction, falsifiable loop in which each material session can reconstruct the minimum correct present state, continue from prior terminal evidence and choose one useful authorized action without asking the Owner to repeat settled facts. Do not create a second router, memory store, coordinator or model. `CURRENT-STATE.md` remains the sole task router; D019/D020/D021 define its activation and selection method. Front doors should point to the route, not copy a second evolving route.

## 3. Deterministic boot protocol

Run this at the start of every new session and before any material state transition:

```text
BOOT
  0. FETCH live refs/heads/main; record observed SHA and timestamp.
  1. FETCH CURRENT-STATE active header from that exact revision.
  2. CHECK whether the content was actually returned; if not, fetch by blob SHA.
  3. BIND current Owner objective, acceptance condition, scope, constraints and authority.
  4. RETRIEVE only relevant D019/D020/D021 + owning task receipt + live PR/commit metadata.
  5. RECONCILE current facts against live refs; mark stale/conflicted claims; never average conflicts.
  6. BUILD minimal evidence/dependency graph and fingerprint the last terminal attempt.
  7. LOCATE first open causal edge and list admissible actions after hard authorization filters.
  8. SELECT one target-closing or decision-discriminating action; otherwise record the exact blocker.
  9. DECLARE expected observable, stop condition, and how each plausible result changes the route.
 10. ACT, OBSERVE, CLASSIFY stage, VERIFY exact input/revision/result.
 11. UPDATE the owning record; FETCH BACK exact bytes/revision; reconcile route.
 12. On a later non-identical task, test whether the method was causally reused.
```

### Required evidence labels

Keep these labels intact and apply them to claims, not just sections:

- `VERIFIED`: directly confirmed from the relevant live source or independently fetched artifact.
- `OWNER_REPORTED`: reported by the Owner/Codex but not independently reproduced in this session.
- `INFERENCE`: follows from stated facts but is not directly observed.
- `HYPOTHESIS`: testable explanation with a discriminating expected observable.
- `UNKNOWN`: available evidence does not resolve it.
- `NOT_RUN`: action not executed.
- `CONFLICTED` / `STALE`: source claims disagree or an old time-specific status was superseded.
- `NOT_ESTABLISHED`: a gate's acceptance criteria have not been proven.

A negative result from one route is scoped to that route and its preconditions. “Supported route not found” does not prove that an asset does not exist.

## 4. Causal anti-loop and utility selector

Before an action, bind its fingerprint:

```text
(objective + acceptance,
 target and exact revision/digest,
 operation and material inputs,
 actor/route,
 authority and hard preconditions,
 relevant environment,
 expected observable,
 stop/switch condition)
```

Treat a proposal as `SAME_EXPERIMENT` unless a relevant precondition, evidence source, authorization, operation or falsifiable hypothesis materially changes. New chat IDs, task names, timestamps, wording, branches or elapsed time alone are not causal deltas.

After two consecutive `PREPARATION_ONLY` actions on the same objective, reset strategy before a third. Before a third attempt at the same causal edge, record the material delta and explain the expected new evidence. Prompts and documents count as progress only if they close a dependency, reduce decision-changing uncertainty, prove a necessary prerequisite or preserve safety with concrete blocker evidence.

Selection is lexicographic:
1. Hard authorization/privacy/safety/precondition filters (not scored; a hard fail excludes the action).
2. Verified closure of the target dependency edge.
3. Decision-changing information gain.
4. A proven necessary prerequisite when no shorter route exists.
5. Reversibility, elapsed cost and reduction in Owner burden.

Use one bounded action then reconcile. “Wait” is permissible only after comparing current authorized tools/actions and naming the exact missing external input. A terminal failure closes only the same operation under the same route/preconditions; it is not a project-wide stop.

## 5. State machine for cross-session continuity

```text
MEMORY_NOT_RETRIEVED
  -> MEMORY_RETRIEVED
  -> METHOD_ACTIVATED
  -> METHOD_APPLIED
  -> OUTCOME_VERIFIED
  -> LATER_CAUSAL_REUSE_VERIFIED
```

Evidence requirements:
- `MEMORY_RETRIEVED`: exact source path plus live ref/commit/blob SHA and non-empty content received.
- `METHOD_ACTIVATED`: identify which rule applies to the current objective and which prior terminal result matters.
- `METHOD_APPLIED`: point to a decision the rule changed (e.g., reject stale M1B state, do not reclone, verify PR HEAD).
- `OUTCOME_VERIFIED`: show evidence that the chosen action produced the expected target-correlated state transition; documentation fetch-back alone is not product-runtime proof.
- `LATER_CAUSAL_REUSE_VERIFIED`: on a later, non-identical task, show that the method altered action selection and avoided repeating a known loop. This cannot be claimed at initial adoption.

External GitHub memory is durable storage only for records actually published there. It does not alter model weights, guarantee retrieval in all clients, synchronize hidden chat context, or provide continuous shared subjective consciousness. The practical objective is reliable state reconstruction and action continuity, not a metaphysical claim.

## 6. Minimal session receipt

Every material task should leave one compact receipt in the owning route or task record:

```text
SESSION_RECEIPT:
  observed_main_sha=
  route_blob_sha=
  objective_and_acceptance=
  activated_rules=
  prior_terminal_fingerprint=
  first_open_causal_edge=
  selected_action_and_authority=
  expected_observable_and_stop_condition=
  action_stage=
  result_evidence_and_provenance=
  acceptance_status=
  owning_record_updated=
  fetchback_revision=
  method_application=
  later_causal_reuse=NOT_TESTED|VERIFIED
```

Do not append a full duplicate history on every turn. Update the owning entry in place, retain dated evidence receipts, and keep the active route at the top. Front doors should only contain the short activation recipe and a link to `CURRENT-STATE.md` and this contract.

## 6A. Objective-conditioned perception and task-local world model

Memory retrieval is an input to perception, not a substitute for building a model of the current task. Before a material action or cross-AI handoff, construct the smallest source-grounded model that can distinguish the leading explanations for the current objective. This is a provisional operational model, not a complete digital twin or a claim of subjective consciousness.

The model must bind:

1. **Objective and acceptance oracle:** the requested observable transition, success condition and failure condition.
2. **Source identity and time:** exact repository/ref/commit/blob or object identity; event time, observation time, record time and currentness.
3. **Effective causal path:** producer/source → transformation or contract → consumer/decision → effective operation → observed outcome, limited to the path capable of changing the objective.
4. **Authority and environment:** applicable permissions, prerequisites, exact scope, tool/actor capability, resources and prohibited effects.
5. **Epistemic separation:** directly verified facts, Owner/actor reports, inferences, competing hypotheses, unknowns and actions not run.
6. **Discriminating evidence:** for each material hypothesis, its predicted distinguishing observation and falsifier.

Do not expand into a broad repository inventory if a smaller observation can decide the next action. A retrieved document proves the bytes at that reference, not that every assertion in it is true or that a later consumer loaded it. A static source path does not prove runtime execution. An abnormal empty or truncated response is `RETRIEVAL_FAILED`, not evidence of an empty or nonexistent source.

For material tasks, use this compact representation:

```text
WORLD_MODEL_SNAPSHOT = {
  objective_and_acceptance_oracle,
  observed_at_and_currentness,
  exact_source_refs_and_artifact_identity,
  verified_observations_and_owner_reports,
  inferences_and_competing_hypotheses,
  predicted_observations_and_falsifiers,
  unknowns_and_not_run_actions,
  scope_authority_environment_and_no_go_constraints,
  producer_transformation_consumer_operation_chain,
  first_open_causal_or_evidential_edge,
  selected_action_and_actor_fit_reason,
  expected_observation_and_stop_or_switch_condition,
  actual_result_stage_and_model_delta,
  writeback_ref_and_fetchback_status,
  later_causal_reuse_status
}
```

This snapshot does not become another router: `CURRENT-STATE.md` remains the sole owner of `ACTIVE_TASK` and `NEXT_ACTION`. Do not duplicate those fields as competing instructions. Update the model only when a source-bound observation or explicitly classified report changes it; retain unresolved contradictions rather than blending them into a confident narrative.
### 6A.1 Bounded impact projection across affected tasks and artifacts

The task-local world model must account for material effects beyond the immediate file or action when the proposed change touches a shared method, entrypoint, contract, branch, PR, route, permission or published state. Use a bounded impact projection rather than assuming the immediate task is isolated, but do not turn every action into a full-repository or all-project inventory.

Before a consequential shared-surface change, construct:

```text
IMPACT_PROJECTION = {
  owning_project_and_current_objective,
  parent_objective_and_acceptance,
  target_task_and_exact_artifact_refs,
  proposed_action_and_expected_delta,
  direct_dependents_and_evidence_edges,
  downstream_consumers_whose_acceptance_may_change,
  shared_paths_contracts_and_entrypoints,
  affected_open_candidates_with_exact_refs_and_heads,
  project_specific_authority_and_memory_boundaries,
  predicted_effects_of_apply_defer_reject_or_failure,
  invariants_to_preserve,
  overlap_and_merge_simulation_status,
  post_action_revalidation_and_stop_condition
}
```

Apply this bounded traversal:

1. **R0 — target:** identify the current Owner objective, the owning project's canonical state, the active task, its acceptance oracle and the exact object/branch/file/contract being changed. `CURRENT-STATE.md` is not a router for other projects.
2. **R1 — direct impact:** identify only consumers or candidates connected by verifiable evidence: a shared changed path, imported/referenced contract, entrypoint, schema, route/gate, or explicit dependency. For PR/branch operations, inspect open candidates that share changed paths or interfaces; bind their actual refs and HEADs rather than trusting branch names or summaries.
3. **R2 — consequential downstream impact:** follow an R1 edge only when the proposed state change can alter another task's acceptance, prerequisite, authorization, compatibility or next action. Stop when further traversal cannot materially change the current decision. Record unsupported or inaccessible edges as `UNKNOWN`; do not invent dependencies.
4. **Project isolation:** a shared method may transfer across projects, but project facts, artifacts, permissions, private state and canonical routers do not. A cross-project impact edge must identify the shared method/contract and the consuming project without importing its private state into the source project.
5. **Candidate integration:** where branches overlap, compare exact base/head refs and changed-path intersections. Use a merge simulation when available, but distinguish textual conflict/mergeability from semantic preservation. A clean merge simulation is not proof that required invariants survived. For conflicts, name the resolution order, exact invariant, resolved paths and post-resolution diff; if these cannot be verified, keep integration `UNKNOWN` and do not merge.
6. **Outcome projection:** consider the material success, failure, rejection and blocked branches of the proposed action. State which downstream edges would change, remain blocked or need revalidation. Do not project only the happy path.
7. **Post-action update and artifact integrity:** compare the observed result with the projection, update only affected task/objective nodes and their owning records, and preserve links to the evidence. For every modified structured document or contract, re-fetch the exact final blob and verify both byte identity and semantic structure: balanced Markdown fences, intact headings/paragraph boundaries, all declared receipt/schema fields still present, every field referenced by later prose defined, and no accidental deletion or concatenation at edit boundaries. For source/schema changes, use the applicable parser/schema checks when authorized; do not claim tests when only static checks ran. Do not rewrite unrelated project state or trigger automatic follow-on work.

Use evidence classes on each material edge: `VERIFIED_SOURCE_LINK`, `ACTOR_REPORTED`, `INFERENCE` or `UNKNOWN`. Shared filenames alone can establish a review/integration candidate, not semantic dependency or correctness. A stale Control Master snapshot is not a live objective/priority edge; record its freshness and use only a source-bound live signal when an authorized read surface exists.

### Minimum evidence for a non-vacuous impact projection

`UNKNOWN` is an evidence classification, not a substitute for performing the bounded discovery required by the task. Before treating the impact gate as complete for a consequential shared-surface action, record an `IMPACT_DISCOVERY_RECEIPT`:

```text
IMPACT_DISCOVERY_RECEIPT = {
  target_base_head_and_changed_paths,
  direct_source_or_contract_refs_inspected,
  bounded_reference_searches_and_scope,
  open_related_candidates_checked_when_PR_OR_BRANCH_IS_TOUCHED,
  results_and_observation_time_for_each_attempt,
  identified_dependents_and_evidence_links,
  unavailable_or_denied_sources_and_exact_reason,
  unresolved_edges_and_why_they_remain_unknown,
  R2_FOLLOWED_OR_STOPPED_WITH_CAUSAL_REASON
}
```

Minimum bounded attempt:
- Inspect the exact target diff and relevant owning contract/entrypoint.
- For each shared path or contract, make one bounded check for direct consumers using the available authorized repository search/reference mechanism, or record that this mechanism is unavailable/denied with evidence.
- When a PR/branch is touched, inspect open PRs sharing changed paths or an explicit interface using available PR metadata/search; if no such query is available, record the exact limitation.
- Follow R2 only where an R1 dependency can materially affect another task's acceptance, prerequisite, authority, compatibility or next action.

A generic statement such as "not inspected", "insufficient context" or "unknown; stop" without the bounded attempts and source/capability reason is `IMPACT_GATE=INCOMPLETE`, not acceptance. If an essential direct-dependency source is unavailable or denied, record `CAPABILITY_UNAVAILABLE` or `ACCESS_DENIED` and stop the consequential shared-surface mutation until that dependency is bounded. Do not convert missing evidence into `EMPTY` or `NO_DEPENDENTS`.

For IABV, re-read the live canonical `CURRENT-STATE.md` and carry forward its currently applicable Option D, M1A/G1-G3 and other authorization/fail-closed constraints when relevant to the target. This section does not hard-code old gate values, change those gates, or authorize an action; only the live canonical route does. For other projects, use their own canonical state and permissions.

**Acceptance criterion:** before a shared-surface action, the coordinator must complete and record the minimum bounded attempts above, name evidence-backed direct dependents and consequential downstream consumers, preserve project-specific boundaries and applicable gates, identify integration risks, and define exact post-action checks. Any remaining `UNKNOWN` must name the exact attempted sources, missing discriminator and stop consequence. This is a complete decision-relevant impact envelope, not a claim of omniscience or a requirement to scan the entire repository. It does not create a second portfolio/router, override `CURRENT-STATE.md`, promote a Control Master signal to authority, or authorize any blocked action.


## 6B. Adjudicate incoming results before preparing another handoff

A returned result from Codex, another AI, a tool or a reviewer is evidence to be adjudicated, not an instruction to continue blindly. Before any new cross-AI handoff:

1. Rebind the receipt to the original task contract, acceptance oracle, current live route, exact target HEAD/ref, exact file paths and artifact identities. A verdict for HEAD A stays bound to A; if the live target is HEAD B, inspect the delta or obtain a bounded review of the changed scope.
2. Split the receipt into direct observations, actor-reported execution, inference, hypotheses, unknowns and not-run actions. Preserve the source and provenance for every material claim.
3. Compare the reported outcome with the original acceptance oracle and the expected distinguishing observation. Do not silently substitute a more convenient success criterion after seeing the result.
4. Adjudicate each dependency edge independently as `CLOSED_AT_REVIEW_SCOPE`, `PARTIAL`, `OPEN`, `BLOCKED` or `UNKNOWN`. Static closure, synthetic tests, native execution, exact-HEAD tests, authenticated fetch-back, authority acceptance and operational activation are different stages.
5. Update the task-local world model with what changed, what did not, contradictions, residual unknowns and the first remaining open edge.
6. Only then select one authorized next action from that earliest open edge. If evidence is missing, retrieve or request only the specific missing item; do not restart the whole review or generate another broad handoff.
7. Keep branch persistence distinct from canonical adoption. A draft PR or branch fetch-back is not a change to `main`; adoption requires permitted integration and exact fetch-back from live `main`.

| Returned condition | Required route update | Prohibited conclusion |
|---|---|---|
| Review says PASS on HEAD A, but the candidate is HEAD B | Bind PASS to A; inspect or review only the B delta | Claim B is reviewed without checking it |
| Static finding closed; tests are reported from a reduced harness | Close only the static finding; preserve test provenance and harness limits | Claim full-suite, native-runtime or production acceptance |
| Source retrieval returns empty, but the exact blob is retrievable | Record the transport failure and use the verified blob bytes | Treat the source as empty or ask the Owner to recreate the record |
| Receipt omits a digest, target revision or test command/output needed for acceptance | Mark that claim `UNKNOWN` and retrieve only the missing evidence | Infer success from a headline or repeat the entire task |
| A draft branch contains an apparently useful method, while live `main` has moved | Compare the branch with current `main`; reuse only the compatible bounded delta | Merge a stale broad branch or create a duplicate method without comparison |
| A technical route is blocked, but a separate documentation task is explicitly authorized | Keep the technical gate closed and perform only that bounded documentation task | Treat documentation progress as technical authorization |

**Pass criterion:** all applicable checks have been adjudicated, or each unsatisfied check is explicitly `UNKNOWN`/`NOT_RUN` with the exact missing evidence and a justified stop condition. This is a reasoning-method acceptance check; it does not prove automatic enforcement, delivery to another chat or model-weight learning.

### 6B.1. Mandatory Owner-known-input ledger and no-repeat gate (2026-10-31)

Before asking the Owner to identify, confirm, configure or repeat any mechanism, the coordinator must first recover the relevant Owner-input history from the live project sources and current conversation context. A question is not justified merely because the latest task receipt omitted a fact that an earlier canonical receipt already recorded.

For every material Owner-dependent decision, construct a compact `OWNER_INPUT_REUSE_LEDGER` with:
- the exact fact or decision already supplied;
- its source reference and recorded date;
- evidence class (`OWNER_REPORTED`, `INDEPENDENTLY_VERIFIED`, `INFERENCE`, or `UNKNOWN`);
- the scope it applies to;
- any explicit `DO_NOT_REPEAT` instruction;
- the exact unresolved claim that the fact does not establish.

Apply these rules:

1. **Reuse known input as an existing candidate.** An Owner-reported setup is valid project context and must be evaluated; lack of independent verification does not erase it or justify asking the Owner to repeat it.
2. **Do not conflate functions.** Separate human identity/MFA, a conversational or mobile approval interface, an IABV runtime issuer/trust anchor, Owner mandate, machine principal, exact host/server binding, and operation-level authorization. A mechanism may satisfy one layer and not another.
3. **Investigate before asking.** Compare known candidates against current source, design and gate evidence. Ask only for a genuinely missing fact that cannot be recovered from project history and whose answer would change the next authorized action. Never ask the Owner to invent or design the technical solution.
4. **Close the input question when answered.** When the Owner says no additional mechanism is identified, record `OWNER_INPUT_RECONCILED=NO_ADDITIONAL_MECHANISM_IDENTIFIED`. Do not rephrase the same question. Keep technical gates blocked where evidence is insufficient; do not infer that uninspected assets do not exist.
5. **Use a material-delta rule.** Reopen the same question or review only after new independent evidence, a changed precondition, or an explicitly authorized new scope. Do not repeat an unchanged census, Entra setup, mobile-authenticator enrollment, or broad feasibility review.

#### Owner-facing action planning gate — D019 §9E / D020 §9 (2026-11-02 proposal)

The `OWNER_INPUT_REUSE_LEDGER` above is a mandatory input to, not a substitute for, the decision-complete `OWNER_ACTION_PACKET` defined by UAAL-D019 §9E and selected under UAAL-D020 §9. Before any material instruction that asks the Owner to use a device, application, account or private UI, the coordinator must first retrieve and reconcile the canonical route, reuse this ledger, inspect assistant-accessible sources/tools, classify the action and its actor, and apply the exact authorization/no-bootstrap boundary. For material IABV work, D021 §6D supplies the Control Master signal status only when an already-authorized read surface exists; a stale snapshot or unavailable runtime signal must be labelled and must not be fabricated into a live queue.

The packet is an internal planning/verification artifact, not an extra Owner form or a new authority source. Its useful result is presented as one consolidated safe sequence plus predictable outcome branches and stop conditions. Do not ask the Owner to transcribe visible screenshots, perform coordinator-side research, or report each predictable screen as a separate round-trip. Retain a pause when a genuinely unpredictable observation, separate high-impact confirmation or missing authorization controls the next action. If the canonical route does not authorize the exact mutation, stop before recommending it. If no Owner intervention is needed, proceed with authorized assistant-side work instead of manufacturing one.

This D021 cross-reference is a candidate amendment on the PR branch. Until adoption, the existing live-main D021 §6B.1 and D019/D020 remain authoritative; this proposal does not alter any technical gate, Option D or product permission.

#### Case-specific continuity facts already recorded

- The Owner reported an organizational Microsoft Entra directory, a dedicated `IABV Owner` account, Microsoft Authenticator enrollment and a successful sign-in verification. Classify this as `ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY`; `IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID`; `PLAUSIBLE_FOR_HUMAN_OWNER_AUTHENTICATION`; `NOT_YET_TRUSTED_BY_IABV`. **Do not repeat setup or ask whether this identity provider exists.**
- The existing record says that no IABV app registration, token verifier, role-to-mandate mapping or protected Owner-to-Windows / issuer-to-exact-server binding was established in the inspected main path. Successful MFA is not IABV runtime authorization and does not independently bind a production root selection.
- The Owner primarily uses the ChatGPT phone app; the 2026-10-26 approval protocol also records Codex Remote/mobile approval as a possible interface to the already-open local session when connected. Treat these as human interaction/approval channels, not as an established IABV issuer, runtime trust root, or proof that a response reached and was enforced by the exact protected process.
- A phone approval, QR code, displayed challenge or copied fingerprint is not independent proof of the target root when the value originates only from the target and no prior trusted binding exists.
- For the 2026-10-31 reconciliation, the Owner stated that no additional mechanism is identified beyond the phone authentication/approval app. The correct result is that the known Entra/Authenticator and mobile approval channels are already in memory, no additional independent root/issuer mechanism is identified, and the technical root-provenance gate remains open. This resolves the Owner-input question; it does not close G1 or prove that other uninspected authority assets are absent.

**Acceptance rule:** no further Owner question is permitted until the ledger shows that the proposed question is not answered by an existing source and identifies the precise new decision/evidence it would change.

### 6B.2. Independent-review context separation preflight

Apply this gate before dispatching or claiming an **independent**, **adversarial**, or **second-opinion** review of a material candidate, protocol, PR or technical decision. It prevents a reviewer from being asked to validate work using the same task-specific conclusions that shaped the work.

Context separation, source acquisition and source identity are separate requirements. Do not collapse them into one pass/fail label:

- The reviewer must be a distinct actor/session from the candidate author/editor. A fresh conversation in a separate provider/model context is preferred when the prior session has already discussed or shaped the candidate.
- Preferred source acquisition is reviewer-side retrieval of the exact pinned repository base, candidate HEAD, diff and acceptance criteria from the canonical source. Sharing the same canonical source revision is required and does not itself contaminate the review.
- When direct retrieval is unavailable, a coordinator-exported pinned diff or user-supplied source may support a bounded static assessment only when the supplied material's revision, paths and scope have adequate provenance. Record the indirect acquisition explicitly; never describe it as independent live retrieval.
- Generic safety policy, repository method definitions and the review rubric are allowed inputs. The candidate author's narrative, prior review verdicts, task-specific findings, implementation rationale, previous conversation transcript and review discussion must not be supplied before the reviewer completes its own source inspection.
- A PR description or handoff summary authored by the candidate author is not a substitute for the diff. For a blinded review, ignore its evaluative claims and derive the scope from the pinned source and changed-file list.

Before dispatch, build:

```text
REVIEW_CONTEXT_SEPARATION_RECEIPT = {
  REVIEW_TASK_ID,
  REVIEWER_ROLE_AND_PROVIDER,
  REVIEWER_SESSION_IS_NEW_FOR_THIS_REVIEW,
  REVIEW_CONTEXT_CONTINUITY: NEW_SEPARATE_SESSION | CONTINUED_SAME_CONVERSATION,
  CANDIDATE_SPECIFIC_PRIOR_CONTEXT_EXPOSED: YES | NO | UNKNOWN,
  SAME_CANDIDATE_METADATA_EXPOSED: NONE | PR_TITLE_BRANCH_SHA_CHANGED_PATHS_ONLY | NON_EVALUATIVE_COMMIT_SUBJECTS | AUTHOR_DESCRIPTION_OR_COMMIT_RATIONALE | MIXED | UNKNOWN,
  AUTHOR_EVALUATIVE_CLAIMS_EXPOSED: YES | NO | UNKNOWN,
  RELATED_CANDIDATE_CONTEXT_EXPOSED: NONE | METADATA_ONLY | FINDINGS_OR_RATIONALE | UNKNOWN,
  REVIEWER_AUTHORED_OR_EDITED_CANDIDATE,
  PRIOR_AUTHORING_TRANSCRIPT_EXPOSED,
  PRIOR_REVIEW_FINDINGS_EXPOSED,
  TASK_SPECIFIC_MEMORY_OR_PROJECT_CONTEXT_IMPORTED,
  ALLOWED_INPUTS_AND_SOURCE_REFS,
  PROHIBITED_INPUTS_CHECKED,
  BASE_SHA_AND_CANDIDATE_HEAD,
  CONTEXT_SEPARATION: PASS | LIMITED | BLOCKED,
  SOURCE_ACQUISITION_METHOD: INDEPENDENT_LIVE_RETRIEVAL | COORDINATOR_EXPORTED_PINNED_DIFF | USER_SUPPLIED_SOURCE | OTHER,
  SOURCE_IDENTITY_VERIFICATION: REVIEWER_VERIFIED | COORDINATOR_ATTESTED | USER_ATTESTED | UNVERIFIED,
  SOURCE_COVERAGE: FULL_BASE_HEAD_DIFF | PINNED_DIFF_WITH_HUNKS | PARTIAL_SOURCE | UNKNOWN,
  SOURCE_RETRIEVAL_STATUS: PASS | LIMITED | BLOCKED
}
```

Classify carefully:

1. `PASS`: the reviewer is not the author/editor; the review runs in a new, separate task context; and no prior candidate-specific analysis or verdict was exposed. Generic method/policy knowledge and the candidate's canonical source files remain permissible. Source acquisition is assessed separately below.

2. `LIMITED`: use this status for either of these non-blocking context limitations:
   - The session is new and no known prior findings were supplied, but some persistent memory/context provenance cannot be inspected.
   - The reviewer continues the same conversation/session for a **different, non-identical candidate/task**, did not author/edit the candidate under review, and no prior analysis, verdict, author rationale or candidate-specific finding about that exact candidate was exposed before source inspection. General project memory, canonical method knowledge, and discussion of another candidate do not by themselves establish contamination of this candidate.
   
   For the continued-conversation case, record `REVIEW_CONTEXT_CONTINUITY=CONTINUED_SAME_CONVERSATION` and `CANDIDATE_SPECIFIC_PRIOR_CONTEXT_EXPOSED=NO`. The review may proceed as a bounded independent assessment, but must not be described as a fresh, fully blinded session. If exposure cannot be established either way, use `CANDIDATE_SPECIFIC_PRIOR_CONTEXT_EXPOSED=UNKNOWN`, retain `LIMITED`, and explicitly limit any claim of blindness.

3. `BLOCKED`: the reviewer authored/edited the candidate; prior findings, author analysis or implementation rationale about the **same candidate** were exposed before its own source inspection; the same candidate was substantively discussed in the review conversation before the reviewer independently inspected its pinned source; or candidate-specific memory contamination is known. A continued conversation alone is not sufficient for `BLOCKED`; the decisive factor is exposure to material that can pre-judge the candidate being reviewed.

4. Source acquisition is classified independently:
   - `PASS`: the reviewer directly retrieves the exact pinned base, candidate HEAD and diff from the canonical repository and verifies their identities and scope.
   - `LIMITED`: the reviewer receives a coordinator-exported pinned diff, user-supplied source or other indirect copy with enough provenance to identify its claimed revision and scope, but cannot independently retrieve the live source or inspect all required base context. A bounded static assessment may proceed on the supplied material; mark every conclusion requiring omitted content `NOT_ASSESSED` and do not claim independent live retrieval.
   - `BLOCKED`: the candidate revision/source identity cannot be established, the supplied material is insufficient to identify the candidate under review, or no usable source is available. Stop before substantive review and report `SUBSTANTIVE_REVIEW=NOT_RUN`.
   
   Record the acquisition method, identity-verification actor/status and source coverage in the receipt fields above. A clean reviewer context can therefore be `CONTEXT_SEPARATION=PASS` while `SOURCE_RETRIEVAL_STATUS=LIMITED`; these are not contradictory.

5. Same-candidate metadata exposure must be classified by content, not merely by whether it came from GitHub:
   - `PR_TITLE_BRANCH_SHA_CHANGED_PATHS_ONLY` and `NON_EVALUATIVE_COMMIT_SUBJECTS` are `METADATA_ONLY`. If these are the only prior exposure and no candidate-specific findings/rationale were seen, classify context as `LIMITED`, not `BLOCKED`; record the exposure and do not call the review fully blinded.
   - A PR description, commit body, review comment or author note that contains design rationale, favorable/unfavorable evaluation, asserted findings, proposed fixes, risk interpretation or acceptance claims is `AUTHOR_DESCRIPTION_OR_COMMIT_RATIONALE` and `AUTHOR_EVALUATIVE_CLAIMS_EXPOSED=YES`. For a review advertised as blinded/adversarial, classify `BLOCKED` and use a reviewer context that has not received those claims. Do not re-label author-authored rationale as harmless metadata.
   - If only part of a description/message was seen, classify the actual exposed content. If the content cannot be reconstructed, use `UNKNOWN`; do not assume it was metadata-only. A transparently non-blinded supplemental review may still be useful, but it must not satisfy the blinded independent-review gate.

6. When reviewing multiple related PRs or candidates that share files/contracts, separate two phases:
   - `CANDIDATE_INTERNAL_REVIEW`: inspect this candidate's own exact base-to-HEAD diff and acceptance criteria before relying on another PR's conclusions.
   - `CROSS_CANDIDATE_INTEGRATION_REVIEW`: inspect live related PR refs, changed-path intersections, shared invariants and merge simulation after the standalone review, or label the phase as limited if related findings were already exposed.
   
   Record related-candidate exposure as `NONE`, `METADATA_ONLY`, `FINDINGS_OR_RATIONALE` or `UNKNOWN`. Do not use another PR's review verdict as proof that this candidate is correct or defective. A merge simulation is evidence of textual mergeability/conflict only; it does not prove semantic preservation. For every conflicted or overlapping path, record the chosen integration order, the invariant that must survive, the resolved result and the exact post-integration diff. If the same session performs both phases, preserve separate receipts and do not relabel the standalone review as fully blinded after integration findings have been disclosed.

When blocked, stop before substantive evaluation and return exactly:

```text
INDEPENDENT_REVIEW=BLOCKED_PRECONDITION
SUBSTANTIVE_REVIEW=NOT_RUN
REVIEW_DIMENSIONS=NOT_ASSESSED
MISSING_EVIDENCE=REVIEW_CONTEXT_SEPARATION
```

Do not label unexamined rubric dimensions `PARTIAL`, `PASS` or `FAIL`. Those statuses are valid only after the reviewer inspected the corresponding content. Apply the same rule to source-limited reviews: omitted base context is `NOT_ASSESSED`, not an inferred pass or failure. Do not ask the Owner to repeat the same review in the same contaminated context. Select a genuinely separate reviewer or report that no admissible independent-review route is presently available.

Finally, distinguish `INDEPENDENT_STATIC_REVIEW` from a formal GitHub approval by an authorized human/code owner. A separate AI context may provide an independent technical assessment; it does not become a formal approval or merge authorization.

## 6C. Distinct operating contexts and memory-scope isolation (Owner clarification; 2026-10-31)

The shared UAAL method is intended to help the Owner across different subjects and projects while preserving continuity between chats and participating AIs. This does not mean every project fact belongs in one undifferentiated memory, or that every deployment of IABV has the same capabilities.

The Owner's phrase "states of consciousness" may be used as a design metaphor. In this protocol it means **operational context/state**, not subjective consciousness, a continuously shared hidden mind, or model-weight learning. D021 §6A remains controlling: each task requires a source-grounded, objective-conditioned world model.

### 6C.1 Identify the operating context before reasoning or acting

Every material session/action must declare the actual context in which it is operating:

```text
OPERATING_CONTEXT =
  CLOUD_SHARED_COORDINATION
  | LOCAL_IABV_RUNTIME
  | CONTROLLED_CLOUD_LOCAL_HANDOFF

ACTOR_SESSION_ID=
PROJECT_ID=
TASK_ID=
MEMORY_SCOPE=
SOURCE_REVISION_OR_ARTIFACT=
OBSERVED_AT=
AVAILABLE_CAPABILITIES=
AUTHORITY_AND_NO_GO_SCOPE=
```

- **CLOUD_SHARED_COORDINATION** is the GitHub-backed developmental/method layer used by participating ChatGPT, Codex and other AI sessions. It coordinates objectives, retrieves versioned external memory, selects relevant methods/actors, adjudicates reports and prepares bounded handoffs. It may claim local machine, GPU, file, process, device or physical-world facts only when an actual connected tool/agent supplies a correlated observation. A cloud chat's access to GitHub is not access to the Owner's laptop.
- **AI session/agent** is a temporary participant in the cloud coordination process. Its hidden conversational context is not the shared memory. It must explicitly retrieve the relevant sources or receive a bounded package through a supported route; receipt and use must be evidenced separately.
- **LOCAL_IABV_RUNTIME** is the IABV program running in the Owner's laptop environment, potentially using local GPU/models, files, processes, tools and devices. Its real capabilities, observations, resource state and permissions must be established from that runtime and its current environment. A design, source path, cloud report or prior runtime snapshot does not establish current local execution.
- **CONTROLLED_CLOUD_LOCAL_HANDOFF** is the explicit boundary between the cloud coordination context and the local runtime. A task package, prompt or queued message is not proof of dispatch, receipt, execution, response or verified effect. Preserve correlation IDs, exact payload/digest, target revision, actor/runtime identity, authorization, timestamps, returned receipt and postcondition.

The cloud and local contexts are complementary but not interchangeable. The cloud layer can guide and coordinate the local IABV when the bridge is ready and governed; the local IABV can provide observations and execution receipts back to the cloud layer. Until each link is independently verified, describe it as a proposed or partial handoff, not an operational symbiosis.

### 6C.2 Separate memory by scope, not by creating competing brains

Classify each durable record into one owning scope:

| Scope | Contents | Owner / rule |
|---|---|---|
| `GLOBAL_CORE` | Reusable UAAL methods, evidence rules, safety invariants and cross-domain coordination lessons | Existing canonical method lineage; promote only through the learning gate in §6C.4 |
| `PORTFOLIO_POINTER` | Project identifiers, high-level status, priority and links to each project's owning state | Navigation only; never a second task router or source of technical permissions |
| `PROJECT` | That project's objectives, requirements, decisions, research, files, versions, risks and open dependencies | The project's own canonical folder/repository/private workspace |
| `TASK_EPISODE` | One bounded action, experiment, actor handoff, evidence receipt, outcome and next dependency | The task's owning project record |
| `SESSION` | Temporary discussion context and unsaved working notes | Non-canonical; consolidate material outcomes before the session is abandoned |
| `RUNTIME` | Time-sensitive host, GPU, process, model, device, local file and environment observations | Local runtime record with source, machine/runtime identity and freshness; never infer from cloud state |

Default rule: a fact remains in its narrowest valid scope. Project-specific discoveries do not become global rules merely because they are useful or interesting. Cross-project transfer may reuse a method without importing the source project's facts, artifacts, assumptions or permissions.

The portfolio pointer, where maintained, is a directory of project-owned records. It may show that a project is active, parked, blocked or awaiting input, but must not duplicate each project's full state. Each project has its own `PROJECT_ID`, owning state record and bounded active task. Multiple projects may remain open in the portfolio; within each project's foreground execution lane, keep one active bounded task and one next action. The Owner may reprioritize projects explicitly; otherwise, capture new ideas and triage them rather than allowing every new idea to displace the current task.

`CURRENT-STATE.md` remains the sole authority for IABV's own `ACTIVE_TASK`, `NEXT_ACTION`, technical gates and permissions. It is not the Owner's all-project portfolio, and this section does not create a replacement. Other projects must retain their own state and evidence. The IABV development route, a BURVE/farol task, a business task and a future local-runtime task must never overwrite one another's route.

### 6C.3 Space-Time identity: scope plus provenance plus temporal validity

For each material record, "space" means its owning scope and object identity; "time" means the sequence and validity of observations and decisions. Bind at least:

```text
PROJECT_ID
TASK_ID
ACTOR_SESSION_ID
OPERATING_CONTEXT
MEMORY_SCOPE
SOURCE_OBJECT_AND_REVISION_OR_DIGEST
EVENT_TIME=
OBSERVED_AT=
RECORDED_AT=
VERIFIED_AT=
SUPERSEDES_OR_CONFLICTS_WITH=
FRESHNESS_OR_VALIDITY=
```

Do not use a current laptop/GPU/process observation as a permanent fact. Do not use a project file from one version as evidence about another. Keep event time, observation time and record time distinct. Mark stale or foreign-context observations explicitly. A context transition requires a handoff receipt, not an assumption that two contexts share one clock, process state or hidden memory.

### 6C.4 Learning and promotion: preserve everything useful without contaminating the core

Use this staged path:

```text
RAW_OBSERVATION
  -> PROJECT_FACT_OR_DECISION
  -> LESSON_CANDIDATE
  -> NONIDENTICAL_CROSS_CONTEXT_OR_CROSS_DOMAIN_TRIAL
  -> SHARED_METHOD_ADOPTION
  -> LATER_CAUSAL_REUSE_VERIFIED
```

A candidate lesson must state its evidence/provenance, original scope, proposed transferable principle, conditions where it applies, counterexample/falsifier, decision it changed and observed outcome. Promote it to `GLOBAL_CORE` only when the abstraction is justified; retain the original project record and link it rather than copying its full history into the core. One successful case may supply provisional evidence, not universal validation. A write to a branch/PR is a proposal; canonical adoption requires permitted integration and exact fetch-back from live `main`.

### 6C.5 Standard chat/agent handoff envelope

**Operational copy-ready entry:** use the [UAAL New-Chat Boot and Handoff Kit](./CHAT-ARCH-2026-10-31-UAAL-NEW-CHAT-BOOT-AND-HANDOFF-KIT.md) for the universal startup prompt, project-chat assignment, role boundaries, receiver/sender obligations, return receipt and new-chat acceptance checklist. This kit operationalizes §6C.1–§6C.4; it does not create another router or memory, and it remains subordinate to the live `CURRENT-STATE.md` for IABV routing and to each other project's own canonical state source.

Every external-agent prompt or handoff must identify one **explicit recipient** before its task body. Do not use ambiguous dispatch language such as "send to Claude or another AI", "use the same reviewer", or "ask an agent". The sender must select the recipient from the task's required capability and the capabilities actually available, then state the provider, named agent/model or channel, role, session requirement, permitted input/source route, authorized operation scope, exclusions, expected return and stop condition.

Use this dispatch header at the top of every copy-ready external prompt:

```text
DISPATCH_HEADER = {
  TARGET_AI_PROVIDER_AND_AGENT,
  TARGET_MODEL_OR_CHANNEL,
  TARGET_PROJECT_AND_TASK_ID,
  TARGET_ROLE,
  TARGET_SESSION_MODE: NEW_SEPARATE | CONTINUED | EXISTING_EXECUTOR,
  CONTEXT_SEPARATION_REQUIREMENT,
  REQUIRED_SOURCE_ACCESS_AND_EXACT_REFS,
  AUTHORIZED_OPERATION_SCOPE,
  EXPLICIT_EXCLUSIONS,
  EXPECTED_RETURN_ARTIFACT_AND_RECEIPT,
  STOP_CONDITION
}
```

Recipient selection rules:
1. Select by the operation and capability required, not by habit or brand. An independent adversarial review needs a reviewer distinct from the author/editor and an admissible context under §6B.2. Source access and runner capability must be checked separately.
2. Name exactly one intended destination in the prompt header. If the preferred provider/account/channel has not been confirmed available, label it `PREFERRED_RECIPIENT; AVAILABILITY_UNCONFIRMED`; do not imply the handoff was sent or silently substitute another AI. Ask the Owner only for an irreducible routing decision when no supported choice can be established from the task context.
3. For a blinded independent review, require a new separate reviewer conversation and state what candidate-specific materials must not be exposed. If the selected destination has already seen the candidate's author rationale or findings, apply §6B.2 rather than calling it independent.
4. For code execution or local tests, Codex is only a candidate executor when its exact checkout, tools, runner and permissions are actually available. For independent static review, a different model/provider such as Claude (Anthropic) may be selected when the Owner has that destination available and its source access is sufficient. Neither is assumed to possess access or capabilities merely from its product name.
5. Distinguish `PROMPT_PREPARED`, `PROMPT_SENT`, `RECIPIENT_ACKNOWLEDGED`, `SOURCE_RETRIEVED`, `ACTION_EXECUTED` and `RESULT_ADJUDICATED`. Preparing a copy-ready prompt does not prove that it was delivered, read or executed.
A new chat is a new session, not a continuation by assumption. Start with a small, project-scoped envelope and retrieve only the relevant shared methods:

```text
HANDOFF_ID=
TARGET_AI_PROVIDER_AND_AGENT=
TARGET_MODEL_OR_CHANNEL=
TARGET_PROJECT_AND_TASK_ID=
TARGET_ROLE=
TARGET_SESSION_MODE=NEW_SEPARATE | CONTINUED | EXISTING_EXECUTOR
CONTEXT_SEPARATION_REQUIREMENT=
REQUIRED_SOURCE_ACCESS_AND_EXACT_REFS=
SOURCE_PACKAGE_REQUIRED=YES|NO
SOURCE_PACKAGE_STATUS=NOT_REQUIRED|IDENTIFIED|BYTES_PRESENT|IDENTITY_VERIFIED|BLOCKED
SOURCE_ACQUISITION_METHOD=RECIPIENT_LIVE_FETCH|ATTACHED_PACKAGE|OWNER_SUPPLIED_PACKAGE|LINK_ONLY|UNKNOWN
SOURCE_PACKAGE_FILENAME_AND_FORMAT=
SOURCE_PACKAGE_IDENTITY=REPOSITORY|BASE_SHA|HEAD_SHA|PATHS|REVISION
SOURCE_PACKAGE_DIGEST=SHA256_OR_GIT_BLOB_SHA_OR_NOT_AVAILABLE
OUTBOUND_ATTACHMENT_STATUS=NOT_REQUIRED|NOT_ATTACHED|ATTACHED_VERIFIED|ATTACHED_REPORTED|UNKNOWN
RECEIVER_ATTACHMENT_ACK=NOT_REQUIRED|PENDING|VERIFIED|FAILED
SOURCE_IDENTITY_VERIFICATION=RECIPIENT_LIVE_VERIFIED|COORDINATOR_ATTESTED|OWNER_ATTESTED|UNVERIFIED
SOURCE_COVERAGE=COMPLETE|PARTIAL|NOT_ASSESSED
REVIEW_CLASS=INDEPENDENT_LIVE|BOUNDED_STATIC_PACKAGE|NOT_RUN|NOT_APPLICABLE
PARENT_OBJECTIVE=
PROJECT_ID=
TASK_ID=
ROLE=COORDINATOR | SPECIALIST | EXECUTOR | INDEPENDENT_REVIEWER
OPERATING_CONTEXT=
MEMORY_SCOPE=
LIVE_MAIN_SHA_AND_OBSERVED_AT=
PROJECT_STATE_SOURCE_AND_REVISION=
OBJECTIVE_AND_ACCEPTANCE=
VERIFIED_FACTS=
OWNER_OR_ACTOR_REPORTED=
INFERENCES_AND_UNKNOWN=
DECISIONS_ALREADY_CLOSED=
LAST_TERMINAL_FINGERPRINT=
FIRST_OPEN_CAUSAL_EDGE=
AUTHORIZATION_AND_EXCLUSIONS=
EXPECTED_RETURN_ARTIFACT_AND_RECEIPT=
NEXT_SINGLE_ACTION=
EXPECTED_RETURN_ARTIFACT_OR_RECEIPT=
STOP_CONDITION=
WRITEBACK_TARGET_AND_PRIVACY_CLASS=
```

The sender provides the minimum context needed; the receiver acknowledges the project/task identity, sources actually retrieved, context actually available and any missing artifacts before acting. The receiver returns a correlated result to the owning project space. The coordinator adjudicates it under §6B before any next handoff. Do not make the Owner relay entire histories when one producer-generated, provenance-bound package can carry the necessary evidence; do not claim delivery until receipt is observed.

### 6C.6 Privacy and storage boundary

The repository `jhonf463r/Python` was checked on 2026-10-31 and its visibility was `public`. Therefore, this public repository is suitable for public-safe method contracts and sanitized/generalizable lessons only. Do not write private project archives, personal data, private designs/source files, customer information, credentials, keys, tokens, account identifiers or other restricted material here. Keep such project material in an appropriately private, access-controlled project store and place only a sanitized pointer or transferable method in the public core. Never weaken a project's privacy boundary for convenience of cross-chat retrieval.


## 6D. Control Master signal intake and decision binding (2026-10-31)

The existing IABV Control Master is a governance/priority signal that must be consulted when it is relevant and available. This section closes a cross-session method gap: new chats were following the canonical route while failing to explicitly retrieve and adjudicate the Control Master signal that should inform the next useful action. It does **not** create another coordinator, router, memory, service or authority source.

### 6D.1 Keep the two sources distinct and ordered

- `CURRENT-STATE.md` remains the sole canonical authority for IABV `ACTIVE_TASK`, `NEXT_ACTION`, technical gates and permissions.
- The live `ControlMasterService.current_state()` / `current_work_queue()` and their `ControlMasterDigest` projection provide a second, objective-relevant governance/priority signal: active objectives, backlog, priority, dependencies, next action, evidence refs, risks, decisions and unresolved items.
- A committed `data/evolution/control_master/latest.json` or `latest.md` is a snapshot with its own generation time. It is not automatically a live view of the local runtime. Use it as historical evidence when stale; do not silently promote it to current state.
- The Evolution Center's Control Master view and `ProactiveDashboardService` are not interchangeable. The former exposes the Control Master digest; the latter summarizes pending human approvals and learned approval policies. Neither replaces `CURRENT-STATE.md`.
- A digest, queue item or UI card is not an authorization, mandate, permission grant or proof that an operation may execute.

### 6D.2 Mandatory source-bound intake

For every material IABV development/coordination session, attempt the narrowest already-available, authorized read of the Control Master signal when it is relevant to the objective. Do not start IABV, launch the runtime, run a CLI, access protected data or inspect credentials merely to manufacture a signal.

Record at least:

```text
CONTROL_MASTER_SIGNAL_STATUS=FRESH|STALE|UNAVAILABLE|UNVERIFIED|CONFLICTED|NOT_APPLICABLE
CONTROL_MASTER_SOURCE=
CONTROL_MASTER_WORKSPACE_OR_PROJECT_SCOPE=
CONTROL_MASTER_STATE_ID=
CONTROL_MASTER_DIGEST_ID_OR_SHA=
CONTROL_MASTER_GENERATED_AT=
CONTROL_MASTER_OBSERVED_AT=
CONTROL_MASTER_TOP_QUEUE_ITEM_IDS=
CONTROL_MASTER_TOP_QUEUE_PRIORITIES=
CONTROL_MASTER_NEXT_ACTIONS_AND_DEPENDENCIES=
CONTROL_MASTER_EVIDENCE_REFS=
CONTROL_MASTER_DECISION_INFLUENCE=
```

`FRESH` means the digest was obtained from the current, source-identified runtime/read surface for this task episode and its generation/observation times are available. `STALE` means the source is known to predate relevant state changes or falls outside an established freshness bound. `UNAVAILABLE` means no supported read route or payload was available. `UNVERIFIED` means content was supplied without enough source identity/time to establish currentness. `CONFLICTED` means material fields disagree with a source of higher authority or newer evidence. `NOT_APPLICABLE` is reserved for tasks unrelated to IABV Control Master.

Do not invent a freshness interval. Use an existing documented producer TTL if one governs the source; otherwise report exact timestamps and whether the read came from the current runtime or a committed snapshot.

### 6D.3 Empty is not unavailable

A valid, successfully retrieved digest with a verified source identity and timestamps may legitimately contain an empty queue. That is `EMPTY_CONFIRMED`.

A blank normal-read response, exception, missing service, missing property, stale cache or failed export is `RETRIEVAL_FAILED` / `UNAVAILABLE`, not `EMPTY_CONFIRMED`. Never catch an error and silently replace it with `[]`, `{}` or `None` in the session's reasoning record. Preserve the failure status and continue only on evidence sufficient for the chosen action.

### 6D.4 Reconcile signal with the canonical route before selecting work

Construct the objective-conditioned model using both sources but preserve their authority order:

1. Read the active `CURRENT-STATE.md` header at the pinned `main` SHA. It controls the active route, gates and permissions.
2. Read the Control Master signal and bind its scope, timestamps, state ID and queue item evidence.
3. Match queue entries to the Owner's current objective, acceptance condition, project, exact target and current dependencies.
4. Exclude completed, superseded, unrelated, stale, blocked-by-unmet-dependency and unauthorized items. A high priority score is a ranking input, not permission.
5. Apply D019 to identify the first open causal/evidential edge and anti-loop fingerprint; apply D020 to compare the available authorized actions and select the smallest useful action.
6. Select one action and explain whether the Control Master signal changed the choice, confirmed it, or was unavailable and therefore did not influence it.

If the panel conflicts with `CURRENT-STATE.md`, do not merge the instructions. Preserve the canonical route and record the panel conflict for reconciliation. If D019 permits an independent lane, continue only when the Owner's current objective and its own authorization support a concrete task.

### 6D.5 Consumer coverage and failure visibility

Source code that defines or wires a digest is not proof that every consumer receives it. For any future code-level work, verify separately:

- the full prompt path receives the digest;
- compact/small-model paths receive an equivalent bounded projection or explicitly declare why not;
- dashboard/view-model rendering preserves signal identity and freshness;
- unavailable/error paths remain visibly unavailable instead of appearing empty;
- task outcomes link to their owning objective where intended;
- a later decision actually changes or is confirmed because of the signal.

The 2026-10-31 static reconciliation observed a full-prompt digest path, a compact-prompt omission, and silent empty/null fallbacks in some consumers. This is a source-level gap record, not proof of runtime failure or a mandate to implement now. Do not modify product code under a documentation-only authorization.

### 6D.6 Cross-chat handoff and causal reuse

A handoff that materially depends on the Control Master must carry the fields in §6D.2 and the exact source refs. The receiving chat must independently acknowledge whether it retrieved the digest, reconcile it with its own live `CURRENT-STATE.md`, and state how it affected the selected action. A pasted digest or a link proves availability of content, not that it was consumed or causally influential.

Use separate states:

```text
CONTROL_MASTER_SIGNAL_RETRIEVED=VERIFIED|REPORTED|NOT_AVAILABLE
ROUTE_RECONCILED=VERIFIED|PARTIAL|NOT_RUN
SIGNAL_CONSIDERED=YES|NO
SIGNAL_INFLUENCE=CHANGED_ACTION|CONFIRMED_ACTION|NO_EFFECT|UNAVAILABLE
ACTION_OUTCOME=VERIFIED|PARTIAL|FAILED|NOT_RUN
LATER_CAUSAL_REUSE=NOT_TESTED|VERIFIED
```

Claim causal influence only when the receipt identifies the signal and demonstrates the decision it changed or confirmed. Do not claim automatic delivery to future chats, runtime enforcement or generalization from a single session.

### 6D.7 Safety and scope

The Control Master is subordinate to the Owner's current objective and all existing hard gates. It cannot authorize protected reads, credential access, root provisioning, code changes, tests, build, runtime, tunnel, deployment, permission changes or PR merges. Do not put secrets or protected payloads into public GitHub receipts. Keep local runtime evidence and cloud coordination evidence explicitly separate.

## 6E. ChatGPT native project context and cross-agent artifact transport (2026-10-31)

### 6E.1 Purpose and boundary

Use ChatGPT's native Project as the shared context surface for participating ChatGPT conversations, not as another IABV memory or router. A Project can provide its chats with the same Project instructions, files and conversations. A Project can use Default memory or Project-only memory. The selected mode changes which other chats and saved memories can contribute; there is no universal best setting. Project-only confines references to chats inside the Project and excludes saved memories and conversations outside it. Shared Projects automatically use project-only memory. Default memory can use saved memories and, depending on plan/settings, relevant conversations beyond the Project. A chat outside the Project cannot use its private chat context. The Project does not automatically share its contents with Codex, Claude, another provider, an unrelated ChatGPT Project or the Owner's local filesystem.

For cross-product collaboration, continue using the owning project repository as the common versioned store, provided the receiving AI has an authorized connector or exact repository access. Do not create another coordinator, message bus, knowledge base or competing state file.

### 6E.2 One-time ChatGPT configuration

For IABV ChatGPT work, the recommended owner-side setup is:

1. Create or designate one Project named IABV — Coordinación compartida.
2. Add the copy-ready text from CHAT-ARCH-2026-10-31-CHATGPT-PROJECT-INSTRUCTIONS-R1.md to that Project's instructions.
3. Choose the Project memory mode deliberately:
   - `PROJECT_ONLY` is appropriate when the IABV Project must remain isolated from other projects. It lets chats refer to other IABV Project conversations, but excludes account-level saved memories and conversations outside this Project. Move eligible IABV chats into it and place required operating rules in its Project instructions.
   - `DEFAULT` is appropriate when the Owner wants the Project to draw on account-level memories and relevant chats outside the Project, where the plan and settings permit it. This improves broad continuity but can introduce unrelated cross-project context; apply the project-boundary rules before using it.
   - For this portfolio's existing `one shared method / separate project memories` policy, use `PROJECT_ONLY` for the dedicated IABV Project unless the Owner explicitly chooses account-wide context instead. Do not claim that either mode remembers every message.
   - When available, enable `Reference saved memories` and `Reference chat history` under Settings > Personalization > Memory; Project-only mode requires the applicable personal memory/reference controls. Availability varies by plan, region and workspace.
4. Move existing IABV chats into this Project when the UI permits; create all new IABV ChatGPT chats from inside it. A chat created with a custom GPT may not be movable; start a replacement chat inside the Project and use the canonical GitHub boot instead of copying an entire transcript.
5. Connect/authorize the GitHub app for jhonf463r/Python in every account/session that needs repository access. Do not assume one collaborator's app authorization or credentials transfer to another collaborator.

Do not put this IABV policy in global Custom Instructions when that would contaminate unrelated project work. Project instructions take precedence within their Project, but they remain guidance and do not override platform/system policy, app availability, tool permissions, Owner gates or fail-closed rules.

### 6E.3 ChatGPT memory limits and the two-level memory model

ChatGPT Memory is selective personalization, not a transcript database or deterministic retrieval of every past message. OpenAI documents that Memory does not retain every conversation detail, that the memory summary can omit details/sources, and that ChatGPT searches for relevant history only when likely to improve the response. Plan, region, platform and settings affect available features. Therefore:

- Use account-level Memory for stable, cross-project preferences and reusable coordination principles when the Owner wants those preferences across ordinary chats.
- Use one Project per substantive project to hold its exact instructions, chats and reference files. Project-only memory gives strong project isolation; Default memory provides broader account context where supported.
- Use the owning GitHub state and artifact records for exact technical settings, decisions, hashes, task status, permissions and provenance. Do not rely on the personal Memory summary as the canonical project record.
- When an exact prior fact or instruction matters, retrieve the canonical source. Do not assume ChatGPT has searched every chat or that a detail omitted from the visible Memory summary is absent from all underlying sources.

### 6E.4 Artifact retrieval ladder — eliminate avoidable manual transfer

Before asking the Owner for an upload, pasted text, local export or repeated explanation, check in this order:

1. The current ChatGPT Project's shared Sources/files and relevant chats, when this chat is actually inside the IABV Project.
2. The connected, authorized GitHub repository; retrieve the exact canonical file/ref/commit and verify its revision, rather than relying on a remembered link or copied excerpt.
3. Another already-connected, authorized project source/connector that can retrieve the exact artifact and preserve its provenance.
4. Only then, request one precisely identified artifact from the Owner, and only when evidence establishes that it exists solely in a local/runtime location not exposed through an authorized connector or controlled bridge. Explain the missing route; never ask for a whole project export when one file/field is sufficient.

If GitHub/project retrieval is available, do not make the Owner act as a manual courier between ChatGPT chats. Use the common source directly and report what was actually retrieved. If a tool is not present in the receiving session, classify the capability as unavailable; do not pretend a prompt or Project instruction can install the tool.

### 6E.5 Distinguish file sharing from live runtime synchronization

Use these separate channels:

- CHATGPT_PROJECT_SHARED_CONTEXT: Project instructions, files and chats accessible to participating ChatGPT chats in that Project.
- GITHUB_CANONICAL_STORE: versioned, source-bound records available to any AI that has an authorized repository route.
- CONNECTED_APP_SOURCE: content returned on demand by a connected app; availability and scope depend on that session's app access and permissions.
- LOCAL_RUNTIME_SOURCE: local application/database/files/processes; not visible to a cloud chat unless an explicitly supported, authorized connector or bridge exposes them.
- CROSS_PRODUCT_HANDOFF: a correlated, published artifact in the shared repository or another agreed authorized store; a prompt, link or PR alone does not prove receipt or application.

ChatGPT's GitHub app is documented as on-demand retrieval, not a continuously synchronized GitHub index or local-runtime feed; its availability varies by plan, workspace and product surface. The standard GitHub app may be read-only. Use only the write-capable tool actually exposed and authorized in the current session; do not infer write capability from read access.

A Project therefore removes repeated uploading of shared project material, but does not make a live local Control Master digest appear automatically. If the live digest exists only inside the Owner's local runtime and no authorized reader/bridge publishes it, mark it UNAVAILABLE/UNVERIFIED; do not substitute the stale latest.json/md, start the runtime, access protected data or bypass M1A gates. An authorized future bridge/export would require its own security and scope approval.

### 6E.6 Receipt and no-claim rules

Record the transport state separately:

SOURCE_IDENTIFIED -> ARTIFACT_RETRIEVED -> REVISION_VERIFIED -> CONTEXT_AVAILABLE -> RECEIVER_ACKNOWLEDGED -> DECISION_BOUND -> OUTCOME_VERIFIED -> CANONICAL_FETCHBACK.

- A shared Project/file/link means AVAILABLE, not necessarily RETRIEVED or CONSUMED.
- A connector read proves retrieval only for the current session and exact returned source/ref.
- A receiving chat's correlated receipt is evidence of acknowledgement; its explanation of decision influence is needed to claim application.
- A verified outcome and canonical fetch-back are separate from receipt/application.
- Never claim automatic delivery, automatic boot, model-weight learning, or cross-vendor synchronization from Project membership, a commit or a link.

### 6E.6A Source-package integrity and recipient attachment acknowledgement

The sender/receiver chain in §6E.6 is not complete merely because a prompt contains a URL or says “attach the patch.” When a task depends on a package, patch, diff, archive or document that the recipient cannot independently retrieve through an available authorized source, use this explicit sub-gate before substantive review or execution.

**Source-acquisition routes are distinct:**

- `RECIPIENT_LIVE_FETCH`: the receiving actor independently retrieves the exact repository/ref/commit and verifies the relevant bytes in its own authorized session.
- `ATTACHED_PACKAGE`: the recipient receives the actual bytes as an attachment, not merely a URL or instruction to download them. Record who produced the package and the provenance available to the receiver.
- `OWNER_SUPPLIED_PACKAGE`: the Owner supplies the actual file; treat its source identity as unverified until the recipient compares its manifest/content with the stated canonical revision.
- `LINK_ONLY`: a URL is present but no successful recipient retrieval or actual attachment has been observed. This is availability, not retrieval.
- `UNKNOWN`: the acquisition route cannot be established.

When a package is required, track this ordered state:

```text
SOURCE_PACKAGE_IDENTIFIED
  -> PACKAGE_BYTES_PRESENT
  -> PACKAGE_IDENTITY_AND_SCOPE_VERIFIED
  -> OUTBOUND_ATTACHMENT_VERIFIED
  -> RECEIVER_ATTACHMENT_ACKNOWLEDGED
  -> SUBSTANTIVE_ACTION_ALLOWED
```

The handoff must record at least:

```text
SOURCE_PACKAGE_REQUIRED=YES|NO
SOURCE_ACQUISITION_METHOD=RECIPIENT_LIVE_FETCH|ATTACHED_PACKAGE|OWNER_SUPPLIED_PACKAGE|LINK_ONLY|UNKNOWN
SOURCE_PACKAGE_FILENAME_AND_FORMAT=
SOURCE_PACKAGE_IDENTITY=REPOSITORY|BASE_SHA|HEAD_SHA|PATHS|REVISION
SOURCE_PACKAGE_DIGEST=SHA256_OR_GIT_BLOB_SHA_OR_NOT_AVAILABLE
SOURCE_PACKAGE_STATUS=NOT_REQUIRED|IDENTIFIED|BYTES_PRESENT|IDENTITY_VERIFIED|BLOCKED
OUTBOUND_ATTACHMENT_STATUS=NOT_REQUIRED|NOT_ATTACHED|ATTACHED_VERIFIED|ATTACHED_REPORTED|UNKNOWN
RECEIVER_ATTACHMENT_ACK=NOT_REQUIRED|PENDING|VERIFIED|FAILED
SOURCE_IDENTITY_VERIFICATION=RECIPIENT_LIVE_VERIFIED|COORDINATOR_ATTESTED|OWNER_ATTESTED|UNVERIFIED
SOURCE_COVERAGE=COMPLETE|PARTIAL|NOT_ASSESSED
REVIEW_CLASS=INDEPENDENT_LIVE|BOUNDED_STATIC_PACKAGE|NOT_RUN|NOT_APPLICABLE
```

**Hard stop rules:**

1. A prompt, URL, browser link, PR number, filename or request to attach a file does not prove that package bytes exist in the sending surface or are attached to the outbound message.
2. `OUTBOUND_ATTACHMENT_STATUS=ATTACHED_VERIFIED` requires the actual attachment to be visible/confirmed in the sending surface. Do not infer it from instructions or a download URL.
   If the sender can only report that it attached the file and the coordinator cannot observe the sending surface, use `ATTACHED_REPORTED` and preserve `OWNER_REPORTED` / `ACTOR_REPORTED` provenance until the receiver's correlated acknowledgement arrives.
3. `RECEIVER_ATTACHMENT_ACK=VERIFIED` requires the receiver to confirm that it can open/read the actual package and to echo enough identity data to correlate it (for example filename, base SHA, head SHA and changed-path count). A generic “got it” is insufficient.
4. If a package is required and absent, unreadable, unverified or unacknowledged, keep `PROMPT_PREPARED` or `HANDOFF_BLOCKED`; substantive review/execution is `NOT_RUN`. Do not fill a review receipt, infer PASS/FAIL, or tell the Owner the handoff is ready.
5. A coordinator-exported or Owner-supplied diff/patch can support a bounded static assessment after its bytes and scope are verified. It does **not** become independent live source retrieval merely because a second model reads it. Use `REVIEW_CLASS=BOUNDED_STATIC_PACKAGE` and `SOURCE_IDENTITY_VERIFICATION=COORDINATOR_ATTESTED` or `OWNER_ATTESTED` unless the receiver independently fetches and verifies the live source.
6. Claim `REVIEW_CLASS=INDEPENDENT_LIVE` only when reviewer-context separation is satisfied under §6B.2 **and** the recipient independently verifies the exact live base, head, diff/source coverage. Context independence and source independence are separate dimensions.
7. If no direct cross-product send/attach action exists, say so and keep the state at the last evidenced stage. The Owner may perform one exact attachment step only after the coordinator has made the exact package available and identified it; do not make the Owner reconstruct, generate or diagnose the package.
8. Do not retry the same failed source route without a material capability/evidence change. A repeated prompt without the missing bytes or retrieval capability is `SAME_EXPERIMENT` under D019/D020.

A recipient that reports “no file attached” has supplied a valid transport-failure observation, not a source review. Record `RECEIVER_ATTACHMENT_ACK=FAILED`, `SUBSTANTIVE_REVIEW=NOT_RUN`, and the exact missing package. Resume only after a material source-acquisition change.

### 6E.7 Owner friction rule

The coordinator performs retrieval, reconciliation, source navigation, file comparison, and handoff assembly whenever the current tools and permissions permit. The Owner should perform only the one-time ChatGPT Project configuration that cannot be changed by an assistant tool, or provide an exact local-only artifact when no authorized connector exists. Do not repeatedly request manual export/upload for the same stable artifact once it is stored in the Project or repository.

**Official product behavior references checked 2026-10-31:**
- Projects in ChatGPT: https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- Connecting GitHub to ChatGPT: https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- Connected apps in ChatGPT: https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt
- Memory in ChatGPT: https://help.openai.com/en/articles/8590148-memory-in-chatgpt

## 6F. Pre-action precision gate, branch identity and anti-waste execution loop (2026-11-02)

This section integrates the corrections from the 2026-11-02 Control Master bridge review into the existing UAAL loop. It is a mandatory decision gate for material work, external-agent handoffs, repository edits, PR reviews and test requests. It does not create a new coordinator, router, memory store, service or technical authority. `CURRENT-STATE.md` remains the sole active route authority; Owner authorization remains action-specific.

### 6F.1 Build one exact target-and-authority bundle before proposing work

Before drafting a Codex/Claude prompt or making a consequential repository action, bind the task to the following tuple:

```text
TASK_ID=
PROJECT_ID=
OPERATING_CONTEXT=
TASK_SCOPE=DOCS|SOURCE|TESTS|BUILD|RUNTIME|REVIEW|OTHER
REPOSITORY=
BASE_REF=
BASE_SHA=
TARGET_PR=
PR_HEAD_BRANCH=
PR_HEAD_SHA=
REQUESTED_BRANCH=
TARGET_PATHS_AND_CURRENT_BLOB_SHAS=
OWNER_AUTHORIZATION_SCOPE=
EXPLICIT_EXCLUSIONS=
EXPECTED_OBSERVABLE=
STOP_CONDITION=
```

For a task without a PR, mark the PR fields `NOT_APPLICABLE`; do not omit the distinction. Record source and observation time. A remembered SHA, an earlier assistant message, a task number or a branch-like name is not a live reference.

The actual PR head branch and SHA must be read from the live PR/ref. The branch requested in an earlier prompt is only a requested target until it is proven identical. If names or commit ancestry differ, classify `BRANCH_IDENTITY_MISMATCH` or `BRANCHES_DIVERGED`; do not silently switch, rename, rebase, cherry-pick, recreate or open a second candidate. Compare both exact refs and stop before writes until the intended owner target is clear. A branch with a similar prefix is not an alias.

### 6F.2 Capability and permission preflight — do not send impossible work

Before delegating, verify separately that the receiving actor actually has:
- the correct repository and exact ref/HEAD;
- the intended checkout/worktree, when local inspection or edits are required;
- an available executor and the required interpreter/toolchain, when tests/build are requested;
- the explicit permission needed for each read, write, test, build or runtime operation;
- the exact files and source revision needed to complete the bounded task.

A GitHub connector's ability to read or write remote repository objects does not prove that Codex has a local checkout, that a Windows workspace is attached, or that a test runner exists. An existing GitHub Actions workflow also does not establish that it can validate this task: inspect its event type, branch filters, path filters, runner OS, Python/toolchain and exact test command. Classify an inapplicable workflow as `NO_MATCHING_CI_ROUTE`, separately from `RUNNER_UNAVAILABLE`. If a matching workflow is accepted but the platform refuses to start its job because the repository/account is account-restricted, classify `ACTIONS_ACCOUNT_RESTRICTION` and `RUNNER_JOB_NOT_STARTED`; this is neither a source/test failure nor proof that the runner configuration is absent. If GitHub rejects the workflow definition before creating a job, classify `WORKFLOW_CONFIGURATION_ERROR` and correct the YAML before interpreting CI results. Do not add dummy file changes or unrelated source edits merely to trigger a workflow; do not create or dispatch a new runner/workflow unless that mechanism is explicitly authorized and its cost/permissions are known. A reported `BLOCKED_NO_AUTHORIZED_RUNNER`, missing checkout or unavailable capability is not a code defect and is not permission to bypass the boundary. Do not issue a test command to an actor that has already reported no authorized runner. Choose a useful, authorized static/documentation action if one exists; otherwise record the dependency and stop.


**Observed CI-route classification (2026-11-02):** the repository's main branch contains `.github/workflows/iabv-authorization-focused-tests.yml` (blob `fc3ff9c6d04a16a391a19b7e0792d6f3c482995c`). It uses `windows-latest` and Python 3.11, but its push trigger is restricted to `codex/iabv-m1f-authz-candidate-review-20261025`; its pull-request trigger requires changes in a fixed list of M1A authorization source/test paths. It has no `workflow_dispatch` trigger. The changed paths in PR #591 and PR #598 do not match those conditions. Therefore the result for these tasks is `NO_MATCHING_CI_ROUTE`, not proof that GitHub Actions is disabled or that the repository has no Windows runner. Do not alter unrelated authorization files or add dummy source changes merely to trigger this workflow. The exact PR #591 candidate has zero reported status checks and zero PR-triggered runs; the four new focused publisher tests remain `AUTHORED_NOT_RUN`.


**Subsequent CI execution evidence — PR #591 (2026-11-02):** the initial `NO_MATCHING_CI_ROUTE` finding referred to the repository's pre-existing M1A-only workflow. A dedicated workflow was then added to the actual PR #591 branch at `.github/workflows/iabv-control-master-focused-tests.yml`; its current branch-only blob at this observation was `baadd228fe983dae73be88780775517e1ce9691e`. GitHub accepted the matching `pull_request/synchronize` event and created run `41519019291`, but explicitly annotated that the job was not started because the GitHub reported an account-level platform restriction; the exact account annotation is intentionally not copied into this public record. Run `41519008799` reached the same account-level stop via the branch-push event. Earlier runs `41518778170` and `41518883184` exposed the `runner.temp` job-env scope error; this was corrected by moving `IABV_DATA_DIR` into the pytest step environment. The current definition is accepted by GitHub; no test step ran. Classify `ACTIONS_ACCOUNT_RESTRICTION=BLOCKED`, `RUNNER_JOB_NOT_STARTED=TRUE`, `TESTS=NOT_RUN` — not a test failure or missing route. Standard GitHub-hosted runners for public repositories are ordinarily free under GitHub's billing guidance (<https://docs.github.com/en/billing/concepts/product-billing/github-actions>), but this account-level lock still prevents job startup. Do not switch runner classes or attempt a restriction bypass. The Owner/account administrator must resolve the restriction through GitHub's normal account process before test execution can proceed.


For every external-agent handoff, apply §6E.6A before substantive review or execution. Verify the actual source package bytes, outbound attachment and recipient acknowledgement when that route is required. A link or a prompt that says “attach the patch” is `LINK_ONLY`, not `ATTACHED_PACKAGE`. If direct recipient live-fetch is unavailable and the actual attachment/acknowledgement chain is incomplete, stop at `PROMPT_PREPARED` / `REVIEW=NOT_RUN`; do not issue another copy of the prompt or claim dispatch. A coordinator-exported attachment permits only a bounded static package review unless the receiver independently verifies the live repository state.

### 6F.2A Pull-request path-filter comparison semantics — aggregate diff, not latest commit

A workflow path filter must be evaluated using the event's comparison semantics, not by inspecting only the files modified in the newest commit.

- For `pull_request`, GitHub computes changed files using a **three-dot diff** between the latest topic-branch revision and the commit where that topic branch was last synchronized with its base. The filter therefore evaluates the aggregate PR change set.
- For `push` to an existing branch, GitHub uses a **two-dot diff** between the pushed head and base. This is a different comparison scope.
- Consequently, a documentation-only commit pushed to a PR branch can still trigger a `pull_request.paths` workflow if any other file in the PR's aggregate three-dot diff matches the configured path patterns. The fact that the latest commit itself changed no matching path is insufficient to predict `NO_MATCHING_CI_ROUTE`.
- Before any PR-branch write, compute the current merge-base/three-dot changed-file set and test every path against the workflow's positive/negative patterns; also bind the expected event type, base branch, PR branch and workflow revision.
- After a matching workflow is blocked before runner startup by an unchanged account/platform restriction, do not add receipt-only commits, tweak workflow files or retry on that same PR merely to refresh its record. Each new PR synchronize event may reproduce the same blocked job because the aggregate PR diff remains matched. Freeze that PR branch until the external restriction changes or a genuinely necessary source correction changes the task's acceptance evidence.
- Do not create a second PR/branch, use dummy source changes, alter runner classes or bypass the platform restriction to avoid this result. Persist the blocker in the PR description or a non-triggering coordination record when possible; resume the existing workflow once the account administrator has resolved the restriction through the normal GitHub process.

**Observed falsifier and correction (2026-11-02):** PR #591's dedicated workflow excludes the D021 Markdown path from its explicit `paths` list, but a D021-only commit still triggered run #8 because the PR's aggregate three-dot diff continued to contain matching source/test/workflow files. The job was not started under the account-level restriction; no test step ran. The earlier coordinator assumption that a documentation-only commit would not retrigger a PR-filtered workflow was therefore false and is superseded by this rule.

Official reference: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow (section "Git diff comparisons").

Owner inputs already reconciled in canonical history must be reused. Ask one question only when a genuinely missing answer would change the authorized choice. Never ask the Owner to repeat settled identity, setup, branch or approval facts.

### 6F.3 Repository and branch identity guard

For every PR operation, record and verify all four identities: repository, PR number, actual source branch, and actual source HEAD SHA. Also record the base branch and base SHA. Do not derive the actual PR branch from a previously prepared task prompt.

Before writing:
1. Refresh live `main` and the target PR/ref.
2. Confirm the exact source branch and HEAD SHA still match the bundle.
3. Inspect the relevant final diff and exact source/test blobs, not merely commit count or PR title.
4. If the PR head moved, the branch disappeared, the branch name differs, or the compare status is unexpected, stop and reconcile. Do not apply a write against a stale assumption.
5. For ref updates, use an expected-SHA/lease check where the interface supports it; never force-update to “make it fit”.

The two Control Master bridge branches observed on 2026-11-02 are separate refs: `iabv/control-master-signal-bridge-r1-20261031` and the actual PR #591 source `iabv/control-master-signal-bridge-r1-20261031-review`. Their common base at the observed revision did not make them aliases. Only the actual PR source may be modified for PR #591 unless the Owner separately changes the target.

### 6F.4 Temporal preconditions, TOCTOU and safe branch reconciliation

A precondition that may change between inspection and action must be checked again at the narrowest practical point immediately before the write/side effect. Record both observations and the interval. For a public-branch publisher, checking the remote default branch only at startup is insufficient: re-check it immediately before pushing. If the value changed, fail closed and do not push.

A last-moment client-side re-check narrows but does not eliminate a race: the remote default branch can still change after the check and before the server accepts the push. Do not describe this as atomic protection. Absolute prevention requires a server-side invariant or an atomic server operation that binds the target ref to the non-default condition. Preserve this residual risk in review and acceptance language.

When a dedicated signal branch is behind current `main`, do not treat ordinary new `main` commits as contamination and do not force-push or overwrite the signal branch. Use a normal, non-force fast-forward/merge reconciliation of current `main` into the signal branch, then compare the resulting complete tree against the exact current `main` tree. Continue only when the sole remaining delta is the allowlisted signal file. If merge conflicts occur or any non-allowlisted delta remains, stop fail-closed. Verify the subsequent normal push by remote ref, fetched commit and exact file bytes. A successful merge/read-back proves branch consistency, not signal authenticity or M1A authority. Also perform this read-back when the push command itself exits non-zero or times out: the remote may have accepted the ref before the transport acknowledgement was lost. Do not classify that case as definitely unpublished; report `PUBLISHED_UNVERIFIED`/`PUSH_RESULT_UNVERIFIED` unless the exact remote ref, commit and bytes prove the postcondition. A verified read-back may confirm publication despite an ambiguous client-side exit.

### 6F.5 Batch writes and verify the final artifact, not activity volume

Group related edits into one coherent tree/commit when the Git interface permits it. Prefer create-blob/create-tree/create-commit and one guarded ref update over a sequence of one-file commits. If the available interface only supports sequential file updates, keep the sequence minimal, verify each resulting blob and inspect the final aggregate diff. Connector-generated commits are transport artifacts; `ahead_by`, commit count, file count, tool-call count and text volume are not independent deliverables or progress metrics.

After writing, fetch every changed path back from the exact candidate ref. Verify the final base/head, changed-path set, blob identities, scope and exclusions. A successful API write is not enough; it must be reconciled against the intended branch and final diff.

### 6F.6 Evidence-bound testing and result classification

A test result is valid only for the exact source revision it exercised. Bind every execution result to:
- exact commit/HEAD SHA;
- exact source and test file blob SHAs;
- exact command and selected test set;
- executor/runner, OS, interpreter and relevant environment;
- exit code and raw result summary;
- whether the run was independent, reported by an actor, or observed directly.

A prior `11 passed` result on earlier publisher/projector/test blobs does not validate changed blobs or the current PR HEAD. Label results `VERIFIED`, `ACTOR_REPORTED`, `AUTHORED_NOT_RUN`, `CI_REPORTED`, or `NOT_RUN` as applicable. No runner, no checkout, an unavailable workflow, or a permission block is not a passing test and must not be hidden by a synthetic harness. A bounded harness result must state what it stubbed and what integration paths it did not exercise.

Use a specific stop classification rather than a generic `BLOCKED`:
`BRANCH_IDENTITY_MISMATCH`, `AUTHORITY_NOT_GRANTED`, `CAPABILITY_UNAVAILABLE`, `WORKSPACE_NOT_ATTACHED`, `SOURCE_UNAVAILABLE`, `PRECONDITION_CHANGED`, `MERGE_CONFLICT`, `TESTS_NOT_RUN`, `TEST_FAILURE`, `INTEGRATION_UNVERIFIED`, or `TOOL_TRANSPORT_FAILURE`. Preserve confirmed defects separately from hypotheses and missing evidence.

### 6F.7 Anti-waste selector and causal learning

Before repeating any attempt, compute a task fingerprint from the objective, first open causal/evidential edge, exact target/ref, preconditions, attempted operation and expected observable. Compare it with the terminal fingerprints already recorded under D019. A new chat, changed wording, new task ID, new branch suffix or repeated prompt is not a material delta. Retry only when new source evidence, a changed precondition, a corrected operation or an explicitly authorized scope changes the expected result.

Select the smallest action that creates verified progress or decision-changing evidence. Exhaust already-authorized repository/source tools before asking the Owner to copy information manually. If the same blocker remains and no authorized discriminating action exists, stop that lane; continue a genuinely independent lane only when the Owner's current objective and that lane's authorization support it. Do not invent a new runner, memory store, router or live signal.

For Control Master, record whether the signal was fresh/stale/unavailable/unverified, what exact queue evidence was considered, and whether it changed the selected action, confirmed it, had no effect, or was unavailable. A signal is not consumed merely because it was fetched or included in a prompt. A causal-learning claim requires a later, non-identical task/session to retrieve the rule, apply it, and demonstrate an attributable improvement. Until then, report only that the rule was stored or explicitly applied in the current bounded episode.

### 6F.8 Minimum correlated receipt

Every material handoff or repository action returns one compact receipt:

```text
TASK_ID=
OBSERVED_AT=
REPOSITORY=
BASE_REF_AND_SHA=
TARGET_PR=
ACTUAL_HEAD_BRANCH_AND_SHA=
REQUESTED_BRANCH_AND_MATCH_STATUS=
CHANGED_PATHS_AND_BLOB_SHAS=
CONTROL_MASTER_SIGNAL_STATUS_AND_DECISION_INFLUENCE=
CAPABILITY_PREFLIGHT=
SOURCE_PACKAGE_REQUIRED_AND_STATUS=
SOURCE_ACQUISITION_METHOD_AND_IDENTITY=
SOURCE_PACKAGE_DIGEST_AND_COVERAGE=
OUTBOUND_ATTACHMENT_STATUS=
RECEIVER_ATTACHMENT_ACK=
SOURCE_IDENTITY_VERIFICATION=
REVIEW_CLASS=INDEPENDENT_LIVE|BOUNDED_STATIC_PACKAGE|NOT_RUN|NOT_APPLICABLE
AUTHORIZATION_SCOPE_AND_EXCLUSIONS=
ACTION_ATTEMPTED=
TEST_COMMAND_AND_EXACT_HEAD=
TEST_STATUS=VERIFIED|ACTOR_REPORTED|AUTHORED_NOT_RUN|NOT_RUN
EXPECTED_VS_ACTUAL=
ROOT_CAUSE_CLASS=
STOP_CONDITION_OR_NEXT_DEPENDENCY=
FETCH_BACK=VERIFIED|PARTIAL|NOT_RUN
MAIN_CHANGED=TRUE|FALSE
MERGE_OR_PUBLICATION=NOT_ATTEMPTED|VERIFIED|UNVERIFIED
```

Do not claim that another chat received or applied the method from a link, commit or handoff attempt. Do not claim tests, build, runtime, publication, merge or learning without the matching evidence.

**Observed triggers for this revision (2026-11-02):** PR #591's actual source branch had a `-review` suffix while a separately existing requested branch lacked it; Codex reported no authorized runner/checkout and did not run tests; the public signal publisher checked the remote default branch before cloning but not immediately before push; the publisher rejected every non-signal tree delta against live `main` without first reconciling ordinary `main` advancement; historical test success was attached to earlier blobs; and the connector-generated PR history had many sequential commits that did not represent separate deliveries. These observations require the guards above. They do not authorize a merge, public signal publication, local/protected read, runtime operation, or any M1A gate transition.


## 7. Historical authoring snapshot and per-session falsifiable checks

The values below are the original D021 authoring snapshot, not current route authority. Each material session must refresh live `main` and current PR metadata before reuse. Observed while preparing the initial revision:
- `main` baseline: `79ab8c50eaa7518120d5ebed9db4747d395a21cb`.
- PR #555: open/draft/unmerged; HEAD `c36ee5ed177a3b5afee764c277cc4a8b243594c8`; M1B candidate source is published in a reviewable PR, contradicting older “local-only/unpublished” headers.
- PR #556: open/draft/unmerged; HEAD `fb635aab18d9c2ef19b20d48e3625d52383fe6af`.
- `G1/G2/G3=NOT_ESTABLISHED`; `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`; `PROTECTED_READS=FAIL_CLOSED`; `BRIDGE=BRIDGE_NOT_READY`.

Per-session method acceptance checklist:
- [ ] Live `main` and PR HEADs refreshed, not copied from an old chat.
- [ ] The active header no longer calls PR #555 local/unpublished.
- [ ] All continuity front doors use the same short route and treat old snapshots as history.
- [ ] D019/D020 remain the owning causal-selection methods; D021 adds activation/reconciliation rather than another router.
- [ ] Exact edited files are fetch-backed from the proposal branch and the PR diff is reviewed.
- [ ] Once adopted, a later non-identical task validates causal reuse; until then it stays `NOT_TESTED`.

## 7A. Pre-search context and source-provenance ceiling (2026-10-29)

The [pre-search baseline receipt](./CHAT-ARCH-2026-10-29-UAAL-D021-PRE-SEARCH-CONTEXT-BASELINE-RECEIPT.md) records an owner-supplied transcript that reports project-specific information was available before new searches. The transcript itself acknowledges that the session had prior context and does not authenticate the initial context payload or its source.

This limitation matters because the official [OpenAI Memory in ChatGPT documentation](https://help.openai.com/en/articles/8590148-memory-in-chatgpt) says available memory/personalization can draw from multiple sources, including past chats, saved memories, custom instructions, Library files and connected apps (depending on plan/settings), and that visible Memory Sources may not show every factor. Thus, correctly naming IABV before a new search cannot identify GitHub as the source.

For this experiment, the evidence supports only:
- `PRE_SEARCH_CONTEXT_AVAILABILITY=LIMITED_EVIDENCE_FROM_SUBMITTED_TRANSCRIPT`
- `SOURCE_PROVENANCE=UNKNOWN`
- `EXPLICIT_EXTERNAL_GITHUB_RETRIEVAL=VERIFIED_IN_THE_PRESENT_RECONCILIATION`
- `AUTOMATIC_CROSS_SESSION_BOOT=NOT_PROVEN`
- `GENERALIZATION=NOT_TESTED`

Do not repeat text-only baseline tests as if they solve source attribution. Reopen the automatic-boot hypothesis only if new, trustworthy provenance observability or a controlled source-isolation capability becomes available. Until then, the supported operational path is explicit retrieval and verification of canonical external state. This is an epistemic stop condition, not an implementation of automatic bootstrap and not a change to `OPTION_D=RATIFIED_NO_BOOTSTRAP` or any technical gate.

## 8. Scope and non-goals

This is a documentation/control-plane repair only. It does not create trust roots, keys, credentials, Entra registrations, authority assets, production providers, an MCP allowlist, protected reads, local runtime or tunnel. It does not change IABV technical acceptance criteria. G1/G2/G3 remain `NOT_ESTABLISHED` until their independent product evidence is supplied. No test suite or runtime was executed as part of this method authoring.
