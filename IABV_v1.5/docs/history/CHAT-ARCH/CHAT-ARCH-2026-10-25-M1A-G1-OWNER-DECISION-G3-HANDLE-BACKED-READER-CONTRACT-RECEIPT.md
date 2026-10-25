# Owner decision — authorize one bounded G3 handle-backed reader-contract task

- Date: 2026-10-25, America/Bogota.
- Decision: **OWNER_EXPLICIT_SCOPE_APPROVED**.
- Decision provenance: the Owner replied “si autorizo” to the immediately preceding explicit question authorizing exactly one new Codex task in the existing Windows session, limited to the G3 handle-backed same-object reader contract, bounded source-code changes, tests not executed, and all protected reads blocked. This receipt records the in-chat statement; it does not independently authenticate an external identity event.
- Repository baseline for this decision: live **refs/heads/main** was verified identical to **2968b0c836b38e61d5c2e659d9c4847c0558674a** immediately before this documentation branch was created.
- Task identifier: **M1A_G1_G3_HANDLE_BACKED_READER_CONTRACT_SOURCE_CANDIDATE_20261025**.
- Prior task remains terminal: **M1A_G1_INTEGRATED_AUTHORIZATION_ORGAN_SOURCE_COMPLETION_CANDIDATE** returned **BLOCKED_ON_EXTERNAL_TRUST_BOUNDARY** with no reported new source delta. This decision does not reopen or repeat that task.

## 1. Authorized task — exactly one

Use the already existing Codex Windows session and the existing reported candidate checkout, after verifying it in-session:

- Reported checkout: **C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27**
- Reported branch: **codex/m1a-g1-owner-governed-bootstrap-organ-20261024**
- Reported HEAD: **6bc568e1c5a898afd65cc045c779c25a9cdc5489**
- Reported pre-existing worktree: 7 staged routes, 11 unstaged routes, 12 unique routes.
- Reported index SHA-256: **8a32e6f7b2d642ee4a0217f96df037497cf47ecac52cecbea08717d4b8cb301a**.

These checkout details and dirty-state values are **OWNER_SUPPLIED_CODEX_REPORT** and must be revalidated by Codex before edits; this receipt does not claim local Windows access. Do not switch to a fresh public-main checkout, reset or clean the existing candidate, or alter the pre-existing index/staged changes.

Permitted: narrow source inspection directly along the known G3 call path; source-only changes limited to the genuine handle-backed authorization-to-reader contract and its directly related focused source tests; author or adjust those tests but do not execute them. If a safe, genuine same-object implementation cannot be supported by the current code/platform primitives within this scope, make no unsafe fallback and return an explicit blocker.

## 2. G3 acceptance criteria

1. The authorization decision and reader must share the same live, identity-bearing opened filesystem object; a canonical path string, previously resolved path, stat result, copied identity fields alone, or a second path lookup is not proof of same-object consumption.
2. The authorized object must have explicit type and lifetime/ownership semantics. The content reader must consume that same handle/object rather than re-resolving the original path through Path.read_text, stat, os.listdir(path), or equivalent path-based helpers after authorization.
3. File reads and directory enumeration must each state how the exact object is bound. Reparse-point behavior, ancestor/path traversal semantics, object replacement races, handle closure/invalidation, and unsupported platforms/providers must be explicit. If the available primitive cannot establish these semantics, deny and report the missing primitive; do not disguise a path-based fallback as handle-backed.
4. Keep all production default/unconfigured paths fail-closed. A synthetic ALLOW, local mock provider, or written test must not be described as production authority or a G3 pass.
5. Focused regression tests may be authored for handle identity propagation, cross-object substitution/path re-resolution denial, directory/file semantics and unsupported-provider denial. They remain source artifacts only because test execution is prohibited.
6. Provide exact complete diffs against the pre-edit file-byte baselines, file paths, before/after SHA-256 values, a clear separation between existing staged/unstaged work and this task's new delta, plus preservation evidence for the original index and unrelated routes. Do not omit diff hunks.

## 3. Prohibited side effects

- Do not run tests, build/compile, runtime, MCP calls, real transport, or any protected read.
- Do not provision, search for, or configure authority roots/mandates/custodians, credentials, certificates, certificate/key stores, TPM, Entra/Authenticator, Windows services, ACLs, registry, IPC/named pipes, or other OS/platform trust.
- Do not change services, environment, operating-system configuration, network/tunnels, credentials, applications, or spend funds.
- Do not stage, commit, push, publish, merge or deploy product/source changes. Do not discard, rewrite or stage any pre-existing candidate work.
- Do not repeat the broad source review, previous micro-patches, trust-asset inventory, TPM path or Entra setup.
- Do not claim G1, G2 or G3 closed; do not enable positive protected reads.

## 4. Required terminal report and stop

Return one bounded task result with:
- exact TASK identifier and one TASK_RESULT;
- preflight checkout path, branch, HEAD, status and index hash, with provenance;
- exact files changed and complete diffs against preserved pre-edit bytes, diff/file hashes and preservation checks;
- what was implemented, partially implemented, or blocked, distinguishing a source contract from operating-system/runtime proof;
- SOURCE_TESTS=AUTHORED_OR_UNCHANGED; NOT_RUN, TESTS=NOT_RUN, BUILD=NOT_RUN, RUNTIME=NOT_RUN, MCP=NOT_RUN, REAL_TRANSPORT=NOT_RUN, PROTECTED_READS=FAIL_CLOSED;
- unresolved edge and exact evidence needed to close it.

Terminal classifications may be G3_HANDLE_CONTRACT_SOURCE_ONLY_CANDIDATE, PARTIAL_G3_HANDLE_CONTRACT_SOURCE_ONLY, BLOCKED_ON_PLATFORM_HANDLE_SEMANTICS, or NO_SOURCE_DELTA. Do not claim an implementation outcome before observing it.

After the one task report, stop. AUTOMATIC_FOLLOW_ON=FALSE; any further technical action requires a fresh explicit Owner decision. The source candidate remains non-canonical until separately reviewed, and G1/G2, authority bindings, rollback-resistant replay, and bridge readiness remain unresolved regardless of this task's result.

## 5. Canonical status at authorization

~~~text
OWNER_DECISION=EXPLICIT_SCOPE_APPROVED_IN_CHAT
OWNER_DECISION_RECEIPT=THIS_DOCUMENT
ACTIVE_TASK=M1A_G1_G3_HANDLE_BACKED_READER_CONTRACT_SOURCE_CANDIDATE_20261025
TASK_COUNT=ONE
SOURCE_CHANGES=BOUNDED_G3_CONTRACT_AND_DIRECTLY_RELATED_SOURCE_TESTS_ONLY
SOURCE_TEST_AUTHORING=PERMITTED; EXECUTION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED; TASK_AUTHORIZED; NOT_YET_OBSERVED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
STOP_CONDITION=RETURN_ONE_TERMINAL_REPORT; NO_FOLLOW_ON
~~~
