# CHAT-ARCH-2026-10-03-014 — BIO-04 STAGE-A M2 PRIMARY-SOURCE RESEARCH PASS

## EXECUTION RECEIPT
- PLANNED_EXECUTION_ID: `BROWSE_2026-10-03_BIO-04-A-M2_001`
- ACTUAL_EXECUTION_ID: `BROWSE_EQUIV_2026-10-03_BIO-04-A-M2_001`
- OBJECT_ID: `BIO-04-STAGE-A-M2-AGENTIC-AI-RUNTIME-DATA-DISCLOSURE`
- RESEARCH_PHASE: `BIO-04-STAGE-A-M2`
- DATE BOUNDARY: through 2026-10-03
- TASK TYPE: `RESEARCH — NOT DIAGNOSTIC`

PROVENANCE: The planned Deep Research surface was not invoked. A bounded equivalent primary-source research pass was performed in this chat using current web retrieval. The planned execution remains NOT EXECUTED; this equivalent execution is separately identified.

REQUESTED CONTRACT → ACTUAL SUBMITTED REQUEST → EXECUTION INSTANCE → RETURNED RESULT

`BIO-04-STAGE-A-M2-AGENTIC-AI-RUNTIME-DATA-DISCLOSURE-2026-10-03.md` → bounded primary-source searches matching its required coverage → `BROWSE_EQUIV_2026-10-03_BIO-04-A-M2_001` → this record.

## DIRECT SCIENTIFIC ANSWER

Contemporary LLM/agent systems have multiple privacy-relevant disclosure boundaries. Empirical work demonstrates leakage through task execution, tool surfaces, persistent memory, inter-agent messages, reasoning traces and metadata; official protocol/provider documentation establishes additional transport, state, authorization, trace and retention paths.

Core conclusion:
`final output safety != system privacy safety`

and:
`host availability != model-context inclusion != tool exposure != external transmission != retention/logging != downstream inference`.

Empirical results remain benchmark-, model-, framework-, task- and configuration-dependent; they are not universal prevalence estimates.

## 1. MODEL-CONTEXT DISCLOSURE

AgentDAM demonstrates end-to-end inference-time leakage of task-irrelevant sensitive information in benign, isolated web-agent tasks and shows that asking a model about privacy can overestimate actual trajectory privacy. Its privacy-aware system prompting reduced leakage in the tested setting. citeturn521406view0

Leaky Thoughts (EMNLP 2025) shows that reasoning traces can contain sensitive user data, can leak via prompt injection or accidental output, and that more test-time reasoning can amplify leakage in tested personal-agent settings. This does not prove every provider exposes reasoning traces. citeturn312986view4

## 2. TOOL / FUNCTION / MCP / AGENT

AgentDojo empirically demonstrates that untrusted tool-returned content can hijack tool-using agents; it evaluated 97 realistic tasks and 629 security test cases and measured defense/utility tradeoffs. citeturn311034academia20turn311034search8

A 2025 study integrated data-exfiltration attacks into AgentDojo and reports that prompt injection can cause tool-calling agents to disclose personal data observed during execution. citeturn797914academia37

A 2026 large-scale preprint analyzed 17,022 agent skills, found 520 vulnerable skills and 1,708 issues, and reported multiple accidental/adversarial leakage patterns including a large debug-logging component. Treat as preprint evidence for the studied corpus, not as ecosystem-wide prevalence. citeturn565344academia35

MCP is a protocol realization, not a universal architecture. The current MCP specification separates prompts, resources and tools; resources are application-controlled context and tools are model-controlled executable functions. The 2026-07-28 release also adds stateless transport, explicit metadata, routable headers and authorization hardening. citeturn728507search0turn946795search0

Preserve:
`protocol capability != implementation != deployed configuration != observed runtime behavior`.

## 3. MEMORY / SESSION / STATE

ACL 2025 research on MEXTRA demonstrates black-box extraction of private information from representative agent-memory systems. This establishes a tested path `retention → retrieval → disclosure`, not a universal memory vulnerability. citeturn472088search1

Preserve:
`retention != exposure != retrieval != disclosure != secondary use`.

MCP 2026-07-28 further shows that transport can be stateless while an application can carry explicit state/task handles, so session is not one universal privacy primitive. citeturn312986view6turn294071search4

## 4. LOGGING / TRACE / TELEMETRY

AgentLeak instruments output, tool, inter-agent, shared-memory, telemetry/log and artifact channels and reports privacy violations invisible to final-output-only inspection. Its published study reports 68.8% inter-agent leakage versus 27.2% final-output leakage in its evaluated coordinator-worker setting, with 41.7% of 4,979 traces showing clean final output but internal violations. citeturn690590search0turn312986view2

The 2026 skill-corpus study reports debug logging as the primary vector in its own analyzed corpus and attributes 73.5% of observed leaks to print/console.log paths. This remains preprint/ecosystem-specific evidence. citeturn565344academia35

MCP's 2026 documentation also defines W3C Trace Context propagation through MCP metadata, allowing a host-to-tool-to-downstream span tree. This is mechanism evidence for metadata propagation, not proof of sensitive payload leakage. citeturn294071search1

## 5. EXTERNAL PROVIDER / CLOUD

OpenAI's current API data controls document that API inputs/outputs are not used for training by default, while abuse-monitoring logs can contain customer content and derived metadata; retention/application-state behavior varies by endpoint, and third-party/MCP services have their own retention policies. citeturn312986view5

Anthropic's current commercial documentation states a standard 30-day deletion period for API inputs/outputs, with stated exceptions/alternative arrangements, while products that persist conversations have different behavior. citeturn521406view6

Therefore provider handling is product/endpoint specific:
`provider transmission → provider-specific retention/processing regime`.

## 6. DIRECT / PROPAGATED / TRANSFORMED / INFERRED

Direct: demonstrated by AgentDAM task-time leakage and MEXTRA memory extraction. citeturn521406view0turn472088search1

Propagated: demonstrated through inter-agent messages/shared memory and tool-mediated chains; AgentLeak directly measures internal channels. citeturn690590search0

Transformed: AgentLeak reports an internal masking/redaction interceptor reducing internal leakage from 31.5% to 2.4% in a 120-scenario test; strict privacy settings also created utility tradeoffs. This is bounded control evidence, not a universal transformation guarantee. citeturn690590search1

Inferred/composed: AgentPrint reports that encrypted traffic patterns can reveal agent activity and infer user attributes in tested simulated and real-user settings, including 0.866 F1 agent identification and top-3 user-attribute inference of 73.9% simulated / 69.1% real-user. citeturn728507academia60

## 7. METADATA / LINKAGE / COMPOSITION

Metadata is not intrinsically harmless or intrinsically sensitive. Privacy risk may arise through timing, identifiers, traffic patterns, repetition, auxiliary information, linkage or composition. AgentPrint is direct empirical evidence for this class under tested conditions. citeturn728507academia60

## 8. CONTROLS AND EVIDENCE

Empirical support exists in named evaluations for privacy-aware prompting (AgentDAM), tool filtering / prompt-injection detection (AgentDojo), internal-channel redaction (AgentLeak) and information-theoretic defenses in a simulated multi-agent study. citeturn521406view0turn311034search21turn690590search1turn565344search0

AgentDojo also shows that a defense can reduce attack success while reducing utility or creating false positives; therefore security and utility must be measured together. citeturn311034search21

Not established as universal controls: generic pseudonymization, generalized de-identification, universal memory isolation, universal provenance enforcement, universal differential privacy for runtime context, or local processing as a sufficient privacy guarantee.

## 9. AUTHORIZATION / PURPOSE / NECESSITY

AgentDAM gives a concrete end-to-end way to compare task-required versus task-irrelevant sensitive information. MCP provides technical authorization mechanisms, but those mechanisms do not themselves decide whether a given data field was necessary for a particular purpose. citeturn521406view0turn946795search0

Preserve:
`authentication != authorization`
`access authorization != transmission authorization`
`authorized recipient != necessary data set`.

No IABV policy is chosen here.

## 10. LOCAL VS REMOTE

The evidence does not support locality as an intrinsic privacy guarantee. Local processes/stdio and remote HTTP/provider paths can coexist in a single causal flow; downstream calls, logs and retention must be traced before claiming a local boundary. MCP documentation distinguishes transport realizations but does not transform locality into privacy authorization. citeturn294071search2turn946795search0

Thus:
`local execution != proven local data boundary`.

## 11. DISCLOSURE-BOUNDARY TAXONOMY

`B0 HOST AVAILABILITY`
`B1 MODEL CONTEXT`
`B2 TOOL / FUNCTION`
`B3 INTER-AGENT`
`B4 EXTERNAL PROVIDER`
`B5 OBSERVABILITY`
`B6 RETENTION / PERSISTENCE`
`B7 TRANSFORMED`
`B8 INFERRED / COMPOSED`

These are analytical categories, not a claim that every architecture implements all of them.

## 12. COMPARATIVE EVIDENCE MATRIX

| Mechanism | Boundary | Exposure | Type | Evidence | Strength | Main limitation |
|---|---|---|---|---|---|---|
| Task-irrelevant private-data use | B1/B2 | sensitive fields | Direct | AgentDAM | High in benchmark | isolated simulated environments |
| Tool-result prompt injection | B2 | agent-accessible context | Propagated | AgentDojo | High | benchmark/model dependent |
| Memory extraction | B6→B1/output | stored interactions | Direct | MEXTRA | High | representative systems |
| Reasoning-trace leakage | B1/internal→output | sensitive user data | Direct/propagated | EMNLP 2025 | High | provider exposure varies |
| Inter-agent leakage | B3 | task context | Propagated | AgentLeak | High in tested topology | topology/model dependent |
| Debug/log leakage | B5 | credentials/context | Propagated | 2026 skill study | Medium-high | preprint/ecosystem specific |
| Traffic fingerprinting | B5 metadata | activity/user attributes | Inferred | AgentPrint | Medium | tested traffic conditions |
| Provider retention/state | B4/B6 | content/metadata/state | Retained | official docs | High for stated products | product specific |
| MCP trace propagation | B3/B5 | trace metadata | Propagated | official protocol | High for protocol semantics | not privacy-outcome evidence |
| Internal redaction interceptor | B3/B6 | sensitive fields | Transformed | AgentLeak | Medium-high | bounded benchmark + utility tradeoff |

## 13. CONTROL EVIDENCE MATRIX

| Control | Evidence | Result | Limitation |
|---|---|---|---|
| Privacy-aware prompting | AgentDAM empirical | reduced leakage in tested setting | not architectural enforcement |
| Tool-output filtering | AgentDojo empirical | reduced attack success | false positives / utility tradeoff |
| Prompt-injection detector | AgentDojo empirical | reduced attack success | task completion can suffer |
| Internal-channel redaction | AgentLeak empirical | 31.5%→2.4% internal leakage | 120-scenario bounded test |
| MI/BIG/RDP-style defense | IEEE BigData empirical/formal | leakage/ASR reductions in simulation | configuration specific |
| Dynamic memory ACL/provenance | formal/proposed | policy adherence claimed | not broad deployment evidence |

## 14. STRONGEST EMPIRICAL FINDINGS

1. Privacy leakage can occur during benign agent execution without attackers.
2. Tool-returned untrusted content can induce harmful agent behavior and data exfiltration.
3. Persistent memory is an empirically demonstrated extraction surface.
4. Reasoning traces can contain and leak sensitive user data.
5. Multi-agent internal channels can reveal violations missed by final-output inspection.
6. Encrypted traffic metadata can support privacy inference in tested conditions.
7. Provider retention/state is endpoint/product specific.

## 15. STRONGEST FORMAL / THEORETICAL RESULTS

MI, Bayesian inference gain and RDP provide distinct formal views of privacy leakage; provenance-bearing memory and dynamic policy can also be formally modeled. These do not prove universal runtime enforcement. citeturn565344search0turn728507academia59

## 16. COUNTEREVIDENCE / COMPETING EXPLANATIONS

- benchmark result != production prevalence;
- framework capability != deployed configuration;
- host access != model-context inclusion;
- model context != external transmission;
- provider documentation != independent packet-level observation;
- lower ASR can reflect task abortion/utility loss;
- reasoning-trace leakage != proof of provider exposure;
- memory extraction in one architecture != universal memory vulnerability;
- direct disclosure != inference;
- metadata risk is context-dependent;
- encryption/authentication do not establish contextual appropriateness or purpose compatibility.

## 17. EVIDENCE GAPS

Universal necessity criteria; generalized redaction/de-identification efficacy; runtime purpose/consent semantics; production-wide prevalence; standardized memory isolation; architecture-independent local-vs-remote semantics; compositional privacy guarantees across tools/memory/agents; and robust causal metrics separating direct/propagated/transformed/inferred leakage.

## 18. UNRESOLVED SCIENTIFIC QUESTIONS

1. How can necessary context be established without trusting the agent's own judgment?
2. How can runtime observability be increased without becoming a new privacy channel?
3. How do privacy guarantees compose across repeated tool/memory/inter-agent interactions?
4. How can legitimate multi-agent coordination coexist with selective disclosure?
5. When does transformation remain non-reconstructive under realistic auxiliary information?
6. What should UNKNOWN mean when purpose, recipient, provider behavior or necessity is unverified?
7. What establishes a true local-processing boundary?
8. How should inferred sensitive facts be governed when raw data never crosses the boundary?

## 19. PRINCIPAL PRIMARY SOURCES

- AgentDAM, 2025: end-to-end inference-time data minimization and trajectory-based leakage. citeturn521406view0
- AgentDojo, NeurIPS 2024: tool-output prompt injection and defense/utility evaluation. citeturn311034academia20turn311034search8
- Unveiling Privacy Risks in LLM Agent Memory, ACL 2025: memory extraction. citeturn472088search1
- Leaky Thoughts, EMNLP 2025: reasoning-trace privacy leakage. citeturn312986view4
- AgentLeak, IEEE Access 2026, DOI 10.1109/ACCESS.2026.3704541: internal-channel leakage and output-only audit gap. citeturn690590search0turn690590search1
- Quantifying Privacy Leakage in Multi-Agent LLMs, IEEE BigData 2025, DOI 10.1109/BigData66926.2025.11401523. citeturn565344search0
- Model Context Protocol 2026-07-28 official specification. citeturn728507search0turn946795search0
- OpenAI API Data Controls, current official documentation. citeturn312986view5
- Anthropic commercial retention documentation, current official documentation. citeturn521406view6

## 20. STAGE-A M2 KNOWLEDGE DELTA

1. Agentic privacy is a multi-channel causal data-flow problem, not an output-only problem.
2. End-to-end agent evaluation can reveal privacy behavior that model-only privacy questioning underestimates.
3. Tool, memory, inter-agent, reasoning, telemetry and provider paths are separate disclosure surfaces.
4. Direct, propagated, transformed and inferred/composed disclosure must remain distinct.
5. Metadata can be privacy-relevant even when payloads are encrypted.
6. Provider retention/state is product/endpoint specific.
7. Selective disclosure, tool/context filtering and internal-channel interception have bounded empirical support, not universal guarantees.
8. Defensible request-level policy requires full-path observability, not merely host-side data availability.

## 21. FINAL EPISTEMIC BOUNDARY

EMPIRICALLY ESTABLISHED: named benchmark findings for task-time leakage, tool-mediated attacks, memory extraction, reasoning-trace leakage, inter-agent leakage and metadata inference.

FORMAL / THEORETICAL: information-theoretic leakage measures, formal memory/provenance policies and compositional analyses.

STANDARD / OFFICIAL: MCP protocol semantics; provider-specific retention/state declarations; NIST agent-security framing. citeturn728507search7turn728507search8

ENGINEERING PRACTICE: filtering, redaction, allowlisting, memory partitioning, local processing and observability instrumentation.

RESEARCHER SYNTHESIS: B0–B8 taxonomy; full-path observability requirement; separation of purpose compatibility from necessity.

HYPOTHESIS: universal runtime selective-disclosure policy; adaptive trace-depth/privacy control.

NOT ESTABLISHED: production-wide prevalence, universal necessity semantics, universal transformation efficacy, universal local guarantees, universal memory isolation, universal compositional guarantees.

## 22. EXACT FINAL QUESTIONS — RESOLVED

1. Boundaries: model context; tool/function; MCP; inter-agent/shared state; memory/session; logs/traces/telemetry; providers; persistence; transformation; inference/composition.
2. Directly demonstrated: task-time unnecessary use, tool exfiltration under injection, memory extraction, reasoning-trace leakage, inter-agent leakage, metadata inference in named evaluations.
3. Primarily formal: privacy accounting, information-theoretic leakage measures, formal provenance/access control, general composition.
4. Empirically supported controls: privacy-aware prompting, tool/context filtering, injection detection, internal-channel redaction/interception, bounded information-theoretic defenses.
5. Not strongly generalized: generic pseudonymization/de-identification, universal memory isolation, universal provenance enforcement, universal runtime DP, local processing as sufficient guarantee.
6. Necessary vs over-disclosure: compare actual execution with a task-required information set and measure unnecessary sensitive use; AgentDAM is a concrete method. citeturn521406view0
7. Direct/propagated/transformed/inferred: trace provenance plus content/representation comparison and inferability testing.
8. Missing before policy: necessity model, purpose/authorization/recipient/locality semantics, full-path observability, UNKNOWN behavior, transformation guarantees, lifecycle/retention semantics.
9. Uncertain: prevalence, cross-framework generality, necessity thresholds, locality guarantees, inference thresholds, memory isolation.
10. Smallest delta: `agentic privacy must be analyzed as a multi-channel causal data-flow problem`.
11. Residual frontier, pending audit: `request-level necessity + authorization + UNKNOWN-state semantics + enforceable selective disclosure across heterogeneous agent channels`, with residual transformation/de-identification, locality/trust and lifecycle questions.

## 23. ANTI-DRIFT RESULT

No IABV code audit. No IABV policy selection. No provider behavior inferred beyond documentation. No benchmark promoted to universal prevalence. No consciousness claims.

## 24. CURRENT STATUS / ROUTING

M2 equivalent primary-source pass = `PARTIALLY SATISFIED / MATERIAL EVIDENCE ACQUIRED`.

The planned Deep Research execution remains unexecuted. The next required capability is independent source/claim verification.

NEXT ACTOR: `SONNET / CLAUDE-CLASS INDEPENDENT SOURCE-EVIDENCE VERIFIER`.

Audit focus: publication/provenance status; exact metrics and conditions; direct vs propagated vs transformed vs inferred classification; control efficacy and utility effects; generalization limits; and whether the residual frontier is truly the smallest open scientific edge.

No implementation actor is authorized from this result.

END OF RECORD