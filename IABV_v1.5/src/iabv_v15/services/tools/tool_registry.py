from __future__ import annotations

from datetime import datetime, timezone

from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_adapters import ToolAdapter


class ToolRegistry:
    _PRESERVE_METADATA_KEYS = {
        'executable_path',
        'workspace_root',
        'updated_at_utc',
    }
    _AVAILABILITY_CACHE_SECONDS = 45.0

    def __init__(self, repository: ToolRecordRepository, adapters: dict[str, ToolAdapter]):
        self.repository = repository
        self.adapters = adapters
        self._seed_defaults()

    def list_cards(self) -> list[ToolCard]:
        return self.repository.list_cards()

    def get_card(self, tool_id: str) -> ToolCard | None:
        return self.repository.get_card(tool_id)

    def pick_card_for_task(self, task: ToolTask) -> ToolCard | None:
        if task.tool_id:
            card = self.get_card(task.tool_id)
            if card is not None:
                return self.refresh_card(card)
        objective = (task.objective + ' ' + task.title).lower()
        for card in self.list_cards():
            score = 0
            joined = ' '.join([card.title, card.description, card.adapter_key, ' '.join(card.capabilities)]).lower()
            for token in objective.split():
                if token and token in joined:
                    score += 1
            if score > 0:
                return self.refresh_card(card)
        cards = self.list_cards()
        return self.refresh_card(cards[0]) if cards else None

    def refresh_card(self, card: ToolCard, *, force: bool = False, max_age_seconds: float | None = None) -> ToolCard:
        if not force and self._card_is_fresh(card, max_age_seconds=max_age_seconds):
            return card
        adapter = self.adapters.get(card.adapter_key)
        available = bool(adapter and adapter.is_available(card))
        if card.available == available and str(card.metadata.get('updated_at_utc') or '').strip():
            return card
        updated = card.model_copy(
            update={
                'available': available,
                'metadata': {
                    **card.metadata,
                    'updated_at_utc': datetime.now(timezone.utc).isoformat(),
                },
            }
        )
        self.repository.save_card(updated)
        return updated

    def _card_is_fresh(self, card: ToolCard, *, max_age_seconds: float | None) -> bool:
        ttl = self._AVAILABILITY_CACHE_SECONDS if max_age_seconds is None else max(float(max_age_seconds), 0.0)
        if ttl <= 0.0:
            return False
        updated_at = str(card.metadata.get('updated_at_utc') or '').strip()
        if not updated_at:
            return False
        try:
            refreshed_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except ValueError:
            return False
        age_seconds = (datetime.now(timezone.utc) - refreshed_at).total_seconds()
        return 0.0 <= age_seconds <= ttl

    def _seed_defaults(self) -> None:
        defaults = [
            ToolCard(
                tool_id='playwright_browser',
                title='Playwright browser',
                tool_type=ToolType.BROWSER,
                description='Automatizacion web local usando el stack Playwright ya integrado en captura.',
                adapter_key='playwright',
                supports_sandbox=True,
                supports_write=True,
                supports_rollback=True,
                requires_human_approval=True,
                capabilities=['open_url', 'click', 'type_text', 'extract_text', 'screenshot'],
            ),
            ToolCard(
                tool_id='ollama_llm',
                title='Ollama local',
                tool_type=ToolType.LLM_LOCAL,
                description='Proveedor local principal para inferencia, chat adaptativo y razonamiento sin APIs de pago.',
                adapter_key='ollama',
                supports_sandbox=True,
                capabilities=[
                    'llm_query',
                    'summarize',
                    'classify',
                    'knowledge.query.local',
                    'assistant.local.chat',
                    'local_chat_context',
                ],
                metadata={
                    'assistant_kind': 'ollama',
                    'launch_mode': 'local_provider',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'supports_local_chat': True,
                },
            ),
            ToolCard(
                tool_id='shell_command',
                title='Shell local seguro',
                tool_type=ToolType.SHELL,
                description='Wrapper controlado para comandos locales no destructivos y observables.',
                adapter_key='shell',
                supports_sandbox=True,
                supports_rollback=True,
                capabilities=['run_command', 'inspect_environment'],
            ),
            ToolCard(
                tool_id='desktop_human_runner',
                title='Desktop human runner',
                tool_type=ToolType.CUSTOM,
                description='Ejecucion desktop real o simulada con mouse, teclado, ventanas y evidencia visual antes/despues.',
                adapter_key='desktop_human',
                supports_sandbox=True,
                supports_write=True,
                requires_human_approval=True,
                capabilities=['launch_app', 'focus_window', 'click', 'type_text', 'scroll', 'screenshot', 'wait_for_window', 'wait_for_change'],
                metadata={
                    'assistant_kind': 'iabv_runtime',
                    'launch_mode': 'desktop_real',
                    'response_capture_mode': 'local_evidence',
                    'requires_manual_pasteback': False,
                },
            ),
            ToolCard(
                tool_id='aider_coder',
                title='Aider coder',
                tool_type=ToolType.CODE_EDITOR,
                description='Edicion de codigo trazable sobre el repo local, sin auto-commit.',
                adapter_key='aider',
                supports_sandbox=True,
                supports_write=True,
                requires_human_approval=True,
                capabilities=['edit_code', 'plan_patch'],
            ),
            ToolCard(
                tool_id='mcp_client',
                title='MCP client',
                tool_type=ToolType.MCP_CLIENT,
                description='Cliente MCP extensible para conectores o servidores futuros.',
                adapter_key='mcp',
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['mcp_call'],
            ),
            ToolCard(
                tool_id='codex_installed',
                title='Codex instalado',
                tool_type=ToolType.CUSTOM,
                description='Consulta tecnica guiada usando la app o CLI instalada de Codex antes de caer a web.',
                adapter_key='external_assistant',
                local_first=False,
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['launch_app', 'llm_query', 'consult_external', 'code_assistance'],
                metadata={
                    'assistant_kind': 'codex',
                    'launch_mode': 'desktop_app',
                    'command_name': 'codex',
                    'command_aliases': ['codex.exe'],
                    'windows_default_paths': [
                        r'{localappdata}\Microsoft\WindowsApps\codex.exe',
                        r'{programfiles}\WindowsApps\OpenAI.Codex_*\app\resources\codex.exe',
                        r'{programfiles}\WindowsApps\OpenAI.Codex_*\app\resources\codex.EXE',
                    ],
                    'prompt_template_id': 'codex_consult_v1',
                    'response_capture_mode': 'clipboard_capture',
                    'background_capture_mode': 'codex_rollout',
                    'session_state_path': r'{userprofile}\.codex\state_5.sqlite',
                    'session_rollouts_root': r'{userprofile}\.codex\sessions',
                    'requires_manual_pasteback': False,
                    'window_title_hints': ['Codex'],
                    'submit_prompt_after_paste': True,
                    'response_wait_seconds': 10.0,
                    'dry_run_launch': False,
                },
            ),
            ToolCard(
                tool_id='chatgpt_installed',
                title='ChatGPT instalado',
                tool_type=ToolType.CUSTOM,
                description='Consulta explicativa guiada usando la app instalada de ChatGPT cuando esta disponible.',
                adapter_key='external_assistant',
                local_first=False,
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['launch_app', 'llm_query', 'consult_external', 'explain_issue'],
                metadata={
                    'assistant_kind': 'chatgpt',
                    'launch_mode': 'desktop_app',
                    'command_name': 'chatgpt',
                    'command_aliases': ['ChatGPT', 'chatgpt.exe', 'OpenAI'],
                    'windows_default_paths': [
                        r'{localappdata}\Programs\ChatGPT\ChatGPT.exe',
                        r'{localappdata}\OpenAI\ChatGPT.exe',
                        r'{localappdata}\OpenAI\*\ChatGPT.exe',
                        r'{localappdata}\OpenAI\**\ChatGPT.exe',
                        r'{localappdata}\Microsoft\WindowsApps\ChatGPT.exe',
                        r'{programfiles}\ChatGPT\ChatGPT.exe',
                        r'{programfilesx86}\ChatGPT\ChatGPT.exe',
                    ],
                    'prompt_template_id': 'chatgpt_consult_v1',
                    'response_capture_mode': 'clipboard_capture',
                    'requires_manual_pasteback': False,
                    'window_title_hints': ['ChatGPT'],
                    'submit_prompt_after_paste': True,
                    'response_wait_seconds': 10.0,
                    'dry_run_launch': False,
                },
            ),
            ToolCard(
                tool_id='chatgpt_web_assisted',
                title='ChatGPT web asistido',
                tool_type=ToolType.LLM_WEB_UI,
                description='Consulta web en sesion aislada del programa hacia ChatGPT cuando no hay app instalada disponible.',
                adapter_key='external_assistant',
                local_first=False,
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['launch_app', 'llm_query', 'consult_external', 'web_assisted'],
                metadata={
                    'assistant_kind': 'chatgpt',
                    'launch_mode': 'web_assisted',
                    'web_url': 'https://chatgpt.com/',
                    'prompt_template_id': 'chatgpt_web_consult_v1',
                    'response_capture_mode': 'dom_capture',
                    'background_capture_mode': 'browser_dom',
                    'requires_manual_pasteback': False,
                    'isolated_session_required': True,
                    'session_scope': 'program_chat',
                    'session_label': 'ChatGPT especial de IABV',
                    'background_headless': True,
                    'close_after_capture': True,
                    'input_selectors': [
                        'textarea',
                        'div[contenteditable="true"]',
                    ],
                    'response_selectors': [
                        '[data-message-author-role="assistant"]',
                        'main article',
                    ],
                    'submit_selectors': [
                        'button[data-testid="send-button"]',
                    ],
                    'response_wait_seconds': 45.0,
                    'security_verification_wait_seconds': 12.0,
                    'max_security_retries': 3,
                    'dry_run_launch': False,
                },
            ),
            ToolCard(
                tool_id='claude_installed',
                title='Claude instalado',
                tool_type=ToolType.CUSTOM,
                description='Consulta explicativa guiada usando la app instalada de Claude cuando esta disponible.',
                adapter_key='external_assistant',
                local_first=False,
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['launch_app', 'llm_query', 'consult_external', 'explain_issue'],
                metadata={
                    'assistant_kind': 'claude',
                    'launch_mode': 'desktop_app',
                    'command_name': 'claude',
                    'command_aliases': ['Claude', 'claude.exe', 'Anthropic'],
                    'windows_default_paths': [
                        r'{localappdata}\Programs\Claude\Claude.exe',
                        r'{localappdata}\Anthropic\Claude.exe',
                        r'{localappdata}\Anthropic\*\Claude.exe',
                        r'{localappdata}\Microsoft\WindowsApps\Claude.exe',
                        r'{programfiles}\Claude\Claude.exe',
                        r'{programfilesx86}\Claude\Claude.exe',
                    ],
                    'prompt_template_id': 'claude_consult_v1',
                    'response_capture_mode': 'clipboard_capture',
                    'requires_manual_pasteback': False,
                    'window_title_hints': ['Claude'],
                    'submit_prompt_after_paste': True,
                    'response_wait_seconds': 10.0,
                    'dry_run_launch': False,
                },
            ),
            ToolCard(
                tool_id='claude_web_assisted',
                title='Claude web asistido',
                tool_type=ToolType.LLM_WEB_UI,
                description='Consulta web en sesion aislada del programa hacia Claude cuando no hay app instalada disponible.',
                adapter_key='external_assistant',
                local_first=False,
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['launch_app', 'llm_query', 'consult_external', 'web_assisted'],
                metadata={
                    'assistant_kind': 'claude',
                    'launch_mode': 'web_assisted',
                    'web_url': 'https://claude.ai/',
                    'prompt_template_id': 'claude_web_consult_v1',
                    'response_capture_mode': 'dom_capture',
                    'background_capture_mode': 'browser_dom',
                    'requires_manual_pasteback': False,
                    'isolated_session_required': True,
                    'session_scope': 'program_chat',
                    'session_label': 'Claude especial de IABV',
                    'background_headless': True,
                    'close_after_capture': True,
                    'input_selectors': [
                        'div[contenteditable="true"]',
                        'textarea',
                    ],
                    'response_selectors': [
                        'main article',
                        '[data-testid="message-content"]',
                    ],
                    'submit_selectors': [],
                    'response_wait_seconds': 18.0,
                    'dry_run_launch': False,
                },
            ),
        ]
        existing = {card.tool_id: card for card in self.repository.list_cards()}
        for card in defaults:
            current = existing.get(card.tool_id)
            if current is not None:
                merged_metadata = {**(current.metadata or {}), **card.metadata}
                for key in self._PRESERVE_METADATA_KEYS:
                    if key in (current.metadata or {}):
                        merged_metadata[key] = current.metadata[key]
                merged = current.model_copy(
                    update={
                        'tool_type': card.tool_type,
                        'title': card.title,
                        'description': card.description,
                        'adapter_key': card.adapter_key,
                        'local_first': card.local_first,
                        'supports_sandbox': card.supports_sandbox,
                        'supports_write': card.supports_write,
                        'supports_rollback': card.supports_rollback,
                        'requires_human_approval': card.requires_human_approval,
                        'capabilities': card.capabilities,
                        'metadata': merged_metadata,
                    }
                )
                if current.model_dump(mode='json', exclude={'available'}) != merged.model_dump(mode='json', exclude={'available'}):
                    self.repository.save_card(merged)
                self.refresh_card(merged)
            else:
                self.refresh_card(card)


