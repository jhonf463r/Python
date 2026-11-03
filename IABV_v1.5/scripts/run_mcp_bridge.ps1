# run_mcp_bridge.ps1 -- inicia el MCP server local por stdio.
#
# Este launcher no inicia HTTP, SSE, cloudflared ni otro túnel. Los transportes
# de red permanecen deshabilitados hasta que autenticación de transporte y
# autorización independiente por operación estén implementadas y verificadas.

$ErrorActionPreference = 'Stop'

$pythonBin = $env:IABV_PYTHON
if (-not $pythonBin) { $pythonBin = 'C:\Users\faber\miniconda3\python.exe' }

$workspaceRoot = $env:IABV_WORKSPACE_ROOT
if (-not $workspaceRoot) { $workspaceRoot = Split-Path -Parent $PSScriptRoot }

$transport = $env:IABV_MCP_TRANSPORT
if (-not $transport) { $transport = 'stdio' }
if ($transport -ne 'stdio') {
    throw "Transporte '$transport' deshabilitado: este launcher solo admite stdio local."
}

$serverName = $env:IABV_MCP_NAME
if (-not $serverName) { $serverName = 'iabv-v15' }

if (-not (Test-Path -LiteralPath $pythonBin -PathType Leaf)) {
    throw "No se encontró Python en '$pythonBin'. Define IABV_PYTHON para sobrescribir."
}
if (-not (Test-Path -LiteralPath $workspaceRoot -PathType Container)) {
    throw "No se encontró el workspace IABV en '$workspaceRoot'. Define IABV_WORKSPACE_ROOT."
}

$env:PYTHONPATH = Join-Path $workspaceRoot 'src'
$env:IABV_WORKSPACE_ROOT = $workspaceRoot
$env:IABV_MCP_TRANSPORT = 'stdio'
$env:IABV_MCP_PROFILE = 'local_restricted'
$env:IABV_MCP_NAME = $serverName
$env:IABV_STARTUP_TIMELINE = '0'

Push-Location -LiteralPath $workspaceRoot
try {
    & $pythonBin -m iabv_v15.infra.mcp.server
    if ($LASTEXITCODE -ne 0) {
        throw "MCP stdio server exited with code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
