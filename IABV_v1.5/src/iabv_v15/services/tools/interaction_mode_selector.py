from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from iabv_v15.domain.models import InferenceRequest, InteractionMode, ModeSelectionDecision, ToolCard, ToolTask, ToolType
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_registry import ToolRegistry


@dataclass(slots=True)
class _CandidateAssessment:
    card: ToolCard
    mode: InteractionMode
    scores: dict[str, float]
    total_score: float
    reason: str
    reusable_pattern_id: str | None = None
    reusable_episode_id: str | None = None
    equivalent_pattern_exists: bool = False
    already_resolved: bool = False
    improvement_already_implemented: bool = False


class InteractionModeSelector:
    def __init__(self, registry: ToolRegistry, repository: ToolRecordRepository):
        self.registry = registry
        self.repository = repository

    def select(
        self,
        *,
        request: InferenceRequest,
        draft_task: ToolTask | None = None,
        suggested_tool_id: str | None = None,
        allowed_tool_ids: list[str] | None = None,
    ) -> ModeSelectionDecision:
        desired_modes = self._desired_modes(request)
        cards = [self.registry.refresh_card(item) for item in self.registry.list_cards()]
        if allowed_tool_ids:
            allowed = set(allowed_tool_ids)
            cards = [item for item in cards if item.tool_id in allowed]
        preferred_external = self._preferred_external_decision(
            request=request,
            draft_task=draft_task,
            suggested_tool_id=suggested_tool_id,
            allowed_tool_ids=allowed_tool_ids,
            desired_modes=desired_modes,
            cards=cards,
        )
        if preferred_external is not None:
            return preferred_external
        assessments = [
            self._assess_candidate(card=item, request=request, draft_task=draft_task, suggested_tool_id=suggested_tool_id, desired_modes=desired_modes)
            for item in cards
        ]
        assessments.sort(key=lambda item: item.total_score, reverse=True)
        best = assessments[0] if assessments else None
        if best is None:
            return ModeSelectionDecision(
                selected_mode=InteractionMode.FALLBACK,
                fallback_used=True,
                reason='No hay ToolCards registradas para resolver esta tarea.',
            )
        fallback_used = (
            best.mode not in desired_modes
            or not best.card.available
            or (bool(allowed_tool_ids) and bool(suggested_tool_id) and best.card.tool_id != suggested_tool_id)
        )
        metadata = {
            'desired_modes': [item.value for item in desired_modes],
            'candidate_ranking': [
                {
                    'tool_id': item.card.tool_id,
                    'mode': item.mode.value,
                    'score': round(item.total_score, 4),
                }
                for item in assessments[:5]
            ],
        }
        if best.reusable_pattern_id:
            metadata['reusable_pattern_id'] = best.reusable_pattern_id
        if best.reusable_episode_id:
            metadata['reusable_episode_id'] = best.reusable_episode_id
        return ModeSelectionDecision(
            selected_mode=best.mode if best.card.available else InteractionMode.FALLBACK,
            selected_tool_id=best.card.tool_id,
            selected_tool_type=best.card.tool_type,
            adapter_exists=best.card.adapter_key in self.registry.adapters,
            available=best.card.available,
            fallback_used=fallback_used,
            already_resolved=best.already_resolved,
            equivalent_pattern_exists=best.equivalent_pattern_exists,
            improvement_already_implemented=best.improvement_already_implemented,
            reusable_pattern_id=best.reusable_pattern_id,
            reusable_episode_id=best.reusable_episode_id,
            scores={**best.scores, 'total': round(best.total_score, 4)},
            reason=best.reason,
            metadata=metadata,
        )

    def _preferred_external_decision(
        self,
        *,
        request: InferenceRequest,
        draft_task: ToolTask | None,
        suggested_tool_id: str | None,
        allowed_tool_ids: list[str] | None,
        desired_modes: list[InteractionMode],
        cards: list[ToolCard],
    ) -> ModeSelectionDecision | None:
        if str(request.goal_parameters.get('consultation_scope') or '').strip().lower() != 'external_assistant':
            return None
        preferred_tool_id = str(suggested_tool_id or request.goal_parameters.get('tool_id') or '').strip()
        if not preferred_tool_id:
            return None
        if allowed_tool_ids and preferred_tool_id not in set(allowed_tool_ids):
            return None
        preferred = next((item for item in cards if item.tool_id == preferred_tool_id), None)
        if preferred is None:
            return None
        adapter_exists = preferred.adapter_key in self.registry.adapters
        if not preferred.available or not adapter_exists:
            return None
        if self._has_repeated_blocked_failures(card=preferred, goal=request.user_goal.lower(), site_id=(draft_task.site_id if draft_task is not None else None) or request.site_hint):
            return None
        mode = self._mode_for_tool(preferred.tool_type)
        goal = request.user_goal.lower()
        site_id = (draft_task.site_id if draft_task is not None else None) or request.site_hint
        pattern = self._best_pattern(card=preferred, goal=goal, site_id=site_id)
        episode = self._best_episode(card=preferred, goal=goal, site_id=site_id)
        equivalent_pattern_exists = pattern is not None
        already_resolved = episode is not None and episode.result is not None and episode.result.success
        improvement_already_implemented = self._improvement_already_implemented(goal, equivalent_pattern_exists, already_resolved)
        automatic_capture = self._supports_automatic_external_capture(preferred)
        reason_bits = [
            'consulta_externa_preferida',
            f'modo={mode.value}',
            f'automatica={automatic_capture}',
            f'available={preferred.available}',
        ]
        if pattern is not None:
            reason_bits.append(f'patron_equivalente={pattern.pattern_id}')
        if episode is not None:
            reason_bits.append(f'episodio_resuelto={episode.interaction_episode_id}')
        return ModeSelectionDecision(
            selected_mode=mode if mode in desired_modes else InteractionMode.FALLBACK,
            selected_tool_id=preferred.tool_id,
            selected_tool_type=preferred.tool_type,
            adapter_exists=adapter_exists,
            available=preferred.available,
            fallback_used=mode not in desired_modes,
            already_resolved=already_resolved,
            equivalent_pattern_exists=equivalent_pattern_exists,
            improvement_already_implemented=improvement_already_implemented,
            reusable_pattern_id=pattern.pattern_id if pattern is not None else None,
            reusable_episode_id=episode.interaction_episode_id if episode is not None else None,
            scores={
                'availability': 1.0,
                'adapter_exists': 1.0,
                'desired_match': 1.0 if mode in desired_modes else 0.0,
                'suggested_match': 1.0,
                'automatic_capture': 1.0 if automatic_capture else 0.0,
                'total': 5.0 if automatic_capture else 4.0,
            },
            reason=' | '.join(reason_bits),
            metadata={
                'desired_modes': [item.value for item in desired_modes],
                'candidate_ranking': [
                    {
                        'tool_id': preferred.tool_id,
                        'mode': mode.value,
                        'score': 5.0 if automatic_capture else 4.0,
                    }
                ],
                'selection_policy': 'preferred_external_tool',
            },
        )

    def _assess_candidate(
        self,
        *,
        card: ToolCard,
        request: InferenceRequest,
        draft_task: ToolTask | None,
        suggested_tool_id: str | None,
        desired_modes: list[InteractionMode],
    ) -> _CandidateAssessment:
        mode = self._mode_for_tool(card.tool_type)
        goal = request.user_goal.lower()
        site_id = (draft_task.site_id if draft_task is not None else None) or request.site_hint
        pattern = self._best_pattern(card=card, goal=goal, site_id=site_id)
        episode = self._best_episode(card=card, goal=goal, site_id=site_id)
        repeated_block = self._has_repeated_blocked_failures(card=card, goal=goal, site_id=site_id)
        availability = 1.0 if card.available and not repeated_block else 0.0
        adapter_exists = 1.0 if card.adapter_key in self.registry.adapters else 0.0
        total_runs = card.success_count + card.failure_count
        stability = (card.success_count / total_runs) if total_runs else 0.55
        if pattern is not None and (pattern.success_count + pattern.failure_count):
            pattern_stability = pattern.success_count / max(pattern.success_count + pattern.failure_count, 1)
            stability = max(stability, pattern_stability)
        cost = self._cost_score(card.tool_type)
        risk = 0.0 if repeated_block else self._risk_score(card=card, request=request)
        latency = self._latency_score(card=card)
        frequency = min(1.0, (total_runs + (pattern.success_count if pattern is not None else 0)) / 8.0)
        learned_pattern = 1.0 if pattern is not None and pattern.success_count > 0 else 0.45 if pattern is not None else 0.0
        desired_match = 1.0 if mode in desired_modes else 0.2
        suggested_match = 1.0 if suggested_tool_id and suggested_tool_id == card.tool_id else 0.0
        already_resolved = episode is not None and episode.result is not None and episode.result.success
        equivalent_pattern_exists = pattern is not None
        improvement_already_implemented = self._improvement_already_implemented(goal, equivalent_pattern_exists, already_resolved)
        resolution_bonus = 1.0 if already_resolved else 0.0
        total_score = (
            availability * 2.2
            + adapter_exists * 0.8
            + stability * 1.5
            + cost * 0.8
            + risk * 1.2
            + latency * 0.8
            + frequency * 0.6
            + learned_pattern * 1.8
            + desired_match * 1.4
            + suggested_match * 0.5
            + resolution_bonus * 0.8
        )
        reason_bits = [
            f'modo={mode.value}',
            f'disponibilidad={availability:.2f}',
            f'estabilidad={stability:.2f}',
            f'costo={cost:.2f}',
            f'riesgo={risk:.2f}',
            f'latencia={latency:.2f}',
            f'uso={frequency:.2f}',
            f'patron={learned_pattern:.2f}',
        ]
        if pattern is not None:
            reason_bits.append(f'patron_equivalente={pattern.pattern_id}')
        if episode is not None:
            reason_bits.append(f'episodio_resuelto={episode.interaction_episode_id}')
        if repeated_block:
            reason_bits.append('bloqueo_repetido_reciente=1')
        return _CandidateAssessment(
            card=card,
            mode=mode,
            scores={
                'availability': availability,
                'adapter_exists': adapter_exists,
                'stability': stability,
                'cost': cost,
                'risk': risk,
                'latency': latency,
                'frequency': frequency,
                'learned_pattern': learned_pattern,
                'desired_match': desired_match,
                'suggested_match': suggested_match,
                'resolved_bonus': resolution_bonus,
            },
            total_score=total_score,
            reason=' | '.join(reason_bits),
            reusable_pattern_id=pattern.pattern_id if pattern is not None else None,
            reusable_episode_id=episode.interaction_episode_id if episode is not None else None,
            equivalent_pattern_exists=equivalent_pattern_exists,
            already_resolved=already_resolved,
            improvement_already_implemented=improvement_already_implemented,
        )

    def _desired_modes(self, request: InferenceRequest) -> list[InteractionMode]:
        text = request.user_goal.lower()
        words = set(re.split(r'\W+', text)) - {''}
        modes: list[InteractionMode] = []
        if 'http://' in text or 'https://' in text or words & {'pagina', 'página', 'url', 'click', 'clic', 'playwright', 'captura'}:
            modes.append(InteractionMode.UI)
        if words & {'mcp', 'api', 'endpoint', 'graphql'} or 'post ' in text or 'get ' in text:
            modes.append(InteractionMode.API)
        if words & {'shell', 'powershell', 'comando', 'script', 'fondo', 'background', 'aider', 'codigo', 'código'}:
            modes.append(InteractionMode.BACKGROUND)
        if not modes:
            modes.append(InteractionMode.BACKGROUND)
            modes.append(InteractionMode.UI)
        return list(dict.fromkeys(modes))

    def _mode_for_tool(self, tool_type: ToolType) -> InteractionMode:
        if tool_type in {ToolType.BROWSER, ToolType.LLM_WEB_UI}:
            return InteractionMode.UI
        if tool_type == ToolType.MCP_CLIENT:
            return InteractionMode.API
        return InteractionMode.BACKGROUND

    def _best_pattern(self, *, card: ToolCard, goal: str, site_id: str | None):
        patterns = self.repository.list_interaction_patterns(tool_id=card.tool_id, site_id=site_id, limit=12) if site_id else self.repository.list_interaction_patterns(tool_id=card.tool_id, limit=12)
        goal_tokens = self._tokens(goal)
        best = None
        best_score = -1.0
        for pattern in patterns:
            tokens = self._tokens(pattern.title + ' ' + str(pattern.metadata.get('objective_excerpt') or ''))
            overlap = len(goal_tokens.intersection(tokens))
            success_bias = pattern.success_count - pattern.failure_count
            score = overlap * 1.5 + success_bias * 0.2
            if score > best_score:
                best_score = score
                best = pattern
        return best if best_score >= 0.5 and best is not None and best.success_count > 0 else None

    def _best_episode(self, *, card: ToolCard, goal: str, site_id: str | None):
        episodes = self.repository.list_interaction_episodes(tool_id=card.tool_id, mode_used=self._mode_for_tool(card.tool_type).value, site_id=site_id, limit=12) if site_id else self.repository.list_interaction_episodes(tool_id=card.tool_id, mode_used=self._mode_for_tool(card.tool_type).value, limit=12)
        goal_tokens = self._tokens(goal)
        for episode in episodes:
            tokens = self._tokens(episode.objective)
            if goal_tokens and len(goal_tokens.intersection(tokens)) == 0:
                continue
            if episode.result is not None and episode.result.success:
                return episode
        return None

    def _has_repeated_blocked_failures(self, *, card: ToolCard, goal: str, site_id: str | None) -> bool:
        episodes = self.repository.list_interaction_episodes(tool_id=card.tool_id, mode_used=self._mode_for_tool(card.tool_type).value, site_id=site_id, limit=8) if site_id else self.repository.list_interaction_episodes(tool_id=card.tool_id, mode_used=self._mode_for_tool(card.tool_type).value, limit=8)
        goal_tokens = self._tokens(goal)
        signatures: Counter[str] = Counter()
        for episode in episodes:
            tokens = self._tokens(episode.objective)
            if goal_tokens and tokens and len(goal_tokens.intersection(tokens)) == 0:
                continue
            result = episode.result
            if result is None or result.success:
                continue
            signature = self._blocked_failure_signature(result=result)
            if signature:
                signatures[signature] += 1
        if not signatures:
            return False
        _signature, count = signatures.most_common(1)[0]
        return count >= 2

    def _blocked_failure_signature(self, *, result) -> str:
        state = str(result.execution_state.state or '').strip().lower()
        error_message = str(getattr(result, 'error_message', '') or '').strip()
        summary = str(getattr(result, 'summary', '') or '').strip()
        errors = ' '.join(str(item or '').strip() for item in list(getattr(result, 'errors', []) or []))
        metadata = dict(getattr(result, 'metadata', {}) or {})
        detail = ' '.join(
            part
            for part in (
                error_message,
                str(result.execution_state.detail or '').strip(),
                summary,
                errors,
                str(metadata.get('error_message') or '').strip(),
                str(metadata.get('detail') or '').strip(),
            )
            if part
        ).lower()
        if 'acceso denegado' in detail or 'access denied' in detail:
            return 'access_denied'
        if 'session expired' in detail or 'sesion expirada' in detail or 'assistant_login_required' in detail:
            return 'session_unavailable'
        if 'wrong_thread' in detail or 'wrong thread' in detail:
            return 'wrong_thread'
        if 'quota' in detail or 'rate limit' in detail or 'credits exhausted' in detail or 'plan upgrade required' in detail:
            return 'account_limited'
        if state in {'adapter_missing', 'missing_tool'}:
            return state
        return ''

    def _cost_score(self, tool_type: ToolType) -> float:
        return {
            ToolType.SHELL: 1.0,
            ToolType.LLM_LOCAL: 0.85,
            ToolType.BROWSER: 0.65,
            ToolType.MCP_CLIENT: 0.75,
            ToolType.CODE_EDITOR: 0.4,
            ToolType.FILE_SYSTEM: 0.9,
            ToolType.CUSTOM: 0.5,
            ToolType.LLM_WEB_UI: 0.55,
        }.get(tool_type, 0.5)

    def _risk_score(self, *, card: ToolCard, request: InferenceRequest) -> float:
        scope = str(request.goal_parameters.get('execution_scope') or request.execution_scope or 'read_only')
        base = 0.85
        if card.supports_write:
            base -= 0.15
        if card.requires_human_approval:
            base += 0.05
        if scope in {'write', 'destructive'}:
            base -= 0.25
        return max(0.05, min(base, 1.0))

    def _latency_score(self, *, card: ToolCard) -> float:
        episodes = self.repository.list_interaction_episodes(tool_id=card.tool_id, limit=8)
        execution_ms = [item.result.execution_ms for item in episodes if item.result is not None and item.result.execution_ms > 0]
        if execution_ms:
            avg = sum(execution_ms) / len(execution_ms)
            return max(0.1, min(1.0, 1.0 - min(avg, 5000.0) / 5000.0))
        return {
            ToolType.SHELL: 0.9,
            ToolType.LLM_LOCAL: 0.55,
            ToolType.BROWSER: 0.6,
            ToolType.MCP_CLIENT: 0.7,
            ToolType.CODE_EDITOR: 0.35,
        }.get(card.tool_type, 0.5)

    def _improvement_already_implemented(self, goal: str, equivalent_pattern_exists: bool, already_resolved: bool) -> bool:
        if not any(token in goal for token in ['mejora', 'mejorar', 'implementa', 'implementar', 'ajusta', 'optimiza', 'corregir', 'arregla']):
            return False
        return equivalent_pattern_exists or already_resolved

    def _supports_automatic_external_capture(self, card: ToolCard) -> bool:
        capture_mode = str(card.metadata.get('response_capture_mode') or '').strip().lower()
        manual_required = bool(card.metadata.get('requires_manual_pasteback', True))
        return capture_mode in {'clipboard_capture', 'tool_result', 'direct_text', 'dom_capture', 'browser_dom'} and not manual_required

    def _tokens(self, text: str) -> set[str]:
        return {token for token in text.lower().replace('/', ' ').replace(':', ' ').split() if len(token) >= 3}
