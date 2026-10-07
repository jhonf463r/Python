from __future__ import annotations

from types import SimpleNamespace

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    CapabilityReadiness,
    CapabilityStatus,
    ExecutionPlaybook,
    InferenceRequest,
    InteractionMode,
    ModeSelectionDecision,
    PlaybookStep,
    RunStatus,
    TaskIntent,
    TaskRole,
    ToolCard,
    ToolTask,
    ToolTaskStatus,
    ToolType,
)
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_operational_executor import ToolOperationalExecutor
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


class MemoryToolRepository:
    def __init__(self) -> None:
        self.cards: dict[str, ToolCard] = {}

    def list_cards(self):
        return list(self.cards.values())

    def get_card(self, tool_id: str):
        return self.cards.get(tool_id)

    def save_card(self, card: ToolCard):
        self.cards[card.tool_id] = card
        return card

    def list_interaction_patterns(self, **_kwargs):
        return []

    def list_interaction_episodes(self, **_kwargs):
        return []


class AvailableAdapter:
    def is_available(self, _card):
        return True


def _card(tool_id: str, realization_ids: list[str], *, assistant_kind: str = '') -> ToolCard:
    metadata = {'assistant_kind': assistant_kind} if assistant_kind else {}
    return ToolCard(
        tool_id=tool_id,
        title=tool_id,
        tool_type=ToolType.CUSTOM,
        adapter_key='fake',
        realizes_capability_ids=realization_ids,
        metadata=metadata,
    )


def _registry(*cards: ToolCard):
    repository = MemoryToolRepository()
    registry = ToolRegistry(repository, {'fake': AvailableAdapter(), 'playwright': AvailableAdapter(), 'ollama': AvailableAdapter()})
    for card in cards:
        repository.save_card(card)
    return registry, repository


def test_session_readiness_transports_stable_operational_requirements_and_excludes_meta_ids():
    readiness = [
        CapabilityReadiness(capability_id='cap.alpha', title='A', status=CapabilityStatus.READY, score=1.0),
        CapabilityReadiness(capability_id='tools.local.registry', title='Registry', status=CapabilityStatus.READY, score=1.0),
        CapabilityReadiness(capability_id='cap.beta', title='B', status=CapabilityStatus.READY, score=1.0),
        CapabilityReadiness(capability_id='cap.alpha', title='A duplicate', status=CapabilityStatus.READY, score=1.0),
        CapabilityReadiness(capability_id='tools.local.execution', title='Execution', status=CapabilityStatus.READY, score=1.0),
        CapabilityReadiness(capability_id='tools.local.sandbox', title='Sandbox', status=CapabilityStatus.READY, score=1.0),
    ]
    raw, excluded, required = CapabilityReadinessService.operational_task_requirements(
        intent=TaskIntent(intent_key='general.assistance', title='help'),
        readiness=readiness,
    )
    assert raw == ['cap.alpha', 'tools.local.registry', 'cap.beta', 'tools.local.execution', 'tools.local.sandbox']
    assert excluded == ['tools.local.registry', 'tools.local.execution', 'tools.local.sandbox']
    assert required == ['cap.alpha', 'cap.beta']


def test_legacy_session_without_readiness_uses_canonical_intent_mapping_not_goal_text():
    raw, excluded, required = CapabilityReadinessService.operational_task_requirements(
        intent=TaskIntent(intent_key='general.assistance', title='help'),
        readiness=[],
    )
    assert raw == ['assistant.local.chat']
    assert excluded == []
    assert required == ['assistant.local.chat']


def test_build_task_for_session_transports_readiness_requirements_and_provenance():
    class StubToolTeachService:
        def build_task_from_request(self, request, *, required_capability_ids, capability_requirement_provenance):
            assert request.user_goal == 'navigate'
            assert required_capability_ids == ['browser.generic.navigation']
            assert capability_requirement_provenance['excluded_system_readiness_ids'] == ['tools.local.registry']
            return ToolTask(
                tool_id='',
                title='navigate',
                objective=request.user_goal,
                required_capability_ids=required_capability_ids,
                metadata={'capability_requirement_provenance': capability_requirement_provenance},
            )

    session = AdaptiveSession(
        user_goal='navigate',
        intent=TaskIntent(intent_key='browser.navigate', title='navigate', detected_role=TaskRole.TOOL_USE),
        capability_readiness=[
            CapabilityReadiness(capability_id='browser.generic.navigation', title='navigation', status=CapabilityStatus.READY, score=1.0),
            CapabilityReadiness(capability_id='tools.local.registry', title='registry', status=CapabilityStatus.READY, score=1.0),
        ],
    )
    task = ToolTeachService.build_task_for_session(StubToolTeachService(), session)
    assert task.required_capability_ids == ['browser.generic.navigation']
    assert task.metadata['capability_requirement_provenance']['source'] == 'session.capability_readiness'
    assert task.metadata['capability_requirement_provenance']['session_id'] == session.session_id
    assert task.metadata['capability_requirement_provenance']['task_id'] == task.task_id


def test_tool_task_and_card_old_payloads_default_to_unconstrained_empty_fields():
    task = ToolTask.model_validate({'tool_id': 'legacy', 'title': 'legacy', 'objective': 'legacy'})
    card = ToolCard.model_validate({'tool_id': 'legacy', 'title': 'legacy', 'tool_type': 'custom', 'adapter_key': 'fake'})
    assert task.required_capability_ids == []
    assert card.realizes_capability_ids == []


def test_registry_requires_conjunctive_capability_coverage_and_does_not_use_availability_as_realization():
    registry, _repository = _registry(
        _card('partial', ['cap.alpha']),
        _card('complete', ['cap.alpha', 'cap.beta']),
        _card('unavailable_complete', ['cap.alpha', 'cap.beta']),
    )
    unavailable = registry.get_card('unavailable_complete')
    assert unavailable is not None
    registry.repository.save_card(unavailable.model_copy(update={'available': False}))
    task = ToolTask(tool_id='partial', title='test', objective='test', required_capability_ids=['cap.alpha', 'cap.beta'])
    assert [card.tool_id for card in registry.eligible_cards_for_task(task)] == ['complete', 'unavailable_complete']
    selected = registry.pick_card_for_task(task)
    assert selected is not None and selected.tool_id == 'complete'


def test_registry_does_not_resurrect_ineligible_explicit_or_synaptic_preference():
    registry, _repository = _registry(
        _card('preferred_bad', [], assistant_kind='preferred'),
        _card('eligible', ['cap.required'], assistant_kind='other'),
    )
    task = ToolTask(tool_id='preferred_bad', title='task', objective='task', required_capability_ids=['cap.required'])
    selected = registry.pick_card_for_task(task, preferred_assistant_kind='preferred')
    assert selected is not None
    assert selected.tool_id == 'eligible'


def test_empty_requirements_preserve_legacy_selection_and_empty_allowlist_is_not_unrestricted():
    registry, _repository = _registry(_card('legacy', [], assistant_kind='legacy'))
    unconstrained = ToolTask(tool_id='legacy', title='task', objective='task')
    assert registry.pick_card_for_task(unconstrained).tool_id == 'legacy'
    assert [card.tool_id for card in registry.eligible_cards_for_task(unconstrained)]
    assert registry.eligible_cards_for_task(unconstrained, allowed_tool_ids=[]) == []
    assert registry.eligible_cards_for_task(unconstrained, allowed_tool_ids=None)


def test_preferred_external_decision_cannot_bypass_realization_gate():
    registry, repository = _registry(
        _card('preferred_external', [], assistant_kind='chatgpt'),
        _card('eligible_local', ['assistant.local.chat'], assistant_kind='ollama'),
    )
    selector = InteractionModeSelector(registry, repository)
    request = InferenceRequest(
        user_goal='consult external assistant',
        task_role=TaskRole.TOOL_USE,
        goal_parameters={'consultation_scope': 'external_assistant'},
    )
    draft = ToolTask(
        tool_id='preferred_external',
        title='consult',
        objective='consult external assistant',
        required_capability_ids=['assistant.local.chat'],
    )
    decision = selector.select(request=request, draft_task=draft, suggested_tool_id='preferred_external')
    assert decision.selection_outcome == 'selected'
    assert decision.selected_tool_id != 'preferred_external'
    assert decision.selected_tool_id in decision.metadata['eligible_tool_ids']
    assert any(item['tool_id'] == 'preferred_external' for item in decision.metadata['excluded_tool_cards'])


def test_adjudicated_seed_mappings_are_exact_and_google_search_remains_unrealized():
    registry, _repository = _registry()
    browser = registry.get_card('playwright_browser')
    ollama = registry.get_card('ollama_llm')
    assert browser is not None and browser.realizes_capability_ids == ['browser.generic.navigation']
    assert ollama is not None and ollama.realizes_capability_ids == ['assistant.local.chat']
    assert 'browser.search.google' not in browser.realizes_capability_ids


def test_registry_seed_preserves_an_existing_curated_realization_declaration():
    registry, repository = _registry()
    card = repository.get_card('playwright_browser')
    assert card is not None
    repository.save_card(card.model_copy(update={'realizes_capability_ids': ['curated.navigation']}))
    ToolRegistry(repository, {'fake': AvailableAdapter(), 'playwright': AvailableAdapter(), 'ollama': AvailableAdapter()})
    refreshed = repository.get_card('playwright_browser')
    assert refreshed is not None
    assert refreshed.realizes_capability_ids == ['curated.navigation']


def test_legacy_model_payload_round_trip_preserves_new_realization_fields():
    legacy_card = ToolCard.model_validate({'tool_id': 'legacy', 'title': 'legacy', 'tool_type': 'custom', 'adapter_key': 'fake'})
    legacy_task = ToolTask.model_validate({'tool_id': 'legacy', 'title': 'legacy', 'objective': 'legacy'})
    task = legacy_task.model_copy(update={'required_capability_ids': ['cap.x']})
    card = legacy_card.model_copy(update={'realizes_capability_ids': ['cap.x']})
    assert ToolTask.model_validate(task.model_dump(mode='json')).required_capability_ids == ['cap.x']
    assert ToolCard.model_validate(card.model_dump(mode='json')).realizes_capability_ids == ['cap.x']


def test_selector_fails_closed_with_typed_no_eligible_realization():
    registry, repository = _registry(_card('navigation_only', ['browser.generic.navigation']))
    selector = InteractionModeSelector(registry, repository)
    decision = selector.select(
        request=InferenceRequest(user_goal='search Google', task_role=TaskRole.TOOL_USE),
        draft_task=ToolTask(
            tool_id='navigation_only',
            title='search',
            objective='search Google',
            required_capability_ids=['browser.search.google'],
        ),
        suggested_tool_id='navigation_only',
    )
    assert decision.selection_outcome == 'no_eligible_realization'
    assert decision.selected_tool_id == ''
    assert decision.metadata['eligible_tool_ids'] == []


def test_task_builder_does_not_resurrect_suggested_card_when_selection_has_no_realization():
    service = object.__new__(ToolTeachService)
    service._select_mode = lambda **_kwargs: ModeSelectionDecision(
        selection_outcome='no_eligible_realization',
        reason='no realization',
    )
    service._synaptic_decision_for_request = lambda _request: (_ for _ in ()).throw(AssertionError('Synaptic must not run'))
    service._pattern_from_selection = lambda _selection: None
    service._assistant_configuration_snapshot = lambda **_kwargs: SimpleNamespace(model_dump=lambda **_dump_kwargs: {})
    service._config_signature = lambda _configuration: 'signature'
    service._comparison_scope_key = lambda **_kwargs: 'scope'
    service._source_trace_ids_from_payload = lambda **_kwargs: []
    service._proposal_summary = lambda **_kwargs: 'proposal'
    service._assistant_family_for_tool_id = lambda _tool_id: ''
    service._build_ia_trace_entry = lambda **_kwargs: SimpleNamespace(model_dump=lambda **_dump_kwargs: {})
    request = InferenceRequest(
        user_goal='search Google',
        task_role=TaskRole.TOOL_USE,
        goal_parameters={'tool_id': 'navigation_only'},
    )

    task = service.build_task_from_request(request, required_capability_ids=['browser.search.google'])

    assert task.status == ToolTaskStatus.DEFERRED
    assert task.tool_id == ''
    assert task.actions == []
    assert task.rollback_actions == []
    assert task.required_capability_ids == ['browser.search.google']


def test_execute_task_fails_closed_if_no_card_realizes_all_requirements():
    saved_results = []
    service = object.__new__(ToolTeachService)
    service.registry = SimpleNamespace(eligible_cards_for_task=lambda _task: [])
    service.memory = SimpleNamespace(
        audit_event=lambda **_kwargs: None,
        repository=SimpleNamespace(save_result=saved_results.append),
    )
    service._tool_type_for_unknown = lambda _tool_id: ToolType.CUSTOM
    task = ToolTask(
        tool_id='suggested',
        title='search',
        objective='search Google',
        required_capability_ids=['browser.search.google'],
    )

    result = service.execute_task(task)

    assert result.success is False
    assert result.execution_state.state == 'no_eligible_realization'
    assert result.error_message == 'no_eligible_realization'
    assert saved_results == [result]


def test_explicit_empty_scope_is_not_conflated_with_absent_scope_in_selector():
    registry, repository = _registry(_card('available', ['cap.x']))
    selector = InteractionModeSelector(registry, repository)
    request = InferenceRequest(user_goal='do task', task_role=TaskRole.TOOL_USE)
    task = ToolTask(tool_id='available', title='task', objective='task', required_capability_ids=['cap.x'])
    decision = selector.select(request=request, draft_task=task, suggested_tool_id='available', allowed_tool_ids=[])
    assert decision.selection_outcome == 'no_eligible_realization'
    assert decision.metadata['allowed_tool_ids'] == []
    unrestricted = selector.select(request=request, draft_task=task, suggested_tool_id='available', allowed_tool_ids=None)
    assert unrestricted.selection_outcome == 'selected'


def test_playbook_surfaces_no_realization_separately_from_adapter_missing():
    session = AdaptiveSession(
        user_goal='search Google',
        intent=TaskIntent(intent_key='browser.search', title='search', detected_role=TaskRole.TOOL_USE),
        chosen_pack_id='tools.browser',
        status=AdaptiveSessionStatus.READY_TO_EXECUTE,
        playbook=ExecutionPlaybook(
            goal='search Google',
            pack_id='tools.browser',
            summary='execute',
            steps=[PlaybookStep(phase_key='execute', title='execute', description='execute', status=RunStatus.PARTIAL)],
        ),
    )
    fake_tool_service = SimpleNamespace(
        build_task_for_session=lambda _session: ToolTask(
            tool_id='',
            title='search',
            objective='search Google',
            status=ToolTaskStatus.DEFERRED,
            required_capability_ids=['browser.search.google'],
            metadata={'mode_selection': {'selection_outcome': 'no_eligible_realization'}},
        ),
    )
    executor = ToolOperationalExecutor(fake_tool_service)
    updated = ExecutionPlaybookService(executor=executor).execute(session)
    assert updated.outcome is not None
    assert updated.outcome.metadata['mode'] == 'no_eligible_realization'
    assert updated.metadata['execution_state']['state'] == 'no_eligible_realization'
    assert updated.metadata['execution_state']['state'] != 'adapter_missing'


def test_tool_executor_reports_adapter_missing_when_realization_exists_but_adapter_is_unavailable():
    task = ToolTask(
        tool_id='realized',
        title='task',
        objective='task',
        required_capability_ids=['cap.x'],
        metadata={'mode_selection': {'selection_outcome': 'selected'}},
    )
    card = _card('realized', ['cap.x'])

    class UnavailableAdapter:
        def is_available(self, _card):
            return False

    fake_service = SimpleNamespace(
        build_task_for_session=lambda _session: task,
        registry=SimpleNamespace(pick_card_for_task=lambda _task: card),
        adapters={'fake': UnavailableAdapter()},
    )
    session = AdaptiveSession(
        user_goal='task',
        intent=TaskIntent(intent_key='general.assistance', title='task', detected_role=TaskRole.TOOL_USE),
        chosen_pack_id='tools.local',
    )
    assert ToolOperationalExecutor(fake_service).preflight_status(session) == 'adapter_missing'
