"""Source tests for the typed authorization chain.

Provider fixtures and their test-only key labels are not production roots or
Windows process-authentication evidence. The native signature vector is tested
separately through Windows CNG in test_github_owner_merge_bootstrap.py.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import sqlite3
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from iabv_v15.services.security.github_owner_merge_bootstrap import (
    EXPECTED_OWNER_ID,
    EXPECTED_REPOSITORY_ID,
    OwnerMergeVerificationEvidence,
)
from iabv_v15.infra.mcp.server import IABVMCPServer
from iabv_v15.services.security.read_authorization import (
    AuthenticatedIssuerResponse,
    G2PolicySnapshot,
    OwnerMandate,
    ReadAuthorizationDecision,
    ReadAuthorizationCoordinator,
    ReadAuthorizationDenied,
    ReadDecisionEffect,
    ReadRequest,
    ResolvedTarget,
    SignedReadDecision,
    SQLiteReplayConsumer,
    TrustAnchor,
)

NOW = 1_800_000_000
_RSA_N_B64URL = (
    "ofgWCuLjybRlzo0tZWJjNiuSfb4p4fAkd_wWJcyQoTbji9k0l8W26mPddx"
    "HmfHQp-Vaw-4qPCJrcS2mJPMEzP1Pt0Bm4d4QlL-yRT-SFd2lZS-pCgNMs"
    "D1W_YpRPEwOWvG6b32690r2jZ47soMZo9wGzjb_7OMg0LOL-bSf63kpaSH"
    "SXndS5z5rexMdbBYUsLA9e-KXBdQOS-UTo7WTBEMa2R2CapHg665xsmtdV"
    "MTBQY4uDZlxvb3qCo5ZwKh9kG4LT6_I5IhlJH7aGhyxXFvUK-DWNmoudF8"
    "NAco9_h9iaGNj8q2ethFkMLs91kzk2PAcDTW9gb54h4FRWyuXpoQ"
)
_RSA_D_B64URL = (
    "Eq5xpGnNCivDflJsRQBXHx1hdR1k6Ulwe2JZD50LpXyWPEAeP88vLNO97I"
    "jlA7_GQ5sLKMgvfTeXZx9SE-7YwVol2NXOoAJe46sui395IW_GO-pWJ1O0"
    "BkTGoVEn2bKVRUCgu-GjBVaYLU6f3l9kJfFNS3E0QbVdxzubSu3Mkqzjkn"
    "439X0M_V51gfpRLI9JYanrC4D4qAdGcopV_0ZHHzQlBjudU2QvXt4ehNYT"
    "CBr6XCLQUShb1juUO1ZdiYoFaFQT5Tw8bGUl_x_jTj3ccPDVZFD9pIuhLh"
    "BOneufuBiB4cS98l2SR_RQyGWSeWjnczT0QU91p1DhOVRuOopznQ"
)


def _der(tag: int, value: bytes) -> bytes:
    if len(value) < 128:
        encoded_length = bytes([len(value)])
    else:
        length = len(value).to_bytes((len(value).bit_length() + 7) // 8, "big")
        encoded_length = bytes([0x80 | len(length)]) + length
    return bytes([tag]) + encoded_length + value


def _rsa_public_key_pem(modulus: bytes | None = None) -> str:
    n = modulus or base64.urlsafe_b64decode(_RSA_N_B64URL + "=" * (-len(_RSA_N_B64URL) % 4))
    n_der = _der(0x02, (b"\x00" if n[0] & 0x80 else b"") + n)
    e_der = _der(0x02, b"\x01\x00\x01")
    rsa_key = _der(0x30, n_der + e_der)
    algorithm = _der(0x30, bytes.fromhex("06092a864886f70d0101010500"))
    spki = _der(0x30, algorithm + _der(0x03, b"\x00" + rsa_key))
    encoded = base64.b64encode(spki).decode("ascii")
    body = "\n".join(encoded[i : i + 64] for i in range(0, len(encoded), 64))
    return f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----"


_TEST_PUBLIC_KEY_PEM = _rsa_public_key_pem()


def _test_only_rfc_signature(message: bytes) -> bytes:
    """Use RFC 7515's published test key; it is not a production credential."""

    n = int.from_bytes(base64.urlsafe_b64decode(_RSA_N_B64URL + "=" * (-len(_RSA_N_B64URL) % 4)), "big")
    d = int.from_bytes(base64.urlsafe_b64decode(_RSA_D_B64URL + "=" * (-len(_RSA_D_B64URL) % 4)), "big")
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(message).digest()
    encoded = b"\x00\x01" + b"\xff" * (256 - len(digest_info) - 3) + b"\x00" + digest_info
    return pow(int.from_bytes(encoded, "big"), d, n).to_bytes(256, "big")


requires_cng = pytest.mark.skipif(os.name != "nt", reason="authorization signature path uses Windows CNG")


class _Trust:
    def __init__(self, anchor: TrustAnchor | None = None) -> None:
        self.anchor = anchor or TrustAnchor(
            anchor_id="test-root-only",
            public_key_pem=_TEST_PUBLIC_KEY_PEM,
            policy_source_id="test-policy-source",
            valid_from_epoch=NOW - 100,
            expires_at_epoch=NOW + 10_000,
            revoked=False,
        )

    def current_anchor(self) -> TrustAnchor:
        return self.anchor


class _Mandates:
    def __init__(self, mandate: OwnerMandate | None = None) -> None:
        value = mandate or OwnerMandate(
            mandate_id="test-mandate",
            anchor_id="test-root-only",
            repository_id=EXPECTED_REPOSITORY_ID,
            owner_id=EXPECTED_OWNER_ID,
            merged_pr_number=489,
            merge_commit_sha="a" * 40,
            issuer_id="test-issuer-process",
            issuer_public_key_pem=_TEST_PUBLIC_KEY_PEM,
            server_id="server-test",
            instance_id="instance-test",
            service_fingerprint="e" * 64,
            local_principal_commitment="f" * 64,
            allowed_operations=("read_repo_file", "list_repo_directory"),
            policy_version=4,
            issued_at_epoch=NOW - 10,
            expires_at_epoch=NOW + 500,
            revoked=False,
            signature=b"",
        )
        self.mandate = replace(value, signature=_test_only_rfc_signature(value.signed_bytes()))

    def current_mandate(self, anchor_id: str) -> OwnerMandate:
        return self.mandate


class _Merges:
    def __init__(self, evidence: OwnerMergeVerificationEvidence | None = None) -> None:
        self.evidence = evidence or OwnerMergeVerificationEvidence(
            pull_request_number=489,
            merge_commit_sha="a" * 40,
            main_sha="b" * 40,
            manifest_git_blob_sha="c" * 40,
            merged_by_id=EXPECTED_OWNER_ID,
            challenge_id="test-challenge",
            policy_version=4,
            manifest_sha256="d" * 64,
        )

    def verified_merge(self, pull_request_number: int) -> OwnerMergeVerificationEvidence:
        return self.evidence


class _Policies:
    def __init__(self, policy: G2PolicySnapshot | None = None) -> None:
        value = policy or G2PolicySnapshot(
            source_id="test-policy-source",
            anchor_id="test-root-only",
            version=4,
            issued_at_epoch=NOW - 5,
            expires_at_epoch=NOW + 300,
            revoked_mandate_ids=(),
            allowed_operations=("read_repo_file", "list_repo_directory"),
            signature=b"",
            root_binding_id="synthetic-root-binding",
            policy_binding_id="synthetic-policy-binding",
        )
        self.policy = replace(value, signature=_test_only_rfc_signature(value.signed_bytes()))

    def current_policy(self, source_id: str) -> G2PolicySnapshot:
        return self.policy


class _Targets:
    def __init__(self, target: ResolvedTarget | None = None) -> None:
        self._dynamic = target is None
        self.target = target or ResolvedTarget(
            server_id="server-test",
            instance_id="instance-test",
            operation="read_repo_file",
            canonical_target="docs/readme.md",
            workspace_id="workspace-7",
            checkout_id="checkout-7",
            resolver_version="resolver-test-v1",
            root_binding_id="synthetic-root-binding",
            policy_binding_id="synthetic-policy-binding",
        )

    def resolve(self, request: ReadRequest) -> ResolvedTarget:
        assert request.opened_target is not None
        values = {}
        if self._dynamic:
            values = {
                "operation": request.operation,
                "canonical_target": request.opened_target.canonical_target,
                "workspace_id": request.opened_target.workspace_id,
                "checkout_id": request.opened_target.checkout_id,
                "resolver_version": request.opened_target.resolver_version,
            }
        return replace(
            self.target,
            **values,
            opened_target=request.opened_target,
            target_binding_id=request.opened_target.target_binding_id,
            root_binding_id=request.opened_target.root_binding_id,
            policy_binding_id=request.opened_target.policy_binding_id,
        )


class _Issuer:
    def __init__(self, decision: SignedReadDecision | None = None, peer: str = "test-issuer-process") -> None:
        self._dynamic = decision is None
        if decision is None:
            value = SignedReadDecision(
                decision_id="test-decision",
                mandate_id="test-mandate",
                issuer_id="test-issuer-process",
                server_id="server-test",
                instance_id="instance-test",
                service_fingerprint="e" * 64,
                local_principal_commitment="f" * 64,
                operation="read_repo_file",
                canonical_target="docs/readme.md",
                workspace_id="workspace-7",
                checkout_id="checkout-7",
                policy_source_id="test-policy-source",
                policy_version=4,
                resolver_version="resolver-test-v1",
                challenge_id="test-challenge",
                nonce="test-nonce-once",
                issued_at_epoch=NOW - 1,
                expires_at_epoch=NOW + 30,
                signature=b"",
                target_binding_id="synthetic-target-binding",
                root_binding_id="synthetic-root-binding",
                policy_binding_id="synthetic-policy-binding",
            )
            self.decision = replace(value, signature=_test_only_rfc_signature(value.signed_bytes()))
        else:
            self.decision = decision
        self.peer = peer

    def request_decision(self, request: ReadRequest, target: ResolvedTarget) -> AuthenticatedIssuerResponse:
        decision = self.decision
        if self._dynamic:
            decision = replace(
                decision,
                server_id=request.server_id,
                instance_id=request.instance_id,
                service_fingerprint=request.service_fingerprint,
                local_principal_commitment=request.local_principal_commitment,
                operation=request.operation,
                canonical_target=target.canonical_target,
                workspace_id=target.workspace_id,
                checkout_id=target.checkout_id,
                resolver_version=target.resolver_version,
                target_binding_id=target.target_binding_id,
                root_binding_id=target.root_binding_id,
                policy_binding_id=target.policy_binding_id,
                challenge_id=request.challenge_id,
                nonce=request.nonce,
                signature=b"",
            )
            decision = replace(decision, signature=_test_only_rfc_signature(decision.signed_bytes()))
        return AuthenticatedIssuerResponse(peer_identity=self.peer, decision=decision)


class _Replay:
    def __init__(self) -> None:
        self.consumed: list[tuple[str, str, str]] = []

    def consume_once(self, *, challenge_id: str, nonce: str, decision_id: str, expires_at_epoch: int, now_epoch: int) -> None:
        self.consumed.append((challenge_id, nonce, decision_id))


def _opened_target(operation: str = "read_repo_file", relative_target: str = "docs/readme.md") -> SimpleNamespace:
    return SimpleNamespace(
        is_open=True,
        operation=operation,
        relative_target=relative_target,
        target_binding_id="synthetic-target-binding",
        canonical_target=relative_target,
        workspace_id="workspace-7",
        checkout_id="checkout-7",
        resolver_version="resolver-test-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )


def _request() -> ReadRequest:
    return ReadRequest(
        server_id="server-test",
        instance_id="instance-test",
        service_fingerprint="e" * 64,
        local_principal_commitment="f" * 64,
        workspace_id="workspace-7",
        checkout_id="checkout-7",
        operation="read_repo_file",
        requested_relative_target="docs/readme.md",
        challenge_id="test-challenge",
        nonce="test-nonce-once",
        challenge_issued_at_epoch=NOW - 5,
        challenge_expires_at_epoch=NOW + 60,
        opened_target=_opened_target(),
    )


class _RequestContext:
    """Synthetic host-side context factory; never wired by AppBootstrap."""

    def create_request(self, *, operation: str, requested_relative_target: str) -> ReadRequest:
        return replace(
            _request(),
            operation=operation,
            requested_relative_target=requested_relative_target,
        )


class _McpStub:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


class _WorldModel:
    def current_model(self):
        return SimpleNamespace(
            network_status=SimpleNamespace(connected=True),
            block_records=[],
            permission_gates=[],
        )


def _mcp_server(coordinator: ReadAuthorizationCoordinator, workspace_root: str) -> tuple[IABVMCPServer, _McpStub]:
    stub = _McpStub()
    container = SimpleNamespace(
        config=SimpleNamespace(workspace_root=workspace_root),
        workspace_root=workspace_root,
        world_model_service=_WorldModel(),
        read_authorization_coordinator=coordinator,
    )
    return IABVMCPServer(
        container,
        mcp=stub,
        read_authorization_coordinator=coordinator,
    ), stub


def _coordinator(
    *,
    trust: object | None = None,
    mandates: object | None = None,
    merges: object | None = None,
    policies: object | None = None,
    targets: object | None = None,
    issuer: object | None = None,
    replay: object | None = None,
    request_context: object | None = None,
) -> ReadAuthorizationCoordinator:
    return ReadAuthorizationCoordinator(
        trust_provider=trust if trust is not None else _Trust(),
        mandate_provider=mandates if mandates is not None else _Mandates(),
        merge_evidence_provider=merges if merges is not None else _Merges(),
        policy_provider=policies if policies is not None else _Policies(),
        target_resolver=targets if targets is not None else _Targets(),
        issuer_client=issuer if issuer is not None else _Issuer(),
        replay_consumer=replay if replay is not None else _Replay(),
        request_context_provider=request_context,
        clock=lambda: NOW,
    )


@requires_cng
def test_test_fixture_chain_returns_exact_scoped_permit() -> None:
    replay = _Replay()
    coordinator = _coordinator(replay=replay)
    request = _request()
    permit = coordinator.authorize(request)
    assert permit.canonical_target == "docs/readme.md"
    assert permit.opened_target is request.opened_target
    assert permit.target_binding_id == permit.opened_target.target_binding_id
    assert permit.root_binding_id == permit.opened_target.root_binding_id
    assert permit.policy_binding_id == permit.opened_target.policy_binding_id
    assert permit.operation == "read_repo_file"
    assert permit.workspace_id == "workspace-7"
    assert permit.checkout_id == "checkout-7"
    assert permit.policy_version == 4
    assert replay.consumed == [("test-challenge", "test-nonce-once", "test-decision")]


@requires_cng
def test_mcp_decision_is_typed_allow_only_after_full_synthetic_chain() -> None:
    coordinator = _coordinator(request_context=_RequestContext())
    decision = coordinator.decide_mcp_read(
        operation="read_repo_file",
        requested_relative_target="docs/readme.md",
        opened_target=_opened_target(),
    )
    assert isinstance(decision, ReadAuthorizationDecision)
    assert decision.effect is ReadDecisionEffect.ALLOW
    assert decision.reason == "AUTHORIZED"
    assert decision.permit is not None
    assert decision.permit.operation == "read_repo_file"
    assert decision.permit.requested_relative_target == "docs/readme.md"
    assert decision.permit.canonical_target == "docs/readme.md"
    assert decision.permit.opened_target is not None
    assert decision.permit._issuance_seal is coordinator._permit_issuance_seal


@pytest.mark.parametrize(
    ("operation", "relative_target"),
    [("read_repo_file", "docs/readme.md"), ("list_repo_directory", "docs")],
)
def test_mcp_authorized_helper_consumes_the_same_opened_object(
    tmp_path, monkeypatch, operation: str, relative_target: str,
) -> None:  # type: ignore[no-untyped-def]
    from iabv_v15.infra.mcp.windows_handle_reader import (
        OpenedTargetCapability,
        OwnedWindowsHandle,
        WorkspaceRootCapability,
    )

    coordinator = _coordinator(request_context=_RequestContext())
    server, mcp_stub = _mcp_server(coordinator, str(tmp_path))
    opened = OpenedTargetCapability(
        handle=OwnedWindowsHandle(731),
        operation=operation,
        relative_target=relative_target,
        workspace_id="workspace-7",
        checkout_id="checkout-7",
        resolver_version="resolver-test-v1",
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
    )
    opened.close = lambda: None
    root = WorkspaceRootCapability(
        handle=OwnedWindowsHandle(732),
        workspace_id="workspace-7",
        checkout_id="checkout-7",
        expected_volume_serial=1,
        expected_file_id=b"\x00" * 16,
        root_binding_id="synthetic-root-binding",
        policy_binding_id="synthetic-policy-binding",
        resolver_version="resolver-test-v1",
    )
    server.container.approved_workspace_root_provider = SimpleNamespace(
        current_workspace_root=lambda: root,
    )
    monkeypatch.setattr(
        "iabv_v15.infra.mcp.server.windows_handle_reader.open_target",
        lambda _root, _path, _operation: opened,
    )
    helper_calls: list[object] = []

    def consume_exact(target, **kwargs):  # type: ignore[no-untyped-def]
        assert target is opened
        assert target._begin_consume(operation) == 731
        helper_calls.append(target)
        target._end_consume()
        return {"status": "ok", "target": target.canonical_target}

    helper_name = "read_opened_file" if operation == "read_repo_file" else "list_opened_directory"
    monkeypatch.setattr(f"iabv_v15.infra.mcp.server.windows_handle_reader.{helper_name}", consume_exact)
    result = mcp_stub.tools[operation](relative_path=relative_target)  # type: ignore[operator]
    assert result == {"status": "ok", "target": relative_target}
    assert helper_calls == [opened]


def test_mcp_decision_denies_when_production_boundary_providers_are_missing() -> None:
    coordinator = ReadAuthorizationCoordinator(
        trust_provider=None,
        mandate_provider=None,
        merge_evidence_provider=None,
        policy_provider=None,
        target_resolver=None,
        issuer_client=None,
        replay_consumer=None,
        request_context_provider=None,
        clock=lambda: NOW,
    )
    decision = coordinator.decide_mcp_read(
        operation="read_repo_file",
        requested_relative_target="docs/readme.md",
        opened_target=_opened_target(),
    )
    assert decision.effect is ReadDecisionEffect.DENY
    assert decision.permit is None
    assert decision.reason == (
        "AUTHORITY_REQUIREMENTS_MISSING:INDEPENDENT_TRUST_ROOT_PROVIDER,OWNER_MANDATE_PROVIDER,"
        "OWNER_MERGE_EVIDENCE_PROVIDER,G2_POLICY_PROVIDER,G3_TARGET_RESOLVER,AUTHENTICATED_ISSUER_IPC,"
        "PERSISTENT_REPLAY_CONSUMER,HOST_OWNED_SERVER_PROCESS_IDENTITY"
    )


@requires_cng
def test_valid_synthetic_chain_stays_denied_without_approved_workspace_root(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    coordinator = _coordinator(request_context=_RequestContext())
    server, mcp_stub = _mcp_server(coordinator, str(tmp_path))
    assert server._read_authorization_coordinator is coordinator
    opened_target = _opened_target()
    decision = coordinator.decide_mcp_read(
        operation="read_repo_file",
        requested_relative_target="docs/readme.md",
        opened_target=opened_target,
    )
    assert decision.effect is ReadDecisionEffect.ALLOW
    assert decision.permit is not None
    assert decision.permit.opened_target is opened_target

    def fail_if_helper_invoked(*args: object, **kwargs: object) -> dict[str, object]:
        pytest.fail("un helper volvió a resolver la ruta en vez de consumir el destino autorizado")

    monkeypatch.setattr("iabv_v15.infra.mcp.server.windows_handle_reader.read_opened_file", fail_if_helper_invoked)
    monkeypatch.setattr(coordinator, "decide_mcp_read", lambda **kwargs: decision)
    result = mcp_stub.tools["read_repo_file"](relative_path="docs/readme.md")  # type: ignore[operator]
    assert result["governance_blocked"] is True  # type: ignore[index]
    assert result["reason"] == "APPROVED_WORKSPACE_ROOT_UNAVAILABLE"  # type: ignore[index]


@requires_cng
def test_signature_expiry_replay_scope_revocation_and_ipc_denials_never_call_mcp_reader(
    tmp_path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    invalid_signature = _Issuer(replace(_Issuer().decision, signature=b"invalid"))
    expired = _Issuer(replace(_Issuer().decision, expires_at_epoch=NOW))
    wrong_server = _Issuer(replace(_Issuer().decision, server_id="another-server"))
    wrong_target = _Targets(replace(_Targets().target, checkout_id="another-checkout"))
    revoked_policy = _Policies(replace(_Policies().policy, revoked_mandate_ids=("test-mandate",)))

    class ReplayFailure:
        def consume_once(self, **kwargs: object) -> None:
            raise ReadAuthorizationDenied("REPLAY_NONCE_OR_DECISION_REUSED")

    coordinators = (
        _coordinator(request_context=_RequestContext(), issuer=invalid_signature),
        _coordinator(request_context=_RequestContext(), issuer=expired),
        _coordinator(request_context=_RequestContext(), replay=ReplayFailure()),
        _coordinator(request_context=_RequestContext(), issuer=wrong_server),
        _coordinator(request_context=_RequestContext(), targets=wrong_target),
        _coordinator(request_context=_RequestContext(), policies=revoked_policy),
        _coordinator(request_context=_RequestContext(), issuer=_Issuer(peer="untrusted-process")),
    )

    def forbidden_reader(*args: object, **kwargs: object) -> dict[str, object]:
        pytest.fail("un rechazo de autorización invocó el helper MCP")

    monkeypatch.setattr("iabv_v15.infra.mcp.server.audit_tools.read_repo_file", forbidden_reader)
    monkeypatch.setattr("iabv_v15.infra.mcp.server.audit_tools.list_repo_directory", forbidden_reader)
    for coordinator in coordinators:
        server, mcp_stub = _mcp_server(coordinator, str(tmp_path))
        result = mcp_stub.tools["read_repo_file"](relative_path="docs/readme.md")  # type: ignore[operator]
        assert result["governance_blocked"] is True  # type: ignore[index]
        list_result = mcp_stub.tools["list_repo_directory"](relative_path="docs")  # type: ignore[operator]
        assert list_result["governance_blocked"] is True  # type: ignore[index]


@pytest.mark.parametrize(
    "provider",
    [
        "trust",
        "mandates",
        "merges",
        "policies",
        "targets",
        "issuer",
        "replay",
    ],
)
def test_missing_g1_g2_g3_issuer_or_replay_provider_denies(provider: str) -> None:
    kwargs = {provider: None}
    coordinator = ReadAuthorizationCoordinator(
        trust_provider=kwargs.get("trust", _Trust()),
        mandate_provider=kwargs.get("mandates", _Mandates()),
        merge_evidence_provider=kwargs.get("merges", _Merges()),
        policy_provider=kwargs.get("policies", _Policies()),
        target_resolver=kwargs.get("targets", _Targets()),
        issuer_client=kwargs.get("issuer", _Issuer()),
        replay_consumer=kwargs.get("replay", _Replay()),
        clock=lambda: NOW,
    )
    with pytest.raises(ReadAuthorizationDenied, match="AUTHORITY_PROVIDER_UNAVAILABLE"):
        coordinator.authorize(_request())


@requires_cng
def test_untrusted_root_signature_and_missing_mandate_deny() -> None:
    bad_modulus = bytearray(base64.urlsafe_b64decode(_RSA_N_B64URL + "=" * (-len(_RSA_N_B64URL) % 4)))
    bad_modulus[-1] ^= 0x02
    wrong_root = _Trust(replace(_Trust().anchor, public_key_pem=_rsa_public_key_pem(bytes(bad_modulus))))
    bad_signature = _coordinator(trust=wrong_root)
    with pytest.raises(ReadAuthorizationDenied):
        bad_signature.authorize(_request())

    class MissingMandate:
        def current_mandate(self, anchor_id: str) -> OwnerMandate:
            raise LookupError("no mandate")

    with pytest.raises(ReadAuthorizationDenied, match="AUTHORITY_DEPENDENCY_FAILED"):
        _coordinator(mandates=MissingMandate()).authorize(_request())


@requires_cng
def test_wrong_owner_merge_or_revoked_g2_policy_denies() -> None:
    wrong_merge = _Merges(replace(_Merges().evidence, merged_by_id=1))
    with pytest.raises(ReadAuthorizationDenied, match="OWNER_MANDATE_INVALID_OR_UNTRUSTED"):
        _coordinator(merges=wrong_merge).authorize(_request())

    revoked_policy = _Policies(replace(_Policies().policy, revoked_mandate_ids=("test-mandate",)))
    with pytest.raises(ReadAuthorizationDenied, match="G2_POLICY_MISSING_STALE_REVOKED_OR_INVALID"):
        _coordinator(policies=revoked_policy).authorize(_request())

    wrong_root = _Policies(replace(_Policies().policy, root_binding_id="other-root"))
    with pytest.raises(ReadAuthorizationDenied, match="G2_POLICY_MISSING_STALE_REVOKED_OR_INVALID"):
        _coordinator(policies=wrong_root).authorize(_request())
    wrong_policy_binding = _Policies(replace(_Policies().policy, policy_binding_id="other-policy"))
    with pytest.raises(ReadAuthorizationDenied, match="G2_POLICY_MISSING_STALE_REVOKED_OR_INVALID"):
        _coordinator(policies=wrong_policy_binding).authorize(_request())


@requires_cng
def test_exact_boolean_false_mandate_revocation_allows_synthetic_chain() -> None:
    mandate = _Mandates().mandate
    assert type(mandate.revoked) is bool
    assert mandate.revoked is False
    assert _coordinator(mandates=_Mandates(replace(mandate, revoked=False))).authorize(_request())

    with pytest.raises(ReadAuthorizationDenied, match="OWNER_MANDATE_INVALID_OR_UNTRUSTED"):
        _coordinator(mandates=_Mandates(replace(mandate, revoked=True))).authorize(_request())


@requires_cng
@pytest.mark.parametrize("revoked", [0, "", None, []])
def test_falsey_non_boolean_mandate_revocation_is_rejected(revoked: object) -> None:
    malformed = replace(_Mandates().mandate, revoked=revoked)  # type: ignore[arg-type]
    with pytest.raises(ReadAuthorizationDenied, match="OWNER_MANDATE_INVALID_OR_UNTRUSTED"):
        _coordinator(mandates=_Mandates(malformed)).authorize(_request())


@requires_cng
def test_wrong_issuer_or_target_decision_denies_before_replay_consumption() -> None:
    replay = _Replay()
    with pytest.raises(ReadAuthorizationDenied, match="ISSUER_IPC_PEER_UNAUTHENTICATED"):
        _coordinator(issuer=_Issuer(peer="untrusted-process"), replay=replay).authorize(_request())
    assert replay.consumed == []

    wrong_target = _Targets(replace(_Targets().target, checkout_id="another-checkout"))
    with pytest.raises(ReadAuthorizationDenied, match="G3_TARGET_RESOLUTION_INVALID"):
        _coordinator(targets=wrong_target, replay=replay).authorize(_request())
    assert replay.consumed == []


@requires_cng
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("server_id", "other-server"),
        ("instance_id", "other-instance"),
        ("service_fingerprint", "0" * 64),
        ("local_principal_commitment", "1" * 64),
        ("operation", "list_repo_directory"),
        ("canonical_target", "other-target"),
        ("workspace_id", "other-workspace"),
        ("checkout_id", "other-checkout"),
        ("policy_version", 99),
        ("resolver_version", "other-resolver"),
        ("root_binding_id", "other-root"),
        ("policy_binding_id", "other-policy"),
        ("challenge_id", "other-challenge"),
        ("nonce", "other-nonce"),
    ],
)
def test_decision_must_match_server_instance_operation_target_and_policy(field: str, value: object) -> None:
    replay = _Replay()
    decision = replace(_Issuer().decision, **{field: value})
    with pytest.raises(ReadAuthorizationDenied, match="SIGNED_DECISION_BINDING_INVALID"):
        _coordinator(issuer=_Issuer(decision=decision), replay=replay).authorize(_request())
    assert replay.consumed == []


@requires_cng
def test_expired_or_badly_signed_decision_denies_before_replay() -> None:
    replay = _Replay()
    expired = _Issuer(replace(_Issuer().decision, expires_at_epoch=NOW))
    with pytest.raises(ReadAuthorizationDenied, match="SIGNED_DECISION_BINDING_INVALID"):
        _coordinator(issuer=expired, replay=replay).authorize(_request())
    invalid_signature = _Issuer(replace(_Issuer().decision, signature=b"bad"))
    with pytest.raises(ReadAuthorizationDenied, match="SIGNED_DECISION_SIGNATURE_INVALID"):
        _coordinator(issuer=invalid_signature, replay=replay).authorize(_request())
    assert replay.consumed == []


def test_sqlite_replay_store_denies_missing_corrupt_and_reused_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    missing = SQLiteReplayConsumer(tmp_path / "missing.sqlite")
    with pytest.raises(ReadAuthorizationDenied, match="REPLAY_STORE_MISSING"):
        missing.consume_once(
            challenge_id="c", nonce="n", decision_id="d", expires_at_epoch=NOW + 1, now_epoch=NOW,
        )

    corrupt_path = tmp_path / "corrupt.sqlite"
    corrupt_path.write_bytes(b"not a sqlite database")
    corrupt = SQLiteReplayConsumer(corrupt_path)
    with pytest.raises(ReadAuthorizationDenied):
        corrupt.consume_once(
            challenge_id="c", nonce="n", decision_id="d", expires_at_epoch=NOW + 1, now_epoch=NOW,
        )

    store = SQLiteReplayConsumer(tmp_path / "replay.sqlite")
    store.initialize_empty_for_service_provisioning()
    kwargs = dict(challenge_id="c", nonce="n", decision_id="d", expires_at_epoch=NOW + 30, now_epoch=NOW)
    store.consume_once(**kwargs)
    with pytest.raises(ReadAuthorizationDenied, match="REPLAY_NONCE_OR_DECISION_REUSED"):
        store.consume_once(**kwargs)


def test_sqlite_replay_store_fails_closed_on_persistence_error(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteReplayConsumer(tmp_path / "replay.sqlite")
    store.initialize_empty_for_service_provisioning()

    def fail_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        raise OSError("fixture storage failure")

    monkeypatch.setattr(store, "_connect", fail_connect)
    with pytest.raises(ReadAuthorizationDenied, match="REPLAY_STORE_CONSUME_FAILED_OR_REPEATED"):
        store.consume_once(
            challenge_id="c", nonce="n", decision_id="d", expires_at_epoch=NOW + 1, now_epoch=NOW,
        )


def test_sqlite_replay_store_allows_only_one_concurrent_consumer(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteReplayConsumer(tmp_path / "replay.sqlite")
    store.initialize_empty_for_service_provisioning()
    kwargs = dict(challenge_id="concurrent-c", nonce="concurrent-n", decision_id="concurrent-d",
                  expires_at_epoch=NOW + 30, now_epoch=NOW)
    barrier = threading.Barrier(2)

    def consume() -> str:
        barrier.wait(timeout=2)
        try:
            store.consume_once(**kwargs)
            return "CONSUMED"
        except ReadAuthorizationDenied as exc:
            return exc.reason

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: consume(), range(2)))
    assert results.count("CONSUMED") == 1
    assert results.count("REPLAY_NONCE_OR_DECISION_REUSED") == 1


@requires_cng
def test_fixture_positive_does_not_claim_production_root_or_ipc() -> None:
    """The engine fixture checks composition only; the IPC peer is not OS-proven."""
    permit = _coordinator().authorize(_request())
    assert permit.decision_id == "test-decision"
