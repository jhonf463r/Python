# IABV v1.5 — METACOGNITIVE SELF-USE + PROVENANCE GATE
## Canonical source record — 2026-09-21

## 1. SOURCE / PURPOSE

Source: user-provided continuation transcript dated 2026-09-20/21, including the reconciliation of the IABV self-use strategy and the I0 credential-seam handoff.

Purpose: preserve the material methodological knowledge from this cycle so future chats do not repeat the same provenance archaeology, confuse I0 operational status with the metacognitive track, or treat external-agent reports as evidence before artifact verification.

This record is a synthesis/absorption of the chat, not a claim that every historical report in the chat was correct.

## 2. STRATEGIC INFLECTION

The central development shift is:

Previous:
`human → external AI analysis → implementation → external audit → human transport of context`

Target:
`objective → IABV retrieves relevant memory → IABV observes itself → IABV maps uncertainty → IABV introspects → IABV selects capability-fit → governed action → independent verification → Knowledge Delta → later decision`

The target is not unrestricted self-modification. It is observable, governed and evidence-bearing self-assessment that can choose the smallest next action.

## 3. INTERNAL SYMBIOSIS STATUS

IABV already contains substantial relevant organs:
- WorldModel / EnvironmentSelfModel;
- self-awareness and SelfAudit;
- OSES / OperationalSelfExamination;
- self-code analysis / holistic metacognition;
- CodeAuditTrail;
- ExperimentLab;
- StrategySelector / AdaptiveWeightLayer;
- validation;
- PortableContext.

Current knowledge:
`org exists != organ integrated != causal cognitive circuit`.

Not proven:
`IABV observes → identifies uncertainty → introspects → finds first broken edge → designs discriminating experiment → verifies → writes Knowledge Delta → changes future decision`.

Preferred first experiment:
IABV-native deep self-assessment preflight, read-only with respect to repository/runtime state, followed by independent external verification for critical claims.

## 4. SELF-AWARENESS VS METACOGNITION

Preserve:
- `system.self_awareness` = current condition/state/availability description.
- `system.metacognition` = why, uncertainty, changed surface, likely downstream effects, evidence gaps, hypotheses and discriminating experiment.

A deep request to "analyze current IABV state" must not be reduced to health telemetry.

## 5. CHANGE-SURFACE INTROSPECTION

For a changed symbol, predicate or contract, inspect:
`symbol → callers → producers → consumers → contracts → fallbacks → alternate routes → tests → negative cases → downstream effects`.

Use adversarial neighboring cases:
- expected positive;
- nearby negative;
- same token/different domain;
- alternative route/producer;
- fallback path.

P041-R7/R8 is retained as the concrete lesson that a locally correct predicate can still create semantic or temporal false positives elsewhere.

## 6. OBSERVE / MUTATE SEPARATION

Canonical phase separation:
`OBSERVE → REASON → HYPOTHESIZE → EXPERIMENT → VERIFY → AUTHORIZE → CHANGE → REVERIFY → LEARN`.

Any auto-analysis that switches branches, resets/cleans worktrees or applies corrections must not be represented as a pure observation.

## 7. REMOTE PROVENANCE GATE — NEW OPERATIONAL RULE

A material modification claim may only advance to an independent auditor after:

`REPORT → ARTIFACT → exact branch/ref → exact SHA → relevant working-tree provenance (when applicable) → remote read-back → claimed file/content present → runtime provenance (when applicable) → independent verification`.

Operational distinctions:
- reported SHA != committed object;
- local commit != remote-verifiable commit;
- branch label != branch tip evidence;
- remote SHA existence != proof that claimed content is present;
- remote content verification != runtime proof;
- runtime proof != external effect proof.

This rule was reinforced by two earlier reported-but-unreadable test SHAs in the I0 cycle and then a successful remote artifact publication at `7753ce5632370b2a03726aeff63dbcd1ac7afc42`.

Do not infer why an earlier artifact was absent. The durable fact is only that the cited objects were not remotely resolvable at audit time.

## 8. I0 CREDENTIAL-SEAM STATE FROM THIS CYCLE

Remote experimental branch:
`devin/i0-credential-get-coverage-2026-09-21`

Remote commit:
`7753ce5632370b2a03726aeff63dbcd1ac7afc42`

Verified by direct GitHub commit read-back:
- only `IABV_v1.5/tests/test_i0_credential_seam.py` changed;
- POST mock now returns `running` and therefore reaches polling;
- GET mock returns `finished`;
- POST asserts `Bearer invocation-key`;
- GET asserts `Bearer invocation-key` from `mock_get.call_args`;
- the commit is real and remotely resolvable.

Reported M3 mutation result:
production GET binding changed from `_headers(effective_key)` to `_headers()`; the test failed with constructor-key instead of invocation-key.

Epistemic boundary:
- remote artifact/provenance = VERIFIED;
- test content = REMOTELY VERIFIED;
- mutation result = REPORTED BY IMPLEMENTER, pending independent reproduction/audit;
- Windows runtime = NOT PROVEN;
- external effect = NOT PROVEN;
- I0 full closure = NOT PROVEN.

Thus the next actor for this exact artifact is Sonnet for independent forensic audit. Only after independent validation should the runtime experiment resume.

## 9. I0 TRACK MUST NOT OVERRIDE THE METACOGNITIVE TRACK

The current mainline I0 state includes a separate Windows credential/runtime blocker and other production-route work. The experimental M3 test branch does not close I0.

Do not merge:
- unit/mutation coverage;
- Windows runtime;
- authentication/authorization;
- external effect;
- learning/metacognitive closure.

They remain distinct causal tracks.

## 10. DYNAMIC CAPABILITY ROUTING

Actor selection remains:
`objective → uncertainty → required capability → actor/resource → action → verification`.

Current capability hypotheses:
- ChatGPT: synthesis, adjudication, evidence boundaries, reconciliation/writeback.
- Sonnet: independent forensic challenge.
- Devin: bounded implementation + Windows/runtime execution.
- Codex: difficult technical seam/ambiguity and repository archaeology where specifically required.
- Opus 5: genuine architectural ownership/policy/higher-order causal contradiction.

These are mutable hypotheses, not fixed roles or rankings.

For the current I0 M3 artifact: Sonnet first; then Devin for runtime if M3 independently survives.

## 11. DEVELOPMENT-INFLECTION CRITERION

The desired inflection remains:

`verified experience → reusable knowledge → future decision change → reduced routine coordination → more efficient experiment`.

No single green test, memory write, or multi-AI agreement proves the inflection.

## 12. KNOWLEDGE DELTA

`ΔK`: stronger evidence that IABV can formalize a self-assessment method and a remote-provenance gate.

`Δπ`: any material actor-reported modification must cross the remote-provenance gate before the next auditor consumes its claim.

`ΔB`: future orchestration should block handoff of unanchored implementation claims and should route deep IABV-state questions to native self-assessment first.

`ΔY`: not yet demonstrated as a causal future-decision change inside IABV itself.

## 13. NON-CLAIMS

This record does not establish consciousness, sentience, self-directed autonomy, generalized metacognition, I0/I1/I2 closure, or autonomous self-modification.

It establishes a stronger experimental method and a narrower evidence boundary.

## 14. NEXT DISCRIMINATING ACTION

1. Sonnet independently audits remote commit `7753ce...` and its M3 causal sensitivity.
2. If valid, Devin performs real Windows runtime execution from the exact appropriate implementation revision with controlled credential provisioning.
3. Sonnet independently audits runtime evidence.
4. ChatGPT reconciles evidence and writes the resulting Knowledge Delta.

Do not rerun closed provenance archaeology unless contradictory evidence appears.
