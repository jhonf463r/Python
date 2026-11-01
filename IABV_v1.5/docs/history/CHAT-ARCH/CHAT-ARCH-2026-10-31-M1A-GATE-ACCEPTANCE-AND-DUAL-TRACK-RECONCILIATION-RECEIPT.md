# M1A authority-gate acceptance and dual-track continuation receipt

- Task: `IABV_M1A_DOC_STATE_PRECISION_AND_LANE_SPLIT_R1_20261031`
- Date: 2026-10-31 (America/Bogota)
- Scope: documentation-only adjudication of the supplied coordinator review and live canonical state.
- Authorization: explicit Owner instruction in the coordinating conversation: “ok procedamos”.
- Base: `main@b0f8032bf7914de983607c5247010f8b94276e0e`
- Base tree: `9ce8ed493910aaaa548472f3ac73c8a4ec52d0b9`
- CURRENT-STATE base blob: `4718db4cfe60daa2ce2148c90d2e25c43bd98da1`
- D021 base blob: `d96551cdc8ff601510b8c718615db3df6f3ad3a0`
- CONTEXT-INDEX base blob: `42d16e2e4bf51cbb23ff03c0d1026aad896dc7ca`

## 1. D021 §6B.1 post-adoption evidence adjudication

```text
D021_6B1_POST_ADOPTION_APPLICATION=ONE_PARTIAL_REPORTED_WITH_LIMITATIONS
D021_6B1_CAUSAL_ATTRIBUTION=NOT_ISOLATED
D021_6B1_FORMAL_INDEPENDENT_CAUSAL_REUSE=PENDING
D021_6B1_AUTOMATIC_CROSS_SESSION_BOOT=NOT_PROVEN
D021_6B1_RUNTIME_ENFORCEMENT=NOT_PROVEN
D021_6B1_GENERALIZATION=NOT_TESTED
```

This is not zero application and not a causal pass. The separately opened session's application was reported; its internal tool trace was not independently available to the coordinator. The task prompt explicitly instructed §6B.1 application and the session disclosed pre-existing context. The reported revision and canonical state were corroborated, but causal attribution to the stored rule is not isolated. Preserve the no-repeat gate as adopted; do not repeat the Entra/Authenticator or “another mechanism” questions.

## 2. Dual-track adjudication under D019/D020

- Lane A remains blocked at the task-local M1A/G1 authority and root-provenance edge.
- The wait applies only to this authority dependency. It is not a project-wide IABV stop.
- Lane B is not an automatic new task. It may be selected only when a current Owner objective, a concrete useful action and that action's own authorization exist independently of Lane A.
- Do not repeat R1, reconstruct R5, reconfigure Entra, repeat setup, or prepare implementation without a material evidence/precondition change and a valid authorization.
- No automatic follow-on is created.

## 3. M1A gate acceptance contract

These definitions preserve the adopted M1A v1.0.1 gate boundaries; they do not change them or close any gate. The complete normative acceptance contract for all eight gates is the [M1A v1.0.1 implementation-prerequisite evidence gate matrix](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md), blob `1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37`. That matrix remains normative if this concise route summary is read in isolation.

| Gate | Evidence required for adjudication |
|---|---|
| G1 — authenticated Owner/governance principal and trust anchor | Correlated evidence identifying the live Owner/governance principal and mandate plus the live server, issuer and reader principals; verifiable trust-root material and chain; authority binding to the relevant governance role; independent custodian/verification path; provenance, custody, rotation and revocation lifecycle; exact instance/revision scope; and Owner-to-Windows-principal binding where host identity is part of the protected boundary. An adoption token, MFA event or accountability statement is not a runtime credential or trust anchor. |
| G2 — catalogue publisher / producer policy | Authorized catalogue publisher; producer-class policy; integrity and version lifecycle; authoritative freshness, expiry and revocation. |
| G3 — operation-to-target resolver | Versioned server-side resolver bound to real registered operation IDs and implementation/call sites; caller-supplied scope, descriptive tool metadata or path strings are not authoritative resolution. |

**Cross-cutting same-object invariant:** the authorization decision must be evaluated against the identity-bearing target capability/open object that the reader actually consumes. A path-string decision followed by a separate open is not sufficient. A valid handle proves neither the legitimacy of the selected root nor an authorized operation.

Each of G4, G5, G6, G7 and G8 remains individually OPEN; none is closed. They are separate prerequisites, and G1–G3 evidence does not close any of them. No gate closes from MFA, a Git commit signature, a hash, a design, synthetic tests, a source-level handle candidate or a reported test count alone.

## 4. Reopening and stop conditions

Reopen only on genuinely new, independently verifiable and source-bound evidence that changes at least one required dependency: Owner mandate/principal; independent issuer/root and custody; policy publisher/revocation; exact server/process binding; versioned operation resolver; or the same-object authorization/consumption binding. Assess only the affected gate and its causal dependencies; do not restart the whole census.

Until then preserve:

```text
OWNER_INPUT_RECONCILED=NO_ADDITIONAL_MECHANISM_IDENTIFIED
OPTION_D=RATIFIED_NO_BOOTSTRAP
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
MCP_TOOL_ALLOWLIST=EMPTY
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
TESTS/BUILD/RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

No credentials, tokens, keys or production-root provisioning are requested or authorized by this receipt.

## 5. Separate repository-governance observation

At the base revision, the repository API reported `main.protected=false`; the repository rulesets endpoint returned an empty list. This observation does not invalidate the verified base commit/blob and does not change M1A's technical gate. It is a separate repository-governance risk. No branch protection, ruleset, permission or repository setting was changed in this task; any remediation requires a separately scoped authorization and compatibility review.

## 6. Exact scope and verification plan

Only these paths are in scope for this documentary update:

- `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — active header only; historical suffix is preserved byte-for-byte.
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-UAAL-D021-CROSS-SESSION-BOOT-AND-STATE-RECONCILIATION.md` — §6B.1 clarification.
- `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md` — pointer to this receipt.
- This receipt.

No product source, authorization implementation, credentials, permissions, branch-protection settings, protected reads, tests, build, runtime, tunnel or deployment are in scope.

**Completed verification:** PR #586 was merged as `cb5b13af0c06bacaa71e355d5b2baeb79e0d3226` from head `7e0270ace5cada4e185ecccd5ce5efddab7e019e`, based on `b0f8032bf7914de983607c5247010f8b94276e0e`. The exact diff contained the four paths listed above; the PR was mergeable and the merge was reported successful. Fetch-back from live `main` confirmed the following blobs:

- `CURRENT-STATE.md`: `b792ef0575e1998451467c07fd2e3a1a7e368b2e` (exact blob decoded; ordinary content read blank).
- D021: `c8873bf82653a27278ff335b9dccdd7e56aaa7e1`.
- `CONTEXT-INDEX.md`: `306bce5932e543069db1a5326314b41cac266168`.
- This receipt: `d2758197e6eccb5484cf3dbf9c22b4c351dc04d8`.

The `CURRENT-STATE.md` historical suffix after the first standalone `---` was compared against the PR base and was byte-for-byte equal. The active header contains the D021 status correction, task-local Lane A, conditional Lane B, G1/G2/G3 criteria and unchanged fail-closed controls.

A successful documentation merge is not technical M1A authorization or evidence of runtime enforcement.


## 7. Follow-on route-consistency correction — documentation only (2026-10-31)

```text
TASK_ID=IABV_DOC_ROUTE_REOPEN_TRIGGER_CONSISTENCY_R1_20261031
AUTHORIZATION=OWNER_EXPLICIT_DOCUMENTATION_ONLY
BASE_MAIN=0037ff4f8a92d779c3b9b015ca94b6a642ecc76e
SCOPE=FOUR_DOCUMENTATION_FILES_ONLY
PRODUCT_SOURCE=UNCHANGED
PERMISSIONS_AND_REPOSITORY_SETTINGS=UNCHANGED
TESTS/BUILD/RUNTIME=NOT_RUN
M1A_GATES=UNCHANGED; G1/G2/G3_NOT_ESTABLISHED; G4/G5/G6/G7/G8_OPEN
```

This follow-on correction aligns the active route with section 4 above: new independent, verifiable and source-bound evidence affecting **at least one open M1A dependency** permits reassessment of only that affected gate and its causal dependencies. A complete bundle of Owner mandate, issuer/root and exact-target evidence is not required before a partial dependency can be evaluated. The full v1.0.1 matrix remains normative and all eight implementation-acceptance gates remain open.

The 2026-10-27 handoff in `IABV_v1.5/AGENTS.md` is explicitly marked historical/superseded without deleting its provenance. Section 11 of the new-chat kit is likewise marked as a non-authoritative snapshot and points back to CURRENT-STATE. The CURRENT-STATE historical suffix after its first standalone `---` is preserved byte-for-byte.

This is documentation routing precision only. It does not provision or establish an authority, close a gate, authorize implementation or tests, enable protected reads, alter Option D, or change repository governance.
