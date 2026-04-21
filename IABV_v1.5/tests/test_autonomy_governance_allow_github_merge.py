"""Unit tests for ``AutonomyGovernancePolicy.allow_github_merge``.

Verifica las reglas Nivel 1 de auto-merge gobernado: sin evidencia bloqueamos,
CI debe estar verde, diff acotado, no tocar rutas sensibles, no tocar tests,
no mergear drafts ni PRs con ``CHANGES_REQUESTED``.

La politica debe ser defensiva por defecto: falta de metadata = bloqueo, no
optimismo.
"""

from __future__ import annotations

from iabv_v15.services.adaptive.autonomy_governance_policy import (
    AutonomyGovernancePolicy,
)


def _ok_metadata() -> dict[str, object]:
    return {
        'pull_number': 123,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 40,
        'deletions': 10,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/services/tools/tool_adapters.py',
            'src/iabv_v15/services/tools/tool_registry.py',
            'docs/adapters.md',
        ],
    }


def test_allow_github_merge_accepts_safe_pr_metadata() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_merge(pr_metadata=_ok_metadata())

    assert allowed is True
    assert reason is None


def test_allow_github_merge_blocks_without_metadata() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_merge(pr_metadata=None)

    assert allowed is False
    assert reason is not None and 'pr_metadata' in reason


def test_allow_github_merge_blocks_empty_metadata() -> None:
    policy = AutonomyGovernancePolicy()

    allowed, reason = policy.allow_github_merge(pr_metadata={})

    assert allowed is False
    assert reason is not None


def test_allow_github_merge_blocks_draft_pr() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['draft'] = True

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'draft' in reason.lower()


def test_allow_github_merge_blocks_when_ci_not_green() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['ci_status'] = 'failure'

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'CI' in reason


def test_allow_github_merge_blocks_when_ci_pending() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['ci_status'] = 'pending'

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False


def test_allow_github_merge_blocks_when_changes_requested() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['reviews'] = [
        {'state': 'APPROVED'},
        {'state': 'CHANGES_REQUESTED'},
    ]

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'changes_requested' in reason.lower()


def test_allow_github_merge_blocks_when_diff_too_large() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['additions'] = 180
    meta['deletions'] = 50  # total 230 > 200

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'Diff' in reason


def test_allow_github_merge_blocks_when_too_many_files() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_files'] = 20

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'archivos' in reason.lower()


def test_allow_github_merge_blocks_missing_additions_field() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta.pop('additions')

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'Diff size' in reason


def test_allow_github_merge_blocks_missing_reviews_field() -> None:
    # El contrato dice: campo ausente => bloqueo. Si el caller no pasa
    # reviews no podemos decir que no hay changes_requested.
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta.pop('reviews')

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'reviews' in reason.lower()


def test_allow_github_merge_blocks_reviews_explicit_none() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['reviews'] = None

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'reviews' in reason.lower()


def test_allow_github_merge_blocks_reviews_wrong_type() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['reviews'] = 'APPROVED'

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None


def test_allow_github_merge_accepts_empty_reviews_list() -> None:
    # Lista vacia es evidencia explicita de "cero reviews existentes"
    # (distinto de ausente). El resto de los gates deciden.
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['reviews'] = []

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is True
    assert reason is None


def test_allow_github_merge_blocks_missing_changed_paths_field() -> None:
    # El red finding original: sin changed_paths no podiamos verificar rutas
    # sensibles ni tests => habia que bloquear, no permitir silenciosamente.
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta.pop('changed_paths')

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'changed_paths' in reason.lower()


def test_allow_github_merge_blocks_changed_paths_explicit_none() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = None

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'changed_paths' in reason.lower()


def test_allow_github_merge_accepts_empty_changed_paths_list() -> None:
    # Lista vacia es evidencia explicita (p.ej. PR con solo merge commit).
    # Puede parecer raro, pero es estado valido y no cambia rutas sensibles.
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = []
    meta['changed_files'] = 0
    meta['additions'] = 0
    meta['deletions'] = 0

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is True
    assert reason is None


def test_allow_github_merge_blocks_sensitive_path_bootstrap() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = [
        'src/iabv_v15/bootstrap.py',
        'docs/adapters.md',
    ]

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'sensible' in reason.lower()


def test_allow_github_merge_blocks_sensitive_path_domain_models() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = ['src/iabv_v15/domain/models.py']

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None


def test_allow_github_merge_blocks_sensitive_path_policy_itself() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = [
        'src/iabv_v15/services/adaptive/autonomy_governance_policy.py',
    ]

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None


def test_allow_github_merge_blocks_github_workflow_changes() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = ['.github/workflows/ci.yml']

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False


def test_allow_github_merge_blocks_test_only_changes() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = [
        'tests/test_tool_registry.py',
        'tests/test_github_api_adapter.py',
    ]

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False
    assert reason is not None and 'tests' in reason.lower()


def test_allow_github_merge_blocks_mixed_path_including_tests() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = [
        'src/iabv_v15/services/tools/tool_adapters.py',
        'tests/test_github_api_adapter.py',
    ]

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False


def test_allow_github_merge_handles_path_with_leading_slash() -> None:
    # Algunos clientes devuelven el path con / inicial; no debe escapar la
    # deteccion de ruta sensible.
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['changed_paths'] = ['/src/iabv_v15/bootstrap.py']

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is False


def test_allow_github_merge_accepts_boundary_200_lines() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['additions'] = 150
    meta['deletions'] = 50  # total exactly 200

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is True
    assert reason is None


def test_allow_github_merge_ignores_malformed_review_entries() -> None:
    policy = AutonomyGovernancePolicy()
    meta = _ok_metadata()
    meta['reviews'] = [
        'not-a-dict',
        None,
        {'state': 'APPROVED'},
    ]

    allowed, reason = policy.allow_github_merge(pr_metadata=meta)

    assert allowed is True
    assert reason is None
