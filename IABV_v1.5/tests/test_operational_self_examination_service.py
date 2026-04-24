from datetime import datetime, timedelta, timezone
import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    AutonomousValidationSnapshot,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRecommendation,
    ExperimentRun,
    InferenceRequest,
    InferenceResult,
    IssueSeverity,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    SandboxExperiment,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    TaskRole,
    ToolCapability,
    ToolLiveStatus,
    WindowObservation,
    WorldModelSnapshot,
    utc_now,
)
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_operational_self_examination_service_detects_repeated_blocks_and_adjustments() -> None:
    root = _workspace('operational_self_examination')
    try:
        bootstrap = AppBootstrap(str(root))
        for _ in range(3):
            bootstrap.experiment_lab.record_outcome(
                domain=ExperimentDomain.LANGUAGE,
                objective='Revisar consulta externa bloqueada',
                subject_key='general',
                route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                candidate_label='chatgpt',
                success=False,
                observed_summary='La ruta quedo bloqueada por hilo incorrecto y termino en fallback.',
                precision=0.22,
                robustness=0.25,
                execution_ms=2400,
                metadata={
                    'assistant_kind': 'chatgpt',
                    'config_signature': 'web',
                    'external_state_flags': ['wrong_thread'],
                    'blocked': True,
                    'fallback_used': True,
                },
            )
        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='general',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                score=0.89,
                confidence=0.86,
                rationale='Codex viene cerrando mejor los cambios tecnicos repetibles.',
                metadata={
                    'adaptive_learning_summary': {
                        'reasons': ['Codex mantiene mejor precision en cambios tecnicos repetibles.'],
                    }
                },
            )
        )
        bootstrap.world_model_service.current_model = lambda: WorldModelSnapshot(  # type: ignore[assignment]
            active_windows=[WindowObservation(title='Codex - IABV', app_name='Codex', pid=41, focused=True)],
            focused_window=WindowObservation(title='Codex - IABV', app_name='Codex', pid=41, focused=True),
            tool_live_status=[
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    status='abierto',
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                )
            ],
            detected_blocks=['wrong_thread'],
            confidence=0.82,
        )
        bootstrap.autonomous_validation_cycle.current_snapshot = lambda: AutonomousValidationSnapshot(  # type: ignore[assignment]
            status='active',
            summary='Claude sigue en validacion, pero Codex ya mostro mejor comportamiento para el caso tecnico.',
            promoted_count=1,
            last_experiment_id='sandbox-1',
            current_experiment=SandboxExperiment(
                subject_key='general',
                candidate_assistant_kind='claude',
                candidate_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                verdict='unresolved',
            ),
        )

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = {item.category for item in review.findings}

        assert review.summary
        assert review.validated_improvements
        assert 'repeated_block' in categories
        assert 'inertial_route' in categories
        assert Path(review.package_path).exists()
        assert Path(review.markdown_path).exists()
        assert 'wrong_thread' in review.assistant_brief
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_operational_self_examination_service_feedback_classifies_previous_adjustments() -> None:
    root = _workspace('operational_self_examination_feedback')
    try:
        bootstrap = AppBootstrap(str(root))
        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=2),
            recommended_adjustments=[
                {
                    'title': 'Ruta debil o inercial: codex por code_agent',
                    'recommended_change': 'Exigir validacion adicional antes de reutilizar esta ruta.',
                    'category': 'inertial_route',
                    'metadata': {'assistant_kind': 'codex', 'route': 'code_agent', 'config_signature': 'patch'},
                    'feedback_key': 'inertial_route:codex:code_agent:patch',
                    'source_refs': ['ExperimentLab', 'AdaptiveWeightLayer'],
                },
                {
                    'title': 'Ruta debil o inercial: claude por language_understanding',
                    'recommended_change': 'Debilitar esta preferencia hasta confirmar mejora.',
                    'category': 'inertial_route',
                    'metadata': {'assistant_kind': 'claude', 'route': 'language_understanding', 'config_signature': 'review'},
                    'feedback_key': 'inertial_route:claude:language_understanding:review',
                    'source_refs': ['ExperimentLab', 'AdaptiveWeightLayer'],
                },
                {
                    'title': 'Ruta debil o inercial: chatgpt por language_understanding',
                    'recommended_change': 'Exigir validacion adicional antes de reutilizar esta ruta.',
                    'category': 'inertial_route',
                    'metadata': {'assistant_kind': 'chatgpt', 'route': 'language_understanding', 'config_signature': 'web'},
                    'feedback_key': 'inertial_route:chatgpt:language_understanding:web',
                    'source_refs': ['ExperimentLab', 'AdaptiveWeightLayer'],
                },
                {
                    'title': 'Pack atascado: pack_research',
                    'recommended_change': 'Revisar defaults, readiness y preguntas obligatorias del pack.',
                    'category': 'repeated_stall',
                    'metadata': {'pack_id': 'pack_research'},
                    'feedback_key': 'repeated_stall:pack_research',
                    'source_refs': ['AdaptiveSessionRepository'],
                },
            ],
        )
        bootstrap.operational_self_examination_service.storage.save_json_atomic(
            'self_examination/latest.json',
            previous_review.model_dump(mode='json'),
        )

        def save_run(*, assistant: str, route: EvaluationRoute, config_signature: str, success: bool, score: float, blocked: bool = False, fallback: bool = False) -> ExperimentRun:
            run = ExperimentRun(
                domain=ExperimentDomain.CODE if route == EvaluationRoute.CODE_AGENT else ExperimentDomain.LANGUAGE,
                suite_name='self_exam_feedback',
                objective='Retroalimentacion de ajustes',
                subject_key='general',
                route=route,
                assistant_kind=assistant,
                config_signature=config_signature,
                candidate_label=assistant,
                success=success,
                observed_summary='Corrida sintetica para evaluar retroalimentacion de autoexaminacion.',
                metrics=ExperimentMetric(
                    total_score=score,
                    execution_ms=950 if success else 2400,
                ),
                metadata={
                    'assistant_kind': assistant,
                    'config_signature': config_signature,
                    'blocked': blocked,
                    'fallback_used': fallback,
                    'external_state_flags': ['wrong_thread'] if blocked else [],
                },
            )
            return bootstrap.experiment_lab_repository.save_run(run)

        codex_runs = [
            save_run(assistant='codex', route=EvaluationRoute.CODE_AGENT, config_signature='patch', success=True, score=0.91),
            save_run(assistant='codex', route=EvaluationRoute.CODE_AGENT, config_signature='patch', success=True, score=0.9),
            save_run(assistant='codex', route=EvaluationRoute.CODE_AGENT, config_signature='patch', success=True, score=0.93),
        ]
        save_run(assistant='claude', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='review', success=True, score=0.69)
        save_run(assistant='claude', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='review', success=True, score=0.7)
        save_run(assistant='claude', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='review', success=True, score=0.71)
        save_run(assistant='chatgpt', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='web', success=False, score=0.22, blocked=True, fallback=True)
        save_run(assistant='chatgpt', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='web', success=False, score=0.2, blocked=True, fallback=True)
        save_run(assistant='chatgpt', route=EvaluationRoute.LANGUAGE_UNDERSTANDING, config_signature='web', success=False, score=0.24, blocked=True, fallback=True)

        bootstrap.experiment_lab_repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='general',
                recommended_route=EvaluationRoute.CODE_AGENT,
                recommended_assistant_kind='codex',
                recommended_config_signature='patch',
                score=0.91,
                confidence=0.88,
                rationale='Codex volvio a ser consistente despues del ajuste previo.',
                supporting_run_ids=[run.run_id for run in codex_runs],
            )
        )
        bootstrap.autonomous_validation_cycle.current_snapshot = lambda: AutonomousValidationSnapshot(status='idle')  # type: ignore[assignment]

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        feedback = list((review.metadata or {}).get('recommendation_feedback') or [])
        statuses = {item['feedback_key']: item['status'] for item in feedback}
        summary = dict((review.metadata or {}).get('feedback_summary') or {})

        assert statuses['inertial_route:codex:code_agent:patch'] == 'validated_improvement'
        assert statuses['inertial_route:claude:language_understanding:review'] == 'valid_adjustment'
        assert statuses['inertial_route:chatgpt:language_understanding:web'] == 'false_improvement'
        assert statuses['repeated_stall:pack_research'] == 'no_evidence'
        assert summary['validated_improvement'] == 1
        assert summary['valid_adjustment'] == 1
        assert summary['false_improvement'] == 1
        assert summary['no_evidence'] == 1
        assert any(item.get('repeat_policy') == 'require_new_evidence' for item in review.recommended_adjustments if item.get('last_feedback_status') == 'false_improvement')
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _build_run(
    *,
    task_role: TaskRole,
    status: RunStatus,
    created_at: datetime,
    run_id: str | None = None,
    site_hint: str = '',
) -> RunRecord:
    request = InferenceRequest(
        user_goal='goal',
        task_role=task_role,
        site_hint=site_hint,
    )
    result = InferenceResult(
        request_id=request.request_id,
        provider_name='Ollama',
        reasoning_mode=ReasoningMode.LOCAL,
        summary='ok' if status == RunStatus.SUCCESS else 'fallo',
        inferred_task='goal',
        confidence=0.5,
    )
    route = RoleRoute(
        task_role=task_role,
        role_title='stub',
        provider_name='Ollama',
        model_profile_id='general-qwen',
        model_name='qwen3:8b',
        tool_chain=[ToolCapability.ANALYTICS],
        reason='stub',
    )
    kwargs: dict[str, object] = {
        'request': request,
        'result': result,
        'route': route,
        'status': status,
        'created_at_utc': created_at,
    }
    if run_id is not None:
        kwargs['run_id'] = run_id
    return RunRecord(**kwargs)


def test_recurring_failure_ignores_partial_runs_so_no_false_fallo_repetido_training() -> None:
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    now = datetime.now(timezone.utc)
    runs: list[RunRecord] = []
    # Fixture de 40 dossiers mixtos: 32 SUCCESS + 8 PARTIAL, todos en
    # TaskRole.TRAINING. Ninguno FAILED. El heuristico anterior agrupaba
    # FAILED+PARTIAL bajo "Fallo repetido" y generaba el falso positivo
    # "Fallo repetido en general:training" con solo PARTIAL.
    for _ in range(32):
        runs.append(
            _build_run(
                task_role=TaskRole.TRAINING,
                status=RunStatus.SUCCESS,
                created_at=now,
            )
        )
    for _ in range(8):
        runs.append(
            _build_run(
                task_role=TaskRole.TRAINING,
                status=RunStatus.PARTIAL,
                created_at=now,
            )
        )

    findings = OperationalSelfExaminationService._recurring_failure_findings(
        service, recent_runs=runs
    )

    assert findings == []


def test_recurring_failure_flags_two_distinct_failed_runs_in_window() -> None:
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    now = datetime.now(timezone.utc)
    runs = [
        _build_run(
            task_role=TaskRole.TRAINING,
            status=RunStatus.FAILED,
            created_at=now,
            run_id='run-failed-1',
        ),
        _build_run(
            task_role=TaskRole.TRAINING,
            status=RunStatus.FAILED,
            created_at=now,
            run_id='run-failed-2',
        ),
    ]

    findings = OperationalSelfExaminationService._recurring_failure_findings(
        service, recent_runs=runs
    )

    assert len(findings) == 1
    finding = findings[0]
    assert 'general:training' in finding.title
    assert finding.category == 'recurring_failure'
    assert finding.metadata['failed_count'] == 2
    assert finding.metadata['window_hours'] == 48


def test_recurring_failure_ignores_stale_runs_outside_window() -> None:
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    now = datetime.now(timezone.utc)
    stale = now - timedelta(days=7)
    runs = [
        _build_run(
            task_role=TaskRole.TRAINING,
            status=RunStatus.FAILED,
            created_at=stale,
            run_id='run-old-1',
        ),
        _build_run(
            task_role=TaskRole.TRAINING,
            status=RunStatus.FAILED,
            created_at=stale,
            run_id='run-old-2',
        ),
    ]

    findings = OperationalSelfExaminationService._recurring_failure_findings(
        service, recent_runs=runs
    )

    assert findings == []


def test_recurring_failure_dedupes_repeated_run_ids_defensively() -> None:
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    now = datetime.now(timezone.utc)
    repeated = _build_run(
        task_role=TaskRole.TRAINING,
        status=RunStatus.FAILED,
        created_at=now,
        run_id='single-fail',
    )
    runs = [repeated, repeated, repeated]

    findings = OperationalSelfExaminationService._recurring_failure_findings(
        service, recent_runs=runs
    )

    assert findings == []


def test_dedupe_adjustments_collapses_equivalent_pendiente_codex_entries() -> None:
    service = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    items = [
        {
            'title': 'Pendiente Codex: ',
            'recommended_change': 'Ya existe un patron equivalente Decision: continue_local. Confianza 0.96.',
            'category': 'backlog',
            'severity': 'medium',
            'confidence': 0.45,
            'evidence_refs': ['evidence-a'],
            'source_refs': ['EvolutionReviewService'],
            'metadata': {},
            'feedback_key': 'backlog:pendiente_codex',
        },
        {
            'title': 'Pendiente Codex: ',
            'recommended_change': 'Sin hallazgos. Decision: continue_local. Confianza 0.66.',
            'category': 'backlog',
            'severity': 'medium',
            'confidence': 0.66,
            'evidence_refs': ['evidence-b'],
            'source_refs': ['EvolutionReviewService'],
            'metadata': {},
            'feedback_key': 'backlog:pendiente_codex',
        },
        {
            'title': 'Ruta debil: codex por code_agent',
            'recommended_change': 'Exigir validacion adicional.',
            'category': 'inertial_route',
            'severity': 'medium',
            'confidence': 0.8,
            'evidence_refs': [],
            'source_refs': ['ExperimentLab'],
            'metadata': {},
            'feedback_key': 'inertial_route:codex',
        },
    ]

    deduped = OperationalSelfExaminationService._dedupe_adjustments(service, items)
    assert len(deduped) == 2
    pendiente_codex = next(item for item in deduped if item['title'] == 'Pendiente Codex: ')
    assert pendiente_codex['metadata']['duplicate_count'] == 2
    assert 'duplicate_variants' in pendiente_codex['metadata']
    assert len(pendiente_codex['metadata']['duplicate_variants']) == 2
    assert set(pendiente_codex['evidence_refs']) == {'evidence-a', 'evidence-b'}
    assert pendiente_codex['confidence'] == 0.66

    inertial = next(item for item in deduped if item['category'] == 'inertial_route')
    assert inertial['metadata']['duplicate_count'] == 1


def test_environment_self_awareness_marks_missing_sensors_as_not_available_instead_of_unresolved() -> None:
    from iabv_v15.services.evolution.environment_self_awareness_service import (
        EnvironmentSelfAwarenessService,
    )

    root = _workspace('environment_sensors_not_available')
    try:
        evolution_dir = root / 'evolution'
        evolution_dir.mkdir(parents=True, exist_ok=True)
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(root),
            evolution_dir=str(evolution_dir),
            auto_start=False,
            bootstrap_scan=False,
        )

        hardware = {
            'hostname': 'test-host',
            'cpu_temperature_c': None,
            'gpu_name': None,
            'gpu_temperature_c': None,
            'battery_percent': None,
            'battery_status': None,
            'current_clock_mhz': None,
            'max_clock_mhz': None,
        }
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
        for entry in not_available:
            assert entry['reason'] == 'sensor_not_exposed_on_this_host'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pending_auto_probes_emits_request_for_high_confidence_recurring_failure() -> None:
    """Regression H4: self-exam must emit a concrete probe for HIGH+0.92 findings.

    The symptom observed live: `Fallo repetido en general:training`, severity
    HIGH, confidence 0.92, was surfaced as a finding but the recommendation
    `Construir prueba reproducible del fallo` stayed with
    ``last_feedback_status == 'no_evidence'`` because no component picked up
    the testigo. Closing capa P4 means the self-exam itself has to leave a
    structured probe request (scope, evidence_refs, suggested_tests) ready
    for the orchestrator to dispatch.
    """
    root = _workspace('pending_auto_probes_recurring')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = bootstrap.operational_self_examination_service
        findings = [
            SelfExaminationFinding(
                finding_id='finding-high-training',
                category='recurring_failure',
                title='Fallo repetido en general:training',
                summary='La clase de tarea general:training acumula 7 corridas fallidas.',
                severity=IssueSeverity.HIGH,
                confidence=0.92,
                recommendation='Revisar la ruta antes de repetir general:training.',
                evidence_refs=['run-a', 'run-b', 'run-c', 'run-d'],
                source_refs=['RunRepository'],
                metadata={'scope': 'general:training', 'failed_count': 7, 'window_hours': 48},
            ),
            SelfExaminationFinding(
                finding_id='finding-low',
                category='recurring_failure',
                title='Fallo repetido low-conf',
                summary='Evidence todavia debil.',
                severity=IssueSeverity.HIGH,
                confidence=0.70,
                recommendation='Observar.',
                evidence_refs=['run-x'],
                source_refs=['RunRepository'],
                metadata={'scope': 'other:scope'},
            ),
            SelfExaminationFinding(
                finding_id='finding-medium',
                category='recurring_failure',
                title='Fallo repetido medium-severity',
                summary='Hay algo pero no es critico.',
                severity=IssueSeverity.MEDIUM,
                confidence=0.95,
                recommendation='Observar.',
                evidence_refs=['run-y'],
                source_refs=['RunRepository'],
                metadata={'scope': 'medium:scope'},
            ),
        ]
        probes = service._pending_auto_probes(findings=findings)
        assert len(probes) == 1, (
            'Only the HIGH + confidence >= 0.85 finding should produce an auto-probe; '
            f'got: {probes}'
        )
        probe = probes[0]
        assert probe['finding_id'] == 'finding-high-training'
        assert probe['category'] == 'recurring_failure'
        assert probe['scope'] == 'general:training'
        assert probe['severity'] == IssueSeverity.HIGH.value
        assert probe['status'] == 'requested'
        assert probe['evidence_refs'][:3] == ['run-a', 'run-b', 'run-c']
        # suggested_tests carries: pytest command + reproduce_run_ids + scope
        tests = probe['suggested_tests']
        assert any(t.startswith('pytest -q') for t in tests)
        assert any(t.startswith('reproduce_run_ids=') for t in tests)
        assert any(t == 'scope=general:training' for t in tests)
        assert '0.92' in probe['trigger_reason']
        assert '0.85' in probe['trigger_reason']
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pending_auto_probes_returns_empty_when_no_high_confidence_finding() -> None:
    """H4 guard: never emit spurious probes when findings are all low-conf."""
    root = _workspace('pending_auto_probes_empty')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = bootstrap.operational_self_examination_service
        findings = [
            SelfExaminationFinding(
                category='recurring_failure',
                title='Low-conf',
                summary='No hay evidencia suficiente.',
                severity=IssueSeverity.HIGH,
                confidence=0.50,
                recommendation='Observar.',
                evidence_refs=['run-1'],
                source_refs=['RunRepository'],
                metadata={'scope': 'weak:scope'},
            ),
        ]
        assert service._pending_auto_probes(findings=findings) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_build_review_persists_pending_auto_probes_and_surfaces_in_summary() -> None:
    """End-to-end H4: build_review -> metadata.pending_auto_probes -> review_summary.

    Drives the service through build_review() with a synthetic run history so
    a HIGH + 0.92 finding is produced organically (not injected) and verifies
    the probe reaches both ``SelfExaminationSnapshot.metadata`` and
    ``review_summary()`` output.
    """
    root = _workspace('pending_auto_probes_e2e')
    try:
        bootstrap = AppBootstrap(str(root))
        # Inject 7 FAILED TRAINING runs inside the 48h window. ``_task_scope``
        # returns ``general:training`` for these, so the service's organic
        # ``_recurring_failure_findings`` yields a HIGH-severity finding with
        # confidence clamped to 0.92 (``min(0.92, 0.45 + 7*0.12)``).
        now = datetime.now(timezone.utc)
        for index in range(7):
            run = _build_run(
                task_role=TaskRole.TRAINING,
                status=RunStatus.FAILED,
                created_at=now - timedelta(minutes=30 + index),
            )
            bootstrap.run_repository.record(run)
        service: OperationalSelfExaminationService = bootstrap.operational_self_examination_service
        snapshot = service.build_review()
        probes = list((snapshot.metadata or {}).get('pending_auto_probes') or [])
        assert probes, 'build_review must surface pending_auto_probes when HIGH+0.92 finding exists'
        assert probes[0]['category'] == 'recurring_failure'
        assert probes[0]['status'] == 'requested'
        # review_summary must also expose the list so MCP/UI consumers see it.
        summary = service.review_summary(snapshot)
        assert summary['pending_auto_probes']
        assert summary['pending_auto_probes'][0]['category'] == 'recurring_failure'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Capa 2.2 — _token_rotation_findings
# ---------------------------------------------------------------------------


class _StubLedger:
    """Double del TokenRotationLedger con ``predictions()`` controlable.

    Emula solo la porcion de la API que consume OSES. Mantener esto como
    stub explicito (en vez de instanciar el ledger real) evita depender de
    la persistencia y deja la logica de findings como unico SUT.
    """

    def __init__(self, predictions: list[dict]) -> None:
        self._predictions = predictions

    def predictions(self) -> list[dict]:
        return list(self._predictions)


def test_token_rotation_findings_emits_high_when_token_expired_live() -> None:
    root = _workspace('token_rotation_expired')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = (
            bootstrap.operational_self_examination_service
        )
        service.token_rotation_ledger = _StubLedger([
            {
                'token_name': 'github_api',
                'last_probe_ok_at': '2026-03-20T12:00:00+00:00',
                'last_probe_failed_at': '2026-04-21T00:00:00+00:00',
                'last_rotation_at': None,
                'rotations_observed': 0,
                'avg_interval_days': None,
                'projected_expiry_at': None,
                'days_until_projected_expiry': None,
                'stale': False,
                'expired_live': True,
                'proactive_due': False,
            },
        ])
        findings = service._token_rotation_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.category == 'token_rotation'
        assert f.severity == IssueSeverity.HIGH
        assert 'expirado' in f.title.lower()
        assert 'rotate_tokens.ps1' in (f.recommendation or '')
        assert f.metadata.get('token_name') == 'github_api'
        assert f.metadata.get('expired_live') is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_token_rotation_findings_emits_high_on_proactive_due() -> None:
    root = _workspace('token_rotation_proactive')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = (
            bootstrap.operational_self_examination_service
        )
        service.token_rotation_ledger = _StubLedger([
            {
                'token_name': 'devin_api',
                'last_probe_ok_at': '2026-04-20T12:00:00+00:00',
                'last_probe_failed_at': None,
                'last_rotation_at': '2026-03-22T12:00:00+00:00',
                'rotations_observed': 2,
                'avg_interval_days': 30.0,
                'projected_expiry_at': '2026-04-21T12:00:00+00:00',
                'days_until_projected_expiry': 1.0,
                'stale': False,
                'expired_live': False,
                'proactive_due': True,
            },
        ])
        findings = service._token_rotation_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.severity == IssueSeverity.HIGH
        assert 'proactiva' in f.title.lower()
        assert f.metadata.get('proactive_due') is True
        # Evidencia visible para el orquestador.
        assert '2026-04-20T12:00:00+00:00' in f.evidence_refs
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_token_rotation_findings_emits_medium_on_stale_only() -> None:
    root = _workspace('token_rotation_stale')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = (
            bootstrap.operational_self_examination_service
        )
        service.token_rotation_ledger = _StubLedger([
            {
                'token_name': 'github_api',
                'last_probe_ok_at': '2026-04-10T12:00:00+00:00',
                'last_probe_failed_at': None,
                'last_rotation_at': None,
                'rotations_observed': 0,
                'avg_interval_days': None,
                'projected_expiry_at': None,
                'days_until_projected_expiry': None,
                'stale': True,
                'expired_live': False,
                'proactive_due': False,
            },
        ])
        findings = service._token_rotation_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.severity == IssueSeverity.MEDIUM
        assert 'stale' in f.title.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_token_rotation_findings_no_ops_when_no_signal() -> None:
    root = _workspace('token_rotation_no_signal')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = (
            bootstrap.operational_self_examination_service
        )
        service.token_rotation_ledger = _StubLedger([
            {
                'token_name': 'github_api',
                'stale': False,
                'expired_live': False,
                'proactive_due': False,
            },
        ])
        assert service._token_rotation_findings() == []
        # Ledger ausente tampoco rompe.
        service.token_rotation_ledger = None
        assert service._token_rotation_findings() == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_token_rotation_feedback_key_is_stable_across_days_projection() -> None:
    """``_adjustment_feedback_key`` debe ignorar ``days_txt`` del title.

    Si el key dependiera del title completo, cada review devolveria un key
    distinto (``...(3.0d)`` vs ``...(2.0d)``), y ``_recommendation_feedback``
    nunca encontraria al finding previo -> siempre ``no_evidence``.
    """
    root = _workspace('token_rotation_feedback_key')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = (
            bootstrap.operational_self_examination_service
        )
        key_yesterday = service._adjustment_feedback_key(
            category='token_rotation',
            title='Rotacion proactiva de github_api (3.0d)',
            metadata={'token_name': 'github_api'},
        )
        key_today = service._adjustment_feedback_key(
            category='token_rotation',
            title='Rotacion proactiva de github_api (2.0d)',
            metadata={'token_name': 'github_api'},
        )
        key_expired = service._adjustment_feedback_key(
            category='token_rotation',
            title='Token github_api expirado: rotar ya',
            metadata={'token_name': 'github_api'},
        )
        assert key_yesterday == key_today == key_expired
        assert 'github_api' in key_today
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_build_review_promotes_expired_token_finding_to_auto_probe() -> None:
    """End-to-end capa 2.2: finding HIGH -> pending_auto_probes con rotate_tokens.ps1."""
    root = _workspace('token_rotation_auto_probe')
    try:
        bootstrap = AppBootstrap(str(root))
        service: OperationalSelfExaminationService = (
            bootstrap.operational_self_examination_service
        )
        service.token_rotation_ledger = _StubLedger([
            {
                'token_name': 'github_api',
                'last_probe_ok_at': '2026-03-20T12:00:00+00:00',
                'last_probe_failed_at': '2026-04-21T00:00:00+00:00',
                'last_rotation_at': None,
                'rotations_observed': 0,
                'avg_interval_days': None,
                'projected_expiry_at': None,
                'days_until_projected_expiry': None,
                'stale': False,
                'expired_live': True,
                'proactive_due': False,
            },
        ])
        snapshot = service.build_review()
        probes = list((snapshot.metadata or {}).get('pending_auto_probes') or [])
        token_probes = [p for p in probes if p.get('category') == 'token_rotation']
        assert token_probes, 'HIGH token_rotation finding must surface as auto-probe'
        probe = token_probes[0]
        tests = probe.get('suggested_tests') or []
        assert any('rotate_tokens.ps1' in t for t in tests)
        assert any('token_name=github_api' in t for t in tests)
        # scope debe caer en token_name (no dejarlo vacio): asi el
        # AdaptiveTaskOrchestrator / UI pueden agrupar por token.
        assert probe.get('scope') == 'github_api'
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ------------------------------------------------------------------
# Metacognitive error detection tests
# ------------------------------------------------------------------


def _make_experiment_run(
    *,
    assistant_kind: str = 'codex',
    success: bool = True,
    subject_key: str = 'general',
    route: EvaluationRoute = EvaluationRoute.CODE_AGENT,
    created_offset_hours: float = 0.0,
    score: float = 0.7,
) -> ExperimentRun:
    return ExperimentRun(
        domain=ExperimentDomain.CODE,
        suite_name='test',
        objective='test',
        subject_key=subject_key,
        route=route,
        assistant_kind=assistant_kind,
        success=success,
        metrics=ExperimentMetric(total_score=score, precision=score),
        created_at_utc=utc_now() - timedelta(hours=created_offset_hours),
    )


def test_metacognitive_accuracy_detects_false_positives() -> None:
    """Previous HIGH finding not confirmed by subsequent good runs = false positive."""
    root = _workspace('metacognitive_fp')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=3),
            findings=[
                SelfExaminationFinding(
                    title='Fijación cognitiva en codex',
                    category='cognitive_fixation',
                    severity=IssueSeverity.HIGH,
                    confidence=0.78,
                    metadata={'dominant_kind': 'codex'},
                ),
            ],
        )
        post_runs = [
            _make_experiment_run(assistant_kind='codex', success=True, created_offset_hours=1.0)
            for _ in range(5)
        ]
        findings = service._metacognitive_accuracy_findings(
            previous_review=previous_review,
            current_findings=[],
            experiment_runs=post_runs,
        )
        assert len(findings) >= 1
        fp_finding = next((f for f in findings if f.category == 'metacognitive_false_positive'), None)
        assert fp_finding is not None
        assert 'codex' in fp_finding.summary.lower()
        assert fp_finding.severity == IssueSeverity.MEDIUM
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_metacognitive_accuracy_detects_false_negatives() -> None:
    """Failures without any prior warning = false negative."""
    root = _workspace('metacognitive_fn')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=3),
            findings=[
                SelfExaminationFinding(
                    title='Algo sobre codex',
                    category='inertial_route',
                    severity=IssueSeverity.MEDIUM,
                    metadata={'dominant_kind': 'codex'},
                ),
            ],
        )
        post_runs = [
            _make_experiment_run(assistant_kind='claude', success=False, created_offset_hours=1.0)
            for _ in range(4)
        ]
        findings = service._metacognitive_accuracy_findings(
            previous_review=previous_review,
            current_findings=[],
            experiment_runs=post_runs,
        )
        fn_finding = next((f for f in findings if f.category == 'metacognitive_false_negative'), None)
        assert fn_finding is not None
        assert 'claude' in fn_finding.summary.lower()
        assert fn_finding.severity == IssueSeverity.HIGH
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_metacognitive_accuracy_no_findings_without_previous_review() -> None:
    """Without a previous review, no metacognitive errors can be detected."""
    root = _workspace('metacognitive_no_prev')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service
        runs = [_make_experiment_run() for _ in range(5)]
        findings = service._metacognitive_accuracy_findings(
            previous_review=None,
            current_findings=[],
            experiment_runs=runs,
        )
        assert findings == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_introspection_blind_spot_detects_unexamined_kinds() -> None:
    """IAs with runs but no findings = blind spots."""
    root = _workspace('introspection_blind_spot')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        runs = [
            _make_experiment_run(assistant_kind='codex', success=True, created_offset_hours=float(i))
            for i in range(3)
        ] + [
            _make_experiment_run(assistant_kind='gemini', success=False, created_offset_hours=float(i))
            for i in range(4)
        ]
        existing_findings = [
            SelfExaminationFinding(
                title='Fijación en codex',
                category='cognitive_fixation',
                metadata={'dominant_kind': 'codex'},
            ),
        ]
        findings = service._introspection_blind_spot_findings(
            experiment_runs=runs,
            findings_so_far=existing_findings,
        )
        assert len(findings) == 1
        assert findings[0].category == 'introspection_blind_spot'
        assert 'gemini' in findings[0].summary.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_introspection_blind_spot_no_findings_when_all_covered() -> None:
    """No blind spots when all kinds have findings."""
    root = _workspace('introspection_no_blind')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        runs = [
            _make_experiment_run(assistant_kind='codex', created_offset_hours=float(i))
            for i in range(4)
        ]
        existing_findings = [
            SelfExaminationFinding(
                title='Atractor en codex',
                category='neural_attractor',
                metadata={'attractor_key': 'codex:code_agent'},
            ),
        ]
        findings = service._introspection_blind_spot_findings(
            experiment_runs=runs,
            findings_so_far=existing_findings,
        )
        assert findings == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_metacognitive_calibration_detects_overconfidence() -> None:
    """High confidence + high severity but good post outcomes = overconfidence."""
    root = _workspace('metacognitive_overconfidence')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=3),
            findings=[
                SelfExaminationFinding(
                    title='Problema grave detectado',
                    category='recurring_failure',
                    severity=IssueSeverity.HIGH,
                    confidence=0.82,
                ),
                SelfExaminationFinding(
                    title='Otro problema grave',
                    category='repeated_block',
                    severity=IssueSeverity.HIGH,
                    confidence=0.75,
                ),
            ],
        )
        post_runs = [
            _make_experiment_run(success=True, created_offset_hours=1.0)
            for _ in range(6)
        ]
        findings = service._metacognitive_calibration_findings(
            previous_review=previous_review,
            experiment_runs=post_runs,
        )
        overconf = next((f for f in findings if f.category == 'metacognitive_overconfidence'), None)
        assert overconf is not None
        assert overconf.severity == IssueSeverity.MEDIUM
        assert float(overconf.metadata.get('post_success_rate', 0)) >= 0.75
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_metacognitive_calibration_detects_underconfidence() -> None:
    """Low confidence + low severity but bad post outcomes = underconfidence."""
    root = _workspace('metacognitive_underconfidence')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=3),
            findings=[
                SelfExaminationFinding(
                    title='Observación menor',
                    category='neural_attractor',
                    severity=IssueSeverity.LOW,
                    confidence=0.35,
                ),
                SelfExaminationFinding(
                    title='Otro tema menor',
                    category='loop_closure',
                    severity=IssueSeverity.LOW,
                    confidence=0.40,
                ),
            ],
        )
        post_runs = [
            _make_experiment_run(success=False, created_offset_hours=1.0)
            for _ in range(5)
        ]
        findings = service._metacognitive_calibration_findings(
            previous_review=previous_review,
            experiment_runs=post_runs,
        )
        underconf = next((f for f in findings if f.category == 'metacognitive_underconfidence'), None)
        assert underconf is not None
        assert underconf.severity == IssueSeverity.HIGH
        assert float(underconf.metadata.get('post_success_rate', 0)) < 0.5
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_metacognitive_ledger_persistence_and_bias_detection() -> None:
    """Metacognitive ledger persists errors and detects persistent bias."""
    root = _workspace('metacognitive_ledger')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        for i in range(3):
            service._persist_metacognitive_ledger(
                false_positives=[f'fp_{i}_a', f'fp_{i}_b'],
                false_negatives=[],
                review_id=f'review-{i}',
            )

        ledger = service._load_metacognitive_ledger()
        assert len(ledger) == 3
        total_fp = sum(len(e.get('false_positives', [])) for e in ledger)
        assert total_fp == 6

        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=3),
            findings=[
                SelfExaminationFinding(
                    title='Hallazgo con confianza',
                    category='test',
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.60,
                ),
            ],
        )
        post_runs = [
            _make_experiment_run(success=True, created_offset_hours=1.0)
            for _ in range(4)
        ]
        findings = service._metacognitive_calibration_findings(
            previous_review=previous_review,
            experiment_runs=post_runs,
        )
        bias_finding = next((f for f in findings if f.category == 'metacognitive_persistent_bias'), None)
        assert bias_finding is not None
        assert 'falsos positivos' in bias_finding.summary
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_build_review_includes_metacognitive_findings_in_full_cycle() -> None:
    """End-to-end: build_review includes metacognitive findings when
    previous review exists and enough experiment data is available."""
    root = _workspace('metacognitive_e2e')
    try:
        bootstrap = AppBootstrap(str(root))
        service = bootstrap.operational_self_examination_service

        previous_review = SelfExaminationSnapshot(
            updated_at_utc=utc_now() - timedelta(hours=4),
            findings=[
                SelfExaminationFinding(
                    title='Fijación cognitiva en chatgpt',
                    category='cognitive_fixation',
                    severity=IssueSeverity.HIGH,
                    confidence=0.80,
                    metadata={'dominant_kind': 'chatgpt'},
                ),
            ],
        )
        payload = previous_review.model_dump(mode='json')
        service.storage.save_json_atomic('self_examination/latest.json', payload)

        for _ in range(5):
            bootstrap.experiment_lab.record_outcome(
                domain=ExperimentDomain.CODE,
                objective='Test metacognition',
                subject_key='general',
                route=EvaluationRoute.CODE_AGENT,
                candidate_label='chatgpt',
                success=True,
                observed_summary='Success after previous HIGH finding.',
                precision=0.85,
                robustness=0.80,
                execution_ms=1200,
                metadata={'assistant_kind': 'chatgpt', 'config_signature': 'web'},
            )

        review = service.build_review()

        all_categories = {f.category for f in review.findings}
        has_metacognitive = any(
            cat.startswith('metacognitive_') or cat == 'introspection_blind_spot'
            for cat in all_categories
        )
        assert review.summary
        assert review.findings
        assert has_metacognitive, (
            f'Expected metacognitive findings in categories, got: {all_categories}'
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)
