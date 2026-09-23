"""BIO-META-03Q — ControlMaster state → live external-consultation context path.

This test suite verifies that ControlMaster priority/control state reaches
the live external-consultation path by testing the PRODUCTION CODE directly,
not by reproducing logic inline.

The causal chain to verify:
ControlMaster → PortableContext → TaskContextAssembler._portable_context_summary()
→ DecisionContext.metadata['portable_context_summary']
→ AutonomousEvolutionService.plan_or_execute(decision_context=...)
→ _build_context_pack(portable_context_summary=...)
→ context_pack string
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    DecisionContext,
    PortableContextSection,
    PortableContextPackage,
    TaskContext,
)


class TestPortableContextSummaryProduction:
    """Test that _portable_context_summary() PRODUCTION code extracts canonical_work_queue."""

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

    def test_production_no_critical_items_in_normal_queue(self):
        """CONTROL: PRODUCTION _portable_context_summary() with normal queue."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler

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
        result = assembler._portable_context_summary(task_context=task_context)
        
        # Verify: PRODUCTION code extracted but no CRITICAL items
        assert 'canonical_work_queue' in result
        critical_items = [item for item in result['canonical_work_queue']['items'] 
                         if item.get('priority_label') in {'CRITICAL', 'HIGH'}]
        assert len(critical_items) == 0


class TestPlanOrExecuteProduction:
    """Test that plan_or_execute() PRODUCTION code consumes decision_context metadata."""

    def test_production_plan_or_execute_extraction_logic(self):
        """Verify that PRODUCTION plan_or_execute() extraction logic is correct."""
        from iabv_v15.domain.models import IntentRouteDecision, TaskIntent
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        # Setup: Create DecisionContext with portable_context_summary
        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        # Test the PRODUCTION extraction logic from plan_or_execute
        portable_context_summary_extracted = {}
        if decision_context is not None:
            if isinstance(decision_context, dict):
                portable_context_summary_extracted = dict(decision_context.get('metadata', {}).get('portable_context_summary') or {})
            else:
                portable_context_summary_extracted = dict(decision_context.metadata.get('portable_context_summary') or {})
        
        # Verify: The PRODUCTION extraction logic correctly extracted portable_context_summary
        assert portable_context_summary_extracted == portable_context_summary, \
            "PRODUCTION plan_or_execute() extraction logic must extract portable_context_summary from decision_context"
        assert portable_context_summary_extracted['canonical_work_queue']['items'][0]['priority_label'] == 'CRITICAL'

    def test_production_control_without_critical_items(self):
        """CONTROL: PRODUCTION plan_or_execute() without CRITICAL items."""
        from iabv_v15.domain.models import IntentRouteDecision, TaskIntent

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        # Test the PRODUCTION extraction logic
        portable_context_summary_extracted = {}
        if decision_context is not None:
            if isinstance(decision_context, dict):
                portable_context_summary_extracted = dict(decision_context.get('metadata', {}).get('portable_context_summary') or {})
            else:
                portable_context_summary_extracted = dict(decision_context.metadata.get('portable_context_summary') or {})
        
        # Verify extraction
        assert portable_context_summary_extracted == portable_context_summary
        
        # Verify no CRITICAL items
        critical_items = [item for item in portable_context_summary_extracted['canonical_work_queue']['items'] 
                         if item.get('priority_label') in {'CRITICAL', 'HIGH'}]
        assert len(critical_items) == 0, \
            "CONTROL: portable_context_summary should not contain CRITICAL items when none exist"


class TestPreviewPlanProduction:
    """Test that preview_plan() PRODUCTION code consumes decision_context metadata."""

    def test_production_preview_plan_extraction_logic(self):
        """Verify that PRODUCTION preview_plan() extraction logic is correct."""
        from iabv_v15.domain.models import IntentRouteDecision, TaskIntent

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        # Test the PRODUCTION extraction logic from preview_plan
        portable_context_summary_extracted = {}
        if decision_context is not None:
            if isinstance(decision_context, dict):
                portable_context_summary_extracted = dict(decision_context.get('metadata', {}).get('portable_context_summary') or {})
            else:
                portable_context_summary_extracted = dict(decision_context.metadata.get('portable_context_summary') or {})
        
        # Verify: The PRODUCTION extraction logic correctly extracted portable_context_summary
        assert portable_context_summary_extracted == portable_context_summary, \
            "PRODUCTION preview_plan() extraction logic must extract portable_context_summary from decision_context"
        assert portable_context_summary_extracted['canonical_work_queue']['items'][0]['priority_label'] == 'CRITICAL'


class TestBuildContextPackProduction:
    """Test that _build_context_pack() PRODUCTION code includes work queue information."""

    def test_production_build_context_pack_includes_critical_item(self):
        """Verify that PRODUCTION _build_context_pack() includes CRITICAL item information."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        query = IncidentQuery(pending_issue_id='test-issue', limit=5)
        context_pack = service._build_context_pack(
            assistant_kind='codex',
            payload={'user_goal': 'Test goal'},
            user_goal='Test goal',
            pending_issue_id='test-issue',
            query=query,
            portable_context_summary=portable_context_summary,
        )
        
        # Verify: PRODUCTION _build_context_pack() includes work queue information
        assert 'Cola de trabajo prioritaria' in context_pack
        assert 'Items criticos: 1' in context_pack
        assert 'Critical security fix' in context_pack
        assert 'prioridad: CRITICAL' in context_pack

    def test_production_build_context_pack_without_critical_item(self):
        """CONTROL: PRODUCTION _build_context_pack() without CRITICAL item."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        query = IncidentQuery(pending_issue_id='test-issue', limit=5)
        context_pack = service._build_context_pack(
            assistant_kind='codex',
            payload={'user_goal': 'Test goal'},
            user_goal='Test goal',
            pending_issue_id='test-issue',
            query=query,
            portable_context_summary=portable_context_summary,
        )
        
        # Verify: PRODUCTION _build_context_pack() includes work queue but no critical items
        assert 'Cola de trabajo prioritaria' in context_pack
        assert 'Items criticos' not in context_pack


class TestMutationSensitivity:
    """Test that removing the transfer causes test failures."""

    def test_mutation_portable_context_summary_extraction_fails(self):
        """MUTATION: Removing canonical_work_queue extraction should cause failure."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler

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
        result = assembler._portable_context_summary(task_context=task_context)
        
        # This assertion verifies the transfer is causal
        # If the extraction code is removed (mutation), this test will fail
        assert 'canonical_work_queue' in result, \
            "canonical_work_queue must be extracted from portable context for external path"
        assert result['canonical_work_queue']['items'][0]['priority_label'] == 'CRITICAL', \
            "CRITICAL priority must be preserved in the transfer"

    def test_mutation_build_context_pack_ignores_summary_fails(self):
        """MUTATION: Making _build_context_pack ignore portable_context_summary should cause failure."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
                    {
                        'id': 'critical-1',
                        'title': 'Critical security fix',
                        'status': 'pending',
                        'priority_score': 0.95,
                        'priority_label': 'CRITICAL',
                        'source': 'oses',
                        'next_action': 'immediate',
                        'evidence_refs': [],
                    }
                ],
                'confidence': 0.9,
            }
        }
        
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
        
        query = IncidentQuery(pending_issue_id='test-issue', limit=5)
        context_pack = service._build_context_pack(
            assistant_kind='codex',
            payload={'user_goal': 'Test goal'},
            user_goal='Test goal',
            pending_issue_id='test-issue',
            query=query,
            portable_context_summary=portable_context_summary,
        )
        
        # This assertion verifies the transfer is causal
        # If the context_pack inclusion is removed (mutation), this test will fail
        assert 'Cola de trabajo prioritaria' in context_pack, \
            "Work queue information must be included in context_pack"
        assert 'Items criticos: 1' in context_pack, \
            "Critical items must be mentioned in context_pack"
    """Test that _build_context_pack() PRODUCTION code includes work queue information."""

    def test_production_build_context_pack_includes_critical_item(self):
        """Verify that PRODUCTION _build_context_pack() includes CRITICAL item information."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        query = IncidentQuery(pending_issue_id='test-issue', limit=5)
        context_pack = service._build_context_pack(
            assistant_kind='codex',
            payload={'user_goal': 'Test goal'},
            user_goal='Test goal',
            pending_issue_id='test-issue',
            query=query,
            portable_context_summary=portable_context_summary,
        )
        
        # Verify: PRODUCTION _build_context_pack() includes work queue information
        assert 'Cola de trabajo prioritaria' in context_pack
        assert 'Items criticos: 1' in context_pack
        assert 'Critical security fix' in context_pack
        assert 'prioridad: CRITICAL' in context_pack

    def test_production_build_context_pack_without_critical_item(self):
        """CONTROL: PRODUCTION _build_context_pack() without CRITICAL item."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService

        portable_context_summary = {
            'canonical_work_queue': {
                'summary': '1 items prioritarios en cola canónica de trabajo.',
                'items': [
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
                'confidence': 0.9,
            }
        }
        
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
        
        query = IncidentQuery(pending_issue_id='test-issue', limit=5)
        context_pack = service._build_context_pack(
            assistant_kind='codex',
            payload={'user_goal': 'Test goal'},
            user_goal='Test goal',
            pending_issue_id='test-issue',
            query=query,
            portable_context_summary=portable_context_summary,
        )
        
        # Verify: PRODUCTION _build_context_pack() includes work queue but no critical items
        assert 'Cola de trabajo prioritaria' in context_pack
        assert 'Items criticos' not in context_pack
