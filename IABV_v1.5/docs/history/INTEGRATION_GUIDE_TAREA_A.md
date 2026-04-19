# Guía de Integración - Tarea A (Backend) con Tarea B (UI)

**Documento para equipo de Tarea A**

> **Estado:** RESUELTO. Los 7 items del checklist estan implementados en
> `AppBootstrap._wire_task_a_signals()` (`src/iabv_v15/bootstrap.py` lineas
> 768 y 779-815). Los 4 servicios backend (`CredentialBroker`,
> `ClarificationRequestService`, `EnvironmentBootstrapService`,
> `ProviderHealthRouter`) registran handlers que re-emiten los payloads como
> senales Qt de ambos ViewModels. Tests de integracion end-to-end en
> `tests/test_task_a_wiring.py` y tests de emision de senal en
> `tests/test_control_center_viewmodel.py` (`test_control_center_emits_*`).
> Archivado en `docs/history/` como referencia.
>
> Nota sobre el item 4: el checklist menciona `ProviderRouter` pero el wiring
> real usa `ProviderHealthRouter` — un servicio dedicado a polling de salud
> que es quien produce `providerHealthChanged`. `ProviderRouter` sigue siendo
> el que decide rutas de inferencia y no debe emitir senales UI.

---

## 🎯 Resumen

Tarea B implementó los componentes UI evolutivos. Esta guía explica cómo Tarea A debe conectar sus servicios backend a las señales UI.

---

## 📡 Señales Disponibles (ViewModels)

### ControlCenterViewModel & EvolutionCenterViewModel

```python
# 1. Solicitar credenciales al usuario
credentialPromptRequested = Signal(dict)
# Payload: {domain: str, reason: str, username_hint: str}
# Retorno esperado: Conectar a onCredentialProvided(payload: dict)

# 2. Solicitar aclaración al usuario
clarificationRequested = Signal(dict)
# Payload: {id: str, question: str, options: List[str], context: str}
# Retorno esperado: Conectar a onClarificationResponse(payload: dict)

# 3. Solicitar aprobación de dependencia
missingDependencyRequested = Signal(dict)
# Payload: {package_name: str, manager: str, reason: str}
# Retorno esperado: Conectar a onDependencyApproved/Rejected(payload: dict)

# 4. Actualizar actividad en segundo plano
backgroundActivityChanged = Signal(dict)
# Payload: {text: str, progress: float (0-100), status: str, details: List[str]}

# 5. Actualizar estado de providers
providerHealthChanged = Signal(list)
# Payload: [{name: str, status: str, latency: float, detail: str}]
```

---

## 🔌 Cómo Conectar Servicios Backend

### Ejemplo: CredentialBroker → UI

```python
# En tu servicio de backend (services/)
from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

class CredentialBroker:
    def __init__(self, control_center_vm: ControlCenterViewModel):
        self._vm = control_center_vm
        self._pending_requests = {}
        
        # Conectar retorno del usuario
        self._vm.onCredentialProvided.connect(self._handle_credential_response)
        self._vm.onCredentialDelegated.connect(self._handle_delegation)
    
    def request_credential(self, domain: str, reason: str) -> Future:
        """Solicita credencial al usuario."""
        request_id = str(uuid4())
        future = Future()
        self._pending_requests[request_id] = future
        
        # Emitir señal al UI
        self._vm.credentialPromptRequested.emit({
            'domain': domain,
            'reason': reason,
            'username_hint': '',  # Opcional
        })
        
        return future
    
    def _handle_credential_response(self, payload: dict):
        """Callback cuando usuario proporciona credencial."""
        # Resolver future pendiente
        pass
```

### Ejemplo: ClarificationRequestService → UI

```python
class ClarificationRequestService:
    def request_clarification(self, question: str, options: list, context: str) -> Future:
        request_id = str(uuid4())
        
        self._vm.clarificationRequested.emit({
            'id': request_id,
            'question': question,
            'options': options,
            'context': context
        })
        
        # Retorno via onClarificationResponse
        return self._register_pending(request_id)
```

### Ejemplo: ProviderRouter → UI

```python
class ProviderRouter:
    def _update_health_ui(self):
        """Actualiza panel de salud en UI."""
        health = self.health_snapshot()
        
        providers = [
            {
                'name': h.provider_name,
                'status': h.status,  # 'ready', 'degraded', 'unavailable'
                'latency': h.latency_ms,
                'detail': h.detail
            }
            for h in health
        ]
        
        self._vm.providerHealthChanged.emit(providers)
```

---

## 🔄 Flujo de Datos

```
┌─────────────────┐    emit Signal     ┌──────────────────┐
│  Servicio       │ ─────────────────> │  ViewModel       │
│  Backend        │                    │  (UI Layer)      │
│  (Tarea A)      │                    │                  │
└─────────────────┘                    └──────────────────┘
                                              │
                                              │ expose to QML
                                              v
                                       ┌──────────────────┐
                                       │  QML Components  │
                                       │  (Tarea B)       │
                                       │                  │
                                       │  • Dialogs       │
                                       │  • ToolHealthPanel│
                                       │  • ActivityChip  │
                                       └──────────────────┘
                                              │
                                              │ user action
                                              v
                                       ┌──────────────────┐
                                       │  Slot Response   │
                                       │  (ViewModel)     │
                                       └──────────────────┘
                                              │
                                              │ callback
                                              v
                                       ┌──────────────────┐
                                       │  Servicio        │
                                       │  Backend         │
                                       └──────────────────┘
```

---

## 📝 Checklist de Integración para Tarea A

- [x] `CredentialBroker` conecta a `credentialPromptRequested` (bootstrap.py:801)
- [x] `ClarificationRequestService` conecta a `clarificationRequested` (bootstrap.py:804)
- [x] `EnvironmentBootstrapService` conecta a `missingDependencyRequested` (bootstrap.py:807)
- [x] `ProviderHealthRouter` actualiza via `providerHealthChanged` (bootstrap.py:813) — ver nota al inicio
- [x] `EnvironmentBootstrapService.register_activity_handler` usa `backgroundActivityChanged` (bootstrap.py:810)
- [x] Todos los callbacks están registrados via `AppBootstrap._wire_task_a_signals()`
- [x] Tests de integración pasan (`tests/test_task_a_wiring.py`, `tests/test_control_center_viewmodel.py::test_control_center_emits_*`)

---

## 🎨 Referencia de Estados UI

### ToolHealthPanel Status Colors
```
'green' / 'ready' / 'available'     → Verde (#8ccf8b)
'yellow' / 'degraded' / 'warning' → Amarillo (#d9b15f)
'red' / 'error' / 'failed'         → Rojo (#cf7e7e)
'idle' / 'optional_inactive'       → Gris (#6b7b8c)
```

### BackgroundActivityChip Status
```
'idle'      → Oculto
'running'   → Visible + pulsing animation
'completed' → Visible + checkmark verde
'failed'    → Visible + X rojo
```

---

## 🚀 Próximos Pasos

1. Implementar stubs/fakes que emitan señales para testing
2. Crear tests de integración UI+Backend
3. Documentar casos de uso específicos (Wplay, MercadoLibre, etc.)

---

**Contacto Tarea B:** UI lista para consumir señales.  
**Archivos clave Tarea B:**
- `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`
- `src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py`
- `src/iabv_v15/ui/qml/components/*.qml`
