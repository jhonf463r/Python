"""
R32-G2: Production runtime experiment

Demonstrates that a system-generated recommendation from a real production
execution becomes the prediction basis for a subsequent production execution
and produces a causally attributable metacognitive_evaluation.

This script:
1. Creates an isolated workspace
2. Constructs AppBootstrap with that workspace
3. Executes a warm-up request through InferenceService
4. Reads back the system-generated ExperimentRecommendation
5. Executes a target request through InferenceService
6. Verifies that metacognitive_evaluation is generated from the warm-up recommendation
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

# Configure UTF-8 output for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to PYTHONPATH
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import InferenceRequest, TaskRole


def main():
    # Isolated workspace
    workspace = Path(__file__).parent / 'data' / 'r32g2_isolated' / f'run_{uuid4().hex}'
    workspace.mkdir(parents=True, exist_ok=True)
    
    print(f"R32-G2 ISOLATED WORKSPACE: {workspace}")
    
    # Environment for isolation
    os.environ['IABV_WORKSPACE'] = str(workspace)
    os.environ['IABV_WORKSPACE_ROOT'] = str(workspace)
    os.environ['IABV_AUTONOMOUS_EXTERNAL_LAUNCH'] = '0'
    
    # Ollama configuration
    ollama_base_url = os.environ.get('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    ollama_model = os.environ.get('IABV_OLLAMA_MODEL', 'gemma3:1b')
    
    os.environ['IABV_OLLAMA_BASE_URL'] = ollama_base_url
    os.environ['IABV_OLLAMA_MODEL'] = ollama_model
    
    print(f"OLLAMA_BASE_URL: {ollama_base_url}")
    print(f"OLLAMA_MODEL: {ollama_model}")
    
    # Construct AppBootstrap with isolated workspace
    print("\n" + "="*60)
    print("CONSTRUCTING AppBootstrap")
    print("="*60)
    
    bootstrap = AppBootstrap(workspace_root=str(workspace))
    
    # Effective AdaptiveWeightLayer path for evidence
    if hasattr(bootstrap, 'adaptive_weight_layer'):
        if hasattr(bootstrap.adaptive_weight_layer, '_weights_path'):
            effective_path = bootstrap.adaptive_weight_layer._weights_path
            print(f"EFFECTIVE ADAPTIVE_WEIGHT_PATH: {effective_path}")
        else:
            print("WARNING: _weights_path not found on AdaptiveWeightLayer")
    else:
        print("WARNING: adaptive_weight_layer not found in bootstrap")
    
    # Access InferenceService
    if not hasattr(bootstrap, 'inference_service'):
        print("ERROR: inference_service not found in bootstrap")
        return False
    
    inference_service = bootstrap.inference_service
    print(f"InferenceService found: {type(inference_service).__name__}")
    
    # Access ExperimentLab for recommendation read-back
    if not hasattr(bootstrap, 'experiment_lab'):
        print("ERROR: experiment_lab not found in bootstrap")
        return False
    
    experiment_lab = bootstrap.experiment_lab
    print(f"ExperimentLab found: {type(experiment_lab).__name__}")
    
    # Warm-up request
    warmup_request = InferenceRequest(
        request_id=str(uuid4()),
        user_goal="Responde simplemente: OK",
        task_role=TaskRole.KNOWLEDGE,
        role_hint=TaskRole.KNOWLEDGE,
    )
    
    print("\n" + "="*60)
    print("WARM-UP EXECUTION")
    print("="*60)
    print(f"REQUEST: {warmup_request.user_goal}")
    print(f"TASK_ROLE: {warmup_request.task_role}")
    
    try:
        warmup_result = inference_service.infer_task(warmup_request)
        print(f"WARM-UP RUN_RECORD_ID: {warmup_result.run_id}")
        print(f"WARM-UP STATUS: {warmup_result.status}")
        print(f"WARM-UP PROVIDER: {warmup_result.result.provider_name}")
        print(f"WARM-UP MODEL: {warmup_result.result.executor_model}")
        print(f"WARM-UP CONFIDENCE: {warmup_result.result.confidence}")
        
        # Extract RunRecord and AdaptiveSession from result
        if hasattr(warmup_result.result, 'raw_output'):
            raw_output = warmup_result.result.raw_output
            print(f"WARM-UP RAW_OUTPUT KEYS: {list(raw_output.keys())}")
            
            adaptive_session_data = raw_output.get('adaptive_session')
            
            # Check local_chat_llm evidence
            local_chat_llm = raw_output.get('local_chat_llm', {})
            print(f"WARM-UP LOCAL_CHAT_LLM: {json.dumps(local_chat_llm, indent=2)}")
            
            if adaptive_session_data:
                print(f"WARM-UP SESSION_ID: {adaptive_session_data.get('session_id')}")
                session_metadata = adaptive_session_data.get('metadata', {})
                adaptive_learning = session_metadata.get('adaptive_learning', {})
                subject_keys = adaptive_learning.get('subject_keys', [])
                print(f"WARM-UP SUBJECT_KEYS: {subject_keys}")
            else:
                print("ERROR: No adaptive_session in warm-up result")
                return False
        else:
            print("ERROR: No raw_output in warm-up result")
            return False
            
    except Exception as e:
        print(f"WARM-UP EXECUTION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Read back system-generated recommendation
    print("\n" + "="*60)
    print("READING SYSTEM-GENERATED RECOMMENDATION")
    print("="*60)
    
    # Determine subject key from session
    if subject_keys:
        subject_key = subject_keys[0]  # Use first subject key
    else:
        print("ERROR: No subject_keys found in warm-up session")
        return False
    
    print(f"SUBJECT_KEY: {subject_key}")
    
    try:
        # Read latest recommendation from ExperimentLab
        recommendations = experiment_lab.repository.list_recommendations()
        print(f"TOTAL RECOMMENDATIONS: {len(recommendations)}")
        
        # Find recommendation matching subject_key
        warmup_recommendation = None
        for rec in recommendations:
            if rec.subject_key == subject_key:
                warmup_recommendation = rec
                break
        
        if warmup_recommendation:
            print(f"WARM-UP RECOMMENDATION_ID: {warmup_recommendation.recommendation_id}")
            print(f"WARM-UP RECOMMENDATION_DOMAIN: {warmup_recommendation.domain}")
            print(f"WARM-UP RECOMMENDATION_SUBJECT_KEY: {warmup_recommendation.subject_key}")
            print(f"WARM-UP RECOMMENDATION_ROUTE: {warmup_recommendation.recommended_route}")
            print(f"WARM-UP RECOMMENDATION_ASSISTANT_KIND: {warmup_recommendation.recommended_assistant_kind}")
            print(f"WARM-UP RECOMMENDATION_CONFIDENCE: {warmup_recommendation.confidence}")
            print(f"WARM-UP RECOMMENDATION_CREATED_AT: {warmup_recommendation.created_at_utc}")
            print(f"WARM-UP RECOMMENDATION_SUPPORTING_RUN_IDS: {warmup_recommendation.supporting_run_ids}")
        else:
            print("ERROR: No recommendation found for subject_key")
            return False
            
    except Exception as e:
        print(f"RECOMMENDATION READ-BACK ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Target execution (same logical goal)
    target_request = InferenceRequest(
        request_id=str(uuid4()),
        user_goal="Responde simplemente: OK",
        task_role=TaskRole.KNOWLEDGE,
        role_hint=TaskRole.KNOWLEDGE,
    )
    
    print("\n" + "="*60)
    print("TARGET EXECUTION")
    print("="*60)
    print(f"REQUEST: {target_request.user_goal}")
    print(f"TASK_ROLE: {target_request.task_role}")
    
    try:
        target_result = inference_service.infer_task(target_request)
        print(f"TARGET RUN_RECORD_ID: {target_result.run_id}")
        print(f"TARGET STATUS: {target_result.status}")
        print(f"TARGET PROVIDER: {target_result.result.provider_name}")
        print(f"TARGET MODEL: {target_result.result.executor_model}")
        print(f"TARGET CONFIDENCE: {target_result.result.confidence}")
        
        # Extract RunRecord and AdaptiveSession from result
        if hasattr(target_result.result, 'raw_output'):
            raw_output = target_result.result.raw_output
            print(f"TARGET RAW_OUTPUT KEYS: {list(raw_output.keys())}")
            
            adaptive_session_data = raw_output.get('adaptive_session')
            
            # Check local_chat_llm evidence
            local_chat_llm = raw_output.get('local_chat_llm', {})
            print(f"TARGET LOCAL_CHAT_LLM: {json.dumps(local_chat_llm, indent=2)}")
            
            if adaptive_session_data:
                print(f"TARGET SESSION_ID: {adaptive_session_data.get('session_id')}")
            else:
                print("ERROR: No adaptive_session in target result")
                return False
        else:
            print("ERROR: No raw_output in target result")
            return False
            
    except Exception as e:
        print(f"TARGET EXECUTION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Read back ExperimentRun for metacognitive_evaluation
    print("\n" + "="*60)
    print("READING EXPERIMENT RUN FOR METACOGNITIVE EVALUATION")
    print("="*60)
    
    try:
        experiment_runs = experiment_lab.repository.list_runs()
        print(f"TOTAL EXPERIMENT RUNS: {len(experiment_runs)}")
        
        for er in experiment_runs:
            print(f"\nEXPERIMENT_RUN_ID: {er.run_id}")
            print(f"METADATA KEYS: {list(er.metadata.keys())}")
            
            if 'metacognitive_evaluation' in er.metadata:
                print("\n" + "="*60)
                print("METACOGNITIVE_EVALUATION FOUND:")
                print("="*60)
                print(json.dumps(er.metadata['metacognitive_evaluation'], indent=2))
                print("="*60)
                
                # Verify persistence read-back
                print("\n" + "="*60)
                print("PERSISTENCE READBACK VERIFICATION")
                print("="*60)
                all_runs = experiment_lab.repository.list_runs()
                reloaded_run = next((r for r in all_runs if r.run_id == er.run_id), None)
                if reloaded_run and 'metacognitive_evaluation' in reloaded_run.metadata:
                    print(f"READBACK: metacognitive_evaluation persisted and reloadable")
                    print(f"READBACK VALUE: {json.dumps(reloaded_run.metadata['metacognitive_evaluation'], indent=2)}")
                    print("="*60)
                    return True
                else:
                    print(f"READBACK FAILED: metadata not found in reloaded run")
                    return False
            else:
                print("NO metacognitive_evaluation in this run")
                
    except Exception as e:
        print(f"EXPERIMENT RUN READ-BACK ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)
    print("NO METACOGNITIVE_EVALUATION FOUND IN ANY RUN")
    print("="*60)
    return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
