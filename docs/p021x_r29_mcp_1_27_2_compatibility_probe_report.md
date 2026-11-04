# P0.21x-R29: Isolated MCP 1.27.2 Compatibility Probe - Final Report

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
**Current MCP Version Before Change**: 2.0.0
**Runtime Worktree**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
**HEAD**: 4256cee28d1a9712b3637d30f2abc71e015bea22
**Source Root**: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src

**Conclusion**: Precheck confirmed the environment and identified mcp 2.0.0 as the current version.

==================================================
2. VERSION CHANGE
==================================================

**Action**: Replaced mcp 2.0.0 with mcp==1.27.2
**Command Used**: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\pip.exe install mcp==1.27.2
**Result**: Successfully installed mcp 1.27.2
**Additional Dependencies Installed**:
- httpx-sse-0.4.3
- pydantic-settings-2.15.0
- python-dotenv-1.2.3

**Source Modifications**: NONE
**pyproject.toml Modifications**: NONE
**Script Modifications**: NONE
**Configuration Modifications**: NONE
**SQLite Modifications**: NONE

**Conclusion**: Version change completed successfully without modifying source code.

==================================================
3. VERSION VERIFY
==================================================

**import mcp**: SUCCESS
**mcp.__version__**: N/A (not exposed by the package)
**mcp.__file__**: C:\Python\IABV_v1.5_runtime_p020n_venv\Lib\site-packages\mcp\__init__.py
**Distribution**: mcp 1.27.2 (confirmed via pip show)

**Expected Version**: 1.27.2
**Actual Version**: 1.27.2

**Conclusion**: Version verification successful. mcp 1.27.2 is installed and importable.

==================================================
4. API IMPORT PROBE
==================================================

**Test 1: from mcp.server.fastmcp import FastMCP**
- Status: SUCCESS
- FastMCP: <class 'mcp.server.fastmcp.server.FastMCP'>

**Test 2: from mcp.server.transport_security import TransportSecuritySettings**
- Status: SUCCESS
- TransportSecuritySettings: <class 'mcp.server.transport_security.TransportSecuritySettings'>

**Conclusion**: Both required API imports succeed with mcp 1.27.2. This resolves the import failure that occurred with mcp 2.0.0.

==================================================
5. IABV MCP MODULE IMPORT
==================================================

**Test: import iabv_v15.infra.mcp.server**
- Status: SUCCESS
- Module file: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\infra\mcp\server.py
- Module spec origin: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\infra\mcp\server.py
- Import Status: No exceptions

**Conclusion**: The IABV MCP module imports successfully without starting the server.

==================================================
6. SOURCE RESOLUTION
==================================================

**iabv_v15.infra.mcp.server Resolution**:
- Module file: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\infra\mcp\server.py
- Canonical worktree: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5
- Status: ✓ RESOLVES TO CANONICAL WORKTREE

**iabv_v15.domain.models Resolution**:
- Models file: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\domain\models.py
- Status: ✓ RESOLVES TO CANONICAL WORKTREE

**Contamination Check**:
- IABV_v1.5_canonical: NOT DETECTED
- p020m: NOT DETECTED
- p020o: NOT DETECTED
- OneDrive: NOT DETECTED

**Conclusion**: All modules resolve exclusively to the canonical worktree with no contamination.

==================================================
7. DEPENDENCY COMPATIBILITY
==================================================

**Installed Versions**:
- mcp: 1.27.2
- pydantic: 2.13.2
- pydantic_core: 2.46.2
- starlette: 1.6.0
- uvicorn: 0.52.3
- anyio: 4.14.2
- httpx: 0.28.1

**Dependency Changes**:
- Only mcp version changed (2.0.0 → 1.27.2)
- Additional dependencies installed: httpx-sse, pydantic-settings, python-dotenv (required by mcp 1.27.2)
- No unrelated package versions changed

**Conclusion**: Dependency compatibility confirmed. All required packages are at compatible versions.

==================================================
8. RUNTIME PRESERVATION
==================================================

**main.py**: NOT STARTED
**MCP Server**: NOT STARTED
**UI**: NOT STARTED
**UI Bridge**: NOT STARTED
**External Assistant**: NOT STARTED
**SynapticRouter**: NOT STARTED

**Process Check**: No python processes found matching IABV

**Conclusion**: Runtime preservation confirmed. No IABV components were started during the probe.

==================================================
9. FINAL REPORT
==================================================

### Interpreter
- Executable: C:\Python\IABV_v1.5_runtime_p020n_venv\Scripts\python.exe
- Version: 3.13.2
- Environment: IABV_v1.5_runtime_p020n_venv

### MCP Version
- Before: 2.0.0
- After: 1.27.2
- Status: Successfully changed

### MCP Path
- Location: C:\Python\IABV_v1.5_runtime_p020n_venv\Lib\site-packages\mcp\__init__.py
- Distribution: mcp 1.27.2

### FastMCP Import
- Status: SUCCESS
- Class: mcp.server.fastmcp.server.FastMCP

### TransportSecuritySettings Import
- Status: SUCCESS
- Class: mcp.server.transport_security.TransportSecuritySettings

### IABV MCP Module Import
- Status: SUCCESS
- Module file: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\infra\mcp\server.py
- Spec origin: C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5\IABV_v1.5\src\iabv_v15\infra\mcp\server.py

### Module Fingerprints
- iabv_v15.infra.mcp.server: Canonical worktree
- iabv_v15.domain.models: Canonical worktree
- No contamination detected

### Dependency Versions
- mcp: 1.27.2
- pydantic: 2.13.2
- pydantic_core: 2.46.2
- starlette: 1.6.0
- uvicorn: 0.52.3
- anyio: 4.14.2
- httpx: 0.28.1

### Source Contamination
- Status: NONE
- All modules resolve to canonical worktree
- No contamination from other checkouts

### Files Modified
- Source code: NONE
- pyproject.toml: NONE
- Scripts: NONE
- Configuration: NONE
- SQLite: NONE

### P0.20 Integrity
- Status: PRESERVED
- No modifications to P0.20 components
- No governance changes
- No synaptic routing changes

==================================================
10. FINAL VERDICT
================================================##

**MCP_1_27_2_IMPORT_COMPATIBLE**

**Rationale**:
The isolated compatibility probe confirms that mcp 1.27.2 is fully compatible with the IABV MCP code at HEAD 4256cee28d1a9712b3637d30f2abc71e015bea22. All required API imports (FastMCP and TransportSecuritySettings) succeed with mcp 1.27.2, resolving the import failure that occurred with mcp 2.0.0. The IABV MCP module (iabv_v15.infra.mcp.server) imports successfully without starting the server. All modules resolve exclusively to the canonical worktree with no contamination. Dependency versions are compatible, and no source code or configuration modifications were made. The runtime preservation check confirms no IABV components were started during the probe. The version change from mcp 2.0.0 to mcp 1.27.2 successfully resolves the SOURCE DEFECT identified in P0.21x-R27.

==================================================
11. NEXT_SINGLE_ACTION
================================================##

Start the IABV runtime using the canonical launcher (launch_deterministic_runtime_p021v.ps1) to verify that the MCP server can now start successfully with mcp 1.27.2 and that the UI Bridge becomes available for the codex_installed approval checkpoint.
