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

These definitions preserve the adopted M1A v1.0.1 gate boundaries; they do not change them or close any gate.

| Gate | Evidence required for adjudication |
|---|---|
| G1 — authenticated governance principal / trust anchor | Authenticated Owner/governance principal and mandate; independent trust anchor and custodian/verification path; issuer-to-reader/exact-server trust chain; Owner-to-Windows-principal binding. |
| G2 — catalogue publisher / producer policy | Authorized catalogue publisher; producer-class policy; integrity and version lifecycle; authoritative freshness, expiry and revocation. |
| G3 — operation-to-target resolver | Versioned server-side resolver bound to real registered operation IDs and implementation/call sites; caller-supplied scope, descriptive tool metadata or path strings are not authoritative resolution. |

**Cross-cutting same-object invariant:** the authorization decision must be evaluated against the identity-bearing target capability/open object that the reader actually consumes. A path-string decision followed by a separate open is not sufficient. A valid handle proves neither the legitimacy of the selected root nor an authorized operation.

G4–G8 remain separate prerequisites. G1–G3 evidence does not close them. No gate closes from MFA, a Git commit signature, a hash, a design, synthetic tests, a source-level handle candidate or a reported test count alone.

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

The PR must be checked for exactly these four paths, exact base, preservation of the CURRENT-STATE historical suffix, consistency of gate status and correct fetch-back. A successful documentation merge is not technical M1A authorization or evidence of runtime enforcement.
