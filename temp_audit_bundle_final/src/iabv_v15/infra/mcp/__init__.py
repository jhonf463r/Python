"""MCP (Model Context Protocol) integration for IABV v1.5.

Expone los servicios core del programa (world_model, orchestrator,
site_exploration, portable_context, self_examination, chatgpt_web_assisted)
como herramientas MCP para que agentes externos (Devin, Claude, Codex u otros
clientes MCP-compatibles) puedan consumirlos de forma autónoma y gobernada.

La exposición respeta AutonomyGovernancePolicy: no se abre ninguna ruta que
no esté permitida por la política viva del programa.
"""

from iabv_v15.infra.mcp.server import IABVMCPServer, create_server

__all__ = ["IABVMCPServer", "create_server"]
