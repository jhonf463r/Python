"""P0.136B: Agent Session Gate connection to PortableContext and OSES.

Tests focalizados para:
- PortableContext exporta audit_control_master si existe latest.json
- PortableContext marca UNRESOLVED si falta latest.json
- OSES detecta tarea stale/parcial desde snapshot
- OSES detecta duplicate_risks desde snapshot
- OSES no falla si el snapshot está corrupto
"""
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from iabv_v15.domain.models import SelfExaminationFinding, IssueSeverity, utc_now
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_portable_context_exports_audit_control_master_if_latest_json_exists() -> None:
    """PortableContext exporta sección audit_control_master si existe latest.json."""
    root = _workspace('audit_control_master_export')
    try:
        # Crear agent_session_gate/latest.json
        gate_dir = root / 'data' / 'evolution' / 'agent_session_gate'
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_snapshot = {
            'generated_at': utc_now().isoformat(),
            'agent': 'devin',
            'mode': 'pre',
            'active_objectives': [
                {
                    'id': 'task_1',
                    'title': 'Test task 1',
                    'priority': 'critical',
                    'status': 'PENDING',
                    'next_action': 'Implement task 1',
                }
            ],
            'stale_or_partial_tasks': [
                {
                    'id': 'task_2',
                    'title': 'Stale task',
                    'declared_status': 'PENDING',
                    'verification_status': 'CODE_NOT_STARTED',
                    'inferred_state': 'STALE_OR_PARTIAL',
                    'evidence': ['src/test.py'],
                    'path': 'data/evolution/platform_pending/task_2.json',
                }
            ],
            'duplicate_risks': [
                {
                    'kind': 'DUPLICATED',
                    'symbol': 'test_method',
                    'path': 'src/test.py',
                    'lines': [10, 20],
                    'unresolved': 'UNRESOLVED:duplicate_definition:test_method',
                }
            ],
            'human_review_required': True,
            'unresolved': [],
        }
        with open(gate_dir / 'latest.json', 'w', encoding='utf-8') as f:
            json.dump(gate_snapshot, f, ensure_ascii=False, indent=2)

        service = PortableContextService(
            workspace_root=str(root),
            storage=ArtifactStorage(str(root / 'data' / 'evolution')),
        )

        snapshot = service._audit_control_master_snapshot()  # type: ignore[attr-defined]
        section = service._audit_control_master_section(snapshot=snapshot, now=utc_now())  # type: ignore[attr-defined]

        assert snapshot['status'] == 'ok'
        assert snapshot['agent'] == 'devin'
        assert snapshot['active_objectives_count'] == 1
        assert snapshot['stale_or_partial_count'] == 1
        assert snapshot['duplicate_risks_count'] == 1
        assert snapshot['human_review_required'] is True
        assert section.section_id == 'audit_control_master'
        assert 'Agent session gate (devin)' in section.summary
        assert 'UNRESOLVED:agent_session_gate_snapshot_missing' not in section.unresolved_fields
    finally:
        if root.exists():
            import shutil
            shutil.rmtree(root)


def test_portable_context_marks_unresolved_if_latest_json_missing() -> None:
    """PortableContext marca UNRESOLVED si falta latest.json."""
    root = _workspace('audit_control_master_missing')
    try:
        service = PortableContextService(
            workspace_root=str(root),
            storage=ArtifactStorage(str(root / 'data' / 'evolution')),
        )

        snapshot = service._audit_control_master_snapshot()  # type: ignore[attr-defined]
        section = service._audit_control_master_section(snapshot=snapshot, now=utc_now())  # type: ignore[attr-defined]

        assert snapshot['status'] == 'no_snapshot'
        assert 'UNRESOLVED:agent_session_gate_snapshot_missing' in snapshot['unresolved_fields']
        assert section.section_id == 'audit_control_master'
        assert 'no disponible' in section.summary.lower()
        assert 'UNRESOLVED:agent_session_gate_snapshot_missing' in section.unresolved_fields
        assert section.confidence == 0.0
    finally:
        if root.exists():
            import shutil
            shutil.rmtree(root)


def test_oses_detects_stale_partial_tasks_from_snapshot() -> None:
    """OSES detecta tareas stale/parcial desde snapshot."""
    root = _workspace('oses_stale_partial_detection')
    try:
        # Crear agent_session_gate/latest.json con stale tasks
        gate_dir = root / 'data' / 'evolution' / 'agent_session_gate'
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_snapshot = {
            'generated_at': utc_now().isoformat(),
            'agent': 'devin',
            'mode': 'pre',
            'stale_or_partial_tasks': [
                {
                    'id': 'task_stale_1',
                    'title': 'Stale task 1',
                    'declared_status': 'PENDING',
                    'verification_status': 'CODE_NOT_STARTED',
                    'inferred_state': 'STALE_OR_PARTIAL',
                    'evidence': ['src/test1.py'],
                    'path': 'data/evolution/platform_pending/task_stale_1.json',
                },
                {
                    'id': 'task_stale_2',
                    'title': 'Stale task 2',
                    'declared_status': 'PENDING',
                    'verification_status': 'CODE_NOT_STARTED',
                    'inferred_state': 'STALE_OR_PARTIAL',
                    'evidence': ['src/test2.py'],
                    'path': 'data/evolution/platform_pending/task_stale_2.json',
                },
            ],
            'duplicate_risks': [],
            'unresolved': [],
        }
        with open(gate_dir / 'latest.json', 'w', encoding='utf-8') as f:
            json.dump(gate_snapshot, f, ensure_ascii=False, indent=2)

        service = OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=ArtifactStorage(str(root / 'data' / 'evolution')),
        )

        findings = service._agent_session_gate_findings()  # type: ignore[attr-defined]

        assert len(findings) > 0
        stale_findings = [f for f in findings if f.category == 'platform_pending_stale_vs_code']
        assert len(stale_findings) > 0
        assert stale_findings[0].severity == IssueSeverity.MEDIUM
        assert '2 tareas stale/partial' in stale_findings[0].title
        assert 'task_stale_1' in stale_findings[0].metadata['stale_task_ids']
        assert 'task_stale_2' in stale_findings[0].metadata['stale_task_ids']
    finally:
        if root.exists():
            import shutil
            shutil.rmtree(root)


def test_oses_detects_duplicate_risks_from_snapshot() -> None:
    """OSES detecta duplicate_risks desde snapshot."""
    root = _workspace('oses_duplicate_risks_detection')
    try:
        # Crear agent_session_gate/latest.json con duplicate risks
        gate_dir = root / 'data' / 'evolution' / 'agent_session_gate'
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_snapshot = {
            'generated_at': utc_now().isoformat(),
            'agent': 'devin',
            'mode': 'pre',
            'stale_or_partial_tasks': [],
            'duplicate_risks': [
                {
                    'kind': 'DUPLICATED',
                    'symbol': 'duplicate_method',
                    'path': 'src/duplicate.py',
                    'lines': [15, 30],
                    'unresolved': 'UNRESOLVED:duplicate_definition:duplicate_method',
                },
            ],
            'unresolved': [],
        }
        with open(gate_dir / 'latest.json', 'w', encoding='utf-8') as f:
            json.dump(gate_snapshot, f, ensure_ascii=False, indent=2)

        service = OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=ArtifactStorage(str(root / 'data' / 'evolution')),
        )

        findings = service._agent_session_gate_findings()  # type: ignore[attr-defined]

        assert len(findings) > 0
        duplicate_findings = [f for f in findings if f.category == 'duplicate_self_examination_method']
        assert len(duplicate_findings) > 0
        assert duplicate_findings[0].severity == IssueSeverity.MEDIUM
        assert 'duplicate_method' in duplicate_findings[0].title
        assert duplicate_findings[0].metadata['symbol'] == 'duplicate_method'
        assert duplicate_findings[0].metadata['lines'] == [15, 30]
    finally:
        if root.exists():
            import shutil
            shutil.rmtree(root)


def test_oses_does_not_fail_if_snapshot_corrupt() -> None:
    """OSES no falla si el snapshot está corrupto."""
    root = _workspace('oses_corrupt_snapshot')
    try:
        # Crear agent_session_gate/latest.json corrupto
        gate_dir = root / 'data' / 'evolution' / 'agent_session_gate'
        gate_dir.mkdir(parents=True, exist_ok=True)
        with open(gate_dir / 'latest.json', 'w', encoding='utf-8') as f:
            f.write('corrupt json {{{')

        service = OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=ArtifactStorage(str(root / 'data' / 'evolution')),
        )

        findings = service._agent_session_gate_findings()  # type: ignore[attr-defined]

        # No debe fallar, debe retornar findings con error
        assert isinstance(findings, list)
        error_findings = [f for f in findings if f.category == 'agent_gate_snapshot_read_error']
        assert len(error_findings) > 0
        assert error_findings[0].severity == IssueSeverity.LOW
        assert 'error al leer' in error_findings[0].title.lower()
        assert 'agent_session_gate_read_error' in error_findings[0].unresolved_fields
    finally:
        if root.exists():
            import shutil
            shutil.rmtree(root)


def test_oses_detects_agent_gate_snapshot_missing() -> None:
    """OSES detecta cuando falta el snapshot de agent session gate."""
    root = _workspace('oses_snapshot_missing')
    try:
        # No crear agent_session_gate/latest.json
        service = OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=ArtifactStorage(str(root / 'data' / 'evolution')),
        )

        findings = service._agent_session_gate_findings()  # type: ignore[attr-defined]

        assert len(findings) > 0
        missing_findings = [f for f in findings if f.category == 'agent_gate_snapshot_missing']
        assert len(missing_findings) > 0
        assert missing_findings[0].severity == IssueSeverity.LOW
        assert 'no disponible' in missing_findings[0].title.lower()
        assert 'agent_session_gate_snapshot_missing' in missing_findings[0].unresolved_fields
    finally:
        if root.exists():
            import shutil
            shutil.rmtree(root)
