# IABV v1.5 — CHAT-ARCH-2026-09-11-018-R1
# Correction / superseding addendum: provenance and objective-verifier state

This is an append-only correction to `CHAT-ARCH-2026-09-11-018-objective-verifier-continuity.md`.
It does not erase the original record. It corrects facts discovered after the first archive commit was created.

## CORRECTION SCOPE

ORIGINAL_RECORD=`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-11-018-objective-verifier-continuity.md`
CORRECTION_RECORD=`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-11-018-r1-provenance-objective-verifier-correction.md`

## NEW PROVENANCE FACT

The original archive commit was created as:
`25aeb4d794ae3244ea29d84a58253937cca923a2`

Its actual parent is:
`93a52b4f64f43d64adb62a98a6b9f48bd9efaf5c`

Therefore the repository state did NOT stop at `49c8a87dc534988b25afaeaf3c44adb4fb4af75b` when the archive was created.

The actual chain was:

`49c8a87dc534988b25afaeaf3c44adb4fb4af75b`
→ `93a52b4f64f43d64adb62a98a6b9f48bd9efaf5c`
→ `25aeb4d794ae3244ea29d84a58253937cca923a2`

The intermediate commit `93a52b4...` is a real published remediation and must be included in the final historical interpretation.

## WHAT 93A52B4 ACTUALLY FIXED

Verified from GitHub source:

1. `file_content_changed` is no longer computed as `bool(changed_files)`.
2. `capture()` passes `base_commit` into `_evaluate()`.
3. `_evaluate()` uses `target_file` for `file_content_changed`.
4. `_git_show_file()` reads file content at explicit Git commits.
5. `_verify_file_content_changed()` compares base and result content.
6. `changed_files_nonempty` remains a separate execution observation.
7. The producer records an explicit `target_file` for the objective criterion.
8. A comment-only unit negative control and wrong-target unit negative control were added.

These are source-level verified facts.

## WHAT 93A52B4 DOES NOT YET PROVE

### 1. Objective effect vs declared goal

The producer automatically adds an objective criterion when `file_scope` is non-empty and chooses:
`target_file = file_scope[0]`.

The criterion verifies:
`file_content_changed(target_file) == True`.

That is sufficient to verify the narrow proposition:
`the normalized non-comment content of target_file changed between BASE and RESULT`.

It is NOT automatically sufficient to verify an arbitrary natural-language `CodexTaskSpec.goal`.

Example implication:

`GOAL = "fix retry logic so configured backoff is used"`

and

`TARGET FILE = retry_handler.py`

can still receive an objective PASS when unrelated non-comment content in `retry_handler.py` changes.

Therefore:

`OBJECTIVE CRITERION EXISTS`
≠
`OBJECTIVE GOAL IS PROVEN`

unless the declared goal is explicitly equivalent to the verifier proposition.

### 2. Comment-only and wrong-target controls are not full production-path controls

The added `test_comment_only_change_negative_control` and `test_wrong_target_file_negative_control` directly call `_verify_file_content_changed()`.

They are useful unit-level discriminating tests, but they do not independently demonstrate the entire production chain:

`real production caller → commit → capture → verifier → DAR → TaskOutcome`.

The positive control does exercise the production path, but the negative controls described above do not fully reproduce the production path.

Therefore:
`ADVERSARIAL_PRODUCTION_NEGATIVE_CONTROL = NOT_PROVEN`

### 3. The content verifier uses heuristic comment stripping

The verifier removes inline text matching `#.*$` before comparing normalized content.

This can misinterpret literals containing `#`, such as Python string values with hash characters.

Therefore the verifier is deterministic but not a general Python semantic parser.

Its valid scope should be treated as the narrower property it actually computes, unless a future test suite establishes stronger guarantees.

## UPDATED OBJECTIVE-EVIDENCE STATUS

The correct status is now:

`49c8a87 = REJECTED residual verifier proxy`

`93a52b4 = SIGNIFICANT REMEDIATION / PARTIAL`

`Objective Evidence = NOT YET CLOSED for arbitrary development goals`

The specific diff-presence false positive is addressed at source level.
The broader goal-to-verifier causal binding remains open.

## UPDATED FALSE-POSITIVE REGISTER

### FP-003 — Verifier validates a narrower proposition than the goal

INITIAL_BELIEF=`A target-file content verifier proves the declared development goal.`

WHY_IT_LOOKED_TRUE=`The verifier compares BASE vs RESULT, strips comments, is labeled objective, and the producer supplies target_file.`

WHAT_WAS_ACTUALLY_TRUE=`The verifier establishes only a normalized non-comment content difference in the selected target file.`

HOW_DISCOVERED=`Inspection of `_build_codex_task_spec()` together with `_verify_file_content_changed()` after resolving the intermediate commit.`

DISCOVERED_BY=`ChatGPT / GitHub source inspection`

EVIDENCE=`93a52b4 source`

CORRECTIVE_ACTION=`Require explicit alignment between declared objective and verifier proposition; do not equate arbitrary goal satisfaction with generic file-content change.`

GENERALIZED_LESSON=`A stronger measurement can still measure the wrong property.`

## UPDATED MODEL EVOLUTION

`DIFF PRESENCE`
→ `BASE-vs-RESULT CONTENT DIFFERENCE`
→ `GOAL-SPECIFIC EFFECT`

93a52b4 advances the system from the first stage to the second.
It does not yet establish the third for arbitrary goals.

## UPDATED NEXT LOGICAL STEP

The next implementation/audit sequence should be:

1. Keep `changed_files_nonempty` as execution evidence only.
2. Keep the BASE-vs-RESULT verifier as a narrow capability.
3. Explicitly bind a verifier proposition to the declared objective before allowing objective PASS.
4. Add a production-path comment-only negative control.
5. Add a production-path wrong-target negative control.
6. Add at least one goal-mismatch control where the target file changes meaningfully but the declared objective is not achieved.
7. Run independent Claude adversarial audit only after these controls exist.

No Experience promotion occurs before this gate.

## UPDATED CROSS-IA LEARNING

`Claude` identified the original semantic verifier weakness.
`ChatGPT` independently inspected the published implementation and rejected premature closure.
`Devin` then produced `93a52b4`, which materially improved the verifier implementation.
`GitHub` verification exposed that this remediation is stronger but narrower than the general claim of objective-goal proof.

This is observable cross-IA knowledge transfer, but broad AI capability rules remain `OBSERVED/HYPOTHESIS`, not canonical.

## PROVENANCE STATE

ORIGINAL_ARCHIVE_COMMIT=`25aeb4d794ae3244ea29d84a58253937cca923a2`
ORIGINAL_ARCHIVE_PARENT=`93a52b4f64f43d64adb62a98a6b9f48bd9efaf5c`
ACTUAL_REMEDIATION_COMMIT=`93a52b4f64f43d64adb62a98a6b9f48bd9efaf5c`
PREVIOUS_REMEDIATION=`49c8a87dc534988b25afaeaf3c44adb4fb4af75b`
CORRECTION_STATUS=`APPENDED`

## DELETION GATE UPDATE

DELETE_SAFE=`CONDITIONAL`

Condition:
The correction record and original record must both be retained, and the entire archive history should be reconciled into the canonical long-lived branch before chat deletion. The objective-verifier remediation and independent audit remain open work.

## FINAL CORRECTED STATE

`CURRENT_BRANCH=`foundation/reconstruction`
`CURRENT_ARCHIVE_CHAIN=`49c8a87 -> 93a52b4 -> 25aeb4 -> CORRECTION_COMMIT_PENDING`
`OBJECTIVE_EVIDENCE=`PARTIAL / NOT CLOSED`
`EXPERIENCE=`BLOCKED`
`CLAUDE_AUDIT=`PENDING FOR FINAL OBJECTIVE-GOAL BINDING`
`CHAT_DELETE_SAFE=`CONDITIONAL`
