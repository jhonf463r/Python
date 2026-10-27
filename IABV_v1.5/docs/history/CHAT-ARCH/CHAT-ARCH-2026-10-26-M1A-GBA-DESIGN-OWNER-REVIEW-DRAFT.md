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


## 19. Reutilización posible del adaptador GitHub existente: capacidades y límites (2026-10-26)

Esta comprobación estática adicional usa únicamente blobs de `main`. No inspeccionó ni leyó tokens, no llamó al adaptador en runtime y no confirma que su token esté configurado.

### Capacidades ya presentes

- `GitHubRemoteService`, blob `f410a70f63cd9f125bc78d618c6ccf85d9341c17`, puede solicitar aprobación al `HumanApprovalBroker` antes de una publicación de PR cuando la política no permite autoaprobar. El alcance observado se forma alrededor de `open_pr`, rama y base; el resultado registra `approved`, `rejected`, `timed_out` y `auto_resolved`, y luego continúa a push/creación de PR si aprueba.
- `GitHubApiToolAdapter`, blob `f8ce508342d2da96f30b2152ffa242f08b187987`, declara estas acciones: `read_pr`, `create_pr`, `merge_pr`, `enable_auto_merge`, `comment_issue`, `list_issues` y `list_prs`. Requiere un token y un repositorio configurados para estar disponible.
- El flujo de publicación demuestra que el repositorio ya tiene una integración GitHub reutilizable para determinadas operaciones. No demuestra una bandeja de aprobación remota, consulta de comentarios, ni un canal autenticado que llegue al reader.

Fuente: [GitHubRemoteService](https://github.com/jhonf463r/Python/blob/f5e5643df9dbf2a9c10e4d950275b8b28459d1ed/IABV_v1.5/src/iabv_v15/services/tools/github_remote_service.py) · [Tool adapters / GitHubApiToolAdapter](https://github.com/jhonf463r/Python/blob/f5e5643df9dbf2a9c10e4d950275b8b28459d1ed/IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py).

### Qué no puede reutilizarse directamente

1. La aprobación de publicar una PR es una acción distinta de autorizar una lectura protegida; no debe ampliarse su semántica.
2. El broker sigue sin un manejador de prompt registrado en el cableado de UI observado, y el resultado de aprobación no acredita la identidad autenticada del Owner.
3. El adaptador actual no declara una acción para leer comentarios/feedback de una solicitud de aprobación ni un mecanismo de polling de desafíos; `comment_issue` y `list_issues` no forman una ida y vuelta de autorización.
4. La presencia de un token en configuración no fue verificada y no se inspeccionaron secretos. La identidad GitHub `jhonf463r` y los permisos del repositorio en el plano GitHub no se consideran adoptados automáticamente como la autoridad Owner de runtime de IABV.

### Hipótesis de relay pull-based — no aprobada ni implementada

Como alternativa futura, un consumidor local podría publicar una petición mínima en un recurso privado ya gobernado y consultar desde el equipo (solo salida) una respuesta que incluya un challenge y digest del alcance. Eso evitaría requerir una conexión entrante al listener local, pero sería un protocolo nuevo: harían falta una ruta de lectura de respuestas, límites de acceso verificados, una identidad Owner adoptada, presentación humana del alcance exacto, vínculo challenge/digest, expiración, consumo duradero, anti-replay/rollback, revocación y confirmación del reader. Cualquier detalle de una lectura protegida enviado a GitHub también tendría que estar expresamente dentro del alcance de datos aprobado.

Esta hipótesis no es actualmente una solución existente, no supera por sí sola G1 y probablemente añadiría más complejidad que probar el candidato Entra ya evaluado. Se conserva como comparación, no como siguiente tarea autorizada.

### Estado

```text
GITHUB_API_ADAPTER=EXISTS; TOKEN_AVAILABILITY=UNKNOWN
GITHUB_APPROVAL_POLLING=NOT_IMPLEMENTED_IN_DECLARED_ACTIONS
GITHUB_REMOTE_SERVICE=EXISTING_PR_PUBLICATION_APPROVAL_ONLY
REMOTE_COMMENT_IDENTITY_TO_OWNER=NOT_ESTABLISHED
PULL_BASED_RELAY=DESIGN_HYPOTHESIS_ONLY
PUBLIC_INBOUND_LISTENER=NOT_REQUIRED_FOR_POLLING_HYPOTHESIS; NO_RELAY_CONFIGURED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
```


## 20. Candidato de canal móvil↔equipo sin listener entrante: GitHub App + aprobación por comentario privado (diseño para decisión; no provisionado)

### Evidencia nueva verificada en el plano GitHub

En esta reconciliación, la conexión GitHub disponible devuelve la identidad `jhonf463r` (user ID `28608338`). La metadata viva del repositorio devuelve `jhonf463r/Python` (repository ID `860009771`), propietario con el mismo user ID; el nivel de permiso de esa cuenta en el repositorio es `admin`. El repositorio es privado. Esto es evidencia del plano de control de GitHub y de los permisos de la conexión usada en esta sesión; **no** demuestra que IABV tenga el mismo token, conozca esta identidad en runtime o ya la acepte como autoridad.

### Propuesta

La alternativa más prometedora para la experiencia solicitada (Owner usa el teléfono, PC no expone un listener público) es una **bandeja de aprobación pull-based en un issue privado del repositorio**, creada y consultada por una GitHub App limitada a ese único repositorio.

1. Un emisor local de confianza genera una solicitud con un ID aleatorio, desafío de un solo uso, expiración y digest canónico del alcance. El cuerpo del issue enseña antes de decidir: instalación/checkout y revisión exactos, operación, destino, propósito, datos que se transmitirían, destinatario, límites y vencimiento. No incluye contenido protegido del archivo ni secretos.
2. La GitHub App instala permisos mínimos para el único repositorio; como candidato, `Metadata: read` más `Issues: write` (que permite leer los comentarios necesarios). Se verifica que Issues esté habilitado antes de cualquier prueba. La solicitud se crea como actividad de la App, no usando un token personal que pueda publicar una aprobación fingiendo ser el Owner.
3. El Owner abre ese issue desde GitHub en el teléfono y responde explícitamente `APPROVE <request-id> <challenge>` o `REJECT ...` después de revisar el alcance. La respuesta se recibe mediante el endpoint de comentarios del issue; el equipo inicia todas las conexiones hacia la API de GitHub. No requiere conexión entrante al equipo ni túnel público.
4. Antes de aceptar, el consumidor local verifica: repository ID y issue inmutables; autor del comentario igual al user ID Owner enrolado (no solo el texto/login); asociación con la misma solicitud; digest y versión del cuerpo sin cambios; desafío, expiración y no-replay; permiso y estado de revocación; y que la confirmación no supere el alcance mostrado. Consume el desafío de forma durable y atómica.
5. El reader sigue haciendo la comprobación final inmediatamente antes de operar y consume el mismo objeto cuya identidad fue autorizada. La respuesta de GitHub es evidencia de una decisión humana autenticada en el plano GitHub; no sustituye las garantías del issuer, del host ni del reader.

Documentación oficial que acredita la capacidad básica del proveedor, no esta integración hipotética:
- GitHub permite habilitar Device Flow para ciertas GitHub Apps y generar tokens de usuario desde un dispositivo secundario: https://docs.github.com/en/apps/maintaining-github-apps/modifying-a-github-app-registration y https://docs.github.com/es/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app.
- La API de GitHub puede listar comentarios de issues y la respuesta incluye el autor/ID; los tokens de GitHub App pueden leerlos con permisos de Issues o Pull requests: https://docs.github.com/en/rest/issues/comments.
- Una GitHub App puede actuar como App/instalación o en nombre de un usuario; los tokens de usuario están limitados por los permisos efectivos de la App y del usuario: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app y https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app.

### Por qué se prefiere investigar este canal antes de Entra o Codex Remote

- No requiere que el teléfono llegue por red al listener loopback del PC.
- Usa un proveedor externo con identidad de comentario verificable y una pantalla de consentimiento que puede mostrar el alcance exacto; un flujo de login por sí solo no puede aprobar ese alcance.
- Evita depender de que Codex Remote exponga una API de callback hacia el broker de IABV, integración que sigue sin demostrarse.
- Permite acotar los datos enviados al proveedor externo al manifiesto de solicitud y la respuesta. El contenido protegido no se publica en el issue. Si ni siquiera los metadatos de alcance pueden enviarse a GitHub según una política futura, este canal no será admisible.
- Requiere una nueva GitHub App, su instalación y una clave privada de App custodiada en el host. Esa clave no debe confundirse con la credencial Owner ni puede autorizar por sí misma una operación. La provisión y protección de esa clave, la política de coste cero y el tratamiento de revocación son trabajos posteriores.

### Límite crítico de confianza

Esta arquitectura **no cierra G1 por el mero hecho de autenticarse en GitHub**. El Owner debe adoptar explícitamente la identidad de GitHub y su relación con el repositorio como fuente de mandato para el puente, y aceptar una ceremonia de enrolamiento que enlace esa autoridad externa con el principal local y la instancia exacta de IABV. El ID de usuario, el permiso `admin`, el comentario, un merge o un token aislados no crean automáticamente esa delegación. La conexión GitHub de esta sesión no se transfiere a IABV.

Si el Owner no adopta esa fuente externa, se mantiene Option D/no-bootstrap. Si la adopta, aún quedan por diseñar y aprobar el enrolamiento del host/issuer, almacenamiento de clave, ledger anti-rollback y productor G3 antes de que un reader pueda permitir una lectura protegida.

### Precondiciones que deben verificarse en una fase posterior, no ahora

- GitHub Issues habilitado en el repositorio privado.
- Registro e instalación de una GitHub App con permisos mínimos restringidos a repository ID `860009771`.
- Identidad de comentario con user ID `28608338` verificada por respuesta API autenticada; denegar cualquier otro actor aunque tenga permiso de comentario.
- Protección del cuerpo del issue: comparar contra el digest local esperado y denegar si es editado, sustituido o reabierto con otro alcance.
- Persistencia durable del consumo, revocación y recuperación anti-rollback.
- Comprobación de reader a la revisión/objeto exactos, fuera de los metadatos controlados por el caller.
- Verificación de que no se inicia ningún listener público ni túnel; R-07 permanece `loopback-only`.
- Revisión independiente posterior del diseño y un permiso de implementación separado.

### Dictamen provisional

```text
GITHUB_ACCOUNT_AND_REPO_OWNERSHIP=VERIFIED_IN_CONNECTED_CONTROL_PLANE
OWNER_ID=28608338; REPOSITORY_ID=860009771
PRIVATE_REPO=TRUE; OWNER_PERMISSION=ADMIN
GITHUB_APP_PRIVATE_APPROVAL_INBOX=FEASIBLE_DESIGN_CANDIDATE; NOT_CREATED
ISSUE_COMMENT_AUTHOR_ID=AVAILABLE_FROM_GITHUB_API; NOT_INTEGRATED_IN_IABV
PHONE_TO_LOCAL_PULL_CHANNEL=ARCHITECTURALLY_PLAUSIBLE; NOT_IMPLEMENTED
GITHUB_ISSUES_ENABLED=UNKNOWN
GITHUB_APP_KEY_CUSTODY=NOT_ESTABLISHED
OWNER_ADOPTION_OF_GITHUB_AS_IABV_AUTHORITY=NOT_PROVIDED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
PUBLIC_LISTENER_OR_TUNNEL=NOT_PROPOSED
IMPLEMENTATION_OR_APP_PROVISIONING=NOT_AUTHORIZED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
```

Esta opción convierte el siguiente bloqueo en una decisión concreta de gobernanza: si el Owner autoriza que la cuenta GitHub que ya posee el repositorio sea la identidad externa que IABV reconocerá para iniciar el enrolamiento. No se registra ninguna App ni se crea credencial hasta que esa decisión se formule expresamente. La decisión de identidad no elimina los gates restantes ni autoriza lecturas protegidas.

## 21. Decisión explícita del Owner: GitHub como identidad externa para la ruta de aprobación (2026-10-27)

### Decisión recibida

El Owner respondió: **“Sí autorizo; procede y ten en cuenta que autorizo todo lo que nos ayude avanzar más rápido”** tras la pregunta específica sobre usar la cuenta GitHub propietaria del repositorio como fuente externa de identidad para las aprobaciones de IABV mediante una GitHub App privada y limitada a ese repositorio.

Se registra como una decisión de gobernanza para adoptar **la identidad de la cuenta GitHub propietaria y el repositorio privado `jhonf463r/Python` como autoridad externa candidata** en la ceremonia de aprobación. No significa que el host Windows, el issuer, el proceso IABV ni el reader ya estén autenticados o enlazados a esa identidad.

### Nueva precondición comprobada

La consulta autenticada de la API de repositorios devolvió para `jhonf463r/Python`:
- `repository_id=860009771`
- `owner_id=28608338`
- `private=true`
- `has_issues=true`
- `permissions.admin=true` para la cuenta conectada.

Por tanto, Issues está habilitado; no es necesario volver a investigar esa precondición. No se creó ningún issue ni se publicó contenido de aprobación.

### Alcance permitido y límites de custodia

La autorización permite avanzar con el registro/configuración de una GitHub App privada de aprobación, estrictamente restringida al repositorio anterior, para usar Issues como relay pull-based. Diseño mínimo previsto:
- `Metadata: read` y `Issues: read/write`; sin permisos adicionales.
- Sin webhook, sin eventos suscritos, sin callback OAuth/device flow, sin listener ni endpoint entrante.
- La instalación, si se completa, se limitará mediante “Only select repositories” al repositorio `jhonf463r/Python`.
- No crear solicitudes/Issues de prueba ni permitir lecturas protegidas hasta completar la cadena local de confianza.
- La clave privada de la App no se publica en Issues, no se copia al chat ni se confunde con la identidad del Owner; su custodia se debe cerrar en el host Windows autorizado. No se habilitan credenciales improvisadas ni acceso a otros repositorios.

### Reconciliación del estado causal

La selección de identidad externa cierra la decisión de gobernanza que estaba pendiente en §20, pero no cierra los gates técnicos:

```text
OWNER_ADOPTION_OF_GITHUB_AS_IABV_AUTHORITY=AUTHORIZED; DATE=2026-10-27
GITHUB_OWNER_ID=28608338; REPOSITORY_ID=860009771
GITHUB_ISSUES_ENABLED=TRUE; VERIFIED_BY_REPOSITORY_API
GITHUB_APP_REGISTRATION=NOT_CREATED
GITHUB_APP_INSTALLATION=NOT_CREATED
GITHUB_APP_KEY_CUSTODY=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

### Siguiente paso discriminante

Registrar y configurar la App con los permisos mínimos exactos, instalarla únicamente en el repositorio designado, y luego definir cómo custodiar su clave en Windows sin transmitirla por el chat. Después se debe establecer y verificar el enlace entre Owner GitHub, identidad del host/issuer y la instancia exacta del reader. Solo entonces procede implementación/aceptación de un flujo mínimo de solicitud→comentario→verificación→consumo anti-replay→reader, mediante autorización acotada por revisión y evidencia de ejecución. GitHub Issues no se debe tratar como un sustituto del issuer ni como permiso autónomo para leer archivos.

Esta decisión se incorpora en la rama de diseño de la PR #546 para revisión; no modifica `main`, no fusiona ni rebasa PRs y no activa la ruta del puente.


## 22. Evidencia posterior: GitHub App registrada e instalada en el repositorio único (2026-10-27)



### Resultado observado

Tras completar la verificación adicional de GitHub, se registró y luego instaló la GitHub App dedicada al relay de aprobación. La automatización verificó la pantalla de creación y el resultado de instalación.

- Owner GitHub: `@jhonf463r`, user ID `28608338`.
- Repositorio: `jhonf463r/Python`, repository ID `860009771`, privado, Issues habilitado.
- App registrada: `iabv-approval-relay-20261027`.
- Slug: `iabv-approval-relay-20261027`.
- App ID: `5496678`.
- Página de ajustes: https://github.com/settings/apps/iabv-approval-relay-20261027
- Installation ID: `175851462`.
- Fecha de instalación confirmada: 2026-10-27.

### Alcance y permisos confirmados

La instalación quedó en modalidad **Only select repositories** y el único repositorio seleccionado es `jhonf463r/Python`.

- `Metadata: read-only`.
- `Issues: read/write`.
- Todos los demás permisos de repositorio, organización, cuenta y empresa: `No access`.
- Webhook Active: desmarcado; sin URL, eventos suscritos ni secreto.
- OAuth user authorization: desmarcado.
- Device Flow: desmarcado.
- Callback y post-install setup URL: no configurados.
- Clave privada de la App: no generada ni descargada.
- No se crearon Issues, comentarios, ramas, commits de código ni contenido de aprobación en el repositorio.

La instalación es una capacidad externa configurada; todavía no demuestra que IABV o el proceso Windows puedan autenticarse como la App ni que un mensaje de aprobación sea verificado por el reader.

### Reconciliación causal

Esta evidencia sustituye, solo como estado posterior a la fecha de registro, los valores históricos `GITHUB_APP_REGISTRATION=NOT_CREATED` y `GITHUB_APP_INSTALLATION=NOT_CREATED` que aparecen en §21. §21 conserva la cronología válida a la hora en que se escribió; este apartado registra el cambio posterior. No modificar ni inferir desde este documento un nuevo estado de `main` o de `CURRENT-STATE.md`.

```text
OWNER_ADOPTION_OF_GITHUB_AS_IABV_AUTHORITY=AUTHORIZED; DATE=2026-10-27
GITHUB_OWNER_ID=28608338; REPOSITORY_ID=860009771
GITHUB_ISSUES_ENABLED=TRUE; VERIFIED_BY_REPOSITORY_API
GITHUB_APP_REGISTRATION=CREATED; NAME=iabv-approval-relay-20261027; APP_ID=5496678
GITHUB_APP_INSTALLATION=INSTALLED; INSTALLATION_ID=175851462
GITHUB_APP_INSTALLATION_REPOSITORIES=ONLY:jhonf463r/Python; REPOSITORY_ID=860009771
GITHUB_APP_PERMISSIONS=METADATA_READ; ISSUES_READ_WRITE; ALL_OTHER_PERMISSIONS=NONE
GITHUB_APP_WEBHOOKS=DISABLED
GITHUB_APP_OAUTH=DISABLED; DEVICE_FLOW=DISABLED
GITHUB_APP_PRIVATE_KEY=NOT_GENERATED; KEY_CUSTODY=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
CANONICAL_MAIN_CURRENT_STATE=UNCHANGED_BY_THIS_DOCUMENTATION_UPDATE
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

### Siguiente acción discriminante

No crear un Issue de prueba ni simular que ya existe transporte. El siguiente paso es cerrar la custodia de clave de la App en el host Windows autorizado, sin colocar la clave en el chat, en Issues ni en el repositorio; luego definir y verificar un flujo local pull-based con identidad Owner autenticada, digest/canonical scope, expiración y consumo durable anti-replay. La App instalada no es un issuer y el permiso `Issues: write` no autoriza por sí mismo lecturas protegidas. La siguiente implementación debe quedar sujeta a revisión de la ruta exacta y a la autorización de implementación ya delimitada, y requiere evidencia independiente antes de habilitar cualquier reader protegido.

Este apartado se añade únicamente a la rama documental de la PR #546. No modifica `main`, no fusiona/rebasa ninguna PR y no altera el estado operativo canónico.


## 23. Estado reportado de clave local y protocolo de saldo/contingencia (2026-10-27)

### Estado de la clave: declaración del Owner, aún sin validación técnica

El Owner informa que generó una clave privada para la GitHub App pero que no consiguió descargarla directamente; indica que pudo copiar su contenido, pegarlo en el Bloc de notas y cambiar la extensión del archivo de `.txt` a `.pem`.

Esta es una declaración del Owner, no evidencia suficiente de que el archivo sea un PEM íntegro, válido o correspondiente a la clave pública que GitHub muestra para la App. **No se ha recibido, leído ni almacenado aquí ningún secreto, y la clave no debe copiarse al chat ni a este documento.**

Distinción importante: cambiar el nombre o la extensión a `.pem` no convierte ni repara el contenido. El archivo puede funcionar si el texto PEM completo fue copiado sin omisiones ni alteraciones y conserva sus saltos de línea; esto aún no se ha comprobado. La documentación de GitHub indica que la clave para una GitHub App se descarga en formato PEM, concretamente PKCS#1 RSA, y recomienda verificar la clave local comparando su huella con la huella que aparece en las credenciales de la App.

Procedimiento seguro pendiente, desde el Windows que ejecutará IABV:

1. Revisar el historial de descargas del navegador y la carpeta Descargas antes de asumir que la descarga falló. No enviar el archivo a ningún servicio ni repositorio.
2. Comprobar localmente que el archivo tiene el nombre real terminado en `.pem` (no `.pem.txt`) y que el contenido conserva los marcadores PEM de inicio/fin y todas sus líneas. No mostrar ni copiar el contenido secreto a la conversación.
3. Validar la sintaxis y calcular localmente la huella pública de la clave con OpenSSL; compararla exactamente con la huella de la clave que figura en la página Credentials → Key pairs de la GitHub App. La igualdad confirma correspondencia; el nombre/extensión del archivo no lo hace.
4. Mantener la clave en almacenamiento local protegido para la identidad Windows que ejecuta IABV, fuera del repositorio y de carpetas sincronizadas/compartidas. No usarla para pedir tokens hasta validar la huella y definir su custodia.
5. Si la copia es incompleta o no coincide la huella, generar una nueva clave desde la configuración de GitHub App, localizar el PEM que el navegador descargue y validar la nueva clave antes de usarla. No revocar la clave existente hasta tener confirmada la sustituta; si la clave antigua pudo quedar expuesta, tratarlo como incidente y rotar/revocar con el procedimiento de GitHub.

### Saldo de automatización y regla de contingencia

Consulta de solo lectura al saldo TinyFish en 2026-10-27: `available_balance=4.52 USD`, `auto_reload=unconfigured`, sin recarga pendiente. Es saldo de la herramienta de automatización del navegador; no es saldo ni credencial de GitHub y su agotamiento no desinstala ni invalida la GitHub App.

Regla para evitar ejecuciones truncadas y vueltas repetidas:

- Antes de una automatización larga, comprobar el saldo y estimar su coste desde las tarifas vigentes; conservar un margen y no iniciar una tarea que probablemente se quede sin saldo a mitad de una operación.
- Si la herramienta avisa que faltan créditos, detener nuevas automatizaciones y conservar el último resultado verificable. No reintentar la misma tarea sin cambio de precondiciones.
- Solo considerar un perfil/cuenta de un ayudante distinto cuando el Owner confirme que esa persona autoriza expresamente el uso y esa persona conecte de forma segura su propia sesión/cuenta. No pedir ni recibir contraseñas, códigos MFA, tokens o credenciales en el chat; no intentar trasladar la sesión de GitHub propietaria ni cambiar el dueño de la App/repositorio.
- Antes de cambiar, explicar el impacto y confirmar que se utiliza únicamente para automatización autorizada. No cambiar de cuenta en silencio ni usar otra cuenta para eludir controles de seguridad, permisos, límites de uso o facturación.
- Si el ayudante no está disponible o no hay consentimiento/perfil independiente, detener la automatización y pedir al Owner que recargue el saldo o autorice explícitamente otro método válido.

### Estado técnico resultante

```text
GITHUB_APP_REGISTRATION=CREATED; NAME=iabv-approval-relay-20261027; APP_ID=5496678
GITHUB_APP_INSTALLATION=INSTALLED; INSTALLATION_ID=175851462
GITHUB_APP_INSTALLATION_REPOSITORIES=ONLY:jhonf463r/Python
OWNER_REPORTED_PRIVATE_KEY_FILE=TEXT_COPIED_TO_NOTEPAD; EXTENSION_CHANGED_TO_PEM
PRIVATE_KEY_FILE_INTEGRITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT_MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_VERIFIED
TINYFISH_WALLET_BALANCE=4.52_USD; AUTO_RELOAD=UNCONFIGURED; AS_OF=2026-10-27T15:08:58.364Z
HELPER_ACCOUNT_FALLBACK=OWNER_CONSENT_AND_SEPARATE_AUTHENTICATED_PROFILE_REQUIRED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

No se ejecutó prueba de la clave, no se solicitó ni generó un token de instalación, no se creó contenido en Issues y no se alteró `main` ni `CURRENT-STATE.md`. Este apartado es documentación de continuidad en esta PR de borrador; no cierra gates de autoridad ni habilita lecturas protegidas.

Referencia oficial: https://docs.github.com/es/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps


## 24. Decisión Owner: Codex local como operador de custodia y preflight, nunca pegado de la clave al modelo (2026-10-27)

### Decisión y criterio de ergonomía

El Owner solicita minimizar tareas manuales y delegar en Codex las operaciones que una IA pueda ejecutar mejor y más rápido, incluyendo el uso de GitHub cuando esté disponible y autorizado. Se adopta como ruta preferida Codex ejecutado localmente en el Windows destino, con un pequeño flujo de custodia local, en vez de pedir al Owner que vuelva a copiar datos manualmente o que pegue la clave dentro de una conversación.

La idea de un “prompt seguro” debe distinguir dos mecanismos:
- **No seguro:** pegar el contenido PEM en la caja de chat/prompt de Codex, ChatGPT, una Issue, una variable incluida en un comando, o cualquier interfaz cuyo contenido pueda ser registrado en transcriptos/logs.
- **Preferido:** Codex genera y ejecuta en el Windows local un asistente/script que abre un selector de archivo local, lee la clave dentro del proceso local sin imprimir su contenido, la valida, compara su huella y solo entonces la guarda cifrada/protegida localmente. El prompt contiene instrucciones; no contiene la clave.

Este flujo requiere Codex CLI/desktop con acceso local al Windows y al árbol de trabajo local. Si la sesión de Codex es remota/cloud o no puede interactuar con el sistema de archivos local, debe detenerse y no simular que puede guardar el secreto en el host físico.

### Evidencia y estado no presumido

El Owner informa que ya generó una clave para la App, que no consiguió descargarla directamente, que copió su contenido en Bloc de notas y cambió la extensión a .pem. Esto **no demuestra** que el texto esté completo, que el archivo sea PEM válido ni que corresponda a la clave pública que registra GitHub.

- No se recibió ni almacenó el contenido privado en chat o en GitHub.
- App: iabv-approval-relay-20261027, App ID 5496678.
- Instalación: ID 175851462, limitada a jhonf463r/Python (repository ID 860009771).
- GitHub owner user ID 28608338.
- Permisos instalados: Metadata read; Issues read/write; todos los demás sin acceso.
- Aún no se ha validado el PEM local, su huella, la identidad de Windows bajo la que corre IABV ni la autenticación JWT/install-token.

### Prompt listo para usar en Codex local

El texto siguiente es una orden de trabajo; **no anexar ni pegar la clave al prompt**.

---

Trabaja en el Windows físico donde se ejecuta IABV, usando Codex local (CLI/Desktop con acceso real al disco local), no un entorno cloud/remoto. Objetivo: custodiar y validar localmente la clave de la GitHub App aprobada, y hacer un preflight API estrictamente de solo lectura si la clave es válida. El secreto nunca debe entrar en el transcript/model context.

Contexto verificado:
- Repo privado: jhonf463r/Python; repository_id=860009771.
- Owner: @jhonf463r; owner user id=28608338.
- GitHub App: iabv-approval-relay-20261027; app_id=5496678.
- Installation id=175851462; instalada únicamente en jhonf463r/Python.
- Permisos instalados: Metadata read; Issues read/write; todos los demás No access.
- Webhooks, OAuth y Device Flow desactivados.
- main/CURRENT-STATE.md es la autoridad operativa. La PR #546 está abierta, draft y sin fusionar. Sus apartados 22–24 son documentación candidata, no autoridad canónica.

Reglas de seguridad obligatorias:
1. No pidas pegar la clave en el chat, el prompt, una Issue ni un comando. No muestres, imprimas, registres, adjuntes ni copies el contenido PEM al transcript, logs, reporte, variables de entorno o argumentos de línea de comandos.
2. Primero confirma que la ejecución es local en Windows y que tienes acceso al equipo/disco. Si estás en cloud/remoto, detente.
3. Lee solo lo necesario para identificar, de forma de solo lectura, el usuario Windows actual y el principal que ejecuta IABV (proceso/servicio/tarea ya existente). No hagas inventario amplio ni cambies servicios, ACLs globales, políticas, rama, código ni configuración canónica.
4. Abre un selector de archivo local (Windows OpenFileDialog) para que el Owner elija su archivo PEM/TXT ya guardado. El script local debe leerlo en memoria sin que una operación tipo Get-Content/cat muestre su contenido. No asumir que cambiar extensión valida el archivo.
5. Valida la estructura PEM localmente con las APIs criptográficas .NET compatibles con Windows/PowerShell (clave RSA privada). No normalices ni reescribas el original; si está incompleto/inválido, detente y explica el resultado sin imprimir el contenido.
6. Calcula localmente la huella de clave pública con el mismo algoritmo que GitHub documenta: equivalente a la secuencia OpenSSL rsa, public output, DER, SHA-256 y Base64. Se puede implementar con RSA.ExportSubjectPublicKeyInfo + SHA-256 + Base64. Usa el navegador GitHub ya autenticado, si está disponible, para consultar Credentials → Key pairs de la App y comparar la huella. Solo una coincidencia exacta permite continuar. La huella no es la clave privada; solo mostrarla si hace falta para la verificación.
7. No revoques ni generes otra clave automáticamente. Si el archivo no se puede validar o la huella no coincide, detente; reporta que se necesita recuperar el archivo original o generar una clave sustituta y espera una decisión explícita antes de cualquier rotación.
8. Antes de instalar el secreto, determina el principal real de ejecución de IABV. Si IABV corre bajo el mismo usuario Windows, guarda una copia cifrada con Windows DPAPI CurrentUser en un directorio local de secretos de IABV y restringe los permisos del directorio al usuario y SYSTEM. No dejes un PEM plaintext adicional. Si la identidad de runtime es distinta/desconocida, no pongas ACLs al azar ni afirmes que IABV lo puede leer: detente después de verificar la huella y presenta las opciones compatibles con el principal real. Nunca guardes clave/cifrado/config dentro del repositorio ni de carpetas sincronizadas.
9. Guarda solo configuración no secreta (app_id, installation_id, repository_id, método de almacenamiento y ruta del secreto cifrado) en el lugar local apropiado y con ACL mínima. Ningún token debe persistirse.
10. Después de coincidencia de huella y custodia coherente con el principal runtime, intenta un preflight GitHub App mínimo: crea un JWT RS256 de corta duración en memoria; GET /app debe confirmar app id 5496678; GET /app/installations/175851462 debe confirmar la instalación; intercambia el JWT por un installation access token efímero, úsalo solo en memoria y hace GET /repos/jhonf463r/Python verificando id=860009771 y private=true. No llames endpoints de Issues, no crees ni edites nada, no hagas push/commit/PR, no leas contenido del repositorio con ese token y nunca imprimas JWT ni installation token. Descarta los secretos de memoria en cuanto sea viable.
11. No cambies main/CURRENT-STATE.md ni fuentes de producto, no alteres PRs, no fusiones, no ejecutes tests/build/runtime ni lecturas protegidas del producto. Este preflight es solo comprobación de credencial y alcance de la instalación, no valida G1/G2/G3 ni el puente físico.
12. Informe final sin secretos: host local confirmado sí/no; usuario/principal runtime (nombre, no credenciales); resultado PEM válido sí/no; huella local coincide sí/no; ubicación protegida (ruta, no contenido); preflight GET /app, GET instalación y GET repo con sus códigos HTTP/IDs; qué se modificó localmente; qué no se hizo; siguiente única dependencia.

No afirmes éxito si no viste cada resultado; ante cualquier ambigüedad, detente de forma segura y explica el bloqueo en lenguaje sencillo.

---

### Política de saldo y uso de perfil ayudante

Lectura TinyFish de solo lectura a las 2026-10-27 15:08:58 UTC: available_balance=4.52 USD, recarga automática sin configurar, ninguna recarga pendiente. Tarifas observadas: Agent US$0.016/paso; Browser US$0.002/minuto. Los créditos cubren la automatización del navegador, no GitHub ni IABV.

Antes de cada automatización larga, estimar coste con las tarifas vigentes. No iniciar si el saldo disponible no cubre el coste estimado más un margen de al menos 25% y un remanente de US$0.50; en tal caso, presentar las opciones antes de iniciar. No cambiar de cuenta de forma silenciosa.

Se podrá usar el saldo/perfil de un ayudante solo si el Owner lo autoriza para esa tarea y el ayudante autoriza expresamente usar su propia cuenta/perfil autenticado de forma independiente. No compartir sesiones, contraseñas, códigos MFA, cookies, claves o tokens, ni utilizar una cuenta alternativa para eludir controles de seguridad, permisos o facturación. La identidad propietaria de GitHub, el repositorio, la App y la instalación sigue siendo @jhonf463r y no se transfiere al ayudante.

### Estado y aceptación del próximo paso

- OWNER_PREFERENCE=MINIMIZE_MANUAL_STEPS; DELEGATE_TO_LOCAL_CODEX_WHERE_SAFE
- PRIVATE_KEY_SOURCE=OWNER_COPIED_TO_NOTEPAD_AND_RENAMED_PEM
- PRIVATE_KEY_CONTENT_IN_CHAT=NEVER_PROVIDED
- PRIVATE_KEY_VALIDITY=NOT_VERIFIED
- PRIVATE_KEY_FINGERPRINT_MATCH=NOT_VERIFIED
- PRIVATE_KEY_LOCAL_CUSTODY=NOT_ESTABLISHED
- WINDOWS_RUNTIME_PRINCIPAL=NOT_VERIFIED
- GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN
- INSTALLATION_TOKEN=NOT_CREATED
- TINYFISH_WALLET_BALANCE=4.52_USD; AUTO_RELOAD=UNCONFIGURED; AS_OF=2026-10-27T15:08:58.364Z
- G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
- PROTECTED_READS=FAIL_CLOSED
- TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
- BRIDGE=BRIDGE_NOT_READY

Esta sección es un plan de ejecución seguro y un handoff para Codex local. No afirma que la clave sea válida ni cierra G1/G2/G3. Añadida solo a la rama documental de la PR #546; main y CURRENT-STATE.md permanecen sin cambios.


## 25. Resultado del primer preflight local de clave: selector bloqueado antes de leer (2026-10-27)

### Hecho observado comunicado por Codex local

La ejecución ocurrió en Windows 10, equipo reportado como `MSI`, usuario `MSI\\faber`. Se observaron dos procesos `python -m iabv_v15` ejecutándose bajo el mismo usuario. Esto es evidencia de que el usuario interactivo observado y los procesos IABV observados coinciden en ese momento; no demuestra todavía que cualquier servicio, tarea futura o proceso de producción use esa misma identidad ni que vaya a poder descifrar un secreto DPAPI CurrentUser.

Codex se detuvo **antes de abrir/leer el archivo de clave** porque la inicialización del controlador de interfaz para el selector falló con:

```text
failed to write kernel assets: El sistema no puede encontrar la ruta especificada (os error 3)
```

El agente no intentó una vía alternativa y reportó:
- PEM no seleccionado ni leído.
- Validez de la clave y huella: no verificadas.
- Clave no cifrada, no guardada ni copiada por este intento.
- Preflight autenticado con GitHub: no ejecutado.
- Sin cambios en archivos/configuración/ACLs/GitHub.
- Sin tests, build, runtime, lecturas protegidas ni transporte real.

Esta falla corresponde al mecanismo para abrir el diálogo, no prueba que la clave sea inválida, que GitHub esté mal configurado ni que la identidad local no sea compatible.

### Próxima acción discriminante recomendada

Evitar repetir el mismo controlador de interfaz que falló. Dar a Codex una autorización separada y acotada para implementar un **selector nativo de Windows desde PowerShell/.NET (System.Windows.Forms.OpenFileDialog)**, ejecutado directamente por el proceso local de Codex, sin depender del controlador externo que reportó el error. No es una autorización para saltarse la selección explícita del Owner ni para copiar el secreto al chat.

El selector debe devolver al flujo local únicamente la ruta elegida, no el contenido de la clave. La lectura y validación criptográfica ocurren en memoria dentro del mismo proceso local. Requisitos:
1. Confirmar localmente Windows y el usuario real antes de abrir el selector.
2. Invocar el diálogo nativo mediante PowerShell/.NET; si ese método también falla o se detecta entorno remoto, detenerse y conservar este estado sin buscar una ruta insegura.
3. El Owner selecciona el archivo que ya tiene. El proceso comprueba el PEM sin imprimir su contenido ni reescribir el original.
4. Calcular la huella local exactamente como indica GitHub y compararla contra la huella que figura en la App. La documentación oficial actual indica que el archivo descargado es PKCS#1 RSAPrivateKey PEM y que la comparación local se hace con `openssl rsa -in PATH_TO_PEM_FILE -pubout -outform DER | openssl sha256 -binary | openssl base64`. La coincidencia exacta es obligatoria antes de guardar o usar la clave.
5. Solo después de validar la huella, determinar el principal real que consumirá la clave. No asumir que el usuario observado en dos procesos basta para identificar todos los modos de ejecución.
6. Si la huella coincide, establecer custodia que funcione para el principal runtime; si no coincide o no puede verificarse la huella de GitHub, detenerse y pedir recuperación segura o autorización para generar una clave sustituta. No revocar la clave registrada automáticamente.
7. Luego, y solo después de validar clave y custodia, realizar un preflight API de identidad/instalación/repositorio con tokens efímeros en memoria. Sin Issues, comentarios, contenido del repositorio, commits, PRs, tests ni lecturas protegidas.

Referencia vigente de GitHub: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps

### Estado actualizado

```text
LOCAL_WINDOWS=CONFIRMED_BY_CODEX_REPORT; OS=WINDOWS_10; HOST_LABEL=MSI
OBSERVED_WINDOWS_USER=MSI\\faber
OBSERVED_IABV_PROCESSES=2; COMMAND=python -m iabv_v15; USER_MATCH=OBSERVED_ONLY
PRIVATE_KEY_FILE=NOT_SELECTED; NOT_READ
PRIVATE_KEY_VALIDITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT_MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
NATIVE_WINDOWS_PICKER_FALLBACK=PROPOSED_NOT_RUN
GITHUB_APP_REGISTRATION=CREATED; APP_ID=5496678
GITHUB_APP_INSTALLATION=INSTALLED; INSTALLATION_ID=175851462
GITHUB_APP_INSTALLATION_REPOSITORIES=ONLY:jhonf463r/Python; REPOSITORY_ID=860009771
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN
INSTALLATION_TOKEN=NOT_CREATED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

Esta sección registra el resultado y una siguiente acción acotada. No cambia `main` ni `CURRENT-STATE.md`, no modifica código de producto y no cierra ningún gate de autoridad. La sección pertenece a la rama documental de PR #546 y no es autoridad canónica.


## 26. Segundo preflight local: selector funciona, diagnóstico de importación pendiente (2026-10-27)

Codex local informa que el selector nativo de Windows funcionó y el Owner seleccionó el archivo `.txt`. El archivo se leyó solo dentro del proceso local; su contenido y su ruta no se mostraron ni se transmitieron.

El intento de validación devolvió `KEY_VALID=NO_OR_UNREADABLE`, `ERROR_TYPE=MethodInvocationException`, código de salida `3`. El flujo se detuvo sin calcular huella, persistir el secreto ni llamar a GitHub. No hubo cambios de archivos, configuración ni recursos remotos.

**Interpretación:** `MethodInvocationException` es el tipo envolvente de PowerShell y no basta para identificar el fallo subyacente. No se puede concluir que el archivo sea válido ni inválido. Entre las posibilidades están un método de importación no compatible con el runtime, formato PEM no reconocido o una clave incompleta; ninguna está confirmada.

### Siguiente acción discriminante

En una nueva ejecución local y solo de diagnóstico, Codex debe:
1. Obtener la versión de PowerShell/.NET y el nombre del método criptográfico que produjo la excepción.
2. Capturar el tipo y mensaje de la excepción interna, sin mostrar contenido del archivo, ni imprimir ni registrar el secreto o la ruta completa.
3. Usar, si ya existe, un validador compatible instalado localmente; preferir el procedimiento oficial de huella de GitHub. No instalar herramientas ni convertir el archivo automáticamente.
4. Si obtiene una huella local, compararla con la visible en Credentials → Key pairs de la GitHub App. No cifrar, guardar ni usar la clave para autenticar hasta que la huella coincida exactamente.
5. No generar ni revocar otra clave sin decisión explícita. No crear JWT/tokens ni llamar a la API de GitHub mientras la clave siga sin validar.

Referencias: [GitHub: administración y verificación de claves de GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps); [Microsoft: RSA.ImportFromPem y compatibilidad de .NET](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.rsa.importfrompem).

```text
WINDOWS_NATIVE_PICKER=WORKED; OWNER_SELECTED_FILE=YES
SECRET_CONTENT_EXPOSED=NO
PRIVATE_KEY_VALIDITY=NO_OR_UNREADABLE; ROOT_CAUSE=UNKNOWN
POWERSHELL_EXCEPTION=MethodInvocationException; INNER_EXCEPTION=NOT_CAPTURED
FINGERPRINT=NOT_OBTAINED; MATCH=NOT_VERIFIED
CUSTODY=NOT_ESTABLISHED
GITHUB_APP_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

Esta sección es continuidad documental en la rama de borrador de PR #546. No modifica `main` ni `CURRENT-STATE.md`, ni cierra ningún gate.


## 27. Diagnóstico dirigido: posible confusión entre ruta del archivo y contenido PEM (2026-10-27)

### Resultado del último intento

Codex reportó PowerShell 7.6.5 y .NET 10.0.11. Se seleccionó el archivo mediante el selector nativo. `RSA.ImportFromPem` lanzó `System.ArgumentException` con este mensaje sanitizado:

```text
No supported key formats were found. Check that the input represents the contents of a PEM-encoded key file, not the path to such a file. (Parameter 'input')
```

OpenSSL no está instalado. No se obtuvo huella, no se accedió a GitHub y no se guardó ni cifró la clave. El original no se modificó y no se expuso el secreto.

### Inferencia técnica prioritaria, todavía no prueba definitiva

La documentación de Microsoft especifica que `RSA.ImportFromPem` recibe el **texto PEM**, no una ruta de archivo. La mención explícita del mensaje a “not the path to such a file” hace de la confusión entre ruta y contenido la primera hipótesis que debe comprobarse en el código del pequeño script local. No prueba por sí sola que ese sea el error, porque el texto seleccionado también podría carecer de una etiqueta PEM reconocida o estar incompleto.

No generar otra clave ni volver a editar el archivo. El siguiente intento debe corregir o verificar el argumento de la API, no reiniciar el registro de GitHub.

### Siguiente paso acotado

- Abrir una vez el selector nativo para que el Owner seleccione el archivo.
- Mantener la ruta en una variable local separada, por ejemplo `$selectedPath`.
- Leer el contenido en memoria con `[System.IO.File]::ReadAllText($selectedPath)` y pasar ese **contenido** a una importación RSA compatible, nunca `$selectedPath` directamente a `ImportFromPem`.
- No mostrar contenido ni ruta, no usar `Write-Host`, `Format-List`, transcript o logging sobre el PEM. Si falla, devolver solamente tipo/mensaje interno sanitizado y si el método recibió contenido o ruta (booleano, sin valores).
- Si la importación tiene éxito, generar localmente la huella según el procedimiento oficial de GitHub sin imprimir el PEM. Comparar la huella con Credentials → Key pairs de la App; si la UI de GitHub no está disponible, detenerse sin asumir correspondencia.
- Esta fase solo valida estructura y compara huella. Todavía no cifrar/guardar la clave, no crear JWT o tokens y no llamar a la API.

Microsoft documenta el parámetro como “The PEM text of the key to import” y el soporte de las etiquetas `PRIVATE KEY` y `RSA PRIVATE KEY`: https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.rsa.importfrompem. GitHub documenta que su clave descargada es PKCS#1 RSAPrivateKey y el método de huella SHA-256/Base64: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps.

```text
POWERSHELL_VERSION=7.6.5; DOTNET_VERSION=10.0.11
WINDOWS_NATIVE_PICKER=WORKED; OWNER_SELECTED_FILE=YES
RSA_IMPORT_API=RSA.ImportFromPem
ERROR=ArgumentException; PATH_VS_CONTENT=FIRST_HYPOTHESIS_NOT_CONFIRMED
OPENSSL=NOT_INSTALLED
PRIVATE_KEY_VALIDITY=NOT_VERIFIED
PRIVATE_KEY_FINGERPRINT=NOT_OBTAINED; MATCH=NOT_VERIFIED
PRIVATE_KEY_CUSTODY=NOT_ESTABLISHED
GITHUB_APP_AUTH_PREFLIGHT=NOT_RUN; INSTALLATION_TOKEN=NOT_CREATED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```

La sección es evidencia de continuidad en la rama de borrador de PR #546. No cambia `main` ni `CURRENT-STATE.md` y no cierra ningún gate.
