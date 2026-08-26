# Limitations for R4 G1 Implementation

1. **Runtime Evidence**: Tests were not executed in this session. Runtime evidence will be captured during independent audit.

2. **Cloud Provider**: CloudReasoningPlannerService requires valid credentials. If unavailable, the test will skip with REAL_PROVIDER_UNAVAILABLE.

3. **Authority Service**: Tests require AuthorityService running with Named Pipe IPC.

4. **Tool Support**: Currently only write_repo_file is supported in the canonical contract. Other tools can be added by extending TOOL_DESCRIPTORS.

5. **MCP Transport**: Tests use direct Python call to MCP tool function (server.mcp._tools[tool].fn). Full MCP transport runtime verification requires external MCP client.

6. **Force Push**: Used force-with-lease to push due to remote having diverged from local. This is acceptable for correction commits.
