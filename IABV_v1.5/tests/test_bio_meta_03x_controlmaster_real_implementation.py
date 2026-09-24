"""BIO-META-03X — ControlMasterService.current_work_queue() REAL implementation → context_pack

This test suite verifies that the REAL PRODUCTION implementation of
ControlMasterService.current_work_queue() (not overridden) produces items
that traverse the productive chain to context_pack when fed with deterministic
sources.

Causal chain to verify:
deterministic source (ObjectiveRepository)
→ ControlMasterService.current_work_queue() REAL
→ _project_objective_queue_items() REAL
→ _make_item() REAL
→ scoring → _score_to_label() REAL
→ current_work_queue() result
→ PortableContextService._canonical_work_queue_section() REAL
→ PortableContextPackage REAL
→ TaskContextAssembler._portable_context_summary() REAL
→ DecisionContext.metadata REAL
→ AutonomousEvolutionService.plan_or_execute() REAL
→ _build_context_pack() REAL
→ context_pack

PROHIBITED:
- control_master_service.current_work_queue = ... (NO override)
- patch.object(control_master_service, "current_work_queue", ...) (NO override)
- MagicMock(return_value=...) for current_work_queue() (NO override)

REQUIRED:
- Execute REAL current_work_queue() implementation
- Use deterministic source that respects production contracts
- Observe REAL projector (_project_objective_queue_items)
- Verify REAL scoring and priority_label production
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    DecisionContext,
    IntentRouteDecision,
    ObjectiveNode,
    ObjectiveStatus,
    TaskContext,
    TaskIntent,
)


class TestControlMasterRealImplementationToContextPack:
    """REAL IMPLEMENTATION: Test that REAL current_work_queue() produces items that reach context_pack.

    Causal chain verified:
    ObjectiveRepository (deterministic source)
    → ControlMasterService.current_work_queue() REAL
    → _project_objective_queue_items() REAL
    → _make_item() REAL
    → scoring REAL
    → PortableContextService._canonical_work_queue_section() REAL
    → PortableContextPackage REAL
    → TaskContextAssembler._portable_context_summary() REAL
    → DecisionContext.metadata REAL
    → AutonomousEvolutionService.plan_or_execute() REAL
    → _build_context_pack() REAL
    → context_pack

    Mutation F (verified):
    Modified ControlMasterService._project_objective_queue_items() to return []
    Result: Test FAILS because marker from source no longer appears in current_work_queue()
    Edge discriminated: source → projector → current_work_queue
    """

    def test_current_work_queue_real_implementation_reaches_context_pack(self):
        """Verify that REAL current_work_queue() implementation produces marker that reaches context_pack."""
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        # Unique marker that will be born in the source object
        CM_MARKER = "BIO-META-03X-CM-SOURCE-001"

        # Create deterministic ObjectiveRepository with marker in source object
        class DeterministicObjectiveRepository:
            def list_recent(self, status=None, limit=20):
                # Return ObjectiveNode with marker in title (born in source)
                return [
                    ObjectiveNode(
                        objective_id='test-obj-001',
                        title=f'{CM_MARKER} critical objective',
                        summary='Test objective with marker',
                        priority=85,  # HIGH priority to trigger high_priority scoring
                        status=ObjectiveStatus.ACTIVE,
                        evidence_refs=[f'{CM_MARKER}-ref'],
                        blocker='',
                    )
                ]

        # Create ControlMasterService with REAL current_work_queue() implementation
        # Only input sources are deterministic; current_work_queue() itself is NOT overridden
        class FakeControlMasterRepository:
            def load_latest_state(self):
                from iabv_v15.domain.models import ControlMasterState
                return ControlMasterState()

            def list_rules(self):
                return []

            def list_decisions(self):
                return []

        class FakePlatformPendingQueue:
            pass

        class FakePendingIssueRepository:
            pass

        class FakeSelfExaminationService:
            pass

        class FakeExperimentLabRepository:
            pass

        class FakeAccountResourceScanner:
            pass

        control_master_service = ControlMasterService(
            repository=FakeControlMasterRepository(),
            objective_repository=DeterministicObjectiveRepository(),  # Deterministic source
            pending_issue_repository=FakePendingIssueRepository(),
            self_examination_service=FakeSelfExaminationService(),
            experiment_lab_repository=FakeExperimentLabRepository(),
            account_resource_scanner=FakeAccountResourceScanner(),
            platform_pending_queue=FakePlatformPendingQueue(),
            workspace_root='/test/workspace',
        )

        # DO NOT override current_work_queue() - execute REAL implementation
        # NO: control_master_service.current_work_queue = ...
        # NO: patch.object(control_master_service, "current_work_queue", ...)

        # Execute REAL current_work_queue() and verify marker appears
        queue = control_master_service.current_work_queue(limit=5)

        # Verify: Marker appears in REAL current_work_queue() output
        assert len(queue) > 0, "current_work_queue() must produce items from deterministic source"
        item = queue[0]
        assert CM_MARKER in item['title'], f"Marker {CM_MARKER} must appear in item title from REAL current_work_queue()"
        assert item['source'] == 'objective_repository', "Item must be from _project_objective_queue_items() projector"
        assert item['status'] == 'active', "Status must match ObjectiveNode status"

        # Verify: REAL scoring logic produced priority_score and priority_label
        # Base score (20) + high_priority (30 for priority >= 80) = 50
        assert item['priority_score'] > 0, "priority_score must be produced by REAL scoring logic"
        assert item['priority_label'] in ('critical', 'high', 'medium', 'low'), \
            "priority_label must be produced by REAL _score_to_label() logic (lowercase)"
        assert 'score_breakdown' in item, "score_breakdown must be produced by REAL _make_item()"

        # Verify: marker born in source object
        assert CM_MARKER in item['id'] or CM_MARKER in item['title'], \
            "Marker must originate from source object, not be constructed downstream"

        # Create PortableContextService connected to REAL ControlMasterService
        # Use isolated storage to avoid cached portable_context/latest.json
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        try:
            isolated_storage = ArtifactStorage(temp_dir)
            portable_context_service = PortableContextService(
                workspace_root='/test/workspace',
                storage=isolated_storage,
            )
            # Wire REAL ControlMasterService (production wiring)
            portable_context_service.control_master_service = control_master_service

            # Create contract-valid stubs for TaskContextAssembler dependencies
            class StubEpisodeRepository:
                def list_recent(self, limit=10):
                    return []
                def get(self, episode_id):
                    return None

            class StubKnowledgeRepository:
                def search(self, query, limit=10):
                    return []
                def get(self, knowledge_id):
                    return None

            class StubRunRepository:
                def list_recent(self, limit=10):
                    return []
                def get(self, run_id):
                    return None

            class StubDossierRepository:
                def list_recent(self, limit=10):
                    return []
                def get(self, dossier_id):
                    return None

            class StubHiddenIncidentRepository:
                def list_recent(self, limit=10):
                    return []
                def get(self, incident_id):
                    return None

            class StubSitePolicyRegistry:
                class StubPolicy:
                    display_name = 'Test Policy'
                    domains = []
                    notes = ''
                def get_policy(self, site_id):
                    return self.StubPolicy()

            class StubCapabilityRepository:
                def list_recent(self, limit=10):
                    return []
                def find_by_site(self, site_id, limit=10):
                    return []

            class StubAdaptiveSessionRepository:
                def list_recent(self, limit=10):
                    return []

            # Create TaskContextAssembler with contract-valid stubs
            assembler = TaskContextAssembler(
                episode_repository=StubEpisodeRepository(),
                knowledge_repository=StubKnowledgeRepository(),
                run_repository=StubRunRepository(),
                dossier_repository=StubDossierRepository(),
                hidden_incident_repository=StubHiddenIncidentRepository(),
                site_policy_registry=StubSitePolicyRegistry(),
                capability_repository=StubCapabilityRepository(),
                adaptive_session_repository=StubAdaptiveSessionRepository(),
                portable_context_service=portable_context_service,
            )

            # Call REAL build_perception_snapshot() to get production DecisionContext
            from iabv_v15.domain.models import InferenceRequest

            request = InferenceRequest(
                user_goal='Test goal',
                site_hint=None,
                enable_planning=False,
                requires_visual_reasoning=False,
            )

            intent = TaskIntent(
                user_goal='Test goal',
                detected_role='knowledge',
                multi_step=False,
                enable_planning=False,
                requires_visual_reasoning=False,
            )

            # Execute REAL build_perception_snapshot()
            snapshot = assembler.build_perception_snapshot(
                request=request,
                intent=intent,
            )

            # Verify: Production DecisionContext contains portable_context_summary with marker
            decision_context = snapshot.decision_context
            assert decision_context is not None, "build_perception_snapshot() must produce DecisionContext"
            assert 'portable_context_summary' in decision_context.metadata, \
                "Production DecisionContext must contain portable_context_summary in metadata"
            portable_context_summary = decision_context.metadata['portable_context_summary']
            assert 'canonical_work_queue' in portable_context_summary, \
                "portable_context_summary must contain canonical_work_queue"
            assert len(portable_context_summary['canonical_work_queue']['items']) > 0, \
                "canonical_work_queue must contain items"
            assert any(
                'BIO-META-03X-CM-SOURCE-001' in item['title']
                for item in portable_context_summary['canonical_work_queue']['items']
            ), "Marker from source must appear in production DecisionContext.metadata"

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
                        decision_context=snapshot.decision_context,  # Use production DecisionContext from build_perception_snapshot()
                    )

            # Verify: Marker from source (via REAL current_work_queue()) appears in context_pack
            assert captured_context_pack is not None, \
                "plan_or_execute() must call execute_external_consultation with context_pack"
            assert CM_MARKER in captured_context_pack, \
                f"Marker {CM_MARKER} from source must appear in context_pack after traversing REAL chain"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
