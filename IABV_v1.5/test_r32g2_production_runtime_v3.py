#!/usr/bin/env python3
"""
R32-G2 v3: Production runtime discriminating experiment

Objective: Close the causal edge from real production ExperimentRun
to generic OSES metacognitive finding using the implemented seam.

Key constraint: Do NOT attempt to prove adjustment → future decision influence.
"""
import os
import sys
import shutil
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# Ensure UTF-8 output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configure model BEFORE importing IABV
MODEL_NAME = 'gemma3:1b'
os.environ['IABV_OLLAMA_MODEL'] = MODEL_NAME

def main():
    print(f"=== R32-G2 v3 PRODUCTION RUNTIME DISCRIMINATING EXPERIMENT ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Model configured: {MODEL_NAME}")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    # Create fresh isolated workspace
    workspace_root = Path('C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5/data/r32g2_isolated_v3')
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

    # Execute multiple warm-up/target pairs
    from iabv_v15.domain.models import ExperimentDomain

    PAIRS = [
        ('pair-a', 'What is 2+2?', 'Simple arithmetic'),
        ('pair-b', 'What is the capital of France?', 'Geography'),
        ('pair-c', 'Write a haiku about code', 'Creative writing'),
    ]

    execution_records = []

    for pair_id, warmup_goal, target_goal in PAIRS:
        print(f"=== {pair_id.upper()} ===")
        print(f"Warm-up goal: {warmup_goal}")
        print(f"Target goal: {target_goal}")
        print()

        # Warm-up
        print("Executing warm-up...")
        warmup_request = InferenceRequest(
            user_goal=warmup_goal,
            role=TaskRole.KNOWLEDGE,
            metadata={}
        )
        warmup_result = bootstrap.inference_service.infer_task(warmup_request)
        warmup_run_id = warmup_result.run_id
        warmup_session_id = warmup_result.result.raw_output.get('adaptive_session', {}).get('session_id', 'unknown')
        print(f"Warm-up run_id: {warmup_run_id}")
        print(f"Warm-up session_id: {warmup_session_id}")
        print()

        # Get recommendations from warm-up
        from iabv_v15.services.lab.experiment_lab import ExperimentLab
        lab = bootstrap.experiment_lab
        lab_repo = lab.repository

        subject_keys = warmup_result.result.raw_output.get('adaptive_session', {}).get('subject_keys', [])
        print(f"Warm-up subject_keys: {subject_keys}")
        print()

        warmup_recommendations = []
        for sk in subject_keys:
            rec = lab_repo.latest_recommendation(ExperimentDomain.LANGUAGE, sk)
            if rec:
                warmup_recommendations.append({
                    'subject_key': sk,
                    'recommendation_id': rec.recommendation_id,
                    'confidence': rec.confidence,
                    'created_at': rec.created_at_utc.isoformat() if rec.created_at_utc else None
                })
        print(f"Warm-up recommendations: {json.dumps(warmup_recommendations, indent=2)}")
        print()

        # Target
        print("Executing target...")
        target_request = InferenceRequest(
            user_goal=target_goal,
            role=TaskRole.KNOWLEDGE,
            metadata={}
        )
        target_result = bootstrap.inference_service.infer_task(target_request)
        target_run_id = target_result.run_id
        target_session_id = target_result.result.raw_output.get('adaptive_session', {}).get('session_id', 'unknown')
        print(f"Target run_id: {target_run_id}")
        print(f"Target session_id: {target_session_id}")
        print()

        # Check Ollama state
        try:
            ps_resp = requests.get('http://127.0.0.1:11434/api/ps', timeout=5)
            ps_resp.raise_for_status()
            ps_data = ps_resp.json()
            if ps_data.get('models'):
                loaded_model = ps_data['models'][0].get('name', 'unknown')
                print(f"Ollama loaded model after execution: {loaded_model}")
        except Exception as e:
            print(f"WARNING checking Ollama /api/ps: {e}")
        print()

        execution_records.append({
            'pair_id': pair_id,
            'warmup_run_id': warmup_run_id,
            'warmup_session_id': warmup_session_id,
            'warmup_subject_keys': subject_keys,
            'warmup_recommendations': warmup_recommendations,
            'target_run_id': target_run_id,
            'target_session_id': target_session_id,
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
                })

    print(f"Target ExperimentRuns found: {len(target_runs)}")
    for tr in target_runs:
        print(f"  {tr['pair_id']}: {tr['experiment_run_id']}")
        print(f"    subject_key: {tr['subject_key']}")
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

    # Final summary
    print("=== FINAL SUMMARY ===")
    print(f"Execution pairs: {len(PAIRS)}")
    print(f"Total ExperimentRuns: {len(all_runs)}")
    print(f"Target ExperimentRuns: {len(target_runs)}")
    print(f"Metacognitive findings: {len(mc_findings)}")
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
        ]
    }

    evidence_file = workspace_path / 'evidence.json'
    with open(evidence_file, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2, default=str)
    print(f"Evidence saved to: {evidence_file}")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
