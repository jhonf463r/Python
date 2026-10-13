# CHAT-ARCH-2026-10-13-255 — Installed CLI version versus current model and plan entitlement

- **Episode ID:** `CHAT-ARCH-2026-10-13-255`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** `00eb5b9856c4921e84b63bd4d2391f6f3863a108`
- **Related records:** entries 246–254.
- **Classification:** `CODEX_0120_INSTALLED_VERSION_CURRENT_MODEL_COMPATIBILITY_UNPROVEN`
- **First open edge:** `CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED`

## 1. New current official requirements

The current official OpenAI Help Center article [GPT-5.6 and GPT-6 Pro in ChatGPT](https://help.openai.com/en/articles/20001354-gpt-56-and-gpt-6-pro-in-chatgpt) was updated within the last day during this review. It says:
- Codex requires CLI **0.144.0 or newer** to access GPT-5.6.
- GPT-6 Astra requires CLI **0.153.0 or newer**.
- Free/Go use a current Codex model availability profile; current account/model access remains plan-dependent.

The Owner-supplied static inventory from entry 246 identified an installed `@openai/codex` CLI version `0.120.0` in that inspected shell. This is older than both documented minimums. This does not prove that `0.120.0` cannot run every older/available model, nor that this is the binary IABV would launch, but it means the design **cannot assume access to those current models** via the known installed binary.

Reference (fresh official source): https://help.openai.com/en/articles/20001354-gpt-56-and-gpt-6-pro-in-chatgpt

No update/install is authorized in the current scope. Do not launch the binary, use `--version` or `--help`, or assume an upgrade can be done without additional setup/cost.

## 2. Plan inclusion and cost are separate from model compatibility

Current official OpenAI Help Center [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan), updated about a day before this review, says Codex is included in ChatGPT plans including Free and Go, with plan-dependent usage limits. When included allowances are exhausted, some eligible accounts can buy additional usage credits; those are a paid add-on. Other Codex activity remains subject to plan usage and the applicable allowance/credit/billing route.

This establishes a supported **plan-included option**, but not the Owner's current account session, model eligibility, remaining usage, credit settings, workspace constraints or a guarantee that a specific CLI invocation will not incur an extra charge. It is essential to distinguish:
- no paid API key / no API billing route;
- no new OAuth/login setup;
- consumption of included ChatGPT/Codex usage;
- no incremental cash charge;
- no possibility of automatically using paid credits.

These are not equivalent. The future design must hard-stop before additional paid credits/API fallback. If included quota is depleted, do not buy credits, install another version or continue under a different billing route.

References:
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://help.openai.com/en/articles/12642688-using-credits-for-flexible-usage-in-chatgpt-personal-plans

## 3. Combined decision implications

The proposed CLI route now has four separate version/config/account gates:

1. **Installed version/model compatibility:** reported CLI 0.120.0 does not meet official minimum CLI versions for GPT-5.6/Astra. Access to another currently supported model through this exact binary is `UNPROVEN`.
2. **Authentication/home coupling:** file auth is `CODEX_HOME/auth.json`; keyring lookup is keyed from the canonical `CODEX_HOME` path. A new home does not automatically reuse an existing keyring session (entry 253).
3. **Effective execpolicy:** explicit Allow rules from the applicable config-layer `rules/*.rules` can cause `SandboxType::None` for matching commands (entry 252). A permission profile alone is not sufficient.
4. **Included usage versus extra spend:** plan-included usage is documented, but active auth, entitlement, model availability, quota and credit fallback behavior are not verified for the Owner's actual account/runtime.

The local worktree and actual environment remain inaccessible from this GitHub source review. These gates cannot be closed by versioned public documentation alone.

## 4. Updated recommendation

Continue design and source-only discrimination; keep runtime at C/block. Do not make an owner choose a home yet, because the version and effective-rule constraints might make both A and B unusable without violating no-install/no-extra-spend constraints.

A future separately authorized, **non-mutating** preflight should establish only the minimum non-secret facts:
- which exact CLI path/version would be selected by the IABV child, without invoking it to discover the version;
- which currently supported model, if any, is permitted for that version under the Owner's account;
- selected Codex home and auth store mode, without reading credentials;
- provenance of all applicable rule layers and whether an explicit Allow rule can match the proposed command surface;
- already provisioned Windows sandbox backend and effective restrictions;
- Owner-confirmed included usage and a hard stop preventing additional paid credits/API fallback.

If resolving any of these facts requires a CLI turn, login, install/update, credential access, additional spending or mutating configuration, stop and request separate authorization. Do not bypass a failed version gate by switching to API keys or buying credits.

## 5. First open edge

**`CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED`**

This edge is ahead of implementation but is not itself a request to install a newer version. Under the current no-install constraint, the route can advance only if the existing `0.120.0` binary has an already available compatible, plan-included model/usage path and the home/rule/security gates can be satisfied. If not, keep the bridge blocked and return the exact incompatibility to the Owner rather than silently changing the constraints.

## 6. Non-authorization and provenance

No CLI/App Server invocation, process launch, agent turn, tests/build, login/OAuth, credential/session inspection, network action on the Owner's machine, update/install/download, credit purchase, additional spend, local source/config mutation, commit, push or promotion was performed or authorized by this entry. Preserve the reported dirty/untracked local worktree. Current official plan/model documentation is source evidence; it is not local account/runtime evidence and does not prove a live IABV→Codex→IABV exchange or autonomous learning.
