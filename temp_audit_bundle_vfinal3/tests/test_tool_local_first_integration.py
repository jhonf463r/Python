from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import InferenceRequest, TaskContext, ToolCard, ToolTask, ToolType
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.tools.tool_registry import ToolRegistry


class FakeToolAdapter:
    def __init__(self, tool_type: ToolType, *, available: bool = True) -> None:
        self.tool_type = tool_type
        self.available = available

    def is_available(self, card: ToolCard) -> bool:
        return self.available

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict:
        return {
            'success': True,
            'output_text': 'ok',
            'extracted_data': {},
            'artifacts': [],
            'error_message': '',
            'execution_ms': 1,
            'metadata': {'sandbox': sandbox},
        }


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_tool_local_first_intent_and_pack_resolution() -> None:
    root = _workspace('tool_local_first_intent')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'evolution'))
        pack_repository = StrategyPackRepository(db, storage)
        registry = StrategyPackRegistry(pack_repository)
        intent_service = IntentUnderstandingService()
        request = InferenceRequest(user_goal='Usa playwright en sandbox para abrir https://example.com')

        intent, _ = intent_service.classify(request)
        pack = registry.resolve_pack(intent, TaskContext())

        assert intent.intent_key == 'tools.sandbox'
        assert intent.detected_role.value == 'tool_sandbox'
        assert pack.pack_id == 'tools.sandbox'
        assert pack.approval_policy == 'never'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_capability_readiness_uses_registered_cards() -> None:
    root = _workspace('tool_capability_readiness')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        tool_storage = ArtifactStorage(str(root / 'tool_teaching'))
        evolution_storage = ArtifactStorage(str(root / 'evolution'))
        tool_repository = ToolRecordRepository(db, tool_storage)
        ToolRegistry(
            tool_repository,
            {
                'playwright': FakeToolAdapter(ToolType.BROWSER),
                'ollama': FakeToolAdapter(ToolType.LLM_LOCAL),
                'shell': FakeToolAdapter(ToolType.SHELL),
                'aider': FakeToolAdapter(ToolType.CODE_EDITOR, available=False),
                'mcp': FakeToolAdapter(ToolType.MCP_CLIENT, available=False),
            },
        )
        capability_repository = CapabilityRepository(db, evolution_storage)
        service = CapabilityReadinessService(capability_repository, tool_repository)
        sandbox_intent = IntentUnderstandingService().classify(InferenceRequest(user_goal='Usa una herramienta local en sandbox'))[0]
        workflow_intent = IntentUnderstandingService().classify(InferenceRequest(user_goal='Usa una herramienta local para ejecutar una tarea'))[0]

        sandbox_capabilities = service.evaluate(sandbox_intent, TaskContext())
        workflow_capabilities = service.evaluate(workflow_intent, TaskContext())
        sandbox_map = {item.capability_id: item for item in sandbox_capabilities}
        workflow_map = {item.capability_id: item for item in workflow_capabilities}

        assert sandbox_map['tools.local.registry'].status.value == 'ready'
        assert sandbox_map['tools.local.sandbox'].status.value == 'ready'
        assert workflow_map['tools.local.registry'].status.value == 'ready'
        assert workflow_map['tools.local.execution'].status.value == 'ready_with_approval'
    finally:
        shutil.rmtree(root, ignore_errors=True)
