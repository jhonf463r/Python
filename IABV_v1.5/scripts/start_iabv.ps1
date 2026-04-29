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
#   -AutoPull               Corre 'git pull --rebase=false' en el workspace
#                           antes de cualquier otra cosa (default ON). Si hubo
#                           commits nuevos, invoca summarize_updates para
#                           imprimir un resumen humano en espanol de los
#                           cambios. Usa --rebase=false para tolerar ramas
#                           divergentes (e.g. auto-merge local). Si el pull
#                           falla, aborta con mensaje claro (NO fuerza merge).
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

# --- Paths used throughout ---
$iabvRoot   = Split-Path -Parent $PSScriptRoot
$logsDir    = Join-Path (Join-Path $iabvRoot 'data') 'logs'
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

# --- Single-instance guard ---------------------------------------------------
# Prevents zombie processes when the user double-clicks the shortcut rapidly.
# A lock file with a 45-second TTL ensures only one start_iabv.ps1 runs at a time.
$lockFile = Join-Path $logsDir 'iabv_start.lock'
if (Test-Path $lockFile) {
    $lockAge = (Get-Date) - (Get-Item $lockFile).LastWriteTime
    if ($lockAge.TotalSeconds -lt 45) {
        # Another instance is already starting — exit silently
        exit 0
    }
}
Set-Content -Path $lockFile -Value "$PID $(Get-Date -Format o)" -Force
# Clean up the lock when this script exits (normal or error)
trap { Remove-Item -Path $lockFile -Force -ErrorAction SilentlyContinue }
# ---------------------------------------------------------------------------

# --- Console log capture ---------------------------------------------------
# All console output is captured to a log file so the program can self-examine
# its own startup (OSES, auditing, diagnostics). The user never sees the console
# but the program reads this log internally.
$startupLog = Join-Path $logsDir 'startup_console.log'
try {
    Start-Transcript -Path $startupLog -Force | Out-Null
} catch {
    # Transcript already running or not available — continue anyway
}
# ---------------------------------------------------------------------------

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
# Devin mergeo fixes automaticos. Usa --rebase=false para tolerar divergencia
# local (e.g. auto-merge commits). Si falla, abortamos con mensaje claro.
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
        Write-Info "Auto-pull : git pull --rebase=false en $repoRoot"
        $oldSha = (& git -C $repoRoot rev-parse HEAD 2>$null).Trim()
        & git -C $repoRoot pull --rebase=false
        $pullExit = $LASTEXITCODE
        if ($pullExit -ne 0) {
            Write-Err "[auto-pull] git pull --rebase=false fallo (exit $pullExit)."
            Write-Err "  Verifica el estado del repo y corregilo a mano,"
            Write-Err "  o corre con -NoAutoPull si sabes lo que haces."
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

            # Auto-restart detection: if critical files changed, relaunch
            $criticalPatterns = @('bootstrap.py', 'control_center_viewmodel.py',
                                  'adaptive_task_orchestrator.py', 'models.py',
                                  'start_iabv.ps1')
            $changedFiles = @()
            try {
                $changedFiles = (& git -C $repoRoot diff --name-only $oldSha $newSha 2>$null) -split "`n" | Where-Object { $_ }
            } catch {}
            $criticalChanged = $changedFiles | Where-Object {
                $file = $_
                ($criticalPatterns | Where-Object { $file -like "*$_" }).Count -gt 0
            }
            if ($criticalChanged) {
                Write-Warn "[auto-pull] Archivos criticos cambiaron:"
                foreach ($cf in $criticalChanged) { Write-Warn "  - $cf" }
                Write-Warn "[auto-pull] Relanzando el proceso para cargar los cambios..."
                # Re-invoke ourselves with -NoAutoPull to avoid infinite loop
                $relaunchArgs = @('-ExecutionPolicy', 'Bypass', '-File', $MyInvocation.MyCommand.Path)
                if ($StartUI)  { $relaunchArgs += '-StartUI' }
                if ($Quiet)    { $relaunchArgs += '-Quiet' }
                $relaunchArgs += '-NoAutoPull'
                Start-Process powershell.exe -ArgumentList $relaunchArgs -WindowStyle Hidden
                exit 0
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
    $issues += "GITHUB_TOKEN_IABV todavia tiene el placeholder; edita $secretsPath."
}
if (-not $env:DEVIN_API_KEY) {
    $issues += "DEVIN_API_KEY no esta seteado (opcional para github pero necesario para cross-IA)."
} elseif ($env:DEVIN_API_KEY -match 'REEMPLAZAR') {
    $issues += "DEVIN_API_KEY todavia tiene el placeholder; edita $secretsPath."
}

if ($issues.Count -gt 0) {
    Write-Warn "Problemas detectados:"
    foreach ($i in $issues) { Write-Warn "  - $i" }
    Write-Warn "Tip: rotacion asistida sin copy-paste con"
    Write-Warn "     powershell -ExecutionPolicy Bypass -File scripts\rotate_tokens.ps1"
    Write-Warn "Podes arrancar igual (los adapters reportaran 'missing' en run_self_audit)."
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
    # Tell the UI bootstrap NOT to auto-start MCP+tunnel -- this script
    # manages them externally.  Prevents port-8000 conflict (Errno 10048).
    $env:IABV_SKIP_MCP_AUTOSTART = '1'
    # Ensure PYTHONPATH includes src/ so `python -m iabv_v15` resolves correctly.
    # run_mcp_bridge.ps1 sets this for the MCP server, but the UI process needs
    # it too — Start-Process inherits the parent env so we set it here.
    $uiSrcPath = Join-Path $iabvRoot 'src'
    if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$uiSrcPath*") {
        if ($env:PYTHONPATH) {
            $env:PYTHONPATH = "$uiSrcPath;$env:PYTHONPATH"
        } else {
            $env:PYTHONPATH = $uiSrcPath
        }
    }
    $env:IABV_WORKSPACE_ROOT = $iabvRoot
    try {
        $pythonExe = 'python'
        if ($env:IABV_PYTHON) { $pythonExe = $env:IABV_PYTHON }
        # IMPORTANT: DO NOT use Start-Process -WindowStyle Hidden here.
        # -WindowStyle Hidden sets STARTUPINFO.wShowWindow = SW_HIDE which
        # causes Windows to override the FIRST ShowWindow() call for EVERY
        # top-level window in the process with SW_HIDE.  This kills the
        # PySide6/QML window: Qt calls ShowWindow(hwnd, SW_SHOW) but
        # Windows substitutes SW_HIDE from STARTUPINFO, so the HWND exists
        # but is invisible (MainWindowHandle = 0, EnumWindows = 0 visible).
        #
        # Instead we use .NET ProcessStartInfo with CreateNoWindow = $true.
        # CreateNoWindow adds CREATE_NO_WINDOW to the process creation flags
        # which suppresses the console window WITHOUT touching STARTUPINFO
        # .wShowWindow.  Qt windows appear normally.
        #
        # DO NOT add -RedirectStandardOutput/-RedirectStandardError — those
        # flags also prevent PySide6 GUI windows from appearing on Windows.
        $psi = [System.Diagnostics.ProcessStartInfo]::new()
        $psi.FileName = $pythonExe
        $psi.Arguments = '-m iabv_v15 app'
        $psi.WorkingDirectory = $iabvRoot
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $uiProc = [System.Diagnostics.Process]::Start($psi)
        Write-Info "  UI PID     : $($uiProc.Id)"
        Write-Info "  PYTHONPATH : $env:PYTHONPATH"
    } catch {
        Write-Warn "[warn] No se pudo lanzar la UI con -StartUI: $_"
        Write-Warn "       El MCP sigue vivo. Podes lanzar la UI manual con:"
        Write-Warn "         python -m iabv_v15 app"
    }
}

# M7: limpiar directorios pytest-cache-files huerfanos que se acumulan
# en el workspace con el tiempo. Son seguros de borrar.
$iabvWorkspace = Split-Path -Parent $PSScriptRoot
$pytestCacheDirs = Get-ChildItem -Path $iabvWorkspace -Recurse -Directory -Filter 'pytest-cache-files' -ErrorAction SilentlyContinue
if ($pytestCacheDirs) {
    $count = ($pytestCacheDirs | Measure-Object).Count
    foreach ($d in $pytestCacheDirs) {
        Remove-Item -Path $d.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Info "[cleanup] Eliminados $count directorio(s) pytest-cache-files."
} else {
    Write-Info "[cleanup] Sin directorios pytest-cache-files pendientes."
}

Write-Info ""
Write-Info "Libera puerto :$McpPort (kill MCP zombi) ..."
Stop-McpZombies -Port $McpPort

Write-Info ""
Write-Info "Arrancando MCP + Cloudflare tunnel via $bridge ..."
& powershell -ExecutionPolicy Bypass -File $bridge
