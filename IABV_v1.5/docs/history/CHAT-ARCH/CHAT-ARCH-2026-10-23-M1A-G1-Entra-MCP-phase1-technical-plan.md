# M1A G1 — Plan técnico fase 1: autoridad de confianza y seguridad del puente MCP

- Fecha: 2026-10-23 (America/Bogota).
- Norte: `GOVERNED_IABV_CODEX_BRIDGE`.
- Frontera activa: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.
- Tipo: plan documental y revisión estática; **PLAN_ONLY**.
- Baseline remoto fijado: `main` = `c95fb23c8ae5f7b6fdd1f94b4dba253347bb89cd`.
- Rama documental aislada: `codex/m1a-g1-entra-mcp-phase1-plan-20261023`.
- Alcance de este registro: documentación; no toca código de producto ni cambia `main`.

## 1. Decisión ejecutiva

No avanzar directamente a registrar una aplicación Entra ni a añadir middleware. La primera necesidad es decidir y documentar una ruta compatible con el cliente MCP real, cerrar la frontera de confianza de G1 y evitar toda exposición HTTP no autenticada. La identidad Entra y Authenticator que el Owner reporta como funcionales son evidencia de autenticación humana, no un ancla de confianza IABV ni permiso de lectura.

**Recomendación condicionada:**

1. Si el consumidor aprobado es Codex en la misma máquina Windows y el mismo contexto de usuario, evaluar primero MCP `stdio` como candidato de transporte local. Reduce la superficie de red; no satisface por sí mismo G1 ni sustituye la autorización por operación.
2. Si el consumidor necesita HTTP remoto, evaluar únicamente Streamable HTTP protegido con un flujo OAuth compatible con Codex y con el servidor de recursos; autenticación antes de ejecutar herramientas, validación estricta de access tokens y autorización IABV independiente en cada operación.
3. No volver a lanzar ni utilizar el túnel público actual durante la evaluación. Si no puede evidenciarse una autoridad raíz independiente, no crear una raíz a partir de la propia identidad Entra: el estado requerido sigue siendo opción D, sin bootstrap y fail-closed, hasta decisión de Owner.

Esta recomendación no selecciona todavía una arquitectura final: el cliente exacto, transporte vivo, versión instalada del SDK MCP y compatibilidad de Entra con los requisitos de autorización MCP no están verificados.

## 2. Evidencia verificable y límites

### Estado canónico

Los cinco documentos de enrutamiento se recuperaron de la misma rama `main` en el orden normativo: `IABV_v1.5/AGENTS.md`, `docs/history/CHAT-ARCH/README.md`, `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`. Sus cabeceras actuales mantienen:

```text
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID; NOT_YET_TRUSTED_BY_IABV
MCP_HTTP_TOKEN_AUTH=ABSENT_IN_DOCUMENTED_DESIGN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

### Hallazgos de la rama pública actual

- [`docs/mcp-bridge.md`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/mcp-bridge.md), blob `e53709d10a7a40d089cc8a55c94a4a23f620718e`, declara que el endpoint HTTP no tiene autenticación por token y que un túnel público permitiría invocar herramientas.
- [`src/iabv_v15/infra/mcp/server.py`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/infra/mcp/server.py), blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`, admite `stdio`, `sse` y `streamable-http`; el constructor inspeccionado desactiva DNS-rebinding protection y configura hosts/orígenes comodín cuando el ajuste del SDK está disponible. El método `run` por sí solo tiene `stdio` como default, pero eso no describe el proceso que está ejecutándose en el equipo.
- [`scripts/run_mcp_bridge.ps1`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/scripts/run_mcp_bridge.ps1), blob `a29a58399b6c180f36f1c2a2e33d9bbd53256144`, define por defecto `streamable-http` y, después de iniciar el proceso MCP, ejecuta `cloudflared tunnel --url` contra el origen local. No debe usarse en futuras verificaciones mientras la protección no esté aprobada y validada.
- [`scripts/start_iabv.ps1`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/scripts/start_iabv.ps1), blob `c689e894e3fb0d11429341b065e68ba766b5ea2e`, delega en el script de bridge y puede hacer auto-pull y arranque; no ejecutarlo como comprobación de este plan.
- [`pyproject.toml`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/pyproject.toml), blob `22827c38cc3f7ee3bd3e16f6ed3ec0543841beb1`, no declara directamente el paquete `mcp` ni una dependencia de validación OIDC/JWT. La guía instala `mcp` y `uvicorn` sin fijar versión. La versión real instalada no está verificada.

Los documentos estáticos no prueban que el servidor esté actualmente corriendo, que el túnel esté activo ni que el proceso local use estos blobs. No se declara un incidente de exposición.

### Referencias oficiales vigentes para el diseño

- [Codex / MCP: transportes, OAuth, CIMD y DCR](https://learn.chatgpt.com/docs/extend/mcp): la documentación actual describe STDIO y Streamable HTTP, OAuth, PKCE y opciones de registro CIMD/DCR para Codex.
- [MCP Python SDK: autorización del servidor](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/authorization.md): explica el servidor HTTP como resource server, la verificación del bearer token por petición, Protected Resource Metadata y el rechazo HTTP 401. También advierte que la autorización HTTP no protege STDIO: allí la frontera de seguridad es el proceso que inicia el servidor. Es documentación de la rama actual del SDK, no evidencia de la versión instalada por IABV.
- [Microsoft Entra: access tokens](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens) y [validación de claims](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation): distinguen access tokens de ID tokens y exigen que la API valide firma, emisor/tenant, audiencia y claims aplicables.
- [Microsoft Entra: authorization-code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow): describe el flujo OAuth y el uso de PKCE para los tipos de clientes compatibles.

La integración de Codex y Entra **todavía no se considera interoperable por defecto**. El diseño debe verificar el flujo exacto, la redirección, metadatos de autorización, método de registro de cliente, audiencias/scopes y cualquier requisito MCP de `resource` antes de recomendar registro de una aplicación.

## 3. Principios no negociables

1. **Fail-closed:** si falta el principal autenticado, autoridad, evidencia fresca, catálogo, revocación, destino resuelto, decisión, presupuesto, integridad de ledger o release independiente requerido, se deniega.
2. **Separación de poderes:** autenticación de transporte, aprobación interactiva, decisión de lectura, verificación del reader, auditoría/recibo y liberación de bloque son autoridades distintas. Ningún bearer token ni respuesta positiva genérica equivale a una decisión de lectura.
3. **Una sola autoridad existente:** ampliar los contratos y mecanismos que ya pertenecen a IABV; no crear otro orquestador, “cerebro”, issuer paralelo ni ruta de liberación.
4. **Separación de identidad y confianza:** MFA confirma un inicio de sesión; no prueba por sí solo el mandato sobre IABV, el vínculo Owner→principal Windows, ni el vínculo issuer→instancia exacta de servidor.
5. **Minimización de superficie:** no abrir puertos ni túneles para probar autenticación. No exponer herramientas de escritura/ejecución como si el endpoint fuese exclusivamente de lectura; definir una política por herramienta y negar por defecto lo no aprobado.
6. **Cero coste pagado:** no actualizar Azure a Pay-As-You-Go, quitar límites, comprar licencias ni desplegar recursos. La facturación y el límite real de Azure no se han verificado; no afirmar garantía de coste cero basada solo en Entra ID Free.
7. **Evidencia por SHA:** los resultados futuros deben vincularse al SHA y blobs exactos, distinguir el diseño de la conducta runtime, y registrar resultados reales sin completar evidencia faltante por inferencia.

## 4. Arquitectura candidata y decisión de transporte

### Ruta A — Codex local con STDIO

Evaluarla primero solo si el consumidor previsto realmente ejecuta Codex en la misma máquina y contexto Windows.

- Codex inicia el proceso por comando local y se comunica por STDIO; no hay endpoint HTTP ni necesita túnel.
- La frontera principal de proceso/OS no autentica automáticamente un usuario frente a IABV. Hay que demostrar el principal y su vínculo al mandato de gobernanza, además de conservar la aprobación fresca y el verificador de operaciones.
- La guía oficial del SDK indica que su token verifier HTTP no se aplica a STDIO; no afirmar lo contrario ni presentar STDIO como una solución completa de G1.
- No reutilizar `run_mcp_bridge.ps1` como launcher de STDIO: ese script está diseñado para abrir `cloudflared` después de arrancar el servidor. La configuración exacta de un launcher local se determina solo tras una autorización posterior y una comprobación de compatibilidad del cliente.

### Ruta B — Codex remoto/Streamable HTTP con OAuth

Usarla únicamente si existe un requisito confirmado de acceso HTTP remoto que no pueda satisfacerse con el proceso local.

- Exigir OAuth compatible con el cliente y el protocolo MCP; recurso protegido con metadatos de descubrimiento y respuestas HTTP 401/WWW-Authenticate correctas.
- Validar cada access token para la API concreta: firma y claves confiables, `iss`, `tid`, `aud` o recurso, `exp`, `nbf`, sujeto autorizado (`oid`/`sub` según el contrato), cliente/actor y scopes. Rechazar ID tokens, tokens de otro tenant, audience incorrecta, firma desconocida, token expirado y claims ausentes/no admitidos.
- Confirmar el procedimiento de cliente que efectivamente soporta Codex y Entra —cliente preconfigurado, CIMD o DCR—, callback exacto, PKCE S256, validación del emisor de respuesta y scopes. No registrar una aplicación ni crear un secreto durante la fase actual.
- No confiar en cabeceras estáticas, nombres enviados por el caller o un token copiado como autorización por operación.
- Mantener el listener en ámbito no público hasta que la autenticación y autorización se hayan implementado, probado y revisado independientemente. El túnel público sigue prohibido como método de prueba.

### Selección pendiente

La selección A/B requiere el inventario de metadatos del cliente/host real y la versión instalada del servidor/SDK por una ruta explícitamente autorizada. Esa comprobación no se hizo aquí. Si no se puede verificar el cliente o la compatibilidad OAuth de Entra sin un servicio/coste adicional, detenerse y mantener la denegación en lugar de añadir un proveedor o servicio no aprobado.

## 5. Plano de autorización IABV que debe preservarse

Las condiciones siguientes proceden de Entry 274 y del diseño M1A v1.0.1 adoptado solo como diseño. No se presentan como capacidades ya implementadas.

### G1 — Principal y raíz de confianza

Antes de cualquier lectura protegida debe existir evidencia verificable de una autoridad raíz independiente, su mandato, custodio, canal de verificación y revocación, más los vínculos Owner→principal Windows, autoridad→issuer e issuer→instancia/revisión exacta del servidor. Un hash de GitHub, un usuario local administrador, MFA, un SID o una raíz recién creada por el mismo proceso no son pruebas suficientes de bootstrap independiente.

**Puerta previa obligatoria:** el Owner debe proporcionar evidencia verificable de una autoridad independiente, o ratificar la opción D (sin bootstrap, mantener bloqueado). No hay base para implementar una raíz inventada.

### G2 — Catálogo, productor y revocación

Exigir catálogo versionado e íntegro; publicación desde un productor autenticado y autorizado para la clase de bloque; ciclo de vida versionado de publicar/retirar/revocar; origen de revocación autoritativo y comprobación de vigencia. Si el origen falta, falla o da respuesta inconsistente, denegar.

### G3 — Resolver de operación a destino

Exigir resolución versionada en el servidor para cada herramienta/operación a un destino canónico y a los call sites reales; no aceptar que el caller controle `target_scope`, una ruta abierta o el destino final mediante campos arbitrarios. El resolver no puede leer paths fuera del alcance permitido para calcular identidad.

### G4–G6 — Evaluación, bloqueos y decisión de lectura

Solo después de resolver G1–G3 bajo autoridad válida, especificar la integración mínima con el contrato existente:

- Validación de esquema tipado antes de seleccionar; semántica conjunctiva de selectores de asistente y destino.
- Evaluación determinista de todos los bloques aplicables con snapshot completo/autenticado del conjunto activo; liberación por bloque desde una autoridad independiente, nunca inferida desde la decisión de lectura.
- Aprobación interactiva fresca por operación y alcance explícito; challenge de un solo uso; identidad y sesión de servidor derivadas de contexto confiable; decisión autoritativa en ledger del servidor, con tiempos/budget finito, expiración, revocación, ligadura al reader y al destino exacto.
- Verificación del reader justo antes de la operación y antes de entregar el resultado; contención resistente a carreras; si el ledger o cualquier dato crítico no está disponible, no servir lecturas.
- Recibo correlacionado que distingue pre-registro durable, intento, resultado observado, entrega y persistencia reconciliada. Un recibo informa lo ocurrido; nunca confiere autoridad por sí solo.

### G7–G8 — Conformidad y aceptación

Después de una autorización de implementación separada: diseñar la matriz negativa/positiva, ejecutar los 38 casos sintéticos M1A requeridos más casos específicos de la frontera MCP/OAuth, adjuntar comandos/entorno/resultados y vincularlos al SHA exacto. Después, un verificador independiente debe recuperar el commit, las pruebas y las evidencias de runtime realmente autorizadas y limitar sus afirmaciones a lo que haya observado.

## 6. Secuencia del trabajo futuro y salidas de cada fase

| Fase | Trabajo propuesto (no ejecutado) | Entregable / salida exigida | Condición de paso |
|---|---|---|---|
| **P1 — Plan** | Reconciliar fuentes públicas, límites y rutas candidatas. | Este plan en una rama documental aislada. | Completada como documentación, sin código/runtime. |
| **P2 — Decisión de autoridad** | Owner aporta autoridad independiente verificable o ratifica opción D. | Registro de decisión y evidencia de autoridad redaccionada/publicable solo en lo necesario. | Sin una raíz independiente, detenerse en D y no implementar. |
| **P3 — Compatibilidad de cliente** | Tras autorización aparte, obtener solo metadatos necesarios del Codex/host y las versiones reales; determinar proceso, transporte y protocolo sin exponer credenciales. | Matriz cliente↔SDK↔OAuth↔callback↔claims, con fuentes/versions y elementos desconocidos explícitos. | Versión concreta soportada y ruta viable, local o HTTP. |
| **P4 — Diseño final de autoridad** | Cerrar contratos de G1–G3, trust root, revocación, catálogo, resolver y ubicación de decisión. | Diseño versionado, secuencia de datos/autoridad, estados de error y criterios de aceptación; sin pseudocapacidades presentadas como existentes. | Autoridad y responsables de evidencia determinados. |
| **P5 — Autorización de implementación** | Owner delimita cambio de código, rama aislada, archivos, pruebas, dependencia exacta, costes y rollback. | Autorización independiente y alcance reproducible. | No inferida desde este plan. |
| **P6 — Implementación aislada** | Cambio mínimo: seguridad de transporte primero; luego el enlace autenticación→principal→decisión por operación→reader/ledger y las herramientas permitidas. | Diff mínimo, versionado, sin secretos; fetch-back verificable. | No ejecutar mientras falte cualquier autoridad. |
| **P7 — Pruebas autorizadas** | Casos sintéticos offline y luego, solo con autorización separada, cualquier verificación de transporte/runtime de alcance limitado. | Resultados correlacionados por caso/commit, con negativas probadas y fallos no ocultos. | Ningún caso requerido puede declararse PASS sin evidencia. |
| **P8 — Revisión independiente** | Releer desde GitHub el SHA exacto y reconciliar diseño, diff, pruebas y recibos. | Veredicto por gate, riesgos abiertos y alcance honesto. | G8 solo cierra con evidencia exacta; la aprobación de diseño no basta. |

## 7. Criterios de aceptación del futuro cambio (no son pruebas ejecutadas)

Debe demostrarse, una vez autorizado, que:

- petición HTTP sin token, token inválido y token válido para otra audiencia reciben denegación antes de ejecutar cualquier herramienta;
- tokens wrong-tenant/issuer, firma desconocida, expirados, prematuros o con claims/scopes incorrectos se rechazan;
- rotación de claves, revocación, cierre de sesión, replay de challenge y tokens reutilizados no permiten acceso no autorizado;
- no puede ejecutarse una operación protegida solo por tener una sesión HTTP autenticada: falta de aprobación, decision ID, alcance explícito, target binding o release independiente implica denegación;
- cambios de ruta/destino, bloque activo, catálogo obsoleto, revocación inalcanzable, presupuesto agotado, fallo de ledger, reinicio o carrera cierran la operación sin entregar datos;
- las herramientas de escritura/ejecución no quedan expuestas por el hecho de añadir OAuth a nivel del servidor;
- no se registra token, código de autorización, secret, UPN, tenant ID u Object ID en logs, pruebas públicas o artefactos;
- la prueba de compatibilidad identifica el SDK MCP y la versión exacta del cliente, no la documentación de una versión distinta;
- la solución no requiere servicio de pago ni crea exposición pública durante la prueba;
- no se afirma que G1–G8 se han cerrado solo por pasar una prueba de autenticación HTTP.

## 8. Pre-scan metacognitivo y límite de esta fase

`AGENTS.md` exige, antes de modificar/planificar una evolución de código, revisar Audit Trail, OSES, contexto portable, ciclo de validación y ExperimentLab. Esta sesión solo tiene autorización de planificación documental; no se accedió al checkout local, runtime, SQLite ni los datos vivos. Por tanto ese pre-scan **no se declara ejecutado** y queda `NOT_RUN / SUPPORTED_AUTHORIZED_ROUTE_NOT_ESTABLISHED`. No se ha creado ni duplicado un servicio de metacognición.

Antes de cualquier trabajo de código se debe resolver la ruta autorizada y compatible para obtener esa evidencia, sin sortear un reader denegado. Si no existe dicha ruta, detenerse y mantener el bloqueo.

## 9. Presupuesto, reversibilidad y condiciones de parada

- Gasto autorizado en esta fase: cero.
- Registros de aplicaciones, secretos, nuevas identidades, licencias, Azure resources, túneles y deployments: ninguno autorizado.
- Cambio de producto, tests, build, runtime, transporte real, lectura protegida, merge y liberación de bloque: no autorizados.
- La rama documental es aislada y parte del SHA de baseline fijado; `main` no debe modificarse por este plan.
- Detenerse si el consumidor real no puede identificarse, la versión exacta no se puede verificar, Entra no puede satisfacer la ruta OAuth bajo las restricciones, la autoridad independiente no existe, la revocación no tiene custodio, o no puede garantizarse el estado fail-closed.
- No repetir la exploración general ya cerrada de Windows/TPM, Google OIDC, passkeys, ni los escaneos genéricos de herramientas. La única pregunta de arquitectura pendiente es qué evidencia de autoridad existe y qué ruta exacta de cliente/transporte está soportada.

## 10. Próxima decisión concreta del Owner

```text
TASK=M1A_G1_ENTRA_MCP_PHASE1_TECHNICAL_PLAN
PLAN_STATUS=DOCUMENTARY_PLAN_COMPLETE
CODE_CHANGED=NO
MAIN_CHANGED=NO
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
TRANSPORT=NOT_RUN
APP_REGISTRATION=NOT_CREATED
SECRETS_CREATED=NO
TUNNEL_LAUNCHED=NO
PAID_RESOURCES=NONE
M1A_NORMATIVE_DESIGN=V1.0.1; ADOPTED_DESIGN_ONLY
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRE_SCAN_METACOGNITIVE=NOT_RUN; AUTHORIZED_ROUTE_NOT_ESTABLISHED
NEXT_ACTION=OWNER_DECISION_ONLY
NEXT_OWNER_DECISION=PROVIDE_VERIFIABLE_INDEPENDENT_AUTHORITY_EVIDENCE_OR_RATIFY_OPTION_D
AUTOMATIC_FOLLOW_ON=FALSE
```

El Owner debe decidir entre aportar/designar una autoridad independiente realmente verificable con mandato, custodio, canal y revocación; o ratificar la opción D y conservar el bloqueo. Ningún otro trabajo se auto-inicia a partir de esta decisión.
