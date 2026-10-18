# IABV UAAL — R10 v0.7.5 reconstructed contract (documentary repair candidate)

**Artifact ID:** `R10_V0_7_4_CONTRACT`  
**Classification:** `RECONSTRUCTED_FROM_REVIEW` + `PROPOSED`  
**Governance:** `KEEP_BLOCKED`  
**Purpose:** repair D1–D6 from the independent static audit of the v0.7.1 reconstruction.  
**Review state:** `PENDING_INDEPENDENT_DELTA_REVIEW`; no execution/test/runtime claim.

## 0. Source provenance and supersession

The literal R10 v0.6 contract and its original test matrix remain `NOT_RECOVERED`. The earlier reference named `R10_V0_7_RECONSTRUCTED_CONTRACT_REFERENCE.md` with claimed SHA `5babd981…` was absent from v0.7.3 and is `NOT_RECOVERED`; it is not relied upon. Included `v0.7.2/R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md` SHA-256 is `107746aeb02cbf52d736f438cb466b013f66696545b9934b111458ce990ede9e` and is non-normative. The independent v0.7.1 audit report is the accompanying file `R10_V0_7_1_AUDIT_REPORT_CLAUDE.md` and remains a report of static reasoning, not runtime evidence.

This v0.7.5 artifact is a **new reconstructed normative contract**, not the original v0.7.1 from another chat and not a byte-faithful correction of v0.6. Its test IDs T123–T240 are defined only by `R10_V0_7_5_TEST_MATRIX_T123_T240.csv`. That CSV is the sole normative test-ID registry for this package. Historical reference tests are not normative and must use the prefix `REF_V07_` whenever cited.

Provenance states: `RECOVERED` means bytes were available for inspection; `RECONSTRUCTED_FROM_REVIEW` means derived from the supplied review; `PROPOSED` means newly specified; `OWNER_REPORTED` means reported but not independently inspected; `UNPROVEN` means a technical capability has not been demonstrated. No document, test definition, or hash alone proves runtime behavior.

## 1. Normative vocabulary and identities

### 1.1 Distinct entities and IDs

Every accepted entity gets an immutable store-assigned ID. Producers provide stable event identity but do not choose `result_id`, `evaluation_id`, `contribution_id`, `effect_plan_id` or `task_seq`.

Required identities:

- `task_id`: logical objective.
- `execution_id`, `attempt_no`: one particular attempt.
- `dispatch_id`, `dispatch_nonce`, `dispatch_turn_id`: one authorized dispatch and its authenticated origin turn.
- `producer_event_id`: stable producer-side identity for a delivery.
- `turn_id`, `in_reply_to_turn_id`, `destination_session_id`: platform-attested response identity and parent relation.
- `capture_id`, `attachment_id`, `result_id`: distinct automatic capture, manual attachment, and stored result.
- `criteria_bundle_id`, `criteria_bundle_digest`, `check_set_digest`, `validation_policy_digest`, `canonicalization_version`, `eligibility_policy_version`, `selection_policy_id/digest`.
- `validation_id`, `evaluation_id`, `supersedes_evaluation_id`, `restores_event_id`.
- `strategy_lineage_id`: stable grouping for versions of a strategy.
- `result_lineage_id`: stable identity for one captured result lineage, unchanged by evaluation revisions of that same result; distinct result lineages remain distinct even when they use the same strategy or have identical bytes.
- `destination_id`, `contribution_kind`, `contribution_id`, `source_evaluation_id`, `effect_plan_id`, `tombstone_id`, `conflict_id`.
- `authorization_generation` and `projection_generation`, which are separate counters and must never be aliased.
- `task_seq`: store-assigned monotonic order comparable only within one `task_id`; there is no cross-task sequence tie-break.

An event carries `event_id`, `task_id`, affected entity IDs, `event_type`, authenticated `actor_id`, stable producer identity where required, canonical payload digest, `task_seq`, store-authenticated `accepted_at`, authorization generation, fencing token where applicable, and causal predecessor references. Producers cannot supply or rewrite store-assigned sequence/time values.

### 1.2 Metrics and projections — no ambiguous `PA` alias

The historical meaning of `PA`, and the exact literal semantics of `TS`, have not been recovered. They are not normative identifiers in this reconstructed contract. Use instead:

- `TASK_SUCCESS_COUNT`: number of logical tasks whose current adopted automatic result satisfies the frozen final-success policy, counted once per `task_id`.
- `ACTIVE_AUTO_PATTERN_CONTRIBUTION_COUNT`: number of currently visible, eligible, active automated pattern contributions; re-delivery does not add a second copy.
- `active_execution_id`: current attempt, not a success indicator.
- `current_evaluation_id_by_result`: current evaluation for one `result_lineage_id`.
- `current_task_evaluation_id`: adopted task-level evaluation pointer, which can be `null`.

These are not interchangeable. Replacing an evaluation for the same already-successful task does not increment `TASK_SUCCESS_COUNT` again. The active contribution count is a current-state projection, not a cumulative observation counter. Any historical use of `TS` or `PA` must be marked `SEMANTICS_UNRECOVERED` until its original glossary is recovered.

### 1.3 Lineages and uniqueness

`strategy_lineage_id` groups strategies and is used for analysis/routing. `result_lineage_id` scopes revisions of a single result. A strategy can have many independent result lineages. Do not use these two IDs as substitutes for one another.

For one `(destination_id, result_lineage_id, contribution_kind)`, at most one contribution may be visible/active. Successive evaluations of the same result retain the same `result_lineage_id`; their replacement contribution uses a new `contribution_id` and source evaluation. Different results from the same strategy can each contribute once under their own result lineage if separately eligible and allowed by the pattern policy. Revisions of one result cannot be double-counted.

## 2. Durable log, ordering, idempotency, and clocks

### 2.1 Task sequencer

The store atomically assigns the next `task_seq` within the `task_id` when it accepts an event. Every reducer uses the same durable event order. Sequence values local to other entities are not comparable and must never resolve a task-level winner or a semantic evaluation conflict.

The ordering of accepted events is deterministic, but arrival order alone does not settle semantic disagreement. A compare-and-set (CAS) protects pointer/version writes; it does not make two incompatible evaluations equivalent and does not authorize “highest sequence wins.”

### 2.2 Producer idempotency

For automated producer events, the uniqueness scope is `(execution_id, lane=AUTO, producer_event_id)`. For a stable identity with the same canonical digest, return `ACK_DUPLICATE` without new effects. With the same identity and a different digest, append `CONFLICT_DETECTED` with a read-visibility barrier in the same atomic acceptance operation; do not return a benign duplicate acknowledgment. An event missing `producer_event_id` is rejected at ingress as `MISSING_PRODUCER_EVENT_ID`: no `result_id`, no terminal slot, no validation, no plan, no metric change.

Digest equality is not global deduplication. Identical output digests in different tasks or executions remain separate attributed results.

### 2.3 Trusted time

The store seals `dispatched_at`, `abandon_deadline_at` and event `accepted_at`. Producer timestamps do not decide causality or abandonment. If the authoritative monotonic clock cannot be verified, operations that depend on expiry or deadlines fail closed with `CLOCK_UNAVAILABLE`.

## 3. Profiles, modes, and execution states

### 3.1 Modes and attestation

The canonical mode vocabulary is `AUTHORIZED_REAL_EXECUTION`, `DRY_RUN`, `SIMULATED`, `SANDBOX_ISOLATED`, `NO_RESULT`, and `UNKNOWN`. For an automatic result to be `BASE_ELIGIBLE`, the planned mode and independently attested observed mode must both equal `AUTHORIZED_REAL_EXECUTION`.

The dispatch record stores `planned_mode`, `execution_path_id`, attestation requirements, authorization generation and frozen criteria digest. The observed mode is attested by an independently authorized observation source. The executor or result producer cannot attest itself merely by declaring a field. A mismatch produces `MODE_MISMATCH`; missing/invalid attestation produces `MODE_UNATTESTED`; an absent or unregistered route produces `UNACCREDITED_ROUTE`.

`DRY_RUN`, `SIMULATED`, `SANDBOX_ISOLATED`, `NO_RESULT`, `UNKNOWN`, mode mismatch and unaccredited routes may be retained as isolated diagnostic records. They cannot alter automatic task success or automatic pattern projections.

### 3.2 Profiles

- `CONVERSATIONAL_CAPTURE`: needs an authenticated dispatch turn and platform-attested child response turn.
- `DIRECT_OUTPUT`: needs an output receipt from the authorized execution path with the same stable execution/dispatch identity.
- `NO_RESULT`: explicitly does not produce an automatic terminal result.

A sandbox event is not `EXECUTION_STARTED`, not a real terminal output, and not a substitute for `OUTPUT_RECEIVED` or `CAPTURE_RECEIVED`.

### 3.3 Execution state machine

Execution states: `PLANNED → DISPATCHED → EXECUTION_STARTED → RESULT_ACCEPTED`, with alternate terminal states `ABANDONED` or `SUPERSEDED`. `FAILED`, `ABORTED` and `TIMED_OUT` are not canonical R10 execution states because this contract defines no accepted event writer or transition for them. An infrastructure timeout or process crash without accepted terminal output is diagnostic evidence only; it does not create a terminal result or negative strategy learning. `ABANDONED` and `SUPERSEDED` are terminal for that execution. `TASK_REOPENED` opens a new `execution_id`; it never reopens an old execution or relabels old output.

A result whose terminal event is accepted after its execution was already `SUPERSEDED` or `ABANDONED` is rejected as `LATE_STALE` with a durable rejection record; no `result_id` is minted, no terminal slot is claimed and no evaluation/effect follows. If valid terminal output was accepted before supersession, it may remain eligible as attempt evidence, but task-winner adoption still follows the current frozen policy and CAS.

## 4. Authenticated dispatch-to-response correlation

### 4.1 Mandatory platform link for AUTO

`UNCORRELATED` is a capture-rejection disposition, never a `ResultState`. Without authenticated parent-link evidence, ingress may append durable `CAPTURE_REJECTED` diagnostics but MUST NOT allocate eligible `result_id`, AUTO slot, evaluation, contribution, or task-success effect. Later MANUAL attachment is a distinct `ATTACHED` event with new `attachment_id` and independent evidence; it cannot convert the rejected capture.

Every automatic `CONVERSATIONAL_CAPTURE` dispatch **must** possess a platform-authenticated `dispatch_turn_id` and `destination_session_id` before dispatch. These fields are not optional for automatic capture. If `dispatch_turn_id` is absent, reject before `DISPATCHED` with `DISPATCH_TURN_ID_REQUIRED`; do not mint a dispatch receipt/nonce, claim an AUTO terminal slot, create a result, or apply any effect. If the target platform cannot supply the required authenticated fields, the operation cannot use the AUTO capture profile; it must fail closed for automatic learning. A manual attachment remains separate.

The captured response must carry platform-attested (not captor-invented) `turn_id`, `in_reply_to_turn_id`, `destination_session_id` and the matching dispatch nonce/receipt. The authenticated `in_reply_to_turn_id` must equal the authenticated `dispatch_turn_id`. Enforce uniqueness `(destination_session_id, turn_id) → one execution`. Also verify dispatch receipt, captor authority, nonce, completeness, canonical digest, canonicalization version and accepted task ordering.

Nonce, session and time alone are insufficient. If the parent-turn relation is absent, unverifiable, mismatched or supplied only as an unauthenticated captor claim, record `UNCORRELATED`; do not infer correlation heuristically.

### 4.2 Terminal output slot

For AUTO, one terminal slot is keyed by `(execution_id, profile, lane=AUTO, output_ordinal=1)`. The first valid, complete and correlated terminal event accepted while the execution is eligible claims it. A different later terminal output is `EXTRA_TERMINAL_OUTPUT`; it cannot silently overwrite the first. A duplicate with same producer identity and digest is idempotent; same identity with different digest is a conflict. `MANUAL` attachments have stable `attachment_id` in a separate namespace and cannot occupy AUTO slots.

## 5. Frozen criteria and verifiable validation

Before each dispatch, the coordinator commits an immutable `criteria_bundle` with `criteria_digest`, `check_set_digest`, `validation_policy_digest`, `canonicalization_version`, `eligibility_policy_version`, profile, planned mode, execution path, abandon deadline policy and frozen selection policy/version. `DISPATCHED` must reference that bundle. Criteria cannot be frozen retroactively after dispatch.

`VALIDATION_COMPLETED` stores the **actual** `used_criteria_digest`, `used_check_set_digest`, `used_validation_policy_digest`, `used_canonicalization_version`, validator identity, validator version, execution-attestation/reference for the checks, result and per-check evidence references. `EVALUATED` must reference that validation and record the same relevant digests. All used digests/versions must equal the frozen bundle; otherwise reject the validation/evaluation with `CRITERIA_MISMATCH` and no automatic evaluation or effect.

An attested digest proves which content was named, not that the checks were actually executed. Independent evidence of validator execution remains `UNPROVEN` until demonstrated. A relaxed post-hoc criteria revision cannot make the old execution eligible. New acceptance criteria require a newly frozen bundle and a new dispatch.

## 6. Evaluation, winner selection, and conflict handling

### 6.1 Evaluation states and identities

An evaluation in `QUARANTINED` remains quarantined after barrier release. Release changes barrier visibility only; it does not mutate evaluation state or restore eligibility. Replay or pointer refresh cannot make the old evaluation current.

Evaluation states are `PENDING`, `VALIDATING`, `VALID`, `INVALID`, `INDETERMINATE`, `COMPLETED_UNVERIFIED`, `QUARANTINED`, `SUPERSEDED`, `VOIDED`. Plan or execution states cannot be reused for evaluations. Each evaluation has `evaluation_id`, stable `result_lineage_id`, `criteria_bundle_digest`, all used validation digests, `evaluation_policy_digest`, canonical output digest and—when revising—`supersedes_evaluation_id`.

Same canonical evaluation identity and same content is idempotent reuse. Same identity but different canonical content is a conflict. If two authorized validators claim the same frozen inputs but return semantically incompatible evaluation outputs, create `CONFLICT_DETECTED`; the system must not pick the highest `task_seq` or whichever CAS wins as the truth.

### 6.2 Independent resolution authority

Only an independently authorized resolver, distinct from producer and affected captor, may record `CONFLICT_RESOLVED` bound to conflict and reviewed evidence. `QUARANTINE_RELEASED` removes only the named barrier; it never activates original evaluation/contribution. Restoration requires accepted independent resolution, new evaluation/contribution IDs, same `result_lineage_id`, a new effect plan, and all current guards. Otherwise the original stays `QUARANTINED`.

A `CONFLICT_RESOLVED` or `QUARANTINE_RELEASED` event requires a separately authorized reviewer (`role=INDEPENDENT_CONFLICT_REVIEWER`) whose `actor_id` differs from the producer, validator/evaluator(s), plan owner and actor whose write caused the conflict. The reviewer records evidence refs, resolution reason, prior conflict ID, chosen interpretation, policy digest and authorization generation. If no independent authorized reviewer exists, the conflict stays quarantined. Automatic quarantine resolution is disabled in this version. `QUARANTINE_RELEASED` only removes the conflict barrier after the independent resolution is durably accepted; it does not activate an evaluation, restore a pointer, or publish a contribution. Restoration requires the separate new-evaluation/new-contribution flow in §8.3.

### 6.3 Task-level pointer

`current_evaluation_id_by_result` and `current_task_evaluation_id` are distinct. The selection policy is immutable/versioned for each applicable projection generation and specifies eligible candidates, priority and deterministic tie-breakers. Incompatible evaluations for the same result and same frozen inputs enter conflict; this is not resolved by sequence priority. `current_task_evaluation_id` is `null` when no candidate is eligible or an applicable barrier blocks adoption.

Dispatch changes `active_execution_id` only; it does not modify the task's current outcome pointer or its `projection_generation`. Adoption/invalidation updates pointer and generation through one atomic compare-and-set against the expected pointer/generation. A pointer can never refer to a superseded, voided or ineligible evaluation. `winner_generation` is replaced here by the unambiguous name `projection_generation`.

## 7. `BASE_ELIGIBLE` and outcome/pattern policy

`BASE_ELIGIBLE` is derived by the coordinator/store and is not producer-writable. It is true only when all are true:

1. current execution/task identity and attempt are valid;
2. execution reached `EXECUTION_STARTED` and accepted a complete terminal result;
3. AUTO correlation and terminal slot checks passed;
4. `planned_mode = observed_mode = AUTHORIZED_REAL_EXECUTION`, backed by required attestations;
5. execution path is accredited;
6. frozen criteria bundle preceded dispatch and all used digest/version values match;
7. validator execution is accepted under the specified evidence contract and evaluation is `VALID` and current for that result;
8. task-sequenced eligibility confirms the result was not late/stale, abandoned or otherwise superseded before terminal acceptance;
9. authorization generations and fencing tokens are current at each required boundary;
10. no conflict/quarantine/tombstone/read barrier or applicable retroactive revocation blocks the result/contribution;
11. no source evaluation, result lineage or effect plan is superseded/voided/retracted;
12. required profile, destination and writer permissions match the frozen package.

If any prerequisite is absent or unverified, `BASE_ELIGIBLE=false`. Failure to establish eligibility never defaults to true.

`TASK_SUCCESS_COUNT` changes only when the task's adopted current result crosses the frozen final-success predicate. It counts a logical task once. `ACTIVE_AUTO_PATTERN_CONTRIBUTION_COUNT` changes only when an eligible unique contribution becomes visible or ceases to be visible. Negative pattern evidence requires a validated, attributable strategy failure under frozen criteria. Provider downtime, rate limits, missing authorization, captor errors, missing output, simulation, uncorrelated response or other non-attributable operational failures do not count as a negative strategy pattern.

## 7.1 Validation evidence and cumulative evidence predicates

Digests identify bytes but do not prove validator execution. Acceptance requires an authenticated validator execution receipt verified against an allowlisted validator key and binding validation/task/execution/result IDs and result digest; frozen bundle/check-set/policy/canonicalization IDs, versions and digests actually used; all required outcomes and completion; validator identity/version; and authorization generation. Missing, untrusted, partial or mismatched evidence rejects `VALIDATION_EVIDENCE_INCOMPLETE`. Implementation, key custody and verifier execution remain `UNPROVEN`; gate is fail-closed.

Predicates apply to one named evidence snapshot and policy version:
- **L0**: complete persisted result binds exact `task_id`, `execution_id`, complete payload and immutable refs. Persistence/identity only.
- **L1**: L0 plus authenticated platform evidence binding authorized dispatch to destination session, turn and parent turn. Text, nonce, timestamp or captor claim alone is insufficient.
- **L2**: L1 plus frozen bundle and authenticated receipt binding exact required bundle/check-set/policy/canonicalization versions and digests actually used, with all required outcomes.
- **L3**: L2 plus authorized, valid, conflict-free, current evaluation, not superseded/quarantined.
- **L4**: L3 plus fully committed/reconciled effect, visible and consumer-eligible at observation time. Any active barrier or incomplete reconciliation makes it false.
- **L5a**: L4 plus preregistered counterfactual replay through normal selector; snapshot, candidates, availability, selector/version, policy held constant; only learned delta changes; selected candidate changes materially by predeclared criterion.
- **L5b**: L4-eligible outcomes improve a preregistered metric versus named comparator over fixed window, eligibility filter, minimum sample and threshold. Exclude effects not L4-valid at relevant time.

Revocation, conflict, quarantine, tombstone, supersession or failed reconciliation invalidates affected levels. Higher levels imply lower levels for same identity/snapshot. Forbidden inference: persistence≠execution; digest≠validator execution; result≠attribution; evaluation≠committed effect; effect≠selector influence; influence≠outcome improvement. All implementation capabilities remain `UNPROVEN`.

## 7.2 Rejection vocabulary

`INELIGIBLE_MODE`: mode disallowed; `UNAUTHORIZED_WRITE`: actor lacks transition authority; `UNAUTHORIZED_CAPTOR`: captor unregistered/out of scope; `INVALID_EVALUATION`: policy/evidence invalid; `UNREGISTERED_PROFILE`: exact tuple (strategy, mode, route, criteria bundle/digest, evaluator version, selection policy/digest) absent; `ACTIVE_CONTRIBUTION_EXISTS`: uniqueness key active without valid replacement; `TOMBSTONE_IRREVOCABLE`: attempt to erase immutable record; `STALE_TASK_HEAD`: expected head differs; `AUTHORIZATION_REQUIRED`: required permission absent; `MODE_MISMATCH`: authenticated observed mode differs from planned; `VALIDATION_EVIDENCE_INCOMPLETE`: receipt absent/incomplete/untrusted/inconsistent; `STALE_FENCING_TOKEN`: obsolete writer token. Legacy dotted labels are not states/codes.

## 8. Contributions, plans, visibility barrier, tombstones

### 8.1 Canonical plan states

The only plan states are `PREPARING`, `PARTIAL`, `COMMITTED`, `SUPERSEDED`, `VOIDED`. `PREPARING` is transient; `PARTIAL` is a durable incomplete remnant after a crash. Both are invisible to all selectors. `COMMITTED` means the plan's complete intended changes are durably committed, but an individual contribution is visible only if its own current-eligibility predicate is true. `SUPERSEDED` means replaced by a new plan for the same relevant result lineage. `VOIDED` is terminal and can never reactivate drafts.

Contribution states are `PREPARED`, `ACTIVE`, `RETRACT_PENDING`, `RETRACTED`, `VOIDED`. A `COMMITTED` plan is not itself proof of an active contribution. An `APPLIED` receipt is not proof that a contribution is still visible.

### 8.2 Atomic publication and recovery

Before any change is visible, a durable `effect_plan_id` contains all intended destinations, contribution IDs, source evaluations, previous contributions to retract, effect kinds, provenance, expected `authorization_generation`, expected `projection_generation`, policy version and a digest of the whole plan. Partial writes remain invisible.

An `effect_plan_id` is immutable: replay of the same ID and digest reads the same durable plan/commit; the same ID with a different digest is a conflict and cannot publish effects. The store must atomically publish the complete replacement state, including retracting/superseding prior contributions, committing the successor, updating relevant pointers/generation, and recording the durable recovery journal. If the storage cannot make this atomic, it must use a durable generation barrier/read gate that keeps all affected contributions invisible until the replacement is reconciled. It may never expose both predecessor and successor contributions and “fix” that later by retracting whichever has the smaller sequence.

Recovery from a pre-commit crash either resumes the exact idempotent plan if all source/policy/authorization checks still hold, or moves the plan to `VOIDED`. Recovery after commit reads the commit record and produces the same visible state. A required retract is a persisted recovery obligation created in the same transaction as the invalidation/barrier, not a remembered future action.

### 8.3 Visibility predicate and invalidation

Tombstones have immutable explicit `scope_kind`: `CONTRIBUTION_ONLY` or `RESULT_AND_LEARNING`. The first hides scoped contributions and makes their L4 false, but leaves a separately valid adopted result pointer and `TASK_SUCCESS_COUNT` unchanged. The second also invalidates the adopted task-result pointer, makes L4 false, and decrements `TASK_SUCCESS_COUNT` once when final-success no longer holds. Both decrement active contribution projection once per scoped active contribution. Commit a durable visibility barrier before cleanup; consumers honor it immediately. Independent resolution plus a new guarded plan may release a barrier; the immutable tombstone record is never erased. Incomplete cleanup/reconciliation keeps the barrier effective.

A contribution is visible only if: its plan is fully committed; it is `ACTIVE`; its source evaluation is the current evaluation of the same `result_lineage_id`; it is not superseded/retracted/voided; its lineages/destination/kind pass the uniqueness constraint; authorization is valid for that contribution; and there is no active conflict, tombstone or applicable retroactive revocation barrier.

`CONFLICT_DETECTED` and `TOMBSTONE_COMMITTED` atomically set a read-visibility barrier for the affected result lineage/strategy scope and persist the associated retract/suspend job in the same store transaction. From the event's acceptance point onward no selector may observe the affected contribution, even if physical cleanup has not finished. `L4` becomes false immediately from the same barrier. A crash between event and cleanup cannot expose the contribution.

An authorization revocation prevents new starts/commits using the old generation and voids incomplete plans. Previously committed contributions remain valid by default unless `retroactive_scope` explicitly identifies affected scopes. `retroactive_scope` requires an authorized authority role, policy digest, scope and reason; if it invalidates existing contributions, the visibility barrier and retract job are atomic with accepting the retroactive revocation. It cannot be inferred from a generic revoke event.

Tombstones are durable and scope-bound. They cannot be erased by their creator. A separately authorized barrier release does not erase the immutable tombstone record. Restoration of the same evidence requires `CONFLICT_RESOLVED`, `restores_event_id`, new evaluation/contribution IDs, a new guarded plan, and the same `result_lineage_id`. A different strategy lineage is not a substitute for resolving SC-10; SC-10 remains `UNPROVEN` unless its authority is separately recovered.

## 9. Authorization generations, fencing, and plan commit

`authorization_generation` versions permissions; stale values reject `AUTHORIZATION_GENERATION_MISMATCH`. A fencing token orders writers and is distinct; an obsolete token rejects `STALE_FENCING_TOKEN`. Task append supplies `expected_task_head_seq`; atomic store CAS compares current head and assigns next `task_seq`. Mismatch rejects `STALE_TASK_HEAD` without accepting payload or consuming producer identity. Writer rereads and submits a newly authorized operation with a new event identity. CAS prevents lost updates; it does not choose semantic winners.

`authorization_generation` guards permissions; `projection_generation` guards selected task/evaluation/effect view. They are separate and neither stands in for task order. Each dispatch, pre-start check, validation/evaluation and effects commit records its authorization generation. The effects commit uses atomic CAS against the expected current authorization generation, expected projection generation, source evaluation ID, policy digests and absence of barriers/tombstones.

If `AUTHORIZATION_REVOKED` advanced the relevant generation before commit, the plan commit is rejected with `AUTHORIZATION_GENERATION_MISMATCH`, the plan becomes `VOIDED`, prepared contributions remain invisible, and no `ACTIVE_AUTO_PATTERN_CONTRIBUTION_COUNT` or `TASK_SUCCESS_COUNT` delta occurs from the blocked plan. A stale fencing token cannot append an effective event or mutate pointers.

The commit is one operation from the reader's perspective. “Check authorization then later commit” without an atomic generation check is forbidden. A `COMMITTED` plan that was valid before a later prospective revoke remains visible unless an explicit retroactive scope applies; any retroactive scope must invoke the barrier rule in §8.3.

## 10. Abandonment, supersession and task reopening

The frozen criteria bundle includes `abandon_timeout_ms`, its clock basis and policy. The store calculates and records `abandon_deadline_at` when dispatch is accepted. `ABANDONED` may be accepted only when authoritative store `accepted_at > abandon_deadline_at` (strictly after, not equal), while the execution is still abandonable. At or before the deadline reject with `ABANDONMENT_NOT_DUE`. If the clock is unavailable, auto-abandon is rejected with `CLOCK_UNAVAILABLE`.

An execution may be marked `SUPERSEDED` by an authorized dispatcher when a later attempt becomes active, but this does not itself supersede an already accepted result or evaluation without the corresponding per-entity event and projection rule. Distinguish `EXECUTION_SUPERSEDED`, `EVALUATION_SUPERSEDED`, and `PLAN_SUPERSEDED`; do not reuse one generic state across entities. Output received after execution supersession is diagnostic `LATE_STALE` and cannot create a result. `TASK_REOPENED` opens a new attempt with a new execution ID and frozen package; old results stay historical and do not become current automatically.

## 11. Legacy writer isolation and closed writer matrix

The R10 projection namespace rejects legacy writes based only on `result.success`. No old counter/pattern formula can write into R10 projections. Historical records lacking stable identity, correlation, stage, frozen criteria, validation evidence and authorization are `LEGACY_UNATTRIBUTABLE`, not auto-migrated by guessed fields.

The authorized writer matrix is closed:

| Event / operation | Authorized writer | Required preconditions |
|---|---|---|
| `CRITERIA_FROZEN` | Criteria coordinator | Immutable bundle validated and stored before dispatch |
| `DISPATCHED`, `TASK_REOPENED`, `EXECUTION_SUPERSEDED` | Dispatch coordinator | Current authorization generation, new IDs/nonce, bundle/route/profile recorded |
| `EXECUTION_STARTED` | Executor/start observer | Current pre-start authorization check and valid dispatch receipt |
| `SANDBOX_RECORDED` | Sandbox adapter | Diagnostic scope only; never terminal eligibility |
| `CAPTURE_RECEIVED` / `OUTPUT_RECEIVED` | Authorized captor/output adapter | Stable producer event ID, attested mode/path and complete metadata |
| `RESULT_RECORDED` | Result store | Correlation, terminal-slot and completeness checks |
| `VALIDATION_COMPLETED` | Authorized validator | Frozen bundle and recorded used-digest evidence |
| `EVALUATED`, `EVALUATION_REVISED` | Evaluation service / independent reviewer for revisions | Validation accepted; canonical identity; supersession pointer; required reviewer independence |
| `PROJECTION_ADOPTED`, `WINNER_INVALIDATED` | Projection coordinator | Frozen selection policy, task_seq, CAS on pointers and projection generation |
| `ABANDONED` | Supervisor/coordinator | Frozen deadline expired and execution is still abandonable |
| `ATTACHED` | Manual attachment service | Stable attachment ID, MANUAL lane; no AUTO terminal ownership |
| `CONFLICT_DETECTED` | Event/result store | Closed conflict predicate in §6 or §8; barrier and work item atomically persisted |
| `CONFLICT_RESOLVED`, `QUARANTINE_RELEASED` | Independent conflict reviewer | Actor distinct from involved producers/evaluators/plan owner; evidence/reason/policy/generation recorded |
| `AUTHORIZATION_REVOKED` | Authorization authority | Authenticated authority, incremented authorization generation; optional explicit retroactive scope |
| `TOMBSTONE_COMMITTED` | Projection/authority service | Defined scope, author, reason; barrier + recovery obligation atomic |
| `EFFECT_PLAN_PREPARED` | Projection service | Full immutable effect plan; all sources/destinations/generations specified |
| `EFFECTS_COMMITTED` | Projection store | Atomic source/pointer/policy/auth/barrier CAS and complete publication |
| `EFFECT_RETRACTED` | Projection store | Durable cause and obligation ID; atomic visibility change or existing read barrier |
| `PLAN_VOIDED` | Coordinator/store | Invalid source, failed authorization generation, conflict, tombstone or unrecoverable plan |

Any event written by a non-authorized role or stale fencing token is rejected before it can affect projections. The same human may not be both the conflicted producer and the independent resolver.

## 12. Canonical event-transition matrix

`RESULT_ACCEPTED` terminalizes the capture/result acceptance decision and freezes evidence references; it does not terminalize execution or guarantee evaluation/consumer eligibility. Supersession does not erase accepted evidence, but may remove current eligibility. Output arriving after superseded or abandoned execution is diagnostic only and cannot create a result. `QUARANTINE_RELEASED` removes a barrier only; original evaluation stays `QUARANTINED`. Restoration requires fresh evaluation/contribution IDs and a new guarded plan under §6.2.

| Event | From → to | Durable effect / rejection rule |
|---|---|---|
| `CRITERIA_FROZEN` | no bundle → frozen bundle | Store digests/versions; reject mutation after dispatch |
| `DISPATCHED` | PLANNED → DISPATCHED | Assign task_seq/time/receipt; require authorized generation and route; AUTO conversational needs platform dispatch turn |
| `EXECUTION_STARTED` | DISPATCHED → EXECUTION_STARTED | Recheck authorization/fencing; stale generation rejects start |
| `SANDBOX_RECORDED` | diagnostic event | No automatic result or learning eligibility, with or without sandbox pass |
| `CAPTURE_RECEIVED` / `OUTPUT_RECEIVED` | no result → captured candidate | Require producer_event_id, completeness and attestation; after supersession/abandonment → `LATE_STALE`, no result ID |
| `RESULT_RECORDED` | captured → correlated/frozen | Coordinator verifies parent-turn link, nonce, session, terminal slot and digests; otherwise rejects/`UNCORRELATED` |
| `VALIDATION_COMPLETED` | PENDING → VALIDATING → VALID/INVALID | Exact used digests must match; content conflict under same validator identity rules triggers conflict |
| `EVALUATED` | PENDING → VALID/INVALID/INDETERMINATE/COMPLETED_UNVERIFIED | Derive flags; never trust producer-supplied eligibility |
| `EVALUATION_REVISED` | current eval E1 → E2 successor | Explicit supersedes ID; unique successor; update per-result head with CAS; incompatibility creates conflict |
| `PROJECTION_ADOPTED` | task pointer old/null → eligible candidate | Atomic CAS and policy check; manual or ineligible candidate rejected |
| `WINNER_INVALIDATED` | current candidate → successor/null | Pointer and projection generation updated atomically; old evaluation cannot remain current |
| `TASK_REOPENED` | task gains new attempt | New execution/package; old terminal execution not reopened |
| `EXECUTION_SUPERSEDED` | nonterminal execution → SUPERSEDED | Late future output rejected as LATE_STALE; previously accepted attempt evidence remains immutable |
| `ABANDONED` | eligible in-flight execution → ABANDONED | Only after frozen deadline; absorbent; late output stale |
| `ATTACHED` | new manual record | Independent attachment ID; never claims AUTO terminal slot |
| `CONFLICT_DETECTED` | affected lineage → read-blocked/quarantined | Atomic visibility barrier + durable recovery/retraction job; no downstream contribution read |
| `CONFLICT_RESOLVED` | conflict open → resolved but not automatically active | Requires independent reviewer; restoration requires new evaluation and contribution IDs |
| `QUARANTINE_RELEASED` | barrier active → barrier released; evaluation remains `QUARANTINED` | No eligibility change. Fresh evaluation/contribution IDs and new guarded plan are required to restore same evidence. |
| `AUTHORIZATION_REVOKED` | generation g → g+1 | Cancels/voids incomplete old-generation plans; retroactive effects only if scope explicitly says so, via barrier |
| `TOMBSTONE_COMMITTED` | affected scope → read-blocked | Barrier and retraction obligation atomic; same writer cannot revoke tombstone |
| `EFFECT_PLAN_PREPARED` | none → PREPARING/PARTIAL | All prepared effects invisible |
| `EFFECTS_COMMITTED` | PREPARING → COMMITTED | Complete atomic publication only after all guards pass |
| `EFFECT_RETRACTED` | ACTIVE → RETRACTED | Visibility revoked atomically/barrier already in force; idempotent obligation completion |
| `PLAN_VOIDED` | PREPARING/PARTIAL → VOIDED | Terminal; drafts invisible forever |

## 13. Learning levels and causal claims

Levels are current predicates, not irreversible historical flags:

- `L0`: complete result stored with task/execution identity.
- `L1`: L0 plus authenticated dispatch-to-result correlation.
- `L2`: L1 plus frozen package and actual used digests/version match.
- `L3`: L2 plus valid current evaluation.
- `L4`: L3 plus a fully committed, reconciled and currently visible contribution/effect that is eligible for the consumer. The barrier rules make L4 false immediately when a source becomes blocked.
- `L5a`: evidence that a learned delta materially changed a normal production selector decision under a predeclared comparable counterfactual replay, changing only the learned evidence and holding snapshot, candidates, availability, selector and policy versions constant.
- `L5b`: a predefined outcome metric, comparator, window, eligibility filter and sample threshold show improvement in a subsequent objective. `L5b` must ignore contributions/results not L4-valid at the relevant time.

Persistence is not consumption; consumption is not evaluation; evaluation is not application; application is not decision influence; decision influence is not outcome improvement.

## 14. Invariant traceability I1–I12

| Invariant | Predicate | Matrix coverage |
|---|---|---|
| I1 | Stable typed identity and lineage. | T130–T131,T200 |
| I2 | Authenticated dispatch/result correlation. | T135–T138,T199–T200 |
| I3 | Mode/profile/writer gates. | T123–T129,T139,T153,T175,T185 |
| I4 | Contribution uniqueness/conflict barriers. | T130–T134,T160–T162,T184,T205 |
| I5 | Complete frozen validation evidence. | T142–T154,T179,T198,T204 |
| I6 | Separate authorization, fencing, task-head guards. | T163–T170,T174,T182,T193 |
| I7 | Atomic plans and safe recovery. | T155–T160,T177–T178,T192,T212 |
| I8 | Tombstone scope and visibility. | T133,T160,T196,T205 |
| I9 | MANUAL/AUTO provenance isolation. | T140,T183,T208,T213 |
| I10 | Accepted evidence immutable; late/superseded output not current. | T177–T178,T191–T192 |
| I11 | Trusted strict-deadline abandonment. | T168,T180,T214–T216 |
| I12 | Each cumulative level L0–L5b independently checked. | T201–T207,T218–T221 |

This is the sole invariant map. Every cited row must assert its predicate. All rows remain `NOT_RUN`.

The literal historical definitions of I1–I12 were not recovered. The §14 labels are reconstructed from review descriptions, not verbatim historical equivalence; exact historical traceability remains `NOT_RECOVERED`.

## 15. Acceptance and authority boundary

This file is a proposed reconstructed contract awaiting independent static review. It does not claim implementation or test execution. Known dependencies remain `UNPROVEN`: platform-authenticated parent-turn IDs, observed-mode/path attestation, validator execution attestation, durable task sequencer, CAS, transactions/read barriers, fencing, authorization-generation propagation, independent conflict reviewer and real legacy-writer rejection. If any required mechanism is absent, the corresponding operation must fail closed at runtime; the text cannot make it exist.

No execution, tests, builds, M0A access, credential access, canonical document modification or repository mutation is authorized. Government remains `KEEP_BLOCKED`.

## 16. Supplemental clarifications for v0.7.4

This section records supplemental clarifications consistent with the normative clauses above. If any wording conflicts, this candidate is internally inconsistent and must not be accepted; no appendix precedence rule repairs a conflicting normative clause or test oracle. The matrix is the sole test-ID registry. The namespaced reference and the v0.7.1 report are provenance only; original v0.6 remains `NOT_RECOVERED`.

### 16.1 Evidence and error vocabulary

A validation evidence reference must resolve to immutable evidence content, include its digest, and bind the evidence to the execution, result and required check. The accepted check set must equal the frozen bundle's check set; missing references reject with `VALIDATION_EVIDENCE_INCOMPLETE`. Digest/version mismatch rejects with `CRITERIA_MISMATCH`. An absent or unfrozen bundle rejects with `CRITERIA_NOT_FROZEN`. Attested names/digests alone do not prove a validator actually ran: validator execution remains `UNPROVEN` until independently demonstrated.

`DISPATCH_TURN_ID_REQUIRED` is a pre-dispatch rejection. `ABANDONMENT_NOT_DUE` applies at or before the authoritative deadline. `AUTHORIZATION_GENERATION_MISMATCH` is the canonical stale-authorization rejection; do not substitute `FENCING_VIOLATION` or `generation_id`. Missing producer identity rejects with `MISSING_PRODUCER_EVENT_ID`; same `(execution_id,lane=AUTO,producer_event_id)` plus same canonical digest is `ACK_DUPLICATE`, while same identity plus different digest creates a conflict barrier. `UNCORRELATED` is a rejection disposition, never an eligible result state.

### 16.2 Deadline, plan and restoration clarifications

The abandonment boundary is strict: `accepted_at > abandon_deadline_at` is required. Equality is not due. A crash before `EXECUTION_STARTED` leaves an execution `DISPATCHED`; it remains nonterminal until accepted `ABANDONED` after the deadline or another canonical transition. Reopening creates new execution and dispatch IDs; the old attempt is never changed to an unsupported `ABORTED` state.

The only plan states are `PREPARING`, `PARTIAL`, `COMMITTED`, `SUPERSEDED`, `VOIDED`; the only contribution states are `PREPARED`, `ACTIVE`, `RETRACT_PENDING`, `RETRACTED`, `VOIDED`. Drafts remain invisible. Recovery may resume the exact plan only while all original guards remain valid; otherwise it is voided. A quarantined evaluation cannot be directly activated by conflict resolution. Restoring the same evidence requires an independently accepted resolution, a new evaluation ID and contribution ID, a new plan, and unchanged `result_lineage_id`.

### 16.3 Single invariant map

The unique invariant mapping is §14; no duplicate mapping is defined here.


## 17. v0.7.5 normative amendments (PROPOSED)

This section supersedes conflicting earlier text in this reconstructed contract. It does not recover v0.6, the missing original Claude review, or SC-10 authority. New rules are proposed and require independent review.

### 17.1 Separate execution and result lifecycles
`ExecutionState`: CREATED → CRITERIA_FROZEN → DISPATCHED → EXECUTION_STARTED → one of SUCCEEDED, FAILED, TIMED_OUT, ABANDONED, SUPERSEDED. `RESULT_ACCEPTED` is not an execution state. `ResultState`: ABSENT → CAPTURED → ACCEPTED, REJECTED, LATE_STALE, or UNCORRELATED. `RESULT_RECORDED` durably creates CAPTURED only; it does not terminate execution, accept the result, confer eligibility, or create effects. `RESULT_ACCEPTED` changes only ResultState after guards pass. A separate authorized execution event establishes execution terminality. Capture evidence and digests are immutable. Capture ingress writes RESULT_RECORDED/CAPTURE_REJECTED; independent validation writes RESULT_ACCEPTED; dispatcher writes DISPATCHED; authenticated observer writes EXECUTION_STARTED and terminal execution events. Timeout diagnostics are durable as INFRASTRUCTURE_TIMEOUT_DIAGNOSED with execution ID, source/time/deadline/reason and do not authorize retry. LATE_STALE stores the immutable rejected digest and target identity.

### 17.2 Correlation, duplicate claims and deterministic rejection
`correlation_status` is required: MATCHED, UNCORRELATED, LATE_STALE, CONFLICT_DETECTED. Missing/invalid link is UNCORRELATED. A distinct execution claiming an already-bound authenticated (destination_session_id, turn_id) is UNCORRELATED. Same producer event ID plus same digest is ACK_DUPLICATE; same event ID plus different digest is CONFLICT_DETECTED and installs a barrier. CAPTURE_REJECTED durably stores capture ID/digest, target execution, validator, every failed guard code in stable order, and primary disposition. Precedence: AUTHORIZATION_REQUIRED, AUTHORIZATION_GENERATION_MISMATCH, CRITERIA_NOT_FROZEN, UNACCREDITED_ROUTE, MODE_UNATTESTED, UNCORRELATED, CONFLICT_DETECTED, LATE_STALE, VALIDATION_EVIDENCE_INCOMPLETE, CRITERIA_MISMATCH, INVALID_EVALUATION, TASK_HEAD_MISMATCH. Corrected evidence uses a new capture ID and references the prior rejection.

### 17.3 Validation and conflict restoration
Present but mismatching digest/key/check/policy/canonicalization is CRITERIA_MISMATCH; VALIDATION_EVIDENCE_INCOMPLETE is only for missing required evidence/reference/outcome. QUARANTINE_RELEASED releases a hold only; it does not clear a lineage barrier or restore eligibility. CONFLICT_RESOLVED requires an authorized resolver distinct from producer and affected captor, signed scope/rationale, conflict identity and `restores_event_id`. Restoration uses fresh evaluation_id, contribution_id and effect_plan_id; original quarantined evaluation stays immutable/quarantined; new evaluation rechecks current guards before publication.

### 17.4 Tombstone scopes and exact counters
CONTRIBUTION_ONLY hides scoped contributions, makes L4 false for them, and preserves a separately valid adopted task-result pointer and TASK_SUCCESS_COUNT. In a one-contribution case: task delta 0, contribution delta -1. RESULT_AND_LEARNING also invalidates the scoped adopted-result pointer and decrements TASK_SUCCESS_COUNT once iff no final-success remains; it hides the scoped contributions. Tombstones are immutable/idempotent by event ID and digest. Scope behaviors are tested separately (T205, T233).

### 17.5 Plan recovery boundary
PREPARING/PARTIAL effects remain invisible until a durable commit marker. Before the marker, recovery may resume the same immutable plan ID/digest only if all original guards and authorization generations still hold; else it records VOIDED. After the marker, recovery reads the committed journal and applies no effect twice. This is a proposed single-ledger/projection contract, not cross-store or external-system atomicity. If a participant cannot prove whether it applied an effect, retry is prohibited and the plan stays blocked for explicit reconciliation.

### 17.6 Policy/profile/history/score scope
Policy versions are immutable by ID+digest; profile versions bind route/mode, validator allowlist and criteria bundle. Only the policy registry writer registers versions; evaluations record exact policy/profile IDs and digests. History is append-only and never authorizes dispatch, validation, adoption or restoration. No score formula/default is specified here. A score-dependent row must use an explicit frozen threshold and input score; absent score is not zero or success. F-10 remains open pending independent review.

### 17.7 Learning predicates
L0–L5b are evidence predicates, not product-capability claims. L1 requires authenticated dispatch/session/turn/parent; L2 an authorized validator receipt binding the frozen bundle and all outcomes; L3 a valid non-quarantined evaluation; L4 a committed visible eligible contribution without barrier; L5a a preregistered counterfactual changing selector choice with other inputs fixed; L5b the explicit sample/metric thresholds in its fixture only. Negative cases T226–T229 are distinct. All rows remain NOT_RUN.


### 17.8 Added-row invariant map
T221/T222/T224/T225 exercise I12/L5b threshold and sample predicates independently; T226 exercises I12/L1 authentication; T227–T228 exercise I12/L2 authorization and completeness; T229 exercises I12/L4 commit visibility; T230 exercises I2 producer idempotency/conflict; T231 exercises I3 execution/result lifecycle separation; T232 exercises I3 deterministic rejection persistence; T233 exercises I9 tombstone result-and-learning scope; T234–T237 exercise I3/I9 route and authorization gates. These are proposed fixture mappings, not test results. Any row-to-invariant mapping in §14 remains subordinate to the row's exact preconditions and oracle.


### 17.9 Matrix field semantics
`initial_state_and_preconditions` is fixture setup only. `ordered_events_and_oracle` states the ordered stimulus and expected disposition/state/effects. The two delta columns contain exact numeric net changes from that fixture baseline. `crash_retry_conflict_oracle` either names the fault point, durable pre-crash state, recovery action and post-recovery oracle, or gives a scenario-specific recovery-not-applicable reason. `control_or_falsifier` changes one discriminating condition while holding others fixed. `normative_basis` points to governing clauses. The removed expected_final_state/evidence_required/fixture_discriminant columns are intentionally absent; no field is duplicated. Evidence needed to close a future run consists of the durable events, identities/digests, state snapshot and counter/pointer delta named by its oracle.
