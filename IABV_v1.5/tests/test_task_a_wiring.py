"""Tests de integracion end-to-end del cableado Tarea A -> Tarea B.

Los tests existentes en `test_control_center_viewmodel.py` (`test_control_center_emits_*`)
verifican que los ViewModels pueden *emitir* las 5 senales Tarea A. Pero no
verifican que `AppBootstrap._wire_task_a_signals()` haya registrado
efectivamente los handlers en los 4 servicios backend (`CredentialBroker`,
`ClarificationRequestService`, `EnvironmentBootstrapService`,
`ProviderHealthRouter`).

Estos tests cierran ese hueco: invocan las APIs publicas de cada servicio
(`request`, `_prompt_handler`, `_activity_handler`, `_listener`) con un
payload de prueba y verifican que ambos ViewModels (`control_center_viewmodel`
y `evolution_center_viewmodel`) reciben el payload por la senal Qt
correspondiente.

No tocan bootstrap.py, ViewModels, ni QML. Solo agregan cobertura del
contrato de wiring existente.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap


def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = Path.cwd() / 'data' / f'{name}_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap


def _cleanup_bootstrap(bootstrap: AppBootstrap) -> None:
    workspace = getattr(bootstrap, '_test_workspace', None)
    stop = getattr(bootstrap, 'stop', None)
    if callable(stop):
        stop()
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)


def _capture_signal(viewmodel, signal_name: str) -> dict:
    """Conecta un slot a la senal del VM y retorna un dict donde se captura el payload."""
    captured: dict = {'payload': None, 'count': 0}

    def _slot(payload):
        captured['payload'] = payload
        captured['count'] += 1

    getattr(viewmodel, signal_name).connect(_slot)
    return captured


def test_bootstrap_registers_credential_prompt_handler_on_broker() -> None:
    """CredentialBroker.request() -> ambos VMs reciben credentialPromptRequested."""
    bootstrap = _make_bootstrap('test_wiring_credential')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'credentialPromptRequested')
        ec_cap = _capture_signal(ec, 'credentialPromptRequested')

        # El handler fue registrado por _wire_task_a_signals().
        assert bootstrap.credential_broker._handler is not None

        bootstrap.credential_broker.request(
            domain='example.com',
            reason='login de prueba',
            username_hint='user@example.com',
        )

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
        assert cc_cap['payload']['domain'] == 'example.com'
        assert cc_cap['payload']['reason'] == 'login de prueba'
        assert cc_cap['payload']['username_hint'] == 'user@example.com'
        assert ec_cap['payload'] == cc_cap['payload']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_bootstrap_registers_clarification_prompt_handler() -> None:
    """ClarificationRequestService._prompt_handler() -> ambos VMs reciben clarificationRequested."""
    bootstrap = _make_bootstrap('test_wiring_clarification')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'clarificationRequested')
        ec_cap = _capture_signal(ec, 'clarificationRequested')

        handler = bootstrap.clarification_request_service._handler
        assert handler is not None

        payload = {
            'id': 'req-1',
            'question': 'Cual opcion prefieres?',
            'options': ['A', 'B'],
            'context': 'test-context',
        }
        handler(payload)

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
        assert cc_cap['payload']['question'] == 'Cual opcion prefieres?'
        assert cc_cap['payload']['options'] == ['A', 'B']
        assert ec_cap['payload'] == cc_cap['payload']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_bootstrap_registers_missing_dependency_handler() -> None:
    """EnvironmentBootstrapService._prompt_handler() -> ambos VMs reciben missingDependencyRequested."""
    bootstrap = _make_bootstrap('test_wiring_missing_dep')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'missingDependencyRequested')
        ec_cap = _capture_signal(ec, 'missingDependencyRequested')

        handler = bootstrap.environment_bootstrap_service._prompt_handler
        assert handler is not None

        payload = {
            'id': 'dep-1',
            'package_name': 'numpy',
            'manager': 'pip',
            'reason': 'requerido para analisis',
        }
        handler(payload)

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
        assert cc_cap['payload']['package_name'] == 'numpy'
        assert cc_cap['payload']['manager'] == 'pip'
        assert ec_cap['payload'] == cc_cap['payload']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_bootstrap_registers_background_activity_handler() -> None:
    """EnvironmentBootstrapService._activity_handler() -> ambos VMs reciben backgroundActivityChanged."""
    bootstrap = _make_bootstrap('test_wiring_activity')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'backgroundActivityChanged')
        ec_cap = _capture_signal(ec, 'backgroundActivityChanged')

        handler = bootstrap.environment_bootstrap_service._activity_handler
        assert handler is not None

        payload = {
            'text': 'Instalando numpy...',
            'progress': 42,
            'status': 'running',
            'details': ['step 1/3', 'step 2/3'],
        }
        handler(payload)

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
        assert cc_cap['payload']['progress'] == 42
        assert cc_cap['payload']['status'] == 'running'
        assert ec_cap['payload'] == cc_cap['payload']
    finally:
        _cleanup_bootstrap(bootstrap)


def test_bootstrap_registers_provider_health_listener() -> None:
    """ProviderHealthRouter._listener() -> ambos VMs reciben providerHealthChanged."""
    bootstrap = _make_bootstrap('test_wiring_provider_health')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'providerHealthChanged')
        ec_cap = _capture_signal(ec, 'providerHealthChanged')

        listener = bootstrap.provider_health_router._listener
        assert listener is not None

        snapshot = [
            {'name': 'Ollama', 'status': 'verde', 'latency_ms': 12.3, 'detail': 'Disponible.'},
            {'name': 'Embeddings', 'status': 'gris', 'latency_ms': 0.0, 'detail': 'inactivo'},
        ]
        listener(snapshot)

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
        assert cc_cap['payload'] == snapshot
        assert ec_cap['payload'] == snapshot
    finally:
        _cleanup_bootstrap(bootstrap)


def test_bootstrap_wires_handlers_on_all_four_services() -> None:
    """Sanity: los 4 servicios Tarea A tienen handler registrado tras bootstrap."""
    bootstrap = _make_bootstrap('test_wiring_sanity')
    try:
        assert bootstrap.credential_broker._handler is not None
        assert bootstrap.clarification_request_service._handler is not None
        assert bootstrap.environment_bootstrap_service._prompt_handler is not None
        assert bootstrap.environment_bootstrap_service._activity_handler is not None
        assert bootstrap.provider_health_router._listener is not None
    finally:
        _cleanup_bootstrap(bootstrap)
