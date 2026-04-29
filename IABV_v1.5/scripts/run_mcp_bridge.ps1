# run_mcp_bridge.ps1 -- arranca el MCP server de IABV v1.5 + Cloudflare Tunnel.
#
# Uso tipico:
#   powershell -ExecutionPolicy Bypass -File scripts\run_mcp_bridge.ps1
#
# Variables de entorno reconocidas:
#   IABV_PYTHON                   python.exe a usar (default: miniconda3 del AGENTS.md)
#   IABV_WORKSPACE_ROOT           raiz del workspace IABV v1.5
#   IABV_MCP_TRANSPORT            stdio | sse | streamable-http (default: streamable-http)
#   IABV_MCP_BIND_HOST            host local (default: 127.0.0.1)
#   IABV_MCP_BIND_PORT            puerto local (default: 8000 -- default de FastMCP)
#   IABV_MCP_NAME                 nombre visible del server (default: iabv-v15)
#   IABV_MCP_HTTP_HOST_HEADER     Host header que cloudflared reenvia al origen
#                                 (default: <bindHost>:<bindPort>; poner vacio ""
#                                 para reenviar el Host publico de trycloudflare).
#   CLOUDFLARED_BIN               binario cloudflared.exe (default: cloudflared)
#
# Pre-requisitos:
#   - python con iabv_v15 instalado (pip install -e . en la raiz del repo)
#   - pip install mcp uvicorn
#   - cloudflared instalado: winget install --id Cloudflare.cloudflared
#   - (opcional) 'cloudflared tunnel login' si quieres un subdominio permanente
#
# Troubleshooting:
#   * "Invalid Host header" en uvicorn: FastMCP/starlette rechaza el Host del
#     tunnel publico. Este script le pasa --http-host-header 127.0.0.1:<port>
#     a cloudflared para que el origen siempre reciba Host=127.0.0.1:<port>.
#   * FASTMCP_PORT se setea pero FastMCP puede ignorarlo segun version; por
#     eso el default ahora es 8000 (el mismo que uvicorn usa por default) y
#     el tunnel siempre apunta a <bindHost>:<bindPort>.

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
if (-not $bindPort) { $bindPort = '8000' }

$serverName = $env:IABV_MCP_NAME
if (-not $serverName) { $serverName = 'iabv-v15' }

$cloudflaredBin = $env:CLOUDFLARED_BIN
if (-not $cloudflaredBin) { $cloudflaredBin = 'cloudflared' }

# Host header que cloudflared reenvia al origen. Evita el "Invalid Host header"
# de starlette/FastMCP cuando el tunnel publico usa *.trycloudflare.com.
# Si el usuario exporta la var en blanco, respetamos esa decision (no override).
if ($null -ne $env:IABV_MCP_HTTP_HOST_HEADER) {
    $httpHostHeader = $env:IABV_MCP_HTTP_HOST_HEADER
} else {
    $httpHostHeader = "${bindHost}:${bindPort}"
}

Write-Host "=== IABV v1.5 MCP Bridge ===" -ForegroundColor Cyan
Write-Host "Python       : $pythonBin"
Write-Host "Workspace    : $workspaceRoot"
Write-Host "Transport    : $transport"
Write-Host "Local bind   : http://${bindHost}:${bindPort}"
Write-Host "Server name  : $serverName"
Write-Host "Cloudflared  : $cloudflaredBin"
if ($httpHostHeader) {
    Write-Host "Host header  : $httpHostHeader (rewrite hacia el origen)"
} else {
    Write-Host "Host header  : <passthrough>"
}
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
# El startup_timeline.jsonl audita el arranque visible de la UI. El MCP del
# bridge externo no debe escribir en ese mismo archivo porque rompe el orden de
# fases y falsea la metacognicion de splash -> shell.
$env:IABV_STARTUP_TIMELINE = '0'
# FastMCP lee FASTMCP_HOST / FASTMCP_PORT para streamable-http / sse
$env:FASTMCP_HOST = $bindHost
$env:FASTMCP_PORT = $bindPort

# Inyecta los CLIs portable de iabv_bootstrap.ps1 al PATH del MCP server.
# Sin esto, el proceso python hijo no hereda los directorios que el $PROFILE
# del usuario agrega interactivamente, y LocalCliToolAdapter reporta gh/
# cloudflared/git/winget como 'missing' aun cuando la shell del usuario los ve.
$iabvToolsRoot = $env:IABV_TOOLS_ROOT
if (-not $iabvToolsRoot) { $iabvToolsRoot = Join-Path $HOME '.iabv\tools' }
if (Test-Path $iabvToolsRoot) {
    $iabvPathCandidates = @(
        (Join-Path $iabvToolsRoot 'gh\bin'),
        (Join-Path $iabvToolsRoot 'cloudflared')
    ) | Where-Object { Test-Path $_ }
    if ($iabvPathCandidates) {
        $env:PATH = ($iabvPathCandidates -join ';') + ';' + $env:PATH
        Write-Host ("Tools en PATH: " + ($iabvPathCandidates -join '; ')) -ForegroundColor DarkGray
    }
}

# Lanza el MCP server en background (una sola ventana para ver logs).
# Si IABV_MCP_HOT_RELOAD=1, se envuelve en scripts\mcp_hot_reload.py para que
# se reinicie solo al cambiar archivos en src/iabv_v15/ (util post git pull).
if ($env:IABV_MCP_HOT_RELOAD -eq '1') {
    Write-Host "Arrancando MCP server (hot-reload ON)..." -ForegroundColor Yellow
    $hotReloadScript = Join-Path $workspaceRoot 'scripts\mcp_hot_reload.py'
    $serverProcess = Start-Process -PassThru -NoNewWindow -FilePath $pythonBin `
        -ArgumentList @($hotReloadScript) `
        -WorkingDirectory $workspaceRoot
} else {
    Write-Host "Arrancando MCP server..." -ForegroundColor Yellow
    $serverProcess = Start-Process -PassThru -NoNewWindow -FilePath $pythonBin `
        -ArgumentList @('-m', 'iabv_v15.infra.mcp.server') `
        -WorkingDirectory $workspaceRoot
}

Start-Sleep -Seconds 3
if ($serverProcess.HasExited) {
    Write-Error "El MCP server termino antes de poder abrir tunnel (exit=$($serverProcess.ExitCode)). Revisa los logs arriba."
}

Write-Host ""
Write-Host "MCP server PID: $($serverProcess.Id)"
Write-Host "Abriendo Cloudflare Tunnel sobre http://${bindHost}:${bindPort} ..." -ForegroundColor Yellow

# Cloudflare Tunnel rapido (sin cuenta). Entrega una URL *.trycloudflare.com
# que es persistente mientras cloudflared siga corriendo.
$tunnelArgs = @(
    'tunnel',
    '--url', "http://${bindHost}:${bindPort}",
    '--no-autoupdate',
    '--loglevel', 'info'
)
if ($httpHostHeader) {
    $tunnelArgs += @('--http-host-header', $httpHostHeader)
}

try {
    & $cloudflaredBin @tunnelArgs
} finally {
    if (-not $serverProcess.HasExited) {
        Write-Host "Deteniendo MCP server (PID $($serverProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
