from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ExperimentRun,
    ToolCard,
    ToolDiscoverySignal,
    ToolDiscoveryStatus,
    ToolType,
    utc_now,
)
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ToolDiscoveryService:
    def __init__(
        self,
        *,
        storage: ArtifactStorage,
        tool_registry: Any,
        experiment_lab_repository: ExperimentLabRepository,
        world_model_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
    ) -> None:
        self.storage = storage
        self.tool_registry = tool_registry
        self.experiment_lab_repository = experiment_lab_repository
        self.world_model_service = world_model_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self._current_status: ToolDiscoveryStatus | None = None

    def current_status(
        self,
        *,
        refresh: bool = False,
        max_age_seconds: int = 300,
        subject_key: str | None = None,
    ) -> ToolDiscoveryStatus:
        cached = self._current_status
        if cached is None:
            cached = self._load_latest_status()
            self._current_status = cached
        if (
            cached is not None
            and not refresh
            and self._is_fresh(cached, max_age_seconds=max_age_seconds)
            and (not subject_key or subject_key in list((cached.metadata or {}).get('subject_keys') or []))
        ):
            return cached
        status = self.build_status(subject_key=subject_key)
        self._current_status = status
        return status

    def build_status(
        self,
        *,
        subject_key: str | None = None,
        recommendation_limit: int = 8,
        run_limit: int = 12,
    ) -> ToolDiscoveryStatus:
        now = utc_now()
        entries = self._subject_entries(subject_key=subject_key, recommendation_limit=recommendation_limit)
        cards = self._available_cards()
        world_model = self._current_world_model()
        signals: list[ToolDiscoverySignal] = []
        subject_keys: list[str] = []
        seen_keys: set[str] = set()
        for entry in entries:
            resolved_subject_key = str(entry.get('subject_key') or '').strip() or 'general'
            resolved_domain = self._domain_from_value(entry.get('domain'))
            subject_keys.append(resolved_subject_key)
            runs = self.experiment_lab_repository.list_runs(
                domain=resolved_domain.value,
                subject_key=resolved_subject_key,
                limit=max(run_limit, 6),
            )
            recommendation = entry.get('recommendation')
            baseline = (
                recommendation if isinstance(recommendation, ExperimentRecommendation) else self._recommendation_from_runs(runs)
            )
            if baseline is None:
                continue
            for card in cards:
                signal = self._signal_for_card(
                    card=card,
                    domain=resolved_domain,
                    subject_key=resolved_subject_key,
                    recommendation=baseline,
                    runs=runs,
                    world_model=world_model,
                )
                if signal is None or signal.proposal_key in seen_keys:
                    continue
                seen_keys.add(signal.proposal_key)
                signals.append(signal)
        signals = self._reconcile_signals(signals)
        detected = [item for item in signals if item.status == 'detected']
        deferred = [item for item in signals if item.status == 'deferred']
        promoted = [item for item in signals if item.status == 'promoted']
        discarded = [item for item in signals if item.status == 'discarded']
        unresolved = [item for item in signals if item.status == 'unresolved']
        unresolved_fields: list[str] = []
        if not entries:
            unresolved_fields.append('UNRESOLVED:tool_discovery_subjects')
        if not cards:
            unresolved_fields.append('UNRESOLVED:tool_discovery_catalog')
        if world_model is None:
            unresolved_fields.append('UNRESOLVED:tool_discovery_live_status')
        summary = (
            f'Detecte {len(signals)} senal(es) de descubrimiento: {len(detected)} activa(s), '
            f'{len(deferred)} en evaluacion, {len(promoted)} promovida(s), {len(discarded)} descartada(s).'
        )
        if unresolved:
            summary += f' {len(unresolved)} quedo/quedaron sin cierre concluyente.'
        status = ToolDiscoveryStatus(
            created_at_utc=now,
            updated_at_utc=now,
            summary=summary,
            signals=signals[:12],
            unresolved_fields=unresolved_fields,
            metadata={
                'subject_keys': list(dict.fromkeys(subject_keys))[:8],
                'active_signals': [item.model_dump(mode='json') for item in detected[:6]],
                'in_validation_signals': [item.model_dump(mode='json') for item in deferred[:6]],
                'promoted_signals': [item.model_dump(mode='json') for item in promoted[:6]],
                'discarded_signals': [item.model_dump(mode='json') for item in discarded[:6]],
                'unresolved_signals': [item.model_dump(mode='json') for item in unresolved[:6]],
            },
        )
        markdown = self._render_markdown(status)
        archive_json_rel = f'tool_discovery/history/{status.status_id}.json'
        archive_md_rel = f'tool_discovery/history/{status.status_id}.md'
        latest_json_rel = 'tool_discovery/latest.json'
        latest_md_rel = 'tool_discovery/latest.md'
        self.storage.save_json_atomic(archive_json_rel, status.model_dump(mode='json'))
        self.storage.save_bytes(archive_md_rel, markdown.encode('utf-8'))
        self.storage.save_json_atomic(latest_json_rel, status.model_dump(mode='json'))
        self.storage.save_bytes(latest_md_rel, markdown.encode('utf-8'))
        status = status.model_copy(
            update={
                'package_path': str(self.storage.resolve(latest_json_rel)),
                'markdown_path': str(self.storage.resolve(latest_md_rel)),
            }
        )
        self.storage.save_json_atomic(latest_json_rel, status.model_dump(mode='json'))
        return status

    def status_summary(self, status: ToolDiscoveryStatus | None = None) -> dict[str, Any]:
        resolved = status or self.current_status()
        metadata = dict(resolved.metadata or {})
        return {
            'summary': resolved.summary,
            'status_id': resolved.status_id,
            'updated_at_utc': resolved.updated_at_utc.isoformat(),
            'signals': [item.model_dump(mode='json') for item in list(resolved.signals or [])[:6]],
            'active_signals': list(metadata.get('active_signals') or [])[:6],
            'in_validation_signals': list(metadata.get('in_validation_signals') or [])[:6],
            'promoted_signals': list(metadata.get('promoted_signals') or [])[:6],
            'discarded_signals': list(metadata.get('discarded_signals') or [])[:6],
            'unresolved_fields': list(resolved.unresolved_fields or []),
            'package_path': resolved.package_path,
            'markdown_path': resolved.markdown_path,
        }

    def get_status(self) -> dict[str, Any]:
        return self.status_summary()

    def _load_latest_status(self) -> ToolDiscoveryStatus | None:
        try:
            if not self.storage.exists('tool_discovery/latest.json'):
                return None
            return ToolDiscoveryStatus.model_validate(self.storage.load_json('tool_discovery/latest.json'))
        except Exception:
            return None

    def _is_fresh(self, status: ToolDiscoveryStatus, *, max_age_seconds: int) -> bool:
        try:
            return (utc_now() - status.updated_at_utc).total_seconds() <= max_age_seconds
        except Exception:
            return False

    def _subject_entries(self, *, subject_key: str | None, recommendation_limit: int) -> list[dict[str, Any]]:
        if subject_key:
            recommendation = self.experiment_lab_repository.latest_recommendation(subject_key=subject_key)
            if recommendation is not None:
                return [{'subject_key': subject_key, 'domain': recommendation.domain, 'recommendation': recommendation}]
            runs = self.experiment_lab_repository.list_runs(subject_key=subject_key, limit=1)
            if runs:
                return [{'subject_key': subject_key, 'domain': runs[0].domain, 'recommendation': None}]
            return []
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for recommendation in self.experiment_lab_repository.list_recommendations(limit=recommendation_limit):
            probe = str(recommendation.subject_key or '').strip()
            if not probe or probe in seen or probe.startswith('sandbox:'):
                continue
            seen.add(probe)
            entries.append({'subject_key': probe, 'domain': recommendation.domain, 'recommendation': recommendation})
        if entries:
            return entries
        for run in self.experiment_lab_repository.list_runs(limit=max(recommendation_limit * 3, 18)):
            probe = str(run.subject_key or '').strip()
            if not probe or probe in seen or probe.startswith('sandbox:'):
                continue
            seen.add(probe)
            entries.append({'subject_key': probe, 'domain': run.domain, 'recommendation': None})
            if len(entries) >= recommendation_limit:
                break
        return entries

    def _available_cards(self) -> list[ToolCard]:
        registry = self.tool_registry
        if registry is None or not hasattr(registry, 'list_cards'):
            return []
        cards: list[ToolCard] = []
        try:
            for card in registry.list_cards():
                refreshed = registry.refresh_card(card) if hasattr(registry, 'refresh_card') else card
                if bool(getattr(refreshed, 'available', False)):
                    cards.append(refreshed)
        except Exception:
            return []
        return cards

    def _current_world_model(self) -> Any | None:
        service = self.world_model_service
        if service is None or not hasattr(service, 'current_model'):
            return None
        try:
            return service.current_model()
        except Exception:
            return None

    def _recommendation_from_runs(self, runs: list[ExperimentRun]) -> ExperimentRecommendation | None:
        if not runs:
            return None
        probe = runs[0]
        assistant_kind = str(probe.assistant_kind or probe.metadata.get('assistant_kind') or probe.candidate_label or '').strip().lower()
        config_signature = str(probe.config_signature or probe.metadata.get('config_signature') or '').strip()
        return ExperimentRecommendation(
            domain=probe.domain,
            subject_key=probe.subject_key,
            recommended_route=probe.route,
            recommended_assistant_kind=assistant_kind,
            recommended_config_signature=config_signature,
            score=float(probe.metrics.total_score or 0.0),
            confidence=0.52,
            rationale='Baseline inferida desde la corrida mas reciente disponible.',
            supporting_run_ids=[probe.run_id],
        )

    def _signal_for_card(
        self,
        *,
        card: ToolCard,
        domain: ExperimentDomain,
        subject_key: str,
        recommendation: ExperimentRecommendation,
        runs: list[ExperimentRun],
        world_model: Any | None,
    ) -> ToolDiscoverySignal | None:
        assistant_kind = self._assistant_kind_for_card(card)
        route = self._route_for_card(card=card, domain=domain)
        if route == EvaluationRoute.FALLBACK:
            return None
        config_signature = self._config_signature_for_card(card)
        current_assistant = str(recommendation.recommended_assistant_kind or '').strip().lower()
        current_signature = str(recommendation.recommended_config_signature or '').strip()
        if (
            route == recommendation.recommended_route
            and assistant_kind == current_assistant
            and config_signature == current_signature
        ):
            return None
        known = {
            (
                run.route.value,
                str(run.assistant_kind or run.metadata.get('assistant_kind') or '').strip().lower(),
                str(run.config_signature or run.metadata.get('config_signature') or '').strip(),
            )
            for run in runs
        }
        if (route.value, assistant_kind, config_signature) in known:
            return None
        compatibility = self._compatibility_score(domain=domain, card=card, route=route, assistant_kind=assistant_kind)
        if compatibility < 0.55:
            return None
        cost_score = self._cost_score(card)
        current_blocked = self._current_assistant_blocked(recommendation=recommendation, world_model=world_model)
        impact_score = self._impact_score(
            domain=domain,
            card=card,
            route=route,
            current_assistant=current_assistant,
            current_blocked=current_blocked,
        )
        live_status = self._live_status_for(card=card, assistant_kind=assistant_kind, world_model=world_model)
        live_bonus = 0.1 if live_status in {'listo', 'disponible', 'abierto', 'correcto_probable', 'hilo_correcto'} else 0.0
        confidence = min(0.96, 0.26 + compatibility * 0.36 + impact_score * 0.2 + cost_score * 0.12 + live_bonus)
        baseline_score = float(recommendation.score or 0.0)
        estimated_gain = round(max(0.02, impact_score * 0.08 + cost_score * 0.03), 4)
        estimated_candidate_score = round(min(0.99, baseline_score + estimated_gain), 4)
        proposal_key = self._proposal_key(
            subject_key=subject_key,
            baseline_route=recommendation.recommended_route,
            baseline_assistant=current_assistant,
            baseline_signature=current_signature,
            candidate_route=route,
            candidate_assistant=assistant_kind,
            candidate_signature=config_signature,
        )
        source_refs = ['ToolRegistry', 'ExperimentLab']
        if world_model is not None:
            source_refs.append('WorldModelSnapshot')
        title = f'Probar {card.title} para {subject_key}'
        summary = (
            f'{card.title} aparece disponible y compatible con {subject_key}. '
            f'Conviene validarlo frente a {current_assistant or recommendation.recommended_route.value}.'
        )
        return ToolDiscoverySignal(
            proposal_key=proposal_key,
            source='tool_registry',
            source_refs=list(dict.fromkeys(source_refs)),
            domain=domain,
            scope=subject_key,
            title=title,
            summary=summary,
            tool_id=card.tool_id,
            tool_title=card.title,
            assistant_kind=assistant_kind,
            route=route,
            config_signature=config_signature,
            status='detected',
            confidence=round(confidence, 4),
            compatibility_score=round(compatibility, 4),
            impact_score=round(impact_score, 4),
            cost_score=round(cost_score, 4),
            evidence_refs=[run.run_id for run in runs[:4]],
            metadata={
                'tool_type': card.tool_type.value,
                'capabilities': list(card.capabilities or []),
                'current_route': recommendation.recommended_route.value,
                'current_assistant_kind': current_assistant,
                'current_config_signature': current_signature,
                'baseline_weighted_score': round(baseline_score, 4),
                'estimated_candidate_score': estimated_candidate_score,
                'estimated_gain': estimated_gain,
                'live_status': live_status,
                'requires_human_approval': bool(card.requires_human_approval),
                'local_first': bool(card.local_first),
                'supports_sandbox': bool(card.supports_sandbox),
            },
        )

    def _reconcile_signals(self, signals: list[ToolDiscoverySignal]) -> list[ToolDiscoverySignal]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_decision_log'):
            return signals
        try:
            log = service.current_decision_log(refresh=True)
        except Exception:
            return signals
        latest_by_key: dict[str, Any] = {}
        for entry in list(getattr(log, 'entries', []) or []):
            probe = str(getattr(entry, 'proposal_key', '') or '').strip()
            if probe:
                latest_by_key[probe] = entry
        reconciled: list[ToolDiscoverySignal] = []
        for signal in signals:
            latest = latest_by_key.get(str(signal.proposal_key or '').strip())
            if latest is None:
                reconciled.append(signal)
                continue
            metadata = {
                **dict(signal.metadata or {}),
                'decision_state': {
                    'decision': str(getattr(latest, 'decision', '') or ''),
                    'winner': str(getattr(latest, 'winner', '') or ''),
                    'reason': str(getattr(latest, 'reason', '') or ''),
                    'recorded_at_utc': str(getattr(latest, 'recorded_at_utc', '') or ''),
                },
            }
            reconciled.append(signal.model_copy(update={'status': str(getattr(latest, 'decision', '') or 'detected'), 'metadata': metadata}))
        return reconciled

    def _assistant_kind_for_card(self, card: ToolCard) -> str:
        metadata = dict(card.metadata or {})
        assistant_kind = str(metadata.get('assistant_kind') or '').strip().lower()
        if assistant_kind:
            return assistant_kind
        probe = str(card.tool_id or '').strip().lower()
        if 'playwright' in probe:
            return 'playwright'
        if 'aider' in probe:
            return 'aider'
        if 'shell' in probe:
            return 'shell'
        if 'mcp' in probe:
            return 'mcp'
        if 'desktop' in probe:
            return 'iabv_runtime'
        return str(card.adapter_key or probe).strip().lower()

    def _route_for_card(self, *, card: ToolCard, domain: ExperimentDomain) -> EvaluationRoute:
        capabilities = {str(item).strip().lower() for item in (card.capabilities or []) if str(item).strip()}
        assistant_kind = self._assistant_kind_for_card(card)
        if card.tool_type == ToolType.CODE_EDITOR or 'edit_code' in capabilities or 'code_assistance' in capabilities:
            return EvaluationRoute.CODE_AGENT
        if card.tool_type == ToolType.BROWSER or {'open_url', 'click', 'type_text'} & capabilities:
            return EvaluationRoute.UI
        if card.tool_type == ToolType.SHELL:
            return EvaluationRoute.LOCAL
        if card.tool_type == ToolType.MCP_CLIENT or 'mcp_call' in capabilities:
            return EvaluationRoute.API
        if card.tool_type in {ToolType.LLM_LOCAL, ToolType.LLM_WEB_UI} or 'llm_query' in capabilities or 'consult_external' in capabilities:
            if domain == ExperimentDomain.CODE and assistant_kind in {'codex', 'aider'}:
                return EvaluationRoute.CODE_AGENT
            return EvaluationRoute.LANGUAGE_UNDERSTANDING
        if domain == ExperimentDomain.CODE:
            return EvaluationRoute.CODE_AGENT
        return EvaluationRoute.LANGUAGE_UNDERSTANDING

    def _config_signature_for_card(self, card: ToolCard) -> str:
        metadata = dict(card.metadata or {})
        parts = [
            str(metadata.get('launch_mode') or '').strip(),
            str(metadata.get('prompt_template_id') or '').strip(),
            str(card.adapter_key or '').strip(),
        ]
        return ':'.join([part for part in parts if part]) or str(card.tool_id or '').strip()

    def _compatibility_score(
        self,
        *,
        domain: ExperimentDomain,
        card: ToolCard,
        route: EvaluationRoute,
        assistant_kind: str,
    ) -> float:
        capabilities = {str(item).strip().lower() for item in (card.capabilities or []) if str(item).strip()}
        score = 0.35
        if domain == ExperimentDomain.CODE:
            if route == EvaluationRoute.CODE_AGENT:
                score = 0.9
            elif route == EvaluationRoute.LANGUAGE_UNDERSTANDING:
                score = 0.7
            elif route == EvaluationRoute.LOCAL:
                score = 0.56
            elif route == EvaluationRoute.UI:
                score = 0.44
        elif domain == ExperimentDomain.LANGUAGE:
            if route == EvaluationRoute.LANGUAGE_UNDERSTANDING:
                score = 0.88
            elif route == EvaluationRoute.UI:
                score = 0.52
            elif route == EvaluationRoute.LOCAL:
                score = 0.45
        else:
            if route in {EvaluationRoute.UI, EvaluationRoute.API, EvaluationRoute.LOCAL}:
                score = 0.48
        if 'consult_external' in capabilities or 'llm_query' in capabilities:
            score += 0.04
        if 'code_assistance' in capabilities or assistant_kind in {'codex', 'aider'}:
            score += 0.05 if domain == ExperimentDomain.CODE else 0.0
        if bool(card.supports_sandbox):
            score += 0.03
        return min(0.98, max(0.0, score))

    def _impact_score(
        self,
        *,
        domain: ExperimentDomain,
        card: ToolCard,
        route: EvaluationRoute,
        current_assistant: str,
        current_blocked: bool,
    ) -> float:
        score = 0.42
        if current_blocked:
            score += 0.22
        if domain == ExperimentDomain.CODE and route == EvaluationRoute.CODE_AGENT:
            score += 0.22
        if route == EvaluationRoute.LANGUAGE_UNDERSTANDING and card.local_first and current_assistant not in {'ollama', 'codex', 'aider'}:
            score += 0.18
        if route == EvaluationRoute.UI and 'playwright' in str(card.tool_id or '').lower():
            score += 0.12
        return min(0.96, max(0.0, score))

    def _cost_score(self, card: ToolCard) -> float:
        score = 0.45
        if bool(card.local_first):
            score += 0.28
        if card.tool_type in {ToolType.LLM_LOCAL, ToolType.SHELL, ToolType.CODE_EDITOR}:
            score += 0.14
        if bool(card.supports_sandbox):
            score += 0.05
        if bool(card.requires_human_approval):
            score -= 0.04
        return min(0.95, max(0.0, score))

    def _current_assistant_blocked(self, *, recommendation: ExperimentRecommendation, world_model: Any | None) -> bool:
        if world_model is None:
            return False
        assistant_kind = str(recommendation.recommended_assistant_kind or '').strip().lower()
        route_value = recommendation.recommended_route.value
        for block in list(getattr(world_model, 'block_records', []) or []):
            target = str(getattr(block, 'target_scope', '') or '').strip().lower()
            block_assistant = str(getattr(block, 'assistant_kind', '') or '').strip().lower()
            if block_assistant and assistant_kind and block_assistant != assistant_kind:
                continue
            if target and target not in {'consult_external', f'consult_{assistant_kind}', route_value, 'heavy_local_model'}:
                continue
            return True
        return False

    def _live_status_for(self, *, card: ToolCard, assistant_kind: str, world_model: Any | None) -> str:
        if world_model is None:
            return ''
        for item in list(getattr(world_model, 'tool_live_status', []) or []):
            tool_id = str(getattr(item, 'tool_id', '') or '').strip().lower()
            live_assistant = str(getattr(item, 'assistant_kind', '') or '').strip().lower()
            if tool_id == str(card.tool_id or '').strip().lower() or (assistant_kind and live_assistant == assistant_kind):
                return str(getattr(item, 'status', '') or getattr(item, 'thread_status', '') or '').strip().lower()
        return ''

    def _domain_from_value(self, value: Any) -> ExperimentDomain:
        if isinstance(value, ExperimentDomain):
            return value
        text = str(value or '').strip().lower()
        for candidate in ExperimentDomain:
            if candidate.value == text:
                return candidate
        return ExperimentDomain.LANGUAGE

    def _proposal_key(
        self,
        *,
        subject_key: str,
        baseline_route: EvaluationRoute,
        baseline_assistant: str,
        baseline_signature: str,
        candidate_route: EvaluationRoute,
        candidate_assistant: str,
        candidate_signature: str,
    ) -> str:
        return '|'.join(
            [
                str(subject_key or '').strip(),
                'validate_discovery',
                baseline_route.value,
                str(baseline_assistant or '').strip().lower(),
                str(baseline_signature or '').strip(),
                candidate_route.value,
                str(candidate_assistant or '').strip().lower(),
                str(candidate_signature or '').strip(),
            ]
        )

    def _render_markdown(self, status: ToolDiscoveryStatus) -> str:
        lines = [
            '# IABV v1.5 - Tool Discovery',
            '',
            f'Generado: {status.updated_at_utc.isoformat()}',
            f'Resumen: {status.summary}',
            '',
            '## Senales',
        ]
        if not status.signals:
            lines.append('- Sin senales nuevas con evidencia suficiente.')
        for item in status.signals[:8]:
            lines.append(
                f"- {item.scope}: {item.tool_title or item.assistant_kind or item.route.value} | "
                f"estado={item.status} | confianza={item.confidence:.2f} | {item.summary}"
            )
        if status.unresolved_fields:
            lines.append('')
            lines.append(f"UNRESOLVED: {', '.join(status.unresolved_fields)}")
        return '\n'.join(lines).strip()
