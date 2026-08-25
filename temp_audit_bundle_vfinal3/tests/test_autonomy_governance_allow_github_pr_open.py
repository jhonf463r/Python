"""Unit tests for ``AutonomyGovernancePolicy.allow_github_pr_open``.

Gate para abrir PRs (no mergear). Las reglas son por patron de rama:
``iabv-auto/*`` puede auto-abrir si el diff es pequeno; ``devin/*`` siempre
requiere humano; ``main`` / ``master`` nunca son head validos; base distinto
de main/master requiere humano.
"""

from __future__ import annotations

from iabv_v15.services.adaptive.autonomy_governance_policy import (
    AutonomyGovernancePolicy,
)


def test_iabv_auto_branch_small_diff_auto_approved() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='iabv-auto/123-small-fix', base='main', diff_lines=40,
    )

    assert allowed is True
    assert reason is None


def test_iabv_auto_branch_without_diff_lines_requires_human() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='iabv-auto/123', base='main', diff_lines=None,
    )

    assert allowed is False
    assert reason is not None and 'diff_lines desconocido' in reason


def test_iabv_auto_branch_large_diff_requires_human() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='iabv-auto/123', base='main', diff_lines=500,
    )

    assert allowed is False
    assert reason is not None and '500' in reason


def test_iabv_auto_branch_negative_diff_lines_rejected() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='iabv-auto/bad', base='main', diff_lines=-1,
    )

    assert allowed is False
    assert reason is not None and 'negativo' in reason


def test_devin_branch_always_requires_human() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='devin/1776797946-foo', base='main', diff_lines=10,
    )

    assert allowed is False
    assert reason is not None and 'devin/*' in reason


def test_main_cannot_be_head() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='main', base='main', diff_lines=10,
    )

    assert allowed is False
    assert reason is not None and 'PR contra si mismo' in reason


def test_empty_branch_rejected() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='', base='main', diff_lines=10,
    )

    assert allowed is False
    assert reason is not None and 'vacio' in reason


def test_base_not_main_requires_human() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='iabv-auto/abc', base='feature/xyz', diff_lines=10,
    )

    assert allowed is False
    assert reason is not None and 'main/master' in reason


def test_arbitrary_branch_requires_human() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='feature/foo', base='main', diff_lines=5,
    )

    assert allowed is False
    assert reason is not None and 'patron no reconocido' in reason


def test_master_as_base_allowed_for_iabv_auto() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_pr_open(
        branch='iabv-auto/backport', base='master', diff_lines=50,
    )

    assert allowed is True
    assert reason is None
