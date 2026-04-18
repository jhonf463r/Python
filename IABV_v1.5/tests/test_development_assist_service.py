from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.services.development.development_assist_service import DevelopmentAssistService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_development_assist_service_builds_local_stack_summary() -> None:
    root = _workspace('devassist')
    service = DevelopmentAssistService(str(root))

    summary = service.build_local_stack_summary()

    assert 'qwen3:8b' in summary
    assert 'gemma3:4b' in summary
    assert 'OpenAI no forma parte del runtime' in summary


def test_development_assist_service_builds_repo_bridge_summary() -> None:
    root = _workspace('devassist')
    service = DevelopmentAssistService(str(root))

    summary = service.build_repo_bridge_summary()

    assert 'Codex trabaja mejor como agente externo' in summary
    assert 'AGENTS.md' in summary


def test_development_assist_service_builds_codex_packet() -> None:
    root = _workspace('devassist')
    service = DevelopmentAssistService(str(root))

    packet = service.build_codex_packet(
        user_goal='Deja listo el backend local',
        selected_role_title='Evolucion del proyecto',
        project_context={
            'episodes': 3,
            'knowledge_items': 2,
            'runs': 5,
            'artifacts': 8,
            'analytics': {'summary': 'Hay fallos repetidos en ejecucion.'},
            'teaching_gaps': {'summary': 'Falta reensenar checkout.', 'follow_up_teachings': ['Reforzar checkout']},
            'pbt_state': {'generation': 2, 'best_score': 91.4, 'summary': 'Generacion 2 estable.'},
        },
    )

    assert 'Paquete para Codex' in packet
    assert 'Deja listo el backend local' in packet
    assert 'Reforzar checkout' in packet
    assert 'Generacion 2 estable.' in packet
