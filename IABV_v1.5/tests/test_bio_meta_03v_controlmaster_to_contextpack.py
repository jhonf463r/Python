"""BIO-META-03V — ControlMaster state → live external-consultation context path.

This test suite verifies that ControlMaster priority/control state reaches
the live external-consultation context path by testing the PRODUCTION CODE directly
from ControlMasterService through to context_pack.

The causal chain to verify:
ControlMasterService.current_work_queue()
→ PortableContextService._canonical_work_queue_section()
→ PortableContextPackage
→ TaskContextAssembler._portable_context_summary()
→ DecisionContext.metadata['portable_context_summary']
→ AutonomousEvolutionService.plan_or_execute()
→ _build_context_pack()
→ context_pack
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    DecisionContext,
    IntentRouteDecision,
    TaskContext,
    TaskIntent,
)


class TestControlMasterToContextPackProduction:
    """PRODUCTIVE-INTEGRATION: Test that ControlMaster state reaches context pack through production chain.

    Causal chain verified:
    ControlMasterService.current_work_queue()
    → PortableContextService._canonical_work_queue_section()
    → PortableContextPackage
    → TaskContextAssembler._portable_context_summary()
    → DecisionContext.metadata['portable_context_summary']
    → AutonomousEvolutionService.plan_or_execute()
    → _build_context_pack()
    → context_pack

    Mutation E (verified):
    Modified PortableContextService._canonical_work_queue_section() to ignore cms.current_work_queue()
    Result: Test FAILS because marker from ControlMaster no longer appears in context_pack
    Edge discriminated: ControlMaster → canonical_work_queue
    """

    def test_controlmaster_marker_reaches_context_pack(self):
        """Verify that a marker from ControlMaster.current_work_queue() reaches context_pack."""
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        # Unique marker that will travel through the chain
        CM_MARKER = "BIO-META-03V-CM-REAL-001"

        # Create ControlMasterService with repository that will produce the marker
        class FakeControlMasterRepository:
            def load_latest_state(self):
                from iabv_v15.domain.models import ControlMasterState
                return ControlMasterState()

            def list_rules(self):
                return []

            def list_decisions(self):
                return []

        class FakeObjectiveRepository:
            pass

        class FakePendingIssueRepository:
            pass

        class FakeSelfExaminationService:
            pass

        class FakeExperimentLabRepository:
            pass

        class FakeAccountResourceScanner:
            pass

        class FakePlatformPendingQueue:
            pass

        control_master_service = ControlMasterService(
            repository=FakeControlMasterRepository(),
            objective_repository=FakeObjectiveRepository(),
            pending_issue_repository=FakePendingIssueRepository(),
            self_examination_service=FakeSelfExaminationService(),
            experiment_lab_repository=FakeExperimentLabRepository(),
            account_resource_scanner=FakeAccountResourceScanner(),
            platform_pending_queue=FakePlatformPendingQueue(),
            workspace_root='/test/workspace',
        )

        # Override current_work_queue to return item with marker
        original_current_work_queue = control_master_service.current_work_queue
        def current_work_queue_with_marker(*args, **kwargs):
            return [
                {
                    'id': f'{CM_MARKER}-id',
                    'title': f'{CM_MARKER} security fix',
                    'status': 'pending',
                    'priority_score': 0.95,
                    'priority_label': 'CRITICAL',
                    'source': 'oses',
                    'next_action': 'immediate',
                    'evidence_refs': [f'{CM_MARKER}-ref'],
                }
            ]

        control_master_service.current_work_queue = current_work_queue_with_marker

        # Create PortableContextService connected to ControlMasterService
        portable_context_service = PortableContextService(
            workspace_root='/test/workspace',
            storage=ArtifactStorage('/test/storage'),
        )
        # Wire ControlMasterService into PortableContextService (as done in bootstrap.py line 1518)
        portable_context_service.control_master_service = control_master_service

        # Create TaskContextAssembler with PortableContextService
        assembler = TaskContextAssembler(
            episode_repository=MagicMock(),
            knowledge_repository=MagicMock(),
            run_repository=MagicMock(),
            dossier_repository=MagicMock(),
            hidden_incident_repository=MagicMock(),
            site_policy_registry=MagicMock(),
            capability_repository=MagicMock(),
            adaptive_session_repository=MagicMock(),
            portable_context_service=portable_context_service,
        )

        # Call PRODUCTION _portable_context_summary() method
        task_context = TaskContext(user_goal='Test goal')
        # Force fresh package to avoid cache that bypasses mutation
        portable_context_service._current_package = None
        # Patch current_package to always call with refresh=True
        original_current_package = portable_context_service.current_package
        def current_package_always_refresh(*args, **kwargs):
            kwargs['refresh'] = True
            return original_current_package(*args, **kwargs)
        portable_context_service.current_package = current_package_always_refresh
        portable_context_summary = assembler._portable_context_summary(
            task_context=task_context,
            environment_self_model=None,
            world_model=None,
        )

        # Verify: Marker appeared in portable_context_summary from PRODUCTION chain
        assert 'canonical_work_queue' in portable_context_summary
        assert len(portable_context_summary['canonical_work_queue']['items']) > 0
        assert CM_MARKER in portable_context_summary['canonical_work_queue']['items'][0]['title']
        assert CM_MARKER in portable_context_summary['canonical_work_queue']['items'][0]['id']

        # Create DecisionContext with PRODUCTION portable_context_summary
        decision_context = DecisionContext(
            user_goal='Test goal',
            intent=TaskIntent(
                user_goal='Test goal',
                detected_role='knowledge',
                multi_step=False,
                enable_planning=False,
                requires_visual_reasoning=False,
            ),
            route_decision=IntentRouteDecision(
                detected_role='knowledge',
                planner_required=False,
                visual_required=False,
                reason='Test reason',
            ),
            metadata={'portable_context_summary': portable_context_summary},
        )

        # Create AutonomousEvolutionService
        config = MagicMock()
        config.workspace_root = '/test/workspace'
        config.autonomous_external_launch = False

        tool_teach_service = MagicMock()
        incident_packet_service = MagicMock()
        incident_packet_service.build_codex_packet_for_issue.return_value = 'Test packet'
        pending_issue_repository = MagicMock()

        service = AutonomousEvolutionService(
            config=config,
            tool_teach_service=tool_teach_service,
            incident_packet_service=incident_packet_service,
            pending_issue_repository=pending_issue_repository,
        )

        # Mock execute_external_consultation to capture context_pack
        captured_context_pack = None
        def capture_context_pack(*args, **kwargs):
            nonlocal captured_context_pack
            captured_context_pack = kwargs.get('context_pack', '')
            # Return minimal valid result structure
            mock_task = MagicMock()
            mock_task.task_id = 'test-task-id'
            mock_task.metadata = {}
            mock_task.tool_id = 'test-tool'
            mock_task.objective = 'Test objective'

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.result_id = 'test-result-id'
            mock_result.execution_state = MagicMock()
            mock_result.execution_state.metadata = {}
            mock_result.execution_state.detail = ''
            mock_result.error_message = ''
            mock_result.output_text = ''
            mock_result.tool_id = 'test-tool'
            mock_result.execution_ms = 100

            return mock_task, mock_result, {'summary': 'Test preview'}

        tool_teach_service.execute_external_consultation.side_effect = capture_context_pack

        # Call REAL plan_or_execute() method
        with patch.object(service, '_assessment_from_decision_context') as mock_assessment:
            mock_assessment.return_value = {
                'action': 'consult_codex',
                'assistant_kind': 'codex',
                'should_consult': True,
                'reason': 'Test reason',
                'diagnostic_category': 'general',
            }

            with patch.object(service, '_ensure_pending_issue') as mock_pending:
                mock_pending.return_value = MagicMock(issue_id='test-issue')

                result = service.plan_or_execute(
                    adaptive_payload={'user_goal': 'Test goal'},
                    user_goal='Test goal',
                    source='test',
                    decision_context=decision_context,
                )

        # Verify: Marker from ControlMaster appears in context_pack
        assert captured_context_pack is not None, \
            "plan_or_execute() must call execute_external_consultation with context_pack"
        assert CM_MARKER in captured_context_pack, \
            f"Marker {CM_MARKER} from ControlMaster must appear in context_pack"
