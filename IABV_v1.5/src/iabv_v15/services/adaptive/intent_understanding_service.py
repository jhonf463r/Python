from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import InferenceRequest, IntentDisposition, IntentHypothesis, IntentSchema, TaskIntent, TaskRole

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# IntentLearningLayer — aprendizaje persistente de patrones
# ──────────────────────────────────────────────────────────────

def _intent_learning_path() -> Path:
    """Return path to the learned intent patterns JSONL file."""
    env_val = os.environ.get('IABV_DATA_DIR', '').strip()
    data_dir = Path(env_val) if env_val else (
        Path(os.path.expanduser('~')) / 'IABV_v1.5' / 'data'
    )
    learning_dir = data_dir / 'evolution' / 'intent_learning'
    learning_dir.mkdir(parents=True, exist_ok=True)
    return learning_dir / 'learned_patterns.jsonl'


class IntentLearningLayer:
    """Persistent layer that learns intent patterns from user interactions.

    When the system classifies an intent with low confidence or falls back
    to ``general.assistance``, and the user subsequently reformulates or
    the system detects a correction, the learning layer records the mapping:

        normalized_input → confirmed_intent_key

    On startup, learned patterns are loaded and consulted BEFORE the
    hardcoded pattern matching, giving them priority. Patterns that
    accumulate enough confirmations (``_MIN_CONFIRMATIONS``) are promoted
    to "trusted" and bypass the static classification entirely.
    """

    _MIN_CONFIRMATIONS = 3
    _MAX_LEARNED_PATTERNS = 2000

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._patterns: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load learned patterns from JSONL file."""
        path = _intent_learning_path()
        if not path.exists():
            return
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        key = record.get('pattern', '').strip().lower()
                        if key:
                            self._patterns[key] = record
                    except json.JSONDecodeError:
                        continue
            logger.info(
                'intent_learning: loaded %d learned patterns from %s',
                len(self._patterns), path,
            )
        except Exception as exc:
            logger.debug('intent_learning: failed to load: %s', exc)

    def _save(self) -> None:
        """Persist all learned patterns to JSONL file."""
        path = _intent_learning_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                for record in self._patterns.values():
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as exc:
            logger.debug('intent_learning: failed to save: %s', exc)

    def lookup(self, normalized_text: str) -> dict[str, Any] | None:
        """Check if a normalized input matches a learned pattern.

        Returns the learned record if found and confirmed enough times,
        otherwise None. Uses substring matching for flexibility:
        if "dame los comandos para ejecutar" was learned, it also
        matches "dame los comandos para ejecutar mi programa".
        """
        text_lower = normalized_text.strip().lower()
        with self._lock:
            # Exact match first
            exact = self._patterns.get(text_lower)
            if exact and exact.get('confirmations', 0) >= self._MIN_CONFIRMATIONS:
                return exact

            # Substring match — check if any learned pattern is contained
            # in the input or vice versa
            best_match: dict[str, Any] | None = None
            best_score = 0.0
            for pattern_key, record in self._patterns.items():
                if record.get('confirmations', 0) < self._MIN_CONFIRMATIONS:
                    continue
                if pattern_key in text_lower or text_lower in pattern_key:
                    # Score by overlap ratio
                    overlap = len(pattern_key) / max(len(text_lower), 1)
                    if overlap > best_score and overlap > 0.5:
                        best_score = overlap
                        best_match = record
            return best_match

    def record(
        self,
        normalized_text: str,
        intent_key: str,
        *,
        confidence: float = 0.0,
        source: str = 'user_correction',
    ) -> None:
        """Record or reinforce a learned pattern.

        Called when:
        - The user reformulates and the system classifies differently
        - The system falls back to general.assistance and the user
          provides a clearer instruction that resolves to a specific intent
        - An action succeeds after being classified with a specific intent
        """
        text_lower = normalized_text.strip().lower()
        if not text_lower or not intent_key:
            return

        with self._lock:
            existing = self._patterns.get(text_lower)
            if existing:
                if existing.get('intent_key') == intent_key:
                    existing['confirmations'] = existing.get('confirmations', 0) + 1
                    existing['last_seen'] = time.time()
                    existing['confidence'] = max(
                        existing.get('confidence', 0.0), confidence,
                    )
                else:
                    # Intent changed — could be a correction. If the new
                    # intent has higher confidence, override.
                    if confidence > existing.get('confidence', 0.0):
                        existing['intent_key'] = intent_key
                        existing['confirmations'] = 1
                        existing['last_seen'] = time.time()
                        existing['confidence'] = confidence
                        existing['source'] = source
            else:
                if len(self._patterns) >= self._MAX_LEARNED_PATTERNS:
                    # Evict least-confirmed pattern
                    weakest = min(
                        self._patterns,
                        key=lambda k: self._patterns[k].get('confirmations', 0),
                    )
                    del self._patterns[weakest]

                self._patterns[text_lower] = {
                    'pattern': text_lower,
                    'intent_key': intent_key,
                    'confirmations': 1,
                    'confidence': confidence,
                    'first_seen': time.time(),
                    'last_seen': time.time(),
                    'source': source,
                }

            self._save()

    def get_stats(self) -> dict[str, Any]:
        """Return statistics about learned patterns for reporting."""
        with self._lock:
            total = len(self._patterns)
            trusted = sum(
                1 for p in self._patterns.values()
                if p.get('confirmations', 0) >= self._MIN_CONFIRMATIONS
            )
            by_intent: dict[str, int] = {}
            for p in self._patterns.values():
                ik = p.get('intent_key', 'unknown')
                by_intent[ik] = by_intent.get(ik, 0) + 1
            return {
                'total_patterns': total,
                'trusted_patterns': trusted,
                'learning_patterns': total - trusted,
                'by_intent': by_intent,
            }


# Singleton instance — loaded once at import time, persists across calls
_intent_learning_layer = IntentLearningLayer()


class IntentUnderstandingService:
    # M4: registro de fallos por patron para confidence decay.
    # Stores (count, first_failure_epoch) per intent_key so entries
    # older than _FAILURE_EXPIRY_SECONDS auto-expire, preventing
    # permanent penalty from transient issues.
    _pattern_failure_counts: dict[str, tuple[int, float]] = {}
    _pattern_failure_lock = threading.Lock()
    _DECAY_PER_FAILURE = 0.03
    _MAX_DECAY = 0.15
    _FAILURE_EXPIRY_SECONDS = 7200.0  # 2 hours

    SITE_ALIASES = {
        'wplay': ['wplay', 'w play'],
        'mercadolibre': ['mercadolibre', 'mercado libre'],
        'google': ['google'],
    }
    CONVERSATIONAL_INTENT_KEYS = {
        'general.assistance',
        'knowledge.query',
        'system.self_awareness',
        'system.metacognition',
        'consulta_estado_evolutivo',
    }
    ACTIONABLE_INTENT_KEYS = {
        'project.evolution',
        'research.local',
        'research.external_consultation',
        'tools.local_workflow',
        'tools.sandbox',
        'wplay.login',
        'wplay.core',
        'wplay.casino',
        'browser.search',
        'browser.navigate',
        'analytics.strategy',
        'customer.support',
    }
    PROJECT_SIGNAL_PATTERNS = [
        'proyecto',
        'codigo',
        'c?digo',
        'bug',
        'error',
        'fallo',
        'falla',
        'mejora',
        'refactor',
        'convers',
        'intencion',
        'intenci',
        'subintencion',
        'subintenci',
        'contexto',
        'mensaje largo',
        'mensajes largos',
        'desvia',
        'desv?a',
        'desvios',
        'ambig',
        'genera un ',
        'generar un ',
        'genera el ',
        'generar el ',
        'genera la ',
        'generar la ',
        'crea un ',
        'crear un ',
        'crea el ',
        'crear el ',
        'crea la ',
        'crear la ',
        'genera codigo',
        'generar codigo',
        'implementa ',
        'implementar ',
        'analiza los log',
        'analizar los log',
        'analiza el log',
        'analizar el log',
        'analiza el codigo',
        'analizar el codigo',
        'revisa el codigo',
        'revisar el codigo',
    ]
    # Patrones fuertes de generacion/modificacion de codigo que deben rutear a
    # ``project.evolution`` (TaskRole.PROJECT_EVOLUTION) en vez de caer al
    # fallback conversacional ``general.assistance``. Incluye verbos de
    # generacion, artefactos de codigo tipicos y solicitudes de tests.
    CODE_GENERATION_PATTERNS = [
        'genera un parche',
        'genera parche',
        'generar parche',
        'un parche',
        ' parche ',
        'pequeno parche',
        'pequeno cambio',
        'patch ',
        'escribe codigo',
        'escribir codigo',
        'escribe una funcion',
        'escribir una funcion',
        'escribe un metodo',
        'escribir un metodo',
        'implementa una funcion',
        'implementar una funcion',
        'implementa un metodo',
        'implementar un metodo',
        'crea una funcion',
        'crear una funcion',
        'crea un metodo',
        'crear un metodo',
        'genera un script',
        'generar un script',
        'genera un modulo',
        'generar un modulo',
        'genera una clase',
        'generar una clase',
        'genera un servicio',
        'generar un servicio',
        'genera un archivo',
        'generar un archivo',
        'refactoriza',
        'refactorizar',
        'refactor',
        'tests unitarios',
        'test unitario',
        'tests unitario',
        'pruebas unitarias',
        'prueba unitaria',
        'unit tests',
        'unit test',
        'pytest',
        'migra a ',
        'migrar a ',
        'migra el ',
        'migrar el ',
        'agrega un test',
        'agregar un test',
        'anade un test',
        'anadir un test',
        'commitea',
        'commitear',
        'abre un pr',
        'abrir un pr',
        'manda un pr',
        'mandar un pr refactor',
        'fix en ',
        'fixea',
        'fixear',
        'corrige el codigo',
        'corregir el codigo',
        'implementa la clase',
        'implementar la clase',
        'implementa el metodo',
        'implementar el metodo',
    ]
    ACTION_REQUEST_PATTERNS = [
        'necesito',
        'quiero',
        'ayudame',
        'ay?dame',
        'revisa',
        'revisa ',
        'revisar',
        'analiza',
        'analizar',
        'diagnostica',
        'diagnosticar',
        'corrige',
        'corregir',
        'arregla',
        'arreglar',
        'mejora',
        'mejorar',
        'implementa',
        'implementar',
        'ajusta',
        'ajustar',
        'separa',
        'separar',
        'clasifica',
        'clasificar',
        'explica',
        'explicar',
        'dime',
        'responde',
        'marca',
        'confirma',
        'prioriza',
    ]

    @classmethod
    def register_pattern_failure(cls, intent_key: str) -> None:
        """M4: registrar un fallo para un intent_key especifico (thread-safe)."""
        now = time.monotonic()
        with cls._pattern_failure_lock:
            existing = cls._pattern_failure_counts.get(intent_key)
            if existing is not None:
                count, first_ts = existing
                if (now - first_ts) > cls._FAILURE_EXPIRY_SECONDS:
                    cls._pattern_failure_counts[intent_key] = (1, now)
                else:
                    cls._pattern_failure_counts[intent_key] = (count + 1, first_ts)
            else:
                cls._pattern_failure_counts[intent_key] = (1, now)

    @classmethod
    def reset_pattern_failures(cls) -> None:
        """Clear all accumulated pattern failures (useful for test teardown)."""
        with cls._pattern_failure_lock:
            cls._pattern_failure_counts.clear()

    def _confidence_decay(self, intent_key: str) -> float:
        """M4: retorna el decay acumulado para un intent_key (with expiry)."""
        now = time.monotonic()
        with self._pattern_failure_lock:
            existing = self._pattern_failure_counts.get(intent_key)
            if existing is None:
                return 0.0
            count, first_ts = existing
            if (now - first_ts) > self._FAILURE_EXPIRY_SECONDS:
                del self._pattern_failure_counts[intent_key]
                return 0.0
        return min(count * self._DECAY_PER_FAILURE, self._MAX_DECAY)

    def classify(self, request: InferenceRequest) -> tuple[TaskIntent, list[IntentHypothesis]]:
        text = self._normalize(request.user_goal)

        # ── Learned pattern lookup (BEFORE static patterns) ──
        learned = _intent_learning_layer.lookup(text)
        if learned:
            learned_intent_key = str(learned.get('intent_key', ''))
            learned_confidence = min(float(learned.get('confidence', 0.85)), 0.95)
            confirmations = int(learned.get('confirmations', 0))
            logger.info(
                'intent_learning: matched learned pattern — intent=%s '
                'confirmations=%d confidence=%.2f',
                learned_intent_key, confirmations, learned_confidence,
            )
            # Map known intent_keys to their TaskRole (must match static paths)
            role_map: dict[str, TaskRole] = {
                'general.assistance': TaskRole.KNOWLEDGE,
                'knowledge.query': TaskRole.KNOWLEDGE,
                'system.self_awareness': TaskRole.KNOWLEDGE,
                'system.metacognition': TaskRole.TOOL_USE,
                'consulta_estado_evolutivo': TaskRole.KNOWLEDGE,
                'project.evolution': TaskRole.PROJECT_EVOLUTION,
                'research.local': TaskRole.RESEARCH,
                'research.external_consultation': TaskRole.RESEARCH,
                'tools.local_workflow': TaskRole.TOOL_USE,
                'tools.sandbox': TaskRole.TOOL_SANDBOX,
                'wplay.login': TaskRole.TRAINING,
                'wplay.core': TaskRole.TRAINING,
                'wplay.casino': TaskRole.TRAINING,
                'browser.search': TaskRole.TOOL_USE,
                'browser.navigate': TaskRole.TOOL_USE,
                'analytics.strategy': TaskRole.ANALYTICS,
                'customer.support': TaskRole.CUSTOMER_SUPPORT,
            }
            disposition_map: dict[str, IntentDisposition] = {
                'general.assistance': IntentDisposition.ANSWER_NOW,
                'knowledge.query': IntentDisposition.ANSWER_NOW,
                'system.self_awareness': IntentDisposition.ANSWER_NOW,
                'system.metacognition': IntentDisposition.ANSWER_NOW,
                'consulta_estado_evolutivo': IntentDisposition.ANSWER_NOW,
                'project.evolution': IntentDisposition.PLAN_THEN_EXECUTE,
                'research.local': IntentDisposition.PLAN_THEN_EXECUTE,
                'research.external_consultation': IntentDisposition.PLAN_THEN_EXECUTE,
                'tools.local_workflow': IntentDisposition.PLAN_THEN_EXECUTE,
                'tools.sandbox': IntentDisposition.PLAN_THEN_EXECUTE,
                'wplay.login': IntentDisposition.PLAN_THEN_EXECUTE,
                'wplay.core': IntentDisposition.PLAN_THEN_EXECUTE,
                'wplay.casino': IntentDisposition.PLAN_THEN_EXECUTE,
                'browser.search': IntentDisposition.PLAN_THEN_EXECUTE,
                'browser.navigate': IntentDisposition.PLAN_THEN_EXECUTE,
                'analytics.strategy': IntentDisposition.ANSWER_NOW,
                'customer.support': IntentDisposition.ANSWER_NOW,
            }
            detected_role = role_map.get(learned_intent_key, TaskRole.KNOWLEDGE)
            detected_disposition = disposition_map.get(
                learned_intent_key, IntentDisposition.ANSWER_NOW,
            )
            intent = TaskIntent(
                disposition=detected_disposition,
                intent_key=learned_intent_key,
                title=f'Learned: {learned_intent_key}',
                summary=f'Clasificado por patrón aprendido ({confirmations} confirmaciones)',
                detected_role=detected_role,
                site_hint=request.site_hint,
                domain_hint=learned_intent_key.split('.')[0] if '.' in learned_intent_key else 'general',
                confidence=learned_confidence,
                reasoning=[
                    f'patrón aprendido con {confirmations} confirmaciones',
                    f'fuente: {learned.get("source", "unknown")}',
                ],
                metadata={
                    'learned_pattern': True,
                    'learned_confirmations': confirmations,
                },
            )
            hypotheses = [IntentHypothesis(
                intent_key=learned_intent_key,
                title=f'Learned: {learned_intent_key}',
                confidence=learned_confidence,
                rationale=f'Patrón aprendido previamente ({confirmations} confirmaciones)',
            )]
            return intent, hypotheses

        conversation_text = self._conversation_context_text(request.conversation_context)
        detected_site, context_carried_from_history = self._detect_site_with_history(
            text,
            request.goal_parameters,
            conversation_text,
        )
        site_hint = request.site_hint or detected_site
        analysis = self._analyze_conversation(
            text=text,
            request=request,
            site_hint=site_hint,
            conversation_text=conversation_text,
            context_carried_from_history=context_carried_from_history,
        )
        hypotheses: list[IntentHypothesis] = []
        analysis_metadata = {
            'conversation_analysis': analysis,
            'primary_intent': str(analysis.get('primary_intent') or ''),
            'sub_intents': list(analysis.get('sub_intents') or []),
            'compound_intent': bool(analysis.get('compound')),
            'requires_clarification': bool(analysis.get('requires_clarification')),
            'ambiguity_score': float(analysis.get('ambiguity_score') or 0.0),
            'context_carried_from_history': bool(analysis.get('context_carried_from_history')),
        }

        def build(
            *,
            intent_key: str,
            title: str,
            detected_role: TaskRole,
            disposition: IntentDisposition,
            confidence: float,
            domain_hint: str,
            summary: str,
            sensitive: bool = False,
            monetary: bool = False,
            multi_step: bool = False,
            missing_requirements: list[str] | None = None,
            reasoning: list[str] | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> TaskIntent:
            decay = self._confidence_decay(intent_key)
            adjusted_confidence = max(0.1, confidence - decay)
            merged_metadata = {**analysis_metadata, **(metadata or {})}
            if decay > 0:
                merged_metadata['confidence_decay'] = round(decay, 4)
                merged_metadata['original_confidence'] = confidence
            return TaskIntent(
                disposition=disposition,
                intent_key=intent_key,
                title=title,
                summary=summary,
                detected_role=detected_role,
                site_hint=site_hint,
                domain_hint=domain_hint,
                confidence=adjusted_confidence,
                sensitive=sensitive,
                monetary=monetary,
                multi_step=multi_step,
                missing_requirements=missing_requirements or [],
                reasoning=reasoning or [],
                metadata=merged_metadata,
            )

        def finalize(intent: TaskIntent, current_hypotheses: list[IntentHypothesis]) -> tuple[TaskIntent, list[IntentHypothesis]]:
            merged_hypotheses = self._merge_intent_hypotheses(current_hypotheses, analysis)
            if bool(analysis.get('requires_clarification')) and intent.intent_key in {'general.assistance', 'project.evolution', 'research.local'}:
                clarification_prompt = str(analysis.get('clarification_prompt') or '').strip()
                missing_requirements = list(intent.missing_requirements)
                if clarification_prompt and clarification_prompt not in missing_requirements:
                    missing_requirements.insert(0, clarification_prompt)
                reasoning = list(intent.reasoning)
                note = 'mensaje compuesto con ambiguedad fuerte; conviene aclarar antes de asumir'
                if note not in reasoning:
                    reasoning.append(note)
                intent = intent.model_copy(
                    update={
                        'disposition': IntentDisposition.NEED_INFO if intent.disposition == IntentDisposition.ANSWER_NOW else intent.disposition,
                        'missing_requirements': missing_requirements,
                        'reasoning': reasoning,
                        'confidence': min(intent.confidence, 0.58),
                        'metadata': {**intent.metadata, 'requires_clarification': True},
                    }
                )

            # ── Intent Learning: record pattern for future use ──
            if intent.confidence >= 0.7 and intent.intent_key != 'general.assistance':
                _intent_learning_layer.record(
                    text,
                    intent.intent_key,
                    confidence=intent.confidence,
                    source='high_confidence_classification',
                )
            elif intent.intent_key == 'general.assistance':
                # Low-confidence fallback — record as candidate for
                # learning when the user next provides clearer input
                _intent_learning_layer.record(
                    text,
                    intent.intent_key,
                    confidence=intent.confidence,
                    source='fallback_candidate',
                )

            return intent, merged_hypotheses

        if self._contains_any(text, ['hola', 'que sabes hacer', 'quÃ© sabes hacer']) and len(text.split()) <= 8 and not bool(analysis.get('compound')):
            intent = build(
                intent_key='general.assistance',
                title='Asistencia general del centro de control',
                detected_role=TaskRole.KNOWLEDGE,
                disposition=IntentDisposition.ANSWER_NOW,
                confidence=0.93,
                domain_hint='general',
                summary='Responder de forma util y corta sobre capacidades operativas del sistema.',
                reasoning=['saludo o consulta general sobre capacidades'],
                metadata={'conversational_prompt': True, 'meta_assistant_prompt': self._contains_any(text, ['codex', 'chatgpt', 'claude', 'ollama', 'devin', 'windsurf', 'ia', 'ias'])},
            )
            hypotheses.append(IntentHypothesis(intent_key='knowledge.query', title='Consulta local', confidence=0.44, rationale='Pregunta abierta sin sitio especifico.'))
            return finalize(intent, hypotheses)

        if self._is_metacognition_prompt(text):
            intent = build(
                intent_key='system.metacognition',
                title='Metacognicion autonoma: auto-analisis de codigo, GPU y estado',
                detected_role=TaskRole.TOOL_USE,
                disposition=IntentDisposition.ANSWER_NOW,
                confidence=0.96,
                domain_hint='system',
                summary='Ejecutar auto-analisis completo: sintaxis, @Slot, routing, tests, ramas, GPU. Corregir lo que se pueda y reportar con transparencia.',
                reasoning=['peticion explicita de auto-analisis, diagnostico, o revision de codigo propio'],
                metadata={
                    'conversational_prompt': True,
                    'metacognition_prompt': True,
                    'requires_mcp_tools': ['self_code_analysis', 'gpu_metacognition_check'],
                },
            )
            hypotheses.append(
                IntentHypothesis(
                    intent_key='system.self_awareness',
                    title='Autodiagnostico conversacional',
                    confidence=0.55,
                    rationale='Podria ser solo pregunta de estado, pero la peticion pide accion (analisis de codigo).',
                )
            )
            return finalize(intent, hypotheses)

        if self._is_self_awareness_prompt(text) and not bool(analysis.get('mixed_actionable')):
            intent = build(
                intent_key='system.self_awareness',
                title='Autodiagnostico conversacional del sistema',
                detected_role=TaskRole.KNOWLEDGE,
                disposition=IntentDisposition.ANSWER_NOW,
                confidence=0.94,
                domain_hint='system',
                summary='Responder directo desde el estado real del entorno, las herramientas disponibles y las conexiones activas.',
                reasoning=['pregunta explicita por entorno, herramientas, arquitectura o estado actual del sistema'],
                metadata={
                    'conversational_prompt': True,
                    'self_awareness_prompt': True,
                    'meta_assistant_prompt': self._contains_any(text, ['codex', 'chatgpt', 'claude', 'ollama', 'devin', 'windsurf', 'ia', 'ias']),
                },
            )
            hypotheses.append(
                IntentHypothesis(
                    intent_key='knowledge.query',
                    title='Consulta local',
                    confidence=0.61,
                    rationale='La respuesta debe salir del estado real del sistema y no de una consulta externa.',
                )
            )
            return finalize(intent, hypotheses)

        if self._is_evolution_status_prompt(text) and not bool(analysis.get('mixed_actionable')):
            intent = build(
                intent_key='consulta_estado_evolutivo',
                title='Consulta de estado evolutivo',
                detected_role=TaskRole.KNOWLEDGE,
                disposition=IntentDisposition.ANSWER_NOW,
                confidence=0.92,
                domain_hint='evolution',
                summary='Responder desde el estado real de evolucion de herramientas, validacion y discovery sin disparar autonomia.',
                reasoning=['pregunta explicita por ganadores, validacion, descartes o descubrimientos del ciclo evolutivo'],
                metadata={
                    'conversational_prompt': True,
                    'evolution_status_prompt': True,
                },
            )
            hypotheses.append(
                IntentHypothesis(
                    intent_key='knowledge.query',
                    title='Consulta local',
                    confidence=0.58,
                    rationale='La respuesta debe salir del estado evolutivo ya persistido y no de una via externa.',
                )
            )
            return finalize(intent, hypotheses)

        explicit_assistant = self._requested_external_assistant(text)
        if explicit_assistant and not bool(analysis.get('conditional_external_consultation')):
            assistant_title = {
                'codex': 'Codex',
                'chatgpt': 'ChatGPT',
                'claude': 'Claude',
                'ollama': 'Ollama local',
                'devin': 'Devin (Cognition AI)',
                'windsurf': 'Windsurf',
            }.get(explicit_assistant, explicit_assistant.title())
            reasoning = ['el usuario pidio una consulta externa dirigida']
            if site_hint:
                reasoning.append(f'sitio detectado: {site_hint}')
            intent = build(
                intent_key='research.external_consultation',
                title=f'Consulta externa dirigida a {assistant_title}',
                detected_role=TaskRole.RESEARCH,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.9,
                domain_hint='external_assistant',
                summary=f'Preparar una consulta externa dirigida a {assistant_title}, mantener coherencia del asistente y devolver el progreso visible.',
                multi_step=True,
                reasoning=reasoning,
                metadata={'conversational_prompt': False, 'explicit_external_consultation': True},
            )
            hypotheses.append(
                IntentHypothesis(
                    intent_key='knowledge.query',
                    title='Consulta local',
                    confidence=0.31,
                    rationale='Puede responderse parcialmente en local, pero la peticion explicita pide escalar a otra IA.',
                )
            )
            return finalize(intent, hypotheses)

        _has_web_verb = self._contains_any(text, ['buscar', 'busca', 'navega', 'abre', 'abrir', 've a']) and self._contains_any(text, ['internet', 'web', 'en linea', 'online', 'pagina', 'sitio', 'url', 'http', 'google', 'mercadolibre', 'mercado libre'])
        if not _has_web_verb and (self._is_tool_prompt(text, request.goal_parameters) or str(analysis.get('primary_intent') or '') in {'tools.local_workflow', 'tools.sandbox'}):
            sandbox_only = self._contains_any(text, ['sandbox', 'probar herramienta', 'probar tool', 'validar herramienta'])
            intent = build(
                intent_key='tools.sandbox' if sandbox_only else 'tools.local_workflow',
                title='Sandbox de herramientas locales' if sandbox_only else 'Tool Teaching local-first',
                detected_role=TaskRole.TOOL_SANDBOX if sandbox_only else TaskRole.TOOL_USE,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.9 if sandbox_only else 0.86,
                domain_hint='tools',
                summary='Seleccionar herramienta local, validarla en sandbox y ejecutar con trazabilidad.',
                multi_step=True,
                reasoning=['menciona una herramienta local o una prueba de sandbox'],
            )
            hypotheses.append(IntentHypothesis(intent_key='project.evolution', title='Evolucion del proyecto', confidence=0.38, rationale='La consulta puede terminar en ajuste tecnico o Codex si la herramienta falla.'))
            return finalize(intent, hypotheses)
        if site_hint == 'wplay' and self._contains_any(text, ['casino', 'juega', 'jugar', 'apuesta', 'estrategia', 'algoritmo']):
            missing = []
            if not self._contains_any(text, ['estrateg', 'algoritmo', 'limite', 'lÃ­mite', 'stop']):
                missing.append('conviene confirmar o editar la estrategia antes de ejecutar fases sensibles')
            intent = build(
                intent_key='wplay.casino',
                title='Sesion Wplay para casino y estrategia',
                detected_role=TaskRole.TRAINING,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.95,
                domain_hint='wplay',
                summary='Preparar una sesion por fases para entrar a Wplay, navegar a casino y configurar estrategia con checkpoints.',
                sensitive=True,
                monetary=True,
                multi_step=True,
                missing_requirements=missing,
                reasoning=['menciona Wplay', 'menciona juego o casino', 'requiere estrategia configurable y aprobaciones'],
            )
            hypotheses.extend([
                IntentHypothesis(intent_key='wplay.login', title='Login Wplay', confidence=0.86, rationale='La ejecucion de casino depende del login.'),
                IntentHypothesis(intent_key='wplay.core', title='Core Wplay', confidence=0.78, rationale='Hay una tarea operativa sobre el sitio.'),
            ])
            return finalize(intent, hypotheses)

        if site_hint == 'wplay' and self._contains_any(text, ['inicia sesion', 'iniciar sesion', 'login', 'loguea', 'abre wplay']):
            intent = build(
                intent_key='wplay.login',
                title='Sesion Wplay e inicio de sesion',
                detected_role=TaskRole.TRAINING,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.94,
                domain_hint='wplay',
                summary='Preparar la apertura de Wplay y el inicio de sesion usando capacidades aprendidas y aprobacion por fases.',
                sensitive=True,
                multi_step=True,
                reasoning=['menciona Wplay', 'menciona inicio de sesion o login'],
            )
            hypotheses.append(IntentHypothesis(intent_key='wplay.core', title='Core Wplay', confidence=0.67, rationale='Sesion operativa sobre Wplay.'))
            return finalize(intent, hypotheses)

        if site_hint == 'wplay' and self._contains_any(text, ['abre', 'abrir', 'pagina', 'p?gina', 'entra', 'ingresa', 've a']):
            intent = build(
                intent_key='wplay.core',
                title='Abrir Wplay y preparar sesion',
                detected_role=TaskRole.TRAINING,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.9,
                domain_hint='wplay',
                summary='Abrir Wplay, validar si la sesion puede restaurarse y dejar lista la siguiente fase sin saltar directo a acciones criticas.',
                sensitive=False,
                multi_step=True,
                reasoning=['menciona Wplay', 'pide abrir o entrar al sitio'],
            )
            hypotheses.append(IntentHypothesis(intent_key='wplay.login', title='Login Wplay', confidence=0.74, rationale='Si la sesion no se restaura, el siguiente paso sera login guiado.'))
            return finalize(intent, hypotheses)

        _web_context_detected = self._contains_any(text, [
            'internet', 'web', 'en linea', 'online',
            'pagina', 'sitio', 'url', 'http',
        ])
        if self._contains_any(text, ['abre', 'abrir', 've a', 'buscar', 'busca', 'navega']) and (site_hint is not None or self._contains_any(text, ['google', 'mercadolibre', 'mercado libre']) or _web_context_detected):
            target_title = 'Busqueda web guiada' if self._contains_any(text, ['buscar', 'busca']) else 'Navegacion web guiada'
            intent_key = 'browser.search' if self._contains_any(text, ['buscar', 'busca']) else 'browser.navigate'
            reasoning = ['hay un verbo operativo de navegador']
            if site_hint:
                reasoning.append(f'sitio detectado: {site_hint}')
            if _web_context_detected:
                reasoning.append('contexto web explicito (internet/web/online/pagina/sitio)')
            intent = build(
                intent_key=intent_key,
                title=target_title,
                detected_role=TaskRole.TRAINING,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.82,
                domain_hint='browser',
                summary='Preparar navegacion guiada por fases sobre navegador o sitio especifico.',
                sensitive=site_hint == 'wplay',
                multi_step=True,
                reasoning=reasoning,
            )
            return finalize(intent, hypotheses)

        if self._is_project_prompt(text) or str(analysis.get('primary_intent') or '') == 'project.evolution':
            disposition = IntentDisposition.PLAN_THEN_EXECUTE if request.deep_reasoning or len(text.split()) >= 12 else IntentDisposition.ANSWER_NOW
            code_generation_match = self._is_code_generation_prompt(text)
            reasoning = ['consulta relacionada con codigo o arquitectura']
            if code_generation_match:
                reasoning.append('patrones explicitos de generacion o modificacion de codigo detectados')
            if bool(analysis.get('compound')):
                reasoning.append('mensaje compuesto con intencion principal y subintenciones detectadas')
            if bool(analysis.get('context_carried_from_history')):
                reasoning.append('continuidad conversacional aplicada desde el historial reciente')
            sub_intents = [str(item) for item in (analysis.get('sub_intents') or []) if str(item).strip()]
            if sub_intents:
                reasoning.append('subintenciones detectadas: ' + ', '.join(sub_intents[:3]))
            intent = build(
                intent_key='project.evolution',
                title='Evolucion del proyecto',
                detected_role=TaskRole.PROJECT_EVOLUTION,
                disposition=disposition,
                confidence=0.88,
                domain_hint='project',
                summary='Revisar evidencia del repo, fallos y mejoras verticales priorizadas.',
                multi_step=disposition == IntentDisposition.PLAN_THEN_EXECUTE,
                reasoning=reasoning,
                metadata={'code_generation_prompt': code_generation_match} if code_generation_match else None,
            )
            return finalize(intent, hypotheses)

        if self._contains_any(text, ['marketing', 'estadistica', 'estadisticas', 'metricas', 'campana', 'campaÃ±a', 'roi', 'embudo', 'conversion']):
            intent = build(
                intent_key='analytics.strategy',
                title='Analitica y estrategia',
                detected_role=TaskRole.ANALYTICS,
                disposition=IntentDisposition.ANSWER_NOW if len(text.split()) < 14 else IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.84,
                domain_hint='analytics',
                summary='Responder con metricas locales y, si hace falta, proponer una estrategia por fases.',
                multi_step=len(text.split()) >= 14,
                reasoning=['consulta analitica o de marketing'],
            )
            return finalize(intent, hypotheses)

        if self._contains_any(text, ['cliente', 'soporte', 'respuesta al cliente', 'pedido', 'producto', 'formas de pago', 'horario']):
            intent = build(
                intent_key='customer.support',
                title='Atencion al cliente',
                detected_role=TaskRole.CUSTOMER_SUPPORT,
                disposition=IntentDisposition.ANSWER_NOW,
                confidence=0.84,
                domain_hint='customer',
                summary='Construir una respuesta local apoyada en conocimiento y datos internos.',
                reasoning=['consulta de soporte o cliente'],
            )
            return finalize(intent, hypotheses)

        if self._contains_any(text, ['investiga', 'investigar', 'compar', 'benchmark', 'analiza a fondo', 'tendencia']) or str(analysis.get('primary_intent') or '') == 'research.local':
            intent = build(
                intent_key='research.local',
                title='Investigacion local',
                detected_role=TaskRole.RESEARCH,
                disposition=IntentDisposition.PLAN_THEN_EXECUTE,
                confidence=0.79,
                domain_hint='research',
                summary='Sintetizar evidencia local, conocimiento y huecos antes de proponer la siguiente linea de trabajo.',
                multi_step=True,
                reasoning=['consulta de investigacion o comparacion'],
            )
            return finalize(intent, hypotheses)

        if self._contains_any(text, ['conocimiento', 'base de conocimiento', 'documentacion', 'documentaciÃ³n', 'memoria', 'consulta', 'que sabes', 'quÃ© sabes']) or str(analysis.get('primary_intent') or '') == 'knowledge.query':
            intent = build(
                intent_key='knowledge.query',
                title='Consulta a la base local',
                detected_role=TaskRole.KNOWLEDGE,
                disposition=IntentDisposition.ANSWER_NOW,
                confidence=0.77,
                domain_hint='knowledge',
                summary='Responder desde conocimiento, memoria local y ejecuciones recientes sin preguntas genericas.',
                reasoning=['consulta de memoria o base de conocimiento'],
                metadata={'conversational_prompt': True, 'meta_assistant_prompt': self._contains_any(text, ['codex', 'chatgpt', 'claude', 'ollama', 'devin', 'windsurf', 'ia', 'ias'])},
            )
            return finalize(intent, hypotheses)

        missing_requirements = []
        if self._contains_any(text, ['abre', 'abrir', 've a', 'navega', 'buscar', 'busca']) and site_hint is None:
            missing_requirements.append('indica el sitio o la URL exacta para preparar la estrategia')
        disposition = IntentDisposition.NEED_INFO if missing_requirements else IntentDisposition.ANSWER_NOW
        intent = build(
            intent_key='general.assistance',
            title='Asistencia adaptativa general',
            detected_role=TaskRole.KNOWLEDGE,
            disposition=disposition,
            confidence=0.62,
            domain_hint='general',
            summary='Aterrizar la intencion y responder con el siguiente paso util sin preguntas vagas.',
            missing_requirements=missing_requirements,
            reasoning=['no coincide con un dominio fuerte, se aplica fallback adaptativo'],
            metadata={'conversational_prompt': disposition == IntentDisposition.ANSWER_NOW},
        )
        return finalize(intent, hypotheses)

    def classify_with_schema(
        self,
        user_goal: str,
        goal_parameters: dict[str, Any] | None = None,
        *,
        conversation_history: list[dict[str, Any]] | None = None,
        request: InferenceRequest | None = None,
    ) -> tuple[TaskIntent, IntentSchema | None]:
        if request is not None:
            # Respect the caller's full request (site_hint, task_role, allowed_tools,
            # prompt, deep_reasoning, requires_vision, screenshots, steps, etc.).
            # Only enrich the fields we were given explicitly.
            metadata = dict(request.metadata or {})
            if conversation_history is not None:
                metadata['conversation_history'] = conversation_history
            updates: dict[str, Any] = {'metadata': metadata}
            if user_goal and user_goal != request.user_goal:
                updates['user_goal'] = user_goal
            if goal_parameters:
                merged_parameters = dict(request.goal_parameters or {})
                merged_parameters.update(goal_parameters)
                updates['goal_parameters'] = merged_parameters
            if conversation_history is not None:
                updates['conversation_context'] = conversation_history
            request = request.model_copy(update=updates)
        else:
            request = InferenceRequest(
                user_goal=user_goal,
                goal_parameters=goal_parameters or {},
                conversation_context=conversation_history or [],
                metadata={'conversation_history': conversation_history or []},
            )
        intent, hypotheses = self.classify(request)
        intent = intent.model_copy(update={'hypotheses': hypotheses})

        # ── Cross-turn learning: ONLY when the previous turn was a
        #    fallback (general.assistance) or low-confidence, and THIS
        #    turn resolved to a specific intent with high confidence ──
        if (
            intent.intent_key != 'general.assistance'
            and intent.confidence >= 0.7
            and conversation_history
        ):
            for prev_msg in reversed(conversation_history[-3:]):
                prev_role = str(prev_msg.get('role', '')).strip().lower()
                if prev_role in ('user', 'human'):
                    prev_intent = str(prev_msg.get('intent_key', '')).strip()
                    prev_confidence = float(prev_msg.get('confidence', 1.0))
                    was_fallback = (
                        prev_intent == 'general.assistance'
                        or prev_confidence < 0.65
                    )
                    if not was_fallback:
                        break
                    prev_text = self._normalize(str(prev_msg.get('content', '')))
                    if prev_text and len(prev_text.split()) >= 3:
                        _intent_learning_layer.record(
                            prev_text,
                            intent.intent_key,
                            confidence=intent.confidence * 0.8,
                            source='cross_turn_correction',
                        )
                    break

        analysis: dict[str, Any] = dict(intent.metadata.get('conversation_analysis') or {})
        sub_intents = list(analysis.get('sub_intents') or [])
        ambiguity_score = float(analysis.get('ambiguity_score') or 0.0)
        risk_level = 'high' if intent.sensitive or intent.monetary else (
            'medium' if ambiguity_score >= 0.5 or intent.multi_step else 'low'
        )
        semantic_source = 'conversation_analysis'
        if intent.metadata.get('learned_pattern'):
            semantic_source = 'learned_pattern'
        schema = IntentSchema(
            primary_intent=intent.intent_key,
            sub_intents=sub_intents,
            ambiguity_score=ambiguity_score,
            requires_clarification=bool(analysis.get('requires_clarification')),
            clarification_prompt=str(analysis.get('clarification_prompt') or ''),
            risk_level=risk_level,
            confidence=intent.confidence,
            semantic_source=semantic_source,
            compound=bool(analysis.get('compound')),
            constraints=list(analysis.get('constraints') or []),
            objective_summary=str(analysis.get('objective_summary') or ''),
            context_carried_from_history=bool(analysis.get('context_carried_from_history')),
        )
        return intent, schema

    @staticmethod
    def get_learning_stats() -> dict[str, Any]:
        """Return statistics about learned intent patterns."""
        return _intent_learning_layer.get_stats()

    @staticmethod
    def record_intent_correction(
        normalized_text: str,
        correct_intent_key: str,
        confidence: float = 0.9,
    ) -> None:
        """Manually teach the system a correct intent for an input.

        Called by external services (e.g., ControlCenterViewModel) when
        the user explicitly corrects a misclassification.
        """
        _intent_learning_layer.record(
            normalized_text,
            correct_intent_key,
            confidence=confidence,
            source='explicit_user_correction',
        )

    def _analyze_conversation(
        self,
        *,
        text: str,
        request: InferenceRequest,
        site_hint: str | None,
        conversation_text: str,
        context_carried_from_history: bool,
    ) -> dict[str, Any]:
        segments = self._segment_message(text)
        candidate_scores: dict[str, dict[str, Any]] = {}
        conditional_external = self._contains_any(
            text,
            [
                'si hace falta',
                'si conviene',
                'si toca',
                'si lo ves necesario',
                'si vale la pena',
                'despues decide',
                'despu?s decide',
                'si no puedes',
            ],
        )

        def register(intent_key: str, score: float, reason: str) -> None:
            bucket = candidate_scores.setdefault(intent_key, {'intent_key': intent_key, 'score': 0.0, 'reasons': []})
            bucket['score'] = float(bucket.get('score') or 0.0) + float(score)
            reasons = list(bucket.get('reasons') or [])
            if reason not in reasons:
                reasons.append(reason)
            bucket['reasons'] = reasons

        if self._is_metacognition_prompt(text):
            register('system.metacognition', 6.0, 'peticion de auto-analisis, diagnostico de codigo, o metacognicion')
        if self._is_self_awareness_prompt(text):
            register('system.self_awareness', 5.0, 'pregunta explicita por entorno, herramientas o conexiones')
        if self._is_evolution_status_prompt(text):
            register('consulta_estado_evolutivo', 5.0, 'pregunta explicita por estado evolutivo o discovery')
        explicit_assistant = self._requested_external_assistant(text)
        if explicit_assistant:
            register(
                'research.external_consultation',
                5.0 if not conditional_external else 2.0,
                f'consulta externa mencionada para {explicit_assistant}',
            )
        if self._is_tool_prompt(text, request.goal_parameters):
            register(
                'tools.sandbox' if self._contains_any(text, ['sandbox', 'probar herramienta', 'probar tool', 'validar herramienta']) else 'tools.local_workflow',
                4.0,
                'mensaje asociado a herramientas locales o sandbox',
            )
        if site_hint == 'wplay' and self._contains_any(text, ['casino', 'juega', 'jugar', 'apuesta', 'estrategia', 'algoritmo']):
            register('wplay.casino', 5.0, 'flujo Wplay orientado a casino o estrategia')
        if site_hint == 'wplay' and self._contains_any(text, ['inicia sesion', 'iniciar sesion', 'login', 'loguea', 'abre wplay']):
            register('wplay.login', 5.0, 'flujo Wplay orientado a login')
        if site_hint == 'wplay' and self._contains_any(text, ['abre', 'abrir', 'pagina', 'p?gina', 'entra', 'ingresa', 've a']):
            register('wplay.core', 4.0, 'flujo Wplay orientado a navegacion base')
        _web_ctx = self._contains_any(text, ['internet', 'web', 'en linea', 'online', 'pagina', 'sitio', 'url', 'http'])
        if self._contains_any(text, ['abre', 'abrir', 've a', 'buscar', 'busca', 'navega']) and (site_hint is not None or self._contains_any(text, ['google', 'mercadolibre', 'mercado libre']) or _web_ctx):
            register(
                'browser.search' if self._contains_any(text, ['buscar', 'busca']) else 'browser.navigate',
                3.5,
                'mensaje operativo de navegador sobre sitio conocido o contexto web explicito',
            )
        if self._is_project_prompt(text):
            project_score = 4.0
            if self._contains_any(text, self.ACTION_REQUEST_PATTERNS):
                project_score += 1.0
            if len(segments) >= 3:
                project_score += 0.5
            register('project.evolution', project_score, 'mensaje tecnico sobre proyecto, chat o comprension conversacional')
        if self._contains_any(text, ['marketing', 'estadistica', 'estadisticas', 'metricas', 'campana', 'campaÃ±a', 'roi', 'embudo', 'conversion']):
            register('analytics.strategy', 4.0, 'mensaje de analitica o marketing')
        if self._contains_any(text, ['cliente', 'soporte', 'respuesta al cliente', 'pedido', 'producto', 'formas de pago', 'horario']):
            register('customer.support', 4.0, 'mensaje de soporte o atencion al cliente')
        if self._contains_any(text, ['investiga', 'investigar', 'compar', 'benchmark', 'analiza a fondo', 'tendencia']):
            register('research.local', 4.0, 'mensaje de investigacion o comparacion')
        if self._contains_any(text, ['conocimiento', 'base de conocimiento', 'documentacion', 'documentaciÃ³n', 'memoria', 'consulta', 'que sabes', 'quÃ© sabes']):
            register('knowledge.query', 3.0, 'mensaje de memoria o base local')
        if context_carried_from_history and site_hint:
            register('general.assistance', 0.5, f'continuidad conversacional aplicada desde {site_hint}')
        if not candidate_scores:
            register('general.assistance', 1.0, 'fallback adaptativo')
        ordered = sorted(
            candidate_scores.values(),
            key=lambda item: (-float(item.get('score') or 0.0), str(item.get('intent_key') or '')),
        )
        primary_intent = str(ordered[0].get('intent_key') or 'general.assistance')
        best_actionable = next(
            (item for item in ordered if str(item.get('intent_key') or '') in self.ACTIONABLE_INTENT_KEYS),
            None,
        )
        if primary_intent in self.CONVERSATIONAL_INTENT_KEYS and best_actionable is not None:
            if float(best_actionable.get('score') or 0.0) >= float(ordered[0].get('score') or 0.0) - 1.0:
                primary_intent = str(best_actionable.get('intent_key') or primary_intent)
        top_score = float(ordered[0].get('score') or 0.0)
        sub_intents: list[str] = []
        for item in ordered:
            intent_key = str(item.get('intent_key') or '')
            if not intent_key or intent_key == primary_intent:
                continue
            if float(item.get('score') or 0.0) >= max(2.0, top_score - 2.0):
                sub_intents.append(intent_key)
        sub_intents = list(dict.fromkeys(sub_intents))[:4]
        actionable_candidates = [
            str(item.get('intent_key') or '')
            for item in ordered
            if str(item.get('intent_key') or '') in self.ACTIONABLE_INTENT_KEYS
        ]
        conversational_candidates = [
            str(item.get('intent_key') or '')
            for item in ordered
            if str(item.get('intent_key') or '') in self.CONVERSATIONAL_INTENT_KEYS
        ]
        mixed_actionable = bool(actionable_candidates) and (
            bool(conversational_candidates)
            or len(set(actionable_candidates)) > 1
            or bool(sub_intents)
        )
        ambiguity_score = 0.0

        # Length: longer messages tend to be more complex
        if len(text.split()) >= 24:
            ambiguity_score += 0.12
        elif len(text.split()) >= 16:
            ambiguity_score += 0.06

        # Segments: multiple logical breaks indicate complexity
        if len(segments) >= 3:
            ambiguity_score += min(0.24, 0.08 * (len(segments) - 1))
        elif len(segments) == 2:
            # Two segments with "pero", "aunque", "luego" connectors often indicate alternatives
            ambiguity_score += 0.08

        # Sub-intents: multiple detected intents indicate compound message
        if sub_intents:
            ambiguity_score += min(0.3, 0.12 * len(sub_intents))

        # Uncertainty markers: explicit expressions of doubt/alternatives
        has_uncertainty = self._contains_any(text, ['quizas', 'quiz?', 'tal vez', 'no se', 'duda', 'ambig', 'conviene', 'amerita'])
        if has_uncertainty:
            ambiguity_score += 0.22

        # Temporal uncertainty: phrases like "ahora o despues", "despues o ahora" express ordering doubt
        has_temporal_uncertainty = self._contains_any(text, ['ahora o despues', 'despues o ahora', 'despues o luego', 'si ahora o despues', 'no se si ahora', 'no se cuando'])
        if has_temporal_uncertainty:
            ambiguity_score += 0.18

        # Conditional secondary actions: "quizas" + action verb indicates tentative intent
        action_verbs = ['revisa', 'revisar', 'refactor', 'refactoriza', 'mejora', 'mejorar', 'ajusta', 'arregla', 'arreglar', 'analiza', 'analizar']
        has_multiple_actions = sum(1 for verb in action_verbs if verb in text)
        if has_multiple_actions >= 2:
            ambiguity_score += 0.15
        elif has_multiple_actions == 1 and has_uncertainty:
            # Single action but expressed with uncertainty (quizas + verb)
            ambiguity_score += 0.10

        # Score margin between top candidates
        if len(ordered) > 1:
            score_margin = float(ordered[0].get('score') or 0.0) - float(ordered[1].get('score') or 0.0)
            if score_margin <= 0.5:
                ambiguity_score += 0.22
            elif score_margin <= 1.0:
                ambiguity_score += 0.12

        if conditional_external:
            ambiguity_score += 0.08

        ambiguity_score = round(min(1.0, ambiguity_score), 2)
        requires_clarification = ambiguity_score >= 0.78 or (primary_intent == 'general.assistance' and len(sub_intents) >= 2)
        clarification_prompt = (
            'Detecte varias intenciones mezcladas. Confirma que quieres que atienda primero: '
            f'{primary_intent}.'
            if requires_clarification
            else ''
        )
        request_like_segments = [
            segment['text']
            for segment in segments
            if 'request' in list(segment.get('labels') or []) or 'instruction' in list(segment.get('labels') or [])
        ]
        objective_summary = request_like_segments[0] if request_like_segments else (segments[0]['text'] if segments else text)
        return {
            'primary_intent': primary_intent,
            'sub_intents': sub_intents,
            'candidate_intents': [
                {
                    'intent_key': str(item.get('intent_key') or ''),
                    'score': round(float(item.get('score') or 0.0), 2),
                    'reasons': list(item.get('reasons') or []),
                }
                for item in ordered[:6]
            ],
            'segments': segments,
            'compound': len(segments) > 1 or bool(sub_intents),
            'mixed_actionable': mixed_actionable,
            'ambiguity_score': ambiguity_score,
            'requires_clarification': requires_clarification,
            'clarification_prompt': clarification_prompt,
            'objective_summary': objective_summary,
            'constraints': self._extract_constraints(text, segments),
            'context_carried_from_history': bool(context_carried_from_history and not request.site_hint),
            'conversation_turns_used': min(len(request.conversation_context or []), 6) if conversation_text else 0,
            'conditional_external_consultation': conditional_external,
        }

    def _conversation_context_text(self, conversation_context: list[dict[str, Any]] | None) -> str:
        if not conversation_context:
            return ''
        snippets: list[str] = []
        for item in conversation_context[-6:]:
            if not isinstance(item, dict):
                continue
            parts = [str(item.get('text') or '').strip(), str(item.get('meta') or '').strip()]
            merged = ' '.join(part for part in parts if part)
            if merged:
                snippets.append(merged)
        return self._normalize(' '.join(snippets)) if snippets else ''

    def _segment_message(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []
        raw_segments = re.split(
            r'(?<=[\.\?\!\n;:])\s+|\s+(?:pero|aunque|ademas|además|luego|despues|después|por otro lado)\s+',
            text,
        )
        segments: list[dict[str, Any]] = []
        for raw in raw_segments:
            cleaned = ' '.join(str(raw or '').strip(' ,;:-').split())
            if not cleaned:
                continue
            labels = self._segment_labels(cleaned)
            segments.append(
                {
                    'text': cleaned,
                    'labels': labels,
                    'primary_label': labels[0] if labels else 'statement',
                }
            )
        return segments[:8]

    def _segment_labels(self, segment: str) -> list[str]:
        lowered = self._normalize(segment)
        labels: list[str] = []
        if self._contains_any(lowered, ['te doy contexto', 'contexto', 'pasa que', 'viene de', 'venimos de', 'el problema', 'sigue', 'porque', 'por que']):
            labels.append('context')
        if self._contains_any(lowered, self.ACTION_REQUEST_PATTERNS):
            labels.append('request')
        if self._contains_any(lowered, ['sin ', 'no ', 'debe', 'evita', 'primero', 'antes', 'si hay ambig', 'si no puedes', 'sin ejecutar', 'no ejecutes', 'no invent', 'no asum']):
            labels.append('criteria')
        if self._contains_any(lowered, ['revisa', 'analiza', 'corrige', 'arregla', 'separa', 'clasifica', 'responde', 'dilo claro', 'marca', 'confirma', 'prioriza', 'no ejecutes']):
            labels.append('instruction')
        if '?' in segment or self._contains_any(lowered, ['duda', 'no se', 'quizas', 'quiz?', 'tal vez', 'conviene', 'amerita']):
            labels.append('doubt')
        if not labels:
            labels.append('statement')
        order = {'request': 0, 'context': 1, 'criteria': 2, 'instruction': 3, 'doubt': 4, 'statement': 5}
        return sorted(list(dict.fromkeys(labels)), key=lambda label: order.get(label, 99))

    def _extract_constraints(self, text: str, segments: list[dict[str, Any]]) -> list[str]:
        constraints: list[str] = []
        direct_constraints = {
            'no ejecutes': 'no ejecutar todavia',
            'sin ejecutar': 'no ejecutar todavia',
            'si hay ambig': 'explicitar ambiguedad fuerte',
            'no invent': 'no inventar',
            'no asum': 'no asumir',
            'dilo claro': 'declarar limites con claridad',
            'responde primero': 'responder primero la intencion principal',
        }
        for probe, label in direct_constraints.items():
            if probe in text and label not in constraints:
                constraints.append(label)
        for segment in segments:
            labels = list(segment.get('labels') or [])
            if 'criteria' in labels:
                snippet = str(segment.get('text') or '').strip()
                if snippet and snippet not in constraints:
                    constraints.append(snippet)
        return constraints[:5]

    def _merge_intent_hypotheses(
        self,
        current_hypotheses: list[IntentHypothesis],
        analysis: dict[str, Any],
    ) -> list[IntentHypothesis]:
        merged = list(current_hypotheses)
        seen = {item.intent_key for item in merged}
        primary_intent = str(analysis.get('primary_intent') or '')
        for item in list(analysis.get('candidate_intents') or []):
            intent_key = str(item.get('intent_key') or '')
            if not intent_key or intent_key == primary_intent or intent_key in seen:
                continue
            score = float(item.get('score') or 0.0)
            if score < 2.0:
                continue
            rationale = '; '.join(str(reason) for reason in list(item.get('reasons') or [])[:2]) or 'Subintencion detectada en un mensaje compuesto.'
            merged.append(
                IntentHypothesis(
                    intent_key=intent_key,
                    title=self._intent_title(intent_key),
                    confidence=round(min(0.84, max(0.35, score / 6.0)), 2),
                    rationale=rationale,
                )
            )
            seen.add(intent_key)
        return merged

    def _intent_title(self, intent_key: str) -> str:
        return {
            'general.assistance': 'Asistencia general',
            'knowledge.query': 'Consulta local',
            'system.self_awareness': 'Autodiagnostico conversacional',
            'system.metacognition': 'Metacognicion autonoma',
            'consulta_estado_evolutivo': 'Consulta de estado evolutivo',
            'research.external_consultation': 'Consulta externa dirigida',
            'research.local': 'Investigacion local',
            'project.evolution': 'Evolucion del proyecto',
            'tools.local_workflow': 'Tool Teaching local-first',
            'tools.sandbox': 'Sandbox de herramientas',
            'wplay.login': 'Login Wplay',
            'wplay.core': 'Core Wplay',
            'wplay.casino': 'Casino Wplay',
            'browser.search': 'Busqueda web guiada',
            'browser.navigate': 'Navegacion web guiada',
            'analytics.strategy': 'Analitica y estrategia',
            'customer.support': 'Atencion al cliente',
        }.get(intent_key, intent_key)

    def _is_tool_prompt(self, text: str, goal_parameters: dict[str, Any]) -> bool:
        if goal_parameters.get('tool_id'):
            return True
        if self._contains_any(text, ['playwright', 'ollama', 'aider', 'mcp', 'powershell', 'shell']):
            return True
        if self._contains_any(text, ['herramienta local', 'herramientas locales', 'tool local', 'tools locales', 'local-first']):
            return True
        if 'tool' in text:
            return True
        return 'herramienta' in text and self._contains_any(
            text,
            [
                'sandbox',
                'probar herramienta',
                'probar tool',
                'validar herramienta',
                'adaptador',
                'workflow',
                'usa la herramienta',
                'usar herramienta',
                'ejecuta la herramienta',
            ],
        )

    def _is_code_generation_prompt(self, text: str) -> bool:
        """Detecta pedidos explicitos de generacion/modificacion de codigo.

        Cubre goals que antes caian al fallback ``general.assistance`` por
        no contener las palabras fuertes (``codigo``/``bug``/``refactor``)
        pese a ser peticiones claras de trabajo tecnico: ``genera un parche``,
        ``escribe tests unitarios``, ``implementa una funcion``, etc.
        """

        return self._contains_any(text, self.CODE_GENERATION_PATTERNS)

    def _is_project_prompt(self, text: str) -> bool:
        strong_project_terms = self._contains_any(
            text,
            ['proyecto', 'codigo', 'c?digo', 'bug', 'error', 'fallo', 'falla', 'mejora', 'refactor'],
        )
        conversational_issue_terms = self._contains_any(
            text,
            ['convers', 'intencion', 'intenci', 'subintencion', 'subintenci', 'contexto', 'mensaje largo', 'mensajes largos', 'desvia', 'desv?a', 'ambig'],
        )
        action_signals = self._contains_any(
            text,
            self.ACTION_REQUEST_PATTERNS
            + ['por que', 'porque', 'diagnostico', 'diagnosticar', 'decide', 'prioriza'],
        )
        architecture_request = 'arquitectura' in text and action_signals
        return (
            strong_project_terms
            or self._is_code_generation_prompt(text)
            or (conversational_issue_terms and action_signals)
            or architecture_request
        )

    def _is_metacognition_prompt(self, text: str) -> bool:
        """Detecta peticiones de auto-analisis de codigo, diagnostico de rendimiento,
        revision de GPU, o metacognicion general. Diferencia clave vs self_awareness:
        self_awareness = 'que herramientas tienes' (informacional)
        metacognition  = 'analiza tu codigo, busca errores' (accion sobre si mismo)
        """
        if not text:
            return False
        direct_phrases = (
            'analizate', 'analízate', 'analiza tu codigo', 'analiza tu código',
            'revisa tu codigo', 'revisa tu código', 'busca errores', 'busca fallas',
            'busca bugs', 'autoanalisis', 'autoanálisis', 'auto analisis',
            'auto análisis', 'auto diagnostico', 'autodiagnostico', 'autodiagnóstico',
            'por que te congelas', 'por qué te congelas', 'por que estas lento',
            'por qué estás lento', 'por que respondes lento', 'por qué respondes lento',
            'analiza tu estado', 'diagnostica tu estado', 'diagnosticate', 'diagnostícate',
            'examina tu codigo', 'examina tu código', 'revisa tu estado real',
            'reporte de tu estado', 'mejoras pendientes', 'ramas sin mergear',
            'ramas pendientes', 'codigo desactualizado', 'código desactualizado',
            'tu gpu esta funcionando', 'tu gpu está funcionando', 'revisa tu gpu',
            'self code analysis', 'self_code_analysis', 'actualizate y analizate',
            'actualízate y analízate', 'analiza tu rendimiento', 'analiza tu salud',
            'corrige lo que puedas', 'tu codigo tiene errores', 'tu código tiene errores',
        )
        if any(phrase in text for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', text))
        asks_self = any(t in word_tokens for t in ('analizate', 'analízate', 'autoanalisis', 'diagnosticate', 'metacognicion'))
        asks_code = any(t in word_tokens for t in ('codigo', 'código', 'errores', 'fallas', 'bugs', 'sintaxis'))
        asks_perf = any(t in word_tokens for t in ('lento', 'congela', 'congelas', 'rendimiento', 'lentitud'))
        asks_analyze = any(t in text for t in ('analiza', 'revisa', 'examina', 'diagnostica', 'busca'))
        if asks_analyze and (asks_code or asks_perf):
            return True
        if asks_self:
            return True
        return False

    def _is_self_awareness_prompt(self, text: str) -> bool:
        if not text:
            return False
        direct_phrases = (
            'conoces tu entorno',
            'conoce tu entorno',
            'sabes tu entorno',
            'sabes tu arquitectura',
            'conoces tu arquitectura',
            'que herramientas tienes',
            'quÃ© herramientas tienes',
            'que herramientas tienes disponibles',
            'quÃ© herramientas tienes disponibles',
            'que herramientas hay disponibles',
            'quÃ© herramientas hay disponibles',
            'con que ias te conectas',
            'con quÃ© ias te conectas',
            'con que ias te puedes conectar',
            'con quÃ© ias te puedes conectar',
            'con que ia te conectas',
            'con quÃ© ia te conectas',
            'con que ia te puedes conectar',
            'con quÃ© ia te puedes conectar',
            'con que asistentes te conectas',
            'con quÃ© asistentes te conectas',
            'con que asistentes te puedes conectar',
            'con quÃ© asistentes te puedes conectar',
            'que tan consciente eres',
            'quÃ© tan consciente eres',
            'que tan bien estas',
            'quÃ© tan bien estÃ¡s',
            'que tan bien estas ahora',
            'quÃ© tan bien estÃ¡s ahora',
            'como estas ahora',
            'cÃ³mo estÃ¡s ahora',
            'que tienes disponible',
            'quÃ© tienes disponible',
            'que puedes usar ahora',
            'quÃ© puedes usar ahora',
            'como te sientes',
            'como te va',
            'que problemas ves',
            'que problemas detectas',
            'que desajustes ves',
            'que desajustes detectas',
            'tu propio funcionamiento',
            'tu funcionamiento',
            'como funciones',
            'como funcionas',
            'como estas funcionando',
            'diagnosticate',
            'autodiagnostico',
            'autodiagnosticarte',
            'examinate',
            'autoexaminate',
        )
        if any(phrase in text for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', text))
        asks_system_state = any(token in word_tokens for token in (
            'entorno', 'arquitectura', 'herramienta', 'herramientas',
            'ias', 'ia', 'estado', 'conexiones',
            'funcionamiento', 'desajustes', 'problemas', 'degradacion',
            'diagnostico', 'autoexaminacion', 'salud',
        ))
        asks_directly = any(token in text for token in (
            'conoces', 'sabes', 'tienes', 'disponibles',
            'te conectas', 'te puedes conectar', 'puedes usar',
            'consciente', 'que tan bien', 'como estas', 'como estÃ¡s',
            'como te sientes', 'que problemas', 'que desajustes',
            'detectas', 'funcionando', 'tu propio',
        ))
        return asks_system_state and asks_directly

    def _is_evolution_status_prompt(self, text: str) -> bool:
        if not text:
            return False
        direct_phrases = (
            'que herramienta va ganando',
            'qué herramienta va ganando',
            'que herramientas van ganando',
            'qué herramientas van ganando',
            'que esta en validacion',
            'qué está en validacion',
            'que esta en validación',
            'qué está en validación',
            'que fue descartado',
            'qué fue descartado',
            'que herramientas fueron descartadas',
            'qué herramientas fueron descartadas',
            'que se descubrio nuevo',
            'qué se descubrio nuevo',
            'que se descubrió nuevo',
            'qué se descubrió nuevo',
            'que herramienta nueva vale la pena probar',
            'qué herramienta nueva vale la pena probar',
            'que herramienta vale la pena probar',
            'qué herramienta vale la pena probar',
        )
        if any(phrase in text for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', text))
        asks_evolution = any(token in word_tokens for token in ('ganando', 'validacion', 'validacion', 'descartado', 'descartadas', 'descubrio', 'descubrio', 'descubierta', 'nuevo', 'nueva'))
        asks_tools = any(token in word_tokens for token in ('herramienta', 'herramientas', 'ruta', 'rutas', 'prueba', 'probar'))
        asks_state = any(token in word_tokens for token in ('esta', 'estan', 'va', 'van', 'fue', 'fueron', 'vale'))
        return asks_evolution and (asks_tools or asks_state)

    def _detect_site(self, text: str, goal_parameters: dict[str, Any]) -> str | None:
        site_hint, _ = self._detect_site_with_history(text, goal_parameters, '')
        return site_hint

    def _detect_site_with_history(
        self,
        text: str,
        goal_parameters: dict[str, Any],
        conversation_text: str,
    ) -> tuple[str | None, bool]:
        probes: list[str] = [text]
        probes.extend(str(value).lower() for value in goal_parameters.values() if isinstance(value, (str, int, float)))
        merged = ' '.join(probes)
        for site_id, aliases in self.SITE_ALIASES.items():
            if any(alias in merged for alias in aliases):
                return site_id, False
        if conversation_text:
            for site_id, aliases in self.SITE_ALIASES.items():
                if any(alias in conversation_text for alias in aliases):
                    return site_id, True
        return None, False

    def _contains_any(self, text: str, patterns: list[str]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _normalize(self, text: str) -> str:
        normalized = text.strip().lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    def _requested_external_assistant(self, text: str) -> str:
        normalized = self._normalize(text)
        if not normalized:
            return ''
        if self._contains_any(normalized, ['que sabes hacer', 'qu? sabes hacer', 'como funcionas', 'c?mo funcionas', 'sabes consultar automaticamente']):
            return ''
        consult_verbs = (
            'consulta',
            'consulta externa',
            'consultar',
            'consultalo',
            'cons?ltalo',
            'usa ',
            'utiliza ',
            'apoyate en',
            'ap?yate en',
            'pregunta a',
            'preguntale',
            'preg?ntale',
            'pidele a',
            'p?dele a',
            'dile a',
            'valida con',
            'revisa con',
            'escala a',
            'escalalo a',
            'escalalo con',
            'razona con',
            'piensa con',
        )
        # M1-fix: reconocer frases compuestas "abre X y preguntale/pidele"
        # donde el verbo de navegacion precede al verbo de consulta.
        compound_consult = False
        if self._contains_any(normalized, ['abre ', 'abrir ']):
            for assistant in ('chatgpt', 'claude', 'codex', 'devin', 'windsurf', 'ollama'):
                if assistant in normalized and self._contains_any(normalized, ['pregunta', 'pidele', 'dile', 'consultale', 'cons?ltale']):
                    compound_consult = True
                    break
        if not compound_consult and not any(verb in normalized for verb in consult_verbs):
            return ''
        if 'chatgpt' in normalized:
            return 'chatgpt'
        if 'claude' in normalized:
            return 'claude'
        if 'codex' in normalized:
            return 'codex'
        if 'ollama' in normalized:
            return 'ollama'
        if 'devin' in normalized:
            return 'devin'
        if 'windsurf' in normalized:
            return 'windsurf'
        return ''

