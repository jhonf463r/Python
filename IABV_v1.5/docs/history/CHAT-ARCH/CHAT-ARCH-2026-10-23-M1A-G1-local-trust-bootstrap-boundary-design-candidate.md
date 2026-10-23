# M1A G1 — Diseño de frontera local de confianza para bootstrap

- TASK: M1A_G1_LOCAL_TRUST_BOOTSTRAP_BOUNDARY_DESIGN_ONLY
- Fecha: 2026-10-23 (America/Bogota)
- Repositorio: jhonf463r/Python
- Baseline remoto observado: 30554c56e36101638fb24513a7a1590f88e41ad7
- Rama candidata: codex/m1a-g1-local-trust-bootstrap-design-20261023
- Artefacto: IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-local-trust-bootstrap-boundary-design-candidate.md
- Estado: candidato documental; no aceptado ni implementado
- GOVERNANCE=KEEP_BLOCKED; G1=NOT_ESTABLISHED; BRIDGE=BRIDGE_NOT_READY
- TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; REAL_TRANSPORT=NOT_RUN
- Checkout local protegido del Owner: NOT_ACCESSED

## 1. Resumen y veredicto

### Arquitectura recomendada

Propongo una frontera de confianza de dos planos:

1. Una raíz de enrolamiento independiente autentica la responsabilidad de Owner/gobernanza y autoriza un vínculo puntual entre una credencial criptográfica del Owner, el principal Windows obtenido del token real, la clave pública del emisor y la identidad exacta de la instalación/reader. La raíz no la crea, auto-firma ni declara confiable el mismo broker que luego emitirá decisiones.
2. Un servicio Windows emisor, en proceso e identidad de OS separados del solicitante y reader MCP, conserva su clave privada y estado bajo ACL del sistema operativo. Solo emite decisiones después de verificar aprobación humana fresca, target resuelto por el servidor, catálogo completo, bloqueos y alcance.
3. El reader y cada frontera de lectura verifican la decisión, identidad, revocación, vigencia y presupuesto justo antes de usar el recurso. Ni el servicio ni la decisión pueden liberar un bloqueo operativo.
4. Un ledger durable, protegido y auditable registra solicitud, aprobación, decisión, reserva, denegación y resultado. Un recibo es evidencia de eventos, nunca autoridad.

Esta estructura supera los intentos terminales porque no confunde SID, consentimiento de UI, clave recién generada, API de Windows, hash de documento o clase Python con una raíz de autoridad. Conserva la guardia fail-closed del candidato M1; no abre una lectura permisiva mientras falte autoridad.

### Veredictos separados

- Diseño arquitectónico: definido como propuesta condicional en este documento.
- Factibilidad: condicionada a una raíz inicial verificable, ceremonia Owner→principal y garantías de proceso/objeto que deberán probarse en Windows.
- Autoridad inicial demostrada: no.
- Implementación: no.
- Verificación operativa: no.
- G1: NOT_ESTABLISHED.
- DESIGN_VERDICT=PASS_WITH_OPEN_AUTHORITY_DECISIONS. Las fronteras, flujos y criterios quedan especificados; la raíz inicial no puede seleccionarse o fabricarse aquí. No está listo para implementación hasta resolver D1–D4 de la sección 10.

## 2. Identidad y evidencia de continuidad

### Baseline y destino

La conexión GitHub observó el repositorio público jhonf463r/Python y main en 30554c56e36101638fb24513a7a1590f88e41ad7, tree a273cd5573b9b25997d1169a86d81f68f2e16a9d. La rama codex/m1a-g1-local-trust-bootstrap-design-20261023 no existía al consultar GitHub; el archivo de destino tampoco existía en el baseline. No se reutilizó una candidata anterior.

### Cinco documentos canónicos obtenidos desde el commit fijado

| Archivo | Blob |
|---|---|
| IABV_v1.5/AGENTS.md | c59e1ce1faf212852a342478f03dbabead2190b9 |
| IABV_v1.5/docs/history/CHAT-ARCH/README.md | 70f71073d402da1fb1c0a842ad25f2178336fadb |
| IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md | 5a2cf6d1bab5beb4eff3a9f3f2bd7a37919e28e0 |
| IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md | bbd86375f3cdbf940fbed62d1efde0d2fb6a5589 |
| IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md | b96e9333f0b27b61ad443bee77f1641c32879f18 |

Los cinco sitúan el estado vigente en PARTIAL_FAIL_CLOSED_GUARD_ONLY: la ruta scoped-read no está implementada; G1, G2 y G3 no están establecidos; GOVERNANCE=KEEP_BLOCKED; y no hay continuación automática. Esta evidencia es del contenido público en ese commit, no del checkout local del Owner.

### Artefactos históricos recuperados y verificados por blob/contenido

| Artefacto | Blob | Evidencia que aporta y límite |
|---|---|---|
| M1 scoped-read candidate static reconciliation, 2026-10-23 | ec6ef86fd926db97d911a8b26dc39fb681ba70af | El candidato anterior añadió denegación fail-closed y no implementó autorización. No se repite su revisión. |
| M1A G1 trust-bootstrap candidate implementation result, 2026-10-22 | 33ba4562c3753a053b92176061d0258a1c35e77d | BLOCKED_MISSING_G1_TRUST_ANCHOR; no se demostró autoridad independiente de enrolamiento. |
| M1A G1 Windows OS candidate result, 2026-10-22 | fa9a0d217b4e01e2f496d4e2cc9a31c548b5de9c | BLOCKED_MISSING_G1_TRUST_ANCHOR; primitivas OS no prueban instalación o ceremonia. |
| M1A G1 Windows OS candidate handoff, 2026-10-22 | 0f9be4908d63dd525e572519c1e1891c894fea0a | Service SID, CNG y named pipe fueron propuesta histórica; el intento terminó sin cambios. |
| Entry 274 consolidated read decision contract | 5943a87d907436fc7ecac31534cbfcd31fe7de55 | Separa aprobación, decisión, verificador, ledger y liberación de bloques. |
| M1A v1.0.1 explicit Owner adoption receipt | 34bee2ad8b3b4beeb468e8d563b99f511f0b352d | Adopción de diseño solamente; la revisión figura como OWNER_REPORTED. |
| M1A v1.0.1 implementation prerequisite gate matrix | 1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37 | Ocho prerrequisitos siguen abiertos; no es implementación. |
| M1A operational-block scope contract v1.0.1 | 7c72474a5f7c114c02320c177d6ea2aea68ad28f | Contrato fuente de diseño, no catálogo runtime verificado. |
| Windows OS trust-bootstrap route research | 0316f3b897ed5db98e185bf55db1ba482b7dcaf5 | Documenta primitivas Windows potenciales; no su disponibilidad/configuración local. |

Los documentos recuperados contienen esos resultados y sus límites. Los estados terminales de algunos intentos Codex son Owner-supplied; los recibos históricos reportan reconciliaciones GitHub independientes de sus commits/branches. No se eleva la procedencia del intento original.

### Drift de versión

El override inicial de CURRENT-STATE, AGENTS, README, CONTEXT-INDEX y MEMORY-OPERATING-PROTOCOL indica M1A v1.0.0 como contrato adoptado. El recibo explícito del Owner y su matriz vigente identifican v1.0.1 como diseño normativo adoptado, blob 7c72474a5f7c114c02320c177d6ea2aea68ad28f, y v1.0.0 como antecesor. Siguiendo la instrucción de esta tarea, el diseño usa la adopción explícita v1.0.1 para los requisitos M1A y registra la discrepancia sin resolverla ni editar continuidad. Los efectos que dependan de precedencia siguen sujetos a reconciliación canónica.

## 3. Separación de requisitos, propuesta y evidencia

Entry 274 separa cinco autoridades: diagnóstico, evidencia de aprobación fresca, decisión de lectura, verificación del reader y ledger durable. No se pueden colapsar en approved=true. El servidor deriva target; la decisión se guarda en registro server-side ligado a sesión/reader, con presupuestos finitos; no es bearer transferible. Una decisión de lectura no libera bloques. Revocación y ledger son obligatorios y fallan cerrados. El reader debe aplicar contención resistente a carreras y no liberar contenido si no puede persistir finalización.

M1A v1.0.1 exige catálogo completo, autenticado y versionado; principal productor autenticado y autorizado; resolución confiable de assistant/target; evaluación de todos los bloqueos activos; liberación independiente por bloque; y rechazo de datos desconocidos. La adopción es normativa de diseño, no establece los productores ni autoridades runtime.

El informe Windows documenta service SID restringido, clave CNG con descriptor de seguridad, named pipe con ACL explícita y WebAuthn como candidato. También dice que no se inspeccionó/configuró el equipo ni se instalaron servicio, claves o credenciales. No se observó Owner→principal Windows, emisor, servicio, instancia, catálogo, revocación, ledger local o lectura real.

## 4. Threat model y actores

### Límite de amenazas

La propuesta busca impedir que un requester MCP ordinario o reader no privilegiado se autoautorice, modifique política, firme decisiones o sustituya la raíz. Depende de Windows, el operador autorizado y la cadena de instalación según garantías que deberán probarse.

No afirma resistencia frente a kernel comprometido, administrador local malicioso, SYSTEM, compromiso de raíz/Owner, sustitución física ni UI comprometida. Si se exige resistir esos actores, hace falta autoridad o atestación independiente adicional; factibilidad y evidencia permanecen UNRESOLVED.

| Actor | Evidencia de identidad | Puede | No puede por sí solo |
|---|---|---|---|
| Owner humano accountable | Decisión de gobernanza que vincule la responsabilidad de proyecto con una credencial criptográfica. Conversación documenta decisiones, no identidad runtime. | Decidir política y aprobar enrolamiento/acceso presentado. | Hacer que una SID o botón sea identidad humana verificable. |
| Principal Windows | SID/tokens obtenidos del OS en la sesión/proceso real. | Identificar principal local. | Probar identidad civil o responsabilidad de Owner. |
| Operador/instalador | Release/installer autorizado, publisher verificado y recibo de instalación. | Instalar/actualizar dentro del alcance aprobado. | Probar que es Owner por tener admin local. |
| Raíz de enrolamiento | Clave/fingerprint recibido por canal confiable previo, custodio, versión y revocación aprobados. | Certificar delegaciones y revocar. | Autojustificar su confianza; no existe demostrada actualmente. |
| Credencial de Owner | Clave cuya asociación al Owner fue anclada por la raíz. Firma challenge fresco. | Aprobar enrolamiento y scope. | Ser raíz si su clave pública no está anclada. |
| Servicio emisor | Proceso Windows separado y clave privada protegida por OS. | Verificar y emitir decisiones acotadas/ledger. | Crear la raíz, auto-enrolarse, modificar política o liberar bloques. |
| Solicitante | Identidad derivada del canal real, no del payload. | Pedir operación y declarar propósito. | Fijar autoridad, target, principal, block IDs o scope autorizado. |
| Reader MCP | Binario/instancia comprobados por deployment/OS y ligados al emisor. | Verificar decisión y ejecutar operación admitida. | Firmar autorización, cambiar root/policy ni ignorar bloqueos y alegar conformidad. |
| Autoridad de catálogo/revocación | Delegación de raíz y rol explícito. | Publicar snapshot completo versionado y revocación. | Inferirse del emisor o de respuesta vacía. |
| Autoridad de liberación de bloque | Delegación del propietario de cada clase de bloqueo. | Emitir release temporal específico del bloque. | Ser reader, solicitante o issuer por defecto; Entry 274 no ofrece release actual. |

La separación debe materializarse en identidad OS, proceso, custodia, ACL, canales y política. Nombres de clase separados no bastan.

### Amenazas adversariales mínimas

Inscripción propia; sustitución o rollback de raíz/configuración; SID o Owner falsificado por texto; nonce/evento repetido; PID reciclado/checkout recreado; decisión transferida entre sesiones; revocación ausente/stale; target controlado por caller; TOCTOU por symlink/junction/reparse/hardlink; caída/corrupción/pérdida del emisor o ledger; y operador/admin comprometido. Cada caso debe denegar, salvo administración y recovery independientes, documentados y verificables.

## 5. Ceremonia inicial condicional

Instalar un broker no lo hace confiable. Esta ceremonia solo puede comenzar luego de que Owner/gobernanza seleccione una raíz independiente existente y verifique su autoridad fuera del host y de los procesos solicitante/reader/emisor.

### Fase 0 — Decisiones previas

1. Gobernanza nombra la raíz, custodio, método de verificar su fingerprint/cadena, delegaciones, recuperación y revocación. Una clave generada por el propio bootstrap, first-run, SID, hash, commit, admin local o consentimiento conversacional no es raíz.
2. La raíz vincula una credencial criptográfica con la responsabilidad de Owner sobre IABV. La clave privada no se guarda en IABV. Si no existe root/canal preestablecido, parar sin trust-on-first-use.
3. Owner acepta explícitamente el threat model: qué privilegios de administrador, kernel y distribución se consideran TCB; quién instala y qué release/build se valida.
4. Se nombra separadamente autoridad de catálogo/revocación y autoridad para cada clase de release de bloque.

### Fase 1 — Instalación del proceso

5. Operador privilegiado instala artefacto de issuer validado contra una autoridad de distribución previamente adoptada. El requester/reader no instala ni puede cambiar binario, servicio, ACL, política o root.
6. Servicio de mínimo privilegio con service SID restringido, named pipe con DACL explícita y estado en ubicación protegida. CNG key se crea dentro del servicio; private key accesible solo a identidad de servicio/SYSTEM según política aprobada. Nada de claves en checkout.
7. Servicio crea instalación aleatoria de correlación y challenge de un solo uso. El id aleatorio no es identidad confiable.
8. Sistema recopila datos de binario, service SID, public key, policy revision y reader registration desde fuentes protegidas. El servicio no los acepta como claims del caller.

### Fase 2 — Binding Owner y principal local

9. Broker construye un challenge canónico con nonce, hash/release del binario, instalación/instancia, service SID, issuer public key, revisión de política y SID local real derivado del token del principal que solicita enrolamiento.
10. Owner se autentica con credencial pre-registrada mediante canal confiable independiente que muestre el contenido completo. Owner confirma que liga su responsabilidad y esa instalación/instancia al SID exacto. SID significa principal local, nunca identidad civil.
11. Raíz independiente verifica firma Owner, challenge, vigencia y alcance, y certifica Owner credential ref, SID, issuer key/id, server/reader identity, policy version, roles permitidos, expiración y generación de revocación. El broker no firma su propia autorización de enrolamiento.
12. Si falta Owner credential, vínculo de responsabilidad, canal independiente, trust root o release verificado, detener en BLOCKED_MISSING_G1_TRUST_ANCHOR. No autoenrolamiento.

### Fase 3 — Pin y operación

13. Instalar certificado/registro de enrolamiento y root pin en ubicación protegida. Root public key debe corroborarse por fuente independiente; configuración mutable por reader no puede añadir roots, bajar versión o restaurar issuer revocado.
14. En cada conexión, issuer autentica el caller por named pipe y contexto OS: token/SID y PID asociado por APIs de OS, imagen instalada autorizada y challenge de sesión. Nunca aceptar caller-provided reader_id, PID, hash, path o policy revision como prueba.
15. Vincular instancia al menos a instalación/lifecycle ID, service principal, release digest, reader process creation binding y sesión IPC challenge. PID solo no basta. APIs/garantías de obtención sin carrera deben demostrarse en la implementación, no se consideran probadas por este diseño.
16. Cambios de binario, instalación, root, policy o checkout invalidan decisiones activas. Rotación solo autorizada por root vigente con transición auditada; pérdida de root requiere canal externo de recuperación, nunca self-enrollment del broker.

### Límite real de la cadena

La cadena debe comenzar con clave pública cuya identidad y autoridad sobre IABV se establezcan fuera de solicitante, reader y broker. GitHub ID, commit público, firma recién creada, admin, Windows Hello, SID, hash, nombre de archivo o primera ejecución no lo prueban automáticamente. Las fuentes actuales no demuestran raíz preexistente ni canal de Owner. La secuencia es completa solo condicionalmente; el vínculo inicial está abierto, por lo que G1 no se cierra.

## 6. Arquitectura y límites de OS

| Elemento | Propiedad requerida | No demuestra |
|---|---|---|
| Issuer service | Proceso Windows aparte, identidad OS propia, SID restringido, mínimo privilegio; no contiene reader/requester. | Que el servicio exista o esté configurado. |
| CNG private key | Key persistida/no exportable si proveedor compatible, DACL explícita para servicio/SYSTEM, uso de firma dentro del servicio. | TPM/provider disponible o protección ante admin/kernel. |
| Named pipe | Descriptor/DACL restrictiva explícita; autenticar por token OS y challenge. | Seguridad si usa DACL por defecto o acepta SID textual. |
| Protected state | Ejecutables, root pin, enrolment, catálogo y ledger fuera de checkout/user-write scope. Backup y rollback versionados. | Integridad ante SYSTEM/admin/kernel comprometido ni antirollback sin fuente confiable. |
| Reader | No privilegiado; decision reference ligada a sesión; verificación en cada frontera; sin escritura a root/policy/ledger. | Que un reader comprometido no omita verificación; requiere evidencia de binary/runtime enforcement. |
| Approval UI | Canal Owner confiable independiente del requester, muestra todo el scope/audience. | Que una UI existente o consentimiento genérico tenga ese contrato. |

Actualización requiere autoridad de distribución aprobada y versión monotónica. Rotación issuer: root vigente autoriza key nueva y ventana corta; revocar la vieja después de reconciliar. Desinstalación: revocar instancia/key, detener emisión, conservar receipts/intents; eliminación solo por operador autorizado. Rollback, ledger corrupto o pérdida de root implica fail-closed. No se verificaron ACL, servicio, CNG, pipe, token, instalador o deployment local.

## 7. Contrato de solicitud y decisión

### Solicitud

El servidor crea request_id, nonce oculto al requester, session identity y operation canonical. El target del caller es una pista visible, no autoridad. Se permiten propósito y destinatario como texto para mostrar. Rechazar caller-supplied owner, issuer, instance, block IDs, resolved_target, policy version, approved=true, receipt o hash como evidencia de autoridad.

### Aprobación fresca

La UI confiable muestra servidor/reader/instancia, checkout registration y stable root object, operación, paths/list target exactos, raw y normalizado, propósito, destinatario, budgets, expiry, estado/bloqueos y cualquier destino de contenido. Rechazar truncamiento, scope ambiguo, identidad desconocida, evento ausente/cacheado/autoresuelto, replay, nonce inválido o UI controlada por caller.

Entry 274 exige fresh interactive Owner approval para read_file y list_directory. Una aprobación puede definir scope exacto con budgets finitos para varias operaciones de una sesión corta solo si la autoridad/UI lo soporta; cada op consume budget y revalida. No equivale a autorización de todo el workspace.

### Decision record

Registro autoritativo dentro del ledger server-side del issuer; al requester solo vuelve un ID de referencia no autoritativo ligado a conexión/sesión y reader. Campos mínimos: schema/policy version, decision/request/session IDs, approval UI event y nonce digest, Owner credential reference, OS principal reference, issuer chain/key revision, exact server-reader-installation-session binding, checkout/worktree lifecycle identity, operation, resolver revision, allowlist/scope digest, purpose/audience, catálogo y complete block-set revision/digest/freshness, per-block applicability/release refs, issue/expiry/revocation epoch, finite budgets, reserve/completion IDs y status. Integridad/firma debe validarse contra root aprobada.

Una firma no basta. Reader debe revisar cadena, audiencia, sesión, resolver, scope, block snapshot completo, releases independientes, revocación/freshness, presupuesto y objeto filesystem. Decision ≤ 5 min desde emisión, siguiendo Entry 274. La frescura de catálogo/revocation requiere decisión normativa explícita; no se inventa aquí.

## 8. Verificación por operación de lectura

1. Autenticar al caller mediante contexto OS/MCP confiable.
2. Resolver server-side instancia, checkout, operación y path; caller no expande target.
3. Verificar raíz/cadena, issuer, policy y reader/instance identity.
4. Obtener conjunto completo, autenticado, versionado y fresco de todos los bloques; ausencia no equivale a lista vacía.
5. Ejecutar M1A v1.0.1 pre-selector validation y agregar todos los resultados; assistant y target son identidades confiables, no texto caller.
6. Por cada block applicable exigir release independiente ligado a block/revision, target, operación, scope y expiry. Entry 274 establece BLOCK_RELEASE_UNSUPPORTED en la ausencia de release soportada; por tanto el default de hoy sigue denegando.
7. Exigir aprobación fresca y crear decisión ledger-side; reservar atómicamente budgets de bytes, entries y calls.
8. Abrir/listar respecto a root handle/objeto fijado con método OS resistente a TOCTOU, symlink, junction, reparse, hardlink y sustitución de componente. Normalización string solo es filtro inicial.
9. Tras staging, revalidar root, target, política, expiración, revocación y bloques. Si hay cambio, descartar staging.
10. Commit durable del recibo de finalización y consumo antes de entregar contenido. Si commit falla, no entregar; presupuesto queda cargado/incierto y el intent requiere reconciliación autenticada.
11. Registrar denegación segura cuando sea posible. Si ledger está caído, denegar aunque no se pueda escribir el recibo.
12. Cualquier evidencia obligatoria ausente, stale, parcial, ambigua o contradictoria ⇒ no leer/entregar.

La resistencia TOCTOU es requisito de aceptación futuro. Comprobar ruta y abrirla en operación separada no es suficiente. Si Windows no puede demostrar la equivalencia requerida, CONTAINMENT_UNPROVEN.

## 9. Revocación, recuperación y receipts

La raíz delega revocación a autoridad explícita distinta del issuer; no hay autoridad local actual identificada. Decisiones expiran en ≤5 minutos. Intervalo máximo de freshness para catálogo/bloque/revocation debe adoptarlo Owner. Revocación offline/stale/inconsistente => deny; no fail-open con cache.

Issuer revocado no emite nuevas decisiones; sesiones existentes se invalidan en expiración o detección. La rotación requiere firma de root vigente. Si root perdida/comprometida, recuperar por autoridad externa ya reconocida; si no existe, bloqueo administrativo, no autogeneración. Pérdida/rollback de ledger mantiene intents UNRESOLVED y detiene reads hasta reconciliación independiente. Liberación de bloque es artefacto distinto de autoridad responsable de esa clase. No es consecuencia de Owner read approval ni de firma issuer.

Ledger append-only/tamper-evident bajo authority fuera del alcance write/delete reader/requester. Registra seq, principal refs, request/decision, target/object digests, policy/catalogue/revocation versions, timestamps, operation/result, budgets y error codes; omite contenido/secretos. Si hoy no existe esa storage authority, no reemplazarla por JSON firmado por el mismo servicio y llamarlo prueba suficiente.

## 10. Decisiones pendientes de Owner/gobernanza

| ID | Decisión | Alternativas coherentes y recomendación | Evidencia exigida | Autoridad que decide | Mientras no se decida |
|---|---|---|---|---|---|
| D1 | Raíz de confianza inicial | Usar raíz/clave de Owner preexistente con fingerprint autenticado fuera del host; o raíz organizacional preexistente con delegación explícita. No generar raíz durante setup. | Custodio, key/fingerprint, origen confiable, canal y recovery/revocation. | Owner y autoridad de gobernanza independiente. | No enrolar; G1 bloqueado. |
| D2 | Binding Owner credential→responsabilidad | Credencial individual del Owner o clave delegada por organización; recomendar prueba de posesión y certificación de rol sin guardar private key en IABV. | Acta/delegación verificada por la raíz. | Owner/governance. | No aceptar aprobación Owner runtime. |
| D3 | Owner→Windows principal | Confirmación fresh, out-of-band, de SID real obtenido del token más challenge/instance/issuer key; mostrar datos íntegros. SID solo identifica principal local. | Credencial, nonce, UI/canal y verificación independiente. | Owner, enrollment authority, operador. | No binding de principal. |
| D4 | Threat model de admin/OS | Declarar admin/kernel/distribución como TCB o exigir mecanismos adicionales; no se decide aquí. | Aceptación explícita y source/release authority. | Owner/governance. | No confiar en key/ACL/process claims. |
| D5 | Firma y ruta del instalador | Adoptar publisher/release signing o mecanismo existente. | Artefacto, cadena y supply-chain verificables. | Owner + responsable de release/IT. | No instalar broker. |
| D6 | Catálogo y revocación | Delegar autoridad separada de issuer; definir catálogo completo, publisher, revocation epoch/freshness. | Identidad, firma, completeness, scope y revocation evidence. | Autoridad de catálogo. | No evaluar blocks ni emitir. |
| D7 | Resolver target/version | Resolver server-owned versionado, ligado a checkout lifecycle y objetos, nunca caller path. | Call-site mappings y objetos estables, protected source. | Owner/governance + resolver owner. | TARGET_IDENTITY_UNTRUSTED. |
| D8 | Liberar bloqueos | Autoridad específica por clase y artefacto independiente. | Block id/revision/digest, target, op, scope, expiry, authority. | Owner del bloqueo, independiente del issuer/reader. | Cualquier bloque aplicable deniega. |
| D9 | Ledger, recovery y antirollback | Store protegido durable con backup/sequence/reconciliation; no cache como autoridad. | Integridad, atomicidad, rol de custodia y recuperación. | Owner/governance/security. | No entregar bytes sin receipt. |
| D10 | Sesión/scopes/budgets | Una operación o sesión corta con exact scope, budgets finitos y fresh approval. | UI contract, rate limits, expiry y ledger reservation. | Owner por interfaz aprobada. | READ_LIST=FAIL_CLOSED. |

D1–D4 son mínimos para que la ceremonia no sea circular. El diseño no elige una política nueva en nombre del Owner. La identidad real de cualquier autoridad nominada permanece UNRESOLVED hasta que se compruebe.

## 11. Trazabilidad de los vínculos

| Vínculo | Estado actual | Evidencia futura necesaria |
|---|---|---|
| OWNER_TO_WINDOWS_PRINCIPAL | DESIGN_DEFINED / NOT_ESTABLISHED | Firma Owner fresca sobre SID real/token, nonce e instancia; rechazo de SID falso/replay. |
| OWNER_TO_BOOTSTRAP_AUTHORITY | NOT_ESTABLISHED | Root/fingerprint, custodio, delegación de Owner, revocación y verificación independiente. |
| BOOTSTRAP_AUTHORITY_TO_ISSUER | DESIGN_DEFINED / NOT_ESTABLISHED | Certificado/registro root-signed ligado a key, service identity, policy y expiry. |
| ISSUER_KEY_CUSTODY_AND_SEPARATION | DESIGN_DEFINED / NOT_VERIFIED | ACL, token/process, acceso permitido/denegado y ausencia de exportación. |
| ISSUER_TO_EXACT_SERVER_INSTANCE | DESIGN_DEFINED / NOT_ESTABLISHED | Process creation/session challenge, binary/release, lifecycle registration, reemplazo/replay tests. |
| READER_SIDE_DECISION_VERIFICATION | DESIGN_DEFINED / NOT_ESTABLISHED | Cada read verifica issuer, sesión, scope, target, freshness, block/release y budget. |
| VERSIONED_TARGET_RESOLVER | NOT_ESTABLISHED | Resolver confiable, revisionado; forged caller target/root/path siempre deniega. |
| REVOCATION_AUTHORITY_AND_FRESHNESS | NOT_ESTABLISHED | Autoridad separada, fetch fresco, offline/replay/rollback deniega. |
| COMPLETE_ACTIVE_BLOCK_SET | DESIGN_DEFINED / NOT_ESTABLISHED | Attestation de totalidad/versión/freshness; respuestas faltantes o vacías sin prueba deniegan. |
| INDEPENDENT_BLOCK_RELEASE | NOT_ESTABLISHED / BLOCK_RELEASE_UNSUPPORTED | Artefacto por bloqueo ligado a revisión/target/op/scope; no herencia de aprobación. |
| DURABLE_OPERATION_RECEIPT | DESIGN_DEFINED / NOT_VERIFIED | Atomic reserve/completion, tamper/reorder/delete/crash/recovery tests. |
| RACE_RESISTANT_RESOURCE_CONTAINMENT | DESIGN_DEFINED / NOT_VERIFIED | Pruebas reales en Windows sobre root/path substitution, links/reparse/hardlink y handles. |

DESIGN_DEFINED significa que este documento describe el contrato conceptual; no significa que el mecanismo exista ni haya sido aceptado.

## 12. Matriz futura de conformidad, no ejecutada

- Root missing/unpinned/self-signed: enrolment y lectura denegados.
- Owner key desconocida, SID equivocado, challenge repetido o UI no confiable: no certificar.
- Issuer key sustituida, ACL amplia, caller con admin no autorizado: detener y exigir recovery; no asumir separación.
- Service/reader equivocado, PID reciclado, binario cambiado o checkout recreado: decision mismatch.
- Catalog/block snapshot parcial, stale, incompleto, desconocido o revocation offline: BLOCK_SCOPE_UNEVALUABLE/deny.
- Bloque aplicable sin release propia, release para otro bloque/revision/scope: BLOCK_RELEASE_UNSUPPORTED/deny.
- Caller-supplied target, resolver desconocido o root mutable: TARGET_IDENTITY_UNTRUSTED/deny.
- Decision de otra sesión, replay nonce/event/decision, vencimiento o presupuesto excedido: reject sin leer.
- Symlink/junction/reparse/hardlink/rename race, path cambia entre check/open o staged object cambia: CONTAINMENT_UNPROVEN; cero bytes liberados.
- Crash tras reserva o tras leer pero antes de completion; ledger corrupto/unavailable: no entrega, intent UNRESOLVED y halt persistente.
- Revocation/expiry/block change mientras staging: descartar datos y denegar.
- Admin/kernel adversario: verificar explícitamente el límite; no afirmar protección más allá del TCB adoptado.
- Receipts nunca contienen contenido; un receipt válido no convierte una operación denegada en autorizada.

Tests de OS requieren filesystem temporal real en Windows y hooks de sustitución; mocks solos no prueban TOCTOU.

## 13. Plan posterior de aceptación; no autorizado

1. Reconciliar CURRENT-STATE con v1.0.1, fijar autoridad activa y aprobar decisiones D1–D4. Si falla, no bootstrap.
2. Acordar delegaciones de issuer, catálogo, revocación, block-release, resolver y ledger (D5–D10). Si falta un rol, la capacidad correspondiente sigue denegada.
3. Aprobar contrato de instalación y root desde canal independiente. No implementar antes.
4. Emitir autorización nueva para candidato aislado, base/SHA y archivos concretos; preservar la guardia fail-closed.
5. Implementar la frontera mínima en slices revisables. Sin credenciales/servicios locales salvo autorización específica.
6. Revisión adversarial independiente del commit exacto.
7. Pruebas de conformidad focalizadas y separadamente autorizadas, datos sintéticos y sin acceso a data/SQLite.
8. Validación Windows/deployment autorizada, verificando ACL, proceso, key, IPC, revocación, reader boundary y receipt. Sin estas pruebas no se cierra G1.
9. Una lectura estática real requiere G1–G8 satisfechos, autorización de lectura nueva y release independiente de todo bloqueo aplicable; correlacionar solicitud→decisión→reserva→read/result→receipt y reconciliar fetch-back.
10. Promoción o despliegue requiere nueva decisión y autorización; no se deriva de la existencia del candidato.

Cada fallo conserva KEEP_BLOCKED y el alcance anterior; no hay continuación automática.

## 14. Limitaciones y estado de cierre

- Windows research prueba documentación de primitivas candidatas, no configuración ni seguridad del equipo.
- No se demostró root preexistente, credencial Owner, canal de inscripción, installer, service, CNG provider, named pipe, catalog/revocation authority, target resolver, block release, ledger, ACL, instancia o lectura.
- No se accedió al checkout local, data/, SQLite, secretos, credenciales ni runtime.
- No se ejecutaron comandos, pruebas, build, lint, proceso, MCP, Codex CLI, issuer/reader, transporte o protected read.
- No se crearon claves, identidades, servicios, configuración o permisos; no se liberó bloqueo.
- El guard fail-closed M1 no se modifica ni retira.
- El siguiente actor todavía no es implementador: Owner/governance debe resolver D1–D4 y la discrepancia canónica. No hay follow-on automático.

### Estados

DESIGN_ARTIFACT=DOCUMENTARY_CANDIDATE_ONLY
DESIGN_VERDICT=PASS_WITH_OPEN_AUTHORITY_DECISIONS
OWNER_DECISIONS=D1-D10_PENDING
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
READ_LIST=FAIL_CLOSED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_OWNER_CHECKOUT_ACCESSED=NO
LOCAL_PROTECTED_READ=NOT_AUTHORIZED
CREDENTIALS_OR_SERVICES_CREATED=NO
MERGED=NO
DEPLOYED=NO
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_ON_INDEPENDENT_ROOT_AND_OWNER_IDENTITY_BINDING
