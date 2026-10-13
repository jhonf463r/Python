# CHAT-ARCH-2026-10-13-235 — Codex plan entitlement and App Server auth-mode distinction

Date: 2026-10-13 (America/Bogota)
Classification: official documentation reconciliation / route-selection constraint.
Baseline: remote `main @ 9fd4373bbc8f8d861e9786c35dab0bc9bf742de1`.
Scope: official current OpenAI help/developer documentation plus canonical records 231–234; no local source/runtime was independently inspected or executed.

## 1. Documentation facts affecting the no-extra-spend route

Current official ChatGPT help says Codex is included in all ChatGPT plans, including Free and Go, with plan-dependent usage limits; Codex Cloud is not included in Free or Go. See:
https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan

The separate Sign in with ChatGPT (SIWC) developer flow for third-party/open-source applications says usage of a user's ChatGPT plan in an integrating app is available to eligible Plus and Pro users (and participating/eligible apps). See:
https://developers.openai.com/siwc/quickstart

The specific SIWC App Server example configures an OAuth access token as `ACCESS_TOKEN` for the `openai_chatgpt_plan` Responses provider and requires the application to perform that auth/token lifecycle. See:
https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server

These are distinct access modes. The existence of Codex access in the native desktop/CLI client does **not** prove that a third-party SIWC plan-usage integration can use the same allowance, and the SIWC example does **not** prove the local `CodexAppServerToolAdapter` uses that flow.

## 2. Routing implication

Do not reject App Server solely because the account is Free, and do not declare it cost-free merely because Codex is included in Free. The next source audit must identify which precise auth mode the adapter implements:

- Native Codex client/App Server auth via its configured Codex home and already signed-in account; or
- SIWC OAuth token-sharing to the ChatGPT-plan Responses provider; or
- API-key/billable API or another mode.

No token files, tokens, credentials or environment dumps may be read or disclosed during this static audit. If the implementation depends on SIWC plan usage that is not eligible for the user's available account/app, or on a billable API credential, mark that route incompatible with the current no-extra-spend constraint unless the Owner explicitly changes the constraint. If native local Codex auth is used, static source can identify the mechanism but live sign-in, plan entitlement and available quota remain unproven until separately authorized validation.

Do not conflate Codex Local with Codex Cloud. Do not create a new OAuth client, register SIWC, request a new API key, buy credits, subscribe, install software or download a model in this mission.

## 3. Next bounded source-only decision

Continue from record 234 without repeating the Desktop window or launch-provenance investigation. Inspect the already-known App Server adapter and only its direct auth/config/preflight/tool-policy call sites to answer:

1. Which auth mode is actually used?
2. Which exact `CODEX_HOME` supplies it, and is the selected home the isolated IABV data path or a native signed-in Codex home? Do not inspect credential contents.
3. Does normal dispatch call all applicable preflight/readiness checks?
4. What effective protocol-level policy prevents unwanted tool effects before execution for a text-only consultation?
5. For a separate coding task, how could tools be restricted to an isolated candidate worktree and exact approved scope, with authority gates RQ218/RQ223/RQ224 preserved?
6. How does a completed turn reach the existing consumer and get evaluated?

No process start/stop, App Server invocation, HTTP/DNS, UI/CDP, tests/builds, code edits, configuration mutation or prompt dispatch. Stop where static evidence ends.

## 4. State preservation and continuity

Preserve the reported local worktree `codex/m0a-safe-ui-boot`, HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, with 56 tracked modifications and 5 untracked files; these are owner-reported and not newly inspected. No reset/clean/restore/commit/push.

Current result from record 234 remains `LAUNCH_PROVENANCE_UNAVAILABLE`; it does not prove a mismatch. The Desktop capture-home link stays unproven. This record adds an entitlement/auth-mode constraint but does not claim the App Server route works or fails.

No extra spend remains mandatory. M0-A live round-trip, M0-B, D016 self-development and later causal reuse remain unproven.

Current next edge: `CODEX_APP_SERVER_AUTH_MODE_AND_ENTITLEMENT_UNRESOLVED`.
