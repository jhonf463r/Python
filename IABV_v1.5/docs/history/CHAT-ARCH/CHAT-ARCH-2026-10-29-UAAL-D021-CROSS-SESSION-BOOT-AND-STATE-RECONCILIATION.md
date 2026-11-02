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

#### Case-specific continuity facts already recorded

- The Owner reported an organizational Microsoft Entra directory, a dedicated `IABV Owner` account, Microsoft Authenticator enrollment and a successful sign-in verification. Classify this as `ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY`; `IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID`; `PLAUSIBLE_FOR_HUMAN_OWNER_AUTHENTICATION`; `NOT_YET_TRUSTED_BY_IABV`. **Do not repeat setup or ask whether this identity provider exists.**
- The existing record says that no IABV app registration, token verifier, role-to-mandate mapping or protected Owner-to-Windows / issuer-to-exact-server binding was established in the inspected main path. Successful MFA is not IABV runtime authorization and does not independently bind a production root selection.
- The Owner primarily uses the ChatGPT phone app; the 2026-10-26 approval protocol also records Codex Remote/mobile approval as a possible interface to the already-open local session when connected. Treat these as human interaction/approval channels, not as an established IABV issuer, runtime trust root, or proof that a response reached and was enforced by the exact protected process.
- A phone approval, QR code, displayed challenge or copied fingerprint is not independent proof of the target root when the value originates only from the target and no prior trusted binding exists.
- For the 2026-10-31 reconciliation, the Owner stated that no additional mechanism is identified beyond the phone authentication/approval app. The correct result is that the known Entra/Authenticator and mobile approval channels are already in memory, no additional independent root/issuer mechanism is identified, and the technical root-provenance gate remains open. This resolves the Owner-input question; it does not close G1 or prove that other uninspected authority assets are absent.

**Acceptance rule:** no further Owner question is permitted until the ledger shows that the proposed question is not answered by an existing source and identifies the precise new decision/evidence it would change.

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

A new chat is a new session, not a continuation by assumption. Start with a small, project-scoped envelope and retrieve only the relevant shared methods:

```text
HANDOFF_ID=
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

#### 6D.2.1 Dedicated GitHub signal snapshot (when published)

The implementation candidate publishes an explicitly requested, privacy-minimised snapshot to the dedicated non-default branch `control-master-live`, at:

`IABV_v1.5/data/evolution/control_master/shared_signal.json`

This is an optional, source-bound retrieval path for participating sessions; it is not an automatic feed or proof that the local runtime is currently connected. The publisher is invoked only from an already-running, authorized `AppBootstrap` instance. The Evolution Center exposes a manual action that opens a disclosure/confirmation dialog before invoking that existing instance; ordinary panel refresh never publishes. No second bootstrap, CLI launch, protected read or credential inspection is needed or permitted merely to fetch the snapshot. A missing branch/file, inaccessible ref, malformed payload or failed verification is `UNAVAILABLE` / `UNVERIFIED`, never an empty queue.

A receiving session should fetch the file from the exact `control-master-live` branch commit using its already-available authorized GitHub connector/API, then record the branch commit SHA, file blob SHA, retrieval time and source URL. Validate all of the following before treating the signal as usable:

1. `schema_version=iabv.control_master_signal.v1`, `project_id=IABV`, and `transport=READY_FOR_DEDICATED_BRANCH_PUBLICATION`.
2. `signal_status` is `AVAILABLE` or `EMPTY_QUEUE`; an `UNAVAILABLE` payload is deliberately marked non-publishable and must not be promoted to a valid snapshot.
3. `content_sha256` equals SHA-256 of canonical UTF-8 JSON containing every top-level field except `content_sha256`, serialized with sorted keys, separators `,` and `:`, and `ensure_ascii=true`. This is an integrity checksum only: it is not a digital signature, issuer authentication or proof of an IABV trust root. Repository/ref access and commit provenance remain separate trust assumptions; never use this hash to satisfy M1A/G1 or another root-authentication gate.
4. `signal_id` equals `cms-` plus the first 24 hex characters of SHA-256 over the same canonical JSON after removing `content_sha256` and setting `signal_id` to the empty string.
5. `generated_at_utc` and `expires_at_utc` are timezone-aware, generation is not in the future, expiry is still in the future, and the interval is at most the declared 900-second freshness window. An expired snapshot is `STALE`, even if its hash is valid.
6. The source component is `ControlMasterService`; capture `source.state_id` and `source.state_observed_at_utc`. This timestamp denotes the producer's state projection observation, not a claim that a persisted object was modified at that time.
7. Queue status, signal status, item count and actual item list agree. `EMPTY_QUEUE` is valid only when the verified item list is empty; an `AVAILABLE` queue must contain at least one item.

Queue item IDs are per-snapshot positional references such as `queue-item-01` and `queue-item-02`, assigned in priority order and scoped only to the exact `signal_id`. They have no stable mapping to source item IDs across snapshots and do not reveal, identify, authorize or resolve an objective/task. A recipient must use a separate already-authorized local read to correlate a slot with a real source object; never guess the mapping. The snapshot deliberately omits titles, free-form summaries, next actions, reason text, evidence paths, logs and user content. It carries only allowlisted status/source/priority metadata and a `queue_items_published` count derived from the exact item list in the snapshot. The repository is public: do not expand this payload with private or protected fields. A receipt based only on this public snapshot must record `CONTROL_MASTER_NEXT_ACTIONS_AND_DEPENDENCIES=OMITTED_BY_PUBLIC_SIGNAL_PRIVACY_ALLOWLIST` and `CONTROL_MASTER_EVIDENCE_REFS=OMITTED_BY_PUBLIC_SIGNAL_PRIVACY_ALLOWLIST`; do not infer them from opaque IDs or priorities. If a separate authorized local read supplies those fields, record that distinct source and its provenance.

The snapshot is subordinate to the route and must be reconciled with the pinned `main` `CURRENT-STATE.md`; it cannot establish task authority, permissions, Option D changes, M1A/G1/G2/G3 acceptance, or approval for implementation/tests/runtime/merge. Do not call the branch a live runtime view beyond its recorded generation and expiry. Do not claim automatic cross-chat delivery: each recipient must retrieve, verify and acknowledge the exact published commit independently.

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

The 2026-10-31 main-branch reconciliation observed a full-prompt digest path, a compact-prompt omission, and silent empty/null fallbacks in some consumers. This remains the historical baseline for that main revision; it is not a claim about the later PR #591 branch. The branch-only source review and bounded corrections are recorded in §6D.5A. No product code is adopted by this receipt, and the branch remains unmerged.
### 6D.5A PR #591 consumer-path reconciliation (branch-only; 2026-10-31)

This subsection records source review of the separately Owner-authorized PR #591 implementation. It does not change the canonical route on `main`, authorize any runtime operation, or claim that the code has been adopted.

**Source-level coverage observed on the PR branch:**

- **Full prompt:** `AdaptiveTaskOrchestrator._control_master_digest()` obtains the state and queue, collects the same-thread queue diagnostics, and returns `UNAVAILABLE` on source/read errors. The full `SystemPromptBuilder.build()` receives that digest.
- **Compact prompt:** the small-model path calls `build_compact()` with the same digest. The shared Control Master section explicitly says `UNAVAILABLE` is not an empty queue and preserves the other valid digest fields.
- **Identity and freshness visibility:** `ControlMasterDigest` already carries `digest_id`, `source_state_id`, and `generated_at_utc`. This revision adds those fields to the shared prompt section and to the Evolution Center's Control Master brief, and adds contract assertions for both consumers. The QML view displays that brief.
- **Error visibility:** the Evolution Center refresh path collects `last_work_queue_errors`; when a configured source read fails, it sets `signal_status=UNAVAILABLE` and `work_queue_status=UNAVAILABLE` rather than presenting that result as an empty queue.
- **Manual publisher wiring:** the existing `AppBootstrap` instance wires its publisher action into `EvolutionCenterViewModel`. The QML button opens a public-disclosure dialog; only accepting that dialog invokes the slot. Normal refresh is not a publication trigger.
- **Public projection:** the projector is an allowlist, omits free text and original queue IDs, uses per-snapshot positional references, includes source/timing/expiry metadata and an integrity checksum. The publisher independently validates the payload and targets only the dedicated non-default branch.

**Test evidence and boundary:**

```text
PROJECTOR_AND_PUBLISHER_FOCUSED_TESTS=11_PASSED
TEST_FILE_BLOB=789362a24688f98b8cb3a44c3226cac557164cf1
PROJECTOR_BLOB=bd2c8627e6407e154a86c22ee4621d6d77ed2009
PUBLISHER_BLOB=27801109246ee4295b62ba99267df9e4c6573b78
EXECUTION=TEMPORARY_PYTHON_HARNESS; MINIMAL_ControlMasterState_STUB
NETWORK=NOT_USED
SECRETS=NOT_LOADED
PUBLISHER_TRANSPORT=NOT_INVOKED
```

Those 11 tests exercise the projector/publisher contracts only. The prompt-builder, work-queue integration and ViewModel tests added or updated on this branch have **not** been executed. The complete repository test suite, native PySide/QML load, build, application runtime and real local Control Master read remain unverified. GitHub reported no workflow runs or commit status checks for the reviewed head. Do not promote this result to full integration acceptance.

**Control Master intake in this coordinator session:**

- Canonical route was read from `main@a64f9e331ccbf13225ed5a3d945e16586e8756db`. The normal content read of `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` returned an empty body; the exact blob `63e1b459a13e23e1012da81826dc50727b688d8c` was then fetched successfully (1,074,956 characters).
- The active route remains `IABV_M1A_OWNER_ISSUER_MECHANISM_INPUT_GATE_R1_20261030`, with the root/issuer provenance edge blocked, `G1/G2/G3=NOT_ESTABLISHED`, `OPTION_D=RATIFIED_NO_BOOTSTRAP`, protected reads fail-closed, and no product-runtime authority. Its wait is task-local; the independent PR #591 work remains bounded by its own Owner authorization.
- The newest Control Master state snapshot found on `main`, `IABV_v1.5/data/evolution/control_master/latest.json`, has blob `d76d521e6f8d73e874a21ffe1b720dcdbcd48293`, state ID `dc840807-ef2a-4e7a-8f11-4c6362ccbcb7`, and `last_updated=2026-04-19T19:23:46.389095Z`. It predates the current task and later repository state, and contains no current prioritized queue. Classify it as `STALE`, not as the live signal.
- The dedicated `control-master-live` branch and `shared_signal.json` were not present at this observation. No authorized live local-runtime read surface was available in this session. Therefore `LIVE_RUNTIME_SIGNAL=UNAVAILABLE`; do not infer an empty queue or publish a synthetic snapshot.

**Current PR state at this receipt:** base `main@a64f9e331ccbf13225ed5a3d945e16586e8756db`; PR #591 remains open and Draft, not merged. Its source-level corrections are branch-persistent only. The PR's UI publisher is not invoked; no public signal was published. Main, Option D, M1A and the G1/G2/G3 gates are unchanged.

**Remaining §6D.5 acceptance edges:** exact-HEAD execution of the updated prompt-builder/work-queue/ViewModel tests in a full isolated project environment; native QML load/interaction verification; source/runtime timestamp and queue provenance confirmation from the real local Control Master; outcome-to-owning-objective linkage; and a later decision receipt showing whether the signal changed or confirmed action selection. The public signal branch remains uncreated until a separate deliberate UI confirmation in an authorized runtime.



### 6D.5B PR #591 publication-integrity follow-up (2026-11-01; branch-only)

This follow-up applies to the exact PR #591 candidate branch, not to `main`. The source HEAD immediately before this receipt was `1766861e7a279ee04305b22e51913e6fcb611997`; the branch remains an isolated, unmerged Draft. This is a source-level correction and test-authoring receipt, not runtime acceptance.

**Corrections made in the candidate:**

- `ControlMasterSignalProjector` now sets `source.state_observed_at_utc` from the timestamp captured when the producer projects the state/queue. It no longer substitutes `ControlMasterState.last_updated`, which describes the persisted object's modification time. The field therefore means projection observation time only; it does not independently prove that every underlying repository/cache was fresh.
- Before writing to an existing public `control-master-live` branch, the publisher fetches the current `main` tree and compares complete commit trees. The branch is rejected unless its delta from current `main` is empty or exactly `IABV_v1.5/data/evolution/control_master/shared_signal.json`. This prevents carrying unrelated pre-existing public branch changes into the publication.
- After push, the publisher checks the exact remote branch head, fetches that ref, checks the fetched commit SHA and compares the returned file bytes with the exact serialized payload. If push may have succeeded but read-back is not verified, the result is `PUBLISHED_UNVERIFIED`, not `PUBLISHED` or `BLOCKED`.
- The Evolution Center ViewModel now renders `PUBLISHED` as published-and-verified and reports `PUBLISHED_UNVERIFIED` distinctly, preserving the fact that a push may have happened without a verified remote postcondition.

**Changed source/test blob identities at this review point:**

| Path | Blob |
|---|---|
| `src/iabv_v15/services/evolution/control_master_signal_projector.py` | `7888a07d90e864058fc738bc0c653039c7f63237` |
| `src/iabv_v15/services/evolution/control_master_signal_publisher.py` | `70a9005c4a69100c32187ccfe40c0c01578c817b` |
| `tests/test_control_master_signal_projector.py` | `19b78b47201bb902918e8c571d3b069f7c4cb472` |
| `src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py` | `9f4f24a6ca075cfe8684dac3be03db32d482c927` |
| `tests/test_evolution_center_viewmodel.py` | `f1f52506041f723178813834041fec67706094b1` |

Five focused tests were added for observation-time semantics, the public-branch delta allowlist, exact remote ref/commit/content read-back, and the mismatch stop states; the ViewModel test also asserts the distinct `PUBLISHED_UNVERIFIED` presentation.

```text
SOURCE_REVIEW=STATIC_BRANCH_FETCH_BACK
TESTS_AUTHORED=5_FOCUSED_PLUS_VIEWMODEL_ASSERTION
TESTS_EXECUTED=NOT_RUN
BUILD=NOT_RUN
QML_LOAD=NOT_RUN
APPBOOTSTRAP=NOT_RUN
LOCAL_RUNTIME=NOT_OBSERVED
PUBLIC_SIGNAL_PUBLISHED=FALSE
MAIN_MODIFIED=FALSE
M1A_GATES_CHANGED=FALSE
```

**Limitations retained:** this code does not create a signature, authenticated issuer, independent trust root or M1A/G1 evidence. Observation time is not a guarantee that underlying persisted inputs were freshly regenerated. No public signal was generated or published in this review, and the real local Control Master remains unavailable. The pre-existing checksum remains an integrity checksum only. Branch-level source correction, static review and authored tests do not establish integrated runtime acceptance.

---


### 6D.5C PR #591 next-session coordination receipt (2026-11-01; branch-only)

This receipt records the latest coordinator reconciliation for continuation in a separately opened chat. It is attached to PR #591's isolated candidate branch and is **not adopted by main**. Read the live CURRENT-STATE.md from main first; this receipt supplements that canonical router and does not replace it.

**Exact source and route observations**

```text
OBSERVED_AT=2026-11-01 (America/Bogota; GitHub metadata fetched in this session)
MAIN_SHA=a64f9e331ccbf13225ed5a3d945e16586e8756db
CURRENT_STATE_PATH=IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md
CURRENT_STATE_BLOB=63e1b459a13e23e1012da81826dc50727b688d8c
CURRENT_STATE_NORMAL_READ=EMPTY_BODY; EXACT_BLOB_FETCHED
D021_MAIN_BLOB=b0c262730794a8f27b2f9815bfeda3e119cbb327
M1A_ACTIVE_TASK=IABV_M1A_OWNER_ISSUER_MECHANISM_INPUT_GATE_R1_20261030
M1A_OPEN_EDGE=OWNER_ROOT_DECISION_AUTHENTICATION_AND_ROOT_HANDLE_PROVENANCE_NOT_ESTABLISHED
OWNER_INPUT_RECONCILED=NO_ADDITIONAL_MECHANISM_IDENTIFIED
G1/G2/G3=NOT_ESTABLISHED
G4/G5/G6/G7/G8=OPEN; NONE_CLOSED
OPTION_D=RATIFIED_NO_BOOTSTRAP
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
C:/Python=DO_NOT_TOUCH
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
TESTS/BUILD/RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

The canonical route is task-local: M1A/G1 remains blocked, but this is not a project-wide stop. Do not ask the Owner to repeat the Entra/Authenticator setup or identify another mechanism. No new independent root/issuer evidence was received in this continuation.

**PR #591 live state and source identity**

```text
PR=591
URL=https://github.com/jhonf463r/Python/pull/591
STATE=OPEN; DRAFT=TRUE; MERGED=FALSE
BASE=main@a64f9e331ccbf13225ed5a3d945e16586e8756db
SOURCE_HEAD_AT_START_OF_THIS_RECEIPT=3cf320140733e3fc99171fd4ba25951dfbd88324
COMPARE_AT_START=ahead_72; behind_0; 15_changed_files
PR_REVIEWS=0
INLINE_REVIEW_THREADS=0
COMBINED_STATUS_CHECKS=0
CHECK_RUNS=0
PR_TRIGGERED_WORKFLOW_RUNS=0
CONTROL_MASTER_LIVE_BRANCH=NOT_FOUND
PUBLIC_SIGNAL_PUBLISHED=FALSE
```

GitHub reports 72 sequential connector-generated commits on the candidate branch; this is not 72 independent deliverables. Review the final file diff and exact final source, not commit count. The prior 11-passed claim in the PR description is bound to earlier projector/publisher/test blobs (bd2c8627e6407e154a86c22ee4621d6d77ed2009, 27801109246ee4295b62ba99267df9e4c6573b78, 789362a24688f98b8cb3a44c3226cac557164cf1) and **does not validate the final HEAD**.

**Final source blobs statically fetched in this continuation**

| Path | Blob |
|---|---|
| src/iabv_v15/services/evolution/control_master_signal_projector.py | 7888a07d90e864058fc738bc0c653039c7f63237 |
| src/iabv_v15/services/evolution/control_master_signal_publisher.py | 70a9005c4a69100c32187ccfe40c0c01578c817b |
| src/iabv_v15/services/evolution/control_master_service.py | 3b2605d0e0a12c5e3f0601a01c9b944c907692d1 |
| src/iabv_v15/bootstrap.py | a1bbc4ecf73448b82ea9aae99e8fdeade3592868 |
| src/iabv_v15/services/llm/system_prompt_builder.py | e76ea07d8afb6490846479ae2585459eaba3b42d |
| src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py | 9f4f24a6ca075cfe8684dac3be03db32d482c927 |
| src/iabv_v15/ui/qml/pages/EvolutionCenterPage.qml | c4568020e4d051e810f75f459f9d159873cc5e22 |
| tests/test_control_master_signal_projector.py | 19b78b47201bb902918e8c571d3b069f7c4cb472 |
| tests/test_canonical_work_queue.py | dcf8dd70bac73b7d7d70c0e5f31904bb5188d5ef |
| tests/test_evolution_center_viewmodel.py | f1f52506041f723178813834041fec67706094b1 |
| tests/test_system_prompt_builder.py | 4c0529988ac6b3a1782497284e5d8ffbce1f63a7 |

**Adjudicated static findings**

- The observation timestamp, existing-public-branch tree allowlist, exact post-push ref/commit/byte read-back and distinct PUBLISHED_UNVERIFIED ViewModel result are present in the exact fetched source blobs.
- AppBootstrap statically constructs and wires the objective repository, pending-issue repository, operational self-examination service, platform pending queue and workspace root into ControlMasterService. This is source wiring only; it does not prove runtime reads succeed.
- Some ControlMasterService readers accept optional dependencies and return no items when a dependency is absent; configured-but-failing/unsupported readers in several paths do record diagnostics. The main AppBootstrap path inspected wires those main dependencies. A missing runtime_audit.jsonl is treated as no audit items. This review did not establish a false-empty queue in the main composition: record it as REVIEW_NOTE; NO_CONFIRMED_DEFECT, not as a reason to patch speculatively.
- The manual QML confirmation dialog discloses the public destination and payload limits. Static source presence does not prove QML loads or the action works in the native UI.

**Validation boundary and next discriminating action**

```text
STATIC_SOURCE_FETCHBACK=VERIFIED_FOR_LISTED_BLOBS
NEW_TESTS_AUTHORED=VERIFIED
FINAL_HEAD_TESTS_EXECUTED=NOT_RUN
FULL_SUITE=NOT_RUN
BUILD=NOT_RUN
APPBOOTSTRAP_RUNTIME=NOT_RUN
QML_LOAD_AND_INTERACTION=NOT_RUN
LIVE_CONTROL_MASTER_READ=UNAVAILABLE
PUBLIC_SIGNAL_PUBLICATION=NOT_RUN
MAIN_MODIFIED=FALSE
PR_591_MERGE=NOT_AUTHORIZED
```

No authorized project test runner was available through this coordination session. The next action is **not another source rewrite**: obtain/use an already-authorized isolated project runner and execute, against the exact final PR HEAD, the four focused suites:

1. tests/test_control_master_signal_projector.py
2. tests/test_canonical_work_queue.py
3. tests/test_system_prompt_builder.py
4. tests/test_evolution_center_viewmodel.py

Record interpreter/version, exact commands, test counts, exit codes, logs and tested HEAD. Then adjudicate each result separately. Only after these pass should an authorized native QML/AppBootstrap integration check be considered. Do not invoke the publisher, create control-master-live, access local/protected stores, start runtime, touch C:/Python, change permissions/tunnels, merge any PR, or infer M1A/G1 closure.

**Other open PRs were inspected but not modified:** #592 is open Draft at 73300951298fd9e03f20aa3b2a94aa965ed3c33e; its two-test/smoke pass is recorded in its PR body as actor-reported, not re-executed here. #589 is open, targets an older base f39daa5231c5c85c83a7545879aa522286525fef, and GitHub reports mergeable=false; mergeable_state=dirty. It must be reconciled with current main before any review/merge decision. Neither PR is authorized to merge by this receipt.

**Cross-session instruction:** the next chat must fetch live main and its exact CURRENT-STATE.md blob first, then fetch PR #591 and this D021 branch receipt at the PR's live HEAD. Record that the receipt is branch-persistent only until adopted. Do not ask the Owner to repeat settled inputs. The receiver must independently acknowledge retrieval and state whether this receipt changed or confirmed the chosen action; do not claim automatic boot or causal reuse.

---

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


### 6D.5D M1A G1–G3 live-main source reconciliation (2026-11-01; branch-only)

This receipt records the Owner's request for a deep reconciliation of the path toward the governed IABV bridge. It supplements the canonical router; it does not replace or amend `CURRENT-STATE.md` on `main`. The new evidence is a bounded static comparison of the exact live-main source against the existing PR #531 authorization-organ candidate.

#### Exact inputs fetched

- Canonical `main`: `a64f9e331ccbf13225ed5a3d945e16586e8756db`.
- Canonical `CURRENT-STATE.md` blob: `63e1b459a13e23e1012da81826dc50727b688d8c`; recovered by exact blob after the ordinary content fetch returned an empty body.
- Main `bootstrap.py`: blob `e4befa6b683fc87aed7481f377f1332f5753e2c3`.
- Main MCP `server.py`: blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`.
- Main `mcp_bridge_service.py`: blob `340c8f88e198655be86b874fd14c102d486bf8fd`.
- Main evidence matrix: `CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md`, blob `1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37`.
- M1A acceptance/dual-track receipt: blob `239efe95c0451e61147eeed72b6b66858b83531d`.

#### Finding A — canonical main does not demonstrate M1A authorization in the current MCP read/list handlers

Static source observations at the exact main SHA:

1. `AppBootstrap` constructs the MCP bridge through `build_mcp_bridge_service(self, workspace_root=self.config.workspace_root)`.
2. The builder accepts the container and workspace root plus transport/bind settings; the reviewed composition does not inject a `ReadAuthorizationCoordinator`, G1 trust/mandate producer, G2 policy producer or G3 target resolver.
3. Main's `read_repo_file` and `list_repo_directory` handlers call `_governance_block_for_route(assistant_kind="audit", requires_network=False)`. If it returns no block, the handlers call the path-based `audit_tools` readers.
4. That route gate evaluates a World Model snapshot, network state, active block records and permission gates filtered by `assistant_kind`. The inspected handler/gate path does not derive a versioned G3 operation-to-target binding, does not ask an M1A issuer for a typed decision, and does not bind that decision to the same opened native object consumed by the reader.

Adjudication: `MAIN_SOURCE_M1A_READ_LIST_INTEGRATION=NOT_DEMONSTRATED`. This is a source-to-route discrepancy against the normative `PROTECTED_READS=FAIL_CLOSED` posture. The required policy remains deny; however, this static review cannot claim that main's current read/list handlers enforce the M1A organ. Actual runtime activation/behavior was not inspected or invoked and remains `NOT_VERIFIED`.

#### Finding B — PR #531 contains a partial fail-closed organ candidate, not production authority

Live PR #531 was re-fetched and compared against main:

- State: `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`.
- Base SHA: `7ddfe285b1a3267f9ef6f57f862cca78bc8438c2`.
- Candidate HEAD: `bc2baf525a70d66628809360a197f25a069aa328`.
- Compare to current main: `ahead_by=17`, `behind_by=179`; 13 changed paths. No review submissions or inline threads were present in the queried review collections.
- Candidate `bootstrap.py` blob: `802f1b42881f383d9ac33fea8ee6c2c913a4da32`.
- Candidate `read_authorization.py` blob: `3a57d1148c175040b7b747a6e04411c542c51dd3`.
- Candidate MCP `server.py` blob: `af0d95dd27172685a04e28f51d8bdc97c4f00b32`.
- Candidate `windows_handle_reader.py` blob: `cf3045be70e6824bdcc627ccefa14ea33faf6342`.

The candidate declares typed G1/G2/G3/issuer/replay interfaces. Its `ReadAuthorizationCoordinator.unconfigured()` sets all eight required production dependencies to `None`; `missing_requirements()` enumerates the missing independent trust root, Owner mandate, merge evidence, G2 policy provider, G3 resolver, authenticated issuer IPC, replay consumer and host-owned process identity. This is explicit deny-only composition, not an operational authority chain.

The candidate read/list handlers do have a useful same-object source path: they obtain an `OpenedTargetCapability`, pass that same capability to the authorization decision and then pass it to the handle reader. This advances the G3 enforcement contract at source level. It does not supply the production approved-workspace-root provider, a concrete authoritative versioned target resolver or any of the independent authority producers. Synthetic/source-level structure does not prove native Windows behavior.

A corresponding detailed static reconciliation was also recorded in [PR #531's conversation](https://github.com/jhonf463r/Python/pull/531#issuecomment-6568862657). It is not a formal review approval and it does not change the branch or its merge status.

#### Gate disposition and dependency order

```text
MAIN=a64f9e331ccbf13225ed5a3d945e16586e8756db
MAIN_M1A_READ_LIST_INTEGRATION=NOT_DEMONSTRATED
PR531=OPEN_DRAFT_UNMERGED; BASE_STALE; 17_AHEAD_179_BEHIND
PR531_SOURCE=PARTIAL_FAIL_CLOSED_CONTRACT; NOT_CANONICAL
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=PARTIAL_SOURCE_CONTRACT; PRODUCTION_ROOT_AND_RESOLVER_NOT_ESTABLISHED
G4_G8=OPEN; NONE_CLOSED
OWNER_INPUT_RECONCILED=NO_ADDITIONAL_INDEPENDENT_MECHANISM
OPTION_D=RATIFIED_NO_BOOTSTRAP
TESTS=NOT_RUN_IN_THIS_RECONCILIATION
BUILD=NOT_RUN
RUNTIME=NOT_RUN
PROTECTED_READS_POLICY=FAIL_CLOSED_REQUIRED
MAIN_HANDLER_ENFORCEMENT=NOT_DEMONSTRATED
TUNNEL=NOT_ACTIVATED_BY_THIS_TASK
MERGE_REBASE=NOT_AUTHORIZED
```

Causal order remains:

1. **G1 first:** independently verifiable root provenance/custody, legitimate Owner/governance mandate and authenticated identity binding to the issuer, host principal and exact server instance. The already-reconciled Entra/Authenticator setup is not to be repeated and does not by itself prove this chain.
2. **G2 second:** an authorized publisher and versioned catalogue/active set bound to G1; producer-class policy; integrity; freshness/expiry; authoritative revocation; and rollback-resistant lifecycle.
3. **G3 third:** a server-side versioned registry mapping actual registered operation IDs and implementation/call sites to approved canonical targets; a production approved-root provider; and evidence that authorization and the reader consume the same identity-bearing open object.

Do not create more interfaces or repeat the old broad R1/R5 inventories. Do not rebase or merge PR #531 merely because its source contract is useful: first reconcile its 179-commit divergence against the current main under a separately scoped authorization. Do not interpret PR #576's unmerged enrollment proposal as permission to create a key, manifest or enrollment effect. The Control Master signal work in PR #591 is a separate coordination surface and is not the M1A protected-read authority bridge.

#### Method, authorization and limitations

This task used read-only GitHub fetches for exact public source revisions and one traceability comment on PR #531. It did not access `C:/Python`, local or protected stores, secrets, credentials, the live runtime or issuer; it did not invoke MCP, publish a signal, activate a tunnel, execute tests/builds, edit product source, rebase or merge a PR. No new independent G1 authority evidence was received.

The canonical main route remains the sole router. This section is persisted on the PR #591 branch only, for cross-session retrieval; it is not adopted in main. The independent M1A/G1 wait is task-local and does not imply a project-wide stop, but no separate authorized action was invented by this receipt.

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

### 6E.7 Owner friction rule

The coordinator performs retrieval, reconciliation, source navigation, file comparison, and handoff assembly whenever the current tools and permissions permit. The Owner should perform only the one-time ChatGPT Project configuration that cannot be changed by an assistant tool, or provide an exact local-only artifact when no authorized connector exists. Do not repeatedly request manual export/upload for the same stable artifact once it is stored in the Project or repository.

**Official product behavior references checked 2026-10-31:**
- Projects in ChatGPT: https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- Connecting GitHub to ChatGPT: https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- Connected apps in ChatGPT: https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt
- Memory in ChatGPT: https://help.openai.com/en/articles/8590148-memory-in-chatgpt

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

### 6D.5E Authenticator app observation and no-repeat correction (2026-11-02; branch-only)

**Triggering Owner observation:** the Owner reports that the already-installed Microsoft Authenticator app currently shows only the email address for the previously created `IABV Owner` account. The Owner is not reporting a visible Passkey/FIDO2 entry inside the app. This is a fresh UI observation, not evidence that the Entra account has no registered passkey, nor evidence that a passkey exists.

**Correct evidence classification:**
- `ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY` remains the previously reconciled setup fact; do not ask the Owner to reinstall Authenticator, recreate the account, repeat enrollment, or reconfirm the already reported successful sign-in.
- `AUTHENTICATOR_APP_ACCOUNT_TILE=OWNER_REPORTED_VISIBLE`.
- `AUTHENTICATOR_APP_VISIBLE_METHOD_DETAILS=NOT_OBSERVED`.
- `ENTRA_REGISTERED_AUTHENTICATION_METHODS=NOT_INDEPENDENTLY_VERIFIED`.
- `PASSKEY_FIDO2_REGISTRATION=UNKNOWN`; an email/account tile alone neither confirms nor rules out FIDO2.
- `OWNER_AUTHORITY_MANDATE=NOT_ESTABLISHED`; `ISSUER_HOST_BINDING=NOT_ESTABLISHED`; M1A/G1 remains blocked.

**Correct next-step selection (read-only, no setup loop):**
1. Do not ask the Owner to find a Passkey inside the Authenticator account tile. The app's visible account/email entry is not the authoritative inventory of Entra-registered methods.
2. Use the Owner-facing Microsoft Security Info portal `https://mysignins.microsoft.com/security-info` with the already known `IABV Owner` account. Inspect the registered methods list only; do not add, delete, reset or re-register any method during this observation step.
3. Classify the exact entries separately: `Microsoft Authenticator` indicates the registered Authenticator method; `Passkey (FIDO2)` indicates a registered FIDO2 credential; `Microsoft Passwordless phone sign-in` is a distinct passwordless method and must not be relabeled as FIDO2. If the portal lists only Authenticator, record FIDO2 as `NOT_OBSERVED_IN_OWNER_PORTAL`, not as globally absent.
4. If stronger tenant-side confirmation is needed and the Owner already has an authorized administrative role, inspect the Entra user Authentication methods page or the Authentication Methods Activity registration report. Do not assume the Owner has the required role or license, request role elevation, or change tenant policy. The report can lag; record its observation time and limitations.
5. Only after the read-only inventory establishes that FIDO2 is absent and a concrete need is justified may the coordinator assess the tenant's existing Passkey (FIDO2) policy and supported authenticator profile. Do not opt in to passkey profiles, enable policies, create a credential, or alter Conditional Access without a separate exact scope/authorization; profile opt-in can be non-reversible.
6. A Passkey/FIDO2, if present, is a phishing-resistant authentication credential, not by itself a free-form digital signature or an IABV authority mandate. Any future Owner decision flow must bind a fresh challenge to the exact decision digest, relying-party/server identity and intended scope, and independently verify the credential assertion. Entra token validation, Owner mandate, issuer identity, host identity and server-instance binding remain separate checks.

**Protocol correction:** the coordinator must recover the Owner-input ledger and prior setup facts before asking anything; interpret app UI observations narrowly; select the authoritative read-only evidence surface; and ask for only the single unresolved observation that changes the next action. Never transfer a known investigation step back to the Owner as an open-ended request to diagnose or design the security mechanism.

**Source basis:** current Microsoft documentation for [Security Info](https://mysignins.microsoft.com/security-info), [Authentication Methods Activity](https://learn.microsoft.com/entra/identity/authentication/howto-authentication-methods-activity), and [Passkeys (FIDO2)](https://learn.microsoft.com/entra/identity/authentication/how-to-authentication-passkeys-fido2), checked 2026-11-02. This subsection is a branch-only coordination correction; it does not alter canonical `main`, provision credentials, authorize tenant-policy changes, establish G1, or enable protected reads.

#### 6D.5E.1 Exact Security Info inventory (2026-11-02; Owner-reported)

The Owner inspected the existing Security info page for the already-created `IABV Owner` account and reported the visible methods:
- `Password`.
- `Microsoft Authenticator — MFA` (the page's registration label identifies the notification/code MFA registration).

No `Passkey (FIDO2)` entry was visible in the reported inventory. Classify:
- `SECURITY_INFO_PASSWORD=OWNER_REPORTED_VISIBLE`.
- `SECURITY_INFO_AUTHENTICATOR_MFA=OWNER_REPORTED_VISIBLE`.
- `SECURITY_INFO_PASSKEY_FIDO2=NOT_OBSERVED_IN_REPORTED_INVENTORY`.
- `ENTRA_REGISTERED_FIDO2=UNKNOWN` pending authoritative tenant-side verification; do not overstate the portal observation as proof that no credential exists anywhere.
- `OWNER_IDENTITY_MFA=OWNER_REPORTED_READY`; `OWNER_DECISION_SIGNATURE=NOT_ESTABLISHED`; `G1=NOT_ESTABLISHED`.

**Next single bounded observation:** the Owner may open `Add sign-in method` only to view the offered method names, then cancel/close without selecting, registering, deleting or changing anything. Record whether `Passkey` / `Passkey (FIDO2)` is offered. If it is offered, stop before registration; assess the exact method type and allowed passkey provider first. If it is not offered, do not assume the user can enable it from Security info: tenant-side Passkey (FIDO2) policy and targeting may need an appropriately authorized Authentication Policy Administrator. Do not instruct the Owner to enable policy, opt into passkey profiles, modify Conditional Access, or register a credential under the current no-bootstrap boundary.

**Important interpretation:** Microsoft documents that the Security info registration label `Microsoft Authenticator: (Notification/Code)` represents an MFA registration, distinct from `Microsoft Authenticator: Passwordless phone sign-in`. Neither label is equivalent to an Entra `Passkey (FIDO2)` credential. The current Owner-reported screen therefore confirms Authenticator MFA, not FIDO2 or a digital signature.

**Microsoft source basis checked 2026-11-02:** [Authenticator registration types](https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-authenticator-app); [register a FIDO2 passkey with a security key](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-register-passkey-with-security-key); [enable Passkey (FIDO2) policy](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-authentication-passkeys-fido2). This is a branch-only continuity update. It does not change canonical `main`, configure Entra policy, create credentials, satisfy G1, or authorize protected reads.

#### 6D.5E.2 Owner-provided Entra passkey option screen (2026-11-02; pre-registration)

The Owner supplied a screenshot of the Security info "Add a sign-in method" chooser. The visible options are:
1. `Passkey in Microsoft Authenticator` (Spanish UI: `Clave de paso en Microsoft Authenticator`; label says sign in with face, fingerprint or PIN).
2. `Passkey` (generic passkey provider/security key flow).
3. `Microsoft Authenticator` (MFA approval or one-time codes).

**Evidence:** `OWNER_REPORTED_SCREENSHOT_VISIBLE` for all three offered options. This confirms the user-facing registration flow currently offers the Authenticator-specific passkey route. It does not yet prove that a credential has been created, accepted by Entra, registered on the authentication server, or usable for sign-in.

**Chosen route for guided Owner enrollment:** option 1, `Passkey in Microsoft Authenticator`, because the Owner already reported that the dedicated `IABV Owner` account is present in the existing Authenticator app. Do not select the generic Passkey option or the old MFA option for this specific enrollment. Microsoft documentation says Authenticator passkeys are device-bound and hardware-backed (iOS Secure Enclave; Android Keystore with supported secure hardware); they do not sync to another phone. Keep the current password and MFA method as fallback and do not delete them.

**Registration procedure:** the Owner starts the Authenticator-specific option from Security info; completes any fresh MFA challenge; follows the browser/app handoff to the existing Authenticator account; creates the passkey in Authenticator using the device screen lock/biometric/PIN; returns to the browser and completes server-side verification. The procedure may require Android 14+ or iOS 17+. A method is counted as registered only after Security info displays the resulting passkey entry and the registration flow confirms completion. A locally created but server-unregistered credential is not accepted as proof.

**Security and evidence boundary:**
- `PASSKEY_AUTHENTICATOR_OPTION=OWNER_REPORTED_VISIBLE`.
- `PASSKEY_AUTHENTICATOR_REGISTRATION=NOT_YET_PERFORMED`.
- `PASSKEY_AUTHENTICATOR_SERVER_ACCEPTANCE=NOT_ESTABLISHED`.
- `OWNER_AUTHENTICATION_MFA=OWNER_REPORTED_READY`.
- `OWNER_DECISION_SIGNATURE=NOT_ESTABLISHED`.
- `ISSUER_HOST_BINDING=NOT_ESTABLISHED`.
- `M1A_G1=NOT_ESTABLISHED`.

The passkey authenticates the Owner to Microsoft Entra; it is not itself a digital signature of an arbitrary IABV authority decision, does not create the IABV root of trust, and does not bind an issuer, Windows principal or exact server instance. Those validations remain separate. This is a branch-only continuity receipt and does not modify canonical `main` or authorize product runtime/protected reads.

**Microsoft source basis checked 2026-11-02:** [Register passkeys in Authenticator](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-register-passkey-authenticator); [Authenticator passkey requirements and policy](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-enable-authenticator-passkey); [Passkey FAQ and device-bound storage](https://learn.microsoft.com/en-us/entra/identity/authentication/passkey-faq).

#### 6D.5E.3 Safety correction — visible option is not enrollment authorization (2026-11-02)

The Owner's screenshot establishes that the Security info UI offers `Passkey in Microsoft Authenticator`. The prior coordinator instruction to select it and proceed with registration was premature because it did not first reconcile the active canonical no-bootstrap boundary.

**Controlling rule:** `OPTION_D=RATIFIED_NO_BOOTSTRAP` and D021 §8 excludes creation of Entra registrations/authority assets unless the canonical route is explicitly changed by an authorized, sufficiently scoped decision. A visible menu option proves availability in the UI, not permission to register. Therefore:
- `PASSKEY_AUTHENTICATOR_OPTION=OWNER_REPORTED_VISIBLE`.
- `PASSKEY_AUTHENTICATOR_REGISTRATION=NOT_AUTHORIZED_UNDER_CURRENT_ROUTE`.
- `PASSKEY_AUTHENTICATOR_SERVER_ACCEPTANCE=NOT_ESTABLISHED`.
- `OWNER_MFA=OWNER_REPORTED_READY`.
- `OWNER_DECISION_SIGNATURE=NOT_ESTABLISHED`.
- `G1=NOT_ESTABLISHED`; `PROTECTED_READS=FAIL_CLOSED`.

**Immediate operator correction:** do not select the option, create/register a passkey, alter Entra authentication policy, change Conditional Access, request admin-role elevation, remove existing MFA/password methods, or change any host/runtime setting under the current route. Leave the chooser and existing account methods unchanged. The first option remains a technically plausible future phishing-resistant Owner-authentication method, but it is neither an IABV root nor an arbitrary decision-signing credential.

**What must change before enrollment can be proposed:** the canonical active route must identify an exact Owner-authorized, bounded Entra registration action; its target tenant/account, specific credential type, platform prerequisites, permitted side effects, rollback/recovery, expected server-side registration evidence and post-enrollment test must be defined. The route owner must explicitly authorize that exact mutation. A generic request to "help establish trust", a visible option or a successful MFA event cannot silently override the ratified no-bootstrap decision.

**Why this correction matters:** Authenticator MFA/Passkey can authenticate a human to Microsoft Entra; it does not by itself issue a signed IABV authority mandate, prove custody/provenance of an IABV trust root, authenticate the IABV issuer, or bind the issuer to the exact Windows principal and server instance. Do not claim G1 closure from passkey enrollment alone.

**Incident classification:** `COORDINATOR_ERROR=ADVANCED_OWNER_MUTATION_BEFORE_ACTIVE_ROUTE_AND_AUTHORIZATION_PREFLIGHT`; `CORRECTION=PAUSE_REGISTRATION_AND_ADD_PRE_ACTION_DECISION_BUNDLE_TO_D019_D020`; `PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED`; `AUTOMATIC_FOLLOW_ON=FALSE`. This subsection supersedes any earlier procedural wording in §6D.5E.2 that appears to direct immediate registration. It is branch-only and does not modify canonical `main`.
