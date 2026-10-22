# M1 — Bounded governance-surface inventory follow-up

- **Episode ID:** `EP-20261022-M1-SESSION-SURFACE-INVENTORY-01`
- **Date:** 2026-10-22, America/Bogota.
- **Type:** bounded evidence update; documentary only.
- **Primary outcome:** `GOVERNED_IABV_CODEX_BRIDGE`.
- **Active task:** `M1 — IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`.
- **Canonical route authority:** [CURRENT-STATE.md](./CURRENT-STATE.md). This record does not change that route or grant access.

## Scope and method

This session verified the current remote `main` ref using the GitHub connector before reading the ordered continuity documents. At the time of the bounded surface check, `main` pointed to commit `f891810b4daf00bf7440e438f0afbc832ccb326e` (message: `docs(iabv): anchor latest chat handoff in canonical current state`). The seven required documents were fetched from `main`; their observed blob IDs were:

| Document | Observed blob SHA |
|---|---|
| `IABV_v1.5/AGENTS.md` | `9971817f1e5bba0d09473c6696dec4a546234b89` |
| `docs/history/CHAT-ARCH/README.md` | `be096d73d8debc099ae846e9f57f5e8db3862542` |
| `docs/history/CHAT-ARCH/CURRENT-STATE.md` | `29bb738f805d167da16ff181be5fad2a184b169a` |
| `docs/history/CHAT-ARCH/CONTEXT-INDEX.md` | `a6cfe6c2b97441ff0d857f3e1f49fca398c78303` |
| `docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md` | `b8c95c9b6678f9d5813ed5bc1f5387ec66601de8` |
| `docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-coordinator-reality-aligned-bridge-continuity-handoff.md` | `86e81033c15b8dad1364815d51fdd87e4e8cc7ce` |
| `docs/history/CHAT-ARCH/DEVELOPMENT-CONTROL-TOWER-2026-09-21.md` | `a46df627c8264f0b5a393a5825eb8625e71c1637` |

The exposed callable-tool catalogue was enumerated for the current ChatGPT session. Its available namespaces were generic file/library tools, Automations, GitHub, OpenAI Platform, Plugin Management, skills and user settings. No IABV-local/MCP governance-owned operation was exposed that could issue or verify a scoped repository-read decision or release an operational block.

Issue [#470 — supported scoped-read route](https://github.com/jhonf463r/Python/issues/470) was fetched again. It remains `OPEN` with five comments. The current issue body and comments record the missing authority/route and the design-only discussion, but do not identify a callable governance interface, trusted issuer, responsible operational contact, decision receipt, or independent release authority. A repository issue is evidence of the unresolved request, not the authority itself.

## Bounded result

```
CHECKED_SURFACE=CHATGPT_EXPOSED_CALLABLE_TOOL_CATALOGUE
SESSION_EXPOSED_SUPPORTED_ADMIN_READ_TOOL=NOT_FOUND
SUPPORTED_SCOPED_READ_ROUTE=NOT_FOUND_IN_CHECKED_SESSION_SURFACE
ISSUE_470_EXECUTABLE_ROUTE_OR_OPERATOR=NOT_FOUND_IN_CURRENT_ISSUE_CONTENT
GLOBAL_ROUTE_EXISTENCE=UNRESOLVED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
LOCAL_SOURCE_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

This is a negative result for the named session tool surface and current issue content only. It does **not** prove that an administrative surface/operator does not exist outside the examined surfaces. Do not upgrade it to global `NOT_FOUND`.

## What was and was not done

**Done:** remote `main` and the required documentary entry points were fetched; the callable-tool catalogue was enumerated; issue #470 and its five comments were fetched and reviewed; the bounded result was reconciled against the canonical M1 state.

**Not done:** no IABV/MCP local reader was invoked; no alternative reader was used; no local checkout or configuration was read; no Codex CLI/App Server, IABV or Ollama process was started; no tests, builds or runtime/transport actions occurred; no code, local configuration, credentials, models, GPU settings, branches or local worktree were modified.

## One next action and acceptance criterion

**Next actor:** the actual owner-controlled IABV governance/administrative surface or its responsible governance operator, whose identity/interface remains `UNRESOLVED` from the surfaces examined here.

**Next action:** identify that real interface/operator and verify whether it can provide a scoped read decision for the verified MCP server and checkout. Required evidence: trusted issuer/principal; authenticated server plus root/checkout identity; exact operation and explicit paths; expiry/revocation; verification on each operation; durable verifiable receipt; and a separate authority/decision for releasing the applicable operational block. The read decision must not release its own block.

**Acceptance:** either the supported interface/issuer and applicable authority chain are identified and a verifiable decision/receipt can be demonstrated within authorization, or a bounded inventory of a newly named surface records `NOT_FOUND` for that surface. Until then retain `GLOBAL_ROUTE_EXISTENCE=UNRESOLVED` and the states above. Do not repeat the ordinary IABV general-chat scan, retry the denied reader, route around the gate, or advance to M2.

## Coordination and parked ideas

This step applied the coordination rule by advancing one new bounded evidence check, not repeating the prior general scan. The single active task remains M1. Parked items remain: (1) Ollama startup/RAM and lazy-versus-eager inference; (2) the inferred “Ollama wins for general” claim, eight-proposal count, three discarded-candidate count and `probe_consumed` semantics; (3) IABV's unverified claims about source/GPU/model/credential changes and 282 modified files; and (4) implementation of a project coordinator/runtime, which remains documentation-only until separately authorized. None replaces M1.

`COORDINATION_METHOD=DOCUMENTED` · `COORDINATOR_RUNTIME=NOT_PROVEN` · `CAUSAL_CROSS_CHAT_REUSE=NOT_PROVEN`.


## Prepared next handoff — NOT DISPATCHED (destination must first be identified)

- **Routing status:** `PREPARED_NOT_SENT`.
- **Actor required now:** actual owner-controlled IABV governance/administrative surface or its responsible operator.
- **AI destination:** `DESTINO_NO_DETERMINABLE` from current evidence. Do not send this to IABV's ordinary general-chat route, Codex, Kilo or OpenCode as though any of them could self-authorize the blocked read.
- **Why this is the next edge:** M1 is not a source-analysis task until its trusted access route and independent block authority are established. More public-source review of the same proposal, or a reworded general prompt, would not change the failed precondition.
- **After M1 acceptance only:** Codex in its already-existing authorized interface may receive the separately bounded static-inspection handoff. Do not launch Codex CLI/App Server or any runtime.

### Exact request for the real governance surface/operator

> **IABV GOVERNANCE — IDENTIFY THE SUPPORTED SCOPED-READ ROUTE (M1; NO GENERAL SCAN)**
>
> Objective: identify the actual, already-supported administrative operation and responsible authority for the previously authorized, strictly read-only local source inspection. Do not infer or invent an API, permission, operator, issuer, receipt, or route.
>
> Return one of:
>
> - `SUPPORTED_ROUTE_IDENTIFIED`: name the existing interface/operation and its authoritative documentation; identify the trusted issuer/principal and how that identity is verified; bind it to the real MCP server and actual root/checkout; state the exact allowed read operation and path allowlist; specify expiry/revocation and verification on every operation; show the format and verification method of a durable receipt; and identify the independent authority and decision needed for the active `operational_block_active` block. The read decision must not release its own block.
> - `NOT_FOUND_IN_NAMED_SURFACE`: state exactly which administrative surface was examined, who was responsible for that surface, the bounded method/evidence used, and what capability was absent. This only supports a surface-bounded `NOT_FOUND`; leave `GLOBAL_ROUTE_EXISTENCE=UNRESOLVED` unless the competent authority establishes global non-existence.
> - `BLOCKED_OR_UNRESOLVED`: name the exact missing authority, identity, evidence or capability and stop.
>
> Restrictions: no broad source scan; no invocation of a local or alternative reader; no access to `data/`, SQLite, secrets, credentials or `.env`; no source/configuration changes, tests, builds, probes, process launches, Codex CLI/App Server, IABV/MCP or Ollama launch, model/GPU/credential changes, branch cleanup, merge, rollback or real transport. Do not treat conversational approval, observation permission, `approved=true`, or public source as repository-read authority.
>
> Required acceptance: an existing supported route and authority chain are documented with verifiable evidence, or a bounded negative result is returned for the named surface. Do not claim M1 complete from a proposed design or a promise to investigate later. Stop after this response and do not perform additional work.

### Handoff after acceptance — not authorized to execute yet

Only after the legitimate route and applicable independent block decision are verified should the coordinator prepare a new, separately scoped Codex handoff for static inspection of executor registration/caller/result/receipt/consumer and whitelisted non-secret effective policy. That later handoff must stop on denial and does not authorize implementation, tests, builds, process launch or real transport.

The request above is preserved as a prepared handoff. Its inclusion in this document does not identify a destination, dispatch the request, grant access, or change `GOVERNANCE=KEEP_BLOCKED`.
