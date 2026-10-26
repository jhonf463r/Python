"""Typed fail-closed authorization contracts for protected MCP reads.

The coordinator composes authority, mandate, G2 policy, G3 target resolution,
an authenticated issuer IPC client, cryptographic signatures, expiry and
durable replay consumption. Production implementations of the providers and
the Windows process boundary are intentionally not supplied until their
independent trust and OS identities can be provisioned and verified.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from iabv_v15.services.security.github_owner_merge_bootstrap import (
    EXPECTED_OWNER_ID,
    EXPECTED_REPOSITORY_ID,
    OwnerMergeVerificationEvidence,
)
from iabv_v15.services.security.windows_crypto import verify_rsa_sha256

MAX_DECISION_TTL_SECONDS = 300
MAX_POLICY_TTL_SECONDS = 24 * 60 * 60
REPLAY_SCHEMA_VERSION = 1


class ReadAuthorizationDenied(RuntimeError):
    """A missing, stale, invalid or unverifiable authorization denies access."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ReadDecisionEffect(str, Enum):
    """Typed outcome consumed by the MCP enforcement point."""

    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class ReadRequest:
    """Server-created operation request; no authorization claims come from MCP."""

    server_id: str
    instance_id: str
    service_fingerprint: str
    local_principal_commitment: str
    workspace_id: str
    checkout_id: str
    operation: str
    requested_relative_target: str
    challenge_id: str
    nonce: str
    challenge_issued_at_epoch: int
    challenge_expires_at_epoch: int
    opened_target: Any | None = None


@dataclass(frozen=True)
class TrustAnchor:
    """Anchor returned only by a separately authenticated trust provider."""

    anchor_id: str
    public_key_pem: str
    policy_source_id: str
    valid_from_epoch: int
    expires_at_epoch: int
    revoked: bool


@dataclass(frozen=True)
class OwnerMandate:
    """Root-signed grant binding an issuer key to one repository and scope."""

    mandate_id: str
    anchor_id: str
    repository_id: int
    owner_id: int
    merged_pr_number: int
    merge_commit_sha: str
    issuer_id: str
    issuer_public_key_pem: str
    server_id: str
    instance_id: str
    service_fingerprint: str
    local_principal_commitment: str
    allowed_operations: tuple[str, ...]
    policy_version: int
    issued_at_epoch: int
    expires_at_epoch: int
    revoked: bool
    signature: bytes

    def signed_bytes(self) -> bytes:
        return _canonical_json({
            "mandate_id": self.mandate_id,
            "anchor_id": self.anchor_id,
            "repository_id": self.repository_id,
            "owner_id": self.owner_id,
            "merged_pr_number": self.merged_pr_number,
            "merge_commit_sha": self.merge_commit_sha,
            "issuer_id": self.issuer_id,
            "issuer_public_key_pem": self.issuer_public_key_pem,
            "server_id": self.server_id,
            "instance_id": self.instance_id,
            "service_fingerprint": self.service_fingerprint,
            "local_principal_commitment": self.local_principal_commitment,
            "allowed_operations": list(self.allowed_operations),
            "policy_version": self.policy_version,
            "issued_at_epoch": self.issued_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "revoked": self.revoked,
        })


@dataclass(frozen=True)
class G2PolicySnapshot:
    """Root-signed catalog snapshot with explicit freshness and revocations."""

    source_id: str
    anchor_id: str
    version: int
    issued_at_epoch: int
    expires_at_epoch: int
    revoked_mandate_ids: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    signature: bytes
    root_binding_id: str = ""
    policy_binding_id: str = ""

    def signed_bytes(self) -> bytes:
        return _canonical_json({
            "source_id": self.source_id,
            "anchor_id": self.anchor_id,
            "version": self.version,
            "issued_at_epoch": self.issued_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "revoked_mandate_ids": list(self.revoked_mandate_ids),
            "allowed_operations": list(self.allowed_operations),
            "root_binding_id": self.root_binding_id,
            "policy_binding_id": self.policy_binding_id,
        })


@dataclass(frozen=True)
class ResolvedTarget:
    """G3 output from a server-owned versioned target resolver."""

    server_id: str
    instance_id: str
    operation: str
    canonical_target: str
    workspace_id: str
    checkout_id: str
    resolver_version: str
    opened_target: Any | None = None
    target_binding_id: str = ""
    root_binding_id: str = ""
    policy_binding_id: str = ""


@dataclass(frozen=True)
class SignedReadDecision:
    """Issuer-signed, exact-target, time-limited, one-use decision."""

    decision_id: str
    mandate_id: str
    issuer_id: str
    server_id: str
    instance_id: str
    service_fingerprint: str
    local_principal_commitment: str
    operation: str
    canonical_target: str
    workspace_id: str
    checkout_id: str
    policy_source_id: str
    policy_version: int
    resolver_version: str
    challenge_id: str
    nonce: str
    issued_at_epoch: int
    expires_at_epoch: int
    signature: bytes
    target_binding_id: str = ""
    root_binding_id: str = ""
    policy_binding_id: str = ""

    def signed_bytes(self) -> bytes:
        return _canonical_json({
            "decision_id": self.decision_id,
            "mandate_id": self.mandate_id,
            "issuer_id": self.issuer_id,
            "server_id": self.server_id,
            "instance_id": self.instance_id,
            "service_fingerprint": self.service_fingerprint,
            "local_principal_commitment": self.local_principal_commitment,
            "operation": self.operation,
            "canonical_target": self.canonical_target,
            "workspace_id": self.workspace_id,
            "checkout_id": self.checkout_id,
            "policy_source_id": self.policy_source_id,
            "policy_version": self.policy_version,
            "resolver_version": self.resolver_version,
            "challenge_id": self.challenge_id,
            "nonce": self.nonce,
            "issued_at_epoch": self.issued_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "target_binding_id": self.target_binding_id,
            "root_binding_id": self.root_binding_id,
            "policy_binding_id": self.policy_binding_id,
        })


@dataclass(frozen=True)
class AuthenticatedIssuerResponse:
    """IPC response; peer_identity is trustworthy only if the adapter proves it."""

    peer_identity: str
    decision: SignedReadDecision


@dataclass(frozen=True)
class ReadPermit:
    """Internal result returned only after every configured gate succeeds."""

    decision_id: str
    requested_relative_target: str
    canonical_target: str
    operation: str
    workspace_id: str
    checkout_id: str
    policy_version: int
    resolver_version: str
    expires_at_epoch: int
    issued_at_epoch: int
    opened_target: Any | None = None
    target_binding_id: str = ""
    root_binding_id: str = ""
    policy_binding_id: str = ""
    coordinator_binding_id: str = ""
    _issuance_seal: object | None = None


@dataclass(frozen=True)
class ReadAuthorizationDecision:
    """Typed authorization result; a denial can never carry a permit."""

    effect: ReadDecisionEffect
    reason: str
    permit: ReadPermit | None = None

    def __post_init__(self) -> None:
        if self.effect is ReadDecisionEffect.ALLOW:
            if type(self.permit) is not ReadPermit or self.reason != "AUTHORIZED":
                raise ValueError("ALLOW requires a scoped permit and AUTHORIZED reason")
        elif self.permit is not None or not self.reason:
            raise ValueError("DENY requires a reason and cannot carry a permit")

    @classmethod
    def deny(cls, reason: str) -> "ReadAuthorizationDecision":
        return cls(ReadDecisionEffect.DENY, reason)

    @classmethod
    def allow(cls, permit: ReadPermit) -> "ReadAuthorizationDecision":
        return cls(ReadDecisionEffect.ALLOW, "AUTHORIZED", permit)


def _is_coordinator_issued_permit(permit: object, coordinator: object) -> bool:
    return (
        type(permit) is ReadPermit
        and isinstance(coordinator, ReadAuthorizationCoordinator)
        and permit._issuance_seal is coordinator._permit_issuance_seal
        and permit.coordinator_binding_id == coordinator.coordinator_binding_id
    )


class TrustAnchorProvider(Protocol):
    """Must retrieve the independently provisioned active root, not MCP input."""

    def current_anchor(self) -> TrustAnchor: ...


class OwnerMandateProvider(Protocol):
    def current_mandate(self, anchor_id: str) -> OwnerMandate: ...


class OwnerMergeEvidenceProvider(Protocol):
    """Must revalidate the fixed-repository Owner merge from an approved source."""

    def verified_merge(self, pull_request_number: int) -> OwnerMergeVerificationEvidence: ...


class G2PolicyProvider(Protocol):
    """Must supply an authorized, integrity-protected, fresh catalog snapshot."""

    def current_policy(self, source_id: str) -> G2PolicySnapshot: ...


class G3TargetResolver(Protocol):
    """Must resolve the already-open target capability, never reopen a path."""

    def resolve(self, request: ReadRequest) -> ResolvedTarget: ...


class AuthenticatedIssuerIpcClient(Protocol):
    """Adapter must authenticate the OS peer process, SID and protected channel.

    A response field alone is not peer authentication. The production adapter
    remains absent until a separately identified service and secure IPC ACLs
    exist; the MCP server must therefore keep the positive path disabled.
    """

    def request_decision(self, request: ReadRequest, target: ResolvedTarget) -> AuthenticatedIssuerResponse: ...


class ReplayConsumer(Protocol):
    def consume_once(
        self,
        *,
        challenge_id: str,
        nonce: str,
        decision_id: str,
        expires_at_epoch: int,
        now_epoch: int,
    ) -> None: ...


class ServerReadRequestContextProvider(Protocol):
    """Create a request from host-owned identity; MCP arguments are not identity."""

    def create_request(self, *, operation: str, requested_relative_target: str) -> ReadRequest: ...


class SQLiteReplayConsumer:
    """Atomic, persistent nonce consumer for a future protected issuer process.

    The caller must place the database in service-owned storage. This class
    fails on missing/corrupt/incompatible state and duplicate use. It cannot
    detect restoration of an older valid database snapshot; rollback protection
    requires a separate monotonic OS-backed counter and is not claimed here.
    """

    def __init__(self, database_path: str | os.PathLike[str]) -> None:
        self._path = Path(database_path)
        if not self._path.is_absolute():
            raise ValueError("replay database path must be absolute")

    def initialize_empty_for_service_provisioning(self) -> None:
        """Create a new empty ledger once; never called by an MCP reader."""

        if self._path.exists():
            raise ReadAuthorizationDenied("REPLAY_STORE_ALREADY_EXISTS")
        if not self._path.parent.is_dir():
            raise ReadAuthorizationDenied("REPLAY_STORE_PARENT_MISSING")
        try:
            with self._path.open("xb"):
                pass
            with closing(self._connect(read_only=False)) as connection:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA synchronous=FULL")
                connection.executescript(
                    "BEGIN IMMEDIATE;"
                    "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
                    "INSERT INTO metadata(key, value) VALUES ('schema_version', '1');"
                    "CREATE TABLE consumed ("
                    "challenge_id TEXT NOT NULL, nonce TEXT NOT NULL, decision_id TEXT NOT NULL UNIQUE, "
                    "expires_at_epoch INTEGER NOT NULL, consumed_at_epoch INTEGER NOT NULL, "
                    "PRIMARY KEY(challenge_id, nonce));"
                    "COMMIT;"
                )
        except (OSError, sqlite3.Error) as exc:
            raise ReadAuthorizationDenied("REPLAY_STORE_INITIALIZATION_FAILED") from exc

    def consume_once(
        self,
        *,
        challenge_id: str,
        nonce: str,
        decision_id: str,
        expires_at_epoch: int,
        now_epoch: int,
    ) -> None:
        if not all(isinstance(value, str) and value for value in (challenge_id, nonce, decision_id)):
            raise ReadAuthorizationDenied("REPLAY_INPUT_INVALID")
        if type(expires_at_epoch) is not int or type(now_epoch) is not int or now_epoch >= expires_at_epoch:
            raise ReadAuthorizationDenied("REPLAY_DECISION_EXPIRED")
        if not self._path.is_file():
            raise ReadAuthorizationDenied("REPLAY_STORE_MISSING")
        try:
            with closing(self._connect(read_only=False)) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity != ("ok",):
                    raise ReadAuthorizationDenied("REPLAY_STORE_CORRUPT")
                version = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'schema_version'"
                ).fetchone()
                if version != (str(REPLAY_SCHEMA_VERSION),):
                    raise ReadAuthorizationDenied("REPLAY_STORE_INCOMPATIBLE")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO consumed(challenge_id, nonce, decision_id, expires_at_epoch, consumed_at_epoch) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (challenge_id, nonce, decision_id, expires_at_epoch, now_epoch),
                )
                connection.commit()
        except ReadAuthorizationDenied:
            raise
        except sqlite3.IntegrityError as exc:
            raise ReadAuthorizationDenied("REPLAY_NONCE_OR_DECISION_REUSED") from exc
        except sqlite3.DatabaseError as exc:
            raise ReadAuthorizationDenied("REPLAY_STORE_CORRUPT_OR_INCOMPATIBLE") from exc
        except OSError as exc:
            raise ReadAuthorizationDenied("REPLAY_STORE_CONSUME_FAILED_OR_REPEATED") from exc

    def _connect(self, *, read_only: bool) -> sqlite3.Connection:
        mode = "ro" if read_only else "rw"
        uri = f"{self._path.as_uri()}?mode={mode}"
        connection = sqlite3.connect(uri, uri=True, timeout=2.0, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=2000")
        if not read_only:
            connection.execute("PRAGMA synchronous=FULL")
        return connection


class ReadAuthorizationCoordinator:
    """Composes G1 trust/mandate, G2 policy, G3 target and issuer decision.

    No production provider is wired into the current MCP server. Missing
    dependencies deny, and test-only providers must never be supplied in
    production.
    """

    @classmethod
    def unconfigured(cls) -> "ReadAuthorizationCoordinator":
        """Build the explicit fail-closed composition used until real providers exist."""

        return cls(
            trust_provider=None,
            mandate_provider=None,
            merge_evidence_provider=None,
            policy_provider=None,
            target_resolver=None,
            issuer_client=None,
            replay_consumer=None,
            request_context_provider=None,
        )

    def __init__(
        self,
        *,
        trust_provider: TrustAnchorProvider | None,
        mandate_provider: OwnerMandateProvider | None,
        merge_evidence_provider: OwnerMergeEvidenceProvider | None,
        policy_provider: G2PolicyProvider | None,
        target_resolver: G3TargetResolver | None,
        issuer_client: AuthenticatedIssuerIpcClient | None,
        replay_consumer: ReplayConsumer | None,
        request_context_provider: ServerReadRequestContextProvider | None = None,
        clock=None,
    ) -> None:
        self._trust = trust_provider
        self._mandates = mandate_provider
        self._merges = merge_evidence_provider
        self._policies = policy_provider
        self._targets = target_resolver
        self._issuer = issuer_client
        self._replay = replay_consumer
        self._request_context = request_context_provider
        self._clock = clock or (lambda: int(datetime.now(timezone.utc).timestamp()))
        self.coordinator_binding_id = uuid.uuid4().hex
        self._permit_issuance_seal = object()

    def missing_requirements(self) -> tuple[str, ...]:
        """Return absent production-boundary dependencies without relaxing policy."""

        required = (
            ("INDEPENDENT_TRUST_ROOT_PROVIDER", self._trust),
            ("OWNER_MANDATE_PROVIDER", self._mandates),
            ("OWNER_MERGE_EVIDENCE_PROVIDER", self._merges),
            ("G2_POLICY_PROVIDER", self._policies),
            ("G3_TARGET_RESOLVER", self._targets),
            ("AUTHENTICATED_ISSUER_IPC", self._issuer),
            ("PERSISTENT_REPLAY_CONSUMER", self._replay),
            ("HOST_OWNED_SERVER_PROCESS_IDENTITY", self._request_context),
        )
        return tuple(name for name, provider in required if provider is None)

    def permit_is_current(self, permit: object) -> bool:
        """Check coordinator provenance and validity against its trusted clock."""

        if not _is_coordinator_issued_permit(permit, self):
            return False
        try:
            now = self._clock()
        except Exception:
            return False
        return (
            type(now) is int
            and type(permit.issued_at_epoch) is int
            and type(permit.expires_at_epoch) is int
            and permit.issued_at_epoch <= now < permit.expires_at_epoch
        )

    def decide_mcp_read(
        self,
        *,
        operation: str,
        requested_relative_target: str,
        opened_target: Any | None = None,
    ) -> ReadAuthorizationDecision:
        """Create a host-context request and return an explicit ALLOW or DENY.

        No caller-supplied identity or authority is accepted here. The production
        AppBootstrap currently has no providers, so its route remains fail-closed.
        """

        if operation not in {"read_repo_file", "list_repo_directory"}:
            return ReadAuthorizationDecision.deny("READ_OPERATION_NOT_ALLOWED")
        if (
            opened_target is None
            or getattr(opened_target, "is_open", False) is not True
            or getattr(opened_target, "operation", None) != operation
            or getattr(opened_target, "relative_target", None) != requested_relative_target
            or type(getattr(opened_target, "target_binding_id", None)) is not str
            or not getattr(opened_target, "target_binding_id", "")
        ):
            return ReadAuthorizationDecision.deny("G3_OPEN_TARGET_CAPABILITY_REQUIRED")
        if not isinstance(requested_relative_target, str):
            return ReadAuthorizationDecision.deny("READ_REQUEST_TARGET_INVALID")
        missing = self.missing_requirements()
        if missing:
            return ReadAuthorizationDecision.deny("AUTHORITY_REQUIREMENTS_MISSING:" + ",".join(missing))
        try:
            request = self._request_context.create_request(  # type: ignore[union-attr]
                operation=operation,
                requested_relative_target=requested_relative_target,
            )
            if (
                not isinstance(request, ReadRequest)
                or request.operation != operation
                or request.requested_relative_target != requested_relative_target
            ):
                return ReadAuthorizationDecision.deny("HOST_READ_REQUEST_CONTEXT_MISMATCH")
            request = replace(request, opened_target=opened_target)
            return self.decide(request)
        except Exception:
            return ReadAuthorizationDecision.deny("HOST_READ_REQUEST_CONTEXT_UNAVAILABLE")

    def decide(self, request: ReadRequest) -> ReadAuthorizationDecision:
        """Convert the validated composition into a typed MCP decision."""

        try:
            return ReadAuthorizationDecision.allow(self.authorize(request))
        except ReadAuthorizationDenied as exc:
            return ReadAuthorizationDecision.deny(exc.reason)
        except Exception:
            return ReadAuthorizationDecision.deny("AUTHORITY_DECISION_INTERNAL_FAILURE")

    def authorize(self, request: ReadRequest) -> ReadPermit:
        if not isinstance(request, ReadRequest):
            raise ReadAuthorizationDenied("READ_REQUEST_INVALID")
        opened_target = request.opened_target
        if (
            opened_target is None
            or getattr(opened_target, "is_open", False) is not True
            or getattr(opened_target, "operation", None) != request.operation
            or getattr(opened_target, "relative_target", None) != request.requested_relative_target
            or type(getattr(opened_target, "target_binding_id", None)) is not str
            or not getattr(opened_target, "target_binding_id", "")
        ):
            raise ReadAuthorizationDenied("G3_OPEN_TARGET_CAPABILITY_INVALID")
        providers = (
            self._trust,
            self._mandates,
            self._merges,
            self._policies,
            self._targets,
            self._issuer,
            self._replay,
        )
        if any(provider is None for provider in providers):
            raise ReadAuthorizationDenied("AUTHORITY_PROVIDER_UNAVAILABLE")
        now = self._clock()
        if type(now) is not int or type(request.challenge_expires_at_epoch) is not int:
            raise ReadAuthorizationDenied("AUTHORIZATION_CLOCK_OR_CHALLENGE_INVALID")
        if now >= request.challenge_expires_at_epoch:
            raise ReadAuthorizationDenied("CHALLENGE_EXPIRED")
        if now < request.challenge_issued_at_epoch:
            raise ReadAuthorizationDenied("CHALLENGE_NOT_YET_VALID")
        _validate_request(request)

        try:
            anchor = self._trust.current_anchor()  # type: ignore[union-attr]
            if (
                not isinstance(anchor.anchor_id, str)
                or not anchor.anchor_id
                or not isinstance(anchor.policy_source_id, str)
                or not anchor.policy_source_id
                or type(anchor.valid_from_epoch) is not int
                or type(anchor.expires_at_epoch) is not int
                or anchor.valid_from_epoch > now
                or anchor.expires_at_epoch <= now
                or anchor.revoked is not False
            ):
                raise ReadAuthorizationDenied("TRUST_ANCHOR_UNAVAILABLE_OR_EXPIRED")
            mandate = self._mandates.current_mandate(anchor.anchor_id)  # type: ignore[union-attr]
            if type(mandate.revoked) is not bool:
                raise ReadAuthorizationDenied("OWNER_MANDATE_INVALID_OR_UNTRUSTED")
            if mandate.revoked is not False:
                raise ReadAuthorizationDenied("OWNER_MANDATE_INVALID_OR_UNTRUSTED")
            merge = self._merges.verified_merge(mandate.merged_pr_number)  # type: ignore[union-attr]
            if (
                mandate.anchor_id != anchor.anchor_id
                or type(mandate.repository_id) is not int
                or mandate.repository_id != EXPECTED_REPOSITORY_ID
                or type(mandate.owner_id) is not int
                or mandate.owner_id != EXPECTED_OWNER_ID
                or type(mandate.merged_pr_number) is not int
                or mandate.merged_pr_number < 1
                or type(mandate.policy_version) is not int
                or mandate.policy_version < 1
                or not isinstance(mandate.mandate_id, str)
                or not mandate.mandate_id
                or not isinstance(mandate.issuer_id, str)
                or not mandate.issuer_id
                or mandate.server_id != request.server_id
                or mandate.instance_id != request.instance_id
                or mandate.service_fingerprint != request.service_fingerprint
                or mandate.local_principal_commitment != request.local_principal_commitment
                or type(mandate.issued_at_epoch) is not int
                or type(mandate.expires_at_epoch) is not int
                or mandate.expires_at_epoch <= mandate.issued_at_epoch
                or merge.pull_request_number != mandate.merged_pr_number
                or merge.merge_commit_sha != mandate.merge_commit_sha
                or merge.merged_by_id != EXPECTED_OWNER_ID
                or merge.challenge_id != request.challenge_id
                or merge.policy_version != mandate.policy_version
                or type(mandate.allowed_operations) is not tuple
                or len(set(mandate.allowed_operations)) != len(mandate.allowed_operations)
                or request.operation not in mandate.allowed_operations
                or not (mandate.issued_at_epoch <= now < mandate.expires_at_epoch)
                or not verify_rsa_sha256(anchor.public_key_pem, mandate.signed_bytes(), mandate.signature)
            ):
                raise ReadAuthorizationDenied("OWNER_MANDATE_INVALID_OR_UNTRUSTED")

            policy = self._policies.current_policy(anchor.policy_source_id)  # type: ignore[union-attr]
            if (
                policy.source_id != anchor.policy_source_id
                or policy.anchor_id != anchor.anchor_id
                or policy.version != mandate.policy_version
                or policy.root_binding_id != getattr(opened_target, "root_binding_id", None)
                or policy.policy_binding_id != getattr(opened_target, "policy_binding_id", None)
                or type(policy.version) is not int
                or type(policy.issued_at_epoch) is not int
                or type(policy.expires_at_epoch) is not int
                or policy.expires_at_epoch <= policy.issued_at_epoch
                or type(policy.allowed_operations) is not tuple
                or type(policy.revoked_mandate_ids) is not tuple
                or request.operation not in policy.allowed_operations
                or mandate.mandate_id in policy.revoked_mandate_ids
                or not (policy.issued_at_epoch <= now < policy.expires_at_epoch)
                or policy.expires_at_epoch - policy.issued_at_epoch > MAX_POLICY_TTL_SECONDS
                or not verify_rsa_sha256(anchor.public_key_pem, policy.signed_bytes(), policy.signature)
            ):
                raise ReadAuthorizationDenied("G2_POLICY_MISSING_STALE_REVOKED_OR_INVALID")

            target = self._targets.resolve(request)  # type: ignore[union-attr]
            if (
                not target.canonical_target
                or not target.workspace_id
                or not target.checkout_id
                or not target.resolver_version
                or target.server_id != request.server_id
                or target.instance_id != request.instance_id
                or target.operation != request.operation
                or target.workspace_id != request.workspace_id
                or target.checkout_id != request.checkout_id
                or target.opened_target is not opened_target
                or target.target_binding_id != opened_target.target_binding_id
                or type(getattr(opened_target, "canonical_target", None)) is not str
                or target.canonical_target != opened_target.canonical_target
                or target.root_binding_id != opened_target.root_binding_id
                or target.policy_binding_id != opened_target.policy_binding_id
                or not target.root_binding_id
                or not target.policy_binding_id
            ):
                raise ReadAuthorizationDenied("G3_TARGET_RESOLUTION_INVALID")

            response = self._issuer.request_decision(request, target)  # type: ignore[union-attr]
            if response.peer_identity != mandate.issuer_id:
                raise ReadAuthorizationDenied("ISSUER_IPC_PEER_UNAUTHENTICATED")
            decision = response.decision
            if not _decision_matches(decision, request, target, mandate, policy, now):
                raise ReadAuthorizationDenied("SIGNED_DECISION_BINDING_INVALID")
            if not verify_rsa_sha256(mandate.issuer_public_key_pem, decision.signed_bytes(), decision.signature):
                raise ReadAuthorizationDenied("SIGNED_DECISION_SIGNATURE_INVALID")

            self._replay.consume_once(  # type: ignore[union-attr]
                challenge_id=request.challenge_id,
                nonce=request.nonce,
                decision_id=decision.decision_id,
                expires_at_epoch=decision.expires_at_epoch,
                now_epoch=now,
            )
            return ReadPermit(
                decision_id=decision.decision_id,
                requested_relative_target=request.requested_relative_target,
                canonical_target=target.canonical_target,
                operation=request.operation,
                workspace_id=target.workspace_id,
                checkout_id=target.checkout_id,
                policy_version=policy.version,
                resolver_version=target.resolver_version,
                expires_at_epoch=decision.expires_at_epoch,
                issued_at_epoch=decision.issued_at_epoch,
                opened_target=opened_target,
                target_binding_id=target.target_binding_id,
                root_binding_id=target.root_binding_id,
                policy_binding_id=target.policy_binding_id,
                coordinator_binding_id=self.coordinator_binding_id,
                _issuance_seal=self._permit_issuance_seal,
            )
        except ReadAuthorizationDenied:
            raise
        except Exception as exc:
            raise ReadAuthorizationDenied("AUTHORITY_DEPENDENCY_FAILED") from exc


def _validate_request(request: ReadRequest) -> None:
    values = (
        request.server_id,
        request.instance_id,
        request.service_fingerprint,
        request.local_principal_commitment,
        request.workspace_id,
        request.checkout_id,
        request.operation,
        request.challenge_id,
        request.nonce,
    )
    if any(not isinstance(value, str) or not value for value in values):
        raise ReadAuthorizationDenied("READ_REQUEST_INVALID")
    if not isinstance(request.requested_relative_target, str):
        raise ReadAuthorizationDenied("READ_REQUEST_INVALID")
    if (
        type(request.challenge_issued_at_epoch) is not int
        or type(request.challenge_expires_at_epoch) is not int
        or request.challenge_issued_at_epoch >= request.challenge_expires_at_epoch
    ):
        raise ReadAuthorizationDenied("READ_CHALLENGE_TIME_INVALID")
    if request.operation not in {"read_repo_file", "list_repo_directory"}:
        raise ReadAuthorizationDenied("READ_OPERATION_NOT_ALLOWED")
    if request.operation == "read_repo_file" and not request.requested_relative_target:
        raise ReadAuthorizationDenied("READ_REQUEST_TARGET_INVALID")


def _decision_matches(
    decision: SignedReadDecision,
    request: ReadRequest,
    target: ResolvedTarget,
    mandate: OwnerMandate,
    policy: G2PolicySnapshot,
    now: int,
) -> bool:
    if type(decision.issued_at_epoch) is not int or type(decision.expires_at_epoch) is not int:
        return False
    if type(decision.policy_version) is not int or decision.policy_version != policy.version:
        return False
    if (
        decision.expires_at_epoch <= now
        or decision.issued_at_epoch > now
        or decision.issued_at_epoch < request.challenge_issued_at_epoch
        or not isinstance(decision.decision_id, str)
        or not decision.decision_id
        or not isinstance(decision.signature, bytes)
        or not decision.signature
    ):
        return False
    if decision.expires_at_epoch > request.challenge_expires_at_epoch:
        return False
    if decision.expires_at_epoch - decision.issued_at_epoch > MAX_DECISION_TTL_SECONDS:
        return False
    return all((
        decision.decision_id,
        decision.mandate_id == mandate.mandate_id,
        decision.issuer_id == mandate.issuer_id,
        decision.server_id == request.server_id == target.server_id,
        decision.instance_id == request.instance_id == target.instance_id,
        decision.service_fingerprint == request.service_fingerprint,
        decision.local_principal_commitment == request.local_principal_commitment,
        decision.operation == request.operation == target.operation,
        decision.canonical_target == target.canonical_target,
        decision.workspace_id == target.workspace_id,
        decision.checkout_id == target.checkout_id,
        decision.policy_source_id == policy.source_id,
        decision.policy_version == policy.version,
        decision.resolver_version == target.resolver_version,
        decision.target_binding_id == target.target_binding_id,
        decision.root_binding_id == target.root_binding_id,
        decision.policy_binding_id == target.policy_binding_id,
        decision.challenge_id == request.challenge_id,
        decision.nonce == request.nonce,
        decision.signature,
    ))


def _canonical_json(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def public_key_fingerprint(public_key_pem: str) -> str:
    """Diagnostic fingerprint only; never an independent trust decision."""

    return hashlib.sha256(public_key_pem.encode("utf-8")).hexdigest()
