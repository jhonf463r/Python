"""Authenticated, read-only GitHub fetch-back for the enrollment manifest.

Authentication is delegated to the existing GitHub CLI login. This module
never asks for, prints, or stores a token. It is not wired to MCP or startup.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from iabv_v15.services.security.github_owner_merge_bootstrap import (
    BOOTSTRAP_MANIFEST_PATH,
    EXPECTED_BASE_BRANCH,
    EXPECTED_REPOSITORY,
    EXPECTED_REPOSITORY_ID,
    MAX_API_RESPONSE_BYTES,
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
from iabv_v15.services.security.windows_cng_key_store import CngPublicKey
from iabv_v15.services.security.windows_cng_key_store import PLATFORM_PROVIDER, SOFTWARE_PROVIDER

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_API_PATH_SUFFIX = re.compile(r"(?:/[A-Za-z0-9._~-]+)*$")


class OwnerManifestReceiptStore(Protocol):
    """Host-owned durable local receipt boundary.

    Implementations must atomically create one record per enrollment ID,
    return the existing record for an identical verified merge, and reject a
    different record for that ID. This contract alone does not prove that a
    production store is durable or protected.
    """

    def record_if_absent(self, receipt: OwnerManifestFetchbackReceipt) -> OwnerManifestFetchbackReceipt: ...


class AuthenticatedGitHubCliApi:
    """Small API adapter that uses gh's existing credential store internally."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        runner: Callable[..., Any] = subprocess.run,
    ) -> None:
        self.executable = executable or shutil.which("gh")
        self._runner = runner
        self.last_link_relations: set[str] = set()
        if not self.executable:
            raise OwnerMergeVerificationError("GITHUB_CLI_UNAVAILABLE")

    def __enter__(self) -> "AuthenticatedGitHubCliApi":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get_json(self, path: str, *, params: Mapping[str, object] | None = None) -> Any:
        root = f"/repos/{EXPECTED_REPOSITORY}"
        if (
            not isinstance(path, str)
            or len(path) > 1024
            or not path.startswith(root)
            or _API_PATH_SUFFIX.fullmatch(path[len(root):]) is None
            or any(part in {".", ".."} for part in path.split("/"))
            or any(char in path for char in "?#\\")
        ):
            raise OwnerMergeVerificationError("API_PATH_OUT_OF_SCOPE")
        args = [self.executable, "api", path, "--method", "GET"]
        query = params or {}
        for name, value in query.items():
            if not re.fullmatch(r"[a-z_]+", name) or isinstance(value, bool) or not isinstance(value, (str, int)):
                raise OwnerMergeVerificationError("API_QUERY_INVALID")
            if isinstance(value, str) and (len(value) > 256 or re.fullmatch(r"[A-Za-z0-9._~-]+", value) is None):
                raise OwnerMergeVerificationError("API_QUERY_INVALID")
            args.extend(["-f", f"{name}={value}"])
        paginate = path.endswith("/files") or ("/commits/" in path and path.endswith("/pulls"))
        if paginate:
            args.extend(["--paginate", "--slurp"])
        env = os.environ.copy()
        env["GH_PROMPT_DISABLED"] = "1"
        env["GIT_TERMINAL_PROMPT"] = "0"
        try:
            result = self._runner(
                args,
                capture_output=True,
                check=False,
                timeout=20,
                env=env,
                shell=False,
                stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise OwnerMergeVerificationError("AUTHENTICATED_GITHUB_REQUEST_FAILED") from None
        raw = result.stdout if isinstance(result.stdout, bytes) else str(result.stdout or "").encode("utf-8")
        error = result.stderr if isinstance(result.stderr, bytes) else str(result.stderr or "").encode("utf-8", errors="replace")
        if result.returncode != 0:
            text = error.decode("utf-8", errors="replace").casefold()
            code = "GITHUB_AUTHENTICATION_OR_PERMISSION_FAILED" if any(x in text for x in ("http 401", "http 403", "http 404")) else "AUTHENTICATED_GITHUB_REQUEST_FAILED"
            raise OwnerMergeVerificationError(code)
        if len(raw) > MAX_API_RESPONSE_BYTES:
            raise OwnerMergeVerificationError("GITHUB_API_RESPONSE_TOO_LARGE")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise OwnerMergeVerificationError("GITHUB_API_JSON_INVALID") from None
        if paginate:
            if not isinstance(payload, list) or any(not isinstance(page, list) for page in payload):
                raise OwnerMergeVerificationError("GITHUB_API_PAGINATION_INVALID")
            return [item for page in payload for item in page]
        return payload


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
    api: AuthenticatedGitHubCliApi | Any | None = None,
    clock: Callable[[], datetime] | None = None,
) -> OwnerManifestFetchbackReceipt:
    """Verify an Owner-merged manifest at the merge commit and current main.

    Returns evidence only after the explicitly supplied receipt-store boundary
    records it idempotently. No production store is supplied here. This does
    not consume a challenge, enroll a G1 root, enable a gate, or change runtime
    authorization state.
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
    now_fn = clock or (lambda: datetime.now(timezone.utc))
    own_api = api is None
    client = AuthenticatedGitHubCliApi() if own_api else api
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
        if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict) or files[0].get("filename") != BOOTSTRAP_MANIFEST_PATH or files[0].get("status") not in {"added", "modified"}:
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
        if own_api:
            client.__exit__(None, None, None)
