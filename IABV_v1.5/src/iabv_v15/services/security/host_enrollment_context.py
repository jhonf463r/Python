"""Read-only, host-composed local context for the bounded G1 enrollment.

This evidence is descriptive only. It does not establish an Owner assertion,
approve a workspace root, grant a capability, or enable enrollment.
"""
from __future__ import annotations

import ctypes
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


_SID_PATTERN = re.compile(r"^S-1-(?:[0-9]+-){1,14}[0-9]+$", re.IGNORECASE)


class ContextStatus(str, Enum):
    OBSERVED = "OBSERVED_LOCAL_CONTEXT"
    DENIED = "LOCAL_CONTEXT_DENIED"


class ProcessIdentitySource(str, Enum):
    WINDOWS_PROCESS_TOKEN_AND_IMAGE_API = "WINDOWS_PROCESS_TOKEN_AND_IMAGE_API"


class WorkspaceRootSource(str, Enum):
    APP_BOOTSTRAP_EXPLICIT_ARGUMENT = "APP_BOOTSTRAP_EXPLICIT_ARGUMENT"
    CONFIG_DEFAULTED_FROM_CWD = "CONFIG_DEFAULTED_FROM_CWD"


@dataclass(frozen=True)
class ProcessIdentityEvidence:
    pid: int | None
    image_path: str | None
    effective_user_sid: str | None
    source: ProcessIdentitySource


@dataclass(frozen=True)
class HostEnrollmentContext:
    status: ContextStatus
    process_identity: ProcessIdentityEvidence
    workspace_root_candidate: str | None
    workspace_root_source: WorkspaceRootSource
    integrity_errors: tuple[str, ...]

    @property
    def is_complete_observation(self) -> bool:
        return self.status is ContextStatus.OBSERVED and not self.integrity_errors


@dataclass(frozen=True)
class _NativeProcessResult:
    pid: int | None
    image_path: str | None
    sid: str | None
    errors: tuple[str, ...]


def _read_windows_process_identity() -> _NativeProcessResult:
    """Read the effective process token and image identity using Win32 APIs."""
    if os.name != "nt":
        return _NativeProcessResult(None, None, None, ("WINDOWS_API_UNAVAILABLE",))

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    except Exception:
        return _NativeProcessResult(None, None, None, ("WINDOWS_API_UNAVAILABLE",))

    errors: list[str] = []
    pid: int | None = None
    image_path: str | None = None
    sid: str | None = None
    token = ctypes.c_void_p()
    process = kernel32.GetCurrentProcess()

    try:
        try:
            kernel32.GetCurrentProcessId.restype = ctypes.c_ulong
            raw_pid = int(kernel32.GetCurrentProcessId())
            if raw_pid > 0:
                pid = raw_pid
            else:
                errors.append("PROCESS_ID_INCOMPLETE")
        except Exception:
            errors.append("PROCESS_ID_INCOMPLETE")

        try:
            capacity = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(capacity.value)
            kernel32.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
            if kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(capacity)):
                candidate = buffer.value
                if candidate and os.path.isabs(candidate):
                    image_path = candidate
                else:
                    errors.append("PROCESS_IMAGE_PATH_INVALID")
            else:
                errors.append("PROCESS_IMAGE_PATH_INCOMPLETE")
        except Exception:
            errors.append("PROCESS_IMAGE_PATH_INCOMPLETE")

        try:
            advapi32.OpenProcessToken.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p)]
            advapi32.OpenProcessToken.restype = ctypes.c_int
            if not advapi32.OpenProcessToken(process, 0x0008, ctypes.byref(token)):
                errors.append("PROCESS_TOKEN_UNREADABLE")
            else:
                required = ctypes.c_ulong(0)
                advapi32.GetTokenInformation.argtypes = [
                    ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
                    ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                ]
                advapi32.GetTokenInformation.restype = ctypes.c_int
                advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
                if required.value <= 0 or required.value > 1024 * 1024:
                    errors.append("PROCESS_TOKEN_UNREADABLE")
                else:
                    token_buffer = ctypes.create_string_buffer(required.value)
                    if not advapi32.GetTokenInformation(
                        token, 1, token_buffer, required.value, ctypes.byref(required),
                    ):
                        errors.append("PROCESS_TOKEN_UNREADABLE")
                    else:
                        class _SidAndAttributes(ctypes.Structure):
                            _fields_ = [("sid", ctypes.c_void_p), ("attributes", ctypes.c_ulong)]

                        class _TokenUser(ctypes.Structure):
                            _fields_ = [("user", _SidAndAttributes)]

                        user = ctypes.cast(token_buffer, ctypes.POINTER(_TokenUser)).contents
                        advapi32.IsValidSid.argtypes = [ctypes.c_void_p]
                        advapi32.IsValidSid.restype = ctypes.c_int
                        sid_text = ctypes.c_wchar_p()
                        advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
                        advapi32.ConvertSidToStringSidW.restype = ctypes.c_int
                        if not user.user.sid or not advapi32.IsValidSid(user.user.sid):
                            errors.append("PROCESS_SID_INVALID")
                        elif not advapi32.ConvertSidToStringSidW(user.user.sid, ctypes.byref(sid_text)):
                            errors.append("PROCESS_TOKEN_UNREADABLE")
                        else:
                            try:
                                candidate_sid = sid_text.value or ""
                                if _SID_PATTERN.fullmatch(candidate_sid):
                                    sid = candidate_sid
                                else:
                                    errors.append("PROCESS_SID_INVALID")
                            finally:
                                kernel32.LocalFree.argtypes = [ctypes.c_void_p]
                                kernel32.LocalFree.restype = ctypes.c_void_p
                                kernel32.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
        except Exception:
            errors.append("PROCESS_TOKEN_UNREADABLE")
    finally:
        if token:
            try:
                kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel32.CloseHandle(token)
            except Exception:
                errors.append("PROCESS_TOKEN_HANDLE_CLOSE_FAILED")

    return _NativeProcessResult(pid, image_path, sid, tuple(dict.fromkeys(errors)))


class HostEnrollmentContextProvider:
    """Host-owned, read-only provider created by ``AppBootstrap`` composition.

    It takes no request-supplied identity or root arguments. The constructor
    stores source metadata only; native identity is read when ``observe`` is
    called. A cwd-derived root is recorded but rejected for enrollment use.
    """

    def __init__(self, app_config: Any, requested_workspace_root: str | None) -> None:
        self._app_config = app_config
        self._requested_workspace_root = requested_workspace_root
        self._configured_root_snapshot = getattr(app_config, "workspace_root", None)
        self._root_source = (
            WorkspaceRootSource.APP_BOOTSTRAP_EXPLICIT_ARGUMENT
            if requested_workspace_root is not None
            else WorkspaceRootSource.CONFIG_DEFAULTED_FROM_CWD
        )

    def observe(self) -> HostEnrollmentContext:
        errors: list[str] = []
        native = _read_windows_process_identity()
        errors.extend(native.errors)

        pid = native.pid if type(native.pid) is int and native.pid > 0 else None
        image_path = (
            native.image_path
            if isinstance(native.image_path, str) and native.image_path and os.path.isabs(native.image_path)
            else None
        )
        sid = native.sid if isinstance(native.sid, str) and _SID_PATTERN.fullmatch(native.sid) else None
        if pid is None:
            errors.append("PROCESS_ID_INCOMPLETE")
        if image_path is None:
            errors.append("PROCESS_IMAGE_PATH_INVALID")
        if native.sid is not None and sid is None:
            errors.append("PROCESS_SID_INVALID")
        elif sid is None and not any(
            item in errors for item in ("WINDOWS_API_UNAVAILABLE", "PROCESS_TOKEN_UNREADABLE", "PROCESS_SID_INVALID")
        ):
            errors.append("PROCESS_SID_INVALID")

        process = ProcessIdentityEvidence(
            pid=pid,
            image_path=image_path,
            effective_user_sid=sid,
            source=ProcessIdentitySource.WINDOWS_PROCESS_TOKEN_AND_IMAGE_API,
        )

        root_candidate: str | None = None
        configured = getattr(self._app_config, "workspace_root", None)
        if configured != self._configured_root_snapshot:
            errors.append("WORKSPACE_ROOT_CONFIG_CHANGED")
        if self._root_source is WorkspaceRootSource.CONFIG_DEFAULTED_FROM_CWD:
            errors.append("WORKSPACE_ROOT_CWD_FALLBACK_NOT_ALLOWED")
        elif not isinstance(self._requested_workspace_root, str) or not self._requested_workspace_root.strip():
            errors.append("WORKSPACE_ROOT_EXPLICIT_VALUE_INVALID")
        elif not Path(self._requested_workspace_root).is_absolute():
            errors.append("WORKSPACE_ROOT_NOT_ABSOLUTE")
        elif not isinstance(configured, str) or not configured:
            errors.append("WORKSPACE_ROOT_CONFIG_INVALID")
        else:
            try:
                resolved = Path(configured).resolve(strict=True)
                if not resolved.is_absolute():
                    errors.append("WORKSPACE_ROOT_NOT_ABSOLUTE")
                elif not resolved.is_dir():
                    errors.append("WORKSPACE_ROOT_NOT_DIRECTORY")
                else:
                    root_candidate = str(resolved)
            except FileNotFoundError:
                errors.append("WORKSPACE_ROOT_NOT_FOUND")
            except (OSError, RuntimeError, ValueError):
                errors.append("WORKSPACE_ROOT_INVALID")

        errors_tuple = tuple(dict.fromkeys(errors))
        status = ContextStatus.OBSERVED if not errors_tuple else ContextStatus.DENIED
        return HostEnrollmentContext(
            status=status,
            process_identity=process,
            workspace_root_candidate=root_candidate,
            workspace_root_source=self._root_source,
            integrity_errors=errors_tuple,
        )
