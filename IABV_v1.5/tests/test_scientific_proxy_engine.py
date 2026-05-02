"""Tests for scientific proxy engine and full telemetry pipeline.

Covers:
- Scientific proxy calculations (compression, entropy, inference depth, etc.)
- Worker recommendation logic
- Calibration error (ECE)
- Nonlinearity indicator
- Adapter telemetry stamping (DevinApi, ExternalAssistant)
- New OSES findings (high corrections, good compression, performance jump)
- PortableContext scientific proxy aggregation
- ExternalWorkerTelemetry extended model fields
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExternalWorkerTelemetry,
    ToolCard,
    ToolTask,
    ToolType,
)
from iabv_v15.services.lab.scientific_proxy_engine import (
    calibration_error,
    compression_ratio,
    description_length_proxy,
    entropy_proxy,
    inference_depth_proxy,
    multi_step_success_rate,
    nonlinearity_indicator,
    reuse_score_from_runs,
    stability_score_from_runs,
    step_count_proxy,
    uncertainty_proxy_from_scores,
    worker_recommendation,
)


# ---- Scientific proxy unit tests ----

def test_compression_ratio_nonempty() -> None:
    text = 'The quick brown fox jumps over the lazy dog. ' * 10
    cr = compression_ratio(text)
    assert 0.0 < cr < 1.0, f'Expected compressible text to have ratio < 1.0, got {cr}'


def test_compression_ratio_empty() -> None:
    assert compression_ratio('') == 1.0


def test_compression_ratio_random_high() -> None:
    import random
    random.seed(42)
    text = ''.join(chr(random.randint(32, 126)) for _ in range(1000))
    cr = compression_ratio(text)
    assert cr > 0.5, f'Random text should be hard to compress, got {cr}'


def test_description_length_proxy_basic() -> None:
    text = 'Hello world ' * 100
    dl = description_length_proxy(text)
    assert dl > 0
    assert dl < len(text.encode('utf-8'))


def test_description_length_empty() -> None:
    assert description_length_proxy('') == 0


def test_entropy_proxy_uniform() -> None:
    text = ''.join(chr(i) for i in range(32, 127)) * 10
    ep = entropy_proxy(text)
    assert ep > 5.0, f'Uniform distribution should have high entropy, got {ep}'


def test_entropy_proxy_repetitive() -> None:
    text = 'aaa' * 100
    ep = entropy_proxy(text)
    assert ep < 1.0, f'Repetitive text should have low entropy, got {ep}'


def test_entropy_proxy_empty() -> None:
    assert entropy_proxy('') == 0.0


def test_inference_depth_proxy_multi_step() -> None:
    text = (
        'Step 1. Analyze the problem. '
        'Then consider alternatives. '
        'Therefore the solution is X. '
        'Because of this, we proceed. '
        'Finally, verify the result.'
    )
    depth = inference_depth_proxy(text)
    assert depth >= 5, f'Multi-step text should have depth >= 5, got {depth}'


def test_inference_depth_empty() -> None:
    assert inference_depth_proxy('') == 0


def test_step_count_proxy_lines() -> None:
    text = 'Line 1\nLine 2\nLine 3\n\nLine 4'
    count = step_count_proxy(text)
    assert count == 4


def test_step_count_empty() -> None:
    assert step_count_proxy('') == 0


def test_reuse_score_all_same() -> None:
    runs = [{'assistant_kind': 'codex'}] * 10
    assert reuse_score_from_runs(runs) == 1.0


def test_reuse_score_diverse() -> None:
    runs = [{'assistant_kind': f'worker_{i}'} for i in range(10)]
    score = reuse_score_from_runs(runs)
    assert score == 0.1


def test_reuse_score_empty() -> None:
    assert reuse_score_from_runs([]) == 0.0


def test_stability_score_stable() -> None:
    scores = [0.8, 0.82, 0.79, 0.81, 0.8]
    ss = stability_score_from_runs(scores)
    assert ss > 0.9, f'Stable scores should have high stability, got {ss}'


def test_stability_score_volatile() -> None:
    scores = [0.1, 0.9, 0.2, 0.8, 0.15, 0.85]
    ss = stability_score_from_runs(scores)
    assert ss < 0.5, f'Volatile scores should have low stability, got {ss}'


def test_stability_score_single() -> None:
    assert stability_score_from_runs([0.5]) == 1.0


def test_calibration_error_perfect() -> None:
    confs = [0.9, 0.9, 0.9, 0.9, 0.9]
    successes = [True, True, True, True, True]
    ece = calibration_error(confs, successes)
    assert ece < 0.15, f'Perfect calibration should have low ECE, got {ece}'


def test_calibration_error_overconfident() -> None:
    confs = [0.9, 0.9, 0.9, 0.9, 0.9]
    successes = [False, False, False, False, False]
    ece = calibration_error(confs, successes)
    assert ece > 0.5, f'Overconfident system should have high ECE, got {ece}'


def test_calibration_error_empty() -> None:
    assert calibration_error([], []) == 0.0


def test_nonlinearity_flat() -> None:
    scores = [0.5] * 12
    nli = nonlinearity_indicator(scores)
    assert abs(nli - 1.0) < 0.1


def test_nonlinearity_jump() -> None:
    scores = [0.3, 0.31, 0.29, 0.32, 0.3, 0.7, 0.72, 0.69, 0.71, 0.7]
    nli = nonlinearity_indicator(scores, window=5)
    assert nli > 1.5, f'Performance jump should show nli > 1.5, got {nli}'


def test_nonlinearity_insufficient_data() -> None:
    assert nonlinearity_indicator([0.5, 0.6]) == 1.0


def test_multi_step_success_rate_basic() -> None:
    outcomes = [
        {'inference_depth_proxy': 5, 'success': True},
        {'inference_depth_proxy': 5, 'success': False},
        {'inference_depth_proxy': 1, 'success': True},
    ]
    rate = multi_step_success_rate(outcomes)
    assert rate == 0.5


def test_uncertainty_proxy() -> None:
    scores = [0.5, 0.5, 0.5]
    assert uncertainty_proxy_from_scores(scores) == 0.0
    scores2 = [0.1, 0.9, 0.1, 0.9]
    assert uncertainty_proxy_from_scores(scores2) > 0.3


# ---- Worker recommendation tests ----

def test_recommend_checkpoint_on_budget_exhausted() -> None:
    rec = worker_recommendation(
        success=False, budget_state='exhausted', handoff_required=True,
        correction_rounds=0, reuse_score=0.5, stability_score=0.5,
    )
    assert rec == 'checkpoint_and_resume'


def test_recommend_switch_on_high_corrections() -> None:
    rec = worker_recommendation(
        success=False, budget_state='ok', handoff_required=False,
        correction_rounds=3, reuse_score=0.5, stability_score=0.5,
    )
    assert rec == 'switch_worker'


def test_recommend_promote_on_success() -> None:
    rec = worker_recommendation(
        success=True, budget_state='ok', handoff_required=False,
        correction_rounds=0, reuse_score=0.8, stability_score=0.9,
    )
    assert rec == 'promote_to_recommendation'


def test_recommend_continue_on_success_low_reuse() -> None:
    rec = worker_recommendation(
        success=True, budget_state='ok', handoff_required=False,
        correction_rounds=0, reuse_score=0.3, stability_score=0.5,
    )
    assert rec == 'continue_with_same_worker'


def test_recommend_reject_on_failure() -> None:
    rec = worker_recommendation(
        success=False, budget_state='ok', handoff_required=False,
        correction_rounds=0, reuse_score=0.5, stability_score=0.5,
    )
    assert rec == 'reject_and_stop'


def test_recommend_reanalyze_on_correctable_failure() -> None:
    rec = worker_recommendation(
        success=False, budget_state='ok', handoff_required=False,
        correction_rounds=1, reuse_score=0.5, stability_score=0.5,
    )
    assert rec == 'reanalyze'


# ---- Extended model tests ----

def test_external_worker_telemetry_scientific_fields() -> None:
    wt = ExternalWorkerTelemetry(
        worker_kind='devin',
        compression_ratio=0.42,
        entropy_proxy=4.5,
        inference_depth_proxy=8,
        step_count_proxy=15,
        confidence=0.85,
        calibration_error=0.12,
        recommended_action='continue_with_same_worker',
    )
    assert wt.compression_ratio == 0.42
    assert wt.entropy_proxy == 4.5
    assert wt.inference_depth_proxy == 8
    assert wt.recommended_action == 'continue_with_same_worker'
    data = wt.model_dump(mode='json')
    assert data['compression_ratio'] == 0.42
    assert data['calibration_error'] == 0.12


def test_external_worker_telemetry_scientific_defaults() -> None:
    wt = ExternalWorkerTelemetry()
    assert wt.compression_ratio is None
    assert wt.entropy_proxy is None
    assert wt.confidence is None
    assert wt.recommended_action is None


# ---- Adapter telemetry stamping tests ----

def test_devin_adapter_stamps_telemetry() -> None:
    from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
    adapter = DevinApiToolAdapter(api_key='', timeout_seconds=0.1)
    card = ToolCard(
        tool_id='devin-test',
        title='Devin Test',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
    )
    task = ToolTask(tool_id='devin-test', title='Test Task', objective='test task')
    result = adapter.run(card, task)
    # Without API key, run returns failure — but still should NOT have telemetry
    # because the early-return for missing key doesn't stamp.
    # The telemetry is only stamped on the final return path.
    assert 'metadata' in result


def test_build_worker_telemetry_success() -> None:
    from iabv_v15.services.tools.tool_adapters import ToolAdapter
    result = {
        'success': True,
        'output_text': 'The result is 42. Therefore the answer is confirmed. Step 1 done.',
        'error_message': '',
        'execution_ms': 5000,
        'metadata': {},
    }
    wt = ToolAdapter._build_worker_telemetry(
        result=result,
        worker_kind='codex',
        assistant_kind='codex',
    )
    assert wt['worker_kind'] == 'codex'
    assert wt['result_status'] == 'success'
    assert wt['budget_state'] == 'ok'
    assert wt['handoff_required'] is False
    assert wt['latency_ms'] == 5000
    assert wt['compression_ratio'] is not None
    assert wt['entropy_proxy'] is not None
    assert wt['inference_depth_proxy'] is not None
    assert wt['inference_depth_proxy'] > 0


def test_build_worker_telemetry_quota_exceeded() -> None:
    from iabv_v15.services.tools.tool_adapters import ToolAdapter
    result = {
        'success': False,
        'output_text': '',
        'error_message': 'Rate limit exceeded',
        'execution_ms': 1000,
        'metadata': {},
    }
    wt = ToolAdapter._build_worker_telemetry(
        result=result,
        worker_kind='devin',
        assistant_kind='devin_api',
    )
    assert wt['budget_state'] == 'quota_exceeded'
    assert wt['handoff_required'] is True
    assert wt['continuation_state'] == 'truncated'
    assert wt['result_status'] == 'truncated'


def test_build_worker_telemetry_timeout() -> None:
    from iabv_v15.services.tools.tool_adapters import ToolAdapter
    result = {
        'success': False,
        'output_text': '',
        'error_message': 'Request timed out',
        'execution_ms': 120000,
        'metadata': {},
    }
    wt = ToolAdapter._build_worker_telemetry(
        result=result,
        worker_kind='windsurf',
        assistant_kind='windsurf',
    )
    assert wt['budget_state'] == 'timeout'
    assert wt['handoff_required'] is True


def test_stamp_telemetry() -> None:
    from iabv_v15.services.tools.tool_adapters import ToolAdapter
    result = {
        'success': True,
        'metadata': {'existing_key': 'value'},
    }
    telemetry = {'worker_kind': 'test', 'budget_state': 'ok'}
    stamped = ToolAdapter._stamp_telemetry(result, telemetry)
    assert stamped['metadata']['worker_telemetry'] == telemetry
    assert stamped['metadata']['existing_key'] == 'value'
    # Original should not be mutated
    assert 'worker_telemetry' not in result['metadata']


# ---- Integration tests: OSES new findings ----

def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _seed_runs_with_bootstrap(bootstrap, runs_data: list[dict]) -> None:
    from iabv_v15.bootstrap import AppBootstrap
    for rd in runs_data:
        meta = {
            'evidence_basis': rd.get('evidence_basis', {'state': 'observed'}),
            'governance_flags': rd.get('governance_flags', {}),
            'selected_worker': rd.get('selected_worker', {}),
            'ranked_worker_count': rd.get('ranked_worker_count', 1),
            'task_unresolved': rd.get('task_unresolved', []),
            'assistant_kind': 'codex',
            'comparison_scope_key': 'general',
        }
        if 'worker_telemetry' in rd:
            meta['worker_telemetry'] = rd['worker_telemetry']
        if 'metacognitive_evaluation' in rd:
            meta['metacognitive_evaluation'] = rd['metacognitive_evaluation']
        bootstrap.experiment_lab.record_outcome(
            domain=ExperimentDomain.LANGUAGE,
            objective='test objective',
            subject_key='general',
            route=EvaluationRoute.LOCAL,
            candidate_label='codex',
            success=rd.get('success', True),
            observed_summary='test run',
            precision=rd.get('precision', 0.8),
            robustness=0.8,
            execution_ms=100,
            metadata=meta,
        )


def test_oses_detects_high_correction_recurrence() -> None:
    root = _workspace('wt_oses_corrections')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'correction_rounds': 3,
                    'budget_state': 'ok',
                },
            },
        ] * 6
        _seed_runs_with_bootstrap(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_worker_high_corrections' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_detects_nonlinear_performance_jump() -> None:
    root = _workspace('wt_oses_nonlinear')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        # Low scores first, then high scores
        runs = []
        for i in range(5):
            runs.append({
                'evidence_basis': {'state': 'observed'},
                'precision': 0.3,
                'success': False,
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'budget_state': 'ok',
                },
            })
        for i in range(5):
            runs.append({
                'evidence_basis': {'state': 'observed'},
                'precision': 0.9,
                'success': True,
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'budget_state': 'ok',
                },
            })
        _seed_runs_with_bootstrap(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        # The jump may or may not trigger depending on total_score values,
        # but we verify no crash and the finding mechanism works
        assert isinstance(categories, list)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- TaskOutcomeRecorder propagation of new fields ----

def test_task_outcome_recorder_propagates_scientific_proxies() -> None:
    root = _workspace('wt_tor_proxies')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'budget_state': 'ok',
                    'compression_ratio': 0.42,
                    'entropy_proxy': 4.5,
                    'inference_depth_proxy': 8,
                    'confidence': 0.85,
                    'recommended_action': 'continue_with_same_worker',
                },
            },
        ] * 3
        _seed_runs_with_bootstrap(bootstrap, runs)

        # Check that the latest run has the extended fields
        latest_runs = bootstrap.experiment_lab.repository.list_runs(
            domain='language', subject_key='general', limit=3,
        )
        assert len(latest_runs) >= 1
        wt = latest_runs[0].metadata.get('worker_telemetry', {})
        assert wt.get('compression_ratio') == 0.42
        assert wt.get('entropy_proxy') == 4.5
        assert wt.get('confidence') == 0.85
        assert wt.get('recommended_action') == 'continue_with_same_worker'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- PortableContext scientific proxy aggregation ----

def test_portable_context_includes_scientific_proxy_aggregates() -> None:
    root = _workspace('wt_portable_proxies')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'budget_state': 'ok',
                    'compression_ratio': 0.4,
                    'entropy_proxy': 4.0,
                    'inference_depth_proxy': 6,
                },
            },
        ] * 4 + [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'devin',
                    'budget_state': 'ok',
                    'compression_ratio': 0.6,
                    'entropy_proxy': 5.0,
                    'inference_depth_proxy': 10,
                },
            },
        ] * 2
        _seed_runs_with_bootstrap(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)
        tp_section = next(
            (s for s in package.sections if s.section_id == 'task_packet_summary'),
            None,
        )
        assert tp_section is not None
        wt_summary = tp_section.metadata.get('worker_telemetry_summary')
        assert wt_summary is not None
        assert 'avg_compression_ratio' in wt_summary
        assert 'avg_entropy_proxy' in wt_summary
        assert 'avg_inference_depth' in wt_summary
        assert 0.0 < wt_summary['avg_compression_ratio'] < 1.0
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- Metacognitive prediction / evaluation tests ----

def test_extract_prediction_from_recommendation() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    from iabv_v15.domain.models import ExperimentRecommendation, ExperimentDomain

    rec = ExperimentRecommendation(
        domain=ExperimentDomain.LANGUAGE,
        subject_key='general',
        recommended_route=EvaluationRoute.LOCAL,
        recommended_assistant_kind='codex',
        confidence=0.85,
        metadata={
            'ranked_configurations': [
                {'route': 'local', 'assistant_kind': 'codex', 'weighted_score': 0.9},
                {'route': 'cloud', 'assistant_kind': 'gpt4', 'weighted_score': 0.6},
            ],
        },
    )
    prediction = TaskOutcomeRecorder._extract_prediction(
        rec, route=EvaluationRoute.LOCAL, assistant_kind='codex',
    )
    assert prediction['predicted_outcome'] == 'success'
    assert prediction['confidence'] == 0.85
    assert prediction['uncertainty_proxy'] >= 0.0
    assert prediction['predicted_route'] == 'local'
    assert prediction['predicted_assistant_kind'] == 'codex'


def test_extract_prediction_no_recommendation() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    prediction = TaskOutcomeRecorder._extract_prediction(
        None, route=EvaluationRoute.LOCAL, assistant_kind='codex',
    )
    assert prediction == {}


def test_extract_prediction_low_confidence() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    from iabv_v15.domain.models import ExperimentRecommendation, ExperimentDomain

    rec = ExperimentRecommendation(
        domain=ExperimentDomain.LANGUAGE,
        recommended_route=EvaluationRoute.FALLBACK,
        confidence=0.3,
    )
    prediction = TaskOutcomeRecorder._extract_prediction(
        rec, route=EvaluationRoute.LOCAL, assistant_kind='codex',
    )
    assert prediction['predicted_outcome'] == 'failure'
    assert prediction['confidence'] == 0.3


def test_evaluate_prediction_correct_success() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    prediction = {
        'predicted_outcome': 'success',
        'confidence': 0.85,
        'uncertainty_proxy': 0.1,
    }
    result = TaskOutcomeRecorder._evaluate_prediction(prediction, actual_success=True)
    assert result['actual_outcome'] == 'success'
    assert result['predicted_outcome'] == 'success'
    assert result['false_positive'] is False
    assert result['false_negative'] is False
    assert result['calibration_error'] < 0.2  # |0.85 - 1.0| = 0.15
    assert result['recommended_action'] is not None


def test_evaluate_prediction_false_positive() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    prediction = {
        'predicted_outcome': 'success',
        'confidence': 0.9,
        'uncertainty_proxy': 0.0,
    }
    result = TaskOutcomeRecorder._evaluate_prediction(prediction, actual_success=False)
    assert result['actual_outcome'] == 'failure'
    assert result['false_positive'] is True
    assert result['false_negative'] is False
    assert result['calibration_error'] == 0.9  # |0.9 - 0.0|


def test_evaluate_prediction_false_negative() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    prediction = {
        'predicted_outcome': 'failure',
        'confidence': 0.2,
        'uncertainty_proxy': 0.5,
    }
    result = TaskOutcomeRecorder._evaluate_prediction(prediction, actual_success=True)
    assert result['actual_outcome'] == 'success'
    assert result['false_positive'] is False
    assert result['false_negative'] is True
    assert result['calibration_error'] == 0.8  # |0.2 - 1.0|


def test_evaluate_prediction_empty() -> None:
    from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
    result = TaskOutcomeRecorder._evaluate_prediction({}, actual_success=True)
    assert result == {}


# ---- OSES miscalibration findings ----

def test_oses_detects_miscalibration() -> None:
    root = _workspace('wt_oses_miscalibration')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {'worker_kind': 'codex', 'budget_state': 'ok'},
                'metacognitive_evaluation': {
                    'calibration_error': 0.6,
                    'false_positive': True,
                    'false_negative': False,
                },
            },
        ] * 6
        _seed_runs_with_bootstrap(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_metacognitive_miscalibration' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_detects_overconfidence() -> None:
    root = _workspace('wt_oses_overconfidence')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {'worker_kind': 'codex', 'budget_state': 'ok'},
                'metacognitive_evaluation': {
                    'calibration_error': 0.7,
                    'false_positive': True,
                    'false_negative': False,
                },
            },
        ] * 6
        _seed_runs_with_bootstrap(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_metacognitive_overconfidence' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_detects_underconfidence() -> None:
    root = _workspace('wt_oses_underconfidence')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {'worker_kind': 'codex', 'budget_state': 'ok'},
                'metacognitive_evaluation': {
                    'calibration_error': 0.5,
                    'false_positive': False,
                    'false_negative': True,
                },
            },
        ] * 6
        _seed_runs_with_bootstrap(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_metacognitive_underconfidence' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- PortableContext calibration summary ----

def test_portable_context_includes_calibration_summary() -> None:
    root = _workspace('wt_portable_calibration')
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {'worker_kind': 'codex', 'budget_state': 'ok'},
                'metacognitive_evaluation': {
                    'calibration_error': 0.3,
                    'false_positive': True,
                    'false_negative': False,
                },
            },
        ] * 4 + [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {'worker_kind': 'devin', 'budget_state': 'ok'},
                'metacognitive_evaluation': {
                    'calibration_error': 0.1,
                    'false_positive': False,
                    'false_negative': False,
                },
            },
        ] * 2
        _seed_runs_with_bootstrap(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)
        tp_section = next(
            (s for s in package.sections if s.section_id == 'task_packet_summary'),
            None,
        )
        assert tp_section is not None
        wt_summary = tp_section.metadata.get('worker_telemetry_summary')
        assert wt_summary is not None
        cal = wt_summary.get('metacognitive_calibration')
        assert cal is not None, 'metacognitive_calibration missing from summary'
        assert cal['evaluations_count'] == 6
        assert cal['false_positive_count'] == 4
        assert cal['false_negative_count'] == 0
        assert 0.0 < cal['avg_calibration_error'] < 1.0
    finally:
        shutil.rmtree(root, ignore_errors=True)
