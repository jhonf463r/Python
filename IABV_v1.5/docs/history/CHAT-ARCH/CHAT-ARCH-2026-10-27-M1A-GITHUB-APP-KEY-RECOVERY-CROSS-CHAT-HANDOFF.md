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

## 5. Current next action — validate the newly obtained PEM, not the old TXT

The previous Codex browser-history investigation is complete. It found no PEM in the checked Downloads folder or matching Opera GX history; Opera Stable history was locked and was not bypassed. The authenticated GitHub Key pairs page showed that the 40-character value the Owner had copied is labeled **“Copyable key fingerprint”** and that no private-key download action is offered from that page. That visible value is the fingerprint field, not the PEM file. Do not select the old 40-character TXT again.

The Owner now reports they have obtained a `.pem` file through another option. That is a new artifact reported by the Owner; it has not yet been inspected or validated by Codex. The next action is to validate that new file locally and compare its public fingerprint with the registered key pair. Do not repeat the historical download investigation unless new evidence shows a new issue.

Use the focused local Codex prompt in section 13. Do not save/encrypt the key, create a JWT/token, call the App API, or modify the App until structural validity and exact fingerprint correspondence have been established.

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
GITHUB_KEY_UI_LABEL=Copyable key fingerprint; CONFIRMED_BY_READ_ONLY_BROWSER_INSPECTION
PRIVATE_KEY_PEM=OWNER_REPORTS_OBTAINED_VIA_ANOTHER_UI_PATH; NOT_YET_VALIDATED
OLD_SELECTED_TXT=40_CHARACTERS; PEM_MARKERS_ABSENT; DO_NOT_RESELECT
PRIVATE_KEY_VALIDITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT=NOT_OBTAINED; MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
NEXT_ACTION=VALIDATE_NEW_PEM_LOCALLY_AND_COMPARE_FINGERPRINT
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


## 13. Next Codex prompt — validate the newly obtained PEM (2026-10-27)

The Owner reports a new `.pem` file obtained via another GitHub UI option. This is a new fact reported by the Owner, not yet verified locally. The old TXT of 40 characters was not the key; read-only browser inspection confirmed its GitHub label is “Copyable key fingerprint” and no download action appears on the Key pairs page. Do not select the old TXT or repeat the old download workflow.

Use the following prompt in Codex running locally on Windows. Do not paste key material into the prompt.

```text
Estamos en el Windows local donde se ejecuta IABV. Quiero validar el archivo PEM nuevo que ya obtuve. No uses el antiguo TXT de 40 caracteres.

Contexto:
- GitHub App: iabv-approval-relay-20261027; App ID 5496678.
- Installation ID 175851462.
- Repositorio único: jhonf463r/Python; repository ID 860009771.
- La UI de GitHub muestra el campo de 40 caracteres como “Copyable key fingerprint”; ese valor no es el PEM.
- El nuevo archivo PEM aún no se ha validado.

Seguridad:
1. Confirma que la ejecución es local en Windows. Si es cloud/remota, detente.
2. Abre el selector nativo de archivos para que el Owner elija el PEM nuevo. No pidas pegar el contenido en el chat y no imprimas la ruta completa.
3. Lee el contenido solo en memoria con System.IO.File.ReadAllText($selectedPath), asegurándote de pasar el TEXTO a RSA.ImportFromPem, no la ruta.
4. Comprueba que el PEM contiene una clave RSA PRIVADA importable. GitHub descarga estas claves en formato PKCS#1 RSAPrivateKey. Informa solo de la etiqueta PEM (por ejemplo RSA PRIVATE KEY o PRIVATE KEY), si la importación funcionó, y el tamaño de clave. No muestres, registres ni transmitas el contenido, el bloque PEM, los parámetros privados, la ruta, el JWT o cualquier token.
5. Exporta en memoria la clave pública en formato DER SubjectPublicKeyInfo y calcula SHA-256 del DER; codifica el digest en Base64. Esto debe ser equivalente a la verificación oficial de GitHub: openssl rsa -in PATH_TO_PEM_FILE -pubout -outform DER | openssl sha256 -binary | openssl base64. No instales OpenSSL.
6. Si puedes consultar la UI de GitHub ya autenticada, encuentra la huella de la entrada existente y compara localmente. La inspección read-only de la UI identificó el campo como “Copyable key fingerprint”, pero no uses ni reportes su valor. No asumas que dos cadenas coinciden por longitud o aspecto: compara según el formato exacto que muestre GitHub y la documentación oficial. Si la huella no se puede obtener o los formatos no se pueden reconciliar inequívocamente, reporta la validez estructural por separado y deja MATCH=NOT_VERIFIED.
7. No imprimas ni registres el valor de ninguna huella completa; devuelve solo MATCH=YES/NO/NOT_VERIFIED. Nunca imprimas contenido o ruta del PEM. Si falla, captura solamente el tipo y mensaje sanitizado de la excepción.
8. En esta tarea NO cifres ni guardes la clave, no crees JWT ni installation token, no llames a la API de la App, no hagas cambios en GitHub y no revoques/sustituyas claves. El objetivo es solo: validar la estructura y comparar la huella.
9. No cambies archivos de producto, main, CURRENT-STATE.md, PRs, Issues ni comentarios. No ejecutes tests, build, runtime, lecturas protegidas ni transporte real.

Informe: ejecución local confirmada; tipo/etiqueta de clave; importación válida sí/no; huella local calculada sí/no; comparación exacta con GitHub sí/no/no verificable; error interno sanitizado si existe; confirmación de que el secreto no se expuso y no se guardó.

No afirmes que la clave está lista para IABV ni que el puente está listo. G1/G2/G3 siguen sin establecerse.
```

Referencia oficial: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps

Estado después del prompt:
- Si importación/huella pasan y coincide la huella, el siguiente paso será una autorización separada para custodia local y preflight de API.
- Si la estructura falla, reportar la excepción interna exacta sanitizada y no regenerar/revocar automáticamente.
- Si la estructura pasa pero la huella no puede compararse, no declarar que la clave pertenece a la App.



## 14. Latest Codex execution report — valid PEM; compare fingerprint locally (2026-10-27)

### Result received from local Codex

The Owner supplied the following Codex result. This is an owner-provided execution report; the assistant did not independently run the local Windows process.

- Local execution confirmed on Windows, machine label MSI, user MSI\faber.
- The native filtered file picker selected a PEM file.
- RSA.ImportFromPem accepted it as a private RSA PKCS#1 key of 2048 bits.
- The public fingerprint was computed in memory and neither shown nor persisted.
- GitHub fingerprint matching was not performed. Codex reported it had no authenticated comparison path that kept the value out of the transcript.
- No key custody/storage, GitHub changes, JWT, installation token, or API request occurred; repository/files were unchanged.

Supported state transition: PRIVATE_KEY_STRUCTURE=VALID; LOCAL_PUBLIC_FINGERPRINT=COMPUTED_IN_MEMORY; GITHUB_FINGERPRINT_MATCH=NOT_VERIFIED. This does not establish that the PEM belongs to the registered App.

### Important format constraint

Current official GitHub documentation says the App key fingerprint is SHA-256 and specifies this comparison algorithm:

    openssl rsa -in PATH_TO_PEM_FILE -pubout -outform DER | openssl sha256 -binary | openssl base64

Reference: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps

The earlier read-only UI observation reported a 40-character value labeled **“Copyable key fingerprint”**. A 40-character value is not the normal Base64 rendering of a 32-byte SHA-256 digest. Preserve this format discrepancy as unresolved; do not assume the formats match, silently switch algorithms, or report success based only on length/appearance.

### Next bounded action: compare from Windows clipboard, never transcript

Before running Codex, the Owner should open the already authenticated GitHub session in the **local Windows browser**, go to the App's Credentials → Key pairs page, and click GitHub's copy control for the displayed “Copyable key fingerprint”. Leave that copied text only in the Windows clipboard; **do not paste it into Codex, ChatGPT, a terminal command, an issue, or a file**.

Use this prompt in Codex running locally on Windows:

~~~text
Continuamos el diagnóstico local de GitHub App en Windows. El último resultado ya confirmó que el nuevo PEM es una clave privada RSA PKCS#1 válida de 2048 bits y calculó la huella local en memoria. No repitas pruebas sobre el TXT antiguo.

Preparación humana previa: ya pulsé el botón de copia del campo GitHub “Copyable key fingerprint” en el navegador local autenticado. El valor está únicamente en el portapapeles de Windows; no lo pegaré en Codex ni en el chat.

Objetivo único: comparar localmente la huella del PEM nuevo con el valor copiado desde GitHub, sin mostrar ni persistir ninguno de los dos.

1. Confirma que el proceso está en el Windows local, usuario MSI\faber. Si es remoto/cloud o no puedes confirmar el contexto local, detente.
2. Abre el selector nativo de archivos y permite seleccionar el PEM nuevo (NO el TXT anterior). Lee el contenido solo en memoria y confirma mediante RSA.ImportFromPem que sigue siendo una clave privada RSA importable. No imprimas la ruta completa ni contenido.
3. Calcula el formato documentado por GitHub: exporta la clave pública como DER SubjectPublicKeyInfo, aplica SHA-256 y codifica el digest en Base64. Todo en memoria. No instales OpenSSL ni escribas artefactos.
4. Lee el texto copiado mediante Get-Clipboard -Raw y guárdalo directamente en una variable local. No uses una expresión que lo muestre, no lo interpolas en errores, no lo imprimas, no lo captures en el output de Codex, y no lo escribas a disco. Tampoco imprimas ni registres la huella calculada localmente.
5. Comparación estricta: permite solo quitar espacios/saltos externos y un prefijo literal “SHA256:” si existe. Para comparar, acepta el Base64 de 32 bytes SHA-256 con o sin padding “=” final; no cambies mayúsculas/minúsculas ni apliques transformaciones heurísticas. Compara los bytes del digest o representaciones Base64 equivalentes en memoria.
6. Si el contenido del portapapeles tiene 40 caracteres u otro formato que no sea la huella SHA-256/Base64 documentada, NO pruebes algoritmos alternativos silenciosamente y NO declares coincidencia. Devuelve FORMAT_MISMATCH=YES; MATCH=NOT_VERIFIED, con solo metadatos no secretos (por ejemplo longitud y categoría de caracteres), nunca la cadena copiada. Si el formato sí es compatible y coincide, MATCH=YES. Si es compatible pero diferente, MATCH=NO. Si el portapapeles está vacío/no disponible, MATCH=NOT_VERIFIED.
7. Devuelve solo: LOCAL_EXECUTION=YES/NO; PEM_IMPORT=VALID/INVALID; RSA_BITS; LOCAL_FINGERPRINT=COMPUTED/NOT_COMPUTED; CLIPBOARD_FORMAT=SHA256_BASE64/OTHER/UNAVAILABLE; MATCH=YES/NO/NOT_VERIFIED; FORMAT_MISMATCH=YES/NO; SECRET_VALUES_EXPOSED=NO; SECRET_MATERIAL_PERSISTED=NO. Si falla, informa solo el tipo de excepción y un mensaje sanitizado que no incluya el valor del portapapeles, PEM, huellas o ruta.
8. No guardes ni cifres el PEM; no generes JWT ni installation token; no llames a ninguna API; no cambies GitHub; no revoques ni reemplaces claves; no cambies archivos/configuración del producto; no ejecutes tests/build/runtime/protected reads ni real transport.

No concluyas que la clave corresponde al App, que la custodia está resuelta, ni que el puente está listo salvo que el formato documentado sea compatible y la comparación exacta resulte MATCH=YES. Incluso entonces, detente aquí: custodia y API preflight son fases separadas y aún no autorizadas.
~~~

If the copied field remains 40 characters or otherwise cannot be reconciled with the documented SHA-256/Base64 format, stop at MATCH=NOT_VERIFIED and record the format discrepancy as an open question. Do not solve it by exposing the value, guessing its hash algorithm, or moving ahead to JWT/API preflight.

### Current status after this result

~~~text
LOCAL_WINDOWS_EXECUTION=CONFIRMED_BY_CODEX_REPORT; USER=MSI\faber
NEW_PEM=RSA_PRIVATE_PKCS1_2048; STRUCTURE_VALID
LOCAL_FINGERPRINT=COMPUTED_IN_MEMORY; NOT_PRINTED; NOT_PERSISTED
GITHUB_FINGERPRINT_LABEL=Copyable key fingerprint; READ_ONLY_UI_OBSERVATION
GITHUB_FINGERPRINT_MATCH=NOT_VERIFIED
FINGERPRINT_FORMAT_DISCREPANCY=OPEN; 40_CHAR_UI_VALUE_VS_DOCUMENTED_SHA256_BASE64
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; JWT=NOT_CREATED; INSTALLATION_TOKEN=NOT_CREATED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
BRIDGE=BRIDGE_NOT_READY
~~~



## 15. Latest Codex report — clipboard is not the fingerprint (2026-10-27)

### New result received from Owner

The Owner supplied the latest local Codex summary:

    LOCAL_EXECUTION=YES
    PEM_IMPORT=VALID
    RSA_BITS=2048
    LOCAL_FINGERPRINT=COMPUTED
    CLIPBOARD_FORMAT=OTHER
    CLIPBOARD_LENGTH=3734
    CLIPBOARD_CHAR_CLASS=OTHER
    MATCH=NOT_VERIFIED
    FORMAT_MISMATCH=YES
    SECRET_VALUES_EXPOSED=NO
    SECRET_MATERIAL_PERSISTED=NO

This supports that the new PEM remains structurally valid and that the compare attempt did not establish a match. The clipboard value is not the expected documented fingerprint representation. Its contents are unknown and must not be inferred from length/class alone. Do not read it into a transcript, echo it, write it to disk, or retry comparing it as if it were a fingerprint. The report says no values were exposed or persisted; this is a user-supplied Codex report, not independently observed by the assistant.

### Immediate next action

Use local Codex only to reset the current Windows clipboard to a harmless empty/marker value, without reading the previous clipboard content. Do not inspect or change clipboard-history/cloud-sync settings during this action. Do not save the old clipboard value to disk. If the user uses Windows clipboard history or sync, note that resetting the current clipboard does not itself prove historical copies were erased.

After reset, inspect the actual local GitHub page/control before attempting another comparison. Identify the visible label “Copyable key fingerprint” and the specific adjacent copy button via accessibility/UI automation. Do not click a generic page-copy or “copy all” control; do not select/copy the page, DOM, HTML, or entire row. Do not expose the field value to model output. If the exact adjacent copy control cannot be identified with confidence, stop with COPY_CONTROL_IDENTIFIED=NO; do not copy anything and do not fabricate a comparison.

If and only if the correct adjacent control is positively identified, click just that control locally, read clipboard contents directly into a local variable, and report metadata only. A valid value must be accepted only if it exactly conforms to GitHub’s documented SHA-256/Base64 fingerprint representation. If clipboard length remains 3734 or format class is OTHER, reset the clipboard again and stop. No alternate hashing guesses, no clipboard content output, no secret/token/API actions.

### Prompt for the next Codex local run

~~~text
Seguimos en Windows local, con la App GitHub iabv-approval-relay-20261027. El PEM nuevo ya está validado como RSA PKCS#1 privada de 2048 bits; no lo vuelvas a probar salvo que sea necesario para una comparación local.

La comparación anterior devolvió CLIPBOARD_FORMAT=OTHER, CLIPBOARD_LENGTH=3734, CLIPBOARD_CHAR_CLASS=OTHER, MATCH=NOT_VERIFIED. No se conoce el contenido. NO lo leas, lo imprimas, lo guardes ni lo describas. No vuelvas a usar ese contenido para comparar.

Fase A — mitigar clipboard:
1. Confirma ejecución local en Windows y usuario MSI\faber.
2. Sobrescribe inmediatamente el contenido ACTUAL del portapapeles por una cadena inocua fija, por ejemplo IABV_DIAGNOSTIC_CLIPBOARD_RESET. Hazlo sin leer el contenido anterior. No lo imprimas como resultado ni lo guardes en disco.
3. Devuelve únicamente CLIPBOARD_RESET=YES/NO. No cambies la configuración de Clipboard History/cloud sync ni inspecciones su contenido histórico.

Fase B — inspección del control, sin copiar todavía:
4. Abre/usa la sesión del navegador local ya autenticada en la página exacta Credentials → Key pairs de la App existente. No inicies sesión con otra cuenta ni solicites credenciales en el chat.
5. Mediante UI automation/accesibilidad identifica sin leer ni imprimir el valor de la huella: su etiqueta exacta “Copyable key fingerprint”, el contenedor de ese campo y el control de copia ADYACENTE. Distingue ese botón de los controles para copiar la página completa, el HTML, el nombre de la clave o cualquier otro dato.
6. En esta fase no hagas click en ningún botón de copia. No devuelvas screenshot, DOM, HTML, innerText ni atributo value que pueda incluir la huella. Devuelve solo COPY_CONTROL_IDENTIFIED=YES/NO y el nombre accesible del botón si se puede obtener sin incluir valores.

Si COPY_CONTROL_IDENTIFIED=NO, detente. No sigas probando controles al azar. Reporta el motivo concreto y pide al Owner una acción manual mínima para seleccionar el control correcto.

Fase C — solo si el paso B identificó inequívocamente el botón correcto:
7. Haz click SOLO en el control de copia adyacente a “Copyable key fingerprint”. No uses Ctrl+A/Ctrl+C, no copies el row ni la página.
8. Lee el portapapeles directamente en una variable local, sin imprimirlo, registrarlo, introducirlo en prompts, ni escribirlo a disco. Calcula solo longitud y clase de caracteres. Si no es inequívocamente el SHA-256/Base64 documentado por GitHub, devuelve CLIPBOARD_FORMAT=OTHER, MATCH=NOT_VERIFIED y FORMAT_MISMATCH=YES; vuelve a sobrescribir el portapapeles con la cadena inocua fija y detente.
9. Solo si el formato es compatible, calcula/reutiliza la huella local desde el PEM y compara todo en memoria, devolviendo MATCH=YES/NO/NOT_VERIFIED. Nunca muestres la huella completa ni el contenido del clipboard.
10. No guardes ni cifres la clave; no generes JWT ni installation token; no llames a la API de GitHub; no cambies GitHub, el repositorio ni archivos del producto; no ejecutes tests/build/runtime/protected reads/real transport; no revoques ni sustituyas claves.

Informe final: LOCAL_EXECUTION; CLIPBOARD_RESET; COPY_CONTROL_IDENTIFIED; CLIPBOARD_LENGTH; CLIPBOARD_CHAR_CLASS; CLIPBOARD_FORMAT; MATCH; FORMAT_MISMATCH; SECRET_VALUES_EXPOSED=NO; SECRET_MATERIAL_PERSISTED=NO. Si el control no se identifica inequívocamente, no continúes hacia la comparación.
~~~

### Current evidence state

~~~text
NEW_PEM=RSA_PRIVATE_PKCS1_2048; STRUCTURE_VALID
LOCAL_FINGERPRINT=COMPUTED_IN_MEMORY
LATEST_CLIPBOARD_READ=3734_CHARS; FORMAT_OTHER; CONTENT_UNKNOWN; DO_NOT_REUSE
GITHUB_FINGERPRINT_MATCH=NOT_VERIFIED
COPY_CONTROL_IDENTIFICATION=NOT_DONE
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; JWT=NOT_CREATED; INSTALLATION_TOKEN=NOT_CREATED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
BRIDGE=BRIDGE_NOT_READY
~~~



## 16. Latest live UI finding — fingerprint is plain code text (2026-10-27, 11:34 America/Bogota)

### Owner-reported local result

The Owner reported the local Codex result at 11:34:

    LOCAL_EXECUTION=YES
    CLIPBOARD_RESET=YES
    COPY_CONTROL_IDENTIFIED=NO
    CLIPBOARD_LENGTH=UNKNOWN
    CLIPBOARD_CHAR_CLASS=UNKNOWN
    CLIPBOARD_FORMAT=UNAVAILABLE
    MATCH=NOT_VERIFIED
    FORMAT_MISMATCH=NO
    SECRET_VALUES_EXPOSED=NO
    SECRET_MATERIAL_PERSISTED=NO

The local process says the current Windows clipboard was overwritten with a harmless marker without reading the former contents. It could not identify a dedicated copy control. No comparison occurred and no fingerprint match or mismatch was established.

### New read-only inspection on the authenticated GitHub UI

After first re-fetching live `main/CURRENT-STATE.md` (blob still `7a261129c8611cc0b5ed3788fc00c5d90ae189ea`), a separate read-only browser inspection was performed on the saved GitHub-signed-in browser profile at:

`https://github.com/settings/apps/iabv-approval-relay-20261027/key_pairs`

The browser task was constrained to page structure and accessible control metadata only. It did not click any copy/delete control or return the fingerprint value. Its result:

- The literal label **“Copyable key fingerprint” is not present** on the inspected page.
- The heading immediately above the fingerprint is **“Private key”**.
- The key entry/card includes a secondary label “Label: Private”.
- The fingerprint appears as plain text beginning with `SHA256:` inside an HTML `code` element.
- The entry also shows metadata of when/by whom the key was added.
- **No dedicated copy button, clipboard icon, or adjacent copy control is present.**
- The Delete button is disabled because this is the only private key; it was not clicked.

This newer inspection conflicts with the earlier observation that there was a 40-character “Copyable key fingerprint” field. Preserve that earlier observation as historical evidence of a discrepancy, not as the current confirmed UI structure. Do not continue referring to the visible value as a “copyable” field. The 3734-character clipboard result is compatible with an overly broad copy action, but its prior contents remain unknown; do not claim this inference is certain. The current clipboard reset was reported successful.

### Updated conclusion and next bounded action

The UI structure explains why trying to discover an adjacent copy button failed: the inspected page has no such control. Do not copy the page, card, DOM, or entire row, and do not retry ambiguous clipboard interactions.

Next, use Codex locally on Windows to read only the text content of the **specific `code` node whose enclosing card is headed “Private key” and contains the “Label: Private” metadata**, within the existing local authenticated browser session. Use a local accessibility/DOM inspection method that keeps the extracted string solely in the local process. Do not dump the DOM, page text, HTML, screenshot, node value, or fingerprint into Codex's response/transcript. Do not rely on or read the clipboard.

For the comparison:
1. Calculate/reuse the local public-key SHA-256 digest from the already validated PEM, in memory.
2. Read the single fingerprint text node locally. Require the `SHA256:` prefix. Remove only that exact prefix and surrounding whitespace.
3. Accept only the standard Base64 encoding of a 32-byte SHA-256 digest, either unpadded (43 Base64 characters) or with the single expected trailing padding character. Decode strictly and ensure exactly 32 bytes; reject any non-Base64 character or other length. Do not guess alternate hash algorithms or compare only textual lengths.
4. Compare the decoded bytes to the locally computed digest in memory. Return only `MATCH=YES`, `MATCH=NO`, or `MATCH=NOT_VERIFIED`; never print either value.
5. If the local browser/DOM/accessibility mechanism cannot unambiguously target that exact code node or keep the content out of the transcript, stop with `FINGERPRINT_NODE_IDENTIFIED=NO` and `MATCH=NOT_VERIFIED`. Do not fall back to clipboard or screenshots.

No PEM custody/storage, JWT, installation token, API call, app mutation, product source/runtime change, tests, protected reads, or transport is authorized by this step. Even a confirmed match is only identity binding for this key; custody and API preflight remain separate phases.

### Replacement prompt for local Codex

~~~text
Seguimos el diagnóstico de la GitHub App en Windows local. No repitas los intentos anteriores de copiar al portapapeles.

Hechos:
- El PEM nuevo fue validado localmente como clave privada RSA PKCS#1 de 2048 bits.
- La huella pública local ya fue calculada en memoria.
- El portapapeles se limpió con un marcador inocuo. No leas el contenido anterior ni vuelvas a usar clipboard para esta tarea.
- Una inspección read-only actual de la UI autenticada mostró que la página no tiene un botón de copia adyacente. El encabezado visible es “Private key”; el valor de huella se muestra como texto en un elemento HTML code dentro de la tarjeta “Label: Private” y comienza por “SHA256:”.
- No uses la antigua suposición “Copyable key fingerprint”; la observación anterior de 40 caracteres fue contradictoria y queda como histórica/no reconciliada.

ÚNICO OBJETIVO: leer localmente el contenido de ese único nodo code y compararlo con la huella pública local, sin que ningún valor aparezca en salida, prompts, logs, transcripción o archivos.

1. Confirma ejecución local en Windows como MSI\faber. Si el navegador no es local o no puedes usar la sesión autenticada existente, detente.
2. Usa la accesibilidad o DOM del navegador local para identificar la tarjeta cuyo encabezado es “Private key” y metadato secundario “Label: Private”; dentro de esa tarjeta, identifica el único nodo code correspondiente al fingerprint visible. No vuelques el DOM, innerText, HTML, capturas, valor del nodo, ni el texto completo de la página.
3. Si no puedes identificar con certeza ese único nodo sin mostrar su contenido, devuelve FINGERPRINT_NODE_IDENTIFIED=NO; MATCH=NOT_VERIFIED y detente. No uses clipboard ni copies la página.
4. Si se identifica el nodo, lee su contenido directamente a una variable local de proceso. Nunca imprimas, registres, persistas ni devuelvas ese valor.
5. Calcula o reutiliza en memoria el SHA-256 de la clave pública DER SubjectPublicKeyInfo del PEM validado. Mantén el digest como bytes.
6. Valida estrictamente el valor del nodo: debe comenzar por el prefijo literal “SHA256:”. Quita únicamente ese prefijo y espacios externos. El resto debe ser Base64 estándar que decodifique exactamente a 32 bytes; admite Base64 sin padding de 43 caracteres o con un único “=” final. No aceptes formatos alternativos ni algoritmos distintos.
7. Compara en memoria los bytes del digest. Informa solo FINGERPRINT_NODE_IDENTIFIED=YES/NO, LOCAL_EXECUTION=YES/NO, PEM_IMPORT=VALID/INVALID, RSA_BITS, LOCAL_FINGERPRINT=COMPUTED/NOT_COMPUTED, PAGE_FINGERPRINT_FORMAT=SHA256_BASE64/OTHER/UNAVAILABLE, MATCH=YES/NO/NOT_VERIFIED, SECRET_VALUES_EXPOSED=NO, SECRET_MATERIAL_PERSISTED=NO.
8. Si el formato no coincide o el acceso al nodo no es inequívoco, deja MATCH=NOT_VERIFIED; no improvises. Si coincide, detente igualmente tras informar MATCH=YES.

No guardes/cifres el PEM, no generes JWT ni token de instalación, no llames a la API, no cambies GitHub ni archivos, no revokes ni sustituyas claves, no ejecutes tests/build/runtime, lecturas protegidas ni transporte real. No afirmes que el puente está listo. G1/G2/G3 siguen sin establecerse.
~~~

### Current state after this inspection

    NEW_PEM=RSA_PRIVATE_PKCS1_2048; STRUCTURE_VALID
    LOCAL_FINGERPRINT=COMPUTED_IN_MEMORY
    WINDOWS_CLIPBOARD=RESET_MARKER_REPORTED; PRIOR_VALUE_NOT_READ_AGAIN
    CURRENT_GITHUB_UI=HEADING_PRIVATE_KEY; FINGERPRINT_IN_CODE_NODE_WITH_SHA256_PREFIX
    ADJACENT_COPY_CONTROL=ABSENT_IN_READ_ONLY_INSPECTION
    EARLIER_40_CHAR_COPYABLE_LABEL_OBSERVATION=CONTRADICTED_BY_LATER_INSPECTION; HISTORICAL_DISCREPANCY_OPEN
    GITHUB_FINGERPRINT_MATCH=NOT_VERIFIED
    PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
    GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; JWT=NOT_CREATED; INSTALLATION_TOKEN=NOT_CREATED
    G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
    PROTECTED_READS=FAIL_CLOSED
    TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
    AUTOMATIC_FOLLOW_ON=FALSE
    BRIDGE=BRIDGE_NOT_READY


## 17. Session closeout and next-chat routing (2026-10-27, Owner report 11:34 America/Bogota)

### Exact latest result supplied by Owner

```text
LOCAL_EXECUTION=YES
CLIPBOARD_RESET=YES
COPY_CONTROL_IDENTIFIED=NO
CLIPBOARD_LENGTH=UNKNOWN
CLIPBOARD_CHAR_CLASS=UNKNOWN
CLIPBOARD_FORMAT=UNAVAILABLE
MATCH=NOT_VERIFIED
FORMAT_MISMATCH=NO
SECRET_VALUES_EXPOSED=NO
SECRET_MATERIAL_PERSISTED=NO
```

Interpretation:
- The local task ran and reported that the current Windows clipboard was overwritten with a harmless marker without reading the prior contents.
- The exact copy control could not be identified. No further clipboard sample was taken and no fingerprint comparison occurred.
- `FORMAT_MISMATCH=NO` in this specific result means no new value was available to classify; it does **not** mean the formats matched. The latest determination remains `MATCH=NOT_VERIFIED`.
- The prior 3734-character `OTHER` clipboard sample remains unknown. Do not read, infer, recover, log or reuse its contents. The reported reset concerns the current clipboard only and does not establish deletion of any clipboard-history/cloud-sync copies.
- No private key, public fingerprint, token or key material was reported exposed or persisted.

### Reconciled evidence timeline — carry this into the next chat

1. **GitHub App exists, but is not an IABV trust root yet.** App `iabv-approval-relay-20261027`, App ID `5496678`, installation `175851462`, repository scope only `jhonf463r/Python` (repository ID `860009771`). Permissions remain Metadata read and Issues read/write; all others no access. Webhook/OAuth/Device Flow remain disabled. This is configuration evidence, not an App-auth preflight or G1/G2/G3.
2. **Old TXT is not the private key.** The earlier selected file held 40 characters and was rejected by `RSA.ImportFromPem`; do not repeat its selection. An earlier UI observation called a value “Copyable key fingerprint”, but that observation is contradicted by the later read-only page inspection recorded in section 16. Preserve the conflict as history instead of silently choosing the older observation.
3. **New PEM structure is valid, according to the Owner-provided local Codex report.** The file imports as private RSA PKCS#1, 2048 bits. Its public SHA-256 fingerprint was computed in local memory; no fingerprint value was shown or persisted.
4. **Clipboard is not a usable comparison path.** The earlier comparison returned `OTHER`, 3734 characters. The current clipboard reset was reported successful. The adjacent copy-control identification returned NO. Do not use clipboard again for the fingerprint workflow.
5. **Latest UI evidence changes the method.** Section 16 records a separate read-only browser inspection: heading “Private key”; secondary metadata “Label: Private”; fingerprint appears as plain text in a `code` element beginning with `SHA256:`; no adjacent copy button exists. This is the current route hypothesis, distinct from the Owner's just-reported result that Codex could not identify the control. The next discriminating action is local browser DOM/accessibility targeting of that exact code node, not copying UI.
6. **Fingerprint match has never succeeded.** Current state is `GITHUB_FINGERPRINT_MATCH=NOT_VERIFIED`. Do not say the PEM is wrong or right for this App until a strict byte comparison is completed. If the node cannot be uniquely identified and read only in local process memory, stop.
7. **Nothing beyond comparison is authorized/completed.** No private-key custody/storage, JWT, installation token, GitHub App API preflight, product change, protected read, tests, build, runtime or real transport. Even a future `MATCH=YES` does not grant authorization for those later stages.

### Next action — one bounded local test

Use section 16's replacement Codex prompt. The only objective is to:
- confirm local Windows context and reuse the already validated PEM;
- identify the one `code` node belonging to the card headed “Private key” and labeled “Label: Private” using local DOM/accessibility;
- read that single node's text directly into a local variable, never printing it or dumping page/DOM content;
- verify the literal `SHA256:` prefix and strict Base64 decoding to exactly 32 digest bytes (standard padded or unpadded form only);
- compare digest bytes locally and report only `MATCH=YES/NO/NOT_VERIFIED`.

No clipboard fallback. No screenshot, DOM dump, page text, HTML, node contents, fingerprint, PEM, path or token in output. If selector is ambiguous or the content cannot be kept local, stop at `FINGERPRINT_NODE_IDENTIFIED=NO; MATCH=NOT_VERIFIED`. Do not invent an alternate algorithm.

### How to start the next ChatGPT conversation

Paste the following as the opening message, then use the linked handoff as the detailed evidence source:

~~~text
Continúa el proyecto IABV → Codex desde el estado vivo de GitHub. Primero vuelve a leer live main/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md; esa es la única autoridad operativa. Después lee PR #548 y la sección 17 (incluida la sección 16) de este handoff:
https://github.com/jhonf463r/Python/blob/chat-continuity-key-recovery-handoff-20261027/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-27-M1A-GITHUB-APP-KEY-RECOVERY-CROSS-CHAT-HANDOFF.md

No repitas los intentos con el TXT de 40 caracteres, no uses el portapapeles para esta huella y no repitas las instrucciones genéricas de descarga. Hecho reportado: el PEM nuevo importa como RSA PKCS#1 privada de 2048 bits; su huella local ya se calculó en memoria. La coincidencia con GitHub no está verificada. El portapapeles actual fue limpiado según Codex; el control de copia no se identificó; no se expusieron ni persistieron valores.

El siguiente paso acotado es seguir la sección 16: inspeccionar solo con DOM/accesibilidad local el nodo code que contiene la huella dentro de la tarjeta “Private key” con metadato “Label: Private”, leerlo en memoria y comparar estrictamente SHA-256/Base64. Nunca mostrar huellas, PEM, DOM o página. Si no puede identificarse unívocamente, detenerse con MATCH=NOT_VERIFIED.

Antes de cualquier otro cambio, no modificar main/CURRENT-STATE, código, permisos, PR merge/rebase, tests/build/runtime, lecturas protegidas o transporte. No crear JWT ni tokens, no llamar a la API, no almacenar la clave. G1/G2/G3 siguen NOT_ESTABLISHED; protected reads fail-closed; automatic follow-on false; bridge not ready.
~~~

### Canonical status guardrails

Live `main/CURRENT-STATE.md` was re-fetched in this session and its blob remains `7a261129c8611cc0b5ed3788fc00c5d90ae189ea`. The active frontier remains `G1_INDEPENDENT_ROOT_MANDATE_AND_VERIFICATION_CHANNEL`. Preserve the existing guardrails verbatim: `G1/G2/G3=NOT_ESTABLISHED`; `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`; `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`; `PROTECTED_READS=FAIL_CLOSED`; `TESTS=NOT_RUN; RUNTIME=NOT_RUN`; `AUTOMATIC_FOLLOW_ON=FALSE`; `BRIDGE=BRIDGE_NOT_READY`.

The supporting documentation branch/PR is not canonical until normally reviewed; do not merge it automatically and do not write this episode into `main/CURRENT-STATE.md` under the current scope.


## 18. Latest local execution result — browser observation route still unavailable (2026-10-27, 12:29 America/Bogota)

### Exact Owner-supplied Codex result

```text
LOCAL_EXECUTION=YES
WINDOW_CONTEXT_RETAINED=YES
OPERA_WINDOW_IDENTIFIED=YES
TARGET_PAGE_PRESENT=UNKNOWN
LOGIN_OR_SECURITY_CHALLENGE=UNKNOWN
TARGET_CARD_IDENTIFIED=NO
FINGERPRINT_NODE_IDENTIFIED=NO
PEM_IMPORT=NOT_RECHECKED
RSA_BITS=2048
LOCAL_FINGERPRINT=NOT_RECHECKED
PAGE_FINGERPRINT_FORMAT=NOT_REACHED
MATCH=NOT_VERIFIED
SECRET_VALUES_EXPOSED=NO
SECRET_MATERIAL_PERSISTED=NO
GITHUB_CHANGED=NO
REPOSITORY_CHANGED=NO
TOKENS_CREATED=NO
GITHUB_APP_API_CALLED=NO
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
AUTOMATIC_FOLLOW_ON=FALSE
BRIDGE=BRIDGE_NOT_READY
Blocker reported: no IABV navigation/comparison route was exposed. The local operation retained Opera's identifier, but Windows UI Automation did not confirm the target page. The process stopped without inspecting the card or reading the fingerprint.
```

### Interpretation and route control

- This is the latest Owner-supplied local execution result; it is not an independently reproduced local observation by the ChatGPT/GitHub connector.
- The operation reached neither target-page confirmation nor card/node identification. No digest comparison was performed. `MATCH=NOT_VERIFIED` is neither a match nor a mismatch; `PEM_IMPORT=NOT_RECHECKED` does not overturn the prior Owner-reported successful PEM import.
- `IABV_ROUTE_AVAILABLE=NO` from this session is evidence that the required route was not exposed to that Codex execution. It does not establish that IABV has no browser/perception organs globally, nor that the target page is absent; `TARGET_PAGE_PRESENT=UNKNOWN` must remain unknown.
- Repeating the same navigation/UI Automation sequence without a materially new observation channel is not justified. The next bounded task is a read-only diagnosis of whether this local Codex session exposes an approved, demonstrably local DOM/accessibility reader that can target a single node without returning its value. Scope the probe only to browser observation capabilities and data-boundary guarantees; do not repeat a broad organ inventory or inspect the fingerprint during that diagnostic.
- Do not use the clipboard, screenshots, page/DOM dumps, remote browser services, or an alternate route that bypasses governance. If no local observation method and output boundary can be demonstrated without touching the fingerprint, stop with `LOCAL_DOM_ACCESS=UNAVAILABLE_OR_NOT_PROVEN; MATCH=NOT_VERIFIED`. Only after a supported local method is established may the exact §16 comparison be attempted; do not replay its prior navigation sequence by default.

### Preserved restrictions and canonical status

No GitHub App API call, JWT, installation token, PEM storage, app mutation, repository/code change, tests/build/runtime, protected read, or real transport was performed. The sole change associated with this note is documentary continuity on the existing PR #548 branch; `main` and `main/CURRENT-STATE.md` were not modified.

The canonical route remains the live `main/CURRENT-STATE.md`: `ACTIVE_FRONTIER=G1_INDEPENDENT_ROOT_MANDATE_AND_VERIFICATION_CHANNEL`; `G1/G2/G3=NOT_ESTABLISHED`; `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`; `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`; `PROTECTED_READS=FAIL_CLOSED`; `TESTS=NOT_RUN`; `RUNTIME=NOT_RUN`; `AUTOMATIC_FOLLOW_ON=FALSE`; `BRIDGE=BRIDGE_NOT_READY`. This key-identity comparison does not alter that route or authorize follow-on stages.