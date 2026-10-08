# IABV v1.5 — DEEP RESEARCH PROMPT CONSTRUCTION AND REUSE PROTOCOL
## Method Delta from Repeated Deep-Research Execution Failures — 2026-10-03

## MANDATORY PRE-PROMPT GATE — ACTIVATE EXPERIENCE BEFORE CONSTRUCTION

Do not compose a Deep Research prompt by extending the previous prompt or by relying on the user's latest context dump alone.

Before construction:
1. enter the current IABV frame using `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`, and the objective-relevant source records;
2. recover prior failures and false positives for this research class;
3. retrieve negative knowledge and existing source/organ reuse candidates;
4. identify which experience changes the research object, in/out scope, source plan, required coverage, stop conditions or acceptance gates;
5. write the prompt only after these constraints are explicit.

Mandatory evidence-derived controls from the RQ21.55/RQ21.56 failures:
- A wrong-object report is rejected before source quality is assessed.
- A report on the broad correct domain is still insufficient unless it answers the exact discriminating research object.
- Every required technical guarantee must map to primary-source API/policy, enforcement boundary, observation/evidence, uncovered paths, target-version availability and proof requirement.
- A bibliography category such as "Microsoft documentation" is not a verifiable citation. Require direct primary-source URLs and claim-level attribution.
- A named API or mechanism found in documentation is a candidate, not proof of target availability or sufficient coverage.
- Explicitly separate external documentation research from target-machine/runtime feasibility. The former cannot claim the latter without evidence from that runtime.
- Do not infer that extensive prose, Mermaid diagrams, a roadmap, or current-sounding CVEs satisfy the required result signature.

The result gates must remain ordered:
`OBJECT ALIGNMENT → REQUIRED COVERAGE → SOURCE SUPPORT → EVIDENCE QUALITY → METHODOLOGICAL RIGOR → SYNTHESIS QUALITY`.

Material prompt construction is blocked until the experience-activation gate is satisfied. This is a use of existing IABV memory/coordination organs, not a new research/memory subsystem.

---

## PURPOSE

Preserve the reusable method for constructing future Deep Research requests so new chats and future actors do not repeat prior semantic-substitution failures.

Deep Research is a capability/resource, not an epistemic authority over IABV.

The durable lesson is:

`prompt quality ≠ prompt length`

and:

`detailed prompt ≠ correct research execution`.

The prompt must preserve the objective, research object, boundaries, source strategy, execution identity, result signature and acceptance gates.

---

# 1. CURRENT PROVEN FAILURE PATTERN

The 2026-09-30 through 2026-10-03 sequence demonstrated repeated substitutions such as:

`scientific research object → generic "advanced research" report`

`privacy/data-flow question → generic contract/security report`

`research execution → object/metadata diagnostic`

Therefore future research must be controlled as:

`objective
→ research contract
→ execution identity
→ research-object lock
→ research decomposition
→ source strategy
→ execution
→ result-signature gate
→ source/evidence adjudication
→ accepted knowledge
`

Never use:

`long prompt → long report → assume success`.

---

# 2. TASK SPECIFICATION VS RESEARCH OBJECT

Every research prompt must distinguish:

### TASK SPECIFICATION
The instructions governing the execution.

### RESEARCH OBJECT
The exact phenomenon/questions/claims being investigated.

The following are not interchangeable:

`research topic ≠ research methodology`

`research object ≠ attached document`

`research object ≠ prompt text`

`research phase label ≠ scientific subject`

`IABV context ≠ external scientific evidence`

A coherent report about the wrong object is still a failed research result.

---

# 3. REQUIRED PROMPT HEADER

Every Deep Research prompt should begin with:

- ACTOR / CAPABILITY FIT
- TASK TYPE
- EXECUTION_ID
- OBJECT_ID
- RESEARCH_PHASE
- EXACT RESEARCH OBJECT
- CENTRAL QUESTION

The execution identity identifies the run.

The object identity identifies what is being researched.

Never reuse a diagnostic token as the sole identity of a research run.

---

# 4. RESEARCH OBJECT LOCK

Write the research object in one sentence that can be compared literally against the eventual result.

A good object statement answers:

`What phenomenon is being investigated?`

not:

`What kind of report should be written?`

Then repeat the exact object in a short OBJECT LOCK near the beginning of the prompt.

The result must be adjudicated first against this sentence.

---

# 5. CENTRAL QUESTION

The central question must be discriminative, not merely topical.

Weak:

`Research privacy and AI.`

Stronger:

`What evidence distinguishes context-appropriate information flow from merely authorized access when sender, recipient, purpose and transmission conditions differ?`

The central question should make clear what uncertainty the research is intended to reduce.

---

# 6. SCOPE BOUNDARY

Every prompt must contain:

### IN SCOPE
Only the dimensions required to answer the central question.

### OUT OF SCOPE
Neighboring topics that could produce plausible but irrelevant reports.

For repeated drift domains, explicitly prohibit known substitutions.

Examples:

- generic research methodology;
- generic cybersecurity;
- generic software architecture;
- generic requirements engineering;
- generic contract analysis;
- project management.

Do not over-expand the scope merely to make the prompt appear comprehensive.

---

# 7. DECOMPOSE THE RESEARCH INTO THREADS

For complex questions, do not rely on one giant search query.

Decompose into independent research threads.

Each thread should follow:

`concept → mechanism → primary evidence → counterevidence/limitations → operational implication`

Use only the threads necessary to answer the research object.

A complex research program may be assembled later from accepted modules.

This reduces topic substitution and makes coverage auditable.

---

# 8. SEARCH STRATEGY

The prompt should direct the researcher to:

1. identify foundational sources;
2. search recent primary research;
3. compare competing findings;
4. verify source metadata;
5. inspect the actual methods/results of important papers;
6. distinguish consensus from active disagreement;
7. avoid treating recency as evidence strength.

For rapidly changing domains, explicitly set a date boundary.

---

# 9. SOURCE HIERARCHY

Default priority:

1. primary empirical studies;
2. peer-reviewed conference/journal papers;
3. foundational theoretical papers;
4. systematic reviews/meta-analyses;
5. official standards and government guidance;
6. high-quality technical reports.

Secondary web pages may help discover sources but should not silently replace primary evidence when primary material is available.

---

# 10. CLAIM-LEVEL SOURCE CONTRACT

For every major claim require:

`CLAIM
→ SOURCE
→ YEAR
→ SOURCE TYPE
→ WHAT WAS ACTUALLY SHOWN
→ LIMITATION
→ RELEVANCE`

Where applicable also record:

- authors;
- venue;
- DOI/PMID/arXiv/canonical URL;
- peer-review status;
- study/system type;
- method;
- measured variables;
- actual result.

Never allow a citation merely attached to a paragraph to stand in for source verification.

---

# 11. EVIDENCE TYPE SEPARATION

Every major conclusion should be typed as one or more of:

- EMPIRICAL FINDING
- THEORETICAL FRAMEWORK
- STANDARD / OFFICIAL GUIDANCE
- ENGINEERING PRACTICE
- RESEARCHER SYNTHESIS
- UNRESOLVED

Preserve:

`empirical result → author interpretation → researcher synthesis`

Do not silently promote one layer into another.

---

# 12. RESULT SIGNATURE

The prompt must define what a successful result MUST contain.

Examples:

- direct answer to the central question;
- coverage of each required thread;
- primary-source evidence;
- methodological limitations;
- competing explanations;
- false-positive controls;
- unresolved questions;
- source audit;
- explicit handoff boundary.

The result-signature is an acceptance contract, not merely formatting guidance.

---

# 13. ACCEPTANCE GATE ORDER

Always evaluate the returned research in this order:

`OBJECT ALIGNMENT
→ REQUIRED COVERAGE
→ SOURCE SUPPORT
→ EVIDENCE QUALITY
→ METHODOLOGICAL RIGOR
→ SYNTHESIS QUALITY`

Do not let:

- report length;
- number of citations;
- tables;
- technical vocabulary;
- polished formatting;
- confident tone

compensate for failure of an earlier gate.

---

# 14. FALSE-POSITIVE CONTROLS

Every research prompt should ask:

`What simpler explanation could produce the same observed conclusion?`

Depending on the domain, require consideration of:

- confounding;
- selection effects;
- memorization;
- leakage;
- circular evaluation;
- proxy metrics;
- missing counterfactuals;
- correlation/causation confusion;
- context omission;
- unsupported generalization.

Research should identify the control, ablation, intervention, replication or other design feature that distinguishes the stronger claim.

---

# 15. INPUT / CONTEXT RULE

If external context is supplied, type it explicitly.

Use:

`IABV-CONTEXT`
`EXTERNAL-SCIENCE`
`RESEARCHER-SYNTHESIS`
`UNRESOLVED`

Remember:

`IABV-CONTEXT ≠ EXTERNAL-SCIENCE`

Repository content can establish what IABV says about itself.

It cannot establish an external scientific claim.

An external scientific paper can establish a scientific finding.

It cannot establish that an IABV implementation satisfies that finding.

---

# 16. SELF-CONTAINED STAGE A

When the immediate goal is external scientific grounding, prefer a self-contained Stage-A execution unless repository context is itself the object of investigation.

Stage A:

`external scientific evidence`

Stage B:

`IABV source/runtime reconciliation`

Do not force Stage A to reconstruct IABV architecture.

This separation is especially important after prior failures where repository context caused document-centric or architecture-centric drift.

---

# 17. WHEN REPOSITORY CONTEXT IS NECESSARY

Use repository-aware research only when the research question genuinely requires IABV context.

If repository context is required:

- pin the exact ref/SHA;
- list the exact files that must be read;
- require an IABV context receipt;
- distinguish repository claims from external science;
- fail closed if required inputs are unavailable;
- never invent missing repository content.

Do not assume:

`repository URL supplied → repository actually inspected`.

Require evidence of what was actually read when it matters.

---

# 18. DIAGNOSTIC VS RESEARCH

A diagnostic answers one interface question.

Examples:

`Was the research object preserved?`

`Was the attachment accessible?`

`Was the canonical prompt actually delivered?`

A research execution answers the substantive scientific question.

Do not substitute:

`object-preservation diagnostic → scientific result`

Once a diagnostic has answered its intended question, repeating the same diagnostic without a changed uncertainty is evidence of diagnostic replay / execution-handoff ambiguity.

---

# 19. EXECUTION PROVENANCE

Preserve separately:

`requested prompt
→ prompt actually submitted, if observable
→ execution instance
→ returned result
→ independent adjudication`

Never infer:

`canonical prompt exists → canonical prompt was executed`.

A research artifact is not proof of its own execution provenance.

---

# 20. MODULAR RESEARCH DESIGN

For large research programs, prefer:

`Stage A / Module 1
→ adjudication
→ Module 2
→ adjudication
→ Module 3
→ synthesis`

rather than one enormous undifferentiated execution when modularization materially improves falsifiability and coverage.

A module should have:

- one primary object;
- one central question;
- bounded threads;
- source contract;
- result signature;
- stop conditions.

---

# 21. STOP CONDITIONS

Stop and report the failure boundary when:

- the object cannot be preserved;
- required input is unavailable;
- source verification is materially impossible;
- the requested evidence cannot be obtained;
- the task would require inventing missing information;
- output is repeatedly substituted by a neighboring topic.

Do not repair a blocked scientific task by silently changing the object.

---

# 22. ACTOR SELECTION

Deep Research is a capability, not a permanent actor assignment.

Select it when the open edge requires:

- broad literature discovery;
- primary-source synthesis;
- current evidence;
- methodological comparison;
- source verification.

After each result recompute:

`current truth
→ uncertainty
→ required capability
→ capability-fit actor`

Do not inherit the next actor from a previous research prompt.

---

# 23. POST-RESEARCH ADJUDICATION

Never absorb the returned report directly.

Use:

`result
→ object gate
→ coverage gate
→ source audit
→ evidence classification
→ contradiction analysis
→ Knowledge Delta
→ IABV reconciliation`

Then distinguish:

`report
≠ artifact
≠ source
≠ evidence
≠ verified knowledge`

---

# 24. PROMPT QUALITY CRITERION

A robust research prompt is not the longest possible prompt.

Its quality comes from:

`object precision
+ boundary precision
+ query decomposition
+ source strategy
+ evidence contract
+ false-positive controls
+ execution provenance
+ result signature
+ stop conditions`

A shorter prompt with those properties is preferable to a longer prompt without them.

---

# 25. METHOD DELTA FROM BIO-04

The BIO-04 experience adds a specific reusable lesson:

A long report about:

`"advanced research"`

may be internally coherent and still have zero value for a privacy/data-flow research objective.

Therefore:

**OBJECT ALIGNMENT IS A HARD PRECONDITION TO EVIDENCE QUALITY.**

Likewise:

`citation mention ≠ source verification`

and:

`research brief ≠ executed research result`.

---

# 26. FUTURE-CHAT ENTRY RULE

When a new chat asks for Deep Research:

1. Read the current Deep Research operating protocol.
2. Identify the current objective and first open research edge.
3. Reconcile relevant memory and current state.
4. Determine whether the need is:
   - diagnostic,
   - external science,
   - repository-aware science,
   - source/contract audit,
   - post-research adjudication.
5. Construct the execution contract accordingly.
6. Give the researcher the smallest bounded object that can produce the needed information gain.
7. Define acceptance before execution.
8. After the result, adjudicate before routing onward.

Do not copy an old research prompt mechanically.

---

# 27. REUSABLE PROMPT TEMPLATE

Use this structure for future Deep Research requests:

`ACTOR / CAPABILITY
TASK TYPE
EXECUTION_ID
OBJECT_ID
RESEARCH_PHASE

EXACT RESEARCH OBJECT

CENTRAL QUESTION

WHY THIS QUESTION MATTERS / UNCERTAINTY

IN SCOPE

OUT OF SCOPE

RESEARCH THREADS

SEARCH / SOURCE STRATEGY

SOURCE HIERARCHY

CLAIM-LEVEL EVIDENCE CONTRACT

FALSE-POSITIVE / COUNTEREXPLANATION REQUIREMENTS

INPUT / CONTEXT RULE

EXECUTION PROVENANCE

REQUIRED RESULT SIGNATURE

ACCEPTANCE GATES

STOP CONDITIONS

FINAL EPISTEMIC BOUNDARY

END`

---

# 28. CURRENT BIO-04 APPLICATION

For BIO-04, the current research modules should follow the above method.

Current scientific object:

`privacy / contextual integrity / information-flow foundations for AI-assistant data transfer`

Current module example:

`Contextual Integrity + privacy engineering + information flow`

This module should be adjudicated before dispatching the next module.

Do not automatically expand back into a giant prompt until the first module demonstrates that the research execution surface is preserving the object and producing source-audited evidence.

---

# 29. FINAL PRINCIPLE

The purpose of this protocol is not to make prompts verbose.

It is to make the research chain auditable:

`objective
→ exact object
→ bounded search
→ evidence
→ verification
→ accepted knowledge`

The enduring negative knowledge is:

`well-written prompt ≠ successful research`

`long report ≠ good research`

`citation ≠ verified evidence`

`diagnostic ≠ research`

`research contract ≠ execution`

`external science ≠ IABV proof`

`methodological recommendation ≠ human policy decision`

END OF PROTOCOL

## 30. CONCRETE RESEARCHER / IA DESTINATION

Deep Research is a capability, not a sufficient handoff identity.

Every research routing decision must explicitly materialize:

`RESEARCH CAPABILITY → CONCRETE IA / EXECUTION SURFACE → COMPLETE PROMPT`.

The prompt header must therefore contain:

- `IA DESTINO / EXECUTION SURFACE`;
- `ACTOR / CAPABILITY FIT`;
- `TASK TYPE`;
- `EXECUTION_ID`;
- `OBJECT_ID`.

Examples:
- `IA DESTINO: ChatGPT Deep Research`
- `IA DESTINO: Claude Sonnet`
- `IA DESTINO: Devin Windows runtime`
- `IA DESTINO: Codex repository/provenance`

Do not end with `Deep Research capability` or `independent verifier` alone when a concrete destination is known.

The distinction is preserved:
`capability != concrete IA`
`concrete IA != fixed pipeline position`.

The destination must be recomputed after each material reconciliation.
