"""Tests for CloudReasoningPlannerService — plan parsing and persistence."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from iabv_v15.services.adaptive.cloud_reasoning_planner import (
    CloudPlan,
    CloudReasoningPlannerService,
    PlanStep,
    TOOL_DESCRIPTORS,
)


class TestPlanStep:
    def test_defaults(self) -> None:
        step = PlanStep()
        assert step.order == 0
        assert step.status == 'pending'
        assert step.assigned_tool == ''
        assert step.requires_approval is False

    def test_custom_values(self) -> None:
        step = PlanStep(
            order=1,
            title='Analyze code',
            assigned_tool='codex',
            requires_approval=True,
            estimated_seconds=60,
        )
        assert step.order == 1
        assert step.assigned_tool == 'codex'
        assert step.requires_approval is True


class TestCloudPlan:
    def test_defaults(self) -> None:
        plan = CloudPlan()
        assert plan.user_goal == ''
        assert plan.steps == []
        assert plan.confidence == 0.0

    def test_with_steps(self) -> None:
        plan = CloudPlan(
            user_goal='fix bug',
            steps=[PlanStep(order=1, title='Step 1', assigned_tool='codex')],
            cloud_source='groq',
            confidence=0.85,
        )
        assert len(plan.steps) == 1
        assert plan.cloud_source == 'groq'
        assert plan.confidence == 0.85


class TestToolDescriptors:
    def test_all_have_required_fields(self) -> None:
        for td in TOOL_DESCRIPTORS:
            assert 'id' in td
            assert 'name' in td
            assert 'strengths' in td
            assert 'limitations' in td

    def test_known_tools_present(self) -> None:
        ids = {td['id'] for td in TOOL_DESCRIPTORS}
        assert 'codex' in ids
        assert 'chatgpt' in ids
        assert 'claude' in ids
        assert 'devin' in ids
        assert 'ollama_local' in ids


class TestParsePlan:
    service = CloudReasoningPlannerService()

    def test_valid_plan(self) -> None:
        raw = {
            'summary': 'Fix the login bug',
            'confidence': 0.9,
            '_cloud_source': 'groq',
            'steps': [
                {
                    'order': 1,
                    'title': 'Analyze error logs',
                    'description': 'Review stack trace',
                    'assigned_tool': 'codex',
                    'tool_rationale': 'Best for code analysis',
                    'requires_approval': False,
                    'estimated_seconds': 30,
                },
                {
                    'order': 2,
                    'title': 'Research solution',
                    'description': 'Find similar fixes',
                    'assigned_tool': 'chatgpt',
                    'tool_rationale': 'Good for research',
                    'requires_approval': False,
                    'estimated_seconds': 60,
                },
            ],
        }
        plan = self.service._parse_plan(raw, 'fix login')
        assert plan is not None
        assert plan.user_goal == 'fix login'
        assert len(plan.steps) == 2
        assert plan.steps[0].assigned_tool == 'codex'
        assert plan.steps[1].assigned_tool == 'chatgpt'
        assert plan.confidence == 0.9

    def test_empty_steps(self) -> None:
        raw = {'summary': 'Nothing', 'steps': []}
        plan = self.service._parse_plan(raw, 'test')
        assert plan is None

    def test_missing_steps_key(self) -> None:
        raw = {'summary': 'Nothing'}
        plan = self.service._parse_plan(raw, 'test')
        assert plan is None

    def test_invalid_tool_falls_back_to_ollama(self) -> None:
        raw = {
            'summary': 'Plan',
            'confidence': 0.7,
            'steps': [
                {
                    'order': 1,
                    'title': 'Do something',
                    'assigned_tool': 'nonexistent_tool',
                },
            ],
        }
        plan = self.service._parse_plan(raw, 'test')
        assert plan is not None
        assert plan.steps[0].assigned_tool == 'ollama_local'

    def test_confidence_clamped(self) -> None:
        raw = {
            'summary': 'Plan',
            'confidence': 5.0,
            'steps': [{'order': 1, 'title': 'Step', 'assigned_tool': 'codex'}],
        }
        plan = self.service._parse_plan(raw, 'test')
        assert plan is not None
        assert plan.confidence == 1.0

    def test_max_8_steps(self) -> None:
        raw = {
            'summary': 'Big plan',
            'steps': [
                {'order': i, 'title': f'Step {i}', 'assigned_tool': 'codex'}
                for i in range(1, 15)
            ],
        }
        plan = self.service._parse_plan(raw, 'test')
        assert plan is not None
        assert len(plan.steps) == 8


class TestPersistPlan:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        plan = CloudPlan(
            user_goal='test goal',
            summary='test summary',
            steps=[PlanStep(order=1, title='Step 1', assigned_tool='codex')],
            cloud_source='groq',
            confidence=0.8,
        )
        with patch.dict('os.environ', {'IABV_DATA_DIR': str(tmp_path)}):
            CloudReasoningPlannerService._persist_plan(plan)
        log_path = tmp_path / 'evolution' / 'cloud_plans' / 'plans.jsonl'
        assert log_path.exists()
        entry = json.loads(log_path.read_text().strip())
        assert entry['user_goal'] == 'test goal'
        assert entry['cloud_source'] == 'groq'
        assert entry['step_count'] == 1
        assert 'codex' in entry['tools_used']


class TestGeneratePlan:
    service = CloudReasoningPlannerService()

    def test_generate_plan_returns_none_without_keys(self) -> None:
        with patch.dict('os.environ', {'GEMINI_API_KEY': '', 'GROQ_API_KEY': ''}, clear=False):
            with patch.object(
                CloudReasoningPlannerService,
                '_query_cloud_for_plan',
                return_value=None,
            ):
                result = self.service.generate_plan('do something')
                assert result is None

    def test_generate_plan_with_mock_cloud(self) -> None:
        mock_response = {
            'summary': 'Fix the issue',
            'confidence': 0.85,
            '_cloud_source': 'groq',
            'steps': [
                {
                    'order': 1,
                    'title': 'Analyze',
                    'description': 'Look at the code',
                    'assigned_tool': 'codex',
                    'tool_rationale': 'Best for code',
                    'estimated_seconds': 30,
                },
            ],
        }
        with patch.object(
            CloudReasoningPlannerService,
            '_query_cloud_for_plan',
            return_value=mock_response,
        ):
            with patch.object(
                CloudReasoningPlannerService,
                '_persist_plan',
            ):
                result = self.service.generate_plan('fix the bug')
                assert result is not None
                assert result.summary == 'Fix the issue'
                assert len(result.steps) == 1
                assert result.steps[0].assigned_tool == 'codex'
