"""EnvironmentBootstrapService: detecta e instala dependencias faltantes.

Flujo:
    1. ensure(package, manager) detecta si ya esta presente (find_spec o which).
    2. Si falta, emite missingDependencyRequested con id, package, manager, reason.
    3. La UI responde via approve(id) o reject(id).
    4. Al aprobar, se ejecuta la instalacion via subprocess y se streamea el
       progreso por backgroundActivityChanged (text, progress, status, details).

Devuelve un EnsureResult describiendo el estado final.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Callable, Optional


PromptHandler = Callable[[dict], None]
ActivityHandler = Callable[[dict], None]
Runner = Callable[[list[str]], subprocess.CompletedProcess]
Finder = Callable[[str, str], bool]


SUPPORTED_MANAGERS = frozenset({"pip", "apt", "playwright", "npm"})


@dataclass(frozen=True)
class EnsureResult:
    package: str
    manager: str
    already_present: bool
    approved: bool
    installed: bool
    output: str = ""
    error: str = ""


class EnvironmentBootstrapService:
    def __init__(
        self,
        *,
        runner: Runner | None = None,
        finder: Finder | None = None,
        which: Callable[[str], str | None] | None = None,
    ) -> None:
        self._runner: Runner = runner or self._default_runner
        self._finder: Finder | None = finder
        self._which = which or shutil.which
        self._prompt_handler: Optional[PromptHandler] = None
        self._activity_handler: Optional[ActivityHandler] = None
        self._lock = threading.RLock()
        self._pending: dict[str, Future[bool]] = {}

    # ---- public API -------------------------------------------------

    def register_prompt_handler(self, handler: PromptHandler) -> None:
        with self._lock:
            self._prompt_handler = handler

    def register_activity_handler(self, handler: ActivityHandler) -> None:
        with self._lock:
            self._activity_handler = handler

    def ensure(
        self,
        package: str,
        manager: str = "pip",
        reason: str = "",
        timeout_s: float | None = None,
    ) -> EnsureResult:
        if manager not in SUPPORTED_MANAGERS:
            return EnsureResult(
                package=package,
                manager=manager,
                already_present=False,
                approved=False,
                installed=False,
                error=f"Unsupported manager: {manager}",
            )
        if self._is_present(package, manager):
            return EnsureResult(
                package=package,
                manager=manager,
                already_present=True,
                approved=True,
                installed=False,
            )
        approved = self._request_approval(package, manager, reason, timeout_s)
        if not approved:
            return EnsureResult(
                package=package,
                manager=manager,
                already_present=False,
                approved=False,
                installed=False,
            )
        return self._install(package, manager)

    def approve(self, request_id: str) -> bool:
        with self._lock:
            future = self._pending.pop(request_id, None)
        if future is None or future.done():
            return False
        future.set_result(True)
        return True

    def reject(self, request_id: str) -> bool:
        with self._lock:
            future = self._pending.pop(request_id, None)
        if future is None or future.done():
            return False
        future.set_result(False)
        return True

    def pending_ids(self) -> list[str]:
        with self._lock:
            return list(self._pending.keys())

    # ---- internals --------------------------------------------------

    def _is_present(self, package: str, manager: str) -> bool:
        if self._finder is not None:
            return bool(self._finder(package, manager))
        if manager == "pip":
            return importlib.util.find_spec(package) is not None
        if manager == "playwright":
            return importlib.util.find_spec("playwright") is not None
        if manager in {"apt", "npm"}:
            return self._which(package) is not None
        return False

    def _request_approval(
        self,
        package: str,
        manager: str,
        reason: str,
        timeout_s: float | None,
    ) -> bool:
        request_id = uuid.uuid4().hex
        future: Future[bool] = Future()
        with self._lock:
            self._pending[request_id] = future
            handler = self._prompt_handler
        payload = {
            "id": request_id,
            "package_name": package,
            "manager": manager,
            "reason": reason or "",
        }
        if handler is None:
            with self._lock:
                self._pending.pop(request_id, None)
            return False
        handler(payload)
        try:
            if timeout_s is None:
                return bool(future.result())
            return bool(future.result(timeout=timeout_s))
        except FutureTimeoutError:
            with self._lock:
                self._pending.pop(request_id, None)
            return False

    def _install(self, package: str, manager: str) -> EnsureResult:
        command = self._build_command(package, manager)
        self._stream_activity(
            text=f"Instalando {package} ({manager})",
            progress=0.0,
            status="running",
            details=[" ".join(command)],
        )
        try:
            completed = self._runner(command)
        except Exception as exc:  # pragma: no cover - runner error path tested via mock
            self._stream_activity(
                text=f"Fallo al instalar {package}",
                progress=100.0,
                status="failed",
                details=[str(exc)],
            )
            return EnsureResult(
                package=package,
                manager=manager,
                already_present=False,
                approved=True,
                installed=False,
                error=str(exc),
            )
        stdout = str(getattr(completed, "stdout", "") or "").strip()
        stderr = str(getattr(completed, "stderr", "") or "").strip()
        returncode = int(getattr(completed, "returncode", 1))
        if returncode == 0:
            self._stream_activity(
                text=f"{package} instalado",
                progress=100.0,
                status="completed",
                details=[stdout[-500:]] if stdout else [],
            )
            return EnsureResult(
                package=package,
                manager=manager,
                already_present=False,
                approved=True,
                installed=True,
                output=stdout,
            )
        self._stream_activity(
            text=f"Fallo al instalar {package}",
            progress=100.0,
            status="failed",
            details=[stderr[-500:]] if stderr else [],
        )
        return EnsureResult(
            package=package,
            manager=manager,
            already_present=False,
            approved=True,
            installed=False,
            output=stdout,
            error=stderr or f"exit code {returncode}",
        )

    def _build_command(self, package: str, manager: str) -> list[str]:
        if manager == "pip":
            return [sys.executable, "-m", "pip", "install", package]
        if manager == "apt":
            return ["sudo", "apt-get", "install", "-y", package]
        if manager == "npm":
            return ["npm", "install", "-g", package]
        if manager == "playwright":
            return [sys.executable, "-m", "playwright", "install", package]
        return []

    def _default_runner(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603 - comando construido a partir de parametros controlados
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    def _stream_activity(
        self,
        *,
        text: str,
        progress: float,
        status: str,
        details: list[str],
    ) -> None:
        with self._lock:
            handler = self._activity_handler
        if handler is None:
            return
        handler(
            {
                "text": text,
                "progress": float(progress),
                "status": status,
                "details": list(details),
            }
        )
