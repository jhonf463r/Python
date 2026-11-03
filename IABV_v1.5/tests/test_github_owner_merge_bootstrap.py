"""Offline contract tests for the GitHub Owner merge verifier.

MockTransport exercises API interpretation only; it is not evidence of TLS,
Windows issuer isolation, durable nonce consumption, or protected-read safety.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from iabv_v15.services.security.github_owner_merge_bootstrap import (
    BOOTSTRAP_MANIFEST_PATH,
    EXPECTED_OWNER_ID,
    EXPECTED_OWNER_LOGIN,
    EXPECTED_REPOSITORY,
    EXPECTED_REPOSITORY_ID,
    G1EnrollmentChallenge,
    OwnerAuthenticationEvidence,
    OwnerBootstrapChallengeConsumption,
    OwnerBootstrapEnrollmentReceipt,
    OwnerMergeVerificationEvidence,
    OwnerMergeVerificationError,
    OwnerBootstrapTrustRegistryPersistence,
    ProtectedIssuerCredentialEvidence,
    _GitHubApi,
    _verify_with_api,
    validate_owner_bootstrap_enrollment_receipt,
    validate_owner_bootstrap_evidence,
)
from iabv_v15.services.security.windows_crypto import (
    InvalidRsaPublicKey,
    validate_rsa_sha256_public_key_pem,
    verify_rsa_sha256,
)

NOW = datetime.now(timezone.utc).replace(microsecond=0)
NOW_EPOCH = int(NOW.timestamp())
PR_NUMBER = 47
MAIN_SHA = "a" * 40
MERGE_SHA = "b" * 40
PR_HEAD_SHA = "c" * 40


def _der(tag: int, value: bytes) -> bytes:
    if len(value) < 128:
        encoded_length = bytes([len(value)])
    else:
        length_bytes = len(value).to_bytes((len(value).bit_length() + 7) // 8, "big")
        encoded_length = bytes([0x80 | len(length_bytes)]) + length_bytes
    return bytes([tag]) + encoded_length + value


def _der_integer(value: bytes) -> bytes:
    return _der(0x02, (b"\x00" if value[0] & 0x80 else b"") + value)


def _rfc7515_rsa_public_key_pem() -> str:
    # Public test vector from RFC 7515 Appendix A.2; never a production root.
    n = (
        "ofgWCuLjybRlzo0tZWJjNiuSfb4p4fAkd_wWJcyQoTbji9k0l8W26mPddx"
        "HmfHQp-Vaw-4qPCJrcS2mJPMEzP1Pt0Bm4d4QlL-yRT-SFd2lZS-pCgNMs"
        "D1W_YpRPEwOWvG6b32690r2jZ47soMZo9wGzjb_7OMg0LOL-bSf63kpaSH"
        "SXndS5z5rexMdbBYUsLA9e-KXBdQOS-UTo7WTBEMa2R2CapHg665xsmtdV"
        "MTBQY4uDZlxvb3qCo5ZwKh9kG4LT6_I5IhlJH7aGhyxXFvUK-DWNmoudF8"
        "NAco9_h9iaGNj8q2ethFkMLs91kzk2PAcDTW9gb54h4FRWyuXpoQ"
    )
    modulus = base64.urlsafe_b64decode(n + "=" * (-len(n) % 4))
    exponent = b"\x01\x00\x01"
    rsa_key = _der(0x30, _der_integer(modulus) + _der_integer(exponent))
    algorithm = _der(0x30, bytes.fromhex("06092a864886f70d0101010500"))
    subject_public_key_info = _der(0x30, algorithm + _der(0x03, b"\x00" + rsa_key))
    encoded = base64.b64encode(subject_public_key_info).decode("ascii")
    body = "\n".join(encoded[index : index + 64] for index in range(0, len(encoded), 64))
    return f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----"


PUBLIC_KEY = _rfc7515_rsa_public_key_pem()


def _challenge(**changes: Any) -> G1EnrollmentChallenge:
    values: dict[str, Any] = {
        "challenge_id": "1" * 32,
        "nonce": "n" * 43,
        "server_id": "iabv-local-mcp",
        "issuer_id": "test-issuer",
        "instance_id": "11111111-1111-4111-8111-111111111111",
        "service_fingerprint": "2" * 64,
        "issuer_public_key_pem": PUBLIC_KEY,
        "local_principal_commitment": "3" * 64,
        "scopes": ("read_repo_file",),
        "policy_version": 1,
        "issued_at_epoch": NOW_EPOCH - 2,
        "expires_at_epoch": NOW_EPOCH + 600,
    }
    values.update(changes)
    return G1EnrollmentChallenge(**values)


def _git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def _content_payload(content: bytes) -> dict[str, Any]:
    return {
        "type": "file",
        "path": BOOTSTRAP_MANIFEST_PATH,
        "encoding": "base64",
        "size": len(content),
        "sha": _git_blob_sha(content),
        "content": base64.b64encode(content).decode("ascii"),
    }


def _state(challenge: G1EnrollmentChallenge) -> dict[str, Any]:
    approved_manifest = json.dumps(challenge.expected_manifest(), sort_keys=True).encode("utf-8")
    merged_epoch = challenge.issued_at_epoch + 1
    merged_at = datetime.fromtimestamp(merged_epoch, timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "repo": {
            "id": EXPECTED_REPOSITORY_ID,
            "full_name": EXPECTED_REPOSITORY,
            "owner": {"login": EXPECTED_OWNER_LOGIN, "id": EXPECTED_OWNER_ID},
        },
        "pr": {
            "number": PR_NUMBER,
            "state": "closed",
            "merged": True,
            "merged_at": merged_at,
            "merged_by": {"login": EXPECTED_OWNER_LOGIN, "id": EXPECTED_OWNER_ID},
            "merge_commit_sha": MERGE_SHA,
            "base": {"ref": "main", "repo": {"id": EXPECTED_REPOSITORY_ID}},
            "head": {"sha": PR_HEAD_SHA},
        },
        "branch_shas": [MAIN_SHA, MAIN_SHA],
        "branch_calls": 0,
        "files": [{"filename": BOOTSTRAP_MANIFEST_PATH, "status": "added"}],
        "associated_prs": [{
            "number": PR_NUMBER,
            "base": {"ref": "main", "repo": {"id": EXPECTED_REPOSITORY_ID}},
        }],
        "commit": {"sha": MERGE_SHA, "parents": [{"sha": PR_HEAD_SHA}]},
        "compare": {"status": "ahead", "merge_base_commit": {"sha": MERGE_SHA}},
        "merge_content": approved_manifest,
        "main_content": approved_manifest,
        "http_errors": {},
        "extra_headers": {},
    }


def _handler(state: dict[str, Any]):
    root = f"/repos/{EXPECTED_REPOSITORY}"

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.scheme == "https"
        assert request.url.host == "api.github.com"
        assert "authorization" not in request.headers
        path = request.url.path
        if path in state["http_errors"]:
            status, headers, body = state["http_errors"][path]
            return httpx.Response(status, headers=headers, json=body)
        if path == root:
            payload = state["repo"]
        elif path == f"{root}/pulls/{PR_NUMBER}":
            payload = state["pr"]
        elif path == f"{root}/branches/main":
            idx = state["branch_calls"]
            state["branch_calls"] += 1
            payload = {"name": "main", "commit": {"sha": state["branch_shas"][min(idx, len(state["branch_shas"]) - 1)]}}
        elif path == f"{root}/pulls/{PR_NUMBER}/files":
            payload = state["files"]
        elif path == f"{root}/commits/{MERGE_SHA}/pulls":
            payload = state["associated_prs"]
        elif path == f"{root}/commits/{MERGE_SHA}":
            payload = state["commit"]
        elif path == f"{root}/compare/{MERGE_SHA}...{MAIN_SHA}":
            payload = state["compare"]
        elif path == f"{root}/contents/{BOOTSTRAP_MANIFEST_PATH}":
            ref = request.url.params.get("ref")
            payload = _content_payload(state["merge_content"] if ref == MERGE_SHA else state["main_content"])
        else:
            return httpx.Response(404, json={"message": "unexpected route"})
        headers = state["extra_headers"].get(path, {})
        return httpx.Response(200, json=payload, headers=headers)

    return handle


def _verify(challenge: G1EnrollmentChallenge, state: dict[str, Any] | None = None):
    scenario = state if state is not None else _state(challenge)
    challenge.validate(now=NOW)
    with _GitHubApi(transport=httpx.MockTransport(_handler(scenario))) as api:
        return _verify_with_api(api, PR_NUMBER, challenge, clock=lambda: NOW)


def _expect_failure(code: str, challenge: G1EnrollmentChallenge, state: dict[str, Any] | None = None) -> None:
    with pytest.raises(OwnerMergeVerificationError) as caught:
        _verify(challenge, state)
    assert caught.value.code == code


def test_owner_merge_manifest_is_verified_at_merge_and_current_main() -> None:
    challenge = _challenge()
    expected_manifest = challenge.expected_manifest()
    assert expected_manifest["schema_version"] == 2
    assert expected_manifest["server_id"] == challenge.server_id
    assert expected_manifest["issuer_id"] == challenge.issuer_id
    evidence = _verify(challenge)
    assert evidence.pull_request_number == PR_NUMBER
    assert evidence.merge_commit_sha == MERGE_SHA
    assert evidence.main_sha == MAIN_SHA
    assert evidence.merged_by_id == EXPECTED_OWNER_ID
    assert evidence.challenge_id == challenge.challenge_id
    assert evidence.policy_version == challenge.policy_version
    assert evidence.manifest_git_blob_sha == _git_blob_sha(json.dumps(challenge.expected_manifest(), sort_keys=True).encode())
    assert evidence.manifest_sha256 == hashlib.sha256(json.dumps(challenge.expected_manifest(), sort_keys=True).encode()).hexdigest()


def test_manifest_schema_v1_is_rejected_as_unsupported() -> None:
    challenge = _challenge()
    state = _state(challenge)
    manifest = challenge.expected_manifest()
    manifest.pop("server_id")
    manifest.pop("issuer_id")
    manifest["schema_version"] = 1
    content = json.dumps(manifest, sort_keys=True).encode("utf-8")
    state["merge_content"] = content
    state["main_content"] = content
    _expect_failure("MANIFEST_SCHEMA_VERSION_UNSUPPORTED", challenge, state)


def test_rsa_public_key_parameters_are_strictly_validated() -> None:
    bits, exponent, modulus = validate_rsa_sha256_public_key_pem(PUBLIC_KEY)
    assert bits == 2048
    assert exponent == b"\x01\x00\x01"
    assert len(modulus) == 256
    with pytest.raises(InvalidRsaPublicKey):
        validate_rsa_sha256_public_key_pem("-----BEGIN PUBLIC KEY-----\nQUJD\n-----END PUBLIC KEY-----")


@pytest.mark.skipif(os.name != "nt", reason="signature primitive uses Windows CNG")
def test_windows_cng_verifies_rfc7515_rs256_vector_and_rejects_tampering() -> None:
    signing_input = (
        "eyJhbGciOiJSUzI1NiJ9."
        "eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFt"
        "cGxlLmNvbS9pc19yb290Ijp0cnVlfQ"
    ).encode("ascii")
    signature_b64 = (
        "cC4hiUPoj9Eetdgtv3hF80EGrhuB__dzERat0XF9g2VtQgr9PJbu3XOiZj5RZmh7"
        "AAuHIm4Bh-0Qc_lF5YKt_O8W2Fp5jujGbds9uJdbF9CUAr7t1dnZcAcQjbKBYNX4"
        "BAynRFdiuB--f_nZLgrnbyTyWzO75vRK5h6xBArLIARNPvkSjtQBMHlb1L07Qe7K"
        "0GarZRmB_eSN9383LcOLn6_dO--xi12jzDwusC-eOkHWEsqtFZESc6BfI7noOPqv"
        "hJ1phCnvWh6IeYI2w9QOYEUipUTI8np6LbgGY9Fs98rqVt5AXLIhWkWywlVmtVrB"
        "p0igcN_IoypGlUPQGe77Rw"
    )
    signature = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
    assert verify_rsa_sha256(PUBLIC_KEY, signing_input, signature) is True
    tampered = signing_input + b"x"
    assert verify_rsa_sha256(PUBLIC_KEY, tampered, signature) is False


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("repo_id", 1, "REPOSITORY_IDENTITY_MISMATCH"),
        ("owner_id", 1, "OWNER_IDENTITY_MISMATCH"),
        ("owner_login", "attacker", "OWNER_IDENTITY_MISMATCH"),
        ("merged", False, "PULL_REQUEST_NOT_MERGED"),
        ("actor_id", 1, "UNAUTHORIZED_MERGE_ACTOR"),
        ("base_ref", "other", "PULL_REQUEST_BASE_MISMATCH"),
        ("base_repo_id", 1, "PULL_REQUEST_BASE_MISMATCH"),
    ],
)
def test_rejects_wrong_repository_merge_state_or_actor(field: str, value: Any, error: str) -> None:
    challenge = _challenge()
    state = _state(challenge)
    if field == "repo_id": state["repo"]["id"] = value
    elif field == "owner_id": state["repo"]["owner"]["id"] = value
    elif field == "owner_login": state["repo"]["owner"]["login"] = value
    elif field == "merged": state["pr"]["merged"] = value
    elif field == "actor_id": state["pr"]["merged_by"]["id"] = value
    elif field == "base_ref": state["pr"]["base"]["ref"] = value
    elif field == "base_repo_id": state["pr"]["base"]["repo"]["id"] = value
    _expect_failure(error, challenge, state)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nonce", "x" * 43),
        ("instance_id", "22222222-2222-4222-8222-222222222222"),
        ("service_fingerprint", "f" * 64),
        ("issuer_public_key_pem", "-----BEGIN PUBLIC KEY-----\nQUJD\n-----END PUBLIC KEY-----"),
        ("local_principal_commitment", "e" * 64),
        ("scopes", ["list_repo_directory"]),
        ("policy_version", 2),
        ("expires_at_epoch", NOW_EPOCH + 601),
    ],
)
def test_manifest_must_match_every_pending_challenge_field(field: str, value: Any) -> None:
    challenge = _challenge()
    state = _state(challenge)
    manifest = challenge.expected_manifest()
    manifest[field] = value
    changed = json.dumps(manifest, sort_keys=True).encode("utf-8")
    state["merge_content"] = changed
    state["main_content"] = changed
    _expect_failure("MANIFEST_CHALLENGE_MISMATCH", challenge, state)


def test_manifest_with_extra_or_duplicate_keys_is_rejected() -> None:
    challenge = _challenge()
    state = _state(challenge)
    manifest = challenge.expected_manifest()
    manifest["approved_by"] = EXPECTED_OWNER_LOGIN
    content = json.dumps(manifest, sort_keys=True).encode("utf-8")
    state["merge_content"] = content
    state["main_content"] = content
    _expect_failure("MANIFEST_SCHEMA_MISMATCH", challenge, state)

    duplicate = b'{"schema_version":1,"schema_version":1}'
    state = _state(challenge)
    state["merge_content"] = duplicate
    state["main_content"] = duplicate
    _expect_failure("MANIFEST_JSON_INVALID", challenge, state)


def test_expired_challenge_is_rejected_before_any_http_request() -> None:
    challenge = _challenge(expires_at_epoch=NOW_EPOCH)
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(500)

    with pytest.raises(OwnerMergeVerificationError) as caught:
        with _GitHubApi(transport=httpx.MockTransport(handle)) as api:
            _verify_with_api(api, PR_NUMBER, challenge, clock=lambda: NOW)
    assert caught.value.code == "CHALLENGE_EXPIRED"
    assert calls == []


def test_manifest_changed_or_revoked_on_current_main_is_denied() -> None:
    challenge = _challenge()
    state = _state(challenge)
    current = json.loads(state["main_content"])
    current["revoked"] = True
    state["main_content"] = json.dumps(current, sort_keys=True).encode()
    _expect_failure("CURRENT_MAIN_MANIFEST_CHANGED", challenge, state)


def test_commit_must_be_associated_with_the_merged_pr_and_in_main() -> None:
    challenge = _challenge()
    state = _state(challenge)
    state["associated_prs"] = []
    _expect_failure("MERGE_COMMIT_NOT_ASSOCIATED_WITH_PR", challenge, state)

    state = _state(challenge)
    state["compare"] = {"status": "diverged", "merge_base_commit": {"sha": "d" * 40}}
    _expect_failure("MERGE_COMMIT_NOT_IN_MAIN", challenge, state)


def test_manifest_must_be_the_only_file_in_the_approved_pr() -> None:
    challenge = _challenge()
    state = _state(challenge)
    state["files"].append({"filename": "README.md", "status": "modified"})
    _expect_failure("MANIFEST_NOT_EXCLUSIVE_PR_CHANGE", challenge, state)


def test_http_quota_and_api_errors_fail_closed() -> None:
    challenge = _challenge()
    root = f"/repos/{EXPECTED_REPOSITORY}"
    state = _state(challenge)
    state["http_errors"][root] = (403, {"X-RateLimit-Remaining": "0"}, {"message": "rate limit"})
    _expect_failure("GITHUB_RATE_LIMITED", challenge, state)

    state = _state(challenge)
    state["http_errors"][root] = (503, {}, {"message": "unavailable"})
    _expect_failure("GITHUB_API_STATUS_ERROR", challenge, state)


def test_incomplete_paginated_file_list_and_missing_fields_fail_closed() -> None:
    challenge = _challenge()
    state = _state(challenge)
    files_path = f"/repos/{EXPECTED_REPOSITORY}/pulls/{PR_NUMBER}/files"
    state["extra_headers"][files_path] = {"Link": '<https://api.github.com/page/2>; rel="next"'}
    _expect_failure("PULL_REQUEST_FILES_INCOMPLETE", challenge, state)

    state = _state(challenge)
    state["pr"].pop("merged_by")
    _expect_failure("MERGED_BY_INVALID", challenge, state)


def test_main_moving_during_verification_denies() -> None:
    challenge = _challenge()
    state = _state(challenge)
    state["branch_shas"] = [MAIN_SHA, "d" * 40]
    _expect_failure("MAIN_MOVED_DURING_VERIFICATION", challenge, state)


def test_http_redirect_is_not_followed() -> None:
    challenge = _challenge()
    state = _state(challenge)
    root = f"/repos/{EXPECTED_REPOSITORY}"
    state["http_errors"][root] = (302, {"Location": "https://attacker.example/"}, {})
    _expect_failure("GITHUB_API_STATUS_ERROR", challenge, state)


def test_challenge_issuer_generates_distinct_nonce_and_bounded_expiry() -> None:
    args = {
        "server_id": "iabv-local-mcp",
        "issuer_id": "test-issuer",
        "instance_id": "11111111-1111-4111-8111-111111111111",
        "service_fingerprint": "2" * 64,
        "issuer_public_key_pem": PUBLIC_KEY,
        "local_principal_commitment": "3" * 64,
        "scopes": ("read_repo_file",),
        "policy_version": 1,
    }
    before = int(datetime.now(timezone.utc).timestamp())
    first = G1EnrollmentChallenge.issue(**args)
    second = G1EnrollmentChallenge.issue(**args)
    after = int(datetime.now(timezone.utc).timestamp())
    assert first.nonce != second.nonce
    assert first.challenge_id != second.challenge_id
    assert before <= first.issued_at_epoch <= after
    assert first.expires_at_epoch - first.issued_at_epoch <= 900


def _bootstrap_evidence(challenge: G1EnrollmentChallenge):
    owner = OwnerAuthenticationEvidence(
        owner_subject_id="owner-subject-from-test-verifier",
        owner_trust_anchor_id="independent-owner-root-test-only",
        credential_id="owner-credential-test-only",
        challenge_id=challenge.challenge_id,
        nonce=challenge.nonce,
        relying_party_id="iabv-owner-bootstrap",
        verified_at_epoch=NOW_EPOCH,
    )
    issuer = ProtectedIssuerCredentialEvidence(
        issuer_id="test-issuer",
        credential_id="test-issuer-credential",
        public_key_pem=challenge.issuer_public_key_pem,
        server_id=challenge.server_id,
        instance_id=challenge.instance_id,
        service_fingerprint=challenge.service_fingerprint,
        local_principal_commitment=challenge.local_principal_commitment,
        protected_key_reference="synthetic://issuer-key",
        issuer_process_identity="synthetic-test-only",
        valid_from_epoch=NOW_EPOCH - 10,
        expires_at_epoch=challenge.expires_at_epoch,
        revoked=False,
    )
    merge = OwnerMergeVerificationEvidence(
        pull_request_number=PR_NUMBER,
        merge_commit_sha=MERGE_SHA,
        main_sha=MAIN_SHA,
        manifest_git_blob_sha="d" * 40,
        merged_by_id=EXPECTED_OWNER_ID,
        challenge_id=challenge.challenge_id,
        policy_version=challenge.policy_version,
        manifest_sha256=hashlib.sha256(
            json.dumps(challenge.expected_manifest(), sort_keys=True).encode()
        ).hexdigest(),
    )
    return owner, issuer, merge


def test_owner_bootstrap_evidence_requires_exact_challenge_and_server_bindings() -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    validate_owner_bootstrap_evidence(
        challenge=challenge,
        owner=owner,
        issuer=issuer,
        merge=merge,
        now_epoch=NOW_EPOCH,
        expected_relying_party_id="iabv-owner-bootstrap",
        expected_owner_subject_id="owner-subject-from-test-verifier",
        expected_owner_trust_anchor_id="independent-owner-root-test-only",
        expected_issuer_id="test-issuer",
    )

    with pytest.raises(OwnerMergeVerificationError, match="OWNER_ASSERTION_UNTRUSTED_OR_MISMATCHED"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=replace(owner, nonce="x" * 43),
            issuer=issuer,
            merge=merge,
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )
    with pytest.raises(OwnerMergeVerificationError, match="ISSUER_CREDENTIAL_UNPROTECTED_OR_MISMATCHED"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=owner,
            issuer=replace(issuer, server_id="other-server"),
            merge=merge,
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_MERGE_EVIDENCE_MISMATCH"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=owner,
            issuer=issuer,
            merge=replace(merge, policy_version=challenge.policy_version + 1),
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_ASSERTION_UNTRUSTED_OR_MISMATCHED"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=replace(owner, owner_subject_id="caller-substituted-owner"),
            issuer=issuer,
            merge=merge,
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )
    with pytest.raises(OwnerMergeVerificationError, match="ISSUER_CREDENTIAL_UNPROTECTED_OR_MISMATCHED"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=owner,
            issuer=replace(issuer, issuer_id="caller-substituted-issuer"),
            merge=merge,
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )


def test_owner_bootstrap_evidence_rejects_expired_challenge_and_untrusted_owner() -> None:
    challenge = _challenge(expires_at_epoch=NOW_EPOCH)
    owner, issuer, merge = _bootstrap_evidence(challenge)
    with pytest.raises(OwnerMergeVerificationError, match="CHALLENGE_EXPIRED"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=owner,
            issuer=issuer,
            merge=merge,
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )

    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_ASSERTION_UNTRUSTED_OR_MISMATCHED"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=replace(owner, owner_trust_anchor_id=""),
            issuer=issuer,
            merge=merge,
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )


def test_owner_bootstrap_evidence_rejects_well_formed_wrong_manifest_digest() -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    wrong_digest = "0" * 64
    if wrong_digest == merge.manifest_sha256:
        wrong_digest = "1" * 64
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_MERGE_EVIDENCE_MISMATCH"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=owner,
            issuer=issuer,
            merge=replace(merge, manifest_sha256=wrong_digest),
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("manifest_git_blob_sha", "g" * 40),
        ("manifest_git_blob_sha", None),
        ("manifest_git_blob_sha", False),
        ("manifest_git_blob_sha", 123),
        ("manifest_git_blob_sha", "a" * 39),
        ("pull_request_number", 0),
        ("pull_request_number", -1),
        ("pull_request_number", True),
        ("pull_request_number", False),
        ("pull_request_number", None),
        ("pull_request_number", "47"),
        ("challenge_id", None),
        ("challenge_id", False),
        ("policy_version", None),
        ("policy_version", True),
        ("merged_by_id", None),
        ("merged_by_id", True),
        ("merge_commit_sha", None),
        ("merge_commit_sha", False),
        ("merge_commit_sha", 47),
        ("main_sha", None),
        ("main_sha", False),
        ("main_sha", 47),
        ("manifest_sha256", None),
        ("manifest_sha256", False),
        ("manifest_sha256", 47),
    ],
)
def test_malformed_merge_metadata_is_rejected_with_typed_error(field: str, value: Any) -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    with pytest.raises(OwnerMergeVerificationError, match="OWNER_MERGE_EVIDENCE_MISMATCH"):
        validate_owner_bootstrap_evidence(
            challenge=challenge,
            owner=owner,
            issuer=issuer,
            merge=replace(merge, **{field: value}),
            now_epoch=NOW_EPOCH,
            expected_relying_party_id="iabv-owner-bootstrap",
            expected_owner_subject_id="owner-subject-from-test-verifier",
            expected_owner_trust_anchor_id="independent-owner-root-test-only",
            expected_issuer_id="test-issuer",
        )


def _bootstrap_receipt(
    challenge: G1EnrollmentChallenge,
    owner: OwnerAuthenticationEvidence,
    issuer: ProtectedIssuerCredentialEvidence,
    merge: OwnerMergeVerificationEvidence,
) -> OwnerBootstrapEnrollmentReceipt:
    enrollment_id = "synthetic-enrollment-1"
    return OwnerBootstrapEnrollmentReceipt(
        receipt_id="synthetic-receipt-1",
        enrollment_id=enrollment_id,
        challenge_id=challenge.challenge_id,
        challenge_nonce=challenge.nonce,
        server_id=challenge.server_id,
        issuer_id=issuer.issuer_id,
        issuer_credential_id=issuer.credential_id,
        owner_subject_id=owner.owner_subject_id,
        owner_trust_anchor_id=owner.owner_trust_anchor_id,
        owner_credential_id=owner.credential_id,
        relying_party_id=owner.relying_party_id,
        policy_version=challenge.policy_version,
        outcome="ENROLLED",
        merge_evidence=merge,
        challenge_consumption=OwnerBootstrapChallengeConsumption(
            enrollment_id=enrollment_id,
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
            outcome="CONSUMED_ONCE",
            consumed_at_epoch=NOW_EPOCH,
            store_version=1,
            consumption_reference="synthetic-store-event-1",
        ),
        trust_registry_persistence=OwnerBootstrapTrustRegistryPersistence(
            enrollment_id=enrollment_id,
            outcome="PERSISTED",
            registry_id="synthetic-registry",
            registry_version=1,
            record_id="synthetic-record-1",
            persisted_at_epoch=NOW_EPOCH + 1,
            persistence_reference="synthetic-registry-event-1",
        ),
        issued_at_epoch=NOW_EPOCH + 2,
    )


def _validate_receipt(
    receipt: OwnerBootstrapEnrollmentReceipt,
    challenge: G1EnrollmentChallenge,
    owner: OwnerAuthenticationEvidence,
    issuer: ProtectedIssuerCredentialEvidence,
    merge: OwnerMergeVerificationEvidence,
    *,
    expected_registry_id: Any = "synthetic-registry",
) -> None:
    validate_owner_bootstrap_enrollment_receipt(
        receipt=receipt,
        challenge=challenge,
        owner=owner,
        issuer=issuer,
        merge=merge,
        now_epoch=NOW_EPOCH + 2,
        expected_relying_party_id="iabv-owner-bootstrap",
        expected_owner_subject_id="owner-subject-from-test-verifier",
        expected_owner_trust_anchor_id="independent-owner-root-test-only",
        expected_issuer_id="test-issuer",
        expected_registry_id=expected_registry_id,
    )


def test_enrollment_receipt_binds_complete_synthetic_result() -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = _bootstrap_receipt(challenge, owner, issuer, merge)

    # Synthetic references exercise the contract; they do not demonstrate
    # actual challenge consumption or persistence in a protected registry.
    _validate_receipt(receipt, challenge, owner, issuer, merge)


def test_enrollment_receipt_rejects_different_well_formed_registry_id() -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = _bootstrap_receipt(challenge, owner, issuer, merge)

    with pytest.raises(
        OwnerMergeVerificationError,
        match="ENROLLMENT_TRUST_REGISTRY_ID_MISMATCH",
    ):
        _validate_receipt(
            receipt,
            challenge,
            owner,
            issuer,
            merge,
            expected_registry_id="another-valid-registry",
        )


@pytest.mark.parametrize("expected_registry_id", ["", "   ", None, 17, False])
def test_enrollment_receipt_rejects_invalid_expected_registry_id(expected_registry_id: Any) -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = _bootstrap_receipt(challenge, owner, issuer, merge)

    with pytest.raises(OwnerMergeVerificationError, match="ENROLLMENT_RECEIPT_INVALID"):
        _validate_receipt(
            receipt,
            challenge,
            owner,
            issuer,
            merge,
            expected_registry_id=expected_registry_id,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("challenge_id", "f" * 32),
        ("challenge_nonce", "x" * 43),
        ("server_id", "other-server"),
        ("issuer_id", "other-issuer"),
        ("issuer_credential_id", "other-credential"),
        ("owner_subject_id", "other-owner"),
        ("owner_trust_anchor_id", "other-root"),
        ("owner_credential_id", "other-owner-credential"),
        ("relying_party_id", "other-rp"),
        ("policy_version", 2),
    ],
)
def test_enrollment_receipt_rejects_incompatible_identity_bindings(field: str, value: Any) -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = replace(_bootstrap_receipt(challenge, owner, issuer, merge), **{field: value})
    with pytest.raises(OwnerMergeVerificationError):
        _validate_receipt(receipt, challenge, owner, issuer, merge)


def test_enrollment_receipt_rejects_incompatible_merge_evidence() -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = replace(
        _bootstrap_receipt(challenge, owner, issuer, merge),
        merge_evidence=replace(merge, main_sha="f" * 40),
    )
    with pytest.raises(OwnerMergeVerificationError, match="ENROLLMENT_RECEIPT_BINDING_MISMATCH"):
        _validate_receipt(receipt, challenge, owner, issuer, merge)


@pytest.mark.parametrize(
    "change",
    [
        {"challenge_consumption": None},
        {"trust_registry_persistence": None},
        {"challenge_consumption": "missing"},
        {"trust_registry_persistence": "missing"},
        {"challenge_consumption": OwnerBootstrapChallengeConsumption(
            "synthetic-enrollment-1", "1" * 32, "n" * 43, "CONSUMED_ONCE", NOW_EPOCH, 1, ""
        )},
        {"trust_registry_persistence": OwnerBootstrapTrustRegistryPersistence(
            "synthetic-enrollment-1", "PERSISTED", "synthetic-registry", 1, "synthetic-record-1", NOW_EPOCH + 1, ""
        )},
    ],
)
def test_enrollment_receipt_rejects_missing_or_invalid_persistence_references(change: dict[str, Any]) -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = replace(_bootstrap_receipt(challenge, owner, issuer, merge), **change)
    with pytest.raises(OwnerMergeVerificationError):
        _validate_receipt(receipt, challenge, owner, issuer, merge)


@pytest.mark.parametrize(
    "change",
    [
        {"outcome": "PENDING"},
        {"outcome": None},
        {"issued_at_epoch": True},
        {"policy_version": True},
        {"merge_evidence": None},
        {"challenge_consumption": OwnerBootstrapChallengeConsumption(
            "wrong-enrollment", "1" * 32, "n" * 43, "CONSUMED_ONCE", NOW_EPOCH, 1, "synthetic-store-event"
        )},
        {"challenge_consumption": OwnerBootstrapChallengeConsumption(
            "synthetic-enrollment-1", "1" * 32, "n" * 43, "NOT_CONSUMED", NOW_EPOCH, 1, "synthetic-store-event"
        )},
        {"trust_registry_persistence": OwnerBootstrapTrustRegistryPersistence(
            "wrong-enrollment", "PERSISTED", "synthetic-registry", 1, "synthetic-record", NOW_EPOCH + 1, "synthetic-registry-event"
        )},
        {"trust_registry_persistence": OwnerBootstrapTrustRegistryPersistence(
            "synthetic-enrollment-1", "PENDING", "synthetic-registry", 1, "synthetic-record", NOW_EPOCH + 1, "synthetic-registry-event"
        )},
        {"trust_registry_persistence": OwnerBootstrapTrustRegistryPersistence(
            "synthetic-enrollment-1", "PERSISTED", "synthetic-registry", True, "synthetic-record", NOW_EPOCH + 1, "synthetic-registry-event"
        )},
    ],
)
def test_incomplete_or_malformed_enrollment_receipt_is_not_success(change: dict[str, Any]) -> None:
    challenge = _challenge()
    owner, issuer, merge = _bootstrap_evidence(challenge)
    receipt = replace(_bootstrap_receipt(challenge, owner, issuer, merge), **change)
    with pytest.raises(OwnerMergeVerificationError):
        _validate_receipt(receipt, challenge, owner, issuer, merge)
