# CHAT-ARCH-2026-10-13-241 — Reframe the Codex bridge around the actual development objective

Date: 2026-10-13 (America/Bogota)  
Classification: Continuity and route adjudication; no local IABV execution or code change.

## 1. Owner objective clarified

The primary goal is not merely a tool-free answer from an external model. It is a governed development handoff:

`IABV task → Codex receives the exact authorized development prompt → Codex works within explicit boundaries → IABV receives the terminal result and artifacts → task/result identity is correlated → existing verifier/consumer evaluates the result → owner decides whether to promote or reject`.

The longer-term D016 objective is a controlled self-development cycle, not automatic code mutation or unrestricted autonomy. Additional provider integrations should not be added without showing that they shorten this causal path.

## 2. Canonical baseline and evidence provenance

Canonical baseline at intake: `main @ db46f71736df88e0ed3949a25607108f94d4d2a9`, which records RQ/Chat-Arch entry 240.

The Owner-supplied local report remains: branch `codex/m0a-safe-ui-boot`, HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, 56 tracked modified files and 6 untracked files. These are reported figures, not a fresh inspection of the Windows worktree. Preserve all dirty and untracked state; this record does not publish local code.

The prior reported `CODEX_TASK_ID_REPAIR_PASS` and Ollama's 58 synthetic tests are owner-reported, synthetic/source evidence. They do not prove a live Codex or Ollama exchange, authentication, quota, response capture, consumer evaluation, or causal learning.

## 3. Crucial distinction: two execution modes

Entry 240 found no generic all-tools-off field in the named public `rust-v0.120.0` `ThreadStartParams`/`TurnStartParams` structures. That remains a bounded negative finding for a **tool-free text-only Codex turn**; it is not proof that every Codex development integration is impossible.

Do not keep searching for an undocumented global switch or treat tool suppression as a universal prerequisite for the coding objective. Split the operation class:

1. **Text consultation:** no file changes and no tool side effects. Use only a path whose effective no-tools/text-only property is demonstrable. The current App Server route remains blocked for this mode under the reviewed contract. Ollama remains a possible local text capability, but availability/inference are unproven; ChatGPT Web/CDP is a generic consultation route, not the Codex development bridge.
2. **Bounded development task:** tool use is necessary to inspect code, write a candidate patch and run permitted tests. The security requirement is therefore not “Codex has no tools”; it is that every effect-capable tool runs only inside an enforceably confined candidate environment with an explicit operation/resource/scope grant, deny-by-default external effects, and no automatic promotion. A prompt saying “stay in scope,” a path-separated copy, or a requested sandbox mode without evidence of effective enforcement is insufficient.

App Server is still a promising programmatic candidate because its documented purpose includes thread/turn lifecycle and event delivery. However, the local route remains unready: actual CLI/protocol identity is unproven because source reportedly resolves the executable dynamically from `PATH`; normal SafeUI dispatch reportedly skips adapter `preflight()`; effective Windows sandbox and network boundaries are unproven; authentication/home selection, included usage quota/cost behavior, and consumer evaluation are unproven. Keep these as independent gates.

Official references:
- Codex harness/App Server integration choice: https://developers.openai.com/blog/codex-as-a-platform
- Codex with ChatGPT plan; Free-plan availability has usage limits, not unlimited use: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- App Server with OAuth authorized for ChatGPT-plan usage is a distinct integration mode; do not assume it is the local CLI auth path: https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server
- Versioned protocol limitation remains recorded in entry 240 and its tagged schema references.

Cost invariant: no API key, API billing, purchased credits, new OAuth integration, software installation or model download in this route. Existing ChatGPT-plan Codex use may consume included usage and may hit plan limits; do not claim “free/unlimited.” Verify the actual auth path statically and do not run a turn until a separate bounded runtime authorization exists.

## 4. Route decision

Do not return to ChatGPT Web/CDP discovery as the next step for the Codex-specific development objective. Keep entry 229 as valid historical evidence for the generic ChatGPT Web route.

Do not expand OpenAI API or Ollama wiring now. Preserve the dirty local branch and all changes; do not cherry-pick, merge, reset, clean, commit or push code.

The next action is a **bounded source-only route feasibility audit for a confined Codex development task**, not another broad upstream schema search. It must inspect only the existing App Server adapter, direct configuration/tool registry and Windows-specific sandbox/launch composition, plus the already identified result consumer. Answer whether the current code can enforce a candidate-worktree boundary, constrain file writes and command execution, prevent unapproved network/MCP/app integrations, maintain task/thread/turn/digest correlation, and return a terminal artifact/result to the existing consumer. Clearly state which claims are source-proven and which require OS/runtime evidence. Do not implement anything during that audit.

If no enforceable boundary is already available, keep the route blocked and propose the smallest design change separately. Prefer a dedicated low-privilege execution boundary (e.g. an available OS-enforced sandbox/VM) with only a candidate worktree mounted/writable, no access to owner secrets or original worktree, controlled test commands, no promotion/commit/push, and network restricted to the model/control channel required by the host. Do not call a directory outside the worktree “securely isolated” absent an actual OS boundary.

## 5. Required eventual proof ladder

1. Static path and scope feasibility.
2. Explicit design for the process/filesystem/network boundary and exact auth/cost mode.
3. Focused synthetic tests for authorization binding, dispatch-once, task ID, failure/timeout/late event, terminal event, artifact/digest and zero dispatch on invalid authorization.
4. Separate Owner authorization for a single real, non-publishing development task in a disposable candidate workspace.
5. Observed matching task/thread/turn, terminal response and captured diff/test evidence.
6. Existing consumer demonstrably evaluates the result; an independent verifier checks the candidate against a baseline.
7. Owner-controlled promote/reject/revert decision. No automatic commit/push/main mutation.
8. D016 causal-reuse test on a later, non-identical task before claiming learning.

Memory rule: a GitHub record is portable external memory and temporal trace, not automatic runtime memory. Persisting a prompt/result does not show retrieval, activation, a changed future decision, or improved outcome. Record each episode with timestamp/order, parent edge, objective, actor, evidence provenance, decision, expected/observed outcome, delta, next edge and independent-verification status.

## 6. Current decision

Classification of the reviewed App Server proposal remains `APP_SERVER_STATICALLY_BLOCKED` **for a tool-free text-only turn under the reviewed 0.120.0 contract**. The broader Codex development bridge is `CODEX_DEVELOPMENT_ROUTE_NOT_YET_ADJUDICATED`, not proven impossible and not operationally verified.

Next edge: `CODEX_BOUNDED_DEVELOPMENT_EXECUTION_BOUNDARY_UNPROVEN`.

Stop after the bounded source-only feasibility report. No runtime, process, network/UI/CDP, test/build, credentials, source/config edits, real prompt, spend or publication is authorized by this record.
