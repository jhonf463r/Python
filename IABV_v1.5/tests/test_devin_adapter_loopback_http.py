from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from iabv_v15.domain.models import (
    InferenceRequest,
    TaskRole,
    ToolCard,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.evolution.intent_scoped_briefing_service import IntentScopedBriefingService
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.evolution.session_start_briefing_service import SessionBriefing
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_validator import ToolValidator


CANONICAL_HTTP_SENTINEL_R5 = "CANONICAL_HTTP_SENTINEL_R5"
EXTERNAL_HTTP_SENTINEL_R5 = "EXTERNAL_HTTP_SENTINEL_R5"


class _CanonicalBriefing:
    def build_briefing(self, task_context=None):
        return SessionBriefing(
            summary=CANONICAL_HTTP_SENTINEL_R5,
            assistant_brief="Transmit the canonical briefing.",
            lessons=(),
            recommendations=(),
            unresolved=(),
            text=CANONICAL_HTTP_SENTINEL_R5,
            generated_at_epoch=datetime.now(timezone.utc).timestamp(),
            package_id="loopback-r5",
            truncated=False,
        )


def _tool_teach_service(root: Path, adapter: DevinApiToolAdapter) -> ToolTeachService:
    db = AppDatabase(str(root / "app.sqlite"))
    storage = ArtifactStorage(str(root / "tool_teaching"))
    repository = ToolRecordRepository(db, storage)
    registry = ToolRegistry(repository, {"devin_api": adapter})
    devin_card = ToolCard(
        tool_id="devin_api",
        title="Devin API",
        tool_type=ToolType.MCP_CLIENT,
        adapter_key="devin_api",
        validation_status=ToolValidationStatus.SANDBOX_PASS,
        available=True,
        metadata={"assistant_kind": "devin"},
    )
    repository.save_card(devin_card)
    registry.refresh_card(devin_card, force=True)
    learning = InteractionLearningService(repository)
    memory = ToolMemory(repository, learning)
    experiment_lab = ExperimentLab(
        repository=ExperimentLabRepository(db, storage),
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(),
    )
    return ToolTeachService(
        registry=registry,
        memory=memory,
        sandbox=ToolSandbox(ToolValidator()),
        validator=ToolValidator(),
        approval_policy=ToolApprovalPolicy(),
        rollback_manager=ToolRollbackManager(),
        adapters={"devin_api": adapter},
        workspace_root=str(root),
        interaction_learning_service=learning,
        mode_selector=InteractionModeSelector(registry, repository),
        experiment_lab=experiment_lab,
        live_audit_supervisor=LiveAuditSupervisor(
            tool_record_repository=repository,
            experiment_lab=experiment_lab,
        ),
        intent_scoped_briefing_service=IntentScopedBriefingService(
            session_start_briefing_service=_CanonicalBriefing(),
        ),
    )


@contextmanager
def _loopback_devin_server():
    received: dict[str, object] = {"requests": []}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            received["requests"].append({
                "method": "POST",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": body,
            })
            self._json({"session_id": "loopback-session-r5", "status": "running"})

        def do_GET(self):
            received["requests"].append({"method": "GET", "path": self.path})
            self._json({"status": "finished", "structured_output": "loopback complete"})

        def _json(self, payload):
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_tool_task_reaches_devin_adapter_over_real_loopback_http(monkeypatch, tmp_path):
    """Proves ToolTeachService production execution path → adapter → HTTP transmission.

    This test exercises the REAL production boundary:
    ToolTeachService.execute_task() → registry.pick_card_for_task() → adapter resolution → adapter.run()

    NOT: direct adapter.run() invocation which bypasses production path.
    """
    monkeypatch.setenv("IABV_SQLITE_WAL", "0")
    with _loopback_devin_server() as (base_url, received):
        adapter = DevinApiToolAdapter(
            api_key="TEST_LOOPBACK_TOKEN",
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
        )
        adapter.BASE_URL = base_url
        service = _tool_teach_service(tmp_path, adapter)
        task = service.build_task_from_request(InferenceRequest(
            user_goal="Transmit the R5 canonical context.",
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                "tool_id": "devin_api",
                "context_pack": EXTERNAL_HTTP_SENTINEL_R5,
                "force_impact": "high",
            },
            metadata={"force_impact": "high"},
        ))

        # Use PRODUCTION execution path: execute_task() instead of direct adapter.run()
        # approved=True is required for test isolation (not altering production policy)
        result = service.execute_task(task, approved=True)

    requests = received["requests"]
    post = next(item for item in requests if item["method"] == "POST")
    prompt = post["body"]["prompt"]
    assert post["path"] == "/v1/sessions"
    assert post["authorization"] == "Bearer TEST_LOOPBACK_TOKEN"
    assert task.objective in prompt
    assert CANONICAL_HTTP_SENTINEL_R5 in prompt
    # This is failure-first against pre-a89d42e behavior: that implementation
    # put the external value in context_pack, so the canonical assertion fails.
    assert prompt != EXTERNAL_HTTP_SENTINEL_R5
    assert task.metadata["context_pack"] != EXTERNAL_HTTP_SENTINEL_R5
    assert any(item["path"] == "/v1/session/loopback-session-r5" for item in requests)
    assert result.success is True
    # Production execution path validated - adapter was invoked via execute_task()
    # worker_telemetry is nested deeper; the key assertion is success + HTTP transmission
