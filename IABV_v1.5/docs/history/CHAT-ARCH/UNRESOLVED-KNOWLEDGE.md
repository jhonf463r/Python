# IABV v1.5 — Unresolved / Latent Knowledge Register

## PURPOSE

This file exists for ideas, deductions, questions and strategically important gaps that may never have become tickets or commits.

A future chat must consult this register when the active objective overlaps a listed topic. An item is not an implementation commitment merely because it is recorded here.

## ACTIVE HIGH-VALUE UNRESOLVED ITEMS

### UK-01 — Real causal external-agent cognition

QUESTION: Does canonical IABV state actually alter a real external AI's decision or action?

CURRENT STATUS: NOT PROVEN.

WHY IMPORTANT: This is the principal boundary between context delivery and a genuine cognitive control plane.

DISCRIMINATING EXPERIMENT: Compare materially equivalent executions with/without canonical IABV context while holding task, agent and environment stable enough to establish whether the decision/action changes because of IABV state. Capture pre-state, delivered context, action, result, verification and post-state.

### UK-02 — Causal learning / decision influence

QUESTION: After a verified experience is persisted, does a later decision change because of that experience?

CURRENT STATUS: NOT PROVEN.

REQUIRED CHAIN:

`experience → provenance → persistence → later retrieval → decision influence → independently observed changed action`

Persistence alone is insufficient.

### UK-03 — Second-agent continuity

QUESTION: Can a second external agent continue from the canonical state produced by the first agent without manual history reconstruction?

CURRENT STATUS: NOT PROVEN.

WHY IMPORTANT: This is the concrete test of cross-agent continuity as a system property rather than a prompt convention.

### UK-04 — Prediction and calibration loop

QUESTION: Does IABV produce a pre-execution prediction, uncertainty/confidence signal, and later calibration against observed outcome?

CURRENT STATUS: Historical records identify this as an important metacognitive gap; exact end-to-end causal implementation remains unresolved.

TARGET LOOP:

`predict → execute → observe → compare → calibrate → update strategy`

### UK-05 — AdaptiveSession typed provenance canonicalization

QUESTION: Do typed fields actually own runtime decisions and reconstruction?

CURRENT STATUS: Current historical audit found FAIL because legacy metadata remained causally active.

REQUIRED DIRECTION:

`typed canonical fields → runtime decisions → persistence/reconstruction`

Legacy metadata must become compatibility-only and historical sessions may require migration/reconstruction.

### UK-06 — P0-B adversarial Windows validation

QUESTION: Does the hardened authority chain survive the registered Windows attack suite on the latest target?

TARGET:

`origin/audit/p0-b-repopath-on-hardened-base`

`c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3`

STATUS: Pending independent runtime validation in the recorded project state.

ATTACK FAMILIES: pre-registration, trust-root replacement, forged authority/certification, request spoofing, invocation cross-binding, RunRecord cross-binding, SelfAudit forgery, replay/concurrent replay, DB record forgery, runtime code injection, RepoPath substitution, service binary/config replacement.

### UK-07 — Runtime-integrity boundary of cryptographic authority

QUESTION: Can an attacker execute modified code inside the runtime that holds cryptographic authority despite protected keys and trust roots?

CURRENT STATUS: This boundary was explicitly identified as necessary in P0-B hardening.

REQUIRED EVIDENCE: `python314._pth`, user-site isolation, package/site-packages integrity, `RepoPath` integrity, service identity, ACLs, and replacement resistance must be tested together with the authority chain.

### UK-08 — Dynamic historical-context activation

QUESTION: Can a new chat discover the right historical knowledge from GitHub based on its objective without loading the complete archive?

CURRENT STATUS: Navigation layer now exists; operational proof should come from use and subsequent reconciliation.

SUCCESS CONDITION: Objective → domain routing → relevant source archives → current reconciliation → activated context → work without unnecessary historical flooding.

### UK-09 — Archive completeness beyond commits/tasks

QUESTION: Can the archive reliably preserve knowledge that never became code, a ticket or a formal decision?

REQUIRED CONTENT: ideas left in the air, rejected paths, latent deductions, false positives, cross-IA corrections, methodological changes, conceptual breakthroughs and unresolved questions.

CURRENT STATUS: Dedicated register and routing layer now exist; completeness still requires repeated comparison against source conversations when deletion is at stake.

### UK-10 — True D0 external communication frontier

QUESTION: Can IABV demonstrate real authenticated external communication and the symbolic cycle `perspective_before → external observation → reconciliation → perspective_after → persisted delta`?

CURRENT STATUS: Infrastructure and selectors have existed historically, but real authenticated browser/shared-CDP communication was not proven in the available evidence.

## DEFERRED BUT IMPORTANT DESIGN IDEAS

These are intentionally recorded without forcing implementation:

- objective-conditioned context packets rather than universal context dumps;
- capability-driven dynamic role allocation across external AIs;
- automatic activation of only the historical lessons that can affect the current claim;
- explicit "negative knowledge" as a first-class retrieval target;
- claim/evidence ledgers linked to current code and runtime fingerprints;
- causal continuity metrics based on changed downstream decisions rather than message receipt;
- blind reconstruction as a deletion-safety test;
- historical migration of legacy provenance records into typed canonical provenance;
- runtime provenance as a first-class evidence object across tool execution;
- learned collaboration policy: which AI should challenge, implement, observe or adjudicate for a given class of uncertainty.

## REJECTED / DO-NOT-REPEAT IDEAS

- create another brain/orchestrator when existing organs can be wired;
- assume a green unit test proves runtime integration;
- treat a direct adapter call as proof of production routing;
- treat persisted data as proof of causal learning;
- treat a valid signature as proof of legitimate authority;
- treat a new field as canonical while legacy fields still control behavior;
- treat a local archive as sufficient for deletion safety;
- force every objective through the same fixed AI role sequence.

## USE OF THIS REGISTER

A future chat should retrieve this file when its objective overlaps an unresolved item. It should then determine whether the current repository has since resolved, refuted, superseded or still preserves that item.

Resolution requires evidence, not a status edit based only on a later claim.
