"""Tests for the global-human-gates-and-runtime-audit-persistence slice.

Covers:
1. Global dialog host — signals reach VMs from any page context
2. CodeAuditTrail / PortableContext — runtime findings appear in context
3. No dialog duplication — single emission produces one host
4. cpu_frequency → sensors_not_available (not UNRESOLVED)
5. Regression on touched files
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    IssueSeverity,
    SelfExaminationFinding,
    utc_now,
)
from iabv_v15.services.evolution.code_audit_trail import (
    AuditEnvironment,
    AuditFinding,
    AuditRound,
    AuditSource,
    CodeAuditTrail,
    FindingSeverity,
    FindingStatus,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = _workspace(name)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap


def _cleanup(bootstrap_or_path) -> None:
    if isinstance(bootstrap_or_path, AppBootstrap):
        stop = getattr(bootstrap_or_path, 'stop', None)
        if callable(stop):
            stop()
        workspace = getattr(bootstrap_or_path, '_test_workspace', None)
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)
    else:
        shutil.rmtree(bootstrap_or_path, ignore_errors=True)


def _capture_signal(viewmodel, signal_name: str) -> dict:
    captured: dict = {'payload': None, 'count': 0}

    def _slot(payload):
        captured['payload'] = payload
        captured['count'] += 1

    getattr(viewmodel, signal_name).connect(_slot)
    return captured


# ---------------------------------------------------------------------------
# 1. Global dialog host — signals reach VMs regardless of active page
# ---------------------------------------------------------------------------

def test_global_dialog_host_credential_signal_reaches_both_vms() -> None:
    """After _wire_task_a_signals, credentialPromptRequested fires on both VMs.

    This proves the global host in Main.qml (connected to controlCenterViewModel)
    will receive the signal even when the user is on Dashboard.
    """
    bootstrap = _make_bootstrap('global_dialog_credential')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'credentialPromptRequested')
        ec_cap = _capture_signal(ec, 'credentialPromptRequested')

        bootstrap.credential_broker.request(
            domain='github.com',
            reason='Token expirado',
            username_hint='user@test.com',
        )

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
        assert cc_cap['payload']['domain'] == 'github.com'
    finally:
        _cleanup(bootstrap)


def test_global_dialog_host_clarification_signal_reaches_both_vms() -> None:
    """clarificationRequested reaches both VMs for global visibility."""
    bootstrap = _make_bootstrap('global_dialog_clarification')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'clarificationRequested')
        ec_cap = _capture_signal(ec, 'clarificationRequested')

        handler = bootstrap.clarification_request_service._handler
        assert handler is not None

        payload = {
            'id': 'clr-1',
            'question': 'Cual opcion?',
            'options': ['A', 'B'],
            'context': 'test',
        }
        handler(payload)

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
    finally:
        _cleanup(bootstrap)


def test_global_dialog_host_missing_dependency_signal_reaches_both_vms() -> None:
    """missingDependencyRequested reaches both VMs for global visibility."""
    bootstrap = _make_bootstrap('global_dialog_dependency')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'missingDependencyRequested')
        ec_cap = _capture_signal(ec, 'missingDependencyRequested')

        handler = bootstrap.environment_bootstrap_service._prompt_handler
        assert handler is not None

        payload = {
            'id': 'dep-1',
            'package_name': 'httpx',
            'manager': 'pip',
            'reason': 'required',
        }
        handler(payload)

        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1
    finally:
        _cleanup(bootstrap)


# ---------------------------------------------------------------------------
# 2. CodeAuditTrail / PortableContext — runtime audit appears in context
# ---------------------------------------------------------------------------

def test_runtime_audit_finding_appears_in_portable_context() -> None:
    """When a runtime finding is persisted to CodeAuditTrail, PortableContext
    should no longer say 'Sin auditorias registradas'.
    """
    root = _workspace('runtime_audit_portable')
    try:
        trail = CodeAuditTrail(data_root=root)
        audit_round = AuditRound(
            auditor_name='oses_runtime',
            source=AuditSource.SELF_EXAMINATION,
            environment=AuditEnvironment.LINUX_VM,
            modules_audited=['runtime_monitor'],
            total_loc_audited=0,
            findings=[
                AuditFinding(
                    category='runtime_incident',
                    title='high_memory_usage',
                    description='Proceso IABV consume 900MB de RAM.',
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.FOUND,
                    pattern_tag='runtime_runtime_performance_high_memory_usage',
                    confidence=0.95,
                ),
            ],
            metadata={'trigger': 'build_review_runtime_persistence'},
        )
        trail.record_round(audit_round)

        summary = trail.summary_for_portable_context()
        coverage = summary.get('coverage', {})
        assert coverage.get('total_rounds', 0) >= 1
        assert len(summary.get('recent_rounds', [])) >= 1
        assert summary['recent_rounds'][0]['auditor'] == 'oses_runtime'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_persists_high_severity_runtime_findings_to_audit_trail() -> None:
    """OSES._persist_runtime_findings_to_audit_trail writes qualifying findings."""
    root = _workspace('oses_runtime_persist')
    try:
        from iabv_v15.infra.persistence.storage import ArtifactStorage

        storage = ArtifactStorage(str(root))
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        svc = OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=storage,
        )
        trail = CodeAuditTrail(data_root=root)
        svc.code_audit_trail = trail

        findings = [
            SelfExaminationFinding(
                category='runtime_performance',
                title='high_memory_usage',
                summary='900MB RSS',
                severity=IssueSeverity.HIGH,
                confidence=0.95,
                recommendation='lazy load',
            ),
            SelfExaminationFinding(
                category='startup_memory_spike',
                title='startup_rss_growth',
                summary='250MB crecimiento',
                severity=IssueSeverity.HIGH,
                confidence=0.90,
                recommendation='defer init',
            ),
            SelfExaminationFinding(
                category='unrelated_category',
                title='something_else',
                summary='not runtime',
                severity=IssueSeverity.HIGH,
                confidence=0.80,
            ),
        ]

        svc._persist_runtime_findings_to_audit_trail(findings)

        rounds = trail.load_rounds()
        assert len(rounds) == 1
        round_findings = rounds[0].get('findings', [])
        assert len(round_findings) == 2
        tags = {f['pattern_tag'] for f in round_findings}
        assert 'runtime_runtime_performance_high_memory_usage' in tags
        assert 'runtime_startup_memory_spike_startup_rss_growth' in tags
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. No dialog duplication — single _emit produces exactly one per VM
# ---------------------------------------------------------------------------

def test_no_dialog_duplication_single_emit_one_per_vm() -> None:
    """_wire_task_a_signals emits to both VMs exactly once per request.

    The global host in Main.qml connects to controlCenterViewModel only,
    so it sees exactly one dialog open per request (not two).
    """
    bootstrap = _make_bootstrap('dialog_no_dup')
    try:
        cc = bootstrap.control_center_viewmodel
        ec = bootstrap.evolution_center_viewmodel
        assert cc is not None and ec is not None

        cc_cap = _capture_signal(cc, 'credentialPromptRequested')
        ec_cap = _capture_signal(ec, 'credentialPromptRequested')

        bootstrap.credential_broker.request(
            domain='devin.ai',
            reason='API key needed',
            username_hint='',
        )

        # Each VM gets exactly one emission
        assert cc_cap['count'] == 1
        assert ec_cap['count'] == 1

        # A second request still produces exactly one more per VM
        bootstrap.credential_broker.request(
            domain='openai.com',
            reason='quota check',
            username_hint='admin',
        )
        assert cc_cap['count'] == 2
        assert ec_cap['count'] == 2
    finally:
        _cleanup(bootstrap)


# ---------------------------------------------------------------------------
# 4. cpu_frequency → sensors_not_available (not UNRESOLVED)
# ---------------------------------------------------------------------------

def test_cpu_frequency_sensors_not_available_on_all_platforms() -> None:
    """cpu_frequency missing data → sensors_not_available, never UNRESOLVED.

    This is the fix for the real broken test
    test_environment_self_awareness_marks_missing_sensors_as_not_available_instead_of_unresolved.
    The test must pass on both Linux AND Windows.
    """
    from iabv_v15.services.evolution.environment_self_awareness_service import (
        EnvironmentSelfAwarenessService,
    )

    root = _workspace('cpu_freq_fix')
    try:
        evolution_dir = root / 'evolution'
        evolution_dir.mkdir(parents=True, exist_ok=True)
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(root),
            evolution_dir=str(evolution_dir),
            auto_start=False,
            bootstrap_scan=False,
        )

        service._memory_snapshot = lambda: {}  # type: ignore[method-assign]
        service._disk_snapshot = lambda: {}  # type: ignore[method-assign]
        service._cpu_snapshot = lambda *, full: {}  # type: ignore[method-assign]
        service._gpu_snapshot = lambda *, full: {}  # type: ignore[method-assign]
        service._battery_snapshot = lambda *, full: {}  # type: ignore[method-assign]
        service._detect_throttling = lambda *, cpu_info, gpu_info: False  # type: ignore[method-assign]

        _, unresolved = service._scan_hardware(full=False)

        assert 'UNRESOLVED:cpu_frequency' not in unresolved

        hardware_snapshot, _ = service._scan_hardware(full=False)
        not_available = hardware_snapshot.get('sensors_not_available') or []
        sensors = {entry['sensor'] for entry in not_available}
        assert 'cpu_frequency' in sensors
        for entry in not_available:
            if entry['sensor'] == 'cpu_frequency':
                assert entry['reason'] == 'sensor_not_exposed_on_this_host'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5. Regression — runtime audit backoff prevents spam
# ---------------------------------------------------------------------------

def test_runtime_audit_backoff_prevents_duplicate_findings() -> None:
    """If a runtime finding was already persisted recently, it should NOT
    be re-persisted (dedupe via pattern_tag + timestamp backoff).
    """
    root = _workspace('runtime_audit_backoff')
    try:
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        storage = ArtifactStorage(str(root))
        svc = OperationalSelfExaminationService(
            workspace_root=str(root),
            storage=storage,
        )
        trail = CodeAuditTrail(data_root=root)
        svc.code_audit_trail = trail

        findings = [
            SelfExaminationFinding(
                category='runtime_performance',
                title='high_memory_usage',
                summary='900MB RSS',
                severity=IssueSeverity.HIGH,
                confidence=0.95,
            ),
        ]

        svc._persist_runtime_findings_to_audit_trail(findings)
        assert len(trail.load_rounds()) == 1

        # Second call with same findings — should be deduped
        svc._persist_runtime_findings_to_audit_trail(findings)
        assert len(trail.load_rounds()) == 1  # still 1, not 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_existing_environment_sensor_test_still_passes() -> None:
    """Regression: the original test must still pass after cpu_frequency fix."""
    from iabv_v15.services.evolution.environment_self_awareness_service import (
        EnvironmentSelfAwarenessService,
    )

    root = _workspace('env_sensor_regression')
    try:
        evolution_dir = root / 'evolution'
        evolution_dir.mkdir(parents=True, exist_ok=True)
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(root),
            evolution_dir=str(evolution_dir),
            auto_start=False,
            bootstrap_scan=False,
        )

        service._memory_snapshot = lambda: {}  # type: ignore[method-assign]
        service._disk_snapshot = lambda: {}  # type: ignore[method-assign]
        service._cpu_snapshot = lambda *, full: {}  # type: ignore[method-assign]
        service._gpu_snapshot = lambda *, full: {}  # type: ignore[method-assign]
        service._battery_snapshot = lambda *, full: {}  # type: ignore[method-assign]
        service._detect_throttling = lambda *, cpu_info, gpu_info: False  # type: ignore[method-assign]

        _, unresolved = service._scan_hardware(full=False)

        assert 'UNRESOLVED:cpu_temperature' not in unresolved
        assert 'UNRESOLVED:battery_status' not in unresolved
        assert 'UNRESOLVED:cpu_frequency' not in unresolved

        hardware_snapshot, _ = service._scan_hardware(full=False)
        not_available = hardware_snapshot.get('sensors_not_available') or []
        sensors = {entry['sensor'] for entry in not_available}
        assert 'cpu_temperature' in sensors
        assert 'battery_status' in sensors
        assert 'cpu_frequency' in sensors
        for entry in not_available:
            assert entry['reason'] == 'sensor_not_exposed_on_this_host'
    finally:
        shutil.rmtree(root, ignore_errors=True)
