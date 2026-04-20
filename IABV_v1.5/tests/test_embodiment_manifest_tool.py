"""Tests de la MCP tool ``embodiment_manifest`` (PCS v1)."""

from __future__ import annotations

from tests.test_mcp_server import _build_container, _call_tool  # type: ignore
from iabv_v15.infra.mcp.server import IABVMCPServer


def _manifest() -> dict[str, object]:
    server = IABVMCPServer(_build_container())
    payload = _call_tool(server, "embodiment_manifest")
    assert isinstance(payload, dict)
    return payload


def test_embodiment_manifest_declares_protocol_and_principle() -> None:
    payload = _manifest()
    assert payload["protocol"] == "PCS-v1"
    principle = payload["embodiment_principle"]
    assert isinstance(principle, str)
    assert "sensor" in principle.lower()


def test_embodiment_manifest_sensor_map_is_non_empty_and_well_formed() -> None:
    payload = _manifest()
    mapping = payload["sensor_before_question"]
    assert isinstance(mapping, list)
    assert len(mapping) >= 10, "el mapeo debe cubrir al menos 10 sensores"
    for entry in mapping:
        assert isinstance(entry, dict)
        assert set(entry.keys()) == {"question", "tool"}
        assert isinstance(entry["question"], str) and entry["question"].strip()
        assert isinstance(entry["tool"], str) and entry["tool"].strip()


def test_embodiment_manifest_covers_known_iabv_tools() -> None:
    payload = _manifest()
    tools_referenced = {entry["tool"] for entry in payload["sensor_before_question"]}
    # Sensores centrales que ya expone el server deben estar en el manifest.
    expected = {
        "world_model_snapshot",
        "self_examination_current",
        "run_pytest",
        "read_repo_file",
        "probe_assistant_login",
        "chatgpt_web_capture",
        "run_self_audit",
        "portable_context_get",
    }
    missing = expected - tools_referenced
    assert not missing, f"manifest no declara sensores: {missing}"


def test_embodiment_manifest_handshake_is_non_blocking_in_v1() -> None:
    payload = _manifest()
    assert payload["handshake_required"] is False
    assert payload["violations_tracked"] is True
    assert payload["violation_reporting_channel"] == "operational_self_examination_service"
    assert payload["session_scope_header"] == "X-IABV-Embodiment-Session"


def test_embodiment_manifest_cross_references_sibling_endpoints() -> None:
    payload = _manifest()
    assert payload["frame_translation_endpoint"] == "cognitive_frame_translate"
    assert payload["capability_profiles_endpoint"] == "assistant_capabilities_list"


def test_embodiment_manifest_is_deterministic() -> None:
    first = _manifest()
    second = _manifest()
    assert first == second, "el manifest debe ser estable entre llamadas"


# ------------------------------------------------------------------
# record_embodiment_interaction — PCS v1 write endpoint
# ------------------------------------------------------------------

def test_record_embodiment_interaction_records_and_detects_violation() -> None:
    from iabv_v15.services.evolution.embodiment_violation_detector import (
        EmbodimentViolationDetector,
    )
    container = _build_container()
    container.embodiment_violation_detector = EmbodimentViolationDetector()
    server = IABVMCPServer(container)

    result = _call_tool(
        server,
        "record_embodiment_interaction",
        session_id="sess-mcp-1",
        question_text="¿qué ventanas están abiertas ahora?",
        tool_ids_used="web_search",
        assistant_kind="chatgpt",
        trace_id="trace-42",
    )

    assert result["recorded"] is True
    assert result["session_id"] == "sess-mcp-1"
    assert result["tool_ids_used"] == ["web_search"]

    violations = _call_tool(
        server,
        "embodiment_violations_current",
        session_id="sess-mcp-1",
    )
    assert violations["count"] == 1
    record = violations["violations"][0]
    assert record["expected_tool_id"] == "list_open_windows"
    assert record["violation_kind"] == "sensor_bypass"


def test_record_embodiment_interaction_no_violation_when_correct_tool_used() -> None:
    from iabv_v15.services.evolution.embodiment_violation_detector import (
        EmbodimentViolationDetector,
    )
    container = _build_container()
    container.embodiment_violation_detector = EmbodimentViolationDetector()
    server = IABVMCPServer(container)

    _call_tool(
        server,
        "record_embodiment_interaction",
        session_id="sess-ok",
        question_text="¿qué ventanas están abiertas ahora?",
        tool_ids_used="list_open_windows",
    )

    violations = _call_tool(
        server,
        "embodiment_violations_current",
        session_id="sess-ok",
    )
    assert violations["count"] == 0


def test_record_embodiment_interaction_parses_comma_separated_tools() -> None:
    from iabv_v15.services.evolution.embodiment_violation_detector import (
        EmbodimentViolationDetector,
    )
    container = _build_container()
    container.embodiment_violation_detector = EmbodimentViolationDetector()
    server = IABVMCPServer(container)

    result = _call_tool(
        server,
        "record_embodiment_interaction",
        session_id="sess-multi",
        question_text="¿tests pasan?",
        tool_ids_used="run_pytest, read_repo_file",
    )

    assert result["tool_ids_used"] == ["run_pytest", "read_repo_file"]

    violations = _call_tool(
        server,
        "embodiment_violations_current",
        session_id="sess-multi",
    )
    assert violations["count"] == 0


def test_record_embodiment_interaction_fails_gracefully_without_detector() -> None:
    container = _build_container()
    server = IABVMCPServer(container)

    result = _call_tool(
        server,
        "record_embodiment_interaction",
        session_id="sess-no-det",
        question_text="¿qué ventanas?",
    )

    assert result["recorded"] is False
    assert result["error"] == "detector_unavailable"
