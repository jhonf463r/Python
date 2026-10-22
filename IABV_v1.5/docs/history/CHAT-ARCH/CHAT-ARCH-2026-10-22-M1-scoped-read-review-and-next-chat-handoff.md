# M1 — Static review findings and next-chat continuity handoff (2026-10-22)

## 0. Routing authority and one active task

This record preserves the current episode so the next chat can continue without redoing work. CURRENT-STATE.md remains the sole routing authority; this is a detailed handoff, not a competing status file.

- **North star:** GOVERNED_IABV_CODEX_BRIDGE
- **Active task:** M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
- **Next actor:** Codex, same development session, same reported isolated candidate — only for a bounded source-backed review/repair of F-01–F-03.
- **Evidence delivered:** the Owner pasted Codex's partial implementation report, then the complete unified diff for exactly two files. The coordinator inspected the pasted diff, compared its base blob identifiers to public-main source, and compared its semantics against canonical Entry 274.
- **Single next action:** determine from narrowly relevant source/docs whether an authoritative, versioned operational-block scope model and trusted target resolver already exist. If not, stop and report the missing authority; do not invent a production registry or scope semantics.
- **Acceptance target:** F-01–F-03 are fixed using source-backed authoritative semantics, or a precise BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE result is returned with no guessed policy. This does not authorize test execution.
- **Governance:** KEEP_BLOCKED. Tests/builds/lint/runtime/process launches and real transport remain unauthorized. Do not access the Owner's dirty checkout, data/, SQLite, secrets or .env. No commit/push/PR/merge/release is authorized.

## 1. Canonical evidence and links

- [Current route and next action](./CURRENT-STATE.md)
- [M1 implementation handoff prepared for Codex](./CHAT-ARCH-2026-10-22-M1-governed-scoped-read-route-CODEX-implementation-handoff.md)
- [Codex-reported partial implementation](./CHAT-ARCH-2026-10-22-M1-partial-implementation-Codex-result.md)
- [Independent static diff review, F-01–F-03](./CHAT-ARCH-2026-10-22-M1-scoped-read-diff-static-review.md)
- [Entry 274 — consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md)
- [Entry 266 — observation approval is not audit release](./CHAT-ARCH-2026-10-13-266-observation-approval-is-not-audit-release.md)
- [Sonnet-reviewed, unmerged target-scope candidate review](./CHAT-ARCH-2026-10-22-candidate-target-scope-repaired-review.md)
- [GitHub issue #470](https://github.com/jhonf463r/Python/issues/470)
- [Coordination protocol, section 11](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md)

## 2. Evidence chain for this episode

### 2.1 Codex report supplied by the Owner — OWNER_REPORTED

Codex's report stated:

- Candidate folder: C:\temp\IABV_M1_GOVERNED_READ_CANDIDATE_20261022.
- Local branch: codex/m1-governed-scoped-read-route-20261022.
- Base/current HEAD: cb2f2b02ade297660431e7bbd5d0dce75d10e39c.
- Two dirty paths; no commit and no untracked files.
- Sparse clone reportedly included IABV_v1.5/src and IABV_v1.5/tests; IABV_v1.5/data reportedly absent.
- The Owner's dirty checkout, its data and SQLite reportedly were not inspected or modified.
- Changed files: src/iabv_v15/infra/mcp/server.py and tests/test_mcp_server.py.
- The reader/listing functions reportedly return scoped_read_authority_unavailable if the route gate allows the route but there is no verifiable scoped decision.
- Nine tests were reportedly added and four adjusted; none was executed. git diff --check was reported PASS but not independently reproduced.
- No test/build/lint/runtime, IABV/MCP/Codex/Ollama process, real transport, push, PR or merge was reported.

The reported candidate file blob IDs were 14eaa660b6f3ef66ae44638a551407ac37e8aa71 for server.py and 8ebd2c737ce6a3f3ef2336912a2ec9823ecc138d for test_mcp_server.py. These IDs came from the supplied report; they were not independently fetched from a candidate commit.

### 2.2 Exact diff received — OWNER_SUPPLIED_COMPLETE_DIFF

The Owner pasted the full output of these commands:

    git status --short
    git diff --no-ext-diff --unified=80 -- IABV_v1.5/src/iabv_v15/infra/mcp/server.py IABV_v1.5/tests/test_mcp_server.py

The reported status contained exactly these modified paths:

    M IABV_v1.5/src/iabv_v15/infra/mcp/server.py
    M IABV_v1.5/tests/test_mcp_server.py

The diff's base blob prefixes were:
- server.py: 17b87a15
- test_mcp_server.py: 93c11837

Those match the full pinned public-main blobs previously observed: server.py 17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c and tests/test_mcp_server.py 93c11837d39eaee60d2c818e522284f0f9c261d6. This supports that the pasted patch is based on the documented public-main file versions. It does not authenticate the local candidate folder/branch, verify the new blob IDs or establish that a live server runs these files.

The diff modifies:
1. _governance_block_for_route by adding operation_scope, a locally constructed route_scopes set and known_target_scopes set, and separate filter logic for assistant_kind and target_scope.
2. read_repo_file and list_repo_directory by replacing content/listing calls with fixed scoped_read_authority_unavailable denials when the broad route gate returns no block.
3. Regression tests covering several global/specific/unknown scopes and confirming the read/list response still excludes content when scoped authority is absent.

### 2.3 Narrowly consulted public source

- domain/models.py, pinned blob a9033d21052c519e09f482097599c704a62ea916, has distinct OperationalBlockRecord.assistant_kind and OperationalBlockRecord.target_scope string fields. It does not itself supply a finite, versioned authoritative registry or combination evaluator.
- services/evolution/world_model_service.py, pinned blob ba0b5f5d6233330b549e09863975c77c0db735d6, constructs records with concrete targets such as consult_external, heavy_local_model and ui_focus_interaction. Other target values are sourced from gate.required_for[0] and a tool/route scope. These are source examples/producers, not evidence of a single authoritative versioned scope registry or a complete mapping from every production operation to target identity.
- server.py, pinned public-main blob 17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c, registers the read/list tools and invokes the route gate with assistant_kind="audit", requires_network=False. No real production tool call in the supplied diff passes the new operation_scope argument.
- Entry 274 requires an authoritative versioned scope model, explicit dimension-combination semantics, fail-closed treatment of unknown/malformed/partially evaluable/conflicting scope metadata, and proof of non-applicability before an active block can be skipped. It expressly warns against inventing production scope dimensions from a test matrix.
- Entry 266 keeps observation permission distinct from repository-read permission and block release.

No local checkout, live server, secrets, data/SQLite, process or runtime was inspected by the coordinator.

## 3. Independent static-review result

Verdict: STATIC_REVIEW=FAIL_REPAIRS_REQUIRED. This is a finding about the supplied diff text, not a runtime or test verdict. Full itemized review is in [the dedicated static-review record](./CHAT-ARCH-2026-10-22-M1-scoped-read-diff-static-review.md).

### F-01 HIGH — no demonstrated authoritative/versioned scope model or resolver

The patch creates known_target_scopes locally and treats a known target_scope absent from the derived route_scopes as irrelevant by continuing to the next block. The diff gives no evidence the allowlist, target identity and dimension-combination semantics come from an authoritative versioned resolver. A finite list prevents one open-prefix matching pattern; it does not prove production non-applicability.

The route_scopes value is inferred from assistant_kind, a generated consult_<assistant_kind> alias, requires_network → consult_external, a special case gpu_benchmark → heavy_local_model, and the new caller-provided operation_scope. This is an implicit policy/combination model, not a source-verified contract.

**Required resolution:** inspect only the already-permitted candidate and directly relevant public source/docs for an existing authoritative/versioned scope model and trusted target resolver. Reuse it only if the evidence demonstrates its authority and versioning. If absent, do not improvise it; stop with the exact missing dependency and preserve denial.

### F-02 HIGH — operation_scope has no production call-site wiring in the supplied diff

The test named test_ui_focus_scope_only_blocks_matching_audit_operation calls the helper directly with operation_scope="ui_focus_interaction". That proves at most the helper's behavior when a test supplies that argument. The patch changes no actual registered MCP tool call site to pass operation_scope. No evidence therefore shows that a real operation receives the intended scope or that a production path is blocked by its target_scope.

**Required resolution:** only after F-01 yields an authoritative mapping, wire scopes at the narrowest applicable registered-tool call sites and author regression tests through the registered tool entrypoint. Do not add call-site labels by guesswork. If the mapping cannot be proven, do not invent call-site scopes.

### F-03 HIGH — the assistant_kind-first filter can hide unknown/conflicting target metadata

The diff normalizes block_assistant, then immediately skips the record when the assistant kind is neither empty, wildcard nor the current route. That happens before block_target is read and evaluated.

This has two direct consequences:

1. An unknown or malformed nonempty assistant_kind is silently treated as a proven unrelated route.
2. Even when target_scope is unknown or malformed, a record whose assistant_kind differs from the current route is skipped before the target uncertainty is considered.

For example, an active record with assistant_kind="not_a_registered_kind" and target_scope="scope_not_yet_mapped" is excluded by the assistant-kind branch before the target-scope fail-closed branch could act. A record with a known-but-mismatching assistant and an unknown target scope is similarly discarded without resolving whether its metadata is partially evaluable or conflicting. Entry 274 requires fail-closed handling for unknown, malformed, unsupported and conflicting metadata.

**Required resolution:** use the authoritative scope model from F-01 to distinguish a validated mismatch from unknown or conflicting dimensions. Unknown/malformed/unsupported dimensions and unresolved combinations must not be treated as proof of non-applicability. If the authoritative model does not exist, keep the gate closed instead of creating an unvalidated whitelist.

## 4. Positive interim result and its limits

The direct calls to audit_tools.read_repo_file and audit_tools.list_repo_directory are replaced with denial payloads when the broad route gate returns no block. A target-scope correction therefore does not disclose content by itself. The changed tests assert the denied response has no content or entries. This is a reasonable interim closed state.

It is not the supported scoped-read route. There is no demonstrated request → trusted local Owner approval → verified issuer → server-side per-operation decision → expiry/revocation check → durable receipt → race-resistant opened-object containment chain in this diff. The server/checkout identity and active transport authentication remain unverified. A read grant cannot release an operational block; no independent block-release authority is established.

## 5. What must not be repeated or inferred

- Do not request the full diff again; it has been supplied and statically reviewed.
- Do not repeat the broad source scan, earlier tool-inventory prompts or the ordinary IABV general-chat request to discover this route. That route has previously drifted into a broad auto-scan.
- Do not use another reader to bypass the denied MCP reader.
- Do not treat Sonnet's static PASS on the prior target-scope candidate as approval of this implementation or as runtime/test success.
- Do not claim the public-source gate defect caused the live server's refusal. Live server/checkout identity and active block state remain unverified.
- Do not run tests/builds: tests are authored only; TESTS=NOT_RUN.
- Do not infer test success from the diff or the reported git diff --check PASS.
- Do not touch the Owner's dirty checkout, data/, SQLite, secrets, .env, machine configuration, processes, IABV/MCP/Codex/Ollama, transport, or release operations.
- Do not add a remotely exposed MCP grant/release action while transport authentication is unverified.
- Do not publish, push, create a PR, merge, deploy or claim M1 complete.

## 6. Copy-ready bounded handoff for Codex

**Destination:** the Owner's existing Codex development session.
**Working location:** only C:\temp\IABV_M1_GOVERNED_READ_CANDIDATE_20261022 as previously reported. Verify that this is the named isolated candidate before any operation. If identity is not verifiable, stop. Do not inspect or alter the Owner's dirty checkout.

~~~text
M1 FOLLOW-UP — REPAIR F-01–F-03 USING ONLY SOURCE-BACKED AUTHORITY

Canonical task:
M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE

Read the latest CURRENT-STATE.md and this review:
https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1-scoped-read-review-and-next-chat-handoff.md

Also read Entry 274:
https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md

The complete diff has already been reviewed. Do not repeat that request or implement another guessed allowlist.

Bounded task:
1. In the named isolated candidate only, inspect the already relevant sources and exact references: server.py, domain/models.py, services/evolution/world_model_service.py and registered audit-tool call sites. Use Entry 274. Do not conduct a broad repository scan.
2. Determine whether an existing authoritative, versioned OperationalBlockRecord scope model/resolver and trusted operation-target mapping exists. Distinguish observed producer strings from an authoritative, complete registry and policy.
3. If such a model exists, cite its exact path/symbol/source and use it to resolve F-01. State and use the actual combination semantics rather than guessing AND/OR semantics or treating test values as authority.
4. Resolve F-03: unsupported/malformed assistant_kind or target_scope, and conflicting/partially evaluable pairs, must not be silently dismissed as a proven mismatch. In particular, the assistant_kind-first continue must not hide an unknown target_scope.
5. Resolve F-02 only from that same source-backed mapping: wire operation_scope at actual registered tool call sites that the mapping proves need it. Add focused regression tests for unknown/malformed assistant_kind, validated mismatch versus unknown target_scope, crossed dimensions, global/wildcard blocks, and any real operation-scope case. Tests may be authored but not run.
6. If an authoritative model/resolver cannot be found from these bounded sources, stop without inventing one. Keep all content reads denied and report BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE, with the source paths/symbols checked and the exact missing authority. Do not change policy to make tests pass.
7. If the repair is source-grounded, modify only the minimum necessary files in this isolated candidate, preserve the read/list fail-closed response, and provide the full unified diff plus branch/base/HEAD/status receipts.

Hard constraints:
- No tests, build, lint, scripts, runtime, launches, MCP calls or real transport.
- Do not touch the Owner's dirty checkout, data/, SQLite, secrets or .env.
- No new authentication, installs, spend, environment/model/GPU changes.
- No commit, push, PR, merge, deployment, live-block release, or claim that M1/bridge is ready.
- If candidate identity or authority cannot be verified, stop and report rather than improvising.
~~~

## 7. Process knowledge extracted from this episode

These lessons should be reused on the next relevant decision. Documentation alone does not prove behavioral learning.

1. **Report → artifact → review.** A Codex summary was insufficient for a safety adjudication. Requesting the exact unified diff exposed branch-filter ordering and enabled a meaningful static review without reading the blocked live checkout.
2. **Verify provenance without overstating it.** Diff base prefixes matched pinned public-main blobs. That supports the claimed source base, not the local candidate identity, its new blobs, a commit or live runtime.
3. **Separate two gates.** Operational-block applicability determines whether a route may proceed; scoped-read authority independently determines whether file content may be returned. The candidate keeps reads denied after the route gate permits the route, which is correct as an interim fail-closed state.
4. **A known-value allowlist is not automatically authoritative policy.** Replacing open-prefix matching with a finite set closes one pattern, but safe decisions also require a versioned vocabulary, trusted target resolver and explicit combination semantics. “Known string” is not equivalent to “proven non-applicability.”
5. **Combined dimensions must not erase uncertainty.** Filter order matters: an assistant mismatch must not hide an unknown or conflicting target dimension. The test matrix must cover cross-products, not just one-field examples.
6. **Helper-level tests are not call-site evidence.** Calling the helper with operation_scope does not prove that a real registered tool supplies the scope.
7. **Authorship, execution and runtime are separate states.** Tests can be authored but not run. Static review can fail without running code. Documentation can be persisted without proving that a local candidate is published. Keep OWNER_REPORTED, HEAD_SOURCE, TESTS=NOT_RUN, LIVE_MCP_IDENTITY=UNVERIFIED and BRIDGE=BRIDGE_NOT_READY distinct.
8. **The partial fail-closed patch is not M1 completion.** M1 still needs trusted Owner principal/issuer, verified server/session/checkout identity, per-operation server-side decisions, expiry/revocation, durable independently verifiable receipts, race-resistant file-object containment and separate block-release authority.
9. **No circular authority.** A read decision cannot release an operational block; a request is not approval; observation-window grant is not repository-read authority; and no remote MCP grant/release action is permitted while transport authentication is unverified.
10. **Progress is verified edges, not percentages or narrative.** Newly verified coordinator-side edges: full diff was supplied in chat; base prefixes match pinned public-main file blobs; static review completed; F-01–F-03 recorded. Candidate isolation, new blob IDs, test behavior and live-server causal linkage remain unverified.
11. **No-loop continuation.** Do not repeat the full-diff request or prior broad inventories. Continue only with the source-backed authority question blocking the next decision.

## 8. Current state tuple

~~~text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
M1_STATUS=STATIC_REVIEW_FAIL_REPAIRS_REQUIRED
CANDIDATE_BRANCH=codex/m1-governed-scoped-read-route-20261022
CANDIDATE_BASE_AND_HEAD=cb2f2b02ade297660431e7bbd5d0dce75d10e39c
CANDIDATE_COMMIT=NONE_REPORTED
REVIEW_INPUT=OWNER_SUPPLIED_COMPLETE_DIFF
FINDINGS=F01_AUTHORITATIVE_SCOPE_MODEL;F02_OPERATION_SCOPE_NOT_WIRED;F03_UNKNOWN_DIMENSION_MAY_BE_SKIPPED
SCOPED_READ_REQUEST_APPROVAL_FLOW=NOT_IMPLEMENTED
READ_AND_LIST_ACCESS=FAIL_CLOSED_IN_SUPPLIED_DIFF
TESTS=NOT_RUN
LIVE_MCP_IDENTITY=UNVERIFIED
LIVE_CHECKOUT_IDENTITY=UNVERIFIED
REAL_LOCAL_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
OWNER_DIRTY_CHECKOUT=DO_NOT_ACCESS_OR_MODIFY
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
~~~
