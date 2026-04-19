# run_mcp_bridge.ps1 -- arranca el MCP server de IABV v1.5 + Cloudflare Tunnel.
#
# Uso tipico:
#   powershell -ExecutionPolicy Bypass -File scripts\run_mcp_bridge.ps1
#
# Variables de entorno reconocidas:
#   IABV_PYTHON           python.exe a usar (default: miniconda3 del AGENTS.md)
#   IABV_WORKSPACE_ROOT   raiz del workspace IABV v1.5
#   IABV_MCP_TRANSPORT    stdio | sse | streamable-http (default: streamable-http)
#   IABV_MCP_BIND_HOST    host local (default: 127.0.0.1)
#   IABV_MCP_BIND_PORT    puerto local (default: 8765)
#   IABV_MCP_NAME         nombre visible del server (default: iabv-v15)
#   CLOUDFLARED_BIN       binario cloudflared.exe (default: cloudflared)
#
# Pre-requisitos:
#   - python con iabv_v15 instalado (pip install -e . en la raiz del repo)
#   - pip install mcp uvicorn
#   - cloudflared instalado: winget install --id Cloudflare.cloudflared
#   - (opcional) 'cloudflared tunnel login' si quieres un subdominio permanente

$ErrorActionPreference = 'Stop'

# Rutas por defecto coherentes con AGENTS.md
$pythonBin = $env:IABV_PYTHON
if (-not $pythonBin) { $pythonBin = 'C:\Users\faber\miniconda3\python.exe' }

$workspaceRoot = $env:IABV_WORKSPACE_ROOT
if (-not $workspaceRoot) { $workspaceRoot = 'C:\Python\IABV_v1.5' }

$transport = $env:IABV_MCP_TRANSPORT
if (-not $transport) { $transport = 'streamable-http' }

$bindHost = $env:IABV_MCP_BIND_HOST
if (-not $bindHost) { $bindHost = '127.0.0.1' }

$bindPort = $env:IABV_MCP_BIND_PORT
if (-not $bindPort) { $bindPort = '8765' }

$serverName = $env:IABV_MCP_NAME
if (-not $serverName) { $serverName = 'iabv-v15' }

$cloudflaredBin = $env:CLOUDFLARED_BIN
if (-not $cloudflaredBin) { $cloudflaredBin = 'cloudflared' }

Write-Host "=== IABV v1.5 MCP Bridge ===" -ForegroundColor Cyan
Write-Host "Python       : $pythonBin"
Write-Host "Workspace    : $workspaceRoot"
Write-Host "Transport    : $transport"
Write-Host "Local bind   : http://${bindHost}:${bindPort}"
Write-Host "Server name  : $serverName"
Write-Host "Cloudflared  : $cloudflaredBin"
Write-Host ""

if (-not (Test-Path $pythonBin)) {
    Write-Error "No encontre Python en '$pythonBin'. Define IABV_PYTHON para sobrescribir."
}
if (-not (Test-Path $workspaceRoot)) {
    Write-Error "No encontre el workspace IABV en '$workspaceRoot'. Define IABV_WORKSPACE_ROOT."
}

$env:PYTHONPATH = "$workspaceRoot\src"
$env:IABV_WORKSPACE_ROOT = $workspaceRoot
$env:IABV_MCP_TRANSPORT = $transport
$env:IABV_MCP_NAME = $serverName
# FastMCP lee FASTMCP_HOST / FASTMCP_PORT para streamable-http / sse
$env:FASTMCP_HOST = $bindHost
$env:FASTMCP_PORT = $bindPort

# Lanza el MCP server en background (una sola ventana para ver logs)
Write-Host "Arrancando MCP server..." -ForegroundColor Yellow
$serverProcess = Start-Process -PassThru -NoNewWindow -FilePath $pythonBin `
    -ArgumentList @('-m', 'iabv_v15.infra.mcp.server') `
    -WorkingDirectory $workspaceRoot

Start-Sleep -Seconds 3
if ($serverProcess.HasExited) {
    Write-Error "El MCP server termino antes de poder abrir tunnel (exit=$($serverProcess.ExitCode)). Revisa los logs arriba."
}

Write-Host ""
Write-Host "MCP server PID: $($serverProcess.Id)"
Write-Host "Abriendo Cloudflare Tunnel sobre http://${bindHost}:${bindPort} ..." -ForegroundColor Yellow

# Cloudflare Tunnel rapido (sin cuenta). Entrega una URL *.trycloudflare.com
# que es persistente mientras cloudflared siga corriendo.
try {
    & $cloudflaredBin tunnel --url "http://${bindHost}:${bindPort}" --no-autoupdate --loglevel info
} finally {
    if (-not $serverProcess.HasExited) {
        Write-Host "Deteniendo MCP server (PID $($serverProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
