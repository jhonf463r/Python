from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import InferenceRequest
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

        followup_id = ingested['followup_task_id']
        assert ingested['followup_queue_status'] == 'queued'
        cycle = bootstrap.autonomy_cycle_service
        assert any(
            item['id'] == followup_id
            for item in cycle.startup_summary()['actionable_tasks']
        )
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
        assert session.metadata['task_packet']['external_followup_evidence'][0]['id'] == followup_id
        assert session.metadata['decision_context']['metadata']['external_followup_evidence'][0]['id'] == followup_id
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
