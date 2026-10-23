# Codex handoff — M1A G1 Windows OS-enforced trust bootstrap in isolated candidate

Destination: `Codex — existing UI/session`.

Task: `M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE`.
Parent: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.
Research receipt: `CHAT-ARCH-2026-10-22-M1A-G1-Windows-OS-trust-bootstrap-route-research.md`.

## Copy-ready prompt

```text
CODEX — IMPLEMENTAR UNA RUTA G1 CON FRONTERAS REALES DEL SISTEMA OPERATIVO WINDOWS (CANDIDATA AISLADA)

TASK=M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE
DESTINATION=Codex — existing UI/session
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY

OBJETIVO
El intento anterior se detuvo correctamente con BLOCKED_MISSING_G1_TRUST_ANCHOR. NO repitas el inventario general de fuentes ni la misma evaluación de factibilidad. Hay evidencia nueva, documentada en Microsoft Learn, de primitivas Windows que pueden permitir una frontera auténtica: service SID restringido, procesos de servicio con token propio, claves CNG persistidas con DACL explícita y named pipes con DACL explícita. Usa esta ruta como hipótesis concreta de implementación y prueba estática de límites; no la declares segura solo porque existan las API.

PRE-FLIGHT OBLIGATORIO
1. Revalida en GitHub el preflight canónico de main: IABV_v1.5/AGENTS.md → docs/history/CHAT-ARCH/README.md → CURRENT-STATE.md → CONTEXT-INDEX.md → MEMORY-OPERATING-PROTOCOL.md. Lee el nuevo recibo de investigación sobre la ruta Windows.
2. Trabaja exclusivamente sobre la rama pública aislada m1a-g1-g3-governance-route-candidate-20261022, base fijada 60c8ac6e7ff425c815d9bdc7194bf20ef8d134db. Verifica nombre, HEAD, base y árbol antes de editar. La última observación remota era HEAD=base, tree=ca963f8013809d4efcf56133a37d2efe148517e9.
3. No abras ni uses el checkout local preexistente o dirty del Owner. Si no puedes demostrar que tu workspace escribe solamente en la candidata aislada, termina con ISOLATED_CANDIDATE_IDENTITY_UNVERIFIED. Las escrituras de fuente solo pueden terminar en la rama candidata exacta.

DISEÑO A INTENTAR
Implementa una frontera emisora real, separada por proceso/identidad del MCP reader, no otra clase dentro de server.py:
- Un Windows service/broker emisor con identidad propia de servicio y SERVICE_SID_TYPE_RESTRICTED; cuenta con privilegio mínimo. No ejecutar el reader ni el requester con la identidad emisora.
- Clave de firma persistida CNG. Configura/solicita una DACL que permita usar la clave solo a la identidad del servicio emisor y SYSTEM. No presupongas TPM ni proveedor hardware. Si el mecanismo requerido no puede expresarse o verificarse estáticamente, falla cerrado y reporta la brecha.
- Ejecutable, configuración, material de raíz y estado de inscripción en ubicación protegida del despliegue; requester y reader no pueden cambiar el servicio, la política ni el root. No guardes trust anchors en el checkout del usuario ni en una ruta escribible por el proceso solicitante/lector.
- IPC con named pipe y security descriptor/DACL explícita, mínimo privilegio y autenticación real del caller a partir del token/SID del sistema operativo. No uses descriptor NULL/default, ni aceptes el SID, rol o identidad como texto suministrado por el caller.
- Ceremonia de inscripción explícita y separada, iniciada por el Owner; jamás auto-enrollment al arrancar. Vincula el principal local autenticado (SID de Windows derivado del token real, únicamente como identidad de principal local), el registro de credencial Owner/gesto de presencia cuando soporte WebAuthn real, clave pública del emisor, revisión de política e identidad exacta de instancia del servidor. No etiquetes una SID local como identidad civil o como identidad externa de IdP. Si el contrato requiere otra identidad que el entorno actual no permite verificar, detente con la dependencia exacta.
- WebAuthn/Windows Hello es un factor candidato, no raíz automática. Una credencial recién creada no demuestra por sí sola quién es el Owner; ata el challenge fresco al RP ID fijado y a la ceremonia explícita. No presumas API, TPM, provider ni IdP configurado.
- En la frontera de cada lectura protegida, el reader debe validar alcance, principal destino/instancia, vencimiento, revocación/versión de política y firma; el reader no puede usar ni cambiar la clave privada ni alterar su trust root. No declares G1 cerrado si no existe una ruta legible y conectada a cada call site de lectura. Si no puede lograrse separación efectiva y reader-side verification, detente.
- La raíz inicial debe quedar establecida por el boundary de instalación/inscripción explícita del Owner y por ACLs del OS, no por confianza ciega en el primer proceso que inicia. Las funciones requester, issuer, reader no se consideran separadas por nombres de clases. No inventes identidades, llaves, registros confiables ni una autoridad firmante ficticia.

EVIDENCIA NUEVA A UTILIZAR
Fuentes oficiales que fundamentan primitivas, no disponibilidad en esta máquina:
- SERVICE_SID_INFO: https://learn.microsoft.com/en-us/windows/desktop/api/winsvc/ns-winsvc-service_sid_info
- Service user accounts/tokens: https://learn.microsoft.com/en-us/windows/win32/services/service-user-accounts
- CNG persisted key: https://learn.microsoft.com/en-us/windows/win32/api/ncrypt/nf-ncrypt-ncryptcreatepersistedkey
- CNG key DACL property: https://learn.microsoft.com/en-us/windows/win32/api/ncrypt/nf-ncrypt-ncryptsetproperty
- Named pipe security and dangerous NULL/default ACL: https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights
- WebAuthn RP and credential APIs: https://learn.microsoft.com/en-us/windows/win32/api/webauthn/
- Windows Hello for Business identity/IdP limitations, especially local accounts: https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/hello-faq

LÍMITES NO NEGOCIABLES
- No checkout local previo/dirty, no data/, SQLite, secretos, credenciales existentes ni .env.
- No shell/PowerShell, tests, builds, linters que ejecuten código de producto, runtime, probes locales, MCP, Codex App Server, Ollama, procesos o servicios reales.
- No instalar servicios, no cambiar configuración del equipo, no crear ni inscribir credenciales/llaves reales, no invocar lectores, no hacer lecturas protegidas ni transporte real.
- No cambios de red/GPU/model/environment/seguridad, gastos nuevos, nuevos planes o autenticación contra proveedores no autorizados.
- No merge, deployment ni liberación de bloques operativos.
- Se permite editar fuente en la rama remota candidata aislada únicamente. Si la arquitectura necesitaría instalación o una prueba de plataforma para demostrar un hecho que no puede afirmarse estáticamente, marca esa prueba como pendiente; no declares éxito operacional.
- No amplíes a implementar G2 ni G3 ni a mezclar Entry 274 con G3. G3 es el resolver versionado de operación→target. No agregues tests ni los ejecutes.

REGLA PARA DETENERSE
El propósito es intentar la arquitectura nueva, no volver a explicar genéricamente el problema. Si la ruta de inscripción no puede establecer de manera honesta una autoridad inicial y separar issuer/requester/reader sin supuesto no probado, detente en la primera dependencia insalvable y declara exactamente:
- qué parte de la nueva ruta sí queda implementada;
- la ruta/archivo/blob donde existe;
- por qué no basta para G1;
- cuál mínima autoridad faltaría;
- si no hubo archivos cambiados, indícalo claramente. No crear stubs, TODOs o clases de fachada para aparentar trabajo.

ENTREGA
Un resultado terminal:
- G1_WINDOWS_OS_BOUNDARY_IMPLEMENTED_IN_CANDIDATE_STATIC_UNVERIFIED
- PARTIAL_G1_WINDOWS_BOUNDARY_WITH_EXACT_REMAINING_GAP
- BLOCKED_MISSING_G1_TRUST_ANCHOR
- ISOLATED_CANDIDATE_IDENTITY_UNVERIFIED

Incluye HEAD/base/árbol exactos; cada archivo modificado y blob; evidencia estática de service SID, key ACL, pipe ACL, ceremonia explícita, Owner/server binding y verificación en cada ruta de lectura; brechas y validación futura pendiente. Haz fetch-back desde GitHub de cada archivo/blobs después de los cambios. No declares envío al runtime.

Estado terminal obligatorio:
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_CHECKOUT=NOT_ACCESSED
SERVICE_INSTALLATION=NOT_PERFORMED
CREDENTIAL_ENROLLMENT=NOT_PERFORMED
PROTECTED_READ=NOT_AUTHORIZED
MERGE_DEPLOY=NOT_AUTHORIZED
BLOCK_RELEASE=NOT_AUTHORIZED
```

## Interaction contract

The prompt must be shown to the Owner inline in the active chat, not only stored here. Saving it to GitHub does not mean it was dispatched. `CODEX_PROMPT_DISPATCHED=NO` until an actual Codex result is returned and correlated to this task.
