from __future__ import annotations

import ctypes
import threading
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from iabv_v15.infra.mcp import windows_handle_reader as reader


@pytest.mark.parametrize(
    "relative_target",
    [
        "",
        ".",
        "..",
        "../outside.txt",
        "a/../outside.txt",
        "C:/outside.txt",
        "//server/share/file.txt",
        "folder\\file.txt",
        "file.txt:stream",
        "bad?.txt",
    ],
)
def test_relative_target_parser_rejects_ambiguous_or_escaping_paths(relative_target: str) -> None:
    with pytest.raises(reader.WindowsHandleReaderError):
        reader._parse_relative_target(relative_target, "read_repo_file")


def test_relative_target_parser_allows_only_explicit_root_directory_listing() -> None:
    assert reader._parse_relative_target("", "list_repo_directory") == ()
    with pytest.raises(reader.WindowsHandleReaderError):
        reader._parse_relative_target(".", "list_repo_directory")


def test_opened_target_authorized_identity_is_immutable() -> None:
    target = reader.OpenedTargetCapability(
        handle=reader.OwnedWindowsHandle(742),
        operation="read_repo_file",
        relative_target="docs/a.txt",
        workspace_id="workspace",
        checkout_id="checkout",
        resolver_version="resolver-v1",
        root_binding_id="root-binding",
        policy_binding_id="policy-binding",
    )
    with pytest.raises(AttributeError, match="identity is immutable"):
        target.canonical_target = "docs/other.txt"
    with pytest.raises(AttributeError, match="identity is immutable"):
        target.target_binding_id = "substituted"


@pytest.mark.parametrize("fail_final_open", [False, True])
def test_open_target_closes_intermediate_handles_on_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, fail_final_open: bool,
) -> None:
    class FakeChild:
        def __init__(self, value: int) -> None:
            self.value = value
            self.closed = False
            self.close_calls = 0

        @property
        def is_open(self) -> bool:
            return not self.closed

        def borrow(self) -> int:
            assert not self.closed
            return self.value

        def close(self) -> None:
            self.close_calls += 1
            self.closed = True

    root_handle = reader.OwnedWindowsHandle(700)

    @contextmanager
    def root_lease():
        yield 700

    monkeypatch.setattr(root_handle, "borrowed", root_lease)
    monkeypatch.setattr(reader, "_validate_root", lambda *_args, **_kwargs: None)
    root = reader.WorkspaceRootCapability(
        handle=root_handle,
        workspace_id="workspace",
        checkout_id="checkout",
        expected_volume_serial=1,
        expected_file_id=b"\x00" * 16,
        root_binding_id="root-binding",
        policy_binding_id="policy-binding",
        resolver_version="resolver-v1",
    )
    children: list[FakeChild] = []

    def open_child(parent: int, name: str, *, directory: bool) -> FakeChild:
        assert parent == (700 if not children else children[-1].value)
        if name == "a.txt" and fail_final_open:
            raise reader.WindowsHandleReaderError("synthetic-open-failure")
        child = FakeChild(701 + len(children))
        children.append(child)
        return child

    monkeypatch.setattr(reader, "_open_component", open_child)
    if fail_final_open:
        with pytest.raises(reader.WindowsHandleReaderError, match="synthetic-open-failure"):
            reader.open_target(root, "docs/a.txt", "read_repo_file")
        assert len(children) == 1
        assert children[0].close_calls == 1
    else:
        opened = reader.open_target(root, "docs/a.txt", "read_repo_file")
        assert len(children) == 2
        assert children[0].close_calls == 1
        assert children[1].close_calls == 0
        opened.close()
        assert children[1].close_calls == 1


def test_open_target_tracks_new_child_before_parent_close_and_cleans_both_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeChild:
        def __init__(self, value: int, close_errors: list[BaseException] | None = None) -> None:
            self.value = value
            self.close_errors = list(close_errors or [])
            self.close_calls = 0
            self.closed = False

        @property
        def is_open(self) -> bool:
            return not self.closed

        def borrow(self) -> int:
            assert not self.closed
            return self.value

        def close(self) -> None:
            self.close_calls += 1
            if self.close_errors:
                raise self.close_errors.pop(0)
            self.closed = True

    root_handle = reader.OwnedWindowsHandle(700)

    @contextmanager
    def root_lease():
        yield 700

    monkeypatch.setattr(root_handle, "borrowed", root_lease)
    monkeypatch.setattr(reader, "_validate_root", lambda *_args, **_kwargs: None)
    root = reader.WorkspaceRootCapability(
        handle=root_handle,
        workspace_id="workspace",
        checkout_id="checkout",
        expected_volume_serial=1,
        expected_file_id=b"\x00" * 16,
        root_binding_id="root-binding",
        policy_binding_id="policy-binding",
        resolver_version="resolver-v1",
    )

    parent_error = reader.WindowsHandleReaderError("PARENT_CLOSE_FAILED")
    child_error = reader.WindowsHandleReaderError("CHILD_CLEANUP_FAILED")
    opened: list[FakeChild] = []

    def open_child(parent: int, name: str, *, directory: bool) -> FakeChild:
        assert parent == (700 if not opened else opened[-1].value)
        child = FakeChild(
            701 + len(opened),
            [parent_error] if name == "docs" else ([child_error] if name == "a.txt" and child_fails_cleanup else []),
        )
        opened.append(child)
        return child

    child_fails_cleanup = False
    monkeypatch.setattr(reader, "_open_component", open_child)
    with pytest.raises(reader.WindowsHandleReaderError) as exc:
        reader.open_target(root, "docs/a.txt", "read_repo_file")

    assert exc.value is parent_error
    assert [child.value for child in opened] == [701, 702]
    assert opened[0].close_calls == 2  # first close failed, registered cleanup retry succeeded
    assert opened[0].closed is True
    assert opened[1].close_calls == 1  # the newly opened child was not orphaned
    assert opened[1].closed is True


def test_open_target_retains_child_when_cleanup_also_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeChild:
        def __init__(self, value: int, close_errors: list[BaseException] | None = None) -> None:
            self.value = value
            self.close_errors = list(close_errors or [])
            self.close_calls = 0
            self.closed = False

        @property
        def is_open(self) -> bool:
            return not self.closed

        def borrow(self) -> int:
            assert not self.closed
            return self.value

        def close(self) -> None:
            self.close_calls += 1
            if self.close_errors:
                raise self.close_errors.pop(0)
            self.closed = True

    root_handle = reader.OwnedWindowsHandle(700)

    @contextmanager
    def root_lease():
        yield 700

    monkeypatch.setattr(root_handle, "borrowed", root_lease)
    monkeypatch.setattr(reader, "_validate_root", lambda *_args, **_kwargs: None)
    root = reader.WorkspaceRootCapability(
        handle=root_handle,
        workspace_id="workspace",
        checkout_id="checkout",
        expected_volume_serial=1,
        expected_file_id=b"\x00" * 16,
        root_binding_id="root-binding",
        policy_binding_id="policy-binding",
        resolver_version="resolver-v1",
    )
    parent_error = reader.WindowsHandleReaderError("PARENT_CLOSE_FAILED")
    child_error = reader.WindowsHandleReaderError("CHILD_CLEANUP_FAILED")
    opened: list[FakeChild] = []

    def open_child(parent: int, name: str, *, directory: bool) -> FakeChild:
        assert parent == (700 if not opened else opened[-1].value)
        errors = [parent_error] if name == "docs" else ([child_error] if name == "a.txt" else [])
        child = FakeChild(701 + len(opened), errors)
        opened.append(child)
        return child

    monkeypatch.setattr(reader, "_open_component", open_child)
    with pytest.raises(reader.WindowsHandleCleanupError) as exc:
        reader.open_target(root, "docs/a.txt", "read_repo_file")

    error = exc.value
    assert error.operation_error is parent_error
    assert error.cleanup_errors == (child_error,)
    assert opened[0].close_calls == 2 and opened[0].closed is True
    assert opened[1].close_calls == 1 and opened[1].closed is False
    assert opened[1] in error.owned_handles
    assert isinstance(error.__cause__, BaseExceptionGroup)
    assert error.__cause__.exceptions == (parent_error, child_error)

    # The caller can still retry cleanup through the handle retained by the error.
    error.owned_handles[1].close()
    assert opened[1].close_calls == 2 and opened[1].closed is True


def test_open_component_preserves_validation_and_cleanup_errors_and_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle_value = 880
    close_calls: list[int] = []
    close_outcomes = [False, True]
    validation_error = reader.WindowsHandleReaderError("METADATA_VALIDATION_FAILED")

    class NativeCall:
        argtypes = None
        restype = None

        def __init__(self, callback):
            self.callback = callback

        def __call__(self, *args):
            return self.callback(*args)

    def nt_create(output_pointer, *_args):
        ctypes.cast(output_pointer, ctypes.POINTER(reader.wintypes.HANDLE)).contents.value = handle_value
        return 0

    ntcreate = NativeCall(nt_create)
    monkeypatch.setattr(reader, "_windows_apis", lambda: (object(), SimpleNamespace(NtCreateFile=ntcreate)))
    query_calls: list[int] = []

    def fail_query(value: int, *_args) -> None:
        query_calls.append(value)
        raise validation_error

    monkeypatch.setattr(reader, "_query", fail_query)

    class CloseHandle:
        argtypes = None
        restype = None

        def __call__(self, _handle: object) -> int:
            close_calls.append(handle_value)
            return int(close_outcomes.pop(0))

    monkeypatch.setattr(reader, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(reader.ctypes, "WinDLL", lambda *_args, **_kwargs: SimpleNamespace(CloseHandle=CloseHandle()), raising=False)
    monkeypatch.setattr(reader.ctypes, "get_last_error", lambda: 5, raising=False)
    created_handles: list[reader.OwnedWindowsHandle] = []
    original_init = reader.OwnedWindowsHandle.__init__

    def track_handle(self, value):
        original_init(self, value)
        created_handles.append(self)

    monkeypatch.setattr(reader.OwnedWindowsHandle, "__init__", track_handle)
    with pytest.raises(reader.WindowsHandleCleanupError) as exc:
        reader._open_component(700, "a.txt", directory=False)

    error = exc.value
    assert error.phase == "_open_component"
    assert error.operation_error is validation_error
    assert len(error.cleanup_errors) == 1
    assert error.cleanup_errors[0].reason == "WINDOWS_HANDLE_CLOSE_FAILED"
    assert error.owned_handles == tuple(created_handles)
    assert len(created_handles) == 1  # no second wrapper claims the same native handle
    assert created_handles[0].is_open
    assert query_calls == [handle_value]  # no later validation/open phase ran
    assert close_calls == [handle_value]
    assert isinstance(error.__cause__, BaseExceptionGroup)
    assert error.__cause__.exceptions == (validation_error, error.cleanup_errors[0])

    created_handles[0].close()
    assert close_calls == [handle_value, handle_value]
    assert not created_handles[0].is_open


def test_open_target_does_not_open_later_component_after_component_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_handle = reader.OwnedWindowsHandle(700)

    @contextmanager
    def root_lease():
        yield 700

    monkeypatch.setattr(root_handle, "borrowed", root_lease)
    monkeypatch.setattr(reader, "_validate_root", lambda *_args, **_kwargs: None)
    root = reader.WorkspaceRootCapability(
        handle=root_handle,
        workspace_id="workspace",
        checkout_id="checkout",
        expected_volume_serial=1,
        expected_file_id=b"\x00" * 16,
        root_binding_id="root-binding",
        policy_binding_id="policy-binding",
        resolver_version="resolver-v1",
    )
    validation_error = reader.WindowsHandleReaderError("METADATA_VALIDATION_FAILED")
    cleanup_error = reader.WindowsHandleReaderError("WINDOWS_HANDLE_CLOSE_FAILED")

    class FakeChild:
        value = 801
        is_open = True

        def __init__(self) -> None:
            self.close_calls = 0

        def borrow(self) -> int:
            return self.value

        def close(self) -> None:
            self.close_calls += 1

    child = FakeChild()
    opened_names: list[str] = []

    def open_component(_parent: int, name: str, *, directory: bool):
        opened_names.append(name)
        raise reader.WindowsHandleCleanupError(
            phase="_open_component",
            operation_error=validation_error,
            cleanup_errors=(cleanup_error,),
            owned_handles=(child,),
        ) from BaseExceptionGroup("synthetic validation and cleanup failure", [validation_error, cleanup_error])

    monkeypatch.setattr(reader, "_open_component", open_component)
    with pytest.raises(reader.WindowsHandleCleanupError) as exc:
        reader.open_target(root, "docs/a.txt", "read_repo_file")

    assert opened_names == ["docs"]
    assert exc.value is not None
    assert child.close_calls == 1  # outer owner explicitly retries the retained component handle


def test_file_reader_consumes_the_authorized_handle_without_path_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    authorized_handle = 731
    observed_handles: list[int] = []
    remaining = [b"same-handle"]

    class NativeCall:
        def __init__(self, callback):
            self.callback = callback

        def __call__(self, *args):
            return self.callback(*args)

    def read_file(handle, buffer, size, count, _overlapped):
        observed_handles.append(int(handle.value))
        payload = remaining.pop() if remaining else b""
        ctypes.memmove(buffer, payload, len(payload))
        ctypes.cast(count, ctypes.POINTER(reader.wintypes.DWORD)).contents.value = len(payload)
        return 1

    calls = SimpleNamespace(ReadFile=NativeCall(read_file))
    monkeypatch.setattr(reader, "_query", lambda _handle, _kind, info: _set_file_info(info, len(b"same-handle")))
    monkeypatch.setattr(reader, "_windows_apis", lambda: (calls, object()))

    target = reader.OpenedTargetCapability(
        handle=reader.OwnedWindowsHandle(authorized_handle),
        operation="read_repo_file",
        relative_target="docs/readme.txt",
        workspace_id="synthetic-workspace",
        checkout_id="synthetic-checkout",
        resolver_version="synthetic-resolver-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )

    result = reader.read_opened_file(target, max_bytes=1024)

    assert result["content"] == "same-handle"
    assert observed_handles and set(observed_handles) == {authorized_handle}


def test_directory_enumerator_queries_the_authorized_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    authorized_handle = 947
    observed_handles: list[int] = []

    class NativeCall:
        def __init__(self, callback):
            self.callback = callback

        def __call__(self, *args):
            return self.callback(*args)

    def query(handle, _kind, _buffer, _size):
        observed_handles.append(int(handle.value))
        return 0

    calls = SimpleNamespace(GetFileInformationByHandleEx=NativeCall(query))
    monkeypatch.setattr(reader, "_windows_apis", lambda: (calls, object()))
    monkeypatch.setattr(reader.ctypes, "get_last_error", lambda: reader._ERROR_NO_MORE_FILES)
    target = reader.OpenedTargetCapability(
        handle=reader.OwnedWindowsHandle(authorized_handle),
        operation="list_repo_directory",
        relative_target="docs",
        workspace_id="synthetic-workspace",
        checkout_id="synthetic-checkout",
        resolver_version="synthetic-resolver-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )

    result = reader.list_opened_directory(target, max_entries=20)

    assert result == {"path": "docs", "entries": [], "truncated": False}
    assert observed_handles == [authorized_handle]


def _set_file_info(info: ctypes.Structure, size: int) -> None:
    info.Directory = 0
    info.EndOfFile = size


def test_closing_opened_target_waits_for_active_read_and_closes_once(monkeypatch: pytest.MonkeyPatch) -> None:
    target_handle = reader.OwnedWindowsHandle(731)
    close_calls: list[int] = []
    monkeypatch.setattr(target_handle, "close", lambda: close_calls.append(1))
    target = reader.OpenedTargetCapability(
        handle=target_handle,
        operation="read_repo_file",
        relative_target="docs/readme.txt",
        workspace_id="synthetic-workspace",
        checkout_id="synthetic-checkout",
        resolver_version="synthetic-resolver-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )
    close_waiting = threading.Event()
    close_finished = threading.Event()

    class SignalingCondition(threading.Condition):
        def wait(self, timeout: float | None = None) -> bool:
            close_waiting.set()
            return super().wait(timeout)

    target._condition = SignalingCondition(threading.Lock())
    target._begin_consume("read_repo_file")

    def close_target() -> None:
        try:
            target.close()
        finally:
            close_finished.set()

    closer = threading.Thread(target=close_target, daemon=True)
    try:
        closer.start()
        assert close_waiting.wait(timeout=1), "close did not wait for the active read"
    finally:
        target._end_consume()
        closer.join(timeout=1)

    assert not closer.is_alive()
    assert close_finished.is_set()
    assert close_calls == [1]
    target.close()
    assert close_calls == [1]


def test_owned_handle_close_failure_can_retry_and_success_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes = [False, True]
    close_calls: list[int] = []

    class NativeCall:
        argtypes = None
        restype = None

        def __call__(self, _handle: object) -> int:
            close_calls.append(1)
            return int(outcomes.pop(0))

    close_handle = NativeCall()
    kernel32 = SimpleNamespace(CloseHandle=close_handle)
    monkeypatch.setattr(reader, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(reader.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel32, raising=False)
    monkeypatch.setattr(reader.ctypes, "get_last_error", lambda: 5, raising=False)
    handle = reader.OwnedWindowsHandle(731)

    with pytest.raises(reader.WindowsHandleReaderError) as exc:
        handle.close()

    assert exc.value.reason == "WINDOWS_HANDLE_CLOSE_FAILED"
    assert handle._closed is False
    assert handle._closing is False
    assert close_calls == [1]

    handle.close()
    assert handle._closed is True
    assert handle._closing is False
    assert close_calls == [1, 1]

    handle.close()
    assert close_calls == [1, 1]


def test_opened_target_close_failure_can_retry_and_success_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_calls: list[int] = []
    failure = reader.WindowsHandleReaderError("SYNTHETIC_CLOSE_FAILURE")
    handle = reader.OwnedWindowsHandle(731)

    def close_underlying() -> None:
        close_calls.append(1)
        if len(close_calls) == 1:
            raise failure

    monkeypatch.setattr(handle, "close", close_underlying)
    target = reader.OpenedTargetCapability(
        handle=handle,
        operation="read_repo_file",
        relative_target="docs/readme.txt",
        workspace_id="synthetic-workspace",
        checkout_id="synthetic-checkout",
        resolver_version="synthetic-resolver-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )

    with pytest.raises(reader.WindowsHandleReaderError) as exc:
        target.close()

    assert exc.value is failure
    assert target._closed is False
    assert target._closing is False
    assert target._close_requested is True
    assert close_calls == [1]

    target.close()
    assert close_calls == [1, 1]
    assert target._closed is True
    assert target._closing is False
    assert target._close_requested is True

    target.close()
    assert close_calls == [1, 1]


def test_opened_target_concurrent_close_waiter_retries_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_calls: list[int] = []
    active_native_closes = 0
    max_active_native_closes = 0
    first_close_entered = threading.Event()
    release_first_close = threading.Event()
    second_close_waiting = threading.Event()
    failure = reader.WindowsHandleReaderError("SYNTHETIC_CLOSE_FAILURE")
    handle = reader.OwnedWindowsHandle(731)

    def close_underlying() -> None:
        nonlocal active_native_closes, max_active_native_closes
        close_calls.append(1)
        active_native_closes += 1
        max_active_native_closes = max(max_active_native_closes, active_native_closes)
        try:
            if len(close_calls) == 1:
                first_close_entered.set()
                if not release_first_close.wait(timeout=2):
                    raise AssertionError("first synthetic close was not released")
                raise failure
        finally:
            active_native_closes -= 1

    monkeypatch.setattr(handle, "close", close_underlying)
    target = reader.OpenedTargetCapability(
        handle=handle,
        operation="read_repo_file",
        relative_target="docs/readme.txt",
        workspace_id="synthetic-workspace",
        checkout_id="synthetic-checkout",
        resolver_version="synthetic-resolver-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )

    class SignalingCondition(threading.Condition):
        def wait(self, timeout: float | None = None) -> bool:
            second_close_waiting.set()
            return super().wait(timeout)

    target._condition = SignalingCondition(threading.Lock())
    thread_errors: list[BaseException] = []

    def close_target() -> None:
        try:
            target.close()
        except BaseException as exc:
            thread_errors.append(exc)

    first = threading.Thread(target=close_target, daemon=True)
    second = threading.Thread(target=close_target, daemon=True)
    try:
        first.start()
        assert first_close_entered.wait(timeout=1), "first close did not enter the synthetic handle"
        second.start()
        assert second_close_waiting.wait(timeout=1), "second close did not wait for the first"
    finally:
        release_first_close.set()
        if first.ident is not None:
            first.join(timeout=2)
        if second.ident is not None:
            second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert thread_errors == [failure]
    assert close_calls == [1, 1]
    assert max_active_native_closes == 1
    assert target._closed is True
    assert target._closing is False
    target.close()
    assert close_calls == [1, 1]
