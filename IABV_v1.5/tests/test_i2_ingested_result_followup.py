from __future__ import annotations

import hashlib
import copy
from pathlib import Path

import pytest

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import InferenceRequest, PendingTaskStatus
from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker
from iabv_v15.services.security.system_principal_provider import SystemPrincipal

from test_adaptive_task_orchestrator import _orchestrator


class _OfflinePrincipalProvider:
    def get_principal(self) -> SystemPrincipal:
        return SystemPrincipal(sid='S-1-5-21-11-22-33-1001', session_id=7, source='offline_test_fixture')


@pytest.mark.parametrize(
    ('response', 'expected_action', 'expected_lane', 'requires_review'),
    [
        (
            'Causa raiz probable: El bridge acumula eventos sin drenarlos.\n'
            'Cambio vertical recomendado: Ajustar la cola del bridge.\n'
            'file_scope: src/iabv_v15/services/capture/browser_teach_session_service.py\n'
            'Pruebas sugeridas: Medir drenado con carga controlada',
            'prepare_codex_packet',
            'codex_packet',
            True,
        ),
        (
            'Diagnostico breve: La ensenanza del flujo de inicio de sesion no esta clara.\n'
            'Cambio recomendado: Reensenar el paso de confirmacion con evidencia visual.\n'
            'Pruebas sugeridas: Revisar el recuerdo del paso de confirmacion',
            'open_teaching_studio',
            'teaching_replay',
            False,
        ),
    ],
)
def test_ingested_external_result_creates_and_feeds_guarded_followup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response: str,
    expected_action: str,
    expected_lane: str,
    requires_review: bool,
) -> None:
    workspace = tmp_path / 'producer'
    bootstrap = AppBootstrap(str(workspace))
    try:
        # This is a test-only Control Center event through the real broker API.
        broker = HumanApprovalBroker(principal_provider=_OfflinePrincipalProvider())
        broker.register_prompt_handler(
            lambda prompt: broker.approve_external_from_control_center(
                str(prompt['id']), active_dialog_request_id=str(prompt['id'])
            )
        )
        bootstrap.tool_teach_service.human_approval_broker = broker
        bootstrap.config.autonomous_external_launch = True

        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        offline_card = card.model_copy(update={
            'metadata': {
                **card.metadata,
                'launch_mode': 'desktop_app',
                'response_capture_mode': 'direct_text',
                'requires_manual_pasteback': False,
                'direct_response_text': response,
                'offline_test_fixture': True,
            }
        })
        bootstrap.tool_record_repository.save_card(offline_card)
        bootstrap.tool_registry.refresh_card(offline_card)

        payload = {
            'session_id': 'offline-i2-source-session',
            'intent': {'title': 'Diagnosticar el flujo local', 'intent_key': 'system.diagnostic', 'site_hint': 'general'},
            'context': {
                'site_id': 'general',
                'live_audit': {'summary': 'El caso requiere una consulta tecnica.', 'decision_action': 'consult_codex'},
            },
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Consulta offline determinista para I2.'},
            'metadata': {},
        }
        ingested = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )

        assert ingested['status'] == 'ingested'
        assert ingested['response_source'] == 'offline_test_auto_capture'
        assert ingested['response_provenance'] == 'offline_test'
        source_task_id = ingested['task_id']
        source_result_id = ingested['result_id']
        assert source_task_id and source_result_id
        source_task = bootstrap.tool_record_repository.get_task(source_task_id)
        source_results = bootstrap.tool_record_repository.list_results(task_id=source_task_id, limit=20)
        source_result = next(item for item in source_results if item.result_id == source_result_id)
        assert source_task is not None
        assert source_result.task_id == source_task.task_id
        assert source_task.metadata['autonomous_consultation']['response_ingested'] is True
        assert source_result.metadata['external_consult_response']['response_digest'] == hashlib.sha256(
            response.encode('utf-8')
        ).hexdigest()

        # Recapture parameters come from the persisted task/result identity.
        persisted_consultation = dict(source_task.metadata['autonomous_consultation'])
        recapture_calls = []

        def fake_recapture(**kwargs):
            recapture_calls.append(kwargs)
            execution_state = source_result.execution_state.model_copy(update={
                'metadata': {**source_result.execution_state.metadata, 'response_captured': False},
            })
            return source_task, source_result.model_copy(update={
                'output_text': '',
                'execution_state': execution_state,
            }), None

        monkeypatch.setattr(bootstrap.tool_teach_service, 'execute_external_consultation', fake_recapture)
        altered_values = {
            'session_profile_dir': f"{persisted_consultation['session_profile_dir']}\\caller-changed",
            'session_label': f"{persisted_consultation['session_label']} caller-changed",
            'response_capture_mode': 'manual_pasteback',
        }
        for field, altered_value in altered_values.items():
            rejected_recapture = bootstrap.autonomous_evolution_service.reingest_existing_session(
                existing_consultation={**persisted_consultation, field: altered_value},
                adaptive_payload=payload,
                user_goal='Diagnosticar el flujo local',
                source='offline_test',
            )
            assert rejected_recapture['pre_capture_ingested'] is False
            assert rejected_recapture['reason'] == f'recapture_identity_mismatch:{field}'
            assert recapture_calls == []

        valid_recapture = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=persisted_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert valid_recapture['pre_capture_ingested'] is False
        assert len(recapture_calls) == 1
        recapture_parameters = recapture_calls[0]['goal_parameters']
        assert recapture_parameters['response_capture_mode'] == source_task.metadata['response_capture_mode']
        assert recapture_parameters['session_label'] == source_task.metadata['session_label']
        assert recapture_parameters['session_profile_dir'] == source_task.metadata['session_profile_dir']
        assert recapture_parameters['thread_title'] == source_task.metadata['thread_title']
        assert recapture_parameters['site_id'] == source_task.site_id
        assert recapture_parameters['diagnostic_category'] == source_task.metadata['diagnostic_category']
        assert recapture_parameters['incident_kind'] == source_task.metadata['incident_kind']

        # Missing and explicitly empty identity values are both rejected for
        # required fields. The persisted pair is restored after each fixture.
        original_task, original_result = source_task, source_result

        def persist_pair(task, result) -> None:
            bootstrap.tool_record_repository.save_task(task)
            bootstrap.tool_record_repository.save_result(result)

        # ToolTask.site_id=None is absence at that source, so an authorized
        # persisted goal_parameters.site_id remains usable for this recapture.
        persisted_site_id = str(original_task.metadata['goal_parameters'].get('site_id') or '').strip()
        assert persisted_site_id
        no_model_site_task = original_task.model_copy(update={'site_id': None})
        persist_pair(no_model_site_task, original_result)
        recapture_calls.clear()
        task_site_fallback = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=persisted_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert task_site_fallback['pre_capture_ingested'] is False
        assert len(recapture_calls) == 1
        assert recapture_calls[0]['site_id'] == persisted_site_id
        assert recapture_calls[0]['goal_parameters']['site_id'] == persisted_site_id
        persist_pair(original_task, original_result)

        def pair_without_site(*, empty_values: bool = False):
            task_meta = copy.deepcopy(dict(original_task.metadata or {}))
            task_goal = dict(task_meta.get('goal_parameters') or {})
            task_consult = dict(task_meta['autonomous_consultation'])
            result_meta = copy.deepcopy(dict(original_result.metadata or {}))
            result_consult = dict(result_meta['autonomous_consultation'])
            for container in (task_meta, task_goal, task_consult, result_consult):
                if empty_values:
                    container['site_id'] = ''
                else:
                    container.pop('site_id', None)
            task_meta['goal_parameters'] = task_goal
            task_meta['autonomous_consultation'] = task_consult
            result_meta['autonomous_consultation'] = result_consult
            return (
                original_task.model_copy(update={'site_id': None, 'metadata': task_meta}),
                original_result.model_copy(update={'metadata': result_meta}),
                task_consult,
            )

        # With every authorized source absent, or explicitly empty, no site is
        # invented and the optional executor argument remains None.
        for empty_values in (False, True):
            site_free_task, site_free_result, site_free_consultation = pair_without_site(
                empty_values=empty_values
            )
            persist_pair(site_free_task, site_free_result)
            recapture_calls.clear()
            no_site = bootstrap.autonomous_evolution_service.reingest_existing_session(
                existing_consultation=site_free_consultation,
                adaptive_payload=payload,
                user_goal='Diagnosticar el flujo local',
                source='offline_test',
            )
            assert no_site['pre_capture_ingested'] is False
            assert len(recapture_calls) == 1
            assert recapture_calls[0]['site_id'] is None
            assert recapture_calls[0]['goal_parameters']['site_id'] is None
            persist_pair(original_task, original_result)

        # Two non-empty persisted identifiers are an ambiguity, while a site
        # supplied solely by the caller has no authority to fill a blank.
        conflict_task_meta = copy.deepcopy(dict(original_task.metadata or {}))
        conflict_goal = dict(conflict_task_meta.get('goal_parameters') or {})
        conflict_goal['site_id'] = 'persisted-site-beta'
        conflict_task_meta['goal_parameters'] = conflict_goal
        conflict_task_meta.pop('site_id', None)
        conflict_consultation = dict(conflict_task_meta['autonomous_consultation'])
        conflict_consultation.pop('site_id', None)
        conflict_task_meta['autonomous_consultation'] = conflict_consultation
        conflict_result_meta = copy.deepcopy(dict(original_result.metadata or {}))
        conflict_result_consultation = dict(conflict_result_meta['autonomous_consultation'])
        conflict_result_consultation.pop('site_id', None)
        conflict_result_meta['autonomous_consultation'] = conflict_result_consultation
        conflict_site_task = original_task.model_copy(update={
            'site_id': 'persisted-site-alpha',
            'metadata': conflict_task_meta,
        })
        conflict_site_result = original_result.model_copy(update={'metadata': conflict_result_meta})
        persist_pair(conflict_site_task, conflict_site_result)
        recapture_calls.clear()
        site_conflict = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=conflict_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert site_conflict['reason'] == 'recapture_identity_conflict:site_id'
        assert recapture_calls == []
        persist_pair(original_task, original_result)

        site_free_task, site_free_result, site_free_consultation = pair_without_site()
        persist_pair(site_free_task, site_free_result)
        recapture_calls.clear()
        caller_only_site = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation={**site_free_consultation, 'site_id': 'caller-only-site'},
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert caller_only_site['reason'] == 'recapture_identity_mismatch:site_id'
        assert recapture_calls == []
        persist_pair(original_task, original_result)

        def pair_with_consultation_field(field: str, value: object, *, present: bool):
            task_meta = copy.deepcopy(dict(original_task.metadata or {}))
            task_goal = dict(task_meta.get('goal_parameters') or {})
            task_consult = dict(task_meta['autonomous_consultation'])
            result_meta = copy.deepcopy(dict(original_result.metadata or {}))
            result_consult = dict(result_meta['autonomous_consultation'])
            execution_meta = dict(original_result.execution_state.metadata or {})
            for container in (task_goal, task_meta, task_consult, result_consult, execution_meta):
                if present:
                    container[field] = value
                else:
                    container.pop(field, None)
            if field == 'session_profile_dir':
                if present:
                    execution_meta['browser_profile_dir'] = value
                else:
                    execution_meta.pop('browser_profile_dir', None)
            task_meta['goal_parameters'] = task_goal
            task_meta['autonomous_consultation'] = task_consult
            result_meta['autonomous_consultation'] = result_consult
            task_copy = original_task.model_copy(update={'metadata': task_meta})
            execution_state = original_result.execution_state.model_copy(update={'metadata': execution_meta})
            result_copy = original_result.model_copy(update={
                'metadata': result_meta,
                'execution_state': execution_state,
            })
            return task_copy, result_copy, task_consult

        for field in ('session_profile_dir', 'response_capture_mode'):
            for present, explicit_value in ((False, None), (True, '')):
                task_copy, result_copy, consultation_copy = pair_with_consultation_field(
                    field, explicit_value, present=present
                )
                persist_pair(task_copy, result_copy)
                recapture_calls.clear()
                rejected = bootstrap.autonomous_evolution_service.reingest_existing_session(
                    existing_consultation=consultation_copy,
                    adaptive_payload=payload,
                    user_goal='Diagnosticar el flujo local',
                    source='offline_test',
                )
                assert rejected['pre_capture_ingested'] is False
                assert rejected['reason'] == f'recapture_identity_incomplete:{field}'
                assert recapture_calls == []
                persist_pair(original_task, original_result)

        # The execution state is the observed value, the paired consultation
        # is its persisted snapshot, and disagreements fail before recapture.
        conflict_meta = copy.deepcopy(dict(original_result.execution_state.metadata or {}))
        conflict_meta['session_profile_dir'] = f"{persisted_consultation['session_profile_dir']}\\different"
        conflict_state = original_result.execution_state.model_copy(update={'metadata': conflict_meta})
        conflict_result = original_result.model_copy(update={'execution_state': conflict_state})
        persist_pair(original_task, conflict_result)
        recapture_calls.clear()
        conflict = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=persisted_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert conflict['reason'] == 'recapture_identity_conflict:session_profile_dir'
        assert recapture_calls == []
        persist_pair(original_task, original_result)

        # Historical fixture: the paired nested consultation shape persisted
        # symmetrically by plan_or_execute since 1968b640c remains; later flat
        # task/result execution mirrors are absent. The required isolation
        # policy remains in the original goal_parameters contract.
        legacy_task_meta = copy.deepcopy(dict(original_task.metadata or {}))
        legacy_goal = dict(legacy_task_meta.get('goal_parameters') or {})
        for field in (
            'response_capture_mode', 'session_profile_dir', 'session_scope', 'session_label',
            'thread_key', 'thread_title', 'site_id', 'diagnostic_category', 'incident_kind',
            'isolated_session_required', 'actual_assistant_kind',
        ):
            legacy_task_meta.pop(field, None)
            if field != 'isolated_session_required':
                legacy_goal.pop(field, None)
        legacy_task_meta['goal_parameters'] = legacy_goal
        legacy_result_meta = copy.deepcopy(dict(original_result.metadata or {}))
        legacy_execution = dict(original_result.execution_state.metadata or {})
        for field in (
            'response_capture_mode', 'session_profile_dir', 'browser_profile_dir', 'session_scope',
            'session_label', 'thread_key', 'thread_title', 'isolated_session', 'assistant_kind',
        ):
            legacy_execution.pop(field, None)
        legacy_task = original_task.model_copy(update={'metadata': legacy_task_meta})
        legacy_result = original_result.model_copy(update={
            'execution_state': original_result.execution_state.model_copy(update={'metadata': legacy_execution}),
            'metadata': legacy_result_meta,
        })
        persist_pair(legacy_task, legacy_result)
        recapture_calls.clear()
        legacy_consultation = dict(legacy_task_meta['autonomous_consultation'])
        legacy_resulting = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=legacy_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert legacy_resulting['pre_capture_ingested'] is False
        assert len(recapture_calls) == 1, legacy_resulting
        assert recapture_calls[0]['goal_parameters']['session_profile_dir'] == persisted_consultation['session_profile_dir']
        assert recapture_calls[0]['goal_parameters']['response_capture_mode'] == persisted_consultation['response_capture_mode']

        # The same historical nested shape is incompatible when a required
        # identity field is absent from both members of the persisted pair.
        incomplete_legacy_consultation = {
            key: value for key, value in legacy_consultation.items() if key != 'session_profile_dir'
        }
        incomplete_task_meta = {
            **legacy_task_meta,
            'autonomous_consultation': incomplete_legacy_consultation,
        }
        incomplete_result_meta = {
            **legacy_result_meta,
            'autonomous_consultation': incomplete_legacy_consultation,
        }
        persist_pair(
            legacy_task.model_copy(update={'metadata': incomplete_task_meta}),
            legacy_result.model_copy(update={'metadata': incomplete_result_meta}),
        )
        recapture_calls.clear()
        incomplete_legacy = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=incomplete_legacy_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert incomplete_legacy['reason'] == 'recapture_identity_incomplete:session_profile_dir'
        assert recapture_calls == []
        persist_pair(original_task, original_result)

        # Optional category context preserves unknown versus explicitly blank:
        # an unpersisted caller value cannot be treated as recorded identity.
        unknown_category_task_meta = copy.deepcopy(dict(original_task.metadata or {}))
        unknown_category_goal = dict(unknown_category_task_meta.get('goal_parameters') or {})
        unknown_category_task_meta.pop('diagnostic_category', None)
        unknown_category_goal.pop('diagnostic_category', None)
        unknown_category_task_meta['goal_parameters'] = unknown_category_goal
        unknown_category_task = original_task.model_copy(update={'metadata': unknown_category_task_meta})
        persist_pair(unknown_category_task, original_result)
        recapture_calls.clear()
        unknown_category = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation={**persisted_consultation, 'diagnostic_category': ''},
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert unknown_category['reason'] == 'recapture_identity_mismatch:diagnostic_category'
        assert recapture_calls == []
        persist_pair(original_task, original_result)

        blank_category_task_meta = copy.deepcopy(dict(original_task.metadata or {}))
        blank_category_goal = dict(blank_category_task_meta.get('goal_parameters') or {})
        blank_category_task_meta['diagnostic_category'] = ''
        blank_category_goal['diagnostic_category'] = ''
        blank_category_task_meta['goal_parameters'] = blank_category_goal
        blank_category_task = original_task.model_copy(update={'metadata': blank_category_task_meta})
        persist_pair(blank_category_task, original_result)
        recapture_calls.clear()
        explicit_blank_category = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation={**persisted_consultation, 'diagnostic_category': ''},
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert explicit_blank_category['pre_capture_ingested'] is False
        assert len(recapture_calls) == 1
        assert recapture_calls[0]['diagnostic_category'] == ''
        persist_pair(original_task, original_result)

        # Observed isolation is not the configured requirement: failure to
        # satisfy required=True blocks, while observed=True with required=False
        # remains safe and preserves the false requirement passed to recapture.
        required_goal = dict(original_task.metadata['goal_parameters'])
        required_goal['isolated_session_required'] = True
        required_metadata = {**dict(original_task.metadata), 'isolated_session_required': True, 'goal_parameters': required_goal}
        persist_pair(
            original_task.model_copy(update={'metadata': required_metadata}),
            original_result.model_copy(update={
                'execution_state': original_result.execution_state.model_copy(update={
                    'metadata': {**dict(original_result.execution_state.metadata), 'isolated_session_required': True},
                }),
            }),
        )
        recapture_calls.clear()
        isolation_failure = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=persisted_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert isolation_failure['reason'] == 'recapture_isolation_not_satisfied'
        assert recapture_calls == []
        persist_pair(original_task, original_result)

        observed_meta = dict(original_result.execution_state.metadata or {})
        observed_meta['isolated_session'] = True
        observed_consultation = {**persisted_consultation, 'isolated_session': True}
        observed_task_meta = {
            **dict(original_task.metadata),
            'autonomous_consultation': observed_consultation,
        }
        observed_result_meta = {
            **dict(original_result.metadata),
            'autonomous_consultation': observed_consultation,
        }
        persist_pair(
            original_task.model_copy(update={'metadata': observed_task_meta}),
            original_result.model_copy(update={
                'metadata': observed_result_meta,
                'execution_state': original_result.execution_state.model_copy(update={'metadata': observed_meta}),
            }),
        )
        recapture_calls.clear()
        observed_extra_isolation = bootstrap.autonomous_evolution_service.reingest_existing_session(
            existing_consultation=observed_consultation,
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert observed_extra_isolation['pre_capture_ingested'] is False
        assert len(recapture_calls) == 1
        assert recapture_calls[0]['goal_parameters']['isolated_session_required'] is False
        persist_pair(original_task, original_result)

        followup_id = ingested['followup_task_id']
        assert ingested['followup_queue_status'] == 'queued'
        cycle = bootstrap.autonomy_cycle_service
        assert any(
            item['id'] == followup_id
            for item in cycle.startup_summary()['actionable_tasks']
        )
        startup_item = next(item for item in cycle.startup_summary()['actionable_tasks'] if item['id'] == followup_id)
        assert startup_item['metadata']['proposal_only'] is True
        queued = cycle.queue.get(followup_id)
        assert queued is not None
        assert queued.next_action == expected_action
        assert queued.metadata['execution_lane'] == expected_lane
        assert queued.metadata['source_task_id'] == source_task_id
        assert queued.metadata['source_result_id'] == source_result_id
        assert queued.metadata['response_provenance'] == 'offline_test'
        assert queued.metadata['proposal_only'] is True
        assert queued.metadata['sandbox_required'] is requires_review
        assert queued.metadata['requires_human_approval'] is requires_review

        payload['metadata'] = {'autonomous_evolution': dict(ingested)}
        forged_response = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            response_text=response + '\nCambio inyectado por caller',
            source='offline_test',
        )
        assert forged_response['status'] == 'identity_mismatch'
        forged_query_payload = {'metadata': {'autonomous_evolution': {
            **dict(ingested),
            'query': {'issue_hint': 'consulta distinta'},
        }}}
        forged_query = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=forged_query_payload,
            user_goal='Diagnosticar el flujo local',
            response_text=response,
            source='offline_test',
        )
        assert forged_query['status'] == 'identity_mismatch'
        assert bootstrap.tool_record_repository.get_task(source_task_id).metadata[
            'autonomous_consultation'
        ]['response_digest'] == hashlib.sha256(response.encode('utf-8')).hexdigest()

        # Re-ingesting the same persisted task/result is idempotent.
        repeated = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            response_text=response,
            source='offline_test',
        )
        assert repeated['followup_task_id'] == followup_id
        assert len([item for item in cycle.queue.list_actionable() if item.id == followup_id]) == 1

        before_task = bootstrap.tool_record_repository.get_task(source_task_id).model_dump(mode='json')
        before_result = next(
            item for item in bootstrap.tool_record_repository.list_results(task_id=source_task_id, limit=20)
            if item.result_id == source_result_id
        ).model_dump(mode='json')
        before_issues = [item.model_dump(mode='json') for item in bootstrap.pending_issue_repository.list_recent(limit=100)]
        malformed_cases = [
            ({key: value for key, value in ingested.items() if key != 'task_id'}, 'missing_task_id'),
            ({key: value for key, value in ingested.items() if key != 'result_id'}, 'missing_result_id'),
            ({**ingested, 'task_id': 'unknown-task-id'}, 'source_task_not_found'),
            ({**ingested, 'result_id': 'crossed-result-id'}, 'source_result_not_found_for_task'),
            ({**ingested, 'selected_tool_id': 'different-tool'}, 'consultation_metadata_mismatch'),
        ]
        for consultation, expected_error in malformed_cases:
            rejected = bootstrap.autonomous_evolution_service.ingest_consult_response(
                adaptive_payload={'metadata': {'autonomous_evolution': consultation}},
                user_goal='Diagnosticar el flujo local',
                response_text=response,
                source='offline_test',
            )
            assert rejected['status'] == 'identity_mismatch'
            assert rejected['identity_error'] == expected_error
            assert bootstrap.tool_record_repository.get_task(source_task_id).model_dump(mode='json') == before_task
            after_result = next(
                item for item in bootstrap.tool_record_repository.list_results(task_id=source_task_id, limit=20)
                if item.result_id == source_result_id
            )
            assert after_result.model_dump(mode='json') == before_result
            assert [item.model_dump(mode='json') for item in bootstrap.pending_issue_repository.list_recent(limit=100)] == before_issues
            assert cycle.queue.get(followup_id).status == PendingTaskStatus.PENDING

        # A real result from another task cannot be crossed into this consultation.
        from uuid import uuid4
        other_task_id, other_result_id = str(uuid4()), str(uuid4())
        other_consultation = dict(source_task.metadata['autonomous_consultation'])
        other_consultation.update({'task_id': other_task_id, 'result_id': other_result_id})
        other_task = source_task.model_copy(update={
            'task_id': other_task_id,
            'metadata': {**source_task.metadata, 'autonomous_consultation': other_consultation},
        })
        source_result_copy = next(
            item for item in bootstrap.tool_record_repository.list_results(task_id=source_task_id, limit=20)
            if item.result_id == source_result_id
        )
        other_result = source_result_copy.model_copy(update={
            'task_id': other_task_id,
            'result_id': other_result_id,
            'metadata': {**source_result_copy.metadata, 'autonomous_consultation': other_consultation},
        })
        bootstrap.tool_record_repository.save_task(other_task)
        bootstrap.tool_record_repository.save_result(other_result)
        crossed_pair = {**ingested, 'result_id': other_result_id}
        rejected_crossed_pair = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload={'metadata': {'autonomous_evolution': crossed_pair}},
            user_goal='Diagnosticar el flujo local',
            response_text=response,
            source='offline_test',
        )
        assert rejected_crossed_pair['status'] == 'identity_mismatch'
        assert rejected_crossed_pair['identity_error'] == 'source_result_not_found_for_task'
        assert bootstrap.tool_record_repository.get_task(source_task_id).model_dump(mode='json') == before_task
        assert [item.model_dump(mode='json') for item in bootstrap.pending_issue_repository.list_recent(limit=100)] == before_issues

        # A crossed result ID is rejected before changing the persisted source records.
        crossed_payload = {'metadata': {'autonomous_evolution': {
            **dict(ingested),
            'result_id': 'crossed-result-id',
        }}}
        crossed = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=crossed_payload,
            user_goal='Diagnosticar el flujo local',
            response_text=response,
            source='offline_test',
        )
        assert crossed['status'] == 'identity_mismatch'
        assert cycle.queue.get(followup_id) is not None

        # The actual next orchestrator evaluation reads the same persisted queue
        # through AutonomyCycleService and receives the original source IDs.
        downstream, _episodes = _orchestrator(tmp_path / 'consumer')
        downstream.autonomy_cycle_service = cycle
        _route, _result, session = downstream.handle_request(
            InferenceRequest(user_goal='Preparar el siguiente paso del diagnostico', auto_route=True)
        )
        evidence = session.context.metadata['external_followup_evidence']
        assert evidence[0]['id'] == followup_id
        assert evidence[0]['metadata']['source_task_id'] == source_task_id
        assert evidence[0]['metadata']['source_result_id'] == source_result_id
        assert evidence[0]['metadata']['proposal_only'] is True
        assert session.metadata['task_packet']['external_followup_evidence'][0]['id'] == followup_id
        assert session.metadata['task_packet']['external_followup_evidence'][0]['metadata']['proposal_only'] is True
        assert session.metadata['decision_context']['metadata']['external_followup_evidence'][0]['id'] == followup_id
        assert session.metadata['decision_context']['metadata']['external_followup_evidence'][0]['metadata']['proposal_only'] is True

        # A terminal lifecycle is preserved by exact-source reingestion.
        completed = cycle.queue.mark_status(followup_id, PendingTaskStatus.COMPLETED)
        assert completed is not None and completed.status == PendingTaskStatus.COMPLETED
        repeated_terminal = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            response_text=response,
            source='offline_test',
        )
        assert repeated_terminal['followup_queue_status'] == 'already_exists'
        assert cycle.queue.get(followup_id).status == PendingTaskStatus.COMPLETED
        assert len([item for item in cycle.queue.list_all() if item.id == followup_id]) == 1

        conflicting_metadata = {**cycle.queue.get(followup_id).metadata, 'source_result_id': 'foreign-result'}
        cycle.queue.upsert(cycle.queue.get(followup_id).model_copy(update={'metadata': conflicting_metadata}))
        rejected_conflict = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            response_text=response,
            source='offline_test',
        )
        assert rejected_conflict['followup_queue_status'] == 'identity_conflict'
        retained_conflict = cycle.queue.get(followup_id)
        assert retained_conflict.status == PendingTaskStatus.COMPLETED
        assert retained_conflict.metadata['source_result_id'] == 'foreign-result'
    finally:
        bootstrap.autonomy_cycle_service = None


def test_missing_or_unverified_capture_never_creates_actionable_followup(tmp_path: Path) -> None:
    bootstrap = AppBootstrap(str(tmp_path / 'missing-capture'))
    try:
        card = bootstrap.tool_record_repository.get_card('codex_installed')
        assert card is not None
        offline_candidate = card.model_copy(update={
            'metadata': {
                **card.metadata,
                'launch_mode': 'desktop_app',
                'response_capture_mode': 'direct_text',
                'requires_manual_pasteback': False,
                'direct_response_text': 'Causa raiz probable: Texto sintético sin una captura comprobada.\n'
                'Cambio vertical recomendado: Ajustar el flujo de trabajo.\n'
                'file_scope: src/iabv_v15/services/evolution/example.py\n'
                'Pruebas sugeridas: Verificar la ruta offline',
            }
        })
        bootstrap.tool_record_repository.save_card(offline_candidate)
        bootstrap.tool_registry.refresh_card(offline_candidate)
        payload = {
            'session_id': 'offline-no-approval-session',
            'intent': {'title': 'Diagnosticar el flujo local', 'intent_key': 'system.diagnostic', 'site_hint': 'general'},
            'context': {'site_id': 'general', 'live_audit': {'decision_action': 'consult_codex'}},
            'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'Consulta sin aprobación ni captura.'},
            'metadata': {},
        }
        prepared = bootstrap.autonomous_evolution_service.plan_or_execute(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            source='offline_test',
        )
        assert prepared['status'] != 'ingested'
        assert prepared.get('task_id') and prepared.get('result_id')
        payload['metadata'] = {'autonomous_evolution': dict(prepared)}
        ingested = bootstrap.autonomous_evolution_service.ingest_consult_response(
            adaptive_payload=payload,
            user_goal='Diagnosticar el flujo local',
            response_text=(
                'Causa raiz probable: La consulta no llegó a ejecutarse.\n'
                'Cambio vertical recomendado: Revisar el permiso pendiente.\n'
                'file_scope: src/iabv_v15/services/evolution/example.py\n'
                'Pruebas sugeridas: Verificar captura'
            ),
            source='offline_test',
        )
        assert ingested['followup_queue_status'] != 'queued'
        assert not any(
            item.metadata.get('contract_version') == 'external_consultation_followup/v1'
            for item in bootstrap.autonomy_cycle_service.queue.list_all()
        )
    finally:
        bootstrap.autonomy_cycle_service = None
