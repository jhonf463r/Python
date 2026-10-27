# M1A G1 — Objetivo MCP fijado y plan de integración Entra (sin cambios de código)

> **Reconciliación posterior (2026-10-27):** Este plan documenta la decisión original de planificación sin código; una autorización conversacional posterior cubrió únicamente preparar/corregir una candidata de código aislada en [PR #549](https://github.com/jhonf463r/Python/pull/549), HEAD `05d007965ea7efda6f528657e20103ea82bcb6b5`, base inicial `a8624c30744da7f593d6a1c829e48aa229c8efca`. Procedencia: el Owner usó el prompt de alcance limitado preparado en esta conversación y luego aportó el resultado de Codex. Esto registra consentimiento conversacional limitado, no autenticación independiente de runtime ni autorización operativa. No autoriza instalar paquetes, ejecutar tests/build/runtime/CI, portal/configuración real de Entra, túneles, lecturas protegidas, merge, despliegue o activación. `G1/G2/G3=NOT_ESTABLISHED`; lecturas protegidas siguen `FAIL_CLOSED`. La condición de no autorización que sigue en este plan describe el momento original de redacción y queda supersedida solo para la candidata code-only PR #549.


- Fecha: 2026-10-27 (America/Bogota).
- Tarea: M1A_G1_MCP130_TARGET_AND_IMPLEMENTATION_PLAN_20261027.
- Resultado original del plan: TARGET_RATIFIED; PLAN_DOCUMENTED; SOURCE_MODIFICATION_NOT_AUTHORIZED_AT_PLAN_CREATION; LATER=CODE_ONLY_CANDIDATE_PR549_PREPARED.
- Procedencia: el Owner respondió «ok procede» a la propuesta explícita de fijar el objetivo Python 3.13.2 + MCP SDK 1.30.0 + Streamable HTTP loopback en puerto 8000 sin túnel. Este consentimiento fija el objetivo de planificación; no autentica identidad de runtime ni autoriza instalar paquetes, cambiar código, configurar Entra, iniciar procesos, ejecutar pruebas, abrir túneles o realizar lecturas protegidas.

## 1. Objetivo ratificado

| Eje | Objetivo para la futura implementación | Límite |
|---|---|---|
| Intérprete | Miniconda Python 3.13.2, ejecutable previamente observado como C:\Users\faber\miniconda3\python.exe | No cambiar ni instalar paquetes en el entorno durante esta tarea |
| SDK | MCP Python SDK 1.30.0, distribución PyPI mcp | Es un objetivo fijado, no evidencia de que la instalación destino ya tenga esta versión |
| Transporte | Streamable HTTP | HTTP de desarrollo local solamente mientras no se apruebe y verifique una URL HTTPS canónica |
| Bind local | 127.0.0.1:8000 | No enlazar a 0.0.0.0 ni a interfaces de red externas |
| Túnel | Desactivado; ningún Cloudflare Tunnel | No iniciar, reconectar o configurar túneles |
| Confianza | Entra como candidato de autenticación; autorización fail-closed | G1 no establecido; sin registro de aplicación, mandato operativo o lectura protegida |
| Cambio de código | Rama aislada de la revisión viva de main, preferiblemente PR draft | No tocar el checkout local sucio ni modificar main directamente |

La respuesta del Owner autoriza dejar este objetivo registrado y preparar el plan; no es autorización para ejecutar la implementación.

## 2. Evidencia base y discrepancias conocidas

### 2.1 Fuente canónica consultada en main

- CURRENT-STATE.md se volvió a leer desde main antes de esta tarea. Blob observado: a51ca4945c9960162c188823c58292a82b1961b1.
- IABV_v1.5/pyproject.toml: blob 22827c38cc3f7ee3bd3e16f6ed3ec0543841beb1; no declara directamente mcp, uvicorn ni PyJWT.
- IABV_v1.5/scripts/run_mcp_bridge.ps1: blob a29a58399b6c180f36f1c2a2e33d9bbd53256144; el script usa Miniconda como default, Streamable HTTP y puerto 8000, y tiene comportamiento de túnel Cloudflare que deberá quedar detrás de una opción de exclusión segura y desactivada por defecto.
- IABV_v1.5/scripts/start_iabv.ps1: blob c689e894e3fb0d11429341b065e68ba766b5ea2e; el wrapper puede sincronizar con origin/main y delega en el lanzador del puente. No usarlo para la futura modificación del checkout preexistente, que ya fue reportado como muy sucio.
- IABV_v1.5/src/iabv_v15/infra/mcp/server.py: blob 17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c; acepta stdio, sse y streamable-http, pero el default del módulo es stdio. La configuración inspeccionada de seguridad de transporte permite hosts/orígenes wildcard; no se observa un verificador Entra conectado.
- IABV_v1.5/docs/mcp-bridge.md: blob e53709d10a7a40d089cc8a55c94a4a23f620718e; documenta el puerto 8765 y declara que falta autenticación por token HTTP. Eso discrepa con el default 8000 del lanzador.

### 2.2 Evidencia local aportada por el preflight de Codex

Esta información corresponde al entorno local previamente inspeccionado, no a una inspección local repetida en esta tarea:

- Miniconda Python 3.13.2: mcp 1.27.0, uvicorn 0.34.3, starlette 1.0.0, PyJWT 2.12.1, cryptography 44.0.1.
- Python 3.14.4 separado: mcp 1.30.0, uvicorn 0.53.0, starlette 1.6.0, PyJWT 2.14.0, cryptography 50.0.1.
- El checkout C:\Python estaba detached y muy sucio; HEAD local 8425f03... no era main vivo, y origin/main local también estaba atrasado. El informe dice que esta tarea no debe modificar ese checkout.

La versión 1.30.0 del SDK indica Python >=3.10 en su metadata publicada, por lo que Python 3.13 está dentro del rango declarado. Aun así, la combinación destino y todas sus dependencias deben resolverse y verificarse en el entorno Miniconda antes de instalar o actualizar nada. La documentación actual indica que SDK 2.x es la línea estable actual y que 1.x está en mantenimiento para correcciones críticas/de seguridad. Se respeta la decisión de fijar 1.30.0 para esta integración por ser la versión del API revisada, pero la elección es una congelación deliberada de compatibilidad, no una afirmación de que 1.x sea la línea actual preferida para desarrollos nuevos.

## 3. Decisión funcional importante: loopback no equivale a Entra E2E

El objetivo ratificado de 127.0.0.1:8000 sin túnel habilita una frontera local de desarrollo; no resuelve todavía la identidad del recurso HTTPS que Entra exige en su flujo MCP.

Para la integración real:
- El cliente MCP debe pedir el token para un valor resource que coincida carácter por carácter con el Application ID URI registrado.
- Protected Resource Metadata debe anunciar el recurso canónico y el issuer tenant-specific.
- El access token v2 debe validarse con su audiencia de API esperada (normalmente el Application/client ID GUID), además de firma, issuer, tenant, vigencia, identidad y permisos. La URL canónica, el Application ID URI, el valor OAuth resource y el claim aud son comprobaciones relacionadas pero no intercambiables.
- La guía vigente de Microsoft para el MCP HTTP con Entra parte de un endpoint HTTPS. La URL canónica HTTPS aún no está aprobada y no se autoriza un túnel. Por eso el plan puede preparar el código fail-closed y pruebas locales, pero no deberá afirmar que un flujo real de Entra ya es ejecutable hasta resolver esa dependencia con autorización independiente.
- No se debe inventar un dominio, confiar en un URL temporal, convertir la dirección de loopback en una raíz de confianza ni apagar la validación de aud/resource para hacer coincidir configuraciones.

## 4. Cambios futuros propuestos, por archivo

Estos son cambios de alcance propuesto; no se han realizado.

### A. Dependencias y reproducibilidad

Archivo: IABV_v1.5/pyproject.toml.

- Declarar explícitamente la dependencia de runtime mcp==1.30.0; mantener la restricción de no migrar automáticamente a SDK 2.x.
- Declarar las dependencias directas que la implementación utilice realmente, incluida la biblioteca de validación JWT con soporte criptográfico y Uvicorn si el punto de entrada lo importa/gestiona directamente. No asumir que PyJWT o cryptography instalados globalmente son dependencias reproducibles del proyecto.
- Resolver las versiones completas para Miniconda Python 3.13.2 con una herramienta autorizada y guardar un lock o artefacto de dependencias versionado, sin secretos. El método exacto se elige al autorizar la implementación, dado que el repo actual no define un lockfile estándar para este puente.
- No ejecutar instalación, upgrade o resolución de paquetes como parte de esta tarea.

### B. Verificador de tokens Entra

Archivo propuesto: IABV_v1.5/src/iabv_v15/infra/mcp/entra_token_verifier.py.

- Implementar el contrato asíncrono del SDK TokenVerifier: verificar el token bearer y devolver AccessToken solo cuando todas las condiciones sean válidas; en cualquier incertidumbre, token inválido o dependencia de validación no disponible, devolver rechazo.
- Usar una biblioteca mantenida de validación JWT/JWK (no escribir criptografía propia), con metadata OIDC tenant-specific y rotación/cache controlada de claves. No aceptar descubrimiento de issuer arbitrario indicado por un token sin verificar.
- Validar algoritmo permitido, firma, kid/JWKS, issuer v2 exacto, tid exacto, aud GUID de la API, versión v2, exp/nbf y claims requeridos; rechazar ID tokens, Graph tokens, audiencias no esperadas, token expirado y fallos de metadata o firma.
- Validar identidad inmutable del Owner mediante oid/sub conforme al token y una asignación de rol/scope real que deberá definirse en la fase de registro autorizado. Nunca autorizar solo por nombre mostrado o correo.
- No guardar, devolver, escribir en logs ni exponer tokens ni headers Authorization. No persistir secretos en GitHub, .env versionado, issues o memoria de chat.
- Configuración sensible o específica del tenant debe proceder de configuración local protegida. Los valores ausentes o placeholders no deben activar autenticación permisiva; la autenticación HTTP debe seguir en fail-closed.

### C. Cableado FastMCP

Archivo: IABV_v1.5/src/iabv_v15/infra/mcp/server.py.

- Integrar el TokenVerifier con AuthSettings usando la API exacta de mcp 1.30.0 verificada en entorno destino.
- Fijar issuer_url al issuer tenant-specific de Entra y resource_server_url a la URL canónica aprobada cuando exista. No asumir que 127.0.0.1:8000 es la URL canónica externa.
- Para la integración Entra v2, el verificador valida aud como el Application/client ID GUID. La documentación v1.30 del SDK indica que validate_token_resource debe elegirse explícitamente: la comparación SDK entre AccessToken.resource y resource_server_url no debe activarse si son identificadores deliberadamente distintos para este proveedor, pero en ese caso el verificador debe validar aud exacto por su cuenta y devolver el objeto AccessToken sin aceptar otra audiencia. No omitir ambos controles.
- Fijar scope o rol requerido después de la configuración autorizada de Entra; si no existe esa configuración o el rol/scope no viene en el access token, rechazar.
- No usar auth_server_provider para convertir IABV en emisor de tokens; IABV actúa como servidor de recursos, Entra como emisor externo.
- Reemplazar las reglas wildcard de hosts/orígenes por una allowlist local explícita para el objetivo de loopback, y conservar las defensas contra DNS rebinding apropiadas a la versión de FastMCP.
- Si falta cualquier variable/configuración necesaria para proteger HTTP, impedir el arranque del modo HTTP; nunca arrancar silenciosamente sin auth.

### D. Transporte y túnel

Archivo: IABV_v1.5/scripts/run_mcp_bridge.ps1.

- Mantener Miniconda Python 3.13.2 como intérprete del lanzamiento canónico, verificando ruta y versión antes de iniciar.
- Fijar Streamable HTTP, host 127.0.0.1 y puerto 8000 en el modo local.
- El comportamiento Cloudflare Tunnel debe quedar desactivado por defecto y requerir una opción de habilitación explícita, aparte y futura. El objetivo actual no lo habilita.
- No invocar start_iabv.ps1 para pruebas de la integración mientras el wrapper pueda sincronizar main o iniciar procesos secundarios. Preparar una ejecución acotada desde una worktree limpia y con revisión fijada cuando haya autorización separada.
- La integración HTTP no se considera protectora de stdio. El transporte stdio conserva un contrato local distinto y no debe obtener permiso G1 solo por compartir el objeto servidor.

### E. Documentación operacional

Archivo: IABV_v1.5/docs/mcp-bridge.md.

- Reconciliar puerto 8765 vs 8000, intérprete, transporte y punto de entrada con el lanzador verificado.
- Describir que HTTP requiere token bearer validado y que las lecturas/operaciones gobernadas siguen denegadas hasta que G1, G2 y G3 se demuestren.
- Marcar el túnel como fuera de alcance y deshabilitado en la fase local.
- Documentar separadamente el alcance stdio y sus controles de proceso local.
- Nunca describir el puente como listo solo porque el middleware devuelve 401 o porque el SDK publica metadata.

### F. Pruebas futuras

Nuevas pruebas propuestas en tests del proyecto, solo después de autorizar la implementación y ejecutar contra una revisión aislada:

1. Sin token, token malformado, firma inválida, kid desconocido, metadata/JWKS no disponible, issuer/tid/aud incorrectos, token de Graph, ID token, token expirado/no válido y claims requeridos ausentes: rechazo sin ejecutar tools.
2. Token válido criptográficamente pero sin el scope/rol o con oid no autorizado: rechazo de autorización.
3. Un token válido para otra API o URL: rechazo.
4. Recurso, Application ID URI y aud revisados independientemente; prueba específica de validate_token_resource.
5. Protected Resource Metadata y 401/WWW-Authenticate en Streamable HTTP.
6. Hosts/orígenes ajenos y DNS rebinding: rechazo.
7. Tools no invocadas si la autenticación o autorización falla; logs sin token ni datos sensibles.
8. Transporte stdio: confirmar que no hereda la protección HTTP y que no ofrece acceso a operaciones protegidas sin el canal local autorizado.
9. Las fixtures de clave/token, si se usan, son exclusivamente de pruebas automatizadas aisladas y nunca se registran como proveedor, raíz o autoridad runtime de IABV.

No ejecutar pruebas ahora. GitHub Actions mantiene el bloqueo de facturación documentado, así que el preflight posterior debe verificar el estado y no relanzar sin cambio material.

## 5. Riesgos y puertas que siguen abiertos

1. **Checkout local no seguro para edición directa:** el Owner reportó 13.833 entradas de estado sucio y HEAD detached antiguo. No modificar ni limpiar ese directorio para avanzar. Una fase futura debe usar worktree/branch aislada derivada del SHA vigente de main y preservar el checkout actual.
2. **SDK 1.30 no instalado en Miniconda:** el entorno objetivo observado tiene 1.27.0; no instalar hasta autorización explícita de cambios de entorno.
3. **URL HTTPS canónica sin resolver:** sin esa URL y registro coincidente no hay flujo Entra/MCP de extremo a extremo demostrado; no abrir túnel para sortear el bloqueo.
4. **Aplicación Entra no verificada:** no acceder al portal ni crear registro/roles sin autorización nueva. Tenant, API client ID, scope/role y Owner object ID continúan sin confirmación operativa en esta tarea.
5. **Canal de bootstrap G1 aún no establecido:** ni el login MFA ni la validación JWT por sí solos prueban el mandato independiente del Owner sobre IABV.
6. **G2/G3 sin establecer:** un bearer token válido no concede permiso a una ruta, repositorio, archivo o herramienta. Todas las lecturas protegidas siguen denegadas.
7. **Sin implementación ni pruebas:** esta tarea solo elige el objetivo y documenta el plan. No cierra ninguno de los ocho prerrequisitos de implementación.

## 6. Orden correcto de ejecución futura

Fase 0 — Objetivo: **ratificado** por el Owner en la conversación; documentado en este archivo.

Fase 1 — Autorizar por separado una implementación de código en worktree/branch/PR aislada. Sin tocar el checkout sucio existente, sin instalar paquetes en el entorno que el Owner usa diariamente y sin cambiar la configuración de Entra. El alcance exacto debe autorizarse antes de comenzar.

Fase 2 — Con esa autorización, verificar/instalar la combinación fijada en un entorno de trabajo aislado; añadir el verificador y el cableado MCP con configuración ausente => rechazo; asegurar que la ruta HTTP nunca puede arrancar desprotegida; actualizar documentación y tests. Sin token real y sin URL canónica aprobada no se afirma integración E2E.

Fase 3 — Revisión independiente del diff, resolución de dependencias, tests locales acotados y fetch-back del PR con SHA exacto. No merge ni rebase automático. No modificar el directorio local con cambios preexistentes.

Fase 4 — Requerirá autorizaciones separadas: registrar la API en Entra/asignar scope o rol; aprobar la URL HTTPS canónica; realizar el bootstrap local; probar end-to-end con token real sin compartir el token; cualquier túnel/exposición. Ninguna de esas acciones está autorizada por la ratificación del objetivo.

Fase 5 — Solo cuando exista evidencia independiente para G1 y productores válidos G2/G3, revisión de aceptación y decisión explícita, se podrá valorar habilitar operaciones o lecturas protegidas.

## 7. Fuentes y estado terminal

Fuentes oficiales consultadas el 2026-10-27:
- [MCP Python SDK v1 Authorization](https://py.sdk.modelcontextprotocol.io/v1/run/authorization/) — TokenVerifier, AuthSettings, audience/resource y límite HTTP/stdio.
- [MCP SDK release v1.30.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0) — cambios de validate_token_resource, release de mantenimiento 1.x y compatibilidad de API.
- [MCP Python SDK v1.30.0 en PyPI](https://pypi.org/project/mcp/1.30.0/) — metadata de paquete/versión.
- [Microsoft: Secure an MCP server with Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/agent-id/secure-mcp-server-with-entra-id) — registro de API, recurso canónico, metadata, issuer y validación.
- [Microsoft: Access tokens](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens) — la API valida sus access tokens, audiencia, emisor y firma.
- [MCP Authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) — OAuth HTTP, Protected Resource Metadata y requisitos de bearer token.

Estado terminal:
- TARGET=MINICONDA_PYTHON_3_13_2
- TARGET_MCP_SDK=1.30.0
- TARGET_TRANSPORT=STREAMABLE_HTTP
- TARGET_BIND=127.0.0.1:8000
- TUNNEL=DISABLED; NOT_AUTHORIZED
- OWNER_RATIFICATION=EXPLICIT_CHAT_RESPONSE: "OK PROCEDE"; SCOPE=TARGET_AND_DOCUMENTATION_PLAN_ONLY
- SOURCE_CHANGES=NOT_AUTHORIZED; NOT_DONE
- ENVIRONMENT_CHANGES=NOT_AUTHORIZED; NOT_DONE
- ENTRA_PORTAL_OR_REGISTRATION=NOT_AUTHORIZED; NOT_DONE
- TESTS=NOT_RUN
- BUILD=NOT_RUN
- RUNTIME=NOT_RUN
- PROTECTED_READS=FAIL_CLOSED
- G1=NOT_ESTABLISHED
- G2=NOT_ESTABLISHED
- G3=NOT_ESTABLISHED
- IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
- BRIDGE=BRIDGE_NOT_READY
- NEXT_ACTION=OWNER_EXPLICIT_AUTHORIZATION_FOR_ISOLATED_CODE_IMPLEMENTATION
- AUTOMATIC_FOLLOW_ON=FALSE
