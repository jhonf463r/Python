"""Tests for KnowledgeOperationalExecutor - knowledge.query domain execution."""
from __future__ import annotations

from unittest.mock import Mock, MagicMock

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    ExecutionPlaybook,
    IntentDisposition,
    PlaybookStep,
    RunStatus,
    TaskContext,
    TaskIntent,
    TaskRole,
    ToolCapability,
)
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService, OperationalExecutorResult
from iabv_v15.services.adaptive.knowledge_operational_executor import KnowledgeOperationalExecutor
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


def _knowledge_session(*, with_context: bool = True) -> AdaptiveSession:
    """Create a test session for knowledge.query."""
    if with_context:
        context = TaskContext(
            knowledge_hits=[
                {'title': 'Test knowledge', 'summary': 'Test summary'},
            ],
            recent_runs=[
                {'run_id': 'test-run-1', 'status': 'success', 'pack_id': 'knowledge.query'},
            ],
        )
    else:
        context = TaskContext(
            knowledge_hits=[],
            recent_runs=[],
        )
    
    return AdaptiveSession(
        user_goal='¿Qué sabes sobre el sistema de archivos?',
        intent=TaskIntent(
            intent_key='knowledge.query',
            title='Consulta local',
            disposition=IntentDisposition.ANSWER_NOW,
            detected_role=TaskRole.KNOWLEDGE,
        ),
        chosen_pack_id='knowledge.query',
        chosen_pack_title='Consulta local con contexto',
        status=AdaptiveSessionStatus.READY_TO_EXECUTE,
        context=context,
        playbook=ExecutionPlaybook(
            goal='¿Qué sabes sobre el sistema de archivos?',
            pack_id='knowledge.query',
            summary='Pack Consulta local con contexto.',
            status=AdaptiveSessionStatus.READY_TO_EXECUTE,
            next_phase='execute',
            steps=[
                PlaybookStep(
                    phase_key='execute',
                    title='Ejecutar fase',
                    description='Ejecutar consulta de conocimiento.',
                    status=RunStatus.PARTIAL,
                    executable=True,
                    simulation_only=False,
                )
            ],
        ),
    )


def _mock_inference_result() -> MagicMock:
    """Create a mock InferenceResult."""
    result = MagicMock()
    result.summary = 'El sistema de archivos está basado en SQLite con persistencia JSON para artefactos.'
    result.sources = ['knowledge:file_system']
    result.raw_output = {'knowledge_hits': [{'title': 'file_system'}]}
    result.used_fallback = False
    return result


def _mock_role_route() -> MagicMock:
    """Create a mock RoleRoute."""
    route = MagicMock()
    route.model_dump.return_value = {'task_role': 'knowledge', 'provider_name': 'ollama'}
    return route


def test_knowledge_executor_supports_knowledge_query_pack() -> None:
    """Test that KnowledgeOperationalExecutor supports knowledge.query pack."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    
    assert executor.supports(session) is True


def test_knowledge_executor_supports_knowledge_role() -> None:
    """Test that KnowledgeOperationalExecutor supports TaskRole.KNOWLEDGE."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    session.chosen_pack_id = None  # No pack specified
    session.intent.detected_role = TaskRole.KNOWLEDGE
    
    assert executor.supports(session) is True


def test_knowledge_executor_rejects_other_packs() -> None:
    """Test that KnowledgeOperationalExecutor rejects non-knowledge packs."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    session.chosen_pack_id = 'browser.generic'
    
    assert executor.supports(session) is False


def test_knowledge_executor_describes_capability() -> None:
    """Test that executor describes its capability correctly."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    
    description = executor.describe(session)
    
    assert 'Consulta local de conocimiento' in description
    assert 'KnowledgeRepository' in description
    assert 'búsqueda semántica' in description


def test_knowledge_executor_describes_insufficient_context() -> None:
    """Test that executor reports insufficient context when user_goal is empty."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    session.user_goal = ""  # Empty user goal
    
    description = executor.describe(session)
    
    # With empty user_goal, it should report insufficient context
    assert 'insuficiente' in description.lower()


def test_knowledge_executor_executes_with_sufficient_context() -> None:
    """Test that executor executes knowledge query when context is available."""
    mock_router = Mock(spec=LocalRoleRouter)
    mock_router.execute_knowledge_query.return_value = (
        _mock_role_route(),
        _mock_inference_result(),
    )
    
    executor = KnowledgeOperationalExecutor(mock_router)
    session = _knowledge_session()
    
    result = executor.execute(session)
    
    assert result.executed is True
    assert result.status == RunStatus.SUCCESS
    assert result.summary == 'El sistema de archivos está basado en SQLite con persistencia JSON para artefactos.'
    assert result.metadata['knowledge_hits_count'] == 1
    assert result.metadata['sources'] == ['knowledge:file_system']
    assert result.metadata['used_fallback'] is False
    
    # Verify that execute_knowledge_query was called
    mock_router.execute_knowledge_query.assert_called_once()
    
    # Verify that the InferenceRequest was constructed correctly
    call_args = mock_router.execute_knowledge_query.call_args
    request = call_args[0][0]
    assert request.user_goal == '¿Qué sabes sobre el sistema de archivos?'
    assert request.task_role == TaskRole.KNOWLEDGE
    assert request.read_only_sql is True
    assert ToolCapability.KNOWLEDGE_SEARCH in request.allowed_tools
    assert ToolCapability.EMBEDDINGS in request.allowed_tools


def test_knowledge_executor_executes_with_empty_context() -> None:
    """Test that executor executes even when context is empty (no pre-existing knowledge or runs).
    
    The legacy route _route_knowledge() performs its own retrieval via
    KnowledgeRepository.search() and EmbeddingIndexService.search(), so
    pre-existing context is useful but NOT required for execution.
    """
    mock_router = Mock(spec=LocalRoleRouter)
    mock_router.execute_knowledge_query.return_value = (
        _mock_role_route(),
        _mock_inference_result(),
    )
    
    executor = KnowledgeOperationalExecutor(mock_router)
    session = _knowledge_session(with_context=False)
    
    result = executor.execute(session)
    
    # Should execute even with empty context
    assert result.executed is True
    assert result.status == RunStatus.SUCCESS
    assert result.summary == 'El sistema de archivos está basado en SQLite con persistencia JSON para artefactos.'
    
    # Verify that execute_knowledge_query WAS called
    mock_router.execute_knowledge_query.assert_called_once()


def test_knowledge_executor_fails_with_empty_user_goal() -> None:
    """Test that executor returns PARTIAL when user_goal is empty."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    session.user_goal = ""  # Empty user goal
    
    result = executor.execute(session)
    
    assert result.executed is False
    assert result.status == RunStatus.PARTIAL
    assert 'Contexto insuficiente' in result.summary
    assert result.metadata['precondition'] == 'insufficient_context'
    
    # Verify that execute_knowledge_query was NOT called
    mock_router.execute_knowledge_query.assert_not_called()


def test_knowledge_executor_fails_with_null_context() -> None:
    """Test that executor returns PARTIAL when context is None."""
    mock_router = Mock(spec=LocalRoleRouter)
    executor = KnowledgeOperationalExecutor(mock_router)
    
    session = _knowledge_session()
    session.context = None  # No context at all
    
    result = executor.execute(session)
    
    assert result.executed is False
    assert result.status == RunStatus.PARTIAL
    assert 'Contexto insuficiente' in result.summary
    assert result.metadata['precondition'] == 'insufficient_context'
    
    # Verify that execute_knowledge_query was NOT called
    mock_router.execute_knowledge_query.assert_not_called()


def test_knowledge_executor_handles_exceptions() -> None:
    """Test that executor handles exceptions from LocalRoleRouter."""
    mock_router = Mock(spec=LocalRoleRouter)
    mock_router.execute_knowledge_query.side_effect = Exception('Router failure')
    
    executor = KnowledgeOperationalExecutor(mock_router)
    session = _knowledge_session()
    
    result = executor.execute(session)
    
    assert result.executed is False
    assert result.status == RunStatus.FAILED
    assert 'Error en ejecución de knowledge query' in result.summary
    assert result.metadata['error'] == 'Router failure'
    assert result.metadata['error_type'] == 'Exception'


def test_knowledge_executor_handles_fallback_from_inference() -> None:
    """Test that executor correctly handles fallback from model inference."""
    mock_router = Mock(spec=LocalRoleRouter)
    
    # Create a result with fallback
    fallback_result = _mock_inference_result()
    fallback_result.used_fallback = True
    
    mock_router.execute_knowledge_query.return_value = (
        _mock_role_route(),
        fallback_result,
    )
    
    executor = KnowledgeOperationalExecutor(mock_router)
    session = _knowledge_session()
    
    result = executor.execute(session)
    
    assert result.executed is True
    assert result.status == RunStatus.PARTIAL  # Partial because of fallback
    assert result.metadata['used_fallback'] is True
    assert 'Ver evidencia relacionada' in result.next_actions


def test_execution_playbook_service_uses_knowledge_executor_for_knowledge_query() -> None:
    """Test that ExecutionPlaybookService selects KnowledgeOperationalExecutor for knowledge.query."""
    mock_knowledge_executor = Mock(spec=KnowledgeOperationalExecutor)
    mock_knowledge_executor.name = 'knowledge_query_executor'
    mock_knowledge_executor.supports.return_value = True
    mock_knowledge_executor.execute.return_value = OperationalExecutorResult(
        executed=True,
        status=RunStatus.SUCCESS,
        summary='Knowledge query executed.',
        next_actions=['Ver evidencia'],
        metadata={'knowledge_hits_count': 1},
    )
    
    mock_tool_executor = Mock()
    mock_tool_executor.name = 'tool_executor'
    mock_tool_executor.supports.return_value = False
    
    service = ExecutionPlaybookService(
        executor=mock_tool_executor,
        knowledge_executor=mock_knowledge_executor,
    )
    
    session = _knowledge_session()
    
    updated = service.execute(session)
    
    # Verify that knowledge executor was used
    mock_knowledge_executor.supports.assert_called_once_with(session)
    mock_knowledge_executor.execute.assert_called_once_with(session)
    
    # Verify that tool executor was NOT used
    mock_tool_executor.supports.assert_not_called()
    mock_tool_executor.execute.assert_not_called()
    
    # Verify execution state
    assert updated.metadata['execution_state']['executor_name'] == 'knowledge_query_executor'
    assert updated.metadata['execution_state']['executor_available'] is True
    assert updated.metadata['execution_state']['state'] == 'executed'
    assert updated.status == AdaptiveSessionStatus.COMPLETED
    assert updated.outcome.status == RunStatus.SUCCESS
    assert updated.outcome.metadata['mode'] == 'execute_executed'  # ExecutionPlaybookService adds prefix


def test_execution_playbook_service_uses_tool_executor_for_other_packs() -> None:
    """Test that ExecutionPlaybookService uses ToolOperationalExecutor for non-knowledge packs."""
    mock_knowledge_executor = Mock(spec=KnowledgeOperationalExecutor)
    mock_knowledge_executor.name = 'knowledge_query_executor'
    mock_knowledge_executor.supports.return_value = False
    
    mock_tool_executor = Mock()
    mock_tool_executor.name = 'tool_executor'
    mock_tool_executor.supports.return_value = True
    mock_tool_executor.execute.return_value = OperationalExecutorResult(
        executed=True,
        status=RunStatus.SUCCESS,
        summary='Tool executed.',
        next_actions=['Ver resultado'],
        metadata={'mode': 'executed'},
    )
    
    service = ExecutionPlaybookService(
        executor=mock_tool_executor,
        knowledge_executor=mock_knowledge_executor,
    )
    
    session = _knowledge_session()
    session.chosen_pack_id = 'browser.generic'  # Different pack
    
    updated = service.execute(session)
    
    # Verify that tool executor was used
    mock_tool_executor.supports.assert_called_once_with(session)
    mock_tool_executor.execute.assert_called_once_with(session)
    
    # Verify that knowledge executor was NOT used
    mock_knowledge_executor.supports.assert_not_called()
    mock_knowledge_executor.execute.assert_not_called()
    
    # Verify execution state
    assert updated.metadata['execution_state']['executor_name'] == 'tool_executor'
    assert updated.metadata['execution_state']['executor_available'] is True


def test_knowledge_query_no_longer_simulates_when_executor_available() -> None:
    """Test that knowledge.query no longer goes to simulate when executor is available."""
    mock_knowledge_executor = Mock(spec=KnowledgeOperationalExecutor)
    mock_knowledge_executor.name = 'knowledge_query_executor'
    mock_knowledge_executor.supports.return_value = True
    mock_knowledge_executor.execute.return_value = OperationalExecutorResult(
        executed=True,
        status=RunStatus.SUCCESS,
        summary='Knowledge query executed.',
        next_actions=['Ver evidencia'],
        metadata={'knowledge_hits_count': 1},
    )
    
    service = ExecutionPlaybookService(
        knowledge_executor=mock_knowledge_executor,
    )
    
    session = _knowledge_session()
    
    updated = service.execute(session)
    
    # Verify it's NOT in simulate mode
    assert updated.outcome.metadata['mode'] == 'execute_executed'
    assert updated.metadata['execution_state']['state'] == 'executed'
    assert updated.status == AdaptiveSessionStatus.COMPLETED
    assert updated.outcome.status == RunStatus.SUCCESS


def test_knowledge_query_still_simulates_when_executor_unavailable() -> None:
    """Test that knowledge query still simulates when executor is not available."""
    service = ExecutionPlaybookService()  # No knowledge_executor injected
    
    session = _knowledge_session()
    
    updated = service.execute(session)
    
    # Verify it's in simulate/adapter_missing mode
    assert updated.outcome.metadata['mode'] in {'execute_waiting_adapter', 'adapter_missing'}
    assert updated.metadata['execution_state']['state'] == 'adapter_missing'
    assert updated.status == AdaptiveSessionStatus.READY_TO_EXECUTE
    assert updated.outcome.status == RunStatus.PARTIAL


def test_knowledge_executor_does_not_duplicate_persistence() -> None:
    """Test that KnowledgeOperationalExecutor does NOT directly persist runs or knowledge items."""
    mock_router = Mock(spec=LocalRoleRouter)
    mock_router.execute_knowledge_query.return_value = (
        _mock_role_route(),
        _mock_inference_result(),
    )
    
    executor = KnowledgeOperationalExecutor(mock_router)
    session = _knowledge_session()
    
    result = executor.execute(session)
    
    # Verify that the executor only returns OperationalExecutorResult
    # It does NOT call any persistence methods
    assert isinstance(result, OperationalExecutorResult)
    assert 'run_record' not in result.metadata
    assert 'knowledge_item' not in result.metadata
    
    # Verify that only LocalRoleRouter was called
    mock_router.execute_knowledge_query.assert_called_once()
    
    # Persistence should be handled by InferenceService, not the executor


def test_inference_request_construction_from_adaptive_session() -> None:
    """Test that InferenceRequest is correctly constructed from AdaptiveSession."""
    mock_router = Mock(spec=LocalRoleRouter)
    mock_router.execute_knowledge_query.return_value = (
        _mock_role_route(),
        _mock_inference_result(),
    )
    
    executor = KnowledgeOperationalExecutor(mock_router)
    session = _knowledge_session()
    
    executor.execute(session)
    
    # Verify InferenceRequest construction
    call_args = mock_router.execute_knowledge_query.call_args
    request = call_args[0][0]
    
    assert request.user_goal == session.user_goal
    assert request.task_role == TaskRole.KNOWLEDGE
    assert request.read_only_sql is True
    assert ToolCapability.KNOWLEDGE_SEARCH in request.allowed_tools
    assert ToolCapability.EMBEDDINGS in request.allowed_tools
    assert 'episodes' in request.knowledge_scope
    assert 'knowledge_items' in request.knowledge_scope
    assert session.metadata is not None or request.metadata is not None


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
