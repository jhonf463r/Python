# CHAT-ARCH-2026-10-13-248 — Codex exec launch-contract design ready for Owner adjudication

- **Episode ID:** `CHAT-ARCH-2026-10-13-248`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline verified for this adjudication:** `main @ 820bb33f626209cc7f46543e7e083d3384e5d921`
- **Input:** Owner-supplied design report `CODEX_EXEC_LAUNCH_CONTRACT_DESIGN_READY_FOR_OWNER_ADJUDICATION`
- **Related records:** entries 243–247.
- **Adjudication:** `CODEX_EXEC_LAUNCH_CONTRACT_DESIGN_READY_FOR_OWNER_ADJUDICATION`
- **First open edge:** `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`

## 1. Provenance and continuity

The current remote `main` SHA was fetched from GitHub as `820bb33f626209cc7f46543e7e083d3384e5d921`, matching the SHA named in the supplied report. The canonical entry 247 and entry 246 were fetched from remote `main`; the prior record 247 is absent from the older owner-reported local checkout, which is expected when that checkout predates the documentation-only remote writeback.

The local worktree facts remain Owner-reported, not independently inspected here:
- branch `codex/m0a-safe-ui-boot`;
- HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`;
- tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`;
- 56 tracked modified files and 6 untracked files.

Preserve all local changes, including `.pyc` changes. This documentation adjudication did not inspect or modify that worktree, launch a process, invoke Codex, run tests, access credentials, or verify a live IABV→Codex→IABV exchange.

## 2. Design adjudication

The supplied proposal is accepted as **design-ready for Owner adjudication**, not as an approved implementation design and not as permission to implement or execute it. Its central direction is correct: the existing authorization/task correlation needs to bind to the actual child executable, environment, candidate baseline/root, permitted effects and no-publication policy *before dispatch*. A final message is not a diff; a Job Object is not an OS security boundary; a requested sandbox is not proof of effective enforcement.

The proposed artifact receipt should correlate at minimum:
- SafeUI authorization and operation identity, stable task ID, prompt/digest and dispatch ID;
- canonical executable identity/version, selected home/config provenance and intended policy;
- disposable candidate root and baseline/tree identity;
- terminal exit/timeout/interruption status, final response, relevant structured events, changed paths and independently computed diff/digests;
- evidence from only the separately authorized tests;
- consumer/verifier evaluation and explicit Owner decision.

Any timeout, mismatched identity, unexpected executable, altered baseline, missing diff or incomplete terminal result must fail closed. No automatic retry, commit, push or promotion follows from a completed CLI turn.

## 3. Important unresolved design conflict: dedicated home versus existing authentication without new setup

The proposal correctly requires an explicit home and forbids copying credentials. It also requires existing authentication and no additional spend. These constraints must be resolved together before implementation; they cannot be assumed compatible.

The Owner/design adjudicator must choose a supported policy:
1. An already-authenticated, explicitly Owner-approved home may be selected if source and configuration inspection establish the path and the proposed security boundary adequately protects its credential store; or
2. An already-authenticated dedicated home may be selected if it already exists and can be used without new OAuth, copying credentials, installation or additional spend; or
3. If neither is available under current constraints, retain the block. Do not create an empty dedicated home and call it authenticated, migrate/copy credential files, start a new login flow, or infer authorization from a package installation.

Which home, if any, meets those conditions is `UNPROVEN`. The Owner must adjudicate the acceptable home/authentication pattern without disclosing credentials. A dedicated `CODEX_HOME` is a design requirement to consider, not a pre-existing environment fact.

## 4. Independent gates that remain open

| Gate | Current evidence | Decision |
|---|---|---|
| SafeUI authorization and task identity | Report cites existing fields and pre-dispatch guard in current source | Existing operation authorization does not yet bind all coding-specific resource/policy/artifact properties |
| CLI interface | Entry 246 cites public `rust-v0.120.0` declarations | Does not prove which executable the IABV child will run or runtime acceptance |
| Child environment and Codex home | No integrated IABV `exec` launch contract found in supplied inspection | `UNPROVEN`; select only through an explicit future launch contract |
| Windows filesystem/command/network confinement | Requested settings/documentation and a Job Object are not enforcement evidence | `UNPROVEN`; must fail closed unless effective boundary is demonstrated |
| MCP/plugin/app side effects | No pre-effect exclusion guarantee established | `UNPROVEN`; default-deny or demonstrably disable unapproved effects in any future design |
| Existing authentication, entitlement, quota and zero-extra-spend | No live lookup/task was run | `UNPROVEN`; independent gate; no API key/OAuth/new payment/install |
| Diff and artifact handoff | Existing `ToolResult` reportedly has artifact/metadata fields | Data-model support does not prove diff production or consumer evaluation |
| Independent verification and publication | No candidate was produced | No commit/push/promotion; Owner retains sole decision authority |

The source paths and line references cited by the supplied report are useful provenance, but this writer has not independently re-opened the owner-local source file contents. The code facts above therefore remain sourced to that report unless otherwise explicitly stated.

## 5. Minimal route recommendation

Keep `codex exec` as the leading candidate for design, since the existing App Server composition is reported to return text/IDs and does not currently establish a writable candidate-diff handoff. Do not build a separate executor yet. Before implementation, adjudicate the authentication/home conflict and the exact scope of the OS-enforced boundary.

After Owner decision, the smallest next design delta is to turn the proposal into an explicit preflight/receipt contract: inputs that must be authorized, values that must be immutable, fail-closed checks before dispatch, evidence artifacts required at terminal completion, and acceptance/rejection by the existing consumer. This is still design work. A separate explicit authorization is required for implementation; another separate authorization is required for a runtime capability fixture.

## 6. First open edge

`CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`

Required Owner decisions before implementation:
- Is an already-authenticated approved home acceptable, or must it be an existing dedicated home?
- If no home satisfies the no-credential-copy/no-new-login/no-extra-spend constraints, is the route to remain blocked?
- What exact disposable candidate root and baseline may a later task use?
- Which command and network capabilities are genuinely required, and which external integrations must be denied before effects?
- What evidence is enough to accept the Windows sandbox as effective, and which independent verifier/consumer will evaluate the resulting diff?

These questions are gates, not permission to investigate secrets or run a turn.

## 7. Explicit non-authorization and learning boundary

No implementation, process, CLI/App Server invocation, agent turn, test, build, credential/session inspection, installation, OAuth/API setup, extra spending, source/config mutation, commit, push or promotion is authorized by this entry. Preserve the dirty local worktree and all untracked content.

This writeback is external persistent project memory. It does not prove automatic model learning, live execution, successful artifact ingestion, or later causal reuse.
