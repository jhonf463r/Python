"""Public manifest contract for the bounded, Owner-controlled G1 enrollment.

This module prepares and validates public metadata only. It does not establish
trust, grant capabilities, create a key, fetch GitHub data, or persist a receipt.
"""
from __future__ import annotations

import base64
import hashlib
import json
import ntpath
import re
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any

from iabv_v15.services.security.github_owner_merge_bootstrap import (
    BOOTSTRAP_MANIFEST_PATH,
    EXPECTED_REPOSITORY,
    EXPECTED_REPOSITORY_ID,
    OwnerMergeVerificationError,
    _require_object,
)
from iabv_v15.services.security.windows_crypto import validate_rsa_sha256_public_key_pem

OWNER_MANIFEST_SCHEMA_VERSION = 1
ROOT_ENROLLMENT_PROFILE = "ROOT_ENROLLMENT_ONLY"
MAX_OWNER_MANIFEST_BYTES = 16 * 1024
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SID = re.compile(r"^S-1-(?:[0-9]+-){1,14}[0-9]+$", re.IGNORECASE)
_CREDENTIAL_FIELD_NAMES = frozenset({
    "access_token", "token", "client_secret", "secret", "private_key",
    "private_key_pem", "github_app_pem", "credential", "credentials",
})


@dataclass(frozen=True)
class OwnerEnrollmentManifest:
    """Versioned public bindings approved out-of-band in a dedicated PR.

    ``revocation_source_id`` is only a future provider reference. This model
    does not resolve it or establish current revocation status; G2 remains
    unestablished until a separately trusted provider exists.
    """

    enrollment_id: str
    public_key_pem: str
    windows_sid_commitment: str
    server_code_revision: str
    workspace_root: str
    issued_at_epoch: int
    expires_at_epoch: int
    revocation_source_id: str
    schema_version: int = OWNER_MANIFEST_SCHEMA_VERSION
    repository_id: int = EXPECTED_REPOSITORY_ID
    repository_full_name: str = EXPECTED_REPOSITORY
    manifest_path: str = BOOTSTRAP_MANIFEST_PATH
    capability_profile: str = ROOT_ENROLLMENT_PROFILE

    @property
    def public_key_thumbprint(self) -> str:
        validate_rsa_sha256_public_key_pem(self.public_key_pem)
        encoded = "".join(self.public_key_pem.strip().splitlines()[1:-1])
        der = base64.b64decode(encoded, validate=True)
        return hashlib.sha256(der).hexdigest()

    def to_mapping(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "repository_id": self.repository_id,
            "repository_full_name": self.repository_full_name,
            "manifest_path": self.manifest_path,
            "enrollment_id": self.enrollment_id,
            "public_key_pem": self.public_key_pem,
            "public_key_thumbprint_sha256": self.public_key_thumbprint,
            "windows_sid_commitment": self.windows_sid_commitment,
            "server_code_revision": self.server_code_revision,
            "workspace_root": self.workspace_root,
            "capability_profile": self.capability_profile,
            "issued_at_epoch": self.issued_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "revocation_source_id": self.revocation_source_id,
        }

    def canonical_bytes(self) -> bytes:
        raw = json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        if len(raw) > MAX_OWNER_MANIFEST_BYTES:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_TOO_LARGE")
        return raw

    def validate(self) -> None:
        if self.schema_version != OWNER_MANIFEST_SCHEMA_VERSION or type(self.schema_version) is not int:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_SCHEMA_VERSION_UNSUPPORTED")
        if type(self.repository_id) is not int or self.repository_id != EXPECTED_REPOSITORY_ID:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_REPOSITORY_MISMATCH")
        if self.repository_full_name != EXPECTED_REPOSITORY or self.manifest_path != BOOTSTRAP_MANIFEST_PATH:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_LOCATION_MISMATCH")
        if self.capability_profile != ROOT_ENROLLMENT_PROFILE:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_CAPABILITY_PROFILE_INVALID")
        if not isinstance(self.enrollment_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.enrollment_id):
            raise OwnerMergeVerificationError("OWNER_MANIFEST_ENROLLMENT_ID_INVALID")
        if not isinstance(self.revocation_source_id, str) or not self.revocation_source_id.strip():
            raise OwnerMergeVerificationError("OWNER_MANIFEST_REVOCATION_SOURCE_UNRESOLVED")
        if not isinstance(self.windows_sid_commitment, str) or not _SHA256.fullmatch(self.windows_sid_commitment):
            raise OwnerMergeVerificationError("OWNER_MANIFEST_SID_BINDING_INVALID")
        if not isinstance(self.server_code_revision, str) or not _SHA1.fullmatch(self.server_code_revision):
            raise OwnerMergeVerificationError("OWNER_MANIFEST_CODE_REVISION_INVALID")
        if not isinstance(self.workspace_root, str):
            raise OwnerMergeVerificationError("OWNER_MANIFEST_WORKSPACE_ROOT_INVALID")
        root = PureWindowsPath(self.workspace_root)
        if not root.is_absolute() or ntpath.normpath(self.workspace_root) != self.workspace_root or ".." in root.parts:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_WORKSPACE_ROOT_INVALID")
        if type(self.issued_at_epoch) is not int or type(self.expires_at_epoch) is not int:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_VALIDITY_INVALID")
        if self.issued_at_epoch <= 0 or self.expires_at_epoch <= self.issued_at_epoch:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_VALIDITY_INVALID")
        try:
            validate_rsa_sha256_public_key_pem(self.public_key_pem)
        except (TypeError, ValueError):
            raise OwnerMergeVerificationError("OWNER_MANIFEST_PUBLIC_KEY_INVALID") from None


def sid_commitment(windows_sid: str) -> str:
    """Return a stable SHA-256 commitment; raw SID must remain local."""
    if not isinstance(windows_sid, str) or not _SID.fullmatch(windows_sid):
        raise OwnerMergeVerificationError("WINDOWS_SID_INVALID")
    return hashlib.sha256(windows_sid.upper().encode("ascii")).hexdigest()


def parse_owner_manifest(raw: bytes) -> OwnerEnrollmentManifest:
    """Strictly parse exact manifest bytes; reject duplicates and credentials."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_OWNER_MANIFEST_BYTES:
        raise OwnerMergeVerificationError("OWNER_MANIFEST_SIZE_INVALID")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise OwnerMergeVerificationError("OWNER_MANIFEST_JSON_INVALID") from None
    _require_object(value, "OWNER_MANIFEST_SCHEMA_INVALID")
    if any(str(key).casefold() in _CREDENTIAL_FIELD_NAMES for key in value):
        raise OwnerMergeVerificationError("OWNER_MANIFEST_CREDENTIAL_FIELD_FORBIDDEN")
    expected_fields = {
        "schema_version", "repository_id", "repository_full_name", "manifest_path",
        "enrollment_id", "public_key_pem", "public_key_thumbprint_sha256",
        "windows_sid_commitment", "server_code_revision", "workspace_root",
        "capability_profile", "issued_at_epoch", "expires_at_epoch", "revocation_source_id",
    }
    forbidden_self_refs = {"manifest_commit_sha", "manifest_blob_sha", "manifest_sha256", "content_sha256"}
    if forbidden_self_refs.intersection(value):
        raise OwnerMergeVerificationError("OWNER_MANIFEST_SELF_REFERENCE_FORBIDDEN")
    if set(value) != expected_fields:
        raise OwnerMergeVerificationError("OWNER_MANIFEST_SCHEMA_INVALID")
    try:
        manifest = OwnerEnrollmentManifest(
            schema_version=value["schema_version"],
            repository_id=value["repository_id"],
            repository_full_name=value["repository_full_name"],
            manifest_path=value["manifest_path"],
            enrollment_id=value["enrollment_id"],
            public_key_pem=value["public_key_pem"],
            windows_sid_commitment=value["windows_sid_commitment"],
            server_code_revision=value["server_code_revision"],
            workspace_root=value["workspace_root"],
            capability_profile=value["capability_profile"],
            issued_at_epoch=value["issued_at_epoch"],
            expires_at_epoch=value["expires_at_epoch"],
            revocation_source_id=value["revocation_source_id"],
        )
        manifest.validate()
        if type(value["public_key_thumbprint_sha256"]) is not str or value["public_key_thumbprint_sha256"] != manifest.public_key_thumbprint:
            raise OwnerMergeVerificationError("OWNER_MANIFEST_KEY_THUMBPRINT_MISMATCH")
        return manifest
    except (KeyError, TypeError):
        raise OwnerMergeVerificationError("OWNER_MANIFEST_SCHEMA_INVALID") from None


@dataclass(frozen=True)
class OwnerManifestFetchbackReceipt:
    """Local evidence record; this does not adjudicate G1 or grant authority."""

    repository_id: int
    repository_full_name: str
    manifest_path: str
    pull_request_number: int
    merged_by_id: int
    merge_commit_sha: str
    manifest_blob_sha: str
    manifest_sha256: str
    enrollment_id: str
    schema_version: int
    public_key_thumbprint_sha256: str
    windows_sid: str
    server_code_revision: str
    workspace_root: str
    cng_provider_name: str
    cng_assurance: str
    verified_at_epoch: int
    outcome: str = "MANIFEST_FETCHBACK_VERIFIED_G1_NOT_ESTABLISHED"

    def to_mapping(self) -> dict[str, Any]:
        """Return the local evidence fields for a receipt store.

        Callers must keep this receipt local. It is not an authority token and
        must not be copied into a repository, log, or MCP response.
        """
        return {
            "repository_id": self.repository_id,
            "repository_full_name": self.repository_full_name,
            "manifest_path": self.manifest_path,
            "pull_request_number": self.pull_request_number,
            "merged_by_id": self.merged_by_id,
            "merge_commit_sha": self.merge_commit_sha,
            "manifest_blob_sha": self.manifest_blob_sha,
            "manifest_sha256": self.manifest_sha256,
            "enrollment_id": self.enrollment_id,
            "schema_version": self.schema_version,
            "public_key_thumbprint_sha256": self.public_key_thumbprint_sha256,
            "windows_sid": self.windows_sid,
            "server_code_revision": self.server_code_revision,
            "workspace_root": self.workspace_root,
            "cng_provider_name": self.cng_provider_name,
            "cng_assurance": self.cng_assurance,
            "verified_at_epoch": self.verified_at_epoch,
            "outcome": self.outcome,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
