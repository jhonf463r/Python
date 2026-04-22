from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSessionStatus,
    AutonomousValidationSnapshot,
    ExperimentRecommendation,
    ExperimentRun,
    IssueSeverity,
    RunRecord,
    RunStatus,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    WorldModelSnapshot,
    utc_now,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage


class OperationalSelfExaminationService:
    def __init__(
        self,
        *,
        workspace_root: str,
        storage: ArtifactStorage,
        run_repository: Any | None = None,
        adaptive_session_repository: Any | None = None,
        experiment_lab_repository: Any | None = None,
        scenario_run_repository: Any | None = None,
        evolution_review_service: Any | None = None,
        world_model_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        adaptive_weight_layer: Any | None = None,
        token_rotation_ledger: Any | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.storage = storage
        self.run_repository = run_repository
        self.adaptive_session_repository = adaptive_session_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.scenario_run_repository = scenario_run_repository
        self.evolution_review_service = evolution_review_service
        self.world_model_service = world_model_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.adaptive_weight_layer = adaptive_weight_layer
        # Capa 2.2 — dep opcional. Si se pasa un ``TokenRotationLedger``,
        # ``_token_rotation_findings`` produce hallazgos proactivos sobre
        # PATs de GitHub / Devin API a punto de expirar. Es lo unico que
        # permite cerrar el loop "detectar el patron de expiracion antes
        # de que el user lo note" sin inventar observacion nueva.
        self.token_rotation_ledger: Any | None = token_rotation_ledger
        # PCS v1 — hook opcional. Si un provider con ``snapshot()`` está
        # presente, `_persist_review` incluye las violaciones de
        # encarnamiento en ``metadata['embodiment_violations']`` sin
        # cambiar el contrato del SelfExaminationSnapshot.
        self.embodiment_violation_provider: Any | None = None
        self._current_review: SelfExaminationSnapshot | None = None

    def current_review(
        self,
        *,
        refresh: bool = False,
        max_age_seconds: int = 300,
    ) -> SelfExaminationSnapshot:
        cached = self._current_review
        if cached is None:
            cached = self._load_latest_review()
            self._current_review = cached
        if not refresh and cached is not None and self._is_fresh(cached, max_age_seconds=max_age_seconds):
            return cached
        review = self.build_review()
        self._current_review = review
        return review

    def review_summary(self, review: SelfExaminationSnapshot | None = None) -> dict[str, Any]:
        resolved = review or self.current_review()
        metadata = dict(resolved.metadata or {})
        return {
            'review_id': resolved.review_id,
            'package_version': resolved.package_version,
            'summary': resolved.summary,
            'status': resolved.status,
            'assistant_brief': resolved.assistant_brief,
            'top_findings': [item.model_dump(mode='json') for item in resolved.findings[:4]],
            'recurring_issues': list(resolved.recurring_issues[:5]),
            'recommended_adjustments': list(resolved.recommended_adjustments[:5]),
            'validated_improvements': list(resolved.validated_improvements[:4]),
            'unresolved_risks': list(resolved.unresolved_risks[:6]),
            'recommendation_feedback': list(metadata.get('recommendation_feedback') or [])[:6],
            'feedback_summary': dict(metadata.get('feedback_summary') or {}),
            # H4 — surfacing explícito de los probe requests pendientes al
            # summary para que la UI, el orquestador y los MCP consumers los
            # vean sin tener que descender al ``metadata`` crudo.
            'pending_auto_probes': list(metadata.get('pending_auto_probes') or [])[:6],
            'updated_at_utc': resolved.updated_at_utc.isoformat(),
            'package_path': resolved.package_path,
            'markdown_path': resolved.markdown_path,
        }

    def build_review(self) -> SelfExaminationSnapshot:
        now = utc_now()
        previous_review = self._load_latest_review()
        recent_runs = self._recent_runs()
        adaptive_sessions = self._recent_adaptive_sessions()
        experiment_runs = self._recent_experiment_runs()
        recommendations = self._recent_recommendations()
        scenario_runs = self._recent_scenario_runs()
        project_health = self._project_health_snapshot()
        backlog = self._improvement_backlog()
        world = self._world_model()
        validation = self._validation_snapshot()

        findings: list[SelfExaminationFinding] = []
        findings.extend(self._recurring_failure_findings(recent_runs=recent_runs))
        findings.extend(self._pack_stall_findings(adaptive_sessions=adaptive_sessions))
        findings.extend(
            self._route_inertia_findings(
                experiment_runs=experiment_runs,
                recommendations=recommendations,
            )
        )
        findings.extend(
            self._repeated_block_findings(
                experiment_runs=experiment_runs,
                world=world,
            )
        )
        findings.extend(self._weak_correction_findings(scenario_runs=scenario_runs))
        findings.extend(self._token_rotation_findings())
        findings = self._dedupe_findings(findings)

        recurring_issues = self._recurring_issues(findings=findings, project_health=project_health)
        recommended_adjustments = self._recommended_adjustments(findings=findings, backlog=backlog)
        validated_improvements = self._validated_improvements(
            recommendations=recommendations,
            validation=validation,
            experiment_runs=experiment_runs,
        )
        recommendation_feedback = self._recommendation_feedback(
            previous_review=previous_review,
            current_findings=findings,
            validated_improvements=validated_improvements,
            experiment_runs=experiment_runs,
            validation=validation,
        )
        feedback_summary = self._feedback_summary(recommendation_feedback)
        recommended_adjustments = self._apply_feedback_to_adjustments(
            recommended_adjustments=recommended_adjustments,
            recommendation_feedback=recommendation_feedback,
        )
        unresolved_risks = self._unresolved_risks(
            findings=findings,
            world=world,
            validation=validation,
            experiment_runs=experiment_runs,
            adaptive_sessions=adaptive_sessions,
        )
        status = self._status(findings=findings, unresolved_risks=unresolved_risks)
        summary = self._summary(
            status=status,
            findings=findings,
            validated_improvements=validated_improvements,
            recurring_issues=recurring_issues,
            feedback_summary=feedback_summary,
        )
        review = SelfExaminationSnapshot(
            created_at_utc=now,
            updated_at_utc=now,
            summary=summary,
            status=status,
            findings=findings[:8],
            recurring_issues=recurring_issues[:6],
            recommended_adjustments=recommended_adjustments[:6],
            validated_improvements=validated_improvements[:4],
            unresolved_risks=unresolved_risks[:8],
            metadata={
                'recommendation_feedback': recommendation_feedback[:6],
                'feedback_summary': feedback_summary,
            },
        )
        return self._persist_review(review)

    def _persist_review(self, review: SelfExaminationSnapshot) -> SelfExaminationSnapshot:
        embodiment_violations = self._collect_embodiment_violations()
        metadata_update: dict[str, Any] = {
            **dict(review.metadata or {}),
            'workspace_root': self.workspace_root,
            'source_refs': [
                'RunRepository',
                'AdaptiveSessionRepository',
                'ExperimentLab',
                'EvolutionReviewService',
                'WorldModelSnapshot',
                'AutonomousValidationSnapshot',
            ],
        }
        if embodiment_violations is not None:
            metadata_update['embodiment_violations'] = embodiment_violations
        # H4 — cierre del loop de autoexaminacion real (capa P4). Cuando el
        # self-exam detecta un hallazgo HIGH con alta confianza, la responsa-
        # bilidad del servicio no es solo "quejarse" en recommended_adjustments:
        # tambien debe dejar explicita la prueba reproducible concreta (scope,
        # evidence_refs, suggested_tests) lista para que el orquestador o la
        # UI la disparen. Antes esto se perdia en texto generico como
        # "Construir prueba reproducible del fallo" con last_feedback_status
        # == 'no_evidence', y ningun componente recogia ese testigo. No se
        # inventa un cerebro nuevo: solo se estructura la senal de probe para
        # que el AutonomousValidationCycle / ToolTeachService existentes la
        # consuman.
        metadata_update['pending_auto_probes'] = self._pending_auto_probes(
            findings=list(review.findings)
        )
        review = review.model_copy(
            update={
                'assistant_brief': self._render_assistant_brief(review),
                'package_path': str(self.storage.resolve('self_examination/latest.json')),
                'markdown_path': str(self.storage.resolve('self_examination/latest.md')),
                'metadata': metadata_update,
            }
        )
        archive_json_rel = f'self_examination/history/{review.review_id}.json'
        archive_md_rel = f'self_examination/history/{review.review_id}.md'
        latest_json_rel = 'self_examination/latest.json'
        latest_md_rel = 'self_examination/latest.md'
        payload = review.model_dump(mode='json')
        self.storage.save_json_atomic(archive_json_rel, payload)
        self.storage.save_bytes(archive_md_rel, review.assistant_brief.encode('utf-8'))
        self.storage.save_json_atomic(latest_json_rel, payload)
        self.storage.save_bytes(latest_md_rel, review.assistant_brief.encode('utf-8'))
        review.metadata.update(
            {
                'archive_json_path': str(self.storage.resolve(archive_json_rel)),
                'archive_markdown_path': str(self.storage.resolve(archive_md_rel)),
            }
        )
        self.storage.save_json_atomic(latest_json_rel, review.model_dump(mode='json'))
        return review

    def _collect_embodiment_violations(self) -> list[dict[str, Any]] | None:
        """Serializa el snapshot del provider de encarnamiento (si hay).

        Fail-observable: si el provider no está, devuelve ``None`` y el
        caller omite la clave de metadata. Si el provider falla en
        runtime, se come la excepción y se devuelve ``None`` — PCS v1
        declara ``handshake_required=False`` y no debe romper la
        autoexaminación.
        """

        provider = getattr(self, 'embodiment_violation_provider', None)
        if provider is None or not hasattr(provider, 'snapshot'):
            return None
        try:
            records = list(provider.snapshot() or [])
        except Exception:
            return None
        serialized: list[dict[str, Any]] = []
        for record in records:
            if hasattr(record, 'model_dump'):
                try:
                    serialized.append(record.model_dump(mode='json'))
                    continue
                except Exception:
                    pass
            if isinstance(record, dict):
                serialized.append(record)
        return serialized

    def _load_latest_review(self) -> SelfExaminationSnapshot | None:
        try:
            if not self.storage.exists('self_examination/latest.json'):
                return None
            payload = self.storage.load_json('self_examination/latest.json')
            return SelfExaminationSnapshot.model_validate(payload)
        except Exception:
            return None

    def _is_fresh(self, review: SelfExaminationSnapshot, *, max_age_seconds: int) -> bool:
        try:
            age_seconds = (utc_now() - review.updated_at_utc).total_seconds()
        except Exception:
            return False
        return age_seconds <= max_age_seconds

    def _recent_runs(self) -> list[RunRecord]:
        repository = self.run_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        try:
            return list(repository.list_recent(limit=60))
        except Exception:
            return []

    def _recent_adaptive_sessions(self) -> list[Any]:
        repository = self.adaptive_session_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        try:
            return list(repository.list_recent(limit=40))
        except Exception:
            return []

    def _recent_experiment_runs(self) -> list[ExperimentRun]:
        repository = self.experiment_lab_repository
        if repository is None or not hasattr(repository, 'list_runs'):
            return []
        try:
            return list(repository.list_runs(limit=60))
        except Exception:
            return []

    def _recent_recommendations(self) -> list[ExperimentRecommendation]:
        repository = self.experiment_lab_repository
        if repository is None or not hasattr(repository, 'list_recommendations'):
            return []
        try:
            return list(repository.list_recommendations(limit=12))
        except Exception:
            return []

    def _recent_scenario_runs(self) -> list[Any]:
        repository = self.scenario_run_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        try:
            return list(repository.list_recent(limit=30))
        except Exception:
            return []

    def _project_health_snapshot(self) -> dict[str, Any]:
        service = self.evolution_review_service
        if service is None or not hasattr(service, 'build_project_health'):
            return {}
        try:
            return service.build_project_health().model_dump(mode='json')
        except Exception:
            return {}

    def _improvement_backlog(self) -> list[dict[str, Any]]:
        service = self.evolution_review_service
        if service is None or not hasattr(service, 'build_improvement_backlog'):
            return []
        try:
            return [item.model_dump(mode='json') for item in service.build_improvement_backlog(limit=8)]
        except Exception:
            return []

    def _world_model(self) -> WorldModelSnapshot:
        service = self.world_model_service
        if service is None or not hasattr(service, 'current_model'):
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            return service.current_model()
        except Exception:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _validation_snapshot(self) -> AutonomousValidationSnapshot:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_snapshot'):
            return AutonomousValidationSnapshot(
                status='idle',
                unresolved_fields=['UNRESOLVED:validation_cycle'],
            )
        try:
            return service.current_snapshot()
        except Exception:
            return AutonomousValidationSnapshot(
                status='degraded',
                unresolved_fields=['UNRESOLVED:validation_cycle'],
            )

    # Ventana de recurrencia real para "fallo repetido". Runs anteriores a
    # este margen se consideran historia fria y no cuentan, evitando que un
    # fallo viejo unico quede atrapado en `list_recent(limit=60)` como si
    # fuera recurrencia.
    _RECURRING_FAILURE_WINDOW = timedelta(hours=48)

    # Umbral para promover un hallazgo a auto-probe. Por debajo de 0.85 la
    # evidencia del self-exam no es lo suficientemente fuerte como para
    # pedirle al orquestador que gaste ciclos de validacion; por encima, el
    # silencio de no generar probe concreto es peor (capa P4 se queda muda).
    _AUTO_PROBE_CONFIDENCE_FLOOR = 0.85

    def _pending_auto_probes(
        self,
        *,
        findings: list[SelfExaminationFinding],
    ) -> list[dict[str, Any]]:
        """Derivar probe requests concretos para findings HIGH + alta confianza.

        El servicio no ejecuta la prueba: sólo deja la tarjeta lista para que
        el orquestador (``AdaptiveTaskOrchestrator``), la UI
        (``EvolutionCenterViewModel``) o el ciclo de validación autónoma la
        consuman. Respeta los contratos de las capas cerradas P1–P4: no crea
        otro cerebro, ni duplica ``PerceptionSnapshot``, ni toma decisiones de
        ruta por su cuenta.
        """
        probes: list[dict[str, Any]] = []
        now = utc_now()
        for finding in findings:
            if getattr(finding.severity, 'value', str(finding.severity)) != IssueSeverity.HIGH.value:
                continue
            confidence = float(finding.confidence or 0.0)
            if confidence < self._AUTO_PROBE_CONFIDENCE_FLOOR:
                continue
            suggested_tests = self._auto_probe_suggested_tests(finding=finding)
            if not suggested_tests:
                continue
            metadata = dict(finding.metadata or {})
            scope = str(metadata.get('scope') or metadata.get('pack_id') or metadata.get('block') or '').strip()
            probes.append(
                {
                    'finding_id': finding.finding_id,
                    'category': finding.category,
                    'scope': scope,
                    'title': finding.title,
                    'severity': getattr(finding.severity, 'value', str(finding.severity)),
                    'confidence': confidence,
                    'evidence_refs': list(finding.evidence_refs[:4]),
                    'source_refs': list(finding.source_refs[:4]),
                    'suggested_tests': suggested_tests,
                    'trigger_reason': (
                        f'Finding HIGH \'{finding.category}\' con confianza '
                        f'{confidence:.2f} >= {self._AUTO_PROBE_CONFIDENCE_FLOOR:.2f}; '
                        f'autotests=0 no cierra el loop P4.'
                    ),
                    'requested_at_utc': now.isoformat(),
                    'status': 'requested',
                }
            )
        return probes[:6]

    def _auto_probe_suggested_tests(
        self,
        *,
        finding: SelfExaminationFinding,
    ) -> list[str]:
        """Sugerencia de prueba concreta por categoría de finding.

        Las sugerencias son comandos/descripciones estables que el orquestador
        puede mapear a un runner real. No se lanza nada desde aquí.
        """
        metadata = dict(finding.metadata or {})
        category = str(finding.category or '').strip().lower()
        if category == 'recurring_failure':
            scope = str(metadata.get('scope') or '').strip()
            tests = ['pytest -q -p no:cacheprovider tests/']
            run_ids = [ref for ref in finding.evidence_refs[:3] if str(ref).strip()]
            if run_ids:
                tests.append(f"reproduce_run_ids={','.join(run_ids)}")
            if scope:
                tests.append(f'scope={scope}')
            return tests
        if category == 'repeated_stall':
            pack_id = str(metadata.get('pack_id') or '').strip()
            tests = ['revisar defaults y readiness del pack en sandbox']
            if pack_id:
                tests.append(f'pack_id={pack_id}')
            return tests
        if category == 'route_inertia':
            return ['re-lanzar contendiente vs ganador en ExperimentLab']
        if category == 'repeated_block':
            block = str(metadata.get('block') or '').strip()
            return [f'replay con block={block}'] if block else []
        if category == 'weak_correction':
            return ['recapturar escena con anotacion reforzada']
        if category == 'token_rotation':
            token_name = str(metadata.get('token_name') or '').strip()
            tests: list[str] = ['powershell -ExecutionPolicy Bypass -File scripts\\rotate_tokens.ps1']
            if token_name:
                tests.append(f'token_name={token_name}')
            return tests
        return []

    def _recurring_failure_findings(self, *, recent_runs: list[RunRecord]) -> list[SelfExaminationFinding]:
        now = utc_now()
        window_start = now - self._RECURRING_FAILURE_WINDOW
        grouped: dict[str, dict[str, RunRecord]] = defaultdict(dict)
        for run in recent_runs:
            # Solo FAILED cuenta como fallo real; PARTIAL es "resuelto parcial",
            # no es un fallo a repetir. Antes se agrupaban ambos y eso generaba
            # falsos positivos tipo "Fallo repetido en general:training".
            if run.status != RunStatus.FAILED:
                continue
            if run.created_at_utc and run.created_at_utc < window_start:
                continue
            # Dedup defensivo por run_id: garantiza que un mismo run repetido
            # en la lista (retry logging, etc.) no se cuente dos veces.
            grouped[self._task_scope(run)].setdefault(run.run_id, run)
        findings: list[SelfExaminationFinding] = []
        for scope, runs_by_id in grouped.items():
            runs = list(runs_by_id.values())
            if len(runs) < 2:
                continue
            severity = IssueSeverity.HIGH if len(runs) >= 3 else IssueSeverity.MEDIUM
            findings.append(
                SelfExaminationFinding(
                    category='recurring_failure',
                    title=f'Fallo repetido en {scope}',
                    summary=(
                        f'La clase de tarea {scope} acumula {len(runs)} corridas fallidas '
                        f'en las ultimas {int(self._RECURRING_FAILURE_WINDOW.total_seconds() // 3600)} horas.'
                    ),
                    severity=severity,
                    confidence=min(0.92, 0.45 + len(runs) * 0.12),
                    recommendation=f'Revisar la ruta, el pack y la evidencia previa antes de repetir {scope}.',
                    evidence_refs=[run.run_id for run in runs[:4]],
                    source_refs=['RunRepository'],
                    metadata={
                        'scope': scope,
                        'failed_count': len(runs),
                        'window_hours': int(self._RECURRING_FAILURE_WINDOW.total_seconds() // 3600),
                    },
                )
            )
        return findings

    def _pack_stall_findings(self, *, adaptive_sessions: list[Any]) -> list[SelfExaminationFinding]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        stalled_statuses = {
            AdaptiveSessionStatus.NEED_INFO.value,
            AdaptiveSessionStatus.WAITING_APPROVAL.value,
            AdaptiveSessionStatus.FAILED.value,
        }
        for session in adaptive_sessions:
            status = str(getattr(getattr(session, 'status', None), 'value', getattr(session, 'status', '')) or '')
            if status not in stalled_statuses:
                continue
            pack_id = str(getattr(session, 'chosen_pack_id', '') or 'pack_desconocido')
            grouped[pack_id].append(session)
        findings: list[SelfExaminationFinding] = []
        for pack_id, sessions in grouped.items():
            if len(sessions) < 2:
                continue
            findings.append(
                SelfExaminationFinding(
                    category='repeated_stall',
                    title=f'Pack atascado: {pack_id}',
                    summary=f'El pack {pack_id} reaparece {len(sessions)} veces en need_info, waiting_approval o failed.',
                    severity=IssueSeverity.MEDIUM,
                    confidence=min(0.9, 0.42 + len(sessions) * 0.14),
                    recommendation=f'Revisar defaults, readiness y preguntas obligatorias del pack {pack_id}.',
                    evidence_refs=[str(getattr(session, 'session_id', '') or '') for session in sessions[:4]],
                    source_refs=['AdaptiveSessionRepository'],
                    metadata={
                        'pack_id': pack_id,
                        'statuses': [
                            str(getattr(getattr(session, 'status', None), 'value', getattr(session, 'status', '')) or '')
                            for session in sessions[:4]
                        ],
                    },
                )
            )
        return findings

    def _route_inertia_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        recommendations: list[ExperimentRecommendation],
    ) -> list[SelfExaminationFinding]:
        if not experiment_runs:
            return []
        grouped_runs: dict[tuple[object, str, str], list[ExperimentRun]] = defaultdict(list)
        for run in experiment_runs:
            key = (
                run.route,
                str(run.assistant_kind or '').strip().lower(),
                str(run.config_signature or '').strip(),
            )
            grouped_runs[key].append(run)
        profiles = (
            self.adaptive_weight_layer.suggest(grouped_runs=grouped_runs)
            if self.adaptive_weight_layer is not None
            else {}
        )
        recommended_keys = {
            (
                recommendation.recommended_route,
                str(recommendation.recommended_assistant_kind or '').strip().lower(),
                str(recommendation.recommended_config_signature or '').strip(),
            )
            for recommendation in recommendations
        }
        findings: list[SelfExaminationFinding] = []
        for key, profile in profiles.items():
            sample_count = int(profile.get('sample_count') or 0)
            if sample_count < 3:
                continue
            blocked_rate = float(profile.get('blocked_rate') or 0.0)
            fallback_rate = float(profile.get('fallback_rate') or 0.0)
            success_rate = float(profile.get('success_rate') or 0.0)
            trend_score = float(profile.get('trend_score') or 0.0)
            if blocked_rate < 0.34 and fallback_rate < 0.34 and success_rate >= 0.55 and trend_score > -0.12:
                continue
            route, assistant_kind, config_signature = key
            route_value = str(getattr(route, 'value', route) or '')
            recommendation = (
                'Exigir validacion adicional antes de reutilizar esta ruta.'
                if blocked_rate >= 0.34 or fallback_rate >= 0.34
                else 'Debilitar esta preferencia hasta que la tendencia vuelva a mejorar.'
            )
            if key in recommended_keys:
                recommendation += ' Hoy sigue apareciendo como preferencia y conviene revisar si se mantiene por inercia.'
            findings.append(
                SelfExaminationFinding(
                    category='inertial_route',
                    title=f'Ruta debil o inercial: {assistant_kind or "asistente_base"} por {route_value}',
                    summary=(
                        f'Se reutilizo {sample_count} veces con exito {success_rate:.0%}, '
                        f'bloqueos {blocked_rate:.0%}, fallback {fallback_rate:.0%} y tendencia {trend_score:+.2f}.'
                    ),
                    severity=IssueSeverity.HIGH if blocked_rate >= 0.5 or success_rate < 0.45 else IssueSeverity.MEDIUM,
                    confidence=min(0.94, 0.46 + sample_count * 0.08),
                    recommendation=recommendation,
                    evidence_refs=[run.run_id for run in grouped_runs[key][:4]],
                    source_refs=['ExperimentLab', 'AdaptiveWeightLayer'],
                    metadata={
                        'route': route_value,
                        'assistant_kind': assistant_kind,
                        'config_signature': config_signature,
                        'profile': dict(profile),
                        'currently_recommended': key in recommended_keys,
                    },
                )
            )
        return findings

    def _repeated_block_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        world: WorldModelSnapshot,
    ) -> list[SelfExaminationFinding]:
        block_counts: Counter[str] = Counter()
        evidence: dict[str, list[str]] = defaultdict(list)
        for run in experiment_runs:
            metadata = dict(run.metadata or {})
            flags = [str(item).strip() for item in (metadata.get('external_state_flags') or []) if str(item).strip()]
            for flag in flags:
                block_counts[flag] += 1
                evidence[flag].append(run.run_id)
        current_blocks = {str(item).strip() for item in (world.detected_blocks or []) if str(item).strip()}
        findings: list[SelfExaminationFinding] = []
        for flag, count in block_counts.most_common():
            if count < 2:
                continue
            active_now = flag in current_blocks
            recommendation = f'No reintentar rutas afectadas por {flag} hasta verificar la condicion operativa.'
            if active_now:
                recommendation += ' El world model la sigue reportando en este momento.'
            findings.append(
                SelfExaminationFinding(
                    category='repeated_block',
                    title=f'Bloqueo recurrente: {flag}',
                    summary=f'El bloqueo {flag} reaparecio {count} veces en corridas comparables.',
                    severity=IssueSeverity.HIGH if active_now or count >= 3 else IssueSeverity.MEDIUM,
                    confidence=min(0.95, 0.48 + count * 0.1),
                    recommendation=recommendation,
                    evidence_refs=evidence[flag][:5],
                    source_refs=['ExperimentLab', 'WorldModelSnapshot'],
                    metadata={
                        'block': flag,
                        'count': count,
                        'active_now': active_now,
                    },
                )
            )
        return findings

    def _weak_correction_findings(self, *, scenario_runs: list[Any]) -> list[SelfExaminationFinding]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for scenario_run in scenario_runs:
            scenario_id = str(getattr(getattr(scenario_run, 'scenario', None), 'scenario_id', '') or '')
            if not scenario_id:
                continue
            grouped[scenario_id].append(scenario_run)
        findings: list[SelfExaminationFinding] = []
        for scenario_id, runs in grouped.items():
            weak_runs = []
            for scenario_run in runs:
                adjustments = list(getattr(scenario_run, 'runtime_adjustments', []) or [])
                pending_issue_id = str(getattr(scenario_run, 'pending_issue_id', '') or '')
                diagnosis = getattr(scenario_run, 'diagnosis', None)
                category = str(getattr(getattr(diagnosis, 'category', None), 'value', getattr(diagnosis, 'category', '')) or '')
                if adjustments and (pending_issue_id or category == 'need_codex_fix'):
                    weak_runs.append(scenario_run)
                    continue
                guided_cycle = dict(getattr(scenario_run, 'metadata', {}).get('guided_improvement_cycle') or {})
                if int(guided_cycle.get('applied_count') or 0) > 0 and pending_issue_id:
                    weak_runs.append(scenario_run)
            if not weak_runs:
                continue
            findings.append(
                SelfExaminationFinding(
                    category='weak_correction',
                    title=f'Correccion debil en {scenario_id}',
                    summary=(
                        f'Los ajustes o correcciones guiadas del escenario {scenario_id} no cerraron el problema '
                        f'y terminaron en pending issue o need_codex_fix.'
                    ),
                    severity=IssueSeverity.HIGH if len(weak_runs) >= 2 else IssueSeverity.MEDIUM,
                    confidence=min(0.9, 0.5 + len(weak_runs) * 0.12),
                    recommendation=f'Dejar de iterar solo con tuning runtime en {scenario_id} y escalar a cambio verificable.',
                    evidence_refs=[str(getattr(run, 'scenario_run_id', '') or '') for run in weak_runs[:4]],
                    source_refs=['ScenarioRunRepository', 'GuidedImprovementCycle'],
                    metadata={
                        'scenario_id': scenario_id,
                        'occurrences': len(weak_runs),
                    },
                )
            )
        return findings

    def _token_rotation_findings(self) -> list[SelfExaminationFinding]:
        """Hallazgos proactivos sobre rotacion de tokens (capa 2.2).

        Lee el ``TokenRotationLedger`` inyectado por ``bootstrap``. Si no
        hay ledger o todavia no hay eventos registrados, devuelve lista
        vacia (NO inventa observacion). Reglas:

        - ``expired_live`` en la ultima observacion -> HIGH, recomienda
          ``scripts/rotate_tokens.ps1`` ya.
        - ``proactive_due`` (projected_expiry <= lead_time y al menos una
          rotacion previa) -> HIGH: cerrar el loop antes del 401.
        - ``stale`` (sin probe OK reciente) pero sin 401 observado ->
          MEDIUM: quizas el sistema dejo de mirar, quizas el token ya
          no se usa; pide un probe explicito.
        """
        ledger = getattr(self, 'token_rotation_ledger', None)
        if ledger is None or not hasattr(ledger, 'predictions'):
            return []
        try:
            predictions = list(ledger.predictions() or [])
        except Exception:
            return []
        findings: list[SelfExaminationFinding] = []
        for pred in predictions:
            if not isinstance(pred, dict):
                continue
            token_name = str(pred.get('token_name') or '').strip()
            if not token_name:
                continue
            expired = bool(pred.get('expired_live'))
            proactive = bool(pred.get('proactive_due'))
            stale = bool(pred.get('stale'))
            if not (expired or proactive or stale):
                continue

            if expired:
                severity = IssueSeverity.HIGH
                confidence = 0.93
                title = f'Token {token_name} expirado: rotar ya'
                summary = (
                    f'La ultima observacion del token {token_name} fue un probe fallido '
                    f'(probe_failed). El sistema dejo de autenticar contra su endpoint '
                    f'y cualquier ruta externa dependiente esta rota hasta rotar.'
                )
            elif proactive:
                severity = IssueSeverity.HIGH
                confidence = 0.87
                days = pred.get('days_until_projected_expiry')
                days_txt = f'{days:.1f}d' if isinstance(days, (int, float)) else 'pronto'
                title = f'Rotacion proactiva de {token_name} ({days_txt})'
                summary = (
                    f'Por el promedio observado ({pred.get("avg_interval_days"):.1f} dias '
                    f'entre rotaciones pasadas, {pred.get("rotations_observed")} muestras) '
                    f'el token {token_name} expirara en {days_txt}. Rotar antes evita 401.'
                )
            else:  # stale
                severity = IssueSeverity.MEDIUM
                confidence = 0.6
                title = f'Observabilidad stale en {token_name}'
                summary = (
                    f'No hay un probe OK reciente del token {token_name}. No implica '
                    f'caducidad real, pero el sistema perdio la senal. Falta probe '
                    f'contra el endpoint autenticado para reestablecer observabilidad.'
                )

            findings.append(
                SelfExaminationFinding(
                    category='token_rotation',
                    title=title,
                    summary=summary,
                    severity=severity,
                    confidence=confidence,
                    recommendation=(
                        'Ejecutar scripts/rotate_tokens.ps1 (device-flow de GitHub + '
                        'prompt seguro de Devin API key). Es idempotente y solo actualiza '
                        '~/.iabv_secrets.ps1 cuando el probe post-rotacion da 200 OK.'
                    ),
                    evidence_refs=[
                        ref for ref in (
                            pred.get('last_probe_ok_at'),
                            pred.get('last_probe_failed_at'),
                            pred.get('last_rotation_at'),
                        ) if ref
                    ],
                    source_refs=['TokenRotationLedger'],
                    metadata={
                        'token_name': token_name,
                        'expired_live': expired,
                        'proactive_due': proactive,
                        'stale': stale,
                        'avg_interval_days': pred.get('avg_interval_days'),
                        'days_until_projected_expiry': pred.get('days_until_projected_expiry'),
                        'projected_expiry_at': pred.get('projected_expiry_at'),
                        'rotations_observed': pred.get('rotations_observed'),
                    },
                )
            )
        return findings

    def _dedupe_findings(self, findings: list[SelfExaminationFinding]) -> list[SelfExaminationFinding]:
        ranked = sorted(
            findings,
            key=lambda item: (
                self._severity_rank(item.severity),
                float(item.confidence or 0.0),
                len(item.evidence_refs or []),
            ),
            reverse=True,
        )
        unique: list[SelfExaminationFinding] = []
        seen: set[tuple[str, str]] = set()
        for finding in ranked:
            key = (finding.category, finding.title)
            if key in seen:
                continue
            unique.append(finding)
            seen.add(key)
        return unique

    def _recurring_issues(
        self,
        *,
        findings: list[SelfExaminationFinding],
        project_health: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items = [
            {
                'title': finding.title,
                'category': finding.category,
                'summary': finding.summary,
                'severity': getattr(finding.severity, 'value', str(finding.severity)),
                'confidence': finding.confidence,
                'evidence_refs': list(finding.evidence_refs[:4]),
                'source_refs': list(finding.source_refs[:4]),
            }
            for finding in findings[:5]
        ]
        repeated = list(project_health.get('repeated_issues') or [])
        for issue in repeated[:3]:
            issue_hint = str(issue.get('issue_hint') or '').strip()
            if not issue_hint:
                continue
            items.append(
                {
                    'title': issue_hint,
                    'category': 'project_health_repeat',
                    'summary': f'El issue {issue_hint} reaparece {int(issue.get("count") or 0)} veces en la capa evolutiva.',
                    'severity': IssueSeverity.MEDIUM.value,
                    'confidence': 0.68,
                    'evidence_refs': [],
                    'source_refs': ['EvolutionReviewService'],
                }
            )
        return items[:6]

    def _recommended_adjustments(
        self,
        *,
        findings: list[SelfExaminationFinding],
        backlog: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items = [
            {
                'title': finding.title,
                'recommended_change': finding.recommendation,
                'category': finding.category,
                    'severity': getattr(finding.severity, 'value', str(finding.severity)),
                    'confidence': finding.confidence,
                    'evidence_refs': list(finding.evidence_refs[:4]),
                    'source_refs': list(finding.source_refs[:4]),
                    'metadata': dict(finding.metadata or {}),
                    'feedback_key': self._adjustment_feedback_key(
                        category=finding.category,
                        title=finding.title,
                        metadata=dict(finding.metadata or {}),
                    ),
                }
            for finding in findings
            if finding.recommendation
        ]
        for proposal in backlog[:4]:
            recommended_change = str(proposal.get('recommended_change') or '').strip()
            if not recommended_change:
                continue
            if any(str(item.get('recommended_change') or '').strip().lower() == recommended_change.lower() for item in items):
                continue
            items.append(
                {
                    'title': str(proposal.get('title') or 'Mejora sugerida'),
                    'recommended_change': recommended_change,
                    'category': 'backlog',
                    'severity': IssueSeverity.MEDIUM.value,
                    'confidence': min(0.95, float(proposal.get('priority_score') or 0) / 100.0),
                    'evidence_refs': [],
                    'source_refs': ['EvolutionReviewService'],
                    'metadata': dict(proposal.get('metadata') or {}),
                    'feedback_key': self._adjustment_feedback_key(
                        category='backlog',
                        title=str(proposal.get('title') or 'Mejora sugerida'),
                        metadata=dict(proposal.get('metadata') or {}),
                    ),
                }
            )
        return self._dedupe_adjustments(items)[:6]

    def _adjustment_group_key(self, item: dict[str, Any]) -> tuple[str, str, str]:
        """Clave de agrupacion para colapsar ajustes recomendados duplicados.

        Usa ``(fuente_principal, categoria, titulo)``: distintos "recommended_change"
        con el mismo titulo/categoria/fuente se consideran variantes del mismo
        patron y se colapsan con ``duplicate_count``.
        """
        sources = list(item.get('source_refs') or [])
        primary_source = str(sources[0]) if sources else ''
        category = str(item.get('category') or '').strip().lower()
        title = str(item.get('title') or '').strip().lower()
        return primary_source, category, title

    def _dedupe_adjustments(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: dict[tuple[str, str, str], dict[str, Any]] = {}
        order: list[tuple[str, str, str]] = []
        for item in items:
            key = self._adjustment_group_key(item)
            if key in seen:
                existing = seen[key]
                metadata = dict(existing.get('metadata') or {})
                metadata['duplicate_count'] = int(metadata.get('duplicate_count') or 1) + 1
                variants = list(metadata.get('duplicate_variants') or [])
                variant = str(item.get('recommended_change') or '').strip()
                if variant and variant not in variants and len(variants) < 4:
                    variants.append(variant)
                if variants:
                    metadata['duplicate_variants'] = variants
                existing['metadata'] = metadata
                existing_refs = list(existing.get('evidence_refs') or [])
                for ref in item.get('evidence_refs') or []:
                    if ref not in existing_refs and len(existing_refs) < 4:
                        existing_refs.append(ref)
                existing['evidence_refs'] = existing_refs
                if float(item.get('confidence') or 0.0) > float(existing.get('confidence') or 0.0):
                    existing['confidence'] = item.get('confidence')
                    recommended_change = str(item.get('recommended_change') or '').strip()
                    if recommended_change:
                        existing['recommended_change'] = recommended_change
            else:
                clone = dict(item)
                metadata = dict(item.get('metadata') or {})
                metadata['duplicate_count'] = 1
                variant = str(item.get('recommended_change') or '').strip()
                if variant:
                    metadata['duplicate_variants'] = [variant]
                clone['metadata'] = metadata
                clone['evidence_refs'] = list(item.get('evidence_refs') or [])
                seen[key] = clone
                order.append(key)
        return [seen[key] for key in order]

    def _recommendation_feedback(
        self,
        *,
        previous_review: SelfExaminationSnapshot | None,
        current_findings: list[SelfExaminationFinding],
        validated_improvements: list[dict[str, Any]],
        experiment_runs: list[ExperimentRun],
        validation: AutonomousValidationSnapshot,
    ) -> list[dict[str, Any]]:
        if previous_review is None:
            return []
        previous_adjustments = list(previous_review.recommended_adjustments or [])
        if not previous_adjustments:
            return []
        reviewed_after = previous_review.updated_at_utc
        post_review_runs = [
            run
            for run in experiment_runs
            if getattr(run, 'created_at_utc', None) is not None and run.created_at_utc > reviewed_after
        ]
        current_findings_by_key = {
            self._adjustment_feedback_key(
                category=finding.category,
                title=finding.title,
                metadata=dict(finding.metadata or {}),
            ): finding
            for finding in current_findings
        }
        items: list[dict[str, Any]] = []
        for adjustment in previous_adjustments[:8]:
            category = str(adjustment.get('category') or '').strip()
            title = str(adjustment.get('title') or 'Ajuste previo').strip()
            metadata = dict(adjustment.get('metadata') or {})
            feedback_key = str(adjustment.get('feedback_key') or self._adjustment_feedback_key(category=category, title=title, metadata=metadata))
            matching_runs = self._matching_runs_for_adjustment(
                adjustment=adjustment,
                experiment_runs=post_review_runs,
            )
            profile = self._feedback_profile(matching_runs)
            current_finding = current_findings_by_key.get(feedback_key)
            has_validated_evidence = self._adjustment_has_validated_evidence(
                adjustment=adjustment,
                validated_improvements=validated_improvements,
                validation=validation,
            )
            sample_count = int(profile.get('sample_count') or 0)
            success_rate = float(profile.get('success_rate') or 0.0)
            blocked_rate = float(profile.get('blocked_rate') or 0.0)
            fallback_rate = float(profile.get('fallback_rate') or 0.0)
            trend_score = float(profile.get('trend_score') or 0.0)
            positive_metrics = sample_count >= 2 and success_rate >= 0.66 and blocked_rate < 0.25 and fallback_rate < 0.25 and trend_score > -0.08
            negative_metrics = sample_count >= 2 and (success_rate < 0.5 or blocked_rate >= 0.34 or fallback_rate >= 0.34 or current_finding is not None)
            if has_validated_evidence and positive_metrics and current_finding is None:
                status = 'validated_improvement'
                summary = 'La recomendacion previa ya tiene evidencia positiva y validacion suficiente para darla por consolidada.'
                next_step = 'No hace falta proponer el mismo ajuste otra vez salvo que reaparezca degradacion.'
            elif positive_metrics and current_finding is None:
                status = 'valid_adjustment'
                summary = 'La recomendacion previa mejoro el comportamiento en corridas posteriores, aunque todavia sin una validacion fuerte completa.'
                next_step = 'Mantener la preferencia actual y seguir observando antes de consolidarla.'
            elif negative_metrics:
                status = 'false_improvement'
                summary = 'La recomendacion previa no produjo beneficio real en la evidencia posterior o el patron sigue activo.'
                next_step = 'No repetir exactamente este ajuste sin evidencia nueva; exigir alternativa o validacion adicional.'
            else:
                status = 'no_evidence'
                summary = 'Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no.'
                next_step = 'Mantenerla en observacion hasta tener mas corridas comparables.'
            confidence = 0.52
            if sample_count >= 3:
                confidence += 0.18
            if has_validated_evidence:
                confidence += 0.14
            if current_finding is not None:
                confidence += 0.08
            evidence_refs = list(adjustment.get('evidence_refs') or [])[:2]
            evidence_refs.extend(run.run_id for run in matching_runs[:3])
            evidence_refs = list(dict.fromkeys(item for item in evidence_refs if str(item).strip()))
            items.append(
                {
                    'title': title,
                    'category': category or 'unknown',
                    'feedback_key': feedback_key,
                    'status': status,
                    'summary': summary,
                    'next_step': next_step,
                    'confidence': min(0.96, confidence),
                    'sample_count': sample_count,
                    'evidence_refs': evidence_refs[:5],
                    'source_refs': list(dict.fromkeys([*(adjustment.get('source_refs') or []), 'OperationalSelfExaminationService', 'ExperimentLab', 'AutonomousValidationSnapshot'])),
                    'profile': profile,
                    'current_issue_still_active': current_finding is not None,
                    'repeat_recommendation': status not in {'validated_improvement', 'false_improvement'},
                    'updated_at_utc': utc_now().isoformat(),
                }
            )
        return items[:6]

    def _apply_feedback_to_adjustments(
        self,
        *,
        recommended_adjustments: list[dict[str, Any]],
        recommendation_feedback: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        feedback_by_key = {
            str(item.get('feedback_key') or ''): item
            for item in recommendation_feedback
            if str(item.get('feedback_key') or '').strip()
        }
        updated: list[dict[str, Any]] = []
        for item in recommended_adjustments:
            payload = dict(item)
            feedback_key = str(payload.get('feedback_key') or self._adjustment_feedback_key(
                category=str(payload.get('category') or ''),
                title=str(payload.get('title') or ''),
                metadata=dict(payload.get('metadata') or {}),
            ))
            feedback = feedback_by_key.get(feedback_key)
            if feedback is not None:
                payload['last_feedback_status'] = str(feedback.get('status') or '')
                payload['repeat_policy'] = 'require_new_evidence' if str(feedback.get('status') or '') == 'false_improvement' else (
                    'resolved_or_validated' if str(feedback.get('status') or '') in {'validated_improvement', 'valid_adjustment'} else 'pending_evidence'
                )
                payload['feedback_note'] = str(feedback.get('next_step') or '').strip()
            updated.append(payload)
        return updated

    def _feedback_summary(self, recommendation_feedback: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(str(item.get('status') or 'unknown') for item in recommendation_feedback)
        return {
            'total_reviewed': len(recommendation_feedback),
            'validated_improvement': int(counts.get('validated_improvement', 0)),
            'valid_adjustment': int(counts.get('valid_adjustment', 0)),
            'false_improvement': int(counts.get('false_improvement', 0)),
            'no_evidence': int(counts.get('no_evidence', 0)),
        }

    def _validated_improvements(
        self,
        *,
        recommendations: list[ExperimentRecommendation],
        validation: AutonomousValidationSnapshot,
        experiment_runs: list[ExperimentRun],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for recommendation in recommendations[:4]:
            if float(recommendation.confidence or 0.0) < 0.75 and float(recommendation.score or 0.0) < 0.75:
                continue
            adaptive = dict((recommendation.metadata or {}).get('adaptive_learning_summary') or {})
            items.append(
                {
                    'title': f'{recommendation.recommended_assistant_kind or "ruta"} por {recommendation.recommended_route.value}',
                    'summary': str(recommendation.rationale or '').strip(),
                    'subject_key': recommendation.subject_key,
                    'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                    'recommended_route': recommendation.recommended_route.value,
                    'confidence': float(recommendation.confidence or 0.0),
                    'score': float(recommendation.score or 0.0),
                    'reasons': list(adaptive.get('reasons') or []),
                    'source_refs': ['ExperimentLab', 'StrategySelector'],
                    'evidence_refs': list(recommendation.supporting_run_ids[:4]),
                    'feedback_key': self._adjustment_feedback_key(
                        category='inertial_route',
                        title=f'{recommendation.recommended_assistant_kind or "ruta"} por {recommendation.recommended_route.value}',
                        metadata={
                            'assistant_kind': recommendation.recommended_assistant_kind,
                            'route': recommendation.recommended_route.value,
                            'config_signature': recommendation.recommended_config_signature,
                            'subject_key': recommendation.subject_key,
                        },
                    ),
                }
            )
        current_experiment = validation.current_experiment
        if int(validation.promoted_count or 0) > 0:
            items.append(
                {
                    'title': 'Promocion validada en sandbox',
                    'summary': str(validation.summary or '').strip() or 'Una alternativa ya fue promovida tras validacion controlada.',
                    'subject_key': str(getattr(current_experiment, 'subject_key', '') or ''),
                    'recommended_assistant_kind': str(getattr(current_experiment, 'candidate_assistant_kind', '') or ''),
                    'recommended_route': str(getattr(getattr(current_experiment, 'candidate_route', None), 'value', getattr(current_experiment, 'candidate_route', '')) or ''),
                    'confidence': 0.82,
                    'score': min(1.0, 0.68 + int(validation.promoted_count or 0) * 0.06),
                    'reasons': [str(validation.summary or '').strip()] if str(validation.summary or '').strip() else [],
                    'source_refs': ['AutonomousValidationSnapshot'],
                    'evidence_refs': [str(validation.last_experiment_id or '')] if str(validation.last_experiment_id or '').strip() else [],
                    'feedback_key': self._adjustment_feedback_key(
                        category='validation',
                        title='Promocion validada en sandbox',
                        metadata={
                            'assistant_kind': str(getattr(current_experiment, 'candidate_assistant_kind', '') or ''),
                            'route': str(getattr(getattr(current_experiment, 'candidate_route', None), 'value', getattr(current_experiment, 'candidate_route', '')) or ''),
                            'config_signature': str(getattr(current_experiment, 'candidate_config_signature', '') or ''),
                            'subject_key': str(getattr(current_experiment, 'subject_key', '') or ''),
                        },
                    ),
                }
            )
        if not items and experiment_runs:
            best_run = max(experiment_runs, key=lambda item: float(item.metrics.total_score or 0.0))
            items.append(
                {
                    'title': f'{best_run.assistant_kind or "ruta"} por {best_run.route.value}',
                    'summary': 'Hay una mejora fuerte en experimentos recientes, pero todavia no un recommendation consolidado.',
                    'subject_key': best_run.subject_key,
                    'recommended_assistant_kind': best_run.assistant_kind,
                    'recommended_route': best_run.route.value,
                    'confidence': 0.58,
                    'score': float(best_run.metrics.total_score or 0.0),
                    'reasons': [],
                    'source_refs': ['ExperimentLab'],
                    'evidence_refs': [best_run.run_id],
                    'feedback_key': self._adjustment_feedback_key(
                        category='inertial_route',
                        title=f'{best_run.assistant_kind or "ruta"} por {best_run.route.value}',
                        metadata={
                            'assistant_kind': best_run.assistant_kind,
                            'route': best_run.route.value,
                            'config_signature': best_run.config_signature,
                            'subject_key': best_run.subject_key,
                        },
                    ),
                }
            )
        return items[:4]

    def _unresolved_risks(
        self,
        *,
        findings: list[SelfExaminationFinding],
        world: WorldModelSnapshot,
        validation: AutonomousValidationSnapshot,
        experiment_runs: list[ExperimentRun],
        adaptive_sessions: list[Any],
    ) -> list[str]:
        unresolved = list(dict.fromkeys([*list(world.unresolved_fields or []), *list(validation.unresolved_fields or [])]))
        unresolved.extend(
            finding.unresolved_fields[0]
            for finding in findings
            if finding.unresolved_fields
        )
        if not experiment_runs:
            unresolved.append('UNRESOLVED:experiment_history')
        if not adaptive_sessions:
            unresolved.append('UNRESOLVED:adaptive_sessions')
        return list(dict.fromkeys(item for item in unresolved if str(item).strip()))[:8]

    def _status(
        self,
        *,
        findings: list[SelfExaminationFinding],
        unresolved_risks: list[str],
    ) -> str:
        if any(finding.severity == IssueSeverity.HIGH for finding in findings):
            return 'needs_attention'
        if findings:
            return 'watch'
        if unresolved_risks:
            return 'partial'
        return 'stable'

    def _summary(
        self,
        *,
        status: str,
        findings: list[SelfExaminationFinding],
        validated_improvements: list[dict[str, Any]],
        recurring_issues: list[dict[str, Any]],
        feedback_summary: dict[str, Any],
    ) -> str:
        if findings:
            top = findings[0]
            response = (
                f'Autoexaminacion {status}: {len(findings)} hallazgos activos. '
                f'Lo mas fuerte ahora es {top.title.lower()}. '
                f'Mejoras validadas: {len(validated_improvements)} | issues recurrentes: {len(recurring_issues)}.'
            )
            if int(feedback_summary.get('false_improvement') or 0) > 0:
                response += f" La retroalimentacion marca {int(feedback_summary.get('false_improvement') or 0)} ajuste(s) previos que no conviene repetir igual."
            return response
        if validated_improvements:
            response = (
                f'Autoexaminacion {status}: no veo degradaciones fuertes. '
                f'Si hay {len(validated_improvements)} mejoras ya respaldadas por evidencia reciente.'
            )
            if int(feedback_summary.get('valid_adjustment') or 0) > 0 or int(feedback_summary.get('validated_improvement') or 0) > 0:
                response += (
                    f" La retroalimentacion confirma {int(feedback_summary.get('validated_improvement') or 0)} mejora(s) validadas"
                    f" y {int(feedback_summary.get('valid_adjustment') or 0)} ajuste(s) utiles."
                )
            return response
        if int(feedback_summary.get('total_reviewed') or 0) > 0:
            return (
                f'Autoexaminacion {status}: revise {int(feedback_summary.get("total_reviewed") or 0)} ajuste(s) previos. '
                f'Validados: {int(feedback_summary.get("validated_improvement") or 0)} | '
                f'utiles: {int(feedback_summary.get("valid_adjustment") or 0)} | '
                f'falsas mejoras: {int(feedback_summary.get("false_improvement") or 0)} | '
                f'sin evidencia: {int(feedback_summary.get("no_evidence") or 0)}.'
            )
        return 'Autoexaminacion partial: todavia no tengo suficiente evidencia acumulada para emitir una revision fuerte.'

    def _render_assistant_brief(self, review: SelfExaminationSnapshot) -> str:
        lines = [
            '# IABV v1.5 - Operational Self Examination',
            '',
            f'Generado: {review.updated_at_utc.isoformat()}',
            f'Resumen: {review.summary}',
            '',
            'Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.',
            '',
            '## Hallazgos',
        ]
        if review.findings:
            for finding in review.findings[:6]:
                lines.append(
                    f"- {finding.title}: {finding.summary} | recomendacion: {finding.recommendation or 'sin ajuste concreto'} | confianza {finding.confidence:.2f}"
                )
        else:
            lines.append('- Sin hallazgos fuertes confirmados.')
        lines.extend(['', '## Ajustes recomendados'])
        if review.recommended_adjustments:
            for item in review.recommended_adjustments[:6]:
                lines.append(
                    f"- {str(item.get('title') or 'Ajuste')}: {str(item.get('recommended_change') or 'sin cambio sugerido')} | fuente {', '.join(item.get('source_refs') or []) or 'n/d'}"
                )
        else:
            lines.append('- Sin ajustes respaldados por evidencia suficiente.')
        lines.extend(['', '## Mejoras validadas'])
        if review.validated_improvements:
            for item in review.validated_improvements[:4]:
                lines.append(
                    f"- {str(item.get('title') or 'Mejora')}: {str(item.get('summary') or 'sin resumen')} | confianza {float(item.get('confidence') or 0.0):.2f}"
                )
        else:
            lines.append('- Sin mejoras validadas fuertes todavia.')
        feedback = list(dict(review.metadata or {}).get('recommendation_feedback') or [])
        lines.extend(['', '## Retroalimentacion de ajustes'])
        if feedback:
            for item in feedback[:4]:
                lines.append(
                    f"- {str(item.get('title') or 'Ajuste previo')}: {str(item.get('status') or 'sin estado')} | {str(item.get('summary') or 'sin resumen')} | siguiente paso: {str(item.get('next_step') or 'seguir observando')}"
                )
        else:
            lines.append('- Todavia no hay suficiente evidencia posterior para juzgar ajustes anteriores.')
        if review.unresolved_risks:
            lines.extend(['', f"UNRESOLVED: {', '.join(review.unresolved_risks)}"])
        return '\n'.join(lines).strip()

    def _adjustment_feedback_key(self, *, category: str, title: str, metadata: dict[str, Any]) -> str:
        category_value = str(category or 'unknown').strip().lower()
        if category_value == 'inertial_route':
            assistant = str(metadata.get('assistant_kind') or '').strip().lower()
            route = str(metadata.get('route') or '').strip().lower()
            config = str(metadata.get('config_signature') or '').strip().lower()
            return f'{category_value}:{assistant}:{route}:{config}'
        if category_value == 'repeated_block':
            block = str(metadata.get('block') or title).strip().lower()
            return f'{category_value}:{block}'
        if category_value == 'recurring_failure':
            scope = str(metadata.get('scope') or title).strip().lower()
            return f'{category_value}:{scope}'
        if category_value == 'repeated_stall':
            pack_id = str(metadata.get('pack_id') or title).strip().lower()
            return f'{category_value}:{pack_id}'
        if category_value == 'weak_correction':
            scenario_id = str(metadata.get('scenario_id') or title).strip().lower()
            return f'{category_value}:{scenario_id}'
        return f'{category_value}:{str(title or "").strip().lower()}'

    def _matching_runs_for_adjustment(
        self,
        *,
        adjustment: dict[str, Any],
        experiment_runs: list[ExperimentRun],
    ) -> list[ExperimentRun]:
        category = str(adjustment.get('category') or '').strip().lower()
        metadata = dict(adjustment.get('metadata') or {})
        if category == 'inertial_route':
            route = str(metadata.get('route') or '').strip().lower()
            assistant = str(metadata.get('assistant_kind') or '').strip().lower()
            config = str(metadata.get('config_signature') or '').strip()
            return [
                run
                for run in experiment_runs
                if str(run.assistant_kind or '').strip().lower() == assistant
                and str(getattr(run.route, 'value', run.route) or '').strip().lower() == route
                and str(run.config_signature or '').strip() == config
            ]
        if category == 'repeated_block':
            block = str(metadata.get('block') or '').strip().lower()
            if not block:
                return []
            return [
                run
                for run in experiment_runs
                if any(block == str(item).strip().lower() for item in (dict(run.metadata or {}).get('external_state_flags') or []))
            ]
        if category == 'recurring_failure':
            scope = str(metadata.get('scope') or '').strip().lower()
            if not scope:
                return []
            return [run for run in experiment_runs if self._experiment_task_scope(run).lower() == scope]
        return []

    def _feedback_profile(self, runs: list[ExperimentRun]) -> dict[str, Any]:
        if not runs:
            return {
                'sample_count': 0,
                'success_rate': 0.0,
                'blocked_rate': 0.0,
                'fallback_rate': 0.0,
                'trend_score': 0.0,
            }
        if self.adaptive_weight_layer is not None and hasattr(self.adaptive_weight_layer, '_profile'):
            return dict(self.adaptive_weight_layer._profile(runs))
        sample_count = len(runs)
        success_rate = sum(1 for run in runs if run.success) / max(sample_count, 1)
        blocked_rate = sum(1 for run in runs if bool(dict(run.metadata or {}).get('blocked'))) / max(sample_count, 1)
        fallback_rate = sum(1 for run in runs if bool(dict(run.metadata or {}).get('fallback_used') or dict(run.metadata or {}).get('used_fallback'))) / max(sample_count, 1)
        return {
            'sample_count': sample_count,
            'success_rate': round(success_rate, 4),
            'blocked_rate': round(blocked_rate, 4),
            'fallback_rate': round(fallback_rate, 4),
            'trend_score': 0.0,
        }

    def _adjustment_has_validated_evidence(
        self,
        *,
        adjustment: dict[str, Any],
        validated_improvements: list[dict[str, Any]],
        validation: AutonomousValidationSnapshot,
    ) -> bool:
        category = str(adjustment.get('category') or '').strip().lower()
        metadata = dict(adjustment.get('metadata') or {})
        if category == 'inertial_route':
            target_key = self._adjustment_feedback_key(
                category='inertial_route',
                title=str(adjustment.get('title') or ''),
                metadata=metadata,
            )
            for item in validated_improvements:
                item_key = str(item.get('feedback_key') or '')
                if item_key and item_key == target_key:
                    return True
        assistant = str(metadata.get('assistant_kind') or '').strip().lower()
        route = str(metadata.get('route') or '').strip().lower()
        subject_key = str(metadata.get('subject_key') or '').strip().lower()
        text = ' '.join(
            str(part).strip().lower()
            for part in (
                validation.summary,
                *[item.get('title') for item in validated_improvements],
                *[item.get('summary') for item in validated_improvements],
            )
            if str(part or '').strip()
        )
        token_match = False
        if assistant and assistant in text:
            token_match = True
        if route and route in text:
            token_match = True
        if subject_key and subject_key in text:
            token_match = True
        return token_match and (
            int(validation.promoted_count or 0) > 0
            or any(float(item.get('confidence') or 0.0) >= 0.8 for item in validated_improvements)
        )

    def _experiment_task_scope(self, run: ExperimentRun) -> str:
        metadata = dict(run.metadata or {})
        subject_key = str(run.subject_key or '').strip()
        route = str(getattr(run.route, 'value', run.route) or '').strip()
        assistant = str(run.assistant_kind or '').strip().lower()
        if subject_key:
            return subject_key
        if assistant:
            return f'{assistant}:{route}'
        return route or 'general'

    def _task_scope(self, run: RunRecord) -> str:
        request = run.request
        route = run.route
        site = str(getattr(request, 'site_hint', '') or '').strip() or 'general'
        role = str(getattr(getattr(route, 'task_role', None), 'value', getattr(route, 'task_role', '')) or '').strip()
        if not role:
            role = str(getattr(getattr(run.result, 'detected_role', None), 'value', getattr(run.result, 'detected_role', '')) or '').strip()
        if not role:
            role = str(getattr(getattr(request, 'task_role', None), 'value', getattr(request, 'task_role', '')) or 'general')
        return f'{site}:{role}'

    def _severity_rank(self, severity: IssueSeverity | str) -> int:
        value = str(getattr(severity, 'value', severity) or '').strip().lower()
        order = {
            IssueSeverity.LOW.value: 1,
            IssueSeverity.MEDIUM.value: 2,
            IssueSeverity.HIGH.value: 3,
            IssueSeverity.CRITICAL.value: 4,
        }
        return order.get(value, 0)
