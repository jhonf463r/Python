from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from iabv_v15.domain.models import ExperimentCandidate, ExperimentDomain


def _text_similarity(left: str, right: str) -> float:
    left = (left or '').strip().lower()
    right = (right or '').strip().lower()
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(a=left, b=right).ratio()


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in (left or '').lower().replace('/', ' ').replace(':', ' ').split() if len(token) >= 2}
    right_tokens = {token for token in (right or '').lower().replace('/', ' ').replace(':', ' ').split() if len(token) >= 2}
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens.intersection(right_tokens))
    union = len(left_tokens.union(right_tokens))
    return intersection / max(union, 1)


def _jaccard(items_a: list[str], items_b: list[str]) -> float:
    left = {item.strip().lower() for item in items_a if item}
    right = {item.strip().lower() for item in items_b if item}
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / max(len(left.union(right)), 1)


class FormulaTestHarness:
    suite_name = 'formula_test_harness'

    def evaluate(self, *, domain: ExperimentDomain, objective: str, expected: Any, candidate: ExperimentCandidate) -> dict[str, Any]:
        expected_value = expected.get('value') if isinstance(expected, dict) else expected
        expected_text = str(expected.get('expression') or expected.get('text') or expected_value or '') if isinstance(expected, dict) else str(expected or '')
        observed_text = str(candidate.extracted_data.get('expression') or candidate.extracted_data.get('value') or candidate.output_text or '')
        precision = max(_text_similarity(expected_text, observed_text), _token_overlap(expected_text, observed_text))
        if isinstance(expected, dict) and 'truth_label' in expected:
            precision = max(precision, _text_similarity(str(expected.get('truth_label') or ''), observed_text))
        robustness = 0.9 if precision >= 0.95 else 0.7 if precision >= 0.7 else 0.45
        return {
            'suite_name': self.suite_name,
            'precision': precision,
            'robustness': robustness,
            'observed_summary': observed_text[:240],
            'success': precision >= 0.75,
            'metadata': {'domain': domain.value, 'objective': objective},
        }


class OCRBenchmarkSuite:
    suite_name = 'ocr_benchmark_suite'

    def evaluate(self, *, domain: ExperimentDomain, objective: str, expected: Any, candidate: ExperimentCandidate) -> dict[str, Any]:
        expected_text = str(expected.get('text') or expected.get('expected_text') or '') if isinstance(expected, dict) else str(expected or '')
        observed_text = str(candidate.extracted_data.get('recognized_text') or candidate.output_text or '')
        expected_objects = list(expected.get('objects') or []) if isinstance(expected, dict) else []
        observed_objects = list(candidate.extracted_data.get('objects') or [])
        text_score = _text_similarity(expected_text, observed_text) if expected_text or observed_text else 0.0
        object_score = _jaccard(expected_objects, observed_objects) if expected_objects or observed_objects else 0.0
        precision = (text_score + object_score) / (2 if (expected_text or observed_text) and (expected_objects or observed_objects) else 1 or 1)
        if not (expected_text or observed_text) and (expected_objects or observed_objects):
            precision = object_score
        robustness = 0.85 if precision >= 0.9 else 0.65 if precision >= 0.6 else 0.35
        summary_bits = []
        if observed_text:
            summary_bits.append(observed_text[:160])
        if observed_objects:
            summary_bits.append('objetos=' + ', '.join(observed_objects[:6]))
        return {
            'suite_name': self.suite_name,
            'precision': precision,
            'robustness': robustness,
            'observed_summary': ' | '.join(summary_bits)[:240],
            'success': precision >= 0.7,
            'metadata': {'domain': domain.value, 'objective': objective},
        }


class TextUnderstandingSuite:
    suite_name = 'text_understanding_suite'

    def evaluate(self, *, domain: ExperimentDomain, objective: str, expected: Any, candidate: ExperimentCandidate) -> dict[str, Any]:
        expected_text = str(expected.get('text') or expected.get('summary') or expected.get('classification') or '') if isinstance(expected, dict) else str(expected or '')
        observed_text = str(candidate.output_text or candidate.extracted_data.get('summary') or candidate.extracted_data.get('classification') or '')
        precision = max(_text_similarity(expected_text, observed_text), _token_overlap(expected_text, observed_text))
        robustness = 0.88 if precision >= 0.9 else 0.68 if precision >= 0.65 else 0.4
        return {
            'suite_name': self.suite_name,
            'precision': precision,
            'robustness': robustness,
            'observed_summary': observed_text[:240],
            'success': precision >= 0.7,
            'metadata': {'domain': domain.value, 'objective': objective},
        }


class InferenceBenchmarkSuite:
    suite_name = 'inference_benchmark_suite'

    def evaluate(self, *, domain: ExperimentDomain, objective: str, expected: Any, candidate: ExperimentCandidate) -> dict[str, Any]:
        expected_text = str(expected.get('text') or '') if isinstance(expected, dict) else str(expected or '')
        observed_text = str(candidate.output_text or '')
        quality = max(_text_similarity(expected_text, observed_text), _token_overlap(expected_text, observed_text))
        tps = float(candidate.metadata.get('tokens_per_second') or 0.0)
        tps_score = min(tps / 80.0, 1.0) if tps > 0 else 0.0
        precision = quality * 0.6 + tps_score * 0.4
        robustness = 0.9 if precision >= 0.7 else 0.6 if precision >= 0.4 else 0.3
        return {
            'suite_name': self.suite_name,
            'precision': precision,
            'robustness': robustness,
            'observed_summary': observed_text[:240],
            'success': tps > 5.0 and quality >= 0.15,
            'metadata': {
                'domain': domain.value,
                'objective': objective,
                'tokens_per_second': tps,
                'quality_score': round(quality, 4),
            },
        }


class CodeUnderstandingSuite:
    suite_name = 'code_understanding_suite'

    def evaluate(self, *, domain: ExperimentDomain, objective: str, expected: Any, candidate: ExperimentCandidate) -> dict[str, Any]:
        if isinstance(expected, dict):
            expected_text = str(expected.get('text') or expected.get('expected_answer') or expected.get('expected_code') or '')
            required_tokens = [str(item) for item in expected.get('required_tokens') or []]
        else:
            expected_text = str(expected or '')
            required_tokens = []
        observed_text = str(candidate.output_text or candidate.extracted_data.get('answer') or candidate.extracted_data.get('code') or '')
        precision = max(_text_similarity(expected_text, observed_text), _token_overlap(expected_text, observed_text))
        if required_tokens:
            observed_lower = observed_text.lower()
            required_score = sum(1 for token in required_tokens if token.lower() in observed_lower) / max(len(required_tokens), 1)
            precision = max(precision, required_score)
        robustness = 0.9 if precision >= 0.9 else 0.7 if precision >= 0.6 else 0.35
        return {
            'suite_name': self.suite_name,
            'precision': precision,
            'robustness': robustness,
            'observed_summary': observed_text[:240],
            'success': precision >= 0.68,
            'metadata': {'domain': domain.value, 'objective': objective},
        }
