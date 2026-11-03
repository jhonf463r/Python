# start_iabv.ps1
#
# Helper de inicio de IABV v1.5:
#   1. Carga secretos desde $HOME\.iabv_secrets.ps1 si existe.
#   2. Corre validaciones rapidas (token shapes, API reachability opcional).
#   3. No inicia MCP ni túneles. La UI puede iniciarse solo con -StartUI.
#
# Goal: el usuario no tiene que recordar 6 comandos distintos ni re-exportar
# tokens cada sesion. Simplemente:
#
#   cd C:\Python\IABV_v1.5
#   powershell -ExecutionPolicy Bypass -File scripts\start_iabv.ps1
#
# Opciones:
#   -SkipHealthChecks       No pega a GitHub/Devin API antes de arrancar.
#   -HotReload              Compatibilidad histórica; no inicia MCP.
#   -Quiet                  Menos output en consola.
#   -StartUI                Lanza ControlCenter
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
# iniciar la UI. El transporte MCP permanece deshabilitado en este wrapper.

<#
.SYNOPSIS
    Ejecuta comprobaciones de inicio; no arranca MCP ni túneles.
.PARAMETER SkipHealthChecks
    Omite los pings HTTP rapidos contra GitHub/Devin API antes de arrancar.
.PARAMETER HotReload
    Parámetro histórico sin efecto; MCP auto-start está deshabilitado.
.PARAMETER Quiet
    Menos output en consola.
.PARAMETER StartUI
    Lanza la ventana ControlCenter (python -m iabv_v15 app) en un proceso aparte.
#>
[CmdletBinding()]
param(
    [switch]$SkipHealthChecks,
    [switch]$HotReload,
    [switch]$Quiet,
    [switch]$StartUI,
    [switch]$AutoPull = $true,
    [switch]$NoAutoPull,
    [switch]$AllowNonMain
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

function Show-StaleRuntimePopup($msg) {
    try {
        $ws = New-Object -ComObject WScript.Shell
        [void]$ws.Popup($msg, 0, 'IABV runtime desactualizado', 48)
    } catch {
        # Console may be hidden; logging still captures the warning.
    }
}

$secretsPath = Join-Path $HOME '.iabv_secrets.ps1'

Write-Info "=== IABV v1.5 start ==="
Write-Info "Secrets : $secretsPath"

# Runtime hygiene: the repo currently tracks historical __pycache__ files.
# Writing bytecode during normal UI startup dirties the worktree, pollutes
# runtime_build_fingerprint, and adds avoidable IO on low-disk systems.
$env:PYTHONDONTWRITEBYTECODE = '1'

# --- Auto pull (default ON) -------------------------------------------------
# Mantiene el workspace sincronizado con origin/main antes de arrancar la UI,
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
        try {
            & git -C $repoRoot fetch origin main | Out-Null
        } catch {
            Write-Warn "[auto-pull] No pude hacer fetch origin main: $_"
        }
        $currentBranch = (& git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null).Trim()
        $currentHead = (& git -C $repoRoot rev-parse HEAD 2>$null).Trim()
        $originMainHead = (& git -C $repoRoot rev-parse origin/main 2>$null).Trim()
        $allowNonMainRuntime = $AllowNonMain -or ($env:IABV_ALLOW_NON_MAIN_RUNTIME -eq '1')
        if (
            -not $allowNonMainRuntime -and
            $currentBranch -and
            $currentBranch -ne 'main' -and
            $originMainHead -and
            $currentHead -and
            $originMainHead -ne $currentHead
        ) {
            $shortCurrent = if ($currentHead.Length -ge 8) { $currentHead.Substring(0, 8) } else { $currentHead }
            $shortMain = if ($originMainHead.Length -ge 8) { $originMainHead.Substring(0, 8) } else { $originMainHead }
            $msg = @"
IABV no se inicio porque el acceso directo apunta a una rama vieja.

Rama actual: $currentBranch ($shortCurrent)
main actual : $shortMain

Esto puede dejar activos bugs ya corregidos, incluyendo congelamientos y falta de runtime_build_fingerprint.
Arranca desde main o ejecuta con -AllowNonMain solo si estas probando una rama a proposito.
"@
            Write-Err "[runtime-guard] $msg"
            Show-StaleRuntimePopup $msg
            exit 1
        }
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
    Write-Warn "       Seguimos igual; las integraciones que requieran esos valores no estarán disponibles."
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
    Write-Info "Hot-reload MCP ignorado: el auto-start del transporte está deshabilitado."
}

# --- P0.71: UI Presence Contract + Single UI Instance Sovereignty ----------
# When -StartUI is requested, a prior bridge status is NOT sufficient.
# Verify that a real UI process is alive and that its UI bridge port belongs
# to it; this check does not start MCP or a tunnel.
# Traces emitted: ui_presence_check_started, ui_presence_check_result,
#   ui_launch_started, ui_launch_result, ui_launch_skipped_existing_ui,
#   ui_launch_failed, ui_duplicate_prevented, ui_bridge_port_conflict,
#   ui_bridge_owner_verified.

function Write-StartupTrace($kind, $data) {
    $ts = (Get-Date -Format 'o')
    $entry = @{ kind = $kind; ts = $ts; data = $data } | ConvertTo-Json -Compress
    $traceFile = Join-Path $logsDir 'startup_ui_presence.jsonl'
    try { Add-Content -Path $traceFile -Value $entry -Encoding utf8 } catch {}
}

function Find-ExistingUIProcess {
    # Returns the first matching python iabv_v15 app process (not this PID).
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'python3.exe'" -ErrorAction SilentlyContinue
        foreach ($p in $procs) {
            if ($p.ProcessId -eq $PID) { continue }
            $cmdLine = $p.CommandLine
            if ($cmdLine -and $cmdLine -match 'iabv_v15.*app') {
                return [PSCustomObject]@{
                    Pid       = $p.ProcessId
                    CmdLine   = $cmdLine
                }
            }
        }
    } catch {}
    return $null
}

function Test-BridgePortOwner($port, $expectedPid) {
    # Checks if the given port is owned by the expected PID.
    try {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $conn) { return @{ owned = $false; reason = 'no_listener' } }
        if ($conn.OwningProcess -eq $expectedPid) {
            return @{ owned = $true; actual_pid = $conn.OwningProcess }
        }
        return @{ owned = $false; reason = 'wrong_owner'; actual_pid = $conn.OwningProcess; expected_pid = $expectedPid }
    } catch {
        return @{ owned = $false; reason = "probe_error: $_" }
    }
}

function Focus-ExistingUIWindow($pid) {
    try {
        if (-not ("IABVWin32Focus" -as [type])) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class IABVWin32Focus {
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
}
"@
        }
        $proc = Get-Process -Id $pid -ErrorAction Stop
        $hwnd = $proc.MainWindowHandle
        if (-not $hwnd -or $hwnd -eq 0) {
            return @{ success = $false; reason = 'no_main_window_handle' }
        }
        $SW_RESTORE = 9
        $SWP_NOMOVE = 0x0002
        $SWP_NOSIZE = 0x0001
        $SWP_SHOWWINDOW = 0x0040
        $HWND_TOPMOST = [IntPtr](-1)
        $HWND_NOTOPMOST = [IntPtr](-2)
        [void][IABVWin32Focus]::ShowWindowAsync($hwnd, $SW_RESTORE)
        Start-Sleep -Milliseconds 150
        [void][IABVWin32Focus]::SetWindowPos($hwnd, $HWND_TOPMOST, 0, 0, 0, 0, ($SWP_NOMOVE -bor $SWP_NOSIZE -bor $SWP_SHOWWINDOW))
        Start-Sleep -Milliseconds 150
        [void][IABVWin32Focus]::SetForegroundWindow($hwnd)
        Start-Sleep -Milliseconds 150
        [void][IABVWin32Focus]::SetWindowPos($hwnd, $HWND_NOTOPMOST, 0, 0, 0, 0, ($SWP_NOMOVE -bor $SWP_NOSIZE -bor $SWP_SHOWWINDOW))
        return @{ success = $true; reason = 'focused'; hwnd = $hwnd }
    } catch {
        return @{ success = $false; reason = "focus_error: $_" }
    }
}

if ($StartUI) {
    Write-Info ""
    Write-StartupTrace 'ui_presence_check_started' @{ requested_by = 'start_iabv.ps1'; bridge_port = 18921 }

    # --- B. Single UI Instance Sovereignty ---
    $existingUI = Find-ExistingUIProcess
    if ($existingUI) {
        # UI already running — verify its bridge ownership and focus it.
        Write-StartupTrace 'startup_existing_instance_detected' @{
            existing_pid = $existingUI.Pid
        }
        $focusResult = Focus-ExistingUIWindow -pid $existingUI.Pid
        Write-StartupTrace 'startup_existing_instance_focus_attempted' @{
            existing_pid = $existingUI.Pid
            success      = [bool]$focusResult.success
            reason       = [string]$focusResult.reason
        }
        $bridgeOwner = Test-BridgePortOwner -port 18921 -expectedPid $existingUI.Pid
        if ($bridgeOwner.owned) {
            Write-Info "  UI ya corriendo (PID $($existingUI.Pid)), bridge verificado."
            Write-StartupTrace 'ui_launch_skipped_existing_ui' @{
                existing_pid = $existingUI.Pid
                bridge_owner_verified = $true
                focus_success = [bool]$focusResult.success
            }
            Write-StartupTrace 'ui_bridge_owner_verified' @{ pid = $existingUI.Pid; port = 18921 }
            Write-StartupTrace 'ui_presence_check_result' @{
                ui_alive = $true; action = 'focused_existing'; pid = $existingUI.Pid; focus_success = [bool]$focusResult.success
            }
        } elseif ($bridgeOwner.reason -eq 'wrong_owner') {
            Write-Warn "  Bridge port 18921 owned by PID $($bridgeOwner.actual_pid), not UI PID $($existingUI.Pid)."
            Write-StartupTrace 'ui_bridge_port_conflict' @{
                expected_pid = $existingUI.Pid
                actual_pid   = $bridgeOwner.actual_pid
            }
            Write-StartupTrace 'ui_presence_check_result' @{
                ui_alive = $true; action = 'conflict_detected'; bridge_conflict = $true
            }
        } else {
            Write-Info "  UI corriendo (PID $($existingUI.Pid)) pero bridge no activo aun."
            Write-StartupTrace 'ui_presence_check_result' @{
                ui_alive = $true; action = 'skipped_existing'; bridge_status = $bridgeOwner.reason
            }
        }
        Write-StartupTrace 'ui_duplicate_prevented' @{ existing_pid = $existingUI.Pid }
    } else {
        # No UI running — launch it.
        Write-Info "Lanzando ControlCenter UI (python -m iabv_v15 app) en proceso aparte..."
        Write-StartupTrace 'ui_launch_started' @{ bridge_port = 18921 }

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
            # CreateNoWindow suppresses the console without touching wShowWindow.
            $psi = [System.Diagnostics.ProcessStartInfo]::new()
            $psi.FileName = $pythonExe
            $psi.Arguments = '-m iabv_v15 app'
            $psi.WorkingDirectory = $iabvRoot
            $psi.UseShellExecute = $false
            $psi.CreateNoWindow = $true
            # Make the UI import the workspace that launched it, even when
            # Python has an editable install pointing at an older IABV clone.
            $psi.EnvironmentVariables['PYTHONPATH'] = $env:PYTHONPATH
            $psi.EnvironmentVariables['IABV_WORKSPACE_ROOT'] = $iabvRoot
            $uiProc = [System.Diagnostics.Process]::Start($psi)
            Write-Info "  UI PID     : $($uiProc.Id)"
            Write-Info "  PYTHONPATH : $env:PYTHONPATH"
            Write-StartupTrace 'ui_launch_result' @{
                success = $true; pid = $uiProc.Id; bridge_port = 18921
            }
        } catch {
            Write-Warn "[warn] No se pudo lanzar la UI con -StartUI: $_"
            Write-Warn "       Podes lanzar la UI manual con:"
            Write-Warn "         python -m iabv_v15 app"
            Write-StartupTrace 'ui_launch_failed' @{ error = "$_" }
        }
        Write-StartupTrace 'ui_presence_check_result' @{
            ui_alive = $false; action = 'launched_new'
        }
    }
}
# ---------------------------------------------------------------------------

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
Write-Info "MCP/tunnel auto-start deshabilitado por seguridad; no se inició ningún transporte."
Write-Info "El servidor stdio requiere un cliente local explícito y no forma parte del arranque de la UI."
