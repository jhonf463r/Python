from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

import pytest

from iabv_v15.services.security import system_principal_provider as principal_module
from iabv_v15.services.security.system_principal_provider import (
    SystemPrincipal,
    WindowsProcessPrincipalProvider,
)


def test_system_principal_requires_sid_and_non_service_session() -> None:
    assert SystemPrincipal(sid='S-1-5-21-10-20-30-1001', session_id=2).is_valid()
    assert not SystemPrincipal(sid='', session_id=2).is_valid()
    assert not SystemPrincipal(sid='caller-supplied-name', session_id=2).is_valid()
    assert not SystemPrincipal(sid='S-1-5-21-10-20-30-1001', session_id=0).is_valid()


def test_windows_principal_provider_fails_closed_off_windows(monkeypatch) -> None:
    monkeypatch.setattr(principal_module.sys, 'platform', 'linux')
    assert WindowsProcessPrincipalProvider().get_principal() is None


class _FakeFunction:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class _FakeWindowsApis:
    def __init__(self, *, session_state: int = 0) -> None:
        self.required = ctypes.sizeof(ctypes.c_void_p)
        self.calls: list[str] = []
        self.session_id = 7
        self.connection_state = wintypes.DWORD(session_state)
        self.sid_text = ctypes.create_unicode_buffer('S-1-5-21-11-22-33-1001')
        self.kernel32 = type('Kernel32', (), {})()
        self.advapi32 = type('Advapi32', (), {})()
        self.wtsapi32 = type('Wtsapi32', (), {})()
        self.kernel32.GetCurrentProcess = _FakeFunction(lambda: 123)
        self.kernel32.ProcessIdToSessionId = _FakeFunction(self._process_session)
        self.kernel32.LocalFree = _FakeFunction(lambda _ptr: None)
        self.kernel32.CloseHandle = _FakeFunction(lambda _token: 1)
        self.advapi32.OpenProcessToken = _FakeFunction(self._open_token)
        self.advapi32.GetTokenInformation = _FakeFunction(self._token_information)
        self.advapi32.ConvertSidToStringSidW = _FakeFunction(self._convert_sid)
        self.wtsapi32.WTSQuerySessionInformationW = _FakeFunction(self._wts_query)
        self.wtsapi32.WTSFreeMemory = _FakeFunction(lambda _ptr: None)

    @staticmethod
    def _open_token(_process, _access, token_out):
        ctypes.cast(token_out, ctypes.POINTER(wintypes.HANDLE)).contents.value = 456
        return 1

    def _token_information(self, _token, info_class, buffer, _size, required_out):
        self.calls.append(f'token_info:{info_class}:buffer={buffer is not None}')
        ctypes.cast(required_out, ctypes.POINTER(wintypes.DWORD)).contents.value = self.required
        if info_class == 1 and buffer is None:
            return 0
        if info_class == 1:
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 0x1234
            return 1
        if info_class == 12:
            ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value = self.session_id
            return 1
        return 0

    def _convert_sid(self, _sid, string_out):
        self.calls.append('convert_sid')
        ctypes.cast(string_out, ctypes.POINTER(wintypes.LPWSTR)).contents.value = ctypes.addressof(self.sid_text)
        return 1

    def _process_session(self, _pid, session_out):
        self.calls.append('process_session')
        ctypes.cast(session_out, ctypes.POINTER(wintypes.DWORD)).contents.value = self.session_id
        return 1

    def _wts_query(self, _server, session_id, info_class, buffer_out, bytes_out):
        self.calls.append('wts_query')
        assert session_id == self.session_id
        assert info_class == 8
        output_pointer = ctypes.c_void_p(ctypes.addressof(self.connection_state))
        ctypes.memmove(buffer_out, ctypes.byref(output_pointer), ctypes.sizeof(output_pointer))
        ctypes.cast(bytes_out, ctypes.POINTER(wintypes.DWORD)).contents.value = ctypes.sizeof(wintypes.DWORD)
        return 1


@pytest.mark.skipif(os.name != 'nt', reason='Win32 API binding is Windows-only')
def test_windows_principal_comes_from_token_and_active_session(monkeypatch) -> None:
    apis = _FakeWindowsApis(session_state=0)
    monkeypatch.setattr(principal_module.sys, 'platform', 'win32')
    monkeypatch.setattr(principal_module.ctypes, 'WinDLL', lambda name, **_kwargs: {
        'advapi32': apis.advapi32,
        'kernel32': apis.kernel32,
        'wtsapi32': apis.wtsapi32,
    }[name])

    principal = WindowsProcessPrincipalProvider().get_principal()
    assert apis.calls == ['token_info:1:buffer=False', 'token_info:1:buffer=True', 'convert_sid', 'token_info:12:buffer=True', 'process_session', 'wts_query']
    assert principal == SystemPrincipal(sid='S-1-5-21-11-22-33-1001', session_id=7)

    inactive = _FakeWindowsApis(session_state=4)
    monkeypatch.setattr(principal_module.ctypes, 'WinDLL', lambda name, **_kwargs: {
        'advapi32': inactive.advapi32,
        'kernel32': inactive.kernel32,
        'wtsapi32': inactive.wtsapi32,
    }[name])
    assert WindowsProcessPrincipalProvider().get_principal() is None
