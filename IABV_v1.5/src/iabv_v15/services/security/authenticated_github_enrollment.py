"""Fail-closed candidate logic for read-only enrollment-manifest fetch-back.

The fixed Authenticode-pinned CLI adapter is a source candidate. Public
fetch-back stays disabled pending exact candidate review and separate
production-boundary evidence. The injectable verifier core is test-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from iabv_v15.services.security.github_owner_merge_bootstrap import (
    BOOTSTRAP_MANIFEST_PATH,
    EXPECTED_BASE_BRANCH,
    EXPECTED_REPOSITORY,
    EXPECTED_REPOSITORY_ID,
    OwnerMergeVerificationError,
    _fetch_manifest,
    _require_object,
)
from iabv_v15.services.security.owner_enrollment_manifest import (
    OwnerEnrollmentManifest,
    OwnerManifestFetchbackReceipt,
    parse_owner_manifest,
    sid_commitment,
)
from iabv_v15.services.security.windows_cng_key_store import CngKeyReader, CngPublicKey
from iabv_v15.services.security.windows_cng_key_store import PLATFORM_PROVIDER, SOFTWARE_PROVIDER

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_POLICY_ID = "IABV_GITHUB_CLI_AUTHENTICODE_PIN_V1"
_APPROVED_EXECUTABLE = r"C:\Program Files\GitHub CLI\gh.exe"
_APPROVED_SIGNATURE_STATUS = "Valid"
_APPROVED_SIGNER_THUMBPRINT = "9A483710566AC7B58A19D32B4A64E44361EA7350"
_APPROVED_EXECUTABLE_SHA256 = "249613CC9DFB61EB267ACFA08C2253EDEA271BBBEC8F3CA3BF8D949A6575D60B"


@dataclass(frozen=True, slots=True)
class _GitHubCliTrustPolicy:
    policy_id: str
    executable_path: str
    signature_status: str
    signer_thumbprint: str
    executable_sha256: str


@dataclass(frozen=True, slots=True)
class _AuthenticodeEvidence:
    status: str
    signer_thumbprint: str


def _approved_github_cli_policy() -> _GitHubCliTrustPolicy:
    """Return the source-versioned policy approved for this candidate only."""
    return _GitHubCliTrustPolicy(
        policy_id=_POLICY_ID,
        executable_path=_APPROVED_EXECUTABLE,
        signature_status=_APPROVED_SIGNATURE_STATUS,
        signer_thumbprint=_APPROVED_SIGNER_THUMBPRINT,
        executable_sha256=_APPROVED_EXECUTABLE_SHA256,
    )


class OwnerManifestReceiptStore(Protocol):
    """Host-owned durable local receipt boundary.

    Implementations must atomically create one record per enrollment ID,
    return the existing record for an identical verified merge, and reject a
    different record for that ID. This contract alone does not prove that a
    production store is durable or protected.
    """

    def record_if_absent(self, receipt: OwnerManifestFetchbackReceipt) -> OwnerManifestFetchbackReceipt: ...


class AuthenticatedGitHubCliApi:
    """Fixed-policy GitHub CLI adapter; verification precedes every request.

    The pinned file handle denies write/delete sharing and remains open while
    subprocess creation resolves the approved absolute path. This prevents a
    normal user-mode replacement between verification and launch. It does not
    defend against a privileged/kernel actor or prove build-workflow provenance.
    """

    __slots__ = ("_policy", "_pin", "_identity", "_runner", "_closed", "_initialized")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_initialized", False):
            raise AttributeError("verified GitHub client identity is immutable")
        object.__setattr__(self, name, value)

    def __init__(self) -> None:
        policy = _approved_github_cli_policy()
        pin = _open_pinned_executable(policy.executable_path)
        try:
            self._identity = _verify_pinned_executable(
                pin, policy=policy, verifier=_windows_authenticode_verifier,
            )
        except Exception:
            pin.close()
            raise
        self._policy = policy
        self._pin = pin
        self._runner = subprocess.run
        self._closed = False
        self._initialized = True

    def __enter__(self) -> "AuthenticatedGitHubCliApi":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            object.__setattr__(self, "_closed", True)
            self._pin.close()

    def get_json(self, path: str, *, params: Mapping[str, object] | None = None) -> Any:
        repo_root = f"/repos/{EXPECTED_REPOSITORY}"
        if (
            self._closed or not isinstance(path, str)
            or (path != repo_root and not path.startswith(repo_root + "/"))
            or any(token in path for token in ("\\", "//", "?", "#", "\r", "\n"))
            or any(segment in {".", ".."} for segment in path.split("/"))
        ):
            raise OwnerMergeVerificationError("GITHUB_CLIENT_REQUEST_INVALID")
        args = [self._policy.executable_path, "api", path]
        if params is not None:
            if not isinstance(params, Mapping):
                raise OwnerMergeVerificationError("GITHUB_CLIENT_REQUEST_INVALID")
            for key, value in params.items():
                if (
                    not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", key)
                    or type(value) not in {str, int, bool}
                ):
                    raise OwnerMergeVerificationError("GITHUB_CLIENT_REQUEST_INVALID")
                args.extend(("-f", f"{key}={str(value).lower() if type(value) is bool else value}"))
        if self._pin.sha256() != self._identity.executable_sha256:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_PROVENANCE_UNVERIFIED")
        try:
            result = self._runner(
                args,
                executable=self._policy.executable_path,
                capture_output=True,
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
                timeout=30,
            )
        except Exception:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_CALL_FAILED") from None
        if getattr(result, "returncode", None) != 0:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_CALL_FAILED")
        stdout = getattr(result, "stdout", None)
        if not isinstance(stdout, bytes):
            raise OwnerMergeVerificationError("GITHUB_CLIENT_RESPONSE_INVALID")
        try:
            return json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise OwnerMergeVerificationError("GITHUB_CLIENT_RESPONSE_INVALID") from None


@dataclass(frozen=True, slots=True)
class _ExecutableIdentity:
    executable_sha256: str
    file_id: tuple[int, int, int]


class _PinnedExecutable:
    """A Windows read handle opened without write/delete sharing."""

    def __init__(self, file_object: Any, file_id: tuple[int, int, int]) -> None:
        self._file = file_object
        self.file_id = file_id
        self._closed = False

    def sha256(self) -> str:
        if self._closed:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_PROVENANCE_UNVERIFIED")
        try:
            self._file.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: self._file.read(1024 * 1024), b""):
                digest.update(chunk)
            self._file.seek(0)
            return digest.hexdigest().upper()
        except Exception:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_FILE_CHANGED_OR_UNREADABLE") from None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._file.close()


def _open_pinned_executable(path: str) -> _PinnedExecutable:
    """Open the approved image while denying later write/delete handles."""
    if os.name != "nt" or not isinstance(path, str) or not os.path.isabs(path):
        raise OwnerMergeVerificationError("GITHUB_CLIENT_FILE_UNAVAILABLE")
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        class _ByHandleFileInformation(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", wintypes.DWORD),
                ("ftCreationTime", wintypes.FILETIME),
                ("ftLastAccessTime", wintypes.FILETIME),
                ("ftLastWriteTime", wintypes.FILETIME),
                ("dwVolumeSerialNumber", wintypes.DWORD),
                ("nFileSizeHigh", wintypes.DWORD),
                ("nFileSizeLow", wintypes.DWORD),
                ("nNumberOfLinks", wintypes.DWORD),
                ("nFileIndexHigh", wintypes.DWORD),
                ("nFileIndexLow", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create_file.restype = wintypes.HANDLE
        get_info = kernel32.GetFileInformationByHandle
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation)]
        get_info.restype = wintypes.BOOL
        get_final_path = kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        get_final_path.restype = wintypes.DWORD
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        handle = create_file(path, 0x80000000, 0x00000001, None, 3, 0x00000080, None)
        invalid = ctypes.c_void_p(-1).value
        if handle == invalid:
            raise OSError(ctypes.get_last_error())
        info = _ByHandleFileInformation()
        if not get_info(handle, ctypes.byref(info)) or info.dwFileAttributes & 0x00000400:
            raise OSError("file identity unavailable or reparse point")
        final_buffer = ctypes.create_unicode_buffer(32768)
        final_length = get_final_path(handle, final_buffer, len(final_buffer), 0)
        if not final_length or final_length >= len(final_buffer):
            raise OSError("final path unavailable")
        final_path = final_buffer.value
        if final_path.startswith("\\\\?\\"):
            final_path = final_path[4:]
        if os.path.normcase(os.path.abspath(final_path)) != os.path.normcase(os.path.abspath(path)):
            raise OSError("resolved file path differs")
        file_id = (
            int(info.dwVolumeSerialNumber),
            (int(info.nFileIndexHigh) << 32) | int(info.nFileIndexLow),
            (int(info.nFileSizeHigh) << 32) | int(info.nFileSizeLow),
        )
        fd = msvcrt.open_osfhandle(int(handle), os.O_RDONLY | os.O_BINARY)
        handle = None  # ownership transferred to the CRT descriptor
        file_object = os.fdopen(fd, "rb", closefd=True)
        fd = None  # ownership transferred to the Python file object
        return _PinnedExecutable(file_object, file_id)
    except OwnerMergeVerificationError:
        raise
    except Exception:
        raise OwnerMergeVerificationError("GITHUB_CLIENT_FILE_UNAVAILABLE") from None
    finally:
        try:
            if "handle" in locals() and handle is not None and handle != invalid:
                close_handle(handle)
        except Exception:
            pass
        try:
            if "fd" in locals() and fd is not None:
                os.close(fd)
        except Exception:
            pass


def _windows_authenticode_verifier(path: str) -> Mapping[str, object]:
    """Ask the Windows PowerShell Authenticode provider; never run gh here."""
    if os.name != "nt" or path != _APPROVED_EXECUTABLE:
        raise OwnerMergeVerificationError("GITHUB_CLIENT_VERIFIER_UNAVAILABLE")
    try:
        import ctypes
        from ctypes import wintypes

        get_windows_directory = ctypes.WinDLL("kernel32", use_last_error=True).GetWindowsDirectoryW
        get_windows_directory.argtypes = [wintypes.LPWSTR, wintypes.UINT]
        get_windows_directory.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_windows_directory(buffer, len(buffer))
        if not length or length >= len(buffer):
            raise OSError("Windows directory unavailable")
        powershell = os.path.join(buffer.value, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        script = (
            "$ErrorActionPreference='Stop'; $s=Get-AuthenticodeSignature -LiteralPath '"
            + path.replace("'", "''")
            + "'; if ($null -eq $s.SignerCertificate) { throw 'Signer missing' }; "
            + "[ordered]@{status=$s.Status.ToString();thumbprint=$s.SignerCertificate.Thumbprint}|ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            check=False,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=15,
        )
        if result.returncode != 0 or not isinstance(result.stdout, bytes):
            raise ValueError("Authenticode verifier failed")
        value = json.loads(result.stdout.decode("utf-8"))
        if not isinstance(value, dict) or set(value) != {"status", "thumbprint"}:
            raise ValueError("Malformed Authenticode result")
        if not isinstance(value["status"], str) or not isinstance(value["thumbprint"], str):
            raise ValueError("Malformed Authenticode fields")
        return _AuthenticodeEvidence(value["status"], value["thumbprint"].replace(" ", "").upper())
    except Exception:
        raise OwnerMergeVerificationError("GITHUB_CLIENT_VERIFIER_FAILED") from None


def _verify_pinned_executable(
    pin: _PinnedExecutable,
    *,
    policy: _GitHubCliTrustPolicy,
    verifier: Callable[[str], object],
) -> _ExecutableIdentity:
    approved = _approved_github_cli_policy()
    if type(policy) is not _GitHubCliTrustPolicy or policy != approved:
        raise OwnerMergeVerificationError("GITHUB_CLIENT_POLICY_INVALID")
    if not isinstance(pin, _PinnedExecutable) or not callable(verifier):
        raise OwnerMergeVerificationError("GITHUB_CLIENT_PROVENANCE_UNVERIFIED")
    if not os.path.isabs(policy.executable_path) or os.path.normcase(os.path.abspath(policy.executable_path)) != os.path.normcase(os.path.abspath(_APPROVED_EXECUTABLE)):
        raise OwnerMergeVerificationError("GITHUB_CLIENT_PATH_MISMATCH")
    try:
        digest_before = pin.sha256()
        result = verifier(policy.executable_path)
        if type(result) is _AuthenticodeEvidence:
            status, thumbprint = result.status, result.signer_thumbprint
        elif isinstance(result, Mapping) and set(result) == {"status", "thumbprint"}:
            status, thumbprint = result["status"], result["thumbprint"]
        else:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_SIGNATURE_RESULT_INVALID")
        if type(status) is not str or type(thumbprint) is not str:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_SIGNATURE_RESULT_INVALID")
        if status != policy.signature_status:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_SIGNATURE_INVALID")
        if thumbprint.replace(" ", "").upper() != policy.signer_thumbprint:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_SIGNER_MISMATCH")
        digest_after = pin.sha256()
        if digest_before != digest_after:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_FILE_CHANGED")
        if digest_after != policy.executable_sha256:
            raise OwnerMergeVerificationError("GITHUB_CLIENT_HASH_MISMATCH")
        return _ExecutableIdentity(digest_after, pin.file_id)
    except OwnerMergeVerificationError:
        raise
    except Exception:
        raise OwnerMergeVerificationError("GITHUB_CLIENT_VERIFIER_FAILED") from None


def verify_owner_manifest_fetchback(
    pull_request_number: int,
    *,
    expected_manifest: OwnerEnrollmentManifest,
    expected_owner_id: int,
    expected_server_code_revision: str,
    expected_workspace_root: str,
    windows_sid: str,
    cng_key: CngPublicKey,
    receipt_store: OwnerManifestReceiptStore,
    clock: Callable[[], datetime] | None = None,
) -> OwnerManifestFetchbackReceipt:
    """Keep public fetch-back closed until the candidate is independently reviewed."""
    del (
        pull_request_number, expected_manifest, expected_owner_id,
        expected_server_code_revision, expected_workspace_root, windows_sid,
        cng_key, receipt_store, clock,
    )
    raise OwnerMergeVerificationError("GITHUB_CLIENT_PROVENANCE_UNVERIFIED")


def _verify_owner_manifest_fetchback_with_api(
    pull_request_number: int,
    *,
    expected_manifest: OwnerEnrollmentManifest,
    expected_owner_id: int,
    expected_server_code_revision: str,
    expected_workspace_root: str,
    windows_sid: str,
    cng_key: CngPublicKey,
    key_store: CngKeyReader,
    receipt_store: OwnerManifestReceiptStore,
    api: Any,
    clock: Callable[[], datetime] | None = None,
) -> OwnerManifestFetchbackReceipt:
    """Pure verifier core for synthetic tests; not a production trust path.

    Returns evidence only after the explicitly supplied receipt-store boundary
    records it idempotently. No production store is supplied here. This does
    not consume a challenge, enroll a G1 root, enable a gate, or change runtime
    authorization state. Production entry is separately fail-closed until a
    trusted GitHub response producer is implemented.
    """
    if type(pull_request_number) is not int or pull_request_number < 1 or type(expected_owner_id) is not int or expected_owner_id < 1:
        raise OwnerMergeVerificationError("ENROLLMENT_CONTEXT_INVALID")
    expected_manifest.validate()
    if (
        expected_manifest.server_code_revision != expected_server_code_revision
        or expected_manifest.workspace_root != expected_workspace_root
    ):
        raise OwnerMergeVerificationError("LOCAL_ENROLLMENT_BINDING_MISMATCH")
    if receipt_store is None:
        raise OwnerMergeVerificationError("LOCAL_RECEIPT_STORE_REQUIRED")
    if sid_commitment(windows_sid) != expected_manifest.windows_sid_commitment:
        raise OwnerMergeVerificationError("LOCAL_SID_BINDING_MISMATCH")
    if (
        cng_key.key_name != "IABV-G1-" + expected_manifest.enrollment_id
        or cng_key.public_key_pem != expected_manifest.public_key_pem
        or cng_key.thumbprint_sha256 != expected_manifest.public_key_thumbprint
        or cng_key.provider_name not in {PLATFORM_PROVIDER, SOFTWARE_PROVIDER}
        or (cng_key.provider_name == PLATFORM_PROVIDER and not cng_key.assurance.startswith("PLATFORM_PROVIDER_SELECTED; HARDWARE_BACKING_NOT_INDEPENDENTLY_VERIFIED"))
        or (cng_key.provider_name == SOFTWARE_PROVIDER and cng_key.assurance != "SOFTWARE_PROVIDER_LOWER_ASSURANCE")
    ):
        raise OwnerMergeVerificationError("LOCAL_CNG_KEY_BINDING_MISMATCH")
    try:
        persisted_key = key_store.read_existing_key(expected_manifest.enrollment_id, cng_key.provider_name)
    except Exception:
        raise OwnerMergeVerificationError("LOCAL_CNG_PERSISTED_KEY_UNAVAILABLE") from None
    if persisted_key != cng_key:
        raise OwnerMergeVerificationError("LOCAL_CNG_PERSISTED_KEY_MISMATCH")
    now_fn = clock or (lambda: datetime.now(timezone.utc))
    client = api
    try:
        now = now_fn()
        if now.tzinfo is None or now.utcoffset() is None:
            raise OwnerMergeVerificationError("VERIFICATION_CLOCK_INVALID")
        now_epoch = int(now.timestamp())
        if now_epoch < expected_manifest.issued_at_epoch or now_epoch >= expected_manifest.expires_at_epoch:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_NOT_CURRENT")
        root = f"/repos/{EXPECTED_REPOSITORY}"
        repo = client.get_json(root)
        _require_object(repo, "REPOSITORY_RESPONSE_INVALID")
        if repo.get("private") is not True or type(repo.get("id")) is not int or repo.get("id") != EXPECTED_REPOSITORY_ID or repo.get("full_name") != EXPECTED_REPOSITORY:
            raise OwnerMergeVerificationError("REPOSITORY_IDENTITY_MISMATCH")
        pr = client.get_json(f"{root}/pulls/{pull_request_number}")
        _require_object(pr, "PULL_REQUEST_RESPONSE_INVALID")
        merged_by = pr.get("merged_by")
        base = pr.get("base")
        if not isinstance(merged_by, dict) or not isinstance(base, dict) or not isinstance(base.get("repo"), dict):
            raise OwnerMergeVerificationError("PULL_REQUEST_METADATA_INVALID")
        if pr.get("number") != pull_request_number or pr.get("state") != "closed" or pr.get("merged") is not True:
            raise OwnerMergeVerificationError("PULL_REQUEST_NOT_MERGED")
        if type(merged_by.get("id")) is not int or merged_by.get("id") != expected_owner_id:
            raise OwnerMergeVerificationError("UNAUTHORIZED_MERGE_ACTOR")
        if base.get("ref") != EXPECTED_BASE_BRANCH or type(base["repo"].get("id")) is not int or base["repo"].get("id") != EXPECTED_REPOSITORY_ID or base["repo"].get("full_name") != EXPECTED_REPOSITORY:
            raise OwnerMergeVerificationError("PULL_REQUEST_BASE_MISMATCH")
        merge_sha = pr.get("merge_commit_sha")
        if not isinstance(merge_sha, str) or not _SHA1.fullmatch(merge_sha):
            raise OwnerMergeVerificationError("MERGE_COMMIT_MISSING_OR_INVALID")
        merged_at = pr.get("merged_at")
        if not isinstance(merged_at, str):
            raise OwnerMergeVerificationError("MERGE_TIME_INVALID")
        try:
            merged_time = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
        except ValueError:
            raise OwnerMergeVerificationError("MERGE_TIME_INVALID") from None
        if merged_time.tzinfo is None or merged_time.utcoffset() is None or int(merged_time.timestamp()) < expected_manifest.issued_at_epoch or int(merged_time.timestamp()) >= expected_manifest.expires_at_epoch:
            raise OwnerMergeVerificationError("MERGE_OUTSIDE_MANIFEST_VALIDITY")
        files = client.get_json(f"{root}/pulls/{pull_request_number}/files", params={"per_page": 100})
        if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict) or files[0].get("filename") != BOOTSTRAP_MANIFEST_PATH or files[0].get("status") != "added":
            raise OwnerMergeVerificationError("MANIFEST_NOT_EXCLUSIVE_PR_CHANGE")
        branch = client.get_json(f"{root}/branches/{EXPECTED_BASE_BRANCH}")
        _require_object(branch, "MAIN_BRANCH_RESPONSE_INVALID")
        branch_commit = branch.get("commit")
        _require_object(branch_commit, "MAIN_BRANCH_COMMIT_INVALID")
        main_sha = branch_commit.get("sha")
        if not isinstance(main_sha, str) or not _SHA1.fullmatch(main_sha):
            raise OwnerMergeVerificationError("MAIN_SHA_INVALID")
        commit = client.get_json(f"{root}/commits/{merge_sha}")
        _require_object(commit, "MERGE_COMMIT_RESPONSE_INVALID")
        if commit.get("sha") != merge_sha:
            raise OwnerMergeVerificationError("MERGE_COMMIT_IDENTITY_MISMATCH")
        associated = client.get_json(f"{root}/commits/{merge_sha}/pulls", params={"per_page": 100})
        if not isinstance(associated, list) or not any(
            isinstance(item, dict) and item.get("number") == pull_request_number
            and isinstance(item.get("base"), dict) and item["base"].get("ref") == EXPECTED_BASE_BRANCH
            and isinstance(item["base"].get("repo"), dict)
            and type(item["base"]["repo"].get("id")) is int
            and item["base"]["repo"].get("id") == EXPECTED_REPOSITORY_ID
            and item["base"]["repo"].get("full_name") == EXPECTED_REPOSITORY
            for item in associated
        ):
            raise OwnerMergeVerificationError("MERGE_COMMIT_NOT_ASSOCIATED_WITH_PR")
        compare = client.get_json(f"{root}/compare/{merge_sha}...{main_sha}")
        _require_object(compare, "MAIN_ANCESTRY_RESPONSE_INVALID")
        merge_base = compare.get("merge_base_commit")
        _require_object(merge_base, "MAIN_MERGE_BASE_INVALID")
        if compare.get("status") not in {"ahead", "identical"} or merge_base.get("sha") != merge_sha:
            raise OwnerMergeVerificationError("MERGE_COMMIT_NOT_IN_MAIN")
        merged_bytes, blob_sha = _fetch_manifest(client, root, merge_sha)
        current_bytes, current_blob = _fetch_manifest(client, root, main_sha)
        manifest = parse_owner_manifest(merged_bytes)
        if merged_bytes != expected_manifest.canonical_bytes() or manifest != expected_manifest or current_bytes != merged_bytes or current_blob != blob_sha:
            raise OwnerMergeVerificationError("CURRENT_MAIN_MANIFEST_MISMATCH")
        branch_after = client.get_json(f"{root}/branches/{EXPECTED_BASE_BRANCH}")
        _require_object(branch_after, "MAIN_BRANCH_RECHECK_INVALID")
        if not isinstance(branch_after.get("commit"), dict) or branch_after["commit"].get("sha") != main_sha:
            raise OwnerMergeVerificationError("MAIN_MOVED_DURING_VERIFICATION")
        repo_after = client.get_json(root)
        if not isinstance(repo_after, dict) or type(repo_after.get("id")) is not int or repo_after.get("id") != EXPECTED_REPOSITORY_ID or repo_after.get("full_name") != EXPECTED_REPOSITORY or repo_after.get("private") is not True:
            raise OwnerMergeVerificationError("REPOSITORY_IDENTITY_CHANGED")
        receipt = OwnerManifestFetchbackReceipt(
            repository_id=EXPECTED_REPOSITORY_ID,
            repository_full_name=EXPECTED_REPOSITORY,
            manifest_path=BOOTSTRAP_MANIFEST_PATH,
            pull_request_number=pull_request_number,
            merged_by_id=expected_owner_id,
            merge_commit_sha=merge_sha,
            manifest_blob_sha=blob_sha,
            manifest_sha256=hashlib.sha256(merged_bytes).hexdigest(),
            enrollment_id=manifest.enrollment_id,
            schema_version=manifest.schema_version,
            public_key_thumbprint_sha256=manifest.public_key_thumbprint,
            windows_sid=windows_sid,
            server_code_revision=manifest.server_code_revision,
            workspace_root=manifest.workspace_root,
            cng_provider_name=cng_key.provider_name,
            cng_assurance=cng_key.assurance,
            verified_at_epoch=now_epoch,
        )
        try:
            recorded = receipt_store.record_if_absent(receipt)
        except OwnerMergeVerificationError:
            raise
        except Exception:
            raise OwnerMergeVerificationError("LOCAL_RECEIPT_PERSISTENCE_FAILED") from None
        if not isinstance(recorded, OwnerManifestFetchbackReceipt):
            raise OwnerMergeVerificationError("LOCAL_RECEIPT_PERSISTENCE_FAILED")
        current_evidence = receipt.to_mapping()
        stored_evidence = recorded.to_mapping()
        current_evidence.pop("verified_at_epoch", None)
        stored_evidence.pop("verified_at_epoch", None)
        if current_evidence != stored_evidence:
            raise OwnerMergeVerificationError("LOCAL_RECEIPT_CONFLICT")
        return recorded
    finally:
        pass
