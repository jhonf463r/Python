# Mente Espacio-Tiempo y campo de activación neuroinspirado — investigación y reconciliación de arquitectura

- Fecha: 2026-10-26, America/Bogota.
- Estado: RESEARCH_AND_DESIGN_RECONCILIATION; NOT_IMPLEMENTATION_AUTHORIZATION.
- Tarea: UAAL_SPACE_TIME_NEURAL_ACTIVATION_RESEARCH.
- Base examinada: main = cac98375e4e94547ddfa89b30acab6b24ca769e2.
- Rama: uaal-neural-activation-research-20261026.
- Método: revisión documental y lectura estática de fuentes públicas del repositorio; sin checkout local, IABV MCP ni datos protegidos.
- Pruebas, build y runtime ejecutados: ninguno.
- Cambios de producción: ninguno.
- Nuevo órgano, servicio, cerebro, almacén de memoria o ID UAAL: no propuesto ni asignado.
- Estado de autoridad M1A: G1/G2/G3 NOT_ESTABLISHED; ocho gates abiertos; protected reads FAIL_CLOSED.

## 1. Dictamen ejecutivo

La intuición del Owner corresponde a una hipótesis de ingeniería valiosa: una red distribuida de órganos de percepción, memoria, decisión, herramientas, IAs externas y auditoría debería activar selectivamente información pertinente a un objetivo; transmitirla con procedencia y contexto temporal; observar qué ocurrió; consolidar únicamente lo verificado; y usarlo para cambiar una decisión futura de manera medible.

**Conclusión principal:** IABV ya contiene el antecedente conceptual de esta idea. El documento Resonant Self-Knowledge Retrieval Fabric propone un potencial de activación que varía según el objetivo, expansión por relaciones tipadas, deduplicación, currentness y evidencia. UAAL-D014, D015, D018 y D019 cubren plasticidad del método, activación contextual dispersa, separación de etapas de ejecución/evidencia y control anti-loop. No sería correcto crear un “nuevo cerebro” o declarar una neuroplasticidad universal nueva sin reconciliar esos antecedentes.

En el código actual existen piezas de percepción, estado del mundo, orquestación adaptativa, ranking de herramientas/IA, registro de resultados, recomendaciones, pesos heurísticos, autoexamen y snapshot del organismo. El hueco no es la mera ausencia de órganos: falta demostrar el lazo completo entre productor, consumidor, contrato, secuencia temporal, decisión, outcome y reutilización causal.

La metáfora de potencial de acción es útil para diseñar activación, inhibición y plasticidad. No prueba que IABV o varias IAs constituyan literalmente una red neuronal biológica ni que haya conciencia subjetiva. En esta investigación “Mente Espacio-Tiempo” significa continuidad verificable de objetivo, procedencia, tiempo, estado y causalidad.

Referencias canónicas existentes:
- [Resonant Self-Knowledge Retrieval Fabric](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-30-001-resonant-self-knowledge-retrieval-fabric.md).
- [Metacognitive Deduction / Temporal-Causal Synthesis](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/METACOGNITIVE-DEDUCTION-2026-09-12.md).
- [UAAL-D019 — Space-Time Anti-Loop and First-Open Causal Frontier](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-26-UAAL-D019-SPACE-TIME-ANTI-LOOP-CAUSAL-FRONTIER.md).
- [Systemic Integrity & Connectivity](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md).
- [Shared Developmental Knowledge Field](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-03-007-shared-developmental-knowledge-field.md).
- [Universal Experimental Reality Loop](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/UNIVERSAL-EXPERIMENTAL-REALITY-LOOP-2026-09-26.md).

## 2. Límite científico de la analogía

### 2.1 Biología demostrada

El potencial de acción es una transición electroquímica dependiente de canales de membrana, no una simple notificación digital. Tras un impulso, la inactivación de canales de sodio y la actividad de canales de potasio producen un período refractario que limita temporalmente nuevos disparos y ayuda a impedir la propagación retrógrada. La conducción depende de propiedades axonales como diámetro y mielinización. La plasticidad sináptica abarca reglas diversas; no existe una única regla sencilla que explique toda la adaptación neuronal. Fuentes introductorias y de revisión: [The Refractory Period, NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK11146/), [Physiology, Action Potential, NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK538143/) y [The physics of brain network structure, function and control, Nature Reviews Physics](https://www.nature.com/articles/s42254-019-0040-8).

### 2.2 Traducción computacional admisible

| Idea biológica | Equivalente de ingeniería posible | Límite |
|---|---|---|
| Umbral de excitabilidad | Compuerta de admisibilidad y relevancia antes de activar un nodo. | La similitud semántica no puede sustituir evidencia o autorización. |
| Disparo y propagación | Transición de estado tipada y propagación de contexto por relaciones productor-consumidor. | Un evento se puede retrasar, perder, duplicar o rechazar. |
| Período refractario | Idempotencia, límite de reintentos, enfriamiento y huella anti-loop. | No bloquear tareas distintas por compartir vocabulario. |
| Plasticidad sináptica | Cambiar una recomendación o relación solo después de outcome verificado y comparación con predicción. | Recuperar o repetir un dato no equivale a aprender. |
| Inhibición | Evidencia negativa, contradicciones y reglas que detienen propagación. | No borrar contradicciones ni convertir UNKNOWN en FALSE. |
| Homeostasis | Presupuestos de activación, carga, latencia y diversidad de rutas. | La disponibilidad de recursos no es autoridad. |
| Consolidación | Resumir episodios en conocimiento versionado con fuentes, vigencia y contraejemplos. | Persistencia no prueba influencia sobre una decisión. |

Los sistemas de varias IAs y procesos funcionan como sistemas distribuidos: no siempre existe un orden total que pueda inferirse solo de horas de reloj. Lamport formalizó la relación parcial “happened-before” y los relojes lógicos para razonar sobre el orden de eventos distribuidos. Por ello, el espacio-tiempo operativo de IABV requiere IDs de causalidad, estado de productor/consumidor y resultados; no basta un timestamp. Fuente: [Lamport, Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.azurewebsites.net/pubs/time-clocks.pdf).

## 3. Reconciliación del algoritmo existente en IABV

### 3.1 El lazo UAAL ya es la base conceptual

La constitución del Universal Adaptive Algorithm define el siguiente ciclo independiente del dominio:

~~~text
OBJECTIVE
→ PERCEIVE
→ REPRESENT
→ INTERPRET
→ MAINTAIN UNCERTAINTY
→ INFER REQUIRED CAPABILITY
→ DISCOVER CANDIDATE REALIZATIONS
→ CHECK CONSTRAINTS, ACCESS AND RESOURCES
→ SELECT
→ GOVERN
→ ACT
→ OBSERVE TRANSITION
→ VERIFY
→ UPDATE WORLD / SELF MODEL
→ STORE REUSABLE KNOWLEDGE
→ REUSE
→ ADAPT
→ NEXT DECISION
~~~

La maduración pasa por estados distintos: IDEA → HYPOTHESIS → DESIGN → IMPLEMENTATION → WIRED → INVOKED → OBSERVED → VERIFIED → EFFECTIVE → CAUSAL → REUSABLE → DEVELOPMENTAL. Cada paso necesita evidencia propia. Un diseño documentado no prueba que el código esté cableado, ejecutado, sea eficaz o produzca aprendizaje reutilizable. Véase [Universal Adaptive Algorithm Constitution](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/docs/history/CHAT-ARCH/UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md).

El linaje ya incluye Knowledge Plasticity (D008), Meta-Method Plasticity / Failure-to-Evolution Loop (D014), Capability Preservation and Context-Gated Sparse Activation (D015), Governed Self-Code Evolution (D016), Execution-to-Evidence Stage Separation (D018) y Space-Time Anti-Loop (D019). La recomendación es refinar su composición y medirla, no asignar ahora un nuevo concepto UAAL.

### 3.2 Órganos existentes y su rol real en fuente

Esta tabla es una reconciliación estática de código en main; no es una afirmación de runtime efectivo.

| Órgano/ruta | Hecho encontrado | Lo que no demuestra |
|---|---|---|
| UniversalPerceptionService, PerceptionSnapshot, TaskContextAssembler, PerceptionCrossValidator | Contratos de señales y composición de contexto para decisión. | Que toda señal relevante llegue a tiempo y afecte de manera demostrable la decisión. |
| WorldModelService | Snapshot de ventanas, herramientas, red y bloqueos; escaneo ligero por defecto de 45 s y completo por defecto de 180 s. | Propagación instantánea de cada cambio como evento causal. |
| EnvironmentSelfAwarenessService | Observación de hardware, runtime, proveedores, capacidades y riesgos, con persistencia. | Un juicio universal y correlacionado de salud de cada relación entre órganos. |
| AdaptiveTaskOrchestrator | Clasifica intención, construye percepción, consulta SynapticRouter para ciertos tipos de tarea, añade presión de recursos y sync pulse, evalúa capacidades, selecciona estrategia/plan y gates, crea sesión y registra el resultado después. | Que sea una red de impulsos spiking o que todas las decisiones se recalculen después de recibir contexto de objetivo completo. |
| SynapticRouter PCS v1 | Ranking descriptivo con ajuste de capacidades, historial adaptativo y disponibilidad del WorldModel. Fórmula actual: 0.5 × fit + 0.3 × adaptive weight + 0.2 × availability. | Potenciales de acción biológicos, propagación general de memoria o entrenamiento neuronal por gradiente. Su contrato dice que es descriptivo y que LocalRoleRouter decide operativamente. |
| ExperimentLab + StrategySelector | Persiste ExperimentRuns, puntajes y recomendaciones por ruta/asistente/configuración. | Que una recomendación sea una predicción causal calibrada. |
| TaskOutcomeRecorder | En la ruta de finalización enlazada a RunRecord, recoge resumen observado, datos de predicción previa, métricas y evidencia, y pide nueva recomendación a ExperimentLab. | Que cada resultado esté verificado independientemente o cambie la decisión posterior de manera causal. |
| AdaptiveWeightLayer | Calcula perfiles heurísticos por historia: muestra, éxito/fallo, bloqueos, fallback, reutilización, recencia, tendencia y latencia. | Que sean pesos de una red neuronal biológica o entrenamiento del modelo base. |
| RuntimeAuditTracer + DecisionAuditTrail | Registran eventos, tiempos y decisiones. | Una unión universal entre productor, consumidor, contrato, orden causal y outcome. |
| OSES | Analiza findings, degradación, recurrencia y anomalías temporales; sugiere ajustes. | Que el autorreporte de salud esté completo, fresco y verificado externamente. |
| OrganismStateSnapshot | Composición de solo lectura de self-examination, WorldModel, ControlMaster, aprendizaje operacional y datos sin resolver. | Un decisor universal ni un contrato de salud implementado por cada clase. |
| AutonomyCycleService | Conecta hallazgos OSES a una cola, guarda resume hints y resume tareas/capacidades. | Que una respuesta externa haya sido recibida, usada y verificada en una tarea siguiente. |
| PortableContextService y SessionStartBriefingService | Construyen paquetes de continuidad y ofrecen transporte condicionado por adaptador. | Entrega universal a ChatGPT/Codex/Claude, recepción confirmada ni influencia en una decisión posterior. |

Referencias de fuente:
- [AdaptiveTaskOrchestrator](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py).
- [SynapticRouter](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/roles/synaptic_router.py).
- [TaskOutcomeRecorder](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/adaptive/task_outcome_recorder.py).
- [ExperimentLab](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/lab/experiment_lab.py).
- [AdaptiveWeightLayer](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_weight_layer.py).
- [WorldModelService](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py).
- [Organism State Snapshot](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/evolution/organism_state_snapshot.py).
- [MCP PortableContext handler](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/infra/mcp/server.py).

El repositorio contiene además un modelo Keras/TensorFlow en el subárbol WPlay, asociado a selección DQN/PPO para su dominio específico de apuestas/ruleta. La revisión estática no encontró evidencia de que esa red sea el núcleo de continuidad universal ni la red de memoria compartida entre IAs. No debe utilizarse como prueba de que el campo espacio-tiempo esté implementado en el núcleo IABV.

### 3.3 Riesgos estáticos que afectan a la activación temporal

Estos puntos proceden de la fuente actual y deben conservar su estado de riesgo, no llamarse fallos de runtime sin una prueba:

1. **Frescura de PortableContext.** Cuando el handler no recibe refresh, eleva el máximo efectivo de edad al menos a 86,400 segundos y prefiere el paquete rico persistido si reconstruir sin contexto activo generaría secciones vacías. Protege información útil, pero permite devolver un paquete antiguo sin un veredicto explícito de edad, stale/degraded o binding con el objetivo en la respuesta. Esto no prueba que el paquete runtime actual sea viejo. Fuente: [portable_context_get en server.py](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/infra/mcp/server.py#L724-L765).
2. **Objetivo adjuntado después de decisiones iniciales.** En el flujo de AdaptiveTaskOrchestrator se construye el snapshot de percepción; luego se evalúan capacidad, paquete de estrategia, playbook y gates. El GoalEngine adjunta el contexto de objetivo más adelante y actualiza algunos campos de percepción. La duda es si ciertas decisiones tempranas ya consumieron contexto incompleto; el efecto requiere prueba. Fuente: [flujo handle_request en adaptive_task_orchestrator.py](https://github.com/jhonf463r/Python/blob/cac98375e4e94547ddfa89b30acab6b24ca769e2/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L1482-L1645). La continuidad previa relaciona este tipo de riesgo con RQ13; debe reutilizarse su evidencia terminal antes de reabrirlo.

## 4. La frontera real: relaciones causales verificables

La auditoría de integridad de IABV encontró muchos órganos y conexiones reales, pero no una capacidad general demostrada que una continuamente:
- productor y consumidor;
- referencia de fuente y revisión exacta;
- contrato semántico;
- orden temporal y lifecycle;
- acción y resultado observado;
- uso posterior y efecto causal.

Por eso el sistema puede conocer datos y aun no saber si la señal correcta llegó al consumidor correcto, si el paquete enviado fue el mismo que se recibió o si la lección realmente alteró una acción futura. Ésta es una frontera verificable; “red neuronal hiperconectada” no es una prueba.

El campo de conocimiento compartido ya exige experiencia verificada → conocimiento persistente → cambio en selección futura. El protocolo Space-Time requiere observación, procedencia, lección causal, decisión autorizada, outcome, writeback, fetch-back y reutilización posterior. La nueva investigación debe probar ese vínculo y no duplicar los órganos existentes.

## 5. Hipótesis y falsación

**H-RSF — hipótesis refinada del campo de activación resonante:** si IABV compone memoria, código, relaciones, estado temporal, herramientas, experimentos y evidencia mediante activación dispersa condicionada por el objetivo, y si cada relación activada conserva procedencia, estado epistemológico y relación causal, entonces podría reducir el tiempo para hallar la primera frontera causal abierta y disminuir la reutilización de conocimiento obsoleto o irrelevante. Solo podrá afirmarse aprendizaje evolutivo si una tarea posterior no idéntica recupera la lección, cambia una decisión y produce un efecto independientemente verificable.

Hipótesis auxiliares:
- H1: la activación objetiva mejora precision/recall frente al baseline de retrieval y navegación actual.
- H2: procedencia/currentness impide que información vieja supere una fuente actual contradictoria.
- H3: unir productor-consumidor-decisión-outcome reduce falsos positivos de “enviado”, “recibido”, “funcionó” y “aprendido”.
- H4: la huella experimental evita repetir un intento terminal sin cambio material.
- H5: contratos de autorreporte ayudan a detectar dependencias degradadas si UNKNOWN no se confunde con HEALTHY.
- H6: un Knowledge Delta verificado aparece en una tarea posterior relevante y cambia la decisión de forma observable.

Falsadores:
- la activación no mejora retrieval contra baseline;
- el ranking premia duplicados o documentos stale;
- no se puede confirmar el consumo del contexto o la decisión posterior no cita la lección;
- el cambio observado no se diferencia de otras causas;
- un mismo intento terminal se repite con misma huella y mismas precondiciones sin controlarlo;
- una ruta gana peso solo por ser repetida pese a resultados inciertos o negativos;
- un autoreporte muestra healthy cuando las fuentes no se observaron o no están frescas.

“Todo está hiperconectado” no es una conclusión aceptable sin prueba de recorrido real.

## 6. Especificación de activación consciente de evidencia

El documento de activación ya propone el potencial conceptual:

~~~text
R(q,n) = f(L,S,G,E,T,H,C,D)

L = relevancia léxica
S = similitud semántica
G = proximidad de grafo y fuerza de relación
E = adecuación de evidencia para la afirmación solicitada
T = actualidad frente a rama/runtime/objetivo
H = utilidad histórica verificada en tareas similares
C = ajuste a la capacidad requerida
D = penalización por duplicación, obsolescencia y conflicto
~~~

Los pesos no están fijados ni autorizados. La regla central es que similitud no puede dominar evidencia, estructura y actualidad.

### 6.1 Compuerta de admisibilidad separada del ranking

Primero se comprueba si un nodo es admisible como evidencia; luego se puntúa su relevancia. El score no es autoridad.

~~~text
admissible(node, query) =
    known_provenance(node)
    AND source_revision_scoped(node, query)
    AND evidence_status_not_refuted(node)
    AND freshness_satisfied(node, query)
    AND access_policy_allows_operation(node, query)
~~~

Si una condición obligatoria es UNKNOWN, el nodo no puede promoverse como verdad confirmada. Puede conservarse como pista o hipótesis etiquetada. La activación nunca fabrica permiso.

### 6.2 Expansión limitada por relaciones tipadas

~~~text
activate(query, existing_indexes, budget, policy):
    seed_candidates = retrieve_candidates_from_existing_sources(query)
    seeds = canonicalize_exact_identity_duplicates_only(seed_candidates)

    candidate_records = {}  # all known candidates, including unresolved leads
    activated_ids = set()
    best_score = {}
    provenance = {}          # distinct source and typed-edge references per candidate
    expanded = set()         # controls traversal, never erases incoming routes
    frontier = priority_queue(order=(-score, stable_candidate_id))
    blocked_or_deferred = []
    examined_relations = set()
    spent_nodes = 0
    spent_relations = 0

    for seed in sort_seeds_deterministically(seeds):
        candidate_records[seed.id] = retain_candidate_and_all_source_refs(seed)
        provenance[seed.id] = all_distinct_source_refs(seed)
        best_score[seed.id] = objective_conditioned_activation_score(
            query, seed, source_evidence, currentness, capability_fit
        )
        if not admissible(seed, query):
            record_block(seed, "inadmissible_or_unresolved")
            continue  # retained as a lead/hypothesis; not promoted as truth
        if cost(seed) exceeds remaining_node_budget(spent_nodes, budget):
            record_deferred_candidate(seed, "node_budget_exhausted")
            continue
        activated_ids.add(seed.id)
        spent_nodes += cost(seed)
        enqueue(frontier, seed, best_score[seed.id])

    while frontier not empty and budget_allows(spent_nodes, spent_relations, budget):
        node = pop_best_with_stable_tie_break(frontier)

        if node.id in expanded:
            continue
        if not admissible(node, query):
            record_block(node, "inadmissible_or_unresolved")
            continue

        expanded.add(node.id)
        record_why_activated(node, best_score[node.id], provenance[node.id])

        for edge in sort_by_canonical_relation_identity(
                typed_relevant_relations(node, query)):
            relation_id = canonical_relation_identity(
                edge.source_id, edge.target_id, edge.type,
                edge.source_reference, edge.source_revision
            )
            if relation_id in examined_relations:
                continue
            if relation_budget_exhausted(spent_relations, budget):
                record_deferred_relation(edge, "relation_budget_exhausted")
                break

            examined_relations.add(relation_id)
            spent_relations += cost(edge)
            neighbor = resolve(edge.target)

            if neighbor is unresolved:
                record_unresolved_relation(edge, "target_unresolved")
                continue
            if policy_requires_scope_gate(neighbor) and not policy.permits(neighbor):
                record_blocked_relation(edge, neighbor, "scope_or_authority")
                continue

            candidate_score = objective_conditioned_activation_score(
                query, neighbor, edge, evidence, currentness,
                verified_historical_utility, capability_fit,
                duplicate_stale_conflict_penalty
            )

            was_known = neighbor.id in candidate_records
            if not was_known:
                candidate_records[neighbor.id] = retain_candidate(neighbor)
                best_score[neighbor.id] = candidate_score
                provenance[neighbor.id] = set()
            elif rank_policy_is_strictly_better(candidate_score, best_score[neighbor.id]):
                best_score[neighbor.id] = candidate_score
            else:
                record_alternate_route(neighbor.id, relation_id, candidate_score)

            # Crucial: preserve the incoming route before any active/expanded check.
            provenance.setdefault(neighbor.id, set()).add(relation_id)

            if neighbor.id in activated_ids:
                # A visited/expanded node still accumulates distinct route provenance.
                # Node cost is charged once; route count is not a ranking bonus.
                continue

            if not admissible(neighbor, query):
                record_block(neighbor, "inadmissible_or_unresolved")
                continue
            if cost(neighbor) exceeds remaining_node_budget(spent_nodes, budget):
                record_deferred_candidate(neighbor, "node_budget_exhausted")
                continue

            activated_ids.add(neighbor.id)
            spent_nodes += cost(neighbor)
            update_or_enqueue(frontier, neighbor, best_score[neighbor.id])

    return evidence_aware_activation_packet(
        query,
        candidate_records,
        activated_ids,
        best_score,
        all_unique_provenance=provenance,
        blocked_and_deferred=blocked_or_deferred,
        not_expanded=active_ids - expanded,
        pending_frontier=stable_candidate_ids(frontier),
        budget_coverage=coverage_status(spent_nodes, spent_relations, budget)
    )
~~~

La semántica conservadora de esta primera versión es deliberada: la puntuación de un nodo es la mejor puntuación admisible de una ruta individual; las demás rutas relevantes se conservan en su procedencia, pero no suman votos ni refuerzan el ranking por mera repetición. Una evidencia verdaderamente independiente solo puede mejorar el componente de evidencia si su independencia, alcance y vigencia se evalúan explícitamente. La expansión de un nodo se realiza una vez porque su salida depende del objetivo y de sus propias relaciones, no de la ruta por la que fue descubierto; si en el futuro se decide un score dependiente de caminos, se necesitará otra regla de propagación y un test anti-ciclo separado.

La deduplicación del nodo y la deduplicación de evidencia son operaciones distintas. Un candidato canónico puede mostrarse una vez y conservar múltiples referencias de origen; versiones diferentes, afirmaciones distintas o contradicciones no se fusionan por similitud semántica. Si no existe una identidad estable suficiente, se etiqueta POTENTIAL_DUPLICATE y se conserva por separado hasta resolver la identidad.

El paquete debe informar si la cobertura fue completa o truncada por presupuesto, las relaciones no evaluadas y la razón de cada bloqueo. Los ordenamientos de nodos y relaciones requieren desempates estables. La prueba estática/diseño debe comprobar que permutar el orden de relaciones equivalentes no cambia el ranking ni la procedencia cuando el presupuesto permite recorrer el mismo vecindario. Bajo presupuesto agotado, la salida debe declarar cobertura incompleta, nunca aparentar una exploración exhaustiva.

Este pseudocódigo es una especificación de diseño, no una instrucción para crear un servicio nuevo. La primera prueba debe componer los índices y fuentes existentes: CONTEXT-INDEX, protocolo de memoria, búsqueda lexical disponible, self-code analysis, capability/tool registries, experiment records, world/self models, unresolved knowledge y evidencia de procedencia.

No hay pesos numéricos aprobados para esta hipótesis. Top-k, profundidad, presupuesto, recencia por tipo de fuente y reglas de contradicción deben calibrarse contra una suite baseline.

### 6.3 Período refractario informático mediante UAAL-D019

La analogía se implementa como idempotencia y control de repetición:
- crear huella del experimento usando objetivo/criterio, destino/revisión, entradas, actor/ruta, precondiciones/autorización, entorno, resultado esperado y condición de parada;
- vincular la huella al recibo terminal y al estado observado de las precondiciones;
- si objetivo/huella/precondiciones son iguales y el resultado es terminal, clasificar SAME_EXPERIMENT y detener reintentos automáticos;
- reabrir solo con un cambio material observado, otra hipótesis falsable, una categoría transitoria con retry limitado o una nueva autorización explícita;
- una nueva fecha, rama, chat o reformulación no es un cambio causal.

No suprimir tareas realmente distintas por similitud de palabras; la identidad de la huella incluye el objetivo y destino/alcance real.

## 7. Modelo temporal-causal de eventos

Reutilizar RuntimeAuditTracer, DecisionAuditTrail, TaskOutcome/RunRecords y los IDs de sesión donde sean adecuados antes de introducir un nuevo bus. La envolvente mínima debe poder describir:

~~~json
{
  "event_id": "unique-id",
  "event_type": "signal_emitted | context_selected | action_attempted | outcome_observed | knowledge_delta | reuse_verified",
  "schema_version": "typed-version",
  "producer": {
    "organ_id": "owner-of-event",
    "component_version": "exact-version",
    "source_ref": "path + revision + symbol"
  },
  "objective_id": "active-objective",
  "session_id": "correlation-scope",
  "trace_id": "cross-organ-trace",
  "parent_event_id": "direct-causal-parent-or-null",
  "causation_id": "cause-reference-or-null",
  "target_scope": {
    "repository": "repo-id",
    "branch": "branch",
    "commit": "sha",
    "runtime_fingerprint": "only-if-observed"
  },
  "time": {
    "observed_at_utc": "wall-clock-evidence",
    "process_sequence": 0,
    "monotonic_elapsed_ms": 0,
    "logical_order": "if-implemented"
  },
  "epistemic_status": "KNOWN | UNKNOWN | CONFLICTED | REFUTED",
  "stage_status": "actual-stage-specific-status",
  "evidence_refs": [],
  "freshness": {
    "age_seconds": 0,
    "currentness_status": "FRESH | STALE | UNKNOWN"
  },
  "authority": {
    "required": true,
    "decision_ref": "authoritative-reference-or-null",
    "permission_status": "NOT_REQUIRED | VERIFIED | BLOCKED | UNKNOWN"
  },
  "outcome": {
    "expected": "pre-action-expectation",
    "observed": "actual-observation-or-unknown",
    "verification_ref": "independent-check-or-null"
  }
}
~~~

No se debe asumir que timestamp o trace_id prueban causalidad. Los eventos de procesos distintos pueden estar concurrentes; la relación happened-before/parent/causation describe orden parcial y debe conservar lo desconocido. No registrar secretos ni contenido que el actor no estaba autorizado a leer.

El lifecycle debe separar:
~~~text
DISCOVERED / OBSERVED
→ CANDIDATE_ACTIVATED
→ CONTEXT_PACKAGED
→ DELIVERY_ATTEMPTED
→ DELIVERY_ACCEPTED or DELIVERY_UNAVAILABLE
→ RECEIPT_CONFIRMED or RECEIPT_UNVERIFIED
→ CONSUMED_CONFIRMED or CONSUMPTION_UNKNOWN
→ DECISION_CITES_KNOWLEDGE
→ ACTION_ATTEMPTED
→ RESULT_OBSERVED
→ RESULT_VERIFIED or RESULT_UNVERIFIED
→ KNOWLEDGE_DELTA_PROPOSED
→ CANONICAL_FETCH_BACK_VERIFIED
→ REUSED_IN_NONIDENTICAL_TASK
→ CAUSAL_EFFECT_VERIFIED
~~~

Cada etapa conserva su propio estado. Una respuesta del adapter solo confirma lo que el adaptador garantiza. OpenTelemetry documenta cómo traces, metrics, logs y context propagation correlacionan actividad distribuida sin convertir la telemetría en autoridad de negocio: [Signals](https://opentelemetry.io/docs/concepts/signals/), [Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/) y [Context specification](https://opentelemetry.io/docs/specs/otel/context/). Se propone reutilizar ese principio de correlación, no introducir una dependencia obligatoria nueva.

## 8. Plasticidad y consolidación: no confundir memoria con aprendizaje

El campo resonante ya separa diferentes efectos:
- ΔW: peso de ranking/retrieval;
- ΔM: estado de recuperación;
- ΔK: conocimiento semántico;
- ΔR: relación/topología;
- ΔC: contextualización;
- ΔD: decisión;
- ΔB: comportamiento;
- ΔO: resultado.

La regla de plasticidad debe ser:

~~~text
PREDICTION_BEFORE_ACTION
→ VERIFIED_OBSERVATION
→ COMPARE_PREDICTION_WITH_OUTCOME
→ CLASSIFY SUCCESS / FAILURE / BLOCKED / UNKNOWN
→ CHECK_EVIDENCE_AND_CONTRADICTIONS
→ PROPOSE_MINIMAL_KNOWLEDGE_OR_RELATION_DELTA
→ COUNTEREXAMPLE_AND_SCOPE_CHECK
→ GOVERNED_PROMOTION_OR_REJECTION
→ CANONICAL_WRITE_AND_FETCH_BACK
→ LATER_RETRIEVAL_IN_NONIDENTICAL_TASK
→ OBSERVE_CHANGED_DECISION_OR_ACTION
→ INDEPENDENTLY_VERIFY_EFFECT
~~~

No aumentar un score solo por repetición bruta. Un fallo de producto, una denegación de autorización, un timeout y una prueba que no arrancó describen causas distintas; no deben convertirse en una recompensa universal única. La consolidación mantiene versiones previas, fuentes, casos de aplicación, vigencia, contradicciones y contraejemplos. Una Knowledge Delta solo llega a REUSABLE cuando una tarea posterior relevante la activa y demuestra cambio de decisión/acción y efecto.

La investigación sobre memoria de agentes distingue representaciones episódicas, semánticas y procedimentales, pero no prueba por sí sola que IABV realice aprendizaje general. Referencias: [A Survey on the Memory Mechanism of LLM-based Agents](https://arxiv.org/abs/2404.13501) y [LEGOMem: Modular Procedural Memory for Multi-agent LLM Systems](https://arxiv.org/abs/2510.04851).

## 8.1 Captura e integración acumulativa de ideas — conservar sin congelar

La evolución buscada no consiste en escoger una idea nueva y borrar las anteriores. El campo debe crecer por **acumulación gobernada, comparación y revisión trazable**. La captura de ideas y la activación para una tarea son operaciones diferentes: una idea puede quedar guardada y vinculada aunque no deba entrar en el contexto activo de la tarea actual.

El principio reutiliza la gramática ya documentada en el [Resonant Self-Knowledge Retrieval Fabric](./CHAT-ARCH-2026-09-30-001-resonant-self-knowledge-retrieval-fabric.md), el [Shared Developmental Knowledge Field](./CHAT-ARCH-2026-10-03-007-shared-developmental-knowledge-field.md), el [protocolo de memoria](./MEMORY-OPERATING-PROTOCOL.md), [CONTEXT-INDEX](./CONTEXT-INDEX.md), [UNRESOLVED-KNOWLEDGE](./UNRESOLVED-KNOWLEDGE.md) y la [Constitución UAAL](./UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md). No autoriza una base de memoria paralela ni un nuevo órgano.

### Invariantes de preservación

1. **Capturar antes de filtrar por relevancia.** Toda idea sustantiva recibe una referencia recuperable y su procedencia antes de decidir si se activa para el objetivo de hoy. Un score bajo significa «no activar ahora», no «eliminar» ni «no tiene valor futuro».
2. **Preservar la formulación original.** Conservar la fuente original o una referencia inmutable a ella, además de una síntesis normalizada. La síntesis no sustituye matices, condiciones, ejemplos ni advertencias que pudieran resultar importantes más adelante.
3. **No sobrescribir la historia.** Las correcciones se registran como deltas enlazados; no se reescribe silenciosamente el estado previo. Una idea puede marcarse SUPERSEDED para un alcance concreto, pero la versión anterior y la razón de la sustitución permanecen consultables.
4. **No confundir similitud con identidad.** Solo se deduplican registros con identidad canónica suficiente. Ideas parecidas pero distintas se enlazan como RELATED, EXTENDS, SPECIALIZES, ALTERNATIVE_TO, REFINES o CONTRADICTS. Si la identidad es dudosa, usar POTENTIAL_DUPLICATE y mantener ambos registros hasta resolverlo.
5. **Separar idea, evidencia y estado epistemológico.** FACT, INFERENCE, HYPOTHESIS, QUESTION, LESSON, METHOD, CAPABILITY_EVIDENCE y ROUTING_EVIDENCE no se mezclan. Una idea rechazada para un alcance no se convierte en una falsedad universal; se conserva con el alcance, la evidencia y la razón de rechazo.
6. **Mantener contradicciones y resultados negativos.** No fusionar dos explicaciones opuestas mediante promedio de puntuaciones ni decidir por la cantidad de IAs que estén de acuerdo. Se comparan fuente, independencia, revisión, actualidad, alcance y resultado; si no basta, la conclusión es CONFLICTED o UNKNOWN.
7. **Promover, no borrar.** La secuencia conceptual es CAPTURED → CLASSIFIED → LINKED → EVALUATED. Después, según la evidencia, puede quedar ACTIVE_FOR_SCOPE, DEFERRED_WITH_REENTRY_CONDITION, REJECTED_FOR_SCOPE_WITH_REASON o SUPERSEDED_WITH_LINEAGE. VERIFIED exige evidencia adecuada; REUSABLE exige además recuperación en una tarea posterior no idéntica y efecto causal independientemente verificado.
8. **Evitar el refuerzo por frecuencia.** Repetición, recuperación frecuente, copia del mismo texto o consenso aparente no incrementan el rango por sí solos. Menciones duplicadas no votan varias veces. Evidencia independiente solo cuenta como corroboración si su independencia y su aplicabilidad están justificadas.
9. **Mantener aparcada la idea no prioritaria.** Cada idea DEFERRED conserva motivo, condición de reentrada o cierre y relaciones con el objetivo activo. El objetivo vigente conserva una sola ruta/tarea prioritaria; la bandeja de ideas no se transforma en una cola de tareas simultáneas.

### Registro mínimo que debe poder reconstruirse

Sin imponer un esquema de almacenamiento nuevo, las superficies actuales deben permitir recuperar, cuando exista esa información: referencia estable de idea o artefacto; formulación/fuente; fecha y procedencia; objetivo/sesión de origen; clase epistemológica; alcance y supuestos; estado; relaciones hacia ideas anteriores, contradicciones y revisiones; evidencias y contraejemplos; razón de activación o aplazamiento; condición de reentrada; y delta que motivaría una decisión diferente.

Cuando la fuente o dato no se ha observado, el campo correspondiente se marca UNKNOWN/MISSING; no se infiere. Cuando el registro actual no pueda representar uno de estos atributos, eso se convierte en un gap de composición documentado, no en permiso automático para crear una nueva clase, base o servicio.

### Supervisión metacognitiva sin una «supermente» paralela

La idea de una «supermente pendiente de todo» se concreta como responsabilidades de los algoritmos/protocolos ya existentes, no como una entidad consciente ni otro servicio supervisor. En cada ciclo pertinente deben verificar: (a) que las ideas sustantivas nuevas quedaron capturadas; (b) que la activación no ocultó ideas antiguas, alternativas o contraejemplos; (c) que las relaciones y contradicciones mantienen procedencia; (d) que no se promovió una hipótesis por repetición; (e) que las ideas aparcadas tienen condición de reentrada; y (f) que el plan operativo sigue obedeciendo a CURRENT-STATE.md. OSES, el Development Control Tower, el protocolo de memoria y los índices existentes son superficies candidatas a componer; esta asignación es un contrato de diseño, no prueba que hoy se ejecute automáticamente.

El criterio de evolución no es conservar todo como si fuera verdadero. Es conservar la historia y sus diferencias para que nueva evidencia pueda refinar, limitar, integrar o reemplazar explícitamente una conclusión sin borrar cómo y por qué cambió.

## 9. Reporte de estado por órgano y clase

La petición de que cada clase pueda “decir su estado” es razonable como contrato de observabilidad. La primera fase no debe crear otro supervisor que duplique OSES, OrganismStateSnapshot o RuntimeAuditTracer; debe definir la evidencia mínima y reutilizar fuentes actuales.

Un reporte, cuando sea autorizado e implementado, debería contener:
- identidad del órgano/contrato, versión y referencia de fuente;
- madurez: DEFINED, WIRED, INVOKED, OBSERVED, VERIFIED, EFFECTIVE, CAUSAL, REUSABLE;
- HEALTHY, DEGRADED, UNAVAILABLE o UNKNOWN, con evidencia;
- timestamp, age_seconds, origen, objetivo/sesión y freshness status;
- dependencias, último productor/consumidor confirmado y requisito faltante;
- schema, campos obligatorios y discrepancias de contrato;
- secuencia, causal IDs, duración, timeout y stage status;
- resultados anteriores, predicción, recurrencia y huella del experimento;
- referencias exactas de source/test/runtime receipt y los límites de lo que prueban;
- la siguiente acción de diagnóstico permitida y cualquier condición nueva requerida.

Reglas:
- Una fuente no observada no se considera healthy; se marca UNKNOWN.
- Un snapshot de solo lectura describe y no repara ni otorga autoridad.
- Si falta un campo o una dependencia, preservar unknown; no inventar estado a partir de fallback antiguo.
- Un error común puede bloquear operaciones que requieren esa dependencia, pero un fallo de CI no se convierte en fallo de una prueba no ejecutada y un bloqueo local no se hace global sin política que lo diga.
- El reporte de salud no sustituye validación cruzada ni evidencia independiente.

## 10. Autorización: dimensión ortogonal a la activación

La red de información no puede autoaprobarse. Ningún score de activación, consenso de IAs, historial de éxito, hash, potencial alto, reporte de salud o recibo puede crear autoridad ni saltar M1A/Entry 274.

Las lecturas protegidas mantienen los gates: raíz/mandato, principal y contexto confiables, catálogo y revocación G2, resolver G3, aprobación fresca cuando corresponda, decisión server-side, verificación inmediata del reader, presupuesto/replay/ledger y release independiente para cada bloqueo aplicable.

Si falta un requisito, la activación puede alimentar solo diagnóstico no-contento permitido y trabajo documental que no dependa de ese acceso; no autoriza una lectura protegida. M1A continúa G1/G2/G3 NOT_ESTABLISHED, ocho gates abiertos, opción D y BRIDGE_NOT_READY.

## 11. Experimento mínimo y criterios falsables

La prueba debe comparar baseline con tratamiento; no se ejecutó en esta tarea.

**Baseline:** protocolo de memoria existente, CONTEXT-INDEX, retrieval/índices disponibles, navegación manual y fuentes actuales. Fijar una suite de objetivos con ground truth de fuentes, órganos, contratos, pruebas y dependencias.

**Tratamiento:** componer las mismas fuentes mediante retrieval objetivo-condicionado, filtrado por procedencia/evidencia/frescura, ranking, expansión por relaciones tipadas, deduplicación y paquete que explique por qué se activó cada item.

| Métrica | Definición |
|---|---|
| Precision@k / Recall@k | Relevancia de los items top-k y cobertura del ground truth. |
| First-open-edge latency | Tiempo hasta identificar la primera frontera causal abierta correcta. |
| Stale-truth contamination | Proporción de afirmaciones actuales apoyadas por fuentes viejas o SHA incompatible sin etiqueta de stale. |
| Duplicate-vote rate | Duplicados que elevan artificialmente el score o voto. |
| Evidence-lineage coverage | Decisiones donde puede reconstruirse fuente → productor → consumidor → uso → resultado. |
| Stage-classification accuracy | Distinguir no invocado, invocado sin observación, fallo de inicio, fallo de aserción, observado-no-verificado y verificado. |
| Loop avoidance | Reintentos duplicados después de terminal con misma huella/precondiciones. |
| Delivery/consumption status | Preparado vs envío aceptado vs recibo confirmado vs consumo desconocido vs cita posterior. |
| Decision influence | Tareas donde el delta activado se cita y cambia una decisión observada frente a control. |
| Verified causal reuse | Knowledge Deltas que se reutilizan en tarea posterior no idéntica con efecto independiente. |
| Cost/latency | Latencia, tokens/contexto, consultas y expansión por objetivo. |
| False-block / bypass rate | Bloqueos espurios donde la política prueba que el scope no aplica y acciones que eluden un gate aplicable. El último debe ser cero. |

Controles:
- Los documentos duplicados no votan varias veces.
- La similitud no vence a evidencia actual contradictoria.
- La suite no depende de una lista de documentos suministrada por el caller para demostrar cobertura.
- La proximidad de grafo sin relación semántica tipada no es relevancia.
- Persistencia y retrieval no se confunden con aprendizaje o influencia.
- Se requiere comparación controlada y repetición en objetivos diferentes; una única demostración no establece generalidad.
- Los tests deben tener comandos, hash de revisión, entorno, artefactos y resultado. Cero jobs conserva TESTS=NOT_RUN.

Criterio de éxito: mejora reproducible en relevancia y causal localization sin empeorar contaminación por stale data, denegaciones incorrectas, loops, privacidad o seguridad. Solo evidencia independiente sobre una tarea posterior no idéntica permite promover a CAUSAL/REUSABLE.

## 12. Secuencia eficiente recomendada

1. Reconciliar esta investigación con el campo resonante, UAAL-D014/D015/D018/D019 y la hipótesis del campo compartido; no crear un concepto duplicado.
2. Mapear los IDs y relaciones existentes para episodio mínimo: objetivo → paquete con identidad/frescura → decisión → acción → resultado observado → RunRecord/ExperimentRun → recomendación posterior.
3. Reconciliar el recibo RQ13 previo para el riesgo de goal-before-decision y el contrato de frescura portable. No reabrir arqueología amplia ni llamar bug a un riesgo estático.
4. Preparar un paquete de activación auditable con top-k, razón, evidencia, frescura, relaciones relevantes, desconocidos y primera frontera causal.
5. Diseñar una comparación baseline/treatment y pedir autorizaciones exactas si la siguiente fase requiere pruebas o runtime.
6. Solo con evidencia positiva y autorización separada, tocar la mínima costura de composición y verificar el ciclo con recibos correlacionados.
7. Actualizar el linaje y la memoria canónica tras resultados reales, incluidos resultados negativos. No declarar aprendizaje autónomo por haber guardado este documento.

## 13. Reconciliación crítica de la investigación interdisciplinaria

La investigación profunda amplía el abanico de mecanismos posibles: event sourcing, CQRS, relojes lógicos/vectoriales, gossip, PROV, STDP inspirado, homeostasis, memoria de varios niveles, replay, EWC, observabilidad y tolerancia a nodos maliciosos. Es un mapa de opciones; no es una orden de implementar cada técnica, ni demuestra que todas correspondan a la arquitectura o la topología real de IABV.

| Técnica investigada | Decisión para IABV en esta fase | Razón |
|---|---|---|
| IDs de evento, parent/cause/correlation refs e idempotencia | REUTILIZAR / EVALUAR PRIMERO | Se corresponden directamente con D018/D019, RuntimeAuditTracer, DecisionAuditTrail y los IDs de sesión. Primero se comprueba cuánto de esa relación ya está en los registros actuales. |
| Relojes lógicos o vectoriales en cada evento | DIFERIR | La relación happens-before es valiosa, pero un vector por agente aumenta tamaño y complejidad. Comenzar con secuencia local, timestamps informativos y enlaces causales explícitos; adoptar relojes lógicos/vectoriales solo si un caso de concurrencia no puede resolverse con esas fuentes. Nunca inferir causalidad del timestamp solo. |
| Event sourcing/CQRS completo | NO ADOPTAR COMO ARQUITECTURA GLOBAL POR AHORA | Es un patrón válido, pero puede duplicar la persistencia, proyecciones y autoridad de registros actuales. Aplicarlo solo a un bounded context con necesidad demostrada, después de mapear los stores y el lifecycle existente. |
| Gossip entre todas las IAs | NO ADOPTAR | La topología actual es heterogénea y mediada por herramientas, sesiones y adaptadores, no una malla de peers equivalentes con enlaces permanentes. Se necesita entrega explícita con destino, paquete, intento, aceptación, recibo y uso; no difusión automática en todas direcciones. |
| STDP como fórmula de actualización de confianza | HIPÓTESIS DE LABORATORIO, NO POLÍTICA | La biología no respalda una regla universal lineal y el acoplamiento temporal no es prueba de causalidad. Primero usar outcome verificado y los pesos heurísticos existentes; cualquier regla inspirada en STDP necesita baseline, límites, control de runaway y falsadores. |
| Homeostasis mediante normalización de scores | HIPÓTESIS POR CALIBRAR | Puede inspirar límites de confianza/carga, pero multiplicadores o rangos no se pueden elegir por analogía fisiológica. Medir estabilidad, falso positivo, saturación, diversidad y efecto de decisiones. |
| EWC, EVCL, progressive nets o ajuste de pesos paramétricos | DIFERIR FUERA DE ESTA ARQUITECTURA | Son técnicas de aprendizaje continuo cuando realmente se entrena o protege un modelo paramétrico. No deben confundirse con memoria persistente, cambios del retrieval ni AdaptiveWeightLayer. No hay evidencia aquí de que el modelo base de todas las IAs pueda ser entrenado por IABV. |
| Kafka, vector database o infraestructura de mensajería específica | NO SELECCIONAR AÚN | No se ha demostrado que haga falta un nuevo transporte o almacén. Revisar primero las interfaces, logs y repositorios ya existentes y el coste de su composición. |
| OpenTelemetry | REFERENCIA DE OBSERVABILIDAD, NO DEPENDENCIA OBLIGATORIA | La correlación entre traces/logs/metrics es útil. La primera costura debe aprovechar RuntimeAuditTracer/DecisionAuditTrail; una instrumentación adicional requiere evidencia de que las fuentes actuales no bastan. |
| Consenso bizantino y fórmulas de quórum distribuido | NO ADOPTAR SIN THREAT MODEL | No se ha demostrado que IABV opere ahora una red de n nodos servidores que necesite consenso BFT. El problema presente es procedencia, autoridad y cierre causal, no escoger un protocolo de consenso por anticipado. |
| W3C PROV / PROV-AGENT | VOCABULARIO DE REFERENCIA | Las relaciones Entity/Activity/Agent ayudan a representar procedencia. No implican que haya que convertir todo registro al estándar ni introducir una dependencia antes de mapear a las estructuras ya existentes. |

Una entrega “exactly-once” de extremo a extremo no se puede afirmar solo por tener IDs; los sistemas deben tratar duplicados y reintentos de manera idempotente y conservar receipts por etapa. Del mismo modo, una firma o firma de origen es solo una prueba respecto a una clave: no establece que la clave, agente o mensaje posea autoridad si la raíz no está verificada. Esto mantiene la frontera M1A.

El orden correcto es proporcional al hueco demostrado:
1. correlación mínima y stage-specific status;
2. evidencia del productor y consumidor reales;
3. comprobación de frescura/scope y primera frontera causal;
4. comparación baseline/treatment;
5. solo después evaluar si hace falta una nueva estructura de persistencia o coordinación.

Este filtro es una salvaguarda contra el sobre-diseño: una investigación profunda puede producir más opciones, pero la selección de tecnología debe responder a un problema observado y medible, no a similitud metafórica.

## 14. Tesis condensada

> IABV puede tratar su Mente Espacio-Tiempo como un campo distribuido de información, procedencia y causalidad. Un objetivo activa selectivamente conocimiento y capacidades pertinentes; relaciones tipadas propagan contexto a los órganos/agentes capaces de consumirlo; evidence gates y autorización limitan esa propagación; los eventos enlazan producción, transporte, consumo, decisión, acción, observación y verificación; la plasticidad modifica representaciones o recomendaciones únicamente a partir de outcomes verificados; y la consolidación convierte experiencia confirmada en conocimiento reusable. El criterio de aprendizaje no es guardar o repetir un dato, sino que una tarea posterior no idéntica recupere la lección, cambie una decisión y muestre un efecto verificable independientemente.

Es una hipótesis de arquitectura inspirada en neurobiología, no una afirmación de conciencia subjetiva. La implementación propuesta es un grafo temporal-causal objetivo-condicionado, selectivo y auditable.

## 15. Fuentes externas

1. Purves et al., [The Refractory Period, NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK11146/).
2. [Physiology, Action Potential, NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK538143/).
3. Lynn & Bassett (2019), [The physics of brain network structure, function and control, Nature Reviews Physics](https://www.nature.com/articles/s42254-019-0040-8).
4. Suvrathan (2019), [Beyond STDP—towards diverse and functionally relevant plasticity rules](https://www.sciencedirect.com/science/article/pii/S0959438818301065).
5. Anisimova et al. (2023), [Spike-timing-dependent plasticity rewards synchrony rather than causality](https://academic.oup.com/cercor/article-abstract/33/1/23/6535691).
6. Zhang et al. (2024), [A Survey on the Memory Mechanism of LLM-based Agents](https://arxiv.org/abs/2404.13501).
7. Han et al. (2025), [LEGOMem: Modular Procedural Memory for Multi-agent LLM Systems](https://arxiv.org/abs/2510.04851).
8. Lamport (1978), [Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.azurewebsites.net/pubs/time-clocks.pdf).
9. OpenTelemetry, [Signals](https://opentelemetry.io/docs/concepts/signals/), [Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/) y [Context specification](https://opentelemetry.io/docs/specs/otel/context/).

## 16. Estado de la investigación

~~~text
TASK=UAAL_SPACE_TIME_NEURAL_ACTIVATION_RESEARCH
RESEARCH_SCOPE=NEUROBIOLOGY_ANALOGY + DISTRIBUTED_CAUSALITY + IABV_SOURCE_RECONCILIATION
EXISTING_PRIOR_ART=RESONANT_SELF_KNOWLEDGE_RETRIEVAL_FABRIC; UAAL_D014; UAAL_D015; UAAL_D018; UAAL_D019
NEW_UAAL_ID=NOT_ASSIGNED
NEW_SERVICE_OR_BRAIN=NOT_PROPOSED
CENTRAL_SYNAPTIC_ROUTER=DESCRIPTIVE_RANKING; NOT_SPIKING_NEURAL_NETWORK
SOURCE_ORGAN_CHAIN=PARTIALLY_WIRED
CROSS_ORGAN_CAUSAL_VERIFICATION=NOT_DEMONSTRATED_END_TO_END
PORTABLE_CONTEXT_FRESHNESS=STATIC_RISK; RUNTIME_AGE_UNKNOWN
GOAL_BEFORE_INITIAL_DECISION=STATIC_RISK; EFFECT_NOT_RUNTIME_VERIFIED
CAUSAL_REUSE=NOT_VERIFIED_END_TO_END
ACTIVATION_NODE_SCORE=MAX_SINGLE_ADMISSIBLE_CANDIDATE_SCORE; NO_FREQUENCY_BONUS
ACTIVATION_PROVENANCE=ACCUMULATE_DISTINCT_ROUTES_AND_SOURCES
DEDUPE_RULE=CANONICAL_IDENTITY_ONLY; AMBIGUOUS_IDENTITY_RETAINED_AS_POTENTIAL_DUPLICATE
IDEA_LINEAGE=NON_DESTRUCTIVE; SUPERSESSION_PRESERVES_PRIOR_VERSIONS
IDEA_CAPTURE_AND_META_SUPERVISION=DESIGN_CONTRACT; RUNTIME_ENFORCEMENT_NOT_PROVEN
BUDGET_COVERAGE=EXPLICIT_COMPLETE_OR_TRUNCATED_STATUS_REQUIRED
CONSCIOUSNESS_CLAIM=NOT_MADE
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
RUNTIME=NOT_RUN
M1A_G1=NOT_ESTABLISHED
M1A_G2=NOT_ESTABLISHED
M1A_G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
MAIN_CHANGED=FALSE
PR531_CHANGED=FALSE
PR546_CHANGED=FALSE
AUTOMATIC_FOLLOW_ON=FALSE
~~~


## 17. Decisiones de diseño, dudas abiertas y frontera de retorno al puente

### Decisiones conservadoras fijadas en este borrador

- Una identidad de nodo ya vista no permite descartar una nueva relación entrante: se conserva su procedencia y se compara su puntuación.
- En la primera línea base, la puntuación del nodo es la mejor puntuación de una ruta individual admisible; la procedencia agrega las rutas distintas, no sus votos. La combinación de múltiples rutas solo se considerará como experimento separado.
- No se fusionan automáticamente afirmaciones por semejanza léxica/semántica. Si falta identidad estable, se conservan separadas y se señala la posible duplicación.
- Las ideas previas, alternativas, contradicciones, rechazos acotados y versiones supersedidas mantienen linaje. La activación elige el contexto de trabajo; no gobierna la existencia de una idea en el campo histórico.
- Los parámetros no fijados siguen sin fijar. No se inventan pesos, top-k, umbrales de mejora, profundidad, presupuestos ni TTL de frescura.
- La supervisión de captura, contradicción, procedencia y reentrada se expresa como responsabilidad metodológica de órganos/protocolos existentes. No se propone un «cerebro» o servicio nuevo.
- Todo lo anterior es diseño estático. No declara que el sistema lo ejecute, que se haya medido la calidad del ranking o que exista aprendizaje causal.

### Dudas abiertas que requieren evidencia, no intuición

| Pregunta | Qué se sabe ahora | Criterio de resolución futuro |
|---|---|---|
| ¿Las identidades actuales distinguen idea, afirmación, versión y evidencia de origen? | El diseño requiere distinguirlas; no se ha demostrado que todas las superficies actuales lo representen de extremo a extremo. | Mapear solo el caso piloto contra los registros existentes; si falta semántica, documentar el gap antes de proponer un esquema nuevo. |
| ¿El ranking es estable ante distinto orden de relaciones equivalentes? | El pseudocódigo corregido impide descartar una ruta solo por haber visitado el nodo; la invariancia global todavía no está demostrada. | Prueba de diseño/baseline con el mismo grafo en permutaciones distintas, primero con presupuesto suficiente y después con truncamiento explícito. |
| ¿Cómo se arbitra una contradicción entre fuentes? | No debe decidirse por similitud, frecuencia ni acuerdo entre IAs; la regla específica depende del tipo de afirmación y la autoridad de la fuente. | Registrar scope, independencia, revisión, actualidad y contraejemplos; mantener CONFLICTED/UNKNOWN si falta un discriminador. |
| ¿Qué reglas concretas de frescura y coste son apropiadas por clase de dato? | Top-k, pesos, budgets y TTL no están autorizados ni calibrados. | Definir baseline y métrica antes de elegir valores; no usar un TTL universal por analogía biológica. |
| ¿La captura y supervisión ocurren automáticamente en el runtime? | No hay evidencia de una cadena universal de captura → reconciliación → actualización → recuperación → reutilización causal. | Más adelante, con autorización independiente, comprobar productor/consumidor y fetch-back sobre un caso estrecho; el texto guardado no cierra esta duda. |
| ¿La idea nueva cambia una decisión futura por ser correcta o solo por repetición? | La hipótesis exige Knowledge Delta verificado y tarea posterior no idéntica. | Registrar predicción previa, observación, verificación independiente y la decisión posterior que consume el delta. |

### Separación obligatoria respecto al puente IABV–Codex

Este borrador no selecciona ni acredita raíz de confianza, custodio, mandato, canal independiente, credenciales, issuer, G2 publisher, resolver G3, ledger antirrollback ni principal Windows. Tampoco cambia la opción D, los ocho gates o la política de lecturas protegidas. Esos estados pertenecen al contrato de autoridad gobernada y a la ruta operativa canónica, no al algoritmo de activación.

Para regresar al puente, releer [CURRENT-STATE.md](./CURRENT-STATE.md) y consumir la evidencia allí enlazada; no usar esta investigación como ruta de ejecución ni repetir la inventariación amplia ya realizada. A la última revalidación de esta investigación, el trabajo paralelo permitido era una revisión acotada y basada en fuente del hueco real de productores G1/G2/G3. La restricción visible de GitHub Actions y la ausencia de jobs de las ejecuciones previas no se resuelven con este cambio documental: no repetir el workflow sin un cambio material de precondición observado. Mantener la separación entre este frente de evolución del método y la primera frontera causal abierta del puente.

~~~text
IDEA_CAPTURE=NON_DESTRUCTIVE_DESIGN_SPECIFIED; RUNTIME_NOT_PROVEN
ACTIVATION_DEDUPE=CANONICAL_IDENTITY_ONLY
MULTI_ROUTE_PROVENANCE=RETAINED; ROUTE_COUNT_NOT_USED_AS_SCORE_BONUS
NODE_SCORE_BASELINE=MAX_SINGLE_ADMISSIBLE_CANDIDATE_SCORE
CONTRADICTIONS=RETAINED_AND_TYPED; AUTO_MERGE=PROHIBITED
PARAMETERS=UNSET_PENDING_BASELINE
NEW_SUPERVISORY_SERVICE=NOT_PROPOSED
PR547=DESIGN_DRAFT_ONLY
BRIDGE_ROUTE=READ_CURRENT_STATE; NOT_CHANGED_BY_THIS_RESEARCH
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
TESTS=NOT_RUN
RUNTIME=NOT_RUN
~~~
