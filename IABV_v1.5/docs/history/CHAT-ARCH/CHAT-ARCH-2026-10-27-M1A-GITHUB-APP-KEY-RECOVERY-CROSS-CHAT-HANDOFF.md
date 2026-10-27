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

## 5. Current next action — inspect authenticated GitHub field and download behavior

The latest Codex report has now been received and incorporated. Do not wait for or request the same report again. Codex checked the current user’s Downloads folder and Opera histories:
- No PEM was found in the checked Downloads folder.
- Opera GX history was accessible read-only and contained no matching PEM/app-key download in the checked period.
- Opera Stable history returned a database-locked error and was not bypassed.
- The authenticated GitHub Credentials → Key pairs page could not be inspected, so the label of the Owner’s copyable 40-character value remains unknown.
- Selecting the same TXT again returned the same non-PEM text. Do not select or validate that same file again.

Next action:
1. Inspect the exact label next to the copyable value in the authenticated GitHub App UI, without copying its value to chat or transcript.
2. Inspect the actual New key/download interaction and browser state. The specific cause of the unavailable download remains UNKNOWN; do not assume it was blocked or that a download definitely never occurred.
3. If the item is a fingerprint or key ID, explain that it is not a private-key PEM and cannot reconstruct the private key.
4. Only if the UI/download investigation confirms that no usable PEM exists, consider a replacement key and handle download troubleshooting as one bounded action. Preserve existing GitHub key entries until a replacement is validated and safely stored; never revoke automatically.
5. Do not ask the Owner to repeat generic download instructions, paste any secret into chat, or copy the 40-character value again.

A local-only popup for secret input may be a future UX for a complete secret that is genuinely available. It is not a recovery method for a missing PEM or an unknown 40-character value. See section 11 for the complete latest evidence and the distinction between the GitHub App machine key and website credentials managed by IABV.

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
OPERA_GX_HISTORY=CHECKED; NO_MATCHING_PEM_DOWNLOAD_FOUND_IN_CHECKED_PERIOD
OPERA_STABLE_HISTORY=LOCKED; NOT_BYPASSED
LOCAL_DOWNLOADS_PEM=NONE_FOUND_IN_CHECKED_FOLDER
SELECTED_TXT_LENGTH=40; PEM_MARKERS=ABSENT
SELECTED_VALUE_LABEL=UNKNOWN; VALUE_IS_FINGERPRINT=NOT_CONFIRMED
DOWNLOAD_CAUSE=UNKNOWN
PRIVATE_KEY_VALIDITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT=NOT_OBTAINED; MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
NEXT_ACTION=INSPECT_AUTHENTICATED_GITHUB_FIELD_LABEL_AND_NEW_KEY_DOWNLOAD_BEHAVIOR
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
BRIDGE=BRIDGE_NOT_READY
```

This handoff is a supporting memory and route aid, not a replacement for `CURRENT-STATE.md`. Keep the repository free of secret material.

## 11. Latest Codex result and revised next action (2026-10-27, 10:56–11:00 America/Bogota)

### New Codex report — downloads and browser history

At approximately 10:56 America/Bogota, Codex reported:
- The Downloads folder for `MSI\\faber` exists and has no `.pem` files and no recent `.txt` filenames suggestive of a GitHub App key.
- Opera GX's local history database was read-only accessible; it showed no matching download for a `.pem` or this App's settings path since 2026-10-26 UTC.
- Opera Stable's history database returned `OperationalError: database is locked`; the agent did not bypass the lock.
- It could not access the authenticated GitHub UI path Credentials → Key pairs, so the label of the visible copyable value remains unknown.
- No local PEM was located in the bounded locations. This does not establish that no PEM exists elsewhere, nor whether the download failed, was blocked, or never registered in the available history.
- No keys were generated, read, copied, encrypted, persisted or transmitted, and no repository/browser configuration was changed.

At approximately 11:00, the Owner asked for the selector to be opened again and selected the same text file. The result was unchanged: the content was not accepted as PEM by `RSA.ImportFromPem`. Do not ask the Owner to select the same 40-character TXT again. This step adds no new evidence about the GitHub keypair.

### Architectural decision: a local secret-entry window is a design option, not a substitute for the missing PEM

The Owner asks whether Codex/IABV should open a popup to paste a key and then save it securely, and whether the same mechanism should store credentials for websites administered by IABV.

Decision:
- A **local-only secret input window** can be a good long-term UX when a human really has the full secret value and the receiving process demonstrably keeps it outside model prompts, transcripts, application logs, crash dumps and remote telemetry.
- Such a window must submit secret material directly to a local vault/credential service, not back to the model. It must not echo the secret; use a masked input where appropriate, clear the control/clipboard after save, and report only success/failure and a non-secret credential handle. These properties need implementation and security testing; merely calling a window “secure” is not evidence.
- However, in the present GitHub App case, the full private PEM has not been found. The Owner only has a copyable 40-character value whose UI label is unknown, and the selected TXT contains no PEM markers. **A paste popup cannot turn a fingerprint, key ID or other unknown 40-character value into the private key.** Do not build that popup as a workaround for the missing material and do not ask the Owner to paste that number again.
- The immediate route is to recover or re-obtain the actual PEM through GitHub's supported private-key generation/download flow, after inspecting the precise UI label and download behavior in an authenticated browser session. Because the Owner already reported the download was not available, do not repeat generic “download it” instructions. Diagnose the browser interaction/download path or use another already-available authenticated browser if the Owner has one; do not change security policies silently.
- GitHub states that creating a private key downloads a PEM to the computer and that GitHub stores only the public part; its displayed fingerprint is for matching an existing local PEM and cannot reconstruct the private key. Reference: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps.

### Separate the two secret-management cases

1. **GitHub App private key:** machine/application credential. Prefer an OS-backed secret store or encrypted local storage whose consumer identity is proven. Do not expose the raw PEM to the model. A local-only prompt/modal is acceptable only as an input adapter that directly persists to the local vault; it cannot replace obtaining the actual PEM.
2. **Website/user credentials managed by IABV:** use the existing approved credential-management architecture if one is verified in source. Prefer Windows Credential Manager/DPAPI or a purpose-built vault with least privilege and a non-secret handle returned to IABV; do not create a second ad hoc vault or put passwords/cookies/tokens in GitHub Issues, source files, memory documents or chat. A browser automation profile/session is distinct from storing reusable site passwords. Site-specific consent, scope, revocation and audit need separate rules.
3. Do not implement either vault or modify runtime/source under this documentation-only handoff. First inspect the existing credential/secret organs and consumers, and choose reuse over creating a new subsystem. Local secret input, vault persistence, runtime access, audit and revocation are separate acceptance stages.

### Revised next discriminating action

The newly supplied Codex report has now been consumed; there is no longer a pending report from the prior search task. Next:
1. In the user's currently authenticated GitHub session, determine the exact UI label of the 40-character value without asking the Owner to copy the value or exposing it to the model.
2. Inspect the actual New key/download interaction and its resulting browser state. The bounded Opera history checks found no successful PEM download in GX and Stable history was locked; do not assert a confirmed failure reason.
3. If the UI identifies the value as a fingerprint/key ID, classify it correctly and stop treating it as candidate key material.
4. Only pursue a new key generation if the app UI confirms no usable local PEM exists and the download mechanism can be observed/controlled. Prefer a local browser Save As/download flow into a known secure directory, then verify the actual file exists before selecting it. Keep the prior GitHub key entry until a replacement PEM is locally validated and its fingerprint matches; only then plan safe rotation. Never revoke automatically.
5. On success, perform structural validation plus fingerprint comparison before storage. Then separately assess Windows runtime identity and secret custody. Do not generate a token or call the GitHub App API until those gates are met.

### Updated state

```text
OPERA_GX_HISTORY=READ_ONLY_CHECKED; NO_MATCHING_PEM_DOWNLOAD_FOUND_SINCE_2026-10-26_UTC
OPERA_STABLE_HISTORY=DATABASE_LOCKED; NO_BYPASS
DOWNLOAD_CAUSE=UNKNOWN
LOCAL_DOWNLOADS_PEM=NONE_FOUND_IN_CHECKED_FOLDER
GITHUB_KEY_UI_LABEL=NOT_VERIFIED
OWNER_COPYABLE_40_CHAR_VALUE=SEMANTICS_UNKNOWN; NOT_KEY_MATERIAL_UNLESS_PROVEN
PEM_FILE_AVAILABLE=NOT_CONFIRMED
PEM_VALIDITY=NOT_VERIFIED
FINGERPRINT=NOT_OBTAINED; MATCH=NOT_VERIFIED
KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_API_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
NEXT_ACTION=INSPECT_AUTHENTICATED_GITHUB_FIELD_LABEL_AND_DOWNLOAD_INTERACTION
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```


## 12. Decisión del Owner sobre ventana local de secretos y credenciales web (2026-10-27)

### Decisión recomendada

No abrir todavía una ventana para pegar el valor de 40 caracteres. El Owner pidió que Codex/IABV realicen el trabajo de forma más automática y eviten pasos repetidos. La mejor ruta es una arquitectura de entrada local de secretos, pero no debe confundirse con la recuperación de esta clave que aún no está disponible.

**Para la GitHub App de este episodio:**
- Una ventana local de entrada sería válida solo si el Owner ya dispone del PEM completo, pero no lo tiene localizado.
- La interfaz de GitHub normalmente descarga el PEM en el momento de crear la clave y muestra un fingerprint para comprobar la correspondencia. GitHub conserva la parte pública, no la clave privada. No debe suponerse que el valor de 40 caracteres sea el fingerprint, un key ID o la clave privada hasta comprobar la etiqueta real.
- Pegar el valor de 40 caracteres en una ventana no lo convierte en el PEM. La prioridad es abrir la sesión local autenticada de GitHub, identificar el rótulo exacto y observar el estado real de la descarga. Si la sesión no está autenticada, permitir que el Owner complete el login/MFA en esa interfaz local; no solicitar códigos ni contraseñas por chat.
- No repetir la selección del TXT ni intentar leerlo otra vez: ya sabemos que tiene 40 caracteres sin estructura PEM.
- No generar una clave sustituta en esta etapa de diagnóstico. Si tras inspeccionar la UI se confirma que no existe PEM local y la clave debe sustituirse, tratar la generación y descarga como una acción separada y controlada, verificar inmediatamente que el archivo ha llegado al Windows local y preservar cualquier clave anterior hasta validar la nueva.

### Diseño objetivo para secretos de IABV

La solución a largo plazo sí debe reducir la carga manual mediante un **secret-entry local-first** y un almacén de credenciales protegido, pero reutilizando el órgano de credenciales existente de IABV en vez de crear un segundo vault prematuramente.

Propiedades obligatorias de una futura ventana local:
1. Se ejecuta en el Windows local y su control de entrada entrega el secreto directamente a un proceso/servicio local de custodia.
2. El contenido no se envía al modelo, ni aparece en prompt, transcript, logs, crash reporting, Issues o documentos de memoria.
3. El programa devuelve solo un resultado no secreto (guardado/no guardado y un handle), nunca el valor ni un token.
4. Los secretos se cifran/protegen por el principal Windows autorizado; el acceso del proceso runtime se verifica antes de afirmar que una credencial está disponible.
5. No se lee ni se guarda en un vault una contraseña/cookie/token de una web solo porque IABV pueda navegar esa web. Se respetan consentimiento, alcance, caducidad y revocación. Para sesiones de navegador, se prefiere el perfil/almacén del navegador cuando sea suficiente.
6. La GitHub App private key y los secretos de cuentas web son clases distintas: la primera firma JWT como identidad técnica de una App; los segundos autentican al usuario/servicio frente a sitios concretos. No deben compartir permisos ni políticas por defecto.

Para la App, el orden es: obtener el PEM completo → validar su estructura localmente → comparar la huella con GitHub → demostrar el principal Windows runtime → persistirlo bajo custodia local → hacer preflight mínimo de API. Para cada credencial web, el orden es consentimiento/alcance → entrada local → almacenamiento protegido mediante provider existente → acceso por handle para el consumidor autorizado → auditoría/rotación/revocación. El éxito de una etapa no prueba la siguiente.

### Prompt siguiente para Codex local (sin crear claves)

Ejecuta esta tarea acotada en Windows. No cambies archivos del producto ni configuración de GitHub.

- Abre la sesión del navegador local de Windows que ya utiliza el Owner e intenta acceder a la página Credentials → Key pairs de la App existente.
- Si la página exige login/MFA, detente y presenta la interfaz local para que el Owner lo complete. No pidas credenciales en el chat ni compartas cookies/sesiones con otra cuenta.
- Identifica solo la etiqueta del valor que el Owner pudo copiar y el estado del botón/flujo de descarga. No copies el valor al transcript, al modelo ni a logs.
- Inspecciona si el navegador registró un bloqueo/aviso de descarga en el evento de New key anterior, si ese evento está disponible. No cambies silenciosamente configuración de seguridad.
- No generes otra clave, no revokes ninguna, no vuelvas a seleccionar el TXT de 40 caracteres y no intentes validar ese TXT.
- Devuelve: etiqueta exacta del campo (sin valor), si el UI muestra el fingerprint de alguna clave, si hay un PEM original local y el motivo de descarga disponible en la UI. Si el motivo no aparece, deja `DOWNLOAD_CAUSE=UNKNOWN`.
- No generes tokens ni llames a la API de la App.

### Estado

```text
LOCAL_SECRET_ENTRY_WINDOW=RECOMMENDED_AS_FUTURE_LOCAL_ONLY_INTERFACE; NOT_IMPLEMENTED
WINDOW_TO_PASTE_UNKNOWN_40_CHAR_VALUE=NOT_RECOMMENDED
WEBSITE_CREDENTIAL_STORE=REUSE_EXISTING_IABV_PROVIDER_FIRST; NOT_INSPECTED_IN_THIS_TASK
GITHUB_APP_PEM=NOT_LOCATED
SELECTED_TXT=40_CHARACTERS; PEM_MARKERS_ABSENT; DO_NOT_RESELECT
GITHUB_KEY_UI_LABEL=NOT_VERIFIED
DOWNLOAD_CAUSE=UNKNOWN
NEW_KEY_GENERATION=NOT_PERFORMED_BY_THIS_DIAGNOSTIC
PRIVATE_KEY_VALIDITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT_MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

This is supporting continuity on a review branch only; it does not replace `CURRENT-STATE.md` or authorize runtime/source changes.
