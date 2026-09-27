# IABV v1.5 — UNIVERSAL ENVIRONMENTAL SEMANTICS / ALGORITHMIC COGNITION
## Deducción arquitectónica y programa de investigación — 2026-09-26

ESTADO: CANONICAL RESEARCH DIRECTION / ARCHITECTURAL DEDUCTION / NOT IMPLEMENTATION AUTHORIZATION
Repositorio: jhonf463r/Python
Subdirectorio: IABV_v1.5/
Revisión BIO-META inspeccionada: 0785531851c86d072e2c8cdb8fc5b85255b441c8
Parent: 4da2924c6238582ceb87aaa65d25c79c6cafff3e

## 1. OBJETIVO GLOBAL

El objetivo no es enseñar a IABV cada proveedor, aplicación, navegador, sistema operativo o dispositivo como un caso independiente.

El objetivo es que IABV disponga de una lógica ambiental general que pueda observar una realidad nueva, reconocer conceptos, formular relaciones, mantener alternativas, verificar hipótesis, inferir capacidades, elegir canales y reutilizar el conocimiento obtenido.

Secuencia directora:
raw environment → observation → normalization → entity/concept candidate → attributes → relation hypotheses → state estimate → capability/affordance estimate → verification → reusable world knowledge → decision → action → outcome observation → knowledge update → future decision

Lo universal no significa eliminar todos los adaptadores específicos. Significa que el razonamiento semántico superior no debe cambiar solo porque cambien Windows, Linux, macOS, Chrome, Firefox, una API, una CLI o un proveedor.

## 2. CORRECCIÓN DEL AUDIT M1.1

El audit independiente acertó al detectar que DevinAccount y DevinCredential son un silo específico de proveedor.

Sin embargo, la afirmación de que IABV carece de observación de cuentas, sesiones o navegación es demasiado fuerte respecto al código actual. La reconciliación directa encontró AccountInventoryEntry, AccountInventorySnapshot, account_resource_scanner, scan_browser_accounts, scan_browser_sessions, build_inventory_snapshot, UniversalPerceptionService, WorldModelSnapshot, EnvironmentSelfModel, DiscernmentFrameService, CommonSenseEngine, CapabilityDescriptor, ToolRegistry, CapabilityReadiness, PortableContext y ControlMasterService.

Por tanto, el gap verdadero no es percepción cero. El gap es la ausencia de una semántica general demostrada que transforme piezas heterogéneas observadas en entidades, relaciones, estados y capacidades reutilizables entre contextos.

## 3. PRINCIPIO DE UNIVERSALIDAD

Arquitectura objetivo:
platform-specific observer/driver → canonical observation → platform-agnostic semantic reasoning → verified state/relations/capabilities → generic decision/action

Se permiten adaptadores específicos para Windows UI Automation, Win32, macOS Accessibility, Linux accessibility, Chrome/Edge/Firefox/CDP, APIs, CLI, MCP y otros mecanismos.

La capa universal debe razonar sobre el significado funcional de la observación y no sobre el selector, botón, API o nombre del proveedor.

## 4. PRIMITIVAS SEMÁNTICAS PROPUESTAS

Estas son hipótesis de representación, no autorización para crear nuevas clases.

ENTITY CANDIDATE: identidad candidata, tipo hipotético, atributos, procedencia, confianza, estado epistemológico y alcance temporal.

RELATION HYPOTHESIS: entidad origen, relación, entidad destino, referencias de evidencia, confianza, estado epistemológico y alcance temporal.

STATE OBSERVATION: sujeto, propiedad, valor, fuente, instante, confianza y evidencia.

CAPABILITY EVIDENCE: sujeto o canal, capacidad, condiciones, evidencia, confianza y vigencia.

Ejemplos de conceptos que deben poder aparecer sin convertirlos en clases de proveedor:
human, email, digital_identity, account, organization, credential, browser_profile, browser_session, access_channel, provider, API, tool, resource, capability, permission, operation, task, constraint, evidence.

Relaciones candidatas:
identifies, associated_with, belongs_to, member_of, authenticates, provides_channel_to, hosts_session_for, enables, requires, permits, constrained_by, observed_in, derived_from, supports, contradicts, caused.

## 5. ALGORITMO UNIVERSAL DE ENTORNO UER-0

1. PERCEIVE — recoger señales de navegador, API, sistema operativo, procesos, archivos, UI, red y herramientas usando los órganos existentes.

2. NORMALIZE — convertir observaciones heterogéneas en señales semánticas comunes.

3. IDENTIFY — producir candidatos de entidades y roles; preguntar qué puede ser el objeto y qué atributos lo distinguen.

4. RELATE — generar hipótesis sobre cómo se conectan entidades observadas.

5. DISAMBIGUATE — conservar hipótesis alternativas cuando una sola observación no basta.

6. VERIFY — buscar la observación mínima que separe las hipótesis; usar fuentes independientes, comportamiento, estados antes/después y trazas persistentes.

7. MODEL — actualizar el estado ambiental, las relaciones y la confianza sin convertir inferencias en hechos.

8. DERIVE CAPABILITIES — inferir qué acciones son posibles dadas identidad, estado, permisos, canal, recursos y condiciones.

9. SELECT CHANNEL — objetivo → capacidad requerida → canales disponibles → adecuación del canal → autorización → acción.

10. ACT AND OBSERVE — tratar la acción como experimento y registrar el efecto real.

11. LEARN — actualizar relaciones, patrones, pesos, restricciones y propiedades del canal según el resultado.

12. REUSE — exigir que el conocimiento recuperado cambie una decisión posterior observable.

## 6. EJEMPLO: COMPRENDER UN LOGIN SIN CONOCER EL PROVEEDOR

Un sitio nuevo muestra texto de inicio de sesión, un campo de correo, un campo de contraseña y un botón de continuar.

IABV no debería necesitar saber de antemano el nombre del proveedor ni un selector concreto.

Debe poder razonar:
form visible → authentication_flow_candidate
campo email-like → identifier_input_candidate
campo password-like → secret_authentication_input_candidate
control de envío → authentication_operation_candidate
conjunto de evidencias → authentication_required_state_candidate

Después de una acción gobernada:
pre-state = unauthenticated or unknown
action = submit authentication proof
post-state = authenticated-session candidate

El estado posterior todavía no demuestra automáticamente identidad humana, cuenta permanente u organización. Es evidencia para hipótesis posteriores.

## 7. EMAIL NO ES LA IDENTIDAD

El sistema debe aprender que un email es una señal de identidad y no tratarlo como sinónimo de una sola cuenta.

Modelo general:
human ↔ digital_identity ↔ email
digital_identity ↔ account
account ↔ organization membership
credential ↔ principal/account/channel
browser_profile ↔ session/channel

Las relaciones pueden ser many-to-many.

Un humano puede tener múltiples emails, múltiples cuentas de distintas aplicaciones, múltiples organizaciones, múltiples credenciales, múltiples perfiles de navegador y múltiples sesiones.

El mismo email en dos aplicaciones no demuestra que exista una sola cuenta compartida. Puede corresponder al mismo humano pero a cuentas separadas, a identidades organizacionales o a contextos diferentes.

Por ello no deben imponerse las reglas email → exactamente una cuenta, cuenta → exactamente una credencial o browser profile → exactamente una identidad.

## 8. PERFIL, SESIÓN, CUENTA, CREDENCIAL Y CANAL

Browser profile = contexto persistente local.
Browser session = estado temporal de interacción.
Account = identidad o contexto de recursos del sistema externo.
Credential = material o evidencia usada para autenticar un principal.
Access channel = medio de acceso: browser, API, CLI, MCP, desktop app, proceso u otro.
Capability = acción efectiva disponible a través del canal bajo las condiciones actuales.

Estas categorías deben seguir separadas. Observar una sesión no concede autorización; descubrir una credencial no autoriza su uso; inferir una capacidad no sustituye la autorización.

## 9. MOVIMIENTOS DEL NAVEGADOR COMO SEMÁNTICA DE ACCIONES

El núcleo universal debe terminar pudiendo razonar sobre acciones como navigate, back, forward, refresh, open_tab, close_tab, switch_tab, switch_profile, click, type, select, submit, upload, download, copy, paste, sign_in, sign_out, switch_account, grant_permission, respond_to_security_challenge, observe_page, inspect_dom e inspect_accessibility.

El driver específico puede ejecutar un click DOM, una acción Playwright, CDP o UI Automation. La capa semántica debe expresar la intención funcional, por ejemplo perform authentication submission, switch account o enter identifier.

## 10. CÓMO APRENDER UN PROVEEDOR DESCONOCIDO

No debe requerirse una clase ProviderXAccount ni ProviderXLoginService para que IABV comprenda un proveedor nuevo.

El patrón deseado es:
observe → extract signals → generate concepts → compare known patterns → hypothesize → act only when authorized → observe transition → verify → retain semantic knowledge.

El conocimiento específico de un proveedor debe poder emerger como especialización empírica del mecanismo general, no como requisito previo del mecanismo.

## 11. CROSS-DEVICE Y CROSS-OS

Windows observer ┐
macOS observer  ├→ canonical observations
Linux observer   ┤
browser/CDP      ┤
API/CLI/MCP       ┘
                  ↓
            same semantic reasoning loop

Cambiar de sistema operativo debe exigir principalmente nuevos adaptadores de observación/acción, no una nueva teoría de identidad, login, cuenta, capacidad o selección.

## 12. MAPA DE ÓRGANOS EXISTENTES

Perception: UniversalPerceptionService, account_resource_scanner, browser/session scanners, PerceptionCrossValidator.
Environment: EnvironmentSelfAwarenessService, EnvironmentSelfModel, WorldModelService, WorldModelSnapshot.
Discernment: DiscernmentFrameService, CommonSenseEngine, OSES.
Action/capability: ToolRegistry, ToolCard, CapabilityDescriptor, CapabilityReadinessService, InteractionModeSelector, ToolTeachService, adapters.
Context: TaskContextAssembler, PortableContext, ControlMasterService.
Learning/development: ExperimentLab, TaskOutcomeRecorder, StrategySelector, AdaptiveWeightLayer, AutonomousEvolutionService, EvolutionBacklog.
Security: CredentialBroker, SecretVault, SecretReference, ExternalActionAuthorization.

La deducción actual es que estas piezas forman un sustrato distribuido. El problema abierto es cómo sus observaciones se convierten en conocimiento semántico relacional reusable y causalmente útil para decisiones posteriores.

## 13. INTERPRETACIÓN DE M1.1

DevinAccount y DevinCredential deben tratarse provisionalmente como provider-specific projection / scaffolding / case study.

No deben refactorizarse solo para satisfacer la idea de universalidad. Primero debe identificarse el seam semántico mínimo que falta y comprobar si ya puede componerse con modelos existentes.

## 14. FIRST OPEN CAUSAL EDGE

normalized observation
→ candidate entity/relation/state
→ verified reusable semantic knowledge
→ capability/affordance inference
→ existing decision use

El punto crítico no es crear un nuevo registro de cuentas. Es cerrar la transformación genérica entre observación e interpretación relacional, y después demostrar que esa interpretación llega a una decisión real.

## 15. EXPERIMENTO MÍNIMO DISCRIMINANTE

Usar una aplicación web desconocida y controlada.

1. Observar DOM, texto, controles, URL/título y contexto de navegador.
2. Inferir login/authentication, identifier input, secret input, submit y account-switch cuando la evidencia lo permita.
3. Contrastar con una segunda fuente independiente cuando esté disponible.
4. Bajo autorización, ejecutar el paso de autenticación.
5. Observar el cambio antes/después y distinguir sesión autenticada de identidad permanente.
6. Repetir el mismo experimento semántico en una segunda aplicación no relacionada.

Éxito: el mismo mecanismo semántico resuelve ambos casos sin requerir nuevas clases cognitivas por proveedor.

Fallo: la interpretación necesita nombres de proveedor, selectores específicos o reglas uno-a-uno codificadas en el núcleo semántico.

## 16. KNOWLEDGE DELTA

ΔK: la frontera universal relevante es observation → semantic entity/relation/state hypothesis → verified reusable knowledge.

Δπ: antes de crear una pieza específica de proveedor, buscar qué órganos existentes ya observan la señal y qué transformación semántica falta para hacerla reusable.

ΔB: IABV debe tender a razonar desde observaciones, relaciones plausibles, incertidumbre y experimentos discriminantes, no desde un catálogo de recetas.

ΔY: la prueba fuerte será que el mismo razonamiento transfiera entre proveedores, aplicaciones, navegadores, sistemas operativos, dispositivos y canales sin crecimiento proporcional del código específico ni de la coordinación humana rutinaria.

## 17. REGLAS DE NO AUTOENGAÑO

fact ≠ inference ≠ assumption
observation ≠ interpretation
relation hypothesis ≠ verified relation
inventory ≠ identity graph
email ≠ account
account ≠ identity
credential ≠ channel
session ≠ account
capability ≠ permission
availability ≠ suitability
persistence ≠ learning
learning ≠ future decision influence

DECLARED STATE ≠ OBSERVED STATE ≠ EFFECTIVE STATE
DEFINED ≠ WIRED ≠ INVOKED ≠ OBSERVED ≠ CAUSED

## 18. NON-IMPLEMENTATION RULE

Este documento no autoriza un UniversalMind, una ontología gigante, otro router central, otra memoria, otro registro de cuentas ni automatización masiva de login.

Primero debe realizarse arqueología de contratos y consumidores para determinar si las estructuras existentes ya pueden expresar las primitivas semánticas mínimas.

## 19. RELACIÓN CON BIOSOFÍA ARTIFICIAL

Esta línea es un sustrato de la tesis de desarrollo: SENSE → REPRESENT → ASSESS → IDENTIFY DEFICIT → HYPOTHESIZE → VARIATE → SANDBOX → VERIFY → SELECT → CONSTRUCT → ENCODE LINEAGE → RELOAD → REUSE → ADAPT → REPEAT.

Sin una forma general de comprender el entorno, la transferencia de capacidades entre entornos queda limitada por conocimiento específico previamente programado.

Por tanto, el aprendizaje de semánticas ambientales es una hipótesis de sustrato para portabilidad, selección de canales, metacognición y desarrollo generalizable.

## 20. MAXIMUM VALID CLAIM

OBSERVATION SUBSTRATE = PRESENT
ACCOUNT/BROWSER INVENTORY = PRESENT
WEB CONCEPT NORMALIZATION = PRESENT
ENVIRONMENT SELF-MODEL = PRESENT
DISCERNMENT / EVIDENCE REASONING = PRESENT
GENERIC CAPABILITY CONCEPTS = PARTIAL
GENERAL ENTITY/RELATION SEMANTICS = NOT PROVEN
CROSS-DOMAIN RELATION MEMORY = NOT PROVEN
OBSERVATION → RELATION → DECISION CAUSE = NOT PROVEN
CROSS-OS SEMANTIC GENERALIZATION = NOT PROVEN
UNFAMILIAR-PROVIDER SELF-GENERATION = NOT PROVEN

## 21. RETRIEVAL / CHAT CONTINUITY

Activar este documento cuando el objetivo toque universal algorithms, environmental understanding, browser cognition, login/account semantics, identity inference, cross-provider reasoning, cross-device portability, cross-OS portability, access-channel selection, semantic generalization, metacognitive environmental modeling o biosofía artificial development.

Relacionarlo con 00-GLOBAL-DEVELOPMENT-NORTH-STAR-2026-09-21.md, BIOSOFIA-ARTIFICIAL-DEVELOPMENTAL-AUTOPOIETIC-THESIS-2026-09-21.md, MEMORY-OPERATING-PROTOCOL.md, CONTEXT-INDEX.md, UNRESOLVED-KNOWLEDGE.md, SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md y EXPECTATION-MODEL-ARCHAEOLOGY-2026-09-12.md.

## 22. CORE PRINCIPLE

DO NOT TEACH EVERY OBJECT.
TEACH THE SYSTEM HOW TO DISCOVER WHAT OBJECTS, RELATIONS, STATES, CAPABILITIES AND TRANSITIONS MEAN.

DO NOT MAKE EVERY ENVIRONMENT IDENTICAL.
MAKE THE REASONING METHOD TRANSFERABLE BETWEEN ENVIRONMENTS.