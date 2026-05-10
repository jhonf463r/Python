"""Tests para `_chat_research_backlog_findings` en OSES.

Valida que OperationalSelfExaminationService consuma el backlog escrito
por `ChatCapabilityIngestionService` (``data/chat_research_backlog/``) y
produzca `SelfExaminationFinding` de categoria ``research_gap`` agrupados
por ``kind``, sin inventar observacion si el backlog no existe.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import IssueSeverity
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_service(workspace: Path) -> OperationalSelfExaminationService:
    storage = ArtifactStorage(str(workspace / 'evolution'))
    return OperationalSelfExaminationService(
        workspace_root=str(workspace),
        storage=storage,
    )


def _write_backlog_entry(
    backlog_dir: Path,
    *,
    session_id: str,
    kind: str,
    label: str,
    matched_text: str,
    research_hint: str,
    detected_at_utc: str = '2025-01-01T00:00:00+00:00',
    status: str = 'open',
    raw_message: str = 'tengo gpu',
) -> None:
    backlog_dir.mkdir(parents=True, exist_ok=True)
    target = backlog_dir / f'{session_id}.jsonl'
    record = {
        'schema_version': 1,
        'session_id': session_id,
        'detected_at_utc': detected_at_utc,
        'kind': kind,
        'label': label,
        'matched_text': matched_text,
        'research_hint': research_hint,
        'raw_message': raw_message,
        'status': status,
    }
    with target.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + '\n')


def test_chat_research_backlog_findings_emits_finding_per_open_entry() -> None:
    workspace = _workspace('oses_backlog_basic')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    _write_backlog_entry(
        backlog_dir,
        session_id='session-a',
        kind='hardware_gpu',
        label='GPU disponible (sin benchmark)',
        matched_text='gpu',
        research_hint='Medir si esta GPU acelera inferencia local vs CPU.',
    )
    _write_backlog_entry(
        backlog_dir,
        session_id='session-b',
        kind='local_model',
        label='Modelo local mencionado',
        matched_text='qwen3',
        research_hint='Probar qwen3 contra la ruta default del StrategySelector.',
        detected_at_utc='2025-02-01T00:00:00+00:00',
    )

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert len(findings) == 2
    kinds = {finding.metadata.get('kind') for finding in findings}
    assert kinds == {'hardware_gpu', 'local_model'}
    for finding in findings:
        assert finding.category == 'research_gap'
        assert finding.severity == IssueSeverity.MEDIUM
        assert finding.recommendation  # viene del research_hint
        assert 'ChatCapabilityIngestionService' in finding.source_refs


def test_chat_research_backlog_findings_labels_operational_directives() -> None:
    workspace = _workspace('oses_backlog_operational_directive')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    _write_backlog_entry(
        backlog_dir,
        session_id='session-op',
        kind='operational_self_testing',
        label='Auto-test de algoritmos, rendimiento y razonamiento',
        matched_text='testea los algoritmos',
        research_hint='Usar AutonomousValidationCycle, ExperimentLab y OSES para probar configuraciones.',
    )

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert len(findings) == 1
    finding = findings[0]
    assert finding.title.startswith('Directiva operativa sin validar')
    assert 'directiva operativa' in finding.summary.lower()
    assert finding.metadata['kind'] == 'operational_self_testing'


def test_chat_research_backlog_findings_returns_empty_when_no_backlog() -> None:
    workspace = _workspace('oses_backlog_missing')

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert findings == []


def test_chat_research_backlog_findings_returns_empty_when_dir_exists_but_no_files() -> None:
    workspace = _workspace('oses_backlog_empty_dir')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    backlog_dir.mkdir(parents=True, exist_ok=True)

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert findings == []


def test_chat_research_backlog_findings_deduplicates_by_kind() -> None:
    workspace = _workspace('oses_backlog_dedupe')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    # Tres menciones de GPU en dos sesiones distintas y una mencion
    # anterior: deberia producir un unico finding con metadata agregada.
    _write_backlog_entry(
        backlog_dir,
        session_id='session-a',
        kind='hardware_gpu',
        label='GPU disponible (sin benchmark)',
        matched_text='gpu',
        research_hint='Medir si esta GPU acelera inferencia local.',
        detected_at_utc='2025-01-01T00:00:00+00:00',
    )
    _write_backlog_entry(
        backlog_dir,
        session_id='session-a',
        kind='hardware_gpu',
        label='GPU disponible (sin benchmark)',
        matched_text='cuda',
        research_hint='Medir si esta GPU acelera inferencia local.',
        detected_at_utc='2025-01-02T00:00:00+00:00',
    )
    _write_backlog_entry(
        backlog_dir,
        session_id='session-b',
        kind='hardware_gpu',
        label='GPU disponible (sin benchmark)',
        matched_text='rtx 4090',
        research_hint='Medir si esta GPU acelera inferencia local.',
        detected_at_utc='2025-03-15T00:00:00+00:00',
    )

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert len(findings) == 1
    finding = findings[0]
    assert finding.metadata.get('kind') == 'hardware_gpu'
    assert finding.metadata.get('occurrences') == 3
    assert sorted(finding.metadata.get('sessions') or []) == ['session-a', 'session-b']
    # la entrada con detected_at_utc mas reciente gana el matched_text visible
    assert finding.metadata.get('matched_text') == 'rtx 4090'
    assert finding.metadata.get('latest_detected_at_utc') == '2025-03-15T00:00:00+00:00'


def test_chat_research_backlog_findings_ignores_non_open_status() -> None:
    workspace = _workspace('oses_backlog_status')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    _write_backlog_entry(
        backlog_dir,
        session_id='session-a',
        kind='hardware_gpu',
        label='GPU disponible (sin benchmark)',
        matched_text='gpu',
        research_hint='Medir si esta GPU acelera inferencia local.',
        status='resolved',
    )

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert findings == []


def test_chat_research_backlog_findings_skips_malformed_lines() -> None:
    workspace = _workspace('oses_backlog_malformed')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    backlog_dir.mkdir(parents=True, exist_ok=True)
    target = backlog_dir / 'session-a.jsonl'
    with target.open('w', encoding='utf-8') as handle:
        handle.write('not-json-at-all\n')
        handle.write('\n')  # linea vacia
        handle.write(json.dumps({'schema_version': 1, 'status': 'open', 'kind': ''}) + '\n')  # sin kind
        handle.write(
            json.dumps(
                {
                    'schema_version': 1,
                    'session_id': 'session-a',
                    'detected_at_utc': '2025-04-01T00:00:00+00:00',
                    'kind': 'local_runtime',
                    'label': 'Runtime local mencionado',
                    'matched_text': 'docker',
                    'research_hint': 'Agregar docker al ToolRegistry.',
                    'raw_message': 'tengo docker instalado',
                    'status': 'open',
                }
            )
            + '\n'
        )

    service = _make_service(workspace)
    findings = service._chat_research_backlog_findings()

    assert len(findings) == 1
    assert findings[0].metadata.get('kind') == 'local_runtime'


def test_build_review_includes_backlog_findings() -> None:
    workspace = _workspace('oses_backlog_build_review')
    backlog_dir = workspace / 'data' / 'chat_research_backlog'
    _write_backlog_entry(
        backlog_dir,
        session_id='session-a',
        kind='external_account',
        label='Cuenta o acceso externo mencionado',
        matched_text='claude',
        research_hint='Verificar en el ToolRegistry si la cuenta esta conectada.',
    )

    service = _make_service(workspace)
    review = service.build_review()

    research_gap_findings = [f for f in review.findings if f.category == 'research_gap']
    assert research_gap_findings, 'OSES debe surfacear research_gap en build_review()'
    assert any(f.metadata.get('kind') == 'external_account' for f in research_gap_findings)
