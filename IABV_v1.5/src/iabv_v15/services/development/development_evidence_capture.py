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
        criteria = self._evaluate(task_spec.acceptance_criteria, test, base_commit, result_commit, changed_files, push_succeeded)
        required = [item for item in criteria if item.metadata.get("required", True)]
        # Check for unobservable required criteria
        unobservable_required = any(item.metadata.get("reason") == "observation_not_supported" for item in required)
        # Separate execution and objective criteria using the canonical criterion_type field
        objective_criteria = [item for item in criteria if item.criterion_type == "objective"]
        required_objective = [item for item in objective_criteria if item.metadata.get("required", True)]
        # CRITICAL: If no objective criteria exist, goal is UNPROVEN and cannot produce SUCCESS
        # Mechanical criteria (tests_passed, commit_created, etc.) are NOT sufficient to prove the goal
        has_objective_criteria = len(objective_criteria) > 0
        objective_satisfied = has_objective_criteria and all(item.status == "satisfied" for item in required_objective)
        # Verdict logic:
        # - PASS only if all required criteria satisfied AND objective criteria exist AND objective satisfied
        # - FAIL if any required criterion not satisfied OR objective criteria missing OR objective not satisfied
        # - INCONCLUSIVE if no required criteria
        if required and all(item.status == "satisfied" for item in required) and not unobservable_required and has_objective_criteria and objective_satisfied:
            verdict = DevelopmentAuditVerdict.PASS
        elif required and (not all(item.status == "satisfied" for item in required) or unobservable_required):
            verdict = DevelopmentAuditVerdict.FAIL
        elif not has_objective_criteria:
            # Goal is UNPROVEN - no objective criteria to verify it
            verdict = DevelopmentAuditVerdict.INCONCLUSIVE
        else:
            verdict = DevelopmentAuditVerdict.INCONCLUSIVE
        audit = DevelopmentAuditResult(
            execution_evidence_id=evidence.evidence_id, verdict=verdict, auditor_id="deterministic_development_evidence",
            criteria=criteria,
            evidence_refs=[EvidenceRef(kind=EvidenceKind.DEVELOPMENT_EXECUTION, label="real commit execution", ref_id=evidence.evidence_id)],
        )
        # Audit verdict has authority over objective outcome.
        # SUCCESS only if audit PASS, test passed, and push succeeded.
        # FAIL if audit FAIL, regardless of test/push state.
        # PARTIAL if audit INCONCLUSIVE or push failed but test passed.
        if verdict == DevelopmentAuditVerdict.PASS and test.status == DevelopmentTestStatus.PASSED and push_succeeded is not False:
            outcome_status = RunStatus.SUCCESS
        elif verdict == DevelopmentAuditVerdict.FAIL:
            outcome_status = RunStatus.FAILED
        elif test.status == DevelopmentTestStatus.PASSED and push_succeeded is False:
            outcome_status = RunStatus.PARTIAL
        else:
            outcome_status = RunStatus.FAILED
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
        # Idempotent: only normalize bare "pytest", not "python -m pytest" or similar.
        # Use deterministic parsing to avoid double normalization.
        
        # Check if command already contains a python interpreter with -m pytest
        # Patterns to match: "python -m pytest", "python3 -m pytest", "python.exe -m pytest", "/path/to/python -m pytest"
        import shlex
        try:
            # Parse the command to get the first token
            parts = shlex.split(command, posix=False)
            if parts and len(parts) >= 1:
                # Check if it's already a python invocation with -m pytest
                first = parts[0].lower()
                if len(parts) >= 3 and ("python" in first or first.endswith(".exe")) and parts[1] == "-m" and parts[2].lower() == "pytest":
                    # Already normalized, do nothing
                    pass
                elif first == "pytest":
                    # Bare pytest, normalize it
                    parts[0] = f'"{sys.executable}"'
                    parts.insert(1, "-m")
                    parts.insert(2, "pytest")
                    command = " ".join(parts)
        except Exception:
            # If parsing fails, fall back to simple check
            if "pytest" in command and "python -m pytest" not in command and "python3 -m pytest" not in command:
                command = re.sub(r"\bpytest\b", f'"{sys.executable}" -m pytest', command)
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

    def _evaluate(self, criteria: list[CodexAcceptanceCriteria], test: DevelopmentTestResult, base_commit: str, result_commit: str, changed_files: list[str], push_succeeded: bool | None) -> list[DevelopmentAuditCriterion]:
        # Closed-world set of observations that can be objectively verified.
        # Unknown observations are explicitly not_satisfied, never satisfied by absence.
        SUPPORTED_OBSERVATIONS = {"tests_passed", "commit_created", "push_succeeded", "changed_files_nonempty", "file_content_changed"}
        observed = {
            "tests_passed": test.status == DevelopmentTestStatus.PASSED,
            "commit_created": bool(result_commit),
            "push_succeeded": push_succeeded is True,
            "changed_files_nonempty": bool(changed_files),
        }
        evaluated = []
        for criterion in criteria:
            key = str(criterion.metadata.get("observation") or "")
            expected = criterion.metadata.get("expected", True)
            target_file = criterion.metadata.get("target_file")
            
            # Special handling for file_content_changed observation
            if key == "file_content_changed" and target_file:
                # Use the deterministic verifier that compares base vs result content
                content_changed = self._verify_file_content_changed(base_commit, result_commit, target_file)
                value = content_changed
            elif key in observed:
                value = observed.get(key)
            else:
                # Unknown observation: never satisfied
                evaluated.append(
                    DevelopmentAuditCriterion(
                        criterion_id=criterion.criterion_id,
                        name=criterion.description,
                        status="not_satisfied",
                        description=criterion.description,
                        criterion_type=criterion.criterion_type,
                        metadata={
                            "required": criterion.required,
                            "observation": key,
                            "observed": None,
                            "expected": expected,
                            "reason": "observation_not_supported",
                            "verifier": criterion.metadata.get("verifier"),
                            "target_file": target_file,
                        },
                    )
                )
                continue
            
            # Explicit comparison: None/unknown never satisfies, even if expected=False
            if value is None:
                satisfied = False
            else:
                satisfied = bool(value) == bool(expected)
            
            evaluated.append(
                DevelopmentAuditCriterion(
                    criterion_id=criterion.criterion_id,
                    name=criterion.description,
                    status="satisfied" if satisfied else "not_satisfied",
                    description=criterion.description,
                    criterion_type=criterion.criterion_type,
                    metadata={
                        "required": criterion.required,
                        "observation": key,
                        "observed": value,
                        "expected": expected,
                        "verifier": criterion.metadata.get("verifier"),
                        "target_file": target_file,
                    },
                )
            )
        return evaluated

    def _git_lines(self, args: list[str]) -> list[str]:
        result = subprocess.run(["git", *args], cwd=self.workspace_root, text=True, capture_output=True, check=False)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _git_one(self, args: list[str]) -> str:
        values = self._git_lines(args)
        return values[0] if values else ""

    def _git_show_file(self, commit: str, file_path: str) -> str:
        """Read file content at a specific commit using git show."""
        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{file_path}"],
                cwd=self.workspace_root,
                text=True,
                capture_output=True,
                check=False,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""

    def _verify_file_content_changed(self, base_commit: str, result_commit: str, target_file: str) -> bool:
        """Deterministically verify that file content actually changed between commits.
        
        This verifier compares the actual base and result content using git show.
        It distinguishes between:
        - Real content changes (base != result)
        - Comment-only changes (content semantically identical)
        - Whitespace/formatting changes (can be filtered)
        
        Returns True only if the actual content meaningfully changed.
        """
        base_content = self._git_show_file(base_commit, target_file)
        result_content = self._git_show_file(result_commit, target_file)
        
        # If either file doesn't exist, consider it a change
        if not base_content or not result_content:
            return base_content != result_content
        
        # Normalize whitespace for comparison (ignore formatting-only changes)
        # But preserve actual code structure
        base_normalized = "\n".join(line.strip() for line in base_content.splitlines() if line.strip())
        result_normalized = "\n".join(line.strip() for line in result_content.splitlines() if line.strip())
        
        # Remove comment-only lines for comparison
        # This is a simple heuristic: remove lines that are only comments
        # A more sophisticated approach would use AST parsing, but that's overkill for this verifier
        import re
        def remove_comments(code: str) -> str:
            # Remove Python-style comments (lines starting with #)
            lines = []
            for line in code.splitlines():
                # Remove inline comments
                line = re.sub(r"#.*$", "", line).strip()
                if line:
                    lines.append(line)
            return "\n".join(lines)
        
        base_no_comments = remove_comments(base_normalized)
        result_no_comments = remove_comments(result_normalized)
        
        # Content changed only if the non-comment, normalized content differs
        return base_no_comments != result_no_comments
