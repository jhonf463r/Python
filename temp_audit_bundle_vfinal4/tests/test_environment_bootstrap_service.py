from __future__ import annotations

import subprocess
import threading

from iabv_v15.services.environment.environment_bootstrap_service import (
    EnsureResult,
    EnvironmentBootstrapService,
)


class FakeRunner:
    def __init__(self, *, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(list(command))
        return subprocess.CompletedProcess(
            args=command, returncode=self.returncode, stdout=self.stdout, stderr=self.stderr
        )


def _approve_next(service: EnvironmentBootstrapService) -> None:
    def handler(payload: dict) -> None:
        threading.Thread(
            target=lambda: service.approve(payload["id"]), daemon=True
        ).start()

    service.register_prompt_handler(handler)


def _reject_next(service: EnvironmentBootstrapService) -> None:
    def handler(payload: dict) -> None:
        threading.Thread(target=lambda: service.reject(payload["id"]), daemon=True).start()

    service.register_prompt_handler(handler)


def test_ensure_already_present_skips_install() -> None:
    runner = FakeRunner()
    service = EnvironmentBootstrapService(
        runner=runner, finder=lambda pkg, mgr: True
    )
    result = service.ensure("httpx", manager="pip", reason="probe")

    assert isinstance(result, EnsureResult)
    assert result.already_present is True
    assert result.installed is False
    assert runner.calls == []


def test_ensure_approved_triggers_install_and_streams_activity() -> None:
    runner = FakeRunner(returncode=0, stdout="done", stderr="")
    service = EnvironmentBootstrapService(
        runner=runner, finder=lambda pkg, mgr: False
    )
    activity: list[dict] = []
    service.register_activity_handler(activity.append)
    _approve_next(service)

    result = service.ensure("requests", manager="pip", reason="tests", timeout_s=2.0)

    assert result.approved is True
    assert result.installed is True
    assert result.already_present is False
    assert runner.calls and runner.calls[0][-1] == "requests"
    statuses = [item["status"] for item in activity]
    assert "running" in statuses and "completed" in statuses


def test_ensure_rejected_returns_installed_false_and_does_not_run() -> None:
    runner = FakeRunner()
    service = EnvironmentBootstrapService(
        runner=runner, finder=lambda pkg, mgr: False
    )
    _reject_next(service)

    result = service.ensure("requests", manager="pip", reason="tests", timeout_s=2.0)

    assert result.approved is False
    assert result.installed is False
    assert runner.calls == []


def test_ensure_failed_subprocess_marks_not_installed() -> None:
    runner = FakeRunner(returncode=1, stdout="", stderr="boom")
    service = EnvironmentBootstrapService(
        runner=runner, finder=lambda pkg, mgr: False
    )
    activity: list[dict] = []
    service.register_activity_handler(activity.append)
    _approve_next(service)

    result = service.ensure("requests", manager="pip", reason="tests", timeout_s=2.0)

    assert result.approved is True
    assert result.installed is False
    assert "boom" in result.error
    assert any(item["status"] == "failed" for item in activity)


def test_unsupported_manager_returns_error() -> None:
    service = EnvironmentBootstrapService(
        runner=FakeRunner(), finder=lambda pkg, mgr: False
    )
    result = service.ensure("foo", manager="brew", reason="")
    assert result.installed is False
    assert result.approved is False
    assert "brew" in result.error


def test_ensure_without_handler_auto_rejects() -> None:
    runner = FakeRunner()
    service = EnvironmentBootstrapService(
        runner=runner, finder=lambda pkg, mgr: False
    )
    # No prompt handler registrado => no hay manera de aprobar.
    result = service.ensure("requests", manager="pip", reason="tests", timeout_s=0.2)
    assert result.approved is False
    assert runner.calls == []
