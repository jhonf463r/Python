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
#   -AutoPull               Corre 'git pull --ff-only' en el workspace antes
#                           de cualquier otra cosa (default ON). Si hubo
#                           commits nuevos, invoca summarize_updates para
#                           imprimir un resumen humano en espanol de los
#                           cambios. Si el pull falla o hay divergencia,
#                           aborta con mensaje claro (NO fuerza merge).
#   -NoAutoPull             Desactiva el auto-pull (p.ej. cuando ya lo
#                           corriste a mano o estas en una rama intencional).
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
    [switch]$StartUI,
    [int]$McpPort = 8000,
    [switch]$AutoPull = $true,
    [switch]$NoAutoPull
)

if ($NoAutoPull) {
    $AutoPull = $false
}

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { if (-not $Quiet) { Write-Host $msg -ForegroundColor Cyan } }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Err ($msg) { Write-Host $msg -ForegroundColor Red }

# Capa 2.1.1: libera el puerto del MCP antes de arrancar si quedo un zombi.
# Importamos la utilidad compartida con iabv_bootstrap.ps1.
. (Join-Path $PSScriptRoot '_mcp_port_utils.ps1')

$secretsPath = Join-Path $HOME '.iabv_secrets.ps1'

Write-Info "=== IABV v1.5 start ==="
Write-Info "Secrets : $secretsPath"

# --- Auto pull (default ON) -------------------------------------------------
# Mantiene el workspace sincronizado con origin/main antes de arrancar el MCP,
# para que el usuario no termine corriendo una version vieja despues de que
# Devin mergeo fixes automaticos. Solo fast-forward: si hay divergencia real,
# abortamos en vez de resolver a ciegas.
if ($AutoPull) {
    $repoRoot = $null
    try {
        $repoRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel 2>$null).Trim()
    } catch {
        $repoRoot = $null
    }
    if (-not $repoRoot) {
        Write-Warn "[auto-pull] No pude resolver la raiz del repo git desde $PSScriptRoot; salto pull."
    } else {
        Write-Info "Auto-pull : git pull --ff-only en $repoRoot"
        $oldSha = (& git -C $repoRoot rev-parse HEAD 2>$null).Trim()
        & git -C $repoRoot pull --ff-only
        $pullExit = $LASTEXITCODE
        if ($pullExit -ne 0) {
            Write-Err "[auto-pull] git pull --ff-only fallo (exit $pullExit)."
            Write-Err "  Probablemente hay divergencia local (commits sin pushear o rama reescrita)."
            Write-Err "  Resolvelo a mano o corre con -NoAutoPull si sabes lo que haces."
            exit 1
        }
        $newSha = (& git -C $repoRoot rev-parse HEAD 2>$null).Trim()
        if ($oldSha -and $newSha -and $oldSha -ne $newSha) {
            Write-Info "Cambios   : $oldSha -> $newSha"
            $iabvRoot = Split-Path -Parent $PSScriptRoot
            $srcPath  = Join-Path $iabvRoot 'src'
            $prevPy   = $env:PYTHONPATH
            try {
                if ($env:PYTHONPATH) {
                    $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
                } else {
                    $env:PYTHONPATH = $srcPath
                }
                & python -m iabv_v15.scripts.summarize_updates $oldSha $newSha
                if ($LASTEXITCODE -ne 0) {
                    Write-Warn "[auto-pull] summarize_updates salio con exit $LASTEXITCODE (seguimos igual)."
                }
            } catch {
                Write-Warn "[auto-pull] No pude correr summarize_updates: $_"
            } finally {
                $env:PYTHONPATH = $prevPy
            }
        } else {
            Write-Info "Sin cambios nuevos (HEAD ya estaba actualizado)."
        }
    }
} else {
    Write-Info "Auto-pull : OFF (-NoAutoPull activo)."
}
# ---------------------------------------------------------------------------

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
Write-Info "Libera puerto :$McpPort (kill MCP zombi) ..."
Stop-McpZombies -Port $McpPort

Write-Info ""
Write-Info "Arrancando MCP + Cloudflare tunnel via $bridge ..."
& powershell -ExecutionPolicy Bypass -File $bridge
