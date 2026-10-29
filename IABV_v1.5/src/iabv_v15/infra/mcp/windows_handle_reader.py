"""Windows handle-relative MCP readers.

This module deliberately has no pathname-based fallback.  A host must inject a
policy-approved ``WorkspaceRootCapability``; the current AppBootstrap does not
provide one, so production protected reads remain denied.
"""

from __future__ import annotations

import ctypes
import os
import threading
import uuid
from contextlib import contextmanager
from typing import Iterator
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any


_FILE_READ_DATA = 0x0001
_FILE_LIST_DIRECTORY = 0x0001
_FILE_READ_ATTRIBUTES = 0x0080
_SYNCHRONIZE = 0x00100000
_FILE_SHARE_READ = 0x0001
_FILE_OPEN = 1
_FILE_DIRECTORY_FILE = 0x0001
_FILE_NON_DIRECTORY_FILE = 0x0040
_FILE_SYNCHRONOUS_IO_NONALERT = 0x0020
_FILE_OPEN_REPARSE_POINT = 0x00200000
_OBJ_CASE_INSENSITIVE = 0x00000040
_FILE_ATTRIBUTE_DIRECTORY = 0x0010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_FILE_ID_BOTH_DIRECTORY_INFO_CLASS = 10
_FILE_ID_INFO_CLASS = 18
_FILE_STANDARD_INFO_CLASS = 1
_ERROR_NO_MORE_FILES = 18
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_MAX_PATH_COMPONENT_CHARS = 255
_OPENED_TARGET_IDENTITY_FIELDS = frozenset({
    "operation", "relative_target", "canonical_target", "workspace_id", "checkout_id",
    "resolver_version", "root_binding_id", "policy_binding_id", "target_binding_id",
})


class WindowsHandleReaderError(RuntimeError):
    """A handle operation failed; callers must return a denial."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail or reason
        super().__init__(self.detail)

    def to_payload(self) -> dict[str, Any]:
        return {
            "governance_blocked": True,
            "reason": self.reason,
            "detail": self.detail,
        }


class WindowsHandleCleanupError(WindowsHandleReaderError):
    """Preserve the operation error, cleanup failures, and handles still owned."""

    def __init__(
        self,
        *,
        phase: str,
        operation_error: BaseException,
        cleanup_errors: tuple[BaseException, ...],
        owned_handles: tuple[Any, ...],
    ) -> None:
        self.phase = phase
        self.operation_error = operation_error
        self.cleanup_errors = cleanup_errors
        self.owned_handles = owned_handles
        details = "; ".join(repr(error) for error in cleanup_errors)
        super().__init__(
            "WINDOWS_HANDLE_CLEANUP_FAILED",
            f"{phase}: operation={operation_error!r}; cleanup={details}",
        )


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    ]


class _OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(_UNICODE_STRING)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", ctypes.c_void_p),
        ("SecurityQualityOfService", ctypes.c_void_p),
    ]


class _IO_STATUS_UNION(ctypes.Union):
    _fields_ = [("Status", wintypes.LONG), ("Pointer", ctypes.c_void_p)]


class _IO_STATUS_BLOCK(ctypes.Structure):
    _anonymous_ = ("_u",)
    _fields_ = [("_u", _IO_STATUS_UNION), ("Information", ctypes.c_size_t)]


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("FileAttributes", wintypes.DWORD), ("ReparseTag", wintypes.DWORD)]


class _FILE_STANDARD_INFO(ctypes.Structure):
    _fields_ = [
        ("AllocationSize", ctypes.c_longlong),
        ("EndOfFile", ctypes.c_longlong),
        ("NumberOfLinks", wintypes.DWORD),
        ("DeletePending", wintypes.BYTE),
        ("Directory", wintypes.BYTE),
    ]


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", ctypes.c_ubyte * 16)]


class _FILE_ID_BOTH_DIR_INFO(ctypes.Structure):
    _fields_ = [
        ("NextEntryOffset", wintypes.DWORD),
        ("FileIndex", wintypes.DWORD),
        ("CreationTime", ctypes.c_longlong),
        ("LastAccessTime", ctypes.c_longlong),
        ("LastWriteTime", ctypes.c_longlong),
        ("ChangeTime", ctypes.c_longlong),
        ("EndOfFile", ctypes.c_longlong),
        ("AllocationSize", ctypes.c_longlong),
        ("FileAttributes", wintypes.DWORD),
        ("FileNameLength", wintypes.DWORD),
        ("EaSize", wintypes.DWORD),
        ("ShortNameLength", wintypes.BYTE),
        ("ShortName", ctypes.c_uint16 * 12),
        ("FileId", ctypes.c_longlong),
        ("FileName", ctypes.c_uint16 * 1),
    ]


class OwnedWindowsHandle:
    """Single-owner native handle with idempotent, close-once semantics."""

    def __init__(self, value: int | ctypes.c_void_p) -> None:
        raw = value.value if isinstance(value, ctypes.c_void_p) else value
        if type(raw) is not int or raw in (0, _INVALID_HANDLE_VALUE):
            raise WindowsHandleReaderError("WINDOWS_HANDLE_INVALID")
        self._value = raw
        self._closed = False
        self._closing = False
        self._active_borrows = 0
        self._condition = threading.Condition(threading.Lock())

    @property
    def is_open(self) -> bool:
        with self._condition:
            return not self._closed and not self._closing

    def borrow(self) -> int:
        with self._condition:
            if self._closed or self._closing:
                raise WindowsHandleReaderError("WINDOWS_HANDLE_CLOSED")
            return self._value

    @contextmanager
    def borrowed(self) -> Iterator[int]:
        """Lease a handle so a concurrent close waits until the operation ends."""
        with self._condition:
            if self._closed or self._closing:
                raise WindowsHandleReaderError("WINDOWS_HANDLE_CLOSED")
            self._active_borrows += 1
            value = self._value
        try:
            yield value
        finally:
            with self._condition:
                self._active_borrows -= 1
                self._condition.notify_all()

    def close(self) -> None:
        with self._condition:
            while self._closing and not self._closed:
                self._condition.wait()
            if self._closed:
                return
            self._closing = True
            while self._active_borrows:
                self._condition.wait()
            value = self._value
        try:
            if os.name != "nt":
                raise WindowsHandleReaderError("WINDOWS_HANDLE_API_UNSUPPORTED")
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            ok = bool(kernel32.CloseHandle(wintypes.HANDLE(value)))
            if not ok:
                raise WindowsHandleReaderError("WINDOWS_HANDLE_CLOSE_FAILED", str(ctypes.get_last_error()))
        except BaseException:
            with self._condition:
                self._closing = False
                self._condition.notify_all()
            raise
        else:
            with self._condition:
                self._closed = True
                self._closing = False
                self._condition.notify_all()

    def __enter__(self) -> "OwnedWindowsHandle":
        self.borrow()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


@dataclass(frozen=True)
class WorkspaceRootCapability:
    """A host-provider-owned root handle and independently configured identity.

    The object is only a filesystem containment anchor.  The caller must obtain
    it from an approved host provider; constructing it from a path is forbidden.
    """

    handle: OwnedWindowsHandle
    workspace_id: str
    checkout_id: str
    expected_volume_serial: int
    expected_file_id: bytes
    root_binding_id: str
    policy_binding_id: str
    resolver_version: str


class OpenedTargetCapability:
    """Owns the final opened object used by resolution, authorization and read."""

    def __init__(
        self,
        *,
        handle: OwnedWindowsHandle,
        operation: str,
        relative_target: str,
        workspace_id: str,
        checkout_id: str,
        resolver_version: str,
        root_binding_id: str,
        policy_binding_id: str,
    ) -> None:
        self._handle = handle
        self.operation = operation
        self.relative_target = relative_target
        # The parser used by open_target rejects ambiguous spellings before a
        # handle is opened.  This canonical identifier is therefore the exact
        # root-relative name represented by this already-open handle; readers
        # consume the handle and never resolve this string again.
        self.canonical_target = relative_target
        self.workspace_id = workspace_id
        self.checkout_id = checkout_id
        self.resolver_version = resolver_version
        self.root_binding_id = root_binding_id
        self.policy_binding_id = policy_binding_id
        self.target_binding_id = uuid.uuid4().hex
        self._closed = False
        self._close_requested = False
        self._closing = False
        self._consumed = False
        self._active_operations = 0
        self._condition = threading.Condition(threading.Lock())

    def __setattr__(self, name: str, value: object) -> None:
        if name in _OPENED_TARGET_IDENTITY_FIELDS and hasattr(self, name):
            raise AttributeError(f"opened target identity is immutable: {name}")
        object.__setattr__(self, name, value)

    @property
    def is_open(self) -> bool:
        with self._condition:
            return not self._closed and not self._close_requested and self._handle.is_open

    def _begin_consume(self, expected_operation: str) -> int:
        with self._condition:
            if (
                self._closed or self._close_requested or not self._handle.is_open
                or self.operation != expected_operation or self._consumed
            ):
                raise WindowsHandleReaderError("AUTHORIZED_HANDLE_INVALID_OR_ALREADY_CONSUMED")
            self._consumed = True
            self._active_operations += 1
            try:
                return self._handle.borrow()
            except Exception:
                self._active_operations -= 1
                self._condition.notify_all()
                raise

    def _end_consume(self) -> None:
        with self._condition:
            self._active_operations -= 1
            self._condition.notify_all()

    def close(self) -> None:
        with self._condition:
            if self._closed:
                return
            self._close_requested = True
            while self._active_operations or self._closing:
                self._condition.wait()
                if self._closed:
                    return
            if self._closed:
                return
            self._closing = True
        try:
            self._handle.close()
        except BaseException:
            with self._condition:
                self._closing = False
                self._condition.notify_all()
            raise
        with self._condition:
            self._closed = True
            self._closing = False
            self._condition.notify_all()


def _windows_apis() -> tuple[Any, Any]:
    if os.name != "nt":
        raise WindowsHandleReaderError("WINDOWS_HANDLE_API_UNSUPPORTED")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll")
    return kernel32, ntdll


def _query(handle: int, info_class: int, structure: ctypes.Structure) -> None:
    kernel32, _ = _windows_apis()
    fn = kernel32.GetFileInformationByHandleEx
    fn.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    fn.restype = wintypes.BOOL
    if not fn(wintypes.HANDLE(handle), info_class, ctypes.byref(structure), ctypes.sizeof(structure)):
        raise WindowsHandleReaderError("WINDOWS_HANDLE_METADATA_QUERY_FAILED", str(ctypes.get_last_error()))


def _parse_relative_target(relative_target: str, operation: str) -> tuple[str, ...]:
    if type(relative_target) is not str or "\x00" in relative_target:
        raise WindowsHandleReaderError("READ_REQUEST_TARGET_INVALID")
    if operation == "list_repo_directory" and relative_target == "":
        return ()
    if not relative_target or relative_target.startswith(("/", "\\")) or ":" in relative_target:
        raise WindowsHandleReaderError("READ_REQUEST_TARGET_INVALID")
    if "\\" in relative_target or relative_target.startswith("//"):
        raise WindowsHandleReaderError("READ_REQUEST_TARGET_INVALID")
    components = relative_target.split("/")
    if not components or any(not part or part in (".", "..") for part in components):
        raise WindowsHandleReaderError("READ_REQUEST_TARGET_INVALID")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in components:
        if (
            len(part) > _MAX_PATH_COMPONENT_CHARS
            or part.endswith((".", " "))
            or part.upper().split(".", 1)[0] in reserved
            or any(ord(char) < 32 or char in '<>"|?*' for char in part)
        ):
            raise WindowsHandleReaderError("READ_REQUEST_COMPONENT_INVALID")
    return tuple(components)


def _open_component(parent: int, name: str, *, directory: bool) -> OwnedWindowsHandle:
    kernel32, ntdll = _windows_apis()
    encoded = ctypes.create_unicode_buffer(name)
    byte_length = len(name.encode("utf-16-le"))
    unicode_name = _UNICODE_STRING(byte_length, byte_length + 2, ctypes.cast(encoded, wintypes.LPWSTR))
    attributes = _OBJECT_ATTRIBUTES(
        ctypes.sizeof(_OBJECT_ATTRIBUTES), wintypes.HANDLE(parent), ctypes.pointer(unicode_name),
        _OBJ_CASE_INSENSITIVE, None, None,
    )
    io_status = _IO_STATUS_BLOCK()
    output = wintypes.HANDLE()
    desired_access = (_FILE_LIST_DIRECTORY if directory else _FILE_READ_DATA) | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE
    create_options = _FILE_OPEN_REPARSE_POINT | _FILE_SYNCHRONOUS_IO_NONALERT
    create_options |= _FILE_DIRECTORY_FILE if directory else _FILE_NON_DIRECTORY_FILE
    ntcreate = ntdll.NtCreateFile
    ntcreate.argtypes = [
        ctypes.POINTER(wintypes.HANDLE), wintypes.ULONG, ctypes.POINTER(_OBJECT_ATTRIBUTES),
        ctypes.POINTER(_IO_STATUS_BLOCK), ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG,
        wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
    ]
    ntcreate.restype = wintypes.LONG
    status = int(ntcreate(
        ctypes.byref(output), desired_access, ctypes.byref(attributes), ctypes.byref(io_status), None,
        0, _FILE_SHARE_READ, _FILE_OPEN, create_options, None, 0,
    ))
    if status < 0:
        raise WindowsHandleReaderError("WINDOWS_RELATIVE_OPEN_FAILED", f"NTSTATUS=0x{status & 0xffffffff:08x}")
    result = OwnedWindowsHandle(output.value)
    try:
        tag = _FILE_ATTRIBUTE_TAG_INFO()
        _query(result.borrow(), _FILE_ATTRIBUTE_TAG_INFO_CLASS, tag)
        if tag.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise WindowsHandleReaderError("REPARSE_POINT_DENIED")
        standard = _FILE_STANDARD_INFO()
        _query(result.borrow(), _FILE_STANDARD_INFO_CLASS, standard)
        if standard.NumberOfLinks != 1:
            raise WindowsHandleReaderError("HARD_LINK_DENIED")
        if bool(standard.Directory) is not directory:
            raise WindowsHandleReaderError("TARGET_TYPE_MISMATCH")
        return result
    except BaseException as validation_error:
        try:
            result.close()
        except BaseException as cleanup_error:
            raise WindowsHandleCleanupError(
                phase="_open_component",
                operation_error=validation_error,
                cleanup_errors=(cleanup_error,),
                owned_handles=(result,),
            ) from BaseExceptionGroup(
                "handle validation and cleanup both failed",
                [validation_error, cleanup_error],
            )
        raise


def open_target(
    root: WorkspaceRootCapability,
    relative_target: str,
    operation: str,
) -> OpenedTargetCapability:
    """Resolve from a provider-owned root while its handle is leased."""
    if type(root) is not WorkspaceRootCapability:
        raise WindowsHandleReaderError("APPROVED_WORKSPACE_ROOT_UNAVAILABLE")
    if operation not in {"read_repo_file", "list_repo_directory"}:
        raise WindowsHandleReaderError("READ_OPERATION_NOT_ALLOWED")
    if operation == "read_repo_file":
        from iabv_v15.infra.mcp.audit_tools import is_sensitive_path

        if is_sensitive_path(relative_target):
            raise WindowsHandleReaderError("SENSITIVE_FILE_BLOCKED")
    components = _parse_relative_target(relative_target, operation)
    owned_handles: list[Any] = []
    try:
        with root.handle.borrowed() as root_raw:
            _validate_root(root, handle_value=root_raw)
            if not components:
                kernel32, _ = _windows_apis()
                duplicate = kernel32.DuplicateHandle
                duplicate.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                duplicate.restype = wintypes.BOOL
                current_process = kernel32.GetCurrentProcess()
                duplicated = wintypes.HANDLE()
                if not duplicate(current_process, wintypes.HANDLE(root_raw), current_process, ctypes.byref(duplicated), 0, False, 0x2):
                    raise WindowsHandleReaderError("WINDOWS_HANDLE_DUPLICATION_FAILED", str(ctypes.get_last_error()))
                final = OwnedWindowsHandle(duplicated.value)
                owned_handles.append(final)
            else:
                parent = root_raw
                owned_parent: Any | None = None
                final: Any | None = None
                for index, component in enumerate(components):
                    is_directory = index < len(components) - 1 or operation == "list_repo_directory"
                    child = _open_component(parent, component, directory=is_directory)
                    # Establish function ownership before borrowing or closing the parent.
                    owned_handles.append(child)
                    child_raw = child.borrow()
                    if owned_parent is not None:
                        owned_parent.close()
                        owned_handles.remove(owned_parent)
                    owned_parent = child
                    parent = child_raw
                final = owned_parent
            if final is None:
                raise WindowsHandleReaderError("WINDOWS_TARGET_OPEN_FAILED")
            opened = OpenedTargetCapability(
                handle=final, operation=operation, relative_target=relative_target,
                workspace_id=root.workspace_id, checkout_id=root.checkout_id,
                resolver_version=root.resolver_version, root_binding_id=root.root_binding_id,
                policy_binding_id=root.policy_binding_id,
            )
            # Ownership transfers only after the capability has been constructed.
            owned_handles.remove(final)
            return opened
    except BaseException as operation_error:
        for handle in getattr(operation_error, "owned_handles", ()):
            if handle not in owned_handles:
                owned_handles.append(handle)
        cleanup_errors: list[BaseException] = []
        for handle in reversed(owned_handles):
            try:
                handle.close()
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            raise WindowsHandleCleanupError(
                phase="open_target",
                operation_error=operation_error,
                cleanup_errors=tuple(cleanup_errors),
                owned_handles=tuple(owned_handles),
            ) from BaseExceptionGroup(
                "target opening and owned-handle cleanup both failed",
                [operation_error, *cleanup_errors],
            )
        raise


def _validate_root(root: WorkspaceRootCapability, *, handle_value: int | None = None) -> None:
    if type(root) is not WorkspaceRootCapability:
        raise WindowsHandleReaderError("APPROVED_WORKSPACE_ROOT_UNAVAILABLE")
    if (
        type(root.workspace_id) is not str or not root.workspace_id
        or type(root.checkout_id) is not str or not root.checkout_id
        or type(root.expected_volume_serial) is not int or root.expected_volume_serial < 0
        or type(root.expected_file_id) is not bytes or len(root.expected_file_id) != 16
        or type(root.root_binding_id) is not str or not root.root_binding_id
        or type(root.policy_binding_id) is not str or not root.policy_binding_id
        or type(root.resolver_version) is not str or not root.resolver_version
        or type(root.handle) is not OwnedWindowsHandle or not root.handle.is_open
    ):
        raise WindowsHandleReaderError("APPROVED_WORKSPACE_ROOT_IDENTITY_INVALID")
    raw = root.handle.borrow() if handle_value is None else handle_value
    tag = _FILE_ATTRIBUTE_TAG_INFO()
    _query(raw, _FILE_ATTRIBUTE_TAG_INFO_CLASS, tag)
    if not tag.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY or tag.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise WindowsHandleReaderError("APPROVED_WORKSPACE_ROOT_TYPE_OR_REPARSE_INVALID")
    identity = _FILE_ID_INFO()
    _query(raw, _FILE_ID_INFO_CLASS, identity)
    if identity.VolumeSerialNumber != root.expected_volume_serial or bytes(identity.FileId) != root.expected_file_id:
        raise WindowsHandleReaderError("APPROVED_WORKSPACE_ROOT_IDENTITY_MISMATCH")


def read_opened_file(target: OpenedTargetCapability, *, max_bytes: int) -> dict[str, Any]:
    if type(target) is not OpenedTargetCapability or type(max_bytes) is not int or max_bytes < 1:
        raise WindowsHandleReaderError("AUTHORIZED_HANDLE_INVALID")
    raw = target._begin_consume("read_repo_file")
    try:
        return _read_opened_file_handle(target, raw, max_bytes=max_bytes)
    finally:
        target._end_consume()


def _read_opened_file_handle(target: OpenedTargetCapability, raw: int, *, max_bytes: int) -> dict[str, Any]:
    standard = _FILE_STANDARD_INFO()
    _query(raw, _FILE_STANDARD_INFO_CLASS, standard)
    if bool(standard.Directory) or standard.EndOfFile < 0 or standard.EndOfFile > max_bytes:
        raise WindowsHandleReaderError("AUTHORIZED_FILE_SIZE_OR_TYPE_INVALID")
    kernel32, _ = _windows_apis()
    read_file = kernel32.ReadFile
    read_file.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    read_file.restype = wintypes.BOOL
    result = bytearray()
    while len(result) <= max_bytes:
        buffer = ctypes.create_string_buffer(min(65536, max_bytes + 1 - len(result)))
        count = wintypes.DWORD()
        if not read_file(wintypes.HANDLE(raw), buffer, len(buffer), ctypes.byref(count), None):
            raise WindowsHandleReaderError("AUTHORIZED_HANDLE_READ_FAILED", str(ctypes.get_last_error()))
        if count.value == 0:
            break
        result.extend(buffer.raw[:count.value])
    if len(result) > max_bytes:
        raise WindowsHandleReaderError("AUTHORIZED_FILE_SIZE_LIMIT_EXCEEDED")
    try:
        content = bytes(result).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WindowsHandleReaderError("AUTHORIZED_FILE_NOT_UTF8", exc.reason) from exc
    return {"path": target.relative_target, "size": len(result), "content": content}


def list_opened_directory(target: OpenedTargetCapability, *, max_entries: int) -> dict[str, Any]:
    if type(target) is not OpenedTargetCapability or type(max_entries) is not int:
        raise WindowsHandleReaderError("AUTHORIZED_HANDLE_INVALID")
    raw = target._begin_consume("list_repo_directory")
    try:
        return _list_opened_directory_handle(target, raw, max_entries=max_entries)
    finally:
        target._end_consume()


def _list_opened_directory_handle(target: OpenedTargetCapability, raw: int, *, max_entries: int) -> dict[str, Any]:
    cap = max(1, min(max_entries, 200))
    kernel32, _ = _windows_apis()
    query = kernel32.GetFileInformationByHandleEx
    query.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    query.restype = wintypes.BOOL
    entries: list[dict[str, Any]] = []
    truncated = False
    while True:
        buffer = ctypes.create_string_buffer(64 * 1024)
        if not query(wintypes.HANDLE(raw), _FILE_ID_BOTH_DIRECTORY_INFO_CLASS, buffer, len(buffer)):
            error = ctypes.get_last_error()
            if error == _ERROR_NO_MORE_FILES:
                break
            raise WindowsHandleReaderError("AUTHORIZED_DIRECTORY_ENUMERATION_FAILED", str(error))
        offset = 0
        while True:
            if offset + _FILE_ID_BOTH_DIR_INFO.FileName.offset > len(buffer):
                raise WindowsHandleReaderError("AUTHORIZED_DIRECTORY_METADATA_MALFORMED")
            record = _FILE_ID_BOTH_DIR_INFO.from_buffer(buffer, offset)
            name_bytes = int(record.FileNameLength)
            name_offset = offset + _FILE_ID_BOTH_DIR_INFO.FileName.offset
            next_offset = int(record.NextEntryOffset)
            limit = offset + next_offset if next_offset else len(buffer)
            if name_bytes % 2 or name_offset + name_bytes > limit:
                raise WindowsHandleReaderError("AUTHORIZED_DIRECTORY_METADATA_MALFORMED")
            name = ctypes.string_at(ctypes.addressof(buffer) + name_offset, name_bytes).decode("utf-16-le", "strict")
            if name not in (".", ".."):
                attributes = int(record.FileAttributes)
                entry_type = "reparse" if attributes & _FILE_ATTRIBUTE_REPARSE_POINT else (
                    "dir" if attributes & _FILE_ATTRIBUTE_DIRECTORY else "file"
                )
                entries.append({
                    "name": name,
                    "type": entry_type,
                    "size": int(record.EndOfFile) if entry_type == "file" else 0,
                    "mtime": int(record.LastWriteTime),
                    "sensitive": audit_name_is_sensitive(name),
                })
                if len(entries) > cap:
                    raise WindowsHandleReaderError("AUTHORIZED_DIRECTORY_ENTRY_LIMIT_EXCEEDED")
            if next_offset == 0:
                break
            if next_offset < _FILE_ID_BOTH_DIR_INFO.FileName.offset or offset + next_offset >= len(buffer):
                raise WindowsHandleReaderError("AUTHORIZED_DIRECTORY_METADATA_MALFORMED")
            offset += next_offset
    entries.sort(key=lambda entry: entry["name"])
    return {"path": target.relative_target, "entries": entries, "truncated": truncated}


def audit_name_is_sensitive(name: str) -> bool:
    lower = name.lower()
    return lower.startswith(".env") or lower.endswith((".key", ".pem", ".p12", ".pfx")) or "credential" in lower
