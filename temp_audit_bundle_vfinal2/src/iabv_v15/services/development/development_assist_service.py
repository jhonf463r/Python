from __future__ import annotations

from pathlib import Path
from typing import Any


class DevelopmentAssistService:
    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = Path(workspace_root)

    def build_repo_bridge_summary(self) -> str:
        agents_path = self.workspace_root / 'AGENTS.md'
        return (
            'Codex trabaja mejor como agente externo de desarrollo sobre este mismo repo. '
            'La integracion correcta es workspace compartido, AGENTS.md, paquetes de diagnostico y pruebas reproducibles. '
            f'Ruta guia: {agents_path}.'
        )

    def build_local_stack_summary(self) -> str:
        return (
            'Stack local oficial: Ollama con qwen3:8b como cerebro principal, gemma3:4b como perfil visual y '
            'qwen3-embedding:0.6b como base de recuperacion semantica. OpenAI no forma parte del runtime de IABV.'
        )

    def build_codex_packet(
        self,
        *,
        user_goal: str,
        selected_role_title: str,
        project_context: dict[str, Any],
    ) -> str:
        goal = user_goal.strip() or 'Propone la siguiente mejora prioritaria para IABV v1.5.'
        analytics = project_context.get('analytics', {})
        gaps = project_context.get('teaching_gaps', {})
        pbt_state = project_context.get('pbt_state', {})
        return (
            'Paquete para Codex - IABV v1.5\n\n'
            f'Workspace: {self.workspace_root}\n'
            f'Rol activo: {selected_role_title}\n'
            f'Meta actual: {goal}\n'
            'Politica: local-first, secretos protegidos, sin OpenAI en runtime, sin imports legacy en runtime.\n\n'
            'Estado del proyecto:\n'
            f"- episodios: {project_context.get('episodes', 0)}\n"
            f"- conocimiento: {project_context.get('knowledge_items', 0)}\n"
            f"- ejecuciones: {project_context.get('runs', 0)}\n"
            f"- artefactos: {project_context.get('artifacts', 0)}\n\n"
            'Analitica:\n'
            f"{analytics.get('summary', 'Sin analitica.')}\n\n"
            'Huecos de ensenanza:\n'
            f"- resumen: {gaps.get('summary', 'Sin huecos detectados.')}\n"
            f"- siguientes ensenanzas: {', '.join(gaps.get('follow_up_teachings', [])) or 'ninguna'}\n\n"
            'PBT:\n'
            f"- generacion: {pbt_state.get('generation', 0)}\n"
            f"- mejor score: {pbt_state.get('best_score', 0.0)}\n"
            f"- resumen: {pbt_state.get('summary', 'Sin ejecuciones PBT aun.')}\n\n"
            'Entrega esperada para Codex:\n'
            '1. diagnostico breve\n'
            '2. causa raiz\n'
            '3. cambio vertical recomendado\n'
            '4. pruebas a ejecutar\n'
            '5. riesgos o tradeoffs\n'
        )

