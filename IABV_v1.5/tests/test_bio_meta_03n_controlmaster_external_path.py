"""BIO-META-03R — ControlMaster state → live external-consultation context path.

This test suite verifies that ControlMaster priority/control state reaches
the live external-consultation path by calling PRODUCTION METHODS directly,
not by reproducing logic inline.

The causal chain to verify:
PortableContextPackage → TaskContextAssembler._portable_context_summary()
→ DecisionContext.metadata['portable_context_summary']
→ AutonomousEvolutionService.plan_or_execute(decision_context=...)
→ _build_context_pack(portable_context_summary=...)
→ context_pack
→ ToolTeachService.execute_external_consultation(...)

And for preview:
DecisionContext.metadata['portable_context_summary']
→ AutonomousEvolutionService.preview_plan(decision_context=...)
→ _build_context_pack(...)
→ context_pack
→ preview_external_consultation(...)
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    DecisionContext,
    IntentRouteDecision,
    PortableContextSection,
    PortableContextPackage,
    TaskContext,
    TaskIntent,
)


class TestPortableContextSummaryProduction:
    """UNIT-ON-PRODUCTION-CODE: Test that _portable_context_summary() PRODUCTION code extracts canonical_work_queue."""

    def test_production_extracts_canonical_work_queue_section(self):
        """Verify that PRODUCTION _portable_context_summary() extracts the section."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler

        # Setup: Create real PortableContextService with work queue section
        now = datetime.now(timezone.utc)
        
        work_queue_section = PortableContextSection(
            section_id='canonical_work_queue',
            title='Cola canónica de trabajo',
            summary='1 items prioritarios en cola canónica de trabajo.',
            items=[
                {
                    'id': 'critical-1',
                    'title': 'Critical security fix',
                    'status': 'pending',
                    'priority_score': 0.95,
                    'priority_label': 'CRITICAL',
                    'source': 'oses',
                    'next_action': 'immediate',
                    'evidence_refs': ['run-123'],
                }
            ],
            source_kind='control_master',
            source_refs=['ControlMasterService'],
            confidence=0.9,
            last_updated=now,
            unresolved_fields=[],
        )
        
        package = PortableContextPackage(
            package_id='test-package',
            package_version='1.0',
            created_at_utc=now,
            updated_at_utc=now,
            summary='Test package',
            assistant_brief='Test brief',
            package_path='/test/path.json',
            markdown_path='/test/path.md',
            sections=[work_queue_section],
            unresolved_fields=[],
            metadata={},
        )
        
        # Create PortableContextService mock that returns the real package
        portable_context_service = MagicMock()
        portable_context_service.current_package.return_value = package
        portable_context_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
        # Create TaskContextAssembler with all required mocks
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
        result = assembler._portable_context_summary(task_context=task_context)
        
        # Verify: PRODUCTION code extracted canonical_work_queue
        assert 'canonical_work_queue' in result, \
            "PRODUCTION _portable_context_summary() must extract canonical_work_queue"
        assert result['canonical_work_queue']['summary'] == '1 items prioritarios en cola canónica de trabajo.'
        assert len(result['canonical_work_queue']['items']) == 1
        assert result['canonical_work_queue']['items'][0]['priority_label'] == 'CRITICAL'
        assert result['canonical_work_queue']['confidence'] == 0.9


class TestPlanOrExecuteProductionIntegration:
    """PRODUCTIVE-INTEGRATION: Test that plan_or_execute() PRODUCTION method consumes decision_context metadata."""

    def test_plan_or_execute_passes_context_pack_with_critical_item(self):
        """TREATMENT: REAL plan_or_execute() with CRITICAL item in DecisionContext.metadata."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        # Build portable_context_summary from PRODUCTION TaskContextAssembler
        now = datetime.now(timezone.utc)
        
        work_queue_section = PortableContextSection(
            section_id='canonical_work_queue',
            title='Cola canónica de trabajo',
            summary='1 items prioritarios en cola canónica de trabajo.',
            items=[
                {
                    'id': 'critical-1',
                    'title': 'Critical security fix',
                    'status': 'pending',
                    'priority_score': 0.95,
                    'priority_label': 'CRITICAL',
                    'source': 'oses',
                    'next_action': 'immediate',
                    'evidence_refs': ['run-123'],
                }
            ],
            source_kind='control_master',
            source_refs=['ControlMasterService'],
            confidence=0.9,
            last_updated=now,
            unresolved_fields=[],
        )
        
        package = PortableContextPackage(
            package_id='test-package',
            package_version='1.0',
            created_at_utc=now,
            updated_at_utc=now,
            summary='Test package',
            assistant_brief='Test brief',
            package_path='/test/path.json',
            markdown_path='/test/path.md',
            sections=[work_queue_section],
            unresolved_fields=[],
            metadata={},
        )
        
        portable_context_service = MagicMock()
        portable_context_service.current_package.return_value = package
        portable_context_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
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
        
        # Get portable_context_summary from PRODUCTION code
        task_context = TaskContext(user_goal='Test goal')
        portable_context_summary = assembler._portable_context_summary(task_context=task_context)
        
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
        
        # Verify: context_pack passed to execute_external_consultation contains work queue
        assert captured_context_pack is not None, \
            "plan_or_execute() must call execute_external_consultation with context_pack"
        assert 'Cola de trabajo prioritaria' in captured_context_pack, \
            "context_pack must include work queue summary"
        assert 'Items criticos: 1' in captured_context_pack, \
            "context_pack must include CRITICAL items count"
        assert 'Critical security fix' in captured_context_pack, \
            "context_pack must include CRITICAL item title"
        assert 'prioridad: CRITICAL' in captured_context_pack, \
            "context_pack must include CRITICAL item priority"

    def test_plan_or_execute_without_critical_item(self):
        """CONTROL: REAL plan_or_execute() without CRITICAL item in DecisionContext.metadata."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        # Build portable_context_summary from PRODUCTION TaskContextAssembler (CONTROL)
        now = datetime.now(timezone.utc)
        
        work_queue_section = PortableContextSection(
            section_id='canonical_work_queue',
            title='Cola canónica de trabajo',
            summary='1 items prioritarios en cola canónica de trabajo.',
            items=[
                {
                    'id': 'task-1',
                    'title': 'Normal task',
                    'status': 'pending',
                    'priority_score': 0.3,
                    'priority_label': 'MEDIUM',
                    'source': 'user',
                    'next_action': 'review',
                    'evidence_refs': [],
                }
            ],
            source_kind='control_master',
            source_refs=['ControlMasterService'],
            confidence=0.9,
            last_updated=now,
            unresolved_fields=[],
        )
        
        package = PortableContextPackage(
            package_id='test-package',
            package_version='1.0',
            created_at_utc=now,
            updated_at_utc=now,
            summary='Test package',
            assistant_brief='Test brief',
            package_path='/test/path.json',
            markdown_path='/test/path.md',
            sections=[work_queue_section],
            unresolved_fields=[],
            metadata={},
        )
        
        portable_context_service = MagicMock()
        portable_context_service.current_package.return_value = package
        portable_context_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
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
        
        task_context = TaskContext(user_goal='Test goal')
        portable_context_summary = assembler._portable_context_summary(task_context=task_context)
        
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
        
        captured_context_pack = None
        def capture_context_pack(*args, **kwargs):
            nonlocal captured_context_pack
            captured_context_pack = kwargs.get('context_pack', '')
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
        
        # CONTROL: context_pack contains work queue but no CRITICAL items
        assert captured_context_pack is not None
        assert 'Cola de trabajo prioritaria' in captured_context_pack, \
            "CONTROL: context_pack should include work queue summary"
        assert 'Items criticos' not in captured_context_pack, \
            "CONTROL: context_pack should NOT mention critical items when none exist"


class TestPreviewPlanProductionIntegration:
    """PRODUCTIVE-INTEGRATION: Test that preview_plan() PRODUCTION method consumes decision_context metadata."""

    def test_preview_plan_passes_context_pack_with_critical_item(self):
        """TREATMENT: REAL preview_plan() with CRITICAL item in DecisionContext.metadata."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        # Build portable_context_summary from PRODUCTION TaskContextAssembler
        now = datetime.now(timezone.utc)
        
        work_queue_section = PortableContextSection(
            section_id='canonical_work_queue',
            title='Cola canónica de trabajo',
            summary='1 items prioritarios en cola canónica de trabajo.',
            items=[
                {
                    'id': 'critical-1',
                    'title': 'Critical security fix',
                    'status': 'pending',
                    'priority_score': 0.95,
                    'priority_label': 'CRITICAL',
                    'source': 'oses',
                    'next_action': 'immediate',
                    'evidence_refs': ['run-123'],
                }
            ],
            source_kind='control_master',
            source_refs=['ControlMasterService'],
            confidence=0.9,
            last_updated=now,
            unresolved_fields=[],
        )
        
        package = PortableContextPackage(
            package_id='test-package',
            package_version='1.0',
            created_at_utc=now,
            updated_at_utc=now,
            summary='Test package',
            assistant_brief='Test brief',
            package_path='/test/path.json',
            markdown_path='/test/path.md',
            sections=[work_queue_section],
            unresolved_fields=[],
            metadata={},
        )
        
        portable_context_service = MagicMock()
        portable_context_service.current_package.return_value = package
        portable_context_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
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
        
        task_context = TaskContext(user_goal='Test goal')
        portable_context_summary = assembler._portable_context_summary(task_context=task_context)
        
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
        
        captured_context_pack = None
        def capture_context_pack(*args, **kwargs):
            nonlocal captured_context_pack
            captured_context_pack = kwargs.get('context_pack', '')
            return MagicMock(context_pack_excerpt='')
        
        tool_teach_service.preview_external_consultation.side_effect = capture_context_pack
        
        with patch.object(service, '_assessment_from_decision_context') as mock_assessment:
            mock_assessment.return_value = {
                'action': 'consult_codex',
                'assistant_kind': 'codex',
                'should_consult': True,
                'reason': 'Test reason',
                'diagnostic_category': 'general',
            }
            
            result = service.preview_plan(
                adaptive_payload={'user_goal': 'Test goal'},
                user_goal='Test goal',
                source='test',
                decision_context=decision_context,
            )
        
        # Verify: context_pack passed to preview_external_consultation contains work queue
        assert captured_context_pack is not None, \
            "preview_plan() must call preview_external_consultation with context_pack"
        assert 'Cola de trabajo prioritaria' in captured_context_pack, \
            "context_pack must include work queue summary"
        assert 'Items criticos: 1' in captured_context_pack, \
            "context_pack must include CRITICAL items count"
        assert 'Critical security fix' in captured_context_pack, \
            "context_pack must include CRITICAL item title"
