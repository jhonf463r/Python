# Codex and IABV interaction learning receipt

Observed on 2026-11-07, America/Bogota. Source session `01a1b42f-26fb-7050-b9d6-b98d2d22c230`.
The Owner requested persistence of interaction lessons in GitHub and memory,
and authorized the isolated Entra pilot. This receipt is a candidate for
continuity adoption. CURRENT-STATE.md owns technical gate adjudication.

## Observations and evidence boundaries

The maintenance worktree was preserved with its uncommitted changes. The
ledger relocation validation reused the R5 offline harness and passed 547
tests. Source hashes were stable before and after that run.

Authorization work is isolated in a separate sparse clone based on
`bc2baf525a70d66628809360a197f25a069aa328`. Its local changes remain
uncommitted. Later candidate checks produced separate JUnit receipts. The
latest identity-focused run passed 172 tests comprising the Entra identity
verifier, read authorization and Owner merge verifier. The broader earlier
composition run passed 143 tests. These are different suite selections and
revisions. Counts must not be added or treated as a global acceptance result.

Native Windows testing exercised registered read_repo_file and
list_repo_directory handlers against a temporary directory, including root
enumeration and a root-identity mismatch. Authority providers in that test
were synthetic. Formal G1/G2/G3 and G4–G8 acceptance remains pending.

The Owner created a single-tenant pilot API and a separate pilot client.
Codex observed the IABV Owner user and its assigned IABV.Owner application
role. Codex configured API token version 2 and the Pilot.Approve delegated
scope with admin-only consent. The default Graph User.Read request was
removed from the pilot client. After the Owner's explicit confirmation,
Codex configured a native localhost redirect and observed successful
administrator consent for Pilot.Approve.

A loopback-only PKCE receiver was started for an actual Owner login.
It keeps tokens in process memory and writes a credential-free outcome
receipt. Microsoft initially displayed an account/password rejection for the pilot
Owner account. After the Owner completed sign-in, the loopback receiver
terminated successfully with OWNER_IDENTITY_VERIFIED at epoch 1794067656.
The observed real access token passed RS256 signature verification against
tenant-specific Microsoft keys, issuer, tenant, API audience, interactive
client, immutable Owner object ID, delegated Pilot.Approve scope, IABV.Owner
role and time validation. A credential-free receipt and browser success page
were observed. Tokens were retained only in process memory. This establishes
a bounded real Owner-identity observation. Challenge-bound root approval,
protected issuer enrollment and formal gate acceptance remain pending.

Tenant, account and application identifiers, credentials, tokens, login
URLs containing transient state, and private root identities are omitted.

## Operational lessons for later Codex sessions

1. Revalidate actual capabilities in the current session. Shell access,
   browser control, signed-in state, app inventory, tool availability and
   product authority are distinct observations.
2. Both browser and native UI initialization previously failed with
   `failed to write kernel assets` and Windows `os error 3`. Session-level
   reset did not repair it. After the Owner restarted the desktop app,
   cua.getState and browser navigation succeeded. A restart is a supported
   recovery candidate for this failure pattern. The exact missing path and
   root cause were not established.
3. The in-app browser can navigate Entra using the user's signed-in
   session and operate forms. Create or bind the intended tab, inspect
   current state after actions, and verify the resulting resource or
   success message. Reacquire bindings after a JavaScript kernel reset.
   Preserve needed tabs with markDeliverable or markHandoff each turn.
4. A new chatgpt.com tab in the in-app browser loaded successfully and
   exposed its composer and login controls. Page-defined tools advertised
   conversation-state inspection, model listing, drafting, submission and
   generation status. The tab was signed out. Authenticated sending,
   response completion, account quotas and coordination remain untested.
   A working browser route is sufficient reason to try this realization
   before restarting failed routes in other browsers.
5. Before any dispatch, recover existing assignments and terminal results
   to prevent duplicate work. Use only a current tool inventory. For web
   page tools, fetch the current WebMCP tools before invoking them. Inspect
   acceptance and terminal response separately. A dispatched send is not a
   completed result.
6. Reuse authorized actions and prepare reviewable changes before asking
   for confirmation. Browser action-time confirmations still apply to
   legal acceptance and material security-access grants. User authentication
   may require the Owner's password or MFA interaction in the target page.
   Keep credentials out of chat, receipts and public source control.
7. A second ChatGPT conversation can be a coordination surface once its
   authenticated behavior is verified. Its context separation and source
   retrieval must be recorded before claiming independent review. A new
   tab alone does not establish independent review.
8. Store source revisions, patch hashes, suite scope and limitations with
   each result. Distinguish identity verification, explicit approval,
   root/handle provenance, catalogue authority, revocation and runtime
   acceptance. Additional green synthetic tests cannot establish missing
   production authority.

## Current frontier and executable handoff

IA DESTINO is the current Codex session. Its capability is local source
editing and testing, GitHub connector access, and verified in-app browser
navigation. The immediate task is to bind an explicit Owner root approval to a fresh
enrollment challenge through the independently protected issuer. The prior
login verified identity. Its credential-free receipt is a local observation
and cannot substitute for the signed assertion in a later enrollment.

Recover the existing login process and receiver state before starting
another attempt. If the process has expired, generate fresh PKCE state and
a fresh bounded attempt. Never reuse an expired login URL. Read the current
canonical router and this receipt, inspect actual tool availability,
recover existing browser tabs and assignments, and preserve local changes.

After verified Owner identity, finish protected issuer and mandate
binding, authenticated active catalogue/revocation, host root-handle
provenance, replay/budget and durable receipt integration. Verify the full
gate matrix and obtain a reviewer with demonstrable context separation.
The subsequent independent verifier is DESTINO NO DETERMINABLE until a
suitable authenticated review surface is verified.

Persistence in GitHub makes this record retrievable. Runtime retrieval,
causal reuse in another session and automatic IABV learning remain
unverified and require later observation.

## Later enrollment correction in this session

The pending challenge manifest lacked the workspace, checkout and root
identifiers already required by the read mandate. The isolated candidate
now uses manifest schema 3 and requires all three bindings in challenge
issuance, manifest validation and Owner approval evidence. Older schemas
are rejected and require a new challenge. Tests cover substitution of each
binding. The combined enrollment, Entra identity and read-authorization
selection passed 175 tests. This is candidate verification.

The cumulative local patch SHA-256 is
`6c811dc6ed987f81fd6b5bdbc736beca714577b9e8bce658dcb2babb1d8eb8e5`.
Reverse-application checking succeeded against the exact local source.
The source candidate remains uncommitted and requires integration review.

## Verified two-account browser round trips

A later observation in the same Owner session verified signed-in ChatGPT
in the in-app browser and Opera. Visible account menus showed distinct
selected account identifiers. The identifiers were compared in memory
and are omitted from this public receipt.

Codex sent one bounded connectivity prompt in each session. The in-app
browser response completed with IABV_COORD_PRIMARY_READY. Opera's response
completed with IABV_COORD_SECONDARY_READY. Both completion states and
rendered replies were observed. These tests establish observed authenticated
send/response capability for those two sessions at that time. They do not
measure quotas, sustained concurrency or independent source review.

Opening another tab in the same browser does not create an isolated account.
The verified realization for a second account was Opera's existing separate
profile/session. No account was signed out. Preserve current session bindings
and verify availability again before dispatch.

WebMCP tools advertised earlier on signed-out ChatGPT were unavailable in
the later authenticated in-app document. Codex used the observed UI composer
and send controls, then inspected terminal response state. Never assume
an earlier advertised page-tool list remains callable after login/navigation.

The next coordination step can use these verified sessions for bounded
contract questions or source review after explicit task scope and context
separation checks. Before a new task, recover prior assignments and results.
Keep authenticated send/response proof separate from IABV runtime dispatch
and causal learning.
