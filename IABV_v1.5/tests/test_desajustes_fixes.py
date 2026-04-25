"""Tests for desajuste fixes: tool confidence stamp, OSES recurring issue
severity scaling, and corrective block guidance in the orchestrator.
"""

from __future__ import annotations

from datetime import datetime, timezone

from iabv_v15.domain.models import (
    IssueSeverity,
    OperationalBlockRecord,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
    AdaptiveTaskOrchestrator,
)


# ── Fix 1: tool confidence stamp (tested via bootstrap integration) ──


# ── Fix 2: OSES recurring issue severity scaling ──

def test_recurring_issues_severity_scales_with_count() -> None:
    """Severity should scale: LOW < 2, MEDIUM 2-4, HIGH >= 5."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)

    project_health_low = {'repeated_issues': [{'issue_hint': 'minor_glitch', 'count': 1}]}
    project_health_med = {'repeated_issues': [{'issue_hint': 'tool_timeout', 'count': 3}]}
    project_health_high = {'repeated_issues': [{'issue_hint': 'latest_failure', 'count': 7}]}

    result_low = service._recurring_issues(findings=[], project_health=project_health_low)
    result_med = service._recurring_issues(findings=[], project_health=project_health_med)
    result_high = service._recurring_issues(findings=[], project_health=project_health_high)

    assert result_low[0]['severity'] == IssueSeverity.LOW.value
    assert result_med[0]['severity'] == IssueSeverity.MEDIUM.value
    assert result_high[0]['severity'] == IssueSeverity.HIGH.value


def test_recurring_issues_confidence_scales_with_count() -> None:
    """Higher count => higher confidence, capped at 0.80."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)

    ph_low = {'repeated_issues': [{'issue_hint': 'a', 'count': 1}]}
    ph_high = {'repeated_issues': [{'issue_hint': 'b', 'count': 10}]}

    r_low = service._recurring_issues(findings=[], project_health=ph_low)
    r_high = service._recurring_issues(findings=[], project_health=ph_high)

    assert r_low[0]['confidence'] < r_high[0]['confidence']
    assert r_high[0]['confidence'] <= 0.80


def test_recurring_issues_summary_includes_corrective_note() -> None:
    """Summary should mention corrective action."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)

    ph = {'repeated_issues': [{'issue_hint': 'latest_failure', 'count': 7}]}
    result = service._recurring_issues(findings=[], project_health=ph)

    assert 'accion correctiva' in result[0]['summary'].lower()


# ── Fix 3: corrective guidance for tool blocks ──

def test_corrective_guidance_for_known_blocks() -> None:
    """Known block types should produce corrective guidance entries."""
    model = WorldModelSnapshot(
        block_records=[
            OperationalBlockRecord(block_type='wrong_thread', target_scope='codex', assistant_kind='codex'),
            OperationalBlockRecord(block_type='awaiting_response', target_scope='chatgpt', assistant_kind='chatgpt'),
            OperationalBlockRecord(block_type='no_disponible', target_scope='claude', assistant_kind='claude'),
        ],
    )
    guidance = AdaptiveTaskOrchestrator._corrective_guidance_for_blocks(model)

    assert len(guidance) == 3
    types = {g['block_type'] for g in guidance}
    assert types == {'wrong_thread', 'awaiting_response', 'no_disponible'}

    codex_guidance = next(g for g in guidance if g['assistant_kind'] == 'codex')
    assert 'hilo nuevo' in codex_guidance['action'].lower() or 'hilo incorrecto' in codex_guidance['action'].lower()

    chatgpt_guidance = next(g for g in guidance if g['assistant_kind'] == 'chatgpt')
    assert 'pendiente' in chatgpt_guidance['action'].lower()

    claude_guidance = next(g for g in guidance if g['assistant_kind'] == 'claude')
    assert 'instalada' in claude_guidance['action'].lower()


def test_corrective_guidance_deduplicates_blocks() -> None:
    """Duplicate block_type+assistant combos should be deduped."""
    model = WorldModelSnapshot(
        block_records=[
            OperationalBlockRecord(block_type='wrong_thread', target_scope='codex', assistant_kind='codex'),
            OperationalBlockRecord(block_type='wrong_thread', target_scope='codex', assistant_kind='codex'),
            OperationalBlockRecord(block_type='wrong_thread', target_scope='codex2', assistant_kind='codex'),
        ],
    )
    guidance = AdaptiveTaskOrchestrator._corrective_guidance_for_blocks(model)
    assert len(guidance) == 1


def test_corrective_guidance_empty_when_no_blocks() -> None:
    """No blocks => no guidance."""
    model = WorldModelSnapshot()
    guidance = AdaptiveTaskOrchestrator._corrective_guidance_for_blocks(model)
    assert guidance == []


def test_corrective_guidance_skips_unknown_block_types() -> None:
    """Unknown block types should not produce guidance entries."""
    model = WorldModelSnapshot(
        block_records=[
            OperationalBlockRecord(block_type='some_unknown_block', target_scope='x', assistant_kind='x'),
        ],
    )
    guidance = AdaptiveTaskOrchestrator._corrective_guidance_for_blocks(model)
    assert guidance == []


def test_world_model_summary_includes_corrective_guidance() -> None:
    """When blocks exist, _world_model_summary should include corrective_guidance."""
    model = WorldModelSnapshot(
        block_records=[
            OperationalBlockRecord(block_type='wrong_thread', target_scope='codex', assistant_kind='codex'),
        ],
    )
    orch = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
    summary = orch._world_model_summary(model)
    assert 'corrective_guidance' in summary
    assert len(summary['corrective_guidance']) == 1


def test_world_model_summary_omits_corrective_guidance_when_no_blocks() -> None:
    """When no blocks, corrective_guidance key should be absent."""
    model = WorldModelSnapshot()
    orch = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
    summary = orch._world_model_summary(model)
    assert 'corrective_guidance' not in summary


# ── Fix 7: Runtime log self-inspection findings ──────────────


def test_runtime_log_findings_detects_patterns(tmp_path) -> None:
    """_runtime_log_findings should detect anomaly patterns in own log."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )
    from iabv_v15.infra.persistence.storage import ArtifactStorage

    # Create a fake workspace with a log file
    log_dir = tmp_path / 'src' / 'data'
    log_dir.mkdir(parents=True)
    log_file = log_dir / 'iabv_v15.log'
    log_lines = [
        '2026-04-25 13:58:15 | INFO | tool_adapters | multi_source_disagreement: codex_installed\n',
        '2026-04-25 13:58:32 | INFO | tool_adapters | multi_source_disagreement: chatgpt_installed\n',
        '2026-04-25 14:01:27 | INFO | tool_adapters | multi_source_disagreement: codex_installed\n',
        '2026-04-25 14:01:27 | INFO | tool_adapters | multi_source_disagreement: chatgpt_installed\n',
        '2026-04-25 14:03:40 | INFO | viewmodel | No pude completar la consulta externa\n',
    ]
    log_file.write_text(''.join(log_lines), encoding='utf-8')

    storage = ArtifactStorage(root=str(tmp_path / 'artifacts'))
    service = OperationalSelfExaminationService(
        workspace_root=str(tmp_path),
        storage=storage,
    )

    findings = service._runtime_log_findings()

    categories = {f.category for f in findings}
    assert 'runtime_noise' in categories
    assert 'external_consultation_failure' in categories

    noise_finding = next(f for f in findings if f.category == 'runtime_noise')
    assert noise_finding.metadata['occurrences'] == 4
    assert noise_finding.confidence == 0.9


def test_runtime_log_findings_empty_when_no_log(tmp_path) -> None:
    """No log file -> no findings (not an error)."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )
    from iabv_v15.infra.persistence.storage import ArtifactStorage

    storage = ArtifactStorage(root=str(tmp_path / 'artifacts'))
    service = OperationalSelfExaminationService(
        workspace_root=str(tmp_path),
        storage=storage,
    )

    assert service._runtime_log_findings() == []


# ── Fix 8: scan_configured_secrets file-based alias resolution ──


def test_scan_configured_secrets_resolves_file_aliases(monkeypatch, tmp_path) -> None:
    """Secrets in ~/.iabv_secrets.ps1 should satisfy alias groups even if
    not loaded in os.environ."""
    import os
    from iabv_v15.services.account_resource_scanner import scan_configured_secrets

    # Clear all relevant env vars
    for name in ('GITHUB_TOKEN_IABV', 'IABV_GITHUB_TOKEN', 'GITHUB_TOKEN',
                 'GH_TOKEN', 'DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY',
                 'DEVIN_API_KEY'):
        monkeypatch.delenv(name, raising=False)

    # Write a secrets file with GITHUB_TOKEN_IABV configured
    secrets_file = tmp_path / '.iabv_secrets.ps1'
    secrets_file.write_text(
        "$env:GITHUB_TOKEN_IABV = 'ghp_test123'\n"
        "$env:DEVIN_API_KEY_IABV = 'cog_test456'\n",
        encoding='utf-8',
    )
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)

    result = scan_configured_secrets()

    # Both alias groups should be resolved from file
    assert 'GITHUB_TOKEN_IABV' not in result['missing']
    assert 'DEVIN_API_KEY_IABV' not in result['missing']
    assert 'GITHUB_TOKEN_IABV' in result['configured']
    assert 'DEVIN_API_KEY_IABV' in result['configured']
