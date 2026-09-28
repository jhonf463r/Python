#!/usr/bin/env python3
"""
R32-G2 v4: Threshold-crossing metacognitive experiment

Objective: Close causal edge from real threshold-crossing metacognitive
population to OSES finding to AdaptiveWeightLayer adjustment.

Key contract findings:
- Provider failure creates RunRecord with RunStatus.FAILED
- TaskOutcomeRecorder.record() executes with actual_success=False
- override_model in request.metadata allows per-request model change
- Metacognitive evaluation requires prior recommendation
"""
import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone

# Ensure UTF-8 output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configure default model
MODEL_NAME = 'gemma3:1b'
os.environ['IABV_OLLAMA_MODEL'] = MODEL_NAME

def main():
    print(f"=== R32-G2 v4 THRESHOLD-CROSSING METACOGNITIVE EXPERIMENT ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Model configured: {MODEL_NAME}")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    # Create fresh isolated workspace
    workspace_root = Path('C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5/data/r32g2_isolated_v4')
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    workspace_path = workspace_root / f'run_{workspace_id}'
    workspace_path.mkdir(exist_ok=True)

    print(f"Fresh isolated workspace: {workspace_path}")
    print()

    # Import IABV after model configuration
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.domain.models import InferenceRequest, TaskRole

    # Bootstrap with isolated workspace
    print("Constructing AppBootstrap with isolated workspace...")
    bootstrap = AppBootstrap(str(workspace_path))
    print(f"Bootstrap constructed")
    print(f"General provider config model: {bootstrap.general_provider.config.model}")
    print()

    # Verify Ollama availability
    print("Verifying Ollama...")
    try:
        import requests
        tags_resp = requests.get('http://127.0.0.1:11434/api/tags', timeout=5)
        tags_resp.raise_for_status()
        models = tags_resp.json().get('models', [])
        model_names = [m['name'] for m in models]
        print(f"Available models: {model_names}")
        if MODEL_NAME in model_names:
            print(f"Model {MODEL_NAME} is available")
        else:
            print(f"WARNING: Model {MODEL_NAME} not in available list")
    except Exception as e:
        print(f"ERROR checking Ollama: {e}")
        return 1
    print()

    # Execute warm-up + target pairs
    from iabv_v15.domain.models import ExperimentDomain

    # Use a consistent subject_key by using same user_goal
    WARMUP_GOAL = "Calculate 7 * 8"
    TARGET_GOAL = "Calculate 7 * 8"  # Same goal to trigger same subject_key

    PAIRS = 5  # Need at least 5 eligible runs, 3 metacognitive evaluations, 2 FP/FN

    execution_records = []

    for i in range(PAIRS):
        print(f"=== PAIR {i+1}/{PAIRS} ===")
        print(f"Warm-up goal: {WARMUP_GOAL}")
        print(f"Target goal: {TARGET_GOAL}")
        print()

        # Warm-up with real model
        print("Executing warm-up with real model...")
        warmup_request = InferenceRequest(
            user_goal=WARMUP_GOAL,
            role=TaskRole.KNOWLEDGE,
            metadata={}
        )
        warmup_result = bootstrap.inference_service.infer_task(warmup_request)
        warmup_run_id = warmup_result.run_id
        warmup_session_id = warmup_result.result.raw_output.get('adaptive_session', {}).get('session_id', 'unknown')
        print(f"Warm-up run_id: {warmup_run_id}")
        print(f"Warm-up session_id: {warmup_session_id}")
        print(f"Warm-up status: {warmup_result.status}")
        print()

        # Get subject_keys from the finalized session
        adaptive_session_data = warmup_result.result.raw_output.get('adaptive_session', {})
        warmup_subject_keys = adaptive_session_data.get('metadata', {}).get('adaptive_learning', {}).get('subject_keys', [])
        print(f"Warm-up subject_keys: {warmup_subject_keys}")
        print()

        # Check for recommendations
        lab = bootstrap.experiment_lab
        lab_repo = lab.repository

        warmup_recommendations = []
        for sk in warmup_subject_keys:
            rec = lab_repo.latest_recommendation(domain=ExperimentDomain.LANGUAGE.value, subject_key=sk)
            if rec:
                warmup_recommendations.append({
                    'subject_key': sk,
                    'recommendation_id': rec.recommendation_id,
                    'confidence': rec.confidence,
                    'predicted_outcome': 'success' if rec.confidence >= 0.5 else 'failure',
                })
        print(f"Warm-up recommendations: {json.dumps(warmup_recommendations, indent=2)}")
        print()

        # Target with NONEXISTENT model to cause failure
        print("Executing target with nonexistent model (to cause failure)...")
        target_request = InferenceRequest(
            user_goal=TARGET_GOAL,
            role=TaskRole.KNOWLEDGE,
            metadata={'override_model': 'nonexistent-model-xyz-123'}
        )
        target_result = bootstrap.inference_service.infer_task(target_request)
        target_run_id = target_result.run_id
        target_session_id = target_result.result.raw_output.get('adaptive_session', {}).get('session_id', 'unknown')
        print(f"Target run_id: {target_run_id}")
        print(f"Target session_id: {target_session_id}")
        print(f"Target status: {target_result.status}")
        print(f"Target error_summary: {target_result.error_summary}")
        print()

        execution_records.append({
            'pair_id': i + 1,
            'warmup_run_id': warmup_run_id,
            'warmup_session_id': warmup_session_id,
            'warmup_subject_keys': warmup_subject_keys,
            'warmup_recommendations': warmup_recommendations,
            'target_run_id': target_run_id,
            'target_session_id': target_session_id,
            'target_status': str(target_result.status),
            'target_error': target_result.error_summary,
        })

        print("---")
        print()

    # Reload ExperimentRuns from persisted storage
    print("Reloading ExperimentRuns from persistence...")
    all_runs = lab_repo.list_runs(limit=100)
    print(f"Total ExperimentRuns: {len(all_runs)}")
    print()

    # Inspect target ExperimentRuns
    target_runs = []
    for rec in execution_records:
        linked_id = rec['target_run_id']
        for run in all_runs:
            if run.metadata.get('linked_run_id') == linked_id:
                target_runs.append({
                    'pair_id': rec['pair_id'],
                    'experiment_run_id': run.run_id,
                    'linked_run_id': linked_id,
                    'subject_key': run.subject_key,
                    'evidence_basis': run.metadata.get('evidence_basis'),
                    'metacognitive_evaluation': run.metadata.get('metacognitive_evaluation'),
                    'success': run.success,
                })

    print(f"Target ExperimentRuns found: {len(target_runs)}")
    for tr in target_runs:
        print(f"  Pair {tr['pair_id']}: {tr['experiment_run_id']}")
        print(f"    subject_key: {tr['subject_key']}")
        print(f"    success: {tr['success']}")
        print(f"    evidence_basis: {tr['evidence_basis']}")
        print(f"    metacognitive_evaluation: {tr['metacognitive_evaluation']}")
        print()

    # Execute OSES review
    print("Executing OSES current_review...")
    oses = bootstrap.operational_self_examination_service
    review = oses.current_review(refresh=True)
    print(f"Review findings count: {len(review.findings)}")
    print()

    # Check for metacognitive findings
    mc_categories = [
        'task_packet_metacognitive_miscalibration',
        'task_packet_metacognitive_overconfidence',
        'task_packet_metacognitive_underconfidence'
    ]
    mc_findings = [f for f in review.findings if f.category in mc_categories]
    print(f"Metacognitive findings: {len(mc_findings)}")
    for f in mc_findings:
        print(f"  {f.category}: {f.title}")
        print(f"    severity: {f.severity}")
        print(f"    confidence: {f.confidence}")
        print(f"    metadata: {f.metadata}")
        print()

    # Check for feedback applied
    feedback_findings = [f for f in review.findings if f.category == 'metacognitive_feedback_applied']
    print(f"Feedback applied findings: {len(feedback_findings)}")
    for f in feedback_findings:
        print(f"  {f.category}: {f.title}")
        print(f"    metadata: {f.metadata}")
        print()

    # Check AdaptiveWeightLayer adjustment
    awl_path = workspace_path / 'data' / 'evolution' / 'adaptive_weights' / 'metacognitive_adjustments.json'
    print(f"AdaptiveWeightLayer path: {awl_path}")
    if awl_path.exists():
        with open(awl_path, 'r', encoding='utf-8') as f:
            awl_data = json.load(f)
        print(f"AdaptiveWeightLayer adjustments: {json.dumps(awl_data, indent=2)}")
    else:
        print("AdaptiveWeightLayer adjustments file does not exist")
    print()

    # Fresh-process read-back
    print("Testing fresh-process read-back...")
    from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
    fresh_awl = AdaptiveWeightLayer(persistence_path=str(workspace_path))
    for key in awl_data.keys() if awl_path.exists() else []:
        if key != '_version':
            adj = fresh_awl.get_metacognitive_adjustment(*key.split('|'))
            print(f"  {key}: {adj}")
    print()

    # Final summary
    print("=== FINAL SUMMARY ===")
    print(f"Execution pairs: {PAIRS}")
    print(f"Total ExperimentRuns: {len(all_runs)}")
    print(f"Target ExperimentRuns: {len(target_runs)}")
    print(f"Metacognitive findings: {len(mc_findings)}")
    print(f"Feedback applied: {len(feedback_findings)}")
    print(f"AWL adjustments persisted: {awl_path.exists()}")
    print()

    # Save evidence
    evidence = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'model': MODEL_NAME,
        'workspace': str(workspace_path),
        'execution_records': execution_records,
        'target_runs': target_runs,
        'total_experiment_runs': len(all_runs),
        'metacognitive_findings_count': len(mc_findings),
        'metacognitive_findings': [
            {
                'category': f.category,
                'title': f.title,
                'severity': str(f.severity),
                'confidence': f.confidence,
                'metadata': f.metadata
            }
            for f in mc_findings
        ],
        'feedback_applied_count': len(feedback_findings),
        'feedback_applied': [
            {
                'category': f.category,
                'title': f.title,
                'metadata': f.metadata
            }
            for f in feedback_findings
        ],
        'awl_adjustments': dict(awl_data) if awl_path.exists() else None,
    }

    evidence_file = workspace_path / 'evidence.json'
    with open(evidence_file, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2, default=str)
    print(f"Evidence saved to: {evidence_file}")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
