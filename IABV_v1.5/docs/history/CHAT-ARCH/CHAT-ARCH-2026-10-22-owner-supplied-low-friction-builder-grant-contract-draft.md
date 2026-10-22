# Owner-supplied draft — low-friction governed development-access contract

**Provenance:** original draft pasted by the Owner into the ChatGPT conversation on 2026-10-22 and attributed by the Owner to the Codex session. Preserved here so the independent reviewer can inspect the actual artifact rather than a coordinator summary.

**Evidence classification:** OWNER_SUPPLIED_CODEX_DRAFT. Archiving this content does not independently verify the originating model/session or any implementation/capability. This is a documentary proposal only.

---

# Borrador: contrato de acceso de desarrollo amplio y gobernado

`DESIGN_VERDICT=PASS_WITH_REPAIRS`

El contrato puede dar acceso de trabajo amplio dentro de una candidata aislada, sin pedir autorización por archivo. Sigue siendo **un diseño**, no una capacidad disponible ni una autorización para leer el checkout actual. Faltan decisiones de autoridad y una implementación verificable; por eso no resuelve M1.

## Base documental y límites de evidencia

La revisión de la continuidad pública en `main` usó el commit `45043acf61871d55822c4a140a8da5ba9c51e043`. Allí se registra que la superficie de Codex reportada por el Owner no encontró una ruta de sesión aplicable, pero que la existencia de una ruta global permanece `UNRESOLVED`. La continuidad también exige mantener separados el acceso técnico y la autorización, y conservar los gates actuales. [CURRENT-STATE.md](https://github.com/jhonf463r/Python/blob/45043acf61871d55822c4a140a8da5ba9c51e043/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md), [seguimiento del inventario de gobernanza](https://github.com/jhonf463r/Python/blob/45043acf61871d55822c4a140a8da5ba9c51e043/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-governance-surface-inventory-followup.md).

La Entry 266 distingue el permiso de observación de ventanas de la autoridad para leer un repositorio. La Entry 274 propone controles para una lectura de repositorio, pero no demuestra que estén implementados ni concede acceso. Su alcance propuesto de rutas exactas no debe ampliarse silenciosamente para este diseño. [Entry 266](https://github.com/jhonf463r/Python/blob/500bd735fcf4c6f07ee64ee0b96abd79e01401ad/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-266-observation-approval-is-not-audit-release.md), [Entry 274](https://github.com/jhonf463r/Python/blob/500bd735fcf4c6f07ee64ee0b96abd79e01401ad/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md).

La adjudicación registrada en la incidencia #470 también deja sin resolver quién emite la autorización, quién resuelve un bloqueo y cómo se vinculan de manera confiable la sesión y el checkout. Advierte que la lista de seis archivos propuesta para la auditoría del gate no basta para auditar el puente completo. [Adjudicación de #470](https://github.com/jhonf463r/Python/issues/470#issuecomment-6331281066).

## Contrato propuesto

### 1. Identidades y responsabilidades

- **Owner:** decide si se habilita esta clase de acceso de desarrollo y aprueba su política. La identidad debe verificarse mediante un mecanismo confiable de la plataforma; una instrucción conversacional aislada no basta como prueba técnica de identidad.
- **Emisor de autorización:** servicio de confianza independiente del agente constructor y del IABV en ejecución. Emite y revoca grants. Su identidad y el mecanismo de verificación todavía no están identificados.
- **Agente constructor:** trabaja únicamente bajo un grant vigente y ligado a su identidad, tarea y candidata. No puede emitir, ampliar ni liberarse su propio grant.
- **Autoridad del bloqueo operativo:** resuelve por separado los bloqueos que le corresponden. No está identificada en la evidencia disponible.
- **Enforcer y registro:** hacen cumplir el alcance en las operaciones y conservan recibos durables. Su existencia y contrato actuales no están demostrados.

### 2. Grant de sesión de desarrollo

Un grant debe quedar ligado a:

- Identidad verificada del Owner y del agente.
- Identificador del repositorio y commit de origen.
- Identidad estable de una **candidata desechable y aislada**, creada o registrada mediante un mecanismo confiable.
- Raíz del candidato comprobada por identidad del sistema de archivos, no solo por una ruta textual.
- Tarea, capacidades autorizadas, política aplicada, comienzo, expiración y mecanismo de revocación.

El grant cubre las operaciones ordinarias autorizadas durante la sesión completa. No se solicita permiso por cada archivo. El agente no puede extender la raíz, cambiar el candidato o usar el grant en otro checkout; esos cambios requieren una decisión nueva.

**Condición de compatibilidad:** Entry 274 propone rutas exactas sin comodines para el lector de repositorio. El grant de construcción aquí descrito sería una **clase de autorización distinta**, delimitada por una candidata aislada y fronteras del sistema de archivos. No debe implementarse como una ampliación implícita del lector de Entry 274. El Owner debe aprobar explícitamente esa clase y la frontera recursiva antes de implementarla.

### 3. Matriz de capacidades

| Capacidad                                                                | Alcance propuesto                                                                     | Autorización separada             |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- | --------------------------------- |
| Leer y escribir código fuente y documentación                            | Dentro de la candidata registrada y de las áreas de trabajo acordadas para esa sesión | Grant de desarrollo de sesión     |
| Leer o escribir fuera de la candidata                                    | Denegado                                                                              | Decisión nueva y específica       |
| Ejecutar pruebas                                                         | Comandos, entorno, duración, datos y efectos permitidos declarados                    | Grant separado de pruebas         |
| Compilar                                                                 | Herramientas, destinos de salida, red y límites declarados                            | Grant separado de build           |
| Ejecutar IABV, servicios, Codex CLI/App Server, Ollama o transporte real | Denegado por defecto                                                                  | Autorización específica adicional |
| Merge, publicación, despliegue o escritura externa                       | Denegado                                                                              | Autorización específica adicional |

Los grants de pruebas y build tampoco se obtienen por inferencia a partir del grant de lectura/escritura.

### 4. Exclusiones

El grant ordinario no permite leer, modificar ni utilizar:

- Secretos, credenciales, `.env` o archivos de autenticación.
- Datos reales, `data/`, SQLite o bases de producción.
- Configuración del sistema, seguridad del host, GPU, modelos o servicios.
- Procesos no incluidos en un grant separado.
- Efectos externos, red o proveedores.
- Merge, publicación, despliegue, transporte real o activación del puente.

La enforcement debe denegar estas categorías aunque estén bajo una ruta que, de otro modo, quedaría dentro de la candidata. La política concreta para excluirlas sin permitir evasiones por enlaces, rutas reparseadas o sustitución del candidato requiere especificación e implementación verificables.

### 5. Bloqueos operativos

La autorización del Owner para construir **no libera** un bloqueo operativo. Antes de cada operación, el enforcer evalúa ambos controles por separado:

1. ¿Está vigente el grant de desarrollo para esta identidad, candidata y capacidad?
2. ¿Existe un bloqueo operativo aplicable a esta operación y, si lo hay, una decisión válida de la autoridad independiente que lo resuelve?

Si la autoridad, el alcance del bloqueo o la decisión no pueden verificarse, se deniega. El agente, el lector y el IABV en ejecución no pueden modificar o autoaprobar ese estado.

El tratamiento efectivo de `operational_block_active` y de sus alcances no puede inferirse de las referencias públicas ni de la evidencia reportada. Si no hay mecanismo de resolución soportado, el resultado debe ser `BLOCK_RELEASE_UNSUPPORTED`, no un acceso alternativo.

### 6. Recibos y correlación

Como requisito propuesto, el registro durable debe vincular solicitud, decisión, sesión, candidato, operación y resultado. Debe contener:

- Identidad autenticada del emisor y del agente.
- Repositorio, commit de origen e identidad del candidato.
- Capacidades, exclusiones, vigencia, política y revocación.
- Para cada operación: tipo, objetivo, hora, resultado y código de denegación si corresponde.
- Para cambios: inventario y hashes pertinentes de los archivos afectados; para pruebas/builds autorizados, comando aprobado, estado de salida y resumen de resultados.
- Correlación mediante identificadores no reutilizables.

No debe registrar valores secretos ni depender únicamente de texto emitido por el agente. Una operación sin recibo durable o con identidad ambigua falla cerrada. El diseño y la evidencia pública no prueban que tal registro exista hoy.

### 7. Denegación y recuperación

Ante una denegación, el sistema informa qué capacidad falta, qué identidad o alcance no pudo verificar y si el impedimento es un bloqueo operativo. No busca otro lector ni convierte un permiso de observación en autorización de repositorio.

La ruta administrativa legítima debe ser una interfaz oficial del emisor o de la autoridad responsable, una vez identificada. Esa interfaz, sus operadores, el procedimiento de revocación y los recibos emitidos permanecen `UNRESOLVED`; no se inventan aquí.

## Componentes: evidencia frente a propuesta

| Elemento                                                                                 | Estado                                                             |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Permiso de observación de ventanas separado de lectura de repositorio                    | Documentado en Entry 266; no concede acceso al checkout            |
| Contrato de decisión y verificación para lecturas específicas                            | Propuesto en Entry 274; implementación no demostrada               |
| Inventario de sesión Codex sin ruta aplicable, según Owner                               | `OWNER_REPORTED`; no demuestra ausencia global                     |
| Grant amplio de construcción limitado a una candidata desechable                         | Propuesto en este borrador; no demostrado como capacidad existente |
| Emisor, verificador, diálogo, revocación, recibos y resolución independiente de bloqueos | Sin verificación; dependencias pendientes                          |
| Lectura del checkout local actual                                                        | `NOT_RUN`                                                          |

## Escenarios de fallo y aceptación propuesta

Todos los casos siguientes son **propuestas; no ejecutadas**:

1. El agente intenta emitirse o ampliarse su grant: denegación y recibo.
2. Identidad del agente, Owner, repositorio, commit o candidato no coincide: denegación antes de acceso.
3. Acceso ordinario a un archivo permitido dentro del candidato y grant vigente: permitido sin prompt por archivo y registrado.
4. Acceso a otro checkout, raíz sustituida o enlace que escape de la candidata: denegación.
5. Acceso a `.env`, secretos, `data/` o SQLite: denegación aunque la ruta textual parezca pertenecer al candidato.
6. Grant vencido o revocado: denegación en la siguiente operación.
7. Pruebas o build sin su grant específico: no se ejecutan.
8. Bloqueo operativo aplicable sin una resolución independiente verificable: denegación, sin que el grant de construcción lo altere.
9. Reinicio, error del registro o resultado de decisión ambiguo: fallo cerrado; no hay entrega de contenido ni continuación.
10. Merge, publicación, despliegue, proveedor externo o transporte real con solo el grant de desarrollo: denegación.

## Decisiones y dependencias administrativas abiertas

Antes de implementar, el Owner debe decidir:

- Si autoriza una clase de **grant de construcción de sesión**, separada de la lectura exacta de Entry 274.
- Qué candidato y límites de directorio puede abarcar ese grant y cómo se excluyen las categorías sensibles.
- Qué identidad autenticada puede emitir grants, quién controla esa autoridad y cómo se verifican emisión y revocación.
- Qué autoridad independiente posee cada bloqueo operativo y cómo se acredita su resolución.
- Qué grants separados se permitirían para pruebas y builds, con qué límites y efectos.

Además, falta identificar la interfaz administrativa soportada para solicitar esas decisiones. Su ausencia en las superficies consultadas no permite afirmar que no exista globalmente.

**Siguiente actor recomendado:** Owner/coordinador documental para decidir los límites y la autoridad confiable de esta nueva clase de grant; después, revisión adversarial del contrato antes de cualquier implementación. Esta recomendación no concede permisos ni inicia esa revisión.

```
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
```

**No se leyó ni modificó el checkout local y no se ejecutaron comandos, pruebas, builds, probes, servicios ni transporte.**
