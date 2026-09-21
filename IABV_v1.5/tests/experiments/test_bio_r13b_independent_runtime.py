"""BIO-R13B independent, deterministic runtime reproduction.

Run directly for an evidence-producing experiment, or import under pytest.
It invokes the current production selector, adaptive weight layer, and
ToolEvolutionMonitor proposal method.  It never calls a networked service.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from iabv_v15.domain.models import EvaluationRoute, ExperimentDomain, ExperimentMetric, ExperimentRun
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.evolution.tool_evolution_monitor import ToolEvolutionMonitor
from iabv_v15.services.lab.strategy_selector import StrategySelector


SUBJECT = "bio_r13b_independent_2026_09_21"
SCOPE = "bio_r13b_independent_2026_09_21"
DOMAIN = ExperimentDomain.CLOUD_REASONING
STAMP = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _runs(*, a_success: bool, trace_suffix: str = "base") -> list[ExperimentRun]:
    """The treatment changes only A.success; trace_suffix is negative-control-only."""
    common = dict(
        domain=DOMAIN,
        suite_name="bio-r13b-independent-runtime",
        objective="controlled success-to-proposal reproduction",
        subject_key=SUBJECT,
        comparison_scope_key=SCOPE,
        config_signature="test_config_v1",
        created_at_utc=STAMP,
    )
    metadata = {"comparison_scope_key": SCOPE, "environment_scan_status": "controlled", "trace_id": f"trace-{trace_suffix}"}
    return [
        ExperimentRun(
            **common, run_id="A-codex", candidate_id="A", candidate_label="codex",
            route=EvaluationRoute.CLOUD, assistant_kind="codex", success=a_success,
            reused_later=True, metrics=ExperimentMetric(total_score=0.85, execution_ms=0),
            metadata={**metadata, "used_fallback": True},
        ),
        ExperimentRun(
            **common, run_id="B-ollama", candidate_id="B", candidate_label="ollama",
            route=EvaluationRoute.LOCAL, assistant_kind="ollama", success=True,
            metrics=ExperimentMetric(total_score=0.84, execution_ms=1000), metadata=metadata,
        ),
        ExperimentRun(
            **common, run_id="C-chatgpt", candidate_id="C", candidate_label="chatgpt",
            route=EvaluationRoute.CLOUD, assistant_kind="chatgpt", success=True,
            metrics=ExperimentMetric(total_score=0.70, execution_ms=0), metadata=metadata,
        ),
    ]


def _case(*, a_success: bool, trace_suffix: str = "base") -> dict[str, object]:
    runs = _runs(a_success=a_success, trace_suffix=trace_suffix)
    with tempfile.TemporaryDirectory(prefix="bio-r13b-") as root:
        # Fresh layer and non-existent persistence path: no residual adaptive state.
        layer = AdaptiveWeightLayer(persistence_path=str(Path(root) / "weights.json"))
        selector = StrategySelector(adaptive_weight_layer=layer)
        recommendation = selector.recommend(domain=DOMAIN, subject_key=SUBJECT, candidate_runs=runs)
        monitor = ToolEvolutionMonitor.__new__(ToolEvolutionMonitor)
        grouped_runs = monitor._grouped_runs(runs)
        profiles = layer.suggest(grouped_runs=grouped_runs)
        ranked = monitor._rank_profiles(grouped_runs=grouped_runs, profiles=profiles)
        proposal = monitor._proposal_for_subject(
            recommendation=recommendation,
            domain=DOMAIN,
            subject_key=SUBJECT,
            grouped_runs=grouped_runs,
            profiles=profiles,
            ranked=ranked,
        )
    rank = {row["assistant_kind"]: index + 1 for index, row in enumerate(ranked)}
    profile = {
        row["assistant_kind"]: {
            "eligible": bool(next(run.success for run in runs if run.assistant_kind == row["assistant_kind"])),
            "weighted_score": row["weighted_score"],
            "adaptive_weight": row["profile"].get("adaptive_weight"),
            "sample_count": row["sample_count"],
        }
        for row in ranked
    }
    return {
        "successful_keys": sorted(run.assistant_kind for run in runs if run.success),
        "profiles": profile,
        "rank": rank,
        "recommendation": {
            "recommended_assistant_kind": recommendation.recommended_assistant_kind,
            "recommended_route": recommendation.recommended_route.value,
            "weighted_score": recommendation.score,
            "adaptive_weight": recommendation.metadata["adaptive_learning_summary"]["adaptive_weight"],
            "sample_count": recommendation.metadata["adaptive_learning_summary"]["sample_count"],
        },
        "baseline": ranked[0]["assistant_kind"],
        "alternative": ranked[1]["assistant_kind"] if len(ranked) > 1 else None,
        "proposal": None if proposal is None else proposal.model_dump(mode="json"),
    }


def reproduce() -> dict[str, object]:
    control = _case(a_success=True)
    treatment = _case(a_success=False)
    negative = _case(a_success=True, trace_suffix="irrelevant-metadata-only")
    assert control["successful_keys"] == ["chatgpt", "codex", "ollama"]
    assert treatment["successful_keys"] == ["chatgpt", "ollama"]
    assert control["recommendation"]["recommended_assistant_kind"] == "codex"
    assert treatment["recommendation"]["recommended_assistant_kind"] == "ollama"
    assert control["baseline"] == "codex" and control["alternative"] == "ollama"
    # Selector excludes failed A from eligibility; monitor retains it in its
    # diagnostic ranking, where its failure penalty moves it below C.
    assert treatment["baseline"] == "ollama" and treatment["alternative"] == "chatgpt"
    assert control["proposal"]["proposal_kind"] == "validate_local_first"
    assert treatment["proposal"] is None
    def decision_projection(case: dict[str, object]) -> dict[str, object]:
        proposal = case["proposal"]
        return {
            "recommendation": case["recommendation"],
            "baseline": case["baseline"],
            "alternative": case["alternative"],
            "proposal": None if proposal is None else {
                "proposal_kind": proposal["proposal_kind"],
                "proposal_key": proposal["proposal_key"],
                "current_assistant_kind": proposal["current_assistant_kind"],
                "candidate_assistant_kind": proposal["candidate_assistant_kind"],
            },
        }
    assert decision_projection(negative) == decision_projection(control)
    return {"control": control, "treatment": treatment, "negative_control": negative}


def test_bio_r13b_independent_runtime_reproduction() -> None:
    reproduce()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("control", "treatment", "negative", "all"), default="all")
    selected = parser.parse_args().case
    if selected == "control":
        result = _case(a_success=True)
    elif selected == "treatment":
        result = _case(a_success=False)
    elif selected == "negative":
        result = _case(a_success=True, trace_suffix="irrelevant-metadata-only")
    else:
        result = reproduce()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
