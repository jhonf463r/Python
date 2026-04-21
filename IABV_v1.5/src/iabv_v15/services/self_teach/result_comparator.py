from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, CapabilityStatus, DiagnosticCategory, IssueSeverity, ObservedMismatch, ScenarioDefinition, ScenarioMode


class ResultComparator:
    TUNABLE_INCIDENTS = {'bridge_lag', 'navigation_stall', 'tab_attach_gap', 'capture_starvation', 'finalize_slow', 'session_restore_weak'}

    def compare(self, scenario: ScenarioDefinition, session: AdaptiveSession, expected: list[str], observed: list[str]) -> tuple[DiagnosticCategory, list[ObservedMismatch], str, str, float]:
        mismatches: list[ObservedMismatch] = []
        weak_capabilities = [item for item in session.capability_readiness if item.status in {CapabilityStatus.INSUFFICIENT, CapabilityStatus.PARTIAL}]
        incidents = [str(item.get('incident_kind') or '') for item in session.context.recent_incidents if item.get('incident_kind')]
        repeated_technical = bool(incidents)
        tunable = [kind for kind in incidents if kind in self.TUNABLE_INCIDENTS]
        execute_step = next((item for item in (session.playbook.steps if session.playbook else []) if item.phase_key == 'execute'), None)
        execution_state = session.metadata.get('execution_state') if isinstance(session.metadata, dict) else {}
        executor_available = bool(execution_state.get('executor_available')) if isinstance(execution_state, dict) else False
        simulation_only = bool(execution_state.get('simulation_only')) if isinstance(execution_state, dict) else bool(execute_step.simulation_only) if execute_step is not None else False
        missing_adapter = bool(scenario.mode != ScenarioMode.REPLAY_ONLY and execute_step is not None and not simulation_only and not executor_available)
        low_visual = any(
            float((item.metadata or {}).get('visual_alignment_score', 1.0) or 0.0) < 0.55
            or float((item.metadata or {}).get('critical_object_coverage', 1.0) or 0.0) < 0.5
            or float((item.metadata or {}).get('login_visual_completeness', 1.0) or 0.0) < 0.5
            for item in weak_capabilities
            if item.capability_id.startswith('wplay.') or item.capability_id.startswith('browser.')
        )
        if weak_capabilities:
            lead = weak_capabilities[0]
            mismatches.append(
                ObservedMismatch(
                    title='Capacidad operativa aun debil',
                    expected='La capacidad principal deberia estar al menos en ready_with_approval.',
                    observed=f'{lead.title} esta en {lead.status.value}.',
                    probable_cause=lead.suggested_next_step or 'La evidencia reciente aun no sostiene la tarea.',
                    severity=IssueSeverity.HIGH if lead.status == CapabilityStatus.INSUFFICIENT else IssueSeverity.MEDIUM,
                    category=DiagnosticCategory.NEED_TEACHING,
                    evidence_refs=list(session.evidence_refs[:4]),
                )
            )
        if repeated_technical:
            dominant = incidents[0]
            mismatches.append(
                ObservedMismatch(
                    title='Incidentes tecnicos recientes',
                    expected='La tarea deberia avanzar sin incidentes dominantes.',
                    observed=f'Veo incidentes como {dominant}.',
                    probable_cause='El sistema sigue arrastrando un problema tecnico repetido en el navegador, bridge o restauracion.',
                    severity=IssueSeverity.HIGH if dominant in {'navigation_stall', 'capture_starvation'} else IssueSeverity.MEDIUM,
                    category=DiagnosticCategory.NEED_RUNTIME_TUNING if tunable else DiagnosticCategory.NEED_CODEX_FIX,
                    evidence_refs=list(session.evidence_refs[:4]),
                    metadata={'incident_kind': dominant},
                )
            )
        if missing_adapter:
            mismatches.append(
                ObservedMismatch(
                    title='No hay adaptador operativo real',
                    expected='La fase execute deberia tener un adaptador ejecutable cuando el escenario ya esta listo.',
                    observed='El playbook sigue listo o simulable, pero no hay un ejecutor real del dominio conectado.',
                    probable_cause='La tarea ya esta planificada, pero el adaptador operativo del navegador o del dominio aun no existe o no fue cableado.',
                    severity=IssueSeverity.HIGH,
                    category=DiagnosticCategory.NEED_ADAPTER,
                    evidence_refs=list(session.evidence_refs[:4]),
                )
            )
        if low_visual:
            mismatches.append(
                ObservedMismatch(
                    title='La evidencia visual sigue debil',
                    expected='Los objetos criticos del flujo deberian verse alineados y con cobertura suficiente.',
                    observed='Los scores visuales recientes siguen bajos para login o navegacion.',
                    probable_cause='El replay visual o la captura aun no estan mostrando bien correo, contrasena, submit o transicion.',
                    severity=IssueSeverity.HIGH,
                    category=DiagnosticCategory.NEED_TEACHING,
                    evidence_refs=list(session.evidence_refs[:4]),
                )
            )

        if repeated_technical and low_visual and weak_capabilities:
            category = DiagnosticCategory.NEED_CODEX_FIX
            summary = 'La tarea sigue fallando por una mezcla de evidencia debil e incidentes tecnicos repetidos; ya no parece solo falta de ensenanza.'
            cause = 'Las capacidades operativas siguen flojas y, ademas, hay problemas tecnicos repetidos en bridge, navegacion o restauracion.'
            confidence = 0.91
        elif tunable:
            category = DiagnosticCategory.NEED_RUNTIME_TUNING
            summary = 'Hay un problema tecnico repetido que todavia se puede intentar ajustar por runtime antes de escalar a codigo.'
            cause = f'Los incidentes recientes ({", ".join(tunable[:2])}) apuntan a thresholds o defaults ajustables.'
            confidence = 0.83
        elif weak_capabilities or low_visual:
            category = DiagnosticCategory.NEED_TEACHING
            # Distinguir "falta de captura / runner no corrió" (INSUFFICIENT
            # sin evidencia) vs. "captura débil" (PARTIAL con algún marker). En
            # el primer caso el placeholder genérico no ayuda a nadie: el
            # caller recibe "Todavia faltan pasos visibles" cuando el problema
            # real es que NO hay ningún signal todavía (probablemente el
            # capability runner no está registrado o no se ejecutó).
            insufficient_items = [
                item
                for item in weak_capabilities
                if item.status == CapabilityStatus.INSUFFICIENT
            ]
            evidence_present = bool(
                session.evidence_refs
                or any((item.evidence or []) for item in weak_capabilities)
            )
            if insufficient_items and not evidence_present and not low_visual:
                lead = insufficient_items[0]
                missing_ids = ", ".join(
                    item.capability_id for item in insufficient_items[:3]
                )
                summary = (
                    "La app no tiene ningún signal reciente para las "
                    "capacidades requeridas; el runner o la captura nunca "
                    "llegaron a emitir evidencia."
                )
                cause = (
                    f"Capacidades en estado INSUFFICIENT sin evidencia "
                    f"reciente ({missing_ids}). Probablemente el capability "
                    f"runner de '{lead.capability_id}' no está registrado, "
                    f"o el TeachingStudio no capturó el microflujo todavía. "
                    f"Sin runner + captura previos, el pack sensible no "
                    f"puede emitir UniversalPerceptionSignal."
                )
                confidence = 0.82
            else:
                summary = 'La app aun no tiene suficiente evidencia reciente para ejecutar esta tarea con confianza.'
                cause = 'Todavia faltan pasos visibles, cobertura visual o una ensenanza mas limpia del flujo.'
                confidence = 0.78
        elif missing_adapter:
            category = DiagnosticCategory.NEED_ADAPTER
            summary = 'La intencion y el plan ya estan bien, pero sigue faltando el adaptador operativo que ejecute la fase real.'
            cause = 'El playbook llega a execute sin un ejecutor operativo real del dominio.'
            confidence = 0.89
        else:
            category = DiagnosticCategory.READY_FOR_GUIDED_LIVE
            summary = 'La tarea se ve suficientemente comprendida para una prueba guiada con aprobacion.'
            cause = 'La evidencia reciente, el pack y el playbook estan alineados.'
            confidence = 0.74
        return category, mismatches, summary, cause, confidence
