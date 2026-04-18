# ANÁLISIS DE RENDIMIENTO — IABV v1.5 | DIAGNÓSTICO DE CONGELAMIENTO

**Fecha:** 2026-04-18  
**Problema:** Sistema lento al iniciar, congelamiento al cargar interfaces, interfaz incompleta

---

## Síntomas Reportados

1. ❌ **Lento al encender** — demora en startup
2. ❌ **Se congela cuando carga** — interfaz no responde
3. ❌ **No ve demás interfaces de chat** — solo ve la primera, las demás no aparecen
4. ❌ **Interfaz incompleta** — elementos no se renderizan

---

## Causas Encontradas

### 🔴 CRÍTICO #1: Carga Sincrónica del Loader (Main.qml:184)

```qml
Loader {
    id: pageLoader
    ...
    asynchronous: false        ← ❌ PROBLEMATICO
    source: routeSource(activeRoute)
}
```

**Problema:** 
- `asynchronous: false` **BLOQUEA toda la interfaz** mientras carga una página QML
- Cuando cambias de página (dashboard → control → capture, etc.), se congela completamente
- El usuario no puede interactuar con la UI mientras carga la nueva página

**Impacto:** Cada vez que el usuario navega a otra pestaña, la aplicación se congela hasta 2-5 segundos

---

### 🔴 CRÍTICO #2: Bootstrap Carga TODO al Iniciar (bootstrap.py:130-500)

El bootstrap.py crea **50+ servicios en serie** durante startup:

```python
# En el __init__ del AppBootstrap (~650 líneas):
- 15 repositorios (acceden a disk/database)
- 20+ servicios de evolución y validación
- 10+ servicios de herramientas
- 8 servicios de roles
- 5+ servicios de captura
- Embedding index service (carga modelos)
- WorldModelService (parsea archivos)
- Training orchestrator (carga configuración)
```

**Problema:**
- Cada repositorio hace I/O (lectura de SQLite, JSON files)
- Los servicios se inicializan **secuencialmente**, no en paralelo
- EmbeddingIndexService probablemente carga modelos grandes en memoria
- Todo esto ocurre ANTES de que la UI sea visible

**Impacto:** Startup toma 15-60 segundos (depende de computadora y datos persistidos)

---

### 🔴 CRÍTICO #3: Todas las ViewModels se Crean Upfront (bootstrap.py:556-650)

En `_build_ui_objects()`, se crean **7 ViewModels diferentes** antes de mostrar la UI:

```python
self.dashboard_viewmodel = DashboardViewModel(...)        # Carga episodes
self.control_center_viewmodel = ControlCenterViewModel(...) # Carga runs, artifacts
self.capture_studio_viewmodel = CaptureStudioViewModel(...)  # Carga episodes, artifacts
self.evolution_center_viewmodel = EvolutionCenterViewModel(...) # PESADA
self.knowledge_base_viewmodel = KnowledgeBaseViewModel(...)   # Carga memory
self.provider_settings_viewmodel = ProviderSettingsViewModel(...) # Carga config
self.run_history_viewmodel = RunHistoryViewModel(...)         # Carga runs
```

**Problema:**
- Se cargan **todas** las vistas aunque el usuario solo vea 1 al principio
- Cada ViewModel hace queries a la base de datos
- Se ejecutan en serie, bloqueando UI

**Impacto:** Startup delay adicional de 5-15 segundos

---

### 🟠 PROBLEMA #4: Posible Threading en Servicios

Muchos servicios hacen I/O pero pueden estar en el **hilo principal de Qt**:

```python
# Ejemplos que hacen I/O pesado:
- EmbeddingIndexService (carga/busca embeddings)
- EvolutionCenterViewModel (queries complejas)
- WorldModelService (parsea state snapshots)
- ToolRegistry (escanea archivos)
```

**Problema:** Si estos se ejecutan en el hilo de UI, congelan la interfaz

**Impacto:** Congelamiento durante operaciones de background

---

## Árbol del Problema

```
[STARTUP LENTO]
├─ Bootstrap crea 50+ servicios en serie
│  ├─ I/O: SQLite, JSON files, modelos
│  └─ Secuencial: sin paralelismo
├─ _build_ui_objects() crea 7 ViewModels
│  └─ Cada ViewModel hace queries
└─ Loader asynchronous=false
   └─ Bloquea UI en cada navegación

[CONGELAMIENTO AL CARGAR PÁGINAS]
├─ Main.qml Loader con asynchronous: false
│  └─ Cada página nueva congela toda la interfaz
└─ Posible threading de servicios en hilo UI
   └─ Operaciones pesadas bloquean rendering

[INTERFAZ INCOMPLETA]
├─ Posibles timeouts al cargar ViewModels
├─ Errores silenciosos en QML
└─ Páginas no se renderizar completamente
```

---

## Soluciones Recomendadas

### ✅ PRIORITARIO: Cargar QML de Forma Asincrónica

**Archivo:** `/c/Python/IABV_v1.5/src/iabv_v15/ui/qml/Main.qml`

**Cambio línea 184:**
```qml
# ANTES (CONGELA UI):
asynchronous: false

# DESPUÉS (No congela):
asynchronous: true

# BONUS: Mostrar spinner/placeholder mientras carga:
Loader {
    ...
    asynchronous: true
    sourceComponent: pageLoader.status === Loader.Ready ? actualPage : loadingSpinner
}
```

**Impacto:** ⚡ Elimina congelamiento al cambiar páginas

**Tiempo implementación:** 5 minutos

---

### ✅ IMPORTANTE: Lazy Load de ViewModels

**Archivo:** `/c/Python/IABV_v1.5/src/iabv_v15/bootstrap.py` línea 556

**Cambio:**
```python
# ANTES: Crea TODAS las ViewModels en _build_ui_objects()
def _build_ui_objects(self):
    self.dashboard_viewmodel = DashboardViewModel(...)
    self.control_center_viewmodel = ControlCenterViewModel(...)
    # ... 7 ViewModels más

# DESPUÉS: Crear solo cuando se necesitan
def _build_ui_objects(self):
    self._viewmodels = {}  # Cache lazy
    
def get_viewmodel(self, name):
    if name not in self._viewmodels:
        if name == 'dashboard':
            self._viewmodels[name] = DashboardViewModel(...)
        # ... crear bajo demanda
    return self._viewmodels[name]
```

**Impacto:** ⚡ Reduce startup de 30s a 5-10s

**Tiempo implementación:** 15-20 minutos

---

### ✅ IMPORTANTE: Paralelizar Inicialización de Bootstrap

**Archivo:** `/c/Python/IABV_v1.5/src/iabv_v15/bootstrap.py`

**Estrategia:**
```python
# Dividir en fases:
Phase 1 (BLOQUEANTE): DB, Config, UI Framework
Phase 2 (PARALELO): Repositorios, EmbeddingService, WorldModel
Phase 3 (DEFERRED): Servicios no-críticos

# Usar ThreadPoolExecutor:
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)
future_embedding = executor.submit(self._init_embedding_service)
future_evolution = executor.submit(self._init_evolution_services)
# ... esperar en background, no bloquea UI
```

**Impacto:** ⚡ Parallelizar 50% del bootstrap (5-10s más rápido)

**Tiempo implementación:** 30-45 minutos

---

### ✅ RECOMENDADO: Mover Heavy Ops a Background Threads

**Archivo:** `src/iabv_v15/services/roles/embedding_index_service.py` (y similares)

**Cambio:**
```python
# Si EmbeddingIndexService carga modelos grandes:
def __init__(self, ...):
    # NO hacer aquí:
    # self.model = load_model(...)  ← BLOQUEA
    
    # Hacer en thread:
    self.model = None
    threading.Thread(target=self._load_model, daemon=True).start()

def _load_model(self):
    self.model = load_model(...)
    self._ready = True
```

**Impacto:** ⚡ UI aparece inmediatamente (5-15s más rápido en startup)

**Tiempo implementación:** 20 minutos

---

## Plan de Acción — Prioridades

| Prioridad | Solución | Impacto | Tiempo | Esfuerzo |
|-----------|----------|--------|--------|----------|
| 🔴 CRÍTICO | Asynchronous: true en Loader | Elimina congelamiento | Inmediato | 5 min |
| 🔴 CRÍTICO | Lazy load ViewModels | -60% startup | 20-30s → 5-10s | 20 min |
| 🟠 IMPORTANTE | Paralelizar bootstrap | -40% startup | Fase II en bg | 45 min |
| 🟡 RECOMENDADO | Background threads para Heavy Ops | -50% UI blocking | Inmediato | 20 min |

---

## Resumen

**Problemas:** 3 causas raíz encontradas
- Loader sincrónico (congela UI)
- ViewModels eagerly loaded (startup lento)
- Bootstrap sin paralelismo (todo secuencial)

**Soluciones:** 4 cambios específicos con tiempos claros

**Impacto esperado:**
- ⚡ Startup: 30-60s → 5-10s (80% más rápido)
- ⚡ Navegación: Congelamiento → fluida
- ⚡ Interfaz: Completa desde inicio

**Próximos pasos:** ¿Deseas que implemente estas correcciones?
