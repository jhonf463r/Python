from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
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
from iabv_v15.services.evolution.efficiency_audit_mixin import (
    tool_efficiency_findings,
    needs_custom_model_findings,
    account_exhaustion_findings,
    external_tool_misdiagnosis_findings,
    heuristic_perturbation_findings,
)


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
        account_ledger_service: Any | None = None,
        system_backlog_service: Any | None = None,
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
        self.account_ledger_service: Any | None = account_ledger_service
        self.system_backlog_service: Any | None = system_backlog_service
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
        findings.extend(tool_efficiency_findings(experiment_runs))
        findings.extend(needs_custom_model_findings(experiment_runs))
        findings.extend(account_exhaustion_findings(self.account_ledger_service))
        findings.extend(external_tool_misdiagnosis_findings(self.account_ledger_service))
        findings.extend(heuristic_perturbation_findings(
            experiment_runs,
            adaptive_weight_layer=self.adaptive_weight_layer,
        ))
        findings.extend(self._chat_research_backlog_findings())
        # Cognitive meta-patterns: fijación, incubación, atractores, ensambles
        findings.extend(
            self._cognitive_fixation_findings(
                experiment_runs=experiment_runs,
                recommendations=recommendations,
            )
        )
        findings.extend(self._cognitive_incubation_findings(experiment_runs=experiment_runs))
        findings.extend(self._neural_attractor_findings(experiment_runs=experiment_runs))
        findings.extend(self._neural_ensemble_findings(experiment_runs=experiment_runs))
        # Loop-closure introspection: the system checks its own mechanisms
        findings.extend(self._loop_closure_findings(
            findings_so_far=findings,
            experiment_runs=experiment_runs,
        ))
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
        solution_proposals = self._solution_proposals(
            findings=findings,
            recommendations=recommendations,
            experiment_runs=experiment_runs,
            validated_improvements=validated_improvements,
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
                'solution_proposals': solution_proposals[:4],
            },
        )
        review = self._persist_review(review)
        if self.system_backlog_service:
            try:
                finding_dicts = [
                    {
                        'category': f.category,
                        'title': f.title,
                        'summary': f.summary,
                        'severity': f.severity,
                        'recommendation': f.recommendation,
                    }
                    for f in review.findings
                ]
                self.system_backlog_service.ingest_from_findings(finding_dicts)
            except Exception:
                pass
        return review

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
            scope = str(
                metadata.get('scope')
                or metadata.get('pack_id')
                or metadata.get('block')
                or metadata.get('token_name')
                or ''
            ).strip()
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
                    f'Por el promedio observado ({pred.get("avg_interval_days") or 0:.1f} dias '
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

    def _chat_research_backlog_findings(self) -> list[SelfExaminationFinding]:
        """Consume ``data/chat_research_backlog/<session>.jsonl`` y produce
        hallazgos de ``research_gap`` por cada ``kind`` unico con entradas
        ``status='open'``.

        ``ChatCapabilityIngestionService`` (capa chat) persiste capacidades
        declaradas por el usuario (GPU, modelos locales, cuentas, runtimes)
        como tareas de investigacion pendientes. Sin este hook, el dato se
        escribia pero nadie lo consumia. OSES es el lugar natural para
        surfacearlo: las capacidades declaradas son gaps de investigacion
        reales hasta que se midan contra el StrategySelector / ExperimentLab.

        Agrupamos por ``kind`` para evitar ruido: si el usuario menciono
        "gpu" 10 veces en distintas sesiones, es un solo ``research_gap``,
        no diez. Solo se ignoran entradas con ``status`` distinto de
        ``'open'`` (ej: ya investigadas, archivadas). Si el directorio no
        existe o no hay entradas abiertas, devuelve lista vacia sin
        inventar observacion.
        """

        backlog_dir = Path(self.workspace_root) / 'data' / 'chat_research_backlog'
        if not backlog_dir.exists() or not backlog_dir.is_dir():
            return []

        try:
            files = sorted(backlog_dir.glob('*.jsonl'))
        except OSError:
            return []
        if not files:
            return []

        # Agrupacion por ``kind``: nos quedamos con la entrada mas reciente
        # por kind para tener la evidencia mas actual sin duplicar findings.
        per_kind: dict[str, dict[str, Any]] = {}
        per_kind_count: Counter[str] = Counter()
        per_kind_sessions: dict[str, set[str]] = defaultdict(set)
        for path in files:
            try:
                with path.open('r', encoding='utf-8') as handle:
                    for line in handle:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        try:
                            record = json.loads(stripped)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(record, dict):
                            continue
                        if str(record.get('status') or 'open') != 'open':
                            continue
                        kind = str(record.get('kind') or '').strip()
                        if not kind:
                            continue
                        per_kind_count[kind] += 1
                        session_id = str(record.get('session_id') or '').strip()
                        if session_id:
                            per_kind_sessions[kind].add(session_id)
                        existing = per_kind.get(kind)
                        if existing is None:
                            per_kind[kind] = record
                            continue
                        # Conservar la entrada con ``detected_at_utc`` mas
                        # reciente (comparacion lexicografica de ISO-8601 UTC
                        # es equivalente a temporal).
                        if str(record.get('detected_at_utc') or '') > str(existing.get('detected_at_utc') or ''):
                            per_kind[kind] = record
            except OSError:
                continue

        if not per_kind:
            return []

        findings: list[SelfExaminationFinding] = []
        for kind, entry in per_kind.items():
            label = str(entry.get('label') or kind).strip()
            hint = str(entry.get('research_hint') or '').strip()
            matched_text = str(entry.get('matched_text') or '').strip()
            occurrences = per_kind_count[kind]
            sessions = sorted(per_kind_sessions[kind])
            detected_at = str(entry.get('detected_at_utc') or '').strip()

            summary_parts = [
                f'El usuario declaro "{label}"'
                + (f' (detectado como "{matched_text}")' if matched_text else '')
                + ' en el chat, pero el sistema aun no valido su impacto.',
            ]
            if hint:
                summary_parts.append(f'Investigacion pendiente: {hint}')
            if occurrences > 1:
                summary_parts.append(
                    f'La mencion aparece {occurrences} veces en el backlog '
                    f'({len(sessions)} sesiones).'
                )
            summary = ' '.join(summary_parts)

            evidence_refs: list[str] = []
            if detected_at:
                evidence_refs.append(f'detected_at_utc={detected_at}')
            if sessions:
                evidence_refs.append('sessions=' + ','.join(sessions[:4]))

            findings.append(
                SelfExaminationFinding(
                    category='research_gap',
                    title=f'Capacidad declarada sin validar: {label}',
                    summary=summary,
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.6,
                    recommendation=hint or (
                        'Validar la capacidad declarada contra ExperimentLab / '
                        'StrategySelector y registrar resultado real.'
                    ),
                    evidence_refs=evidence_refs,
                    source_refs=['ChatCapabilityIngestionService', 'chat_research_backlog'],
                    metadata={
                        'kind': kind,
                        'label': label,
                        'matched_text': matched_text,
                        'occurrences': occurrences,
                        'sessions': sessions,
                        'latest_detected_at_utc': detected_at,
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
            count = int(issue.get('count') or 0)
            severity = IssueSeverity.HIGH if count >= 5 else IssueSeverity.MEDIUM if count >= 2 else IssueSeverity.LOW
            confidence = min(0.80, 0.30 + count * 0.07)
            items.append(
                {
                    'title': issue_hint,
                    'category': 'project_health_repeat',
                    'summary': (
                        f'El issue {issue_hint} reaparece {count} veces en la '
                        f'capa evolutiva. Requiere accion correctiva si persiste '
                        f'en corridas recientes.'
                    ),
                    'severity': severity.value,
                    'confidence': round(confidence, 2),
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
        seen_feedback_keys: set[str] = set()
        for recommendation in recommendations[:4]:
            if float(recommendation.confidence or 0.0) < 0.75 and float(recommendation.score or 0.0) < 0.75:
                continue
            adaptive = dict((recommendation.metadata or {}).get('adaptive_learning_summary') or {})
            feedback_key = self._adjustment_feedback_key(
                category='inertial_route',
                title=f'{recommendation.recommended_assistant_kind or "ruta"} por {recommendation.recommended_route.value}',
                metadata={
                    'assistant_kind': recommendation.recommended_assistant_kind,
                    'route': recommendation.recommended_route.value,
                    'config_signature': recommendation.recommended_config_signature,
                    'subject_key': recommendation.subject_key,
                },
            )
            if feedback_key in seen_feedback_keys:
                continue
            seen_feedback_keys.add(feedback_key)
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
                    'feedback_key': feedback_key,
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

    # ------------------------------------------------------------------
    # Cognitive meta-patterns
    # ------------------------------------------------------------------

    def _cognitive_fixation_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        recommendations: list[ExperimentRecommendation],
    ) -> list[SelfExaminationFinding]:
        """Detect cognitive fixation: the system choosing the same IA/route
        repeatedly despite availability of better alternatives.

        Cognitive fixation occurs when the orchestrator "locks on" to a
        familiar route even when evidence shows declining performance.
        This goes beyond route_inertia (which is about the decision log)
        by examining the actual experiment outcomes for persistent bias.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 5:
            return findings
        kind_counts: dict[str, int] = defaultdict(int)
        kind_recent_failures: dict[str, int] = defaultdict(int)
        recent_runs = experiment_runs[-10:]
        for run in recent_runs:
            kind = str(run.assistant_kind or '').strip().lower()
            if not kind:
                continue
            kind_counts[kind] += 1
            if not bool(run.success):
                kind_recent_failures[kind] += 1
        dominant_kind = max(kind_counts, key=kind_counts.get, default='')  # type: ignore[arg-type]
        if not dominant_kind:
            return findings
        dominant_ratio = kind_counts[dominant_kind] / len(recent_runs)
        dominant_failure_rate = kind_recent_failures.get(dominant_kind, 0) / max(kind_counts[dominant_kind], 1)
        better_alternatives = [
            rec for rec in recommendations
            if str(rec.recommended_assistant_kind or '').strip().lower() != dominant_kind
            and float(rec.confidence or 0.0) > 0.6
        ]
        if dominant_ratio >= 0.7 and dominant_failure_rate >= 0.4 and better_alternatives:
            findings.append(SelfExaminationFinding(
                title=f'Fijación cognitiva en {dominant_kind}',
                description=(
                    f'El sistema sigue eligiendo {dominant_kind} en {dominant_ratio:.0%} de los últimos runs '
                    f'a pesar de una tasa de fallo de {dominant_failure_rate:.0%}. '
                    f'Hay {len(better_alternatives)} alternativa(s) recomendada(s) con mayor confianza.'
                ),
                severity=IssueSeverity.HIGH,
                category='cognitive_fixation',
                metadata={
                    'dominant_kind': dominant_kind,
                    'dominant_ratio': round(dominant_ratio, 4),
                    'failure_rate': round(dominant_failure_rate, 4),
                    'alternative_count': len(better_alternatives),
                    'best_alternative': str(better_alternatives[0].recommended_assistant_kind or ''),
                },
            ))
        return findings

    def _cognitive_incubation_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect when cognitive incubation could help: problems that failed
        multiple times recently but might benefit from a "cooling period."

        Incubation is the cognitive phenomenon where stepping away from a
        problem allows subconscious processing to find a solution.  Here
        we detect subject_keys with 3+ consecutive failures and suggest
        deferring them to let the system gather new evidence or context.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 3:
            return findings
        subject_recent_failures: dict[str, int] = defaultdict(int)
        subject_total: dict[str, int] = defaultdict(int)
        for run in experiment_runs[-15:]:
            sk = str(run.subject_key or '').strip()
            if not sk:
                continue
            subject_total[sk] += 1
            if not bool(run.success):
                subject_recent_failures[sk] += 1
            else:
                subject_recent_failures[sk] = 0
        for sk, consecutive_fails in subject_recent_failures.items():
            if consecutive_fails >= 3 and subject_total.get(sk, 0) >= 3:
                findings.append(SelfExaminationFinding(
                    title=f'Incubación cognitiva sugerida para {sk}',
                    description=(
                        f'El problema {sk} acumula {consecutive_fails} fallos consecutivos recientes. '
                        f'Postergar este subject_key por 1-2 ciclos para acumular contexto o '
                        f'permitir que el AdaptiveWeightLayer recalcule con datos frescos.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    category='cognitive_incubation',
                    metadata={
                        'subject_key': sk,
                        'consecutive_failures': consecutive_fails,
                        'total_runs': subject_total.get(sk, 0),
                    },
                ))
        return findings[:2]

    def _neural_attractor_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect neural attractors: stable configurations the system
        converges toward naturally.

        An attractor is a (route, assistant_kind, config) combination
        that consistently produces good results.  Identifying attractors
        helps the system consciously reinforce what works instead of
        drifting.  If no attractor exists, that itself is a finding.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 4:
            return findings
        config_success: dict[str, list[float]] = defaultdict(list)
        config_total: dict[str, int] = defaultdict(int)
        for run in experiment_runs:
            kind = str(run.assistant_kind or '').strip().lower()
            route = str(run.route.value if run.route else '')
            if not kind:
                continue
            key = f'{kind}:{route}'
            config_total[key] += 1
            if bool(run.success):
                config_success[key].append(float(run.metrics.total_score or 0.0))
        attractors: list[tuple[str, float, int]] = []
        for key, scores in config_success.items():
            total = config_total.get(key, len(scores))
            if total < 3:
                continue
            success_rate = len(scores) / max(total, 1)
            avg_score = sum(scores) / max(len(scores), 1)
            if success_rate >= 0.75 and avg_score >= 0.5:
                attractors.append((key, avg_score, total))
        if attractors:
            attractors.sort(key=lambda t: (t[1], t[2]), reverse=True)
            best = attractors[0]
            findings.append(SelfExaminationFinding(
                title=f'Atractor neuronal identificado: {best[0]}',
                description=(
                    f'La configuración {best[0]} converge a resultados positivos consistentemente '
                    f'(score {best[1]:.2f}, {best[2]} runs). Este atractor debe ser reforzado '
                    f'como ruta preferente para tareas compatibles.'
                ),
                severity=IssueSeverity.LOW,
                category='neural_attractor',
                metadata={
                    'attractor_key': best[0],
                    'avg_score': round(best[1], 4),
                    'total_runs': best[2],
                    'all_attractors': [{'key': a[0], 'score': round(a[1], 4), 'runs': a[2]} for a in attractors[:3]],
                },
            ))
        elif len(experiment_runs) >= 8:
            findings.append(SelfExaminationFinding(
                title='Sin atractor neuronal estable',
                description=(
                    'No se detecta ninguna configuración (IA+ruta) que converja consistentemente '
                    'a resultados positivos. El sistema opera sin preferencia estable, lo que '
                    'puede indicar exploración excesiva o datos insuficientes.'
                ),
                severity=IssueSeverity.MEDIUM,
                category='neural_attractor',
                metadata={'experiment_count': len(experiment_runs)},
            ))
        return findings[:1]

    def _neural_ensemble_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect neural ensembles: groups of IAs that work well together.

        A neural ensemble is the activation of multiple "neurons" (services/IAs)
        working in concert.  Here we identify pairs of assistant_kinds that,
        when used on the same subject_key, produce consistently better
        outcomes than either alone.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 6:
            return findings
        subject_kind_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for run in experiment_runs:
            sk = str(run.subject_key or '').strip()
            kind = str(run.assistant_kind or '').strip().lower()
            if not sk or not kind:
                continue
            score = float(run.metrics.total_score or 0.0) if bool(run.success) else 0.0
            subject_kind_scores[sk][kind].append(score)
        ensembles: list[tuple[str, str, str, float]] = []
        for sk, kinds_map in subject_kind_scores.items():
            active_kinds = [k for k, scores in kinds_map.items() if len(scores) >= 2]
            if len(active_kinds) < 2:
                continue
            for i, k1 in enumerate(active_kinds):
                for k2 in active_kinds[i + 1:]:
                    avg1 = sum(kinds_map[k1]) / max(len(kinds_map[k1]), 1)
                    avg2 = sum(kinds_map[k2]) / max(len(kinds_map[k2]), 1)
                    combined = (avg1 + avg2) / 2
                    if combined > 0.4:
                        ensembles.append((sk, k1, k2, round(combined, 4)))
        if ensembles:
            ensembles.sort(key=lambda t: t[3], reverse=True)
            best = ensembles[0]
            findings.append(SelfExaminationFinding(
                title=f'Ensamble neuronal detectado: {best[1]} + {best[2]}',
                description=(
                    f'Para el problema {best[0]}, la combinación {best[1]} + {best[2]} '
                    f'produce un score combinado de {best[3]:.2f}. Este ensamble debe '
                    f'ser considerado para planes coordinados futuros en tareas similares.'
                ),
                severity=IssueSeverity.LOW,
                category='neural_ensemble',
                metadata={
                    'subject_key': best[0],
                    'ensemble_pair': [best[1], best[2]],
                    'combined_score': best[3],
                    'all_ensembles': [{'subject': e[0], 'pair': [e[1], e[2]], 'score': e[3]} for e in ensembles[:3]],
                },
            ))
        return findings[:1]

    # ------------------------------------------------------------------
    # Loop-closure introspection: the system audits its own mechanisms
    # ------------------------------------------------------------------

    def _loop_closure_findings(
        self,
        *,
        findings_so_far: list[SelfExaminationFinding],
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Introspect whether G1, G2, G3 and cognitive mechanisms are active.

        This is the system's self-awareness of its own architecture: it
        checks that the introspective loop is actually closed by verifying
        each mechanism is wired and producing output.  If a gap is detected,
        a finding with severity HIGH is emitted so the user (or the system
        itself) can act.
        """
        results: list[SelfExaminationFinding] = []
        checks: list[dict[str, Any]] = []

        # --- G1: auto-execution wire ---
        validation_cycle = self.autonomous_validation_cycle
        g1_wired = False
        g1_has_executed = False
        if validation_cycle is not None:
            orchestrator = getattr(validation_cycle, 'adaptive_task_orchestrator', None)
            g1_wired = orchestrator is not None
            executed_keys = getattr(validation_cycle, '_auto_executed_keys', None)
            if isinstance(executed_keys, set):
                g1_has_executed = len(executed_keys) > 0
        checks.append({
            'mechanism': 'G1_auto_execution',
            'wired': g1_wired,
            'active': g1_has_executed,
            'detail': 'orchestrator wired' if g1_wired else 'orchestrator NOT connected to validation_cycle',
        })

        # --- G2: validation feedback persistence ---
        feedback_path = Path(self.workspace_root) / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
        g2_file_exists = feedback_path.is_file()
        g2_entry_count = 0
        if g2_file_exists:
            try:
                g2_entry_count = sum(1 for line in feedback_path.read_text(encoding='utf-8').splitlines() if line.strip())
            except Exception:
                pass
        checks.append({
            'mechanism': 'G2_feedback_persistence',
            'wired': True,
            'active': g2_file_exists and g2_entry_count > 0,
            'detail': f'{g2_entry_count} entries' if g2_file_exists else 'history.jsonl not yet created (fires after first validation)',
        })

        # --- G3: AdaptiveWeightLayer connected ---
        g3_wired = self.adaptive_weight_layer is not None
        g3_has_suggest = g3_wired and callable(getattr(self.adaptive_weight_layer, 'suggest', None))
        checks.append({
            'mechanism': 'G3_weight_layer',
            'wired': g3_wired,
            'active': g3_has_suggest,
            'detail': 'suggest() available' if g3_has_suggest else ('layer connected but no suggest()' if g3_wired else 'AdaptiveWeightLayer NOT connected'),
        })

        # --- Cognitive mechanisms: check if findings were generated ---
        cognitive_categories = {'cognitive_fixation', 'cognitive_incubation', 'neural_attractor', 'neural_ensemble'}
        found_categories = {f.category for f in findings_so_far if f.category in cognitive_categories}
        checks.append({
            'mechanism': 'cognitive_findings',
            'wired': True,
            'active': len(found_categories) > 0,
            'detail': f'active categories: {sorted(found_categories)}' if found_categories else f'none active (need >= 5 experiment runs, have {len(experiment_runs)})',
        })

        # --- Summary ---
        wired_count = sum(1 for c in checks if c['wired'])
        active_count = sum(1 for c in checks if c['active'])
        total = len(checks)
        all_wired = wired_count == total
        all_active = active_count == total

        if all_wired and all_active:
            results.append(SelfExaminationFinding(
                title='Loop introspectivo cerrado: todos los mecanismos activos',
                description=(
                    f'G1 (auto-ejecución), G2 (feedback persistence), G3 (weight layer) y '
                    f'mecanismos cognitivos están wired y produciendo output. '
                    f'El sistema se auto-observa y actúa sin intervención manual.'
                ),
                severity=IssueSeverity.LOW,
                category='loop_closure',
                metadata={
                    'checks': checks,
                    'wired': wired_count,
                    'active': active_count,
                    'total': total,
                    'closed': True,
                },
            ))
        else:
            gaps = [c for c in checks if not c['wired'] or not c['active']]
            gap_names = [c['mechanism'] for c in gaps]
            results.append(SelfExaminationFinding(
                title=f'Loop introspectivo abierto: {len(gaps)} mecanismo(s) inactivo(s)',
                description=(
                    f'Mecanismos con gaps: {", ".join(gap_names)}. '
                    f'{wired_count}/{total} wired, {active_count}/{total} activos. '
                    + '; '.join(f"{c['mechanism']}: {c['detail']}" for c in gaps)
                ),
                severity=IssueSeverity.HIGH if not all_wired else IssueSeverity.MEDIUM,
                category='loop_closure',
                metadata={
                    'checks': checks,
                    'wired': wired_count,
                    'active': active_count,
                    'total': total,
                    'closed': False,
                    'gap_mechanisms': gap_names,
                },
            ))

        return results[:1]

    # ------------------------------------------------------------------
    # G2: Leer feedback de validación para filtrar propuestas ya intentadas
    # ------------------------------------------------------------------

    def _load_tried_proposal_keys(self) -> set[str]:
        """G2: Load proposal keys that have already been validated.

        Reads the JSONL file written by ``AutonomousValidationCycleService._persist_validation_feedback``
        and returns a set of synthetic keys for proposals that were
        ``discarded`` or ``unresolved`` — so ``_solution_proposals`` avoids
        re-proposing the same strategy.  Proposals that were ``promoted``
        are NOT filtered (they succeeded and may be proposed again for
        different contexts).
        """
        tried: set[str] = set()
        try:
            feedback_path = Path(self.workspace_root) / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
            if not feedback_path.is_file():
                return tried
            for line in feedback_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                decision = str(entry.get('decision') or '')
                if decision not in {'discarded', 'unresolved'}:
                    continue
                kind = str(entry.get('proposal_kind') or entry.get('proposal_key') or '').strip()
                candidate = str(entry.get('candidate_assistant_kind') or '').strip().lower()
                current = str(entry.get('current_assistant_kind') or '').strip().lower()
                if kind and candidate and current:
                    tried.add(f'route_substitution:{current}:{candidate}')
                if kind and candidate and current:
                    tried.add(f'collaborative_execution:{candidate}:{current}')
                    tried.add(f'collaborative_execution:{current}:{candidate}')
                    tried.add(f'validated_collaboration:{candidate}:{current}')
                    tried.add(f'validated_collaboration:{current}:{candidate}')
        except Exception:
            pass
        return tried

    # ------------------------------------------------------------------
    # P3: Propuestas proactivas de solución
    # ------------------------------------------------------------------

    def _solution_proposals(
        self,
        *,
        findings: list[SelfExaminationFinding],
        recommendations: list[ExperimentRecommendation],
        experiment_runs: list[ExperimentRun],
        validated_improvements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate actionable solution proposals from findings and evidence.

        When self-examination detects recurring patterns (failures, blocks,
        inertia), this method converts them into concrete proposals that
        specify which IAs should handle which aspects and with what
        estimated confidence.  Proposals are purely descriptive — the
        orchestrator or UI decides whether to act on them.

        G2: reads validation feedback to filter out proposals already tried.
        G3: uses ``AdaptiveWeightLayer.suggest()`` for weighted profiles
        when available, instead of computing crude averages.
        """
        proposals: list[dict[str, Any]] = []

        # G2: load validation feedback to skip already-tried proposals
        tried_keys = self._load_tried_proposal_keys()

        # G3: use AdaptiveWeightLayer for weighted profiles when available
        kind_success: dict[str, list[float]] = defaultdict(list)
        kind_failures: dict[str, int] = defaultdict(int)
        kind_weighted_scores: dict[str, float] = {}

        if self.adaptive_weight_layer is not None and experiment_runs:
            grouped: dict[tuple[object, str, str], list[ExperimentRun]] = defaultdict(list)
            for run in experiment_runs:
                kind = str(run.assistant_kind or '').strip().lower()
                if not kind:
                    continue
                key = (run.route, kind, str(run.config_signature or ''))
                grouped[key].append(run)
                if bool(run.success):
                    kind_success[kind].append(float(run.metrics.total_score or 0.0))
                else:
                    kind_failures[kind] += 1
            profiles = self.adaptive_weight_layer.suggest(grouped_runs=grouped)
            for key, profile in profiles.items():
                kind = str(key[1]).strip().lower()
                if kind and kind not in kind_weighted_scores:
                    kind_weighted_scores[kind] = float(profile.get('weighted_score') or 0.0)
        else:
            for run in experiment_runs:
                kind = str(run.assistant_kind or '').strip().lower()
                if not kind:
                    continue
                if bool(run.success):
                    kind_success[kind].append(float(run.metrics.total_score or 0.0))
                else:
                    kind_failures[kind] += 1

        def _kind_score(kind: str) -> float:
            """G3: prefer weighted score from AdaptiveWeightLayer."""
            if kind in kind_weighted_scores:
                return kind_weighted_scores[kind]
            scores = kind_success.get(kind, [])
            return sum(scores) / max(len(scores), 1) if scores else 0.0

        recurring_failure_kinds: set[str] = set()
        for finding in findings:
            if finding.severity in {IssueSeverity.HIGH, IssueSeverity.MEDIUM}:
                metadata = dict(finding.metadata or {})
                kind = str(metadata.get('assistant_kind') or '').strip().lower()
                if kind and kind_failures.get(kind, 0) >= 2:
                    recurring_failure_kinds.add(kind)

        for failing_kind in recurring_failure_kinds:
            fail_count = kind_failures.get(failing_kind, 0)
            alternatives = sorted(
                (
                    (k, _kind_score(k), len(scores))
                    for k, scores in kind_success.items()
                    if k != failing_kind and len(scores) >= 2
                ),
                key=lambda t: (t[1], t[2]),
                reverse=True,
            )
            if not alternatives:
                continue
            best_alt, best_score, best_count = alternatives[0]
            proposal_key = f'route_substitution:{failing_kind}:{best_alt}'
            # G2: skip proposals already tried and discarded
            if proposal_key in tried_keys:
                continue
            proposals.append({
                'type': 'route_substitution',
                'title': f'Sustituir {failing_kind} por {best_alt} en tareas con fallos recurrentes',
                'description': (
                    f'{failing_kind} tiene {fail_count} fallos recientes. '
                    f'{best_alt} tiene score {"ponderado" if best_alt in kind_weighted_scores else "promedio"} {best_score:.2f} con {best_count} éxitos.'
                ),
                'action_plan': [
                    {'step': 1, 'ia': best_alt, 'action': 'Asumir tareas que fallaban con ' + failing_kind},
                    {'step': 2, 'ia': failing_kind, 'action': 'Reducir prioridad hasta evidencia de mejora'},
                ],
                'estimated_confidence': round(min(1.0, 0.5 + best_score * 0.3), 4),
                'evidence_refs': [f'failures:{failing_kind}:{fail_count}', f'success:{best_alt}:{best_count}'],
            })

        if len(kind_success) >= 2:
            sorted_kinds = sorted(
                ((k, _kind_score(k), len(v)) for k, v in kind_success.items() if len(v) >= 2),
                key=lambda t: (t[1], t[2]),
                reverse=True,
            )
            if len(sorted_kinds) >= 2:
                primary_kind, primary_score, primary_runs = sorted_kinds[0]
                secondary_kind, secondary_score, secondary_runs = sorted_kinds[1]
                collab_key = f'collaborative_execution:{primary_kind}:{secondary_kind}'
                if primary_score > 0.3 and secondary_score > 0.3 and collab_key not in tried_keys:
                    proposals.append({
                        'type': 'collaborative_execution',
                        'title': f'Plan coordinado: {primary_kind} + {secondary_kind}',
                        'description': (
                            f'{primary_kind} (score {"ponderado" if primary_kind in kind_weighted_scores else "promedio"} {primary_score:.2f}, {primary_runs} éxitos) '
                            f'y {secondary_kind} (score {"ponderado" if secondary_kind in kind_weighted_scores else "promedio"} {secondary_score:.2f}, {secondary_runs} éxitos) '
                            f'pueden trabajar en conjunto: uno investiga, el otro implementa.'
                        ),
                        'action_plan': [
                            {'step': 1, 'ia': primary_kind, 'action': 'Investigar y proponer solución'},
                            {'step': 2, 'ia': secondary_kind, 'action': 'Validar y complementar propuesta'},
                            {'step': 3, 'ia': 'orchestrator', 'action': 'Consolidar y ejecutar plan final'},
                        ],
                        'estimated_confidence': round(
                            min(1.0, 0.4 + primary_score * 0.2 + secondary_score * 0.2 + min(primary_runs, secondary_runs) * 0.02),
                            4,
                        ),
                        'evidence_refs': [f'success:{primary_kind}:{primary_runs}', f'success:{secondary_kind}:{secondary_runs}'],
                    })

        for improvement in validated_improvements[:2]:
            rec_kind = str(improvement.get('recommended_assistant_kind') or '').strip().lower()
            rec_confidence = float(improvement.get('confidence') or 0.0)
            if rec_kind and rec_confidence >= 0.75:
                complementary = [
                    k for k, scores in kind_success.items()
                    if k != rec_kind and len(scores) >= 2 and _kind_score(k) > 0.4
                ]
                if complementary:
                    vc_key = f'validated_collaboration:{rec_kind}:{complementary[0]}'
                    if vc_key not in tried_keys:
                        proposals.append({
                            'type': 'validated_collaboration',
                            'title': f'Extender éxito validado de {rec_kind} con {complementary[0]}',
                            'description': (
                                f'{rec_kind} fue validado con confianza {rec_confidence:.2f}. '
                                f'Combinar con {complementary[0]} para cubrir aspectos complementarios.'
                            ),
                            'action_plan': [
                                {'step': 1, 'ia': rec_kind, 'action': str(improvement.get('summary') or 'Aplicar mejora validada')},
                                {'step': 2, 'ia': complementary[0], 'action': 'Complementar con fortalezas propias'},
                            ],
                            'estimated_confidence': round(min(1.0, rec_confidence * 0.8 + 0.15), 4),
                            'evidence_refs': list(improvement.get('evidence_refs') or [])[:4],
                        })

        return proposals[:4]

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
        if category_value == 'token_rotation':
            # ``title`` incluye dias proyectados (``(3.0d)``) que cambian en
            # cada review. ``token_name`` es estable y esta en metadata de
            # expired/proactive/stale por igual.
            token_name = str(metadata.get('token_name') or title).strip().lower()
            return f'{category_value}:{token_name}'
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
