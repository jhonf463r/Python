"""Cloud-reasoning planner — generates multi-step execution plans using
Gemini / Groq cloud models and maps each step to the best available tool
(Codex, ChatGPT, Claude, Devin, Ollama local).

This service acts as the "cerebro central" layer: it takes a user goal,
asks a cloud LLM to decompose it into concrete steps, and returns a
structured ``CloudPlan`` that the orchestrator can execute step by step.

Architecture rules respected:
- NOT a second brain/orchestrator: it only produces a *plan proposal*.
  ``AdaptiveTaskOrchestrator`` remains the single decision-maker.
- Respects ``AutonomyGovernancePolicy`` — plans that touch closed layers
  or require approval are flagged.
- Cloud-first with local fallback (same tier as Fix 60).
- Results are persisted so the local model can learn over time.
"""
from __future__ import annotations

import json as _json
import logging
import os
import re as _re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain models for cloud-generated plans
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    order: int = 0
    title: str = ''
    description: str = ''
    assigned_tool: str = ''
    tool_rationale: str = ''
    requires_approval: bool = False
    estimated_seconds: int = 0
    status: str = 'pending'
    result_summary: str = ''
    metadata: dict[str, Any] = Field(default_factory=dict)


class CloudPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    user_goal: str = ''
    summary: str = ''
    steps: list[PlanStep] = Field(default_factory=list)
    cloud_source: str = ''
    confidence: float = 0.0
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Available tool descriptors for the LLM
# ---------------------------------------------------------------------------

TOOL_DESCRIPTORS: list[dict[str, str]] = [
    {
        'id': 'codex',
        'name': 'Codex (OpenAI)',
        'strengths': 'code generation, code review, refactoring, debugging, test writing',
        'limitations': 'no browser, no real-time data, context window limits',
    },
    {
        'id': 'chatgpt',
        'name': 'ChatGPT',
        'strengths': 'general reasoning, explanation, research synthesis, brainstorming, browsing',
        'limitations': 'cannot execute code directly, may hallucinate specifics',
    },
    {
        'id': 'claude',
        'name': 'Claude (Anthropic)',
        'strengths': 'long context analysis, careful reasoning, document review, safety-aware',
        'limitations': 'no browser, no code execution, slower for simple tasks',
    },
    {
        'id': 'devin',
        'name': 'Devin (Cognition)',
        'strengths': 'full autonomous coding, PR creation, testing, deployment, browser use',
        'limitations': 'slower startup, heavier for trivial tasks',
    },
    {
        'id': 'ollama_local',
        'name': 'Ollama (local)',
        'strengths': 'fast, private, no quota limits, good for classification and short tasks',
        'limitations': 'smaller model, weaker reasoning on complex problems',
    },
    {
        'id': 'windsurf',
        'name': 'Windsurf (Codeium)',
        'strengths': 'IDE-integrated coding, real-time autocomplete, multi-file edits, project-aware context',
        'limitations': 'requires desktop IDE, no standalone API, heavier for non-code tasks',
    },
]

_TOOL_BLOCK = '\n'.join(
    f"- {t['id']}: {t['name']} — strengths: {t['strengths']}; limits: {t['limitations']}"
    for t in TOOL_DESCRIPTORS
)


# ---------------------------------------------------------------------------
# System prompt for plan generation
# ---------------------------------------------------------------------------

_PLAN_SYSTEM_PROMPT = f"""\
You are the planning engine of IABV, an intelligent desktop assistant.
Your job is to decompose a user goal into a concrete, ordered list of
steps and assign each step to the best available tool.

Available tools:
{_TOOL_BLOCK}

Rules:
1. Each step must have: title, description, assigned_tool (tool id),
   tool_rationale (why this tool is best for this step).
2. Order steps logically — later steps may depend on earlier results.
3. If a step is risky or irreversible, set requires_approval=true.
4. Keep plans concise: 2-6 steps for most goals.
5. Prefer local tools for simple sub-tasks; use cloud/external for
   complex reasoning, code generation, or browsing.

Respond ONLY with a JSON object (no markdown fences) with this schema:
{{
  "summary": "one-line plan summary",
  "confidence": 0.0-1.0,
  "steps": [
    {{
      "order": 1,
      "title": "step title",
      "description": "what to do",
      "assigned_tool": "tool_id",
      "tool_rationale": "why this tool",
      "requires_approval": false,
      "estimated_seconds": 30
    }}
  ]
}}
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CloudReasoningPlannerService:
    """Generates execution plans using cloud reasoning models."""

    # Class-level API health tracking — shared across instances.
    # Maps provider_id → {'last_status_code': int, 'last_checked': str}
    _api_health: dict[str, dict[str, Any]] = {}

    @classmethod
    def _record_api_health(cls, provider_id: str, status_code: int) -> None:
        """Record the HTTP status code from the last API call for a provider.

        This feeds into CommonSenseEngine fact extraction to detect
        expired/revoked tokens (401/403) and trigger auto-renewal.
        """
        from datetime import datetime, timezone
        cls._api_health[provider_id] = {
            'last_status_code': status_code,
            'last_checked': datetime.now(timezone.utc).isoformat(),
            'healthy': 200 <= status_code < 400,
        }
        if status_code in (401, 403):
            logger.warning(
                'cloud-planner: %s returned %d — token may be expired or revoked',
                provider_id, status_code,
            )

    @classmethod
    def get_api_health(cls) -> dict[str, dict[str, Any]]:
        """Return current API health status for all tracked providers."""
        return dict(cls._api_health)

    def generate_plan(self, user_goal: str, *, context: str = '') -> CloudPlan | None:
        """Ask cloud models to decompose *user_goal* into steps.

        Returns a ``CloudPlan`` or ``None`` if no cloud model could
        produce a valid plan.
        """
        prompt_context = f"User goal: {user_goal}"
        if context:
            prompt_context += f"\n\nAdditional context:\n{context}"

        result = self._query_cloud_for_plan(prompt_context, _PLAN_SYSTEM_PROMPT)
        if result is None:
            return None

        plan = self._parse_plan(result, user_goal)
        if plan is not None:
            self._persist_plan(plan)
        return plan

    # ------------------------------------------------------------------
    # Cloud query — adaptive provider selection
    # ------------------------------------------------------------------

    # Class-level selector: set by bootstrap or test harness.
    _model_selector: Any = None

    @staticmethod
    def _query_cloud_for_plan(context: str, system_prompt: str) -> dict[str, Any] | None:
        try:
            import httpx
        except ImportError:
            return None

        import time as _time

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': context},
        ]

        selector = CloudReasoningPlannerService._model_selector

        # Build ordered provider chain: adaptive selector reorders or
        # falls back to the default Gemini → Groq → Ollama chain.
        if selector is not None:
            try:
                selection = selector.select_best_provider(task_type='planning')
                chain = selection.get('fallback_chain', ['gemini', 'groq', 'ollama_local'])
            except Exception:
                chain = ['gemini', 'groq', 'ollama_local']
        else:
            chain = ['gemini', 'groq', 'ollama_local']

        for provider_id in chain:
            started = _time.monotonic()
            result, err_info = CloudReasoningPlannerService._try_provider(
                provider_id, messages,
            )
            elapsed_ms = (_time.monotonic() - started) * 1000

            if result is not None:
                if selector is not None:
                    selector.record_result(
                        provider_id=provider_id,
                        task_type='planning',
                        latency_ms=elapsed_ms,
                        success=True,
                        model_used=result.get('_cloud_source', provider_id),
                    )
                return result

            # Record failure with real error + status code for quota detection
            if selector is not None:
                selector.record_result(
                    provider_id=provider_id,
                    task_type='planning',
                    latency_ms=elapsed_ms,
                    success=False,
                    error=err_info.get('error', f'{provider_id} failed') if err_info else f'{provider_id} failed',
                    status_code=err_info.get('status_code', 0) if err_info else 0,
                )

        return None

    @staticmethod
    def _try_provider(
        provider_id: str,
        messages: list[dict[str, str]],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Try a single provider. Returns (result, error_info).

        error_info includes 'error' (str) and 'status_code' (int) so the
        caller can pass real HTTP status codes to the adaptive selector
        for proper quota cooldown detection (e.g. 429).
        """
        try:
            import httpx
        except ImportError:
            return None, {'error': 'httpx not installed', 'status_code': 0}

        if provider_id == 'gemini':
            key = os.environ.get('GEMINI_API_KEY', '')
            if not key:
                return None, {'error': 'no API key', 'status_code': 0}
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                        json={'model': 'gemini-2.0-flash', 'messages': messages, 'temperature': 0.15},
                        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                    )
                    CloudReasoningPlannerService._record_api_health('gemini', resp.status_code)
                    resp.raise_for_status()
                    data = resp.json()
                parsed = CloudReasoningPlannerService._extract_json(data, 'gemini')
                if parsed is not None:
                    return parsed, None
                return None, {'error': 'JSON parse failed on 2xx response', 'status_code': resp.status_code}
            except Exception as exc:
                logger.debug('cloud-planner gemini failed: %s', exc)
                sc = getattr(getattr(exc, 'response', None), 'status_code', 0)
                return None, {'error': str(exc)[:200], 'status_code': sc}

        if provider_id == 'groq':
            key = os.environ.get('GROQ_API_KEY', '')
            if not key:
                return None, {'error': 'no API key', 'status_code': 0}
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        'https://api.groq.com/openai/v1/chat/completions',
                        json={'model': 'llama-3.3-70b-versatile', 'messages': messages, 'temperature': 0.15},
                        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                    )
                    CloudReasoningPlannerService._record_api_health('groq', resp.status_code)
                    resp.raise_for_status()
                    data = resp.json()
                parsed = CloudReasoningPlannerService._extract_json(data, 'groq')
                if parsed is not None:
                    return parsed, None
                return None, {'error': 'JSON parse failed on 2xx response', 'status_code': resp.status_code}
            except Exception as exc:
                logger.debug('cloud-planner groq failed: %s', exc)
                sc = getattr(getattr(exc, 'response', None), 'status_code', 0)
                return None, {'error': str(exc)[:200], 'status_code': sc}

        if provider_id in ('ollama_local', 'ollama'):
            base_url = os.environ.get('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434/v1')
            model = os.environ.get('IABV_OLLAMA_MODEL', 'qwen3:8b')
            try:
                with httpx.Client(timeout=35.0) as client:
                    resp = client.post(
                        f'{base_url}/chat/completions',
                        json={'model': model, 'messages': messages, 'stream': False, 'temperature': 0.15},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                parsed = CloudReasoningPlannerService._extract_json(data, 'ollama_local')
                if parsed is not None:
                    return parsed, None
                return None, {'error': 'JSON parse failed on 2xx response', 'status_code': resp.status_code}
            except Exception as exc:
                logger.debug('cloud-planner ollama failed: %s', exc)
                sc = getattr(getattr(exc, 'response', None), 'status_code', 0)
                return None, {'error': str(exc)[:200], 'status_code': sc}

        if provider_id == 'openrouter':
            key = os.environ.get('OPENROUTER_API_KEY', '')
            if not key:
                return None, {'error': 'no API key', 'status_code': 0}
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        'https://openrouter.ai/api/v1/chat/completions',
                        json={'model': 'meta-llama/llama-3.3-70b-instruct:free', 'messages': messages, 'temperature': 0.15},
                        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                    )
                    CloudReasoningPlannerService._record_api_health('openrouter', resp.status_code)
                    resp.raise_for_status()
                    data = resp.json()
                parsed = CloudReasoningPlannerService._extract_json(data, 'openrouter')
                if parsed is not None:
                    return parsed, None
                return None, {'error': 'JSON parse failed on 2xx response', 'status_code': resp.status_code}
            except Exception as exc:
                logger.debug('cloud-planner openrouter failed: %s', exc)
                sc = getattr(getattr(exc, 'response', None), 'status_code', 0)
                return None, {'error': str(exc)[:200], 'status_code': sc}

        if provider_id == 'together':
            key = os.environ.get('TOGETHER_API_KEY', '')
            if not key:
                return None, {'error': 'no API key', 'status_code': 0}
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        'https://api.together.xyz/v1/chat/completions',
                        json={'model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo', 'messages': messages, 'temperature': 0.15},
                        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                    )
                    CloudReasoningPlannerService._record_api_health('together', resp.status_code)
                    resp.raise_for_status()
                    data = resp.json()
                parsed = CloudReasoningPlannerService._extract_json(data, 'together')
                if parsed is not None:
                    return parsed, None
                return None, {'error': 'JSON parse failed on 2xx response', 'status_code': resp.status_code}
            except Exception as exc:
                logger.debug('cloud-planner together failed: %s', exc)
                sc = getattr(getattr(exc, 'response', None), 'status_code', 0)
                return None, {'error': str(exc)[:200], 'status_code': sc}

        return None, {'error': f'unknown provider: {provider_id}', 'status_code': 0}

    @staticmethod
    def _extract_json(data: dict[str, Any], source: str) -> dict[str, Any] | None:
        """Extract JSON from LLM response, stripping <think> blocks."""
        try:
            raw = data['choices'][0]['message']['content'].strip()
            raw = _re.sub(r'<think>.*?</think>', '', raw, flags=_re.DOTALL).strip()
            match = _re.search(r'\{[\s\S]*\}', raw)
            if match:
                parsed = _json.loads(match.group())
                parsed['_cloud_source'] = source
                logger.info('cloud-planner: %s plan generated', source)
                return parsed
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Parse raw LLM output into CloudPlan
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_plan(raw: dict[str, Any], user_goal: str) -> CloudPlan | None:
        steps_raw = raw.get('steps')
        if not isinstance(steps_raw, list) or not steps_raw:
            return None

        valid_tool_ids = {t['id'] for t in TOOL_DESCRIPTORS}
        steps: list[PlanStep] = []
        for i, s in enumerate(steps_raw[:8]):
            if not isinstance(s, dict):
                continue
            tool = str(s.get('assigned_tool') or '').strip().lower()
            if tool not in valid_tool_ids:
                tool = 'ollama_local'
            steps.append(PlanStep(
                order=int(s.get('order', i + 1)),
                title=str(s.get('title') or f'Paso {i + 1}'),
                description=str(s.get('description') or ''),
                assigned_tool=tool,
                tool_rationale=str(s.get('tool_rationale') or ''),
                requires_approval=bool(s.get('requires_approval')),
                estimated_seconds=int(s.get('estimated_seconds') or 30),
            ))

        if not steps:
            return None

        return CloudPlan(
            user_goal=user_goal,
            summary=str(raw.get('summary') or ''),
            steps=steps,
            cloud_source=str(raw.get('_cloud_source') or 'unknown'),
            confidence=min(1.0, max(0.0, float(raw.get('confidence') or 0.5))),
        )

    # ------------------------------------------------------------------
    # Persist plan for learning
    # ------------------------------------------------------------------

    @staticmethod
    def _persist_plan(plan: CloudPlan) -> None:
        try:
            env_data_dir = os.environ.get('IABV_DATA_DIR', '').strip()
            if env_data_dir:
                data_dir = Path(env_data_dir) / 'evolution' / 'cloud_plans'
            else:
                data_dir = Path.home() / 'IABV_v1.5' / 'data' / 'evolution' / 'cloud_plans'
            data_dir.mkdir(parents=True, exist_ok=True)
            log_path = data_dir / 'plans.jsonl'
            entry = {
                'timestamp': plan.created_at_utc.isoformat(),
                'plan_id': plan.plan_id,
                'user_goal': plan.user_goal[:200],
                'summary': plan.summary[:200],
                'cloud_source': plan.cloud_source,
                'confidence': plan.confidence,
                'step_count': len(plan.steps),
                'tools_used': list({s.assigned_tool for s in plan.steps}),
            }
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(_json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
