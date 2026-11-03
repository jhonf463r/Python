# UAAL — Kit operativo de arranque de chats nuevos y transferencia entre proyectos

**Date:** 2026-10-31 (America/Bogota)  
**Parent method:** UAAL-D019 / UAAL-D020 / UAAL-D021  
**Scope:** participating ChatGPT, Codex and other AI sessions using the shared IABV method  
**Status:** operational handoff template; explicit retrieval required; automatic cross-chat boot and runtime enforcement are not implied  
**Authority:** live `refs/heads/main` and, for IABV routing only, the active header of `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`

## 1. Purpose

This kit makes the existing UAAL continuity method usable when a new chat, specialist, executor or reviewer is opened. It is an activation and handoff aid, not a second memory, project router, coordinator runtime or source of technical authority.

The objective is to reduce repeated explanations and lost work while allowing the Owner to pursue several unrelated projects. The shared method is reusable; project facts, decisions, artifacts, permissions and task routes remain owned by their own project spaces.

Do not interpret "shared mind", "consciousness" or "Space-Time" as subjective consciousness, shared hidden model context, model-weight learning or automatic delivery. Here they refer to an operational model of scope, provenance, temporal order, available capabilities and governed coordination.

## 2. The five invariants

1. **One shared method, multiple isolated project memories.** Reuse D019/D020/D021, evidence rules and coordination practices across projects. Never import another project's facts, files, assumptions, permissions or active task as if they belonged to the current project.
2. **One owning state source per project.** IABV development uses the active header of `CURRENT-STATE.md`. Every other project uses its own canonical state record or explicitly supplied owner-controlled workspace. A portfolio index is navigation only.
3. **A chat is a temporary participant.** A new chat does not inherit another chat's private context by assumption. It must retrieve its sources or receive a bounded, correlated handoff; receipt and use are separate facts.
4. **No repeated Owner questions.** Before asking about prior setup, preferences, decisions or constraints, build the relevant Owner-input ledger from available conversation context and canonical project records. Ask only for a genuinely missing fact that would change an authorized decision.
5. **Evidence before promotion.** Retrieval is not application; application is not verification; writeback is not learning; one successful reuse is not universal generalization.

## 3. Operating contexts and memory scopes

Every material participant must declare the context it is actually operating in:

```text
OPERATING_CONTEXT=
  CLOUD_SHARED_COORDINATION
  | LOCAL_IABV_RUNTIME
  | CONTROLLED_CLOUD_LOCAL_HANDOFF

ACTOR_SESSION_ID=
PROJECT_ID=
TASK_ID=
ROLE=GLOBAL_COORDINATOR | PROJECT_COORDINATOR | SPECIALIST | EXECUTOR | INDEPENDENT_REVIEWER | LOCAL_RUNTIME
MEMORY_SCOPE=
SOURCE_REVISION_OR_ARTIFACT=
OBSERVED_AT=
AVAILABLE_CAPABILITIES=
AUTHORITY_AND_NO_GO_SCOPE=
```

Use the narrowest owning memory scope:

| Scope | What belongs here | Rule |
|---|---|---|
| `GLOBAL_CORE` | Reusable UAAL methods, evidence discipline, safety invariants, proven cross-project lessons | Promote only after the learning gate |
| `PORTFOLIO_POINTER` | Project ID, short status, priority, owning-state link | Navigation only; not a second router |
| `PROJECT` | Project objectives, decisions, requirements, research, artifacts, risks and dependencies | Keep in that project's own canonical workspace |
| `TASK_EPISODE` | One bounded action, handoff, evidence receipt, result and next dependency | Link to its owning project |
| `SESSION` | Temporary notes and unsaved reasoning | Non-canonical until adjudicated |
| `RUNTIME` | Time-sensitive local machine, GPU, model, process, device and environment observations | Requires actual local-runtime evidence and freshness |

### 3.1 Context boundaries

- `CLOUD_SHARED_COORDINATION`: GitHub-backed method retrieval, project/task coordination, actor selection, report adjudication and preparation of bounded handoffs. It does not observe the Owner's laptop, GPU, files, process or physical device unless a connected, authorized tool returns correlated evidence.
- `LOCAL_IABV_RUNTIME`: the actual application on the Owner's machine. Its capabilities, identity, permissions, models, GPU and process state must be observed from that runtime; do not infer them from cloud documentation.
- `CONTROLLED_CLOUD_LOCAL_HANDOFF`: a governed transfer. A prompt, link, queued item or PR is not proof of dispatch, receipt, execution or effect. Require correlation ID, exact payload/digest, target revision, actor/runtime identity, authority, timestamps, receipt and postcondition.

## 4. Mandatory new-chat boot sequence

Apply this sequence before material reasoning, advice, routing or execution.

### B0 — Identify the assignment

Resolve from the current request and available history: project, objective, role, memory scope and requested operating context. Do not ask the Owner to restate facts already present. If the assignment is genuinely ambiguous in a way that changes the destination or authority, ask one targeted question; otherwise use the best-supported scope and label uncertainty.

### B1 — Refresh canonical IABV method and route

For an IABV task, or when using the IABV shared method:

1. Query the live `refs/heads/main` and record its exact commit SHA and observation time. A remembered SHA or prior answer is not a current read.
2. At that pinned commit, follow the repository entry order: `IABV_v1.5/AGENTS.md`, `docs/history/CHAT-ARCH/README.md`, then the active header of `CURRENT-STATE.md`; consult `CONTEXT-INDEX.md` and `MEMORY-OPERATING-PROTOCOL.md` to locate the relevant methods and evidence.
3. If normal retrieval of `CURRENT-STATE.md` returns an empty body, do not infer the file is empty. Obtain its path's blob SHA from the pinned commit tree and retrieve that exact Git blob. Record both path and blob SHA, decoded size/line count where available, and the exact commit.
4. Retrieve the current D019/D020/D021 revisions and only the objective-relevant sections/receipts of the Space-Time protocol, SYMBIOSIS-MAP and other records. Do not dump or treat the full archive as active state.
5. Treat only the top active header of `CURRENT-STATE.md` as the live IABV route. Text below its historical separator is provenance unless explicitly reactivated by the active header.
6. Reconcile incoming reports against current `main`, PR state, exact file/blob and task fingerprints before acting.
7. For material IABV development/coordination work, apply D021 §6D and read the Control Master digest from an already-available, authorized read surface where possible. Capture source, workspace/scope, state ID, generation/observation times, top queue item IDs, priorities, next actions, dependencies and evidence refs. Do not start the app/runtime, run a CLI or open protected data to obtain it unless a separate authorization and supported route already exist. A stale GitHub `latest.json/md` snapshot is historical only; if no current signal is readable, report `UNAVAILABLE`/ `STALE`, never an empty queue.

For a non-IABV project, this GitHub method remains reusable, but `CURRENT-STATE.md` is not that project's router. Locate and read the project's own canonical state. If unavailable, use the smallest supplied project handoff and mark missing evidence; do not substitute M1A's state.

### B2 — Build the Owner-input reuse ledger

Before any Owner-dependent question, record:

- fact/decision already supplied;
- exact source and date;
- class: `OWNER_REPORTED`, `INDEPENDENTLY_VERIFIED`, `INFERENCE`, or `UNKNOWN`;
- scope it applies to;
- any `DO_NOT_REPEAT` instruction;
- what the fact does **not** establish.

Known IABV continuity facts at this revision: the Owner reported organizational Microsoft Entra, a dedicated IABV Owner account and Microsoft Authenticator enrollment/successful sign-in; the Owner also identified phone-based ChatGPT interaction and possible Codex Remote/mobile approval as interaction channels; the Owner stated no additional independent mechanism is identified. These are not proof of IABV runtime issuer authority, a mandate, a trusted root, Windows principal binding or authorization of a protected operation. Do not ask the Owner to repeat or configure these facts. The current IABV technical edge remains governed by live `CURRENT-STATE.md`.

### B3 — Reconstruct the objective-conditioned world model

At minimum, distinguish:

- objective and acceptance condition;
- owning project and active bounded task;
- verified observations and source provenance;
- Owner/actor reports;
- inferences and hypotheses;
- unknowns and not-run operations;
- decisions already closed;
- constraints, permissions and no-go conditions;
- prior attempts and terminal fingerprints;
- first open causal/evidential dependency;
- capabilities and tools actually available in this session;
- Control Master signal status, exact source/workspace, state ID, generated/observed times, queue item IDs, priorities, dependencies and evidence refs; distinguish live, stale, unavailable and unverified signals.

### B4 — Select one next action

Before any external-agent prompt or handoff, apply D021 §6C.5's explicit dispatch rule. Name one intended AI provider/agent and model or channel, the project/task, role, session mode (new separate, continued or existing executor), required source-access route, exact authorized operations, exclusions and expected return. Do not write ambiguous instructions such as "send to Claude or another AI" or "use the same reviewer". If the preferred destination's availability/capability is unconfirmed, label it unconfirmed and do not claim dispatch or silently substitute another agent. The exact recipient must be selected using the task's required capability and context-separation requirements.

Apply:
- **D019:** identify the first open causal/evidential edge; fingerprint the task; stop unchanged loops.
- **D020:** compare actually available and authorized actions; prioritize verified progress, decision-changing information and minimum useful intervention; switch strategy after preparation-only repetition.
- **D021:** reconcile source and time, build the objective-conditioned world model, adjudicate prior results and select one next action with observable outcome and stop condition.
- **D021 §6B.2:** before dispatching or claiming an independent/adversarial review, record reviewer-context separation separately from source-acquisition method, source identity and source coverage; pin base/HEAD/diff; and exclude prior candidate-specific findings and author analysis. A coordinator-exported or user-supplied diff is a `LIMITED` source route and supports only a bounded static assessment, not independent live retrieval. If context separation or source retrieval is `BLOCKED`, stop before substantive review and mark every unexamined rubric dimension `NOT_ASSESSED`. Use `SOURCE_COVERAGE=PARTIAL` only when some, but not all, of the declared source scope was actually inspected; it is not a substitute for a dimension-level assessment. Never assign `PASS` or `FAIL` to an unexamined dimension.
- **D021 §6D:** intake the Control Master signal, distinguish its freshness/availability, reconcile it with the canonical route and explain whether it changed or confirmed the selected action.
- **D021 §6F:** Use [D021 §6F.0](./CHAT-ARCH-2026-10-29-UAAL-D021-CROSS-SESSION-BOOT-AND-STATE-RECONCILIATION.md#6f0-canonical-trigger-set-and-project-boundary) as the sole canonical trigger/status pointer. Do not reproduce or redefine its trigger list in this kit; consult pinned main to determine whether the section is adopted or candidate-only.
- **D019 §9E / D020 §9 proposed Owner-action method:** check the owning D019 adoption record in the exact pinned `main` before treating this bundle as canonical. Unless adoption is affirmatively recorded there, keep it candidate-only; `CURRENT-STATE.md` and already-adopted authorization/no-bootstrap rules remain controlling.

Do not select an action merely because it is easy to describe. Do not bypass a missing prerequisite, access denial, technical gate or owner authorization.

### B4.1 — Pin the target and verify the executor before handoff

For a PR, record the repository, PR number, actual PR source branch, exact source HEAD SHA, base SHA and requested branch separately. Confirm the requested branch is the actual PR source branch; a similar name is not enough. If the refs differ or diverged, stop before switching, renaming, rebasing, cherry-picking or writing.

Verify that the intended recipient has the exact checkout/worktree and authorized runner needed for the requested action. For GitHub Actions, verify the workflow revision, triggering event, exact ref/path filters, runner OS and command against this task. A runner label or operating system alone does not establish a matching CI route. Record `NO_MATCHING_CI_ROUTE` separately from `RUNNER_UNAVAILABLE`. If a matching event is accepted but no job starts because of an account/platform restriction, record `ACTIONS_ACCOUNT_RESTRICTION` and `RUNNER_JOB_NOT_STARTED`. If GitHub rejects the workflow definition before job creation, record `WORKFLOW_CONFIGURATION_ERROR`. Do not manufacture a matching path change or add an unapproved workflow merely to obtain a green check. A GitHub connector does not imply Codex has a local checkout or Windows runner. If the recipient reports no authorized runner or no checkout, do not request tests/build/runtime from that actor; choose an authorized static/documentary step or stop on the dependency.

Before a consequential write, refresh the target ref and re-check volatile preconditions. Use expected-SHA ref updates where supported. Batch related writes into one coherent commit where possible; do not treat connector-generated commit count as progress. Respect the canonical trigger and candidate-only status rule in D021 §6F.0; detailed controls apply only at the authority level established by the pinned canonical main.

### B4.2 — Verify source-package transport before substantive handoff

Use D021 §6E.6A only when that section is present in the pinned canonical main. If it exists only on a candidate branch, treat it as candidate-only. When reviewing the candidate that proposes §6E.6A itself, evaluate it as proposed text, not as an already-adopted gate.

- Choose the route from what the receiver actually did: RECIPIENT_LIVE_FETCH, ATTACHED_PACKAGE, OWNER_SUPPLIED_PACKAGE, COORDINATOR_EXPORTED_PACKAGE or OTHER (name and justify the exact route). A URL without successful retrieval or actual bytes is SOURCE_PACKAGE_STATUS=LINK_ONLY, not a successful acquisition method.
- For RECIPIENT_LIVE_FETCH, the receiver must independently retrieve the exact pinned base/head/source and report its observed revisions, coverage and byte-derived evidence. OUTBOUND_ATTACHMENT_STATUS=NOT_REQUIRED and RECEIVER_ATTACHMENT_ACK=NOT_REQUIRED; require RECEIVER_SOURCE_ACK=VERIFIED.
- For a transfer route, require actual readable bytes. `ATTACHED_VERIFIED` requires direct sender-side observation and `OUTBOUND_ATTACHMENT_STATUS_PROVENANCE=DIRECT_SENDER_OBSERVATION`. If the sender cannot observe the sending surface, preserve `ATTACHED_REPORTED` with `OUTBOUND_ATTACHMENT_STATUS_PROVENANCE=OWNER_REPORTED` or `ACTOR_REPORTED`, according to the reporting source. Use `NOT_APPLICABLE` when no attachment is required and `UNKNOWN` when provenance cannot be established. Receiver acknowledgement does not upgrade sender-side status.
- Require at least one value derived from actual bytes: preferably SHA-256 of exact package/raw live response bytes, or a named hunk header plus path-level addition/deletion counts recalculated from the diff. Label FILE_DERIVED, API_METADATA_DERIVED or PROMPT_COPIED. A copied base/head SHA is not proof of file reading.
- Keep SOURCE_PACKAGE_FILENAME_AND_FORMAT and SOURCE_PACKAGE_IDENTITY as separate fields; record producer, digest and basis, source identity, coverage, receiver acknowledgement and context separation.
- If bytes are absent, unreadable, identity-mismatched or incomplete for the claimed scope, substantive review/execution of that scope is NOT_RUN and unexamined dimensions are NOT_ASSESSED. A bounded review may proceed only for a narrower scope whose bytes and coverage are COMPLETE.
- A coordinator-exported or Owner-supplied patch remains BOUNDED_STATIC_PACKAGE unless the receiver independently verifies the live canonical source. Never label a URL as an attachment or a coordinator export as independent live retrieval.
- Do not ask the Owner to generate/diagnose an artifact that authorized repository tools can retrieve. Do not repeat a failed route without a material capability/evidence change.

### B5 — Execute only within declared authority

State what will be read, changed, created or run. Respect project boundaries and exact permissions. A documentation-only authorization does not permit source implementation, credentials, portals, protected reads, tests, build, runtime, tunnel, deployment or changes to another project.

### B6 — Verify and return a receipt

Compare the observed result with the expected observable. Record exact artifact paths, revisions, hashes, tool outputs or limitations. For external handoffs, record the named recipient and session, then distinguish `PROMPT_PREPARED`, `PROMPT_SENT`, `RECIPIENT_ACKNOWLEDGED`, `SOURCE_RETRIEVED`, `ACTION_EXECUTED` and `RESULT_ADJUDICATED`; do not infer later stages from earlier ones. When a package is required, record `SOURCE_PACKAGE_STATUS`, `SOURCE_ACQUISITION_METHOD`, producer, filename/format, identity, digest/basis, file-derived evidence and provenance, `OUTBOUND_ATTACHMENT_STATUS`, `RECEIVER_ATTACHMENT_ACK` and `RECEIVER_SOURCE_ACK`. For live-fetch, attachment fields are `NOT_REQUIRED`. A coordinator-exported attachment remains a bounded static review unless the receiver independently live-fetches the exact source. Fetch back authorized writes. Do not claim that work was dispatched, received, executed, tested or merged without the matching evidence. For IABV tasks, include `CONTROL_MASTER_SIGNAL_RETRIEVED`, signal status/source/state ID/timestamps, top queue evidence refs, `SIGNAL_INFLUENCE` and whether the action outcome was verified, following D021 §6D. For repository/test tasks, also bind the result to exact base/head SHAs, actual PR source branch, changed-path/blob SHAs, executor/runner, command and test-file blobs; distinguish `VERIFIED`, `ACTOR_REPORTED`, `CI_REPORTED` and `NOT_RUN` under D021 §6F.6; a test artifact authored but not executed remains `NOT_RUN`.

## 5. Roles and non-overlapping responsibilities

| Role | Owns | Must not do |
|---|---|---|
| `GLOBAL_COORDINATOR` | Shared method, high-level portfolio navigation, IABV cloud route and cross-project prioritization | Replace project-owned state or perform every specialist task |
| `PROJECT_COORDINATOR` | One project's objective, priority, state, task handoffs and project memory | Edit IABV `CURRENT-STATE` for an unrelated project or import another project's permissions |
| `SPECIALIST` | Bounded research/design/analysis in a named discipline | Reassign project priorities or change scope silently |
| `EXECUTOR` | Exact authorized task, specified inputs, outputs and acceptance tests | Expand scope, alter canonical memory, claim unrun tests or override gates |
| `INDEPENDENT_REVIEWER` | Challenge source, reasoning, evidence, acceptance and executor claims | Quietly become the executor or treat agreement as proof |
| `LOCAL_RUNTIME` | Actual local observations/actions through an authorized, verified route | Claim cloud state proves local execution or bypass the controlled bridge |

A single chat may hold more than one role only when the assignment explicitly states that combination and the evidence remains distinguishable. The Owner remains the source of human goals and decisions; agents organize and execute bounded work within authority.

## 6. Standard handoff envelope

The sender should populate this envelope from already available evidence. The Owner should not be made to fill it manually when the coordinator or project state can supply the fields.

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
SOURCE_PACKAGE_STATUS=NOT_REQUIRED|IDENTIFIED|BYTES_PRESENT|BYTES_INCOMPLETE|LINK_ONLY|UNAVAILABLE|MISMATCH|UNKNOWN
SOURCE_ACQUISITION_METHOD=RECIPIENT_LIVE_FETCH|ATTACHED_PACKAGE|OWNER_SUPPLIED_PACKAGE|COORDINATOR_EXPORTED_PACKAGE|OTHER|UNKNOWN
SOURCE_PACKAGE_PRODUCER=PROVIDER_OR_ACCOUNT_OR_AGENT_OR_ORGANIZATION_IDENTIFIER
SOURCE_PACKAGE_FILENAME_AND_FORMAT=
SOURCE_PACKAGE_IDENTITY=
SOURCE_PACKAGE_MANIFEST_ENTRIES=
SOURCE_PACKAGE_DIGEST=SHA256:<64_HEX>|GIT_BLOB_SHA:<40_HEX>|MANIFEST_SHA256:<64_HEX>|NOT_AVAILABLE
SOURCE_PACKAGE_DIGEST_BASIS=EXACT_PACKAGE_BYTES|RAW_LIVE_RESPONSE_BYTES|RECOMPUTED_GIT_BLOB|CANONICALIZED_FILE_MANIFEST|NOT_AVAILABLE
RECEIVER_FILE_DERIVED_EVIDENCE=
RECEIVER_EVIDENCE_PROVENANCE=FILE_DERIVED|API_METADATA_DERIVED|PROMPT_COPIED|ACTOR_ATTESTED|COORDINATOR_ATTESTED|OWNER_ATTESTED
OUTBOUND_ATTACHMENT_STATUS=NOT_REQUIRED|NOT_ATTACHED|ATTACHED_VERIFIED|ATTACHED_REPORTED|UNKNOWN
OUTBOUND_ATTACHMENT_STATUS_PROVENANCE=DIRECT_SENDER_OBSERVATION|OWNER_REPORTED|ACTOR_REPORTED|NOT_APPLICABLE|UNKNOWN
RECEIVER_ATTACHMENT_ACK=NOT_REQUIRED|PENDING|VERIFIED|FAILED|MISMATCH
RECEIVER_SOURCE_ACK=NOT_REQUIRED|PENDING|VERIFIED|FAILED|MISMATCH
SOURCE_IDENTITY_VERIFICATION=RECIPIENT_LIVE_VERIFIED|COORDINATOR_ATTESTED|OWNER_ATTESTED|ACTOR_ATTESTED|UNVERIFIED
DECLARED_REVIEW_SCOPE=
SOURCE_COVERAGE=COMPLETE|PARTIAL|NOT_ASSESSED
SOURCE_RETRIEVAL_STATUS=NOT_ATTEMPTED|PASS|LIMITED|BLOCKED|NOT_APPLICABLE
CONTEXT_SEPARATION=PASS|LIMITED|BLOCKED|NOT_ASSESSED
REVIEW_CLASS=INDEPENDENT_LIVE|INDEPENDENT_LIVE_PARTIAL|BOUNDED_STATIC_PACKAGE|NOT_APPLICABLE
SUBSTANTIVE_REVIEW=COMPLETE|PARTIAL|NOT_RUN|NOT_APPLICABLE
PARENT_OBJECTIVE=
PROJECT_ID=
TASK_ID=
ROLE=
OPERATING_CONTEXT=
MEMORY_SCOPE=
LIVE_MAIN_SHA_AND_OBSERVED_AT=
PROJECT_STATE_SOURCE_AND_REVISION=
OBJECTIVE_AND_ACCEPTANCE=
VERIFIED_FACTS=
OWNER_OR_ACTOR_REPORTED=
INFERENCES_AND_UNKNOWNS=
DECISIONS_ALREADY_CLOSED=
DO_NOT_REPEAT=
LAST_TERMINAL_FINGERPRINT=
FIRST_OPEN_CAUSAL_EDGE=
AUTHORIZED_OPERATION_SCOPE=
EXPLICIT_EXCLUSIONS=
CONTROL_MASTER_SIGNAL_STATUS=
CONTROL_MASTER_SOURCE_STATE_ID_AND_TIMES=
CONTROL_MASTER_QUEUE_ITEM_IDS_AND_EVIDENCE=
SIGNAL_INFLUENCE_ON_NEXT_ACTION=
AVAILABLE_INPUT_ARTIFACTS=
NEXT_SINGLE_ACTION=
EXPECTED_RETURN_ARTIFACT_AND_RECEIPT=
STOP_CONDITION=
```


### 6.0 Mandatory prompt-emission preflight

Before presenting any copy-ready external-agent prompt, apply D021 §6C.5's fail-closed emission check to the exact artifact:

1. The dispatch header must be the first non-empty content **inside the prompt artifact**, before its title or task body. A recipient named only in surrounding chat prose is insufficient.
2. Populate the complete dispatch header: one exact provider/agent, model or channel, project/task, role, session mode, context-separation requirement, source route and exact refs, authorized scope, exclusions, expected return and stop condition. Do not leave blanks, placeholders or alternative recipients.
3. Resolve the destination from the current conversation and task capability. Do not infer account availability, model identity, source access, checkout, runner or delivery from a product name.
4. If the provider is identified but account/channel availability is unconfirmed, retain it as `PREFERRED_RECIPIENT; AVAILABILITY_UNCONFIRMED`, set D021 `PROMPT_EMISSION_STATUS=PREPARED_NOT_SENT`, and do not substitute another agent. If the intended recipient is genuinely unresolved, set `PROMPT_EMISSION_STATUS=BLOCKED` and ask one irreducible routing question before drafting.
5. Verify that the task body agrees with the header and does not expand authority, weaken exclusions, omit required source access or imply an action already occurred.

A prompt with an absent, incomplete, ambiguous or contradictory header has `PROMPT_EMISSION_STATUS=BLOCKED`; do not present it as ready to send. The generic envelope above is a schema, not a completed dispatch. Fill it with exact task values. Any repeated field in a project-specific envelope must match the dispatch header exactly; the header is authoritative and the envelope cannot override it.

### 6.1 Sender obligations

- Resolve the destination chat/agent and role.
- Include only the context needed for the bounded task.
- Pin project sources and artifact revisions; never expose secrets or unnecessary private data.
- State the exact task, acceptance criteria, authorized actions and exclusions.
- Preserve the owning project's task route; a specialist handoff does not create a competing active task.
- Before sending, verify that every required source package's actual bytes are present and correctly identified. If an attachment is required, confirm the file is actually attached in the outbound surface; a URL or instruction to attach it is not an attachment.

### 6.2 Receiver obligations

- Acknowledge the handoff ID, project/task, role and operating context.
- Report which exact sources/artifacts were actually retrieved, and what could not be retrieved.
- Reconcile with the live owning state before action.
- Do not repeat already-settled Owner questions.
- Return a correlated receipt; if blocked, identify the exact missing evidence and stop condition instead of inventing work.
- Confirm whether the actual package is attached/readable or independently live-fetched. For live-fetch, set attachment fields to NOT_REQUIRED and acknowledge RECEIVER_SOURCE_ACK=VERIFIED. For an attachment, echo the filename/identity plus at least one byte-derived value (preferably SHA-256 of exact bytes, or a named hunk header and path-level counts recalculated from the diff). Label evidence FILE_DERIVED, API_METADATA_DERIVED or PROMPT_COPIED. A prompt/link or copied base/head SHA is not proof of package reading; use FAILED or MISMATCH when appropriate.

## 7. Standard return receipt

```text
HANDOFF_ID=
TASK_ID=
ACTOR_SESSION_ID=
OPERATING_CONTEXT=
PROJECT_ID=
ROLE=
OBSERVED_AT=
SOURCE_REVISION_OR_ARTIFACTS=
SOURCE_PACKAGE_REQUIRED=YES|NO
SOURCE_PACKAGE_STATUS=NOT_REQUIRED|IDENTIFIED|BYTES_PRESENT|BYTES_INCOMPLETE|LINK_ONLY|UNAVAILABLE|MISMATCH|UNKNOWN
SOURCE_ACQUISITION_METHOD=RECIPIENT_LIVE_FETCH|ATTACHED_PACKAGE|OWNER_SUPPLIED_PACKAGE|COORDINATOR_EXPORTED_PACKAGE|OTHER|UNKNOWN
SOURCE_PACKAGE_PRODUCER=
SOURCE_PACKAGE_FILENAME_AND_FORMAT=
SOURCE_PACKAGE_IDENTITY=
SOURCE_PACKAGE_MANIFEST_ENTRIES=ROLE<TAB>REVISION<TAB>PATH<TAB>GIT_BLOB_SHA<TAB>BYTE_LENGTH (repeat once per file; see D021 §6E.6A)
SOURCE_PACKAGE_DIGEST=SHA256:<64_HEX>|GIT_BLOB_SHA:<40_HEX>|MANIFEST_SHA256:<64_HEX>|NOT_AVAILABLE
SOURCE_PACKAGE_DIGEST_BASIS=EXACT_PACKAGE_BYTES|RAW_LIVE_RESPONSE_BYTES|RECOMPUTED_GIT_BLOB|CANONICALIZED_FILE_MANIFEST|NOT_AVAILABLE
RECEIVER_FILE_DERIVED_EVIDENCE=
RECEIVER_EVIDENCE_PROVENANCE=
OUTBOUND_ATTACHMENT_STATUS=NOT_REQUIRED|NOT_ATTACHED|ATTACHED_VERIFIED|ATTACHED_REPORTED|UNKNOWN
OUTBOUND_ATTACHMENT_STATUS_PROVENANCE=DIRECT_SENDER_OBSERVATION|OWNER_REPORTED|ACTOR_REPORTED|NOT_APPLICABLE|UNKNOWN
RECEIVER_ATTACHMENT_ACK=
RECEIVER_SOURCE_ACK=
SOURCE_IDENTITY_VERIFICATION=
SOURCE_COVERAGE=COMPLETE|PARTIAL|NOT_ASSESSED
SOURCE_RETRIEVAL_STATUS=NOT_ATTEMPTED|PASS|LIMITED|BLOCKED|NOT_APPLICABLE
CONTEXT_SEPARATION=PASS|LIMITED|BLOCKED|NOT_ASSESSED
REVIEW_CLASS=INDEPENDENT_LIVE|INDEPENDENT_LIVE_PARTIAL|BOUNDED_STATIC_PACKAGE|NOT_APPLICABLE
SUBSTANTIVE_REVIEW=COMPLETE|PARTIAL|NOT_RUN|NOT_APPLICABLE
MEMORY_RETRIEVED=VERIFIED | PARTIAL | NOT_RETRIEVED
METHOD_ACTIVATED=VERIFIED | PARTIAL | NOT_VERIFIED
METHOD_APPLIED=VERIFIED | PARTIAL | NOT_VERIFIED
OWNER_INPUT_REUSE_LEDGER=BUILT | NOT_REQUIRED | BLOCKED
WORLD_MODEL_SNAPSHOT=BUILT | PARTIAL | NOT_BUILT
DECISION_AND_REASON=
ACTION=EXECUTED | BLOCKED | NOT_EXECUTED
OUTCOME=VERIFIED | PARTIAL | UNKNOWN
FILES_OR_SOURCES_MODIFIED=
TEST_EXECUTION_SCOPE=TESTS|BUILD|RUNTIME|COMBINED|NOT_APPLICABLE
TEST_AUTHORIZATION=AUTHORIZED|NOT_AUTHORIZED|NOT_APPLICABLE|UNKNOWN
TEST_STATUS=VERIFIED|ACTOR_REPORTED|CI_REPORTED|NOT_RUN
AUTHORIZATION_BOUNDARY_RESPECTED=YES | NO | UNKNOWN
FIRST_REMAINING_DEPENDENCY=
NEXT_SINGLE_ACTION=
NEXT_ACTION_EXECUTED=NO
STOP_CONDITION=
```

For causal learning claims, add:

```text
KNOWLEDGE_DELTA=
METHOD_DELTA=
ROUTING_DELTA=
LATER_NONIDENTICAL_REUSE=NOT_TESTED | OBSERVED | VERIFIED
LATER_DECISION_CHANGED_BY_RETAINED_DELTA=NOT_ESTABLISHED | VERIFIED
CAUSAL_ATTRIBUTION_LIMITATIONS=
```

A receipt is an actor report until its evidence is independently reconciled. A status field alone does not verify itself.

## 8. Shared learning without project contamination

Use the existing D021 §6C.4 ladder:

```text
RAW_OBSERVATION
 -> PROJECT_FACT_OR_DECISION
 -> LESSON_CANDIDATE
 -> NONIDENTICAL_CROSS_CONTEXT_OR_CROSS_DOMAIN_TRIAL
 -> SHARED_METHOD_ADOPTION
 -> LATER_CAUSAL_REUSE_VERIFIED
```

A transferable lesson must preserve original scope, provenance, conditions, counterexample/falsifier, decision changed and observed outcome. Retain the source project record; promote only the abstracted method. Do not delete old knowledge merely to replace it with a new claim. Supersede explicitly and preserve history.

Because `jhonf463r/Python` is public, write only public-safe methods and sanitized/generalizable lessons here. Private project files, personal information, commercial secrets, source artifacts, account identifiers, credentials, keys and tokens belong in a suitable private project store. This public kit must not become a cross-project private archive.

## 9. Universal bootstrap prompt body template — dispatch header required

Use this as the task-body template when starting or resuming a material task. It is not a released external-agent prompt by itself. When dispatching it to an external agent, prepend a fully populated D021 §6C.5 `DISPATCH_HEADER` as the first non-empty content of the complete prompt artifact. Place any project-specific handoff envelope after that header and before/within this body; never put the header below the bootstrap prompt. The header controls recipient, session, source, scope, exclusions, expected return and stop condition; repeated envelope fields must match it exactly or the complete prompt is BLOCKED. Do not present the body alone as ready to send. This prompt explicitly requires Control Master intake for IABV; a generic instruction to "use D021" is not evidence that the panel was consulted.

```text
UAAL — UNIVERSAL NEW-CHAT BOOT
TASK_ID=GENERATE_FROM_ASSIGNED_TASK
ROLE=USE_ASSIGNED_ROLE_OR_PROJECT_COORDINATOR
OPERATING_CONTEXT=DECLARE_ACTUAL_CONTEXT
MEMORY_SCOPE=RESOLVE_FROM_PROJECT_AND_TASK

You are a temporary participant in the IABV/UAAL coordination method, not a second permanent memory or competing coordinator.

Your first job is to reconstruct the correct present state before recommending or doing work. Do not assume that a link, Project file, old chat, prompt, or PR has already been retrieved or consumed by this session.

1. Identify the owning PROJECT_ID, objective, role, task and memory scope from this request and any attached handoff. Do not mix projects or import another project's facts, permissions or route.

2. For IABV tasks, refresh live GitHub refs/heads/main and record its exact commit SHA and observation time. Follow the current canonical entry order: IABV_v1.5/AGENTS.md -> CHAT-ARCH/README.md -> CHAT-ARCH/CURRENT-STATE.md -> CHAT-ARCH/CONTEXT-INDEX.md -> CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md. If CURRENT-STATE's ordinary read is empty, resolve its path/blob from that exact commit tree and retrieve that exact Git blob. Record the path, blob SHA and the content actually received. Never treat an empty transport response as an empty state file.

3. For IABV tasks, the canonical coordination repository is `jhonf463r/Python`; retrieve only the relevant live-main versions/sections of UAAL-D019, D020, D021, the Space-Time protocol, SYMBIOSIS-MAP and the New-Chat Boot Kit. Separate adopted main content from branch-only candidates and historical snapshots. Do not claim a proposed PR or remembered SHA is canonical. For every non-IABV project, import D019/D020/D021 only as method-only guidance when relevant; do not carry over IABV project facts, CURRENT-STATE, Control Master queue/objectives, Owner identity inputs, M1A gates, root handles, permissions or action-specific approvals.

3a. For every non-IABV project, retrieve that project's own canonical repository/state and relevant artifacts before making project decisions. IABV `CURRENT-STATE.md` is not that project's router. If its state source is unavailable, use the smallest supplied project handoff and mark missing evidence; do not substitute M1A/IABV state or permissions.

4. For every material IABV development/coordination task, explicitly perform UAAL-D021 §6D Control Master signal intake before selecting the next action:
   - Attempt the narrowest already-available, authorized read of the current ControlMasterDigest/runtime signal. Do not start the IABV app/runtime, run a local CLI, inspect protected data or access credentials merely to obtain it.
   - Record CONTROL_MASTER_SIGNAL_STATUS as FRESH, STALE, UNAVAILABLE, UNVERIFIED, CONFLICTED or NOT_APPLICABLE, plus the exact source, workspace/project scope, state_id, digest ID/SHA, generated time and observed time.
   - When available, capture the top queue item IDs, priorities, next actions, dependencies and evidence refs. Reconcile them with the Owner's current objective and the canonical CURRENT-STATE route.
   - A committed control_master/latest.json or latest.md is a snapshot, not a live runtime signal. Check its generation timestamp. Never promote an old snapshot to FRESH.
   - Distinguish EMPTY_CONFIRMED (a valid, source-identified, timestamped digest whose queue is genuinely empty) from UNAVAILABLE/RETRIEVAL_FAILED (blank response, missing reader, stale cache, exception or export failure). Never replace a failed read with an empty list/object.
   - CURRENT-STATE remains the sole authority for active route, gates and permissions. The Control Master informs/qualifies priority; it cannot authorize an operation or override the canonical route.
   - State SIGNAL_INFLUENCE as CHANGED_ACTION, CONFIRMED_ACTION, NO_EFFECT or UNAVAILABLE, and explain the exact decision it changed/confirmed. If the signal was unavailable, say it did not influence the decision; continue only with an independently authorized action supported by the canonical route and current Owner objective.

5. Before asking the Owner anything, recover the known-input ledger from the available conversation context and canonical project records. Record settled facts, source/date, epistemic class, scope and DO_NOT_REPEAT limits. Never repeat a settled question or ask the Owner to design the technical solution.

6. Build a source-grounded world-model snapshot: objective and acceptance condition; canonical route; verified facts; Owner/actor reports; inferences and hypotheses; unknowns and not-run operations; decisions already closed; exact authority and exclusions; prior attempts and terminal fingerprints; first open causal/evidential dependency; actual capabilities available in this session; and the Control Master signal status and influence.

7. Apply D019 to identify the first open causal/evidential edge and prevent unchanged loops. Apply D020 to compare genuinely available, authorized candidate actions and maximize useful verified progress while minimizing Owner effort. Apply D021 to reconcile evidence and adjudicate prior results. Keep candidate actions provisional; do not finalize, dispatch or execute a material action yet.

7a. Before any material Owner-facing device/app/account/private-UI instruction, enforce the action-specific authorization and no-bootstrap rules in the exact pinned canonical route: a visible UI option, permission prompt or available control is not authorization. Apply only pre-action requirements whose owning method is adopted in pinned `main`. The owning D019 record currently states `STATUS=DOCUMENTED_METHOD_CANDIDATE` and `CANONICAL_MAIN_ADOPTION=NOT_YET`; therefore D019 §9E and the dependent D020 §9 `OWNER_ACTION_PACKET` expansion remain candidate-only, not canonical mandatory gates. They may be used as planning aids only when they do not expand authority or override an adopted rule. Recheck the exact D019 owner record in each later session; do not infer adoption from front-door wording or D020's general `STATUS=DOCUMENTED_METHOD`.

8. Before finalizing the next action, consult D021 §6F.0 for the canonical trigger and candidate-only status rule. Apply the detailed pre-action bundle only at the authority level present in the pinned canonical main; if §6F exists only on a candidate branch, label it candidate-only and do not claim adoption. Bind the exact task, repository, base SHA, actual PR source branch/head SHA, target paths/blob SHAs, Owner authorization, recipient checkout/runner capability, expected observable and stop condition. Apply D021 §6E.6A only when it is present in pinned canonical main; otherwise treat it as candidate-only. A similarly named branch is not the PR source branch. Exclude any candidate action that fails a required precondition. Then select one next action only from the gate-eligible candidates; if none remains, stop and report the first unmet precondition instead of dispatching.
   - For every external-agent handoff, apply D021 §6C.5 and complete the §6.0 prompt-emission preflight before presenting the copy-ready artifact. The literal, fully populated dispatch header must be the first content inside that artifact; naming the recipient only in surrounding prose does not comply. Name one exact provider/agent, model or channel, role, session mode, source-access route, permitted scope, exclusions and expected return. Do not use "Claude or another AI", "same reviewer" or another ambiguous substitute. Verify the recipient's actual capability; otherwise mark it unconfirmed and do not claim dispatch.
   - For any independent/adversarial review, freeze `DECLARED_REVIEW_SCOPE` before the first source inspection and apply D021 §6B.2 exactly as present in pinned canonical `main`. Record exact included paths/ranges, criteria, required source items and explicit exclusions; do not narrow scope after seeing source availability or findings. If any required source item is unavailable/incomplete, handle the full claimed scope under the mixed-source rule in §6E.6A; available-subset observations may be recorded separately but are not a partial verdict on an unreviewable full scope. Assess branch-only amendments as candidate text, not adopted authority.
   - Apply D021 §6E.6A only under the canonical-main/candidate-only rule in step 8. For `RECIPIENT_LIVE_FETCH`, verify the receiver's live source identity and byte-derived acknowledgement; set attachment fields to `NOT_REQUIRED`. For a transfer route, verify actual bytes, sender-side status and the receiver's correlated byte-derived acknowledgement. If bytes, identity, coverage or acknowledgement are missing, incomplete or mismatched, stop with `SUBSTANTIVE_REVIEW=NOT_RUN` for the claimed scope. A coordinator-exported package supports only `BOUNDED_STATIC_PACKAGE` unless the reviewer independently fetches and verifies the live source.

9. Execute only within the exact declared authority. Do not expand scope, bypass a failed prerequisite, access protected data, use credentials, alter permissions, start local runtime/bridge/tunnel, or claim tests/build/runtime were run without correlated evidence. Do not merge a PR without separate explicit Owner approval.

10. Return a correlated receipt. Include exact refs/SHAs/timestamps, sources actually retrieved, Control Master intake fields and signal influence, Owner-input reuse ledger, selected action, authority/exclusions, expected observable, stop condition, result provenance and fetch-back evidence. Distinguish VERIFIED, OWNER/ACTOR_REPORTED, INFERENCE, HYPOTHESIS, UNKNOWN and NOT_RUN; record authorship of an unexecuted test artifact only in provenance notes, and keep `TEST_STATUS=NOT_RUN` until a correlated run is actually observed. A receipt is a report until independently reconciled.

Do not change another project's state, IABV CURRENT-STATE, permissions, source code or canonical methods unless the handoff explicitly authorizes that exact change. Keep private project information out of the public repository. Do not ask for information already available. If a source or tool is unavailable, say exactly what failed and continue only within the evidence and authority you do have.

Never claim automatic memory delivery, continuous cross-chat synchronization, runtime enforcement, consciousness, physical observation, test execution, causal learning or autonomy without evidence.
```

## 10. Project-chat assignment block

Use this short assignment block inside an existing project chat. If it is sent as an external-agent prompt, put a fully populated D021 §6C.5 `DISPATCH_HEADER` first and place this block below it; do not send this block as a standalone external prompt:

```text
PROJECT CHAT ASSIGNMENT
PROJECT_ID=
PROJECT_NAME=
ROLE=PROJECT_COORDINATOR | SPECIALIST | EXECUTOR | INDEPENDENT_REVIEWER
PROJECT_STATE_SOURCE=
PROJECT_MEMORY_LOCATION=
PROJECT_OBJECTIVE=
ACTIVE_TASK=
ACCEPTANCE_CRITERIA=
KNOWN_DECISIONS_AND_DO_NOT_REPEAT=
CURRENT_ARTIFACTS_AND_REVISIONS=
AUTHORIZED_OPERATION_SCOPE=
EXPLICIT_EXCLUSIONS=
EXPECTED_RETURN_TO_COORDINATOR=
STOP_CONDITION=

Own only this project and task. Use UAAL's shared methods, but keep this project's facts, files, decisions and permissions in this project's memory. Maintain one foreground task and one next action for this project. Capture new ideas without silently displacing the active task. Return a correlated receipt to the coordinator. Do not update IABV's CURRENT-STATE unless the task is explicitly about IABV development and the write is authorized.
```

## 11. Historical continuity snapshot for the IABV M1A route — superseded by CURRENT-STATE

This section is a continuity aid, **not an independent router**. Its values are a dated snapshot and must never override the live [CURRENT-STATE.md](./CURRENT-STATE.md), which remains the sole authority for ACTIVE_TASK, NEXT_ACTION, gate status and permissions. Each new IABV session must refresh the exact live `main` revision first. If the normal file read returns an empty body, fetch the exact CURRENT-STATE blob by its SHA from that same revision; do not fall back to this snapshot.

The route shape to preserve is:

```text
ROUTING_AUTHORITY=IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md; SOLE_LIVE_ROUTER
ACTIVE_TASK=IABV_M1A_OWNER_ISSUER_MECHANISM_INPUT_GATE_R1_20261030
ACTIVE_TASK_STATUS=BLOCKED_NO_ADDITIONAL_MECHANISM_IDENTIFIED; OWNER_INPUT_RECONCILED
OPEN_EDGE=OWNER_ROOT_DECISION_AUTHENTICATION_AND_ROOT_HANDLE_PROVENANCE_NOT_ESTABLISHED
NEXT_ACTION=WAIT_FOR_NEW_INDEPENDENT_ROOT_ISSUER_BINDING_EVIDENCE_FOR_M1A_G1_ONLY; APPLY_D019_DUAL_TRACK_SELECTOR_TO_ANY_SEPARATE_OWNER_OBJECTIVE; DO_NOT_REPEAT_OWNER_INPUT_OR_ENTRA_AUTHENTICATOR_SETUP
LANE_A=M1A_G1_ROOT_AUTHORITY_AND_PROVENANCE; BLOCKED; TASK_LOCAL
LANE_A_WAIT_SCOPE=TASK_LOCAL_M1A_AUTHORITY_DEPENDENCY_ONLY; NOT_PROJECT_WIDE_STOP
LANE_A_REOPEN_TRIGGER=NEW_INDEPENDENT_SOURCE_BOUND_EVIDENCE_AFFECTING_ANY_OPEN_M1A_DEPENDENCY; REASSESS_ONLY_AFFECTED_GATE_AND_CAUSAL_DEPENDENCIES; NO_FULL_CENSUS_RESTART
LANE_B=INDEPENDENT_PROGRESS; SELECT_ONLY_WHEN_CURRENT_OWNER_OBJECTIVE_AND_OWN_AUTHORIZATION_SUPPORT_A_CONCRETE_TASK
LANE_B_AUTOMATIC_FOLLOW_ON=FALSE
G1/G2/G3=NOT_ESTABLISHED
G4/G5/G6/G7/G8=OPEN; NONE_CLOSED
OPTION_D=RATIFIED_NO_BOOTSTRAP
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
TESTS/BUILD/RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

The Owner-input question is closed. Do not repeat Entra/Authenticator setup, ask whether the Owner has another mechanism, repeat the R1 source census or reconstruct another R5 root provider unchanged. Do not touch `C:/Python`, enter protected stores, create credentials or trust roots, change permissions, enable protected reads, activate a tunnel, implement, test, build or run the product under this handoff kit.

The reopen trigger is deliberately dependency-scoped: genuinely new, independently verifiable, source-bound evidence affecting **any** open M1A dependency permits reassessment of only the affected gate and its causal dependencies. It does not require a complete evidence bundle before a partial dependency can be assessed, and it does not authorize implementation. The normative eight-gate contract remains in the [M1A v1.0.1 prerequisite matrix](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md), blob `1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37`.

## 12. Acceptance checklist for each new material chat

- [ ] Declared project, task, role, operating context and memory scope.
- [ ] Retrieved and pinned live canonical sources where available.
- [ ] Retrieved the correct owning project state; did not substitute IABV state for another project.
- [ ] Built Owner-input reuse ledger before any Owner-dependent question.
- [ ] Distinguished verified, reported, inferred, unknown and not-run facts.
- [ ] Recovered closed decisions and previous terminal fingerprints.
- [ ] Applied D019/D020/D021 to select one authorized next action.
- [ ] Named expected observable, acceptance and stop condition.
- [ ] Returned a correlated receipt and recorded any retrieval limitation.
- [ ] Kept all project and cloud/local boundaries intact.

**Acceptance boundary:** passing this checklist demonstrates that a session followed the explicit boot procedure for this bounded task. It does not prove that GitHub was automatically injected into the chat, that every future chat will comply, that a runtime enforces the method, that model weights learned, or that IABV has subjective consciousness.


## 13. ChatGPT Project shared context (2026-10-31)

Use one owner-controlled ChatGPT Project for IABV coordination. Add the copy-ready instructions from CHAT-ARCH-2026-10-31-CHATGPT-PROJECT-INSTRUCTIONS-R1.md to its Project instructions, and keep IABV ChatGPT chats inside it when the interface permits. The Project makes its own instructions, files and chats available as shared context to its chats. Choose memory mode by intended scope: Project-only confines IABV recall to chats inside this Project and excludes account-level saved memories and chats outside it; Default memory may offer broader account-level context where plan/settings permit, with cross-project mixing risk. Under the existing separate-project-memory policy, Project-only is preferred for the dedicated IABV Project unless the Owner explicitly chooses wider account recall. Neither mode guarantees recall of every message.

At startup, inspect the Project sources/relevant chats, then retrieve the current canonical repository sources through the GitHub connector if available. Do not ask the Owner to re-upload a stable file already present in Project Sources or GitHub. Request a file only after checking authorized shared sources and proving that the missing evidence exists solely in a local-only location.

Codex, Claude and other external AI products do not automatically inherit this ChatGPT Project. Use the existing GitHub repository as the common cross-product store and verify each receiving session's authorized access. Project instructions guide behavior; they do not install tools or enforce permissions.

A ChatGPT Project does not expose the Owner's local runtime, local database or current Control Master digest. Keep that signal unavailable/stale unless an authorized live source is actually read. Do not start the runtime, CLI or bridge, and do not bypass Option D or other M1A gates.

See UAAL-D021 §6E and CHAT-ARCH-2026-10-31-CHATGPT-PROJECT-INSTRUCTIONS-R1.md.
