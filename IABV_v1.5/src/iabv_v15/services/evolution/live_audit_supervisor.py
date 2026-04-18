from __future__ import annotations

from statistics import mean
from typing import Any

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentCandidate,
    ExperimentDomain,
    InteractionEpisode,
    LiveAuditDecision,
    LiveAuditFinding,
    LiveAuditSnapshot,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
)
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.lab.experiment_lab import ExperimentLab


class LiveAuditSupervisor:
    def __init__(
        self,
        *,
        tool_record_repository: ToolRecordRepository | None = None,
        experiment_lab: ExperimentLab | None = None,
    ) -> None:
        self.tool_record_repository = tool_record_repository
        self.experiment_lab = experiment_lab

    def audit_tool_result(self, *, card: ToolCard | None, task: ToolTask, result: ToolResult) -> ToolResult:
        snapshot = self._tool_snapshot(card=card, task=task, result=result)
        updated_state = result.execution_state.model_copy(
            update={
                'metadata': {
                    **dict(result.execution_state.metadata or {}),
                    'audit_reason': snapshot.decision.rationale if snapshot.decision is not None else '',
                    'audit_snapshot_id': snapshot.audit_snapshot_id,
                }
            }
        )
        updated_result = result.model_copy(
            update={
                'execution_state': updated_state,
                'metadata': {
                    **dict(result.metadata or {}),
                    'live_audit': snapshot.model_dump(mode='json'),
                    'audit_snapshot_id': snapshot.audit_snapshot_id,
                    'audit_decision': snapshot.decision.action if snapshot.decision is not None else '',
                    'audit_recommendation': snapshot.decision.action if snapshot.decision is not None else '',
                    'audit_summary': self.summarize_snapshot(snapshot),
                },
            }
        )
        self._attach_snapshot_to_episode(updated_result, snapshot)
        return updated_result

    def audit_teaching_session(
        self,
        *,
        site_id: str,
        display_name: str,
        learning_packet: dict[str, Any],
        interaction_episode: InteractionEpisode | None,
        incidents: list[dict[str, Any]] | None = None,
    ) -> tuple[InteractionEpisode | None, dict[str, Any], LiveAuditSnapshot | None]:
        packet = dict(learning_packet or {})
        if interaction_episode is None:
            return None, packet, None
        snapshot = self._teaching_snapshot(
            site_id=site_id,
            display_name=display_name,
            learning_packet=packet,
            interaction_episode=interaction_episode,
            incidents=incidents or [],
        )
        result = interaction_episode.result
        if result is not None:
            result = result.model_copy(
                update={
                    'execution_state': result.execution_state.model_copy(
                        update={
                            'metadata': {
                                **dict(result.execution_state.metadata or {}),
                                'audit_reason': snapshot.decision.rationale if snapshot.decision is not None else '',
                                'audit_snapshot_id': snapshot.audit_snapshot_id,
                            }
                        }
                    ),
                    'metadata': {
                        **dict(result.metadata or {}),
                        'live_audit': snapshot.model_dump(mode='json'),
                        'audit_snapshot_id': snapshot.audit_snapshot_id,
                        'audit_decision': snapshot.decision.action if snapshot.decision is not None else '',
                    },
                }
            )
        updated_episode = interaction_episode.model_copy(
            update={
                'result': result,
                'metadata': {
                    **dict(interaction_episode.metadata or {}),
                    'live_audit': snapshot.model_dump(mode='json'),
                    'audit_snapshot_id': snapshot.audit_snapshot_id,
                    'audit_summary': self.summarize_snapshot(snapshot),
                },
            }
        )
        self._save_episode(updated_episode)
        metadata = dict(packet.get('metadata') or {})
        metadata.update(
            {
                'live_audit': snapshot.model_dump(mode='json'),
                'audit_snapshot_id': snapshot.audit_snapshot_id,
                'audit_decision': snapshot.decision.action if snapshot.decision is not None else '',
                'audit_summary': self.summarize_snapshot(snapshot),
            }
        )
        packet['metadata'] = metadata
        packet['live_audit'] = snapshot.model_dump(mode='json')
        packet['audit_snapshot_id'] = snapshot.audit_snapshot_id
        packet['audit_decision'] = snapshot.decision.action if snapshot.decision is not None else ''
        packet['audit_findings'] = [item.kind for item in snapshot.findings]
        return updated_episode, packet, snapshot

    def latest_summary(self, *, site_id: str | None = None, tool_id: str | None = None, user_goal: str = '') -> dict[str, Any]:
        if self.tool_record_repository is None:
            return {}
        try:
            episodes = self.tool_record_repository.list_interaction_episodes(site_id=site_id, tool_id=tool_id, limit=20)
        except TypeError:
            episodes = self.tool_record_repository.list_interaction_episodes(site_id=site_id, limit=20) if site_id else self.tool_record_repository.list_interaction_episodes(limit=20)
        goal_tokens = {token for token in (user_goal or '').lower().split() if len(token) >= 3}
        for episode in episodes:
            audit = dict(episode.metadata.get('live_audit') or {})
            if not audit:
                continue
            objective = str(episode.objective or '').lower()
            if goal_tokens and not goal_tokens.intersection(set(objective.split())) and len(goal_tokens) <= 4:
                pass
            findings = [str(item.get('kind') or '') for item in audit.get('findings') or [] if isinstance(item, dict)]
            decision = dict(audit.get('decision') or {})
            return {
                'audit_snapshot_id': audit.get('audit_snapshot_id') or '',
                'summary': self._summary_from_snapshot(audit),
                'decision_action': str(decision.get('action') or ''),
                'recommended_action': str(decision.get('action') or ''),
                'recommended_tool_id': str(decision.get('recommended_tool_id') or ''),
                'confidence': float(audit.get('confidence') or 0.0),
                'findings': findings,
                'metrics': dict(audit.get('metrics') or {}),
                'episode_id': episode.interaction_episode_id,
            }
        return {}

    def summarize_snapshot(self, snapshot: LiveAuditSnapshot) -> str:
        decision = snapshot.decision.action if snapshot.decision is not None else 'continue_local'
        lead = snapshot.findings[0].title if snapshot.findings else 'Sin hallazgos relevantes.'
        return f'{lead} Decision: {decision}. Confianza {snapshot.confidence:.2f}.'

    def _tool_snapshot(self, *, card: ToolCard | None, task: ToolTask, result: ToolResult) -> LiveAuditSnapshot:
        evidence = self._tool_evidence(task=task, result=result)
        findings: list[LiveAuditFinding] = []
        state = str(result.execution_state.state or '')
        selection = dict(task.metadata.get('mode_selection') or {})
        goal_metadata = self._goal_progress_metadata(task.metadata)
        external_state_flags = [
            str(item).strip().lower()
            for item in (
                list(result.metadata.get('external_state_flags') or [])
                + list(result.execution_state.metadata.get('external_state_flags') or [])
            )
            if str(item).strip()
        ]
        external_blocked = any(
            flag in {'account_limited', 'session_expired', 'assistant_login_required', 'wrong_thread', 'capture_unverified'}
            for flag in external_state_flags
        )
        if state in {'missing_tool', 'adapter_missing'}:
            findings.append(
                LiveAuditFinding(
                    kind='tool_adapter_missing',
                    title='Falta adaptador operativo',
                    summary=result.execution_state.detail or 'La herramienta existe pero no tiene adaptador utilizable.',
                    confidence=0.93,
                    evidence_refs=evidence,
                    metadata={'state': state, 'tool_id': card.tool_id if card is not None else task.tool_id},
                )
            )
        if selection.get('selected_tool_id') and selection.get('selected_tool_id') != (card.tool_id if card is not None else task.tool_id):
            findings.append(
                LiveAuditFinding(
                    kind='route_mismatch',
                    title='La ruta elegida no coincide con la herramienta sugerida',
                    summary='El selector termino resolviendo otra herramienta o via para completar la tarea.',
                    confidence=0.68,
                    evidence_refs=evidence,
                )
            )
        execution_metadata = dict(result.execution_state.metadata or {})
        cross_check_summary = dict(execution_metadata.get('cross_check_summary') or result.metadata.get('cross_check_summary') or {})
        if str(execution_metadata.get('simulation_mode') or '').strip().lower() == 'simulated':
            findings.append(
                LiveAuditFinding(
                    kind='execution_simulated',
                    title='La ejecucion humana quedo en modo simulado',
                    summary='El runner no pudo confirmar interaccion real con el entorno y marco la evidencia como simulada.',
                    confidence=0.88,
                    evidence_refs=evidence,
                )
            )
        if cross_check_summary and float(cross_check_summary.get('observer_agreement_score', 0.0) or 0.0) < 0.55:
            findings.append(
                LiveAuditFinding(
                    kind='visual_semantic_mismatch',
                    title='La ejecucion visual no coincide del todo con lo esperado',
                    summary='Los objetos detectados y el gesto humano no quedaron suficientemente alineados.',
                    confidence=0.78,
                    evidence_refs=evidence,
                    metadata=cross_check_summary,
                )
            )
        if external_blocked:
            findings.append(
                LiveAuditFinding(
                    kind='external_route_blocked',
                    title='La via externa quedo bloqueada o sin captura verificable',
                    summary='La consulta externa no devolvio una respuesta confiable y el bloqueo debe tratarse como limitacion real, no como progreso valido.',
                    confidence=0.9,
                    evidence_refs=evidence,
                    metadata={'external_state_flags': external_state_flags},
                )
            )
        if selection.get('equivalent_pattern_exists') or selection.get('already_resolved'):
            findings.append(
                LiveAuditFinding(
                    kind='equivalent_pattern_exists',
                    title='Ya existe un patron equivalente',
                    summary='La tarea ya tenia memoria reutilizable y no deberia reensenarse desde cero.',
                    confidence=0.84,
                    evidence_refs=evidence,
                )
            )
        if (goal_metadata['status'] == 'completed' or goal_metadata['progress'] >= 0.8) and not result.success:
            findings.append(
                LiveAuditFinding(
                    kind='goal_progress_conflict',
                    title='El progreso declarado del objetivo no coincide con el resultado real',
                    summary='La meta figura muy avanzada o completada, pero la ejecucion actual fallo o no valido el resultado.',
                    confidence=0.79,
                    evidence_refs=evidence,
                    metadata=goal_metadata,
                )
            )
        if state == 'waiting_approval':
            decision = LiveAuditDecision(
                action='stop_and_wait_user',
                rationale='La sandbox fue valida, pero se requiere aprobacion humana antes de salir del modo seguro.',
                confidence=0.92,
                recommended_tool_id=card.tool_id if card is not None else task.tool_id,
                approval_required=True,
            )
        elif state == 'simulated':
            decision = LiveAuditDecision(
                action='stop_and_wait_user',
                rationale='La ejecucion quedo en modo simulado y conviene confirmar permisos o entorno antes de confiar en el resultado.',
                confidence=0.86,
                recommended_tool_id=card.tool_id if card is not None else task.tool_id,
                approval_required=True,
            )
        elif state in {'missing_tool', 'adapter_missing'}:
            assistant = self._consultant_for(task=task, result=result)
            action = 'consult_codex' if assistant == 'codex_installed' else 'consult_chatgpt'
            decision = LiveAuditDecision(
                action=action,
                rationale='Falta una via operativa local y conviene escalar con el asistente externo mas util para el tipo de fallo.',
                confidence=0.82,
                recommended_tool_id=assistant,
                approval_required=True,
            )
        elif external_blocked:
            decision = LiveAuditDecision(
                action='continue_local',
                rationale='La via externa quedo bloqueada o sin captura verificable; conviene seguir localmente mientras el bloqueo queda trazado.',
                confidence=0.82,
                recommended_tool_id=card.tool_id if card is not None else task.tool_id,
                approval_required=False,
            )
        else:
            decision = LiveAuditDecision(
                action='continue_local',
                rationale='La herramienta produjo evidencia suficiente para seguir en la via local actual.',
                confidence=0.7 if result.success else 0.55,
                recommended_tool_id=card.tool_id if card is not None else task.tool_id,
                approval_required=bool(task.metadata.get('approval_required')),
            )
        metrics = self._tool_metrics(task=task, result=result, card=card, evidence=evidence)
        confidence = max(float(result.metadata.get('interaction_confidence') or 0.0), float(metrics.get('observer_agreement_score', 0.0) or 0.0), 0.35)
        return LiveAuditSnapshot(
            objective=task.objective,
            session_or_episode_id=str(result.metadata.get('interaction_episode_id') or task.task_id),
            mode_used=str(task.metadata.get('selected_mode') or selection.get('selected_mode') or ''),
            evidence=evidence,
            findings=findings,
            decision=decision,
            confidence=round(min(0.98, confidence), 2),
            auto_safe_action='run_safe_tool_sandbox' if result.execution_state.sandboxed else '',
            human_approval=task.approval_decision.value == 'approved' or bool(task.metadata.get('approval_required')),
            reused_pattern=bool(selection.get('equivalent_pattern_exists') or selection.get('already_resolved')),
            metrics=metrics,
            metadata={
                'mirror_mode': 'tool_execution',
                'tool_id': card.tool_id if card is not None else task.tool_id,
                'tool_type': (card.tool_type.value if card is not None else result.tool_type.value),
                'selector_name': str(selection.get('selector_name') or 'universal_mode_selector'),
                'goal_context': goal_metadata,
            },
        )

    def _teaching_snapshot(
        self,
        *,
        site_id: str,
        display_name: str,
        learning_packet: dict[str, Any],
        interaction_episode: InteractionEpisode,
        incidents: list[dict[str, Any]],
    ) -> LiveAuditSnapshot:
        capture_stats = dict(learning_packet.get('capture_stats') or {})
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        readiness = dict(learning_packet.get('learning_readiness') or {})
        login_learning = dict(learning_packet.get('login_learning') or {})
        evidence = self._teaching_evidence(learning_packet=learning_packet, interaction_episode=interaction_episode)
        goal_metadata = self._goal_progress_metadata(interaction_episode.metadata)
        metrics = self._teaching_metrics(
            learning_packet=learning_packet,
            visual_summary=visual_summary,
            readiness=readiness,
            login_learning=login_learning,
            interaction_episode=interaction_episode,
        )
        findings: list[LiveAuditFinding] = []
        incident_kinds = {str(item.get('incident_kind') or '') for item in incidents}
        if 'bridge_lag' in incident_kinds or metrics['bridge_drain_health'] < 0.45:
            findings.append(
                LiveAuditFinding(
                    kind='bridge_lag',
                    title='El bridge visible no consolido a tiempo la captura',
                    summary='La ensenanza guardo evidencia tecnica, pero el drenado del bridge siguio debil y afecto la interpretacion reutilizable.',
                    confidence=0.9,
                    evidence_refs=evidence,
                    metadata={'queue_depth': capture_stats.get('queue_depth', 0), 'heartbeat_count': capture_stats.get('heartbeat_count', 0)},
                )
            )
        if metrics['semantic_action_alignment'] < 0.45 or metrics['target_element_alignment'] < 0.4:
            findings.append(
                LiveAuditFinding(
                    kind='visual_semantic_mismatch',
                    title='La semantica del flujo no coincide del todo con la evidencia visual',
                    summary='Los pasos observados y los objetos criticos todavia no cuentan una historia suficientemente consistente.',
                    confidence=0.76,
                    evidence_refs=evidence,
                )
            )
        if metrics['learning_consolidation_score'] < 0.55:
            findings.append(
                LiveAuditFinding(
                    kind='learning_not_consolidated',
                    title='La ensenanza existe pero todavia no consolida aprendizaje reutilizable',
                    summary='El replay y el bundle aportan algo de evidencia, pero el readiness y la confianza siguen debiles para reutilizar el login con seguridad.',
                    confidence=0.88,
                    evidence_refs=evidence,
                    metadata={'learning_status': readiness.get('status', ''), 'login_status': login_learning.get('status', '')},
                )
            )
        if interaction_episode.reused_pattern:
            findings.append(
                LiveAuditFinding(
                    kind='equivalent_pattern_exists',
                    title='Ya existe un patron equivalente para este sitio',
                    summary='La ensenanza se superpone con un patron ya observado y debe reusarse antes de abrir otra ensenanza similar.',
                    confidence=0.72,
                    evidence_refs=evidence,
                )
            )
        if (goal_metadata['status'] == 'completed' or goal_metadata['progress'] >= 0.8) and any(item.kind in {'bridge_lag', 'learning_not_consolidated', 'visual_semantic_mismatch'} for item in findings):
            findings.append(
                LiveAuditFinding(
                    kind='goal_progress_conflict',
                    title='El progreso del objetivo no coincide con la coherencia observada',
                    summary='La meta parece demasiado avanzada para el estado real de la ensenanza y su auditoria.',
                    confidence=0.74,
                    evidence_refs=evidence,
                    metadata=goal_metadata,
                )
            )
        if any(item.kind == 'bridge_lag' for item in findings):
            decision = LiveAuditDecision(
                action='consult_codex',
                rationale='El problema dominante parece de bridge, captura o consolidacion del replay, asi que conviene priorizar una revision tecnica.',
                confidence=0.86,
                recommended_tool_id='codex_installed',
                approval_required=True,
            )
        elif any(item.kind == 'learning_not_consolidated' for item in findings):
            decision = LiveAuditDecision(
                action='retry_after_rebuild',
                rationale='La ensenanza ya existe; primero conviene reconstruir bundle, episodio y readiness antes de volver a ensenar desde cero.',
                confidence=0.78,
                recommended_tool_id='playwright_browser',
                approval_required=False,
            )
        elif not interaction_episode.actions:
            decision = LiveAuditDecision(
                action='open_teaching',
                rationale='No hay suficientes acciones relevantes para consolidar el flujo actual.',
                confidence=0.8,
                recommended_tool_id='playwright_browser',
                approval_required=False,
            )
        else:
            decision = LiveAuditDecision(
                action='continue_local',
                rationale='La ensenanza tiene suficiente coherencia para seguir por la via local y reutilizar el patron observado.',
                confidence=0.7,
                recommended_tool_id='playwright_browser',
                approval_required=False,
            )
        return LiveAuditSnapshot(
            objective=interaction_episode.objective,
            session_or_episode_id=interaction_episode.interaction_episode_id,
            mode_used=interaction_episode.mode_used.value,
            evidence=evidence,
            findings=findings,
            decision=decision,
            confidence=round(min(0.98, max(interaction_episode.confidence, metrics['observer_agreement_score'], metrics['learning_consolidation_score'])), 2),
            auto_safe_action='retry_after_rebuild' if decision.action == 'retry_after_rebuild' else '',
            human_approval=False,
            reused_pattern=interaction_episode.reused_pattern,
            metrics=metrics,
            metadata={
                'mirror_mode': 'teaching_session',
                'site_id': site_id,
                'display_name': display_name,
                'replay_status': str(capture_stats.get('status') or ''),
                'unresolved': not bool(learning_packet.get('ocr_observed') or visual_summary.get('critical_objects')),
                'goal_context': goal_metadata,
            },
        )

    def _attach_snapshot_to_episode(self, result: ToolResult, snapshot: LiveAuditSnapshot) -> None:
        if self.tool_record_repository is None:
            return
        episode_id = str(result.metadata.get('interaction_episode_id') or '').strip()
        if not episode_id:
            return
        episode = self.tool_record_repository.get_interaction_episode(episode_id)
        if episode is None:
            return
        updated = episode.model_copy(
            update={
                'metadata': {
                    **dict(episode.metadata or {}),
                    'live_audit': snapshot.model_dump(mode='json'),
                    'audit_snapshot_id': snapshot.audit_snapshot_id,
                    'audit_summary': self.summarize_snapshot(snapshot),
                },
            }
        )
        if updated.result is not None:
            updated = updated.model_copy(
                update={
                    'result': updated.result.model_copy(
                        update={
                            'metadata': {
                                **dict(updated.result.metadata or {}),
                                'live_audit': snapshot.model_dump(mode='json'),
                                'audit_snapshot_id': snapshot.audit_snapshot_id,
                            }
                        }
                    )
                }
            )
        self._save_episode(updated)

    def _save_episode(self, episode: InteractionEpisode) -> None:
        if self.tool_record_repository is not None:
            self.tool_record_repository.save_interaction_episode(episode)

    def _tool_evidence(self, *, task: ToolTask, result: ToolResult) -> list[str]:
        evidence = [str(item) for item in result.artifacts if item]
        for key in ('interaction_pattern_id', 'interaction_episode_id', 'audit_snapshot_id'):
            value = str(result.metadata.get(key) or '').strip()
            if value:
                evidence.append(value)
        if task.site_id:
            evidence.append(f'site:{task.site_id}')
        return evidence[:12]

    def _teaching_evidence(self, *, learning_packet: dict[str, Any], interaction_episode: InteractionEpisode) -> list[str]:
        evidence = []
        for key in ('bundle_id', 'interaction_pattern_id', 'interaction_episode_id'):
            value = str(learning_packet.get(key) or interaction_episode.metadata.get(key) or '').strip()
            if value:
                evidence.append(value)
        for item in interaction_episode.evidence[:8]:
            ref = item.path or item.ref_id
            if ref:
                evidence.append(ref)
        return evidence[:16]

    def _tool_metrics(self, *, task: ToolTask, result: ToolResult, card: ToolCard | None, evidence: list[str]) -> dict[str, float]:
        selected_mode = str(task.metadata.get('selected_mode') or (task.metadata.get('mode_selection') or {}).get('selected_mode') or '')
        semantic_alignment = 1.0 if result.success else 0.42 if result.execution_state.state == 'waiting_approval' else 0.2
        target_alignment = 1.0 if task.actions else 0.3
        progress_visibility = 0.85 if result.output_text or result.artifacts else 0.45 if result.execution_state.detail else 0.2
        bridge_health = 1.0 if result.execution_state.state not in {'adapter_missing', 'missing_tool'} else 0.0
        cross_check_summary = dict(result.execution_state.metadata.get('cross_check_summary') or result.metadata.get('cross_check_summary') or {})
        if cross_check_summary:
            semantic_alignment = max(semantic_alignment, float(cross_check_summary.get('observer_agreement_score', 0.0) or 0.0))
            target_alignment = max(target_alignment, float(cross_check_summary.get('target_element_alignment', 0.0) or 0.0))
            progress_visibility = max(progress_visibility, 0.7 if int(cross_check_summary.get('frame_count', 0) or 0) > 0 else progress_visibility)
        agreement_values = [semantic_alignment, target_alignment, progress_visibility, bridge_health]
        metrics = {
            'semantic_action_alignment': round(semantic_alignment, 4),
            'target_element_alignment': round(target_alignment, 4),
            'progress_visibility_score': round(progress_visibility, 4),
            'bridge_drain_health': round(bridge_health, 4),
            'observer_agreement_score': round(mean(agreement_values), 4),
            'learning_consolidation_score': round(max(float(result.metadata.get('interaction_confidence') or 0.0), mean(agreement_values)), 4),
        }
        lab = self._run_lab_for_tool(card=card, task=task, result=result, evidence=evidence, selected_mode=selected_mode)
        metrics.update(lab)
        return metrics

    def _teaching_metrics(
        self,
        *,
        learning_packet: dict[str, Any],
        visual_summary: dict[str, Any],
        readiness: dict[str, Any],
        login_learning: dict[str, Any],
        interaction_episode: InteractionEpisode,
    ) -> dict[str, float]:
        capture_stats = dict(learning_packet.get('capture_stats') or {})
        cross_check_summary = dict(learning_packet.get('cross_check_summary') or {})
        step_count = max(int(capture_stats.get('step_count', len(interaction_episode.actions)) or len(interaction_episode.actions) or 1), 1)
        relevant_steps = max(int(capture_stats.get('relevant_step_count', len(interaction_episode.actions)) or len(interaction_episode.actions) or 1), 1)
        visible_steps = int(capture_stats.get('visible_step_count', 0) or 0)
        screenshot_count = int(capture_stats.get('screenshot_count', 0) or 0)
        queue_depth = int(capture_stats.get('queue_depth', 0) or 0)
        dropped = int(capture_stats.get('api_dropped_count', 0) or 0)
        heartbeat = int(capture_stats.get('heartbeat_count', 0) or 0)
        semantic_alignment = min(1.0, relevant_steps / step_count)
        target_alignment = mean([
            float(visual_summary.get('critical_object_coverage', 0.0) or 0.0),
            float(cross_check_summary.get('target_element_alignment', visual_summary.get('critical_object_coverage', 0.0)) or 0.0),
        ])
        progress_visibility = min(1.0, (visible_steps + screenshot_count) / max(step_count, 1))
        bridge_health = max(0.0, 1.0 - min(1.0, queue_depth / 12.0) - min(0.4, dropped / 10.0) + min(0.2, heartbeat / 50.0))
        observer_agreement = mean([
            semantic_alignment,
            target_alignment,
            progress_visibility,
            float(visual_summary.get('visual_alignment_score', 0.0) or 0.0),
            float(cross_check_summary.get('observer_agreement_score', visual_summary.get('visual_alignment_score', 0.0)) or 0.0),
        ])
        readiness_state = str(readiness.get('status') or '').strip().lower()
        readiness_bonus = 1.0 if readiness_state == 'ready' else 0.68 if readiness_state == 'partial' else 0.28
        learning_consolidation = mean([
            readiness_bonus,
            float(visual_summary.get('visual_alignment_score', 0.0) or 0.0),
            float(visual_summary.get('critical_object_coverage', 0.0) or 0.0),
            float(login_learning.get('login_visual_completeness', visual_summary.get('login_visual_completeness', 0.0)) or 0.0),
            float(cross_check_summary.get('observer_agreement_score', 0.0) or 0.0),
            float(learning_packet.get('interaction_confidence') or interaction_episode.confidence or 0.0),
        ])
        metrics = {
            'semantic_action_alignment': round(semantic_alignment, 4),
            'target_element_alignment': round(target_alignment, 4),
            'progress_visibility_score': round(progress_visibility, 4),
            'bridge_drain_health': round(max(0.0, min(1.0, bridge_health)), 4),
            'observer_agreement_score': round(max(0.0, min(1.0, observer_agreement)), 4),
            'learning_consolidation_score': round(max(0.0, min(1.0, learning_consolidation)), 4),
        }
        lab = self._run_lab_for_teaching(learning_packet=learning_packet, interaction_episode=interaction_episode)
        metrics.update(lab)
        return metrics

    def _consultant_for(self, *, task: ToolTask, result: ToolResult) -> str:
        incident_kind = str(task.metadata.get('incident_kind') or '')
        diagnostic_category = str(task.metadata.get('diagnostic_category') or '')
        scope = str(task.metadata.get('consultation_scope') or '')
        if any(kind in incident_kind for kind in ('bridge_lag', 'navigation_stall', 'session_restore_weak')):
            return 'codex_installed'
        if diagnostic_category in {'need_codex_fix', 'need_runtime_tuning'}:
            return 'codex_installed'
        if scope == 'external_assistant' and str(task.metadata.get('assistant_kind') or '').lower().startswith('chatgpt'):
            return 'chatgpt_installed'
        return 'chatgpt_installed' if result.execution_state.state == 'missing_tool' else 'codex_installed'

    def _run_lab_for_tool(
        self,
        *,
        card: ToolCard | None,
        task: ToolTask,
        result: ToolResult,
        evidence: list[str],
        selected_mode: str,
    ) -> dict[str, float]:
        if self.experiment_lab is None:
            return {}
        goal_metadata = self._goal_progress_metadata(task.metadata)
        observed = str(result.output_text or result.execution_state.detail or result.error_message or '').strip()
        if not observed:
            return {}
        domain = ExperimentDomain.CODE if (card is not None and card.tool_type in {ToolType.CODE_EDITOR, ToolType.CUSTOM} and 'codex' in card.tool_id) else ExperimentDomain.LANGUAGE
        route = self._route_for_mode(selected_mode, card.tool_type if card is not None else result.tool_type)
        candidate = ExperimentCandidate(
            label=card.title if card is not None else task.tool_id,
            route=route,
            output_text=observed,
            extracted_data=dict(result.extracted_data),
            execution_ms=result.execution_ms,
            operational_cost=0.0,
            metadata={
                'evidence_refs': evidence,
                'reused_pattern': bool(task.metadata.get('reuse_guard_active')),
                'user_progress': float(goal_metadata.get('progress') or 0.0),
            },
        )
        runs, recommendation = self.experiment_lab.run_experiment(
            domain=domain,
            objective=task.objective,
            subject_key=str(goal_metadata.get('objective_id') or task.site_id or (card.tool_id if card is not None else task.tool_id)),
            expected={'text': task.expected_outcome or task.objective},
            candidates=[candidate],
            metadata={'source': 'live_audit_tool', 'user_progress': float(goal_metadata.get('progress') or 0.0)},
        )
        run = runs[0]
        return {
            'lab_precision': round(run.metrics.precision, 4),
            'lab_robustness': round(run.metrics.robustness, 4),
            'lab_reuse_score': round(run.metrics.reuse_score, 4),
            'lab_total_score': round(run.metrics.total_score, 4),
            'lab_recommended_route_score': round(float(recommendation.score or 0.0), 4),
        }

    def _run_lab_for_teaching(self, *, learning_packet: dict[str, Any], interaction_episode: InteractionEpisode) -> dict[str, float]:
        if self.experiment_lab is None:
            return {}
        goal_metadata = self._goal_progress_metadata(interaction_episode.metadata)
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        critical_objects = [str(item) for item in visual_summary.get('critical_objects') or [] if item]
        observed_text = str((interaction_episode.result.summary if interaction_episode.result is not None else '') or interaction_episode.objective)
        if not observed_text and not critical_objects:
            return {}
        candidate = ExperimentCandidate(
            label=interaction_episode.metadata.get('display_name') or interaction_episode.site_id or 'teaching_session',
            route=EvaluationRoute.UI,
            output_text=observed_text,
            extracted_data={'recognized_text': observed_text, 'objects': critical_objects},
            execution_ms=0,
            metadata={
                'evidence_refs': [item.path or item.ref_id for item in interaction_episode.evidence],
                'user_progress': float(goal_metadata.get('progress') or 0.0),
            },
        )
        runs, recommendation = self.experiment_lab.run_experiment(
            domain=ExperimentDomain.OCR,
            objective=interaction_episode.objective,
            subject_key=str(goal_metadata.get('objective_id') or interaction_episode.site_id or 'general'),
            expected={
                'text': interaction_episode.metadata.get('expected_outcome') or interaction_episode.objective,
                'objects': critical_objects,
            },
            candidates=[candidate],
            metadata={'source': 'live_audit_teaching', 'user_progress': float(goal_metadata.get('progress') or 0.0)},
        )
        run = runs[0]
        return {
            'lab_precision': round(run.metrics.precision, 4),
            'lab_robustness': round(run.metrics.robustness, 4),
            'lab_reuse_score': round(run.metrics.reuse_score, 4),
            'lab_total_score': round(run.metrics.total_score, 4),
            'lab_recommended_route_score': round(float(recommendation.score or 0.0), 4),
        }

    def _goal_progress_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        goal_parameters = dict(metadata.get('goal_parameters') or {}) if isinstance(metadata, dict) else {}
        goal_context = dict(metadata.get('goal_context') or {}) if isinstance(metadata, dict) else {}
        objective = dict(goal_context.get('objective') or {})
        return {
            'objective_id': str(goal_parameters.get('objective_id') or objective.get('objective_id') or ''),
            'status': str(goal_parameters.get('goal_status') or goal_context.get('status') or objective.get('status') or ''),
            'progress': float(goal_parameters.get('goal_progress') or goal_context.get('progress') or objective.get('progress') or 0.0),
            'blocker': str(goal_parameters.get('goal_blocker') or goal_context.get('blocker') or objective.get('blocker') or ''),
        }

    def _route_for_mode(self, mode: str, tool_type: ToolType) -> EvaluationRoute:
        mode_value = (mode or '').strip().lower()
        if mode_value == 'ui' or tool_type == ToolType.BROWSER:
            return EvaluationRoute.UI
        if mode_value == 'api' or tool_type == ToolType.MCP_CLIENT:
            return EvaluationRoute.API
        if mode_value == 'background' or tool_type in {ToolType.SHELL, ToolType.CODE_EDITOR}:
            return EvaluationRoute.BACKGROUND
        return EvaluationRoute.LOCAL

    def _summary_from_snapshot(self, audit: dict[str, Any]) -> str:
        findings = [item for item in (audit.get('findings') or []) if isinstance(item, dict)]
        lead = str(findings[0].get('title') or findings[0].get('kind') or 'Sin hallazgos.') if findings else 'Sin hallazgos.'
        decision = dict(audit.get('decision') or {})
        action = str(decision.get('action') or 'continue_local')
        confidence = float(audit.get('confidence') or 0.0)
        return f'{lead} Decision: {action}. Confianza {confidence:.2f}.'

