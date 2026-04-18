from __future__ import annotations

from iabv_v15.domain.models import (
    AdaptiveSession,
    ExecutionState,
    RunStatus,
    TaskIntent,
    TaskRole,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.services.tools.tool_operational_executor import ToolOperationalExecutor


class _FakeOllamaAdapter:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.run_calls: list[tuple[ToolCard, ToolTask]] = []

    def is_available(self, card: ToolCard) -> bool:
        return self.available

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict:
        self.run_calls.append((card, task))
        return {
            'success': True,
            'output_text': 'Hola desde Ollama local',
            'extracted_data': {'provider': 'ollama', 'report_kind': 'assistant'},
            'artifacts': [],
            'error_message': '',
            'execution_ms': 5,
            'metadata': {'assistant_kind': 'ollama', 'sandbox': sandbox},
        }


class _FakeRegistry:
    def __init__(self, card: ToolCard | None) -> None:
        self.card = card
        self.pick_calls: list[ToolTask] = []

    def pick_card_for_task(self, task: ToolTask) -> ToolCard | None:
        self.pick_calls.append(task)
        return self.card


class _FakeToolTeachService:
    def __init__(self, *, card: ToolCard | None, adapter: _FakeOllamaAdapter | None) -> None:
        self.registry = _FakeRegistry(card)
        self.adapters = {'ollama': adapter} if adapter is not None else {}
        self.adapter = adapter
        self.card = card
        self.build_calls: list[AdaptiveSession] = []
        self.execute_calls: list[tuple[ToolTask, bool]] = []

    def build_task_for_session(self, session: AdaptiveSession) -> ToolTask:
        self.build_calls.append(session)
        tool_id = self.card.tool_id if self.card is not None else 'ollama_llm'
        return ToolTask(
            tool_id=tool_id,
            title=session.user_goal[:80],
            objective=session.user_goal,
            requested_by_role=session.intent.detected_role,
            actions=[
                ToolAction(
                    action_type=ToolActionType.LLM_QUERY,
                    label='Consulta local',
                    value=session.user_goal,
                )
            ],
            session_id=session.session_id,
            pack_id=session.chosen_pack_id,
        )

    def execute_task(self, task: ToolTask, *, approved: bool = False) -> ToolResult:
        self.execute_calls.append((task, approved))
        assert self.card is not None
        assert self.adapter is not None
        payload = self.adapter.run(self.card, task, sandbox=False)
        return ToolResult(
            task_id=task.task_id,
            tool_id=task.tool_id,
            tool_type=self.card.tool_type,
            success=bool(payload['success']),
            validation_status=ToolValidationStatus.SANDBOX_PASS,
            execution_state=ExecutionState(state='executed', detail='Respuesta local lista.'),
            output_text=str(payload['output_text']),
            extracted_data=dict(payload.get('extracted_data') or {}),
            metadata=dict(payload.get('metadata') or {}),
        )


def _ollama_card() -> ToolCard:
    return ToolCard(
        tool_id='ollama_llm',
        title='Ollama local',
        tool_type=ToolType.LLM_LOCAL,
        description='Proveedor local principal para chat y razonamiento local.',
        adapter_key='ollama',
        supports_sandbox=True,
        capabilities=[
            'llm_query',
            'knowledge.query.local',
            'assistant.local.chat',
            'local_chat_context',
        ],
        metadata={
            'assistant_kind': 'ollama',
            'launch_mode': 'local_provider',
            'response_capture_mode': 'tool_result',
            'supports_local_chat': True,
        },
    )


def _chat_session(
    *,
    pack_id: str = 'knowledge.query',
    intent_key: str = 'knowledge.query',
    role: TaskRole = TaskRole.KNOWLEDGE,
) -> AdaptiveSession:
    return AdaptiveSession(
        user_goal='Explicame que es la neuroplasticidad operativa del proyecto.',
        intent=TaskIntent(
            intent_key=intent_key,
            title='Consulta local de conocimiento',
            detected_role=role,
        ),
        chosen_pack_id=pack_id,
        chosen_pack_title='Consulta local con contexto',
    )


def test_supports_local_chat_when_ollama_adapter_is_ready() -> None:
    card = _ollama_card()
    adapter = _FakeOllamaAdapter(available=True)
    service = _FakeToolTeachService(card=card, adapter=adapter)
    executor = ToolOperationalExecutor(service)

    session = _chat_session()

    assert executor.supports(session) is True
    description = executor.describe(session)
    assert 'Ollama local' in description
    assert 'No hay un executor' not in description


def test_executes_local_chat_through_ollama_adapter() -> None:
    card = _ollama_card()
    adapter = _FakeOllamaAdapter(available=True)
    service = _FakeToolTeachService(card=card, adapter=adapter)
    executor = ToolOperationalExecutor(service)

    session = _chat_session()

    result = executor.execute(session)

    assert result.executed is True
    assert result.status == RunStatus.SUCCESS
    assert 'Ollama' in result.summary or 'Hola' in result.summary
    assert result.metadata['tool_id'] == 'ollama_llm'
    assert result.metadata['mode'] == 'executed'

    # The adapter.run should have been called with the LLM_QUERY prompt carrying the user goal.
    assert len(adapter.run_calls) == 1
    called_card, called_task = adapter.run_calls[0]
    assert called_card.tool_id == 'ollama_llm'
    llm_actions = [action for action in called_task.actions if action.action_type == ToolActionType.LLM_QUERY]
    assert llm_actions, 'Expected at least one LLM_QUERY action dispatched to the adapter'
    assert 'neuroplasticidad' in llm_actions[0].value


def test_supports_general_assistance_pack_via_local_chat() -> None:
    card = _ollama_card()
    adapter = _FakeOllamaAdapter(available=True)
    service = _FakeToolTeachService(card=card, adapter=adapter)
    executor = ToolOperationalExecutor(service)

    session = _chat_session(
        pack_id='general.assistance',
        intent_key='general.assistance',
        role=TaskRole.KNOWLEDGE,
    )

    assert executor.supports(session) is True


def test_local_chat_is_rejected_when_ollama_adapter_is_unavailable() -> None:
    card = _ollama_card()
    adapter = _FakeOllamaAdapter(available=False)
    service = _FakeToolTeachService(card=card, adapter=adapter)
    executor = ToolOperationalExecutor(service)

    session = _chat_session()

    assert executor.supports(session) is False
    description = executor.describe(session)
    assert 'No hay un executor' in description


def test_non_chat_non_tool_flow_is_rejected() -> None:
    card = _ollama_card()
    adapter = _FakeOllamaAdapter(available=True)
    service = _FakeToolTeachService(card=card, adapter=adapter)
    executor = ToolOperationalExecutor(service)

    session = AdaptiveSession(
        user_goal='Navega a una pagina de casino y abre el juego.',
        intent=TaskIntent(
            intent_key='wplay.casino',
            title='Abrir casino',
            detected_role=TaskRole.VISUAL,
        ),
        chosen_pack_id='wplay.casino',
        chosen_pack_title='Wplay casino',
    )

    assert executor.supports(session) is False


def test_tool_flow_still_requires_available_adapter_regression() -> None:
    # Existing tools.* flow behavior must remain intact: adapter must be available.
    card = _ollama_card()
    adapter = _FakeOllamaAdapter(available=True)
    service = _FakeToolTeachService(card=card, adapter=adapter)
    executor = ToolOperationalExecutor(service)

    session = AdaptiveSession(
        user_goal='Consulta local con herramientas',
        intent=TaskIntent(
            intent_key='tools.local_workflow',
            title='Flujo local de herramientas',
            detected_role=TaskRole.TOOL_USE,
        ),
        chosen_pack_id='tools.local_first',
        chosen_pack_title='Herramientas locales',
    )

    assert executor.supports(session) is True
