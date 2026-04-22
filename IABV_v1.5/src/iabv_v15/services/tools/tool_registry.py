from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_adapters import ToolAdapter


class ToolRegistry:
    _PRESERVE_METADATA_KEYS = {
        'executable_path',
        'workspace_root',
        'updated_at_utc',
        'server_url',
    }
    # In-process availability TTL. The cache is invalidated automatically
    # whenever the adapter registration status changes or when the
    # availability-relevant metadata hash changes (see
    # `_availability_signature`), so external mutations via the repository
    # are reflected on the next refresh even before the TTL expires.
    _AVAILABILITY_CACHE_SECONDS = 45.0

    def __init__(self, repository: ToolRecordRepository, adapters: dict[str, ToolAdapter]):
        self.repository = repository
        self.adapters = adapters
        # In-process availability cache keyed by tool_id. The third tuple
        # element is a hash of the metadata values that affect availability,
        # so an external mutation via the repository (e.g. adding
        # `executable_path` or `web_url`) invalidates the cache on the next
        # refresh even if `updated_at_utc` is still the same.
        self._availability_cache: dict[str, tuple[bool, datetime, str]] = {}
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
        metadata_signature = self._availability_signature(card)
        if not force:
            cached = self._cached_availability(
                card.tool_id,
                metadata_signature=metadata_signature,
                max_age_seconds=max_age_seconds,
            )
            if cached is not None:
                if card.available == cached:
                    return card
                return card.model_copy(update={'available': cached})
        adapter = self.adapters.get(card.adapter_key)
        available = bool(adapter and adapter.is_available(card))
        now = datetime.now(timezone.utc)
        self._availability_cache[card.tool_id] = (available, now, metadata_signature)
        if card.available == available and str(card.metadata.get('updated_at_utc') or '').strip():
            return card
        updated = card.model_copy(
            update={
                'available': available,
                'metadata': {
                    **card.metadata,
                    'updated_at_utc': now.isoformat(),
                },
            }
        )
        self.repository.save_card(updated)
        return updated

    def _availability_signature(self, card: ToolCard) -> str:
        relevant = {
            'adapter_key': card.adapter_key,
            # Capture adapter registration status AND the identity of the
            # adapter instance / its backing provider. This way, hot-swapping
            # the adapter or replacing its provider (common in tests that
            # toggle a fake local provider) invalidates the availability
            # cache even when the card metadata is structurally unchanged.
            'adapter_fingerprint': self._adapter_fingerprint(card.adapter_key),
            'metadata': {
                key: card.metadata.get(key)
                for key in sorted(card.metadata.keys())
                if key != 'updated_at_utc'
            },
        }
        payload = json.dumps(relevant, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _adapter_fingerprint(self, adapter_key: str) -> str:
        adapter = self.adapters.get(adapter_key)
        if adapter is None:
            return 'missing'
        parts = [str(id(adapter))]
        provider = getattr(adapter, 'provider', None)
        if provider is not None:
            parts.append(str(id(provider)))
        return ':'.join(parts)

    def _cached_availability(
        self,
        tool_id: str,
        *,
        metadata_signature: str,
        max_age_seconds: float | None,
    ) -> bool | None:
        ttl = self._AVAILABILITY_CACHE_SECONDS if max_age_seconds is None else max(float(max_age_seconds), 0.0)
        if ttl <= 0.0:
            return None
        cached = self._availability_cache.get(tool_id)
        if cached is None:
            return None
        value, refreshed_at, signature = cached
        if signature != metadata_signature:
            return None
        age_seconds = (datetime.now(timezone.utc) - refreshed_at).total_seconds()
        if age_seconds < 0.0 or age_seconds > ttl:
            return None
        return value

    def invalidate_availability_cache(self, tool_id: str | None = None) -> None:
        if tool_id is None:
            self._availability_cache.clear()
            return
        self._availability_cache.pop(tool_id, None)

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
                description='Proveedor local principal para inferencia y razonamiento sin APIs de pago.',
                adapter_key='ollama',
                supports_sandbox=True,
                capabilities=['llm_query', 'summarize', 'classify'],
                metadata={
                    'assistant_kind': 'ollama',
                    'launch_mode': 'local_provider',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
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
                description='Cliente MCP para auto-inspeccion y conectores externos.',
                adapter_key='mcp',
                supports_sandbox=True,
                requires_human_approval=True,
                capabilities=['mcp_call'],
                metadata={
                    'server_url': 'http://127.0.0.1:8000',
                },
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
                        r'{localappdata}\Programs\claude-desktop\Claude.exe',
                        r'{localappdata}\Anthropic\Claude.exe',
                        r'{localappdata}\Anthropic\*\Claude.exe',
                        r'{localappdata}\Microsoft\WindowsApps\Claude.exe',
                        r'{appdata}\Claude\Claude.exe',
                        r'{appdata}\Anthropic\Claude.exe',
                        r'{programfiles}\Claude\Claude.exe',
                        r'{programfilesx86}\Claude\Claude.exe',
                        r'{userprofile}\scoop\apps\claude\current\Claude.exe',
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
                tool_id='site_explorer_v1',
                title='Site explorer v1',
                tool_type=ToolType.BROWSER,
                description='Explorador acotado de sitios: crawl BFS mismo dominio y manual persistido por hostname.',
                adapter_key='site_explorer',
                supports_sandbox=True,
                supports_write=True,
                requires_human_approval=True,
                capabilities=['open_url', 'explore_site', 'catalog_pages', 'persist_site_manual'],
                metadata={
                    'manual_root': 'data/evolution/site_manuals/',
                    'default_max_pages': 6,
                    'same_domain_only': True,
                    'mutates_remote_state': False,
                    'llm_optional_summary': True,
                },
            ),
            ToolCard(
                tool_id='devin_api',
                title='Devin (Cognition AI)',
                tool_type=ToolType.MCP_CLIENT,
                description='Sesion autonoma via API REST de Devin para tareas de codigo, shell y navegacion.',
                adapter_key='devin_api',
                available=True,
                requires_human_approval=False,
                capabilities=['code_assistance', 'shell_execution', 'web_browsing', 'structured_reasoning'],
                metadata={
                    'assistant_kind': 'devin',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'session_scope': 'api_session',
                    'background_capture_mode': 'devin_api',
                    'launch_mode': 'api',
                },
            ),
            ToolCard(
                tool_id='github_api',
                title='GitHub (REST + GraphQL)',
                tool_type=ToolType.MCP_CLIENT,
                description='Operaciones nativas sobre GitHub (PRs, issues, auto-merge) via API REST y GraphQL sin navegador.',
                adapter_key='github_api',
                available=True,
                supports_sandbox=True,
                supports_write=True,
                requires_human_approval=True,
                capabilities=[
                    'github_read_pr',
                    'github_create_pr',
                    'github_merge_pr',
                    'github_enable_auto_merge',
                    'github_comment_issue',
                    'github_list_issues',
                    'github_list_prs',
                ],
                metadata={
                    'tool_family': 'github',
                    'launch_mode': 'api',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'session_scope': 'api_call',
                    'mutates_remote_state': True,
                    'supported_actions': [
                        'read_pr',
                        'create_pr',
                        'merge_pr',
                        'enable_auto_merge',
                        'comment_issue',
                        'list_issues',
                        'list_prs',
                    ],
                },
            ),
            ToolCard(
                tool_id='gh_cli',
                title='GitHub CLI',
                tool_type=ToolType.SHELL,
                description='CLI oficial de GitHub para operar auth, repos, PRs e issues desde linea de comandos. Observacion read-only por default; escritura real queda detras de ToolApprovalPolicy.',
                adapter_key='local_cli',
                supports_sandbox=False,
                supports_write=False,
                requires_human_approval=True,
                capabilities=['check_version', 'check_auth_status', 'inspect_repo', 'list_prs', 'list_issues'],
                metadata={
                    'tool_family': 'github',
                    'launch_mode': 'local_cli',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'command_name': 'gh',
                    'command_aliases': ['gh.exe'],
                    'windows_default_paths': [
                        r'{userprofile}\.iabv\tools\gh\bin\gh.exe',
                        r'{userprofile}\.iabv\tools\gh\gh_*_windows_amd64\bin\gh.exe',
                        r'{programfiles}\GitHub CLI\gh.exe',
                        r'{programfiles}\GitHub CLI\bin\gh.exe',
                    ],
                    'version_command': '--version',
                    'allowed_verbs': [
                        '--version', 'version', 'auth', 'api', 'repo', 'pr',
                        'issue', 'release', 'run', 'status', 'search', 'browse',
                    ],
                    'notes': 'Escritura (gh repo create, gh pr merge, gh release create) requiere approval via ToolApprovalPolicy.',
                },
            ),
            ToolCard(
                tool_id='cloudflared_cli',
                title='Cloudflared CLI',
                tool_type=ToolType.SHELL,
                description='CLI de Cloudflare Tunnel para inspeccion (version, tunnels, config). El arranque real del tunnel queda delegado a run_mcp_bridge.ps1.',
                adapter_key='local_cli',
                supports_sandbox=False,
                supports_write=False,
                requires_human_approval=True,
                capabilities=['check_version', 'list_tunnels', 'inspect_tunnel', 'access_info'],
                metadata={
                    'tool_family': 'cloudflared',
                    'launch_mode': 'local_cli',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'command_name': 'cloudflared',
                    'command_aliases': ['cloudflared.exe'],
                    'windows_default_paths': [
                        r'{userprofile}\.iabv\tools\cloudflared\cloudflared.exe',
                        r'{programfiles}\cloudflared\cloudflared.exe',
                        r'{programfilesx86}\cloudflared\cloudflared.exe',
                    ],
                    'version_command': '--version',
                    'allowed_verbs': [
                        '--version', 'version', 'tunnel', 'access', 'help',
                    ],
                    'notes': 'Verbos de inspeccion (tunnel list, tunnel info) quedan permitidos; arranque real del tunnel sigue corriendo via run_mcp_bridge.ps1. `cloudflared update` queda fuera del allowlist por read-only: pasa por ToolApprovalPolicy si hace falta.',
                },
            ),
            ToolCard(
                tool_id='git_cli',
                title='Git CLI',
                tool_type=ToolType.SHELL,
                description='CLI de git para inspeccion local (status, log, diff, remote, rev-parse). Operaciones destructivas (reset --hard, push --force) quedan bloqueadas por BLOCKED_TOKENS.',
                adapter_key='local_cli',
                supports_sandbox=False,
                supports_write=False,
                requires_human_approval=True,
                capabilities=['check_version', 'status', 'log', 'diff', 'remote', 'branch_list', 'rev_parse'],
                metadata={
                    'tool_family': 'git',
                    'launch_mode': 'local_cli',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'command_name': 'git',
                    'command_aliases': ['git.exe'],
                    'windows_default_paths': [
                        r'{programfiles}\Git\cmd\git.exe',
                        r'{programfiles}\Git\bin\git.exe',
                        r'{programfilesx86}\Git\cmd\git.exe',
                    ],
                    'version_command': '--version',
                    'allowed_verbs': [
                        '--version', 'version', 'status', 'log', 'diff', 'remote',
                        'branch', 'rev-parse', 'show', 'config', 'describe',
                        'ls-files', 'ls-remote', 'shortlog', 'tag',
                    ],
                    'notes': 'Commits, pushes y rebase quedan fuera del allowlist; pasan por ToolApprovalPolicy o por el flow manual del usuario.',
                },
            ),
            ToolCard(
                tool_id='winget_cli',
                title='Winget',
                tool_type=ToolType.SHELL,
                description='Gestor de paquetes Windows read-only: list, search, show, version. Install/uninstall/upgrade requieren approval explicita.',
                adapter_key='local_cli',
                supports_sandbox=False,
                supports_write=False,
                requires_human_approval=True,
                capabilities=['check_version', 'list_packages', 'search_package', 'show_package', 'source_list'],
                metadata={
                    'tool_family': 'winget',
                    'launch_mode': 'local_cli',
                    'response_capture_mode': 'tool_result',
                    'requires_manual_pasteback': False,
                    'command_name': 'winget',
                    'command_aliases': ['winget.exe'],
                    'windows_default_paths': [
                        r'{localappdata}\Microsoft\WindowsApps\winget.exe',
                    ],
                    'version_command': '--version',
                    'allowed_verbs': [
                        '--version', 'version', 'list', 'search', 'show',
                        'source', 'hash', 'features', 'help',
                    ],
                    'notes': 'winget install, upgrade y uninstall mutan estado del sistema; requieren aprobacion humana explicita antes del subprocess.',
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


