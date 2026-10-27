# M1A G1 — Diseño de bootstrap de confianza con Microsoft Entra (solo documentación)

- Fecha: 2026-10-27 (America/Bogota).
- Tarea: M1A_G1_ENTRA_BOOTSTRAP_DESIGN_DOCUMENTATION_ONLY_20261027.
- Estado: DESIGN_UPDATED_AFTER_INDEPENDENT_REVIEW; OWNER_REVIEW_PENDING; IMPLEMENTATION_NOT_AUTHORIZED.
- Autoridad de esta tarea: respuesta explícita del Owner «sí» a preparar este diseño solo como documentación, sin crear registros, credenciales ni modificar código. El recibo es procedencia de conversación; no autentica por sí mismo una identidad en tiempo de ejecución.

## 1. Dictamen ejecutivo

Microsoft Entra es un candidato razonable para autenticar al Owner, y la documentación oficial actual describe una ruta para proteger servidores MCP HTTP con tokens de acceso de Entra. Eso no significa que el tenant existente ya sea una autoridad G1 de IABV, ni demuestra que una aplicación IABV esté registrada o que el endpoint actual esté protegido.

Este documento convierte la evidencia existente en una propuesta acotada. No cambia la configuración de Entra, no registra aplicaciones, no crea secretos o tokens, no cambia permisos, no modifica código, no ejecuta pruebas, no inicia un servidor ni túnel, y no autoriza lecturas protegidas, merge o despliegue.

La decisión previa de Option D/no-bootstrap permanece vigente para toda operación. La autorización nueva cubre únicamente diseñar esta posible ruta; no autoriza ejecutar el bootstrap ni da por satisfecho G1. El puente continúa bloqueado y fail-closed.

## 2. Qué debe demostrar G1

G1 no equivale a «el Owner puede iniciar sesión en Microsoft». Para considerarlo establecido, la futura implementación deberá demostrar, con evidencia verificable y vinculada al servidor exacto:

1. **Raíz de confianza identificada:** tenant e issuer de Entra fijados de manera inequívoca; API/recurso IABV y audiencia esperada fijados; sin aceptación de tenants, emisores, clientes o audiencias genéricos.
2. **Mandato explícito para IABV:** vínculo comprobable entre la identidad de Entra aprobada y el Owner autorizado de IABV. El nombre visible, el correo, un inicio de sesión exitoso o una afirmación dentro del token sin validación no bastan.
3. **Canal independiente de verificación/control:** una ceremonia local protegida, fuera del propio canal MCP, debe confirmar qué tenant, identidad, recurso, revisión del servidor y permisos se están confiando. Su independencia efectiva debe probarse; el mero diseño no la demuestra.
4. **Vínculo con el servidor concreto:** la confianza debe aplicarse al recurso URL canónico y al proceso/instancia/revisión de IABV previstos, no a cualquier endpoint que presente un token del mismo tenant.
5. **Revocación, vigencia y auditoría:** existe una política comprobable para retirar el mandato, limitar la vigencia de sesiones/tokens y conservar recibos correlacionados sin registrar credenciales.
6. **Separación de controles:** G1 no sustituye a G2 (política/catálogo autorizado y revocación) ni a G3 (resolución de operación y destino exactos). Los tres permanecen separados.

## 3. Arquitectura candidata

- **Proveedor de identidad/autorización:** el tenant de Microsoft Entra ya reportado por el Owner, configurado como single-tenant. Los identificadores exactos se obtendrían y validarían en una fase futura autorizada y se mantendrían fuera del historial público.
- **Cliente MCP:** solicita un token mediante un flujo OAuth que el cliente y la versión exacta del servidor soporten. La compatibilidad real no se ha inspeccionado ni probado. Antes de escoger el flujo debe fijarse el host/cliente exacto y su soporte de OAuth/MCP.
- **Servidor MCP IABV como API/recurso protegido:** valida el token de acceso en cada solicitud HTTP antes de ejecutar herramientas o acceder a datos. El servidor no emite tokens ni acepta un ID token como sustituto de un access token destinado a su API.
- **Registro de mandato G1:** configuración local protegida, versionada y auditable que vincula tenant/issuer, Owner identificado por su ID de objeto, rol autorizado, recurso/audiencia, cliente permitido y servidor/revisión concreta.
- **Canal local de enrolamiento/control:** solo durante una futura fase autorizada, el Owner confirmaría desde la sesión local protegida de Windows el alcance preciso del vínculo. Esa confirmación no puede ser invocable por una herramienta MCP remota. Si la sesión, identidad, límites del proceso o protección de almacenamiento no pueden verificarse, el enrolamiento se cancela.
- **G2/G3 y lector protegido:** siguen siendo puertas independientes. Un token válido de Entra no concede por sí mismo permiso de leer un archivo, ruta, repositorio o destino.

Este modelo es una propuesta de diseño, no una afirmación de que la sesión Windows, el almacén protegido o el canal independiente requerido ya estén comprobados. La sesión Windows no cierra por sí sola el problema de independencia si no se prueba que la identidad local y sus límites de proceso son una fuente de confianza distinta y no controlable desde MCP.

## 4. Configuración de Entra prevista — aún no realizada

En una fase futura con autorización independiente se tendría que evaluar, como mínimo:

1. **Registro de API del servidor MCP.** Registrar el recurso IABV como aplicación single-tenant y configurar access tokens v2. El **Application ID URI** debe coincidir carácter por carácter con el URL canónico del servidor que el cliente envía en el parámetro OAuth **resource** (esquema, host y ruta; sin variaciones de barra final). Esta coincidencia de URL es distinta de la validación del claim **aud**: para tokens v2 de Entra, el **aud** esperado es normalmente el **Application (client) ID** de la API, en formato GUID, según la guía oficial de Microsoft. Por tanto, el verificador debe validar por separado la URL/recurso de MCP y la audiencia real del token; no comparar el aud con la URL por suposición. No reutilizar una URL de prueba como si fuera la identidad del servidor de producción.
2. **URL y transporte.** La guía actual de Microsoft plantea una URL canónica HTTPS para el servidor MCP. Este proyecto todavía no tiene una URL HTTPS pública aprobada ni se ha verificado el runtime local. Por eso no se debe crear ahora una identidad de recurso basada en una URL inventada, abrir un túnel público ni desplegar recursos Azure. Antes de registrar la API habrá que resolver y aprobar la topología exacta, o mantener el uso local/stdio sin afirmar que el flujo OAuth HTTP ya funciona.
3. **Descubrimiento MCP.** El servidor HTTP protegido deberá publicar Protected Resource Metadata (RFC 9728) y anunciar el issuer específico del tenant que corresponda al token v2 aceptado (incluido el issuer v2.0 cuando aplique), con desafíos HTTP 401/WWW-Authenticate apropiados para solicitudes no autenticadas, conforme a la revisión de la especificación MCP que se implemente.
4. **Rol de Owner limitado al recurso IABV.** Evaluar un app role explícito para usuarios/grupos, por ejemplo un rol semánticamente equivalente a IABV.Owner, asignado al usuario exacto solo para la aplicación API de IABV. Los nombres de rol y sus asignaciones reales deben crearse y verificarse en el tenant; no existen por el solo hecho de escribirlos aquí. No autorizar por display name, correo o pertenencia genérica al tenant.
5. **Cliente OAuth.** Elegir y documentar el cliente MCP real y su flujo/redirect URI admitido. La inscripción estática del cliente puede ser necesaria; no dar por supuesto que Entra ofrece Dynamic Client Registration compatible con MCP.
6. **Sin secretos en GitHub.** No almacenar client secrets, access/refresh tokens, cookies, códigos de autorización ni material equivalente en el repositorio, Issues, PRs, logs o memoria conversacional. Preferir un flujo público apropiado para un cliente local si el SDK y el host lo soportan; no crear un secreto por conveniencia sin revisar el modelo de cliente.
7. **Costos.** La ruta mantiene como restricción evitar recursos Azure pagos. No se inspeccionó la suscripción ni el estado de facturación, de modo que coste cero no está garantizado. No activar servicios premium, comprar licencias, cambiar facturación o desplegar recursos como parte de este diseño.

## 5. Validación del access token en el recurso IABV

La futura implementación debe usar una biblioteca de validación mantenida y apropiada para Python/MCP, no una verificación JWT hecha a mano. Antes de ejecutar cualquier herramienta HTTP debe comprobar como mínimo:

- firma criptográfica contra las claves publicadas por el metadata/JWKS tenant-specific esperado, con algoritmos permitidos explícitamente;
- **iss** exacto, **tid** del tenant fijado y emisor de la clave compatible con el issuer del token;
- **aud** exactamente igual al valor esperado para la API IABV en el tipo/versión de token elegidos. Para access tokens v2 estándar de Entra, comprobar el Application (client) ID GUID de la API; no usar automáticamente la URL canónica como aud. Separadamente, el parámetro OAuth resource del cliente debe coincidir exactamente con el Application ID URI/URL canónico registrado. Rechazar tokens para Microsoft Graph, otra API, otro servidor o una audiencia ausente;
- **exp**, **nbf** y tiempos pertinentes dentro de la tolerancia documentada;
- versión/tipo de token esperado y claims de identidad (**oid** y, cuando corresponda, **sub**/actor) vinculados al Owner aprobado; rechazar identidad no asignada o ambigua;
- scope y/o app role esperado para la operación; nunca inferir permiso únicamente de un token válido;
- vinculación al cliente permitido cuando la política y el flujo produzcan un claim de cliente que se pueda validar;
- errores de metadata/JWKS, firma, claims ausentes, configuración o validación con resultado denegado, no con aceptación permisiva.

Los roles incluidos en un access token pueden permanecer hasta que expire el token. La implementación futura deberá definir una ventana máxima de revocación, una vigencia corta y manejable, y el comportamiento al no poder comprobar la configuración vigente. El detalle debe concretarse contra el SDK y flujo elegidos; no asumir revocación instantánea de tokens autocontenidos.

**Compatibilidad del SDK es una puerta obligatoria.** La documentación actual del MCP Python SDK distingue resource_server_url (URL exacta del endpoint) de AccessToken.resource y requiere que el TokenVerifier realice la validación de firma/audiencia. En flujos Entra v2, esa audiencia suele ser el client ID GUID. Antes de implementar, hay que identificar las versiones reales de FastMCP/MCP y probar sus APIs exactas de autenticación, metadata y validación. Si su opción de validación de recurso espera la URL mientras Entra emite aud como GUID, no desactivar la comprobación para hacer pasar el token: hay que configurar correctamente el verificador/adapter y conservar ambas comprobaciones.

No aceptar ID tokens como bearer token de API. No registrar cuerpos de tokens ni valores de Authorization. Las respuestas de autenticación no deben filtrar claims sensibles.

## 6. Ceremonia candidata para vincular la raíz y el mandato

Esta ceremonia queda como diseño para revisión; **no se ejecutó**:

1. El Owner inicia una acción explícita desde la sesión interactiva local del host, nunca a través de una llamada MCP.
2. La interfaz presenta, con identificadores no ambiguos, el tenant/issuer, el Owner de Entra, el rol, el recurso/audiencia exactos, el cliente permitido, el servidor/revisión que quedaría autorizado y el alcance de operaciones. Los IDs sensibles no se copian a un historial público.
3. El sistema valida que la identidad autenticada y su asignación de rol coinciden con la decisión mostrada. No confiar en el nombre mostrado por el cliente sin validación del lado servidor.
4. El Owner confirma deliberadamente el alcance y la duración del mandato por el canal local. Rechazar/cerrar la interfaz no deja una autorización parcial.
5. Solo tras comprobar privilegios y protección del almacenamiento local se escribiría un registro versionado que contenga los identificadores necesarios, la política, el vínculo al servidor/revisión, la fecha, el estado de revocación y el recibo de aprobación. No contiene tokens ni secretos.
6. El sistema vuelve a leer el registro, verifica sus ACL/protección y compara su contenido con lo que se mostró. Una diferencia, un registro ya existente inesperado, un proceso ambiguo o una comprobación fallida cancela el enrolamiento y mantiene fail-closed.
7. La futura evidencia de aceptación debe demostrar que la ceremonia no se puede invocar ni suplantar desde el endpoint MCP, que no permite sustituir el servidor/issuer, y que una retirada del mandato deshabilita la confianza dentro de la ventana definida.

**Límite importante:** aún no se ha demostrado que este canal local satisfaga el contrato de «canal independiente» de G1. La revisión del contrato existente y una prueba específica deberán decidirlo antes de declarar G1. No crear una clave raíz sintética ni elevar automáticamente un login de Entra a autoridad de gobernanza.

## 7. Seguridad de transporte y límites del endpoint actual

La revisión documental de main observó que la ruta de código inspeccionada del constructor FastMCP desactiva la protección de DNS rebinding y permite hosts/orígenes wildcard; la documentación del puente declara que la autenticación de token HTTP está ausente. El runtime real y cualquier túnel activo siguen sin verificarse. Estas observaciones no prueban que haya una exposición activa, pero sí prohíben tratar el endpoint HTTP actual como protegido.

**HTTP y stdio no comparten automáticamente la misma frontera.** La autorización MCP OAuth se aplica al transporte HTTP; el transporte stdio no recibe el header bearer HTTP. Si IABV conserva una ruta stdio, esa ruta necesita su propio contrato de identidad/mandato local y controles de proceso. No se puede afirmar que una prueba del middleware HTTP proteja stdio.

Hasta que una implementación autorizada y verificada cierre esas brechas:

- no iniciar ni reconectar un túnel público;
- no publicar un endpoint HTTP sin autenticar;
- no considerar la allowlist wildcard como autenticación;
- mantener las lecturas protegidas en fail-closed;
- no atribuir al código del PR #531 capacidades que no existen en main.

## 8. Pruebas de aceptación futuras — no ejecutadas

Después de autorizar implementación y elegir una revisión exacta, las pruebas deben demostrar, sin leer datos protegidos reales, como mínimo:

| Caso | Resultado obligatorio |
|---|---|
| Sin token o token malformado | HTTP 401; ninguna herramienta ejecutada |
| Firma inválida, kid desconocido sin clave verificable o issuer/JWKS inaccesible | Denegar; nunca saltarse la validación |
| Tenant o iss distinto | Denegar |
| aud no coincide con el Application (client) ID GUID esperado para el token v2 de Entra | Denegar |
| Parámetro resource del cliente no coincide exactamente con la URL canónica/Application ID URI registrado | La autorización de Entra no debe emitir un token para ese recurso; el flujo debe fallar |
| SDK/verificador compara mal la URL MCP con aud o desactiva el control para evitar el conflicto | Prueba de configuración fallida; no autorizar despliegue |
| aud de Graph, otra API, otro URL o ausente | Denegar |
| ID token enviado como bearer de MCP | Denegar |
| Token expirado o aún no válido | Denegar |
| oid distinto del Owner vinculado | Denegar |
| Rol/scope requerido ausente o asignación revocada más allá de la ventana máxima declarada | Denegar |
| Cliente no permitido o recurso/servidor distinto | Denegar |
| Estado de la raíz, mandato, G2 o G3 no configurado, caduco, conflictivo o no verificable | Denegar lectura protegida |
| Metadata MCP/401/WWW-Authenticate y flujo del cliente | Compatible con la versión MCP y el host que se hayan fijado |
| La misma suite se ejecuta contra HTTP y stdio | La prueba HTTP valida bearer/OAuth; stdio debe demostrar controles propios de proceso/identidad local, sin asumir protección por HTTP |
| Hosts/orígenes no permitidos y ataques de DNS rebinding | Rechazados por configuración explícita; no wildcard permisivo |
| Reinicio, token repetido y revocación | Respeta vigencia, revocación y auditoría sin revelar credenciales |
| Cambio de revisión/servidor o URL | La vinculación anterior no autoriza automáticamente el nuevo destino |

Además de las pruebas del verificador, se debe probar el punto de consumo: el lector recibe una decisión fresca y ligada a la operación y al destino exactos antes de cualquier lectura. Un conjunto de pruebas de JWT aprobado no establece por sí solo G1, G2 o G3.

## 9. Secuencia y puertas de autorización

- **Fase A — diseño documental (esta tarea):** completada documentalmente cuando el archivo se guarde y se verifique por lectura de vuelta. No cambia runtime.
- **Fase B — revisión del Owner y fijación de decisiones:** confirmar el contrato de canal independiente, la topología/transporte y la política de identidad/revocación. Esta revisión no requiere repetir la configuración de Entra.
- **Fase C — configuración de Entra:** requiere autorización nueva y específica antes de inspeccionar/crear registros, asignar roles, añadir redirect URIs o cambiar permisos. Capturar IDs por canal privado; no compartir secretos.
- **Fase D — código y revisión:** requiere autorización separada ligada a la revisión/branch/archivos exactos. Integrar validación con biblioteca, middleware HTTP/MCP, metadata y deny-by-default; sustituir wildcard por controles explícitos; conservar pruebas y revisión independiente. No modificar código como parte de la presente tarea.
- **Fase E — bootstrap local:** autorización específica y ceremonia local aprobada; no automatizarla al arranque ni desde MCP.
- **Fase F — pruebas localmente acotadas:** autorización de pruebas y ejecutor identificado, con resultados y logs saneados. Actions sigue bloqueado por el estado ya documentado hasta que exista evidencia material nueva.
- **Fase G — exposición/lecturas protegidas:** no permitida hasta que G1, G2 y G3 se establezcan con evidencia independiente, aceptación y decisión explícita de habilitación. Un eventual túnel/deployment necesita autorización adicional y presupuesto validado.

No hay seguimiento automático entre fases. Ninguna etapa se inicia solo porque la anterior generó un documento.

## 10. Evidencia de origen y referencias oficiales

Estado de origen revalidado antes del diseño:
- CURRENT-STATE.md en main, blob 86ea4095f890ce03867a3eba1c77a1c6624f1027.
- evaluación estática previa de Entra, blob 025a126f8848cab4ac0e6b33f8bd9f2e4740dda6.
- pyproject.toml en main, blob 22827c38cc3f7ee3bd3e16f6ed3ec0543841beb1.
- src/iabv_v15/infra/mcp/server.py en main, blob 17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c.
- docs/mcp-bridge.md en main, blob e53709d10a7a40d089cc8a55c94a4a23f620718e.

Referencias:
- Microsoft: [Secure an MCP server with Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/agent-id/secure-mcp-server-with-entra-id) — registro de API, access tokens v2, coincidencia exacta del recurso, metadata MCP y validación.
- Microsoft: [Access tokens](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens) — la API valida sus access tokens y audiencia; ID tokens son distintos.
- Microsoft: [Implement role-based access control](https://learn.microsoft.com/en-us/entra/identity-platform/howto-implement-rbac-for-apps) — los roles de aplicación se definen y asignan en el registro.
- MCP: [Authorization specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) — autorización HTTP, Protected Resource Metadata y reglas de tokens.
- MCP Python SDK: [Authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/) — el servidor actúa como resource server; el verificador de token es responsabilidad explícita de la integración.

## 11. Revisión técnica independiente — correcciones obligatorias (2026-10-27)

Se contrastó este diseño contra la guía vigente de Microsoft para proteger servidores MCP con Entra, la especificación de autorización MCP 2025-11-25 y la guía vigente del MCP Python SDK. La revisión fue documental y no accedió al portal Entra ni a un runtime local.

### Corrección 1 — URL del recurso y claim aud son valores distintos

Para el flujo MCP de Entra con access tokens v2, el parámetro resource que envía el cliente debe coincidir exactamente con el Application ID URI registrado para el servidor. Sin embargo, la guía de Microsoft indica que el claim aud de un token v2 estándar identifica la API mediante su Application (client) ID, generalmente el GUID. El futuro verificador deberá validar ambos conceptos según el flujo exacto y no asumir que aud es igual a la URL canónica. Las secciones de configuración, validación y pruebas de aceptación fueron precisadas para expresarlo.

### Corrección 2 — compatibilidad específica del SDK es precondición

La guía actual del MCP Python SDK distingue resource_server_url (URL exacta del endpoint) de AccessToken.resource y requiere que el TokenVerifier haga la validación real de firma/audiencia. La dependencia real y las versiones MCP/FastMCP usadas por el runtime IABV aún no se han comprobado. En la fase de implementación debe inspeccionarse el contrato exacto del SDK y diseñarse un verificador que valide el aud GUID de Entra y el recurso esperado sin deshabilitar la comprobación de audiencia ni aceptar tokens ajenos al servidor.

### Corrección 3 — HTTP y stdio requieren contratos separados

La especificación de autorización MCP se aplica a transportes HTTP; el transporte stdio no recibe el header bearer HTTP. Si el producto usa ambos, la protección OAuth no cubrirá por sí sola las invocaciones stdio: se necesitará una frontera local verificable para proceso, usuario y mandato. Esto no está implementado ni demostrado en la revisión actual.

### Resultado y limitaciones

La arquitectura Entra sigue siendo viable como candidato de autenticación, pero G1 no está establecido. La ceremonia local descrita sigue siendo una hipótesis de canal independiente; una confirmación interactiva de Windows no basta hasta demostrar la identidad local, los límites del proceso y que la ceremonia no es invocable desde MCP. El diseño no autoriza ni ha realizado registros, credenciales, permisos, código, pruebas, runtime, túneles, lecturas protegidas o despliegue.

Fuentes consultadas el 2026-10-27:
- Microsoft, [Secure an MCP server with Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/agent-id/secure-mcp-server-with-entra-id), especialmente secciones de recurso/Application ID URI, token v2, metadata y validación.
- MCP, [Authorization specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), requisitos de audiencia y prohibición de token passthrough.
- MCP Python SDK, [Authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/), separación entre URL de recurso y verificación real del token, y límite HTTP vs stdio.

- DESIGN_REVIEW=INDEPENDENT_DOCUMENTARY_REVIEW_COMPLETE; CORRECTIONS_RECORDED
- OWNER_REVIEW=PENDING
- IMPLEMENTATION=NOT_AUTHORIZED
- G1=NOT_ESTABLISHED

## 12. Estado terminal de esta tarea

- TASK=M1A_G1_ENTRA_BOOTSTRAP_DESIGN_DOCUMENTATION_ONLY_20261027
- DESIGN=UPDATED_AFTER_INDEPENDENT_REVIEW; OWNER_REVIEW_PENDING
- SCOPE=DOCUMENTATION_ONLY
- ENTRA_IDENTITY_PROVIDER_CANDIDATE=PLAUSIBLE_FOR_OWNER_AUTHENTICATION
- ENTRA_AS_STANDALONE_G1_AUTHORITY=NOT_ESTABLISHED
- OPTION_D=FAIL_CLOSED_OPERATIONALLY; DESIGN_CORRECTED; OWNER_REVIEW_PENDING
- APP_REGISTRATION=NOT_CREATED_OR_NOT_REPORTED; PORTAL_NOT_INSPECTED
- SOURCE_MODIFICATION=NOT_AUTHORIZED; NOT_DONE
- TESTS=NOT_RUN
- BUILD=NOT_RUN
- RUNTIME=NOT_RUN
- REAL_TRANSPORT=NOT_RUN
- PROTECTED_READS=FAIL_CLOSED
- G1=NOT_ESTABLISHED
- G2=NOT_ESTABLISHED
- G3=NOT_ESTABLISHED
- IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
- MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
- BRIDGE=BRIDGE_NOT_READY
- NEXT_ACTION=OWNER_REVIEW_OF_CORRECTED_DESIGN; SEPARATE_AUTHORIZATION_REQUIRED_FOR_ANY_IMPLEMENTATION
- AUTOMATIC_FOLLOW_ON=FALSE
