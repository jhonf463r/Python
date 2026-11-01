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

## 6E. ChatGPT native project context and cross-agent artifact transport (2026-10-31)

### 6E.1 Purpose and boundary

Use ChatGPT's native Project as the shared context surface for participating ChatGPT conversations, not as another IABV memory or router. A Project can provide its chats with the same Project instructions, files and conversations. Project-only memory keeps IABV chat context scoped to that Project; in shared Projects, project-only memory is applied automatically. A chat outside the Project does not gain access to its private chat context. The Project does not automatically share its contents with Codex, Claude, another provider, an unrelated ChatGPT Project or the Owner's local filesystem.

For cross-product collaboration, continue using the owning project repository as the common versioned store, provided the receiving AI has an authorized connector or exact repository access. Do not create another coordinator, message bus, knowledge base or competing state file.

### 6E.2 One-time ChatGPT configuration

For IABV ChatGPT work, the recommended owner-side setup is:

1. Create or designate one Project named IABV — Coordinación compartida.
2. Add the copy-ready text from CHAT-ARCH-2026-10-31-CHATGPT-PROJECT-INSTRUCTIONS-R1.md to that Project's instructions.
3. Prefer Project-only memory for separation from unrelated projects, if the setting is available. The account's required memory/reference settings must be enabled for the selected memory mode to work.
4. Move existing IABV chats into this Project when the UI permits; create all new IABV ChatGPT chats from inside it. A chat created with a custom GPT may not be movable; start a replacement chat inside the Project and use the canonical GitHub boot instead of copying an entire transcript.
5. Connect/authorize the GitHub app for jhonf463r/Python in every account/session that needs repository access. Do not assume one collaborator's app authorization or credentials transfer to another collaborator.

Do not put this IABV policy in global Custom Instructions when that would contaminate unrelated project work. Project instructions take precedence within their Project, but they remain guidance and do not override platform/system policy, app availability, tool permissions, Owner gates or fail-closed rules.

### 6E.3 Artifact retrieval ladder — eliminate avoidable manual transfer

Before asking the Owner for an upload, pasted text, local export or repeated explanation, check in this order:

1. The current ChatGPT Project's shared Sources/files and relevant chats, when this chat is actually inside the IABV Project.
2. The connected, authorized GitHub repository; retrieve the exact canonical file/ref/commit and verify its revision, rather than relying on a remembered link or copied excerpt.
3. Another already-connected, authorized project source/connector that can retrieve the exact artifact and preserve its provenance.
4. Only then, request one precisely identified artifact from the Owner, and only when evidence establishes that it exists solely in a local/runtime location not exposed through an authorized connector or controlled bridge. Explain the missing route; never ask for a whole project export when one file/field is sufficient.

If GitHub/project retrieval is available, do not make the Owner act as a manual courier between ChatGPT chats. Use the common source directly and report what was actually retrieved. If a tool is not present in the receiving session, classify the capability as unavailable; do not pretend a prompt or Project instruction can install the tool.

### 6E.4 Distinguish file sharing from live runtime synchronization

Use these separate channels:

- CHATGPT_PROJECT_SHARED_CONTEXT: Project instructions, files and chats accessible to participating ChatGPT chats in that Project.
- GITHUB_CANONICAL_STORE: versioned, source-bound records available to any AI that has an authorized repository route.
- CONNECTED_APP_SOURCE: content returned on demand by a connected app; availability and scope depend on that session's app access and permissions.
- LOCAL_RUNTIME_SOURCE: local application/database/files/processes; not visible to a cloud chat unless an explicitly supported, authorized connector or bridge exposes them.
- CROSS_PRODUCT_HANDOFF: a correlated, published artifact in the shared repository or another agreed authorized store; a prompt, link or PR alone does not prove receipt or application.

ChatGPT's GitHub app is documented as on-demand retrieval, not a continuously synchronized GitHub index or local-runtime feed; its availability varies by plan, workspace and product surface. The standard GitHub app may be read-only. Use only the write-capable tool actually exposed and authorized in the current session; do not infer write capability from read access.

A Project therefore removes repeated uploading of shared project material, but does not make a live local Control Master digest appear automatically. If the live digest exists only inside the Owner's local runtime and no authorized reader/bridge publishes it, mark it UNAVAILABLE/UNVERIFIED; do not substitute the stale latest.json/md, start the runtime, access protected data or bypass M1A gates. An authorized future bridge/export would require its own security and scope approval.

### 6E.5 Receipt and no-claim rules

Record the transport state separately:

SOURCE_IDENTIFIED -> ARTIFACT_RETRIEVED -> REVISION_VERIFIED -> CONTEXT_AVAILABLE -> RECEIVER_ACKNOWLEDGED -> DECISION_BOUND -> OUTCOME_VERIFIED -> CANONICAL_FETCHBACK.

- A shared Project/file/link means AVAILABLE, not necessarily RETRIEVED or CONSUMED.
- A connector read proves retrieval only for the current session and exact returned source/ref.
- A receiving chat's correlated receipt is evidence of acknowledgement; its explanation of decision influence is needed to claim application.
- A verified outcome and canonical fetch-back are separate from receipt/application.
- Never claim automatic delivery, automatic boot, model-weight learning, or cross-vendor synchronization from Project membership, a commit or a link.

### 6E.6 Owner friction rule

The coordinator performs retrieval, reconciliation, source navigation, file comparison, and handoff assembly whenever the current tools and permissions permit. The Owner should perform only the one-time ChatGPT Project configuration that cannot be changed by an assistant tool, or provide an exact local-only artifact when no authorized connector exists. Do not repeatedly request manual export/upload for the same stable artifact once it is stored in the Project or repository.

**Official product behavior references checked 2026-10-31:**
- Projects in ChatGPT: https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- Connecting GitHub to ChatGPT: https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- Connected apps in ChatGPT: https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt
- Memory in ChatGPT: https://help.openai.com/en/articles/8590148-memory-in-chatgpt
