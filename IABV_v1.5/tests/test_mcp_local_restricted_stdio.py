"""End-to-end contract check for the isolated local-restricted MCP stdio profile."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")
from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_restricted_stdio_initialize_list_call_and_forbidden_tool_rejection(
    tmp_path: Path,
) -> None:
    async def exercise_client() -> None:
        isolated_workspace = tmp_path / "synthetic-empty-workspace"
        isolated_workspace.mkdir()
        assert list(isolated_workspace.iterdir()) == []

        # Pass only process/runtime variables required by Windows and Python;
        # do not forward the parent process environment (which may contain secrets).
        env = {
            key: os.environ[key]
            for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
            if key in os.environ
        }
        env.update(
            {
                "PYTHONPATH": str(PROJECT_ROOT / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "IABV_MCP_TRANSPORT": "stdio",
                "IABV_MCP_PROFILE": "local_restricted",
                "IABV_WORKSPACE_ROOT": str(isolated_workspace),
                "IABV_MCP_LOG_LEVEL": "WARNING",
            }
        )
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-c", "from iabv_v15.infra.mcp.server import main; main()"],
            env=env,
            cwd=str(isolated_workspace),
        )

        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                listed = await session.list_tools()
                names = [tool.name for tool in listed.tools]
                assert names == ["bridge_health"]

                result = await session.call_tool("bridge_health", arguments={})
                assert result.isError is not True
                assert len(result.content) == 1
                assert json.loads(result.content[0].text) == {"status": "ok"}

                forbidden = await session.call_tool(
                    "read_repo_file", arguments={"relative_path": "not-present.txt"}
                )
                assert forbidden.isError is True

        assert list(isolated_workspace.iterdir()) == []

    asyncio.run(exercise_client())
