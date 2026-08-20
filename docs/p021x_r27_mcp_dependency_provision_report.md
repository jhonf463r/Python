# P0.21x-R27: Provision MCP Dependency in Canonical Runtime - Final Report

### SOURCE OF TRUTH
**Repository**: IABV v1.5
**HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22
**Runtime Worktree**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5

==================================================
1. PRECHECK
==================================================

**Python Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe
**Python Version**: 3.13.2
**Pip Executable**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\pip.exe (pip 24.3.1)
**Runtime Worktree**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
**HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22
**Launcher**: launch_deterministic_runtime_p021v.ps1
**MCP Existence Before**: NOT_FOUND (Package(s) not found: mcp)
**MCP Version Before**: N/A

**Conclusion**: Precheck confirmed the runtime environment and identified missing mcp dependency.

==================================================
2. DEPENDENCY PROVISION
==================================================

**Action**: Installed mcp package in launcher environment
**Command Used**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\pip.exe install mcp
**Result**: Successfully installed mcp 2.0.0 and 21 dependencies
**Dependencies Installed**: 
- mcp-2.0.0
- mcp-types-2.0.0
- httpx2-2.10.0
- httpcore2-2.10.0
- jsonschema-4.26.0
- uvicorn-0.52.3
- starlette-1.6.0
- pyjwt-2.13.0
- python-multipart-0.0.32
- sse-starlette-3.4.8
- cryptography-50.0.0
- cffi-2.1.1
- pycparser-3.0
- opentelemetry-api-1.44.0
- attrs-26.1.0
- click-8.4.2
- colorama-0.4.6
- referencing-0.37.0
- rpds-py-2026.6.3
- truststore-0.10.4
- jsonschema-specifications-2025.9.1

**Source Modifications**: NONE
**Manual File Copies**: NONE

**Conclusion**: mcp package successfully provisioned in the launcher environment.

==================================================
3. REPRODUCIBILITY CHECK
==================================================

**pyproject.toml Status**: Does NOT declare mcp in dependencies
**Current Dependencies**: PySide6, pydantic, httpx, Pillow, playwright, keyring, psutil, pyperclip, pywin32
**MCP Declaration**: MISSING

**Reproducibility Debt**: 
- pyproject.toml does not include mcp as a dependency
- This is a reproducibility debt that should be addressed separately
- Current objective (R27) was only to provision the runtime environment

**Conclusion**: Reproducibility debt registered. mcp is not declared in pyproject.toml but is required by the code.

==================================================
4. IMPORT PROBE
==================================================

**Test 1: import mcp**
- Status: SUCCESS
- Module Path: C:\Python\IABV_v1.5_runtime_p020n_venv\Lib\site-packages\mcp\__init__.py
- Package Version: mcp 2.0.0

**Test 2: from mcp.server.fastmcp import FastMCP**
- Status: FAILED
- Error: No module named 'mcp.server.fastmcp'

**Test 3: iabv_v15.infra.mcp.server import**
- Status: FAILED
- Error: cannot import name 'FastMCP' from 'iabv_v15.infra.mcp.server'

**Conclusion**: The installed mcp 2.0.0 package does NOT include the fastmcp module that IABV code expects. This is a version/API mismatch.

==================================================
5. MCP-ONLY STARTUP TEST
==================================================

**Status**: NOT_EXECUTED

**Reason**: Cannot start MCP component because the required FastMCP import fails. The IABV code at line 132 of server.py expects:
```python
from mcp.server.fastmcp import FastMCP
```

But the installed mcp 2.0.0 package does not provide this module.

**Conclusion**: MCP-only startup test cannot proceed due to import failure.

==================================================
6. UI BRIDGE
==================================================

**Status**: NOT_AVAILABLE

**Reason**: MCP server cannot start due to FastMCP import failure, which means UI Bridge functionality remains unavailable.

**Conclusion**: UI Bridge remains unavailable due to MCP server startup failure.

==================================================
7. FAILURE BOUNDARY CLASSIFICATION
================================================##

**Classification**: SOURCE DEFECT

**Detailed Analysis**:
- The IABV source code (iabv_v15/infra/mcp/server.py line 132) expects to import FastMCP from mcp.server.fastmcp
- The installed mcp package (version 2.0.0) does NOT include the fastmcp module
- The mcp.server module exists but does not have a fastmcp submodule
- This is a version mismatch between what the code expects and what the current mcp package provides

**Possible Causes**:
1. The IABV code was written for an older version of mcp that included fastmcp
2. The mcp package API changed between versions, removing fastmcp
3. FastMCP might be in a separate package or namespace in the current version

**Conclusion**: The failure is a SOURCE DEFECT - the IABV code expects an API that does not exist in the installed mcp version.

==================================================
8. P0.20 PRESERVATION
================================================##

**Files Verified**:
- discernment_frame_service.py: EXISTS, NOT_MODIFIED
- diagnostic_test_executor.py: EXISTS, NOT_MODIFIED
- task_outcome_recorder.py: EXISTS, NOT_MODIFIED
- EpistemicHypothesis: NOT_FOUND (not present in this codebase)

**Modifications**: NONE
- No source code modifications made
- No P0.20 components altered
- No governance changes
- No synaptic routing changes

**Conclusion**: P0.20 integrity preserved. No modifications to P0.20 components.

==================================================
9. FINAL REPORT
================================================##

### Runtime Identity
- Python: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe (3.13.2)
- Worktree: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
- HEAD: 4256cee28d1a9712b3637d30f2abc71e015bea22

### Interpreter
- Version: 3.13.2
- Environment: IABV_v1.5_runtime_p020n_venv

### MCP Package Version
- Installed: mcp 2.0.0
- Location: C:\Python\IABV_v1.5_runtime_p020n_venv\Lib\site-packages

### Import Probe
- import mcp: SUCCESS
- from mcp.server.fastmcp import FastMCP: FAILED (module not found)

### MCP Startup
- Status: FAILED
- Reason: FastMCP import failure

### UI Bridge
- Status: NOT_AVAILABLE
- Reason: MCP server cannot start

### Files Modified
- Source code: NONE
- pyproject.toml: NONE
- Configuration: NONE

### P0.20 Integrity
- Status: PRESERVED
- No modifications to P0.20 components

### Reproducibility Debt
- pyproject.toml does not declare mcp dependency
- This should be addressed separately

==================================================
10. FINAL VERDICT
================================================##

**NEW_MCP_RUNTIME_FAILURE**

**Rationale**:
While the mcp package was successfully provisioned (version 2.0.0 installed), the IABV source code expects to import FastMCP from mcp.server.fastmcp (line 132 of server.py), but this module does not exist in the installed mcp version. This is a SOURCE DEFECT - the IABV code is written for an API that is not available in the current mcp package version. The MCP server cannot start, which means the UI Bridge remains unavailable, and the approval checkpoint for codex_installed validation cannot be presented. This is a new runtime failure that emerged after provisioning the dependency, indicating a version/API mismatch between the IABV code expectations and the current mcp package.

==================================================
11. NEXT_SINGLE_ACTION
================================================##

Investigate the correct mcp package version that includes FastMCP (likely an older version) and install that specific version, OR modify the IABV source code to use the current mcp 2.0.0 API (which uses a different server initialization pattern without FastMCP).
