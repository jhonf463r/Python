# CHAT-ARCH-2026-10-13-256 — Read-only authenticated model-catalog path unavailable

- **Episode ID:** CHAT-ARCH-2026-10-13-256
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** main @ feb31465e0f5d64f4cc6cf9dc518b65cdd510a1c
- **Related records:** entries 252–255.
- **Mission result:** READ_ONLY_MODEL_CATALOG_PATH_UNAVAILABLE
- **Operational posture:** KEEP_BLOCKED
- **First open edge:** CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED

## Bounded catalog-interface finding

The versioned Codex rust-v0.120.0 CLI declares ordinary exec behavior and the resume/review subcommands; the inspected public CLI surface does not establish a standalone catalog-only command. Its internal ModelsManager::list_models() refreshes model availability and combines remote data with the bundled catalog, but this is an internal application component, not a demonstrated supported isolated catalog-only interface for this mission.

The examined route therefore did not provide a safe, supported way to make only an authenticated catalog request without a model turn. This is bounded to the inspected interface; it does not prove every compatible catalog-only route impossible.

## Evidence and limits

| Claim | Classification | Evidence and boundary |
|---|---|---|
| No standalone catalog-only operation was established in the inspected 0.120 CLI interface | PROVEN_BY_SOURCE | exec/src/cli.rs exposes exec and the listed subcommands; ModelsManager is internal. |
| No isolated supported catalog-only request was identified in this mission | OWNER_REPORTED | Result READ_ONLY_MODEL_CATALOG_PATH_UNAVAILABLE; no substitute route was used. |
| No authenticated HTTP catalog request, model turn, new login/session or alternate execution occurred | OWNER_REPORTED | Mission outcome reports no such action. |
| Bundled models.json does not prove live availability or account eligibility | PROVEN_BY_SOURCE | A packaged catalog is not an authenticated current account response. |
| Known CLI 0.120.0 is below documented minimums for GPT-5.6 (0.144.0) and GPT-6 Astra (0.153.0) | PROVEN_BY_SOURCE + OWNER_REPORTED | Minimums are in the official Help Center; 0.120.0 was reported by an earlier static inventory. This does not prove no other model works. |
| GPT-5.4 and GPT-5.4 mini ceased availability in Codex with ChatGPT sign-in on 2026-08-31 | PROVEN_BY_SOURCE | OpenAI Help Center plan article. |
| GPT-5.2 and GPT-5.3-Codex retirement | PROVEN_BY_SOURCE (bounded) | OpenAI contributor etraut-openai stated this in a public reply on issue #25871; this is a contributor comment, not an account-specific eligibility check. |
| Current authentication, eligible model, included usage, quota, paid-credit fallback, cost and account/workspace restrictions | UNPROVEN | No account/catalog request or credential inspection occurred. |

## Sources

- Codex 0.120 CLI: https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/exec/src/cli.rs
- Internal model manager: https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/models-manager/src/manager.rs
- Bundled catalog: https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/models-manager/models.json
- OpenAI Help Center — GPT-6 and other models in ChatGPT: https://help.openai.com/en/articles/20001354-gpt-6-and-other-models-in-chatgpt
- OpenAI Help Center — Using Codex with your ChatGPT plan: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- OpenAI Codex issue #25871, including the contributor reply: https://github.com/openai/codex/issues/25871

## Decision and next discriminating fact

Keep CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED open and posture KEEP_BLOCKED. The unavailable examined query does not prove every compatible path impossible.

The next discriminating fact is whether a client-compatible model is currently available under the already authorized ChatGPT authentication path and a permitted included-usage route. That requires a separately established supported observation path; do not infer it from models.json, public retirement reports, package presence or plan inclusion. Authentication, entitlement, quota, paid-credit behavior and cost remain separate gates.

No Codex CLI/App Server/IABV process, login, catalog request, inference, model turn, credential inspection, installation, configuration/code change, test/build, spending, promotion or learning claim is made by this record. This writeback is continuity, not operational experience or proof of an IABV-to-Codex exchange.