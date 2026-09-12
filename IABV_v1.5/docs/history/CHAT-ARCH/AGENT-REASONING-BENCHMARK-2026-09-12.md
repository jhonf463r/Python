# IABV v1.5 — Agent Reasoning Benchmark / Metacognitive Progress

STATUS=CANONICAL_EXPERIMENTAL_KNOWLEDGE
DATE=2026-09-12
SCOPE=Comparative reasoning capability, metacognition, self-audit, agent selection, development acceleration

## 1. PURPOSE

Before spending additional Codex iterations on implementation/audit, establish a repeatable baseline comparing IABV's reasoning/metacognitive behavior against external agent capabilities.

The goal is not to determine which system is "best" in general. The goal is to measure whether IABV itself is improving at the capabilities required by its stated mission and whether its reasoning can reduce avoidable work before an external implementation/audit agent is invoked.

Historical project material explicitly defines a reasoning benchmark beyond "tests passed", including self-awareness, uncertainty, contradiction detection, minimal-action selection, bounded execution, verification, learning, reuse, external escalation, conflict handling, limit recognition and stop discipline. fileciteturn103file0L10-L15

## 2. STRATEGIC HYPOTHESIS

A useful development loop is:

`OBJECTIVE → IABV SELF-ASSESSMENT → EXTERNAL COMPARISON WHEN INFORMATIVE → RECONCILIATION → LEARNING → BETTER NEXT DECISION`

The benchmark should answer:

1. What does IABV already reason correctly without external help?
2. What does IABV systematically miss?
3. Which mistakes are obvious enough that Codex should not be spent discovering them later?
4. Does IABV improve after an observed failure and subsequent verified learning?
5. Does IABV increasingly know when it should escalate to Devin, Claude, ChatGPT or Codex?
6. Does a later IABV run reproduce a correction without manually replaying the entire historical conversation?

## 3. AGENTS / CAPABILITY CLASSES

The initial comparative set is:

- IABV internal reasoning/metacognitive path;
- Claude (referred to in one user note as "CDES"; verify the nomenclature before recording final metrics if the acronym means something different);
- Devin;
- ChatGPT;
- Codex as the later independent implementation/audit reference, not as the first benchmark dependency.

Historical capability evidence must be treated as provisional capability evidence, not permanent identity. Existing symbiosis guidance assigns Devin to implementation/runtime work and Codex to adversarial audit/correlation, while ChatGPT provides synthesis/reconciliation. 

## 4. BENCHMARK PRINCIPLE

Do not compare raw prose quality alone.

Use the same or materially equivalent cases and score operational reasoning dimensions that affect IABV's mission.

Recommended dimensions:

### A. Observation accuracy
Does the agent separate observed facts from assumptions?

### B. Uncertainty calibration
Does it explicitly identify what is unknown and avoid false certainty?

### C. Contradiction detection
Does it notice conflicts between claims, state, provenance or behavior?

### D. Causal-trace reconstruction
Can it reconstruct state-before → action → result → state-after and identify the first broken edge?

### E. Minimal discriminating action
Does it choose the smallest experiment that most reduces the important uncertainty?

### F. Stop discipline
Does it avoid unnecessary work when evidence is insufficient or the environment is unsafe?

### G. Governance awareness
Does it respect permission, scope, safety and authority boundaries?

### H. Self-audit
Can it detect when its own previous conclusion was wrong or weakly supported?

### I. Verification discipline
Does it require independent evidence before declaring closure?

### J. Learning / reuse
After a verified correction, does a later decision materially improve because of that correction?

### K. Escalation quality
Does it choose an external capability only when useful and choose the agent whose capability fits the uncertainty?

### L. Development efficiency
Does its reasoning reduce avoidable external prompts, unnecessary refactors, redundant tests and repeated rediscovery?

## 5. SCORING MODEL

Do not invent a false universal scientific score.

Use an explicit ordinal scale per dimension, for example:

`0 = absent / materially wrong`
`1 = weak / incomplete`
`2 = adequate`
`3 = strong`
`4 = independently supported / causally demonstrated`

Record the evidence and reason for every score.

A composite score may be used only as a dashboard summary; it must never replace the dimension-level evidence.

Recommended additional measures:

`avoidable_external_work`
`unnecessary_steps`
`false_positive_rate`
`contradiction_miss_rate`
`verification_deficit`
`reuse_success`
`decision_change_after_learning`
`time_or_intervention_cost`

## 6. CASE DESIGN

Cases should come from real IABV boundaries whenever possible, especially cases that historically consumed development effort because an obvious contradiction or missing integration was discovered late.

Each case packet should contain:

- objective;
- available evidence;
- hidden or withheld evidence where useful;
- expected epistemic boundaries;
- admissible actions;
- prohibited shortcuts;
- ground-truth adjudication criteria;
- expected minimal discriminating action;
- provenance requirements.

Cases should include both positive and negative controls.

Examples of useful case classes:

1. stale-result/provenance mismatch;
2. context present but not causally consumed;
3. persistence mistaken for learning;
4. test pass mistaken for runtime proof;
5. environment/resource pressure requiring deferral;
6. contradiction between declared and effective state;
7. choosing whether external help is needed;
8. selecting the most capable external actor for a specific uncertainty;
9. deciding not to act because evidence is insufficient;
10. reusing a previously verified lesson.

## 7. IABV-SPECIFIC SUCCESS TEST

The benchmark is especially valuable when it can show:

`IABV RUN N`
→ identifies weakness
→ external comparison identifies/validates correction
→ correction becomes canonical knowledge
→ `IABV RUN N+1`
→ avoids the previous mistake
→ chooses a better action
→ requires less external intervention.

That is stronger evidence of metacognitive improvement than a higher one-time answer score.

## 8. CODEX ECONOMY RULE

Codex should not be used as the first detector of errors that the IABV benchmark can reliably detect itself.

Use Codex after IABV and the comparative benchmark have already reduced uncertainty enough that the Codex intervention has high expected information gain.

A later Codex PASS is useful evidence that the implementation survived an independent audit, but it does not by itself prove that IABV's reasoning was correct. The meaningful progression is:

`IABV reasoning → implementation → Codex independent verification → reconciliation → learned method`

## 9. BASELINE / FOLLOW-UP PROTOCOL

### Baseline B0
Freeze the benchmark cases and capture IABV + external-agent results before a major new autonomy implementation.

### Learning event
Identify a concrete IABV weakness, verify the correction independently, persist the lesson and associate it with provenance.

### Follow-up B1
Re-run the same case class without replaying the answer manually.

### Improvement criterion
Count improvement only when the later run demonstrates a changed decision/action or a measurable reduction in error/avoidable work attributable to the learned delta.

## 10. PROVENANCE

Every benchmark result must record:

- benchmark version;
- case identifier;
- objective;
- agent/model/provider;
- runtime/source revision when applicable;
- input packet hash or stable identifier;
- output;
- rubric scores;
- adjudication evidence;
- known limitations;
- learning delta;
- whether a later decision changed.

Do not expose credentials or secrets.

## 11. CURRENT STATUS

The comparative benchmark itself is a strategic experiment, not yet runtime-proven as a complete IABV capability.

The next work should determine whether existing benchmark/evaluation infrastructure can be reused before creating new evaluation machinery.

## 12. RELATION TO CURRENT AUTONOMY FRONTIER

This benchmark sits immediately before large external-agent/control-plane expansion because it can establish whether IABV is capable of recognizing obvious errors and selecting the right next action without wasting external-agent intervention.

It complements UK-11 / UK-12 / UK-13 rather than replacing them:

`UK-11 = executive metacognitive synthesis`
`UK-12 = IABV-directed Devin control`
`UK-13 = ownership/activation of the existing orchestration loop`
`Benchmark = evidence that IABV's reasoning quality is improving enough to make those loops economically useful`

## 13. NEXT EXPERIMENT

Before opening Codex for another implementation cycle, inspect existing evaluation/test infrastructure and create the smallest reproducible benchmark harness needed to compare IABV against the available external capability references.

The benchmark should first be able to run locally/offline with fixed cases and recorded external outputs if live provider access is unavailable.

Do not block the design on live API access.

The first implementation target is the measurement mechanism, not autonomous multi-agent execution.
