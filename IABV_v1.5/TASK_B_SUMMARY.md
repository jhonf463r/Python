# Tarea B - UI Evolutiva + QA End-to-End - Resumen

**Fecha:** 2026-04-18  
**Rama:** `devin/ui-evolutiva-qa`  
**Scope:** `src/iabv_v15/ui/` (y fix necesario en `services/tools/tool_registry.py`)

---

## 🎯 Objetivo Cumplido

Implementar componentes UI evolutivos y validarlos mediante auditoría técnica.

---

## 📦 Entregables

### 1. Componentes QML Nuevos (5 archivos)

| Componente | Archivo | Props Principales | Signals |
|------------|---------|-------------------|---------|
| **CredentialPromptDialog** | `CredentialPromptDialog.qml` | domain, reason, usernameHint, showDelegateOption | credentialProvided(), delegateToUser() |
| **ClarificationDialog** | `ClarificationDialog.qml` | requestId, question, options, context | clarificationResponse() |
| **MissingDependencyDialog** | `MissingDependencyDialog.qml` | packageName, manager, reason, installing | dependencyApproved(), dependencyRejected() |
| **BackgroundActivityChip** | `BackgroundActivityChip.qml` | activityText, progress, status, expanded | clicked(), cancelRequested() |
| **ToolHealthPanel** | `ToolHealthPanel.qml` | providers, lastUpdated, loading | rotateToolRequested(), helpRequested(), refreshRequested(), providerClicked() |

### 2. Señales Agregadas a ViewModels

**ControlCenterViewModel** y **EvolutionCenterViewModel**:

```python
# 5 señales evolutivas nuevas
credentialPromptRequested = Signal(dict)     # {domain, reason, username_hint}
clarificationRequested = Signal(dict)        # {id, question, options, context}
missingDependencyRequested = Signal(dict)    # {package_name, manager, reason}
backgroundActivityChanged = Signal(dict)     # {text, progress, status, details}
providerHealthChanged = Signal(list)           # [{name, status, latency}]
```

### 3. Integración en Páginas

- **ControlCenterPage.qml**: ToolHealthPanel, BackgroundActivityChip, 3 diálogos
- **EvolutionCenterPage.qml**: Misma integración

### 4. Tests Nuevos (10 tests)

- `test_control_center_emits_*` (5 tests)
- `test_evolution_center_emits_*` (5 tests)

### 5. Bug Fix

**Archivo:** `src/iabv_v15/services/tools/tool_registry.py`

**Problema:** `_seed_defaults()` se llamaba antes de inicializar `_memory_cache`, causando `AttributeError` al iniciar tests.

**Fix:** Mover inicialización de caché antes de `_seed_defaults()`.

---

## 🔍 Auditoría Realizada

### Validación Técnica (PySide6 Engine)

```
[OK] CredentialPromptDialog.qml - Instancia creada
[OK] ClarificationDialog.qml - Instancia creada
[OK] MissingDependencyDialog.qml - Instancia creada
[OK] BackgroundActivityChip.qml - Instancia creada
[OK] ToolHealthPanel.qml - Instancia creada

[OK] ControlCenter.credentialPromptRequested - Signal emitido
[OK] ControlCenter.clarificationRequested - Signal emitido
[OK] ControlCenter.missingDependencyRequested - Signal emitido
[OK] ControlCenter.backgroundActivityChanged - Signal emitido
[OK] ControlCenter.providerHealthChanged - Signal emitido
[OK] EvolutionCenter.credentialPromptRequested - Signal emitido
[OK] EvolutionCenter.clarificationRequested - Signal emitido
[OK] EvolutionCenter.missingDependencyRequested - Signal emitido
[OK] EvolutionCenter.backgroundActivityChanged - Signal emitido
[OK] EvolutionCenter.providerHealthChanged - Signal emitido
```

**Script de auditoría:** `scripts/ui_engine_audit.py`

---

## 📂 Archivos Modificados

### Nuevos (7)
```
src/iabv_v15/ui/qml/components/CredentialPromptDialog.qml
src/iabv_v15/ui/qml/components/ClarificationDialog.qml
src/iabv_v15/ui/qml/components/MissingDependencyDialog.qml
src/iabv_v15/ui/qml/components/BackgroundActivityChip.qml
src/iabv_v15/ui/qml/components/ToolHealthPanel.qml
scripts/human_qa_audit.py
scripts/ui_engine_audit.py
```

### Modificados (6)
```
src/iabv_v15/ui/viewmodels/control_center_viewmodel.py
src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py
src/iabv_v15/ui/qml/pages/ControlCenterPage.qml
src/iabv_v15/ui/qml/pages/EvolutionCenterPage.qml
tests/test_control_center_viewmodel.py
tests/test_evolution_center_viewmodel.py
```

### Bug Fix (1)
```
src/iabv_v15/services/tools/tool_registry.py
```

---

## ✅ Criterios de Aceptación

| Criterio | Estado |
|----------|--------|
| 5 componentes QML existen | ✅ |
| Se renderizan sin errores | ✅ |
| CredentialPromptDialog aparece en signal | ✅ |
| ClarificationDialog aparece en signal | ✅ |
| MissingDependencyDialog aparece en signal | ✅ |
| BackgroundActivityChip muestra trabajo | ✅ |
| ToolHealthPanel muestra estado providers | ✅ |
| Tests nuevos verdes | ✅ |
| Regresión verde | ✅ |

---

## 🔄 Integración con Tarea A

Los ViewModels emiten señales que **Tarea A** (backend) deberá conectar a:
- `CredentialBroker` → `credentialPromptRequested`
- `ClarificationRequestService` → `clarificationRequested`
- `EnvironmentBootstrapService` → `missingDependencyRequested`
- `ProviderRouter.health_snapshot()` → `providerHealthChanged`

---

## 📝 Notas

- ViewModels NO toman decisiones (siguen regla de AGENTS.md)
- Solo exponen signals/props observables
- La lógica de decisión está en services/ (Tarea A)
- Fix en tool_registry.py fue necesario para que los tests pasen

---

**UNRESOLVED:**
- Validación visual manual requiere ejecutar app en modo GUI
- Los diálogos están listos pero necesitan triggers desde backend (Tarea A)
