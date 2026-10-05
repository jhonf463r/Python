# CHAT-ARCH-2026-10-05-059 — IABV as Laptop Mind / Single User Interface / Agent Intermediary

**STATUS:** CANONICAL STRATEGIC RECONCILIATION / PRODUCT VISION / ROUTING

## PURPOSE

Consolidate the long-standing product vision with the recent UAAL-RQ01–RQ04 findings so future chats do not repeatedly reconstruct the same objective.

## NORTH-STAR PRODUCT VISION

The primary product is **IABV itself as the user's artificial assistant for the laptop**.

The desired user interaction model is:

`HUMAN ↔ IABV`

not:

`HUMAN ↔ ChatGPT ↔ Codex ↔ Claude ↔ IABV`.

External AIs, tools, browsers, MCP, APIs, local models and installed applications are intended to become resources/channels that **IABV can consult or operate when the objective requires them**.

The desired mature loop is:

`human objective → IABV perceives laptop/environment → IABV understands current context → IABV identifies uncertainty/required capability → IABV discovers candidate resources/channels → IABV checks access/authentication/authorization/quota/constraints → IABV selects the best realization → IABV delegates/acts → observes result → verifies → updates state/knowledge → continues or asks the human only where necessary`.

## THE LAPTOP AS ONE ENVIRONMENT

IABV should model one heterogeneous operational reality containing:

- OS, processes and resources;
- desktop/windows/UI controls;
- installed programs;
- browser profiles and live human browser sessions;
- isolated browser sessions;
- filesystem/local runtime;
- local models/providers;
- ChatGPT, Codex, Claude, Devin and other external AIs;
- APIs/CLI/MCP;
- accounts/identities/sessions;
- credentials and authorization state;
- network/resource/quota state;
- time/freshness/provenance;
- prior/current/pending task context.

These are not separate minds. They are channels, resources and state variables inside one environmental model.

## SINGLE-FRONT-END PRINCIPLE

The long-term user-facing architecture should make IABV the primary conversational control surface.

The human should not have to know:

- which AI should be called;
- whether a task belongs in ChatGPT or Codex;
- which browser/application/API should be used;
- which authentication modality is currently available;
- which tool or resource is technically best.

The human supplies the objective and constraints. IABV should progressively determine the realization.

This does **not** imply that IABV must hide all reasoning or deny the human visibility. It means the human should not need to act as the routine router/transport layer among tools.

## EXTERNAL AI DELEGATION PRINCIPLE

ChatGPT/Codex/Claude/Devin/other AIs are not a mandatory sequence and are not permanent departments.

They are capability-bearing resources.

Example:

`objective → uncertainty → required capability → candidate AI/resource set → evidence/history/access → actor fit → governed selection`

One objective may use no external AI.

Another may use ChatGPT for synthesis.

Another may use Codex for repository archaeology/implementation.

Another may use Sonnet/Claude for adversarial verification.

Another may use several resources in a dynamically chosen order.

The ordering must emerge from the current objective and evidence, not from a hard-coded ChatGPT→Codex→Claude pipeline.

## WHAT SHOULD BE TAUGHT FIRST

The project should not frame the next phase as “teach IABV Codex first” or “teach IABV ChatGPT first” as the primary architectural milestone.

The more fundamental capability order is:

### U0 — Local environmental agency

IABV can reliably observe and represent:

- laptop state;
- windows/apps/processes;
- resources;
- available channels;
- existing accounts/sessions/resources;
- permissions/authentication constraints.

### U1 — One governed external-resource realization

Choose **one** already available external-AI realization as a capability test and prove:

`IABV objective → capability need → resource selection → governed delegation → result capture → verification`.

The choice of AI must be based on the current capability/access experiment, not permanent priority.

### U2 — Dynamic multi-resource selection

Prove that the same objective class can route to different AIs/resources when the constraint or capability requirement changes.

This is where “IABV decides whether to consult ChatGPT, Codex, Claude, etc.” becomes an empirical capability rather than a design statement.

### U3 — Automatic round trip

Prove:

`human objective → IABV decision → external resource invocation → result return → IABV reconciliation`

without human copying the intermediate prompt/result.

This is the operational transition from externalized coordination toward runtime intermediary behavior.

### U4 — Account/session/resource handling

Only after U1/U2/U3 boundaries are understood should the project broaden account operations.

The preferred model is **governed reuse of already authenticated human/browser/application sessions** when appropriate, rather than teaching an AI plaintext passwords or copying secrets between AIs.

Credentials, tokens and authorization must remain governed resources. Possessing an email address, finding an account or seeing a logged-in page does not prove ownership, authorization or permission to act.

Required distinctions:

`email != identity != account != session != credential != authorization`

### U5 — General laptop assistant behavior

Prove repeated heterogeneous objectives such as:

- use a desktop application;
- inspect a file;
- research something through a browser;
- interact with a human browser session;
- use a local provider;
- consult an external AI;
- combine several resources;
- observe the result;
- continue until the objective is satisfied or a human decision is required.

The target is not maximum automation of one program. It is transferable environmental agency.

## SECURITY / AUTHORIZATION PRINCIPLE

IABV should not “learn login” as uncontrolled secret exposure.

The desired progression is:

`discover account/session/resource → determine authentication state → determine authorization → select permissible action channel → request human authorization when required → execute under governance → observe result`.

Do not place secrets into prompts to external AIs unless an explicit, separately governed mechanism requires it and the exposure boundary is understood.

A logged-in browser session can be an access realization; it is not blanket permission for all actions.

## CURRENT REALITY — HOW CLOSE ARE WE?

The project is closer to the **substrate** than to the mature autonomous intermediary.

Already evidenced in source/runtime work:

- laptop/environment modeled through WorldModel and EnvironmentSelfModel;
- multiple perception modalities exist;
- Windows UI Automation capability exists externally;
- ToolRegistry/ToolCard/resource-selection substrate exists;
- external-AI resources are represented;
- governance mechanisms exist;
- memory/context and evidence infrastructure exist;
- RQ02 proved a controlled perception-state difference can change governance.

Still not proven as the end-to-end mature product:

`human → IABV → choose AI/resource → invoke automatically → receive result → verify → update state → continue`.

That boundary corresponds broadly to the previously defined automatic round-trip/dynamic collaboration gates.

Therefore the project should **not yet skip directly to “IABV manages all accounts and all AIs autonomously.”**

## CURRENT DEVELOPMENTAL ORDER

The current development order is:

`safe live environmental observation`
→
`live PerceptionSnapshot observability`
→
`objective-conditioned capability/resource selection`
→
`one governed external-AI round trip`
→
`dynamic multi-AI selection`
→
`account/session/authentication expansion`
→
`repeated heterogeneous laptop objectives`
→
`verified learning and reduced routine human coordination`.

The exact next edge remains determined by current evidence, not by this roadmap alone.

## RELATION TO UAAL-RQ04/RQ05

RQ04 first open technical edge:

`LIVE WorldModel → LIVE PerceptionSnapshot`

This must remain the next technical seam before claiming that IABV can make robust current-environment decisions from live evidence.

Once that edge is closed, recompute the frontier.

Do not create a provider-specific “Codex brain”.

## SYMBIOSIS MATURITY MODEL

### S0 — Human-mediated coordination
Human carries prompts/results between IABV context and external AIs.

### S1 — IABV-frame-assisted coordination
GitHub-backed IABV canonical frame selects actor and generates the exact prompt; human transports it.

**CURRENTLY AVAILABLE OPERATIONALLY.**

### S2 — IABV-mediated delegation
IABV itself discovers/chooses a resource and invokes an external AI/tool, captures the result and returns it to its own decision loop.

**NOT PROVEN.**

### S3 — Dynamic multi-resource collaboration
IABV chooses among ChatGPT/Codex/Claude/etc. based on capability/access/uncertainty and can coordinate multiple resources.

**NOT PROVEN.**

### S4 — Closed developmental collaboration
Verified delegated experience changes later resource selection/strategy and reduces routine human coordination.

**NOT PROVEN.**

These levels are operational milestones, not claims about consciousness.

## CONTINUITY / FUTURE CHAT RULE

For any future prompt involving:

- using IABV as the laptop assistant;
- delegating to ChatGPT/Codex/Claude/Devin;
- logging into or operating accounts;
- browser/application control;
- universal environment understanding;
- external-agent symbiosis;
- automatic delegation;
- self-development;

activate this record together with:

`CURRENT-STATE.md`
`CONTEXT-INDEX.md`
`MEMORY-OPERATING-PROTOCOL.md`
`SYMBIOSIS-MAP.md`
`UNRESOLVED-KNOWLEDGE.md`
and the exact current GitHub/runtime evidence.

Do not make the human restate this vision.

## NON-CLAIMS

This record does not establish:

- autonomous runtime delegation;
- autonomous credential acquisition;
- authorization to use accounts;
- consciousness;
- general intelligence;
- open-ended self-development.

Those remain empirical targets.

