# BIO-04 — STAGE-A M2
# AGENTIC AI RUNTIME DATA DISCLOSURE
## EXTERNAL SCIENTIFIC + TECHNICAL RESEARCH CONTRACT

STATUS:
PLANNED / NOT YET EXECUTED

PLANNED_EXECUTION_ID:
BROWSE_2026-10-03_BIO-04-A-M2_001

OBJECT_ID:
BIO-04-STAGE-A-M2-AGENTIC-AI-RUNTIME-DATA-DISCLOSURE

RESEARCH_PHASE:
BIO-04-STAGE-A-M2

DATE_BOUNDARY:
Evidence current through 2026-10-03.

ACTOR / CAPABILITY:
ChatGPT Deep Research / equivalent primary-source deep-research capability.

TASK_TYPE:
RESEARCH — NOT DIAGNOSTIC
NOT IABV SOURCE AUDIT
NOT IMPLEMENTATION
NOT POLICY SELECTION

## 0. PURPOSE AND RELATION TO M1

BIO-04 Stage-A M1 has already been adjudicated and canonically absorbed as scoped, corrected knowledge.

M1 established, at a bounded scientific level, that information-flow/privacy analysis cannot be reduced to binary public/private labeling and must distinguish contextualized information type, relevant actors/roles, transmission conditions and purpose with source-precise treatment. It also established that external frameworks do not automatically constitute machine-enforceable IABV/OSES transmission policy.

M2 must NOT repeat M1 as a generic privacy survey.

M2 must advance from those foundations to the specific open scientific frontier:

agentic AI / runtime information disclosure and propagation.

The M2 object is external science only. It does not determine the eventual human OSES policy and does not establish any fact about IABV runtime behavior.

## 1. EXACT RESEARCH OBJECT

Study the technical mechanisms by which information can be:

- exposed;
- transmitted;
- propagated;
- retained;
- logged;
- transformed;
- inferred;
- recombined;
- disclosed to another actor or service

inside contemporary LLM and agentic-AI execution environments.

The core path is:

user/context information
→ model/inference context
→ tool/function call
→ external provider/service
→ memory/session state
→ inter-agent exchange
→ logging/trace/telemetry
→ derived/inferred/composed information.

The research must distinguish:

INTENDED / NECESSARY / AUTHORIZED FLOW

from:

UNINTENDED / UNNECESSARY / EXCESSIVE / POLICY-INCONSISTENT DISCLOSURE.

Do not assume that an observed flow is harmful merely because information crossed a boundary. Demonstrate the relevant privacy/security property and the evidence supporting it.

Do not infer production prevalence from a synthetic benchmark.

## 2. CENTRAL QUESTION

What technical mechanisms and empirical, formal, or authoritative evidence distinguish an intended and appropriately constrained information transfer from accidental, unnecessary, excessive, or policy-inconsistent disclosure in contemporary LLM/agentic-AI systems?

For each major mechanism determine:

1. where the disclosure occurs;
2. what mechanism causes it;
3. what information crosses the boundary;
4. which boundary is crossed;
5. whether disclosure is direct, propagated, transformed, inferred, or composed;
6. what evidence demonstrates the phenomenon;
7. what intervention/control was tested;
8. what effect was observed;
9. what competing explanation remains;
10. what remains unresolved.

## 3. REQUIRED BOUNDARIES

Investigate at minimum:

A. MODEL / CONTEXT ASSEMBLY BOUNDARY
B. TOOL / FUNCTION-CALL BOUNDARY
C. MCP-STYLE / PROTOCOL BOUNDARY where evidence exists
D. AGENT-TO-AGENT / ORCHESTRATION BOUNDARY
E. MEMORY / SESSION / STATE BOUNDARY
F. LOGGING / TRACE / TELEMETRY / OBSERVABILITY BOUNDARY
G. EXTERNAL PROVIDER / CLOUD / THIRD-PARTY SERVICE BOUNDARY
H. STORAGE / CACHE / RETENTION BOUNDARY
I. TRANSFORMATION / REDACTION / PSEUDONYMIZATION BOUNDARY
J. INFERENCE / LINKAGE / COMPOSITION BOUNDARY.

Do not assume every contemporary agent framework implements every boundary.

For each boundary report:

WHAT CAN CROSS
HOW IT CROSSES
WHAT IS DIRECTLY OBSERVABLE
WHAT CAN BE INFERRED
WHAT CONTROL WAS TESTED
WHAT EVIDENCE SUPPORTS THE CONTROL
WHAT IS ONLY A PROPOSAL
WHAT REMAINS UNCERTAIN.

## 4. MODEL-CONTEXT DISCLOSURE

Investigate how information enters model context through:

- user messages;
- conversation history;
- system/developer context where documented;
- retrieved documents;
- memory;
- tool results;
- environment metadata;
- application state;
- task history;
- hidden/internal context only where documented by reliable sources.

Study:

- over-inclusion;
- unnecessary context propagation;
- context leakage;
- cross-task context carryover;
- stale context;
- accidental inclusion;
- context-window contamination;
- disclosure caused by broad context assembly.

Explicitly distinguish:

DATA AVAILABLE TO THE HOST APPLICATION
from
DATA ACTUALLY INCLUDED IN MODEL CONTEXT
from
DATA ACTUALLY TRANSMITTED TO AN EXTERNAL PROVIDER.

Do not collapse these levels.

## 5. TOOL / FUNCTION / MCP / AGENT DISCLOSURE

Investigate tool-use and function-calling mechanisms.

Determine whether evidence shows:

A. only task-required fields are transmitted;
B. broader context is transmitted;
C. sensitive context is visible to a tool unnecessarily;
D. tool responses introduce additional information into subsequent reasoning;
E. tool output propagates to another agent/provider;
F. prompt/tool boundaries can be crossed by attack or orchestration behavior.

Where MCP-style evidence exists, examine the protocol-specific mechanism without treating MCP as representative of every agent architecture.

For every finding separate:

protocol capability
from
framework implementation
from
observed runtime behavior.

## 6. MEMORY / SESSION / STATE DISCLOSURE

Investigate:

- conversational memory;
- persistent agent memory;
- session state;
- task history;
- retrieval memories;
- caches;
- cross-agent shared state;
- cross-task reuse.

Explicitly preserve:

RETENTION
≠ EXPOSURE
≠ RETRIEVAL
≠ DISCLOSURE
≠ SECONDARY USE.

Determine under what conditions retained information becomes available to a later task, model, tool, agent, or provider.

Look for empirical demonstrations of:

- unintended retrieval;
- cross-user leakage;
- cross-session leakage;
- memory contamination;
- unauthorized memory access;
- privacy-preserving isolation.

Do not generalize a single framework result to all agent memory systems.

## 7. LOGGING / TRACE / TELEMETRY DISCLOSURE

Investigate whether sensitive or contextual information can cross privacy/security boundaries through:

- request logs;
- prompt/response logs;
- traces;
- observability systems;
- telemetry;
- diagnostics;
- error reporting;
- evaluation pipelines;
- debugging infrastructure;
- monitoring systems.

Distinguish:

NORMAL PRODUCTION BEHAVIOR
from
DEBUG / TEST / EVALUATION BEHAVIOR.

Do not generalize debug-only exposure to production without evidence.

Identify whether controls such as minimization, field filtering, redaction, access controls, retention limits, local-only telemetry, or differential privacy have been empirically evaluated.

## 8. EXTERNAL PROVIDERS / CLOUD

Investigate transmission to:

- hosted model providers;
- inference APIs;
- cloud services;
- third-party APIs;
- delegated agent services.

Separate:

PAYLOAD
METADATA
IDENTIFIERS
TELEMETRY
DIAGNOSTICS
RETENTION
SECONDARY PROCESSING
PROVIDER-SIDE LOGGING
PROVIDER REUSE

whenever the source permits.

Explicitly test the following distinctions:

ENCRYPTION IN TRANSIT ≠ ABSENCE OF DISCLOSURE

LOCAL PROXY ≠ LOCAL PROCESSING

AUTHENTICATED ENDPOINT ≠ PRIVACY AUTHORIZATION

AVAILABLE PROVIDER ≠ PERMITTED PROVIDER.

Do not assert provider retention or reuse unless supported by authoritative provider documentation or independent evidence.

## 9. DIRECT / PROPAGATED / TRANSFORMED / INFERRED DISCLOSURE

Construct and evidence these categories:

DIRECT:
the sensitive/contextual information itself crosses a boundary.

PROPAGATED:
information crosses a chain of actors/services after originating elsewhere.

TRANSFORMED:
the transmitted representation is altered, summarized, redacted, generalized, pseudonymized, or otherwise transformed.

INFERRED / COMPOSED:
new sensitive information becomes inferable or reconstructable from otherwise transmitted information.

For each category identify:

demonstrated mechanisms
strongest evidence
limits of observability
causal/attribution challenges.

Do not call an inference a direct disclosure.

Do not call a possibility an observed disclosure.

## 10. METADATA / LINKAGE / COMPOSITION

Investigate whether apparently low-sensitivity metadata can become sensitive through:

- linkage;
- correlation;
- aggregation;
- timing;
- domain/context;
- identifiers;
- installed applications/models;
- process/window metadata;
- network or provider metadata;
- cross-source composition;
- model inference.

The research must answer both:

WHEN METADATA RISK IS EMPIRICALLY DEMONSTRATED

and

WHEN SUCH A CLAIM REMAINS CONTEXT-DEPENDENT OR THEORETICAL.

Do not assume:
metadata = harmless.

Do not assume:
metadata = sensitive.

## 11. CONTROLS AND CAUSAL EVIDENCE

Research evidence for controls including:

- data minimization;
- selective context disclosure;
- context filtering;
- redaction;
- masking;
- truncation;
- aggregation;
- generalization;
- pseudonymization;
- de-identification;
- capability-scoped tool context;
- information-flow control;
- provenance-aware handling;
- memory isolation;
- runtime authorization;
- policy enforcement at model/tool boundaries;
- local processing;
- output filtering;
- logging/monitoring controls;
- privacy-preserving architectures.

For each control classify evidence as:

EMPIRICAL
FORMAL / THEORETICAL
STANDARD / OFFICIAL GUIDANCE
ENGINEERING PRACTICE
PROPOSED
UNRESOLVED.

Do not treat a proposed architecture as a demonstrated control.

When a causal effect is claimed, identify:

CONTROL
INTERVENTION
COMPARATOR
MEASURE
RESULT
LIMITATION.

Prefer ablation, intervention, controlled comparison, formal proof, reproducible benchmark, or independently replicated evidence.

## 12. AUTHORIZATION / NECESSITY / PURPOSE BOUNDARY

M1 established the conceptual need to distinguish contextualized flow conditions. M2 must now examine how contemporary agent systems technically realize or fail to realize:

- least privilege;
- data minimization;
- purpose limitation;
- authorization;
- recipient restrictions;
- field-level or context-level policy;
- consent where technically relevant;
- persistent-storage permission;
- cross-agent transfer permission.

Explicitly distinguish:

ACCESS AUTHORIZATION
from
TRANSMISSION AUTHORIZATION

and:

AUTHENTICATION
from
AUTHORIZATION.

Do not choose the eventual IABV policy.

## 13. LOCAL VS REMOTE

Research evidence relevant to:

- local inference;
- localhost services;
- local model servers;
- remote endpoint behind a local proxy;
- hybrid inference;
- hosted inference.

Determine what can actually be concluded from “local” as opposed to what still depends on:

- endpoint integrity;
- logging;
- telemetry;
- redirection;
- plugins;
- tool behavior;
- process isolation;
- configuration integrity.

Do not call local execution a privacy guarantee without evidence.

## 14. EMPIRICAL / FORMAL / AUTHORITY SEPARATION

For every major claim classify the strongest available basis:

EMPIRICAL FINDING
FORMAL / THEORETICAL RESULT
STANDARD / OFFICIAL GUIDANCE
ENGINEERING PRACTICE
RESEARCHER SYNTHESIS
HYPOTHESIS
UNRESOLVED.

Preserve:

SOURCE EVIDENCE
→ AUTHOR INTERPRETATION
→ RESEARCHER SYNTHESIS.

Do not silently collapse the layers.

## 15. PRIMARY-SOURCE PRIORITY

Prioritize:

1. peer-reviewed primary empirical research;
2. archival conference/journal papers;
3. formal/theoretical research;
4. reproducible benchmark papers;
5. official standards and government guidance;
6. authoritative provider documentation when the claim concerns provider behavior;
7. high-quality technical reports.

For rapidly changing agentic-AI topics, prioritize 2024–2026 evidence, while retaining older foundational work where necessary.

When a secondary source identifies an important claim, inspect the primary source whenever accessible.

For each important source record:

CLAIM
SOURCE
YEAR
VENUE
SOURCE TYPE
PRIMARY? YES/NO
PEER-REVIEW STATUS
SYSTEM / DATASET
METHOD
WHAT THE SOURCE ACTUALLY SHOWED
LIMITATION
GENERALIZABILITY
RELEVANCE TO THIS OBJECT.

Where available include:
DOI
canonical URL
benchmark
dataset
experimental design
measured variables
effect/result.

## 16. FALSE-POSITIVE / COMPETING-EXPLANATION REQUIREMENT

For each major disclosure finding ask:

WHAT SIMPLER MECHANISM COULD PRODUCE THE SAME OBSERVATION?

Explicitly test or discuss alternatives including:

- required tool context vs unnecessary context;
- benchmark leakage vs runtime leakage;
- prompt injection vs baseline disclosure;
- memorization vs runtime transmission;
- debug logging vs normal production logging;
- documented provider behavior vs independently observed transmission;
- direct disclosure vs inference;
- metadata exposure vs payload exposure;
- possibility vs demonstrated occurrence;
- correlation vs causation;
- framework capability vs deployed configuration.

Where evidence permits, identify the intervention/ablation/counterfactual needed to distinguish alternatives.

## 17. REQUIRED OUTPUT

Return exactly these sections:

## EXECUTION RECEIPT
Include:
PLANNED_EXECUTION_ID
ACTUAL_EXECUTION_ID, if available
OBJECT_ID
RESEARCH_PHASE
DATE BOUNDARY
EXACT RESEARCH OBJECT
CENTRAL QUESTION
TASK TYPE

Explicitly state:
RESEARCH — NOT DIAGNOSTIC

And preserve separately:

REQUESTED CONTRACT
→ ACTUAL SUBMITTED REQUEST
→ EXECUTION INSTANCE
→ RETURNED RESULT.

Do not infer execution from the existence of this contract.

## DIRECT SCIENTIFIC ANSWER

## 1. MODEL-CONTEXT DISCLOSURE

## 2. TOOL / FUNCTION / MCP / AGENT BOUNDARIES

## 3. MEMORY / SESSION / STATE

## 4. LOGGING / TRACE / TELEMETRY

## 5. EXTERNAL PROVIDER / CLOUD

## 6. DIRECT / PROPAGATED / TRANSFORMED / INFERRED DISCLOSURE

## 7. METADATA / LINKAGE / COMPOSITION

## 8. CONTROLS AND EVIDENCE

## 9. AUTHORIZATION / PURPOSE / NECESSITY

## 10. LOCALITY / LOCAL VS REMOTE

## 11. DISCLOSURE-BOUNDARY TAXONOMY

## 12. COMPARATIVE EVIDENCE MATRIX

Required table:

| Disclosure Mechanism | Boundary | Information Exposed | Direct / Propagated / Transformed / Inferred | Evidence Type | Evidence Strength | Intervention / Comparator | Main Limitation |

## 13. CONTROL EVIDENCE MATRIX

Required table:

| Control | Mechanism | Evidence Type | Demonstrated Effect | Comparator | Limitation | Conditions |

## 14. STRONGEST EMPIRICAL FINDINGS

## 15. STRONGEST FORMAL / THEORETICAL RESULTS

## 16. COUNTEREVIDENCE / COMPETING EXPLANATIONS

## 17. EVIDENCE GAPS

## 18. UNRESOLVED SCIENTIFIC QUESTIONS

## 19. PRINCIPAL PRIMARY SOURCES AND EXACT ESTABLISHMENTS

## 20. STAGE-A M2 KNOWLEDGE DELTA

Only knowledge genuinely supported by the research.

Do not turn proposed controls into knowledge of effectiveness.

Do not state an IABV policy.

## 21. FINAL EPISTEMIC BOUNDARY

Explicitly separate:

EMPIRICALLY ESTABLISHED
FORMAL / THEORETICAL
STANDARD / OFFICIAL GUIDANCE
ENGINEERING PRACTICE
RESEARCHER SYNTHESIS
HYPOTHESIS
NOT ESTABLISHED / UNCERTAIN.

## 22. EXACT FINAL QUESTIONS

Answer these exact questions:

1. What are the principal technical boundaries across which information disclosure occurs in contemporary LLM/agentic systems?

2. Which forms of disclosure are directly demonstrated by empirical evidence?

3. Which forms are primarily theoretical or formal?

4. Which controls have empirical evidence of effectiveness?

5. Which controls remain proposals or engineering practices without strong causal evidence?

6. What observations distinguish necessary information transfer from unnecessary over-disclosure?

7. What observations distinguish direct disclosure from propagated disclosure, transformed disclosure, and inferred/composed disclosure?

8. What evidence is still missing before a request-level data-handling policy can be defensibly specified?

9. Which parts of the answer remain uncertain, framework-dependent, or contested?

10. What is the smallest scientifically justified knowledge delta produced by M2?

11. What is the exact first scientific frontier that remains open after M2?

## 23. STRICT ANTI-DRIFT RULES

Do not:

- audit IABV source code;
- audit Codex, Sonnet, Devin, or prior ChatGPT execution;
- design an IABV privacy manager;
- create or propose a new IABV architecture;
- choose the human's request-level policy;
- rank policy choices for IABV;
- claim IABV currently implements or violates a researched mechanism;
- infer IABV runtime transmission from this research;
- generalize one framework or attack to all agentic systems;
- convert possibility into prevalence;
- convert provider documentation into independent empirical proof;
- convert a synthetic benchmark into production prevalence;
- use generic AI privacy as a substitute for runtime mechanism research;
- silently treat encryption, authentication, locality, proxying, or provider availability as privacy authorization;
- make consciousness or superconsciousness claims.

## 24. STOP CONDITIONS

Stop and report the failure boundary if:

- the result becomes primarily generic privacy education;
- the result becomes primarily generic cybersecurity;
- the specific runtime disclosure object is not investigated;
- primary evidence cannot be obtained for central claims;
- the report repeatedly substitutes adjacent topics;
- source provenance cannot be reconstructed sufficiently;
- important conclusions require unsupported generalization.

If an important claim is unsupported, mark it:

NOT ESTABLISHED.

Do not fill evidence gaps with intuition.

END OF RESEARCH CONTRACT
