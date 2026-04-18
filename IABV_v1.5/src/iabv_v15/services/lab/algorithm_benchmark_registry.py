from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import ExperimentCandidate, ExperimentDomain
from iabv_v15.services.lab.suites import CodeUnderstandingSuite, FormulaTestHarness, OCRBenchmarkSuite, TextUnderstandingSuite


class AlgorithmBenchmarkRegistry:
    def __init__(self) -> None:
        self.formula_harness = FormulaTestHarness()
        self.ocr_suite = OCRBenchmarkSuite()
        self.text_suite = TextUnderstandingSuite()
        self.code_suite = CodeUnderstandingSuite()

    def evaluate(self, *, domain: ExperimentDomain, objective: str, expected: Any, candidate: ExperimentCandidate) -> dict[str, Any]:
        if domain in {ExperimentDomain.EQUATION, ExperimentDomain.FORMULA, ExperimentDomain.SYMBOLIC_LOGIC}:
            return self.formula_harness.evaluate(domain=domain, objective=objective, expected=expected, candidate=candidate)
        if domain in {ExperimentDomain.OCR, ExperimentDomain.OBJECT_DETECTION}:
            return self.ocr_suite.evaluate(domain=domain, objective=objective, expected=expected, candidate=candidate)
        if domain == ExperimentDomain.LANGUAGE:
            return self.text_suite.evaluate(domain=domain, objective=objective, expected=expected, candidate=candidate)
        return self.code_suite.evaluate(domain=domain, objective=objective, expected=expected, candidate=candidate)
