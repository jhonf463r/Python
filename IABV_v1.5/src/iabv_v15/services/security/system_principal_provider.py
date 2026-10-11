"""Trusted, fail-closed identity for the current interactive Windows process."""
from __future__ import annotations

import ctypes
import os
import re
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import Protocol


_SID_PATTERN = re.compile(r"^S-1-(?:\d+-)*\d+$", re.IGNORECASE)


@dataclass(frozen=True)
class SystemPrincipal:
    """OS-derived process principal; session 0 and malformed SIDs are invalid."""

    sid: str
    session_id: int
    source: str = "windows_process_token"

    def is_valid(self) -> bool:
        return bool(_SID_PATTERN.fullmatch(self.sid)) and self.session_id > 0


class SystemPrincipalProvider(Protocol):
    def get_principal(self) -> SystemPrincipal | None: ...


class WindowsProcessPrincipalProvider:
    """Read TokenUser and TokenSessionId and require an active WTS session.

    This identifies the account/session running IABV. It does not attest
    physical presence or protect against hostile code in the same process.
    """

    def get_principal(self) -> SystemPrincipal | None:
        if sys.platform != "win32" or os.name != "nt":
            return None
        try:
            return self._read_windows_principal()
        except Exception:
            return None

    @staticmethod
    def _read_windows_principal() -> SystemPrincipal | None:
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)

        token = wintypes.HANDLE()
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi32.OpenProcessToken.restype = wintypes.BOOL
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            return None

        sid_text = wintypes.LPWSTR()
        session_id = wintypes.DWORD()
        try:
            advapi32.GetTokenInformation.argtypes = [
                wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
            ]
            advapi32.GetTokenInformation.restype = wintypes.BOOL
            required = wintypes.DWORD()
            advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))  # TokenUser
            if required.value <= 0:
                return None
            token_user_buffer = ctypes.create_string_buffer(required.value)
            if not advapi32.GetTokenInformation(
                token, 1, token_user_buffer, required.value, ctypes.byref(required)
            ):
                return None

            # TOKEN_USER begins with SID_AND_ATTRIBUTES; its first field is PSID.
            sid_pointer = ctypes.cast(token_user_buffer, ctypes.POINTER(ctypes.c_void_p))[0]
            advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
            advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
            if not advapi32.ConvertSidToStringSidW(sid_pointer, ctypes.byref(sid_text)):
                return None
            sid = str(sid_text.value or "")

            if not advapi32.GetTokenInformation(
                token, 12, ctypes.byref(session_id), ctypes.sizeof(session_id), ctypes.byref(required)
            ):  # TokenSessionId
                return None
            process_session_id = wintypes.DWORD()
            kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
            kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
            if not kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(process_session_id)):
                return None
            if session_id.value == 0 or process_session_id.value != session_id.value:
                return None

            session_state_buffer = ctypes.POINTER(ctypes.c_byte)()
            bytes_returned = wintypes.DWORD()
            wtsapi32.WTSQuerySessionInformationW.argtypes = [
                wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_byte)), ctypes.POINTER(wintypes.DWORD),
            ]
            wtsapi32.WTSQuerySessionInformationW.restype = wintypes.BOOL
            if not wtsapi32.WTSQuerySessionInformationW(
                None, session_id.value, 8, ctypes.byref(session_state_buffer), ctypes.byref(bytes_returned)
            ) or not session_state_buffer:  # WTSConnectState
                return None
            try:
                if bytes_returned.value < ctypes.sizeof(wintypes.DWORD):
                    return None
                connection_state = ctypes.cast(
                    session_state_buffer, ctypes.POINTER(wintypes.DWORD)
                ).contents.value
                if connection_state != 0:  # WTSActive
                    return None
            finally:
                wtsapi32.WTSFreeMemory.argtypes = [ctypes.c_void_p]
                wtsapi32.WTSFreeMemory.restype = None
                wtsapi32.WTSFreeMemory(session_state_buffer)

            principal = SystemPrincipal(sid=sid, session_id=int(session_id.value))
            return principal if principal.is_valid() else None
        finally:
            if sid_text:
                kernel32.LocalFree.argtypes = [ctypes.c_void_p]
                kernel32.LocalFree.restype = ctypes.c_void_p
                kernel32.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            kernel32.CloseHandle(token)
