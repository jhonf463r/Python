"""Read-only verification of the GitHub Owner merge event for G1 bootstrap.

This module verifies an external governance event and an exact manifest. It does
not enroll a key, persist/consume a nonce, authenticate a local Windows
principal, create an issuer, or authorize a protected read. Those operations
require a separately protected issuer process and durable state.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import quote

import httpx

from iabv_v15.services.security.windows_crypto import (
    InvalidRsaPublicKey,
    validate_rsa_sha256_public_key_pem,
)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
EXPECTED_REPOSITORY = "jhonf463r/Python"
EXPECTED_REPOSITORY_ID = 860009771
EXPECTED_OWNER_LOGIN = "jhonf463r"
EXPECTED_OWNER_ID = 28608338
EXPECTED_BASE_BRANCH = "main"
BOOTSTRAP_MANIFEST_PATH = ".github/iabv-g1-bootstrap-manifest.json"
# Version 2 adds required server_id and issuer_id bindings. Version 1 is
# intentionally rejected rather than interpreted with the expanded schema.
MANIFEST_SCHEMA_VERSION = 2
MAX_MANIFEST_BYTES = 16 * 1024
MAX_API_RESPONSE_BYTES = 256 * 1024
MAX_CHALLENGE_TTL = timedelta(minutes=15)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")


class OwnerMergeVerificationError(RuntimeError):
    """A closed failure: no error returned by this module grants authority."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class G1EnrollmentChallenge:
    """Values an external Owner merge must approve exactly.

    The issuer must create and retain this challenge outside the MCP reader.
    This value object alone provides no durable replay protection.
    """

    challenge_id: str
    nonce: str
    server_id: str
    issuer_id: str
    instance_id: str
    service_fingerprint: str
    issuer_public_key_pem: str
    local_principal_commitment: str
    scopes: tuple[str, ...]
    policy_version: int
    issued_at_epoch: int
    expires_at_epoch: int

    @classmethod
    def issue(
        cls,
        *,
        server_id: str,
        issuer_id: str,
        instance_id: str,
        service_fingerprint: str,
        issuer_public_key_pem: str,
        local_principal_commitment: str,
        scopes: tuple[str, ...],
        policy_version: int,
        ttl: timedelta = timedelta(minutes=10),
    ) -> "G1EnrollmentChallenge":
        issued = datetime.now(timezone.utc)
        if issued.tzinfo is None or issued.utcoffset() is None:
            raise ValueError("challenge clock must be timezone-aware")
        seconds = int(ttl.total_seconds())
        if seconds <= 0 or ttl > MAX_CHALLENGE_TTL:
            raise ValueError("challenge TTL is outside the permitted window")
        issued_epoch = int(issued.timestamp())
        challenge = cls(
            challenge_id=uuid.uuid4().hex,
            nonce=secrets.token_urlsafe(32),
            server_id=server_id,
            issuer_id=issuer_id,
            instance_id=instance_id,
            service_fingerprint=service_fingerprint,
            issuer_public_key_pem=issuer_public_key_pem,
            local_principal_commitment=local_principal_commitment,
            scopes=scopes,
            policy_version=policy_version,
            issued_at_epoch=issued_epoch,
            expires_at_epoch=issued_epoch + seconds,
        )
        challenge.validate(now=issued)
        return challenge

    def expected_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "challenge_id": self.challenge_id,
            "nonce": self.nonce,
            "server_id": self.server_id,
            "issuer_id": self.issuer_id,
            "instance_id": self.instance_id,
            "service_fingerprint": self.service_fingerprint,
            "issuer_public_key_pem": self.issuer_public_key_pem,
            "local_principal_commitment": self.local_principal_commitment,
            "scopes": list(self.scopes),
            "policy_version": self.policy_version,
            "issued_at_epoch": self.issued_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "revoked": False,
        }

    def validate(self, *, now: datetime | None = None) -> None:
        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise OwnerMergeVerificationError("INVALID_VERIFICATION_CLOCK")
        if not isinstance(self.challenge_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.challenge_id):
            raise OwnerMergeVerificationError("INVALID_CHALLENGE_ID")
        if not isinstance(self.nonce, str) or not _NONCE_RE.fullmatch(self.nonce):
            raise OwnerMergeVerificationError("INVALID_CHALLENGE_NONCE")
        if not isinstance(self.server_id, str) or not self.server_id:
            raise OwnerMergeVerificationError("INVALID_SERVER_ID")
        if not isinstance(self.issuer_id, str) or not self.issuer_id:
            raise OwnerMergeVerificationError("INVALID_ISSUER_ID")
        if not isinstance(self.instance_id, str):
            raise OwnerMergeVerificationError("INVALID_INSTANCE_ID")
        try:
            uuid.UUID(self.instance_id)
        except (ValueError, AttributeError, TypeError):
            raise OwnerMergeVerificationError("INVALID_INSTANCE_ID") from None
        if not isinstance(self.service_fingerprint, str) or not _SHA256_RE.fullmatch(self.service_fingerprint):
            raise OwnerMergeVerificationError("INVALID_SERVICE_FINGERPRINT")
        _validate_public_key_pem(self.issuer_public_key_pem)
        if not isinstance(self.local_principal_commitment, str) or not _SHA256_RE.fullmatch(self.local_principal_commitment):
            raise OwnerMergeVerificationError("INVALID_PRINCIPAL_COMMITMENT")
        if (
            type(self.scopes) is not tuple
            or not self.scopes
            or any(not isinstance(scope, str) or not scope or len(scope) > 128 for scope in self.scopes)
            or len(set(self.scopes)) != len(self.scopes)
        ):
            raise OwnerMergeVerificationError("INVALID_SCOPE")
        if type(self.policy_version) is not int or self.policy_version < 1:
            raise OwnerMergeVerificationError("INVALID_POLICY_VERSION")
        if type(self.issued_at_epoch) is not int or type(self.expires_at_epoch) is not int:
            raise OwnerMergeVerificationError("INVALID_CHALLENGE_TIME")
        if self.expires_at_epoch <= self.issued_at_epoch:
            raise OwnerMergeVerificationError("INVALID_CHALLENGE_TIME")
        if self.expires_at_epoch - self.issued_at_epoch > int(MAX_CHALLENGE_TTL.total_seconds()):
            raise OwnerMergeVerificationError("CHALLENGE_TTL_EXCEEDED")
        current_epoch = int(instant.timestamp())
        if current_epoch < self.issued_at_epoch:
            raise OwnerMergeVerificationError("CHALLENGE_NOT_YET_VALID")
        if current_epoch >= self.expires_at_epoch:
            raise OwnerMergeVerificationError("CHALLENGE_EXPIRED")


@dataclass(frozen=True)
class OwnerMergeVerificationEvidence:
    """Observed remote facts; intentionally not an enrollment/read grant."""

    pull_request_number: int
    merge_commit_sha: str
    main_sha: str
    manifest_git_blob_sha: str
    merged_by_id: int
    challenge_id: str
    policy_version: int
    manifest_sha256: str


@dataclass(frozen=True)
class OwnerBootstrapChallengeConsumption:
    """Issuer-reported one-use challenge consumption result.

    This record is correlatable metadata, not proof that a durable store
    consumed the challenge. That guarantee requires the real issuer-owned
    store implementation and its authenticated process boundary.
    """

    enrollment_id: str
    challenge_id: str
    nonce: str
    outcome: str
    consumed_at_epoch: int
    store_version: int
    consumption_reference: str


@dataclass(frozen=True)
class OwnerBootstrapTrustRegistryPersistence:
    """Issuer-reported identity of a persisted trust-registry record.

    A reference/version in this value object does not prove persistence or
    registry protection; the actual registry adapter must establish both.
    """

    enrollment_id: str
    outcome: str
    registry_id: str
    registry_version: int
    record_id: str
    persisted_at_epoch: int
    persistence_reference: str


@dataclass(frozen=True)
class OwnerBootstrapEnrollmentReceipt:
    """Correlate Owner, challenge, issuer, verified merge and enrollment steps.

    This is the result contract returned by a future host-owned boundary. It
    is not an autonomous trust assertion and cannot prove that its reported
    consumption or persistence references correspond to durable operations.
    """

    receipt_id: str
    enrollment_id: str
    challenge_id: str
    challenge_nonce: str
    server_id: str
    issuer_id: str
    issuer_credential_id: str
    owner_subject_id: str
    owner_trust_anchor_id: str
    owner_credential_id: str
    relying_party_id: str
    policy_version: int
    outcome: str
    merge_evidence: OwnerMergeVerificationEvidence
    challenge_consumption: OwnerBootstrapChallengeConsumption
    trust_registry_persistence: OwnerBootstrapTrustRegistryPersistence
    issued_at_epoch: int


@dataclass(frozen=True)
class OwnerAuthenticationEvidence:
    """Claims returned by a separately trusted Owner assertion verifier.

    This is an adapter result, not an assertion and not proof by itself. A
    production verifier must validate the assertion signature against an
    independently provisioned Owner credential, the exact challenge and
    relying-party context, and must obtain the principal from that credential
    rather than from caller input.
    """

    owner_subject_id: str
    owner_trust_anchor_id: str
    credential_id: str
    challenge_id: str
    nonce: str
    relying_party_id: str
    verified_at_epoch: int


@dataclass(frozen=True)
class ProtectedIssuerCredentialEvidence:
    """Public metadata for a key held by an independently protected issuer.

    The private key is deliberately absent. A key reference or process label
    is not proof of OS isolation; the provider must be implemented behind an
    authenticated process boundary before its result can be trusted.
    """

    issuer_id: str
    credential_id: str
    public_key_pem: str
    server_id: str
    instance_id: str
    service_fingerprint: str
    local_principal_commitment: str
    protected_key_reference: str
    issuer_process_identity: str
    valid_from_epoch: int
    expires_at_epoch: int
    revoked: bool


class OwnerAssertionVerifier(Protocol):
    """Verify Owner identity, challenge freshness, signature and RP binding."""

    def verify_assertion(
        self, challenge: G1EnrollmentChallenge, assertion: bytes
    ) -> OwnerAuthenticationEvidence: ...


class ProtectedIssuerCredentialProvider(Protocol):
    """Return issuer public metadata only from an authenticated protected host."""

    def current_credential(
        self, challenge: G1EnrollmentChallenge
    ) -> ProtectedIssuerCredentialEvidence: ...


class OwnerBootstrapTrustRegistry(Protocol):
    """Protected non-reader registry for a verified bootstrap result.

    The production implementation must enforce a distinct process/OS
    principal, immutable or transactionally versioned records, and explicit
    revocation. A Python protocol or same-process class does not provide that
    security boundary.
    """

    def register_if_absent(
        self,
        *,
        challenge: G1EnrollmentChallenge,
        owner: OwnerAuthenticationEvidence,
        issuer: ProtectedIssuerCredentialEvidence,
        merge: OwnerMergeVerificationEvidence,
    ) -> bool: ...


class OwnerBootstrapChallengeStore(Protocol):
    """Durable issuer-owned store enforcing one-use challenges and revocation."""

    def consume_once(self, *, challenge_id: str, nonce: str, now_epoch: int) -> None: ...


def validate_owner_bootstrap_evidence(
    *,
    challenge: G1EnrollmentChallenge,
    owner: OwnerAuthenticationEvidence,
    issuer: ProtectedIssuerCredentialEvidence,
    merge: OwnerMergeVerificationEvidence,
    now_epoch: int,
    expected_relying_party_id: str,
    expected_owner_subject_id: str,
    expected_owner_trust_anchor_id: str,
    expected_issuer_id: str,
) -> None:
    """Reject mismatched or stale adapter evidence before registry mutation.

    This validates bindings only. Signature verification, independent root
    provenance, authenticated process identity, durable replay protection and
    registry access control remain obligations of absent production adapters.
    """

    if type(now_epoch) is not int or not all((
        expected_relying_party_id,
        expected_owner_subject_id,
        expected_owner_trust_anchor_id,
        expected_issuer_id,
    )):
        raise OwnerMergeVerificationError("BOOTSTRAP_CONTEXT_INVALID")
    challenge.validate(now=datetime.fromtimestamp(now_epoch, timezone.utc))
    if (
        not isinstance(owner, OwnerAuthenticationEvidence)
        or owner.owner_subject_id != expected_owner_subject_id
        or owner.owner_trust_anchor_id != expected_owner_trust_anchor_id
        or not owner.credential_id
        or owner.challenge_id != challenge.challenge_id
        or owner.nonce != challenge.nonce
        or owner.relying_party_id != expected_relying_party_id
        or type(owner.verified_at_epoch) is not int
        or owner.verified_at_epoch < challenge.issued_at_epoch
        or owner.verified_at_epoch > now_epoch
    ):
        raise OwnerMergeVerificationError("OWNER_ASSERTION_UNTRUSTED_OR_MISMATCHED")
    if (
        not isinstance(issuer, ProtectedIssuerCredentialEvidence)
        or not issuer.issuer_id
        or issuer.issuer_id != expected_issuer_id
        or issuer.issuer_id != challenge.issuer_id
        or not issuer.credential_id
        or not issuer.protected_key_reference
        or not issuer.issuer_process_identity
        or issuer.public_key_pem != challenge.issuer_public_key_pem
        or issuer.server_id != challenge.server_id
        or issuer.instance_id != challenge.instance_id
        or issuer.service_fingerprint != challenge.service_fingerprint
        or issuer.local_principal_commitment != challenge.local_principal_commitment
        or type(issuer.valid_from_epoch) is not int
        or type(issuer.expires_at_epoch) is not int
        or issuer.valid_from_epoch > now_epoch
        or issuer.expires_at_epoch <= now_epoch
        or issuer.revoked is not False
    ):
        raise OwnerMergeVerificationError("ISSUER_CREDENTIAL_UNPROTECTED_OR_MISMATCHED")
    expected_manifest_sha256 = hashlib.sha256(
        json.dumps(challenge.expected_manifest(), sort_keys=True).encode()
    ).hexdigest()
    if (
        not isinstance(merge, OwnerMergeVerificationEvidence)
        or not isinstance(merge.challenge_id, str)
        or merge.challenge_id != challenge.challenge_id
        or type(merge.policy_version) is not int
        or merge.policy_version != challenge.policy_version
        or type(merge.merged_by_id) is not int
        or merge.merged_by_id != EXPECTED_OWNER_ID
        or type(merge.pull_request_number) is not int
        or merge.pull_request_number <= 0
        or not isinstance(merge.merge_commit_sha, str)
        or not isinstance(merge.manifest_git_blob_sha, str)
        or not _SHA1_RE.fullmatch(merge.merge_commit_sha)
        or not _SHA1_RE.fullmatch(merge.manifest_git_blob_sha)
        or not isinstance(merge.main_sha, str)
        or not _SHA1_RE.fullmatch(merge.main_sha)
        or not isinstance(merge.manifest_sha256, str)
        or not _SHA256_RE.fullmatch(merge.manifest_sha256)
        or merge.manifest_sha256 != expected_manifest_sha256
    ):
        raise OwnerMergeVerificationError("OWNER_MERGE_EVIDENCE_MISMATCH")


def validate_owner_bootstrap_enrollment_receipt(
    *,
    receipt: OwnerBootstrapEnrollmentReceipt,
    challenge: G1EnrollmentChallenge,
    owner: OwnerAuthenticationEvidence,
    issuer: ProtectedIssuerCredentialEvidence,
    merge: OwnerMergeVerificationEvidence,
    now_epoch: int,
    expected_relying_party_id: str,
    expected_owner_subject_id: str,
    expected_owner_trust_anchor_id: str,
    expected_issuer_id: str,
    expected_registry_id: str,
) -> None:
    """Validate receipt completeness and cross-bind its reported sub-results.

    This checks structure, equality and chronology only. It does not verify
    that challenge consumption or registry persistence actually occurred.
    ``expected_registry_id`` must come from future host trust configuration or
    a trusted host provider; never derive it from the receipt, caller request,
    or untrusted issuer metadata.
    """

    if not isinstance(receipt, OwnerBootstrapEnrollmentReceipt):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_INVALID")
    if (
        not isinstance(challenge, G1EnrollmentChallenge)
        or not isinstance(owner, OwnerAuthenticationEvidence)
        or not isinstance(issuer, ProtectedIssuerCredentialEvidence)
        or not isinstance(merge, OwnerMergeVerificationEvidence)
        or not all(
            isinstance(value, str) and value
            for value in (
                expected_relying_party_id,
                expected_owner_subject_id,
                expected_owner_trust_anchor_id,
                expected_issuer_id,
            )
        )
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_INVALID")
    if type(expected_registry_id) is not str or not expected_registry_id.strip():
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_INVALID")
    text_values = (
        receipt.receipt_id,
        receipt.enrollment_id,
        receipt.challenge_id,
        receipt.challenge_nonce,
        receipt.server_id,
        receipt.issuer_id,
        receipt.issuer_credential_id,
        receipt.owner_subject_id,
        receipt.owner_trust_anchor_id,
        receipt.owner_credential_id,
        receipt.relying_party_id,
    )
    if any(not isinstance(value, str) or not value for value in text_values):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_INVALID")
    if (
        type(receipt.policy_version) is not int
        or receipt.policy_version < 1
        or receipt.outcome != "ENROLLED"
        or type(receipt.issued_at_epoch) is not int
        or type(now_epoch) is not int
        or receipt.issued_at_epoch > now_epoch
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_INCOMPLETE")
    if (
        not isinstance(receipt.challenge_consumption, OwnerBootstrapChallengeConsumption)
        or not isinstance(receipt.trust_registry_persistence, OwnerBootstrapTrustRegistryPersistence)
        or not isinstance(receipt.merge_evidence, OwnerMergeVerificationEvidence)
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_INCOMPLETE")

    consumption = receipt.challenge_consumption
    persistence = receipt.trust_registry_persistence
    if (
        consumption.enrollment_id != receipt.enrollment_id
        or consumption.challenge_id != receipt.challenge_id
        or consumption.nonce != receipt.challenge_nonce
        or consumption.outcome != "CONSUMED_ONCE"
        or not isinstance(consumption.consumption_reference, str)
        or not consumption.consumption_reference
        or type(consumption.store_version) is not int
        or consumption.store_version < 1
        or type(consumption.consumed_at_epoch) is not int
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_CHALLENGE_CONSUMPTION_INCOMPLETE")
    if (
        persistence.enrollment_id != receipt.enrollment_id
        or persistence.outcome != "PERSISTED"
        or not isinstance(persistence.registry_id, str)
        or not persistence.registry_id
        or type(persistence.registry_version) is not int
        or persistence.registry_version < 1
        or not isinstance(persistence.record_id, str)
        or not persistence.record_id
        or type(persistence.persisted_at_epoch) is not int
        or not isinstance(persistence.persistence_reference, str)
        or not persistence.persistence_reference
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_TRUST_REGISTRY_PERSISTENCE_INCOMPLETE")
    if persistence.registry_id != expected_registry_id:
        raise OwnerMergeVerificationError("ENROLLMENT_TRUST_REGISTRY_ID_MISMATCH")
    if (
        receipt.challenge_id != challenge.challenge_id
        or receipt.challenge_nonce != challenge.nonce
        or receipt.server_id != challenge.server_id
        or receipt.issuer_id != challenge.issuer_id
        or receipt.issuer_id != expected_issuer_id
        or receipt.issuer_credential_id != issuer.credential_id
        or receipt.owner_subject_id != expected_owner_subject_id
        or receipt.owner_subject_id != owner.owner_subject_id
        or receipt.owner_trust_anchor_id != expected_owner_trust_anchor_id
        or receipt.owner_trust_anchor_id != owner.owner_trust_anchor_id
        or receipt.owner_credential_id != owner.credential_id
        or receipt.relying_party_id != expected_relying_party_id
        or receipt.policy_version != challenge.policy_version
        or receipt.merge_evidence != merge
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_BINDING_MISMATCH")
    if (
        consumption.consumed_at_epoch < challenge.issued_at_epoch
        or consumption.consumed_at_epoch >= challenge.expires_at_epoch
        or persistence.persisted_at_epoch < consumption.consumed_at_epoch
        or receipt.issued_at_epoch < persistence.persisted_at_epoch
    ):
        raise OwnerMergeVerificationError("ENROLLMENT_RECEIPT_TIME_INVALID")

    validate_owner_bootstrap_evidence(
        challenge=challenge,
        owner=owner,
        issuer=issuer,
        merge=merge,
        now_epoch=consumption.consumed_at_epoch,
        expected_relying_party_id=expected_relying_party_id,
        expected_owner_subject_id=expected_owner_subject_id,
        expected_owner_trust_anchor_id=expected_owner_trust_anchor_id,
        expected_issuer_id=expected_issuer_id,
    )


class OwnerControlledBootstrapBoundary(Protocol):
    """Host-owned G1 enrollment entry point; no production implementation exists.

    Implementations must verify assertion and merge evidence, bind the Owner,
    issuer, policy challenge and exact server, consume the challenge durably,
    and write only through a protected registry. Reader/requester code must not
    implement this protocol or receive registry mutation capability.
    """

    def enroll(
        self,
        *,
        challenge: G1EnrollmentChallenge,
        owner_assertion: bytes,
        pull_request_number: int,
    ) -> OwnerBootstrapEnrollmentReceipt: ...


def verify_owner_merge(
    pull_request_number: int,
    challenge: G1EnrollmentChallenge,
) -> OwnerMergeVerificationEvidence:
    """Fetch and verify the approved manifest using anonymous GitHub HTTPS.

    Uses the platform CA store through HTTPX's default TLS verification, refuses
    redirects, has bounded timeouts, and fails closed on API/quota/shape errors.
    No credential or cache is used. This is evidence verification only; a
    protected issuer must still consume the challenge durably before enrollment.
    """
    if isinstance(pull_request_number, bool) or not isinstance(pull_request_number, int) or pull_request_number < 1:
        raise OwnerMergeVerificationError("INVALID_PULL_REQUEST_NUMBER")
    with _GitHubApi() as api:
        return _verify_with_api(api, pull_request_number, challenge)


def _verify_with_api(
    api: "_GitHubApi",
    pull_request_number: int,
    challenge: G1EnrollmentChallenge,
    *,
    clock: Callable[[], datetime] | None = None,
) -> OwnerMergeVerificationEvidence:
    current_time = clock or (lambda: datetime.now(timezone.utc))
    challenge.validate(now=current_time())
    root = f"/repos/{EXPECTED_REPOSITORY}"
    repo = api.get_json(root)
    _require_object(repo, "REPOSITORY_RESPONSE_INVALID")
    _verify_repository_identity(repo)

    pr_path = f"{root}/pulls/{pull_request_number}"
    pr = api.get_json(pr_path)
    _require_object(pr, "PULL_REQUEST_RESPONSE_INVALID")
    merged_by = pr.get("merged_by")
    base = pr.get("base")
    _require_object(merged_by, "MERGED_BY_INVALID")
    _require_object(base, "PULL_REQUEST_BASE_INVALID")
    base_repo = base.get("repo")
    _require_object(base_repo, "PULL_REQUEST_BASE_REPOSITORY_INVALID")
    if type(pr.get("number")) is not int or pr["number"] != pull_request_number:
        raise OwnerMergeVerificationError("PULL_REQUEST_NUMBER_MISMATCH")
    if pr.get("state") != "closed" or pr.get("merged") is not True or not isinstance(pr.get("merged_at"), str):
        raise OwnerMergeVerificationError("PULL_REQUEST_NOT_MERGED")
    if type(merged_by.get("id")) is not int or merged_by["id"] != EXPECTED_OWNER_ID or merged_by.get("login") != EXPECTED_OWNER_LOGIN:
        raise OwnerMergeVerificationError("UNAUTHORIZED_MERGE_ACTOR")
    if base.get("ref") != EXPECTED_BASE_BRANCH or type(base_repo.get("id")) is not int or base_repo["id"] != EXPECTED_REPOSITORY_ID:
        raise OwnerMergeVerificationError("PULL_REQUEST_BASE_MISMATCH")
    _validate_merge_time(pr["merged_at"], challenge, current_time())
    merge_sha = pr.get("merge_commit_sha")
    if not isinstance(merge_sha, str) or not _SHA1_RE.fullmatch(merge_sha):
        raise OwnerMergeVerificationError("MERGE_COMMIT_MISSING_OR_INVALID")

    branch_before = api.get_json(f"{root}/branches/{EXPECTED_BASE_BRANCH}")
    _require_object(branch_before, "MAIN_BRANCH_RESPONSE_INVALID")
    branch_commit = branch_before.get("commit")
    _require_object(branch_commit, "MAIN_BRANCH_COMMIT_INVALID")
    main_sha = branch_commit.get("sha")
    if not isinstance(main_sha, str) or not _SHA1_RE.fullmatch(main_sha):
        raise OwnerMergeVerificationError("MAIN_SHA_INVALID")

    files_path = f"{pr_path}/files"
    changed_files = api.get_json(files_path, params={"per_page": 100})
    if "next" in api.last_link_relations:
        raise OwnerMergeVerificationError("PULL_REQUEST_FILES_INCOMPLETE")
    if not isinstance(changed_files, list) or len(changed_files) != 1:
        raise OwnerMergeVerificationError("MANIFEST_NOT_EXCLUSIVE_PR_CHANGE")
    changed = changed_files[0]
    _require_object(changed, "PULL_REQUEST_FILE_INVALID")
    if changed.get("filename") != BOOTSTRAP_MANIFEST_PATH or changed.get("status") not in {"added", "modified"}:
        raise OwnerMergeVerificationError("MANIFEST_NOT_IN_APPROVED_PR")

    commit = api.get_json(f"{root}/commits/{merge_sha}")
    _require_object(commit, "MERGE_COMMIT_RESPONSE_INVALID")
    if commit.get("sha") != merge_sha:
        raise OwnerMergeVerificationError("MERGE_COMMIT_IDENTITY_MISMATCH")
    associated_prs = api.get_json(f"{root}/commits/{merge_sha}/pulls", params={"per_page": 100})
    if "next" in api.last_link_relations:
        raise OwnerMergeVerificationError("ASSOCIATED_PULL_REQUESTS_INCOMPLETE")
    if not isinstance(associated_prs, list) or not any(
        isinstance(item, dict)
        and type(item.get("number")) is int
        and item.get("number") == pull_request_number
        and isinstance(item.get("base"), dict)
        and item["base"].get("ref") == EXPECTED_BASE_BRANCH
        and isinstance(item["base"].get("repo"), dict)
        and item["base"]["repo"].get("id") == EXPECTED_REPOSITORY_ID
        for item in associated_prs
    ):
        raise OwnerMergeVerificationError("MERGE_COMMIT_NOT_ASSOCIATED_WITH_PR")

    compare = api.get_json(f"{root}/compare/{merge_sha}...{main_sha}")
    _require_object(compare, "MAIN_ANCESTRY_RESPONSE_INVALID")
    merge_base = compare.get("merge_base_commit")
    _require_object(merge_base, "MAIN_MERGE_BASE_INVALID")
    if compare.get("status") not in {"ahead", "identical"} or merge_base.get("sha") != merge_sha:
        raise OwnerMergeVerificationError("MERGE_COMMIT_NOT_IN_MAIN")

    merged_content, merged_blob_sha = _fetch_manifest(api, root, merge_sha)
    parsed_manifest = _parse_manifest(merged_content)
    _validate_manifest_for_challenge(parsed_manifest, challenge, current_time())

    current_content, current_blob_sha = _fetch_manifest(api, root, main_sha)
    if current_content != merged_content or current_blob_sha != merged_blob_sha:
        raise OwnerMergeVerificationError("CURRENT_MAIN_MANIFEST_CHANGED")
    branch_after = api.get_json(f"{root}/branches/{EXPECTED_BASE_BRANCH}")
    _require_object(branch_after, "MAIN_BRANCH_RECHECK_INVALID")
    after_commit = branch_after.get("commit")
    _require_object(after_commit, "MAIN_BRANCH_RECHECK_COMMIT_INVALID")
    if after_commit.get("sha") != main_sha:
        raise OwnerMergeVerificationError("MAIN_MOVED_DURING_VERIFICATION")
    repo_after = api.get_json(root)
    _verify_repository_identity(repo_after)
    challenge.validate(now=current_time())

    return OwnerMergeVerificationEvidence(
        pull_request_number=pull_request_number,
        merge_commit_sha=merge_sha,
        main_sha=main_sha,
        manifest_git_blob_sha=merged_blob_sha,
        merged_by_id=EXPECTED_OWNER_ID,
        challenge_id=challenge.challenge_id,
        policy_version=challenge.policy_version,
        manifest_sha256=hashlib.sha256(merged_content).hexdigest(),
    )


def _verify_repository_identity(repo: Any) -> None:
    _require_object(repo, "REPOSITORY_RESPONSE_INVALID")
    owner = repo.get("owner")
    _require_object(owner, "REPOSITORY_OWNER_INVALID")
    if (
        type(repo.get("id")) is not int
        or repo["id"] != EXPECTED_REPOSITORY_ID
        or repo.get("full_name") != EXPECTED_REPOSITORY
    ):
        raise OwnerMergeVerificationError("REPOSITORY_IDENTITY_MISMATCH")
    if owner.get("login") != EXPECTED_OWNER_LOGIN or type(owner.get("id")) is not int or owner["id"] != EXPECTED_OWNER_ID:
        raise OwnerMergeVerificationError("OWNER_IDENTITY_MISMATCH")


def _fetch_manifest(api: "_GitHubApi", root: str, ref: str) -> tuple[bytes, str]:
    path = f"{root}/contents/{quote(BOOTSTRAP_MANIFEST_PATH, safe='/')}"
    payload = api.get_json(path, params={"ref": ref})
    _require_object(payload, "MANIFEST_RESPONSE_INVALID")
    if payload.get("type") != "file" or payload.get("path") != BOOTSTRAP_MANIFEST_PATH or payload.get("encoding") != "base64":
        raise OwnerMergeVerificationError("MANIFEST_FILE_IDENTITY_INVALID")
    encoded = payload.get("content")
    declared_size = payload.get("size")
    blob_sha = payload.get("sha")
    if not isinstance(encoded, str) or type(declared_size) is not int or not isinstance(blob_sha, str) or not _SHA1_RE.fullmatch(blob_sha):
        raise OwnerMergeVerificationError("MANIFEST_CONTENT_METADATA_INVALID")
    try:
        content = base64.b64decode("".join(encoded.split()), validate=True)
    except (binascii.Error, ValueError):
        raise OwnerMergeVerificationError("MANIFEST_BASE64_INVALID") from None
    if len(content) > MAX_MANIFEST_BYTES or len(content) != declared_size:
        raise OwnerMergeVerificationError("MANIFEST_SIZE_INVALID")
    computed_blob_sha = hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()
    if computed_blob_sha != blob_sha:
        raise OwnerMergeVerificationError("MANIFEST_GIT_BLOB_MISMATCH")
    return content, blob_sha


def _parse_manifest(raw: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise OwnerMergeVerificationError("MANIFEST_JSON_INVALID") from None
    _require_object(value, "MANIFEST_SCHEMA_INVALID")
    return value


def _validate_manifest_for_challenge(
    manifest: Mapping[str, Any], challenge: G1EnrollmentChallenge, instant: datetime
) -> None:
    schema_version = manifest.get("schema_version")
    if type(schema_version) is not int:
        raise OwnerMergeVerificationError("MANIFEST_SCHEMA_MISMATCH")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise OwnerMergeVerificationError("MANIFEST_SCHEMA_VERSION_UNSUPPORTED")
    expected = challenge.expected_manifest()
    if set(manifest) != set(expected):
        raise OwnerMergeVerificationError("MANIFEST_SCHEMA_MISMATCH")
    if (
        type(manifest.get("policy_version")) is not int
        or type(manifest.get("issued_at_epoch")) is not int
        or type(manifest.get("expires_at_epoch")) is not int
        or type(manifest.get("revoked")) is not bool
        or not isinstance(manifest.get("scopes"), list)
        or any(not isinstance(scope, str) for scope in manifest.get("scopes", []))
        or any(not isinstance(manifest.get(field), str) for field in (
            "challenge_id", "nonce", "instance_id", "service_fingerprint",
            "issuer_public_key_pem", "local_principal_commitment",
        ))
    ):
        raise OwnerMergeVerificationError("MANIFEST_SCHEMA_MISMATCH")
    if manifest != expected:
        raise OwnerMergeVerificationError("MANIFEST_CHALLENGE_MISMATCH")
    if manifest.get("revoked") is not False:
        raise OwnerMergeVerificationError("MANIFEST_REVOKED")
    if int(instant.timestamp()) >= challenge.expires_at_epoch:
        raise OwnerMergeVerificationError("CHALLENGE_EXPIRED")


def _validate_merge_time(merged_at: str, challenge: G1EnrollmentChallenge, instant: datetime) -> None:
    try:
        parsed = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
    except ValueError:
        raise OwnerMergeVerificationError("MERGE_TIME_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OwnerMergeVerificationError("MERGE_TIME_INVALID")
    merged_epoch = int(parsed.timestamp())
    if merged_epoch < challenge.issued_at_epoch or merged_epoch >= challenge.expires_at_epoch:
        raise OwnerMergeVerificationError("MERGE_OUTSIDE_CHALLENGE_WINDOW")
    if int(instant.timestamp()) >= challenge.expires_at_epoch:
        raise OwnerMergeVerificationError("CHALLENGE_EXPIRED")


def _validate_public_key_pem(value: str) -> None:
    try:
        validate_rsa_sha256_public_key_pem(value)
    except InvalidRsaPublicKey:
        raise OwnerMergeVerificationError("INVALID_ISSUER_PUBLIC_KEY") from None


def _require_object(value: Any, code: str) -> None:
    if not isinstance(value, dict):
        raise OwnerMergeVerificationError(code)


class _GitHubApi:
    """Narrow anonymous GitHub API client; injection is private for unit tests."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            base_url=GITHUB_API_BASE,
            verify=True,
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(5.0, connect=3.0),
            transport=transport,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
                "User-Agent": "IABV-G1-Owner-Merge-Verifier/1",
            },
        )
        self.last_link_relations: set[str] = set()

    def __enter__(self) -> "_GitHubApi":
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    def get_json(self, path: str, *, params: Mapping[str, object] | None = None) -> Any:
        if not path.startswith(f"/repos/{EXPECTED_REPOSITORY}/") and path != f"/repos/{EXPECTED_REPOSITORY}":
            raise OwnerMergeVerificationError("API_PATH_OUT_OF_SCOPE")
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError:
            raise OwnerMergeVerificationError("HTTPS_REQUEST_FAILED") from None
        if response.url.scheme != "https" or response.url.host != "api.github.com":
            raise OwnerMergeVerificationError("API_ORIGIN_MISMATCH")
        if response.status_code == 429 or (
            response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise OwnerMergeVerificationError("GITHUB_RATE_LIMITED")
        if response.status_code != 200:
            raise OwnerMergeVerificationError("GITHUB_API_STATUS_ERROR")
        if len(response.content) > MAX_API_RESPONSE_BYTES:
            raise OwnerMergeVerificationError("GITHUB_API_RESPONSE_TOO_LARGE")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise OwnerMergeVerificationError("GITHUB_API_CONTENT_TYPE_INVALID")
        self.last_link_relations = _parse_link_relations(response.headers.get("link", ""))
        try:
            return json.loads(response.content.decode("utf-8"), object_pairs_hook=_unique_pairs)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise OwnerMergeVerificationError("GITHUB_API_JSON_INVALID") from None


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _parse_link_relations(value: str) -> set[str]:
    relations: set[str] = set()
    for item in value.split(","):
        match = re.search(r";\s*rel=\"?([^\";]+)", item)
        if match:
            relations.update(match.group(1).split())
    return relations
