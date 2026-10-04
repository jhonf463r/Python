# CHAT-ARCH-2026-10-03-039 — IABV as Laptop Cognitive Operating Layer

## 1. CANONICAL DESIGN INTENT
IABV is intended to function as the **cognitive/operational mind of the user's laptop**: one continuously contextualized intelligence layer that can perceive, understand, reason about and act through the laptop's heterogeneous environment, using whatever realization best satisfies the user's objective under current resource, access, visibility, authentication, authorization and timing constraints.

This is a design/research target, not a claim of consciousness or present general intelligence.

## 2. WHAT 'THE LAPTOP AS ONE ENVIRONMENT' MEANS
The physical laptop remains heterogeneous, but IABV should model it as one connected operational reality containing:
- operating system, processes, memory/CPU/GPU/disk/network and permissions;
- windows, desktop and UI controls;
- installed desktop applications;
- browsers, browser profiles and the user's actual browser sessions;
- isolated browser sessions when safer or more suitable;
- filesystem and local runtime;
- local models/providers such as Ollama;
- external AIs (Codex, ChatGPT, Claude, etc.) as cognitive resources;
- APIs, CLI, MCP and other access channels;
- accounts, identities, sessions, credentials, quotas and authorization state;
- historical/current/pending task context and time ordering.

These are not separate brains. They are heterogeneous channels/realizations inside one environmental model.

## 3. PERCEPTION TARGET
IABV should progressively be able to 'see what the user can see and more' through multiple observation layers, depending on availability:
`screen/UI pixels → accessibility/UI semantics → window/process state → browser DOM/accessibility → filesystem/runtime → account/session/resource state → historical/provenance state`.

No single observer is assumed to be universal. A missing DOM for a desktop application does not mean the application is invisible; it means IABV should select another observation layer such as UI Automation, screenshot/vision, process/window state or a different controlled realization.

## 4. ACTION TARGET
Likewise, IABV should be able to act at multiple levels:
`semantic action → browser/API/CLI/MCP/desktop-app realization → foreground/background modality → governed execution → post-action observation`.

Examples include:
- browser navigation or DOM interaction;
- CDP reuse of the human's live browser session;
- isolated browser session;
- desktop application launch/focus/click/type/wait;
- local shell or filesystem action;
- local model inference;
- external AI via installed app;
- external AI via browser/web session;
- MCP tool calls;
- API where a free/existing credential is already available.

The system should not assume the lowest-level mechanism is always best. It should choose the smallest reliable route that satisfies the objective and preserves governance/evidence.

## 5. FOREGROUND / BACKGROUND SEMANTICS
Foreground vs background is a **realization constraint**, not a universal algorithm.
Some actions or applications may require visible foreground interaction; others can be headless/background or API-based. Therefore the desired policy is:
`required capability + current environment constraints → feasible modalities → lowest-friction governed realization → execute → observe`.

If background is unavailable, IABV should consider a foreground UI route, browser route, alternate installed application, local provider, API/session, waiting for the environment, or human intervention according to evidence.

The existence of `background_capture_mode`, `launch_mode`, `isolated_session_required`, `use_browser_session` and similar fields is not sufficient proof that this adaptive modality selection is causally active.

## 6. EXTERNAL AIs AS COGNITIVE OR EXECUTIONAL RESOURCES
ChatGPT, Codex, Claude, Devin and Ollama are not fixed stages in a pipeline.
They are resources that can provide different capabilities:
- reasoning/synthesis;
- repository archaeology;
- implementation;
- adversarial verification;
- runtime execution;
- research;
- browser interaction;
- local inference.

An objective should determine the required capability first. IABV should then compare available realizations/accounts/sessions/resources.

Current code already contains ToolCards for `codex_installed`, `chatgpt_installed`, `chatgpt_web_assisted`, `claude_installed`, `claude_web_assisted`, `ollama_llm`, `desktop_human_runner`, `playwright_browser`, `shell_command` and `mcp_client`. This is important substrate, but not proof of universal adaptive selection.

## 7. HUMAN BROWSER / WEB AI PRINCIPLE
The user's human browser/session is a legitimate environmental resource when governed access exists.
Existing source includes shared-CDP behavior and can prefer reuse of a live user browser session rather than always creating an isolated session. Existing web-assisted cards also model background/headless browser capture.

Therefore using a browser to access ChatGPT/Claude/etc. is not a conceptual workaround. It is a legitimate channel realization when an API is unavailable, undesirable or not needed.

## 8. FREE-FIRST / NO-BUDGET CONSTRAINT
Current operating constraint remains:
**FREE-FIRST / NO NEW PAID API KEYS OR SUBSCRIPTIONS** unless the user explicitly changes it.

Preferred realization order:
`existing local → installed app → existing human/browser session → free web capability → local model/provider → free account/resource route → paid only if explicitly authorized later`.

The system should account for free-tier quotas, resource pressure, authentication and session state rather than assuming infinite external AI access.

## 9. CARTESIAN / 'MATRIX' INTERPRETATION
The user's 'Cartesian/code Matrix' idea is best translated operationally as a **multi-dimensional environmental state space**, not a literal scientific matrix.

Useful dimensions are:
`object/entity | location/scope | time/freshness | state | relation | capability | access channel | visibility | foreground/background feasibility | authentication | authorization | resource/quota | provenance | task/goal relevance`.

An environmental observation becomes useful when IABV can locate it in this state space, relate it to other observations, estimate what it enables, and use it to choose an action.

## 10. UNIVERSAL REASONING LOOP
`objective → environment perception → semantic interpretation → uncertainty → required capability → candidate realizations/channels → prerequisites/constraints → governed selection → action → observation → verification → updated environmental state → next decision`.

This is the operational meaning of IABV as the laptop's cognitive layer.

## 11. CURRENT ARCHITECTURAL SUBSTRATE
Existing owners already map surprisingly well to this target:
- perception: UniversalPerceptionService, browser/session scanners, desktop observation, account/resource scanning;
- world/self state: WorldModelService, EnvironmentSelfAwarenessService, EnvironmentSelfModel;
- interpretation/discernment: DiscernmentFrameService, CommonSenseEngine, OSES;
- capability/selection: ToolRegistry, ToolCard, CapabilityReadinessService, ToolDiscoveryService, InteractionModeSelector, SynapticRouter;
- action: UIExecutionRunner, ToolOperationalExecutor, ToolTeachService, adapters, browser/CDP, shell, local providers;
- governance/authority: AutonomyGovernancePolicy, ExternalActionAuthorization and related controls;
- memory/context: PortableContext, TaskContextAssembler, claims/evidence, CHAT-ARCH;
- learning/development: ExperimentLab, TaskOutcomeRecorder, AdaptiveWeightLayer, AutonomousEvolutionService.

The project already contains much of the substrate. The main unanswered question is composition: whether current observations, capability evidence, modality constraints and external resources actually converge into one objective-driven decision/action loop.

## 12. CURRENT FIRST OPEN CAUSAL EDGE
Do NOT currently treat the narrow `MCP → Codex` connection as the global frontier.
The broader first open edge is:
`fresh laptop/environment evidence → generic capability/affordance understanding → realization/modality selection → governed action → post-action observation`.

The MCP/Codex connection is one concrete test case under this universal substrate.

## 13. DEVELOPMENTAL INFLECTION
The meaningful inflection is not 'IABV can call Codex' and not faster coding.
It is:
`IABV perceives new reality → understands it → selects an appropriate realization → acts → verifies → retains reusable knowledge → later selects better actions with less routine human coordination.`

Repeated cross-realization evidence would support an accelerating development regime:
`verified experience → reusable capability → easier next objective → more evidence → more capability`.

Do not call this exponential until longitudinal evidence supports the claim.

## 14. REQUIRED RESEARCH/ENGINEERING QUESTION
Can the existing IABV organs be composed so that a new objective can be satisfied by navigating the actual laptop environment itself, without first requiring a provider-specific recipe or manually naming the correct tool/app/browser/AI?

This is broader than external-agent delegation and closer to the actual laptop-native objective.

## 15. NON-IMPLEMENTATION RULE
Do not create a universal brain, giant ontology, parallel memory, universal router or provider-specific manager.
First prove which existing composition edge is missing.

## 16. CONTINUITY DELTA
The active design correction for future chats is:
`IABV ↔ Codex` is a **test realization**, not the product objective.
`MCP` is a **channel**, not the product objective.
`ChatGPT/Claude/Codex/Ollama` are **resources**, not fixed pipeline stages.
`browser/desktop/API/CLI/MCP` are **access channels/realizations**, not separate cognitive systems.
`the laptop environment` is the operational reality IABV is intended to understand and navigate.

Future prompts must preserve this hierarchy.

## 17. STATUS
Design intent: **CONFIRMED** from accumulated project direction.
Universal semantic environment understanding: **NOT PROVEN**.
Universal modality selection: **NOT PROVEN**.
General laptop action/observation continuity: **NOT PROVEN**.
Cross-realization causal learning: **NOT PROVEN**.
Consciousness/general intelligence: **NOT CLAIMED**.