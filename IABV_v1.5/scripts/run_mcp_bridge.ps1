$ErrorActionPreference = 'Stop'

# Local-only MCP launcher. Public tunnels are intentionally not started by this script.
$pythonBin = $env:IABV_PYTHON
if (-not $pythonBin) { $pythonBin = 'C:\Users\faber\miniconda3\python.exe' }

$workspaceRoot = $env:IABV_WORKSPACE_ROOT
if (-not $workspaceRoot) { $workspaceRoot = 'C:\Python\IABV_v1.5' }

$transport = $env:IABV_MCP_TRANSPORT
if (-not $transport) { $transport = 'streamable-http' }
$bindHost = $env:IABV_MCP_BIND_HOST
if (-not $bindHost) { $bindHost = '127.0.0.1' }
$bindPort = $env:IABV_MCP_BIND_PORT
if (-not $bindPort) { $bindPort = '8000' }

if (-not (Test-Path $pythonBin)) { throw "No encuentro Python en '$pythonBin'. Define IABV_PYTHON." }
if (-not (Test-Path $workspaceRoot)) { throw "No encuentro el workspace '$workspaceRoot'. Define IABV_WORKSPACE_ROOT." }
if ($transport -ne 'streamable-http') { throw 'Fail-closed: sólo se permite streamable-http autenticado; stdio/SSE no están habilitados.' }
if ($bindHost -ne '127.0.0.1' -or $bindPort -ne '8000') { throw 'Fail-closed: el MCP debe enlazar exclusivamente 127.0.0.1:8000.' }

$env:PYTHONPATH = "$workspaceRoot\src"
$env:IABV_WORKSPACE_ROOT = $workspaceRoot
$env:IABV_MCP_TRANSPORT = $transport
$env:IABV_MCP_NAME = 'iabv-v15'
$env:IABV_STARTUP_TIMELINE = '0'
$env:FASTMCP_HOST = '127.0.0.1'
$env:FASTMCP_PORT = '8000'

Write-Host '=== IABV v1.5 MCP Bridge (local-only) ===' -ForegroundColor Cyan
Write-Host "Python     : $pythonBin"
Write-Host "Workspace  : $workspaceRoot"
Write-Host 'Transport  : streamable-http'
Write-Host 'Local bind : http://127.0.0.1:8000'
Write-Host 'Public tunnel: DISABLED'
Write-Host 'The server exits before listening unless the complete Entra auth configuration is valid.' -ForegroundColor Yellow

& $pythonBin -m iabv_v15.infra.mcp.server
exit $LASTEXITCODE
