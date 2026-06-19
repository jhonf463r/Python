# FASE 2: MEMORIA DE COMPORTAMIENTO - MODELO POR HERRAMIENTA

## RESUMEN EJECUTIVO

- **Total ToolCards registradas**: 18
- **Total InteractionPatterns**: 3
- **Total ToolTasks recientes**: 20
- **Total ToolResults recientes**: 20 (19 éxitos, 1 fallo = 95% éxito)

## HERRAMIENTAS REGISTRADAS

### Asistentes Externos (Web/Desktop)

#### 1. chatgpt_web_assisted
- **Tipo**: ToolType.CUSTOM
- **Adapter**: external_assistant
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0 (en ToolCard)
- **Capabilities**: launch_app, llm_query, consult_external, web_assisted
- **Metadata**:
  - assistant_kind: chatgpt
  - web_url: https://chatgpt.com/
- **Patrones de interacción**: 1
  - Pattern: be61f185-4864-4d59-997e-126c952cf4ff
  - Título: Consultar Ollama local
  - Canal: UI
  - Reusable: True
  - Éxitos: 34, Fallos: 10 (77% éxito)
  - Operaciones: 2 steps
- **Estado actual**: ACTIVO pero con historial de fallos (browser_security_verification)

#### 2. chatgpt_installed
- **Tipo**: ToolType.CUSTOM
- **Adapter**: external_assistant
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: launch_app, llm_query, consult_external, web_assisted
- **Metadata**:
  - assistant_kind: chatgpt
- **Estado actual**: DISPONIBLE pero nunca usado (alternativa potencial)

#### 3. claude_installed
- **Tipo**: ToolType.CUSTOM
- **Adapter**: external_assistant
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: launch_app, llm_query, consult_external, web_assisted
- **Metadata**:
  - assistant_kind: claude
  - web_url: https://claude.ai/
- **Estado actual**: DISPONIBLE pero nunca usado

#### 4. codex_installed
- **Tipo**: ToolType.CUSTOM
- **Adapter**: external_assistant
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: launch_app, llm_query, consult_external, code_assistance
- **Metadata**:
  - assistant_kind: codex
- **Patrones de interacción**: 1
  - Pattern: 080442f8-90f5-4c4c-a2a6-4768722ae1d1
  - Título: Consultar Codex
  - Canal: BACKGROUND
  - Reusable: True
  - Éxitos: 1, Fallos: 1 (50% éxito)
  - Operaciones: 2 steps
- **Estado actual**: DISPONIBLE con uso limitado

#### 5. windsurf_installed
- **Tipo**: ToolType.CODE_EDITOR
- **Adapter**: external_assistant
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: launch_app, code_assistance
- **Metadata**:
  - assistant_kind: windsurf
- **Estado actual**: DISPONIBLE pero nunca usado

### Inferencia Local

#### 6. ollama_llm
- **Tipo**: ToolType.LLM_LOCAL
- **Adapter**: ollama
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: llm_query, summarize, classify
- **Metadata**:
  - assistant_kind: ollama
- **Patrones de interacción**: 1
  - Pattern: aa337d48-920b-4dfb-8829-4981a614537b
  - Título: Consultar Ollama local
  - Canal: BACKGROUND
  - Reusable: True
  - Éxitos: 2, Fallos: 0 (100% éxito)
  - Operaciones: 1 step
- **Estado actual**: DISPONIBLE con buen historial

### Navegador

#### 7. playwright_browser
- **Tipo**: ToolType.BROWSER
- **Adapter**: playwright
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: open_url, click, type_text, extract_text, screenshot
- **Estado actual**: DISPONIBLE pero nunca usado

#### 8. site_explorer_v1
- **Tipo**: ToolType.BROWSER
- **Adapter**: site_explorer
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: open_url, explore_site, catalog_pages, persist_site_manual
- **Estado actual**: DISPONIBLE pero nunca usado

### Shell / CLI

#### 9. shell_command
- **Tipo**: ToolType.SHELL
- **Adapter**: shell
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: run_command, inspect_environment
- **Estado actual**: DISPONIBLE pero nunca usado

#### 10. cloudflared_cli
- **Tipo**: ToolType.SHELL
- **Adapter**: local_cli
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: check_version, list_tunnels, inspect_tunnel, access_info
- **Estado actual**: DISPONIBLE pero nunca usado

#### 11. git_cli
- **Tipo**: ToolType.SHELL
- **Adapter**: local_cli
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: check_version, status, log, diff, remote, branch_list, rev_parse
- **Estado actual**: DISPONIBLE pero nunca usado

#### 12. gh_cli
- **Tipo**: ToolType.SHELL
- **Adapter**: local_cli
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: check_version, check_auth_status, inspect_repo, list_prs, list_issues
- **Estado actual**: DISPONIBLE pero nunca usado

#### 13. winget_cli
- **Tipo**: ToolType.SHELL
- **Adapter**: local_cli
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: check_version, list_packages, search_package, show_package, source_list
- **Estado actual**: DISPONIBLE pero nunca usado

### MCP / APIs

#### 14. mcp_client
- **Tipo**: ToolType.MCP_CLIENT
- **Adapter**: mcp
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: mcp_call
- **Estado actual**: DISPONIBLE pero nunca usado

#### 15. devin_api
- **Tipo**: ToolType.MCP_CLIENT
- **Adapter**: devin_api
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: code_assistance, shell_execution, web_browsing, structured_reasoning
- **Metadata**:
  - assistant_kind: devin
- **Estado actual**: DISPONIBLE pero nunca usado

#### 16. github_api
- **Tipo**: ToolType.MCP_CLIENT
- **Adapter**: github_api
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: github_read_pr, github_create_pr, github_merge_pr, github_enable_auto_merge, github_comment_issue, github_list_issues, github_list_prs
- **Estado actual**: DISPONIBLE pero nunca usado

### Desktop Automation

#### 17. desktop_human_runner
- **Tipo**: ToolType.CUSTOM
- **Adapter**: desktop_human
- **Disponible**: True
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: launch_app, focus_window, click, type_text, scroll, screenshot, wait_for_window, wait_for_change
- **Metadata**:
  - assistant_kind: iabv_runtime
- **Estado actual**: DISPONIBLE pero nunca usado

### Code Editor

#### 18. aider_coder
- **Tipo**: ToolType.CODE_EDITOR
- **Adapter**: aider
- **Disponible**: False
- **Estado**: UNVALIDATED
- **Éxitos/Fallos**: 0/0
- **Capabilities**: edit_code, plan_patch
- **Estado actual**: NO DISPONIBLE

## PATRONES DE INTERACCIÓN DETALLADOS

### chatgpt_web_assisted - Pattern be61f185
- **Uso**: Consultar Ollama local sobre ChatGPT
- **Canal**: UI (interacción con usuario)
- **Reusable**: True
- **Historial**: 34 éxitos, 10 fallos (77% éxito)
- **Operaciones**: 2 steps
- **Problema**: Fallos recurrentes por browser_security_verification
- **Recomendación**: Cambiar a chatgpt_installed (desktop app) para evitar detección de bot

### ollama_llm - Pattern aa337d48
- **Uso**: Consultar Ollama local
- **Canal**: BACKGROUND (automático)
- **Reusable**: True
- **Historial**: 2 éxitos, 0 fallos (100% éxito)
- **Operaciones**: 1 step
- **Estado**: Funcional y confiable

### codex_installed - Pattern 080442f8
- **Uso**: Consultar Codex
- **Canal**: BACKGROUND (automático)
- **Reusable**: True
- **Historial**: 1 éxito, 1 fallo (50% éxito)
- **Operaciones**: 2 steps
- **Estado**: Uso limitado, necesita más datos

## TAREAS RECIENTES (Últimas 5)

Todas las tareas recientes son consultas a ChatGPT vía Ollama:
- Objetivo: "Consultar Ollama local sobre: has una consulta a chatgpt"
- Estado: APPROVED
- Scope: read_only
- Acciones: 2 steps cada una

## RESULTADOS RECIENTES (Últimos 5)

- **Éxito general**: 19/20 (95%)
- **Fallo detectado**: 1 fallo en chatgpt_web_assisted (estado: failed)
- **Estados de validación**: SANDBOX_PASS, APPROVED, UNVALIDATED
- **Estados de ejecución**: sandbox_pass, executed, failed

## MODELO DE MEMORIA POR HERRAMIENTA

### chatgpt_web_assisted
- **Estado operativo**: DEGRADADO
- **Problema principal**: browser_security_verification (headless + nuevo lanzamiento detectado como bot)
- **Historial de fallas**: 10/44 (23%)
- **Alternativa**: chatgpt_installed (desktop app, nunca usado)
- **Recomendación**: Implementar reutilización de ventana existente o cambiar a desktop app

### ollama_llm
- **Estado operativo**: SALUDABLE
- **Historial**: 2/2 (100% éxito)
- **Canal**: BACKGROUND (automático)
- **Recomendación**: Mantener como fallback confiable

### codex_installed
- **Estado operativo**: INCIERTO
- **Historial**: 1/2 (50% éxito)
- **Uso limitado**: Solo 2 ejecuciones
- **Recomendación**: Necesita más datos para evaluación

### Resto de herramientas
- **Estado operativo**: NO USADAS
- **Disponibilidad**: 17/18 disponibles (aider_coder no disponible)
- **Recomendación**: Evaluar uso según necesidades

## PATRONES DE COMPORTAMIENTO IDENTIFICADOS

1. **Preferencia por chatgpt_web_assisted**: 44/44 tareas recientes usan esta herramienta
2. **Falla recurrente en ChatGPT web**: browser_security_verification bloquea ejecuciones headless
3. **Ollama como fallback confiable**: 100% éxito en uso limitado
4. **Subutilización de alternativas**: chatgpt_installed, claude_installed, codex_installed nunca usadas
5. **Falta de validación**: Todas las herramientas en estado UNVALIDATED

## RECOMENDACIONES PARA FASE 4 (REGLAS DE DECISIÓN)

1. **Implementar reutilización de ventana**: Si ventana ChatGPT existe, reusarla en vez de lanzar nueva
2. **Cambiar a desktop app tras N fallos**: Si chatgpt_web_assisted falla >= 3 veces seguidas, cambiar a chatgpt_installed
3. **Validar herramientas**: Ejecutar validación de disponibilidad para todas las herramientas
4. **Expandir uso de alternativas**: Probar claude_installed y codex_installed para diversificar
5. **Usar Ollama como fallback**: Cuando herramientas externas fallan, usar ollama_llm

## PRÓXIMA FASE

FASE 3: Percepción Universal - usar servicios de percepción para entender el entorno real
