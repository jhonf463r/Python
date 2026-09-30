# IABV v1.5 — DEVELOPMENT IDEAS / RESTRUCTURING BACKLOG
## Traceable dormant tasks — 2026-09-29

## PURPOSE

This file preserves useful architectural, methodological and developmental ideas that are not yet justified as implementation work.

An idea is not an active task merely because it is attractive.

Each item must define:
- the hypothesis or design question;
- why it matters;
- the evidence/condition that activates it;
- the existing organs that should be evaluated first;
- the minimum discriminating experiment or audit;
- what must NOT be built prematurely.

This backlog is a traceability layer between:
conversation insight
→ candidate idea
→ activation condition
→ future audit/experiment
→ evidence
→ decision.

## OPERATING RULE

Do not leave high-value ideas only in chat.

Do not turn every idea into code.

Before implementation, reconcile:
objective → current state → existing organ ownership → open causal edge → required capability → experiment/audit.

When an item becomes active, link the resulting evidence and Knowledge Delta back to this file.

---

# ACTIVE / NEAR-ACTIVE TASKS

## MB-01 — FRESH PORTABLE CONTEXT PERSISTENCE

STATUS: OPEN

Current edge:

current DiscernmentFrame
→ PortableContextService.current_package(refresh=True)
→ build_package()
→ portable_context/latest.json
→ read-back
→ semantic state preserved

Activation:
Current META-01-E2a operational frontier.

Preferred capability:
Windows/runtime execution.

Candidate actor:
DEVIN.

Evidence requirement:
Use the public production path, not private helpers. Compare PRE/POST mtime, package_id, updated_at_utc, content hash and discernment state.

Do not interpret persistence as learning.

---

## UI-01 — NATURAL GUI SAME-FRAME CONTINUITY

STATUS: SEPARATE ENVIRONMENTAL EXPERIMENT / UNKNOWN

Question:

automatic Birth Frame
→ real human GUI interaction
→ natural application request path
→ TCA/OSES/PCS consumer
→ same frame observation

Current limitation:
PySide6/QML interaction has not been independently demonstrated in the automated verification environment.

Activation:
Only when a stable graphical-control capability is available.

Candidate capability:
real Windows desktop/browser interaction.

Do not treat a GUI automation failure as proof of a production software defect without independent runtime evidence.

Do not block the whole META-01 program indefinitely on this sub-experiment.

---

# DEVELOPMENTAL / ARCHITECTURAL IDEAS TO ACTIVATE WHEN THE EVIDENCE REACHES THEM

## UFS-01 — UNIVERSAL FLOW SUBSTRATE

STATUS: HYPOTHESIS / FUTURE RESTRUCTURING AUDIT

Hypothesis:

IABV may benefit more from a reusable semantic flow of:
observation → state → decision → action → result → verification → experience → knowledge
than from creating many specialized point-to-point integrations.

The long-term design question is whether an evidence-bearing unit can travel across:
- organs;
- processes;
- machines/devices;
- future IABV instances;
while preserving identity, semantics and provenance.

Candidate existing carriers to evaluate first:
- DiscernmentFrame;
- PerceptionSnapshot;
- TaskContext;
- ExperimentRun;
- PortableContextPackage;
- Claim / VerificationEvent records where applicable.

Do NOT create a UniversalEntity merely to represent this hypothesis.

Activation:
A restructuring audit finds repeated semantic duplication or repeated translation seams among these existing carriers.

Minimum audit:
Compare meaning, owner, scope, mutability, consumers, provenance and lifecycle. Determine whether a canonical transferable state/event/experience/knowledge contract already exists or can emerge from composition.

Success condition:
A reusable transport property is demonstrated without creating a second semantic authority.

---

## UFS-02 — PORTABLE EXPERIENCE / REHYDRATION

STATUS: FUTURE EXPERIMENT

Question:

Can an evidence-bearing experience created on one runtime be serialized, transferred and rehydrated in another process/device without losing:
identity, provenance, verification status, semantic meaning and causal lineage?

Activation:
After MB-01 is proven and after there is an independently verified package that contains a legitimate current state.

Minimum experiment:
runtime A
→ persisted experience package
→ transfer
→ runtime B
→ read-back
→ compare semantic/provenance fields.

Do not call successful deserialization "learning".

---

## UFS-03 — LINEAGE-PRESERVING CROSS-DEVICE MEMORY

STATUS: FUTURE RESTRUCTURING / PROVENANCE AUDIT

Question:

Can IABV distinguish:
same knowledge reused
from:
similar-looking knowledge independently recreated?

Required lineage:

objective
→ observation
→ evidence
→ experience ID
→ verification event
→ knowledge delta
→ transfer
→ receiving runtime
→ reuse event.

Activation:
UFS-02 proves cross-runtime rehydration.

Minimum audit:
Verify globally unique identity, revision-scoped validity, provenance preservation and supersession semantics.

---

## BIO-01 — CELL / NEURON ANALOGY AS FUNCTIONAL AUDIT MODEL

STATUS: CONCEPTUAL / NO IMPLEMENTATION

Use biological analogies only as a design lens:

cell
→ bounded functional organ

membrane
→ interface / contract / governance boundary

neuron
→ message/event carrying state or signal

metabolism
→ observe → decide → act → verify → learn

homeostasis
→ self-observation → deviation detection → correction

heredity
→ verified reusable knowledge + provenance

evolution
→ verified experience changing future behavior/strategy over repeated cycles

This is an analytical model, not a claim of biological equivalence.

Activation:
Future restructuring audit of systemic organization.

Minimum audit:
For each proposed "cell-like" or "neuron-like" unit, identify:
owner, inputs, outputs, state, contract, feedback, persistence, failure mode and verification.

Do not create biologically named abstractions unless the audit demonstrates a semantic need.

---

## BIO-02 — IABV-AS-ITS-OWN-ANALYST

STATUS: STRATEGIC FUTURE TARGET

Question:

Can IABV use its own organs to decide what it needs to investigate about itself?

Target loop:

IABV objective
→ relevant memory
→ self-observation
→ uncertainty
→ causal hypothesis
→ discriminating experiment
→ capability-fit actor/resource
→ governed action
→ independent verification
→ Knowledge Delta
→ future decision.

Activation:
Core operational state/context continuity is sufficiently verified that self-assessment can be grounded in current state rather than stale artifacts.

Minimum experiment:
Present IABV with a bounded self-development objective and require it to identify:
1. current evidence;
2. unresolved uncertainty;
3. first open causal edge;
4. smallest discriminating experiment;
5. required capability;
6. proposed actor/resource;
7. stop condition.

Human remains the governor of consequential permissions.

---

## BIO-03 — LEARNING-TO-ROUTING CAUSAL BRIDGE

STATUS: FUTURE SCIENTIFIC EXPERIMENT

Question:

Does verified experience actually change a later actor/tool/strategy selection?

Required chain:

verified experience
→ persisted knowledge
→ later retrieval
→ measurable score/policy change
→ changed future selection
→ changed observable behavior/outcome.

Activation:
Do not activate until the relevant production learning path is independently proven.

Negative control:
same task without retrieved experience.

Positive condition:
same task with relevant verified experience.

Do not infer behavioral learning from persistence alone.

---

## INT-01 — CROSS-ORGAN SEMANTIC CONTRACT AUDIT

STATUS: FUTURE RESTRUCTURING AUDIT

Question:

Can existing organs collectively detect:

- producer/consumer contract drift;
- temporal mismatch;
- semantic mismatch;
- duplicated responsibility;
- stale state;
- dropped data;
- declared vs observed divergence?

Existing organs to inspect first:
OSES, SelfCodeAnalysis, SignalReconciliation, AnomalyReasoning, RuntimeAuditTracer, DecisionAuditTrail, OrganismStateSnapshot, DiscernmentFrameService, TaskContextAssembler, SystemIdentityRegistry and related registries.

Activation:
Repeated local correctness with end-to-end inconsistency.

Minimum audit:
DISCOVER → CONNECT → IDENTIFY CONTRACT → CHECK TEMPORALITY → CHECK SEMANTICS → DETECT DUPLICATION/DRIFT → RECONCILE → VERIFY EFFECT.

Do not create a universal contract coordinator before proving existing composition is insufficient.

---

# METHODOLOGICAL RULES RECOVERED FROM CURRENT WORK

1. Report-only runtime claims remain report-only until raw artifacts, SHA and runtime provenance are independently reconstructible.
2. Multiple IDs from separate runs are separate evidence populations unless lineage explicitly joins them.
3. Existing public paths are preferred over private method invocation for production-proof experiments.
4. Object-level proof and production-bootstrap proof are separate evidence classes.
5. In-memory generation and persistence are separate causal edges.
6. Persistence, transfer and rehydration do not by themselves prove learning.
7. A GUI automation limitation is not automatically a software defect.
8. Do not manufacture metadata, worker identity, experience counts or thresholds merely to activate a downstream consumer.
9. When a good architectural idea appears, record it here first; implementation waits for an activation condition.
10. A future restructuring audit should evaluate whether the existing graph already contains the proposed capability before adding a new organ.

---

# PRIORITY / ACTIVATION ORDER

Current order is evidence-driven, not a fixed schedule:

1. MB-01 — fresh PortableContext persistence.
2. UI-01 — natural GUI continuity, only when graphical control is genuinely available.
3. Reconcile E2a.
4. BIO-02 — IABV as its own analyst, once the operational substrate is sufficiently grounded.
5. UFS-01 / BIO-01 / INT-01 — structural restructuring audit when repeated semantic seams justify it.
6. UFS-02 / UFS-03 — cross-runtime/device portability after the transferable state contract is evidenced.
7. BIO-03 — causal learning-to-routing transition after production learning evidence is ready.

This ordering is provisional and must be reselected from the first open causal edge at each reconciliation.

---

# TRACEABILITY CONTRACT

Every activated item must record:

OBJECTIVE
→ CURRENT TRUTH
→ OPEN CAUSAL EDGE
→ REQUIRED CAPABILITY
→ ACTOR
→ EXPERIMENT/AUDIT
→ ARTIFACT
→ SHA / runtime provenance
→ INDEPENDENT VERIFICATION
→ RESULT
→ KNOWLEDGE DELTA
→ NEXT ACTIVATION CONDITION

No item becomes "closed" because it is described as designed, implemented, discussed or desirable.


## 2026-09-29 MB-01 RESULT — PERSISTENCE REPORT-BACKED / REMOTE READ-BACK REQUIRED

A Windows execution reported successful use of the public bootstrap path:

export_portable_context(refresh=True)
→ current_package(refresh=True)
→ build_package()
→ persistence
→ read-back.

Reported PRE/POST package identities and hashes indicate a fresh persisted package and matching read-back. However, the new runtime report and raw artifacts have not yet been published to GitHub, so the result remains REPORT-BACKED rather than ARTIFACT-VERIFIED.

Do not rerun the experiment solely to compensate for missing publication.

Required next action:
report → raw artifacts → execution provenance → publication branch/commit → remote read-back → independent Sonnet audit.

After independent verification:
- if confirmed, change MB-01 to CLOSED / PROVEN;
- if discrepancy appears, preserve the discrepancy as a new causal subtask;
- only then reconsider activation of UFS-02 or BIO-02.

Current strategic consequence:
The persistence edge is no longer the conceptual bottleneck if the reported evidence survives publication and audit. The next high-value programmatic frontier is BIO-02: IABV-as-its-own-analyst, not another round of low-level wiring tests.
