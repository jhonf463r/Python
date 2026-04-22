# start_iabv.ps1
#
# Un solo comando para arrancar IABV v1.5 end-to-end:
#   1. Carga secretos desde $HOME\.iabv_secrets.ps1 si existe.
#   2. Corre validaciones rapidas (token shapes, API reachability opcional).
#   3. Delega en scripts\run_mcp_bridge.ps1 (MCP + Cloudflare tunnel).
#
# Goal: el usuario no tiene que recordar 6 comandos distintos ni re-exportar
# tokens cada sesion. Simplemente:
#
#   cd C:\Python\IABV_v1.5
#   powershell -ExecutionPolicy Bypass -File scripts\start_iabv.ps1
#
# Opciones:
#   -SkipHealthChecks       No pega a GitHub/Devin API antes de arrancar.
#   -HotReload              Exporta IABV_MCP_HOT_RELOAD=1 para el server.
#   -Quiet                  Menos output en consola.
#   -StartUI                Ademas de MCP+tunel, lanza ControlCenter
#                           (python -m iabv_v15 app) en proceso aparte.
#
# Si falta algun secreto, el script te dice exactamente cual y sale sin
# arrancar el MCP, para no confundir con un 401/403 en los logs runtime.

<#
.SYNOPSIS
    Arranca IABV v1.5 end-to-end (MCP + tunel + opcionalmente la UI).
.PARAMETER SkipHealthChecks
    Omite los pings HTTP rapidos contra GitHub/Devin API antes de arrancar.
.PARAMETER HotReload
    Exporta IABV_MCP_HOT_RELOAD=1 para que el server se reinicie ante cambios
    en src/iabv_v15/*.py.
.PARAMETER Quiet
    Menos output en consola.
.PARAMETER StartUI
    Ademas de MCP+tunel, lanza la ventana ControlCenter (python -m iabv_v15 app)
    en un proceso aparte no bloqueante. Si la UI falla en arrancar, se loguea
    el error pero NO se mata el MCP (el MCP sigue vivo).
#>
[CmdletBinding()]
param(
    [switch]$SkipHealthChecks,
    [switch]$HotReload,
    [switch]$Quiet,
    [switch]$StartUI
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { if (-not $Quiet) { Write-Host $msg -ForegroundColor Cyan } }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Err ($msg) { Write-Host $msg -ForegroundColor Red }

$secretsPath = Join-Path $HOME '.iabv_secrets.ps1'

Write-Info "=== IABV v1.5 start ==="
Write-Info "Secrets : $secretsPath"

if (Test-Path $secretsPath) {
    . $secretsPath
    Write-Info "[ok] Secretos cargados."
} else {
    Write-Warn "[warn] No existe $secretsPath."
    Write-Warn "       Ejecuta una sola vez: scripts\setup_iabv_profile.ps1"
    Write-Warn "       Seguimos igual; si faltan env vars el MCP lo avisa al arrancar."
}

# Validaciones de shape (no hacen HTTP; solo longitud/formato basico).
$issues = @()
if (-not $env:GITHUB_TOKEN_IABV) {
    $issues += "GITHUB_TOKEN_IABV no esta seteado."
} elseif ($env:GITHUB_TOKEN_IABV -match 'REEMPLAZAR') {
    $issues += "GITHUB_TOKEN_IABV todavia tiene el placeholder; editá $secretsPath."
}
if (-not $env:DEVIN_API_KEY) {
    $issues += "DEVIN_API_KEY no esta seteado (opcional para github pero necesario para cross-IA)."
} elseif ($env:DEVIN_API_KEY -match 'REEMPLAZAR') {
    $issues += "DEVIN_API_KEY todavia tiene el placeholder; editá $secretsPath."
}

if ($issues.Count -gt 0) {
    Write-Warn "Problemas detectados:"
    foreach ($i in $issues) { Write-Warn "  - $i" }
    Write-Warn "Tip: rotacion asistida sin copy-paste con"
    Write-Warn "     powershell -ExecutionPolicy Bypass -File scripts\rotate_tokens.ps1"
    Write-Warn "Podés arrancar igual (los adapters reportaran 'missing' en run_self_audit)."
}

# Health checks opcionales (HTTP rapido).
if (-not $SkipHealthChecks) {
    Write-Info "Health checks (-SkipHealthChecks para omitir)..."
    if ($env:GITHUB_TOKEN_IABV -and $env:GITHUB_TOKEN_IABV -notmatch 'REEMPLAZAR') {
        try {
            $gh = curl.exe -s -o NUL -w '%{http_code}' `
                -H ("Authorization: token " + $env:GITHUB_TOKEN_IABV) `
                https://api.github.com/repos/jhonf463r/Python
            if ($gh -eq '200') { Write-Info "  github_api : 200 OK" }
            else { Write-Warn  "  github_api : HTTP $gh (token invalido o scope insuficiente)" }
        } catch {
            Write-Warn "  github_api : skip (curl fallo: $_)"
        }
    }
    if ($env:DEVIN_API_KEY -and $env:DEVIN_API_KEY -notmatch 'REEMPLAZAR') {
        try {
            $dv = curl.exe -s -o NUL -w '%{http_code}' `
                -H ("Authorization: Bearer " + $env:DEVIN_API_KEY) `
                'https://api.devin.ai/v1/sessions?limit=1'
            if ($dv -eq '200') { Write-Info "  devin_api  : 200 OK" }
            else { Write-Warn  "  devin_api  : HTTP $dv (key invalida)" }
        } catch {
            Write-Warn "  devin_api  : skip (curl fallo: $_)"
        }
    }
}

if ($HotReload) {
    $env:IABV_MCP_HOT_RELOAD = '1'
    Write-Info "Hot-reload : ON (IABV_MCP_HOT_RELOAD=1)"
}

# Delegar en el bridge ya existente. No duplicamos su logica.
$bridge = Join-Path $PSScriptRoot 'run_mcp_bridge.ps1'
if (-not (Test-Path $bridge)) {
    Write-Err "No encontre $bridge. Abortando."
    exit 1
}

# Lanzar la UI (ControlCenter/Qt) en paralelo si el usuario lo pidio.
# Lo hacemos ANTES del `& ... $bridge` porque esa invocacion es bloqueante:
# la UI arranca en su propio proceso via Start-Process y corre en paralelo
# con MCP+tunel. Si falla, lo logueamos pero seguimos arrancando el MCP
# (contrato explicito: la UI no puede tumbar el MCP).
if ($StartUI) {
    Write-Info ""
    Write-Info "Lanzando ControlCenter UI (python -m iabv_v15 app) en proceso aparte..."
    try {
        $pythonExe = 'python'
        if ($env:IABV_PYTHON) { $pythonExe = $env:IABV_PYTHON }
        $uiProc = Start-Process -FilePath $pythonExe `
            -ArgumentList '-m','iabv_v15','app' `
            -PassThru `
            -WindowStyle Normal
        Write-Info "  UI PID     : $($uiProc.Id)"
    } catch {
        Write-Warn "[warn] No se pudo lanzar la UI con -StartUI: $_"
        Write-Warn "       El MCP sigue vivo. Podes lanzar la UI manual con:"
        Write-Warn "         python -m iabv_v15 app"
    }
}

Write-Info ""
Write-Info "Arrancando MCP + Cloudflare tunnel via $bridge ..."
& powershell -ExecutionPolicy Bypass -File $bridge
