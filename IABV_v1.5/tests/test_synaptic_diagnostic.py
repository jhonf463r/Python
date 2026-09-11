"""Tests for diagnose_synaptic_routing MCP tool."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from iabv_v15.infra.mcp.server import IABVMCPServer


# ----------------------------------------------------------------------
# Test fixtures from test_mcp_server (reused)
# ----------------------------------------------------------------------


def _build_container(**kwargs) -> Any:
    """Build a minimal test container for MCP server tests."""
    from iabv_v15.domain.models import (
        EnvironmentSelfModel,
        NetworkStatusSnapshot,
        WorldModelSnapshot,
    )
    from iabv_v15.services.roles.synaptic_router import SynapticRouter

    container = SimpleNamespace()

    # Config
    from iabv_v15.infra.config import load_app_config
    container.config = load_app_config(None)

    # SynapticRouter
    container.synaptic_router = SynapticRouter(
        capability_registry={},
        adaptive_weight_layer=None,
        world_model_provider=lambda: None,
        experiment_lab_repository=None,
        enabled_override=kwargs.get("enabled_override"),
    )

    # Other minimal services
    container.tool_adapters = {}
    container.tool_registry = SimpleNamespace()

    return container


def _call_tool(server: IABVMCPServer, tool_name: str, **kwargs) -> dict[str, Any]:
    """Call a tool by name on the server."""
    registry = server.mcp._tool_manager._tools  # fastmcp exposed internal
    tool = registry.get(tool_name)
    if tool is None:
        raise ValueError(f"Tool {tool_name} not found")
    return tool.fn(**kwargs)


# ----------------------------------------------------------------------
# Tests for diagnose_synaptic_routing (SynapticRouting diagnostic tool)
# ----------------------------------------------------------------------


def test_diagnose_synaptic_routing_default_disabled() -> None:
    """Without any configuration, SynapticRouting should be disabled by default."""
    import os

    # Clear env vars
    saved = {}
    for key in ["SYNAPTIC_ROUTING", "IABV_SYNAPTIC_ROUTING_ENABLED"]:
        saved[key] = os.environ.get(key)
        os.environ.pop(key, None)

    try:
        # Build container without synaptic routing enabled
        container = _build_container()
        # Ensure config is None/false
        if hasattr(container, "config"):
            container.config.synaptic_routing_enabled = None

        server = IABVMCPServer(container)
        payload = _call_tool(server, "diagnose_synaptic_routing")

        assert payload.get("synaptic_routing_env") is None
        assert payload.get("iabv_synaptic_routing_enabled_env") is None
        assert payload.get("appconfig_synaptic_routing_enabled") is None
        assert payload.get("synaptic_router_enabled_override") is None
        assert payload.get("synaptic_router_effective_enabled") is False
        assert payload.get("config_source") == "default"
    finally:
        # Restore
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


def test_diagnose_synaptic_routing_env_true() -> None:
    """With SYNAPTIC_ROUTING=true in environment, should be enabled."""
    import os

    saved = {}
    for key in ["SYNAPTIC_ROUTING", "IABV_SYNAPTIC_ROUTING_ENABLED"]:
        saved[key] = os.environ.get(key)
        os.environ.pop(key, None)

    try:
        os.environ["SYNAPTIC_ROUTING"] = "true"

        container = _build_container()
        server = IABVMCPServer(container)
        payload = _call_tool(server, "diagnose_synaptic_routing")

        assert payload.get("synaptic_routing_env") == "true"
        assert payload.get("iabv_synaptic_routing_enabled_env") is None
        # config should have resolved to True from env
        assert payload.get("appconfig_synaptic_routing_enabled") is True
        assert payload.get("synaptic_router_enabled_override") is None
        assert payload.get("synaptic_router_effective_enabled") is True
        assert payload.get("config_source") in ("environment", "appconfig")
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


def test_diagnose_synaptic_routing_iabv_env_true() -> None:
    """With IABV_SYNAPTIC_ROUTING_ENABLED=true in environment, should be enabled."""
    import os

    saved = {}
    for key in ["SYNAPTIC_ROUTING", "IABV_SYNAPTIC_ROUTING_ENABLED"]:
        saved[key] = os.environ.get(key)
        os.environ.pop(key, None)

    try:
        os.environ["IABV_SYNAPTIC_ROUTING_ENABLED"] = "true"

        container = _build_container()
        server = IABVMCPServer(container)
        payload = _call_tool(server, "diagnose_synaptic_routing")

        assert payload.get("synaptic_routing_env") is None
        assert payload.get("iabv_synaptic_routing_enabled_env") == "true"
        assert payload.get("appconfig_synaptic_routing_enabled") is True
        assert payload.get("synaptic_router_enabled_override") is None
        assert payload.get("synaptic_router_effective_enabled") is True
        assert payload.get("config_source") in ("environment", "appconfig")
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


def test_diagnose_synaptic_routing_override_precedence() -> None:
    """Explicit enabled_override should take precedence over environment."""
    import os

    saved = {}
    for key in ["SYNAPTIC_ROUTING", "IABV_SYNAPTIC_ROUTING_ENABLED"]:
        saved[key] = os.environ.get(key)
        os.environ.pop(key, None)

    try:
        # Set env to false but override to true
        os.environ["SYNAPTIC_ROUTING"] = "false"

        container = _build_container()
        # Simulate explicit override
        if hasattr(container, "synaptic_router"):
            container.synaptic_router._enabled_override = True

        server = IABVMCPServer(container)
        payload = _call_tool(server, "diagnose_synaptic_routing")

        assert payload.get("synaptic_routing_env") == "false"
        assert payload.get("synaptic_router_enabled_override") is True
        assert payload.get("synaptic_router_effective_enabled") is True
        assert payload.get("config_source") == "explicit_override"
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


def test_diagnose_synaptic_routing_read_only() -> None:
    """The diagnostic tool should not modify runtime state."""
    import os

    saved = {}
    for key in ["SYNAPTIC_ROUTING", "IABV_SYNAPTIC_ROUTING_ENABLED"]:
        saved[key] = os.environ.get(key)
        os.environ.pop(key, None)

    try:
        container = _build_container()
        server = IABVMCPServer(container)

        # Call diagnostic twice
        payload1 = _call_tool(server, "diagnose_synaptic_routing")
        payload2 = _call_tool(server, "diagnose_synaptic_routing")

        # Results should be identical (no state mutation)
        assert payload1 == payload2
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
