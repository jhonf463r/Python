"""Scientific proxy calculations for measurable approximations of theoretical concepts.

Each function computes a proxy value from data already available in the
system (adapter results, experiment runs, telemetry).  No external
dependencies — only stdlib math/zlib.
"""

from __future__ import annotations

import math
import zlib
from typing import Any


def compression_ratio(text: str) -> float:
    """Proxy for Kolmogorov complexity via zlib compression.

    Returns ``len(compressed) / len(original)``.  Lower values indicate
    more compressible (and therefore structurally simpler) output.
    Returns 1.0 for empty input.
    """
    if not text:
        return 1.0
    raw = text.encode('utf-8', errors='replace')
    compressed = zlib.compress(raw, level=6)
    return round(len(compressed) / max(len(raw), 1), 4)


def description_length_proxy(text: str) -> int:
    """MDL proxy: compressed size in bytes of the output.

    Approximates ``L_datos`` — how many bits are needed to describe the
    output given the implicit model (zlib dictionary).
    """
    if not text:
        return 0
    return len(zlib.compress(text.encode('utf-8', errors='replace'), level=6))


def entropy_proxy(text: str) -> float:
    """Shannon entropy of the byte distribution of the text.

    Higher entropy indicates more uniform (less predictable) byte
    distribution.  Returns 0.0 for empty input.
    """
    if not text:
        return 0.0
    raw = text.encode('utf-8', errors='replace')
    length = len(raw)
    freq: dict[int, int] = {}
    for byte in raw:
        freq[byte] = freq.get(byte, 0) + 1
    h = 0.0
    for count in freq.values():
        p = count / length
        if p > 0:
            h -= p * math.log2(p)
    return round(h, 4)


def inference_depth_proxy(text: str) -> int:
    """Proxy for reasoning depth: count of logical step markers.

    Counts sentence-ending punctuation, numbered list items, and
    common multi-step markers (then, therefore, because, so, next,
    finally, step) as indicators of sequential reasoning.
    """
    if not text:
        return 0
    lower = text.lower()
    markers = ['.', '?', '!']
    step_words = ['then ', 'therefore ', 'because ', ' so ', 'next ', 'finally ', 'step ']
    count = sum(lower.count(m) for m in markers)
    count += sum(lower.count(w) for w in step_words)
    # Numbered steps: "1.", "2.", etc.
    import re
    count += len(re.findall(r'\b\d+\.', text))
    return max(count, 0)


def step_count_proxy(text: str) -> int:
    """Count explicit reasoning steps (paragraphs or numbered items)."""
    if not text:
        return 0
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return len(lines)


def reuse_score_from_runs(
    runs: list[dict[str, Any]],
    key: str = 'assistant_kind',
) -> float:
    """Measure how much the system reuses a specific route/assistant.

    Returns ratio of the most-used value of ``key`` across runs.
    1.0 = always the same; near 0 = high diversity.
    """
    if not runs:
        return 0.0
    values = [str(r.get(key) or '') for r in runs if r.get(key)]
    if not values:
        return 0.0
    from collections import Counter
    most_common_count = Counter(values).most_common(1)[0][1]
    return round(most_common_count / len(values), 4)


def stability_score_from_runs(
    scores: list[float],
) -> float:
    """Stability proxy: 1 - coefficient of variation of scores.

    Near 1.0 = very stable outcomes; near 0 = highly variable.
    """
    if len(scores) < 2:
        return 1.0
    mean = sum(scores) / len(scores)
    if mean == 0:
        return 0.0
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = math.sqrt(variance)
    cv = std / abs(mean)
    return round(max(0.0, 1.0 - cv), 4)


def calibration_error(
    predicted_confidences: list[float],
    actual_successes: list[bool],
    n_bins: int = 5,
) -> float:
    """Expected Calibration Error (ECE).

    Bins predictions by confidence, computes |avg_confidence - accuracy|
    per bin, weighted by bin population.
    """
    if not predicted_confidences or len(predicted_confidences) != len(actual_successes):
        return 0.0
    n = len(predicted_confidences)
    bins: dict[int, list[tuple[float, bool]]] = {}
    for conf, success in zip(predicted_confidences, actual_successes):
        b = min(int(conf * n_bins), n_bins - 1)
        bins.setdefault(b, []).append((conf, success))
    ece = 0.0
    for entries in bins.values():
        avg_conf = sum(c for c, _ in entries) / len(entries)
        accuracy = sum(1 for _, s in entries if s) / len(entries)
        ece += len(entries) / n * abs(avg_conf - accuracy)
    return round(ece, 4)


def nonlinearity_indicator(
    recent_scores: list[float],
    window: int = 5,
) -> float:
    """Detect non-linear jumps in performance.

    Compares the average of the last ``window`` scores to the average
    of the preceding ``window`` scores.  Returns the ratio of improvement.
    Values > 1.5 suggest a potential phase-transition-like jump.
    Values near 1.0 indicate smooth progression.
    """
    if len(recent_scores) < window * 2:
        return 1.0
    older = recent_scores[-(window * 2):-window]
    newer = recent_scores[-window:]
    avg_old = sum(older) / len(older) if older else 0.001
    avg_new = sum(newer) / len(newer) if newer else 0.001
    if avg_old <= 0:
        avg_old = 0.001
    return round(avg_new / avg_old, 4)


def multi_step_success_rate(
    outcomes: list[dict[str, Any]],
    depth_key: str = 'inference_depth_proxy',
    success_key: str = 'success',
    min_depth: int = 3,
) -> float:
    """Success rate for multi-step tasks (depth >= min_depth)."""
    multi = [o for o in outcomes if (o.get(depth_key) or 0) >= min_depth]
    if not multi:
        return 0.0
    successes = sum(1 for o in multi if o.get(success_key))
    return round(successes / len(multi), 4)


def uncertainty_proxy_from_scores(scores: list[float]) -> float:
    """Uncertainty proxy: standard deviation of recent scores.

    Higher = more uncertain about outcomes.
    """
    if len(scores) < 2:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    return round(math.sqrt(variance), 4)


def worker_recommendation(
    *,
    success: bool,
    budget_state: str,
    handoff_required: bool,
    correction_rounds: int,
    reuse_score: float,
    stability_score: float,
) -> str:
    """Recommend next action based on observable variables.

    Returns one of: continue_with_same_worker, switch_worker,
    checkpoint_and_resume, reject_and_stop, promote_to_recommendation.
    """
    if budget_state in ('exhausted', 'quota_exceeded', 'timeout'):
        return 'checkpoint_and_resume'
    if handoff_required:
        return 'checkpoint_and_resume'
    if not success and correction_rounds >= 3:
        return 'switch_worker'
    if not success and correction_rounds >= 1:
        return 'reanalyze'
    if not success:
        return 'reject_and_stop'
    if success and stability_score >= 0.7 and reuse_score >= 0.5:
        return 'promote_to_recommendation'
    return 'continue_with_same_worker'
