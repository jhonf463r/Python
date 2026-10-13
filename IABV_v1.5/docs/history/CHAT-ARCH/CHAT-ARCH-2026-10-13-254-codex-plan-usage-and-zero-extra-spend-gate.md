# CHAT-ARCH-2026-10-13-254 — Codex plan usage is not the same as zero additional spend

- **Episode ID:** `CHAT-ARCH-2026-10-13-254`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** `main @ 00eb5b9856c4921e84b63bd4d2391f6f3863a108`
- **Related records:** entries 246–253.
- **Classification:** `CODEX_INCLUDED_PLAN_ROUTE_DOCUMENTED_ACCOUNT_ENTITLEMENT_AND_NO_EXTRA_CHARGE_UNPROVEN`
- **First open edge:** `CODEX_EXEC_AUTH_HOME_POLICY_AND_USAGE_BUDGET_ROUTE_UNRESOLVED`

## 1. Current official plan/usage documentation

The current official OpenAI Help Center page [“Using Codex with your ChatGPT plan”](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan), updated about a day before this review, says:
- Codex is included across ChatGPT plans, including Free and Go, but limits vary by plan.
- Users should check Settings/the usage dashboard for which allowance is being consumed, remaining credits and reset time.
- Codex model activity remains subject to the plan's usage limits and applicable credits/billing. Standard Codex Cloud VMs have no additional VM charge at launch, but model use still comes from plan allowances/credits/billing.
- Some supported accounts may buy additional usage credits when included limits are exhausted; credits are pay-as-you-go, not part of the original included allowance.

Official Spanish page: https://help.openai.com/es-419/articles/11369540-using-codex-with-your-chatgpt-plan

The current official [flexible-usage credits article](https://help.openai.com/en/articles/12642688-using-credits-for-flexible-usage-in-chatgpt-personal-plans) clarifies that credits expand usage after the included plan limit and are a pay-as-you-go add-on.

This improves the entitlement picture but does **not** prove the Owner's active account, authentication state, remaining allowance, credit settings, workspace policy or billing mode. It is not permission to assume cost-free unlimited execution. Plan-included use can consume the Owner's normal Codex allowance; that is different from an incremental cash charge and from using no quota at all.

## 2. Version caveat

The previously identified local package was owner-reported as Codex CLI `0.120.0`. The public CLI docs above describe current plan entitlement and sign-in pathways, not every runtime behavior of the older `0.120.0` binary.

The Help Center directs users to sign in with an existing ChatGPT account in the selected Codex client. That documents the supported general path, but it does not establish that the Owner's current CLI/home is already authenticated or that the exact `0.120.0` installation is still compatible with the account, required model and current policy. Do not update/install a newer version under the current no-install constraints just to resolve this uncertainty.

## 3. Combined with entries 251–253

Three independent controls now intersect:

1. **Authentication lookup:** in Codex 0.120, file auth lives in `CODEX_HOME/auth.json`; keyring lookup derives its key from the canonical home path. Switching homes does not automatically reuse an existing keyring auth entry (entry 253).
2. **Command sandbox:** a matching explicit execpolicy `Allow` can lead to `SandboxType::None`; a permission profile alone is insufficient if any effective policy layer permits a command bypass (entry 252).
3. **Usage budget:** Codex is included in ChatGPT plans, but included usage is finite/plan-dependent and additional credits may be available in eligible accounts; the Owner's actual entitlement and credit/billing condition are unknown.

Consequently, a valid design cannot claim both “reuse existing authentication” and “no extra spending” solely from the fact that the CLI package is installed. It must establish an approved existing home/auth path, prove the applicable execpolicy layers cannot bypass the boundary (or establish a separate OS boundary), and define a hard stop before any paid credits/add-on budget would be consumed.

## 4. No-extra-spend acceptance contract

Before any separately authorized test, the design should require:
- Use only an already-approved ChatGPT/Codex entitlement path; no API key, new OAuth/login, install/update, purchased credits or paid API fallback.
- If included quota is used, recognize it as consumption of the plan allowance; do not claim “no quota used.”
- Do not configure or invoke an automatic transition to pay-as-you-go credits or billable API usage. If this cannot be established from the existing configuration/account controls, stop instead of continuing when included usage is exhausted.
- The actual account UI/usage state and entitlement must be checked by the Owner or through a separately authorized allowed read-only action. They are not available from public source code or GitHub.
- Record the usage precondition and stop condition before dispatch; a CLI return code does not prove zero cost.
- Any inability to prove the cost boundary means the route remains blocked.

This entry does not instruct the agent to open Settings, inspect usage, launch `codex`, issue `/status`, authenticate, or trigger a task. Those actions require their own Owner authorization and must not expose credentials.

## 5. Revised decision status

The operative runtime decision remains C/block. A/B remains unselected:
- An already-authenticated existing home may retain the only valid keyring lookup, but its applicable rules must not be able to bypass confinement.
- An already-existing dedicated authenticated home may be preferable if it truly exists and needs no new login/copying/spend; its own rule layers and usage path still require verification.
- A new home does not inherit the old keyring entry, and a new session cannot be assumed cost-free or authorized.

## 6. First open edge

**`CODEX_EXEC_AUTH_HOME_POLICY_AND_USAGE_BUDGET_ROUTE_UNRESOLVED`**

Continue cloud source analysis where useful. The minimum later local evidence is a separately authorized non-mutating preflight establishing only non-secret facts: selected home path/store mode; provenance of effective policy layers and explicit-Allow bypass; already provisioned Windows boundary; and an Owner-confirmed current entitlement/allowance/billing stop condition. It must not read credentials, invoke the CLI, start a coding task, change configuration, buy credits or consume additional spend.

Keep all previous non-authorization gates. No implementation, test or runtime turn is authorized; preserve all dirty/untracked local work. This writeback is external project memory, not live evidence of usage, successful coding or autonomous model learning.
