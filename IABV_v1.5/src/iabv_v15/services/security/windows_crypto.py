"""Narrow Windows CNG RSA/SHA-256 verification without extra dependencies.

This module verifies signatures under a supplied public key. It does not decide
whether that key is trusted, belongs to the Owner, or has an applicable
mandate. Trust-anchor provenance must be established by a separate authority.
"""
from __future__ import annotations

import base64
import binascii
import ctypes
import hashlib
import os
import re
import struct
from ctypes import wintypes

_PEM_BEGIN = "-----BEGIN PUBLIC KEY-----"
_PEM_END = "-----END PUBLIC KEY-----"
_RSA_ENCRYPTION_OID = bytes.fromhex("2a864886f70d010101")
_BCRYPT_RSAPUBLIC_MAGIC = 0x31415352  # RSA1
_BCRYPT_PAD_PKCS1 = 0x00000002
_MAX_PEM_BYTES = 16 * 1024


class SignatureVerificationUnavailable(RuntimeError):
    """The native verifier is absent or returned an operational error."""


class InvalidRsaPublicKey(ValueError):
    """The supplied key is not the narrowly supported RSA SubjectPublicKeyInfo."""


def validate_rsa_sha256_public_key_pem(public_key_pem: str) -> tuple[int, bytes, bytes]:
    """Parse strict RSA SPKI PEM and return (bits, exponent, modulus).

    Only RSA keys from 2048 through 4096 bits with exponent 65537 are accepted.
    Signature validity is checked separately by :func:`verify_rsa_sha256`.
    """

    if not isinstance(public_key_pem, str) or len(public_key_pem.encode("utf-8", errors="ignore")) > _MAX_PEM_BYTES:
        raise InvalidRsaPublicKey("public key PEM is missing or too large")
    lines = public_key_pem.strip().splitlines()
    if len(lines) < 3 or lines[0].strip() != _PEM_BEGIN or lines[-1].strip() != _PEM_END:
        raise InvalidRsaPublicKey("expected PUBLIC KEY PEM envelope")
    encoded = "".join(line.strip() for line in lines[1:-1])
    if not encoded or re.search(r"[^A-Za-z0-9+/=]", encoded):
        raise InvalidRsaPublicKey("invalid PEM base64")
    try:
        der = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise InvalidRsaPublicKey("invalid PEM base64") from None
    if not der or len(der) > _MAX_PEM_BYTES:
        raise InvalidRsaPublicKey("invalid DER size")

    outer, end = _read_der_tlv(der, 0, 0x30)
    if end != len(der):
        raise InvalidRsaPublicKey("trailing SubjectPublicKeyInfo bytes")
    algorithm, offset = _read_der_tlv(outer, 0, 0x30)
    oid, alg_offset = _read_der_tlv(algorithm, 0, 0x06)
    if oid != _RSA_ENCRYPTION_OID:
        raise InvalidRsaPublicKey("only rsaEncryption SubjectPublicKeyInfo is allowed")
    if alg_offset >= len(algorithm):
        raise InvalidRsaPublicKey("rsaEncryption parameters must be NULL")
    null_value, alg_offset = _read_der_tlv(algorithm, alg_offset, 0x05)
    if null_value:
        raise InvalidRsaPublicKey("invalid rsaEncryption parameters")
    if alg_offset != len(algorithm):
        raise InvalidRsaPublicKey("unsupported RSA algorithm parameters")

    bit_string, offset = _read_der_tlv(outer, offset, 0x03)
    if offset != len(outer) or not bit_string or bit_string[0] != 0:
        raise InvalidRsaPublicKey("invalid SubjectPublicKeyInfo bit string")
    rsa_sequence, rsa_end = _read_der_tlv(bit_string[1:], 0, 0x30)
    if rsa_end != len(bit_string) - 1:
        raise InvalidRsaPublicKey("trailing RSAPublicKey bytes")
    modulus_der, rsa_offset = _read_der_tlv(rsa_sequence, 0, 0x02)
    exponent_der, rsa_offset = _read_der_tlv(rsa_sequence, rsa_offset, 0x02)
    if rsa_offset != len(rsa_sequence):
        raise InvalidRsaPublicKey("unexpected RSAPublicKey fields")
    modulus = _positive_der_integer(modulus_der)
    exponent = _positive_der_integer(exponent_der)
    bits = int.from_bytes(modulus, "big").bit_length()
    if bits < 2048 or bits > 4096 or exponent != b"\x01\x00\x01" or modulus[-1] % 2 == 0:
        raise InvalidRsaPublicKey("RSA algorithm parameters are outside policy")
    return bits, exponent, modulus


def verify_rsa_sha256(public_key_pem: str, message: bytes, signature: bytes) -> bool:
    """Verify RSASSA-PKCS1-v1_5/SHA-256 through Windows CNG.

    Raises ``SignatureVerificationUnavailable`` when CNG cannot be used. A
    malformed/unsupported key raises ``InvalidRsaPublicKey``. An invalid
    signature returns ``False``. The caller must separately authenticate the
    public key and its mandate.
    """

    if not isinstance(message, bytes) or not isinstance(signature, bytes):
        return False
    bits, exponent, modulus = validate_rsa_sha256_public_key_pem(public_key_pem)
    modulus_size = (bits + 7) // 8
    if len(signature) != modulus_size:
        return False
    if os.name != "nt":
        raise SignatureVerificationUnavailable("Windows CNG is unavailable on this platform")

    key_blob = struct.pack(
        "<IIIIII",
        _BCRYPT_RSAPUBLIC_MAGIC,
        bits,
        len(exponent),
        len(modulus),
        0,
        0,
    ) + exponent + modulus
    digest = hashlib.sha256(message).digest()
    try:
        bcrypt = ctypes.WinDLL("bcrypt.dll", use_last_error=True)
    except (AttributeError, OSError) as exc:
        raise SignatureVerificationUnavailable("Windows CNG library could not be loaded") from exc

    handle_type = ctypes.c_void_p
    ulong = wintypes.ULONG
    byte_ptr = ctypes.POINTER(ctypes.c_ubyte)
    alg_handle = handle_type()
    key_handle = handle_type()

    bcrypt.BCryptOpenAlgorithmProvider.argtypes = [
        ctypes.POINTER(handle_type), wintypes.LPCWSTR, wintypes.LPCWSTR, ulong,
    ]
    bcrypt.BCryptOpenAlgorithmProvider.restype = ctypes.c_long
    bcrypt.BCryptImportKeyPair.argtypes = [
        handle_type, handle_type, wintypes.LPCWSTR, ctypes.POINTER(handle_type),
        byte_ptr, ulong, ulong,
    ]
    bcrypt.BCryptImportKeyPair.restype = ctypes.c_long
    bcrypt.BCryptVerifySignature.argtypes = [
        handle_type, ctypes.c_void_p, byte_ptr, ulong, byte_ptr, ulong, ulong,
    ]
    bcrypt.BCryptVerifySignature.restype = ctypes.c_long
    bcrypt.BCryptDestroyKey.argtypes = [handle_type]
    bcrypt.BCryptDestroyKey.restype = ctypes.c_long
    bcrypt.BCryptCloseAlgorithmProvider.argtypes = [handle_type, ulong]
    bcrypt.BCryptCloseAlgorithmProvider.restype = ctypes.c_long

    status = bcrypt.BCryptOpenAlgorithmProvider(
        ctypes.byref(alg_handle), "RSA", None, 0,
    )
    if status != 0:
        raise SignatureVerificationUnavailable(f"BCryptOpenAlgorithmProvider failed: 0x{status & 0xffffffff:08x}")
    try:
        blob_buffer = ctypes.create_string_buffer(key_blob)
        status = bcrypt.BCryptImportKeyPair(
            alg_handle,
            None,
            "RSAPUBLICBLOB",
            ctypes.byref(key_handle),
            ctypes.cast(blob_buffer, byte_ptr),
            len(key_blob),
            0,
        )
        if status != 0:
            raise InvalidRsaPublicKey(f"BCryptImportKeyPair rejected key: 0x{status & 0xffffffff:08x}")

        class _Pkcs1PaddingInfo(ctypes.Structure):
            _fields_ = [("pszAlgId", wintypes.LPCWSTR)]

        padding_info = _Pkcs1PaddingInfo("SHA256")
        digest_buffer = (ctypes.c_ubyte * len(digest)).from_buffer_copy(digest)
        signature_buffer = (ctypes.c_ubyte * len(signature)).from_buffer_copy(signature)
        status = bcrypt.BCryptVerifySignature(
            key_handle,
            ctypes.byref(padding_info),
            digest_buffer,
            len(digest),
            signature_buffer,
            len(signature),
            _BCRYPT_PAD_PKCS1,
        )
        return status == 0
    finally:
        if key_handle:
            bcrypt.BCryptDestroyKey(key_handle)
        bcrypt.BCryptCloseAlgorithmProvider(alg_handle, 0)


def _read_der_tlv(data: bytes, offset: int, expected_tag: int) -> tuple[bytes, int]:
    if offset < 0 or offset + 2 > len(data) or data[offset] != expected_tag:
        raise InvalidRsaPublicKey("unexpected DER tag or truncated value")
    length_byte = data[offset + 1]
    cursor = offset + 2
    if length_byte < 0x80:
        length = length_byte
    else:
        count = length_byte & 0x7F
        if count == 0 or count > 4 or cursor + count > len(data) or data[cursor] == 0:
            raise InvalidRsaPublicKey("invalid DER length")
        length = int.from_bytes(data[cursor : cursor + count], "big")
        if length < 0x80:
            raise InvalidRsaPublicKey("non-minimal DER length")
        cursor += count
    end = cursor + length
    if end > len(data):
        raise InvalidRsaPublicKey("truncated DER value")
    return data[cursor:end], end


def _positive_der_integer(value: bytes) -> bytes:
    if not value or value[0] & 0x80:
        raise InvalidRsaPublicKey("negative or empty DER integer")
    if len(value) > 1 and value[0] == 0:
        if value[1] & 0x80 == 0:
            raise InvalidRsaPublicKey("non-minimal DER integer")
        value = value[1:]
    if not value or value[0] == 0:
        raise InvalidRsaPublicKey("zero DER integer")
    return value
