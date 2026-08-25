from __future__ import annotations

from types import SimpleNamespace

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


class _ExplodingObjectiveRepository:
    def latest_active(self, *args, **kwargs):
        raise AssertionError("objective repository must not be read on UI display path")

    def get(self, *args, **kwargs):
        raise AssertionError("objective repository must not be read on UI display path")

    def list_children(self, *args, **kwargs):
        raise AssertionError("objective repository must not be read on UI display path")


def _stub_vm() -> SimpleNamespace:
    vm = SimpleNamespace()
    vm.objective_repository = _ExplodingObjectiveRepository()
    vm._last_goal_context = {}
    vm._last_adaptive_payload = {}
    vm._goal_context_refresh_in_flight = False
    vm._goal_context_refresh_last_ts = 0.0
    vm._goal_context_refresh_cooldown_s = 15.0
    vm._scheduled_goal_refreshes = []
    vm._current_site_id = lambda: ""
    vm._assistant_tool_cards = lambda: [
        {"name": "ChatGPT", "status": "web preparada", "detail": "session ready"},
        {"name": "Codex", "status": "listo automatico", "detail": "local bridge ready"},
    ]
    vm._provider_cards = []
    vm._pbt_state = {}
    vm._assistant_tool_ids = lambda: []
    vm._goal_context_from_payload = (
        ControlCenterViewModel._goal_context_from_payload.__get__(vm)
    )
    vm._goal_context_from_repository = (
        ControlCenterViewModel._goal_context_from_repository.__get__(vm)
    )
    vm._goal_context_matches_site = (
        ControlCenterViewModel._goal_context_matches_site.__get__(vm)
    )

    def _schedule(site_id=None, *, reason=""):
        vm._scheduled_goal_refreshes.append({"site_id": site_id, "reason": reason})

    vm._schedule_goal_context_refresh = _schedule
    vm._goal_context_for_display = (
        ControlCenterViewModel._goal_context_for_display.__get__(vm)
    )
    vm._startup_readiness_text = (
        ControlCenterViewModel._startup_readiness_text.__get__(vm)
    )
    vm._build_agent_cards = ControlCenterViewModel._build_agent_cards.__get__(vm)
    vm._build_provider_diagnostic = (
        ControlCenterViewModel._build_provider_diagnostic.__get__(vm)
    )
    return vm


def test_startup_readiness_nonblocking_does_not_query_objective_repository():
    vm = _stub_vm()

    text = vm._startup_readiness_text(validating_local_stack=True, nonblocking=True)

    assert "Arranque autonomo" in text
    assert vm._scheduled_goal_refreshes


def test_provider_diagnostic_nonblocking_does_not_query_objective_repository():
    vm = _stub_vm()
    vm._provider_cards = [
        {
            "provider_name": "Ollama",
            "status": "pendiente",
            "detail": "not running",
        }
    ]
    vm.config = SimpleNamespace(
        ollama_base_url="http://127.0.0.1:11434",
        lm_studio_base_url="http://127.0.0.1:1234",
        ollama_embedding_model="nomic-embed-text",
    )
    vm._auto_route_enabled = True

    text = vm._build_provider_diagnostic(nonblocking=True)

    assert "Estado del stack local" in text
    assert "Ollama" in text
    assert vm._scheduled_goal_refreshes


def test_agent_cards_nonblocking_does_not_query_objective_repository():
    vm = _stub_vm()

    cards = vm._build_agent_cards(nonblocking_goal_context=True)

    assert any(card["name"] == "Adaptive orchestrator" for card in cards)
    assert vm._scheduled_goal_refreshes

