# Codex local — R10 v0.7.8 T137 documentary repair

Destination IA: Codex local. Role: documentary author and static verifier only. Next actor: ChatGPT coordinator. Claude/Sonnet reviews only after coordinator clearance. GOVERNANCE = KEEP_BLOCKED.

Read the coordinator finding: https://github.com/jhonf463r/Python/blob/handoff/r10-v078-review-20261018/relay/R10_V0_7_8_COORDINATOR_RECHECK_2026-10-18.md
Read the relay index: https://github.com/jhonf463r/Python/blob/handoff/r10-v078-review-20261018/relay/RELAY_INDEX.md

Source candidate commit: aa8ea71578b024c69dba446d010f0ea7b068bee3
Source ZIP URL: https://raw.githubusercontent.com/jhonf463r/Python/aa8ea71578b024c69dba446d010f0ea7b068bee3/R10_V0_7_8_DOCUMENTARY_CANDIDATE.zip
Expected bytes: 5236484
Expected SHA-256: 82d0c634e6624ba07594e6f8debc21551de4ad9c1366cca4e76c6a91263f6f37

Correct only the documented T137 defect plus any additional definite matrix-only state-vocabulary mismatch found by the bounded sweep below. Never overwrite commit aa8ea71578b024c69dba446d010f0ea7b068bee3. Work in a new isolated workspace outside the IABV checkout. The required branch is handoff/r10-v078-t137-repair-20261018.

T137 currently says EXECUTION.COMPLETED in initial_state_and_preconditions and ordered_events_and_oracle. Contract §§3.3, 12 and 17.1 define SUCCEEDED as the canonical normal-attributed-completion state; EXECUTION.COMPLETED is undefined. Use ExecutionState=SUCCEEDED only if the fixture explicitly distinguishes an already accepted authenticated execution receipt binding complete output from a later distinct capture payload that is truncated. Preserve the oracle: durable pre-allocation CAPTURE_REJECTED / VALIDATION_EVIDENCE_INCOMPLETE, without result_id, ResultState, terminal slot, evaluation, adoption, contribution or effect. T137 stays NOT_RUN. If the required semantic distinction is not supported by the source, stop with BLOCKED_COORDINATOR_DECISION_REQUIRED.

Bounded vocabulary sweep: inspect the matrix's 124 rows T123–T246, especially fields naming or implying ExecutionState, ResultState, terminality, result allocation, correlation/rejection and preconditions/oracles. Compare with contract §§3.3, 4.1, 12, 17.1 and 17.2. Confirm RESULT_ACCEPTED does not terminalize execution; UNCORRELATED and pre-allocation LATE_STALE are not ResultState values; pre-allocation rejection yields no result_id/state/slot/effect; allocated invalid results remain distinguishable from rejected ingress captures. No global search/replace. Fix only definite matrix-only vocabulary mismatches unambiguously governed by the contract; report anything requiring a normative choice instead of guessing.

Keep logical contract version/Artifact ID R10_V0_7_8_CONTRACT. Preserve T123–T246 exactly, with every status NOT_RUN. Contract bytes must stay identical. Preserve v0.7.5/v0.7.6/v0.7.7 and all historical source ZIPs/trees byte-for-byte. Changes outside necessary matrix cells and directly dependent hashes/reports require itemized justification.

Rebuild matrix copies, manifest, ZIP and only dependent metadata. Strictly verify 12 columns, 124 contiguous unique IDs, all NOT_RUN; list every parsed cell changed against the original. Verify contract unchanged, manifest hashes from real bytes, ZIP CRC/safe unique paths/tree equality, history preservation. Publish R10 v0.7.8 documentary revision R1 — T137 consistency repair as new immutable bytes/commit; original commit remains pinned. Re-download new ZIP and text artifacts from commit-pinned URLs, calculate byte size/SHA-256, and strict-parse remote matrix. Do not assert readback without actually doing it.

Publish updated relay index and relay/R10_V0_7_8_R1_PREFLIGHT_REPORT_2026-10-18.md on the repair branch. Include source identity, old/new T137 cells, sweep scope/limits, full changed-cell list, CSV structural results, unchanged-contract check, archive/history evidence, readback hashes, uncertainties and next actor. Re-fetch the published index/report afterward. Do not send the package to Claude automatically.

Required response sections: SOURCE_IDENTITY; T137_REPAIR; BOUNDED_STATE_VOCABULARY_SWEEP; CSV_FULL_ROW_WIDTH_AUDIT; PARSED_DIFF_AND_CONTRACT_GUARD; MANIFEST_ZIP_AND_HISTORY; GITHUB_PUBLICATION_AND_REMOTE_READBACK; UNRESOLVED_FRONTIER; NEXT_ACTOR; GOVERNANCE.

Outcomes: BLOCKED_SOURCE_IDENTITY_MISMATCH; BLOCKED_COORDINATOR_DECISION_REQUIRED; or DOCUMENTARY_PATCH_CREATED_PREFLIGHT_COMPLETE_PENDING_COORDINATOR_RECHECK. No product code/tests/build/runtime, M0A, dispatcher or bridge actions. Tests remain NOT_RUN. GOVERNANCE = KEEP_BLOCKED; BRIDGE_NOT_READY. After publishing, ChatGPT rechecks exact bytes; Claude/Sonnet only after coordinator clearance.