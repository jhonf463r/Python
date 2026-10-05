# CHAT-ARCH-2026-10-05-060 — UAAL-RQ05 Candidate Safe PerceptionSnapshot Observation Seam

**STATUS:** RECONCILIATION / CANDIDATE IMPLEMENTATION / RUNTIME VERIFICATION PENDING

## PURPOSE

Preserve the RQ05 result without promoting an uncommitted worktree change to canonical code.

## EXPERIMENT BASELINE

Code-bearing baseline inspected by Codex:

`e46d8304167708bed0764d3bf2be8fd6643e8944`

Canonical GitHub main subsequently contains documentation writebacks, but this RQ05 candidate was executed against the above code-bearing checkout.

## RESULT

RQ05 found that configuration-only exposure of the already-existing `cognitive_frame_translate` surface was insufficient because the canonical assembler path could request World Model refresh and portable-context work.

Codex created an **uncommitted candidate change** in an isolated checkout.

Reported candidate behavior:

`TaskContextAssembler.build_perception_snapshot(refresh=False)`

uses existing `current_model()` state for World Model and Environment Self Model and does not request refresh for that path.

The candidate also excludes portable-context reconstruction for the safe observation path.

`cognitive_frame_translate` was changed to use this no-refresh path and project the produced PerceptionSnapshot.

The external Codex MCP allowlist was changed to expose `cognitive_frame_translate` and point the configuration at the canonical checkout, but the currently active MCP session was not restarted.

## CANDIDATE FILES

- `src/iabv_v15/services/adaptive/task_context_assembler.py`
- `src/iabv_v15/infra/mcp/server.py`
- `tests/test_cognitive_frame_translate_tool.py`
- `tests/test_task_context_assembler.py`
- external Codex MCP configuration

No production commit or push was made.

## TEST EVIDENCE

Codex reported:
- focused tests passed;
- two related test modules passed: **19 passed in 9.85s**;
- `git diff --check` passed.

These are method/unit evidence for the candidate. They do not prove runtime behavior.

## REFRESH / OBSERVATION BOUNDARY

The intended seam is:

`read existing current model`

versus:

`request new observation/refresh`.

This is method-level candidate behavior only until a fresh process loads the candidate and the MCP observation is executed without causing the call under test to request refresh.

Autonomous/background scans remain separately observable phenomena and must not be attributed to the tool invocation without evidence.

## CURRENT EPISTEMIC STATUS

**FACT / OBSERVED FROM CODEx REPORT:**
- candidate code exists in an isolated worktree;
- candidate was not committed;
- tests passed in the candidate checkout;
- active MCP session did not reload the new configuration;
- runtime `cognitive_frame_translate` was not invoked.

**INFERENCE:**
- the candidate appears to provide the missing no-refresh observation seam at source level.

**NOT PROVEN:**
- fresh runtime process loads the candidate;
- MCP exposes and executes the candidate tool;
- returned PerceptionSnapshot contains the live World Model;
- the invocation does not cause refresh;
- live fields correlate;
- the runtime state reaches the DecisionContext.

## ROUTING DELTA

The previous frontier:

`LIVE WorldModel → PerceptionSnapshot LIVE observable`

is now decomposed into:

1. **candidate source seam** — PRESENT / TESTED;
2. **fresh runtime loading** — OPEN;
3. **safe tool invocation** — OPEN;
4. **live WorldModel ↔ PerceptionSnapshot field correlation** — OPEN;
5. **PerceptionSnapshot ↔ DecisionContext live propagation** — remains OPEN for later recomputation.

## NEXT DISCRIMINATING EXPERIMENT

**ACTOR: CODEX**

Run the candidate in a **fresh, directly attributed MCP subprocess** from the candidate checkout, preferably through a temporary stdio harness if the current Codex session cannot reload its MCP connection.

The experiment should:

- start the MCP server from the exact candidate checkout;
- record executable, CWD, module/source path and candidate Git status;
- obtain a World Model state without requesting refresh;
- invoke `cognitive_frame_translate` through the fresh process;
- capture the returned PerceptionSnapshot projection;
- compare relevant fields before/after;
- prove that the invocation itself does not call `request_refresh`;
- distinguish tool-induced effects from autonomous/background scan activity;
- leave the user's environment unchanged;
- not commit or push until runtime behavior is understood.

Only after this runtime proof should the candidate be considered for a branch/commit and independent Sonnet audit.

## STOP CONDITION

Stop if:
- the tool still cannot be invoked from a fresh attributed process;
- the candidate unexpectedly requests refresh;
- provenance cannot be established;
- the returned snapshot cannot be correlated with live World Model state.

Do not add another perception layer.

