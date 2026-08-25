from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from iabv_v15.domain.models import (
    ApprovalDecision,
    CapturedStep,
    EvidenceKind,
    ExecutionState,
    InteractionAction,
    InteractionChannel,
    InteractionEpisode,
    InteractionEvidence,
    InteractionObservation,
    InteractionPattern,
    InteractionPolicyDecision,
    InteractionResult,
    LearningSignal,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    UniversalInteractionStep,
)
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository


class InteractionLearningService:
    def __init__(self, repository: ToolRecordRepository):
        self.repository = repository

    def learn_from_execution(self, *, card: ToolCard, task: ToolTask, result: ToolResult) -> InteractionPattern:
        channel = self._channel_for_tool(card.tool_type)
        normalized_steps = [self._normalize_action(action, channel) for action in task.actions]
        signature = self._signature_for(task=task, card=card, channel=channel, steps=normalized_steps)
        existing = self.repository.get_interaction_pattern_by_signature(signature)
        now = datetime.now(timezone.utc)
        reused_pattern = existing is not None
        goal_metadata = self._goal_metadata(task.metadata)
        effective_success = self._is_effective_success(result)
        effective_failure = self._is_effective_failure(result)
        if existing is not None:
            pattern = existing.model_copy(
                update={
                    'title': task.title or existing.title,
                    'operations': normalized_steps or existing.operations,
                    'success_count': existing.success_count + (1 if effective_success else 0),
                    'failure_count': existing.failure_count + (1 if effective_failure else 0),
                    'last_task_id': task.task_id,
                    'last_result_id': result.result_id,
                    'updated_at_utc': now,
                    'metadata': {
                        **existing.metadata,
                        'objective_excerpt': task.objective[:200],
                        'execution_scope': task.execution_scope,
                        'approval_decision': task.approval_decision.value,
                        'last_validation_status': result.validation_status.value,
                        'last_execution_state': result.execution_state.state,
                        **goal_metadata,
                    },
                }
            )
        else:
            pattern = InteractionPattern(
                signature=signature,
                title=task.title or task.objective[:80],
                channel=channel,
                tool_id=card.tool_id,
                tool_type=card.tool_type,
                site_id=task.site_id,
                operations=normalized_steps,
                reusable=True,
                success_count=1 if effective_success else 0,
                failure_count=1 if effective_failure else 0,
                last_task_id=task.task_id,
                last_result_id=result.result_id,
                created_at_utc=now,
                updated_at_utc=now,
                metadata={
                    'objective_excerpt': task.objective[:200],
                    'execution_scope': task.execution_scope,
                    'approval_decision': task.approval_decision.value,
                    'last_validation_status': result.validation_status.value,
                    'last_execution_state': result.execution_state.state,
                    **goal_metadata,
                },
            )
        saved = self.repository.save_interaction_pattern(pattern)
        confidence = self._confidence_for_result(result)
        evidence = self._build_evidence(task=task, result=result)
        selection = dict(task.metadata.get('mode_selection') or {})
        learning_signals = self._learning_signals(saved, result, evidence)
        interaction_result = InteractionResult(
            success=effective_success,
            execution_state=result.execution_state.model_copy(deep=True),
            summary=result.output_text[:240] or result.execution_state.detail[:240] or result.error_message[:240],
            errors=[item for item in [result.error_message, result.rollback_state.detail if result.rollback_state is not None and result.rollback_state.state == 'rollback_failed' else ''] if item],
            confidence=confidence,
            execution_ms=result.execution_ms,
            rollback_state=result.rollback_state.model_copy(deep=True) if result.rollback_state is not None else None,
            extracted_data=dict(result.extracted_data),
            artifacts=list(result.artifacts),
            metadata={'validation_status': result.validation_status.value, **goal_metadata},
        )
        policy_decision = InteractionPolicyDecision(
            requires_human_approval=task.approval_decision in {ApprovalDecision.APPROVED, ApprovalDecision.PENDING, ApprovalDecision.REJECTED},
            approval_decision=task.approval_decision,
            blocked=result.execution_state.destructive_blocked,
            rationale=str(task.metadata.get('approval_reason') or result.execution_state.detail or ''),
            confidence=confidence,
            metadata={'execution_scope': task.execution_scope, **goal_metadata},
        )
        episode = InteractionEpisode(
            objective=task.objective,
            mode_used=channel,
            environment={
                'tool_id': card.tool_id,
                'tool_type': card.tool_type.value,
                'adapter_key': card.adapter_key,
                'site_id': task.site_id or '',
                'execution_scope': task.execution_scope,
            },
            captured_metadata={
                'task_metadata': dict(task.metadata),
                'execution_metadata': dict(result.execution_state.metadata),
                'result_metadata': dict(result.metadata),
            },
            actions=[self._to_interaction_action(action, channel, now) for action in task.actions],
            result=interaction_result,
            errors=list(interaction_result.errors),
            evidence=evidence,
            learning_signals=learning_signals,
            confidence=confidence,
            human_approval=task.approval_decision in {ApprovalDecision.APPROVED, ApprovalDecision.PENDING, ApprovalDecision.REJECTED},
            policy_decision=policy_decision,
            selector_name=str(selection.get('selector_name') or 'universal_mode_selector'),
            selector_reason=str(selection.get('reason') or task.metadata.get('selector_reason') or ''),
            pattern_id=saved.pattern_id,
            reused_pattern=bool(selection.get('equivalent_pattern_exists') or selection.get('already_resolved') or reused_pattern),
            tool_id=card.tool_id,
            tool_type=card.tool_type,
            task_id=task.task_id,
            result_id=result.result_id,
            site_id=task.site_id,
            created_at_utc=now,
            updated_at_utc=now,
            metadata={
                'learning_signals': [item.model_dump(mode='json') for item in learning_signals],
                'mode_selection': selection,
                'selected_mode': str(selection.get('selected_mode') or channel.value),
                'reusable_pattern_id': str(selection.get('reusable_pattern_id') or ''),
                'reusable_episode_id': str(selection.get('reusable_episode_id') or ''),
                **goal_metadata,
            },
        )
        self.repository.save_interaction_episode(episode)
        saved = saved.model_copy(update={'metadata': {**saved.metadata, 'last_interaction_episode_id': episode.interaction_episode_id}})
        saved = self.repository.save_interaction_pattern(saved)
        observation = InteractionObservation(
            pattern_id=saved.pattern_id,
            task_id=task.task_id,
            result_id=result.result_id,
            episode_id=episode.interaction_episode_id,
            success=effective_success,
            channel=saved.channel,
            tool_id=saved.tool_id,
            tool_type=saved.tool_type,
            site_id=task.site_id,
            summary=interaction_result.summary,
            confidence=confidence,
            evidence_refs=[item.ref_id for item in evidence],
            metadata={
                'validation_status': result.validation_status.value,
                'execution_state': result.execution_state.state,
                'rollback_state': result.rollback_state.state if result.rollback_state is not None else '',
                'artifact_count': len(result.artifacts),
                'extracted_keys': sorted(list(result.extracted_data.keys()))[:8],
                **goal_metadata,
            },
        )
        self.repository.save_interaction_observation(observation)
        return saved

    def learn_from_teaching_session(
        self,
        *,
        episode_id: str,
        site_id: str,
        display_name: str,
        objective: str,
        expected_outcome: str,
        notes: str,
        steps: list[CapturedStep],
        learning_packet: dict[str, Any],
        previous_episode_id: str | None = None,
    ) -> InteractionEpisode | None:
        relevant_steps = [step for step in steps if self._is_teaching_step_relevant(step)]
        if not relevant_steps:
            return None
        now = datetime.now(timezone.utc)
        actions = [self._captured_step_to_interaction_action(step, now=now) for step in relevant_steps]
        normalized_steps = [self._to_universal_step(action) for action in actions]
        dominant_channel = self._dominant_channel([action.channel for action in actions])
        signature = self._teaching_signature(site_id=site_id, channel=dominant_channel, steps=normalized_steps)
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        learning_readiness = dict(learning_packet.get('learning_readiness') or {})
        login_learning = dict(learning_packet.get('login_learning') or {})
        success = self._learning_packet_success(learning_packet)
        confidence = self._confidence_for_learning_packet(learning_packet)
        existing_pattern = self.repository.get_interaction_pattern_by_signature(signature)
        reused_pattern = existing_pattern is not None
        if existing_pattern is not None:
            pattern = existing_pattern.model_copy(
                update={
                    'title': display_name or existing_pattern.title,
                    'operations': normalized_steps or existing_pattern.operations,
                    'success_count': existing_pattern.success_count + (1 if success else 0),
                    'failure_count': existing_pattern.failure_count + (0 if success else 1),
                    'updated_at_utc': now,
                    'metadata': {
                        **existing_pattern.metadata,
                        'objective_excerpt': objective[:200],
                        'source': 'teaching_session',
                        'learning_status': learning_readiness.get('status', ''),
                        'login_status': login_learning.get('status', ''),
                        'visual_alignment_score': float(visual_summary.get('visual_alignment_score', 0.0) or 0.0),
                        'manual_correction_count': int(visual_summary.get('manual_correction_count', 0) or 0),
                    },
                }
            )
        else:
            pattern = InteractionPattern(
                signature=signature,
                title=display_name or objective[:80] or 'Ensenanza guiada',
                channel=dominant_channel,
                tool_id='playwright_browser',
                tool_type=ToolType.BROWSER,
                site_id=site_id,
                operations=normalized_steps,
                reusable=True,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                created_at_utc=now,
                updated_at_utc=now,
                metadata={
                    'objective_excerpt': objective[:200],
                    'source': 'teaching_session',
                    'learning_status': learning_readiness.get('status', ''),
                    'login_status': login_learning.get('status', ''),
                    'visual_alignment_score': float(visual_summary.get('visual_alignment_score', 0.0) or 0.0),
                    'manual_correction_count': int(visual_summary.get('manual_correction_count', 0) or 0),
                },
            )
        saved_pattern = self.repository.save_interaction_pattern(pattern)
        evidence = self._build_teaching_evidence(episode_id=episode_id, relevant_steps=relevant_steps, learning_packet=learning_packet, confidence=confidence)
        learning_signals = self._learning_signals_for_teaching(
            pattern=saved_pattern,
            learning_packet=learning_packet,
            evidence=evidence,
            dominant_channel=dominant_channel,
        )
        summary = self._teaching_summary(display_name=display_name, learning_packet=learning_packet)
        previous_episode = self.repository.get_interaction_episode(previous_episode_id) if previous_episode_id else None
        interaction_result_id = previous_episode.result_id if previous_episode is not None and previous_episode.result_id else InteractionResult(success=success).interaction_result_id
        interaction_result = InteractionResult(
            interaction_result_id=interaction_result_id,
            success=success,
            execution_state=ExecutionState(
                state='observed',
                detail=summary,
                executor_name='teaching_replay_bridge',
                sandboxed=True,
                validated=success,
                approval_decision=ApprovalDecision.SKIPPED,
                metadata={
                    'learning_status': learning_readiness.get('status', ''),
                    'login_status': login_learning.get('status', ''),
                    'episode_id': episode_id,
                },
            ),
            summary=summary,
            errors=list(visual_summary.get('gaps') or login_learning.get('missing_signals') or []),
            confidence=confidence,
            execution_ms=0,
            extracted_data={
                'learning_status': learning_readiness.get('status', ''),
                'login_status': login_learning.get('status', ''),
                'critical_object_coverage': float(visual_summary.get('critical_object_coverage', 0.0) or 0.0),
                'login_visual_completeness': float(visual_summary.get('login_visual_completeness', 0.0) or 0.0),
            },
            artifacts=[item.path or item.ref_id for item in evidence if item.path or item.ref_id],
            metadata={'source': 'teaching_session', 'bundle_id': learning_packet.get('bundle_id', '')},
        )
        selector_reason = 'Patron equivalente ya observado en ensenanzas anteriores.' if reused_pattern else 'Nueva ensenanza consolidada desde replay y learning bundle.'
        episode = InteractionEpisode(
            interaction_episode_id=previous_episode_id or InteractionEpisode(objective='tmp', mode_used=dominant_channel).interaction_episode_id,
            objective=objective or f'Ensenanza guiada de {display_name or site_id or "sitio"}',
            mode_used=dominant_channel,
            environment={
                'tool_id': 'playwright_browser',
                'tool_type': ToolType.BROWSER.value,
                'site_id': site_id,
                'display_name': display_name,
                'expected_outcome': expected_outcome,
            },
            captured_metadata={
                'episode_id': episode_id,
                'step_count': len(steps),
                'relevant_step_count': len(relevant_steps),
                'capture_stats': dict(learning_packet.get('capture_stats') or {}),
                'visual_summary': visual_summary,
            },
            actions=actions,
            result=interaction_result,
            errors=list(interaction_result.errors),
            evidence=evidence,
            learning_signals=learning_signals,
            confidence=confidence,
            human_approval=False,
            policy_decision=InteractionPolicyDecision(
                requires_human_approval=False,
                approval_decision=ApprovalDecision.SKIPPED,
                blocked=False,
                rationale='Ensenanza observada y consolidada para memoria universal.',
                confidence=confidence,
                metadata={'source': 'teaching_session'},
            ),
            selector_name='teaching_replay_bridge',
            selector_reason=selector_reason,
            pattern_id=saved_pattern.pattern_id,
            reused_pattern=reused_pattern,
            tool_id='playwright_browser',
            tool_type=ToolType.BROWSER,
            task_id=f'teaching:{episode_id}',
            result_id=interaction_result.interaction_result_id,
            site_id=site_id,
            created_at_utc=previous_episode.created_at_utc if previous_episode is not None else now,
            updated_at_utc=now,
            metadata={
                'source': 'teaching_session',
                'teaching_episode_id': episode_id,
                'bundle_id': learning_packet.get('bundle_id', ''),
                'expected_outcome': expected_outcome[:240],
                'notes': notes[:240],
                'display_name': display_name,
                'learning_signals': [item.model_dump(mode='json') for item in learning_signals],
                'green_count': int(visual_summary.get('green_count', 0) or 0),
                'orange_count': int(visual_summary.get('orange_count', 0) or 0),
                'red_count': int(visual_summary.get('red_count', 0) or 0),
            },
        )
        self.repository.save_interaction_episode(episode)
        saved_pattern = saved_pattern.model_copy(update={'metadata': {**saved_pattern.metadata, 'last_interaction_episode_id': episode.interaction_episode_id}})
        saved_pattern = self.repository.save_interaction_pattern(saved_pattern)
        episode = episode.model_copy(update={'pattern_id': saved_pattern.pattern_id})
        if previous_episode_id:
            self.repository.save_interaction_episode(episode)
        observation = InteractionObservation(
            pattern_id=saved_pattern.pattern_id,
            task_id=episode.task_id,
            result_id=interaction_result.interaction_result_id,
            episode_id=episode.interaction_episode_id,
            success=success,
            channel=dominant_channel,
            tool_id='playwright_browser',
            tool_type=ToolType.BROWSER,
            site_id=site_id,
            summary=summary,
            confidence=confidence,
            evidence_refs=[item.ref_id for item in evidence],
            metadata={
                'learning_status': learning_readiness.get('status', ''),
                'login_status': login_learning.get('status', ''),
                'manual_correction_count': int(visual_summary.get('manual_correction_count', 0) or 0),
            },
        )
        self.repository.save_interaction_observation(observation)
        return episode

    def match_patterns(self, *, card: ToolCard, task: ToolTask, limit: int = 3) -> list[InteractionPattern]:
        channel = self._channel_for_tool(card.tool_type)
        candidates = self.repository.list_interaction_patterns(channel=channel.value, tool_id=card.tool_id, site_id=task.site_id, limit=20)
        if not candidates and task.site_id:
            candidates = self.repository.list_interaction_patterns(channel=channel.value, tool_id=card.tool_id, limit=20)
        scored: list[tuple[float, InteractionPattern]] = []
        task_tokens = self._tokens(task.objective + ' ' + task.title)
        task_ops = [action.action_type.value for action in task.actions]
        for pattern in candidates:
            score = 0.0
            if pattern.site_id and task.site_id and pattern.site_id == task.site_id:
                score += 2.0
            pattern_ops = [step.operation for step in pattern.operations]
            overlap = len([item for item in task_ops if item in pattern_ops])
            score += overlap * 1.5
            score += min(pattern.success_count, 5) * 0.2
            pattern_tokens = self._tokens(pattern.title + ' ' + str(pattern.metadata.get('objective_excerpt') or ''))
            score += len(task_tokens.intersection(pattern_tokens)) * 0.2
            if score > 0:
                scored.append((score, pattern))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def summarize_patterns(self, *, site_id: str | None = None, user_goal: str = '', limit: int = 6) -> list[dict[str, object]]:
        patterns = self.repository.list_interaction_patterns(site_id=site_id, limit=20) if site_id else self.repository.list_interaction_patterns(limit=20)
        goal_tokens = self._tokens(user_goal)
        items: list[dict[str, object]] = []
        for pattern in patterns:
            pattern_tokens = self._tokens(pattern.title + ' ' + str(pattern.metadata.get('objective_excerpt') or ''))
            if goal_tokens and not goal_tokens.intersection(pattern_tokens) and len(items) >= 4:
                continue
            items.append(self.pattern_summary(pattern))
            if len(items) >= limit:
                break
        return items

    def pattern_summary(self, pattern: InteractionPattern) -> dict[str, object]:
        return {
            'pattern_id': pattern.pattern_id,
            'title': pattern.title,
            'channel': pattern.channel.value,
            'tool_id': pattern.tool_id,
            'site_id': pattern.site_id or '',
            'operation_count': len(pattern.operations),
            'success_count': pattern.success_count,
            'failure_count': pattern.failure_count,
            'reusable': pattern.reusable,
            'last_result_id': pattern.last_result_id or '',
        }

    def _channel_for_tool(self, tool_type: ToolType) -> InteractionChannel:
        if tool_type in {ToolType.BROWSER, ToolType.LLM_WEB_UI}:
            return InteractionChannel.UI
        if tool_type == ToolType.MCP_CLIENT:
            return InteractionChannel.API
        return InteractionChannel.BACKGROUND

    def _normalize_action(self, action: ToolAction, channel: InteractionChannel) -> UniversalInteractionStep:
        target = self._sanitize_target(action.target or str(action.parameters.get('selector') or action.parameters.get('url') or ''))
        value_hint = self._value_hint(action)
        return UniversalInteractionStep(
            channel=channel,
            operation=action.action_type.value,
            target=target,
            value_hint=value_hint,
            expected_signal=action.expected_signal,
            confidence=0.9 if not action.destructive else 0.7,
            metadata={
                'label': action.label,
                'requires_approval': action.requires_approval,
                'destructive': action.destructive,
            },
        )

    def _to_interaction_action(self, action: ToolAction, channel: InteractionChannel, timestamp: datetime) -> InteractionAction:
        normalized = self._normalize_action(action, channel)
        return InteractionAction(
            channel=normalized.channel,
            operation=normalized.operation,
            target=normalized.target,
            value_hint=normalized.value_hint,
            expected_signal=normalized.expected_signal,
            confidence=normalized.confidence,
            metadata={**normalized.metadata, 'parameters': dict(action.parameters)},
            started_at_utc=timestamp,
            finished_at_utc=timestamp,
            destructive=action.destructive,
            requires_approval=action.requires_approval,
        )

    def _build_evidence(self, *, task: ToolTask, result: ToolResult) -> list[InteractionEvidence]:
        evidence: list[InteractionEvidence] = []
        for artifact in result.artifacts:
            evidence.append(
                InteractionEvidence(
                    kind='artifact',
                    label='Artifacto de herramienta',
                    ref_id=artifact,
                    path=artifact,
                    confidence=0.8,
                )
            )
        for key in sorted(result.extracted_data.keys())[:8]:
            evidence.append(
                InteractionEvidence(
                    kind='log',
                    label=f'Dato extraido: {key}',
                    ref_id=f'{result.result_id}:{key}',
                    confidence=0.7,
                    metadata={'key': key},
                )
            )
        return evidence

    def _learning_signals(self, pattern: InteractionPattern, result: ToolResult, evidence: list[InteractionEvidence]) -> list[LearningSignal]:
        signals = [
            LearningSignal(
                label=f'pattern:{pattern.channel.value}:{pattern.tool_id}',
                channel=pattern.channel,
                signal_type='pattern_reuse' if pattern.success_count > 0 else 'pattern_seed',
                confidence=self._confidence_for_result(result),
                source='interaction_learning_service',
                evidence_refs=[item.ref_id for item in evidence[:4]],
                metadata={'pattern_id': pattern.pattern_id},
            )
        ]
        if result.rollback_state is not None and result.rollback_state.state:
            signals.append(
                LearningSignal(
                    label=f'rollback:{result.rollback_state.state}',
                    channel=pattern.channel,
                    signal_type='rollback',
                    confidence=0.6 if result.rollback_state.state == 'rolled_back' else 0.3,
                    source='interaction_learning_service',
                    metadata={'pattern_id': pattern.pattern_id},
                )
            )
        return signals

    def _confidence_for_result(self, result: ToolResult) -> float:
        if result.success and result.validation_status.value in {'approved', 'sandbox_pass'}:
            return 0.92 if result.validation_status.value == 'approved' else 0.78
        if result.success:
            return 0.7
        if result.rollback_state is not None and result.rollback_state.state == 'rolled_back':
            return 0.45
        return 0.22

    def _is_effective_success(self, result: ToolResult) -> bool:
        if not result.success:
            return False
        if result.validation_status.value not in {'approved', 'sandbox_pass'}:
            return False
        execution_metadata = dict(result.execution_state.metadata or {})
        if execution_metadata.get('manual_pasteback_required') and not execution_metadata.get('response_captured'):
            return False
        if execution_metadata.get('response_capture_pending') or execution_metadata.get('assistant_login_required'):
            return False
        consultation_metadata = dict(result.metadata.get('autonomous_consultation') or {})
        coherence_flags = list(execution_metadata.get('coherence_flags') or consultation_metadata.get('coherence_flags') or [])
        if coherence_flags:
            return False
        return True

    def _is_effective_failure(self, result: ToolResult) -> bool:
        if not result.success:
            return True
        return result.execution_state.state in {'blocked', 'failed', 'adapter_missing', 'sandbox_fail'}

    def _signature_for(self, *, task: ToolTask, card: ToolCard, channel: InteractionChannel, steps: list[UniversalInteractionStep]) -> str:
        payload = {
            'channel': channel.value,
            'tool_id': card.tool_id,
            'site_id': task.site_id or '',
            'operations': [
                {
                    'operation': step.operation,
                    'target': step.target,
                    'expected_signal': step.expected_signal,
                }
                for step in steps
            ],
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha1(serialized.encode('utf-8')).hexdigest()

    def _sanitize_target(self, target: str) -> str:
        if not target:
            return ''
        if target.startswith('http://') or target.startswith('https://') or target.startswith('file://'):
            parts = urlsplit(target)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        return target[:180]

    def _value_hint(self, action: ToolAction) -> str:
        if action.action_type == ToolActionType.TYPE_TEXT:
            value = action.value or str(action.parameters.get('text') or '')
            return f'<text:{len(value)}>' if value else '<text>'
        if action.action_type == ToolActionType.RUN_COMMAND:
            value = (action.value or action.target or '').strip()
            return value.split()[0] if value else '<command>'
        if action.action_type == ToolActionType.LAUNCH_APP:
            return '<launch_app>'
        if action.action_type == ToolActionType.EDIT_CODE:
            return '<edit_code>'
        if action.action_type == ToolActionType.MCP_CALL:
            return '<mcp_call>'
        if action.action_type == ToolActionType.LLM_QUERY:
            return '<llm_query>'
        return ''

    def _captured_step_to_interaction_action(self, step: CapturedStep, *, now: datetime) -> InteractionAction:
        metadata = step.metadata or {}
        channel = self._channel_for_capture_step(step)
        target = self._sanitize_target(step.target or str(metadata.get('selector') or metadata.get('frame_url') or metadata.get('url') or ''))
        role = str(metadata.get('field_role') or metadata.get('element_role') or metadata.get('tag_name') or metadata.get('input_type') or '').lower()
        text_hint = self._captured_step_value_hint(step)
        expected_signal = self._captured_step_expected_signal(step)
        confidence = 0.92 if metadata.get('element_rect') or step.screenshot_path else 0.68
        return InteractionAction(
            channel=channel,
            operation=step.action_type,
            target=target,
            value_hint=text_hint,
            expected_signal=expected_signal,
            confidence=confidence,
            metadata={
                'selector': metadata.get('selector') or '',
                'role': role,
                'capture_channel': metadata.get('capture_channel') or '',
                'has_screenshot': bool(step.screenshot_path),
            },
            started_at_utc=step.timestamp_utc or now,
            finished_at_utc=step.timestamp_utc or now,
            destructive=False,
            requires_approval=False,
        )

    def _to_universal_step(self, action: InteractionAction) -> UniversalInteractionStep:
        return UniversalInteractionStep(
            channel=action.channel,
            operation=action.operation,
            target=action.target,
            value_hint=action.value_hint,
            expected_signal=action.expected_signal,
            confidence=action.confidence,
            metadata=dict(action.metadata),
        )

    def _build_teaching_evidence(
        self,
        *,
        episode_id: str,
        relevant_steps: list[CapturedStep],
        learning_packet: dict[str, Any],
        confidence: float,
    ) -> list[InteractionEvidence]:
        evidence: list[InteractionEvidence] = [
            InteractionEvidence(
                kind=EvidenceKind.EPISODE,
                label='Episodio de ensenanza',
                ref_id=episode_id,
                confidence=confidence,
            )
        ]
        seen_paths: set[str] = set()
        for step in relevant_steps:
            if step.screenshot_path and step.screenshot_path not in seen_paths:
                seen_paths.add(step.screenshot_path)
                evidence.append(
                    InteractionEvidence(
                        kind=EvidenceKind.SCREENSHOT,
                        label='Captura guiada',
                        ref_id=step.screenshot_path,
                        path=step.screenshot_path,
                        confidence=min(0.95, confidence + 0.1),
                    )
                )
            if len(evidence) >= 6:
                break
        summary = dict(learning_packet.get('visual_summary') or {})
        if summary:
            evidence.append(
                InteractionEvidence(
                    kind=EvidenceKind.LOG,
                    label='Resumen visual de aprendizaje',
                    ref_id=f'visual_summary:{episode_id}',
                    confidence=confidence,
                    metadata={
                        'green_count': int(summary.get('green_count', 0) or 0),
                        'orange_count': int(summary.get('orange_count', 0) or 0),
                        'red_count': int(summary.get('red_count', 0) or 0),
                    },
                )
            )
        return evidence[:8]

    def _learning_signals_for_teaching(
        self,
        *,
        pattern: InteractionPattern,
        learning_packet: dict[str, Any],
        evidence: list[InteractionEvidence],
        dominant_channel: InteractionChannel,
    ) -> list[LearningSignal]:
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        learning_readiness = dict(learning_packet.get('learning_readiness') or {})
        login_learning = dict(learning_packet.get('login_learning') or {})
        signals = [
            LearningSignal(
                label=f'teaching:{learning_readiness.get("status", "insufficient")}',
                channel=dominant_channel,
                signal_type='teaching_bundle',
                confidence=self._confidence_for_learning_packet(learning_packet),
                source='interaction_learning_service',
                evidence_refs=[item.ref_id for item in evidence[:4]],
                metadata={'pattern_id': pattern.pattern_id},
            ),
            LearningSignal(
                label=f'pattern:{pattern.channel.value}:{pattern.tool_id}',
                channel=dominant_channel,
                signal_type='pattern_reuse' if pattern.success_count > 0 else 'pattern_seed',
                confidence=self._confidence_for_learning_packet(learning_packet),
                source='interaction_learning_service',
                metadata={'pattern_id': pattern.pattern_id},
            ),
        ]
        if login_learning.get('status'):
            signals.append(
                LearningSignal(
                    label=f'login:{login_learning.get("status")}',
                    channel=dominant_channel,
                    signal_type='login_learning',
                    confidence=float(visual_summary.get('login_visual_completeness', 0.0) or 0.0),
                    source='interaction_learning_service',
                )
            )
        manual = int(visual_summary.get('manual_correction_count', 0) or 0)
        if manual > 0:
            signals.append(
                LearningSignal(
                    label=f'manual_corrections:{manual}',
                    channel=dominant_channel,
                    signal_type='human_feedback',
                    confidence=0.8,
                    source='interaction_learning_service',
                )
            )
        return signals

    def _confidence_for_learning_packet(self, learning_packet: dict[str, Any]) -> float:
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        learning_readiness = dict(learning_packet.get('learning_readiness') or {})
        login_learning = dict(learning_packet.get('login_learning') or {})
        learning_status = learning_readiness.get('status', 'insufficient')
        login_status = login_learning.get('status', 'insufficient')
        visual_alignment = float(visual_summary.get('visual_alignment_score', learning_readiness.get('visual_alignment_score', 0.0)) or 0.0)
        critical = float(visual_summary.get('critical_object_coverage', learning_readiness.get('critical_object_coverage', 0.0)) or 0.0)
        login_complete = float(visual_summary.get('login_visual_completeness', login_learning.get('login_visual_completeness', 0.0)) or 0.0)
        if learning_status == 'ready' or login_status == 'ready':
            return min(0.95, 0.55 + (visual_alignment * 0.2) + (critical * 0.15) + (login_complete * 0.1))
        if learning_status == 'partial' or login_status == 'partial':
            return min(0.8, 0.38 + (visual_alignment * 0.2) + (critical * 0.1) + (login_complete * 0.1))
        return max(0.2, 0.18 + (visual_alignment * 0.1))

    def _learning_packet_success(self, learning_packet: dict[str, Any]) -> bool:
        learning_status = str((learning_packet.get('learning_readiness') or {}).get('status', 'insufficient'))
        login_status = str((learning_packet.get('login_learning') or {}).get('status', 'insufficient'))
        return learning_status in {'ready', 'partial'} or login_status in {'ready', 'partial'}

    def _teaching_signature(self, *, site_id: str, channel: InteractionChannel, steps: list[UniversalInteractionStep]) -> str:
        payload = {
            'channel': channel.value,
            'tool_id': 'playwright_browser',
            'site_id': site_id or '',
            'source': 'teaching_session',
            'operations': [
                {
                    'operation': step.operation,
                    'target': step.target,
                    'expected_signal': step.expected_signal,
                }
                for step in steps
            ],
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha1(serialized.encode('utf-8')).hexdigest()

    def _channel_for_capture_step(self, step: CapturedStep) -> InteractionChannel:
        capture_channel = str((step.metadata or {}).get('capture_channel') or '').lower()
        if capture_channel == 'api':
            return InteractionChannel.API
        if capture_channel == 'background':
            return InteractionChannel.BACKGROUND
        return InteractionChannel.UI

    def _captured_step_value_hint(self, step: CapturedStep) -> str:
        metadata = step.metadata or {}
        action_type = str(step.action_type or '').lower()
        role = str(metadata.get('field_role') or metadata.get('element_role') or metadata.get('input_type') or '').lower()
        if action_type in {'input', 'change'}:
            if role in {'password', 'password_input'}:
                return '<password_field>'
            if role in {'email', 'email_input'}:
                return '<email_field>'
            if role in {'username', 'username_input'}:
                return '<username_field>'
            return '<input>'
        if action_type == 'keydown':
            return str(metadata.get('key_display') or metadata.get('key_code') or '<key>')
        return ''

    def _captured_step_expected_signal(self, step: CapturedStep) -> str:
        metadata = step.metadata or {}
        action_type = str(step.action_type or '').lower()
        if action_type == 'submit':
            return 'submit'
        if action_type == 'keydown' and str(metadata.get('key_display') or '').lower() == 'enter':
            return 'enter'
        if action_type == 'frame_fallback':
            return str(metadata.get('frame_request_type') or 'frame_fallback')
        role = str(metadata.get('field_role') or metadata.get('element_role') or '').lower()
        return role[:80]

    def _is_teaching_step_relevant(self, step: CapturedStep) -> bool:
        action_type = str(step.action_type or '')
        metadata = step.metadata or {}
        if action_type in {'click', 'input', 'change', 'submit', 'scroll', 'focus', 'frame_fallback'}:
            return True
        if action_type == 'keydown':
            return str(metadata.get('key_display') or '').lower() in {'enter', 'tab'}
        return False

    def _dominant_channel(self, channels: list[InteractionChannel]) -> InteractionChannel:
        if not channels:
            return InteractionChannel.UI
        counts = Counter(item.value for item in channels)
        return InteractionChannel(counts.most_common(1)[0][0])

    def _teaching_summary(self, *, display_name: str, learning_packet: dict[str, Any]) -> str:
        learning_readiness = dict(learning_packet.get('learning_readiness') or {})
        login_learning = dict(learning_packet.get('login_learning') or {})
        visual_summary = dict(learning_packet.get('visual_summary') or {})
        if learning_readiness.get('summary'):
            return str(learning_readiness['summary'])
        if login_learning.get('summary'):
            return str(login_learning['summary'])
        return (
            f'Ensenanza guiada consolidada para {display_name or "sitio"} '
            f'| visual {float(visual_summary.get("visual_alignment_score", 0.0) or 0.0):.2f}.'
        )

    def _goal_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        goal_parameters = dict(metadata.get('goal_parameters') or {}) if isinstance(metadata, dict) else {}
        goal_context = dict(metadata.get('goal_context') or {}) if isinstance(metadata, dict) else {}
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        return {
            'objective_id': str(goal_parameters.get('objective_id') or objective.get('objective_id') or ''),
            'objective_title': str(goal_parameters.get('objective_title') or objective.get('title') or ''),
            'project_id': str(goal_parameters.get('project_id') or project.get('objective_id') or ''),
            'project_title': str(goal_parameters.get('project_title') or project.get('title') or ''),
            'task_goal_id': str(goal_parameters.get('task_id') or task.get('objective_id') or ''),
            'task_goal_title': str(goal_parameters.get('task_title') or task.get('title') or ''),
            'goal_progress': float(goal_parameters.get('goal_progress') or goal_context.get('progress') or 0.0),
            'goal_status': str(goal_parameters.get('goal_status') or goal_context.get('status') or ''),
            'goal_blocker': str(goal_parameters.get('goal_blocker') or goal_context.get('blocker') or ''),
        }

    def _tokens(self, text: str) -> set[str]:
        return {token for token in text.lower().split() if len(token) >= 3}


