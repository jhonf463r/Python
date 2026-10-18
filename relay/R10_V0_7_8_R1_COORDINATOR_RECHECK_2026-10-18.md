# R10 v0.7.8 R1 — coordinator recheck findings (2026-10-18)

## Status

`COORDINATOR_RECHECK_HOLD` — matrix/contract content is substantially consistent, but do not route R1 to Claude/Sonnet yet. Three bounded documentary traceability/package issues must be closed in a new immutable revision.

`GOVERNANCE = KEEP_BLOCKED`; `BRIDGE_NOT_READY`. This review did not execute product code, tests, builds, runtime, migrations, integrations, dispatcher, M0A or the bridge. All T123–T246 remain `NOT_RUN`.

## Exact candidate and readback evidence

- R1 artifact commit: `541e150b478bcbf24c739860f799f8e5ef227af7`.
- R1 report/index commit: `a081b152407a22b61b6fb11d1947d34e9d0d2795`.
- Branch: `handoff/r10-v078-t137-repair-20261018`.
- The GitHub tree reports the ZIP blob `5f316d94b974e215987b13909587a4297f9e2162`, size 5,248,720 bytes.
- Author-side report declares ZIP SHA-256 `1b18f128ceaadce4a32abe4ec3deb7c08f330aa051c6239e4146f91af575ef1f` and reports successful binary remote readback. Limitation: this coordinator session's GitHub text connector does not return binary ZIP bytes (base64 fetch returned no content; GitHub raw download is not available through the current runtime), so I could not independently recalculate the ZIP's SHA-256. The GitHub commit pins the exact ZIP blob and its byte size, but this is not an independent SHA-256 calculation by ChatGPT.
- R1 matrix, contract, manifest, cell diff and independent-review prompt were fetched from the immutable artifact commit. Their UTF-8 byte lengths and SHA-256 values were independently recomputed from retrieved text and matched the R1 report:
  - Matrix: 76,972 bytes; SHA-256 `f1d5c3e99a34f24f2e19d7426872c5512c610c2713a063de47c3139b961d56cb`.
  - Contract: 60,222 bytes; SHA-256 `f251ad59dfee6a524538b08b034ca895388c03d0427b16a5178eb441a7261419`.
  - Manifest: 32,505 bytes; SHA-256 `cc5288f22724ee02ecddf0ec869448c333779e6c43f86ee5258c364fbff910c5`.
  - Parsed cell diff: 2,196 bytes; SHA-256 `c13b18f8c7fa0d960c3bdd17aaf5927047289c33aead03666355f7dd170342ea`.
  - R1 review prompt: 1,167 bytes; SHA-256 `559baa9adc7b37ea9f23933492fda392c15e6208b592019d2fe787fc3126e84d`.
- The contract's remote blob ID is identical to the original v0.7.8 contract blob, and its downloaded text/hash matches the reported original bytes. Contract remains unchanged.
- Strictly parsed R1 CSV: 124 data rows; 12 columns in header and every data row; unique contiguous T123–T246 IDs; every status `NOT_RUN`.
- Parsed comparison against the original v0.7.8 matrix yields exactly the three reported cell changes: T137 `initial_state_and_preconditions`, T137 `ordered_events_and_oracle`, and T141 `ordered_events_and_oracle`.
- The current matrix has no `EXECUTION.COMPLETED`, no `correlation_status=CORRELATED`, and no visible assignment of `UNCORRELATED` or `LATE_STALE` to `ResultState`. T137's two-stage authenticated-receipt / separate truncated-capture distinction is present; T141 uses `MATCHED`.

## Findings requiring bounded fixup

### COORD-02 — T137 normative basis omits direct pre-allocation rejection clauses

In the R1 matrix T137 has `normative_basis = §4.2; §7`, unchanged from the original row. Its revised oracle now asserts the normative details of durable pre-allocation `CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE`, and absence of `result_id`, `ResultState`, slot, evaluation, adoption, contribution and effect. Those rules are explicitly specified in §§4.1, 12, 17.1 and 17.2; §§4.2 and 7 also support completeness/eligibility. The current basis is therefore under-traced relative to the changed oracle and the R1 change report.

Proposed narrow fix: update T137's `normative_basis` to `§4.1; §4.2; §7; §12; §17.1; §17.2` (or another order that cites these same directly governing clauses). Do not change the contract or intended oracle.

### COORD-03 — T141 normative basis omits the enum clause just used for its correction

T141's changed oracle now sets `correlation_status=MATCHED`, and R1 changelog/report correctly attribute this to §17.2. But T141's `normative_basis` remains `§4.1; §4.2; §2.2`, without §17.2, which defines the allowed correlation dispositions.

Proposed narrow fix: append §17.2 (e.g. `§2.2; §4.1; §4.2; §17.2`). No normative contract change.

### COORD-04 — embedded pre-R1 preflight snapshot is not labelled as historical

The file `candidate-r1/R10_V0_7_8_PREFLIGHT_REPORT.md` has the same Git blob identity as the pre-R1 base preflight at the original candidate commit. It does not describe the R1-specific T137/T141 changes or the R1 package inventory. The R1-specific report exists outside the ZIP at `relay/R10_V0_7_8_R1_PREFLIGHT_REPORT_2026-10-18.md`, but the unchanged generic embedded filename/title `R10_V0_7_8_PREFLIGHT_REPORT.md` makes the older snapshot ambiguous when opening the R1 package.

Required resolution: either (a) convert the embedded file into a current R1.1 internal preflight that accurately describes that package, with no recursive claim about the outer ZIP hash; or (b) clearly relabel/preserve it as a pre-R1 base snapshot and update README, changelog, change map, consistency report, manifest and internal references so only the external commit-pinned R1/R1.1 report is presented as current verification. Do not delete or rewrite the immutable original v0.7.8 package. Ensure the next package has one unambiguous current preflight and no stale report appearing authoritative.

## Exact next action

Do not send R1 to Claude/Sonnet yet. Use the bounded fixup handoff in `relay/CODEX_V078_R1_TRACEABILITY_FIXUP_HANDOFF.md` on this same repair branch. It asks Codex to make the two normative-basis repairs, reconcile the stale embedded preflight, repackage to a new immutable revision, refresh all dependent metadata/manifest, verify exact parsed delta and remote text readback, and provide the ZIP as an attachment to the coordinator if its interface supports it.

The current R1 candidate and both historical source candidates remain immutable. The next revision must state whether the coordinator can independently hash the ZIP bytes; do not present author-reported ZIP hash as a calculation independently performed by ChatGPT.

## Evidence classification and limits

- `GITHUB_API_VERIFIED`: commit, branch, paths, text blobs and GitHub ZIP blob identity/size.
- `BYTE_HASH_VERIFIED`: SHA-256 of fetched UTF-8 text artifacts listed above and exact parsed CSV comparison.
- `OWNER_REPORTED / AUTHOR_REPORTED_WITH_READBACK_REPORT`: ZIP byte-level download/hash and ZIP/member/historical byte comparisons, which the coordinator could not independently recalculate from binary bytes in this session.
- `NOT_RUN`: all 124 test cases and every product execution/build/runtime validation.

`NEXT_ACTOR = CODEX_LOCAL_R1_TRACEABILITY_FIXUP`; after the new immutable revision, ChatGPT performs another exact-artifact check. Claude/Sonnet remains pending until coordinator clearance. `GOVERNANCE = KEEP_BLOCKED`; `BRIDGE_NOT_READY`.
