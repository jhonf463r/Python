# Canonical continuity, space-time reasoning and anti-loop protocol

- Protocol ID: `CONTINUITY_SPACE_TIME_ANTI_LOOP_V1`
- Owner instruction date: 2026-10-23 (America/Bogota)
- Scope: project reasoning, memory navigation, decision traceability and next-action selection
- Intended audience: every new ChatGPT/Codex/other-AI coordination session working on IABV
- Status: proposed by a documentation-only change; effective as a canonical instruction only after adoption on live `main`
- Project North Star: `GOVERNED_IABV_CODEX_BRIDGE`
- Active technical frontier at creation: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`

## 1. Purpose

Keep the project moving toward its declared outcome without restarting completed investigations, asking the Owner to reconstruct the archive, confusing a design with an implemented capability, or substituting activity for progress.

Treat project continuity as a **time-aware evidence graph**, not as a pile of disconnected chat summaries. Each meaningful event has a date/checkpoint, source, provenance, scope, result, effect on the current state, dependencies and a next action. Reason forward from the latest accepted state while retaining the causal history that explains how the project arrived there.

This protocol improves navigation and reasoning. It does not create technical authority, change a security decision by implication, authorize protected reads, or override the canonical state router.

## 2. Authority hierarchy: which record wins

For every new chat:

1. Revalidate the live GitHub `main` reference. Never use a remembered SHA as if it were still current.
2. Read these five canonical files from live `main`, in exactly this order:
   1. `IABV_v1.5/AGENTS.md`
   2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
   3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
   4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
   5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`
3. Use `CURRENT-STATE.md` as the **sole authority for current route, active task and NEXT_ACTION**. The other front doors supply operating rules and navigation; they cannot silently replace that route.
4. Follow only the relevant handoffs, terminal receipts, accepted contracts and review records linked from those files or returned by a targeted archive lookup. Prefer the most recent accepted evidence, not merely the most recently modified prose.
5. Distinguish live-`main` canonical records from candidate-branch proposals. A change on a branch is not canonical until accepted into `main` and fetched back.
6. If records conflict, do not average them or silently choose the convenient statement. Identify the conflict, check chronology and adoption on `main`, preserve the more restrictive current gate until the conflict is resolved, and record the exact source/commit responsible for the result.

GitHub is the durable central project memory for records actually committed there; it is not guaranteed to contain every raw conversation, local file, private secret or event that nobody recorded. If a fact is absent, report that it was not found in the permitted records rather than claiming universal absence or asking the Owner to remember the archive.

## 3. Build the temporal state map before choosing work

Internally reconstruct this compact state map from the canonical files and only the relevant history:

- `PRIMARY_OUTCOME`: the end-to-end outcome the project is trying to achieve.
- `ACTIVE_TASK` / `NEXT_ACTION`: the current frontier and the one action allowed next by the canonical router.
- `LAST_TERMINAL_TASK`: last closed attempt and its exact terminal result.
- `OWNER_DECISIONS`: explicit decisions, their exact scope, date and receipt.
- `ESTABLISHED`: claims supported by accepted evidence, with source and provenance.
- `OWNER_REPORTED`: useful Owner-supplied reports that have not been independently verified.
- `UNKNOWN / NOT_INSPECTED / NOT_RUN`: unresolved observations; never silently promote them to true or false.
- `CLOSED_OR_REJECTED_PATHS`: alternatives already investigated, why they failed, and what genuinely new evidence would justify reopening them.
- `DEPENDENCY_EDGE`: the exact prerequisite that blocks the desired next stage.
- `AUTHORIZATION_BOUNDARY`: the precise read, edit, test, runtime, spend, merge or deployment actions currently permitted and forbidden.
- `EXPECTED_TRANSITION`: what concrete evidence/result would change the state after the proposed action.
- `NEXT_OWNER_INPUT`: leave empty unless a decision or fact only the Owner can supply is genuinely needed.

Use a dependency graph, not a flat checklist: an action is valuable when it resolves the earliest open dependency on the path to the North Star. Do not work on a downstream feature while its trust, authorization or contract prerequisite is still unsatisfied.

## 4. Objective-first next-action algorithm

Before performing or recommending any action, answer these questions in order:

1. **Outcome link:** Which explicit requirement of `PRIMARY_OUTCOME` does this action advance?
2. **Current frontier:** Which exact unresolved dependency or contradiction is it intended to resolve?
3. **Prior-art check:** Does a canonical receipt already answer this question or close this path?
4. **New information:** What genuinely new evidence, authorization or falsifiable test distinguishes this attempt from a prior failed/closed attempt?
5. **Route and actor:** Which supported tool, repository path or named actor can perform it under current permissions?
6. **Scope and risk:** Is it explicitly authorized? What side effects, privacy exposure, tunnel, runtime, cost or protected resource might it touch?
7. **State transition:** What exact evidence must be returned, where will it be recorded, and which state field could legitimately change?
8. **Stop condition:** What result means stop without trying alternate routes or repeating the action?

If the action cannot name a dependency it advances, new information it obtains, a permitted route and a measurable state transition, do not do it. Explain the blocker once in plain language and select the nearest safe, useful action that is actually authorized.

## 5. Anti-loop and Owner-burden rules

- Never ask the Owner to remember, locate or paste a document that the coordinator can search in the project archive through an already-supported, permitted GitHub route.
- Search the canonical index and targeted historical records before asking the Owner for context. Do not perform an indiscriminate repository-wide scan when a targeted query or known receipt is enough.
- Never repeat completed Entra/Authenticator setup, the already-ratified Option D decision, or another closed diagnostic/review just because a new chat started.
- A terminal failure remains terminal for its stated scope. Reopen it only when (a) new evidence changes a premise, (b) a specific correction fixes the identified failure mechanism, or (c) the Owner makes a new explicit decision that changes the permitted scope. A generic desire to progress is not evidence that a failed route now works.
- Do not disguise the same experiment as a different task, rerun a denied/unavailable reader, or move to another tool/AI/transport to bypass a denied route. Record `NOT_RUN` / `SUPPORTED_ROUTE_NOT_FOUND` accurately and stop.
- Do not report “no asset exists” from “could not inspect it.” Preserve `UNKNOWN; NOT_INSPECTED`.
- Do not ask the Owner to provide an independent root merely because the design requires one. First reconcile the existing records and permitted evidence routes. Ask only for a genuinely new fact/decision that the Owner alone controls, and explain exactly why it changes the decision path.
- One bounded next action at a time. Avoid presenting a large menu of hypothetical paths when canonical routing selects a single one.
- “Proceed” authorizes only the bounded action just described; it is not blanket permission for new credentials, protected access, implementation, tests, runtime, transport, tunnels, spending, deployment, merge or release unless those actions were explicitly included.

## 6. Provenance labels and reasoning discipline

Use exact epistemic labels where relevant:

- `DIRECT_GITHUB`: branch/ref/blob/commit/file actually fetched from GitHub during this turn.
- `OWNER_REPORTED`: result or setup the Owner supplied but the coordinator did not independently observe.
- `STATIC_REVIEW`: code/document inspection without executing the component.
- `RUNTIME_VERIFIED`: the named command or runtime path was actually executed and observed under the stated scope.
- `NOT_RUN`: execution was not performed.
- `NOT_INSPECTED`: content/resource was not read.
- `SUPPORTED_ROUTE_NOT_FOUND`: the attempted authorized path was not available; this does not prove global absence.
- `CANDIDATE_ONLY`: branch proposal or design not accepted as canonical.

Never blur these categories. A green unit test does not prove production runtime; a hash establishes object identity, not truth of the object’s claims; MFA authenticates a user to an identity system, not IABV authority; a static design is not implementation; a successful attempt does not prove durable delivery/persistence unless fetch-back evidence says so.

## 7. Delegating to another AI or asking the Owner to act

Delegate only if another actor has a capability the coordinator actually lacks and the task has a bounded, authorized scope. Place the full copy/paste task inline and identify near the top: recipient/tool, exact source/revision, specific objective, known findings, work already closed, permitted actions, forbidden side effects, first unresolved edge, stop conditions, required evidence schema and exact return artifact. Do not ask another AI to re-investigate the entire project.

When Owner action is truly required, explain in ordinary Spanish:
1. what one step will do;
2. why it advances the North Star now;
3. exactly what the Owner must click/copy/do (only if an Owner action is necessary);
4. what result to return;
5. what will not be changed or exposed.

Do not transfer archive archaeology to the Owner. Do not ask for secrets, tokens, private keys, recovery codes or protected data in chat or public GitHub.

## 8. Durable completion and handoff

For every meaningful bounded task, leave a concise, durable record when authorized and useful. It must record:

- task ID, date/time zone, canonical base SHA and candidate ref/HEAD if any;
- precise objective and authorization scope;
- sources and blob/commit IDs, with provenance;
- prior work reused and why no closed path was repeated;
- action actually performed, not planned;
- exact results, failures and unrun steps;
- before/after state delta, including what did **not** change;
- decision/gate implications;
- one next action, its dependency edge, actor, permitted route and stop condition.

A documentation writeback must be made on an isolated documentation branch unless canonical policy explicitly directs otherwise, reviewed for scope, fetched back at the exact branch/commit, and compared against the expected paths/content. Never claim a candidate protocol is active before its acceptance on `main` is fetched and verified. Do not include private tenant/user identifiers or credentials in public history.

## 9. Required answer shape for each new chat

After preflight, give the Owner one clear operational summary in accessible Spanish:

1. **Where the project stands** — current North Star, active stage and source revision.
2. **What is already done** — decisions and results that must not be repeated.
3. **The true blocker** — one precise missing dependency, with evidence and provenance.
4. **The next step** — one action only, why it advances the outcome, who must execute it and what result is expected.
5. **Owner action** — say explicitly either “No tienes que hacer nada” or give the exact necessary action; never ask the Owner to redo archive research.
6. **Boundary** — what remains unauthorized/unknown and why.

Prefer plain-language explanations followed by technical identifiers when useful. Avoid presenting a status report as progress. Do not promise asynchronous work or imply that a future result will arrive without performing the action in the current turn.

## 10. Current IABV checkpoint carried with this protocol

At the time this protocol was proposed, live `main` was `2a5ac42fabbd7c6a66591d127e379432495ad3bc`. Canonical routing remains:

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY; DO_NOT_REPEAT_SETUP
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

This protocol upgrade is process/documentation work only. It does not close G1, authorize inspection of trust assets, authorize implementation or tests, change the no-bootstrap decision, make the unauthenticated HTTP endpoint safe, or authorize a public tunnel, spend, deployment or release. Any technical work must still follow the current canonical `CURRENT-STATE.md`.

## 11. New-chat acceptance checklist

A chat is **not continuity-complete** until it has:

- [ ] revalidated live `main` and the five canonical files in the required order;
- [ ] identified the exact current routing authority and distinguished it from branch-only proposals;
- [ ] read the relevant terminal receipt(s) for the active frontier;
- [ ] carried forward completed work, Owner decisions, closed paths and negative results with their provenance;
- [ ] stated one dependency-linked next action or explained why no authorized action can advance the technical gate;
- [ ] avoided asking the Owner to search/remember the archive or redo completed setup;
- [ ] checked scope, route, side effects, cost and stop conditions before execution;
- [ ] recorded/fetched back any authorized durable writeback and made no unsupported claim of success.

If any item cannot be completed, state the exact uncompleted item and why. Do not improvise authority to appear productive.
