from __future__ import annotations

from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    CapabilityReadiness,
    ExecutionPlaybook,
    InteractionChannel,
    InteractionPattern,
    InferenceRequest,
    TaskIntent,
    TaskRole,
    ToolCard,
    ToolActionType,
    ToolTask,
    ToolTaskStatus,
    ToolType,
    PlaybookStep,
    UniversalInteractionStep,
    ModeSelectionDecision,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_operational_executor import ToolOperationalExecutor
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager


class _Adapter:
    def is_available(self, card: ToolCard) -> bool:
        return True

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        return {'success': True}


def _registry(tmp_path: Path) -> tuple[ToolRegistry, ToolRecordRepository]:
    repository = ToolRecordRepository(
        AppDatabase(str(tmp_path / 'app.sqlite')),
        ArtifactStorage(str(tmp_path / 'artifacts')),
    )
    registry = ToolRegistry(repository, {'adapter': _Adapter()})
    for card in (
        ToolCard(tool_id='eligible_a', title='Eligible A', tool_type=ToolType.CUSTOM, adapter_key='adapter', realizes_capability_ids=['cap.a', 'cap.b'], metadata={'assistant_kind': 'family_a'}),
        ToolCard(tool_id='ineligible_b', title='Strong lexical match for alpha browser', tool_type=ToolType.CUSTOM, adapter_key='adapter', realizes_capability_ids=['cap.b'], metadata={'assistant_kind': 'family_b'}),
        ToolCard(tool_id='eligible_c', title='Eligible C', tool_type=ToolType.CUSTOM, adapter_key='adapter', realizes_capability_ids=['cap.a'], metadata={'assistant_kind': 'family_c'}),
    ):
        repository.save_card(card)
    return registry, repository


def _task(*, required: list[str], tool_id: str = 'ineligible_b', goal_parameters: dict[str, Any] | None = None) -> ToolTask:
    return ToolTask(
        tool_id=tool_id,
        title='Alpha browser task',
        objective='alpha browser task',
        required_capability_ids=required,
        metadata={'goal_parameters': goal_parameters or {}},
    )


def test_registry_single_missing_and_conjunctive_realization(tmp_path: Path) -> None:
    registry, _ = _registry(tmp_path)
    assert {card.tool_id for card in registry.eligible_cards_for_task(_task(required=['cap.a']))} == {'eligible_a', 'eligible_c'}
    assert {card.tool_id for card in registry.eligible_cards_for_task(_task(required=['cap.a', 'cap.b']))} == {'eligible_a'}
    assert registry.eligible_cards_for_task(_task(required=['cap.a', 'cap.missing'])) == []


def test_curated_default_realizations_match_adjudication(tmp_path: Path) -> None:
    registry, _ = _registry(tmp_path)
    assert registry.get_card('playwright_browser').realizes_capability_ids == ['browser.generic.navigation']
    assert registry.get_card('ollama_llm').realizes_capability_ids == ['assistant.local.chat']
    assert 'browser.search.google' not in registry.get_card('playwright_browser').realizes_capability_ids


def test_empty_requirements_are_unrestricted_but_explicit_empty_scope_is_closed(tmp_path: Path) -> None:
    registry, _ = _registry(tmp_path)
    assert len(registry.eligible_cards_for_task(_task(required=[]))) >= 3
    assert registry.eligible_cards_for_task(_task(required=[], goal_parameters={'allowed_tool_ids': []})) == []
    assert registry.eligible_cards_for_task(_task(required=[], goal_parameters={'allowed_tool_ids': ['eligible_a']})) == [registry.get_card('eligible_a')]


def test_registry_preferences_lexical_and_first_card_stay_inside_eligible_set(tmp_path: Path) -> None:
    registry, _ = _registry(tmp_path)
    task = _task(required=['cap.a'], tool_id='ineligible_b')
    assert registry.pick_card_for_task(task).tool_id in {'eligible_a', 'eligible_c'}
    assert registry.pick_card_for_task(task, preferred_assistant_kind='family_b').tool_id in {'eligible_a', 'eligible_c'}
    assert registry.pick_card_for_task(_task(required=['cap.a'], tool_id='')) .tool_id in {'eligible_a', 'eligible_c'}


def test_selector_filters_before_preferred_external_and_ranking(tmp_path: Path) -> None:
    registry, repository = _registry(tmp_path)
    selector = InteractionModeSelector(registry, repository)
    task = _task(required=['cap.a'], tool_id='ineligible_b')
    request = InferenceRequest(
        user_goal='alpha browser task',
        task_role=TaskRole.TOOL_USE,
        goal_parameters={'consultation_scope': 'external_assistant', 'tool_id': 'ineligible_b'},
    )
    selection = selector.select(
        request=request,
        draft_task=task,
        suggested_tool_id='ineligible_b',
    )
    assert selection.selected_tool_id in {'eligible_a', 'eligible_c'}
    assert selection.selection_outcome == 'selected'


def test_selector_distinguishes_no_realization_from_no_allowed_tool(tmp_path: Path) -> None:
    registry, repository = _registry(tmp_path)
    selector = InteractionModeSelector(registry, repository)
    request = InferenceRequest(user_goal='anything', task_role=TaskRole.TOOL_USE)
    no_realization = selector.select(request=request, draft_task=_task(required=['not.realized']))
    no_allowed = selector.select(
        request=request,
        draft_task=_task(required=[], goal_parameters={'allowed_tool_ids': []}),
        allowed_tool_ids=[],
    )
    assert no_realization.selection_outcome == 'no_eligible_realization'
    assert no_allowed.selection_outcome == 'no_allowed_tool'


def test_readiness_requirements_exclude_system_ids_and_preserve_order() -> None:
    intent = TaskIntent(intent_key='general.assistance')
    readiness = [
        CapabilityReadiness(capability_id='tools.local.registry', title='registry'),
        CapabilityReadiness(capability_id='cap.a', title='A'),
        CapabilityReadiness(capability_id='tools.local.execution', title='execution'),
        CapabilityReadiness(capability_id='cap.a', title='A duplicate'),
        CapabilityReadiness(capability_id='tools.local.sandbox', title='sandbox'),
        CapabilityReadiness(capability_id='cap.b', title='B'),
    ]
    raw, excluded, required = CapabilityReadinessService.operational_task_requirements(intent=intent, readiness=readiness)
    assert raw == ['tools.local.registry', 'cap.a', 'tools.local.execution', 'tools.local.sandbox', 'cap.b']
    assert excluded == ['tools.local.registry', 'tools.local.execution', 'tools.local.sandbox']
    assert required == ['cap.a', 'cap.b']


def test_historical_session_uses_canonical_intent_requirements() -> None:
    session = AdaptiveSession(
        user_goal='help',
        intent=TaskIntent(intent_key='general.assistance', detected_role=TaskRole.TOOL_USE),
    )
    _raw, _excluded, required = CapabilityReadinessService.operational_task_requirements(
        intent=session.intent,
        readiness=session.capability_readiness,
    )
    assert required == ['assistant.local.chat']


def test_session_readiness_is_transported_to_tooltask_and_synaptic_stays_gated(tmp_path: Path) -> None:
    registry, repository = _registry(tmp_path)
    learning = InteractionLearningService(repository)
    selector = InteractionModeSelector(registry, repository)
    service = ToolTeachService(
        registry=registry,
        memory=ToolMemory(repository, learning),
        sandbox=ToolSandbox(ToolValidator()),
        validator=ToolValidator(),
        approval_policy=ToolApprovalPolicy(),
        rollback_manager=ToolRollbackManager(),
        adapters={'adapter': _Adapter()},
        workspace_root=str(tmp_path),
        interaction_learning_service=learning,
        mode_selector=selector,
        synaptic_router=type('SynapticStub', (), {
            'decide': lambda self, **_kwargs: type('Decision', (), {
                'model_dump': lambda self, **_inner: {'selected_assistant_kind': 'family_b'},
            })(),
        })(),
    )
    explicit_family_request = InferenceRequest(
        user_goal='alpha browser task',
        task_role=TaskRole.TOOL_USE,
        goal_parameters={'allowed_tool_ids': ['ineligible_b']},
    )
    assert service._resolve_available_family_card(
        tool_id='ineligible_b',
        request=explicit_family_request,
        required_capability_ids=['cap.a'],
    ) is None
    session = AdaptiveSession(
        user_goal='alpha browser task',
        intent=TaskIntent(intent_key='general.assistance', detected_role=TaskRole.TOOL_USE),
        capability_readiness=[
            CapabilityReadiness(capability_id='tools.local.registry', title='registry'),
            CapabilityReadiness(capability_id='cap.a', title='A'),
            CapabilityReadiness(capability_id='cap.a', title='A duplicate'),
        ],
    )
    task = service.build_task_for_session(session)
    assert task.required_capability_ids == ['cap.a']
    assert task.tool_id in {'eligible_a', 'eligible_c'}
    assert task.status == ToolTaskStatus.PENDING
    assert task.model_dump(mode='json')['required_capability_ids'] == ['cap.a']

    unavailable = service.build_task_from_request(
        InferenceRequest(user_goal='anything', task_role=TaskRole.TOOL_USE),
        required_capability_ids=['cap.never.realized'],
    )
    assert unavailable.required_capability_ids == ['cap.never.realized']
    assert unavailable.status == ToolTaskStatus.DEFERRED
    assert unavailable.tool_id == ''
    assert unavailable.actions == []
    assert unavailable.metadata['mode_selection']['selection_outcome'] == 'no_eligible_realization'
    assert unavailable.metadata['synaptic_routing_decision'] == {}

    blocked_session = AdaptiveSession(
        user_goal='unrealizable task',
        intent=TaskIntent(intent_key='general.assistance', detected_role=TaskRole.TOOL_USE),
        capability_readiness=[CapabilityReadiness(capability_id='cap.never.realized', title='missing')],
        playbook=ExecutionPlaybook(
            goal='unrealizable task',
            pack_id='tools.local',
            steps=[PlaybookStep(phase_key='execute', title='Execute', description='Run tool')],
        ),
    )
    executor = ToolOperationalExecutor(service)
    assert executor.preflight_status(blocked_session) == 'no_eligible_realization'
    annotated = ExecutionPlaybookService(executor).annotate_execution_capability(blocked_session)
    assert annotated.metadata['execution_state']['state'] == 'no_eligible_realization'


def test_synaptic_selection_preserves_requirements_and_rejects_cross_tool_pattern(tmp_path: Path) -> None:
    registry, repository = _registry(tmp_path)
    learning = InteractionLearningService(repository)
    service = ToolTeachService(
        registry=registry,
        memory=ToolMemory(repository, learning),
        sandbox=ToolSandbox(ToolValidator()),
        validator=ToolValidator(),
        approval_policy=ToolApprovalPolicy(),
        rollback_manager=ToolRollbackManager(),
        adapters={'adapter': _Adapter()},
        workspace_root=str(tmp_path),
        interaction_learning_service=learning,
        mode_selector=InteractionModeSelector(registry, repository),
        synaptic_router=type('SynapticStub', (), {
            'decide': lambda self, **_kwargs: type('Decision', (), {
                'model_dump': lambda self, **_inner: {'selected_assistant_kind': 'family_a'},
            })(),
        })(),
    )
    pattern = InteractionPattern(
        signature='rq21.10.cross-tool-pattern',
        title='Pattern belonging to B',
        channel=InteractionChannel.UI,
        tool_id='ineligible_b',
        tool_type=ToolType.CUSTOM,
        operations=[UniversalInteractionStep(
            channel=InteractionChannel.UI,
            operation=ToolActionType.OPEN_URL.value,
            target='https://pattern-b.example/',
        )],
    )
    repository.save_interaction_pattern(pattern)

    selection_inputs: list[tuple[list[str], set[str]]] = []

    def select_with_reusable_pattern(*, request, draft_task, **_kwargs):
        eligible_ids = {card.tool_id for card in registry.eligible_cards_for_task(draft_task)}
        selection_inputs.append((list(draft_task.required_capability_ids), eligible_ids))
        # With no propagated requirement B becomes a candidate. When the
        # requirement is preserved, A is selected, but the reusable-pattern
        # metadata still points to B so the downstream identity guard is tested.
        selected_tool_id = 'ineligible_b' if 'ineligible_b' in eligible_ids else 'eligible_a'
        return ModeSelectionDecision(
            selected_tool_id=selected_tool_id,
            selected_tool_type=ToolType.CUSTOM,
            reusable_pattern_id=pattern.pattern_id,
        )

    service.mode_selector.select = select_with_reusable_pattern
    task = service.build_task_from_request(
        InferenceRequest(user_goal='perform the capability-constrained task', task_role=TaskRole.TOOL_USE),
        required_capability_ids=['cap.a'],
    )

    assert task.tool_id == 'eligible_a'
    assert selection_inputs[-1][0] == ['cap.a']
    assert 'ineligible_b' not in selection_inputs[-1][1]
    assert task.metadata['mode_selection']['selected_tool_id'] == 'eligible_a'
    assert task.actions
    assert all(action.action_type != ToolActionType.OPEN_URL for action in task.actions)
    assert all(not action.metadata.get('reused_from_pattern') for action in task.actions)
