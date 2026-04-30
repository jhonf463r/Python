"""Minimal MCP probe for evidence harness.

Connects to the local IABV MCP server via streamable-http and calls
a single tool, printing the JSON result to stdout.

Usage:
    python mcp_probe.py <tool_name>

Examples:
    python mcp_probe.py ui_bridge_get_state
    python mcp_probe.py world_model_snapshot

Exit codes:
    0  success (JSON on stdout)
    1  connection/protocol error (message on stderr)
"""
from __future__ import annotations

import asyncio
import json
import sys


async def probe(tool_name: str, arguments: dict | None = None, url: str = 'http://127.0.0.1:8000/mcp') -> dict:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url, timeout=10) as (read_stream, write_stream, _get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            # result is CallToolResult with .content list
            parts = []
            for item in result.content:
                if hasattr(item, 'text'):
                    try:
                        parts.append(json.loads(item.text))
                    except (json.JSONDecodeError, TypeError):
                        parts.append(item.text)
                else:
                    parts.append(str(item))
            if len(parts) == 1:
                payload = parts[0]
            else:
                payload = parts
            # Some tools wrap their response in {"id": ..., "result": {...}}.
            # Unwrap so callers always get the actual data.
            if isinstance(payload, dict) and 'result' in payload and 'id' in payload:
                payload = payload['result']
            return payload


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python mcp_probe.py <tool_name>', file=sys.stderr)
        sys.exit(1)

    tool_name = sys.argv[1]

    try:
        result = asyncio.run(probe(tool_name))
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    except Exception as exc:
        print('MCP probe failed: {0}'.format(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
