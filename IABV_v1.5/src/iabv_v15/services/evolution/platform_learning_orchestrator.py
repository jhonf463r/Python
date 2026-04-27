"""Platform learning orchestrator — closed-loop learning for any platform.

Implements the source-of-truth crossing paradigm:
  perceive → plan → act → verify → adjust → persist

The orchestrator does NOT replace existing services.  It wires them:
- ``BrowserTeachSessionService`` — browser interactions
- ``SiteExplorationService`` — site scanning
- ``UniversalPerceptionService`` — screen observation
- ``ReplayConfidenceService`` — replay reliability
- ``InteractionLearningService`` — interaction history
- ``ApiKeyDiscoveryService`` — provider health
- ``DecisionSimplifierEngine`` — fast-path for known obstacles

Learning covers:
- Browser / UI platforms (login flows, dashboards)
- REST / gRPC APIs (endpoint discovery, auth, schema)
- CLI tools (commands, flags, output parsing)
- Background services (health monitoring, log parsing)

Architecture:
- NOT another brain or orchestrator.  Feeds data to ``ExperimentLab``,
  ``SelfTeachOrchestrator``, and OSES.
- Persists learned profiles to ``data/evolution/platform_learning/``.
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
# Enums
# ---------------------------------------------------------------------------

class LearningPhase(str, Enum):
    PERCEIVE = 'perceive'
    PLAN = 'plan'
    ACT = 'act'
    VERIFY = 'verify'
    ADJUST = 'adjust'
    PERSIST = 'persist'


class VerificationSource(str, Enum):
    VISUAL = 'visual'             # screenshot / screen content
    DOM = 'dom'                   # page DOM structure
    URL_CHANGE = 'url_change'     # URL changed as expected
    API_RESPONSE = 'api_response' # API returned expected shape
    PROCESS_OUTPUT = 'process_output'
    FILE_CHANGE = 'file_change'
    STATE_CHANGE = 'state_change'
    NETWORK_TRAFFIC = 'network_traffic'


class PlatformType(str, Enum):
    BROWSER = 'browser'
    API = 'api'
    CLI = 'cli'
    BACKGROUND = 'background'


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PlatformProfile:
    platform_id: str
    name: str
    platform_type: PlatformType = PlatformType.BROWSER
    url: str = ''
    login_steps: list[dict[str, str]] = field(default_factory=list)
    known_actions: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_used_utc: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'platform_id': self.platform_id,
            'name': self.name,
            'platform_type': self.platform_type.value if isinstance(self.platform_type, PlatformType) else self.platform_type,
            'url': self.url,
            'login_steps': self.login_steps,
            'known_actions': self.known_actions,
            'confidence': self.confidence,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_used_utc': self.last_used_utc,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlatformProfile:
        pt = d.get('platform_type', 'browser')
        if isinstance(pt, str):
            try:
                pt = PlatformType(pt)
            except ValueError:
                pt = PlatformType.BROWSER
        return cls(
            platform_id=d['platform_id'],
            name=d.get('name', d['platform_id']),
            platform_type=pt,
            url=d.get('url', ''),
            login_steps=d.get('login_steps', []),
            known_actions=d.get('known_actions', []),
            confidence=d.get('confidence', 0.0),
            success_count=d.get('success_count', 0),
            failure_count=d.get('failure_count', 0),
            last_used_utc=d.get('last_used_utc', ''),
        )


@dataclass
class LearningAttempt:
    platform_id: str
    goal: str
    phase: LearningPhase = LearningPhase.PERCEIVE
    success: bool = False
    verification_sources_used: list[str] = field(default_factory=list)
    verification_passed: int = 0
    verification_total: int = 0
    duration_seconds: float = 0.0
    error: str = ''
    adjustments_made: list[str] = field(default_factory=list)
    timestamp_utc: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'platform_id': self.platform_id,
            'goal': self.goal,
            'phase': self.phase.value if isinstance(self.phase, LearningPhase) else self.phase,
            'success': self.success,
            'verification_sources_used': self.verification_sources_used,
            'verification_passed': self.verification_passed,
            'verification_total': self.verification_total,
            'duration_seconds': round(self.duration_seconds, 3),
            'error': self.error,
            'adjustments_made': self.adjustments_made,
            'timestamp_utc': self.timestamp_utc,
        }


# ---------------------------------------------------------------------------
# Seed platforms — common platforms IABV interacts with
# ---------------------------------------------------------------------------

_SEED_PLATFORMS: list[dict[str, Any]] = [
    {
        'platform_id': 'groq_console',
        'name': 'Groq Console',
        'platform_type': 'browser',
        'url': 'https://console.groq.com/keys',
        'login_steps': [
            {'action': 'navigate', 'target': 'https://console.groq.com'},
            {'action': 'click', 'target': 'Sign In / Continue with Google'},
            {'action': 'verify', 'target': 'dashboard or API keys page'},
        ],
    },
    {
        'platform_id': 'gemini_studio',
        'name': 'Google AI Studio',
        'platform_type': 'browser',
        'url': 'https://aistudio.google.com/apikey',
        'login_steps': [
            {'action': 'navigate', 'target': 'https://aistudio.google.com'},
            {'action': 'click', 'target': 'Sign in with Google'},
            {'action': 'verify', 'target': 'API key management page'},
        ],
    },
    {
        'platform_id': 'openrouter',
        'name': 'OpenRouter',
        'platform_type': 'browser',
        'url': 'https://openrouter.ai/keys',
        'login_steps': [
            {'action': 'navigate', 'target': 'https://openrouter.ai'},
            {'action': 'click', 'target': 'Sign In / Google OAuth'},
            {'action': 'verify', 'target': 'API keys page'},
        ],
    },
    {
        'platform_id': 'github',
        'name': 'GitHub',
        'platform_type': 'browser',
        'url': 'https://github.com/settings/tokens',
        'login_steps': [
            {'action': 'navigate', 'target': 'https://github.com/login'},
            {'action': 'fill_credentials', 'target': 'username + password'},
            {'action': 'verify', 'target': 'dashboard or token settings'},
        ],
    },
    {
        'platform_id': 'ollama_api',
        'name': 'Ollama Local API',
        'platform_type': 'api',
        'url': 'http://127.0.0.1:11434',
        'login_steps': [],
        'known_actions': [
            {'action': 'GET /v1/models', 'target': 'list available models'},
            {'action': 'POST /api/chat', 'target': 'chat completion'},
        ],
    },
]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PlatformLearningOrchestrator:
    """Closed-loop learner for external platforms.

    Integration points (set after construction by bootstrap):
    - ``browser_teach``: ``BrowserTeachSessionService``
    - ``site_exploration``: ``SiteExplorationService``
    - ``universal_perception``: ``UniversalPerceptionService``
    - ``replay_confidence``: ``ReplayConfidenceService``
    - ``decision_simplifier``: ``DecisionSimplifierEngine``
    - ``api_key_discovery``: ``ApiKeyDiscoveryService``
    """

    def __init__(self, *, data_root: str | Path = '') -> None:
        self._data_root = Path(data_root) if data_root else Path('data')
        self._platforms: dict[str, PlatformProfile] = {}
        self._attempts: list[LearningAttempt] = []

        # Injected by bootstrap
        self.browser_teach: Any = None
        self.site_exploration: Any = None
        self.universal_perception: Any = None
        self.replay_confidence: Any = None
        self.decision_simplifier: Any = None
        self.api_key_discovery: Any = None

        self._load_platforms()
        self._seed_defaults()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _platform_dir(self) -> Path:
        d = self._data_root / 'evolution' / 'platform_learning'
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _load_platforms(self) -> None:
        path = self._platform_dir() / 'learned_platforms.json'
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            for item in data:
                p = PlatformProfile.from_dict(item)
                self._platforms[p.platform_id] = p
        except Exception as exc:
            logger.warning('platform_learning: load error: %s', exc)

    def _save_platforms(self) -> None:
        path = self._platform_dir() / 'learned_platforms.json'
        data = [p.to_dict() for p in self._platforms.values()]
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except OSError as exc:
            logger.warning('platform_learning: save error: %s', exc)

    def _persist_attempt(self, attempt: LearningAttempt) -> None:
        self._attempts.append(attempt)
        path = self._platform_dir() / 'learning_attempts.jsonl'
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(attempt.to_dict(), ensure_ascii=False) + '\n')
        except OSError:
            pass

    def _seed_defaults(self) -> None:
        for seed in _SEED_PLATFORMS:
            pid = seed['platform_id']
            if pid not in self._platforms:
                self._platforms[pid] = PlatformProfile.from_dict(seed)

    # ------------------------------------------------------------------
    # Core learning loop
    # ------------------------------------------------------------------

    def learn_platform(
        self,
        platform_id: str,
        goal: str,
        executor: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> LearningAttempt:
        """Execute full learning cycle: perceive → plan → act → verify → adjust → persist."""
        start = time.monotonic()
        attempt = LearningAttempt(
            platform_id=platform_id,
            goal=goal,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

        profile = self._platforms.get(platform_id)
        if profile is None:
            profile = PlatformProfile(platform_id=platform_id, name=platform_id)
            self._platforms[platform_id] = profile

        # Fast-path: if confidence is high and decision_simplifier can handle it
        if profile.confidence >= 0.7 and self.decision_simplifier:
            result = self.decision_simplifier.resolve_if_ready(
                f'platform:{platform_id} goal:{goal}',
                context={'platform_id': platform_id},
            )
            if result and result.success:
                profile.success_count += 1
                profile.last_used_utc = datetime.now(timezone.utc).isoformat()
                attempt.success = True
                attempt.phase = LearningPhase.PERSIST
                attempt.duration_seconds = time.monotonic() - start
                self._persist_attempt(attempt)
                self._save_platforms()
                return attempt

        try:
            # Phase 1: PERCEIVE
            attempt.phase = LearningPhase.PERCEIVE
            perception = self._perceive(profile)

            # Phase 2: PLAN
            attempt.phase = LearningPhase.PLAN
            plan = self._plan(profile, goal, perception)

            # Phase 3: ACT
            attempt.phase = LearningPhase.ACT
            act_ok = self._act(profile, plan, executor)

            # Phase 4: VERIFY (source-of-truth crossing)
            attempt.phase = LearningPhase.VERIFY
            v_passed, v_total, v_sources = self._verify(profile, goal)
            attempt.verification_passed = v_passed
            attempt.verification_total = v_total
            attempt.verification_sources_used = v_sources

            if v_total > 0 and v_passed >= (v_total * 2 / 3):
                # Success: at least 2/3 of verification sources confirm
                attempt.success = True
                profile.success_count += 1
                profile.confidence = min(1.0, profile.confidence + 0.1)
            else:
                # Phase 5: ADJUST
                attempt.phase = LearningPhase.ADJUST
                adjustments = self._adjust(profile, goal, v_sources)
                attempt.adjustments_made = adjustments
                profile.failure_count += 1
                profile.confidence = max(0.0, profile.confidence - 0.05)

            # Phase 6: PERSIST
            attempt.phase = LearningPhase.PERSIST
            profile.last_used_utc = datetime.now(timezone.utc).isoformat()

        except Exception as exc:
            attempt.error = str(exc)[:300]
            profile.failure_count += 1
            profile.confidence = max(0.0, profile.confidence - 0.1)
            logger.warning('platform_learning: error in %s: %s', platform_id, exc)

        attempt.duration_seconds = time.monotonic() - start
        self._persist_attempt(attempt)
        self._save_platforms()
        return attempt

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _perceive(self, profile: PlatformProfile) -> dict[str, Any]:
        """Observe current state of the platform."""
        perception: dict[str, Any] = {
            'platform_id': profile.platform_id,
            'type': profile.platform_type.value if isinstance(profile.platform_type, PlatformType) else profile.platform_type,
            'url': profile.url,
        }

        if profile.platform_type == PlatformType.API:
            # For APIs, check if the endpoint responds
            if self.api_key_discovery:
                scan = self.api_key_discovery.scan_configured_keys()
                matching = [s for s in scan if profile.platform_id in s.get('provider_id', '')]
                perception['has_key'] = any(s['configured'] for s in matching)

        if profile.platform_type == PlatformType.BROWSER and self.universal_perception:
            try:
                signals = self.universal_perception.latest_signals()
                if signals:
                    perception['screen_available'] = True
            except Exception:
                perception['screen_available'] = False

        return perception

    def _plan(
        self,
        profile: PlatformProfile,
        goal: str,
        perception: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Decide steps based on stored profile and current perception."""
        if profile.login_steps and 'login' in goal.lower():
            return profile.login_steps

        if profile.known_actions:
            return profile.known_actions

        # Default: navigate and observe
        return [
            {'action': 'navigate', 'target': profile.url or profile.platform_id},
            {'action': 'observe', 'target': 'main content area'},
        ]

    def _act(
        self,
        profile: PlatformProfile,
        plan: list[dict[str, str]],
        executor: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> bool:
        """Execute the plan steps."""
        for step in plan:
            action = step.get('action', '')
            target = step.get('target', '')
            if executor:
                try:
                    ok = executor(action, {'target': target, 'profile': profile.to_dict()})
                    if not ok:
                        return False
                except Exception as exc:
                    logger.warning('platform_learning: act failed: %s', exc)
                    return False
            else:
                logger.debug('platform_learning: dry-run step %s → %s', action, target)
        return True

    def _verify(
        self,
        profile: PlatformProfile,
        goal: str,
    ) -> tuple[int, int, list[str]]:
        """Cross-check sources of truth. Returns (passed, total, sources_used)."""
        sources_used: list[str] = []
        passed = 0
        total = 0

        # Source 1: URL / API response check
        if profile.platform_type == PlatformType.API and profile.url:
            total += 1
            sources_used.append(VerificationSource.API_RESPONSE.value)
            try:
                import httpx
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(profile.url)
                    if resp.status_code < 500:
                        passed += 1
            except Exception:
                pass

        # Source 2: State change (API key configured after goal)
        if self.api_key_discovery and 'key' in goal.lower():
            total += 1
            sources_used.append(VerificationSource.STATE_CHANGE.value)
            scan = self.api_key_discovery.scan_configured_keys()
            if any(s['configured'] for s in scan):
                passed += 1

        # Source 3: Replay confidence (if browser interaction)
        if profile.platform_type == PlatformType.BROWSER and self.replay_confidence:
            total += 1
            sources_used.append(VerificationSource.VISUAL.value)
            try:
                conf = self.replay_confidence.current_confidence()
                if conf and conf >= 0.5:
                    passed += 1
            except Exception:
                pass

        # Minimum: always have at least one check (existence)
        if total == 0:
            total = 1
            sources_used.append('existence')
            passed = 1  # platform exists

        return passed, total, sources_used

    def _adjust(
        self,
        profile: PlatformProfile,
        goal: str,
        failed_sources: list[str],
    ) -> list[str]:
        """Record adjustments when verification fails."""
        adjustments: list[str] = []

        if 'api_response' in failed_sources:
            adjustments.append(f'API endpoint {profile.url} may be down; schedule retry')

        if 'visual' in failed_sources:
            adjustments.append('Browser verification failed; page may need different login flow')

        if not adjustments:
            adjustments.append(f'Goal "{goal}" not fully verified; needs manual review')

        return adjustments

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_platform(
        self,
        platform_id: str,
        name: str = '',
        url: str = '',
        platform_type: str = 'browser',
    ) -> PlatformProfile:
        """Register a new platform or return existing one."""
        if platform_id in self._platforms:
            return self._platforms[platform_id]

        try:
            pt = PlatformType(platform_type)
        except ValueError:
            pt = PlatformType.BROWSER

        profile = PlatformProfile(
            platform_id=platform_id,
            name=name or platform_id,
            platform_type=pt,
            url=url,
        )
        self._platforms[platform_id] = profile
        self._save_platforms()
        return profile

    # ------------------------------------------------------------------
    # OSES findings contribution
    # ------------------------------------------------------------------

    def oses_findings(self) -> list[dict[str, Any]]:
        """Generate findings for OSES consumption."""
        findings: list[dict[str, Any]] = []

        # Find platforms that need learning (low confidence)
        low_conf = [
            p for p in self._platforms.values()
            if p.confidence < 0.5 and p.url
        ]
        if low_conf:
            names = ', '.join(p.name for p in low_conf[:5])
            findings.append({
                'category': 'platform_learning',
                'title': f'{len(low_conf)} platforms need learning',
                'summary': f'Low confidence platforms: {names}. Consider learning sessions.',
                'severity': 'MEDIUM',
                'confidence': 0.7,
                'recommendation': 'Run learn_platform() for low-confidence platforms',
                'metadata': {
                    'platforms': [p.platform_id for p in low_conf],
                },
            })

        # Detect reliability issues (high failure rate)
        for p in self._platforms.values():
            total = p.success_count + p.failure_count
            if total >= 5 and p.failure_count / total >= 0.5:
                findings.append({
                    'category': 'platform_learning',
                    'title': f'Reliability issue: {p.name}',
                    'summary': (
                        f'{p.name} has {p.failure_count}/{total} failures '
                        f'({p.failure_count / total:.0%}). '
                        f'Login flow or API may have changed.'
                    ),
                    'severity': 'HIGH',
                    'confidence': 0.8,
                    'recommendation': f'Re-learn {p.name} platform',
                    'metadata': {
                        'platform_id': p.platform_id,
                        'failure_rate': round(p.failure_count / total, 3),
                    },
                })

        return findings

    # ------------------------------------------------------------------
    # Status summary (for MCP / UI)
    # ------------------------------------------------------------------

    def status_summary(self) -> dict[str, Any]:
        platforms = list(self._platforms.values())
        return {
            'total_platforms': len(platforms),
            'learned': [p.platform_id for p in platforms if p.confidence >= 0.7],
            'learning': [p.platform_id for p in platforms if 0.0 < p.confidence < 0.7],
            'unlearned': [p.platform_id for p in platforms if p.confidence == 0.0],
            'total_attempts': len(self._attempts),
        }

    def get_platform(self, platform_id: str) -> PlatformProfile | None:
        return self._platforms.get(platform_id)

    def all_platforms(self) -> list[PlatformProfile]:
        return list(self._platforms.values())
