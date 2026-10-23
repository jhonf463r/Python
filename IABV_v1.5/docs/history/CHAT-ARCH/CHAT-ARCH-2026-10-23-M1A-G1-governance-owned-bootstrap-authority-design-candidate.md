# M1A G1 — Diseño de autoridad de bootstrap propiedad de gobernanza

- TASK: M1A_G1_GOVERNANCE_OWNED_BOOTSTRAP_AUTHORITY_DESIGN_ONLY
- Fecha: 2026-10-23 (America/Bogota)
- Repositorio público: jhonf463r/Python
- Baseline remoto fijado: af5fc7e7b10ac9941406f67bdf2a0cf2aa5b6b68
- Rama candidata: codex/m1a-g1-governance-owned-bootstrap-authority-design-20261023
- Artefacto: IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-candidate.md
- Tipo: propuesta documental; no aceptada ni implementada
- Base normativa de diseño: M1A v1.0.1, adoptada solo como diseño
- DESIGN_VERDICT=PASS_WITH_OPEN_AUTHORITY_DECISIONS
- GOVERNANCE=KEEP_BLOCKED; G1=NOT_ESTABLISHED; BRIDGE=BRIDGE_NOT_READY
- IMPLEMENTATION=NOT_AUTHORIZED; TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN

## 1. Propósito y límite

Esta propuesta aborda el primer eslabón de confianza que falta: cómo una autoridad de gobernanza podría establecer, sin circularidad, una raíz de bootstrap para vincular al Owner responsable, un principal Windows concreto y un emisor de decisiones de lectura.

El diseño anterior definió una ceremonia local y separación de procesos, pero dejó sin resolver quién confía originalmente en la autoridad de enrolamiento, cómo se verifica su mandato sobre IABV y cómo se repara la semántica de recibos. La reconciliación estática de ese candidato exige mantener la incertidumbre sobre la raíz y el vínculo Owner→principal, y separar el registro previo a liberación del resultado de entrega y de su reconciliación posterior.

Este documento propone límites y decisiones, no afirma que exista una autoridad, cuenta organizacional, PKI, canal, API, clave, interfaz, servicio, ledger o registro local. Ningún diseño redactado por Codex puede transformar por sí mismo una identidad conversacional en un ancla de confianza. Mientras no exista una autoridad de gobernanza autenticada por una base independiente y verificable, la decisión operacional es la opción D: no bootstrap y denegación cerrada.

## 2. Evidencia fijada y jerarquía

Se consultaron artefactos públicos de GitHub, no el checkout local. El SHA de main observado antes de redactar es exactamente af5fc7e7b10ac9941406f67bdf2a0cf2aa5b6b68; los cinco documentos de continuidad tienen los blobs esperados:

| Fuente en el baseline | Blob observado | Aporte y límite |
|---|---|---|
| IABV_v1.5/AGENTS.md | 9891b9aa95083d73ced8800f6b8c03d12542879e | Prioriza CURRENT-STATE; v1.0.1 es diseño adoptado solamente; ocho gates de implementación abiertos. |
| IABV_v1.5/docs/history/CHAT-ARCH/README.md | 496903957c9a8d56ca4ec15b18a61c198b05dc68 | Mismo enrutamiento de continuidad y límite de autoridad. |
| IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md | dc39fb58f5685bb45817d4dc6e95bfe640e44f4c | Fuente de enrutamiento actual; indica raíz independiente y vínculo Owner→principal no establecidos, candidato previo no aceptado y reparación de recibos pendiente. |
| IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md | 3d30d4a245ed19637df01d54f9cfe71662598966 | Registro de la reconciliación más reciente: CONDITIONAL_DESIGN_REVIEW; RECEIPT_SEMANTICS_REPAIR_REQUIRED. |
| IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md | ff34e9cceec6f13f8463dfb2cdfd889370bedbfa | Conserva el mismo estado y prohíbe elevar propuestas a capacidades. |

Fuentes fijadas adicionales leídas por blob:

- M1A v1.0.1, blob 7c72474a5f7c114c02320c177d6ea2aea68ad28f.
- Recibo de adopción, blob 34bee2ad8b3b4beeb468e8d563b99f511f0b352d.
- Matriz de prerrequisitos, blob 1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37.
- Entry 274, blob 5943a87d907436fc7ecac31534cbfcd31fe7de55.
- Candidato local de confianza anterior, commit 35fc8f2cb72d0394b85d34f9b6aa5157a834efc6, blob ecbbdc0504fe4e337c40859472805fb2e08796d2.
- Reconciliación estática de ese candidato, blob e9cdfb62c79f71aa7646a6f9ba5a74f80e65f736.

La reconciliación vigente de CURRENT-STATE y sus copias de enrutamiento prevalece para el estado actual. Se conserva una discrepancia histórica: el texto interno del blob v1.0.1 aún contiene lenguaje de candidato/no adoptado, mientras que el recibo exacto del Owner y el enrutamiento canónico posterior registran ACCEPT_M1A_V1_0_1_SUCCESSOR_BASELINE y ADOPTED_DESIGN_ONLY. Esta diferencia de texto no se resuelve ni se usa para alegar efecto runtime. La adopción es solo normativa de diseño.

La evidencia de la revisión adversarial previa y su reconciliación GitHub se cita como procedencia documental. No se repitió dicha revisión ni se atribuyeron a este agente verificaciones locales, runtime o independientes que no realizó.

## 3. Decisión de diseño: cuatro rutas de bootstrap

Las opciones son alternativas de raíz inicial, no mecanismos ya existentes:

| Opción | Fuente inicial de confianza | Condiciones para ser admisible | Evaluación con evidencia actual |
|---|---|---|---|
| A — Raíz Owner preexistente | Una clave/certificado de control del Owner cuya asociación con su responsabilidad sobre IABV fue establecida antes de este flujo. | Fingerprint autenticado fuera del host y de la conversación solicitante; custodio y recuperación definidos; firma de desafío fresco; delegación explícita al bootstrap authority; revocación independiente. | Preferible si se presenta evidencia verificable. Ninguna raíz ni canal se ha acreditado actualmente. |
| B — Autoridad organizacional existente | Una autoridad de identidad/firma de una organización con jurisdicción sobre el proyecto y delegación de gobernanza. | Existencia, identidad, mandato y control de clave verificables por una base confiable independiente; delegación nominativa; política de revocación y sucesión; vínculo al Owner y al proyecto. | Alternativa admisible si la autoridad y su mandato pueden verificarse. Ninguna organización o servicio se presupone. |
| C — Ceremonia para una autoridad nueva | Un nuevo GBA establecido mediante un acto de gobernanza y anclado por una autoridad ya confiable. | Debe existir una identidad/autoridad preestablecida que autentique a quienes celebran la ceremonia y el fingerprint de la nueva raíz por un canal independiente. Acta, participantes, umbral, alcance, fecha, vigencia, custodia, sucesión, recuperación y revocación quedan registrados. | No resuelve la ausencia de raíz por sí sola. Si el supuesto nuevo root se autentica solo por el mismo host, el broker, el Owner conversacional o una clave generada allí, es circular y se rechaza. |
| D — Sin ancla demostrada | Ninguna. | No aplica. La única acción permitida es conservar denegación y registrar qué evidencia de autoridad falta. | Situación actual respaldada. No emitir, instalar, enrolar, leer ni liberar bloqueos. |

**Recomendación condicional:** no escoger A, B ni C por nombre. Gobernanza debe primero aportar o designar una fuente que satisfaga sus condiciones y mostrar cómo su identidad se verifica fuera del agente solicitante, reader y emisor. Hasta entonces aplicar D. La opción C solo es legítima como delegación desde una raíz independiente preexistente; una ceremonia no crea verdad de identidad desde cero.

## 4. Modelo propuesto de autoridad y separación

“Governance Bootstrap Authority” (GBA) es un rol conceptual de diseño, no el nombre de un servicio actual. Su función sería administrar el ancla inicial y las delegaciones; no aprobar lecturas ordinarias ni modificar el estado de bloqueos.

| Rol separado | Función propuesta | Evidencia mínima antes de aceptar el rol | No puede sustituir |
|---|---|---|---|
| Gobernanza accountable del proyecto | Adopta política, designa custodios y autoridades; decide threat model y límites. | Mandato y titular autenticados mediante una raíz/canal independiente. | Una identidad afirmada por el requester o por Codex. |
| Raíz de bootstrap / GBA | Certifica el vínculo de gobernanza y emite/revoca delegaciones versionadas. | Fingerprint y cadena preanclados; mandato, custodios, quórum y recuperación verificables. | Aprobación interactiva del Owner para una lectura. |
| Owner humano autenticado | Aprueba una inscripción/renovación concreta y firma un challenge del servidor. | Credencial preinscrita bajo la raíz, prueba de posesión y evento fresco en interfaz confiable. | La autoridad raíz ni la verificación del lector. |
| Operador de instalación | Instala el issuer/reader autorizado en el ámbito aprobado. | Identidad OS, artefacto/release firmado por publisher adoptado y recibo de instalación. | Autoridad del Owner por ser administrador local. |
| Emisor de decisiones | Emite una decisión de lectura corta después de verificar solicitud, aprobación, target, catálogo, bloqueos y budgets. | Delegación verificable de GBA; clave protegida; identidad de proceso separada. | Raíz, catálogo, release de bloque o auditoría. |
| Catálogo y revocación | Publica el conjunto completo de autoridades, clases, versiones y revocaciones. | Delegación de gobernanza separada; integridad, secuencia, freshness y completitud comprobables. | El emisor local o una respuesta vacía. |
| Resolver de target | Mapea operación registrada a target/checkout/path canonical mediante contrato versionado. | Autoridad y versión adoptadas; evidencia de registro server-side y lifecycle binding. | El path o scope enviado por el caller. |
| Reader/verificador | Revalida decisión y condiciones justo antes de cada operación; aplica límites y contención. | Binario/instancia ligados a la delegación; tests de conformidad autorizados. | Emisor, GBA o liberación de bloqueo. |
| Autoridad de release de bloque | Resuelve solo el bloqueo de su clase y emite release ligado a revisión/target/operación. | Mandato independiente del requester, emisor y reader, por cada clase. | GBA, aprobación de lectura o prueba de identidad. |
| Custodio del ledger | Conserva eventos durables, integridad, secuencia, recovery y reconciliación. | Control de escritura separado de requester/reader; política de retención/antirollback. | Autoridad decisoria; un recibo nunca es permiso. |

Los roles pueden pertenecer a una misma organización solo si la delegación es explícita y las fronteras de identidad, claves, procesos y revisión son verificables. La propuesta no presupone que una sola persona o servicio satisfaga los roles. La combinación permitida de roles debe decidirla gobernanza en política versionada y documentar conflictos de interés.

## 5. Ceremonia de establecimiento propuesta

Esta secuencia es condicional y no ejecutada. Cada etapa produce evidencia de la etapa que realmente ocurrió; ningún recibo se adelanta a su evento.

### Fase 0 — Mandato externo

1. Identificar la raíz candidata A o B, sus custodios, mandato sobre IABV, fuente de identidad, canal de verificación, sucesión y revocación.
2. Verificar la autoridad fuera del workspace IABV y de los procesos requester, reader y issuer. El fingerprint se entrega por un canal previamente confiable independiente, no por el mismo canal que solicita permiso.
3. La autoridad de gobernanza aprueba un charter versionado: objeto protegido, roles delegables, quórum, conflicto de funciones, alcance geográfico/organizacional, vigencia, revocación, incidente/compromiso y recuperación.
4. Si falta el mandato, canal, principal autenticado, root fingerprint o responsable de revocación, detenerse con BLOCKED_MISSING_GOVERNANCE_BOOTSTRAP_ANCHOR.

### Fase 1 — Delegación de bootstrap

5. El root firma una delegación que nombra la GBA pública y su clave, roles limitados, server/workspace-registration scope, política de versiones, vigencia, epoch y ruta de revocación.
6. Un verificador independiente confirma cadena, firmas, alcance, estado de revocación y canonical encoding. La GBA no puede reescribir la raíz, emitir delegaciones para sí misma ni alterar el charter.
7. La clave privada de raíz permanece fuera del host/local repo. Custodia y quórum se eligen mediante decisión explícita; no se decide hardware o proveedor aquí.

### Fase 2 — Instalación y vínculo Owner↔principal

8. Un operador distinto del requester/reader instala el emisor verificado en un boundary del OS, con identidad de servicio y estado protegido. La GBA emite delegación ligada al digest/release del artefacto, clave pública, service principal, reader/server registration y policy version.
9. El sistema obtiene el principal Windows de la sesión desde token/OS, junto con un challenge fresco y contexto de instalación/instancia; no acepta SID, PID, path, public key o digest aportados por el caller como prueba.
10. La UI confiable muestra el Owner, principal local, servidor/reader, instalación, artefacto emisor, política, vigencia y permisos propuestos sin truncar ni omitir destino. El Owner autentica con credencial preinscrita y confirma un challenge ligado a esos datos.
11. La GBA valida el evento y firma una atestación de enrollment con principal de Owner, principal local, scope exacto, refs de credenciales, servidor/reader, issuer key, policy version, fechas, expiración, epoch de revocación y receipt IDs.
12. Si la UI, canal, credencial o identidad de instancia no es autenticable de manera independiente, negar enrolamiento; no degradar a confirmación verbal ni a contraseña local no verificada.

### Fase 3 — Operación de lectura por solicitud

13. Una lectura requiere fresh interactive Owner approval conforme a Entry 274, distinta de la ceremonia de bootstrap. La autorización de sesión no es una aprobación permanente.
14. El server deriva target y path desde operación registrada y resolver versionado. Rechaza caller-supplied authority, target canónico, block IDs o approved=true.
15. GBA/issuer comprueba delegación activa, revocación, versión, conexión/reader, completitud del catálogo y conjunto de bloqueos. Se evalúan todos los bloqueos aplicables; un bloqueo sin release separada mantiene denegación.
16. El issuer crea decisión server-side, efímera, ligada al request/session/reader/checkout/operation, con allowlist exacta, expiración y budgets. El reader la vuelve a verificar junto con contención resistente a carreras antes de leer y antes de liberar resultado.

Estas etapas no autorizan la ejecución ahora; describen aceptación de un futuro diseño.

## 6. Máquina de estado de establecimiento

| Estado | Significado | Transición permitida |
|---|---|---|
| UNANCHORED | No hay identidad raíz y mandato verificados. | Solo a ROOT_CANDIDATE_PRESENTED tras fuente independiente; jamás por primer arranque. |
| ROOT_CANDIDATE_PRESENTED | Hay fingerprint/mandato propuestos, todavía no aceptados. | A ROOT_VERIFIED solo por verificador externo con cadena/canal y custodia demostrados; errores → DENIED. |
| ROOT_VERIFIED | Autoridad raíz vigente y con scope comprobado. | A GBA_DELEGATED mediante delegación firmada y verificable. |
| GBA_DELEGATED | GBA tiene rol limitado/versión/revocación definidos. | A OWNER_BINDING_PENDING después de instalación/verificador exactos. |
| OWNER_BINDING_PENDING | Challenge ligado a principal/reader/instance y evento UI fresco pendiente. | A ENROLLMENT_RECORDED tras firma root/GBA y recibos durablemente guardados. |
| ENROLLMENT_RECORDED | Vínculo de confianza creado para la versión/instancia exacta. | Puede habilitar la evaluación de una solicitud nueva, no concederla automáticamente. |
| REVOKED | Root/delegación/issuer/binding revocados o vencidos. | No transita localmente a habilitado; recuperación requiere root externa vigente. |
| DENIED | Evidencia obligatoria faltante, contradictoria, no fresca o de autoridad no verificada. | Nueva evaluación solo tras evidencia/decisión independiente; no retry automático. |

La tabla no implica que estas etiquetas o transiciones existan en código. La revocación prevalece inmediatamente; rollback de epoch o pérdida del ledger fuerza DENIED y reconciliación externa.

## 7. Artefactos, identidad y ciclo de vida

Todos estos son tipos propuestos, no nombres de APIs existentes:

- Governance charter: versión, mandato, alcance, quorum, custodios, conflicto de roles, root/delegación, vigencia y recuperación.
- Trust-root record: root key/fingerprint, cadena, prueba de canal independiente, custodio, versión monotónica, revocation reference.
- GBA delegation: root signer, clave/identidad GBA, roles limitados, scope, policy/schema version, issuer targets, expiración y revocation epoch.
- Enrollment challenge: nonce de un solo uso, server/reader/workspace registration, checkout lifecycle, operación de enrolamiento, SID principal obtenido de OS, issuer public key y release digest.
- Owner enrollment attestation: firma root/GBA sobre la asociación autorizada, challenge, Owner principal, principal local, scope, instancias, versiones, expiry y revocación.
- Decision record: artefacto distinto, por lectura concreta; no lo emite la atestación de enrollment.
- Audit events: eventos append-only con emisor/actor autenticado, refs de artefactos, estado, timestamps, IDs correlacionados, resultado seguro e integridad.

En todos los artefactos la identidad de sujeto, autoridad, alcance, destinatario, versión y revocación debe vincularse criptográficamente, no inferirse de nombres de archivo, cuentas declaradas o contenido transportado por requester. Ningún hash demuestra quién autorizó los bytes.

### Emisión, vigencia, rotación y revocación

- La raíz se define fuera de la aplicación y del checkout; su clave privada no reside en el reader/issuer.
- La delegación GBA debe tener alcance mínimo, versión monotónica y expiración. La ventana temporal exacta requiere decisión de Owner; no se inventa un TTL.
- El binding Owner→principal local se invalida si cambian el sujeto, server, reader, instalación, service identity, issuer key, release digest, checkout lifecycle, política o epoch.
- Rotación: root vigente autoriza una clave nueva, periodo de solapamiento finito y orden de invalidación, con receipts enlazados. No aceptar sustitución local del root pin.
- Revocación: autoridad independiente registra objeto, autoridad, motivo/código seguro, effective time, epoch y alcance. Revocation unavailable/stale/mismatched es deny.
- Pérdida o compromiso de root: bloquear, no regenerar bajo la identidad afectada; recuperar solo por ruta externa preautorizada y registrada.
- El Owner puede aprobar la política pero el agente, emisor y lector no se otorgan autorización ni modifican el trust store.
- Ningún bootstrap o read grant libera bloqueos de recursos: cada block-release requiere autoridad independiente por clase y artefacto ligado al bloque/revisión/scope.

## 8. Recibos: intención, entrega y persistencia separadas

La propuesta adopta la corrección F1 del análisis estático previo. Los eventos siguientes son distintos y no se deben colapsar en un “completed”:

1. **Decision/pre-release record durable:** decisión de política, reserva del presupuesto y autorización temporal están registradas antes de operar. Esto prueba solo el estado preoperación.
2. **Operation attempt:** reader registra el inicio y el objeto/capability intentados. No prueba que se leyó o entregó contenido.
3. **Observed operation outcome:** registro con bytes/entries efectivamente procesados, resultado y error. Si no puede observarse, queda UNKNOWN; nunca se deduce de un intento.
4. **Delivery attempt/outcome:** separa stage, liberación al destinatario y confirmación técnica observable por el canal. Aceptar bytes por el issuer no prueba que Codex los recibió; salida visible no prueba persistencia canónica.
5. **Correlated receipt:** prueba de vínculo request→decision→operation→delivery, con IDs, audiencia, digest, contadores, firma/autoridad y estado de completitud. No contiene contenido ni convierte una denegación en permiso.
6. **Canonical persistence/fetch-back:** reconciliación del ledger/recibo desde el almacén autorizado, con secuencia/ID/blob/hash y lectura de retorno fijada al commit/revisión. Un objeto temporal no demuestra persistencia canónica.
7. **Later reuse/causal influence:** evidencia separada de que el resultado persistido fue validado e influyó en una decisión posterior concreta; ni la persistencia ni la coincidencia de IDs demuestra aprendizaje causal.

Cada etapa anterior requiere su propio evento durable, emisor autenticado, estado final (incluido UNKNOWN), enlace de correlación y resultado de reconciliación. Un registro creado antes de una liberación no puede llamarse recibo de entrega completada. Si el ledger falla después de la lectura interna, no entregar contenido; mantener budget consumido/incierto y detener hasta reconciliación autenticada. Si se perdió evidencia de entrega, no repetir automáticamente una operación con estado desconocido.

## 9. Fallos, independencia y relación con M1A

- Falta de root/canal/mandato/Owner credential/delegación: BLOCKED_MISSING_GOVERNANCE_BOOTSTRAP_ANCHOR; no read.
- Solicitud conversacional, token escrito por el agente, SID aislado, admin local, first-run, hash, commit GitHub, clave recién creada o TPM presente sin cadena/mandato: no root.
- Emisor solicita o se firma su propia delegación: rechazo; auditoría independiente.
- Root, issuer, Owner binding, policy o revocation epoch desconocidos/stale/contradictorios: deny.
- Vínculo a distinto principal/reader/checkout lifecycle o al artefacto reemplazado: mismatch; revocar la delegación afectada.
- Bloqueo activo con release ausente o inválido: BLOCK_RELEASE_UNSUPPORTED; bootstrap no lo altera.
- Ledger o autoridad de revocación caído, rollback o recovery ambiguo: deny y conservar intents sin resolver.
- Evento de aprobación repetido, scope alterado, nonce reusado, decision de otra sesión o cuotas agotadas: denegar sin liberar bytes.
- La aprobación de bootstrap no cubre solicitudes posteriores ni crea permisos de lectura.

M1A v1.0.1 sigue la autoridad normativa de diseño adoptada. Esta propuesta de autoridad debe conformar con sus ocho gates, Entry 274 y la separación de autoridades. Su adopción no cierra G1–G8 ni permite implementación.

## 10. Pruebas de conformidad futuras (no ejecutadas)

Con candidato y autorización de pruebas por separado, datos sintéticos y sin data/SQLite:

1. Root absent, unknown, self-signed, substituted, stale, rolled back o fuera de scope → bootstrap y lectura denegados.
2. Root válida pero sin evidencia de mandato sobre IABV → denegado.
3. Autoridad organizacional con identidad verificable pero delegación ausente/expirada → denegado.
4. Ceremonia new-root que se basa solo en el mismo host, Owner-chat, issuer, admin local o huella mostrada por el mismo agente → detecta circularidad y deniega.
5. Fingerprint por canal independiente que difiere del root recibido → no pin/no enrollment.
6. Owner credential no preinscrita, evento UI ausente/reproducido, firma inválida, nonce repetido, desafío expirado o scope renderizado truncado → no binding.
7. PID reciclado, proceso reejecutado, server/reader/installation ID, SID, issuer key o checkout lifecycle distinto → decision mismatch/denial.
8. Reemplazo del binario/ACL/root pin o versión de policy → invalida binding previo.
9. Rol conflictivo (requester=issuer, issuer=reader, reader=block releaser) sin delegación explícita → deniega.
10. Catálogo vacío sin attestation completa, revocación offline/stale y set de bloqueos parcial → deniega.
11. Bloque aplicable sin release independiente por revisión/alcance → BLOCK_RELEASE_UNSUPPORTED.
12. Crash tras decision intent, operación, entrega, ledger write o antes de fetch-back → conserva etapa exacta y UNKNOWN, no afirma siguiente etapa y no reintenta efecto externo incierto.
13. Diferencia entre pre-release record, operación observada, delivery receipt y canonical fetch-back → cada uno requiere evidencia individual.
14. Reader intenta emitir/cambiar root, delegación, policy o bloque → deniega y genera auditoría protegida.
15. Persistencia exitosa sin consumo posterior no prueba influencia causal; test de consumo exige nueva decisión trazada que use el artifact y muestre resultado.

Los casos no se han ejecutado. Los casos de identidad Windows/IPC, ACL, filesystem races y servicio requieren pruebas OS autorizadas; mocks no los cierran.

## 11. Decisiones explícitas que siguen pendientes

| Decisión | Información requerida para la siguiente fase | Efecto hasta resolver |
|---|---|---|
| Selección A/B/C o ratificación de D | Nombre/mandato de autoridad, custodia de root, fingerprint/cadena y canal independiente que un verificador distinto pueda validar. | D; G1 no establecido. |
| Identidad y responsabilidad del Owner | Mecanismo autenticado preexistente que vincule credencial con rol de Project Owner/gobernanza, sin tomar el diálogo con el agente como prueba runtime. | No Owner→principal. |
| Ceremony new-root (si aplica) | Autoridad externa ya confiable, custodios/quorum, public fingerprint delivery, recuperación, sucesión, revocación y threat model. | No crear ni aceptar root. |
| Mezcla de roles | Si puede haber un operador/entidad multirol y qué separación técnica/revisión lo compensa. | Roles aislados; conflicto deniega. |
| Windows principal y TCB | Cómo la autoridad valida el SID/token del proceso y cuál es el límite de admin/SYSTEM/kernel/distribution. | No enrollment local. |
| GBA, issuer, reader, catálogo/revocación y ledger | Responsables/accountable owners, fuente autorizada, versiones, lifecycle/recovery y recipientes. | No hay autoridad runtime. |
| Bloqueos | Autoridad independiente de release por clase; cada bloqueo conserva su policy. | Cualquier bloqueo aplicable deniega. |
| Recibos/durabilidad | Esquema, almacén, secuencia, integridad, recovery y comprobación canónica, separados por etapa. | No declarar entrega o persistencia. |
| Lecturas/testing/implementación | Autoría y autorización nueva para cada fase; se deben fijar candidato/SHA/alcance/stop conditions. | Sin fuente local, tests o runtime. |

## 12. Dictamen y estados

La ruta de bootstrap puede especificarse como un sistema delegado desde una autoridad preestablecida, pero no puede derivarse una raíz de confianza de la conversación ni de una nueva clave autodeclarada. Con la evidencia actualmente fijada, la única disposición operacional defendible es conservar UNANCHORED / D hasta que el Owner/gobernanza identifique una raíz externa verificable y el canal de binding. Esta propuesta no la concede ni la simula.

DESIGN_ARTIFACT=DOCUMENTARY_CANDIDATE_ONLY
DESIGN_VERDICT=PASS_WITH_OPEN_AUTHORITY_DECISIONS
BOOTSTRAP_AUTHORITY=PROPOSED_ROLE_ONLY
INDEPENDENT_ROOT=NOT_ESTABLISHED
ROOT_CUSTODIAN_AND_CHANNEL=UNRESOLVED
OWNER_IDENTITY_BINDING=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
GBA_DELEGATION=NOT_IMPLEMENTED
ISSUER_READER_SEPARATION=NOT_VERIFIED
M1A_NORMATIVE_DESIGN=v1.0.1; ADOPTED_DESIGN_ONLY
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
READ_LIST=FAIL_CLOSED
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_OWNER_CHECKOUT_ACCESSED=NO
LOCAL_DATA_OR_SQLITE_ACCESSED=NO
CREDENTIALS_OR_SERVICES_CREATED=NO
PRODUCT_CODE_CHANGED=NO
MERGED=NO
DEPLOYED=NO
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_ON_VERIFIABLE_EXTERNAL_ROOT_OR_RATIFY_NO_BOOTSTRAP

## 13. Siguiente decisión

**Siguiente actor:** Owner/gobernanza, no implementador.

**Decisión concreta:** aportar/designar una autoridad independiente ya verificable que pueda autenticar su mandato y el vínculo del Owner con IABV, o ratificar que no existe tal autoridad y mantener la denegación sin bootstrap. Solo después de esa decisión se puede definir el paso documental o de evidencia siguiente. El diseño no autoriza descubrir la autoridad mediante lectura del checkout, crear credenciales/servicios, probar un lector, hacer cambios de código, ejecutar pruebas/runtime, abrir bloqueos o lanzar el puente.
