# IABV v1.5 — CURRENT STATE OVERRIDE — 2026-09-19

## L5 FINAL ADJUDICATION

Independent Sonnet 5 Low forensic audit has closed the previous L5 provenance gate.

**L5 = PROVEN** for the selector-level causal-learning claim:

`verified real-world experience → persisted VerifiedTransition/InteractionPattern → cold reload → normal competitive selector with multiple candidates → changed future winner → specific causal attribution`

Evidence branch:
`l5-evidence-capture-3241b3ef6`

Publication commit:
`97bb60b71a3ed438021cb18acf55111d7c71265a`

Tested code:
`70553010bafca96e98b7dc5b113eed4f3ad84e8b`

Runtime artifact:
`IABV_v1.5/l5_evidence/l5_experiment_20260918_022256_runtime.txt`

Artifact SHA-256:
`61c56fd0404469dec60cb29827546b23011d93d4942ce5470c83a705d1628ef2`

Artifact size:
`17617 bytes`

## IMPORTANT CAUSAL CORRECTION

The previously suspected `cost 0.40 → 0.75` anomaly was not a runtime mutation or causal confound. The Reason field describes the winning candidate of each round:

- Control winner = `aider_coder`, CODE_EDITOR, cost 0.40
- Treatment winner = `mcp_client`, MCP_CLIENT, cost 0.75

For the same `mcp_client` candidate, cost/risk/latency and the other non-learning score inputs were constant. The observed score delta is explained by the InteractionPattern-derived changes in stability, frequency and learned_pattern; reconstructed arithmetic matches the observed delta within displayed rounding.

Therefore the independent audit classified:

**A — L5 PROVEN**

## SCOPE BOUNDARY

This is a closure of selector-level causal learning. It must not be propagated into:

- L6 behavioral causality;
- L7 later external-world causal closure;
- full P0-B authority/security closure;
- I0 secure external-agent connection closure;
- I1 automatic round-trip closure;
- I2 dynamic closed symbiosis closure;
- real Devin cognitive influence.

In particular, the historical constraint `REAL AUTHORITY = NOT PROVEN BY G3` remains active for the authority/security subsystem. L5 proof and P0-B proof are separate claims.

## NEXT STRATEGIC FRONTIER

Two tracks remain parallel:

### Scientific proof
`L5 PROVEN → L6 behavioral-change experiment → L7 external-world causal experiment`

### Symbiosis inflection
`I0 external-agent connection → I1 automatic round trip → I2 dynamic closed loop`

Do not require L6/L7 before testing I0/I1.

The smallest next symbiosis experiment should use existing IABV organs and aim to demonstrate a real automated:

`objective → canonical context → selected Devin capability → delegated task → received result → provenance binding → independent verification`

without human copy/paste. Do not create a new orchestration subsystem unless source evidence proves an existing owner cannot close the edge.

## CROSS-CHAT RULE

Future chats touching L5+, external-agent delegation, automatic prompt relay, multi-agent orchestration or symbiosis must treat this override as later than the 2026-09-18 override and reconcile it against the current GitHub tip before acting.

## 2026-09-19 I0/I1 LIVE UPDATE — CREDENTIAL BLOCK

The first I0 runtime probe was blocked before any Devin HTTP request because the controlled Windows environment had no value for `DEVIN_API_KEY_IABV`, `IABV_DEVIN_API_KEY` or `DEVIN_API_KEY`.

**I0 = NOT PROVEN. I1 = NOT REACHED. Primary classification = E (BLOCKED).**

Do not patch around this blocker and do not infer connection/authorization from source existence.

Next action: securely expose a real Devin API key to the controlled runtime using an already-supported environment variable, then rerun only the connection/authentication phase. After authentication succeeds, resume the production round-trip probe.

Credential availability is an environment/account prerequisite. The repository implementation should not contain the secret.