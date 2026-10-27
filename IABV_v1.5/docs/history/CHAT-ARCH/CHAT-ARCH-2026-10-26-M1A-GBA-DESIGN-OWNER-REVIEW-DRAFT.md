# M1A GBA — diseño gobernado de autoridad (borrador de revisión del Owner)

- Fecha: 2026-10-26, America/Bogota.
- Tarea: M1A_GBA_GOVERNED_AUTHORITY_DESIGN_OWNER_REVIEW.
- Estado: DRAFT_FOR_OWNER_REVIEW.
- Rama de revisión: m1a-gba-design-review-20261026.
- Base remota observada: main=cac98375e4e94547ddfa89b30acab6b24ca769e2.
- Alcance: diseño, requisitos, decisiones abiertas y artefactos futuros de aceptación.
- Cambios de código/runtime: ninguno.
- Adopción canónica: no solicitada ni efectuada.
- Implementación, provisión de autoridad/credenciales, pruebas y lecturas protegidas: no autorizadas por este documento.

## 1. Propósito y dictamen preliminar

Este borrador desarrolla los requisitos de G1, G2, G3, emisor, IPC, replay y contexto confiable. Los nombres de roles, artefactos y relaciones son elementos propuestos de diseño, no evidencia de servicios, custodios, claves o canales actualmente existentes.

**Dictamen preliminar:** CONDITIONAL_DESIGN_REVIEW; OWNER_REVIEW_REQUIRED. La propuesta debe mantener la opción D —sin ancla demostrada, sin bootstrap y con denegación— mientras una raíz independiente, su mandato, custodia y canal de verificación no estén demostrados. El borrador no selecciona una autoridad, persona, organización, plataforma, mecanismo IPC ni proveedor.

La adopción normativa previa de M1A v1.0.1 es exclusivamente de diseño. No constituye una credencial de runtime ni autoriza implementación, pruebas, build, acceso al checkout local, transporte real, merge, deployment, lectura protegida o liberación de bloqueos.

Referencias rectoras:
- [CURRENT-STATE.md](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md).
- [Reconciliación estática de diseño GBA](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-static-reconciliation.md).
- [Contrato consolidado Entry 274](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md).
- [Matriz de los ocho prerrequisitos M1A](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md).
- [Recibo de adopción explícita M1A v1.0.1](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-v1_0_1-explicit-owner-adoption-receipt.md).

## 2. Modelo de confianza y flujo de decisión

El diagrama separa de forma deliberada **delegación de autoridad**, **flujo de solicitud/respuesta** y **persistencia**. Una conexión de datos no demuestra confianza; cada relación de autoridad exige evidencia propia, vigente, exacta, verificable y revocable.

~~~mermaid
flowchart LR
    ROOT["Raíz independiente<br/>aún no demostrada"]
    GBA["GBA gobernada<br/>rol de diseño"]
    OWNER["Owner autenticado<br/>aprobación fresca"]
    G2["Catálogo G2<br/>publicadores, clases, versión, revocación"]
    G3["Registro G3 versionado<br/>operación → destino autorizado"]
    ISSUER["Emisor protegido<br/>decisión server-side"]
    IPC["IPC autenticado<br/>peer, sesión, challenge"]
    READER["Reader/servidor exacto<br/>reverifica antes de operar"]
    HANDLE["Handle del objeto<br/>el mismo que se consume"]
    DECISION["Registro autoritativo<br/>decisión y presupuesto"]
    REPLAY["Estado replay/challenge<br/>durable y anti-rollback"]
    LEDGER["Ledger operacional<br/>intención, resultado, entrega y recibo"]
    BLOCK["Autoridad independiente<br/>de release por bloqueo"]

    ROOT -->|"delegación verificada"| GBA
    GBA -->|"delegación limitada"| ISSUER
    GBA -->|"política/mandato"| G2
    GBA -->|"mandato de registro"| G3
    OWNER -->|"aprobación fresca"| ISSUER
    G2 -->|"catálogo y revocación vigentes"| ISSUER
    G3 -->|"mapping autorizado"| ISSUER
    ISSUER -->|"solicitud autenticada / referencia no autoritativa"| IPC
    IPC -->|"sesión y peer verificados"| READER
    READER -->|"consume el objeto ya autorizado"| HANDLE
    ISSUER --> DECISION
    ISSUER --> REPLAY
    ISSUER --> LEDGER
    READER --> LEDGER
    BLOCK -.->|"release separada; hoy no demostrada"| READER
~~~

El diagrama no declara que exista ninguno de estos servicios. Cada enlace deberá tener una evidencia y un responsable propios. La autoridad para crear o revocar raíces, mandatos, catálogo, mappings G3, decisiones, releases de bloqueo y recibos no puede inferirse de la capacidad técnica de conectarlos.

### Semántica obligatoria de la decisión

- La aprobación fresca del Owner, la decisión del emisor, la verificación inmediata del reader, el resultado de la operación, la entrega de contenido y el recibo son etapas distintas.
- La decisión de lectura es un **registro autoritativo del lado del servidor**, ligado a la sesión, instancia, reader, target, scope, expiración y presupuesto. No es un token bearer transferible ni una credencial reutilizable.
- El IPC transporta mensajes autenticados y, cuando proceda, referencias de decisión que no conceden autoridad por sí mismas. El reader consulta/verifica el estado autoritativo apropiado y revalida los requisitos inmediatamente antes de actuar.
- Un ALLOW, una firma válida, un hash, un ID, un recibo o una respuesta positiva de un adapter no sustituyen la validación del reader ni liberan un bloqueo de gobernanza.
- La ausencia, ambigüedad, inconsistencia, caducidad, revocación no comprobable o pérdida de estado autoritativo produce denegación.

Este flujo conserva la separación de Entry 274 entre aprobación, decisión, verificador del reader y ledger.

## 3. Alternativas de anclaje y decisión actual

Las alternativas son opciones conceptuales, no sistemas existentes:

| Opción | Fuente inicial | Condición necesaria | Estado con la evidencia disponible |
|---|---|---|---|
| A — Raíz Owner preexistente | Clave/certificado cuya relación con la responsabilidad sobre IABV ya se hubiera establecido de forma independiente. | Fingerprint autenticado fuera del host y del canal solicitante, mandato, custodia, recuperación y revocación verificables. | No demostrada. |
| B — Autoridad organizacional existente | Autoridad con jurisdicción real sobre el proyecto. | Identidad, mandato, delegación al proyecto y revocación verificados desde una base independiente. | No demostrada; no se presupone organización alguna. |
| C — Nueva autoridad delegada | Ceremonia para una nueva raíz bajo una autoridad externa ya confiable. | Una autoridad preexistente debe autenticar la ceremonia y el fingerprint nuevo por canal independiente. | No admisible si no se prueba primero la raíz delegante; no crea confianza desde cero. |
| D — Sin ancla demostrada | Ninguna. | Mantener el bloqueo y registrar la evidencia faltante. | **Disposición requerida por la evidencia actual.** |

**Condición de parada:** si no se puede demostrar una raíz, su mandato sobre IABV, el custodio y el canal independiente, el estado es UNANCHORED. No se inicializa bootstrap, no se emiten credenciales y no se habilitan lecturas.

## 4. Custodia, establecimiento, rotación y revocación de la raíz

### Decisiones previas que corresponden a gobernanza

Gobernanza debe identificar mediante decisión separada:
- custodio accountable y suplente;
- quién propone, verifica y aprueba operaciones sobre la raíz;
- quórum y separación de funciones, incluyendo tratamiento de conflictos;
- recuperación, sucesión, respuesta ante compromiso y pérdida de custodia;
- verificador independiente y canal de verificación fuera del host, del issuer, del reader y de la solicitud que pide acceso;
- política de alcance, vigencia y revocación;
- amenazas dentro y fuera del modelo, en particular administrador local, SYSTEM, kernel y recuperación física/lógica del equipo.

**Estado:** DECISION_NECESARIA. No se designa aquí una persona, organización, proveedor, algoritmo de quórum, hardware ni período temporal.

### Ceremonia de establecimiento propuesta — no ejecutada

1. Identificar la fuente A o B, la autoridad con mandato, los custodios, el alcance sobre IABV y el canal independiente.
2. Verificar la autoridad fuera del workspace y de los procesos requester, issuer y reader.
3. Publicar un charter versionado que registre identidad/fingerprint, cadena, alcance, delegaciones, custodios, quórum, secuencia monotónica, vigencia, revocación, recuperación y sucesión.
4. Verificar de manera independiente el fingerprint y el mandato por un canal previamente confiable, distinto del que solicita acceso.
5. Si falta cualquier elemento esencial, detenerse con BLOCKED_MISSING_GOVERNANCE_BOOTSTRAP_ANCHOR.

No son raíces válidas por sí solas una clave creada localmente, la confianza TOFU en el primer uso, un SID, un privilegio de administrador, una firma bajo una clave suministrada, un evento de merge, un hash de Git, una aprobación conversacional o el propio issuer futuro.

### Rotación y revocación

El diseño requiere que la rotación sea autorizada por la raíz vigente, secuenciada, correlacionada y verificada independientemente. El host o la entidad enrolada no pueden sustituir el pin de confianza. Cada raíz, delegación, credencial Owner, issuer, publicador G2, versión G3 y registro de servidor debe tener un estado de revocación identificable.

Una fuente de revocación ausente, desactualizada, contradictoria, inaccesible o sin prueba de autoridad implica denegación. Ante compromiso de raíz se bloquea el sistema y se exige recuperación externa; no se regenera localmente una raíz bajo la misma identidad. Ventanas de rotación, TTL de revocación y parámetros de recuperación quedan pendientes de decisión y evidencia; no se inventan valores.

## 5. Vinculación Owner → principal local → issuer → reader/servidor

El enrolamiento debe demostrar por separado:

1. **Owner → rol de gobernanza:** credencial preinscrita bajo una raíz válida, prueba de posesión y aprobación fresca ligada a un challenge, propósito y alcance concretos.
2. **Owner → principal local:** principal obtenido del contexto autenticado del sistema operativo, no de un campo suministrado por el caller.
3. **Principal/instalación → issuer:** delegación que liga clave pública, identidad del servicio, release/artefacto y ámbito autorizado.
4. **Issuer → instancia exacta:** identidad registrada del reader/servidor, sesión autenticada, versión de política y binding del workspace/checkout.
5. **Reader → operación concreta:** operación real registrada y destino derivado del contexto confiable y G3.

Un SID, PID, ruta, nombre de proceso, fingerprint, hash, respuesta MFA o campo peer_identity aislado no demuestra estos enlaces. La posibilidad de utilizar Windows Hello/WebAuthn, CNG o un mecanismo específico de Windows no demuestra que exista enrolamiento ni binding para IABV; su aceptabilidad depende de evidencia de plataforma y revisión separada.

**Estado:** vínculo de raíz y principal NOT_ESTABLISHED; issuer y servidor exactos NOT_ESTABLISHED.

## 6. Enrolamiento del issuer e IPC autenticado

El issuer tendría identidad, clave y delegación limitadas, separadas del requester y del reader. La clave privada no sería accesible al requester ni al reader. El enrolamiento debe vincular el issuer con el release verificado, la clave pública, el principal de servicio, el reader/servidor y la política aplicable.

El canal IPC requiere como mínimo:
- autenticación del peer por una autoridad del sistema operativo y autorización de acceso limitada al principal del servicio;
- desafío/respuesta frescos con protección contra replay;
- vínculo criptográfico entre solicitud, sesión, instancia, issuer, reader, target y política;
- comportamiento definido ante suplantación del endpoint, sustitución del proceso, reutilización del PID, desconexión y mensajes fuera de secuencia;
- verificación inmediata por el reader, sin delegar la decisión a datos no autenticados recibidos por IPC.

No se elige en este borrador un servicio, named pipe, mecanismo de custodia o ACL concretos. El diseño debe someter la alternativa seleccionada a revisión específica de Windows antes de autorizar implementación.

**Estado:** ISSUER_IPC=NOT_ESTABLISHED; el contrato de interfaz no demuestra adapter productivo, servicio issuer, límites de proceso ni autenticación real del peer.

## 7. Catálogo G2: productores, integridad y revocación

Un catálogo admisible debe identificar como mínimo:
- publicadores autorizados y delegaciones vigentes;
- clases de productor y allowlists por clase;
- versiones, integridad, vigencia y ciclo de publicación/retiro;
- revocaciones de publicadores, productores, mandatos y políticas;
- secuencia/epoch monotónico, completitud y freshness;
- attestation firmada por una autoridad cuya confianza se haya establecido independientemente.

Issuer y reader deben rechazar catálogo incompleto, no autenticado, ambiguo, rollbackeado, vencido, sin attestation de completitud o con revocación inaccesible. Un snapshot vacío solo es admisible si una autoridad confiable certifica explícitamente que está completo y vigente. Digest, schema, recibo, manifest o snapshot observacional no establecen autoridad del publicador.

**Estado:** existen tipos y evaluación parcial en fuente candidata; el publicador confiable, el catálogo autoritativo, la allowlist y la fuente de revocación están NOT_ESTABLISHED.

## 8. Resolver G3 y binding al mismo objeto consumido

G3 debe ser un registro versionado y gobernado del lado del servidor que mapee cada operación protegida real a su implementación/call site, workspace y checkout registrados, reglas de destino autorizadas y versión de política. La solicitud del caller puede señalar un nombre de ruta solicitado, pero no definir por sí misma operación confiable, autoridad, workspace, root, scope ni destino canónico.

Requisitos:
- root del workspace y checkout con identidad estable y registro de ciclo de vida; no basta una cadena de ruta;
- mappings G3 versionados, revisados, con autoridad, publisher/custodio y estado de revocación identificables;
- target derivado del registro del servidor y de la operación real, nunca de un scope autorreferenciado por el caller;
- decisión ligada a la identidad del target abierto;
- reader consume exactamente el objeto abierto y autorizado, sin una segunda resolución por ruta después del ALLOW;
- para listados, autorizar el handle de un directorio no autoriza automáticamente leer sus hijos;
- cambios, contradicciones o pérdida de identidad del objeto invalidan la decisión y deniegan.

La apertura relativa por handle y el consumo mediante el mismo handle son mecanismos técnicos presentes en la fuente candidata, pero no acreditan la aprobación de la raíz, el registro G3, ni la identidad del workspace. La viabilidad de una primitiva no constituye autoridad operativa.

**Estado:** G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED; APPROVED_WORKSPACE_ROOT_PROVIDER=NOT_ESTABLISHED.

## 9. Decisión del servidor, IPC y semántica de autorización

La decisión no debe convertirse en un token bearer transferible. Entry 274 exige una decisión autoritativa del lado del servidor, enlazada a la sesión y al reader/target previstos, con presupuestos finitos y registro atómico.

Antes de operar, el reader debe verificar:
- referencia a una decisión existente y autoritativa;
- sesión/instancia/reader/target y scope coincidentes;
- referencia a una decisión autoritativa que demuestre que el issuer verificó una aprobación fresca y un evento UI auténtico ligado al scope; el reader no confía en datos de UI aportados por el caller ni necesita consumir directamente una credencial de interfaz;
- política y revocación vigentes;
- estado del bloqueo aplicable y release independiente, si alguna vez existe;
- vigencia y presupuesto disponible;
- binding del objeto abierto y contexto del host;
- integridad y disponibilidad del ledger.

Una decisión desconocida, registro ausente, ledger inconsistente/perdido, escritura atómica fallida, revocación inaccesible, presupuesto no recuperable o binding contradictorio produce denegación. Tras reinicio no se reconstruyen permisos desde el caller, un token copiado ni defaults in-memory.

## 10. Replay, anti-rollback y ledger operativo

Las responsabilidades relacionadas deben distinguirse en el diseño aunque en el futuro compartan una infraestructura:

1. **Registro de challenges/replay:** consumo único y atómico de nonce/challenge, expiración, vínculo con sesión/decisión y rechazo de duplicación.
2. **Estado de decisión/presupuestos:** decisiones server-side, contabilidad de presupuestos y recuperación de intents no resueltos.
3. **Ledger operacional:** eventos correlacionados de predecisión, intento de operación, resultado observado, intento de entrega, resultado de entrega y recibo.

Cada registro debe tener controles de acceso y escritura definidos. La arquitectura debe decidir si usa almacenes separados o límites lógicos y de permisos equivalentes. La generación/epoch debe estar anclada fuera del almacenamiento que un requester pueda restaurar libremente. La pérdida, restauración de snapshot, corrupción, discontinuidad, contradicción o estado ambiguo detiene las lecturas; no se reinicializa el ledger para restaurar disponibilidad.

Un recibo solo prueba lo realmente observado y persistido. Un intento no demuestra entrega; una respuesta visible no demuestra persistencia canónica; un ID correlacionado por sí solo no acredita causalidad ni aprendizaje.

**Estado:** la candidata contiene una clase SQLite de consumo único, pero no está conectada como autoridad operacional protegida y no detecta por sí sola la restauración de un snapshot válido anterior. Replay protegido contra rollback NOT_ESTABLISHED.

## 11. Frescura y límites temporales

Entry 274 propone estos límites conservadores para aprobación y decisión:
- challenge de aprobación: máximo 120 segundos;
- intervalo entre aprobación interactiva y emisión: máximo 60 segundos;
- vida de la decisión desde emisión del servidor: máximo cinco minutos.

Este borrador los conserva como **parámetros de referencia del diseño**, no como valores aplicados en runtime ni como aceptación de implementación. Antes de una futura especificación implementable, el Owner debe ratificarlos como requisitos de diseño o decidir otros valores mediante una revisión explícita. No deben alterarse silenciosamente como simples parámetros de configuración.

Issuer y reader deben usar reloj confiable de servidor para evidencia temporal y reloj monotónico para vencimiento transcurrido en proceso. Freshness/revocación se comprueban al emitir, al reservar cada intent y antes de entregar contenido. Si la decisión vence o se revoca durante una operación, se descarta el contenido en staging y no se entrega.

Estos límites no fijan las ventanas de rotación, expiración de raíces, delegaciones, catálogos o revocaciones; siguen pendientes de decisión y evidencia.

## 12. Liberación de bloqueos: frontera independiente

Una decisión válida de lectura **no libera un bloqueo de gobernanza**. El issuer y el reader no pueden inferir una liberación a partir de identidad, aprobación del Owner para leer, merge, hash, firma, catálogo, G3 o recibo.

Si aplica cualquier bloqueo y no existe una release independiente, actual, autenticada y autorizada por la autoridad responsable de ese bloqueo, el resultado es terminal:

**BLOCK_RELEASE_UNSUPPORTED → DENY**

Una release futura necesitaría diseño y autorización separados y tendría que quedar ligada como mínimo al ID y revisión/contenido del bloqueo, target, operación/scope, autoridad, principal, emisión, expiración y revocación. El reader la verifica independientemente en la frontera protegida. No se presupone que exista hoy un mecanismo de release.

## 13. Autorización precisa: reducir bloqueos innecesarios sin rebajar garantías

El objetivo operativo es que el órgano pueda avanzar con el mínimo bloqueo necesario **sin convertir una incertidumbre de seguridad en permiso implícito**. La unidad de decisión no debe ser “el proyecto entero está bloqueado” por defecto; debe ser la capacidad concreta solicitada y el límite de confianza que esa capacidad necesita. No obstante, si falta una dependencia que Entry 274 exige para todas las lecturas protegidas (por ejemplo, un ancla confiable aún no establecida), todas esas lecturas siguen denegadas. La granularidad evita bloqueos ajenos; no salta gates requeridos.

### 13.1 Clases de estado que no deben confundirse

| Clase | Cuándo aplica | Comportamiento requerido | Qué no significa |
|---|---|---|---|
| **Invariante de confianza global de lectura** | La raíz, el mandato, el issuer confiable, el contexto obligatorio o la política autoritativa no están establecidos para la superficie protegida. | Denegar todas las operaciones protegidas que dependen de esa invariante; exponer solo diagnóstico mínimo no-contento permitido por el contrato. | No significa que se deban detener tareas documentales, diseño, lectura de documentación pública o comprobaciones que no accedan al contenido protegido. |
| **Bloqueo de gobernanza aplicable al scope** | Un bloqueo autoritativo, vigente y evaluable aplica a la operación/target solicitados. | Evaluar el conjunto completo de bloqueos; denegar esa operación/scope salvo release independiente, válida y actual para cada bloqueo aplicable. | No convierte un bloqueo de scope local en global si el registro autoritativo no lo define como global. No se infiere que bloqueos no consultados no existan. |
| **Entrada o contexto de solicitud inválido** | Falta principal autenticado, identidad de servidor/checkout/target, operación registrada, binding del objeto o un campo obligatorio no puede derivarse de una fuente confiable. | Denegar ese intento con un código estable y el requisito faltante; no intentar “reparar” la identidad usando valores del caller. | No es un fallo genérico de todo el proyecto salvo que el componente sea una dependencia común y necesaria de la superficie protegida. |
| **Dependencia obligatoria indisponible** | No se puede verificar el catálogo, frescura, revocación, decisión, ledger, resolver o estado monotónico requerido. | Denegar las operaciones protegidas que necesitan esa dependencia; registrar el motivo y no usar fallback obsoleto salvo que una política gobernada haya definido explícitamente una garantía de freshness acotada. | No autoriza a ignorar la dependencia, usar una respuesta cacheada indefinidamente ni confundir disponibilidad con autoridad. |
| **Scope, presupuesto o vigencia insuficiente** | El scope es mayor al aprobado, el presupuesto está agotado o la decisión expiró. | No ampliar ni reutilizar la decisión. Permitir una nueva solicitud más estrecha solo mediante el flujo de aprobación fresca exigido por el contrato. | No es un bloqueo del usuario para operaciones futuras que puedan solicitarse legítimamente bajo otra aprobación y un scope compatible. |
| **Bloqueo de infraestructura/CI** | Por ejemplo, la cuenta/Actions no permite iniciar jobs. | Marcar pruebas y validación CI como no ejecutadas; conservar evidencia del bloqueo y avanzar en trabajo documental no dependiente de CI. | No demuestra ni refuta la raíz de confianza de IABV, no prueba fallo de los tests y no habilita una ejecución alternativa no autorizada. |
| **Diagnóstico mínimo** | El caller necesita saber por qué una operación se denegó. | Devolver solo códigos, IDs de bloqueo autorizados para exposición, dependencias ausentes y siguiente requisito permitido; no leer contenidos del repositorio ni conceder autoridad. | No equivale a aprobación fresca, decisión de lectura, release de bloqueo ni recibo de entrega. |

Esta clasificación no cambia el estado de la autoridad. Con la evidencia actual, G1 sigue sin establecerse y el acceso protegido al repositorio debe permanecer fail-closed. Sí evita que una carencia de CI o un bloqueo de un scope se convierta por inferencia en prohibición de trabajo documental no relacionado.

### 13.2 Orden determinista de evaluación

Una futura implementación autorizada debe aplicar, en orden, el siguiente contrato lógico:

1. **Clasificar la capacidad pedida** antes de acceder a contenidos: diagnóstico sin contenido, actividad documental no protegida, o lectura/listado protegido. No reclasificar una lectura de contenido como diagnóstico.
2. **Derivar identidad desde el host**: principal, instancia, operación registrada, workspace/checkout y target. No completar bindings con afirmaciones del caller.
3. **Validar prerequisites comunes** para esa capacidad. Si falta una invariante obligatoria, denegar esa capacidad protegida y explicar el requisito sin iniciar lecturas.
4. **Obtener el estado autoritativo completo** de política, catálogo y bloqueos aplicables. Si no se puede acreditar completitud, freshness o revocación, denegar; un snapshot parcial no equivale a “sin bloqueos”.
5. **Evaluar todos los bloqueos** contra el scope canónico y versionado. La evaluación debe ser determinista e independiente del orden. Si uno o más aplican y carecen de release independiente, denegar terminalmente.
6. **Crear una decisión server-side** solo después de verificar approval fresca, política, target, scope y presupuestos; el ID de decisión no es portador de permiso.
7. **Reverificar en el reader** justo antes de actuar y consumir el mismo objeto abierto que se autorizó. Si cambió el binding, la política, la revocación, el presupuesto o la vigencia, denegar y no entregar staging.
8. **Registrar resultado observado** separado de intento y entrega. El recibo no puede adelantar un resultado ni alterar el bloqueo.
9. **Emitir un diagnóstico mínimo y accionable**: capacidad denegada, razón estable, evidencia faltante, scope afectado, condición que permitiría reevaluar y si existe o no un cambio de precondición. No presentar todos los fallos como “puente bloqueado” sin causa.

### 13.3 Prevención de bloqueos amplios y bucles

- Las decisiones son por operación y scope. No se comparten permisos entre lectura, listado, diagnóstico, operación de escritura, ni entre sesiones, instancias, checkouts o targets.
- Un bloqueo se propaga a todo el órgano solo si la política autoritativa lo clasifica como global o si falta una dependencia común necesaria para todas las operaciones protegidas. No se infiere globalidad por comodidad de implementación.
- La denegación por un requisito desconocido debe conservar el código del requisito desconocido. No se rebaja a advertencia, pero tampoco se inventa un bloqueo de otros scopes que no se evaluaron.
- Ante la misma combinación de operación, target, conjunto/versiones de bloqueos y precondición faltante, no se repite indefinidamente la misma solicitud, prompt, workflow ni auditoría. Se registra el último resultado y se espera un cambio de precondición verificable o una nueva decisión de gobernanza.
- Reintentar se permite solo si existe una condición nueva material o una política específica de retry que pruebe que la operación previa no consumió presupuesto, challenge ni estado de un solo uso. En caso de duda, no reusar decisión o nonce.
- Un error de infraestructura se mantiene en el plano de infraestructura: por ejemplo, la restricción actual de GitHub Actions mantiene `TESTS=NOT_RUN`, pero no altera la decisión G1/G2/G3 y no justifica reabrir el diagnóstico de productores ya cerrado.
- La salida de diagnóstico debe facilitar el siguiente paso legítimo —obtener la evidencia, reducir scope, corregir una referencia, o solicitar una decisión al Owner— y nunca dar un camino alterno para leer, sortear el reader, evitar revocación o liberar un bloqueo.

### 13.4 Criterios futuros de aceptación de baja fricción

Después de una autorización independiente para implementar y probar, las pruebas de conformidad deberían demostrar tanto seguridad como ausencia de bloqueos innecesarios:

1. Un scope denegado no autoriza ese mismo scope; una petición independiente y más estrecha puede seguir el flujo normal si satisface por sí misma todos los gates.
2. Un bloqueo no aplicable no se trata como aplicable, pero la autoridad debe acreditar que el conjunto de bloqueos está completo y que sus reglas de scope son compatibles.
3. Catálogo, revocación, resolver o ledger ausentes no se confunden con listas vacías ni se sustituyen por estado obsoleto.
4. Diagnóstico devuelve motivos mínimos sin contenido y sin otorgar permiso.
5. Fallos repetidos con la misma precondición no desencadenan reintentos ilimitados; un cambio de precondición queda ligado a su evidencia.
6. Los resultados se mantienen iguales ante permutación del orden de bloqueos y no omiten ningún motivo aplicable.
7. Una denegación por CI bloqueada no se presenta como fallo de prueba; una ejecución no iniciada permanece `NOT_RUN`.
8. Ningún diagnóstico, recibo o resultado de aprendizaje puede mutar la raíz, la política, el catálogo, el resolver ni el estado de release.

Estos son criterios de diseño futuros, no pruebas ejecutadas ni una autorización para habilitar lecturas.

## 14. Ocho gates y evidencia de aceptación

Los ocho prerrequisitos siguen abiertos para aceptación de implementación. La existencia de tipos o primitivas en fuente solo permite afirmar lo limitado que se ha verificado estáticamente.

| Gate | Evidencia requerida para una fase futura | Estado actual |
|---|---|---|
| G1 — raíz, Owner y principal autenticado | Raíz, mandato, cadena, custodia, revocación y vínculos exactos verificados por canal independiente. | NOT_ESTABLISHED |
| G2 — catálogo y productores | Catálogo completo versionado, publicador autorizado, clases/allowlists y revocación autenticada. | NOT_ESTABLISHED |
| G3 — resolver destino | Registro server-side versionado, autoridad/custodio, mappings de operaciones reales y binding del objeto. | NOT_ESTABLISHED |
| G4 — wiring de evaluación | Evidencia de cada call site protegido y de que el control obligatorio no puede omitirse. | NOT_VERIFIED |
| G5 — agregación y releases | Evaluación completa de bloqueos, causas de denegación y release separado por bloqueo cuando esté autorizado. | NOT_ESTABLISHED |
| G6 — Entry 274, contención y ledger | Aprobación fresca, decision ledger, reader inmediato, budgets, revocación, contención y recibos correlacionados. | NOT_VERIFIED |
| G7 — pruebas autorizadas | Autorización explícita por separado, commit exacto, entorno, comandos, artefactos y resultados vinculados a cada caso. | NOT_RUN |
| G8 — aceptación independiente | Revisión independiente vinculada a SHA exacto, límites de evidencia y recibos verificables. | NOT_ACCEPTED |

Para aceptar una implementación futura se necesita un paquete correlacionado de charter y registro de raíz; prueba de verificación fuera de banda; delegaciones GBA; identidad/release de issuer y reader; especificación y evidencia IPC; catálogo y revocación; mapping G3 y call sites; ledger y anti-rollback; evidencia de releases de bloqueos; y resultados de pruebas autorizadas vinculados al SHA exacto.

Mocks, hashes, fixtures sintéticos, documentación o análisis estático no cierran las garantías de identidad, custodia, IPC, Windows ni anti-rollback. Pruebas, build, runtime, transporte y lecturas protegidas requieren autorización separada.

## 15. Decisiones aún reservadas al Owner/gobernanza

El Owner/gobernanza debe decidir y evidenciar, sin que este documento las tome en su nombre:
1. Si presenta evidencia que haga admisible A/B, encarga una ceremonia C delegada por una raíz preexistente, o ratifica formalmente D.
2. Custodio/suplente, quórum, recuperación, sucesión, rotación y revocación de la raíz.
3. Credencial del rol de gobernanza y vínculo con principal Windows, issuer y reader exactos.
4. Responsables de publicador G2, registro G3, issuer, reader y ledger; separación de funciones y conflictos permitidos.
5. Amenazas dentro/fuera de alcance, incluido administrador local, SYSTEM, kernel y recuperación de equipo.
6. Ratificación o revisión de los parámetros de frescura de Entry 274 y fijación posterior de períodos de rotación/revocación.
7. Condiciones y autoridad independiente para cualquier futura release de bloqueo.
8. Actores y alcance de las fases futuras de implementación, pruebas y aceptación independiente.

No se debe inventar un actor, custodia, servicio, secreto, raíz, catálogo, registro, release ni canal para cerrar una decisión pendiente.

## 16. Siete precisiones incorporadas en esta revisión

1. **Grafo de autoridad:** el diagrama distingue delegación, comunicación y persistencia.
2. **Custodia de decisión:** la decisión es server-side y no transferible; IPC no convierte una respuesta en permiso.
3. **Ledger:** replay, decisión/presupuestos y auditoría operacional tienen responsabilidades y límites de escritura distintos.
4. **Binding G3/handle:** el target viene de registro autorizado y se consume el mismo objeto abierto, sin segunda resolución por ruta.
5. **Bloqueos:** una decisión de lectura no libera bloqueos; si no hay release independiente válida, denegar terminalmente.
6. **Frescura:** se preservan los límites propuestos por Entry 274 como referencia de diseño, expresamente pendientes de ratificación previa a implementación.
7. **Baja fricción sin bypass:** las denegaciones se atribuyen a su dependencia y scope; diagnóstico no-contento, precondiciones explícitas y reglas anti-loop permiten avanzar por rutas no relacionadas sin rebajar ningún gate de seguridad.

## 17. Disposición y estado terminal

Este documento solicita revisión del Owner; no adopción automática. La opción D sigue siendo la disposición operativa segura mientras no exista evidencia externa verificable de autoridad.

~~~text
TASK=M1A_GBA_GOVERNED_AUTHORITY_DESIGN_OWNER_REVIEW
DESIGN_REVIEW=CONDITIONALLY_SOUND; OWNER_REVIEW_REQUIRED
CANONICAL_ADOPTION=NOT_DONE
GOVERNANCE_BOOTSTRAP=UNANCHORED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
ISSUER_IPC=NOT_ESTABLISHED
PROTECTED_REPLAY=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=OPTION_D_REQUIRED_WITH_CURRENT_EVIDENCE
PROTECTED_READS=FAIL_CLOSED
BLOCK_RELEASE=UNSUPPORTED_UNLESS_INDEPENDENTLY_AUTHORIZED
BRIDGE=BRIDGE_NOT_READY
IMPLEMENTATION=NOT_AUTHORIZED
TRUST_ROOT_CREATION=NOT_AUTHORIZED
CREDENTIAL_OR_ISSUER_PROVISIONING=NOT_AUTHORIZED
TESTS=NOT_RUN
WORKFLOWS=NOT_RUN
SOURCE_RUNTIME_CHANGES=0
MERGE_OR_REBASE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
~~~

## 16. Continuidad de aprobación del Owner desde móvil — addendum de factibilidad (2026-10-26)

**Alcance:** revisión estática de fuente, historial y documentación pública. Este addendum no es una adopción canónica, no selecciona una raíz de confianza y no autoriza implementación, registro de aplicaciones, creación de credenciales, ejecución ni lecturas protegidas.

### 16.1 Reconciliación del resultado terminal de Codex

La respuesta `TASK_RESULT=NOT_RUN; REASON=CANONICAL_ROUTE_CONTRADICTION` es correcta para el encargo que intentó retomar la evaluación de activos ya consumida. La evaluación `M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT` es terminal para su alcance. La revisión de fuente no encontró un localizador concreto para inspección de metadatos de Windows; por tanto `LOCAL_WINDOWS_ASSET_METADATA=NOT_RUN` y `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`. Esto no prueba presencia ni ausencia global de activos. No se debe repetir el inventario ni tratar el `NOT_RUN` como una nueva observación del equipo.

La instrucción del Owner de continuar se interpreta aquí como permiso para avanzar en análisis documental acotado de la experiencia de aprobación, no como autorización para provisionar una raíz, cambiar código, ejecutar pruebas, abrir un túnel, habilitar lecturas protegidas, fusionar o rebasar ramas.

### 16.2 Órganos existentes observados en `main`

Baseline de lectura: `main=f5e5643df9dbf2a9c10e4d950275b8b28459d1ed`.

- `src/iabv_v15/services/security/human_approval_broker.py`, blob `4a447149cf1b2771f6959658338a72b381f00b19`: existe `HumanApprovalBroker`, con solicitud pendiente y métodos de resolución `approve(request_id)` / `reject(request_id)`. La resolución observada es de memoria; su contrato genérico no autentica por sí solo al aprobador ni establece una decisión de lectura autoritativa y durable.
- `src/iabv_v15/bootstrap.py`, blob `e4befa6b683fc87aed7481f377f1332f5753e2c3`: crea el broker y lo pasa al ViewModel/panel de actividad. En `_wire_task_a_signals()` conecta los manejadores de credenciales, aclaraciones, dependencias, actividad y salud; en el tramo inspeccionado no conecta `human_approval_broker.register_prompt_handler`.
- `src/iabv_v15/services/security/proactive_dashboard_service.py`, blob `08535790507b88f9a36e62cbc02e5fa8f84bf379`: convierte solicitudes pendientes en elementos de panel y les asigna `actionable=True`.
- `src/iabv_v15/ui/qml/pages/EvolutionCenterPage.qml`, blob `c96a89bebd405af6a1bd8828d9153d5fd0be882b`: el delegado de esos elementos presenta título y detalle; en el bloque revisado no se observan controles de aprobar/rechazar conectados al broker.
- `src/iabv_v15/services/security/approval_memory.py`, blob `ed85408d96fb0cdfddb05489d6c38cf714275f91`: la memoria de aprobación puede auto-resolver solicitudes que coincidan con políticas. Una autorización protegida que requiere presencia humana fresca no puede aceptar una autoaprobación como si fuese un acto interactivo actual.

**Dictamen de fuente:** hay órganos reutilizables para representar una solicitud y mostrarla en el panel, pero no quedó demostrada la cadena completa `solicitud → UI accionable → Owner autenticado → decisión ligada al alcance exacto → consumo único y durable → verificación inmediata del reader`. No se debe crear otro broker, almacén de memoria u “órgano” antes de verificar qué se puede componer de lo existente.

### 16.3 Móvil y candidatos de identidad: límites verificables

1. La documentación de OpenAI indica que la pestaña **Remoto** de la app móvil ChatGPT puede acceder a chats compatibles de Codex de escritorio. Eso ayuda a interactuar desde el teléfono con una sesión Codex existente, si está conectada y es compatible; no equivale a Codex Cloud ni crea autenticación de Owner dentro del runtime de IABV. Referencia: https://help.openai.com/es-419/articles/20001275-chatgpt-trabajo-y-codex
2. El historial de IABV ya registra el directorio Microsoft Entra, usuario Owner y acceso con Authenticator como información reportada por el Owner. La evaluación estática anterior calificó Entra como candidato plausible para autenticar al humano sin un servicio de pago, pero `ENTRA_TRUSTED_BY_IABV=NOT_ESTABLISHED`: no acreditó app registration, validación de tokens ni integración de runtime. No repetir la configuración de Entra/Authenticator ya intentada.
3. GitHub Apps pueden emitir tokens de usuario para acciones en nombre de una persona; la documentación recomienda GitHub Apps frente a OAuth Apps cuando se requieren permisos más granulares y tokens de corta duración. Es un candidato de diseño, no una integración IABV existente. Referencias: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app y https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app
4. La identidad de GitHub observada por una conexión de herramienta prueba control de ese plano de GitHub, no el vínculo `Owner → principal Windows → issuer → instancia exacta de reader` dentro de IABV. Una conversación, aprobación de Codex, comentario/merge de GitHub o token de usuario tampoco constituye por sí solo el recibo operativo que consume el reader.

### 16.4 Siguiente trabajo de diseño recomendado — reutilizar, no improvisar

Antes de cualquier cambio de código, preparar un contrato mínimo de aprobación que reutilice `HumanApprovalBroker` y el panel existentes:

- Presentar al Owner, antes de confirmar, el repositorio y revisión exactos, la instancia/checkout objetivo, operación, destinos y alcance completos, límites de datos/llamadas, destinatario del contenido, vencimiento y efecto previsto.
- Vincular la confirmación a un challenge de un solo uso y a una representación/digest inequívoco de ese alcance; denegar si caduca, se repite, cambia el destino, falta identidad o no puede comprobarse la revocación.
- Definir un retorno accesible desde el teléfono sin asumir conectividad entrante al servicio local. R-07 sigue siendo `loopback-only`; no crear túnel público ni debilitar Host/Origin/DNS-rebinding para facilitar la UI.
- Evaluar primero la integración de la identidad existente ya reportada; comparar GitHub App solo donde resuelva una dependencia concreta. La identidad externa debe verificarse con issuer/tenant/audience/subject, expiración, revocación y vínculo explícito al rol Owner. No escoger un proveedor ni dar por establecida una raíz por la mera existencia de una cuenta.
- Mantener fuera de la autoaprobación de `ApprovalMemory` las decisiones que requieren presencia humana fresca. La respuesta de UI debe ser una entrada al protocolo, no un permiso transferible ni una sustitución de la autorización del servidor.
- Separar el primer arreglo de la experiencia de solicitud del cierre de G1/G2/G3. Que el Owner pueda responder a un prompt es una capacidad de interfaz; no acredita el origen de la autoridad, al issuer, el catálogo, el resolver, el estado anti-replay ni el objeto exacto que consume el reader.

### 16.5 Estado de cierre de este addendum

```text
TASK=OWNER_MOBILE_APPROVAL_PATH_STATIC_FEASIBILITY
RESULT=SOURCE_GROUNDED_DESIGN_FINDINGS_RECORDED
MAIN_BASE=f5e5643df9dbf2a9c10e4d950275b8b28459d1ed
CURRENT_STATE_REMAINS_CANONICAL=TRUE
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
LOCAL_WINDOWS_ASSET_METADATA=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PUBLIC_TUNNEL=NOT_AUTHORIZED
PR531=OPEN_DRAFT_UNMERGED
PR546=OPEN_DRAFT_UNMERGED
PR547=OPEN_DRAFT_UNMERGED
MERGE_OR_REBASE=NOT_AUTHORIZED
NEXT_ACTION=BOUNDED_OWNER_APPROVAL_DESIGN_REVIEW; NO_PRODUCT_IMPLEMENTATION
```

Este addendum amplía el borrador de diseño de la PR #546 y queda como candidato de revisión. No modifica `main` ni sustituye `CURRENT-STATE.md`.


## 17. Reconciliación del informe de revisión estática del flujo de aprobación móvil (2026-10-26)

- Tarea de origen: `M1A_G1_MOBILE_OWNER_APPROVAL_DESIGN_INDEPENDENT_REVIEW`.
- Procedencia: informe de revisión suministrado por el Owner en la conversación; el propio informe declara que no puede certificar independencia formal porque no hay separación verificable entre implementador y revisor.
- Clasificación: `BOUNDED_STATIC_REVIEW_REPORT`; `FORMAL_INDEPENDENCE=NOT_ESTABLISHED`. No se atribuye certificación externa ni se presenta el informe de usuario como una ejecución que hayamos observado de forma independiente.
- Identidad candidata revisada: PR #546 HEAD previo `9f0cc1a405147748f371bc8eead12b3e0cca3200`, documento blob `41762a2524824f7d611f208d028242bb91242b09`. El borrador sigue siendo candidato no canónico.
- Baseline de código referida por el informe: `main=f5e5643df9dbf2a9c10e4d950275b8b28459d1ed`. Los blobs citados para broker, bootstrap, dashboard, QML y ApprovalMemory fueron contrastados mediante lectura de fuente en main durante la reconciliación: `4a447149cf1b2771f6959658338a72b381f00b19`, `e4befa6b683fc87aed7481f377f1332f5753e2c3`, `08535790507b88f9a36e62cbc02e5fa8f84bf379`, `c96a89bebd405af6a1bd8828d9153d5fd0be882b` y `ed85408d96fb0cdfddb05489d6c38cf714275f91`, respectivamente.

### Hallazgos reconciliados

1. **Solicitud/UI:** el broker mantiene solicitudes pendientes y el dashboard las serializa como entradas `actionable=True`. En el delegado QML inspeccionado se presentan título y detalle, pero no hay controles conectados de aprobar/rechazar ni se demuestra que se renderice el alcance completo que exige Entry 274.
2. **Cableado:** el `_wire_task_a_signals()` de `bootstrap.py` conecta credenciales, aclaraciones, dependencias y actividad, pero no registra `human_approval_broker.register_prompt_handler(...)`. Por tanto, el recorrido integrado desde la solicitud del broker hasta esa UI no está demostrado.
3. **Identidad:** `approve(request_id, payload)` / `reject(request_id)` resuelven una solicitud pendiente en memoria sin comprobar una identidad autenticada del aprobador. El ID correlaciona una entrada local; no prueba el rol Owner.
4. **Persistencia y replay:** `ApprovalMemory` persiste políticas reutilizables y admite auto-resolución. Esto no equivale a presencia humana fresca, recibo ligado criptográficamente a la operación, consumo durable de un solo uso ni protección contra replay/rollback.
5. **Reader:** la ruta de producción protegida y la comprobación inmediata del mismo objeto permanecen sin aceptación demostrada. La fuente candidata de PR #531 no puede tratarse como código ya desplegado en main.
6. **Móvil/transporte:** con R-07 `loopback-only`, el teléfono no se conecta directamente al listener loopback del equipo. No se encontró evidencia de un callback compatible que transporte una respuesta de Codex Remote hasta el broker de IABV. Codex Remote es un posible canal de interacción con la sesión Codex, no un permiso runtime de IABV. No abrir túneles públicos ni debilitar Host/Origin o DNS-rebinding.
7. **Identidad candidata:** los registros existentes consideran Entra una posible fuente para autenticar al humano, pero `ENTRA_TRUSTED_BY_IABV=NOT_ESTABLISHED`; GitHub App también es una alternativa no integrada. No repetir el setup de Entra/Authenticator sin evidencia material nueva.

### Decisión histórica que debe reutilizarse

El registro [RQ224 Owner-Identity Trust Options](./CHAT-ARCH-2026-10-10-228-rq224-owner-identity-trust-options-design.md) contiene una decisión del Owner del 2026-10-11: opción A como dirección de diseño —principal de Windows enrolado más confirmación explícita ligada a la intención—. Su alcance declarado fue exclusivamente de diseño y **no** demuestra que exista enrolamiento, una raíz independiente o autoridad runtime. El handoff del 2026-10-24 reabrió el diseño de bootstrap gobernado, también sin aportar por sí mismo nueva evidencia de raíz.

Regla de continuidad: no volver a preguntar al Owner desde cero si ya eligió una dirección conceptual. Reutilizar opción A como decisión de diseño histórica; investigar primero cómo se puede acreditar y hacer cumplir, y solicitar una decisión nueva solo si la implementación o el modelo de confianza exige una elección distinta y concreta.

### Orden mínimo derivado

1. Mantener separados el diseño de experiencia de aprobación, la autenticación del Owner y la autoridad G1/G2/G3.
2. Conservar el contrato de presentación: instancia/checkout, revisión exacta, operación, destino, datos que se expondrán, destinatario, límites y vencimiento claramente visibles antes de confirmar.
3. Resolver como pregunta arquitectónica previa el canal móvil→sesión local. No asumir que Remote hace de API del broker ni introducir un relay sin diseño y autorización separados.
4. Comparar las opciones de identidad solo contra la dirección histórica del Owner, la restricción de coste cero y el modelo de amenazas; validar issuer/audience/subject en servidor y la vinculación explícita al rol Owner.
5. Solo después diseñar challenge de un solo uso, digest de alcance inequívoco, consumo durable/revocación/anti-rollback y verificación inmediata del reader sobre el objeto que realmente consume.
6. Cualquier implementación, provisión de identidad/credenciales, tests, runtime, transporte, lecturas protegidas, merge o rebase requiere autorización específica posterior y evidencia propia.

### Estado

```text
MOBILE_APPROVAL_SOURCE_REVIEW=BOUNDED_REPORT_RECONCILED
FORMAL_INDEPENDENCE=NOT_ESTABLISHED
BROKER_AND_DASHBOARD=EXIST
BROKER_TO_UI_RESPONSE_PATH=NOT_ESTABLISHED
AUTHENTICATED_OWNER=NOT_ESTABLISHED
MOBILE_TO_LOCAL_RETURN_PATH=NOT_ESTABLISHED
ENTRA_TRUSTED_BY_IABV=NOT_ESTABLISHED
GITHUB_APP_INTEGRATED=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; MCP=NOT_RUN; REAL_TRANSPORT=NOT_RUN
SOURCE_CHANGES=NONE
CANONICAL_MAIN_CHANGED=FALSE
PR546=OPEN_DRAFT_UNMERGED; CANDIDATE_ONLY
NEXT_CANONICAL_ACTION=WAIT_FOR_GENUINELY_NEW_INDEPENDENT_G1_ROOT_AND_MANDATE_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

Este resultado actualiza la trazabilidad del borrador; no cambia el enrutamiento canónico de `CURRENT-STATE.md`, no crea una raíz de confianza y no autoriza automáticamente una fase técnica siguiente.


## 18. Evaluación de canales móviles y retorno local: evidencia oficial, sin integración (2026-10-26)

Esta sección continúa el alcance documental del informe de revisión móvil. No crea una aplicación, no registra un proveedor, no cambia transporte y no afirma una integración existente.

### A. Codex Remote: canal de trabajo humano, no API de autorización IABV

La documentación oficial de OpenAI describe acceso, desde la pestaña Remote de ChatGPT móvil, a chats compatibles de Codex de escritorio. La experiencia permite continuar hilos, responder preguntas y revisar/aprobar acciones de Codex; los archivos, credenciales y permisos del entorno permanecen en el host. Esto puede ser una interfaz útil para dirigir la tarea del puente desde el teléfono cuando el host y la versión instalada sean compatibles.

Fuentes oficiales:
- https://help.openai.com/es-419/articles/20001275-chatgpt-work-and-codex
- https://openai.com/es-419/index/work-with-codex-from-anywhere/

**Límite:** estas fuentes describen interacción remota con Codex, no una integración que entregue un evento firmado, fresco y ligado a la operación desde Remote hasta `HumanApprovalBroker` de IABV. La compatibilidad exacta del host Windows debe verificarse en la instalación real; no se presume por documentación general. `CODEX_REMOTE_TO_IABV_BROKER_BINDING=NOT_ESTABLISHED`.

### B. Entra device authorization flow: candidato para autenticar al humano sin callback entrante

Microsoft documenta un flujo donde el cliente local solicita un `device_code` y un `user_code`, presenta una URL de verificación al usuario y consulta el endpoint de token hasta que el usuario completa o deniega la autenticación. El usuario puede usar otro dispositivo, como el teléfono; no se requiere que el teléfono abra una conexión entrante al listener loopback del equipo local.

Fuente oficial:
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code

**Qué podría resolver:** una posible parte de autenticación de usuario en un flujo iniciado desde el equipo, compatible en principio con un diseño sin listener público, manteniendo el transporte local-only.

**Qué no resuelve:** el flujo devuelve tokens de autenticación/autorización para scopes de la aplicación; no muestra automáticamente el alcance concreto de una lectura IABV ni constituye, por sí solo, un consentimiento fresco para esa operación. La aplicación debe validar el token conforme al protocolo y su configuración, identificar inequívocamente al principal, vincularlo al rol Owner autorizado y exigir una confirmación independiente que cubra la instancia, revisión, operación, destino, datos expuestos, destinatario, límites y vencimiento.

La existencia de un directorio Entra y un inicio con Authenticator es Owner-reported en el historial; una app registration, su client ID, flujo registrado y validación en IABV no están demostrados. Este análisis no repite la configuración previa ni crea nada. `ENTRA_DEVICE_FLOW=DOCUMENTED_CANDIDATE; NOT_CONFIGURED_OR_TESTED`.

Referencias OIDC para el descubrimiento y la validación del lado servidor:
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc
- https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens

### C. GitHub App: identidad atribuible, pero todavía no provisionada

GitHub documenta que una GitHub App puede actuar como la propia app, como instalación o en nombre de un usuario mediante un user access token. Ese tercer modo puede atribuir acciones al usuario autenticado, dentro de los permisos efectivos de la app y del usuario.

Fuentes oficiales:
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app

**Límite:** un user access token autentica/atribuye una acción a un usuario de GitHub; no prueba automáticamente que ese usuario sea el Owner de runtime de IABV, que controle la instancia Windows exacta o que haya aprobado un target/scope de lectura concreto. No hay una GitHub App de aprobación IABV identificada como ya provisionada. No crear una durante este estudio.

### Comparación y decisión de diseño provisional

| Candidato | Puede contribuir | No demuestra |
|---|---|---|
| Codex Remote | Continuidad humana y aprobación de acciones dentro de Codex en un host compatible | Evento de aprobación consumible por IABV; autoridad G1; autorización de lectura |
| Entra device flow | Autenticación de usuario iniciada desde el equipo, con interacción en el teléfono y polling saliente | Consentimiento IABV ligado a un scope concreto; autoridad Owner ya enrolada; raíz G1 |
| GitHub App user token | Identidad GitHub y acciones atribuibles al usuario bajo permisos delimitados | Vínculo Owner→principal Windows→issuer→reader; consentimiento de una lectura específica |

**Recomendación de diseño, no adopción:** conservar como dirección el modelo A ya seleccionado por el Owner (principal Windows enrolado + confirmación explícita ligada a la intención). Para la parte de autenticación remota, evaluar Entra device flow antes de crear una nueva app o ruta, porque se apoya en una identidad que el historial ya registra como configurada por el Owner y no requiere callback entrante. Esta prioridad es una hipótesis de diseño basada en reutilización, no prueba de viabilidad completa ni autorización para registrar una aplicación. GitHub App permanece como alternativa comparativa si Entra no satisface los requisitos.

Incluso si el identity flow resulta viable, queda por diseñar un canal donde el teléfono vea y confirme el alcance exacto de la operación; luego el servidor debe validar challenge, expiración, consumo único, revocación y el binding del reader al mismo objeto consumido. No se debe inventar ese canal a partir del mero flujo de login.

### Estado

```text
CODEX_REMOTE_TO_IABV_BROKER_BINDING=NOT_ESTABLISHED
WINDOWS_REMOTE_HOST_COMPATIBILITY=NOT_VERIFIED_IN_OWNER_INSTALLATION
ENTRA_DEVICE_FLOW=DOCUMENTED_CANDIDATE; NOT_CONFIGURED_OR_TESTED
PHONE_SCOPE_CONFIRMATION_UI=NOT_ESTABLISHED
GITHUB_APP_APPROVAL=ALTERNATIVE; NOT_PROVISIONED
INBOUND_PUBLIC_LISTENER=NOT_REQUIRED_BY_DEVICE-CODE_AUTH_FLOW
R07=LOOPBACK_ONLY; NO_TUNNEL
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

No se eligió una nueva autoridad, no se creó app registration, no se solicitaron tokens, no se inspeccionaron credenciales, no hubo pruebas o runtime y no se cambió `main`. El análisis acota una posibilidad técnica, pero la aprobación móvil completa sigue sin estar implementada.
