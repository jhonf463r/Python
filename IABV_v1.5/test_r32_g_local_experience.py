"""
R32-G: Prove real local productive experience → RunRecord → metacognitive_evaluation

This script creates a minimal service graph with real Ollama provider,
executes a productive request through LocalRoleRouter, creates an AdaptiveSession,
and verifies that TaskOutcomeRecorder generates metacognitive_evaluation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

# Add src to PYTHONPATH
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    AssistantConfigurationSnapshot,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    GoalContext,
    InferenceRequest,
    InferenceResult,
    ProviderKind,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    TaskContext,
    TaskIntent,
    TaskRole,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.providers.ollama_expert_provider import OllamaExpertProvider, ProviderConfig
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


def main():
    # Environment for R32-G isolated persistence
    workspace = Path(__file__).parent / 'data' / 'r32_g_isolated'
    workspace.mkdir(parents=True, exist_ok=True)

    root = workspace / f'test_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)

    print(f"R32-G WORKSPACE: {root}")

    # Database
    db = AppDatabase(str(root / 'app.sqlite'))

    # Repositories
    runs = RunRepository(db)
    evolution_storage = ArtifactStorage(str(root / 'evolution'))
    experiment_lab_repo = ExperimentLabRepository(db, evolution_storage)
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)

    # AdaptiveWeightLayer with isolated persistence
    adaptive_weight_layer = AdaptiveWeightLayer()
    adaptive_weights_dir = root / 'adaptive_weights'
    adaptive_weights_dir.mkdir(parents=True, exist_ok=True)
    adaptive_weight_layer.persistence_path = str(adaptive_weights_dir / 'r32_g_isolated.json')

    # ExperimentLab
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )

    # Real Ollama provider
    ollama_base_url = os.environ.get('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    ollama_model = os.environ.get('IABV_OLLAMA_MODEL', 'phi3:latest')

    print(f"OLLAMA_BASE_URL: {ollama_base_url}")
    print(f"OLLAMA_MODEL: {ollama_model}")

    ollama_config = ProviderConfig(
        name='ollama_local',
        kind=ProviderKind.LOCAL,
        base_url=ollama_base_url,
        model=ollama_model,
    )
    ollama_provider = OllamaExpertProvider(config=ollama_config, timeout_seconds=30.0)

    # Create a real request
    request = InferenceRequest(
        request_id=str(uuid4()),
        user_goal="Responde simplemente: OK",
        task_role=TaskRole.KNOWLEDGE,
        role_hint=TaskRole.KNOWLEDGE,
    )

    print("\n" + "="*60)
    print("EXECUTING REAL OLLAMA REQUEST")
    print("="*60)

    try:
        # Execute real Ollama inference
        result = ollama_provider.infer_task(request)

        print(f"RESULT SUMMARY: {result.summary}")
        print(f"CONFIDENCE: {result.confidence}")
        print(f"PROVIDER: {result.provider_name}")
        print(f"MODEL: {result.executor_model}")

        # Create RunRecord
        route = RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title=TaskRole.KNOWLEDGE.value,
            provider_name=ollama_provider.name,
            model_profile_id=ollama_model,
            model_name=ollama_model,
            reason='R32-G real local experience',
        )

        run_record = RunRecord(
            request=request,
            result=result,
            route=route,
            status=RunStatus.SUCCESS,
            duration_ms=0,
            error_summary='',
        )
        saved_run = runs.record(run_record)
        print(f"RUN_RECORD_ID: {saved_run.run_id}")

        # Create a previous ExperimentRecommendation (needed for metacognitive_evaluation)
        # The subject_key must match what _record_learning will look up
        subject_key = 'r32_g_test'
        recommendation = ExperimentRecommendation(
            recommendation_id=str(uuid4()),
            domain=ExperimentDomain.LANGUAGE,
            objective=request.user_goal,
            subject_key=subject_key,
            route=EvaluationRoute.LOCAL,
            recommended_route=EvaluationRoute.LOCAL,
            recommended_assistant_kind='ollama',
            candidate_label='ollama_local',
            candidate_id=saved_run.run_id,
            success=True,  # This is the prediction: we predict success
            observed_summary='',
            expected_summary='',
            precision=0.8,
            robustness=0.8,
            operational_cost=0.0,
            reuse_score=0.0,
            user_progress=0.0,
            execution_ms=0,
            evidence_refs=[],
            metadata={
                'predicted_success': True,
                'confidence': 0.8,
                'ranked_configurations': [
                    {'weighted_score': 0.8, 'score': 0.8, 'assistant_kind': 'ollama', 'route': 'local'},
                ],
            },
            suite_name='adaptive_session_finalize',
        )
        experiment_lab.repository.save_recommendation(recommendation)
        print(f"RECOMMENDATION_ID: {recommendation.recommendation_id}")
        print(f"RECOMMENDATION_SUBJECT_KEY: {recommendation.subject_key}")

        # Create AdaptiveSession with intent and context
        # The metadata must contain comparison_scope_key for _record_learning
        # The context.goal_context.objective.objective_id must match subject_key
        session = AdaptiveSession(
            session_id=str(uuid4()),
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key='knowledge.query',
                summary='R32-G test: simple knowledge query',
                confidence=0.8,
                detected_role=TaskRole.KNOWLEDGE,
                suggested_route=EvaluationRoute.LOCAL,
            ),
            context=TaskContext(
                goal_context=GoalContext(
                    objective={'objective_id': subject_key},
                ),
            ),
            status=AdaptiveSessionStatus.COMPLETED,
            created_at_utc=datetime.now(timezone.utc),
            updated_at_utc=datetime.now(timezone.utc),
            metadata={'comparison_scope_key': subject_key},
        )
        saved_session = adaptive_sessions.save(session)
        print(f"ADAPTIVE_SESSION_ID: {saved_session.session_id}")

        # TaskOutcomeRecorder
        task_outcome_recorder = TaskOutcomeRecorder(
            adaptive_session_repository=adaptive_sessions,
            capability_repository=capabilities,
            approval_checkpoint_repository=approvals,
            experiment_lab=experiment_lab,
            adaptive_weight_layer=adaptive_weight_layer,
            control_master_service=None,
            intent_understanding_service=None,
        )

        # Call TaskOutcomeRecorder.record with real session and run_record
        print("\n" + "="*60)
        print("CALLING TaskOutcomeRecorder.record()")
        print("="*60)

        finalized_session = task_outcome_recorder.record(saved_session, run_record=saved_run)
        print(f"FINALIZED_SESSION_ID: {finalized_session.session_id}")

        # Check for metacognitive_evaluation
        experiment_runs = experiment_lab_repo.list_runs()
        print(f"\nEXPERIMENT_RUNS_COUNT: {len(experiment_runs)}")

        for er in experiment_runs:
            print(f"\nEXPERIMENT_RUN_ID: {er.run_id}")
            print(f"METADATA KEYS: {list(er.metadata.keys())}")
            if 'metacognitive_evaluation' in er.metadata:
                print("\n" + "="*60)
                print("METACOGNITIVE_EVALUATION FOUND:")
                print("="*60)
                print(er.metadata['metacognitive_evaluation'])
                print("="*60)

                # Persistence read-back verification
                print("\n" + "="*60)
                print("PERSISTENCE READBACK VERIFICATION")
                print("="*60)
                all_runs = experiment_lab_repo.list_runs()
                reloaded_run = next((r for r in all_runs if r.run_id == er.run_id), None)
                if reloaded_run and 'metacognitive_evaluation' in reloaded_run.metadata:
                    print(f"READBACK: metacognitive_evaluation persisted and reloadable")
                    print(f"READBACK VALUE: {reloaded_run.metadata['metacognitive_evaluation']}")
                    print("="*60)
                    return True
                else:
                    print(f"READBACK FAILED: metadata not found in reloaded run")
                    return False
            else:
                print("NO metacognitive_evaluation in this run")

        print("\n" + "="*60)
        print("NO METACOGNITIVE_EVALUATION FOUND IN ANY RUN")
        print("="*60)
        return False

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
