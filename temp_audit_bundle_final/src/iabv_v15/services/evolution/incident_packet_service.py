from __future__ import annotations

from datetime import datetime, timedelta, timezone

from iabv_v15.domain.models import CodexAcceptanceCriteria, CodexConstraints, CodexContextPack, CodexFileScope, CodexTaskSpec, CodexTestPlan, DossierScope, ExecutionDossier, HiddenIncident, IncidentQuery, RunStatus, UserClue
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository


class IncidentPacketService:
    def __init__(
        self,
        *,
        dossier_repository: ExecutionDossierRepository,
        hidden_incident_repository: HiddenIncidentRepository,
        user_clue_repository: UserClueRepository,
        workspace_root: str,
        pending_issue_repository: PendingIssueRepository | None = None,
        tool_record_repository: ToolRecordRepository | None = None,
    ) -> None:
        self.dossier_repository = dossier_repository
        self.hidden_incident_repository = hidden_incident_repository
        self.user_clue_repository = user_clue_repository
        self.workspace_root = workspace_root
        self.pending_issue_repository = pending_issue_repository
        self.tool_record_repository = tool_record_repository

    def find_relevant_evidence(self, query: IncidentQuery) -> list[ExecutionDossier]:
        if query.pending_issue_id and self.pending_issue_repository is not None:
            issue = self.pending_issue_repository.get(query.pending_issue_id)
            if issue is not None:
                if issue.run_id:
                    return self.dossier_repository.find_by_run(issue.run_id)[: query.limit]
                if issue.episode_id:
                    return self.dossier_repository.find_by_episode(issue.episode_id)[: query.limit]
        if query.run_id:
            dossiers = self.dossier_repository.find_by_run(query.run_id)
        elif query.episode_id:
            dossiers = self.dossier_repository.find_by_episode(query.episode_id)
        elif query.issue_hint:
            dossiers = self.dossier_repository.find_by_issue(query.issue_hint, limit=query.limit)
        else:
            dossiers = self.dossier_repository.list_recent(limit=max(query.limit * 3, 20))
        if query.incident_id:
            incident = self.hidden_incident_repository.get(query.incident_id)
            if incident is not None:
                dossiers = self._related_dossiers_for_incident(incident) or dossiers
        elif query.incident_kind:
            incidents = self.hidden_incident_repository.find_by_kind(query.incident_kind, limit=query.limit)
            related: list[ExecutionDossier] = []
            for incident in incidents:
                related.extend(self._related_dossiers_for_incident(incident))
            if related:
                dossiers = related
        if query.task_role is not None:
            dossiers = [item for item in dossiers if item.detected_role == query.task_role]
        if query.status is not None:
            dossiers = [item for item in dossiers if item.status == query.status]
        if query.recent_hours is not None:
            threshold = datetime.now(timezone.utc) - timedelta(hours=query.recent_hours)
            dossiers = [item for item in dossiers if item.created_at_utc >= threshold]
        return dossiers[: query.limit]

    def find_relevant_incidents(self, query: IncidentQuery) -> list[HiddenIncident]:
        if query.pending_issue_id and self.pending_issue_repository is not None:
            issue = self.pending_issue_repository.get(query.pending_issue_id)
            if issue is not None and issue.run_id:
                incidents = self.hidden_incident_repository.find_by_run(issue.run_id)
                return incidents[: query.limit]
        if query.incident_id:
            incident = self.hidden_incident_repository.get(query.incident_id)
            incidents = [incident] if incident is not None else []
        elif query.episode_id:
            incidents = self.hidden_incident_repository.find_by_episode(query.episode_id)
        elif query.run_id:
            incidents = self.hidden_incident_repository.find_by_run(query.run_id)
        elif query.incident_kind:
            incidents = self.hidden_incident_repository.find_by_kind(query.incident_kind, limit=query.limit)
        else:
            incidents = self.hidden_incident_repository.list_recent(limit=max(query.limit * 3, 20))
        if query.recent_hours is not None:
            threshold = datetime.now(timezone.utc) - timedelta(hours=query.recent_hours)
            incidents = [item for item in incidents if item.created_at_utc >= threshold]
        return incidents[: query.limit]

    def build_codex_packet_for_issue(self, query: IncidentQuery) -> str:
        if query.pending_issue_id and self.pending_issue_repository is not None:
            pending_issue = self.pending_issue_repository.get(query.pending_issue_id)
            if pending_issue is not None:
                dossiers = self.find_relevant_evidence(query)
                return self._build_pending_issue_packet(pending_issue, dossiers)
        incidents = self.find_relevant_incidents(query)
        dossiers = self.find_relevant_evidence(query)
        lead_incident = incidents[0] if incidents else None
        lead_dossier = dossiers[0] if dossiers else None
        if lead_incident is None and lead_dossier is None:
            return (
                'Paquete para Codex - Incidente IABV v1.5\n\n'
                f'Workspace: {self.workspace_root}\n'
                'No encontre evidencia que coincida con el filtro solicitado.\n'
                'Siguiente paso sugerido: ejecutar una corrida nueva o abrir el Centro Evolutivo para poblar evidencia.\n'
            )
        case_key, case_title = self._classify_case_type(lead_incident, lead_dossier)
        clues = self._relevant_clues(lead_incident, lead_dossier)
        evidence_lines: list[str] = []
        if lead_incident is not None:
            evidence_lines.append(f"- incidente: {lead_incident.incident_kind} -> {lead_incident.summary}")
            if lead_incident.affected_url:
                evidence_lines.append(f"- url afectada: {lead_incident.affected_url}")
        if lead_dossier is not None:
            for ref in lead_dossier.evidence_refs[:8]:
                target = ref.path or ref.ref_id
                evidence_lines.append(f"- {ref.kind.value}: {ref.label} -> {target}")
        if clues:
            for clue in clues[:3]:
                evidence_lines.append(f"- pista_usuario: {clue.text}")
        interaction_lines, _interaction_context = self._related_interaction_context(lead_incident, lead_dossier)
        evidence_lines.extend(interaction_lines)
        evidence_lines.extend(self._audit_evidence_lines(case_key=case_key, incident=lead_incident, dossier=lead_dossier))
        task_spec = self.build_codex_task_spec_for_issue(query)
        proposal = self._select_relevant_proposal(case_key, lead_incident, lead_dossier)
        issue = None
        if lead_dossier is not None and lead_dossier.issue_candidates:
            issue = lead_dossier.issue_candidates[0]
        elif lead_incident is not None:
            issue = lead_incident
        tests = self._tests_text(case_key, proposal)
        tradeoffs = ', '.join(proposal.tradeoffs) if proposal and proposal.tradeoffs else 'sin tradeoffs fuertes'
        role_value = lead_dossier.detected_role.value if lead_dossier and lead_dossier.detected_role else 'n/d'
        model_value = lead_dossier.model_used if lead_dossier and lead_dossier.model_used else 'n/d'
        run_value = (lead_dossier.run_id if lead_dossier else (lead_incident.run_id if lead_incident else 'n/d')) or 'n/d'
        if case_key == 'replay_teaching' and run_value == 'n/d':
            run_value = 'no aplica (caso de replay/ensenanza)'
        episode_value = (lead_dossier.episode_id if lead_dossier else (lead_incident.episode_id if lead_incident else 'n/d')) or 'n/d'
        summary = self._summary_text(case_key, lead_incident, lead_dossier)
        probable_cause = self._probable_cause_text(case_key, lead_incident, issue)
        recommended_change = self._recommended_change_text(case_key, lead_incident, proposal)
        return (
            f'Paquete para Codex - {case_title} IABV v1.5\n\n'
            f'Workspace: {self.workspace_root}\n'
            f'Tipo de caso: {case_title}\n'
            f'Incidente: {(lead_incident.incident_id if lead_incident else "n/d")}\n'
            f'Dossier base: {(lead_dossier.dossier_id if lead_dossier else "n/d")}\n'
            f'Run: {run_value}\n'
            f'Episode: {episode_value}\n'
            f'Rol detectado: {role_value}\n'
            f'Modelo: {model_value}\n\n'
            'Diagnostico breve:\n'
            f'{summary}\n\n'
            'Causa raiz probable:\n'
            f'{probable_cause}\n\n'
            'Evidencia referenciada:\n'
            + ('\n'.join(evidence_lines) if evidence_lines else '- run_record: evidencia minima disponible')
            + '\n\nCambio vertical recomendado:\n'
            + recommended_change
            + ('\n\nCodexTaskSpec sugerido:\n' + self._format_codex_task_spec(task_spec) if task_spec is not None else '')
            + '\n\nPruebas sugeridas:\n'
            + tests
            + '\n\nRiesgos o tradeoffs:\n'
            + tradeoffs
        )


    def build_codex_task_spec_for_issue(self, query: IncidentQuery) -> CodexTaskSpec | None:
        incidents = self.find_relevant_incidents(query)
        dossiers = self.find_relevant_evidence(query)
        lead_incident = incidents[0] if incidents else None
        lead_dossier = dossiers[0] if dossiers else None
        if lead_incident is None and lead_dossier is None:
            return None
        case_key, case_title = self._classify_case_type(lead_incident, lead_dossier)
        probable_cause = self._probable_cause_text(case_key, lead_incident, lead_dossier.issue_candidates[0] if lead_dossier and lead_dossier.issue_candidates else lead_incident)
        proposal = self._select_relevant_proposal(case_key, lead_incident, lead_dossier)
        recommended_change = self._recommended_change_text(case_key, lead_incident, proposal)
        interaction_lines, context_data = self._related_interaction_context(lead_incident, lead_dossier)
        _ = interaction_lines
        file_scope = self._codex_file_scope(case_key)
        evidence_refs = self._codex_evidence_refs(lead_incident, lead_dossier, context_data)
        interaction_episode_ids = [item.interaction_episode_id for item in context_data.get('episodes', [])]
        return CodexTaskSpec(
            title=f'Resolver {case_title.lower()}',
            goal=recommended_change or probable_cause,
            file_scope=file_scope,
            constraints=CodexConstraints(
                notes=['Mantener local-first y no persistir secretos.', 'Preferir cambios pequenos y verticales.'],
                forbidden_operations=['git reset --hard'],
            ),
            acceptance_criteria=[
                CodexAcceptanceCriteria(description='La causa raiz debe quedar explicada con evidencia reutilizable.'),
                CodexAcceptanceCriteria(description='La suite dirigida del area afectada debe seguir verde.'),
            ],
            test_plan=CodexTestPlan(
                title='Validacion minima',
                commands=[r'.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -p no:tmpdir'],
                expected_outcomes=['Suite verde sin romper el flujo actual.'],
            ),
            context_pack=CodexContextPack(
                summary=f'{case_title} | {probable_cause}',
                evidence_refs=evidence_refs,
                interaction_episode_ids=interaction_episode_ids,
                metadata={
                    'case_key': case_key,
                    'site_id': self._interaction_site_id(lead_incident, lead_dossier),
                    'interaction_pattern_ids': [item.pattern_id for item in context_data.get('patterns', [])],
                },
            ),
            metadata={
                'incident_id': lead_incident.incident_id if lead_incident else '',
                'dossier_id': lead_dossier.dossier_id if lead_dossier else '',
                'case_key': case_key,
            },
        )

    def _build_pending_issue_packet(self, issue, dossiers: list[ExecutionDossier]) -> str:
        evidence_lines = [f"- evidence_ref: {item}" for item in issue.evidence_refs[:8]]
        if dossiers:
            for ref in dossiers[0].evidence_refs[:6]:
                evidence_lines.append(f"- {ref.kind.value}: {ref.label} -> {ref.path or ref.ref_id}")
        adjustments = ', '.join(adj.target_key for adj in issue.runtime_adjustments) if issue.runtime_adjustments else 'sin tuning runtime previo'
        evidence_block = chr(10).join(evidence_lines) if evidence_lines else '- sin evidencia adicional'
        tests_block = ', '.join(issue.suggested_tests) if issue.suggested_tests else 'sin pruebas sugeridas'
        return f"""Paquete para Codex - Pendiente Self-Teacher IABV v1.5

Workspace: {self.workspace_root}
Pending issue: {issue.issue_id}
Escenario: {issue.scenario_id}
Run: {issue.run_id or 'n/d'}
Episode: {issue.episode_id or 'n/d'}
Session: {issue.session_id or 'n/d'}

Diagnostico breve:
{issue.summary}

Causa raiz probable:
{issue.probable_cause or issue.unresolved_reason or 'Sin causa dominante'}

Evidencia referenciada:
{evidence_block}

Ajustes runtime intentados:
{adjustments}

Cambio vertical recomendado:
{issue.recommended_change or 'Revisar el caso y mover la solucion a codigo.'}

Pruebas sugeridas:
{tests_block}

Riesgos o tradeoffs:
Seguir solo con tuning runtime puede ocultar el problema real; conviene corregir la integracion de fondo."""

    def _classify_case_type(self, incident: HiddenIncident | None, dossier: ExecutionDossier | None) -> tuple[str, str]:
        visual_kinds = {'manual_correction_hotspot', 'visual_alignment_weak', 'critical_object_missing', 'annotation_conflict'}
        teaching_capture_kinds = {'bridge_lag', 'navigation_stall', 'session_restore_weak'}
        if incident is not None and incident.incident_kind in visual_kinds:
            return 'replay_teaching', 'Replay y ensenanza'
        if dossier is not None and dossier.scope == DossierScope.TEACHING:
            if dossier.metrics.get('replay_visual_summary') or dossier.metrics.get('manual_correction_count') is not None:
                return 'replay_teaching', 'Replay y ensenanza'
            if incident is not None and incident.incident_kind in teaching_capture_kinds:
                return 'teaching_capture', 'Ensenanza guiada'
            return 'teaching_flow', 'Ensenanza guiada'
        if dossier is not None and dossier.scope == DossierScope.CHAT:
            return 'operational', 'Operacion adaptativa'
        if incident is not None and incident.run_id:
            return 'operational', 'Operacion adaptativa'
        return 'incident', 'Incidente general'

    def _summary_text(self, case_key: str, incident: HiddenIncident | None, dossier: ExecutionDossier | None) -> str:
        if case_key == 'replay_teaching' and incident is not None and incident.incident_kind == 'manual_correction_hotspot':
            return 'El replay visual sigue requiriendo demasiada correccion manual para dejar claro lo que la IA aprendio sobre la captura.'
        if dossier is not None:
            return dossier.summary
        if incident is not None:
            return incident.summary
        return 'Sin resumen dominante.'

    def _probable_cause_text(self, case_key: str, incident: HiddenIncident | None, issue) -> str:
        if incident is not None:
            mapping = {
                'manual_correction_hotspot': 'La deteccion visual de objetos criticos sigue siendo debil y obliga a corregir manualmente rectangulos, etiquetas o focos de accion.',
                'visual_alignment_weak': 'Los overlays no estan cayendo de forma fiable sobre la captura y por eso la alineacion visual sigue siendo debil.',
                'critical_object_missing': 'Siguen faltando objetos criticos del flujo, como campos, botones o submits, con evidencia visual suficiente.',
                'annotation_conflict': 'La reconstruccion automatica y la correccion humana aun no convergen sobre el mismo objeto o paso.',
                'bridge_lag': 'El bridge visible acumulo eventos y checkpoints sin consolidarlos a tiempo, por eso la ensenanza guardo mucha evidencia tecnica pero poca interpretacion reutilizable del flujo.',
                'navigation_stall': 'La ensenanza quedo esperando progreso visible o attach estable a la pagina activa, asi que el flujo no se consolido bien.',
                'session_restore_weak': 'La restauracion de sesion quedo incompleta o con evidencia debil, asi que el flujo no se pudo interpretar como continuidad confiable.',
            }
            if incident.incident_kind in mapping:
                return mapping[incident.incident_kind]
        if issue is not None and hasattr(issue, 'probable_cause') and getattr(issue, 'probable_cause', ''):
            return issue.probable_cause
        if case_key == 'replay_teaching':
            return 'La evidencia de replay/ensenanza todavia no es suficientemente precisa o visual para reutilizar el flujo con confianza.'
        if case_key == 'teaching_capture':
            return 'La captura de ensenanza no esta alineando bien bridge, replay y learning bundle, asi que el conocimiento queda incompleto.'
        return 'Sin hipotesis dominante; revisar autochequeos y evidencia.'


    def _select_relevant_proposal(self, case_key: str, incident: HiddenIncident | None, dossier: ExecutionDossier | None):
        if dossier is None or not dossier.improvement_proposals:
            return None
        proposals = list(dossier.improvement_proposals)
        if incident is None:
            return max(proposals, key=lambda item: getattr(item, 'priority_score', 0))
        keywords: tuple[str, ...] = ()
        if incident.incident_kind == 'bridge_lag':
            keywords = ('bridge', 'cola', 'drenado', 'flush', 'captura visible')
        elif incident.incident_kind == 'navigation_stall':
            keywords = ('navegacion', 'pestana', 'multitab', 'attach', 'progreso visible')
        elif incident.incident_kind == 'session_restore_weak':
            keywords = ('restauracion', 'sesion', 'storage state', 'restore')
        if keywords:
            ranked: list[tuple[int, int, object]] = []
            for index, proposal in enumerate(proposals):
                haystack = ' '.join(
                    [
                        str(getattr(proposal, 'title', '') or ''),
                        str(getattr(proposal, 'rationale', '') or ''),
                        str(getattr(proposal, 'recommended_change', '') or ''),
                        ' '.join(getattr(proposal, 'suggested_tests', []) or []),
                    ]
                ).lower()
                score = sum(1 for keyword in keywords if keyword in haystack)
                ranked.append((score, int(getattr(proposal, 'priority_score', 0) or 0), proposal))
            ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
            if ranked and ranked[0][0] > 0:
                return ranked[0][2]
        if case_key == 'teaching_capture':
            return max(proposals, key=lambda item: getattr(item, 'priority_score', 0))
        return proposals[0]

    def _recommended_change_text(self, case_key: str, incident: HiddenIncident | None, proposal) -> str:
        if proposal is not None and proposal.recommended_change:
            return proposal.recommended_change
        if case_key == 'replay_teaching':
            return 'Fortalecer el replay visual: mejores rectangulos, etiquetas utiles y marcadores visibles para objetos criticos antes de dar la ensenanza por aprendida.'
        if incident is not None and incident.incident_kind == 'bridge_lag':
            return 'Revisar el bridge visible, el flush de checkpoints y la consolidacion replay->learning para que la ensenanza no quede con mucha API y poca evidencia util.'
        if incident is not None and incident.incident_kind == 'navigation_stall':
            return 'Instrumentar mejor la pestana activa, el progreso visible y el attach a nuevas paginas antes de volver a probar.'
        if case_key == 'teaching_capture':
            return 'Alinear mejor captura visible, artefactos y sync hacia memoria universal antes de confirmar la ensenanza como conocimiento reutilizable.'
        return 'Revisar el incidente y convertirlo en prueba reproducible con evidencia viva.'

    def _tests_text(self, case_key: str, proposal) -> str:
        if proposal is not None and proposal.suggested_tests:
            return ', '.join(proposal.suggested_tests)
        if case_key == 'replay_teaching':
            return 'Abrir replay guiado, Ver overlays verde/naranja/rojo, Corregir un objeto y reabrir el replay'
        if case_key == 'teaching_capture':
            return 'Replay guiado, Payload de entrenamiento, Nueva ensenanza corta'
        return 'sin pruebas sugeridas'

    def _format_codex_task_spec(self, task_spec: CodexTaskSpec) -> str:
        lines = [f"- titulo: {task_spec.title}", f"- goal: {task_spec.goal}"]
        if task_spec.context_pack is not None and task_spec.context_pack.interaction_episode_ids:
            lines.append(f"- interaction_episodes: {', '.join(task_spec.context_pack.interaction_episode_ids[:4])}")
        if task_spec.file_scope:
            scope_bits = ', '.join(scope.path for scope in task_spec.file_scope[:4])
            lines.append(f"- file_scope: {scope_bits}")
        if task_spec.acceptance_criteria:
            lines.append(f"- acceptance: {task_spec.acceptance_criteria[0].description}")
        return '\n'.join(lines)

    def _related_interaction_context(self, incident: HiddenIncident | None, dossier: ExecutionDossier | None) -> tuple[list[str], dict[str, object]]:
        if self.tool_record_repository is None:
            return [], {'patterns': [], 'episodes': []}
        site_id = self._interaction_site_id(incident, dossier)
        if not site_id:
            return [], {'patterns': [], 'episodes': []}
        patterns = self.tool_record_repository.list_interaction_patterns(site_id=site_id, limit=4)
        episodes = self.tool_record_repository.list_interaction_episodes(site_id=site_id, limit=4)
        lines: list[str] = []
        if patterns:
            lines.append(f"- patrones_universales: {len(patterns)} para {site_id}")
            for pattern in patterns[:2]:
                lines.append(
                    f"- interaction_pattern: {pattern.title} | canal {pattern.channel.value} | exitos {pattern.success_count} | fallos {pattern.failure_count}"
                )
        if episodes:
            for episode in episodes[:2]:
                lines.append(
                    f"- interaction_episode: {episode.interaction_episode_id} | modo {episode.mode_used.value} | confianza {episode.confidence:.2f}"
                )
        return lines, {'patterns': patterns, 'episodes': episodes}

    def _audit_evidence_lines(
        self,
        *,
        case_key: str,
        incident: HiddenIncident | None,
        dossier: ExecutionDossier | None,
    ) -> list[str]:
        summary = self._extract_audit_summary(incident=incident, dossier=dossier)
        if not summary:
            if case_key in {'replay_teaching', 'teaching_capture'}:
                return ['- auditoria_2_planos: sin auditoria de dos planos disponible']
            return []
        status = str(summary.get('audit_status') or 'sin auditoria')
        confidence = self._format_audit_confidence(summary.get('audit_overall_confidence'))
        primary_issue = self._primary_audit_issue(summary)
        discrepancies = self._audit_discrepancies(summary, primary_issue=primary_issue)
        lines = [
            f'- audit_status: {status}',
            f'- audit_overall_confidence: {confidence}',
            f'- audit_hallazgo_principal: {primary_issue or "Sin hallazgos de auditoria disponibles."}',
        ]
        if discrepancies:
            lines.append(f"- audit_discrepancias_visuales: {'; '.join(discrepancies[:3])}")
        rationale = str(summary.get('audit_rationale') or '').strip()
        if rationale and rationale != primary_issue:
            lines.append(f'- audit_rationale: {rationale}')
        return lines

    def _extract_audit_summary(
        self,
        *,
        incident: HiddenIncident | None,
        dossier: ExecutionDossier | None,
    ) -> dict[str, object]:
        candidates: list[dict[str, object]] = []
        if dossier is not None:
            replay_summary = dossier.metrics.get('replay_visual_summary')
            if isinstance(replay_summary, dict):
                candidates.append(replay_summary)
        if incident is not None and isinstance(incident.metadata, dict):
            visual_summary = incident.metadata.get('visual_summary')
            if isinstance(visual_summary, dict):
                candidates.append(visual_summary)
        for candidate in candidates:
            metadata = candidate.get('metadata') if isinstance(candidate.get('metadata'), dict) else {}
            merged = dict(candidate)
            merged.update(metadata)
            if any(key in merged for key in ('audit_status', 'audit_overall_confidence', 'audit_findings', 'audit_rationale')):
                return merged
        return {}

    def _format_audit_confidence(self, value: object) -> str:
        if isinstance(value, bool):
            return 'n/d'
        if isinstance(value, (int, float)):
            return f'{float(value):.2f}'
        try:
            return f'{float(str(value)):.2f}'
        except (TypeError, ValueError):
            return 'n/d'

    def _primary_audit_issue(self, summary: dict[str, object]) -> str:
        findings = summary.get('audit_findings')
        if isinstance(findings, list):
            for item in findings:
                text = str(item).strip()
                if text:
                    return text
        return str(summary.get('audit_rationale') or '').strip()

    def _audit_discrepancies(self, summary: dict[str, object], *, primary_issue: str) -> list[str]:
        discrepancies: list[str] = []
        findings = summary.get('audit_findings')
        if isinstance(findings, list):
            for item in findings:
                text = str(item).strip()
                if text and text != primary_issue and text not in discrepancies:
                    discrepancies.append(text)
        gaps = summary.get('gaps')
        if isinstance(gaps, list):
            for item in gaps:
                text = str(item).strip()
                if text and text not in discrepancies:
                    discrepancies.append(text)
        return discrepancies[:3]

    def _interaction_site_id(self, incident: HiddenIncident | None, dossier: ExecutionDossier | None) -> str:
        if incident is not None and incident.site_id:
            return incident.site_id
        if dossier is not None:
            adaptive = dossier.metadata.get('adaptive_session') if isinstance(dossier.metadata, dict) else None
            if isinstance(adaptive, dict):
                context = adaptive.get('context') or {}
                intent = adaptive.get('intent') or {}
                return str(context.get('site_id') or intent.get('site_hint') or '')
        return ''

    def _codex_file_scope(self, case_key: str) -> list[CodexFileScope]:
        if case_key == 'replay_teaching':
            return [
                CodexFileScope(path='src/iabv_v15/ui/viewmodels/capture_studio_viewmodel.py', writable=True, reason='Persistencia y consolidacion del replay visual.'),
                CodexFileScope(path='src/iabv_v15/services/capture/replay_visual_assembler.py', writable=True, reason='Ajustes de overlays y agrupacion visual.'),
                CodexFileScope(path='src/iabv_v15/services/capture/replay_learning_feedback_service.py', writable=True, reason='Feedback visual hacia aprendizaje.'),
            ]
        if case_key == 'teaching_capture':
            return [
                CodexFileScope(path='src/iabv_v15/services/capture/browser_teach_session_service.py', writable=True, reason='Bridge visible, checkpoints y captura de ensenanza.'),
                CodexFileScope(path='src/iabv_v15/ui/viewmodels/capture_studio_viewmodel.py', writable=True, reason='Consolidacion del learning bundle y replay guiado.'),
                CodexFileScope(path='src/iabv_v15/services/tools/interaction_learning_service.py', writable=True, reason='Sync hacia memoria universal y reutilizacion posterior.'),
            ]
        if case_key == 'operational':
            return [
                CodexFileScope(path='src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py', writable=True, reason='Diagnostico y guidance operativo.'),
                CodexFileScope(path='src/iabv_v15/services/adaptive/execution_playbook_service.py', writable=True, reason='Ejecucion y estados operativos.'),
                CodexFileScope(path='src/iabv_v15/services/adaptive/strategy_pack_registry.py', writable=True, reason='Seleccion y sesgo de estrategia.'),
            ]
        return [
            CodexFileScope(path='src/iabv_v15/services/evolution/incident_packet_service.py', writable=True, reason='Enriquecer el paquete tecnico y la evidencia.'),
        ]

    def _codex_evidence_refs(self, incident: HiddenIncident | None, dossier: ExecutionDossier | None, context_data: dict[str, object]) -> list[str]:
        refs: list[str] = []
        if incident is not None:
            refs.append(incident.incident_id)
        if dossier is not None:
            refs.append(dossier.dossier_id)
            refs.extend(ref.ref_id for ref in dossier.evidence_refs[:6])
        refs.extend(pattern.pattern_id for pattern in context_data.get('patterns', []))
        refs.extend(episode.interaction_episode_id for episode in context_data.get('episodes', []))
        deduped: list[str] = []
        for item in refs:
            if item and item not in deduped:
                deduped.append(item)
        return deduped[:10]

    def _related_dossiers_for_incident(self, incident: HiddenIncident) -> list[ExecutionDossier]:
        if incident.episode_id:
            dossiers = self.dossier_repository.find_by_episode(incident.episode_id)
            if dossiers:
                return dossiers
        if incident.run_id:
            dossiers = self.dossier_repository.find_by_run(incident.run_id)
            if dossiers:
                return dossiers
        return []

    def _relevant_clues(self, incident: HiddenIncident | None, dossier: ExecutionDossier | None) -> list[UserClue]:
        if incident is not None:
            clues = self.user_clue_repository.find_by_incident(incident.incident_id)
            if clues:
                return clues
        if dossier is not None and dossier.episode_id:
            clues = self.user_clue_repository.find_by_episode(dossier.episode_id)
            if clues:
                return clues
        if dossier is not None and dossier.run_id:
            return self.user_clue_repository.find_by_run(dossier.run_id)
        return []

