from __future__ import annotations

from iabv_v15.domain.models import CapabilityReadiness, CapabilityStatus, TaskContext, TaskIntent
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository


class CapabilityReadinessService:
    STATUS_SCORE = {
        CapabilityStatus.INSUFFICIENT: 0,
        CapabilityStatus.PARTIAL: 1,
        CapabilityStatus.READY_WITH_APPROVAL: 2,
        CapabilityStatus.READY: 3,
    }

    def __init__(self, capability_repository: CapabilityRepository, tool_record_repository: ToolRecordRepository | None = None):
        self.capability_repository = capability_repository
        self.tool_record_repository = tool_record_repository

    def evaluate(self, intent: TaskIntent, context: TaskContext) -> list[CapabilityReadiness]:
        required = self._required_capabilities(intent)
        capabilities: list[CapabilityReadiness] = []
        persisted = {self._capability_key(item.capability_id, item.site_id): item for item in context.capability_snapshot}
        for capability_id in required:
            current = self._derive_capability(capability_id=capability_id, intent=intent, context=context)
            persisted_item = persisted.get(self._capability_key(capability_id, current.site_id))
            prefer_current = self._prefer_current_observation(capability_id=capability_id, context=context)
            if persisted_item is not None:
                merged_evidence = list(dict.fromkeys(current.evidence + persisted_item.evidence))[:8]
                if prefer_current:
                    current = current.model_copy(
                        update={
                            'evidence': merged_evidence,
                            'metadata': {**persisted_item.metadata, **current.metadata},
                            'last_episode_id': current.last_episode_id or persisted_item.last_episode_id,
                        }
                    )
                elif self.STATUS_SCORE[persisted_item.status] > self.STATUS_SCORE[current.status]:
                    current = persisted_item.model_copy(
                        update={
                            'evidence': merged_evidence,
                            'missing_signals': current.missing_signals or persisted_item.missing_signals,
                            'suggested_next_step': current.suggested_next_step or persisted_item.suggested_next_step,
                            'metadata': {**persisted_item.metadata, **current.metadata},
                            'last_episode_id': current.last_episode_id or persisted_item.last_episode_id,
                        }
                    )
            capabilities.append(current)
        self.capability_repository.save_many(capabilities)
        return capabilities

    def _required_capabilities(self, intent: TaskIntent) -> list[str]:
        mapping = {
            'wplay.core': ['wplay.session.restore', 'browser.generic.navigation'],
            'wplay.login': ['wplay.login', 'wplay.session.restore'],
            'wplay.casino': ['wplay.login', 'wplay.navigate.casino', 'wplay.session.restore'],
            'browser.search': ['browser.search.google'],
            'browser.navigate': ['browser.generic.navigation'],
            'knowledge.query': ['knowledge.query.local'],
            'customer.support': ['customer.support.local'],
            'analytics.strategy': ['analytics.report.local'],
            'project.evolution': ['project.review.local'],
            'research.local': ['research.local.memory'],
            'general.assistance': ['assistant.local.chat'],
            'tools.local_workflow': ['tools.local.registry', 'tools.local.execution'],
            'tools.sandbox': ['tools.local.registry', 'tools.local.sandbox'],
        }
        return mapping.get(intent.intent_key, ['assistant.local.chat'])

    def _derive_capability(self, *, capability_id: str, intent: TaskIntent, context: TaskContext) -> CapabilityReadiness:
        site_id = context.site_id or intent.site_hint
        teachings = context.recent_teachings
        incidents = context.recent_incidents
        if capability_id == 'wplay.login':
            lead = teachings[0] if teachings else {}
            ready = any(
                item.get('login_status') == 'ready'
                and float(item.get('login_visual_completeness', 0.0) or 0.0) >= 0.66
                and float(item.get('critical_object_coverage', 0.0) or 0.0) >= 0.66
                and int(item.get('red_count', 0) or 0) == 0
                for item in teachings
            )
            corrected = any(
                item.get('login_status') in {'ready', 'partial'}
                and int(item.get('manual_correction_count', 0) or 0) > 0
                and float(item.get('critical_object_coverage', 0.0) or 0.0) >= 0.55
                for item in teachings
            )
            partial = any(item.get('login_status') == 'partial' for item in teachings) or corrected
            signals = self._collect_signals(teachings, ['email o usuario detectado', 'contrasena detectada', 'submit o enter detectado', 'sesion autenticada detectada'])
            status = CapabilityStatus.READY_WITH_APPROVAL if ready else CapabilityStatus.PARTIAL if partial else CapabilityStatus.INSUFFICIENT
            return CapabilityReadiness(
                capability_id=capability_id,
                title='Login Wplay',
                status=status,
                score=0.94 if ready else 0.66 if partial else 0.18,
                site_id=site_id,
                evidence=signals or ['No encontre ensenanza reciente con login completo.'],
                missing_signals=[] if ready else ['Reforzar correo, contrasena, submit y evidencia visual del login.'],
                last_episode_id=lead.get('episode_id'),
                suggested_next_step='Si ya esta ready_with_approval, aprobar la fase de login. Si no, corrige el replay o reensenalo.',
                metadata={
                    'visual_alignment_score': lead.get('visual_alignment_score', 0.0),
                    'critical_object_coverage': lead.get('critical_object_coverage', 0.0),
                    'login_visual_completeness': lead.get('login_visual_completeness', 0.0),
                    'manual_correction_count': lead.get('manual_correction_count', 0),
                },
            )
        if capability_id == 'wplay.navigate.casino':
            ready = any(
                'navegacion hacia casino detectada' in item.get('signals', [])
                and item.get('learning_status') in {'ready', 'partial'}
                and float(item.get('visual_alignment_score', 0.0) or 0.0) >= 0.55
                and float(item.get('critical_object_coverage', 0.0) or 0.0) >= 0.5
                for item in teachings
            )
            partial = any('navegacion hacia casino detectada' in item.get('signals', []) for item in teachings)
            lead = next((item for item in teachings if 'navegacion hacia casino detectada' in item.get('signals', [])), teachings[0] if teachings else {})
            return CapabilityReadiness(
                capability_id=capability_id,
                title='Navegacion hacia casino en Wplay',
                status=CapabilityStatus.READY_WITH_APPROVAL if ready else CapabilityStatus.PARTIAL if partial else CapabilityStatus.INSUFFICIENT,
                score=0.88 if ready else 0.56 if partial else 0.12,
                site_id=site_id,
                evidence=self._collect_signals(teachings, ['navegacion hacia casino detectada']) or ['No hay una ensenanza fuerte de casino todavia.'],
                missing_signals=[] if ready else ['Hace falta una ensenanza con pasos claros hasta casino y evidencia visual consistente.'],
                last_episode_id=lead.get('episode_id'),
                suggested_next_step='Revisar o reforzar una ensenanza que llegue a casino antes de intentar la fase de juego.',
                metadata={
                    'visual_alignment_score': lead.get('visual_alignment_score', 0.0),
                    'critical_object_coverage': lead.get('critical_object_coverage', 0.0),
                    'manual_correction_count': lead.get('manual_correction_count', 0),
                },
            )
        if capability_id == 'wplay.session.restore':
            weak_restore = any(item.get('incident_kind') == 'session_restore_weak' for item in incidents)
            ready = any(item.get('login_status') == 'ready' and float(item.get('login_visual_completeness', 0.0) or 0.0) >= 0.66 for item in teachings) and not weak_restore
            partial = any(item.get('login_status') in {'ready', 'partial'} for item in teachings)
            lead = teachings[0] if teachings else {}
            status = CapabilityStatus.READY_WITH_APPROVAL if ready else CapabilityStatus.PARTIAL if partial else CapabilityStatus.INSUFFICIENT
            evidence = ['Storage state y evidencias de login reutilizables detectadas.'] if ready else ['No hay evidencia suficiente de restauracion estable de sesion.']
            if weak_restore:
                evidence.append('Hay incidentes recientes de session_restore_weak.')
            return CapabilityReadiness(
                capability_id=capability_id,
                title='Restauracion de sesion Wplay',
                status=status,
                score=0.76 if ready else 0.46 if partial else 0.16,
                site_id=site_id,
                evidence=evidence,
                missing_signals=[] if ready else ['Conviene validar si la sesion se restaura sin pedir login otra vez.'],
                last_episode_id=lead.get('episode_id'),
                suggested_next_step='Probar restauracion de sesion o dejar la fase como login guiado con aprobacion.',
                metadata={
                    'visual_alignment_score': lead.get('visual_alignment_score', 0.0),
                    'login_visual_completeness': lead.get('login_visual_completeness', 0.0),
                },
            )
        if capability_id == 'browser.search.google':
            ready = any(
                item.get('sites', {}).get('google', 0) > 0
                and item.get('relevant_steps', 0) >= 2
                and float(item.get('visual_alignment_score', 0.0) or 0.0) >= 0.55
                and int(item.get('red_count', 0) or 0) <= 1
                for item in teachings
            )
            partial = any(item.get('sites', {}).get('google', 0) > 0 for item in teachings)
            lead = next((item for item in teachings if item.get('sites', {}).get('google', 0) > 0), teachings[0] if teachings else {})
            return CapabilityReadiness(
                capability_id=capability_id,
                title='Busqueda en Google',
                status=CapabilityStatus.READY if ready else CapabilityStatus.PARTIAL if partial else CapabilityStatus.INSUFFICIENT,
                score=0.84 if ready else 0.52 if partial else 0.18,
                site_id='google',
                evidence=self._collect_signals(teachings, ['busqueda web detectada']) or ['No hay una ensenanza fuerte de busqueda en Google.'],
                missing_signals=[] if ready else ['Hace falta una ensenanza o replay con apertura y busqueda completa.'],
                last_episode_id=lead.get('episode_id'),
                suggested_next_step='Ensenar una busqueda corta en Google si quieres ejecucion mas fiable.',
                metadata={
                    'visual_alignment_score': lead.get('visual_alignment_score', 0.0),
                    'manual_correction_count': lead.get('manual_correction_count', 0),
                },
            )
        if capability_id == 'browser.generic.navigation':
            ready = any(
                item.get('learning_status') == 'ready'
                and float(item.get('visual_alignment_score', 0.0) or 0.0) >= 0.6
                and int(item.get('red_count', 0) or 0) <= 1
                for item in teachings
            )
            partial = any(item.get('learning_status') in {'ready', 'partial'} for item in teachings)
            lead = teachings[0] if teachings else {}
            return CapabilityReadiness(
                capability_id=capability_id,
                title='Navegacion web generica',
                status=CapabilityStatus.READY if ready else CapabilityStatus.PARTIAL if partial else CapabilityStatus.INSUFFICIENT,
                score=0.82 if ready else 0.48 if partial else 0.2,
                site_id=site_id,
                evidence=['Hay ensenanzas recientes con pasos visibles reutilizables.'] if ready else ['La navegacion generica aun necesita mas evidencia.'],
                missing_signals=[] if ready else ['Reforzar una ensenanza de apertura y movimiento por paginas.'],
                last_episode_id=lead.get('episode_id'),
                suggested_next_step='Usar una ensenanza mas limpia o capturar un flujo corto de navegacion.',
                metadata={
                    'visual_alignment_score': lead.get('visual_alignment_score', 0.0),
                    'manual_correction_count': lead.get('manual_correction_count', 0),
                },
            )
        if capability_id in {'tools.local.registry', 'tools.local.execution', 'tools.local.sandbox'}:
            cards = self.tool_record_repository.list_cards() if self.tool_record_repository is not None else []
            patterns = self.tool_record_repository.list_interaction_patterns(site_id=site_id, limit=24) if self.tool_record_repository is not None else []
            available_cards = [item for item in cards if item.available]
            sandbox_cards = [item for item in available_cards if item.supports_sandbox]
            channel_counts = {
                'ui': len([item for item in patterns if item.channel.value == 'ui' and item.success_count > 0]),
                'background': len([item for item in patterns if item.channel.value == 'background' and item.success_count > 0]),
                'api': len([item for item in patterns if item.channel.value == 'api' and item.success_count > 0]),
            }
            evidence = [f"{item.title}: {item.validation_status.value}" for item in cards[:6]] or ['No hay ToolCards registradas todavia.']
            if any(channel_counts.values()):
                evidence.append(
                    'Patrones reutilizables -> ' + ', '.join(f"{channel}:{count}" for channel, count in channel_counts.items() if count)
                )
            metadata = {'interaction_pattern_counts': channel_counts}
            if capability_id == 'tools.local.registry':
                ready = bool(cards)
                return CapabilityReadiness(
                    capability_id=capability_id,
                    title='Registro local de herramientas',
                    status=CapabilityStatus.READY if ready else CapabilityStatus.INSUFFICIENT,
                    score=0.9 if ready and any(channel_counts.values()) else 0.86 if ready else 0.18,
                    site_id=site_id,
                    evidence=evidence,
                    missing_signals=[] if ready else ['Registrar al menos una herramienta local util.'],
                    suggested_next_step='Mantener el catalogo de ToolCards validado y visible.' if ready else 'Sembrar ToolCards locales base.',
                    metadata=metadata,
                )
            if capability_id == 'tools.local.sandbox':
                ready = bool(sandbox_cards)
                return CapabilityReadiness(
                    capability_id=capability_id,
                    title='Sandbox de herramientas locales',
                    status=CapabilityStatus.READY if ready else CapabilityStatus.INSUFFICIENT,
                    score=0.86 if ready and any(channel_counts.values()) else 0.82 if ready else 0.2,
                    site_id=site_id,
                    evidence=evidence,
                    missing_signals=[] if ready else ['No hay herramientas locales disponibles para sandbox.'],
                    suggested_next_step='Usar sandbox antes de ejecutar fuera del aislamiento.' if ready else 'Validar herramientas locales antes de habilitar ejecucion real.',
                    metadata=metadata,
                )
            ready = bool(available_cards)
            partial = bool(cards)
            return CapabilityReadiness(
                capability_id=capability_id,
                title='Ejecucion local-first de herramientas',
                status=CapabilityStatus.READY_WITH_APPROVAL if ready else CapabilityStatus.PARTIAL if partial else CapabilityStatus.INSUFFICIENT,
                score=0.9 if ready and sum(1 for count in channel_counts.values() if count > 0) >= 2 else 0.84 if ready else 0.46 if partial else 0.16,
                site_id=site_id,
                evidence=evidence,
                missing_signals=[] if ready else ['Hace falta validar o habilitar herramientas locales para esta tarea.'],
                suggested_next_step='Correr sandbox y luego aprobar la herramienta si el scope lo requiere.' if ready else 'Validar una herramienta local y revisar su adaptador.',
                metadata=metadata,
            )

        title = {
            'knowledge.query.local': 'Consulta local de conocimiento',
            'customer.support.local': 'Soporte local con conocimiento',
            'analytics.report.local': 'Analitica local',
            'project.review.local': 'Revision del proyecto',
            'research.local.memory': 'Investigacion con memoria local',
            'assistant.local.chat': 'Chat adaptativo local',
        }.get(capability_id, capability_id)
        return CapabilityReadiness(
            capability_id=capability_id,
            title=title,
            status=CapabilityStatus.READY,
            score=0.9,
            site_id=site_id,
            evidence=['La capacidad depende principalmente del stack local y del contexto ya disponible.'],
            missing_signals=[],
            suggested_next_step='Seguir con la estrategia propuesta.',
        )

    def _collect_signals(self, teachings: list[dict], probes: list[str]) -> list[str]:
        matches: list[str] = []
        for item in teachings:
            for signal in item.get('signals', []):
                if signal in probes and signal not in matches:
                    matches.append(signal)
        return matches

    def _prefer_current_observation(self, *, capability_id: str, context: TaskContext) -> bool:
        if not context.recent_teachings:
            return False
        return capability_id.startswith('wplay.') or capability_id.startswith('browser.')

    def _capability_key(self, capability_id: str, site_id: str | None) -> str:
        return f"{site_id or 'global'}::{capability_id}"
