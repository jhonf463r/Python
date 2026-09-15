"""
P0-B: Trust Root / External-Action Authorization Tests

Tests obligatorios para el gate de autorización externa de acciones.

Objetivo: Demostrar que ninguna ejecución externa de Devin puede ocurrir
sin una autorización externa válida, vinculada, scoped y de un solo uso.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExternalActionAuthorization,
    ExternalActionAuthorizationStatus,
    ToolCard,
    ToolTask,
    ToolType,
)
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _create_authorization(
    task_id: str,
    tool_id: str,
    adapter_key: str,
    assistant_kind: str,
    prompt_digest: str,
    *,
    expires_minutes: int = 60,
) -> ExternalActionAuthorization:
    """Crea una autorización válida."""
    return ExternalActionAuthorization(
        task_id=task_id,
        tool_id=tool_id,
        adapter_key=adapter_key,
        assistant_kind=assistant_kind,
        prompt_digest=prompt_digest,
        status=ExternalActionAuthorizationStatus.VALIDATED,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        approved_by='test_user@example.com',
        reason='Test authorization',
    )


def test_p0_b_01_no_authorization() -> None:
    """TEST 1: No authorization -> adapter not executed externally."""
    print("=== TEST 1: No authorization -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    task = ToolTask(
        task_id='test_task_01',
        tool_id='devin_api',
        title='Test task',
        objective='Test objective',
    )
    
    result = adapter.run(card, task, sandbox=False)
    
    assert result['success'] == False, "Debe fallar sin autorización"
    assert 'authorization' in result['metadata'], "Metadata debe indicar authorization missing"
    assert result['metadata']['authorization'] == 'missing_or_invalid'
    print("OK: Blocked - no authorization")


def test_p0_b_02_valid_authorization() -> None:
    """TEST 2: Valid authorization -> adapter executes (intercepted transport)."""
    print("\n=== TEST 2: Valid authorization -> ALLOWED (intercepted) ===")
    
    from iabv_v15.services.tools import tool_adapters
    original_httpx = tool_adapters.httpx
    
    # Mock httpx
    post_calls = []
    get_calls = []
    
    class MockResponse:
        def __init__(self, status_code: int, json_data: dict | None = None):
            self.status_code = status_code
            self._json_data = json_data or {}
        
        def json(self) -> dict:
            return self._json_data
    
    def mock_post(url: str, *, headers: dict, json: dict, timeout: float) -> MockResponse:
        post_calls.append({'url': url, 'headers': headers, 'json': json})
        return MockResponse(
            status_code=200,
            json_data={'session_id': 'test_session', 'status': 'running'},
        )
    
    def mock_get(url: str, *, headers: dict, params: dict | None = None, timeout: float) -> MockResponse:
        get_calls.append({'url': url, 'headers': headers, 'params': params})
        if '/session/' in url:
            return MockResponse(
                status_code=200,
                json_data={'session_id': 'test_session', 'status': 'finished', 'structured_output': 'Test output'},
            )
        return MockResponse(status_code=200)
    
    mock_httpx = Mock()
    mock_httpx.post = mock_post
    mock_httpx.get = mock_get
    
    try:
        tool_adapters.httpx = mock_httpx
        
        adapter = DevinApiToolAdapter(api_key='test_key')
        
        # Crear autorización válida
        task_id = 'test_task_02'
        tool_id = 'devin_api'
        adapter_key = 'devin_api'
        assistant_kind = 'devin'
        prompt = 'Test objective'
        prompt_digest = adapter._compute_prompt_digest(prompt)
        
        auth = _create_authorization(
            task_id=task_id,
            tool_id=tool_id,
            adapter_key=adapter_key,
            assistant_kind=assistant_kind,
            prompt_digest=prompt_digest,
        )
        
        adapter._external_authorization = auth
        
        card = ToolCard(
            tool_id=tool_id,
            title='Devin',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key=adapter_key,
            available=True,
        )
        
        task = ToolTask(
            task_id=task_id,
            tool_id=tool_id,
            title='Test task',
            objective=prompt,
        )
        
        result = adapter.run(card, task, sandbox=False)
        
        assert result['success'] == True, "Debe ejecutar con autorización válida"
        assert len(post_calls) == 1, "Debe haber exactamente una llamada POST"
        assert len(get_calls) >= 1, "Debe haber al menos una llamada GET"
        print(f"OK: Allowed - HTTP calls intercepted (POST={len(post_calls)}, GET={len(get_calls)})")
        
    finally:
        tool_adapters.httpx = original_httpx


def test_p0_b_03_wrong_task() -> None:
    """TEST 3: Wrong task -> BLOCK."""
    print("\n=== TEST 3: Wrong task -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Autorización para task_A
    auth_task_A = _create_authorization(
        task_id='task_A',
        tool_id='devin_api',
        adapter_key='devin_api',
        assistant_kind='devin',
        prompt_digest=adapter._compute_prompt_digest('prompt A'),
    )
    
    adapter._external_authorization = auth_task_A
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    # Ejecutar task_B
    task_B = ToolTask(
        task_id='task_B',
        tool_id='devin_api',
        title='Test task',
        objective='prompt B',
    )
    
    result = adapter.run(card, task_B, sandbox=False)
    
    assert result['success'] == False, "Debe fallar por task mismatch"
    print("OK: Blocked - wrong task")


def test_p0_b_04_wrong_prompt() -> None:
    """TEST 4: Wrong prompt -> BLOCK."""
    print("\n=== TEST 4: Wrong prompt -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Autorización para prompt A
    auth_prompt_A = _create_authorization(
        task_id='test_task_04',
        tool_id='devin_api',
        adapter_key='devin_api',
        assistant_kind='devin',
        prompt_digest=adapter._compute_prompt_digest('prompt A'),
    )
    
    adapter._external_authorization = auth_prompt_A
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    # Ejecutar con prompt B
    task = ToolTask(
        task_id='test_task_04',
        tool_id='devin_api',
        title='Test task',
        objective='prompt B',  # Prompt diferente
    )
    
    result = adapter.run(card, task, sandbox=False)
    
    assert result['success'] == False, "Debe fallar por prompt digest mismatch"
    print("OK: Blocked - wrong prompt digest")


def test_p0_b_05_wrong_adapter() -> None:
    """TEST 5: Wrong adapter/tool -> BLOCK."""
    print("\n=== TEST 5: Wrong adapter/tool -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Autorización para devin_api
    auth_devin = _create_authorization(
        task_id='test_task_05',
        tool_id='devin_api',
        adapter_key='devin_api',
        assistant_kind='devin',
        prompt_digest=adapter._compute_prompt_digest('test prompt'),
    )
    
    adapter._external_authorization = auth_devin
    
    # Card con diferente adapter_key
    card = ToolCard(
        tool_id='another_tool',
        title='Another Tool',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='another_adapter',
        available=True,
    )
    
    task = ToolTask(
        task_id='test_task_05',
        tool_id='another_tool',
        title='Test task',
        objective='test prompt',
    )
    
    result = adapter.run(card, task, sandbox=False)
    
    assert result['success'] == False, "Debe fallar por adapter/tool mismatch"
    print("OK: Blocked - wrong adapter/tool")


def test_p0_b_06_expired() -> None:
    """TEST 6: Expired -> BLOCK."""
    print("\n=== TEST 6: Expired -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Autorización expirada
    auth_expired = _create_authorization(
        task_id='test_task_06',
        tool_id='devin_api',
        adapter_key='devin_api',
        assistant_kind='devin',
        prompt_digest=adapter._compute_prompt_digest('test prompt'),
        expires_minutes=-1,  # Expirada
    )
    
    adapter._external_authorization = auth_expired
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    task = ToolTask(
        task_id='test_task_06',
        tool_id='devin_api',
        title='Test task',
        objective='test prompt',
    )
    
    result = adapter.run(card, task, sandbox=False)
    
    assert result['success'] == False, "Debe fallar por autorización expirada"
    print("OK: Blocked - expired authorization")


def test_p0_b_07_replay() -> None:
    """TEST 7: Replay -> BLOCK."""
    print("\n=== TEST 7: Replay -> BLOCKED ===")
    
    from iabv_v15.services.tools import tool_adapters
    original_httpx = tool_adapters.httpx
    
    # Mock httpx
    post_calls = []
    get_calls = []
    
    class MockResponse:
        def __init__(self, status_code: int, json_data: dict | None = None):
            self.status_code = status_code
            self._json_data = json_data or {}
        
        def json(self) -> dict:
            return self._json_data
    
    def mock_post(url: str, *, headers: dict, json: dict, timeout: float) -> MockResponse:
        post_calls.append({'url': url, 'headers': headers, 'json': json})
        return MockResponse(
            status_code=200,
            json_data={'session_id': 'test_session', 'status': 'running'},
        )
    
    def mock_get(url: str, *, headers: dict, params: dict | None = None, timeout: float) -> MockResponse:
        get_calls.append({'url': url, 'headers': headers, 'params': params})
        if '/session/' in url:
            return MockResponse(
                status_code=200,
                json_data={'session_id': 'test_session', 'status': 'finished', 'structured_output': 'Test output'},
            )
        return MockResponse(status_code=200)
    
    mock_httpx = Mock()
    mock_httpx.post = mock_post
    mock_httpx.get = mock_get
    
    try:
        tool_adapters.httpx = mock_httpx
        
        adapter = DevinApiToolAdapter(api_key='test_key')
        
        auth = _create_authorization(
            task_id='test_task_07',
            tool_id='devin_api',
            adapter_key='devin_api',
            assistant_kind='devin',
            prompt_digest=adapter._compute_prompt_digest('test prompt'),
        )
        
        adapter._external_authorization = auth
        
        card = ToolCard(
            tool_id='devin_api',
            title='Devin',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            available=True,
        )
        
        task = ToolTask(
            task_id='test_task_07',
            tool_id='devin_api',
            title='Test task',
            objective='test prompt',
        )
        
        # Primera ejecución
        result1 = adapter.run(card, task, sandbox=False)
        assert result1['success'] == True, "Primera ejecución debe tener éxito"
        
        # Segunda ejecución (replay)
        result2 = adapter.run(card, task, sandbox=False)
        assert result2['success'] == False, "Segunda ejecución debe fallar (autorización consumida)"
        
        print("OK: Blocked - replay attack prevented")
        
    finally:
        tool_adapters.httpx = original_httpx


def test_p0_b_08_broker_unavailable() -> None:
    """TEST 8: Broker unavailable -> BLOCK."""
    print("\n=== TEST 8: Broker unavailable -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Simular broker unavailable (authorization es None)
    adapter._external_authorization = None
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    task = ToolTask(
        task_id='test_task_08',
        tool_id='devin_api',
        title='Test task',
        objective='test prompt',
    )
    
    result = adapter.run(card, task, sandbox=False)
    
    assert result['success'] == False, "Debe fallar sin autorización (broker unavailable)"
    print("OK: Blocked - broker unavailable")


def test_p0_b_09_broker_rejection() -> None:
    """TEST 9: Broker rejection -> BLOCK."""
    print("\n=== TEST 9: Broker rejection -> BLOCKED ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Autorización rechazada
    auth_rejected = _create_authorization(
        task_id='test_task_09',
        tool_id='devin_api',
        adapter_key='devin_api',
        assistant_kind='devin',
        prompt_digest=adapter._compute_prompt_digest('test prompt'),
    )
    auth_rejected.status = ExternalActionAuthorizationStatus.REJECTED
    
    adapter._external_authorization = auth_rejected
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    task = ToolTask(
        task_id='test_task_09',
        tool_id='devin_api',
        title='Test task',
        objective='test prompt',
    )
    
    result = adapter.run(card, task, sandbox=False)
    
    assert result['success'] == False, "Debe fallar por autorización rechazada"
    print("OK: Blocked - broker rejection")


def test_p0_b_10_direct_bootstrap_bypass() -> None:
    """TEST 10: Direct bootstrap bypass -> BLOCK."""
    print("\n=== TEST 10: Direct bootstrap bypass -> BLOCKED ===")
    
    from iabv_v15.bootstrap import _devin_create_session, _devin_send_message
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Sin autorización
    session_id = _devin_create_session(adapter, 'test prompt', authorization=None)
    assert session_id == '', "Deve fallar sin autorización"
    
    # Con autorización inválida
    auth_invalid = _create_authorization(
        task_id='test_task_10',
        tool_id='devin_api',
        adapter_key='devin_api',
        assistant_kind='devin',
        prompt_digest='wrong_digest',
    )
    session_id_invalid = _devin_create_session(adapter, 'test prompt', authorization=auth_invalid)
    assert session_id_invalid == '', "Deve fallar con autorización inválida"
    
    # Test send message
    send_result = _devin_send_message(adapter, 'test_session', 'test message', authorization=None)
    assert send_result == False, "Deve fallar sin autorización"
    
    print("OK: Blocked - direct bootstrap bypass prevented")


def test_p0_b_11_sandbox() -> None:
    """TEST 11: Sandbox -> sin requerir autorización externa real."""
    print("\n=== TEST 11: Sandbox -> allowed without real authorization ===")
    
    adapter = DevinApiToolAdapter(api_key='test_key')
    
    # Sin autorización
    adapter._external_authorization = None
    
    card = ToolCard(
        tool_id='devin_api',
        title='Devin',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
    )
    
    task = ToolTask(
        task_id='test_task_11',
        tool_id='devin_api',
        title='Test task',
        objective='test prompt',
    )
    
    result = adapter.run(card, task, sandbox=True)
    
    assert result['success'] == True, "Sandbox debe permitir ejecución sin autorización real"
    assert result['metadata']['sandbox'] == True, "Metadata debe indicar sandbox"
    print("OK: Allowed - sandbox mode does not require real authorization")


def test_p0_b_12_authorization_survives_no_substitution() -> None:
    """TEST 12: Authorization survives no substitution."""
    print("\n=== TEST 12: Authorization survives no substitution ===")
    
    from iabv_v15.services.tools import tool_adapters
    original_httpx = tool_adapters.httpx
    
    # Mock httpx
    class MockResponse:
        def __init__(self, status_code: int, json_data: dict | None = None):
            self.status_code = status_code
            self._json_data = json_data or {}
        
        def json(self) -> dict:
            return self._json_data
    
    def mock_post(url: str, *, headers: dict, json: dict, timeout: float) -> MockResponse:
        return MockResponse(
            status_code=200,
            json_data={'session_id': 'test_session', 'status': 'running'},
        )
    
    def mock_get(url: str, *, headers: dict, params: dict | None = None, timeout: float) -> MockResponse:
        if '/session/' in url:
            return MockResponse(
                status_code=200,
                json_data={'session_id': 'test_session', 'status': 'finished', 'structured_output': 'Test output'},
            )
        return MockResponse(status_code=200)
    
    mock_httpx = Mock()
    mock_httpx.post = mock_post
    mock_httpx.get = mock_get
    
    try:
        tool_adapters.httpx = mock_httpx
        
        adapter = DevinApiToolAdapter(api_key='test_key')
        
        auth = _create_authorization(
            task_id='test_task_12',
            tool_id='devin_api',
            adapter_key='devin_api',
            assistant_kind='devin',
            prompt_digest=adapter._compute_prompt_digest('test prompt'),
        )
        
        # Intentar modificar superficialmente la autorización
        auth_copy = auth.model_copy(update={'metadata': {'hacked': True}})
        adapter._external_authorization = auth_copy
        
        card = ToolCard(
            tool_id='devin_api',
            title='Devin',
            tool_type=ToolType.MCP_CLIENT,
            adapter_key='devin_api',
            available=True,
        )
        
        task = ToolTask(
            task_id='test_task_12',
            tool_id='devin_api',
            title='Test task',
            objective='test prompt',
        )
        
        result = adapter.run(card, task, sandbox=False)
        
        # La modificación superficial no debería afectar la validación del binding
        # La autorización debe ser consumida correctamente
        assert result['success'] == True, "Debe ejecutar con autorización válida (binding intacto)"
        assert auth_copy.status == ExternalActionAuthorizationStatus.CONSUMED, "Autorización debe ser consumida"
        print("OK: Allowed - binding validation survives metadata modification")
        
    finally:
        tool_adapters.httpx = original_httpx


if __name__ == '__main__':
    print("=== P0-B: External Action Authorization Tests ===")
    print()
    
    test_p0_b_01_no_authorization()
    test_p0_b_02_valid_authorization()
    test_p0_b_03_wrong_task()
    test_p0_b_04_wrong_prompt()
    test_p0_b_05_wrong_adapter()
    test_p0_b_06_expired()
    test_p0_b_07_replay()
    test_p0_b_08_broker_unavailable()
    test_p0_b_09_broker_rejection()
    test_p0_b_10_direct_bootstrap_bypass()
    test_p0_b_11_sandbox()
    test_p0_b_12_authorization_survives_no_substitution()
    
    print("\n=== ALL TESTS PASSED ===")
