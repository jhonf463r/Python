# CHAT-ARCH-2026-09-17-010 — L5 Opus 5 Causal Closure Gate

## Purpose

Preserve the independent Opus 5 adjudication that follows the isolated competitive-selection experiment and defines the final L5 experimental gate. This record supersedes any weaker assumption that a real G3 verified transition automatically proves that verification itself influenced the selector.

## Provenance

- Branch: `experiment/l5-competitive-selection-2026-09-17`
- Actual remote HEAD: `5ef1009c1e97165a62ba04a8dbfaf7f62deb8edb`
- Parent: `d77cbc6015a8358c9005d475c9799efc9791f8f6`
- Previously reported `5ef1009c1a6728332b3c4a0869b6291e7b3b6586` does not exist.
- Diff against parent: only `IABV_v1.5/tests/test_l5_candidate_isolation.py`; no production-code changes in that experiment.
- `allowed_tool_ids` is a pre-existing production selector parameter, not a test hook.

## Evidence already established

The candidate-isolation experiment uses public `InteractionModeSelector.select()` with `allowed_tool_ids={candidate_a,candidate_b}`. The actual candidate universe is asserted and isolated in both arms.

Control:
- candidate_a = 9.620
- candidate_b = 8.345
- winner = candidate_a

Treatment:
- candidate_a = 9.620
- candidate_b = 10.895
- winner = candidate_b

Winner change A -> B is executed evidence, not inference.

Fresh object reconstruction occurs after persistence. No stale Python object was found to explain the effect.

The +2.55 treatment delta is exactly decomposed by production weights:
- learned_pattern: 0 -> 1, contribution +1.800
- stability: 0.55 -> 1.00, contribution +0.675
- frequency: 0 -> 0.125, contribution +0.075
- total +2.550

All three terms derive from the same persisted `InteractionPattern.verified_transition_success_count` change.

## Opus 5 decisive finding

`InteractionModeSelector` does not distinguish ordinary execution success from verified-transition success when calculating selection evidence. It repeatedly reads:

`pattern.success_count + pattern.verified_transition_success_count`

for success/ranking calculations.

Therefore a single ordinary, auto-reported success recorded by `learn_from_execution()` can create the same effective selector state as a single verified-transition success and can produce the same +2.55 and the same winner change.

This is a causal-attribution limitation in the selector, not evidence that G3 verification is false. Persistence preserves the counters separately; the selector merges them at read time.

## Exact current epistemic boundary

The isolated synthetic experiment proves:

`well-formed verified-transition input -> persisted learning state -> cold reload -> normal production select() -> isolated A/B competition -> winner change`

It does NOT prove that independent verification itself is the cause of the decision change.

The strongest honest claim available after the next single-chain experiment is expected to be of the form:

> A persisted learning state produced by a genuinely independently observed/verified real-world transition, reloaded from cold storage, changed the winner of an isolated two-candidate production selector.

Do not claim:

> Independent verification itself caused the selector change.

unless production selector semantics are changed to distinguish verified and ordinary evidence. Such a change would be an architecture-level intervention and is outside the present L5 closure experiment.

## Candidate identity / namespace boundary

`tool_id` alone is not sufficient as a complete causal identity proof.

The selector's `_best_pattern` joins by `tool_id` (and optional `site_id`) and then uses fuzzy token overlap between the pattern objective text and the request goal. `action_signature` is used for persistence/upsert but is not read by the selector.

Minimum observed continuity invariants:

1. `transition.tool_id == card.tool_id == assigned_tool` for the candidate that actually acts and later competes.
2. The request goal is held byte-for-byte/literally identical across control/treatment and overlaps the persisted objective sufficiently for the selector's existing join.
3. `site_id` remains empty/None in both arms because the current `VerifiedTransition` has no `site_id` and G3 persists the created pattern with NULL site identity.
4. The candidate `adapter_key` is available through the same registry conditions in both arms.

Important architectural seam: G3 currently writes patterns using the MCP/action-tool namespace (`tool_id=assigned_tool`, e.g. `write_repo_file`), while the selector ranks `ToolCard.tool_id` identities. The only honest experimental binding is to have the later competing `ToolCard` carry the exact same real `tool_id` as the tool that acted. Declaring a synthetic candidate identity after the fact would reintroduce the very identity discontinuity the experiment is intended to close.

Do not redesign the architecture merely to make this experiment easier. If the existing system cannot produce this identity continuity without synthesis, STOP and report the seam rather than fabricating continuity.

## G3 verification authority boundary

The G3 bridge in `server.py` independently reopens the target path and hashes observed file bytes, rather than trusting the actor's returned handle. This is genuine independent observation by mode of failure.

The experiment must nevertheless expose the origin of the verification verdict, because deterministic verification derived from `plan_parameters` and semantic verification answer different epistemic questions.

The test must prove that the `VerifiedTransition` was produced by the real G3 bridge and not hand-constructed by the test. Capture a cross-reference such as `transition_id` plus `execution_id`/`lease_id`/run identity traceable to the Authority/Runtime audit record.

`learn_from_verified_transition()` trusts the verification fields it receives; that trust is justified only when provenance proves G3 produced them.

## Persistence / reload determination

Opus found no relevant cache/singleton mechanism in selector/repository/persistence paths. Storage is backed by JSON plus SQLite; lookup is mediated through persisted state rather than stale Python objects.

Destroying the treatment repository/registry/learning objects and reconstructing fresh objects against the same storage/DB is sufficient to eliminate ordinary in-memory staleness for this experiment.

The experiment must still print/register the identical storage route and count `interaction_patterns` for the relevant `tool_id` before and after persistence.

## Final L5 gate — minimum single-chain runtime experiment

Next actor: DEVIN.

One Windows-executable experiment should exercise existing production mechanisms only:

`real G3 action -> independent observation -> G3-produced VerifiedTransition -> persistence -> destroy objects -> fresh reload -> normal InteractionModeSelector.select() -> isolated A/B competition -> winner change`

Acceptance evidence must include:

1. Candidate identity: `card.tool_id == transition.tool_id == assigned_tool`, all three explicitly recorded.
2. Real action evidence: `execution_id`, `run_id`, `lease_id` or equivalent Authority-crossable identifiers, plus relevant before/after state.
3. Independent observation: `observed_result_source='independent_filesystem_observation'` and observed SHA-256.
4. Verification origin: explicitly identify which G3 verification branch produced the verdict.
5. Learning bridge provenance: `transition_id`, `pattern_id`, and persisted `verified_transition_success_count`.
6. Cold reload: pattern count for the relevant `tool_id` is 0 before and 1 after; same DB/storage path; objects destroyed/reconstructed.
7. Selector entrypoint: public `InteractionModeSelector.select()`, explicit `allowed_tool_ids`, `suggested_tool_id=None`.
8. Invariants: literal-identical `user_goal`; `site_hint/site_id` empty; same adapter availability; unchanged ordinary `success_count`/`failure_count`; same request/desired modes/worker conditions as applicable.
9. Full ranking and component scores for control and treatment, with winner A -> B.
10. Negative verification arm: `verification_failed` must not produce a positive verified success or winner change.
11. Third discriminant arm: same candidate/signature with one ordinary non-verified success recorded through `learn_from_execution()`, then cold reload and normal selection. Record whether its effect is identical to the verified arm.

The third arm is mandatory as a discriminant, not as permission to alter selector semantics. It documents the selector's inability (or, unexpectedly, ability) to distinguish provenance.

## False-positive status after the gate design

Likely eliminated by the experiment:
- stale in-memory objects
- hidden candidate universe
- suggested-tool shortcut
- forced winner/manual score
- ordinary request difference
- registry cache contamination
- unverified/verified bridge confusion, if G3 provenance is explicitly cross-linked

Must remain explicitly challenged:
- verified vs ordinary success merge in selector
- fuzzy objective-token join
- namespace continuity between executed action tool and future ToolCard candidate
- `site_id` asymmetry
- persistence aliasing within the selector's limited pattern lookup

## L5 status

`PARTIALLY PROVEN` pending the single-chain runtime experiment and its independent audit.

The remaining causal edge is no longer merely “can real verification reach persistence?” G3 already provides evidence for that path. The edge is:

`real verified action identity -> same candidate identity at future selector -> persisted state -> cold reload -> decision`

with explicit documentation that the selector attributes the decision effect to merged success evidence, not specifically to the verification provenance.

## Actor routing / Codex economy

Next actor is DEVIN because the uncertainty is now Windows/runtime execution of an already existing bounded composition. No Codex capability gap was identified. Codex should not be spent on this task.

Do not spend another Opus message unless a genuine architecture-level contradiction emerges, especially if a proposal is made to alter selector weighting of verified vs ordinary success.

After Devin produces the runtime artifact, route to SONNET for independent forensic adjudication.

Do not advance L6 or L7 before this L5 gate is closed.

## Stop condition

Stop spending L5 messages once a single independently auditable runtime artifact contains the real execution/Authority identity, independent observation, verification-origin provenance, learning bridge IDs, cold persistence/reload, exact candidate identity continuity, isolated A/B ranking/winner change, negative verification behavior, and the verified-vs-ordinary discriminant result.

At that point write the strongest claim supported by the discriminant result and move to the next causal frontier. Never upgrade “verified evidence changed the decision” into “verification caused the decision” unless the selector itself can causally distinguish verified provenance.
