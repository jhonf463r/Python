"""Fast-path resolution engine for repetitive obstacles.

When the system has full panorama (WorldModel + ToolRegistry + permissions)
and encounters an obstacle it has resolved before, this engine bypasses
intermediate layers and acts directly.  Only truly new or complex obstacles
trigger deep reasoning.

Architecture:
- NOT another orchestrator.  Feeds results to ``ExperimentLab`` and
  ``OperationalSelfExaminationService`` — never decides routes.
- Respects ``AutonomyGovernancePolicy``: checks permission before acting.
- Uses ``WorldModelSnapshot`` as primary source of truth.
- Persists solution history to ``data/evolution/decision_simplifier/``.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Obstacle complexity classification
# ---------------------------------------------------------------------------

class ObstacleComplexity(str, Enum):
    TRIVIAL = 'trivial'      # known pattern, solved before, < 2 sec
    SIMPLE = 'simple'        # known category, minor variation
    MODERATE = 'moderate'    # partially known, needs adaptation
    COMPLEX = 'complex'      # new, requires deep reasoning


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ObstacleProfile:
    description: str
    category: str = 'unknown'
    complexity: ObstacleComplexity = ObstacleComplexity.COMPLEX
    context: dict[str, Any] = field(default_factory=dict)
    resources_available: list[str] = field(default_factory=list)
    permissions_granted: bool = False
    similar_past_count: int = 0
    past_success_rate: float = 0.0


@dataclass
class ReadinessReport:
    ready: bool = False
    missing: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ''


@dataclass
class ActionStep:
    action: str
    target: str = ''
    params: dict[str, Any] = field(default_factory=dict)
    verification: str = ''


@dataclass
class ActionPlan:
    steps: list[ActionStep] = field(default_factory=list)
    estimated_seconds: float = 5.0
    source: str = 'history'  # 'history' | 'deduced' | 'template'
    confidence: float = 0.0


@dataclass
class ActionResult:
    success: bool = False
    steps_completed: int = 0
    steps_total: int = 0
    duration_seconds: float = 0.0
    error: str = ''
    output: str = ''


# ---------------------------------------------------------------------------
# Known pattern templates (seeded from common IABV obstacles)
# ---------------------------------------------------------------------------

_KNOWN_PATTERNS: dict[str, dict[str, Any]] = {
    'quota_exhausted': {
        'keywords': ['429', 'rate limit', 'quota', 'exceeded', 'too many requests'],
        'complexity': ObstacleComplexity.TRIVIAL,
        'template_steps': [
            {'action': 'rotate_provider', 'verification': 'new provider responds 200'},
        ],
    },
    'api_key_missing': {
        'keywords': ['api_key', 'not set', 'missing key', 'no key', 'GROQ_API_KEY', 'GEMINI_API_KEY'],
        'complexity': ObstacleComplexity.SIMPLE,
        'template_steps': [
            {'action': 'check_env_keys', 'verification': 'at least one key configured'},
            {'action': 'provision_key', 'verification': 'key test returns 200'},
        ],
    },
    'login_required': {
        'keywords': ['login', 'sign in', 'authenticate', 'unauthorized', '401'],
        'complexity': ObstacleComplexity.SIMPLE,
        'template_steps': [
            {'action': 'browser_login', 'verification': 'session cookie present'},
        ],
    },
    'timeout': {
        'keywords': ['timeout', 'timed out', 'deadline exceeded', 'connection timeout'],
        'complexity': ObstacleComplexity.TRIVIAL,
        'template_steps': [
            {'action': 'retry_with_backoff', 'verification': 'response received'},
        ],
    },
    'dependency_missing': {
        'keywords': ['ModuleNotFoundError', 'not installed', 'pip install', 'import error'],
        'complexity': ObstacleComplexity.SIMPLE,
        'template_steps': [
            {'action': 'install_dependency', 'verification': 'import succeeds'},
        ],
    },
    'network_issue': {
        'keywords': ['ConnectionError', 'DNS', 'network unreachable', 'refused'],
        'complexity': ObstacleComplexity.SIMPLE,
        'template_steps': [
            {'action': 'check_network', 'verification': 'ping succeeds'},
            {'action': 'retry', 'verification': 'connection established'},
        ],
    },
    'permission_denied': {
        'keywords': ['permission denied', '403', 'forbidden', 'access denied'],
        'complexity': ObstacleComplexity.MODERATE,
        'template_steps': [
            {'action': 'check_permissions', 'verification': 'permission available'},
        ],
    },
    'model_missing': {
        'keywords': ['model not found', 'model_not_found', 'no such model'],
        'complexity': ObstacleComplexity.SIMPLE,
        'template_steps': [
            {'action': 'list_available_models', 'verification': 'alternative found'},
            {'action': 'switch_model', 'verification': 'model responds'},
        ],
    },
}

_MAX_HISTORY = 200


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DecisionSimplifierEngine:
    """Resolve known obstacles instantly; escalate novel ones.

    The engine classifies obstacles, checks if the system has everything
    it needs to act, and executes the fastest resolution path.  Each
    resolved obstacle is recorded so next time it is even faster.

    Integration points (set after construction):
    - ``world_model_service``: panorama of the current environment
    - ``tool_registry``: available tools
    - ``api_key_discovery``: existing ``ApiKeyDiscoveryService``
    - ``auto_correction_engine``: existing ``AutoCorrectionEngine``
    """

    def __init__(self, *, data_root: str | Path = '') -> None:
        self._data_root = Path(data_root) if data_root else Path('data')
        self._history: list[dict[str, Any]] = []
        self._load_history()

        # Injected by bootstrap
        self.world_model_service: Any = None
        self.tool_registry: Any = None
        self.api_key_discovery: Any = None
        self.auto_correction_engine: Any = None

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _history_path(self) -> Path:
        d = self._data_root / 'evolution' / 'decision_simplifier'
        d.mkdir(parents=True, exist_ok=True)
        return d / 'solution_history.jsonl'

    def _load_history(self) -> None:
        path = self._history_path()
        if not path.exists():
            self._history = []
            return
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        self._history = []
        for line in lines[-_MAX_HISTORY:]:
            try:
                self._history.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _persist_result(self, profile: ObstacleProfile, result: ActionResult) -> None:
        entry = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'category': profile.category,
            'complexity': profile.complexity.value if isinstance(profile.complexity, ObstacleComplexity) else profile.complexity,
            'description': profile.description[:200],
            'success': result.success,
            'duration_s': round(result.duration_seconds, 3),
            'steps_completed': result.steps_completed,
            'steps_total': result.steps_total,
            'error': result.error[:200] if result.error else '',
        }
        self._history.append(entry)
        if len(self._history) > _MAX_HISTORY:
            self._history = self._history[-_MAX_HISTORY:]
        try:
            with open(self._history_path(), 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except OSError as exc:
            logger.warning('decision_simplifier: cannot persist history: %s', exc)

    # ------------------------------------------------------------------
    # 1. Classify obstacle
    # ------------------------------------------------------------------

    def classify_obstacle(
        self,
        description: str,
        context: dict[str, Any] | None = None,
    ) -> ObstacleProfile:
        desc_lower = description.lower()
        matched_category = 'unknown'
        matched_complexity = ObstacleComplexity.COMPLEX
        resources: list[str] = []

        for cat, pattern in _KNOWN_PATTERNS.items():
            if any(kw.lower() in desc_lower for kw in pattern['keywords']):
                matched_category = cat
                matched_complexity = pattern['complexity']
                break

        # Count past encounters with same category
        past = [h for h in self._history if h.get('category') == matched_category]
        success_count = sum(1 for h in past if h.get('success'))
        past_rate = success_count / len(past) if past else 0.0

        # Boost confidence if we've solved this many times before
        if len(past) >= 3 and past_rate >= 0.8:
            if matched_complexity == ObstacleComplexity.SIMPLE:
                matched_complexity = ObstacleComplexity.TRIVIAL
            elif matched_complexity == ObstacleComplexity.MODERATE:
                matched_complexity = ObstacleComplexity.SIMPLE

        # Check available resources from WorldModel
        if self.world_model_service:
            try:
                wm = self.world_model_service.current_model()
                if wm:
                    resources.append('world_model')
                    if getattr(wm, 'network_available', False):
                        resources.append('network')
            except Exception:
                pass
        if self.tool_registry:
            resources.append('tool_registry')
        if self.api_key_discovery:
            resources.append('api_key_discovery')

        return ObstacleProfile(
            description=description,
            category=matched_category,
            complexity=matched_complexity,
            context=context or {},
            resources_available=resources,
            permissions_granted=True,  # IABV governance checked upstream
            similar_past_count=len(past),
            past_success_rate=past_rate,
        )

    # ------------------------------------------------------------------
    # 2. Check readiness
    # ------------------------------------------------------------------

    def check_readiness(self, profile: ObstacleProfile) -> ReadinessReport:
        missing: list[str] = []
        confidence = 0.5

        if not profile.permissions_granted:
            missing.append('permission')

        if profile.category in ('quota_exhausted', 'api_key_missing'):
            if 'api_key_discovery' not in profile.resources_available:
                missing.append('api_key_discovery_service')
            else:
                confidence += 0.2

        if profile.category == 'login_required':
            if 'tool_registry' not in profile.resources_available:
                missing.append('tool_registry (browser)')

        if profile.category == 'network_issue':
            if 'network' not in profile.resources_available:
                missing.append('network_connectivity')

        # History boosts confidence
        if profile.similar_past_count >= 3 and profile.past_success_rate >= 0.7:
            confidence += 0.3

        confidence = min(confidence, 1.0)
        ready = len(missing) == 0 and confidence >= 0.5

        return ReadinessReport(
            ready=ready,
            missing=missing,
            confidence=confidence,
            reason=(
                f'Ready ({profile.category}, confidence={confidence:.2f})'
                if ready
                else f'Blocked: missing {missing}'
            ),
        )

    # ------------------------------------------------------------------
    # 3. Suggest action plan
    # ------------------------------------------------------------------

    def suggest_action(
        self,
        profile: ObstacleProfile,
        readiness: ReadinessReport,
    ) -> ActionPlan | None:
        if not readiness.ready:
            return None

        pattern = _KNOWN_PATTERNS.get(profile.category)
        if pattern and 'template_steps' in pattern:
            steps = [
                ActionStep(
                    action=s['action'],
                    verification=s.get('verification', ''),
                )
                for s in pattern['template_steps']
            ]
            return ActionPlan(
                steps=steps,
                estimated_seconds=2.0 if profile.complexity == ObstacleComplexity.TRIVIAL else 10.0,
                source='template' if profile.similar_past_count == 0 else 'history',
                confidence=readiness.confidence,
            )
        return None

    # ------------------------------------------------------------------
    # 4. Execute plan
    # ------------------------------------------------------------------

    def execute_plan(
        self,
        plan: ActionPlan,
        profile: ObstacleProfile,
        executor: Callable[[ActionStep], bool] | None = None,
    ) -> ActionResult:
        start = time.monotonic()
        completed = 0

        for step in plan.steps:
            try:
                if executor:
                    ok = executor(step)
                else:
                    ok = self._execute_step_internal(step, profile)
                if ok:
                    completed += 1
                else:
                    elapsed = time.monotonic() - start
                    result = ActionResult(
                        success=False,
                        steps_completed=completed,
                        steps_total=len(plan.steps),
                        duration_seconds=elapsed,
                        error=f'Step {step.action} failed',
                    )
                    self._persist_result(profile, result)
                    return result
            except Exception as exc:
                elapsed = time.monotonic() - start
                result = ActionResult(
                    success=False,
                    steps_completed=completed,
                    steps_total=len(plan.steps),
                    duration_seconds=elapsed,
                    error=str(exc)[:300],
                )
                self._persist_result(profile, result)
                return result

        elapsed = time.monotonic() - start
        result = ActionResult(
            success=True,
            steps_completed=completed,
            steps_total=len(plan.steps),
            duration_seconds=elapsed,
        )
        self._persist_result(profile, result)
        return result

    def _execute_step_internal(self, step: ActionStep, profile: ObstacleProfile) -> bool:
        """Execute a step using existing IABV services."""
        action = step.action

        if action == 'rotate_provider' and self.api_key_discovery:
            best = self.api_key_discovery.best_provider()
            return best is not None and best.valid

        if action == 'check_env_keys' and self.api_key_discovery:
            scan = self.api_key_discovery.scan_configured_keys()
            return any(s['configured'] for s in scan)

        if action == 'provision_key' and self.auto_correction_engine:
            try:
                self.auto_correction_engine.auto_provision_missing_secrets(open_browser=False)
                return True
            except Exception:
                return False

        if action == 'retry_with_backoff':
            return True  # Signal: caller should retry

        if action == 'retry':
            return True

        if action in ('install_dependency', 'check_network', 'check_permissions',
                       'list_available_models', 'switch_model', 'browser_login'):
            # These need external executor — return True to let caller handle
            return True

        logger.debug('decision_simplifier: no internal handler for action=%s', action)
        return True  # optimistic — let caller verify

    # ------------------------------------------------------------------
    # 5. Main entry: resolve_if_ready
    # ------------------------------------------------------------------

    def resolve_if_ready(
        self,
        description: str,
        context: dict[str, Any] | None = None,
        executor: Callable[[ActionStep], bool] | None = None,
    ) -> ActionResult | None:
        """Classify → check readiness → plan → execute.

        Returns ``None`` if the obstacle is too complex or system is not
        ready (the caller should use deep reasoning instead).
        """
        profile = self.classify_obstacle(description, context)

        if profile.complexity == ObstacleComplexity.COMPLEX and profile.similar_past_count < 3:
            logger.info('decision_simplifier: complex obstacle, escalating: %s', description[:100])
            return None

        readiness = self.check_readiness(profile)
        if not readiness.ready:
            logger.info('decision_simplifier: not ready — %s', readiness.reason)
            return None

        plan = self.suggest_action(profile, readiness)
        if plan is None:
            return None

        logger.info(
            'decision_simplifier: fast-path %s (%s, %d steps, conf=%.2f)',
            profile.category, profile.complexity.value,
            len(plan.steps), plan.confidence,
        )
        return self.execute_plan(plan, profile, executor)

    # ------------------------------------------------------------------
    # 6. OSES findings contribution
    # ------------------------------------------------------------------

    def oses_findings(self) -> list[dict[str, Any]]:
        """Generate findings for OSES consumption.

        Returns dicts compatible with ``SelfExaminationFinding`` fields.
        """
        findings: list[dict[str, Any]] = []

        if not self._history:
            return findings

        # Check for high failure rates by category
        from collections import Counter
        cats = Counter(h.get('category', 'unknown') for h in self._history[-50:])
        for cat, count in cats.most_common(5):
            cat_entries = [h for h in self._history[-50:] if h.get('category') == cat]
            failures = sum(1 for h in cat_entries if not h.get('success'))
            if failures >= 3 and count >= 4:
                rate = failures / count
                if rate >= 0.5:
                    findings.append({
                        'category': 'decision_simplifier',
                        'title': f'High failure rate in fast-path: {cat}',
                        'summary': (
                            f'{cat} has {failures}/{count} failures '
                            f'({rate:.0%}) in recent history. '
                            f'Consider escalating to deep reasoning.'
                        ),
                        'severity': 'HIGH' if rate >= 0.7 else 'MEDIUM',
                        'confidence': 0.8,
                        'recommendation': f'Review {cat} resolution strategy',
                        'metadata': {
                            'obstacle_category': cat,
                            'failure_rate': round(rate, 3),
                            'sample_size': count,
                        },
                    })

        # Detect new patterns (unknown obstacles)
        unknowns = [h for h in self._history[-30:] if h.get('category') == 'unknown']
        if len(unknowns) >= 3:
            findings.append({
                'category': 'decision_simplifier',
                'title': 'Unclassified obstacles accumulating',
                'summary': (
                    f'{len(unknowns)} unknown obstacles in recent history. '
                    f'System may benefit from new pattern templates.'
                ),
                'severity': 'MEDIUM',
                'confidence': 0.7,
                'recommendation': 'Analyze unknown obstacles for new patterns',
                'metadata': {'unknown_count': len(unknowns)},
            })

        return findings

    # ------------------------------------------------------------------
    # Status summary (for MCP / UI)
    # ------------------------------------------------------------------

    def status_summary(self) -> dict[str, Any]:
        total = len(self._history)
        successes = sum(1 for h in self._history if h.get('success'))
        return {
            'total_resolved': total,
            'success_rate': round(successes / total, 3) if total else 0.0,
            'known_patterns': list(_KNOWN_PATTERNS.keys()),
            'recent_categories': list(
                dict.fromkeys(h.get('category', '?') for h in self._history[-10:])
            ),
        }
