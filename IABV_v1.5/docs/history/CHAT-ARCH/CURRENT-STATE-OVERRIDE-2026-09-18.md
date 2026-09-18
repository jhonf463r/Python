# IABV v1.5 — CURRENT STATE OVERRIDE — 2026-09-18

## PURPOSE

This document supersedes stale L5 status statements when a future chat begins from the canonical GitHub memory layer.

A future chat must read this file after `CURRENT-STATE.md` when the objective touches L5+, causal learning, cross-IA routing, external-agent orchestration, evidence provenance, or reduction of manual prompt copying.

## CURRENT CANONICAL EPISTEMIC STATE

### L5

L5 is **not yet frozen as a final canonical closure**.

The experimental chain has strong runtime evidence and a hardened test with causal assertions, but the current remaining publication issue is artifact reachability/identity on the remote branch.

Known verified remote state:

- `3241b3ef65630f2f863d532d75ae816349e18584` exists on GitHub.
- `70553010bafca96e98b7dc5b113eed4f3ad84e8b` exists on GitHub.
- `35e4ba0c6c44a833dbafdb7685ee1b959ba47114` exists on GitHub.
- remote branch `l5-evidence-capture-3241b3ef6` currently resolves to `b76112f633f082bcc4597ced57f5b3cba27ab36c`.
- the runtime log was reported as recovered locally with SHA256 `61c56fd0404469dec60cb29827546b23011d93d4942ce5470c83a705d1628ef2`, but its final publication must be directly verified remotely.
- previous local commits `5a0eb89e0` and `1982befcf` were not remotely resolved during the latest reconciliation; do not rely on them as canonical refs.

The L5 experiment itself reports:

```
G3 = verified
verified_transition_success_count = 1
reload counter = 1

CONTROL
mcp_client = 4.845
aider_coder = 5.225
winner = aider_coder

TREATMENT
mcp_client = 7.395
aider_coder = 5.225
winner = mcp_client

delta_mcp_client = +2.55
winner_changed = YES
causal assertions = passed
```

These numbers are experiment evidence, but they must not be promoted beyond their actual artifact/provenance boundary until the remote artifact is directly readable and independently audited.

### L5 experimental mechanism already established

The causal mechanism being tested is:

`real verified experience -> persisted learning -> reload -> normal competitive selector -> changed future decision`

The selector experiment deliberately controls ordinary `success_count=0` and uses `verified_transition_success_count` as the intended treatment difference.

### Provenance lessons

Treat these as active constraints:

- report != evidence;
- local commit != remote verification != independent audit;
- commit SHA != clean working tree unless cleanliness is verified;
- `TESTED_HEAD` must be captured from Git, not typed manually;
- artifact SHA must be computed over the final artifact bytes by an external capture process;
- manifest path must exactly equal the remotely stored artifact path;
- runtime evidence must identify the exact tested code/tree and clean-state condition;
- do not repair provenance retrospectively by rewriting the original runtime artifact.

## IMPORTANT ROADMAP CORRECTION: TWO PARALLEL TRACKS

Do NOT model the project as a single rigid sequence:

`L5 -> L6 -> L7 -> automation`

That would unnecessarily preserve human prompt-copying as a bottleneck.

Use two parallel tracks.

### SCIENTIFIC PROOF TRACK

```
L5 = verified experience changed a future decision
L6 = changed decision changed real behavior
L7 = changed behavior changed the world and the effect was independently verified
```

L6 and L7 are proof stages. They are not prerequisites for building the cross-IA relay that will execute future experiments.

### SYMBIOSIS INFLECTION TRACK

The operational inflection point is the point where IABV itself becomes the transport/orchestration layer between external AIs.

Use these minimal gates:

#### I0 — External-agent connection
IABV can securely invoke an external agent/account using a legitimate, auditable authority path.

Status: **NOT PROVEN as a complete system-level capability.**

Existing R3/adapter work is evidence that some production adapter/dispatch edges exist, but do not infer full autonomous external-agent cognition or authority closure.

#### I1 — Automatic round trip
IABV can:

```
select agent
-> build task/prompt from canonical context
-> invoke agent
-> receive result
-> bind result to execution/provenance identity
-> verify result
```

without the human copying the prompt and response.

Status: **NOT PROVEN.**

#### I2 — Dynamic closed symbiosis loop
IABV can:

```
objective
-> choose best-fit external capability
-> generate/delegate prompt
-> invoke agent
-> receive result
-> independently verify
-> learn from the result
-> choose the next agent/task
-> continue automatically
```

with stop/escalation conditions and complete provenance.

Status: **NOT PROVEN.**

### POINT OF INFLECTION

Treat **I2** as the first operational point of inflection.

Why:

Before I2:

```
human
-> copy prompt
-> external AI
-> copy result
-> ChatGPT
-> copy prompt
-> another AI
```

After I2:

```
IABV
-> select
-> invoke
-> receive
-> verify
-> learn
-> reselect
-> invoke
-> ...
```

The human becomes primarily the objective setter/supervisor rather than the manual message transport.

L6 and L7 can then be run through this automated loop instead of repeatedly requiring manual prompt transfer.

## STRONGER INFLECTION, AFTER I2

I2 is the minimum operational inflection. A stronger inflection requires demonstrated reuse across multiple tasks:

```
I2
+
dynamic capability-fit routing
+
verified continuation
+
reusable provenance
+
reduced human transport work
```

This should be measured experimentally rather than assumed.

A useful operational metric is:

`H = human_transport_steps_per_completed_task`

Target direction:

`H_before > H_after`

But this metric alone does not prove intelligence; it measures reduction of manual orchestration cost.

Additional useful metrics:

- `D` = verified delegated tasks completed automatically;
- `R` = verified round trips;
- `V` = verified results accepted;
- `E` = escalations/stops;
- `P` = provenance-complete executions.

A first operational productivity claim can be made only after these are observed in real executions.

## ROUTING PRINCIPLE

Do not use a fixed AI order.

Route by contextual capability fit:

`AVAILABLE -> CAPABLE -> SELECTED -> INVOKED -> EXECUTED -> RESULT -> VERIFIED -> LEARNING ELIGIBLE -> LEARNING REUSED`

Historical role assignments are evidence, not permanent identities.

Current capability evidence:

- ChatGPT: synthesis, reconciliation, epistemic adjudication, memory writeback, routing design.
- Sonnet 5 Low: adversarial forensic audit and false-positive detection.
- Devin: Windows/runtime execution and bounded implementation.
- Codex: reserve for broader/ambiguous repository implementation or archaeology when specifically needed.
- Opus 5: reserve for genuine architectural contradiction or higher-order ambiguity.

## CURRENT NEXT ACTION

The immediate L5 artifact publication problem is still operationally unresolved on the remote branch.

Do NOT advance to L6 yet.

Next actor:

**DEVIN**

Task: publish the already-recovered original runtime artifact from a clean Git state, without rewriting the runtime or introducing unrelated commits.

Then:

**SONNET 5 LOW**

Task: final independent audit of the remotely readable L5 evidence package.

If Sonnet confirms L5, return to **ChatGPT** for the design of the smallest I0/I1 symbiosis experiment.

Do not require L6/L7 to be complete before beginning I0/I1.

## CRITICAL GIT SAFETY RULE

When the evidence branch becomes tangled by local merge/reset attempts:

- do not use `reset --hard` as the next reflex;
- do not force-push;
- do not rewrite published history;
- create a fresh worktree from the remote branch tip;
- recover/copy the original artifact bytes into that clean worktree;
- make one minimal evidence-publication commit;
- verify remote read-back.

## EPISTEMIC INVARIANTS

```
implemented != proven
test pass != production proof
wired != invoked != observed != caused
persistence != learning
learning != behavioral change
behavioral change != improvement
report != evidence
local commit != remote verification != independent audit
CONNECTION != INTEGRITY-VERIFIED CONNECTION
FACT != INFERENCE != ASSUMPTION
confidence != truth status
generated != authorized != executed != verified
```

## CURRENT KNOWLEDGE DELTA

### Delta-K

We now distinguish two different goals that had been partially conflated:

1. proving increasingly strong causal properties of IABV itself (L5/L6/L7);
2. removing the human from the manual transport loop between external AIs (I0/I1/I2).

The second can accelerate the first and should therefore be developed in parallel once the minimum authority/connection boundary is sufficiently controlled.

### Delta-Pi

Future prompts should explicitly identify whether the task is:

- proof-stage work (L5/L6/L7),
- infrastructure for automatic symbiosis (I0/I1/I2),
- or both.

Do not add proof stages merely because the manual orchestration problem has not yet been automated.

### Delta-B

No automated I2 loop is currently proven.

### Delta-Y

No new external-world outcome beyond the existing L5 file mutation is claimed by this overlay.

## CROSS-CHAT RETRIEVAL INSTRUCTION

A new chat whose objective involves:

- L5/L6/L7,
- external-agent delegation,
- automatic prompt routing,
- reducing manual copy/paste,
- multi-Devin-account orchestration,
- agent capability selection,
- or dynamic symbiosis

must read this file together with:

- `CONTEXT-INDEX.md`
- `CURRENT-STATE.md`
- `UNRESOLVED-KNOWLEDGE.md`
- `SYMBIOSIS-MAP.md`
- `CHAT-ARCH-2026-09-17-004-cross-chat-symbiosis-reconciliation.md`
- `CHAT-ARCH-2026-09-17-006-l5-competitive-selection-routing.md`

Then reconcile every claim against current remote Git state before acting.

## 2026-09-18 LIVE UPDATE — L5 ARTIFACT PUBLICATION IS STILL OPEN

Direct remote read-back now establishes:

- remote branch `l5-evidence-capture-3241b3ef6` currently resolves to `caaf23c4b380d2228b3f5a7e494e66419b6934fb`;
- remote runtime artifact path is `IABV_v1.5/l5_evidence/l5_experiment_20260918_022256_runtime.txt`;
- remote blob size is 17267 bytes;
- local original runtime artifact was independently measured at 17617 bytes with SHA256 `61c56fd0404469dec60cb29827546b23011d93d4942ce5470c83a705d1628ef2`;
- therefore the remote artifact is not byte-identical to the original runtime evidence;
- the branch history contains local publication attempts/duplicates, so future repair must NOT use merge/rebase/reset on the contaminated worktree.

Correct recovery procedure:
1. create a fresh worktree from `origin/l5-evidence-capture-3241b3ef6`;
2. set `core.autocrlf=false` for that fresh worktree;
3. copy the ORIGINAL local runtime bytes into the existing remote artifact path;
4. verify SHA256 = `61c56fd0404469dec60cb29827546b23011d93d4942ce5470c83a705d1628ef2`;
5. `git add -f` only the runtime artifact and, if necessary, the manifest path;
6. make one fast-forward commit;
7. push without force;
8. verify the remote blob hash from `git show <remote-ref>:<path>` or equivalent byte-preserving readback.

Do not create another runtime execution. Do not rewrite the original runtime log. Do not add a new evidence run.

L5 remains: **strongly evidenced under the existing Windows test harness, but canonical closure is pending final byte-identical remote artifact readback and independent Sonnet audit.**

The strategic roadmap remains two parallel tracks:
- Proof track: L5 -> L6 -> L7.
- Symbiosis inflection track: I0 -> I1 -> I2, where I2 means IABV can select an external AI, delegate, receive, verify, learn/replan and delegate the next task without human copy/paste. I2 can be developed in parallel with L6/L7 and is not a prerequisite to complete them.

Do not force a fixed AI order. Route by capability fit and current uncertainty.
