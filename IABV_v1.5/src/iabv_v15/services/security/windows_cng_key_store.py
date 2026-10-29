"""User-scoped, non-exportable CNG enrollment-key provider.

The provider is not wired into MCP or AppBootstrap. Calling ``create_key`` is
an explicit key-creation effect and is intentionally not done by module import
or by this candidate's tests.
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import os
import struct
from dataclasses import dataclass
from typing import Protocol

PLATFORM_PROVIDER = "Microsoft Platform Crypto Provider"
SOFTWARE_PROVIDER = "Microsoft Software Key Storage Provider"
_NTE_BAD_KEYSET = 0x80090016
_NTE_NOT_FOUND = 0x80090011
_NCRYPT_PERSIST_FLAG = 0x80000000
_BCRYPT_RSAPUBLIC_MAGIC = 0x31415352
_BCRYPT_RSAPRIVATE_MAGIC = 0x32415352
_KEY_LENGTH_PROPERTY = "Length"
_EXPORT_POLICY_PROPERTY = "Export Policy"


class CngEnrollmentError(RuntimeError):
    """CNG unavailable, unsafe, or unable to preserve the no-overwrite rule."""


@dataclass(frozen=True)
class CngPublicKey:
    key_name: str
    provider_name: str
    assurance: str
    public_key_pem: str
    thumbprint_sha256: str


class _CngApi(Protocol):
    def enumerate_providers(self) -> tuple[int, tuple[str, ...]]: ...
    def open_provider(self, name: str) -> tuple[int, int]: ...
    def open_key(self, provider: int, name: str) -> tuple[int, int]: ...
    def create_key(self, provider: int, name: str) -> tuple[int, int]: ...
    def set_property(self, key: int, name: str, value: bytes, flags: int) -> int: ...
    def finalize(self, key: int) -> int: ...
    def export_public_blob(self, key: int) -> tuple[int, bytes]: ...
    def delete_key(self, key: int) -> int: ...
    def free(self, handle: int) -> int: ...


class WindowsCngKeyStore:
    """Creates one current-user RSA key, preferring Platform KSP.

    The absence of ``NCRYPT_MACHINE_KEY_FLAG`` keeps the key user-scoped.
    Export policy is explicitly zero (no private-key export). A key name is
    deterministic per enrollment ID, and existing keys are never overwritten.
    """

    def __init__(self, api: _CngApi | None = None) -> None:
        self._api = api or _NativeCngApi()

    def create_key(self, enrollment_id: str) -> CngPublicKey:
        if not isinstance(enrollment_id, str) or len(enrollment_id) != 32 or any(c not in "0123456789abcdef" for c in enrollment_id):
            raise CngEnrollmentError("ENROLLMENT_ID_INVALID")
        key_name = "IABV-G1-" + enrollment_id
        provider_name, provider = self._select_provider()
        key = 0
        finalized = False
        try:
            status, existing = self._api.open_key(provider, key_name)
            if status == 0:
                self._api.free(existing)
                raise CngEnrollmentError("ENROLLMENT_KEY_ALREADY_EXISTS")
            if status not in {_NTE_BAD_KEYSET, _NTE_NOT_FOUND}:
                raise CngEnrollmentError("CNG_EXISTING_KEY_CHECK_FAILED")
            status, key = self._api.create_key(provider, key_name)
            if status != 0 or not key:
                raise CngEnrollmentError("CNG_KEY_CREATE_FAILED")
            if self._api.set_property(key, _KEY_LENGTH_PROPERTY, struct.pack("<I", 2048), 0) != 0:
                raise CngEnrollmentError("CNG_KEY_LENGTH_SET_FAILED")
            if self._api.set_property(key, _EXPORT_POLICY_PROPERTY, struct.pack("<I", 0), _NCRYPT_PERSIST_FLAG) != 0:
                raise CngEnrollmentError("CNG_NONEXPORTABLE_POLICY_FAILED")
            if self._api.finalize(key) != 0:
                raise CngEnrollmentError("CNG_KEY_FINALIZE_FAILED")
            finalized = True
            status, blob = self._api.export_public_blob(key)
            if status != 0:
                raise CngEnrollmentError("CNG_PUBLIC_KEY_EXPORT_FAILED")
            pem = _public_blob_to_pem(blob)
            der = base64.b64decode("".join(pem.strip().splitlines()[1:-1]), validate=True)
            assurance = "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED" if provider_name == PLATFORM_PROVIDER else "SOFTWARE_PROVIDER_LOWER_ASSURANCE"
            return CngPublicKey(key_name, provider_name, assurance, pem, hashlib.sha256(der).hexdigest())
        except CngEnrollmentError:
            if key and not finalized:
                self._api.delete_key(key)
            raise
        finally:
            if key:
                self._api.free(key)
            self._api.free(provider)

    def _select_provider(self) -> tuple[str, int]:
        if os.name != "nt" and type(self._api).__name__ == "_NativeCngApi":
            raise CngEnrollmentError("CNG_UNAVAILABLE_ON_THIS_PLATFORM")
        status, providers = self._api.enumerate_providers()
        if status != 0:
            raise CngEnrollmentError("CNG_PROVIDER_ENUMERATION_FAILED")
        selected = PLATFORM_PROVIDER if PLATFORM_PROVIDER in providers else SOFTWARE_PROVIDER if SOFTWARE_PROVIDER in providers else None
        if selected is None:
            raise CngEnrollmentError("NO_APPROVED_CNG_PROVIDER_AVAILABLE")
        status, handle = self._api.open_provider(selected)
        if status != 0 or not handle:
            # Do not silently downgrade when a registered preferred provider
            # exists but is unavailable or blocked by policy.
            raise CngEnrollmentError("CNG_SELECTED_PROVIDER_OPEN_FAILED")
        return selected, handle


class _NativeCngApi:
    """Thin ctypes binding. It never exports private-key material."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise CngEnrollmentError("CNG_UNAVAILABLE_ON_THIS_PLATFORM")
        try:
            self._dll = ctypes.WinDLL("ncrypt.dll", use_last_error=True)
        except (AttributeError, OSError):
            raise CngEnrollmentError("CNG_LIBRARY_UNAVAILABLE") from None

    def enumerate_providers(self) -> tuple[int, tuple[str, ...]]:
        class _ProviderName(ctypes.Structure):
            _fields_ = [("name", ctypes.c_wchar_p), ("comment", ctypes.c_wchar_p)]

        count = ctypes.c_uint32()
        providers = ctypes.POINTER(_ProviderName)()
        fn = self._dll.NCryptEnumStorageProviders
        fn.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.POINTER(_ProviderName)), ctypes.c_uint32]
        fn.restype = ctypes.c_long
        status = int(fn(ctypes.byref(count), ctypes.byref(providers), 0)) & 0xFFFFFFFF
        if status != 0:
            return status, ()
        if count.value > 256 or (count.value and not providers):
            return 1, ()
        try:
            names = tuple(providers[index].name for index in range(count.value) if providers[index].name)
            return 0, names
        finally:
            free_buffer = self._dll.NCryptFreeBuffer
            free_buffer.argtypes = [ctypes.c_void_p]
            free_buffer.restype = ctypes.c_long
            free_buffer(ctypes.cast(providers, ctypes.c_void_p))

    def open_provider(self, name: str) -> tuple[int, int]:
        handle = ctypes.c_void_p()
        fn = self._dll.NCryptOpenStorageProvider
        fn.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_wchar_p, ctypes.c_uint32]
        fn.restype = ctypes.c_long
        status = int(fn(ctypes.byref(handle), name, 0)) & 0xFFFFFFFF
        return status, int(handle.value or 0)

    def open_key(self, provider: int, name: str) -> tuple[int, int]:
        handle = ctypes.c_void_p()
        fn = self._dll.NCryptOpenKey
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
        fn.restype = ctypes.c_long
        status = int(fn(provider, ctypes.byref(handle), name, 0, 0)) & 0xFFFFFFFF
        return status, int(handle.value or 0)

    def create_key(self, provider: int, name: str) -> tuple[int, int]:
        handle = ctypes.c_void_p()
        fn = self._dll.NCryptCreatePersistedKey
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
        fn.restype = ctypes.c_long
        status = int(fn(provider, ctypes.byref(handle), "RSA", name, 0, 0)) & 0xFFFFFFFF
        return status, int(handle.value or 0)

    def set_property(self, key: int, name: str, value: bytes, flags: int) -> int:
        data = ctypes.create_string_buffer(value)
        fn = self._dll.NCryptSetProperty
        fn.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
        fn.restype = ctypes.c_long
        return int(fn(key, name, data, len(value), flags)) & 0xFFFFFFFF

    def finalize(self, key: int) -> int:
        fn = self._dll.NCryptFinalizeKey
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        fn.restype = ctypes.c_long
        return int(fn(key, 0)) & 0xFFFFFFFF

    def export_public_blob(self, key: int) -> tuple[int, bytes]:
        fn = self._dll.NCryptExportKey
        fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32]
        fn.restype = ctypes.c_long
        needed = ctypes.c_uint32()
        status = int(fn(key, None, "RSAPUBLICBLOB", None, None, 0, ctypes.byref(needed), 0)) & 0xFFFFFFFF
        if status != 0 or not 24 <= needed.value <= 16 * 1024:
            return status or 1, b""
        buffer = ctypes.create_string_buffer(needed.value)
        written = ctypes.c_uint32()
        status = int(fn(key, None, "RSAPUBLICBLOB", None, buffer, needed.value, ctypes.byref(written), 0)) & 0xFFFFFFFF
        return status, buffer.raw[: written.value] if status == 0 else b""

    def delete_key(self, key: int) -> int:
        fn = self._dll.NCryptDeleteKey
        fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        fn.restype = ctypes.c_long
        return int(fn(key, 0)) & 0xFFFFFFFF

    def free(self, handle: int) -> int:
        if not handle:
            return 0
        fn = self._dll.NCryptFreeObject
        fn.argtypes = [ctypes.c_void_p]
        fn.restype = ctypes.c_long
        return int(fn(handle)) & 0xFFFFFFFF


def _der(tag: int, value: bytes) -> bytes:
    if len(value) < 128:
        length = bytes([len(value)])
    else:
        size = len(value).to_bytes((len(value).bit_length() + 7) // 8, "big")
        length = bytes([0x80 | len(size)]) + size
    return bytes([tag]) + length + value


def _der_integer(value: bytes) -> bytes:
    return _der(0x02, (b"\0" if value[0] & 0x80 else b"") + value)


def _public_blob_to_pem(blob: bytes) -> str:
    if not isinstance(blob, bytes) or len(blob) < 24:
        raise CngEnrollmentError("CNG_PUBLIC_KEY_BLOB_INVALID")
    magic, bits, exponent_len, modulus_len, prime1_len, prime2_len = struct.unpack("<IIIIII", blob[:24])
    if magic not in {_BCRYPT_RSAPUBLIC_MAGIC, _BCRYPT_RSAPRIVATE_MAGIC} or magic == _BCRYPT_RSAPRIVATE_MAGIC:
        raise CngEnrollmentError("CNG_PRIVATE_OR_INVALID_BLOB_REJECTED")
    if bits < 2048 or bits > 4096 or exponent_len < 1 or modulus_len != (bits + 7) // 8 or prime1_len or prime2_len:
        raise CngEnrollmentError("CNG_PUBLIC_KEY_BLOB_INVALID")
    if len(blob) != 24 + exponent_len + modulus_len:
        raise CngEnrollmentError("CNG_PUBLIC_KEY_BLOB_INVALID")
    exponent = blob[24 : 24 + exponent_len]
    modulus = blob[24 + exponent_len :]
    if exponent != b"\x01\x00\x01" or not modulus or modulus[-1] % 2 == 0:
        raise CngEnrollmentError("CNG_PUBLIC_KEY_PARAMETERS_REJECTED")
    rsa_public = _der(0x30, _der_integer(modulus) + _der_integer(exponent))
    algorithm = _der(0x30, bytes.fromhex("06092a864886f70d0101010500"))
    spki = _der(0x30, algorithm + _der(0x03, b"\0" + rsa_public))
    encoded = base64.b64encode(spki).decode("ascii")
    lines = "\n".join(encoded[i : i + 64] for i in range(0, len(encoded), 64))
    return f"-----BEGIN PUBLIC KEY-----\n{lines}\n-----END PUBLIC KEY-----"
