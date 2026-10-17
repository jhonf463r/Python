# CHAT-ARCH 2026-10-17 — R10 v0.7.2 audit closure

- **Verdict:** `FAIL`
- **Scope:** documentary/hash/matrix review of the supplied R10 v0.7.2 package.
- **Governance:** `GOVERNANCE = KEEP_BLOCKED`
- **Implementation:** not authorized; no v0.7.3 created; no contract/matrix rewritten.
- **Local checkout:** not inspected.
- **Product-code execution / tests / build / runtime:** `NOT_RUN` / `NOT_RUN` / `NOT_RUN` / `NOT_RUN`.
- **Non-product inspection tools used:** shell utilities/scripts on temporary extracted copies (`unzip`, `sha256sum`, `grep`, Python CSV/regex). This is not an absolute “no shell commands” run; it is disclosed because hash verification was required.

## 1. Input artifacts and hash verification

Claude reports computing SHA-256 over the bytes extracted from the ZIP and matching all six payload files to the manifest. The seventh file, `R10_V0_7_2_SHA256.txt`, is the manifest and does not hash itself.

| Artifact | Bytes | Hash result |
|---|---:|---|
| `R10_V0_7_2_RECONSTRUCTED_CONTRACT.md` | 33,982 | Match |
| `R10_V0_7_2_TEST_MATRIX_T123_T196.csv` | 47,684 | Match |
| `R10_V07_REFERENCE_NAMESPACED_NONNORMATIVE.md` | 60,428 | Match |
| `R10_V0_7_1_AUDIT_REPORT_CLAUDE.md` | 10,816 | Match |
| `R10_V0_7_2_AUDIT_README.md` | 3,480 | Match |
| `R10_V0_7_2_AUDIT_PROMPT_FOR_CLAUDE.md` | 3,084 | Match |

**What this establishes:** the extracted bytes match the hashes declared by the package manifest.

**What this does not establish:** semantic correctness, identity of the absent original v0.7.1 artifact, byte-level/version equivalence to v0.6, or equivalence with the namespaced reference. The README explicitly says the reference is not a byte-identical copy. The contract's reference to hash `5babd981…` is not verifiable from the supplied package and remains `UNVERIFIED`. Original v0.7.1 identity is `OWNER_REPORTED`.

### Read coverage and provenance

- Read fully: reconstructed contract, README, v0.7.1 audit report.
- Matrix: all 74 rows passed full-text programmatic scans; approximately 40 rows were read in full.
- Namespaced reference and packaged audit prompt: partial reading only. For the reference, namespace and invariant table/conclusion were reviewed; for the prompt, only the heading. The rest remains `UNVERIFIED`.
- Directly inspected package evidence: hash calculations, contract, README, v0.7.1 report and CSV.
- `OWNER_REPORTED`: assertions in the v0.7.1 audit and manifest, the original v0.7.1 artifact, and hash `5babd981…`.
- No local checkout inspection and no source/runtime validation.

## 2. D1–D6 adjudication

| Dimension | Verdict | Findings |
|---|---|---|
| D1 | `CLOSED_IN_TEXT` | 74 unique IDs T123–T196, no gaps; T185–T196 match the required 12 scenarios. The reference has no T123–T196 IDs without the `REF_V07_` prefix, although a grep can miss lines mixing both forms. Minor debris: T159 cites nonexistent §10.1; T144, T154 and T164 retain heading text from the reference. |
| D2 | `OPEN` | Contract clauses §2.1/§6.1 prohibit “greater seq”; §6.2 disables automatic resolution; §12 rejects manual evaluation as AUTO. Yet T162 directly activates evaluation in quarantine A and makes B `SUPERSEDED`, contrary to §12 and §8.3's requirement for new IDs. T184 encodes the correct path. §0 declares the CSV the normative ID register but gives no precedence rule for clause/oracle conflict. |
| D3 | `PARTIAL` | §4.1 requires `dispatch_turn_id`, attests `in_reply_to` equality, and otherwise returns `UNCORRELATED`. T135/T176 cover old turn offered to new dispatch; T136 covers missing turn evidence. T141 reports `CORRELATED` without the parent relation, relying on nonce/time/turn verification contrary to §2.3/§4.1. T138 adds nonce expiry not specified by the contract. No row verifies fail-closed behavior for conversational AUTO dispatch with no `dispatch_turn_id`. |
| D4 | `PARTIAL` | Unique key `(destination_id, result_lineage_id, contribution_kind)` appears consistently in §1.3/§8.3 and T155/T156/T159/T177/T192. T130/T131 introduce a second exclusivity key for one `STRATEGY.ACTIVE` per `strategy_lineage_id`, a “CAS: first wins” choice and `version_seq`, absent from the contract. “Reverse order, same result” is incompatible with first-wins semantics. |
| D5 | `CLOSED_IN_TEXT`; atomicity `UNPROVEN` | §8.3 says contributions become unobservable upon `CONFLICT_DETECTED` or `TOMBSTONE_COMMITTED`, with retraction obligation persisted in the same transaction; §8.2 specifies recovery. Covered by T133/T166/T171/T182/T184/T192/T196. Textual clarity does not establish transactional implementation. |
| D6 | `PARTIAL` | Authorization/projection generations, task-local seq, plan states and canonical mode are mostly specified. §3.3 lists FAILED/ABORTED/TIMED_OUT without events/writers in §§11–12, although T132/T173 use them. Fourteen rows use undefined vocabulary: T127/T131/T139/T142/T143/T144/T147/T154/T158/T164/T165/T166/T169/T173. Examples: `mode=REAL`, `PLAN.EXECUTING`, `generation_id`, `FREEZE`, `RUNNING`, `idempotency_key`. T165/T169 expect `FENCING_VIOLATION`, while §9 says `AUTHORIZATION_GENERATION_MISMATCH`, which occurs in no CSV row. T180 case B at exactly t0+600s has no declared result although §10 says “only after” the deadline. |

## 3. SC1–SC10

| SC | Status | Remaining issue |
|---|---|---|
| SC1 | `CLOSED_IN_TEXT` | §3.1/§7(4); T123–T126/T175/T185/T187 support text-level distinction. |
| SC2 | `PARTIAL` | T141 lacks attested parent relation; T138 expiry lacks contract support; no dispatch-level AUTO case without turn ID. |
| SC3 | `CLOSED_IN_TEXT` | §1.3/§8.2; T155/T156/T159/T177/T192; implementation atomicity still unproven. |
| SC4 | `CLOSED_IN_TEXT` | §6.3; T150/T167/T178. |
| SC5 | `PARTIAL` | §5; T145/T179. The validator reports its own digests, but §7(7)'s “evidence contract” is undefined. The text fails closed via `BASE_ELIGIBLE=false` when a prerequisite is absent. |
| SC6 | `CLOSED_IN_TEXT` | §2.3/§10; T163/T180, with unresolved deadline-edge result. |
| SC7 | `CLOSED_IN_TEXT` | §6.1; T171/T181. |
| SC8 | `CLOSED_IN_TEXT` | §9; T165/T166/T182/T190/T193, with code mismatch noted under D6. |
| SC9 | `CLOSED_IN_TEXT` | §§11–12; T140/T183/T194. |
| SC10 | `PARTIAL` | §2.2/§8.3/T184 support new-ID behavior, but T162 contradicts it. No dedicated row tests same identity with different digest; only a check in T143. |

## 4. Test matrix T123–T196

- 74 rows; all are `NOT_RUN`.
- T123–T174 (52 rows): `RECONSTRUCTED_FROM_V0_7_REFERENCE_NOT_HISTORICAL_V0_6`.
- T175–T196 (22 rows): `RECONSTRUCTED_ADVERSARIAL_SCENARIO_NOT_EXECUTED`.
- No “Review required”, “Derive from”, “See source_test_body” or “TBD” marker was found in the scan. The previous report's 62 rows with v0.7.1 markers are `OWNER_REPORTED` and were not reproduced in this scan.
- The scan reported no actual disjunctive oracles. Twenty-one rows (T175–T185 and T187–T196) list oracle events without an explicit expected outcome; this is a heuristic scan and outcome is inferred from scenario names, deltas, failure column and controls.
- T124–T126 reference T123 instead of being self-contained.
- CSV lacks separate columns for correlation, allowed/prohibited effects and acceptance oracle; these are in prose. Most rows T123–T164 repeat “No injected crash…” in the crash column.
- T185–T196 have no reassignment and map one-to-one to the required list.

A documented row is not an executed test.

## 5. Invariant traceability I1–I12

I1–I12 exist in contract §14 as `RECONSTRUCTED_FROM_REVIEW`; historical equivalence is `UNPROVEN`. The reference maps only I–VIII, and the v0.7.1 report says I9–I12 did not exist there; that source/history claim and the provenance of I9–I12 remain `UNPROVEN`.

- I1: mode discriminates correctly; remainder partial.
- I2/I3: partial; T141 is weak and T143 uses undefined `idempotency_key`.
- I4: partial; T192's application-crash case does not address its criteria.
- I5/I8: partial; T191 uses `LATE_STALE`, T173 undefined vocabulary, T180 unresolved deadline edge.
- I6/I7/I9: discriminating behavior exists, but T130/T131 introduce a second key in I7 and T158 uses undefined vocabulary in I9.
- I10: partial; T162 contradicts contract and T188 does not treat writers.
- I11: weak; only T195, with no explicit result in its oracle.
- I12: T196 touches L4/L5b only; no row covers L5a or distinguishes L0–L3.

## 6. Proposed minimal repairs (all `PROPOSED`)

- **M0 — Precedence:** add a rule specifying that clauses control when an oracle conflicts with the contract, and the conflicting oracle must be removed/corrected.
- **M1 — T162:** rewrite to the T184 path (no direct activation and use new IDs) or remove as duplicate.
- **M2 — T141/T138:** require attested parent relation in T141; remove T138 or support nonce expiry with a contract clause; add AUTO conversational dispatch without `dispatch_turn_id` and require fail-closed.
- **M3 — Vocabulary/codes:** map the 14 rows to canonical terms; align T165/T169 with §9; define events/writers for FAILED/ABORTED/TIMED_OUT.
- **M4 — T130/T131:** remove them or add normative contract clauses for their additional key and semantics.
- **M5 — Explicit outcomes:** declare expected results for the 21 rows without them and for T180 case B at exactly t0+600s.
- **Minor:** correct I4→T192, I10→T188 and I12→T171–T173 mappings; define the “evidence contract” in §7(7).

These are proposed/documentary repairs only. No corrected v0.7.3 was produced and no source package files were changed.

## 7. Implementation dependencies remain unproven

- Authenticated turn correlation.
- Attested observed mode and route.
- Validator execution evidence.
- Trusted clock.
- Durable sequencer.
- CAS, transactions and read barriers.
- Fencing and authorization generations.
- Reviewer independence.
- Atomic recovery.
- Legacy code isolation.
- Coherent L4/L5b publication.
- Counterfactual replay.

Textual contract completeness does not prove any of these implementation properties.

## 8. Acceptance decision and next step

**Final verdict: `FAIL`.** D1 and D5 are closed in text, and SC1/SC3 text-level protections are present. D2 remains open because normative matrix oracles contradict clauses and there is no clause-over-oracle precedence rule. In particular, T162 can certify direct activation of previously blocked effects (SC10), and T141 can certify `CORRELATED` without the parent relation (SC2). Thus `PASS_WITH_REPAIRS` is not justified at this stage.

Next action: the owner decides whether to return M0–M5 to the package author for documentary correction. If corrected, conduct a new delta review, ideally by a reviewer other than the author. No automatic authorization is implied by closure.

## 9. Execution/provenance boundary

Claude reports direct inspection of hashes, contract, README, v0.7.1 report and CSV, with partial reading of the reference and packaged prompt. Shell utilities and short Python scripts were used only on temporary extracted copies for reading/scanning/hash computation. Product code was not executed. All 74 matrix tests are `NOT_RUN`; build/runtime `NOT_RUN`. The local checkout was not inspected.

`PRODUCT_CODE_EXECUTION = NOT_RUN` · `TESTS = NOT_RUN` · `BUILD = NOT_RUN` · `RUNTIME = NOT_RUN` · `GOVERNANCE = KEEP_BLOCKED`.
