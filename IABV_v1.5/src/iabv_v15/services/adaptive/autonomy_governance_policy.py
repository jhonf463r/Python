from __future__ import annotations

import json
import time
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSessionStatus,
    CapabilityReadiness,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExternalStateFlag,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
    GoalContext,
    IssueSeverity,
    RuntimeAdjustment,
    RuntimeTuningProfile,
    WorldModelSnapshot,
    canonical_external_state_flags,
    utc_now,
)


class AutonomyGovernancePolicy:
    """Central policy for deciding when the system should act, consult, retry or replan."""

    _TECHNICAL_INCIDENTS = {
        'bridge_lag',
        'navigation_stall',
        'session_restore_weak',
        'visual_alignment_weak',
        'critical_object_missing',
    }

    def __init__(
        self,
        *,
        allow_parallel_comparison: bool = True,
        operational_budget_thresholds: dict[str, Any] | None = None,
    ) -> None:
        # Flag que habilita el cotejo en paralelo de IAs externas sobre el mismo
        # ``SynapticRoutingDecision``. Por defecto encendido: la politica es
        # descriptiva y el cotejo no ejecuta rutas operativas, solo prepara /
        # compara consultas via ``AutonomousEvolutionService``. Los tests o el
        # bootstrap pueden apagarlo para forzar ruta IA unica.
        self.allow_parallel_comparison = bool(allow_parallel_comparison)
        self._operational_budget_threshold_source = 'compiled_defaults'
        self._operational_budget_thresholds = _normalize_operational_budget_thresholds(
            operational_budget_thresholds,
        )
        if operational_budget_thresholds:
            self._operational_budget_threshold_source = 'runtime_constructor'

    def operational_budget_thresholds(self) -> dict[str, float]:
        """Return the effective runtime thresholds used by the budget gate."""

        return dict(self._operational_budget_thresholds)

    def configure_operational_budget_thresholds(
        self,
        thresholds: dict[str, Any] | None,
        *,
        source: str = 'runtime_tuning',
    ) -> dict[str, float]:
        """Apply governed operational-budget thresholds to this policy instance."""

        self._operational_budget_thresholds = _normalize_operational_budget_thresholds(thresholds)
        self._operational_budget_threshold_source = str(source or 'runtime_tuning')
        return self.operational_budget_thresholds()

    def apply_runtime_tuning_profile(
        self,
        profile: RuntimeTuningProfile | Any | None,
    ) -> dict[str, float]:
        """Load operational-budget thresholds from an existing tuning profile."""

        if profile is None:
            self._operational_budget_thresholds = _normalize_operational_budget_thresholds(None)
            self._operational_budget_threshold_source = 'compiled_defaults'
            return self.operational_budget_thresholds()
        metadata = dict(getattr(profile, 'metadata', {}) or {})
        payload = metadata.get('operational_budget_thresholds') or {}
        thresholds: dict[str, Any] = {}
        if isinstance(payload, dict):
            raw = payload.get('thresholds') or payload.get('recommended_thresholds') or payload
            if isinstance(raw, dict):
                thresholds = raw
        return self.configure_operational_budget_thresholds(
            thresholds,
            source='runtime_tuning_profile',
        )

    def allow_parallel_ia_comparison(self) -> tuple[bool, str | None]:
        """Gate para ``AdaptiveTaskOrchestrator._parallel_ia_comparison``.

        Retorna ``(allowed, reason_if_blocked)``. Si ``allow_parallel_comparison``
        esta apagado, bloquea y deja el motivo; el orquestador debe entonces
        caer al camino de IA unica (comportamiento previo) sin romper.
        """

        if not self.allow_parallel_comparison:
            return False, 'parallel_ia_comparison deshabilitado por politica.'
        return True, None

    def allow_git_sync(self) -> tuple[bool, str | None]:
        """Gate for infrastructure-level git sync (``GitSyncService``).

        Returns ``(allowed, reason_if_blocked)``. Default is to allow — the
        actual safety is enforced by ``GitSyncService`` itself (clean tree,
        no local unpushed commits, fast-forward only). Override in tests or
        replace at runtime to impose maintenance windows or emergency halts.
        """

        return True, None

    _OPERATIONAL_FOREGROUND_CLASSES = {
        'foreground_response',
        'interaction_lifecycle',
        'visible_ui_update',
        'human_approval',
        'watchdog',
    }
    _OPERATIONAL_BACKGROUND_CLASSES = {
        'autonomy_dock_refresh',
        'ui_refresh',
        'idle_self_test',
        'deep_scan',
        'metacognition',
        'tool_scan',
        'branch_cleanup',
    }
    _OPERATIONAL_CRITICAL_RSS_MB = 6000.0
    _OPERATIONAL_HIGH_RSS_MB = 2500.0
    _OPERATIONAL_STALL_MS = 5000.0
    _OPERATIONAL_IDLE_REST_WINDOW_S = 120.0

    def evaluate_operational_budget(
        self,
        *,
        work_class: str,
        source: str = '',
        priority: str = 'normal',
        user_waiting: bool = False,
        query_pending: bool = False,
        rss_mb: float = 0.0,
        recent_stall_ms: float = 0.0,
        event_loop_lag_ms: float = 0.0,
        idle_seconds: float = 0.0,
        background_active: bool = False,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Budget gate for routine organs that must not starve the UI.

        This is the small "metabolic" rule set used by UI refreshes, idle
        self-tests and other auxiliary work.  It does not decide user intent
        and it does not replace the orchestrator; it only answers whether a
        work item is allowed in the current resource/attention window.
        """

        work = str(work_class or '').strip().lower() or 'unknown'
        src = str(source or '').strip().lower()
        prio = str(priority or 'normal').strip().lower()
        try:
            rss = max(0.0, float(rss_mb or 0.0))
        except Exception:
            rss = 0.0
        try:
            stall = max(float(recent_stall_ms or 0.0), float(event_loop_lag_ms or 0.0), 0.0)
        except Exception:
            stall = 0.0
        try:
            idle = max(0.0, float(idle_seconds or 0.0))
        except Exception:
            idle = 0.0
        try:
            conf = max(0.0, min(float(confidence or 0.0), 1.0))
        except Exception:
            conf = 0.0

        foreground = work in self._OPERATIONAL_FOREGROUND_CLASSES
        evidence = {
            'source': src,
            'priority': prio,
            'user_waiting': bool(user_waiting),
            'query_pending': bool(query_pending),
            'rss_mb': round(rss, 1),
            'recent_stall_ms': round(stall, 1),
            'idle_seconds': round(idle, 1),
            'background_active': bool(background_active),
            'confidence': round(conf, 3),
        }
        thresholds = self.operational_budget_thresholds()
        critical_rss_mb = float(thresholds.get('critical_rss_mb') or self._OPERATIONAL_CRITICAL_RSS_MB)
        high_rss_mb = float(thresholds.get('high_rss_mb') or self._OPERATIONAL_HIGH_RSS_MB)
        stall_ms = float(thresholds.get('stall_ms') or self._OPERATIONAL_STALL_MS)
        idle_rest_window_s = float(thresholds.get('idle_rest_window_s') or self._OPERATIONAL_IDLE_REST_WINDOW_S)

        def _budget(
            decision: str,
            reason: str,
            *,
            defer_seconds: float = 0.0,
            recommended_mode: str = 'normal',
        ) -> dict[str, Any]:
            return {
                'decision': decision,
                'allowed': decision == 'allow',
                'reason': reason,
                'work_class': work,
                'priority': prio,
                'recommended_mode': recommended_mode,
                'defer_seconds': round(max(0.0, defer_seconds), 1),
                'evidence': evidence,
                'decision_source': 'autonomy_governance_policy.operational_budget',
                'threshold_source': self._operational_budget_threshold_source,
                'effective_thresholds': thresholds,
            }

        if conf < 0.45 and work in {'external_action', 'destructive_action', 'branch_cleanup'}:
            return _budget('ask_user', 'confidence_too_low_for_action')

        if (user_waiting or query_pending) and not foreground:
            return _budget('defer', 'visible_query_wait_active', defer_seconds=30.0)

        if bool(background_active) and not foreground:
            return _budget('defer', 'startup_or_background_active', defer_seconds=20.0)

        if stall >= stall_ms and not foreground:
            return _budget('defer', f'recent_ui_stall:{int(stall)}ms', defer_seconds=30.0)

        if rss >= critical_rss_mb and not foreground:
            return _budget('defer', 'resource_pressure_critical', defer_seconds=60.0)

        if rss >= high_rss_mb and not foreground:
            return _budget('defer', 'resource_pressure_high', defer_seconds=30.0)

        rest_window_required = (
            work in {'autonomy_dock_refresh', 'ui_refresh', 'idle_self_test', 'deep_scan', 'metacognition', 'tool_scan'}
            and src != 'user_click'
            and prio not in {'critical', 'foreground'}
        )
        if rest_window_required and idle < idle_rest_window_s:
            return _budget(
                'defer',
                'rest_window_not_reached',
                defer_seconds=idle_rest_window_s - idle,
                recommended_mode='wait_for_idle',
            )

        if work in {'idle_self_test', 'deep_scan', 'metacognition', 'tool_scan'} and prio not in {'critical'}:
            return _budget('allow', 'idle_rest_window_available', recommended_mode='background_idle')

        return _budget('allow', 'budget_available')

    # --- Reglas Nivel 1 para auto-merge gobernado de PRs via GitHubApiToolAdapter.
    # El control fino lo siguen haciendo los ToolAdapters y GitHub (CI, branch
    # protection), pero este metodo deja explicita la decision de politica para
    # que el orquestador y ExperimentLab puedan auditarla.

    _GITHUB_MERGE_MAX_TOTAL_LINES = 200
    _GITHUB_MERGE_MAX_FILES_CHANGED = 15
    _GITHUB_MERGE_SENSITIVE_PATH_PREFIXES = (
        'src/iabv_v15/bootstrap',
        'src/iabv_v15/domain/models',
        'src/iabv_v15/services/adaptive/autonomy_governance_policy',
        'src/iabv_v15/services/adaptive/adaptive_task_orchestrator',
        'src/iabv_v15/infra/persistence',
        '.github/workflows',
        'AGENTS.md',
    )

    def allow_github_merge(
        self,
        *,
        pr_metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """Gate for automated PR merge via ``GitHubApiToolAdapter.merge_pr``.

        Returns ``(allowed, reason_if_blocked)``. Default is to **block**
        (requires human approval) unless ``pr_metadata`` demonstrates every
        Nivel-1 precondition holds:

        - CI status = ``success``.
        - No review marked ``CHANGES_REQUESTED``.
        - Not a draft PR.
        - Diff under ``_GITHUB_MERGE_MAX_TOTAL_LINES`` total (added + deleted).
        - Touches <= ``_GITHUB_MERGE_MAX_FILES_CHANGED`` files.
        - Does not touch sensitive paths (bootstrap, domain contracts, policy
          itself, workflows, AGENTS.md, or tests).

        Any missing or None field in ``pr_metadata`` is treated as "unknown"
        and blocks the merge — the system must refuse to act on partial
        evidence rather than optimistically approve.

        The adapter or caller is expected to pass a dict shaped like::

            {
                'pull_number': int,
                'ci_status': 'success' | 'pending' | 'failure',
                'reviews': [{'state': 'APPROVED' | 'CHANGES_REQUESTED' | ...}],
                'draft': bool,
                'additions': int,
                'deletions': int,
                'changed_files': int,
                'changed_paths': [str],
            }

        This keeps governance declarative and auditable from
        ``ExperimentLab`` without embedding GitHub REST semantics in the
        policy. Override in tests or replace at runtime to impose additional
        guards (maintenance windows, frozen-branch rules, etc.).
        """

        if not isinstance(pr_metadata, dict) or not pr_metadata:
            return False, 'pr_metadata ausente: sin evidencia no se auto-mergea.'

        if bool(pr_metadata.get('draft')):
            return False, 'PR en estado draft: no se auto-mergea.'

        ci_status = str(pr_metadata.get('ci_status') or '').strip().lower()
        if ci_status != 'success':
            return False, f"CI no esta en verde (ci_status={ci_status or 'desconocido'})."

        reviews = pr_metadata.get('reviews')
        if reviews is None:
            return False, 'reviews ausente: sin evidencia de revisiones no se auto-mergea.'
        if not isinstance(reviews, list):
            return False, 'reviews no es una lista.'
        for review in reviews:
            if not isinstance(review, dict):
                continue
            state = str(review.get('state') or '').strip().upper()
            if state == 'CHANGES_REQUESTED':
                return False, 'Hay un review con changes_requested: debe resolverse antes de mergear.'

        additions = pr_metadata.get('additions')
        deletions = pr_metadata.get('deletions')
        if not isinstance(additions, int) or not isinstance(deletions, int):
            return False, 'Diff size desconocido (additions/deletions faltantes).'
        total_lines = additions + deletions
        if total_lines > self._GITHUB_MERGE_MAX_TOTAL_LINES:
            return False, (
                f'Diff demasiado grande ({total_lines} lineas > '
                f'{self._GITHUB_MERGE_MAX_TOTAL_LINES}): requiere revision humana.'
            )

        changed_files = pr_metadata.get('changed_files')
        if not isinstance(changed_files, int):
            return False, 'changed_files desconocido.'
        if changed_files > self._GITHUB_MERGE_MAX_FILES_CHANGED:
            return False, (
                f'Demasiados archivos tocados ({changed_files} > '
                f'{self._GITHUB_MERGE_MAX_FILES_CHANGED}): requiere revision humana.'
            )

        changed_paths = pr_metadata.get('changed_paths')
        if changed_paths is None:
            return False, 'changed_paths ausente: sin evidencia de rutas no se auto-mergea.'
        if not isinstance(changed_paths, list):
            return False, 'changed_paths no es una lista.'
        for raw_path in changed_paths:
            path = str(raw_path or '').strip().lstrip('/').replace('\\', '/')
            if not path:
                continue
            if path.startswith('tests/') or '/tests/' in f'/{path}':
                return False, f'Toca archivo de tests ({path}): no se auto-mergea sin revision humana.'
            for prefix in self._GITHUB_MERGE_SENSITIVE_PATH_PREFIXES:
                if path.startswith(prefix):
                    return False, f'Toca ruta sensible ({path}): requiere aprobacion humana.'

        return True, None

    # --- Reglas Nivel 1 para apertura automatica de PRs via GitHubRemoteService.
    # A diferencia de `allow_github_merge`, aqui decidimos si IABV puede EMPEZAR
    # a publicar una rama. El criterio es por PATRON DE RAMA + tamano de diff:
    #
    #   * main / master         : push directo bloqueado, siempre.
    #   * iabv-auto/*           : IABV abrio la rama por su cuenta -> puede abrir
    #                             PR sin preguntar si el diff esta acotado.
    #   * devin/*               : rama de una sesion Devin asistida -> requiere
    #                             aprobacion humana (la sesion es auditada, pero
    #                             el salto a "PR publico" es decision humana).
    #   * otros patrones        : bloqueado por defecto; debe aprobarse caso a caso.
    #
    # `allow_github_pr_open` decide SI la apertura es auto-aprobada. Si devuelve
    # `(False, reason)` el caller debe pedir aprobacion humana via
    # `HumanApprovalBroker` antes de llamar a `GitHubApiToolAdapter.create_pr`.

    _GITHUB_PR_OPEN_AUTO_MAX_LINES = 200

    def allow_github_pr_open(
        self,
        *,
        branch: str,
        base: str = 'main',
        diff_lines: int | None = None,
    ) -> tuple[bool, str | None]:
        """Gate for ``GitHubRemoteService.publish_branch_as_pr``.

        Returns ``(auto_approved, reason_if_needs_human)``.

        - ``auto_approved=True`` -> IABV puede llamar ``create_pr`` sin
          pasar por ``HumanApprovalBroker``.
        - ``auto_approved=False`` -> el caller debe solicitar aprobacion
          humana (razon explicita en el segundo valor) antes de crear el PR.

        Reglas:
        - Base distinto de ``main`` / ``master`` -> bloquea auto (requiere
          aprobacion): no auto-aprobamos PRs hacia ramas arbitrarias.
        - Rama ``main``/``master``/``HEAD``/vacia -> bloquea siempre (no es
          un head valido para un PR).
        - Rama ``iabv-auto/*`` -> auto si ``diff_lines`` conocido y
          ``<= _GITHUB_PR_OPEN_AUTO_MAX_LINES``. Si falta el dato o excede,
          requiere humano.
        - Rama ``devin/*`` -> requiere humano siempre.
        - Otros patrones -> requiere humano siempre.
        """

        head = str(branch or '').strip()
        base_name = str(base or '').strip().lower()
        if not head:
            return False, 'branch vacio: no se puede abrir un PR sin head.'
        head_lower = head.lower()
        if head_lower in {'main', 'master', 'head'}:
            return False, f'branch {head!r}: no se puede abrir un PR contra si mismo.'
        if base_name not in {'main', 'master'}:
            return False, (
                f'base {base!r} no es main/master: requiere aprobacion humana '
                'antes de auto-publicar.'
            )

        if head_lower.startswith('iabv-auto/'):
            if not isinstance(diff_lines, int):
                return False, 'diff_lines desconocido: sin evidencia de tamano no se auto-publica.'
            if diff_lines < 0:
                return False, 'diff_lines negativo: evidencia invalida.'
            if diff_lines > self._GITHUB_PR_OPEN_AUTO_MAX_LINES:
                return False, (
                    f'Diff demasiado grande ({diff_lines} lineas > '
                    f'{self._GITHUB_PR_OPEN_AUTO_MAX_LINES}): requiere revision humana.'
                )
            return True, None

        if head_lower.startswith('devin/'):
            return False, (
                f'branch devin/* ({head}): rama asistida, la apertura del PR '
                'requiere aprobacion humana explicita.'
            )

        return False, (
            f'branch {head!r}: patron no reconocido para auto-apertura; '
            'requiere aprobacion humana.'
        )

    def evaluate(
        self,
        *,
        user_goal: str,
        session_status: str,
        session_readiness: dict[str, Any],
        live_audit: dict[str, Any],
        assistant_guidance: dict[str, Any],
        capability_snapshot: list[CapabilityReadiness],
        approval_pending: bool,
        goal_context: GoalContext | dict[str, Any] | None = None,
        intent_key: str = '',
        intent_disposition: str = '',
        external_state_flags: list[str] | None = None,
        preferred_assistant_kind: str = '',
        preferred_config_signature: str = '',
        supporting_trace_ids: list[str] | None = None,
        blocked_assistants: list[str] | None = None,
        environment_self_model: EnvironmentSelfModel | dict[str, Any] | None = None,
        world_model: WorldModelSnapshot | dict[str, Any] | None = None,
        ambiguity_score: float = 0.0,
        requires_clarification: bool = False,
        sub_intents: list[str] | None = None,
    ) -> dict[str, Any]:
        goal = self._normalize_goal_context(goal_context)
        environment = self._normalize_environment_self_model(environment_self_model)
        world = self._normalize_world_model(world_model)
        progress = float(goal.get('progress') or 0.0)
        blocker = str(goal.get('blocker') or '').strip()
        goal_status = str(goal.get('status') or '').strip().lower()
        goal_confidence = float(goal.get('confidence') or 0.0)
        external_states = canonical_external_state_flags(external_state_flags)
        historical_assistant = str(preferred_assistant_kind or '').strip().lower()
        blocked_assistant_set = {
            str(item or '').strip().lower()
            for item in (blocked_assistants or [])
            if str(item or '').strip()
        }
        if historical_assistant in blocked_assistant_set:
            historical_assistant = ''

        # ETAPA 2: Ambiguity and clarification check
        if requires_clarification or ambiguity_score > 0.75:
            sub_intents_list = sub_intents or []
            reason = 'Ambigüedad conversacional detectada. El mensaje tiene múltiples intenciones o no es suficientemente claro.'
            if requires_clarification and sub_intents_list:
                reason = f'Detecté varias intenciones: {", ".join(sub_intents_list[:3])}. Necesito que aclares cuál quieres que atienda primero.'
            elif ambiguity_score > 0.75:
                reason = f'Ambigüedad alta (score: {ambiguity_score:.2f}). Por favor, aclara tu petición antes de proceder.'
            return self._snapshot(
                autonomy_level='clarification_needed',
                recommended_action='solicitar_clarificacion',
                reason=reason,
                confidence=0.0,
                should_consult=True,
                blockers=[reason],
                diagnostic_category='conversation_ambiguity',
            )

        guidance_mode = str(assistant_guidance.get('mode') or '').strip().lower()
        live_action = str(session_readiness.get('live_audit_action') or live_audit.get('decision_action') or '').strip().lower()
        summary = str(live_audit.get('summary') or assistant_guidance.get('prompt') or '').strip()
        dominant_incident = str(session_readiness.get('dominant_incident') or '').strip()
        weak_capabilities = [item for item in capability_snapshot if item.status.value in {'insufficient', 'partial'}]

        blockers: list[str] = []
        if blocker:
            blockers.append(blocker)
        if weak_capabilities:
            blockers.append(str(weak_capabilities[0].suggested_next_step or weak_capabilities[0].title or 'Hay capacidades debiles en la ruta actual.'))
        if approval_pending:
            blockers.append('La siguiente fase requiere aprobacion humana antes de continuar.')

        normalized_goal = ' '.join(str(user_goal or '').lower().split())
        conversational_prompt = (
            any(phrase in normalized_goal for phrase in (
                'que sabes hacer',
                'qué sabes hacer',
                'que puedes hacer',
                'qué puedes hacer',
                'en que puedes ayudar',
                'en qué puedes ayudar',
                'quien eres',
                'quién eres',
                'como funcionas',
                'cómo funcionas',
            ))
            or (len(normalized_goal.split()) <= 4 and any(normalized_goal.startswith(prefix) for prefix in ('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches')))
        )
        meta_assistant_prompt = (
            any(token in normalized_goal for token in ('codex', 'chatgpt', 'claude', 'ollama', 'devin', 'windsurf', 'ia', 'ias'))
            and any(token in normalized_goal for token in ('sabes', 'puedes', 'puedo', 'internamente', 'automatic', 'automatica', 'automático', 'respondieron'))
        )
        conversational_intent = (
            intent_key in {'general.assistance', 'knowledge.query'}
            and intent_disposition in {'answer_now', 'need_info'}
            and (conversational_prompt or meta_assistant_prompt)
        )
        explicit_assistant = self._explicit_assistant_request(normalized_goal)
        technical_pressure = guidance_mode in {'need_codex_fix', 'need_adapter'} or live_action == 'consult_codex' or (dominant_incident in self._TECHNICAL_INCIDENTS and bool(weak_capabilities))
        teaching_pressure = guidance_mode == 'need_teaching'
        failed_or_blocked = session_status in {
            AdaptiveSessionStatus.FAILED.value,
            AdaptiveSessionStatus.ABORTED.value,
            AdaptiveSessionStatus.NEED_INFO.value,
        }
        ready_but_guarded = session_status in {
            AdaptiveSessionStatus.READY_TO_EXECUTE.value,
            AdaptiveSessionStatus.EXECUTING.value,
        }
        progress_conflict = progress >= 0.8 and failed_or_blocked

        confidence = max(
            min(goal_confidence, 1.0),
            min(float(live_audit.get('confidence') or 0.0), 1.0),
            0.45 if ready_but_guarded else 0.35,
        )

        environment_guard = self._environment_guard(
            environment=environment,
            confidence=confidence,
            blockers=blockers,
            diagnostic_category=guidance_mode,
            external_state_flags=external_states,
        )
        if environment_guard is not None:
            return environment_guard

        world_model_guard = self._world_model_guard(
            world_model=world,
            confidence=confidence,
            blockers=blockers,
            diagnostic_category=guidance_mode,
            external_state_flags=external_states,
            explicit_assistant=explicit_assistant,
            historical_assistant=historical_assistant,
            technical_pressure=technical_pressure,
        )
        if world_model_guard is not None:
            return world_model_guard

        if approval_pending or session_status == AdaptiveSessionStatus.WAITING_APPROVAL.value:
            return self._snapshot(
                autonomy_level='human_gate',
                recommended_action='stop_and_wait_user',
                reason='La estrategia necesita aprobacion humana antes de seguir.',
                confidence=max(confidence, 0.82),
                approval_required=True,
                block_risky_action=True,
                require_sandbox=False,
                blockers=blockers,
                diagnostic_category=guidance_mode,
                external_state_flags=external_states,
            )

        if ExternalStateFlag.ACCOUNT_LIMITED.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason='La ruta externa quedo limitada por cuenta o cuota. IABV debe avisarlo con claridad y seguir con la mejor via local disponible mientras se resuelve el acceso.',
                confidence=max(confidence, 0.86),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[*blockers, 'La cuenta o cuota del asistente externo no permite continuar con esta ruta.'],
                diagnostic_category=guidance_mode or 'account_limited',
                external_state_flags=external_states,
            )

        if ExternalStateFlag.SESSION_EXPIRED.value in external_states or ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason='La sesion externa no quedo lista para seguir. IABV debe informar el bloqueo y continuar por la mejor via local mientras la sesion se recupera.',
                confidence=max(confidence, 0.84),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[*blockers, 'La sesion del asistente externo no quedo lista para continuar.'],
                diagnostic_category=guidance_mode or 'session_recovery',
                external_state_flags=external_states,
            )

        if ExternalStateFlag.WRONG_THREAD.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action='audit_autonomy',
                reason='La consulta externa parece estar asociada al hilo incorrecto y no debe darse por valida.',
                confidence=max(confidence, 0.81),
                research_needed=True,
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, 'La verificacion del hilo externo no coincide con lo esperado.'],
                diagnostic_category=guidance_mode or 'wrong_thread',
                external_state_flags=external_states,
            )

        if ExternalStateFlag.CAPTURE_UNVERIFIED.value in external_states:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='audit_autonomy',
                reason='La respuesta externa no quedo verificada con suficiente evidencia de captura.',
                confidence=max(confidence, 0.73),
                should_retry=True,
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, 'La captura de la respuesta externa sigue sin verificacion suficiente.'],
                diagnostic_category=guidance_mode or 'capture_unverified',
                external_state_flags=external_states,
            )

        if conversational_intent:
            return self._snapshot(
                autonomy_level='autonomous_local',
                recommended_action='continue_local',
                reason='La consulta actual es conversacional y debe resolverse localmente sin escalar incidentes tecnicos previos.',
                confidence=max(confidence, 0.72),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[],
                diagnostic_category=guidance_mode,
                external_state_flags=external_states,
            )

        if explicit_assistant:
            explicit_action = self._consult_action_for_assistant(explicit_assistant)
            return self._snapshot(
                autonomy_level='guarded_research' if explicit_assistant != 'ollama' else 'autonomous_local',
                recommended_action=explicit_action,
                reason=f'El usuario pidio una consulta externa dirigida a {explicit_assistant}; esa preferencia debe respetarse antes de reciclar incidentes o rutas previas.',
                confidence=max(confidence, 0.78),
                should_consult=True,
                research_needed=explicit_assistant != 'ollama',
                assistant_kind=explicit_assistant,
                approval_required=False,
                block_risky_action=False,
                require_sandbox=explicit_assistant == 'codex',
                blockers=blockers,
                diagnostic_category='explicit_external_consultation',
                external_state_flags=external_states,
            )

        if technical_pressure:
            consult_assistant = historical_assistant or 'codex'
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action=self._consult_action_for_assistant(consult_assistant),
                reason=(
                    f"{summary or 'La evidencia tecnica actual justifica una consulta externa verificable.'} "
                    f"El historico reciente favorece {consult_assistant}."
                ).strip() if historical_assistant else (summary or 'La evidencia tecnica actual justifica una consulta externa verificable.'),
                confidence=max(confidence, 0.74),
                should_consult=True,
                research_needed=consult_assistant != 'ollama',
                assistant_kind=consult_assistant,
                approval_required=False,
                block_risky_action=False,
                require_sandbox=consult_assistant == 'codex',
                blockers=blockers,
                diagnostic_category=guidance_mode or 'need_codex_fix',
                external_state_flags=external_states,
            )

        if teaching_pressure and ('explica' in user_goal.lower() or live_action == 'consult_chatgpt'):
            consult_assistant = historical_assistant or 'chatgpt'
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action=self._consult_action_for_assistant(consult_assistant),
                reason=(
                    f"{summary or 'Conviene contrastar el siguiente microajuste con una explicacion externa antes de reensenar.'} "
                    f"El historico reciente favorece {consult_assistant}."
                ).strip() if historical_assistant else (summary or 'Conviene contrastar el siguiente microajuste con una explicacion externa antes de reensenar.'),
                confidence=max(confidence, 0.68),
                should_consult=True,
                research_needed=consult_assistant != 'ollama',
                assistant_kind=consult_assistant,
                approval_required=False,
                block_risky_action=False,
                require_sandbox=consult_assistant == 'codex',
                blockers=blockers,
                diagnostic_category='need_teaching',
                external_state_flags=external_states,
            )

        if failed_or_blocked or progress_conflict or goal_status == 'blocked' or live_action in {'retry_after_rebuild', 'rebuild_learning'}:
            replan_reason = summary or 'La estrategia actual no consolido el objetivo y conviene replanificar sin perder contexto.'
            if progress_conflict:
                replan_reason = 'El objetivo figura muy avanzado, pero la ultima ejecucion no valido ese progreso. Conviene replanificar y verificar evidencia.'
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='replan_strategy',
                reason=replan_reason,
                confidence=max(confidence, 0.72),
                should_replan=True,
                should_retry=live_action == 'retry_after_rebuild',
                approval_required=False,
                block_risky_action=bool(blocker),
                require_sandbox=True,
                blockers=blockers,
                diagnostic_category=guidance_mode or 'replan',
                external_state_flags=external_states,
            )

        if ready_but_guarded:
            return self._snapshot(
                autonomy_level='guarded_execution',
                recommended_action=live_action or 'continue_local',
                reason=summary or 'La ruta local es suficiente, pero las acciones operativas deben seguir dentro del sandbox o guiadas.',
                confidence=max(confidence, 0.66),
                should_retry=live_action == 'retry_after_rebuild',
                approval_required=False,
                block_risky_action=False,
                require_sandbox=True,
                blockers=blockers,
                diagnostic_category=guidance_mode,
                external_state_flags=external_states,
            )

        return self._snapshot(
            autonomy_level='autonomous_local',
            recommended_action=live_action or 'continue_local',
            reason=summary or 'La evidencia local actual es suficiente para seguir sin escalar.',
            confidence=max(confidence, 0.6),
            should_retry=live_action == 'retry_after_rebuild',
            approval_required=False,
            block_risky_action=False,
            require_sandbox=False,
            blockers=blockers,
            diagnostic_category=guidance_mode,
            external_state_flags=external_states,
        )

    def _explicit_assistant_request(self, normalized_goal: str) -> str:
        if not normalized_goal:
            return ''
        if (
            any(token in normalized_goal for token in ('codex', 'chatgpt', 'claude', 'ollama', 'devin', 'windsurf'))
            and any(token in normalized_goal for token in ('sabes', 'puedes', 'puedo', 'internamente', 'automatic', 'automatica', 'autom?tico', 'respondieron'))
        ):
            return ''
        consult_verbs = (
            'consulta',
            'consulta externa',
            'consultar',
            'usa ',
            'utiliza ',
            'revisa con',
            'valida con',
            'pregunta a',
            'apoyate en',
            'ap?yate en',
            'razona con',
            'piensa con',
            'escala a',
            'escalalo a',
            'escalalo con',
        )
        if not any(token in normalized_goal for token in consult_verbs):
            return ''
        for assistant in ('chatgpt', 'claude', 'codex', 'ollama', 'devin', 'windsurf'):
            if assistant in normalized_goal:
                return assistant
        return ''

    def _consult_action_for_assistant(self, assistant_kind: str) -> str:
        assistant = str(assistant_kind or '').strip().lower()
        return {
            'codex': 'consult_codex',
            'chatgpt': 'consult_chatgpt',
            'claude': 'consult_claude',
            'ollama': 'consult_ollama',
            'devin': 'consult_devin',
            'windsurf': 'consult_windsurf',
        }.get(assistant, 'consult_chatgpt')

    def _snapshot(
        self,
        *,
        autonomy_level: str,
        recommended_action: str,
        reason: str,
        confidence: float,
        should_consult: bool = False,
        should_retry: bool = False,
        should_replan: bool = False,
        research_needed: bool = False,
        assistant_kind: str = '',
        approval_required: bool = False,
        block_risky_action: bool = False,
        require_sandbox: bool = False,
        blockers: list[str] | None = None,
        diagnostic_category: str = '',
        external_state_flags: list[str] | None = None,
        blocked_routes: list[str] | None = None,
        permission_gates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            'autonomy_level': autonomy_level,
            'should_consult': should_consult,
            'should_retry': should_retry,
            'should_replan': should_replan,
            'research_needed': research_needed,
            'assistant_kind': assistant_kind,
            'recommended_action': recommended_action,
            'reason': reason,
            'confidence': round(max(0.0, min(confidence, 0.99)), 4),
            'approval_required': approval_required,
            'block_risky_action': block_risky_action,
            'require_sandbox': require_sandbox,
            'blockers': [item for item in (blockers or []) if str(item).strip()][:4],
            'diagnostic_category': diagnostic_category,
            'decision_source': 'autonomy_governance_policy',
            'external_state_flags': list(external_state_flags or []),
            'blocked_routes': [item for item in (blocked_routes or []) if str(item).strip()][:6],
            'permission_gates': list(permission_gates or [])[:6],
        }

    def _environment_guard(
        self,
        *,
        environment: EnvironmentSelfModel,
        confidence: float,
        blockers: list[str],
        diagnostic_category: str,
        external_state_flags: list[str],
    ) -> dict[str, Any] | None:
        if environment is None:
            return None
        severe_risks = [
            risk for risk in environment.risk_signals
            if risk.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL}
        ]
        if not severe_risks:
            return None
        critical_kinds = {str(risk.kind or '') for risk in severe_risks}
        if not critical_kinds.intersection({'ram_critical', 'ram_pressure', 'gpu_temperature_critical', 'gpu_temperature_warning', 'cpu_pressure', 'throttling_detected'}):
            return None
        preferred_local_assistant = str(environment.ai_capacity.get('preferred_local_assistant_kind') or '').strip().lower()
        risk_notes = [risk.summary for risk in severe_risks][:3]
        return self._snapshot(
            autonomy_level='protective_local',
            recommended_action='continue_local',
            reason='El entorno actual esta bajo presion y la gobernanza debe degradar con gracia antes de lanzar trabajo mas pesado.',
            confidence=max(confidence, 0.8),
            should_consult=False,
            research_needed=False,
            assistant_kind=preferred_local_assistant if preferred_local_assistant == 'ollama' else '',
            approval_required=False,
            block_risky_action=True,
            require_sandbox=False,
            blockers=[*blockers, *risk_notes],
            diagnostic_category=diagnostic_category or 'environment_guard',
            external_state_flags=external_state_flags,
        )

    def _normalize_goal_context(self, goal_context: GoalContext | dict[str, Any] | None) -> dict[str, Any]:
        if goal_context is None:
            return {}
        if isinstance(goal_context, GoalContext):
            return goal_context.model_dump(mode='json')
        return dict(goal_context or {})

    def _normalize_environment_self_model(self, environment_self_model: EnvironmentSelfModel | dict[str, Any] | None) -> EnvironmentSelfModel:
        if isinstance(environment_self_model, EnvironmentSelfModel):
            return environment_self_model
        if isinstance(environment_self_model, dict) and environment_self_model:
            try:
                return EnvironmentSelfModel.model_validate(environment_self_model)
            except Exception:
                return EnvironmentSelfModel(scan_status='degraded')
        return EnvironmentSelfModel(scan_status='unavailable')

    def _normalize_world_model(self, world_model: WorldModelSnapshot | dict[str, Any] | None) -> WorldModelSnapshot:
        if isinstance(world_model, WorldModelSnapshot):
            return world_model
        if isinstance(world_model, dict) and world_model:
            try:
                return WorldModelSnapshot.model_validate(world_model)
            except Exception:
                return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _world_model_guard(
        self,
        *,
        world_model: WorldModelSnapshot,
        confidence: float,
        blockers: list[str],
        diagnostic_category: str,
        external_state_flags: list[str],
        explicit_assistant: str,
        historical_assistant: str,
        technical_pressure: bool,
    ) -> dict[str, Any] | None:
        if world_model is None:
            return None
        meaningful_signal = bool(
            world_model.tool_live_status
            or world_model.active_windows
            or world_model.detected_blocks
            or world_model.focused_window is not None
            or str(world_model.network_status.status or '').strip() not in {'', 'desconocido'}
        )
        if not meaningful_signal:
            return None

        assistant_hint = explicit_assistant or historical_assistant or ('codex' if technical_pressure else '')
        statuses = {
            str(item.assistant_kind or '').strip().lower(): item
            for item in (world_model.tool_live_status or [])
            if str(item.assistant_kind or '').strip()
        }
        permission_gates = [
            item for item in (world_model.permission_gates or [])
            if not assistant_hint or item.assistant_kind == assistant_hint
        ]
        if permission_gates:
            required_gate = next((item for item in permission_gates if item.status == 'requerido'), None)
            if required_gate is not None:
                required_routes = [str(item).strip() for item in (required_gate.required_for or []) if str(item).strip()]
                route_hint = required_routes[0] if required_routes else f'consult_{assistant_hint}' if assistant_hint else 'consult_external'
                return self._snapshot(
                    autonomy_level='guarded_research',
                    recommended_action='request_observation_permission',
                    reason=str(required_gate.detail or 'Necesito permiso explicito para observar el contenido visible antes de seguir con esta ruta.'),
                    confidence=max(confidence, 0.85),
                    approval_required=True,
                    block_risky_action=True,
                    require_sandbox=False,
                    blockers=[*blockers, str(required_gate.detail or 'Falta permiso para verificar la herramienta externa antes de usarla.')],
                    diagnostic_category=diagnostic_category or 'observation_permission_required',
                    external_state_flags=external_state_flags,
                    blocked_routes=[route_hint],
                    permission_gates=[item.model_dump(mode='json') for item in permission_gates],
                )

        block_records = [
            item for item in (world_model.block_records or [])
            if not assistant_hint
            or item.assistant_kind == assistant_hint
            or item.target_scope in {f'consult_{assistant_hint}', 'consult_external'}
        ]
        explicit_record = next(
            (
                item for item in block_records
                if item.block_type in {'wrong_thread', 'account_limited', 'browser_security_verification', 'assistant_unavailable', 'network_blocked'}
            ),
            None,
        )
        if explicit_record is not None:
            category = explicit_record.block_type
            reason_map = {
                'wrong_thread': f'{explicit_record.title or assistant_hint or "La herramienta"} esta abierto, pero el hilo activo no coincide con el workspace esperado.',
                'account_limited': f'{explicit_record.title or assistant_hint or "La herramienta"} muestra senales recientes de cuota, credito o mensajes agotados.',
                'browser_security_verification': f'{explicit_record.title or assistant_hint or "La herramienta"} quedo bloqueado por una verificacion de seguridad del sitio.',
                'assistant_unavailable': f'No pude confirmar que {explicit_record.title or assistant_hint or "la herramienta"} este disponible antes de usarla.',
                'network_blocked': 'La red no esta lista para sostener una consulta externa confiable en este momento.',
            }
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local' if category != 'wrong_thread' else 'audit_autonomy',
                reason=reason_map.get(category, explicit_record.reason or explicit_record.detail or 'La ruta externa no es viable en este momento.'),
                confidence=max(confidence, float(explicit_record.confidence or 0.0), 0.82),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, str(explicit_record.detail or explicit_record.reason or 'Hay un bloqueo operativo activo.')],
                diagnostic_category=diagnostic_category or category,
                external_state_flags=canonical_external_state_flags([*external_state_flags, category]),
                blocked_routes=[str(explicit_record.target_scope or '')],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )
        network = world_model.network_status
        if assistant_hint and assistant_hint != 'ollama' and network.status in {'desconectado', 'bloqueado'}:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason='La red no esta lista para sostener una consulta externa confiable en este momento.',
                confidence=max(confidence, 0.83),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, str(network.detail or 'La red no quedo disponible para esta via externa.')],
                diagnostic_category=diagnostic_category or 'network_blocked',
                external_state_flags=external_state_flags,
                blocked_routes=[f'consult_{assistant_hint}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        targeted = statuses.get(assistant_hint) if assistant_hint else None
        if targeted is None:
            return None

        targeted_blocks = canonical_external_state_flags(
            list(targeted.external_state_flags or []) + list(targeted.detected_blocks or [])
        )
        target_title = str(targeted.title or assistant_hint or 'la herramienta externa').strip()
        target_detail = str(targeted.detail or '').strip()

        if targeted.thread_status in {'otro_hilo_activo', 'sin_hilo_iabv'}:
            return self._snapshot(
                autonomy_level='guarded_research',
                recommended_action='audit_autonomy',
                reason=f'{target_title} esta abierto, pero el hilo activo no coincide con el workspace esperado.',
                confidence=max(confidence, 0.84),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'El hilo activo no coincide con el workspace de IABV.'],
                diagnostic_category=diagnostic_category or 'wrong_thread',
                external_state_flags=canonical_external_state_flags([*external_state_flags, ExternalStateFlag.WRONG_THREAD.value]),
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        if targeted.messages_status == 'agotados_o_limitados' or ExternalStateFlag.ACCOUNT_LIMITED.value in targeted_blocks:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason=f'{target_title} muestra senales recientes de limite de cuenta, cuota o mensajes agotados.',
                confidence=max(confidence, 0.86),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'La cuenta o los mensajes de esta via externa no estan disponibles ahora mismo.'],
                diagnostic_category=diagnostic_category or 'account_limited',
                external_state_flags=canonical_external_state_flags([*external_state_flags, ExternalStateFlag.ACCOUNT_LIMITED.value]),
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        if 'browser_security_verification' in targeted_blocks:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='continue_local',
                reason=f'{target_title} quedo bloqueado por una verificacion de seguridad del sitio y no conviene insistir como si fuera un selector roto.',
                confidence=max(confidence, 0.84),
                approval_required=False,
                block_risky_action=True,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'El sitio activo una verificacion de seguridad antes de abrir el chat.'],
                diagnostic_category=diagnostic_category or 'browser_security_verification',
                external_state_flags=canonical_external_state_flags([*external_state_flags, ExternalStateFlag.CAPTURE_UNVERIFIED.value]),
                blocked_routes=[f'consult_{assistant_hint or "external"}'],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        if targeted.status == 'no_disponible' and explicit_assistant:
            return self._snapshot(
                autonomy_level='guarded_local',
                recommended_action='attempt_external_with_fallback',
                reason=f'No pude confirmar que {target_title} este disponible antes de usarlo; igual intento la ruta y, si falla, lo traigo humanizado.',
                confidence=max(confidence, 0.76),
                approval_required=False,
                block_risky_action=False,
                require_sandbox=False,
                blockers=[*blockers, target_detail or 'La herramienta pedida no quedo confirmada como disponible.'],
                diagnostic_category=diagnostic_category or 'assistant_unavailable',
                external_state_flags=external_state_flags,
                blocked_routes=[],
                permission_gates=[item.model_dump(mode='json') for item in permission_gates],
            )

        return None


def record_operational_budget_experiment(
    *,
    repository: Any | None,
    budget: dict[str, Any] | None,
    observed_summary: str = '',
    evidence_refs: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    execution_ms: int = 0,
    throttle_state: dict[str, float] | None = None,
    throttle_seconds: float = 60.0,
) -> ExperimentRun | None:
    """Persist an operational-budget decision into ExperimentLab history."""

    if repository is None or not hasattr(repository, 'save_run') or not isinstance(budget, dict):
        return None
    decision = str(budget.get('decision') or '').strip().lower() or 'unknown'
    reason = str(budget.get('reason') or '').strip().lower() or 'unknown'
    work_class = str(budget.get('work_class') or 'unknown').strip().lower() or 'unknown'
    source = str(dict(budget.get('evidence') or {}).get('source') or '').strip().lower()
    signature = f'{work_class}:{source}:{decision}:{reason}'
    if throttle_state is not None:
        now = time.monotonic()
        last = float(throttle_state.get(signature, 0.0) or 0.0)
        if last > 0.0 and (now - last) < float(throttle_seconds or 0.0):
            return None
        throttle_state[signature] = now

    evidence = dict(budget.get('evidence') or {})
    confidence = _clamp_float(evidence.get('confidence'), default=0.5)
    allowed = bool(budget.get('allowed'))
    protective = 1.0 if decision in {'defer', 'ask_user'} and reason != 'budget_available' else 0.55
    progress = 1.0 if allowed else 0.35 if decision == 'defer' else 0.2
    metric = ExperimentMetric(
        precision=confidence,
        robustness=protective,
        user_progress=progress,
        execution_ms=max(0, int(execution_ms or 0)),
        total_score=round((confidence * 0.45) + (protective * 0.35) + (progress * 0.20), 4),
        metadata={
            'budget_decision': decision,
            'budget_reason': reason,
            'work_class': work_class,
            'allowed': allowed,
        },
    )
    summary = (observed_summary or f'{work_class} -> {decision}:{reason}')[:240]
    run = ExperimentRun(
        domain=ExperimentDomain.ALGORITHM,
        suite_name='operational_budget',
        objective='Regular trabajo interno sin bloquear la experiencia visible',
        subject_key=f'operational_budget:{work_class}',
        comparison_scope_key='operational_budget',
        route=EvaluationRoute.BACKGROUND,
        assistant_kind='iabv_self',
        config_signature='autonomy_governance_policy.operational_budget',
        candidate_label=f'{decision}:{reason}'[:120],
        success=decision in {'allow', 'defer', 'ask_user'},
        expected_summary='Decidir si un organo interno puede trabajar ahora o debe esperar.',
        observed_summary=summary,
        metrics=metric,
        evidence_refs=list(evidence_refs or []),
        metadata={
            **dict(metadata or {}),
            'suite_name': 'operational_budget',
            'assistant_kind': 'iabv_self',
            'comparison_scope_key': 'operational_budget',
            'operational_budget': budget,
            'budget_decision': decision,
            'budget_reason': reason,
            'work_class': work_class,
            'source': source,
            'outcome_summary': summary,
        },
    )
    try:
        return repository.save_run(run)
    except Exception:
        return None


_OPERATIONAL_BUDGET_THRESHOLD_BOUNDS: dict[str, tuple[float, float]] = {
    'critical_rss_mb': (1500.0, 20000.0),
    'high_rss_mb': (500.0, 15000.0),
    'stall_ms': (500.0, 60000.0),
    'idle_rest_window_s': (10.0, 1800.0),
}


def _normalize_operational_budget_thresholds(
    thresholds: dict[str, Any] | None,
) -> dict[str, float]:
    """Return safe operational-budget thresholds with bounded overrides."""

    defaults = operational_budget_default_thresholds()
    normalized = dict(defaults)
    raw = dict(thresholds or {})
    for key, (minimum, maximum) in _OPERATIONAL_BUDGET_THRESHOLD_BOUNDS.items():
        if key not in raw:
            continue
        try:
            value = float(raw.get(key))
        except Exception:
            continue
        if value <= 0:
            continue
        normalized[key] = round(max(minimum, min(maximum, value)), 1)
    if normalized['critical_rss_mb'] < normalized['high_rss_mb']:
        normalized['critical_rss_mb'] = normalized['high_rss_mb']
    return normalized


def operational_budget_default_thresholds() -> dict[str, float]:
    """Return the currently compiled guardrail thresholds.

    The returned values are observational metadata, not mutable state.  Runtime
    tuning may recommend different values, but applying them remains a separate
    governed step.
    """

    return {
        'critical_rss_mb': AutonomyGovernancePolicy._OPERATIONAL_CRITICAL_RSS_MB,
        'high_rss_mb': AutonomyGovernancePolicy._OPERATIONAL_HIGH_RSS_MB,
        'stall_ms': AutonomyGovernancePolicy._OPERATIONAL_STALL_MS,
        'idle_rest_window_s': AutonomyGovernancePolicy._OPERATIONAL_IDLE_REST_WINDOW_S,
    }


def summarize_operational_budget_calibration(
    experiment_runs: list[ExperimentRun] | list[Any],
    *,
    min_sample: int = 10,
) -> dict[str, Any]:
    """Summarize whether operational-budget thresholds are ready to tune.

    This is deliberately conservative: it converts ExperimentLab evidence into
    a calibration recommendation, but it does not mutate thresholds.  Applying a
    threshold change belongs to the existing runtime-tuning/governance path.
    """

    budget_runs = [
        run for run in list(experiment_runs or [])
        if str(getattr(run, 'suite_name', '') or '') == 'operational_budget'
        or str(dict(getattr(run, 'metadata', {}) or {}).get('suite_name') or '') == 'operational_budget'
    ]
    current_thresholds = operational_budget_default_thresholds()
    by_decision: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    by_work_class: dict[str, int] = {}
    score_by_decision: dict[str, list[float]] = {}
    evidence_ranges: dict[str, dict[str, float]] = {
        'rss_mb': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
        'recent_stall_ms': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
        'idle_seconds': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
    }
    evidence_values: dict[str, list[float]] = {key: [] for key in evidence_ranges}

    for run in budget_runs:
        metadata = dict(getattr(run, 'metadata', {}) or {})
        budget = dict(metadata.get('operational_budget') or {})
        evidence = dict(budget.get('evidence') or {})
        decision = str(metadata.get('budget_decision') or budget.get('decision') or '').strip().lower() or 'unknown'
        reason = str(metadata.get('budget_reason') or budget.get('reason') or '').strip().lower() or 'unknown'
        work_class = str(metadata.get('work_class') or budget.get('work_class') or '').strip().lower() or 'unknown'
        by_decision[decision] = by_decision.get(decision, 0) + 1
        by_reason[reason] = by_reason.get(reason, 0) + 1
        by_work_class[work_class] = by_work_class.get(work_class, 0) + 1
        try:
            score = float(getattr(getattr(run, 'metrics', None), 'total_score', 0.0) or 0.0)
        except Exception:
            score = 0.0
        score_by_decision.setdefault(decision, []).append(score)
        for key in evidence_values:
            try:
                evidence_values[key].append(float(evidence.get(key) or 0.0))
            except Exception:
                pass

    for key, values in evidence_values.items():
        non_empty = [float(v) for v in values]
        if non_empty:
            evidence_ranges[key] = {
                'min': round(min(non_empty), 2),
                'max': round(max(non_empty), 2),
                'avg': round(sum(non_empty) / len(non_empty), 2),
            }

    avg_score_by_decision = {
        key: round(sum(values) / max(len(values), 1), 4)
        for key, values in score_by_decision.items()
        if values
    }
    total = len(budget_runs)
    if total <= 0:
        return {
            'status': 'no_data',
            'policy_version': 'operational_budget_v1',
            'sample_count': 0,
            'minimum_sample': int(min_sample),
            'current_thresholds': current_thresholds,
            'recommended_thresholds': current_thresholds,
            'confidence': 0.0,
            'recommendation': 'collect_operational_budget_samples',
            'by_decision': {},
            'by_reason': {},
            'by_work_class': {},
            'avg_score_by_decision': {},
            'evidence_ranges': evidence_ranges,
        }

    confidence = round(min(0.95, max(0.1, total / max(int(min_sample), 1) * 0.45)), 3)
    if total < int(min_sample):
        status = 'insufficient_sample'
        recommendation = 'collect_more_evidence_before_tuning'
    else:
        defer_count = int(by_decision.get('defer', 0))
        allow_count = int(by_decision.get('allow', 0))
        ask_count = int(by_decision.get('ask_user', 0))
        rest_count = int(by_reason.get('rest_window_not_reached', 0))
        stall_count = sum(
            count for reason, count in by_reason.items()
            if str(reason).startswith('recent_ui_stall')
        )
        pressure_count = int(by_reason.get('resource_pressure_high', 0)) + int(by_reason.get('resource_pressure_critical', 0))
        if allow_count <= 0:
            status = 'needs_allow_samples'
            recommendation = 'collect_post_rest_allow_evidence_before_tuning'
        elif ask_count > 0:
            status = 'human_gate_observed'
            recommendation = 'keep_thresholds_and_review_low_confidence_actions'
        elif pressure_count or stall_count:
            status = 'protective_thresholds_active'
            recommendation = 'keep_current_thresholds_until_stalls_and_pressure_decline'
        elif rest_count >= max(3, total // 2) and defer_count > allow_count:
            status = 'rest_window_dominant'
            recommendation = 'keep_idle_rest_window_and_collect_more_after_idle_samples'
        else:
            status = 'stable_guardrails'
            recommendation = 'keep_current_thresholds'

    return {
        'status': status,
        'policy_version': 'operational_budget_v1',
        'sample_count': total,
        'minimum_sample': int(min_sample),
        'current_thresholds': current_thresholds,
        'recommended_thresholds': current_thresholds,
        'confidence': confidence,
        'recommendation': recommendation,
        'by_decision': by_decision,
        'by_reason': by_reason,
        'by_work_class': by_work_class,
        'avg_score_by_decision': avg_score_by_decision,
        'evidence_ranges': evidence_ranges,
    }


def apply_operational_budget_calibration_to_runtime_tuning(
    *,
    repository: Any | None,
    calibration: dict[str, Any] | None,
    scope_key: str = 'global',
    recent_stall_ms: float = 0.0,
    background_active: bool = False,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Promote a mature operational-budget calibration into runtime tuning.

    This is A5: a governed, reversible application step.  It does not invent
    thresholds; it persists the recommendation already derived from
    ExperimentLab/OSES and lets ``AutonomyGovernancePolicy`` consume it on the
    next evaluation.
    """

    if repository is None or not hasattr(repository, 'get') or not hasattr(repository, 'save'):
        return {'applied': False, 'status': 'unavailable', 'reason': 'runtime_tuning_repository_missing'}
    data = dict(calibration or {})
    status = str(data.get('status') or '').strip().lower()
    recommendation = str(data.get('recommendation') or '').strip() or 'keep_current_thresholds'
    sample_count = int(data.get('sample_count') or 0)
    minimum_sample = int(data.get('minimum_sample') or 10)
    if sample_count < minimum_sample:
        return {
            'applied': False,
            'status': status or 'insufficient_sample',
            'reason': 'minimum_sample_not_reached',
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
        }
    if status in {'no_data', 'insufficient_sample', 'needs_allow_samples', 'human_gate_observed'}:
        return {
            'applied': False,
            'status': status,
            'reason': f'calibration_not_safe_to_apply:{status}',
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
        }
    try:
        stall = max(0.0, float(recent_stall_ms or 0.0))
    except Exception:
        stall = 0.0
    if stall >= AutonomyGovernancePolicy._OPERATIONAL_STALL_MS:
        return {
            'applied': False,
            'status': status,
            'reason': f'recent_ui_stall:{int(stall)}ms',
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
        }
    if bool(background_active):
        return {
            'applied': False,
            'status': status,
            'reason': 'background_active',
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
        }

    thresholds = _normalize_operational_budget_thresholds(data.get('recommended_thresholds') or {})
    profile = repository.get(scope_key) or RuntimeTuningProfile(scope_key=scope_key)
    metadata = dict(profile.metadata or {})
    existing_payload = dict(metadata.get('operational_budget_thresholds') or {})
    previous_thresholds = _normalize_operational_budget_thresholds(
        existing_payload.get('thresholds') if isinstance(existing_payload, dict) else None
    )
    signature = _operational_budget_calibration_signature(data, thresholds)
    if (
        existing_payload
        and previous_thresholds == thresholds
        and str(existing_payload.get('calibration_status') or '').strip().lower() == status
        and str(existing_payload.get('recommendation') or '').strip() == recommendation
    ):
        metadata['operational_budget_thresholds'] = {
            **existing_payload,
            'thresholds': thresholds,
            'calibration_status': status,
            'recommendation': recommendation,
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
            'confidence': float(data.get('confidence') or 0.0),
            'policy_version': data.get('policy_version') or 'operational_budget_v1',
            'calibration_signature': signature,
            'last_confirmed_at_utc': utc_now().isoformat(),
        }
        profile.metadata = metadata
        profile.updated_at_utc = utc_now()
        repository.save(profile)
        return {
            'applied': False,
            'status': status,
            'reason': 'already_effective',
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
            'thresholds': thresholds,
            'profile_id': profile.profile_id,
        }
    if existing_payload.get('calibration_signature') == signature:
        return {
            'applied': False,
            'status': status,
            'reason': 'already_applied',
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
            'thresholds': thresholds,
            'profile_id': profile.profile_id,
        }

    adjustment = RuntimeAdjustment(
        target_key='autonomy_governance_policy.operational_budget.thresholds',
        previous_value=previous_thresholds,
        new_value=thresholds,
        reason=(
            f'A5 operational budget calibration: {recommendation} '
            f'({status}, samples={sample_count}/{minimum_sample}).'
        ),
        evidence_refs=[
            *(evidence_refs or []),
            'ExperimentLab:operational_budget',
            'OSES:operational_budget_calibration',
        ],
        reversible=True,
        helped=None,
        metadata={
            'calibration_status': status,
            'recommendation': recommendation,
            'sample_count': sample_count,
            'minimum_sample': minimum_sample,
            'confidence': float(data.get('confidence') or 0.0),
            'calibration_signature': signature,
        },
    )
    metadata['operational_budget_thresholds'] = {
        'thresholds': thresholds,
        'calibration_status': status,
        'recommendation': recommendation,
        'sample_count': sample_count,
        'minimum_sample': minimum_sample,
        'confidence': float(data.get('confidence') or 0.0),
        'policy_version': data.get('policy_version') or 'operational_budget_v1',
        'calibration_signature': signature,
        'applied_at_utc': utc_now().isoformat(),
    }
    profile.adjustments.append(adjustment)
    profile.metadata = metadata
    profile.updated_at_utc = utc_now()
    repository.save(profile)
    return {
        'applied': True,
        'status': status,
        'reason': 'runtime_tuning_profile_updated',
        'sample_count': sample_count,
        'minimum_sample': minimum_sample,
        'thresholds': thresholds,
        'profile_id': profile.profile_id,
        'adjustment_id': adjustment.adjustment_id,
    }


def _operational_budget_calibration_signature(
    calibration: dict[str, Any],
    thresholds: dict[str, float],
) -> str:
    payload = {
        'policy_version': calibration.get('policy_version') or 'operational_budget_v1',
        'status': calibration.get('status') or '',
        'recommendation': calibration.get('recommendation') or '',
        'sample_count': int(calibration.get('sample_count') or 0),
        'minimum_sample': int(calibration.get('minimum_sample') or 10),
        'thresholds': thresholds,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _clamp_float(value: Any, *, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(0.0, min(parsed, 1.0))


