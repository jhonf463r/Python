# Análisis de Coherencia de Órganos de Planificación de IABV

**Fecha:** 2026-06-15 11:06:43
**Objetivo:** Analizar si el programa IABV funciona como el usuario se lo imagina: un órgano encargado de ver el camino según la tarea a ejecutar, analizando metadatos, viendo navegadores/programas disponibles, estructurando visión mental, reutilizando ventanas/chats existentes, y razonando contextualmente para evitar abrir chats innecesarios.

---

## Resumen Ejecutivo

**El programa IABV TIENE la mayoría de los órganos que el usuario imagina, pero hay una INCOHERENCIA CRÍTICA en la configuración que hace que abra nuevas ventanas/chats en lugar de reutilizar los existentes.**

**Estado general:** ⚠ Órganos existentes pero configuración incoherente con la visión del usuario

---

## 1. Órgano de Planificación y Análisis de Metadatos

### Estado: ✓ EXISTE Y FUNCIONA

**Componente:** ToolTeachService

**Capacidades disponibles:**
- ✓ Tiene registry - acceso a todas las herramientas registradas
- ✓ Tiene memory - memoria de ejecuciones pasadas
- ✓ Tiene sandbox - entorno de prueba seguro
- ✓ Tiene validator - validación de herramientas
- ✓ Tiene adapters - adaptadores para diferentes tipos de herramientas
- ✓ Tiene mode_selector - selector de modo de interacción
- ✓ Tiene build_task_for_session() - analiza sesión para construir tarea
- ✓ Tiene _assistant_configuration_snapshot() - analiza configuración del asistente

**Cómo funciona:**
Cuando llega una tarea, el ToolTeachService:
1. Analiza la sesión y construye una tarea (build_task_for_session)
2. Selecciona la herramienta apropiada basándose en la tarea (pick_card_for_task)
3. Analiza la configuración del asistente (_assistant_configuration_snapshot)
4. Determina el modo de interacción (mode_selector)

**Coherencia con visión del usuario:** ✓ ALTA
El órgano de planificación existe y funciona como el usuario imagina: analiza metadatos y selecciona la herramienta apropiada.

---

## 2. Capacidad de Ver Programas/Navegadores Disponibles

### Estado: ✓ EXISTE Y FUNCIONA

**Componente:** WorldModelService

**Capacidades disponibles:**
- ✓ Tiene current_model() - obtiene snapshot actual del sistema
- ✓ Tiene scan_now() - escanea el sistema
- ✓ Escanea ventanas (_list_windows)
- ✓ Escanea procesos (_background_processes)
- ✓ Escanea red (_network_status)
- ✓ Escanea herramientas (_tool_live_status)

**Resultado del escaneo actual:**
- Ventanas activas: 10
- Ventana enfocada: None
- Estado de red: conectado
- Herramientas live: disponibles

**Coherencia con visión del usuario:** ✓ ALTA
El programa puede ver qué navegadores/programas están disponibles en el sistema.

---

## 3. Capacidad de Estructurar Visión Mental de Programas/Páginas

### Estado: ✓ EXISTE Y FUNCIONA

**Componentes:**
- UniversalPerceptionService
- EnvironmentSelfAwarenessService
- UniversalMetacognitiveScanner

**Capacidades disponibles:**

**UniversalPerceptionService:**
- ✓ analyze_clickable_elements() - analiza elementos clickeables
- ✓ analyze_visual_evidence() - analiza evidencia visual
- ✓ build_capture_signal() - construye señal de captura
- ✓ build_web_surface_snapshot() - construye snapshot de superficie web
- ✓ interpret_web_surface() - interpreta superficie web
- ✓ scan_tool_context() - escanea contexto de herramienta

**EnvironmentSelfAwarenessService:**
- ✓ current_model() - modelo actual del entorno
- ✓ scan_now() - escanea el entorno
- ✓ request_refresh() - solicita actualización

**UniversalMetacognitiveScanner:**
- ✓ current_snapshot() - snapshot actual metacognitivo
- ✓ generate_report() - genera reporte
- ✓ get_bias_detection_counts() - obtiene contadores de sesgos

**Coherencia con visión del usuario:** ✓ ALTA
El programa tiene capacidad de estructurar una visión mental de programas/páginas web mediante múltiples servicios de percepción.

---

## 4. Reutilización de Ventanas/Chats Existente

### Estado: ⚠ INCOHERENCIA CRÍTICA

**Componente:** ToolRegistry + ToolCard metadata

**Análisis de herramientas ChatGPT:**

### chatgpt_web_assisted
- launch_mode: web_assisted
- **isolated_session_required: True** ⚠
- session_scope: program_chat
- session_label: ChatGPT especial de IABV
- **browser_profile_dir: C:\Python\IABV_v1.5\data\evolution\browser_profiles\chatgpt** ✓
- **credential_domain: chatgpt.com** ✓

**Problema:**
- ⚠ `isolated_session_required: True` - Requiere sesión aislada, puede abrir nueva ventana cada vez
- ✓ Tiene `browser_profile_dir` - Puede mantener sesión persistente
- ✓ Tiene `credential_domain` - CredentialBroker puede funcionar

**Incoherencia:**
Aunque tiene `browser_profile_dir` configurado para mantener sesión persistente, `isolated_session_required: True` hace que el programa abra una nueva ventana cada vez, contradiciendo la capacidad de mantener sesión persistente.

### chatgpt_installed
- launch_mode: desktop_app
- **isolated_session_required: None** ✓
- session_scope: None
- session_label: None
- **browser_profile_dir: None** ⚠
- **credential_domain: None** ⚠

**Problema:**
- ✓ No requiere sesión aislada - puede reutilizar sesión existente
- ⚠ No tiene `browser_profile_dir` - no puede mantener sesión persistente
- ⚠ No tiene `credential_domain` - CredentialBroker no puede funcionar

**Coherencia con visión del usuario:** ⚠ BAJA
La configuración actual hace que el programa abra nuevas ventanas/chats en lugar de reutilizar los existentes, contradiciendo la visión del usuario.

---

## 5. Razonamiento Contextual para Evitar Chats Innecesarios

### Estado: ✓ EXISTE PERO NO SE USA EFECTIVAMENTE

**Componentes:**
- InteractionLearningService
- ToolMemory
- InteractionModeSelector

**Capacidades disponibles:**

**InteractionLearningService:**
- ✓ learn_from_execution() - aprende de ejecuciones
- ✓ learn_from_teaching_session() - aprende de sesiones de enseñanza
- ✓ match_patterns() - busca patrones
- ✓ pattern_summary() - resumen de patrones

**ToolMemory:**
- ✓ audit_event() - audita eventos
- ✓ history_for_tool() - historial de herramienta
- ✓ remember_result() - recuerda resultados
- ✓ remember_task() - recuerda tareas

**InteractionModeSelector:**
- ✓ select() - selecciona modo de interacción
- ✓ registry - acceso a registry
- ✓ repository - acceso a repositorio

**Coherencia con visión del usuario:** ⚠ MEDIA
Los servicios de aprendizaje y memoria existen, pero no se usan efectivamente para evitar abrir chats innecesarios. La configuración `isolated_session_required: True` en chatgpt_web_assisted hace que el programa ignore el contexto previo y abra nuevas ventanas.

---

## Análisis de Coherencia General

### Lo que el programa TIENE (✓)

1. ✓ Órgano de planificación (ToolTeachService) - analiza metadatos y selecciona herramientas
2. ✓ Capacidad de ver programas/navegadores (WorldModelService) - escanea ventanas, procesos, red
3. ✓ Capacidad de estructurar visión mental (UniversalPerceptionService) - analiza elementos visuales, snapshots web
4. ✓ Servicios de aprendizaje (InteractionLearningService) - aprende de ejecuciones
5. ✓ Memoria de herramientas (ToolMemory) - recuerda resultados y tareas
6. ✓ Selector de modo (InteractionModeSelector) - selecciona modo de interacción
7. ✓ Scanner metacognitivo (UniversalMetacognitiveScanner) - detecta sesgos cognitivos

### Lo que el programa NO TIENE o NO USA EFECTIVAMENTE (⚠)

1. ⚠ **Coherencia en configuración de sesión** - `isolated_session_required: True` contradice `browser_profile_dir`
2. ⚠ **Reutilización efectiva de ventanas/chats** - configuración hace que abra nuevas ventanas
3. ⚠ **Razonamiento contextual para evitar chats innecesarios** - servicios existen pero no se usan efectivamente
4. ⚠ **Memoria de corto plazo/contexto** - no hay un componente explícito de memoria de contexto activo

### Incoherencia Crítica

**El problema principal es que chatgpt_web_assisted tiene:**
- `isolated_session_required: True` - hace que abra nueva ventana cada vez
- `browser_profile_dir: configurado` - podría mantener sesión persistente

**Estos dos metadatos son contradictorios:**
- Si `isolated_session_required: True`, entonces `browser_profile_dir` no sirve porque cada vez se abre una nueva ventana
- Si `browser_profile_dir` está configurado para mantener sesión persistente, entonces `isolated_session_required` debería ser `False`

**Resultado:** El programa tiene la CAPACIDAD de mantener sesión persistente, pero la CONFIGURACIÓN hace que abra nuevas ventanas cada vez, contradiciendo la visión del usuario.

---

## Recomendaciones

### 1. Corregir incoherencia en chatgpt_web_assisted (ALTA PRIORIDAD)

**Opción A: Habilitar reutilización de sesión**
- Cambiar `isolated_session_required: True` a `False`
- Mantener `browser_profile_dir` configurado
- Esto permitirá reutilizar la misma ventana/chat para múltiples consultas

**Opción B: Eliminar browser_profile_dir si se requiere sesión aislada**
- Mantener `isolated_session_required: True`
- Eliminar `browser_profile_dir` porque no sirve si cada vez es una nueva ventana
- Esto es coherente pero no resuelve el problema del usuario

**Recomendación:** Opción A - cambiar `isolated_session_required: False` para permitir reutilización de sesión.

### 2. Implementar memoria de contexto activo (MEDIA PRIORIDAD)

Crear un componente que:
- Mantenga un registro de ventanas/chats activos
- Asocie cada ventana/chat con su contexto
- Permita reutilizar ventanas/chats existentes cuando el contexto sea compatible
- Evite abrir nuevas ventanas cuando una existente sirva

### 3. Usar efectivamente InteractionLearningService (MEDIA PRIORIDAD)

El servicio existe pero no se usa efectivamente para:
- Detectar patrones de uso de ventanas/chats
- Aprender qué contextos pueden compartir la misma ventana
- Sugerir reutilización de ventanas existentes
- Evitar abrir nuevas ventanas innecesariamente

### 4. Implementar razonamiento contextual antes de abrir nueva ventana (ALTA PRIORIDAD)

Antes de abrir una nueva ventana/chat, el programa debería:
1. Consultar WorldModelService para ver si ya hay ventanas de ChatGPT abiertas
2. Consultar ToolMemory para ver el contexto de esas ventanas
3. Determinar si el contexto actual es compatible con el contexto de la ventana existente
4. Si es compatible, reutilizar la ventana existente
5. Si no es compatible, abrir una nueva ventana

---

## Conclusión

**El programa IABV TIENE los órganos que el usuario imagina, pero hay una INCOHERENCIA CRÍTICA en la configuración que hace que no funcione como el usuario espera.**

**Órganos existentes:**
- ✓ Órgano de planificación y análisis de metadatos
- ✓ Capacidad de ver programas/navegadores disponibles
- ✓ Capacidad de estructurar visión mental de programas/páginas
- ✓ Servicios de aprendizaje y memoria
- ✓ Selector de modo de interacción

**Incoherencia crítica:**
- ⚠ `isolated_session_required: True` en chatgpt_web_assisted hace que abra nuevas ventanas cada vez
- ⚠ Esto contradice la capacidad de mantener sesión persistente con `browser_profile_dir`
- ⚠ Los servicios de aprendizaje y memoria no se usan efectivamente para evitar abrir chats innecesarios

**Resultado:** El programa tiene la CAPACIDAD de funcionar como el usuario imagina, pero la CONFIGURACIÓN hace que no lo haga.

**Para resolver:** Cambiar `isolated_session_required: False` en chatgpt_web_assisted y usar efectivamente los servicios de aprendizaje y memoria para reutilizar ventanas/chats existentes.
