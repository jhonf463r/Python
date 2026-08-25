"""Service that infers an explicit assistant preference from a user message.

This logic used to live inside `ControlCenterViewModel` as the private
`_explicit_assistant_preference` helper. Extracting it into a dedicated service
keeps the ViewModel focused on observation (per the architectural contract in
`AGENTS.md`), avoids duplicating the same parsing in other entry points
(orchestrator, chat bridge, CLI tools), and lets us exercise the logic in
pure-Python tests without a Qt environment.

The resolver is deliberately conservative: it only returns an assistant family
when the user expresses an explicit request to consult that assistant, and it
returns `''` for meta questions (e.g. "sabes consultar a codex?") so the
orchestrator does not escalate to an external tool by mistake.

P0.23: Added typo-aware matching for "chat gpt", "chat-gpt", "chatgo" and
imperative action patterns ("hazle a chatgpt", "preguntale a chatgpt",
"pidele a chatgpt", "a chatgpt hazla") so that real external consultation
intents are not dropped to local chat.
"""
from __future__ import annotations

import re


class AssistantPreferenceResolver:
    """Pure helper that maps a free-text user message to an assistant family.

    Returns one of `{'codex', 'chatgpt', 'claude', 'ollama'}` when the message
    expresses an explicit preference for that assistant, or `''` otherwise.
    """

    _ASSISTANT_FAMILIES: tuple[str, ...] = ('chatgpt', 'claude', 'codex', 'ollama', 'devin', 'windsurf')

    # P0.23: variant spellings / typos that should map to a canonical family.
    _ASSISTANT_ALIASES: dict[str, str] = {
        'chat gpt': 'chatgpt',
        'chat-gpt': 'chatgpt',
    }

    # P0.23: typos that only count when an action verb is present nearby.
    _ASSISTANT_TYPO_ALIASES: dict[str, str] = {
        'chatgo': 'chatgpt',
    }

    # P0.23: action verbs that confirm external consultation intent when
    # combined with a target assistant name or typo.
    _EXTERNAL_ACTION_VERBS: tuple[str, ...] = (
        'haz', 'hacer', 'hazle', 'hazla',
        'consulta', 'consultar',
        'pregunta', 'preguntale', 'pregúntale',
        'pidele', 'pídele',
        'envia', 'envía', 'manda',
        'prueba con',
    )

    _META_PROMPT_PREFIXES: tuple[str, ...] = ('sabes ', 'puedes ', 'puedo ')

    _CONSULT_TOKENS: tuple[str, ...] = (
        'consulta',
        'consulta externa',
        'consulta nueva',
        'consultar',
        'usa ',
        'utiliza ',
        'revisa con',
        'valida con',
        'pregunta a',
        'preguntale a',
        'pregúntale a',
        'pidele a',
        'pídele a',
        'hazle a',
        'apoyate en',
        'ap?yate en',
        'razona con',
        'piensa con',
        'escala a',
        'escalalo a',
        'escalalo con',
    )

    _TASK_ACTION_TOKENS: tuple[str, ...] = (
        'revisa ', 'revisa', 'revisar',
        'analiza', 'analizar',
        'diagnostica', 'diagnosticar',
        'arregla', 'corrige',
        'abre ', 'inicia ',
    )

    _META_INTROSPECTION_TOKENS: tuple[str, ...] = (
        'sabes', 'puedes', 'puedo',
        'internamente',
        'automatic', 'automatica', 'autom?tico',
        'respondieron',
    )

    def _normalize_assistant_aliases(self, command: str) -> str:
        """Replace known variant spellings with canonical family names."""
        for alias, canonical in self._ASSISTANT_ALIASES.items():
            command = command.replace(alias, canonical)
        return command

    def _resolve_typo_with_action(self, command: str) -> str:
        """Return canonical family if a typo alias + action verb are present."""
        for typo, canonical in self._ASSISTANT_TYPO_ALIASES.items():
            if typo in command and any(v in command for v in self._EXTERNAL_ACTION_VERBS):
                return canonical
        return ''

    def resolve(self, message: str) -> str:
        command = ' '.join(str(message or '').lower().strip().split())
        if not command:
            return ''
        # P0.23: normalize alias spellings before any matching.
        command = self._normalize_assistant_aliases(command)
        if any(command.startswith(prefix) for prefix in self._META_PROMPT_PREFIXES) and any(
            token in command for token in self._ASSISTANT_FAMILIES
        ):
            return ''
        has_consult_intent = any(token in command for token in self._CONSULT_TOKENS)
        if has_consult_intent:
            for assistant in self._ASSISTANT_FAMILIES:
                if assistant in command:
                    return assistant
        # P0.23: imperative action + target patterns like "a chatgpt hazla",
        # "hazle a chatgpt", "preguntale a chatgpt".
        has_action_verb = any(v in command for v in self._EXTERNAL_ACTION_VERBS)
        if has_action_verb:
            for assistant in self._ASSISTANT_FAMILIES:
                if assistant in command:
                    return assistant
        # P0.23: typo-aware resolution (e.g. "chatgo" + action verb).
        typo_result = self._resolve_typo_with_action(command)
        if typo_result:
            return typo_result
        for assistant in self._ASSISTANT_FAMILIES:
            if assistant not in command:
                continue
            task_like_external_request = (
                any(token in command for token in self._TASK_ACTION_TOKENS)
                and any(
                    marker in command
                    for marker in (
                        f'con {assistant}',
                        f'a {assistant}',
                        f'usa {assistant}',
                        f'utiliza {assistant}',
                        f'usando {assistant}',
                        f'por {assistant}',
                        f'via {assistant}',
                    )
                )
            )
            if task_like_external_request:
                return assistant
        if (
            any(token in command for token in self._ASSISTANT_FAMILIES)
            and any(token in command for token in self._META_INTROSPECTION_TOKENS)
        ):
            return ''
        return ''
