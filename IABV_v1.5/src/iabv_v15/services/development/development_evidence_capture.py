"""Capture durable, deterministic evidence after a real self-update commit."""
from __future__ import annotations

import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    CodexAcceptanceCriteria, CodexTaskSpec, DevelopmentAuditCriterion,
    DevelopmentAuditResult, DevelopmentAuditVerdict, DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus, DevelopmentTestResult, DevelopmentTestStatus,
    EvidenceKind, EvidenceRef, RunStatus,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.development.development_outcome_attribution_builder import DevelopmentOutcomeAttributionBuilder


class DevelopmentEvidenceCapture:
    """The narrow post-commit evidence bridge for the existing self-update tool."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root)
        self.storage = ArtifactStorage(str(self.workspace_root / "data" / "evolution" / "development_evidence"))

    def capture(
        self, *, task_spec: CodexTaskSpec, base_commit: str, result_commit: str,
        push_succeeded: bool | None, push_detail: str = "",
    ) -> dict[str, Any]:
        started = datetime.now(timezone.utc)
        command = " && ".join(task_spec.test_plan.commands) if task_spec.test_plan and task_spec.test_plan.commands else ""
        test = self._run_test(command, result_commit)
        changed_files = self._git_lines(["diff", "--name-only", base_commit, result_commit])
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        evidence = DevelopmentExecutionEvidence(
            repository=self._git_one(["config", "--get", "remote.origin.url"]) or str(self.workspace_root),
            base_commit=base_commit, result_commit=result_commit, changed_files=changed_files,
            started_at_utc=started,
            completed_at_utc=started + timedelta(seconds=max(0.0, elapsed)),
            duration_seconds=max(0.0, elapsed),
            execution_status=(DevelopmentExecutionStatus.COMPLETED if test.status == DevelopmentTestStatus.PASSED and push_succeeded is not False else DevelopmentExecutionStatus.FAILED),
            test_result_id=test.test_result_id,
            evidence_refs=[EvidenceRef(kind=EvidenceKind.DEVELOPMENT_TEST, label="real subprocess test", ref_id=test.test_result_id)],
            metadata={"task_spec_id": task_spec.codex_task_id, "push_succeeded": push_succeeded, "push_detail": push_detail},
        )
        criteria = self._evaluate(task_spec.acceptance_criteria, test, result_commit, changed_files, push_succeeded)
        required = [item for item in criteria if item.metadata.get("required", True)]
        verdict = DevelopmentAuditVerdict.PASS if required and all(item.status == "satisfied" for item in required) else DevelopmentAuditVerdict.FAIL if required else DevelopmentAuditVerdict.INCONCLUSIVE
        audit = DevelopmentAuditResult(
            execution_evidence_id=evidence.evidence_id, verdict=verdict, auditor_id="deterministic_development_evidence",
            criteria=criteria,
            evidence_refs=[EvidenceRef(kind=EvidenceKind.DEVELOPMENT_EXECUTION, label="real commit execution", ref_id=evidence.evidence_id)],
        )
        outcome_status = RunStatus.SUCCESS if test.status == DevelopmentTestStatus.PASSED and push_succeeded is not False else (RunStatus.PARTIAL if test.status == DevelopmentTestStatus.PASSED else RunStatus.FAILED)
        outcome = DevelopmentOutcomeAttributionBuilder().build(outcome_status=outcome_status, audit_result=audit, execution_evidence=evidence, test_result=test)
        payload = {"task_spec": task_spec.model_dump(mode="json"), "test_result": test.model_dump(mode="json"), "execution_evidence": evidence.model_dump(mode="json"), "audit_result": audit.model_dump(mode="json"), "task_outcome": outcome.model_dump(mode="json")}
        path = self.storage.save_json_atomic(f"attempts/{evidence.evidence_id}.json", payload)
        return {"path": path, "test_result": test, "execution_evidence": evidence, "audit_result": audit, "task_outcome": outcome}

    def _run_test(self, command: str, commit: str) -> DevelopmentTestResult:
        if not command:
            return DevelopmentTestResult(status=DevelopmentTestStatus.NOT_RUN, command="", commit=commit)
        # Specs commonly name pytest without its console-script path.  Execute
        # that exact test plan through the interpreter that hosts IABV instead
        # of depending on PATH; arguments and the requested test remain intact.
        command = re.sub(
            r"(?<!\S)pytest(?=\s|$)",
            lambda _match: f'"{sys.executable}" -m pytest',
            command,
        )
        began = time.monotonic()
        try:
            result = subprocess.run(command, cwd=self.workspace_root, shell=True, text=True, capture_output=True, timeout=300)
            status = DevelopmentTestStatus.PASSED if result.returncode == 0 else DevelopmentTestStatus.FAILED
            counts = self._counts(result.stdout + "\n" + result.stderr)
            return DevelopmentTestResult(status=status, command=command, exit_code=result.returncode, duration_seconds=time.monotonic()-began, stdout=result.stdout, stderr=result.stderr, commit=commit, **counts)
        except subprocess.TimeoutExpired as exc:
            return DevelopmentTestResult(status=DevelopmentTestStatus.TIMEOUT, command=command, duration_seconds=time.monotonic()-began, stdout=exc.stdout or "", stderr=exc.stderr or "", commit=commit)
        except Exception as exc:
            return DevelopmentTestResult(status=DevelopmentTestStatus.ERROR, command=command, duration_seconds=time.monotonic()-began, stderr=str(exc), commit=commit)

    @staticmethod
    def _counts(output: str) -> dict[str, int | None]:
        match = re.search(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) errors?)?(?:, (\d+) skipped)?", output)
        if not match: return {"test_count": None, "passed_count": None, "failed_count": None, "error_count": None, "skipped_count": None}
        values = [int(value or 0) for value in match.groups()]
        return {"test_count": sum(values), "passed_count": values[0], "failed_count": values[1], "error_count": values[2], "skipped_count": values[3]}

    def _evaluate(self, criteria: list[CodexAcceptanceCriteria], test: DevelopmentTestResult, result_commit: str, changed_files: list[str], push_succeeded: bool | None) -> list[DevelopmentAuditCriterion]:
        observed = {"tests_passed": test.status == DevelopmentTestStatus.PASSED, "commit_created": bool(result_commit), "push_succeeded": push_succeeded is True}
        evaluated = []
        for criterion in criteria:
            key = str(criterion.metadata.get("observation") or "")
            expected = criterion.metadata.get("expected", True)
            value = (changed_files if key == "changed_files" else observed.get(key))
            satisfied = bool(value) == bool(expected) if key != "changed_files" else bool(value) == bool(expected)
            evaluated.append(DevelopmentAuditCriterion(criterion_id=criterion.criterion_id, name=criterion.description, status="satisfied" if key and satisfied else "not_satisfied", description=criterion.description, metadata={"required": criterion.required, "observation": key, "observed": value, "expected": expected}))
        return evaluated

    def _git_lines(self, args: list[str]) -> list[str]:
        result = subprocess.run(["git", *args], cwd=self.workspace_root, text=True, capture_output=True, check=False)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _git_one(self, args: list[str]) -> str:
        values = self._git_lines(args)
        return values[0] if values else ""
