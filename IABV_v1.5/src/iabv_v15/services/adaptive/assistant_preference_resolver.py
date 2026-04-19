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
"""
from __future__ import annotations


class AssistantPreferenceResolver:
    """Pure helper that maps a free-text user message to an assistant family.

    Returns one of `{'codex', 'chatgpt', 'claude', 'ollama'}` when the message
    expresses an explicit preference for that assistant, or `''` otherwise.
    """

    _ASSISTANT_FAMILIES: tuple[str, ...] = ('chatgpt', 'claude', 'codex', 'ollama')

    _META_PROMPT_PREFIXES: tuple[str, ...] = ('sabes ', 'puedes ', 'puedo ')

    _CONSULT_TOKENS: tuple[str, ...] = (
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

    def resolve(self, message: str) -> str:
        command = ' '.join(str(message or '').lower().strip().split())
        if not command:
            return ''
        if any(command.startswith(prefix) for prefix in self._META_PROMPT_PREFIXES) and any(
            token in command for token in self._ASSISTANT_FAMILIES
        ):
            return ''
        has_consult_intent = any(token in command for token in self._CONSULT_TOKENS)
        if has_consult_intent:
            for assistant in self._ASSISTANT_FAMILIES:
                if assistant in command:
                    return assistant
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
