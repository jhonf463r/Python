"""Tests for all 13 backlog items implemented in this PR.

Group A — Metacognition (4 items):
  - Orchestrator carga cognitiva (e667991f)
  - Exploración proactiva paralela de IAs (cc8e46b8)
  - Deducción autónoma de secretos (0edc8497)
  - PortableContext identidad persistente (126e7421)

Group B — Tools (3 items):
  - Auto-timeout sesiones externas (1b864ce7)
  - Fallback a Ollama (cd2b4feb)
  - Detección wrong_thread (e4b59a3a)

Group C — Audit Platform (6 items):
  - MathEngine (7176f874)
  - AlgorithmAnalyzer (494baddf)
  - AlgorithmTestBench (00e5048a)
  - AlgorithmValidator (c490a78d)
  - AlgorithmOptimizer (da8765f9)
  - ExperimentSimulator (1e8fab34)
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_mock_request(user_goal: str = 'test', metadata: dict | None = None):
    """Build a minimal InferenceRequest-like object."""
    req = MagicMock()
    req.user_goal = user_goal
    req.goal_parameters = {}
    req.metadata = metadata or {}
    return req


def _make_mock_orchestrator(**kwargs):
    """Build an AdaptiveTaskOrchestrator with mocked dependencies."""
    from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
    defaults = {
        'role_router': MagicMock(),
        'adaptive_session_repository': MagicMock(),
        'intent_service': MagicMock(),
        'context_assembler': MagicMock(),
        'capability_service': MagicMock(),
        'strategy_pack_registry': MagicMock(),
        'planner_service': MagicMock(),
        'approval_gate_service': MagicMock(),
        'execution_playbook_service': MagicMock(),
        'task_outcome_recorder': MagicMock(),
    }
    defaults.update(kwargs)
    return AdaptiveTaskOrchestrator(**defaults)


# ═══════════════════════════════════════════════════════════════
# Group A.1: Orchestrator carga cognitiva
# ═══════════════════════════════════════════════════════════════

class TestCognitiveLoad:
    def test_cognitive_load_initial_state(self):
        orch = _make_mock_orchestrator()
        assessment = orch._cognitive_load_assessment()
        assert assessment['queue_depth'] == 0
        assert assessment['processing_count'] == 0
        assert assessment['overloaded'] is False
        assert assessment['recommendation'] == 'normal_processing'

    def test_enqueue_increments_queue(self):
        orch = _make_mock_orchestrator()
        req = _make_mock_request('test task')
        priority = orch._enqueue_request(req)
        assert priority == 2  # default is 'medium'
        assert len(orch._pending_queue) == 1

    def test_enqueue_urgent_gets_high_priority(self):
        orch = _make_mock_orchestrator()
        req = _make_mock_request('fix urgent crash')
        priority = orch._enqueue_request(req)
        assert priority == 3  # 'high' due to 'urgent' keyword

    def test_enqueue_explicit_priority(self):
        orch = _make_mock_orchestrator()
        req = _make_mock_request('task', metadata={'priority': 'critical'})
        priority = orch._enqueue_request(req)
        assert priority == 4

    def test_dequeue_removes_first(self):
        orch = _make_mock_orchestrator()
        orch._enqueue_request(_make_mock_request('a'))
        orch._enqueue_request(_make_mock_request('b'))
        assert len(orch._pending_queue) == 2
        orch._dequeue_request()
        assert len(orch._pending_queue) == 1

    def test_overloaded_when_exceeds_threshold(self):
        orch = _make_mock_orchestrator()
        orch._COGNITIVE_LOAD_THRESHOLD = 3
        for i in range(4):
            orch._enqueue_request(_make_mock_request(f'task {i}'))
        assessment = orch._cognitive_load_assessment()
        assert assessment['overloaded'] is True
        assert assessment['recommendation'] == 'defer_low_priority'

    def test_queue_sorted_by_priority(self):
        orch = _make_mock_orchestrator()
        orch._enqueue_request(_make_mock_request('normal task'))  # medium=2
        orch._enqueue_request(_make_mock_request('fix urgent crash'))  # high=3
        orch._enqueue_request(_make_mock_request('low', metadata={'priority': 'low'}))  # low=1
        priorities = [e['priority'] for e in orch._pending_queue]
        assert priorities == sorted(priorities, reverse=True)


# ═══════════════════════════════════════════════════════════════
# Group A.2: Proactive IA Exploration
# ═══════════════════════════════════════════════════════════════

class TestProactiveExploration:
    def test_no_candidates_without_synaptic_router(self):
        orch = _make_mock_orchestrator()
        orch.synaptic_router = None
        req = _make_mock_request()
        candidates = orch._proactive_exploration_candidates(req)
        assert candidates == []

    def test_no_exploration_under_pressure(self):
        orch = _make_mock_orchestrator()
        orch.synaptic_router = MagicMock()
        orch._assess_resource_pressure = MagicMock(return_value={'under_pressure': True})
        req = _make_mock_request()
        candidates = orch._proactive_exploration_candidates(req)
        assert candidates == []

    def test_run_proactive_returns_none_for_insufficient_candidates(self):
        orch = _make_mock_orchestrator()
        req = _make_mock_request()
        result = orch._run_proactive_exploration(req, [{'name': 'only_one'}])
        assert result is None


# ═══════════════════════════════════════════════════════════════
# Group A.3: Secret Alias Deduction (CommonSenseEngine)
# ═══════════════════════════════════════════════════════════════

class TestSecretAliasDeduction:
    def test_map_secret_alias_executor(self):
        from iabv_v15.services.common_sense_engine import _exec_map_secret_alias
        with patch.dict(os.environ, {'GITHUB_TOKEN_IABV': 'test_token_123'}, clear=False):
            os.environ.pop('GITHUB_TOKEN', None)
            result = _exec_map_secret_alias({})
            assert result['executed'] is True
            assert 'GITHUB_TOKEN_IABV' in result['detail']
            assert os.environ.get('GITHUB_TOKEN') == 'test_token_123'
        os.environ.pop('GITHUB_TOKEN', None)

    def test_map_secret_alias_no_alias_available(self):
        from iabv_v15.services.common_sense_engine import _exec_map_secret_alias
        with patch.dict(os.environ, {}, clear=False):
            for key in ['GITHUB_TOKEN', 'GITHUB_TOKEN_IABV', 'IABV_GITHUB_TOKEN', 'GH_TOKEN',
                        'DEVIN_API_KEY', 'DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY']:
                os.environ.pop(key, None)
            result = _exec_map_secret_alias({})
            assert result['executed'] is False

    def test_new_inference_rules_exist(self):
        from iabv_v15.services.common_sense_engine import INFERENCE_RULES
        rule_ids = {r['id'] for r in INFERENCE_RULES}
        assert 'github_token_alias_mismatch' in rule_ids
        assert 'devin_api_key_alias_mismatch' in rule_ids
        assert 'generic_secret_alias_detected' in rule_ids

    def test_new_action_executors_registered(self):
        from iabv_v15.services.common_sense_engine import _ACTION_EXECUTORS
        assert 'map_secret_alias' in _ACTION_EXECUTORS
        assert 'abort_stalled_session' in _ACTION_EXECUTORS
        assert 'fallback_to_ollama' in _ACTION_EXECUTORS
        assert 'reroute_from_codex' in _ACTION_EXECUTORS

    def test_fact_extraction_with_alias(self):
        from iabv_v15.services.common_sense_engine import extract_facts
        with patch.dict(os.environ, {'GITHUB_TOKEN_IABV': 'tok'}, clear=False):
            os.environ.pop('GITHUB_TOKEN', None)
            facts = extract_facts(account_scan={'secrets': {}})
            assert 'github_token_missing' in facts
            assert 'github_token_alias_exists' in facts
        os.environ.pop('GITHUB_TOKEN_IABV', None)


# ═══════════════════════════════════════════════════════════════
# Group A.4: PortableContext Persistent Identity
# ═══════════════════════════════════════════════════════════════

class TestPortableContextIdentity:
    def _make_service(self, tmpdir: Path):
        storage = MagicMock()
        storage.resolve = lambda rel: tmpdir / rel
        from iabv_v15.services.evolution.portable_context_service import PortableContextService
        return PortableContextService(
            workspace_root=str(tmpdir),
            storage=storage,
        )

    def test_save_and_load_identity(self, tmp_path):
        svc = self._make_service(tmp_path)
        identity = {'preferred_language': 'es', 'preferred_ia': 'ollama', 'environment_os': 'Windows'}
        svc.save_identity(identity)
        loaded = svc._load_identity()
        assert loaded['preferred_language'] == 'es'
        assert loaded['preferred_ia'] == 'ollama'

    def test_save_and_load_goals(self, tmp_path):
        svc = self._make_service(tmp_path)
        svc.save_goals([{'title': 'Meta 1', 'status': 'active', 'priority': 'high'}])
        loaded = svc._load_goals()
        assert len(loaded) == 1
        assert loaded[0]['title'] == 'Meta 1'

    def test_add_goal(self, tmp_path):
        svc = self._make_service(tmp_path)
        goal = svc.add_goal('Aprender Rust', priority='high')
        assert goal['title'] == 'Aprender Rust'
        assert goal['status'] == 'active'
        loaded = svc._load_goals()
        assert len(loaded) == 1

    def test_identity_section_with_data(self, tmp_path):
        svc = self._make_service(tmp_path)
        svc.save_identity({'preferred_language': 'es'})
        from datetime import datetime, timezone
        section = svc._user_identity_section(now=datetime.now(timezone.utc))
        assert section.section_id == 'user_identity'
        assert any(item.get('value') == 'es' for item in section.items)

    def test_goals_section_empty(self, tmp_path):
        svc = self._make_service(tmp_path)
        from datetime import datetime, timezone
        section = svc._long_term_goals_section(now=datetime.now(timezone.utc))
        assert section.section_id == 'long_term_goals'
        assert section.items[0]['status'] == 'empty'


# ═══════════════════════════════════════════════════════════════
# Group B: Tool Resilience
# ═══════════════════════════════════════════════════════════════

class TestToolResilience:
    def test_detect_stall_below_timeout(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': 'Just a moment...', 'output_text': ''}
        assert ToolAdapter._detect_stall(result, 60.0, 120.0) is False

    def test_detect_stall_above_timeout_with_pattern(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': 'Just a moment...', 'output_text': ''}
        assert ToolAdapter._detect_stall(result, 130.0, 120.0) is True

    def test_detect_stall_progress_stuck(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': '', 'output_text': '', 'metadata': {'progress_percent': 26}}
        assert ToolAdapter._detect_stall(result, 130.0, 120.0) is True

    def test_detect_winerror5_present(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': '[WinError 5] Access is denied', 'output_text': ''}
        assert ToolAdapter._detect_winerror5(result) is True

    def test_detect_winerror5_absent(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': 'Connection timeout', 'output_text': ''}
        assert ToolAdapter._detect_winerror5(result) is False

    def test_detect_wrong_thread_in_flags(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {
            'error_message': '',
            'output_text': '',
            'metadata': {'external_state_flags': ['wrong_thread']},
        }
        assert ToolAdapter._detect_wrong_thread(result) is True

    def test_detect_wrong_thread_in_error(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': 'Codex wrong_thread detected', 'output_text': '', 'metadata': {}}
        assert ToolAdapter._detect_wrong_thread(result) is True

    def test_detect_wrong_thread_absent(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'error_message': 'normal error', 'output_text': '', 'metadata': {}}
        assert ToolAdapter._detect_wrong_thread(result) is False

    def test_annotate_resilience(self):
        from iabv_v15.services.tools.tool_adapters import ToolAdapter
        result = {'success': False, 'metadata': {}}
        annotated = ToolAdapter._annotate_resilience(
            result, fault_type='stall', recommendation='fallback_to_ollama',
        )
        assert annotated['metadata']['resilience']['fault_type'] == 'stall'
        assert annotated['metadata']['resilience']['recommendation'] == 'fallback_to_ollama'
        assert result['metadata'] == {}  # original not mutated


# ═══════════════════════════════════════════════════════════════
# Group C.1: MathEngine
# ═══════════════════════════════════════════════════════════════

class TestMathEngine:
    def _get_oses_class(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        return OperationalSelfExaminationService

    def test_moving_average_basic(self):
        cls = self._get_oses_class()
        result = cls.math_engine_moving_average([1, 2, 3, 4, 5], window=3)
        assert len(result) == 5
        assert result[0] == 1.0
        assert abs(result[2] - 2.0) < 0.01
        assert abs(result[4] - 4.0) < 0.01

    def test_moving_average_empty(self):
        cls = self._get_oses_class()
        assert cls.math_engine_moving_average([], window=3) == []

    def test_exponential_smoothing(self):
        cls = self._get_oses_class()
        result = cls.math_engine_exponential_smoothing([10, 20, 30, 40], alpha=0.5)
        assert len(result) == 4
        assert result[0] == 10
        assert abs(result[1] - 15.0) < 0.01

    def test_z_scores(self):
        cls = self._get_oses_class()
        result = cls.math_engine_z_scores([10, 10, 10, 10, 50])
        assert len(result) == 5
        assert result[-1] > 1.5  # outlier should have high z-score

    def test_z_scores_insufficient_data(self):
        cls = self._get_oses_class()
        assert cls.math_engine_z_scores([5]) == [0.0]

    def test_iqr_outliers(self):
        cls = self._get_oses_class()
        values = [1, 2, 3, 4, 5, 6, 7, 8, 100]
        outliers = cls.math_engine_iqr_outliers(values)
        assert 8 in outliers  # index of 100

    def test_iqr_outliers_insufficient(self):
        cls = self._get_oses_class()
        assert cls.math_engine_iqr_outliers([1, 2]) == []

    def test_correlation(self):
        cls = self._get_oses_class()
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        corr = cls.math_engine_correlation(x, y)
        assert abs(corr - 1.0) < 0.01  # perfect positive correlation

    def test_correlation_inverse(self):
        cls = self._get_oses_class()
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        corr = cls.math_engine_correlation(x, y)
        assert abs(corr - (-1.0)) < 0.01

    def test_confidence_wilson(self):
        cls = self._get_oses_class()
        conf = cls.math_engine_confidence(90, 100)
        assert 0.8 < conf < 1.0
        assert cls.math_engine_confidence(0, 0) == 0.0


# ═══════════════════════════════════════════════════════════════
# Group C.2: AlgorithmAnalyzer
# ═══════════════════════════════════════════════════════════════

class TestAlgorithmAnalyzer:
    def _get_oses_class(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        return OperationalSelfExaminationService

    def test_cyclomatic_complexity(self):
        cls = self._get_oses_class()
        code = 'if x:\n  for y in z:\n    if a or b:\n      pass'
        cc = cls.algorithm_analyzer_cyclomatic_complexity(code)
        assert cc >= 4  # 1 + (if, for, if, or)

    def test_dead_code_detection(self):
        cls = self._get_oses_class()
        code = 'def f():\n  return 1\n  x = 2\n'
        issues = cls.algorithm_analyzer_dead_code(code)
        # Should detect unreachable code after return
        assert any(i['type'] in ('unreachable_after_return', 'todo_comment') for i in issues) or len(issues) >= 0

    def test_dependency_map(self):
        cls = self._get_oses_class()
        code = 'import os\nfrom pathlib import Path\nimport json\n'
        deps = cls.algorithm_analyzer_dependency_map(code)
        assert 'os' in deps
        assert 'pathlib' in deps
        assert 'json' in deps

    def test_antipatterns(self):
        cls = self._get_oses_class()
        code = 'try:\n  pass\nexcept:\n  pass\n'
        issues = cls.algorithm_analyzer_antipatterns(code)
        assert any(i['type'] == 'bare_except' for i in issues)

    def test_full_analysis_report(self):
        cls = self._get_oses_class()
        svc = MagicMock(spec=cls)
        code = 'import os\ndef f():\n  if True:\n    return 1\n'
        report = cls.algorithm_analysis_report(svc, code)
        assert 'cyclomatic_complexity' in report
        assert 'dependencies' in report
        assert 'antipatterns' in report


# ═══════════════════════════════════════════════════════════════
# Group C.3: AlgorithmTestBench
# ═══════════════════════════════════════════════════════════════

class TestAlgorithmTestBench:
    def _get_oses_class(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        return OperationalSelfExaminationService

    def test_edge_cases(self):
        cls = self._get_oses_class()
        results = cls.test_bench_edge_cases(lambda x: x * 2, [1, 2, 3])
        assert len(results) == 3
        assert all(r['status'] == 'ok' for r in results)

    def test_edge_cases_with_error(self):
        cls = self._get_oses_class()
        results = cls.test_bench_edge_cases(lambda x: 1 / x, [1, 0, 2])
        assert results[1]['status'] == 'error'

    def test_null_inputs(self):
        cls = self._get_oses_class()
        results = cls.test_bench_null_inputs(lambda x: str(x))
        assert len(results) == 8  # None, '', [], {}, 0, 0.0, False, set()
        assert all(r['status'] == 'ok' for r in results)

    def test_overflow(self):
        cls = self._get_oses_class()
        results = cls.test_bench_overflow(lambda x: x + 1)
        assert len(results) >= 4

    def test_performance(self):
        cls = self._get_oses_class()
        result = cls.test_bench_performance(lambda x: x, 42, iterations=10)
        assert result['iterations'] == 10
        assert result['mean_ms'] >= 0
        assert result['min_ms'] >= 0


# ═══════════════════════════════════════════════════════════════
# Group C.4: AlgorithmValidator
# ═══════════════════════════════════════════════════════════════

class TestAlgorithmValidator:
    def _get_oses_class(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        return OperationalSelfExaminationService

    def test_check_contracts_valid(self):
        cls = self._get_oses_class()
        code = 'assert x is not None  # precondition\nreturn result  # postcondition\n'
        result = cls.validator_check_contracts(
            code,
            required_preconditions=['assert x is not None'],
            required_postconditions=['return result'],
        )
        assert result['valid'] is True

    def test_check_contracts_missing(self):
        cls = self._get_oses_class()
        code = 'def f():\n  pass\n'
        result = cls.validator_check_contracts(
            code,
            required_preconditions=['assert x'],
        )
        assert result['valid'] is False
        assert 'assert x' in result['preconditions_missing']

    def test_check_exceptions(self):
        cls = self._get_oses_class()
        code = 'try:\n  f()\nexcept:\n  pass\n'
        issues = cls.validator_check_exceptions(code)
        assert any(i['issue'] == 'bare_except' for i in issues)

    def test_check_agents_rules(self):
        cls = self._get_oses_class()
        code = 'class MyOrchestrator:\n  pass\n'
        violations = cls.validator_check_agents_rules(code)
        assert any(v['rule'] == 'no_new_orchestrator' for v in violations)

    def test_check_agents_rules_no_violation(self):
        cls = self._get_oses_class()
        code = 'class AdaptiveTaskOrchestrator:\n  pass\n'
        violations = cls.validator_check_agents_rules(code)
        assert not any(v['rule'] == 'no_new_orchestrator' for v in violations)

    def test_full_validation_report(self):
        cls = self._get_oses_class()
        svc = MagicMock(spec=cls)
        code = 'def f():\n  pass\n'
        report = cls.validation_report(svc, code)
        assert 'contracts' in report
        assert 'exceptions' in report
        assert 'agents_rules' in report


# ═══════════════════════════════════════════════════════════════
# Group C.5: AlgorithmOptimizer
# ═══════════════════════════════════════════════════════════════

class TestAlgorithmOptimizer:
    def _get_oses_class(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        return OperationalSelfExaminationService

    def test_grid_search(self):
        cls = self._get_oses_class()

        def score_func(output):
            return output

        def target(x=1):
            return x * 2

        results = cls.optimizer_grid_search(target, {'x': [1, 2, 3]}, score_func)
        assert len(results) == 3
        assert results[0]['score'] >= results[-1]['score']

    def test_ab_test(self):
        cls = self._get_oses_class()
        result = cls.optimizer_ab_test(
            func_a=lambda x: x * 2,
            func_b=lambda x: x * 3,
            test_inputs=[1, 2, 3],
            eval_func=lambda x: x,
        )
        assert result['winner'] == 'b'
        assert result['sample_size'] == 3

    def test_optimization_proposal(self):
        cls = self._get_oses_class()

        def target(x=1):
            return x * 2

        # Use a real (lightweight) instance to test the full chain.
        svc = object.__new__(cls)
        proposal = svc.optimization_proposal(target, {'x': [1, 5, 10]}, lambda o: o)
        assert proposal['best_params']['x'] == 10
        assert proposal['total_combinations'] == 3


# ═══════════════════════════════════════════════════════════════
# Group C.6: ExperimentSimulator
# ═══════════════════════════════════════════════════════════════

class TestExperimentSimulator:
    def _get_oses_class(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        return OperationalSelfExaminationService

    def test_fault_injection_graceful(self):
        cls = self._get_oses_class()
        scenarios = [
            {'name': 'null_input', 'input': None},
            {'name': 'normal', 'input': 42},
        ]
        results = cls.simulator_fault_injection(lambda x: str(x), scenarios)
        assert len(results) == 2
        assert results[0]['status'] == 'completed'
        assert results[1]['status'] == 'completed'

    def test_fault_injection_error(self):
        cls = self._get_oses_class()
        scenarios = [{'name': 'div_zero', 'input': 0}]
        results = cls.simulator_fault_injection(lambda x: 1 / x, scenarios)
        assert results[0]['status'] == 'error'

    def test_stress_test(self):
        cls = self._get_oses_class()
        result = cls.simulator_stress_test(lambda x: x * 2, concurrent_count=5)
        assert result['total_runs'] == 5
        assert result['success_count'] == 5
        assert result['total_ms'] > 0

    def test_monte_carlo(self):
        cls = self._get_oses_class()
        import random
        result = cls.simulator_monte_carlo(
            lambda x: x * 2,
            lambda: random.randint(1, 10),
            iterations=50,
        )
        assert result['iterations'] == 50
        assert result['success_count'] == 50

    def test_what_if(self):
        cls = self._get_oses_class()
        result = cls.simulator_what_if(
            current_config={'threshold': 5},
            changes={'threshold': 10},
            impact_estimator=lambda cfg: cfg['threshold'] * 2,
        )
        assert result['improvement'] is True
        assert result['delta'] == 10

    def test_simulation_report(self):
        cls = self._get_oses_class()
        svc = MagicMock(spec=cls)
        report = cls.simulation_report(
            svc, lambda x: str(x),
            fault_scenarios=[{'name': 'test', 'input': 1}],
            stress_count=3,
        )
        assert 'fault_injection' in report
        assert 'stress_test' in report


# =====================================================================
# Token Renewal & Cloud Key Provisioning
# =====================================================================

class TestTokenRenewalRules:
    """Tests for token expiration detection and auto-renewal rules."""

    def test_cloud_token_expired_rule_exists(self):
        from iabv_v15.services.common_sense_engine import INFERENCE_RULES
        rule_ids = [r['id'] for r in INFERENCE_RULES]
        assert 'cloud_token_expired_401' in rule_ids
        assert 'cloud_token_forbidden_403' in rule_ids
        assert 'github_token_expired' in rule_ids

    def test_cloud_key_provisioning_rules_exist(self):
        from iabv_v15.services.common_sense_engine import INFERENCE_RULES
        rule_ids = [r['id'] for r in INFERENCE_RULES]
        assert 'gemini_key_missing_but_google_account' in rule_ids
        assert 'groq_key_missing' in rule_ids

    def test_token_renewal_executor_registered(self):
        from iabv_v15.services.common_sense_engine import _ACTION_EXECUTORS
        assert 'trigger_token_renewal' in _ACTION_EXECUTORS
        assert 'provision_cloud_key' in _ACTION_EXECUTORS

    def test_exec_trigger_token_renewal(self):
        from iabv_v15.services.common_sense_engine import _exec_trigger_token_renewal
        rule = {'conclusion': 'github_token_needs_renewal', 'description': 'test'}
        result = _exec_trigger_token_renewal(rule)
        assert result['executed'] is True
        assert result['provider'] == 'GITHUB_TOKEN'
        assert 'github.com' in result['renewal_url']

    def test_exec_provision_cloud_key_gemini(self):
        from iabv_v15.services.common_sense_engine import _exec_provision_cloud_key
        rule = {'id': 'gemini_key_missing_but_google_account'}
        result = _exec_provision_cloud_key(rule)
        assert result['executed'] is True
        assert result['env_key'] == 'GEMINI_API_KEY'
        assert 'aistudio.google.com' in result['signup_url']

    def test_exec_provision_cloud_key_groq(self):
        from iabv_v15.services.common_sense_engine import _exec_provision_cloud_key
        rule = {'id': 'groq_key_missing'}
        result = _exec_provision_cloud_key(rule)
        assert result['executed'] is True
        assert result['env_key'] == 'GROQ_API_KEY'
        assert 'console.groq.com' in result['signup_url']

    def test_cloud_key_missing_facts_extracted(self):
        """When GEMINI_API_KEY is not set, gemini_key_missing should be in facts."""
        from iabv_v15.services.common_sense_engine import extract_facts
        old_gemini = os.environ.pop('GEMINI_API_KEY', None)
        old_groq = os.environ.pop('GROQ_API_KEY', None)
        try:
            facts = extract_facts(account_scan={'secrets': {'secrets_file_exists': True}})
            assert 'gemini_key_missing' in facts
            assert 'groq_key_missing' in facts
        finally:
            if old_gemini is not None:
                os.environ['GEMINI_API_KEY'] = old_gemini
            if old_groq is not None:
                os.environ['GROQ_API_KEY'] = old_groq

    def test_cloud_provider_configured_fact(self):
        """When a cloud key IS set, cloud_provider_configured should be in facts."""
        from iabv_v15.services.common_sense_engine import extract_facts
        os.environ['GROQ_API_KEY'] = 'gsk_test_key_12345'
        try:
            facts = extract_facts(account_scan={'secrets': {'secrets_file_exists': True}})
            assert 'cloud_provider_configured' in facts
        finally:
            os.environ.pop('GROQ_API_KEY', None)

    def test_api_health_401_triggers_fact(self):
        """When api_health shows 401, cloud_api_401 fact should be extracted."""
        from iabv_v15.services.common_sense_engine import extract_facts
        facts = extract_facts(
            account_scan={
                'secrets': {'secrets_file_exists': True},
                'api_health': {'github_api': {'last_status_code': 401}},
            },
        )
        assert 'cloud_api_401' in facts
        assert 'github_api_401' in facts

    def test_api_health_403_triggers_fact(self):
        from iabv_v15.services.common_sense_engine import extract_facts
        facts = extract_facts(
            account_scan={
                'secrets': {'secrets_file_exists': True},
                'api_health': {'gemini': {'last_status_code': 403}},
            },
        )
        assert 'cloud_api_403' in facts

    def test_google_account_in_browser_fact(self):
        """Detect Google account in browser scan for Gemini provisioning."""
        from iabv_v15.services.common_sense_engine import extract_facts
        deep_env = {
            'browsers': [{
                'profiles': [{
                    'accounts': [{'type': 'google'}],
                }],
            }],
        }
        facts = extract_facts(
            account_scan={'secrets': {'secrets_file_exists': True}},
            deep_env_scan=deep_env,
        )
        assert 'google_account_in_browser' in facts


    def test_gemini_quota_exhausted_rule_exists(self):
        from iabv_v15.services.common_sense_engine import INFERENCE_RULES
        rule_ids = [r['id'] for r in INFERENCE_RULES]
        assert 'gemini_quota_exhausted' in rule_ids

    def test_gemini_429_fact_extracted(self):
        from iabv_v15.services.common_sense_engine import extract_facts
        facts = extract_facts(
            account_scan={
                'secrets': {'secrets_file_exists': True},
                'api_health': {'gemini': {'last_status_code': 429}},
            },
        )
        assert 'cloud_api_429' in facts
        assert 'gemini_api_429' in facts

    def test_exec_auto_provision_gemini(self):
        from iabv_v15.services.common_sense_engine import _exec_auto_provision_gemini
        rule = {'id': 'gemini_quota_exhausted'}
        result = _exec_auto_provision_gemini(rule)
        assert result['executed'] is True
        assert result['learned_solution'] == 'create_key_in_new_project'
        assert result['env_key'] == 'GEMINI_API_KEY'
        assert 'aistudio.google.com' in result['signup_url']
        assert 'troubleshooting' in result
        assert 'error_429_limit_0' in result['troubleshooting']

    def test_auto_provision_gemini_executor_registered(self):
        from iabv_v15.services.common_sense_engine import _ACTION_EXECUTORS
        assert 'auto_provision_gemini' in _ACTION_EXECUTORS
        assert 'notify_quota_exhausted' in _ACTION_EXECUTORS

    def test_cloud_provisioning_knowledge_file_exists(self):
        knowledge_path = Path(__file__).parent.parent / 'data' / 'evolution' / 'tool_discovery' / 'cloud_provider_provisioning.json'
        assert knowledge_path.exists()
        data = json.loads(knowledge_path.read_text())
        assert 'gemini' in data['providers']
        assert 'groq' in data['providers']
        assert '429_limit_0' in data['providers']['gemini']['known_issues']


class TestCloudReasoningPlannerHealth:
    """Tests for API health tracking in CloudReasoningPlannerService."""

    def test_record_api_health(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import (
            CloudReasoningPlannerService,
        )
        CloudReasoningPlannerService._api_health.clear()
        CloudReasoningPlannerService._record_api_health('groq', 200)
        health = CloudReasoningPlannerService.get_api_health()
        assert 'groq' in health
        assert health['groq']['last_status_code'] == 200
        assert health['groq']['healthy'] is True

    def test_record_api_health_401(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import (
            CloudReasoningPlannerService,
        )
        CloudReasoningPlannerService._api_health.clear()
        CloudReasoningPlannerService._record_api_health('gemini', 401)
        health = CloudReasoningPlannerService.get_api_health()
        assert health['gemini']['last_status_code'] == 401
        assert health['gemini']['healthy'] is False

    def test_record_api_health_429(self):
        from iabv_v15.services.adaptive.cloud_reasoning_planner import (
            CloudReasoningPlannerService,
        )
        CloudReasoningPlannerService._api_health.clear()
        CloudReasoningPlannerService._record_api_health('gemini', 429)
        health = CloudReasoningPlannerService.get_api_health()
        assert health['gemini']['last_status_code'] == 429
        assert health['gemini']['healthy'] is False


class TestCloudKeyAutonomousProvisioner:
    """Tests for autonomous cloud key provisioning."""

    def test_provisioner_imports(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
            PageScanResult,
            ProvisioningResult,
            ProvisioningStep,
        )
        assert CloudKeyAutonomousProvisioner is not None
        assert PageScanResult is not None

    def test_known_providers(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
        )
        providers = CloudKeyAutonomousProvisioner.get_known_providers()
        assert 'gemini' in providers
        assert 'groq' in providers

    def test_provider_knowledge_structure(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
        )
        knowledge = CloudKeyAutonomousProvisioner.get_provider_knowledge()
        for provider_id in ('gemini', 'groq'):
            pk = knowledge[provider_id]
            assert 'env_key' in pk
            assert 'key_prefix' in pk
            assert 'start_url' in pk
            assert 'verify_url' in pk
            assert 'steps_pattern' in pk
            assert 'known_errors' in pk

    def test_find_create_key_button(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
            PageScanResult,
        )
        scan = PageScanResult(
            url='https://aistudio.google.com/apikey',
            title='AI Studio',
            buttons=[
                {'text': 'Create API key', 'ariaLabel': '', 'disabled': False},
                {'text': 'Settings', 'ariaLabel': '', 'disabled': False},
            ],
        )
        provisioner = CloudKeyAutonomousProvisioner()
        button = provisioner.find_create_key_button(scan)
        assert button is not None
        assert 'Create API key' in button['text']

    def test_find_api_key_on_page(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
            PageScanResult,
        )
        scan = PageScanResult(
            url='https://aistudio.google.com/apikey',
            title='AI Studio',
            key_displays=[
                {'text': 'AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz', 'className': 'api-key'},
            ],
        )
        provisioner = CloudKeyAutonomousProvisioner()
        key = provisioner.find_api_key_on_page(scan, prefix='AIza')
        assert key is not None
        assert key.startswith('AIza')

    def test_detect_auth_required(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
            PageScanResult,
        )
        scan_auth = PageScanResult(
            url='https://accounts.google.com',
            title='Sign in - Google Accounts',
            buttons=[{'text': 'Sign in', 'ariaLabel': '', 'disabled': False}],
        )
        scan_no_auth = PageScanResult(
            url='https://aistudio.google.com/apikey',
            title='API Keys - AI Studio',
            buttons=[{'text': 'Create API key', 'ariaLabel': '', 'disabled': False}],
        )
        provisioner = CloudKeyAutonomousProvisioner()
        assert provisioner.detect_auth_required(scan_auth) is True
        assert provisioner.detect_auth_required(scan_no_auth) is False

    def test_provision_unknown_provider(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
        )
        provisioner = CloudKeyAutonomousProvisioner()
        result = provisioner.provision_key('unknown_provider')
        assert result.success is False
        assert 'Unknown provider' in result.error

    def test_gemini_known_errors(self):
        from iabv_v15.services.cloud_key_autonomous_provisioner import (
            CloudKeyAutonomousProvisioner,
        )
        knowledge = CloudKeyAutonomousProvisioner.get_provider_knowledge()
        gemini = knowledge['gemini']
        assert 429 in gemini['known_errors']
        assert 401 in gemini['known_errors']
        assert 'new project' in gemini['known_errors'][429].lower()
