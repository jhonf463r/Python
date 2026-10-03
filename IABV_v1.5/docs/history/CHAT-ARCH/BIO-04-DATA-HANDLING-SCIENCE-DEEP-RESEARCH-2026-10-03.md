# BIO-04 — DEEP RESEARCH: OSES DATA-HANDLING / PRIVACY / INFORMATION-FLOW POLICY
## SCIENTIFIC + PRIVACY-ENGINEERING + AGENTIC-AI CONCEPTUAL FOUNDATION

### RESEARCH MODE

SCIENCE / TECHNICAL / PRIVACY-ENGINEERING RESEARCH ONLY.

Do not audit IABV source code.
Do not design IABV architecture.
Do not implement anything.
Do not choose the final IABV policy.
Do not treat an AI-generated recommendation as authoritative.

The purpose of this research is to give a human decision-maker a rigorous, current conceptual and empirical foundation for defining a request-level data-handling policy for OSES.

Date boundary:
research current through 2026-10-03.

---

# 1. WHY THIS RESEARCH IS REQUIRED

The engineering audit has identified a genuine semantic gap:

OSES context construction → request-level data classification/policy.

The repository currently contains partial mechanisms in other domains, but no demonstrated request-level policy that determines what contextual information may be sent to a particular inference realization.

The human therefore must eventually decide the policy.

Before making that decision, establish scientifically and technically what the concepts actually mean.

Do NOT begin with the policy classes already proposed as though they were scientifically canonical.

Instead, derive the concepts first, then show how those concepts can be operationalized into policy choices.

---

# 2. CENTRAL RESEARCH QUESTION

What is the most defensible contemporary framework, based on current scientific literature, privacy engineering, information-flow/security research and authoritative standards, for deciding whether a piece of contextual information may flow from a laptop-native AI assistant to a local or remote inference system?

The framework must distinguish:

DATA PROPERTY
→ PRIVACY / SECURITY RISK
→ CONTEXT / PURPOSE
→ SENDER
→ RECIPIENT
→ TRANSMISSION MECHANISM
→ AUTHORIZATION / POLICY
→ TRANSFORMATION
→ ALLOWED FLOW
→ OBSERVABLE EFFECT

---

# 3. REQUIRED CONCEPTUAL DISTINCTIONS

Research and rigorously distinguish at minimum:

### Privacy
What privacy means in contemporary privacy theory and engineering.

### Personal data / personally identifiable information
What counts as identifying information and how indirect identifiers, metadata and contextual identifiers are handled.

### Sensitive information
Whether “sensitive” is a fixed data taxonomy, context-dependent, risk-dependent, or a combination.

### Security
How security differs from privacy.

### Confidentiality
How confidentiality differs from privacy and authorization.

### Authorization
What authorization means technically and whether authorization to access data is equivalent to authorization to transmit data to another recipient.

### Authentication
Why authentication of the sender/account does not by itself authorize a particular information flow.

### Data minimization
What it means and how necessity/relevance are evaluated.

### Purpose limitation
How purpose affects whether an otherwise accessible item may be used or transferred.

### Least privilege
Whether least privilege applies to information disclosure and what its limits are.

### Redaction
What redaction can guarantee and what it cannot.

### Pseudonymization
What it achieves and what residual risks remain.

### Anonymization / de-identification
What scientific criteria are used and why removal of direct identifiers does not necessarily eliminate privacy risk.

### Aggregation
When aggregation reduces risk and when it can still reveal sensitive information.

### Local-only processing
What “local-only” actually means.

Distinguish:
- physically local computation;
- trusted local endpoint;
- local service over localhost;
- remote service accessed through a local proxy;
- encrypted transport;
- hosted remote inference.

Do not assume “local” automatically means private or trustworthy.

### Cloud-permitted processing
What conditions normally need to be established before external processing of contextual data is reasonable.

### Explicit authorization / consent
Distinguish user authorization, technical authorization, policy authorization and informed consent.

Do not collapse these concepts.

### Fail-open / fail-closed / deny-on-unknown
Research the security implications of each and identify when each is appropriate.

Do not assume one universal answer.

---

# 4. CONTEXTUAL INTEGRITY

Research Helen Nissenbaum’s Contextual Integrity theory as a privacy model.

Explain precisely:

- context;
- information subject;
- sender;
- recipient;
- information type/attribute;
- transmission principle;
- appropriateness;
- distribution norms.

Determine whether this framework is useful for an AI assistant deciding whether to transfer contextual information to:
- a local model;
- a cloud model;
- a third-party tool;
- another AI agent.

Do not present Contextual Integrity as the only valid privacy theory.

Compare it with other important approaches where appropriate.

Identify:
- strengths;
- limitations;
- contested points;
- operationalization difficulties.

---

# 5. CURRENT PRIVACY ENGINEERING

Research authoritative privacy-engineering frameworks, prioritizing:

- NIST Privacy Framework;
- NIST Privacy Framework 1.1 material, clearly distinguishing draft/IPD status from final standards;
- NIST privacy engineering guidance;
- NIST AI Risk Management Framework and relevant privacy/trustworthiness material;
- relevant ISO/IEC privacy and information-security standards where publicly verifiable;
- other high-authority technical frameworks if directly relevant.

Focus on:

- privacy risk;
- data processing ecosystem;
- requirements;
- profiles;
- governance;
- controls;
- verification;
- third-party/service-provider data flows;
- minimization;
- accountability;
- risk assessment.

Do not confuse voluntary frameworks with legal obligations.

---

# 6. AGENTIC AI / LLM-SPECIFIC PRIVACY

Research current scientific literature, especially 2025–2026 work, concerning:

- privacy leakage in LLM agents;
- tool-use agents;
- multi-agent systems;
- context leakage;
- runtime-generated disclosures;
- tool/API argument disclosure;
- agent memory leakage;
- prompt/context exfiltration;
- contextual integrity in LLMs;
- over-disclosure;
- data minimization for agents;
- privacy attacks;
- privacy-preserving agent architectures;
- policy enforcement at runtime.

Prioritize peer-reviewed papers, conference papers, authoritative technical reports and primary research.

For each major claim:

SOURCE
YEAR
VENUE
TYPE OF EVIDENCE
WHAT WAS ACTUALLY SHOWN
LIMITATIONS

Do not convert a demonstrated vulnerability in one system into a universal claim about all agents.

---

# 7. CURRENT IABV CASE — CONCEPTUAL MAPPING ONLY

Use the following categories as a case study, NOT as predetermined policy classes.

### A. Identity / account

Possible examples:
- email;
- browser/profile identity;
- account identifiers.

### B. Browser / session

Possible examples:
- profile;
- domain;
- session metadata;
- cookie COUNT;
- browser state metadata.

Important:
cookie values are not part of the observed OSES context construction described by the current audit.

### C. Local environment

Possible examples:
- filesystem paths;
- process names;
- PID;
- window titles;
- executable paths;
- runtime/environment metadata.

### D. Tools / capabilities

Possible examples:
- tool identifiers;
- availability;
- launch/capture mode;
- web URL;
- capabilities.

### E. Providers / infrastructure

Possible examples:
- model availability;
- installed model names;
- quota;
- worker state;
- provider availability.

### F. Operational / reasoning context

Possible examples:
- diagnostic category;
- finding title;
- summary;
- free-form operational text;
- contextual reasoning information.

For each category research:

1. whether it can be personal data;
2. whether it can be sensitive;
3. whether sensitivity is intrinsic or contextual;
4. whether it can reveal protected/private facts indirectly;
5. whether the relevant risk is privacy, security, confidentiality, operational security, or multiple dimensions;
6. what transformations can reduce the risk;
7. what information utility may be lost by each transformation;
8. whether recipient/context changes the assessment.

Do not decide the IABV policy.

---

# 8. IMPORTANT QUESTION: IS METADATA REALLY “LESS SENSITIVE”?

Research whether metadata such as:

- domain;
- browser profile;
- process;
- PID;
- window title;
- local path;
- installed model;
- quota;
- tool availability;

can reveal sensitive information even when it is not a conventional content field.

Include empirical evidence where available.

Do not assume:
“metadata = harmless”

and do not assume:
“metadata = sensitive”.

Determine what the evidence supports.

---

# 9. INFORMATION-FLOW ANALYSIS

Research whether contemporary privacy/security engineering supports evaluating policy at the level of:

DATA ITEM
→ REQUEST
→ RECIPIENT
→ PURPOSE
→ TRANSMISSION PRINCIPLE
→ EFFECTIVE DESTINATION.

Determine whether request-level analysis is sufficient or whether policy often needs:

- field-level classification;
- context-level classification;
- recipient-level classification;
- purpose-level classification;
- combined risk scoring.

Do not introduce scoring unless the literature supports the concept.

---

# 10. POLICY GRANULARITY

Research the tradeoffs between:

### Field-level policy
Classify each field separately.

### Context-level policy
Classify an entire context bundle.

### Request-level policy
Evaluate the complete inference request.

### Recipient-level policy
Rules depend on who receives it.

### Purpose-level policy
Rules depend on why it is transferred.

### Risk-based policy
Rules depend on estimated privacy/security impact.

### Hybrid policy
Combine the above.

Determine what the literature recommends or supports, and under which assumptions.

---

# 11. TRANSFORMATION ANALYSIS

Research what can realistically be achieved using:

- removal;
- redaction;
- masking;
- truncation;
- aggregation;
- generalization;
- pseudonymization;
- de-identification;
- tokenization;
- local summarization;
- semantic filtering.

For each:

WHAT RISK IT REDUCES
WHAT RISK REMAINS
WHAT UTILITY IS LOST
WHETHER REVERSIBILITY EXISTS
WHETHER CONTEXT CAN RE-IDENTIFY THE SUBJECT
WHETHER IT IS SUITABLE FOR AI CONTEXT

Do not use “anonymized” loosely.

---

# 12. AUTHORIZATION MODEL

Research the distinction among:

- user intent;
- user consent;
- account authentication;
- technical access permission;
- authorization to process;
- authorization to transmit;
- authorization for a particular recipient;
- authorization for a particular purpose;
- authorization for persistent storage.

Determine which distinctions are recognized in current technical/security/privacy practice.

This directly informs the IABV invariant:

authentication ≠ authorization
access ≠ transmission permission
provider availability ≠ policy permission.

---

# 13. UNKNOWN / UNCLASSIFIED DATA

Research how mature privacy/security systems handle information that cannot be confidently classified.

Compare:

- allow;
- deny;
- local-only;
- quarantine;
- require authorization;
- transform first;
- human escalation.

Do not choose the policy.

Identify conditions under which each strategy is defensible.

---

# 14. FAIL-OPEN / FAIL-CLOSED

Research the relation between privacy policy and fail-open/fail-closed behavior.

Especially consider:

- remote inference unavailable;
- local inference unavailable;
- classification unavailable;
- redaction fails;
- authorization state unavailable;
- recipient identity uncertain;
- policy version stale.

Determine which failure strategy protects which property.

Do not produce a universal recommendation.

---

# 15. PURPOSE OF LOCAL INFERENCE

Research a subtle issue:

Is local inference itself a privacy guarantee, or merely one risk-reduction measure?

Consider:

- local endpoint compromise;
- localhost service replacing the endpoint;
- local API redirection;
- remote base URL configuration;
- logging;
- model telemetry;
- plugins;
- tool outputs;
- shared files;
- process isolation.

This is important because IABV currently treats “local” as an intended realization but must not falsely promote it to a guarantee without an integrity contract.

---

# 16. HUMAN DECISION MODEL

After the scientific review, create a neutral decision framework for the human.

The human should eventually be able to answer:

### PURPOSE
What is OSES trying to accomplish?

### RECIPIENT
Who/what is allowed to receive the context?

### DATA TYPES
Which context categories may flow?

### NECESSITY
Which parts are actually needed?

### TRANSFORMATION
What must be removed/generalized/redacted?

### AUTHORIZATION
When is explicit authorization required?

### DEFAULT
What happens when classification is uncertain?

### FAILURE
What happens when no realization satisfies policy?

### LOCALITY
What guarantees are required before “local-only” is considered meaningful?

### RETENTION
What happens to the request/result afterward?

The research must explain these concepts without selecting the final values.

---

# 17. SCIENTIFIC CONSENSUS VS NORMATIVE CHOICE

This distinction is mandatory.

For every major conclusion classify it as one of:

- WELL-ESTABLISHED SCIENTIFIC / ENGINEERING PRINCIPLE
- STRONG EMPIRICAL EVIDENCE
- ACTIVE RESEARCH AREA
- THEORETICAL FRAMEWORK
- CONTEXT-DEPENDENT PRACTICE
- NORMATIVE / ORGANIZATIONAL DECISION
- LEGAL/REGULATORY REQUIREMENT
- CONTESTED / UNCERTAIN

Do not present a normative choice as scientific fact.

---

# 18. COMPETING FRAMEWORKS

Where the literature contains real disagreement, compare the relevant approaches.

For example:

- rights/control-oriented privacy;
- contextual integrity;
- risk-based privacy engineering;
- information-flow control;
- data minimization;
- purpose limitation;
- least privilege;
- consent/authorization;
- privacy-enhancing technologies.

Explain where they converge and where they differ.

Do not force consensus where none exists.

---

# 19. EVIDENCE QUALITY

For every substantive claim record:

- primary source;
- publication date;
- venue;
- evidence type;
- population/system studied;
- experimental limitations;
- whether the finding is generalizable;
- whether later literature confirms or challenges it.

Prefer primary scientific literature over blogs, vendor claims and opinion pieces.

Use standards separately from empirical science.

---

# 20. REQUIRED OUTPUT

Return exactly:

## A. EXECUTIVE SCIENTIFIC SYNTHESIS

## B. DEFINITIONS
Precise definitions of privacy, personal data, sensitive data, security, confidentiality, authorization, authentication, minimization, purpose limitation, least privilege, redaction, pseudonymization, anonymization, local-only and cloud-permitted.

## C. PRIVACY THEORIES

## D. CONTEXTUAL INTEGRITY

## E. PRIVACY ENGINEERING FRAMEWORKS

## F. AGENTIC-AI / LLM PRIVACY EVIDENCE

## G. INFORMATION-FLOW MODEL

## H. DATA / METADATA SENSITIVITY FINDINGS

## I. TRANSFORMATION METHODS

## J. AUTHORIZATION MODEL

## K. UNKNOWN / FAIL-SAFE HANDLING

## L. LOCALITY / LOCAL INFERENCE ANALYSIS

## M. POLICY GRANULARITY

## N. NEUTRAL HUMAN DECISION FRAMEWORK

## O. SCIENTIFIC CONSENSUS / UNCERTAINTIES

## P. COMPETING INTERPRETATIONS

## Q. IABV CASE MAPPING

Map categories A–F to the researched concepts, but do not decide the final IABV policy.

## R. PROPOSED POLICY VOCABULARY

Give a terminology set suitable for later IABV engineering, but clearly label which terms are standard and which are IABV operational terms.

## S. EVIDENCE TABLE

For the key conclusions, give:

CLAIM
SOURCE
YEAR
EVIDENCE TYPE
STRENGTH
LIMITATION

## T. OPEN SCIENTIFIC QUESTIONS

## U. HUMAN DECISION CHECKLIST

A neutral checklist only.

## V. SOURCES

Prioritize:
- primary academic literature;
- NIST;
- ISO/IEC public material where available;
- authoritative standards;
- major peer-reviewed/archival research venues.

---

# 21. STRICT ANTI-DRIFT RULES

Do not:

- inspect IABV code;
- audit Codex or Sonnet;
- design an IABV privacy manager;
- propose a new IABV service;
- choose the human's policy;
- rank policy options;
- claim one policy is universally best;
- use one legal framework as universal scientific truth;
- call metadata harmless merely because it lacks obvious PII;
- call metadata sensitive merely by assumption;
- equate authentication with authorization;
- equate authorization to access with authorization to transmit;
- equate local execution with guaranteed privacy;
- treat a privacy framework as a scientific proof;
- treat a single 2025/2026 paper as settled consensus;
- claim that a contextual-integrity violation has occurred in IABV;
- claim that IABV has transmitted sensitive data;
- claim an actual security incident;
- make consciousness/superconsciousness claims.

---

# 22. REQUIRED RESEARCH QUESTION AT THE END

Finish by answering this exact question:

“Which conceptual distinctions must the human fix before IABV can safely define a request-level policy for OSES, and which of those distinctions are scientific/technical facts versus human normative choices?”

Then answer:

“What information must be known about a request, recipient, purpose, context and authorization before the system can defensibly choose local-only, cloud-permitted, transformation-required, authorization-required, or deny-on-unknown behavior?”

Do not choose the values.

---

# 23. RESEARCH ACCEPTANCE GATE

The research is acceptable only if:

1. major concepts are defined independently of IABV;
2. empirical findings are separated from theory;
3. standards are separated from legal requirements;
4. agentic-AI privacy evidence is current through 2026-10-03;
5. metadata risks are addressed;
6. local-versus-remote semantics are addressed;
7. authorization is separated from authentication;
8. minimization and contextual integrity are addressed;
9. transformations and their residual risks are addressed;
10. uncertainty/fail-safe behavior is addressed;
11. the human decision boundary is explicit;
12. the result gives enough conceptual precision to formulate the IABV policy without guessing.

If an important claim cannot be verified, mark it NOT ESTABLISHED rather than filling the gap with intuition.

END RESEARCH CONTRACT