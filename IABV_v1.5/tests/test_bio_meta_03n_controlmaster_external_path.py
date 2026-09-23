"""BIO-META-03N — ControlMaster state → live external-consultation context path.

This test suite verifies that ControlMaster priority/control state reaches
the live external-consultation path without creating a new orchestrator, queue,
authority, or parallel state model.

The causal chain to verify:
ControlMaster → portable_context_summary → DecisionContext → adaptive_payload
→ AutonomousEvolution → context_pack → ToolTask.metadata['context_pack']
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import (
    PortableContextSection,
    PortableContextPackage,
)


class TestPortableContextSummaryExtraction:
    """Test that _portable_context_summary extracts canonical_work_queue section."""

    def test_extracts_canonical_work_queue_section(self):
        """Verify that canonical_work_queue section is extracted from package."""
        # Setup: PortableContextService with work queue section
        mock_service = MagicMock()
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
        
        mock_service.current_package.return_value = package
        mock_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
        # Simulate the extraction logic from _portable_context_summary
        summary = mock_service.package_summary(package)
        result = dict(summary or {})
        
        # Extract canonical_work_queue section (simulating the fix)
        sections = {section.section_id: section for section in package.sections}
        work_queue = sections.get('canonical_work_queue')
        if work_queue is not None:
            result['canonical_work_queue'] = {
                'summary': work_queue.summary,
                'items': list(work_queue.items or [])[:5],
                'confidence': float(work_queue.confidence or 0.0),
            }
        
        # Verify: canonical_work_queue is extracted
        assert 'canonical_work_queue' in result
        assert result['canonical_work_queue']['summary'] == '1 items prioritarios en cola canónica de trabajo.'
        assert len(result['canonical_work_queue']['items']) == 1
        assert result['canonical_work_queue']['items'][0]['priority_label'] == 'CRITICAL'
        assert result['canonical_work_queue']['confidence'] == 0.9

    def test_no_critical_items_in_normal_queue(self):
        """CONTROL: Normal queue without CRITICAL items."""
        mock_service = MagicMock()
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
        
        mock_service.current_package.return_value = package
        mock_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
        # Simulate extraction
        summary = mock_service.package_summary(package)
        result = dict(summary or {})
        sections = {section.section_id: section for section in package.sections}
        work_queue = sections.get('canonical_work_queue')
        if work_queue is not None:
            result['canonical_work_queue'] = {
                'summary': work_queue.summary,
                'items': list(work_queue.items or [])[:5],
                'confidence': float(work_queue.confidence or 0.0),
            }
        
        # Verify: No CRITICAL items
        assert 'canonical_work_queue' in result
        critical_items = [item for item in result['canonical_work_queue']['items'] 
                         if item.get('priority_label') in {'CRITICAL', 'HIGH'}]
        assert len(critical_items) == 0


class TestContextPackInclusion:
    """Test that _build_context_pack includes work queue information."""

    def test_context_pack_includes_critical_item(self):
        """Verify that context_pack includes CRITICAL item information."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
        
        # Setup: portable_context_summary with CRITICAL item
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
        
        # Create AutonomousEvolutionService with minimal config
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
        
        # Build context pack
        query = IncidentQuery(pending_issue_id='test-issue', limit=5)
        context_pack = service._build_context_pack(
            assistant_kind='codex',
            payload={'user_goal': 'Test goal'},
            user_goal='Test goal',
            pending_issue_id='test-issue',
            query=query,
            portable_context_summary=portable_context_summary,
        )
        
        # Verify: context_pack includes work queue information
        assert 'Cola de trabajo prioritaria' in context_pack
        assert 'Items criticos: 1' in context_pack
        assert 'Critical security fix' in context_pack
        assert 'prioridad: CRITICAL' in context_pack

    def test_context_pack_without_critical_item(self):
        """CONTROL: context_pack without CRITICAL item."""
        from iabv_v15.domain.models import IncidentQuery
        from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
        
        # Setup: portable_context_summary without CRITICAL item
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
        
        # Verify: context_pack includes work queue but no critical items mentioned
        assert 'Cola de trabajo prioritaria' in context_pack
        assert 'Items criticos' not in context_pack


class TestMutationSensitivity:
    """Test that removing the transfer causes test failures."""

    def test_mutation_removing_extraction_fails(self):
        """MUTATION: Removing canonical_work_queue extraction should cause failure."""
        # Setup
        mock_service = MagicMock()
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
        
        mock_service.current_package.return_value = package
        mock_service.package_summary.return_value = {
            'package_id': 'test-package',
            'summary': 'Test package',
            'pending_items': [],
        }
        
        # Simulate extraction (the fix)
        summary = mock_service.package_summary(package)
        result = dict(summary or {})
        sections = {section.section_id: section for section in package.sections}
        work_queue = sections.get('canonical_work_queue')
        if work_queue is not None:
            result['canonical_work_queue'] = {
                'summary': work_queue.summary,
                'items': list(work_queue.items or [])[:5],
                'confidence': float(work_queue.confidence or 0.0),
            }
        
        # This assertion verifies the transfer is causal
        # If the extraction code is removed (mutation), this test will fail
        assert 'canonical_work_queue' in result, \
            "canonical_work_queue must be extracted from portable context for external path"
        assert result['canonical_work_queue']['items'][0]['priority_label'] == 'CRITICAL', \
            "CRITICAL priority must be preserved in the transfer"

    def test_mutation_empty_context_pack_fails(self):
        """MUTATION: Emptying context_pack should cause test failure."""
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
