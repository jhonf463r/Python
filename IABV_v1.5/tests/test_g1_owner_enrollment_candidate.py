from __future__ import annotations

import base64
import hashlib
import json
import struct
from types import SimpleNamespace
from datetime import datetime, timezone
from typing import Any

import pytest

from iabv_v15.services.security.authenticated_github_enrollment import (
    AuthenticatedGitHubCliApi,
    _verify_owner_manifest_fetchback_with_api,
    verify_owner_manifest_fetchback as _public_verify_owner_manifest_fetchback,
)
from iabv_v15.services.security.github_owner_merge_bootstrap import (
    BOOTSTRAP_MANIFEST_PATH,
    EXPECTED_OWNER_ID,
    EXPECTED_REPOSITORY,
    EXPECTED_REPOSITORY_ID,
    OwnerMergeVerificationError,
)
from iabv_v15.services.security.owner_enrollment_manifest import (
    OwnerEnrollmentManifest,
    parse_owner_manifest,
    sid_commitment,
)
from iabv_v15.services.security.windows_cng_key_store import (
    CngEnrollmentError,
    CngPublicKey,
    PLATFORM_PROVIDER,
    SOFTWARE_PROVIDER,
    WindowsCngKeyStore,
    _public_blob_to_pem,
)
from iabv_v15.services.security.windows_crypto import validate_rsa_sha256_public_key_pem

NOW = 1_798_200_000
NOW_UTC = datetime.fromtimestamp(NOW, timezone.utc)
PR_NUMBER = 741
MERGE_SHA = "a" * 40
MAIN_SHA = "b" * 40
CODE_SHA = "c" * 40
SID = "S-1-5-21-111111111-222222222-333333333-1001"
def _real_public_key() -> str:
    n = (
        "ofgWCuLjybRlzo0tZWJjNiuSfb4p4fAkd_wWJcyQoTbji9k0l8W26mPddx"
        "HmfHQp-Vaw-4qPCJrcS2mJPMEzP1Pt0Bm4d4QlL-yRT-SFd2lZS-pCgNMs"
        "D1W_YpRPEwOWvG6b32690r2jZ47soMZo9wGzjb_7OMg0LOL-bSf63kpaSH"
        "SXndS5z5rexMdbBYUsLA9e-KXBdQOS-UTo7WTBEMa2R2CapHg665xsmtdV"
        "MTBQY4uDZlxvb3qCo5ZwKh9kG4LT6_I5IhlJH7aGhyxXFvUK-DWNmoudF8"
        "NAco9_h9iaGNj8q2ethFkMLs91kzk2PAcDTW9gb54h4FRWyuXpoQ"
    )
    modulus = base64.urlsafe_b64decode(n + "=" * (-len(n) % 4))
    def der(tag: int, value: bytes) -> bytes:
        length = bytes([len(value)]) if len(value) < 128 else b"\x82" + len(value).to_bytes(2, "big")
        return bytes([tag]) + length + value
    def integer(value: bytes) -> bytes:
        return der(2, (b"\0" if value[0] & 0x80 else b"") + value)
    key = der(0x30, integer(modulus) + integer(b"\x01\x00\x01"))
    alg = der(0x30, bytes.fromhex("06092a864886f70d0101010500"))
    spki = der(0x30, alg + der(3, b"\0" + key))
    encoded = base64.b64encode(spki).decode("ascii")
    body = "\n".join(encoded[i:i+64] for i in range(0, len(encoded), 64))
    return f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----\n"


KEY = _real_public_key()
THUMBPRINT = hashlib.sha256(base64.b64decode("".join(KEY.strip().splitlines()[1:-1]))).hexdigest()


class _SyntheticPersistedKeyReader:
    """Test-only stand-in; never evidence of a native CNG key or trust."""
    def __init__(self, key: CngPublicKey) -> None:
        self.key = key
        self.calls: list[tuple[str, str]] = []
    def read_existing_key(self, enrollment_id: str, provider_name: str) -> CngPublicKey:
        self.calls.append((enrollment_id, provider_name))
        return self.key


def verify_owner_manifest_fetchback(*args: Any, **kwargs: Any):
    """Exercise only the private pure verifier with an explicit fake store."""
    key = kwargs["cng_key"]
    kwargs.setdefault("key_store", _SyntheticPersistedKeyReader(key))
    return _verify_owner_manifest_fetchback_with_api(*args, **kwargs)


def _manifest(**changes: Any) -> OwnerEnrollmentManifest:
    values: dict[str, Any] = {
        "enrollment_id": "e" * 32,
        "public_key_pem": KEY,
        "windows_sid_commitment": sid_commitment(SID),
        "server_code_revision": CODE_SHA,
        "workspace_root": r"C:\Python\IABV_v1.5",
        "issued_at_epoch": NOW - 60,
        "expires_at_epoch": NOW + 86400,
        "revocation_source_id": "owner-configured-source-reference",
    }
    values.update(changes)
    return OwnerEnrollmentManifest(**values)


def test_manifest_is_public_pinned_and_has_no_self_reference_or_capabilities() -> None:
    manifest = _manifest()
    mapping = manifest.to_mapping()
    assert mapping["repository_id"] == EXPECTED_REPOSITORY_ID
    assert mapping["repository_full_name"] == EXPECTED_REPOSITORY
    assert mapping["manifest_path"] == BOOTSTRAP_MANIFEST_PATH
    assert mapping["public_key_thumbprint_sha256"] == THUMBPRINT
    assert mapping["capability_profile"] == "ROOT_ENROLLMENT_ONLY"
    assert not {"scopes", "manifest_commit_sha", "manifest_blob_sha", "manifest_sha256"}.intersection(mapping)
    assert parse_owner_manifest(manifest.canonical_bytes()) == manifest


def test_manifest_rejects_duplicate_credentials_self_reference_and_unknown_fields() -> None:
    raw = _manifest().canonical_bytes()
    duplicate = raw[:-1] + b',"schema_version":1}'
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_MANIFEST_JSON_INVALID"):
        parse_owner_manifest(duplicate)
    for field, code in (("access_token", "OWNER_MANIFEST_CREDENTIAL_FIELD_FORBIDDEN"),
                        ("manifest_commit_sha", "OWNER_MANIFEST_SELF_REFERENCE_FORBIDDEN"),
                        ("extra", "OWNER_MANIFEST_SCHEMA_INVALID")):
        value = _manifest().to_mapping()
        value[field] = "forbidden"
        with pytest.raises(OwnerMergeVerificationError, match=code):
            parse_owner_manifest(json.dumps(value).encode())
    unsupported = _manifest().to_mapping()
    unsupported["schema_version"] = 99
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_MANIFEST_SCHEMA_VERSION_UNSUPPORTED"):
        parse_owner_manifest(json.dumps(unsupported).encode())
    mismatched_thumbprint = _manifest().to_mapping()
    mismatched_thumbprint["public_key_thumbprint_sha256"] = "0" * 64
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_MANIFEST_KEY_THUMBPRINT_MISMATCH"):
        parse_owner_manifest(json.dumps(mismatched_thumbprint).encode())


@pytest.mark.parametrize(
    "change,code",
    [
        ({"repository_id": 1}, "OWNER_MANIFEST_REPOSITORY_MISMATCH"),
        ({"manifest_path": "other.json"}, "OWNER_MANIFEST_LOCATION_MISMATCH"),
        ({"server_code_revision": "bad"}, "OWNER_MANIFEST_CODE_REVISION_INVALID"),
        ({"workspace_root": r"C:\\root\\..\\other"}, "OWNER_MANIFEST_WORKSPACE_ROOT_INVALID"),
        ({"capability_profile": "PROTECTED_READ"}, "OWNER_MANIFEST_CAPABILITY_PROFILE_INVALID"),
        ({"revocation_source_id": ""}, "OWNER_MANIFEST_REVOCATION_SOURCE_UNRESOLVED"),
    ],
)
def test_manifest_binding_changes_fail_closed(change: dict[str, Any], code: str) -> None:
    with pytest.raises(OwnerMergeVerificationError, match=code):
        _manifest(**change).validate()


def test_sid_commitment_rejects_malformed_sid_and_normalizes_case() -> None:
    assert sid_commitment(SID.lower()) == sid_commitment(SID.upper())
    with pytest.raises(OwnerMergeVerificationError, match="WINDOWS_SID_INVALID"):
        sid_commitment("not-a-sid")


class _CngFake:
    def __init__(self, available: tuple[str, ...] = (PLATFORM_PROVIDER, SOFTWARE_PROVIDER), existing: bool = False) -> None:
        self.available = available
        self.existing = existing
        self.created: list[tuple[int, str]] = []
        self.properties: list[tuple[str, bytes, int]] = []
        self.deleted: list[int] = []
        self.freed: list[int] = []
        self.create_status = 0
        self.create_handle = 22
        self.fail_property: str | None = None
        self.finalize_status = 0
        self.export_status = 0
        self.export_blob_override: bytes | None = None
        self.delete_status = 0
        self.free_failures: dict[int, int] = {}
    def enumerate_providers(self) -> tuple[int, tuple[str, ...]]:
        return 0, self.available
    def open_provider(self, name: str) -> tuple[int, int]:
        if name not in self.available:
            return 1, 0
        if getattr(self, "open_failure", False):
            return 5, 0
        return 0, 11
    def open_key(self, provider: int, name: str) -> tuple[int, int]:
        return (0, 21) if self.existing else (0x80090016, 0)
    def create_key(self, provider: int, name: str) -> tuple[int, int]:
        self.created.append((provider, name))
        if self.create_handle:
            self.existing = True
        return self.create_status, self.create_handle
    def set_property(self, key: int, name: str, value: bytes, flags: int) -> int:
        self.properties.append((name, value, flags))
        return 1 if self.fail_property == name else 0
    def finalize(self, key: int) -> int:
        return self.finalize_status
    def export_public_blob(self, key: int) -> tuple[int, bytes]:
        modulus = b"\x80" + b"\x11" * 254 + b"\x01"
        exponent = b"\x01\x00\x01"
        blob = struct.pack("<IIIIII", 0x31415352, 2048, len(exponent), len(modulus), 0, 0) + exponent + modulus
        return self.export_status, self.export_blob_override if self.export_blob_override is not None else blob
    def delete_key(self, key: int) -> int:
        self.deleted.append(key)
        if self.delete_status == 0:
            self.existing = False
        return self.delete_status
    def free(self, handle: int) -> int:
        self.freed.append(handle)
        return self.free_failures.get(handle, 0)


def test_cng_prefers_platform_and_records_nonexportability_without_creating_real_key() -> None:
    fake = _CngFake()
    result = WindowsCngKeyStore(fake).create_key("e" * 32)
    assert result.provider_name == PLATFORM_PROVIDER
    assert result.assurance.startswith("PLATFORM_PROVIDER_SELECTED")
    assert result.key_name.endswith("e" * 32)
    assert validate_rsa_sha256_public_key_pem(result.public_key_pem)[0] == 2048
    assert ("Export Policy", b"\0\0\0\0", 0x80000000) in fake.properties
    assert fake.deleted == []


def test_cng_uses_lower_assurance_fallback_only_when_platform_provider_absent() -> None:
    result = WindowsCngKeyStore(_CngFake((SOFTWARE_PROVIDER,))).create_key("e" * 32)
    assert result.provider_name == SOFTWARE_PROVIDER
    assert result.assurance == "SOFTWARE_PROVIDER_LOWER_ASSURANCE"


def test_cng_never_overwrites_existing_key_or_selects_no_provider() -> None:
    existing = _CngFake(existing=True)
    with pytest.raises(CngEnrollmentError, match="ENROLLMENT_KEY_ALREADY_EXISTS"):
        WindowsCngKeyStore(existing).create_key("e" * 32)
    assert existing.created == []
    with pytest.raises(CngEnrollmentError, match="NO_APPROVED_CNG_PROVIDER_AVAILABLE"):
        WindowsCngKeyStore(_CngFake(())).create_key("e" * 32)
    provider_open_failure = _CngFake()
    provider_open_failure.open_failure = True
    with pytest.raises(CngEnrollmentError, match="CNG_SELECTED_PROVIDER_OPEN_FAILED"):
        WindowsCngKeyStore(provider_open_failure).create_key("e" * 32)


@pytest.mark.parametrize(
    "failure,code",
    [
        ("create", "CNG_KEY_CREATE_FAILED"),
        ("length", "CNG_KEY_LENGTH_SET_FAILED"),
        ("export_policy", "CNG_NONEXPORTABLE_POLICY_FAILED"),
        ("finalize", "CNG_KEY_FINALIZE_FAILED"),
        ("export", "CNG_PUBLIC_KEY_EXPORT_FAILED"),
        ("convert", "CNG_PRIVATE_OR_INVALID_BLOB_REJECTED"),
    ],
)
def test_cng_failed_creation_deletes_once_and_does_not_free_deleted_key(failure: str, code: str) -> None:
    fake = _CngFake()
    if failure == "create":
        fake.create_status = 5
    elif failure == "length":
        fake.fail_property = "Length"
    elif failure == "export_policy":
        fake.fail_property = "Export Policy"
    elif failure == "finalize":
        fake.finalize_status = 5
    elif failure == "export":
        fake.export_status = 5
    else:
        fake.export_blob_override = b"\0" * 24
    with pytest.raises(CngEnrollmentError, match=code):
        WindowsCngKeyStore(fake).create_key("e" * 32)
    assert fake.deleted == [fake.create_handle]
    assert fake.freed.count(fake.create_handle) == 0
    assert fake.freed.count(11) == 1


def test_cng_delete_failure_is_reported_and_key_handle_is_released_once() -> None:
    fake = _CngFake()
    fake.export_status = 5
    fake.delete_status = 5
    with pytest.raises(CngEnrollmentError, match="CNG_CREATION_CLEANUP_FAILED:CNG_KEY_DELETE_FAILED"):
        WindowsCngKeyStore(fake).create_key("e" * 32)
    assert fake.deleted == [fake.create_handle]
    assert fake.freed.count(fake.create_handle) == 1
    assert fake.freed.count(11) == 1
    # The finalized persistent key survives failed deletion; explicit recovery
    # opens that same object instead of attempting to overwrite it.
    fake.export_status = 0
    recovered = WindowsCngKeyStore(fake).read_existing_key("e" * 32, PLATFORM_PROVIDER)
    assert recovered.key_name == "IABV-G1-" + "e" * 32
    assert fake.created == [(11, recovered.key_name)]


def test_cng_delete_and_fallback_release_failures_are_both_reported() -> None:
    fake = _CngFake()
    fake.export_status = 5
    fake.delete_status = 5
    fake.free_failures[22] = 9
    with pytest.raises(CngEnrollmentError, match="CNG_CREATION_CLEANUP_FAILED:CNG_KEY_DELETE_FAILED,CNG_KEY_HANDLE_RELEASE_FAILED"):
        WindowsCngKeyStore(fake).create_key("e" * 32)
    assert fake.freed.count(22) == 1


def test_cng_provider_handle_release_failure_is_reported() -> None:
    fake = _CngFake()
    fake.free_failures[11] = 9
    with pytest.raises(CngEnrollmentError, match="CNG_HANDLE_RELEASE_FAILED:CNG_PROVIDER_HANDLE_RELEASE_FAILED"):
        WindowsCngKeyStore(fake).create_key("e" * 32)
    assert fake.freed.count(22) == 1
    assert fake.freed.count(11) == 1


def test_cng_free_failure_is_not_reported_as_success() -> None:
    fake = _CngFake()
    fake.free_failures[22] = 5
    with pytest.raises(CngEnrollmentError, match="CNG_HANDLE_RELEASE_FAILED:CNG_KEY_HANDLE_RELEASE_FAILED"):
        WindowsCngKeyStore(fake).create_key("e" * 32)
    assert fake.deleted == []
    assert fake.freed.count(22) == 1
    assert fake.freed.count(11) == 1


def test_cng_existing_key_recovery_reads_public_key_from_opened_persisted_handle() -> None:
    fake = _CngFake(existing=True)
    recovered = WindowsCngKeyStore(fake).read_existing_key("e" * 32, PLATFORM_PROVIDER)
    assert recovered.key_name == "IABV-G1-" + "e" * 32
    assert recovered.provider_name == PLATFORM_PROVIDER
    assert validate_rsa_sha256_public_key_pem(recovered.public_key_pem)[0] == 2048
    assert fake.created == []
    assert fake.freed.count(21) == 1
    assert fake.freed.count(11) == 1


def test_public_blob_export_rejects_private_blob() -> None:
    blob = b"\0" * 24
    with pytest.raises(CngEnrollmentError, match="CNG_PRIVATE_OR_INVALID_BLOB_REJECTED"):
        _public_blob_to_pem(blob)


class _FetchbackApi:
    def __init__(self, content: bytes | None = None, *, actor_id: int = EXPECTED_OWNER_ID,
                 response_pr_number: int = PR_NUMBER, merged: bool = True,
                 files: list[dict[str, Any]] | None = None, moved_main: bool = False,
                 current_content: bytes | None = None) -> None:
        self.content = content
        self.current_content = current_content
        self.branch_calls = 0
        self.actor_id = actor_id
        self.response_pr_number = response_pr_number
        self.merged = merged
        self.files = files or [{"filename": BOOTSTRAP_MANIFEST_PATH, "status": "added"}]
        self.moved_main = moved_main
    @staticmethod
    def _blob(data: bytes) -> str:
        return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    def get_json(self, path: str, *, params: Any = None) -> Any:
        root = f"/repos/{EXPECTED_REPOSITORY}"
        if path == root:
            return {"id": EXPECTED_REPOSITORY_ID, "full_name": EXPECTED_REPOSITORY, "private": True}
        if path.endswith(f"/pulls/{PR_NUMBER}"):
            return {"number": self.response_pr_number, "state": "closed", "merged": self.merged,
                    "merged_by": {"id": self.actor_id},
                    "merged_at": datetime.fromtimestamp(NOW - 30, timezone.utc).isoformat(),
                    "merge_commit_sha": MERGE_SHA,
                    "base": {"ref": "main", "repo": {"id": EXPECTED_REPOSITORY_ID, "full_name": EXPECTED_REPOSITORY}}}
        if path.endswith(f"/pulls/{PR_NUMBER}/files"):
            return self.files
        if path.endswith("/branches/main"):
            self.branch_calls += 1
            sha = ("d" * 40) if self.moved_main and self.branch_calls > 1 else MAIN_SHA
            return {"commit": {"sha": sha}}
        if path.endswith(f"/commits/{MERGE_SHA}"):
            return {"sha": MERGE_SHA}
        if path.endswith(f"/commits/{MERGE_SHA}/pulls"):
            return [{"number": PR_NUMBER, "base": {"ref": "main", "repo": {"id": EXPECTED_REPOSITORY_ID, "full_name": EXPECTED_REPOSITORY}}}]
        if path.endswith(f"/compare/{MERGE_SHA}...{MAIN_SHA}"):
            return {"status": "ahead", "merge_base_commit": {"sha": MERGE_SHA}}
        if path.endswith("/contents/" + BOOTSTRAP_MANIFEST_PATH):
            data = self.current_content if params and params.get("ref") == MAIN_SHA and self.current_content is not None else self.content
            if data is None:
                raise AssertionError("manifest bytes not configured")
            return {"type": "file", "path": BOOTSTRAP_MANIFEST_PATH, "encoding": "base64",
                    "size": len(data), "sha": self._blob(data), "content": base64.b64encode(data).decode()}
        raise AssertionError(path)


def test_fetchback_requires_exact_owner_merge_and_current_main_bytes() -> None:
    manifest = _manifest()
    raw = manifest.canonical_bytes()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER,
                       "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED",
                       KEY, THUMBPRINT)
    store = _FakeReceiptStore()
    receipt = verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest,
            expected_owner_id=EXPECTED_OWNER_ID, expected_server_code_revision=CODE_SHA,
            expected_workspace_root=r"C:\Python\IABV_v1.5", windows_sid=SID, cng_key=key,
            receipt_store=store, api=_FetchbackApi(raw), clock=lambda: NOW_UTC)
    assert receipt.merge_commit_sha == MERGE_SHA
    assert receipt.manifest_sha256 == hashlib.sha256(raw).hexdigest()
    assert receipt.windows_sid == SID
    assert receipt.outcome == "MANIFEST_FETCHBACK_VERIFIED_G1_NOT_ESTABLISHED"
    assert "revocation_status" not in receipt.to_mapping()
    assert store.records[manifest.enrollment_id] == receipt


class _FakeReceiptStore:
    def __init__(self) -> None:
        self.records = {}
    def record_if_absent(self, receipt):
        prior = self.records.get(receipt.enrollment_id)
        if prior is None:
            self.records[receipt.enrollment_id] = receipt
            return receipt
        left, right = prior.to_mapping(), receipt.to_mapping()
        left.pop("verified_at_epoch")
        right.pop("verified_at_epoch")
        if left != right:
            raise OwnerMergeVerificationError("LOCAL_RECEIPT_CONFLICT")
        return prior


def test_fetchback_rejects_sid_or_current_main_mismatch() -> None:
    manifest = _manifest()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER, "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    with pytest.raises(OwnerMergeVerificationError, match="LOCAL_SID_BINDING_MISMATCH"):
        verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid="S-1-5-21-999-1001", cng_key=key, receipt_store=_FakeReceiptStore(), api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC)
    with pytest.raises(OwnerMergeVerificationError, match="CURRENT_MAIN_MANIFEST_MISMATCH"):
        verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=key, receipt_store=_FakeReceiptStore(),
            api=_FetchbackApi(manifest.canonical_bytes(), current_content=b"{}"), clock=lambda: NOW_UTC)


def test_fetchback_rejects_key_actor_extra_file_and_moved_main() -> None:
    manifest = _manifest()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER, "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    mismatched_key = CngPublicKey(key.key_name, PLATFORM_PROVIDER, key.assurance, KEY, "0" * 64)
    with pytest.raises(OwnerMergeVerificationError, match="LOCAL_CNG_KEY_BINDING_MISMATCH"):
        verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=mismatched_key, receipt_store=_FakeReceiptStore(), api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC)
    cases = [
        (_FetchbackApi(manifest.canonical_bytes(), actor_id=EXPECTED_OWNER_ID + 1), "UNAUTHORIZED_MERGE_ACTOR"),
        (_FetchbackApi(manifest.canonical_bytes(), response_pr_number=PR_NUMBER + 1), "PULL_REQUEST_NOT_MERGED"),
        (_FetchbackApi(manifest.canonical_bytes(), merged=False), "PULL_REQUEST_NOT_MERGED"),
        (_FetchbackApi(manifest.canonical_bytes(), files=[{"filename": BOOTSTRAP_MANIFEST_PATH, "status": "modified"}]), "MANIFEST_NOT_EXCLUSIVE_PR_CHANGE"),
        (_FetchbackApi(manifest.canonical_bytes(), files=[{"filename": BOOTSTRAP_MANIFEST_PATH, "status": "added"}, {"filename": "extra", "status": "added"}]), "MANIFEST_NOT_EXCLUSIVE_PR_CHANGE"),
        (_FetchbackApi(manifest.canonical_bytes(), moved_main=True), "MAIN_MOVED_DURING_VERIFICATION"),
    ]
    for api, code in cases:
        with pytest.raises(OwnerMergeVerificationError, match=code):
            verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
                expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
                windows_sid=SID, cng_key=key, receipt_store=_FakeReceiptStore(), api=api, clock=lambda: NOW_UTC)


def test_fetchback_receipt_store_is_idempotent_and_required() -> None:
    manifest = _manifest()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER, "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    store = _FakeReceiptStore()
    first = verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
        expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
        windows_sid=SID, cng_key=key, receipt_store=store, api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC)
    later = verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
        expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
        windows_sid=SID, cng_key=key, receipt_store=store, api=_FetchbackApi(manifest.canonical_bytes()),
        clock=lambda: datetime.fromtimestamp(NOW + 5, timezone.utc))
    assert later == first
    assert len(store.records) == 1
    with pytest.raises(OwnerMergeVerificationError, match="LOCAL_RECEIPT_STORE_REQUIRED"):
        verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=key, receipt_store=None, api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC)


def test_fetchback_rejects_local_code_or_workspace_binding_mismatch() -> None:
    manifest = _manifest()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER, "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    with pytest.raises(OwnerMergeVerificationError, match="LOCAL_ENROLLMENT_BINDING_MISMATCH"):
        verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision="d" * 40, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=key, receipt_store=_FakeReceiptStore(), api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC)
    with pytest.raises(OwnerMergeVerificationError, match="LOCAL_ENROLLMENT_BINDING_MISMATCH"):
        verify_owner_manifest_fetchback(PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\OtherRoot",
            windows_sid=SID, cng_key=key, receipt_store=_FakeReceiptStore(), api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC)


def test_fetchback_rejects_public_key_that_differs_from_persisted_cng_handle() -> None:
    manifest = _manifest()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER,
                       "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    with pytest.raises(OwnerMergeVerificationError, match="LOCAL_CNG_PERSISTED_KEY_MISMATCH"):
        _verify_owner_manifest_fetchback_with_api(
            PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=key,
            key_store=WindowsCngKeyStore(_CngFake(existing=True)),
            receipt_store=_FakeReceiptStore(), api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC,
        )


@pytest.mark.parametrize(
    "store_error,expected_code",
    [
        (OwnerMergeVerificationError("LOCAL_RECEIPT_CONFLICT"), "LOCAL_RECEIPT_CONFLICT"),
        (OSError("simulated store failure"), "LOCAL_RECEIPT_PERSISTENCE_FAILED"),
    ],
)
def test_fetchback_rejects_receipt_conflict_and_storage_failure(store_error: Exception, expected_code: str) -> None:
    class FailingStore:
        def record_if_absent(self, _receipt):
            raise store_error
    manifest = _manifest()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER,
                       "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    with pytest.raises(OwnerMergeVerificationError, match=expected_code):
        _verify_owner_manifest_fetchback_with_api(
            PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=key, key_store=_SyntheticPersistedKeyReader(key),
            receipt_store=FailingStore(), api=_FetchbackApi(manifest.canonical_bytes()), clock=lambda: NOW_UTC,
        )


def test_authenticated_gh_api_rejects_unverified_executable_without_running_it() -> None:
    observed: list[Any] = []
    def runner(args, **kwargs):
        observed.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=b"{}", stderr=b"")
    with pytest.raises(OwnerMergeVerificationError, match="GITHUB_CLIENT_PROVENANCE_UNVERIFIED"):
        AuthenticatedGitHubCliApi(executable="gh", runner=runner)
    assert observed == []


def test_authenticated_gh_api_candidate_is_unavailable_until_provenance_exists() -> None:
    with pytest.raises(OwnerMergeVerificationError, match="GITHUB_CLIENT_PROVENANCE_UNVERIFIED"):
        AuthenticatedGitHubCliApi(executable="gh", runner=lambda *_args, **_kwargs: None)


def test_public_fetchback_rejects_unverified_injected_client_before_call() -> None:
    class Client:
        def __init__(self) -> None:
            self.called = False
        def get_json(self, *_args: Any, **_kwargs: Any) -> Any:
            self.called = True
            return {}
    manifest = _manifest()
    client = Client()
    key = CngPublicKey("IABV-G1-" + manifest.enrollment_id, PLATFORM_PROVIDER,
                       "PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED", KEY, THUMBPRINT)
    with pytest.raises(OwnerMergeVerificationError, match="GITHUB_CLIENT_PROVENANCE_UNVERIFIED"):
        _public_verify_owner_manifest_fetchback(
            PR_NUMBER, expected_manifest=manifest, expected_owner_id=EXPECTED_OWNER_ID,
            expected_server_code_revision=CODE_SHA, expected_workspace_root=r"C:\Python\IABV_v1.5",
            windows_sid=SID, cng_key=key, receipt_store=_FakeReceiptStore(), api=client, clock=lambda: NOW_UTC,
        )
    assert client.called is False
