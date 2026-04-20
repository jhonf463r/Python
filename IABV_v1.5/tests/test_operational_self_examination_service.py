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
