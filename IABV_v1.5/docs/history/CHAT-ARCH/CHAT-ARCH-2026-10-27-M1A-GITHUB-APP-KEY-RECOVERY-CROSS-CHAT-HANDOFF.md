# IABV → Codex bridge — cross-chat handoff: GitHub App key recovery and continuity (2026-10-27)

- Date: 2026-10-27, America/Bogota.
- Type: supporting handoff and unresolved-task receipt; documentation only.
- Scope: this conversation’s GitHub approval-app setup, local key validation attempts, continuity failures to avoid, and next discriminating action.
- Canonical route authority: [CURRENT-STATE.md](./CURRENT-STATE.md). Re-fetch it from live `main` at the beginning of any new session.
- This handoff is a candidate on branch `chat-continuity-key-recovery-handoff-20261027`, based on live `main=f5e5643df9dbf2a9c10e4d950275b8b28459d1ed`. It is not itself canonical until accepted through the repository’s normal review process.
- Related ongoing design history: [PR #546](https://github.com/jhonf463r/Python/pull/546), still open/draft/unmerged. Its current design draft contains the earlier app-setup chronology and sections 22–29, but this new handoff supersedes their scattered key-recovery instructions for the next chat.

## 1. Required startup protocol

Before taking any material action:
1. Fetch live `main` and read [CURRENT-STATE.md](./CURRENT-STATE.md) first. Its blob was `7a261129c8611cc0b5ed3788fc00c5d90ae189ea` when this handoff was prepared; re-fetch rather than trusting the recorded SHA.
2. Re-check the exact current PR heads and only the files required for the active edge.
3. Use the facts and stop conditions below; do not repeat already failed attempts, and do not promote a draft receipt into operational authority.
4. Classify owner-reported output separately from independently verified GitHub/API facts and inferences.
5. One discriminating action per iteration, preserve the exact error, and verify any documentation write by fetching the exact final blob.
6. Explain in plain Spanish what is happening and why. Prefer AI/local-tool execution for work the assistant can safely perform; ask the Owner only for the irreducible interactive step. Do not make the Owner repeat a previously attempted action without new evidence that the precondition changed.

## 2. Current canonical project state

Live main at preparation: `f5e5643df9dbf2a9c10e4d950275b8b28459d1ed`.
Canonical `CURRENT-STATE.md` blob at preparation: `7a261129c8611cc0b5ed3788fc00c5d90ae189ea`.

The current-state authority says:
- Active frontier: `G1_INDEPENDENT_ROOT_MANDATE_AND_VERIFICATION_CHANNEL`.
- `G1/G2/G3=NOT_ESTABLISHED`.
- `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`.
- `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`; this is not proof that assets do not exist.
- `PROTECTED_READS=FAIL_CLOSED`.
- `TESTS=NOT_RUN; RUNTIME=NOT_RUN`.
- `AUTOMATIC_FOLLOW_ON=FALSE`.
- `BRIDGE=BRIDGE_NOT_READY`.

Never claim that a GitHub App, a public key, an authenticated browser session, or a local private key by itself establishes G1/G2/G3. A connector’s GitHub authority does not automatically transfer to IABV or the Windows reader.

## 3. GitHub approval App — confirmed configuration

The Owner explicitly authorized adopting the GitHub owner account and private repository as a candidate external authority source for an IABV approval relay. This is a governance choice, not completed host/issuer/reader enrollment.

The app was registered through the authenticated browser automation, and the subsequent installation result reported success on 2026-10-27:

- Owner: `@jhonf463r`, GitHub user ID `28608338`.
- Repository: `jhonf463r/Python`, repository ID `860009771`, private, Issues enabled.
- App name/slug: `iabv-approval-relay-20261027`.
- App ID: `5496678`.
- Installation ID: `175851462`.
- App settings: https://github.com/settings/apps/iabv-approval-relay-20261027
- Install scope: `Only select repositories`; only `jhonf463r/Python`.
- App permissions: `Metadata: read`, `Issues: read/write`; all other repository/organization/account/enterprise permissions are `No access`.
- Webhook inactive; no webhook URL, secret or events.
- OAuth user authorization and Device Flow disabled; no callback or post-install setup URL.
- The automation did not generate or download a private key. Afterwards, the Owner reported generating a key through GitHub but being unable to download it while being able to copy a visible “number”. The exact label of that copied value has not been verified.

These app/install details were confirmed by the browser-automation result. Do not overstate them as a successful App API preflight: no valid PEM was provided to the local preflight and no GET /app or installation-token exchange was performed using this key.

## 4. Private-key episode — chronology and exact meaning

### Owner report

The Owner said GitHub would not let them download the private key and would allow copying a visible number/value. The assistant repeatedly told them to download the PEM again; that was a continuity error. Do not repeat the same download instruction without first investigating what happened in the browser and identifying the visible field’s actual label.

### Local Codex observations

- Codex reported running locally on Windows 10, host label `MSI`, as `MSI\\faber`.
- Codex observed two `python -m iabv_v15` processes under the same Windows user. This shows the observed processes shared that identity at that moment; it does not establish future service/task identity or DPAPI integration.
- First UI controller failed to initialize, with `failed to write kernel assets: El sistema no puede encontrar la ruta especificada (os error 3)`. No file was selected/read during that attempt.
- The native Windows file picker then worked. The Owner selected a Notepad `.txt` file. Its content was read only inside the local process; no secret or full path appeared in output.
- Codex reported the selected file content had length 40 characters, no BOM, no newline, and no recognized PEM label.
- The script correctly used `System.IO.File.ReadAllText($selectedPath)` and passed the resulting text to `RSA.ImportFromPem($pem)`; it did not pass the path as the PEM content. Do not repeat the path-versus-content hypothesis as if established.
- PowerShell 7.6.5 / .NET 10.0.11; the method `RSA.ImportFromPem` threw `System.ArgumentException`: “No supported key formats were found. Check that the input represents the contents of a PEM-encoded key file, not the path to such a file. (Parameter 'input')”.
- OpenSSL was not installed; nothing was installed.
- No local public-key fingerprint was calculated, no GitHub fingerprint was compared, no key was encrypted/stored, no JWT or installation token was created, and no GitHub API preflight was performed.
- No files/configuration/ACLs/GitHub content were modified. The 40-character text file was not changed.

### Supported conclusion

The selected TXT’s 40-character content was not a complete PEM private key accepted by the API. Its semantics are unknown: do not assume it is a fingerprint, key ID, or any specific value until the field label is checked in GitHub UI. The failed import does not establish that the GitHub-side keypair is invalid; it establishes that this selected file is not the full recognizable PEM expected by `RSA.ImportFromPem`.

Changing `.txt` to `.pem` would only change the extension. It cannot turn a fingerprint, ID or partial value into the private key. The private key cannot be reconstructed from the public-key fingerprint.

## 5. Current next action — consume the pending Codex download investigation

The last prompt given to Codex was to **investigate existing downloads and the GitHub UI label**, not to validate the same 40-character TXT again. The Owner said they will provide Codex’s result. At handoff creation, that result has not yet been received in this conversation. Therefore:

1. Wait for/read the Owner’s next Codex report and reconcile it here. Do not automatically start another browser/Codex task before evaluating that result.
2. Codex should have checked the relevant Opera download history and the current Windows user’s Downloads folder in a bounded way, without broad disk inventory or disclosing private paths.
3. Codex should have identified the actual label associated with the copied 40-character item, without copying the value into a transcript or log.
4. If a previously downloaded PEM exists, use that original file for local validation; do not ask the Owner to repeat a download operation.
5. If no PEM exists and local browser evidence shows the download did not complete, report the exact observed cause. Only then consider creating a replacement key and troubleshooting the browser download with explicit Owner involvement. Preserve existing keypair entries until a replacement has been validated and securely stored; do not revoke or delete automatically.
6. If the “number” is only a fingerprint/key identifier, explain plainly that it cannot authenticate as the private key and cannot recreate that key.
7. Do not install OpenSSL, change browser/security policies, use secret-sharing websites, or ask the Owner to paste the PEM into ChatGPT/Codex chat. A private-key file should be read by a local process from the selected file path.

## 6. Local key verification — only after locating a real PEM

If and only if a candidate PEM file is found:
1. Use a local, safe validation method compatible with PowerShell 7.6.5/.NET 10.0.11. Read the file into process memory without printing/logging the contents. Do not treat the suffix `.pem` as proof of validity.
2. Calculate the public-key fingerprint locally using the GitHub-documented SHA-256/Base64 digest of the DER public key, and compare it against the fingerprint displayed for the corresponding key in Credentials → Key pairs.
3. Exact match is required before storing or using the private key. If the local key fails validation, the fingerprint differs, or the GitHub UI fingerprint cannot be obtained, stop and report the actual evidence. Do not revoke or replace keys automatically.
4. Determine the real Windows principal that will run IABV. The observed same-account processes alone do not prove how the reader consumes a stored secret. Do not claim DPAPI CurrentUser is integrated until the consumer implementation is verified.
5. Only after key validation and runtime-principal assessment should a separate bounded action authorize secret storage and a minimal App API preflight. Tokens/JWTs must remain ephemeral in memory, never appear in output, and never be persisted.

Official GitHub reference: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps.

## 7. Wallet and helper-account fallback

Latest observed TinyFish wallet snapshot: `US$4.52`, auto-reload unconfigured, no pending top-up, as of `2026-10-27T15:49:54.976Z`. Observed rates then: Agent `US$0.016/step`, Browser `US$0.002/minute`. These are automation credits, unrelated to GitHub, the App installation, or IABV itself. This is a timestamped observation, not a perpetual balance.

Before every long browser automation:
- Fetch the current balance/rates and estimate the cost; preserve at least 25% buffer plus US$0.50 remainder. If below that, pause and present options before starting. Do not begin a task likely to exhaust the balance mid-way.
- If the wallet blocks execution, preserve the last verified state and do not retry unchanged actions.
- A helper’s automation account may be used only with the Owner’s explicit authorization for the task and that helper’s own consent and separately authenticated profile. Never ask for/share passwords, MFA codes, sessions, cookies, private keys or tokens; never change accounts to bypass a security gate or billing restriction. GitHub ownership, repository ownership, App and installation remain under `@jhonf463r`.

## 8. Lessons to prevent repeated failures

- Do not repeat an action the Owner already said failed. First inspect the evidence to identify why.
- Distinguish the file extension from file contents; distinguish GitHub key ID/fingerprint from a private-key PEM. Never guess the semantics of a copied value.
- Keep the error’s actual inner type/message. `MethodInvocationException` alone was too broad; the later result narrowed the reason to unrecognized PEM content but did not make it a valid key.
- Local success at one stage is not success at the next: picker opened ≠ file valid; file valid ≠ fingerprint match; fingerprint match ≠ protected custody; custody ≠ App API preflight; App preflight ≠ G1/G2/G3; none of these alone means bridge ready.
- Prefer Codex/local tools for tasks the AI can perform, but never push a secret into model context just for convenience. Make the Owner’s manual action as small as selecting an actual file or completing a genuine security prompt.
- Keep a one-action-per-iteration protocol; record result/error; make one material change; fetch back any durable record.
- Separate chronology from current state: historical PR notes can say “not created” at their time, while this newer handoff carries later App installation facts.
- Do not modify `main`, `CURRENT-STATE.md`, code, permissions, tests, runtime, protected reads, merge or rebase under this handoff. This document is documentation only on a branch until reviewed.

## 9. Live refs at preparation and candidate PRs

Re-fetch before relying on these refs:
- `main=f5e5643df9dbf2a9c10e4d950275b8b28459d1ed`.
- `CURRENT-STATE.md` blob on main: `7a261129c8611cc0b5ed3788fc00c5d90ae189ea`.
- PR #531: open/draft/unmerged, head `bc2baf525a70d66628809360a197f25a069aa328`.
- PR #546: open/draft/unmerged; at this handoff preparation its head was `52efa8d77a815408bf2f0e0529ccf5947be719b7`. Sections 22–29 contain the more detailed app/key chronology. PR #546 is not authority for the canonical route.
- PR #547: open/draft/unmerged, head `9b60d787528a5199c36b59a6c172f860c4bd6a86`; its research topic is not the active bridge key-recovery route.

## 10. Current status snapshot

```text
OWNER_ADOPTION_OF_GITHUB_AS_IABV_AUTHORITY=AUTHORIZED; DATE=2026-10-27
GITHUB_APP=CREATED; NAME=iabv-approval-relay-20261027; APP_ID=5496678
GITHUB_APP_INSTALLATION=INSTALLED; INSTALLATION_ID=175851462
GITHUB_APP_REPOSITORIES=ONLY:jhonf463r/Python; REPOSITORY_ID=860009771
GITHUB_APP_PERMISSIONS=METADATA_READ; ISSUES_READ_WRITE; ALL_OTHERS_NONE
GITHUB_APP_WEBHOOKS=DISABLED; OAUTH=DISABLED; DEVICE_FLOW=DISABLED
PRIVATE_KEY_PEM_LOCATED=NOT_CONFIRMED
SELECTED_TXT_LENGTH=40; PEM_MARKERS=ABSENT
SELECTED_VALUE_LABEL=UNKNOWN; VALUE_IS_FINGERPRINT=NOT_CONFIRMED
PRIVATE_KEY_VALIDITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT=NOT_OBTAINED; MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
NEXT_ACTION=AWAIT_CODEX_REPORT_ON_BROWSER_DOWNLOADS_AND_GITHUB_FIELD_LABEL
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
BRIDGE=BRIDGE_NOT_READY
```

This handoff is a supporting memory and route aid, not a replacement for `CURRENT-STATE.md`. Keep the repository free of secret material.