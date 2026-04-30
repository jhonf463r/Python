<#
.SYNOPSIS
    Mide rendimiento post-startup de IABV v1.5 con foco en WorldModelService.

.DESCRIPTION
    Corridas de evidencia para comparar cadencia de WorldModel.
    Consume scan_stats directamente via MCP (world_model_snapshot tool).
    Usa scripts/mcp_probe.py como cliente real del protocolo MCP
    streamable-http (no hand-rolled JSON-RPC).
    Mide: memoria 30s/60s/120s, bridge ready, scan counters, frescura P1.

.PARAMETER RunLabel
    Etiqueta para la corrida (ej: "main_run1", "pr_45s_run1")

.PARAMETER WorkspaceRoot
    Ruta al workspace IABV. Default: directorio padre del script.

.EXAMPLE
    .\measure_wm_cadence.ps1 -RunLabel "main_run1"
    .\measure_wm_cadence.ps1 -RunLabel "pr_45s_run1" -WorkspaceRoot "D:\worktree\IABV_v1.5"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$RunLabel,

    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$resultsDir = Join-Path $WorkspaceRoot 'data\perf_evidence'
$runTimestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$runFile = Join-Path $resultsDir ('{0}_{1}.json' -f $RunLabel, $runTimestamp)
$probeScript = Join-Path $WorkspaceRoot 'scripts\mcp_probe.py'
$pythonExe = 'python'
if ($env:IABV_PYTHON) { $pythonExe = $env:IABV_PYTHON }

if (-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null }

Write-Host ('[measure] Run:       {0}' -f $RunLabel)
Write-Host ('[measure] Workspace: {0}' -f $WorkspaceRoot)
Write-Host ('[measure] Results:   {0}' -f $runFile)
Write-Host ('[measure] Probe:     {0}' -f $probeScript)
Write-Host ''

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

$script:lastProbeError = ''

function Invoke-MCPTool {
    <# Calls an MCP tool via mcp_probe.py (real streamable-http client).
       Returns parsed PSObject or $null on failure.
       Stores last stderr in $script:lastProbeError for diagnostics. #>
    param(
        [string]$ToolName
    )
    try {
        $srcPath = Join-Path $WorkspaceRoot 'src'
        $env:PYTHONPATH = $srcPath
        $errFile = Join-Path $env:TEMP ('mcp_probe_err_{0}.txt' -f [guid]::NewGuid().ToString('N').Substring(0,8))
        $raw = & $pythonExe $probeScript $ToolName 2>$errFile
        $script:lastProbeError = ''
        if (Test-Path $errFile) {
            $script:lastProbeError = (Get-Content $errFile -Raw -ErrorAction SilentlyContinue)
            Remove-Item $errFile -Force -ErrorAction SilentlyContinue
        }
        if ($LASTEXITCODE -ne 0 -or -not $raw) { return $null }
        $joined = $raw -join "`n"
        return ($joined | ConvertFrom-Json)
    } catch {
        $script:lastProbeError = $_.Exception.Message
        return $null
    }
}

function Test-MCPBridge {
    <# Returns $true if the MCP server responds to ui_bridge_get_state. #>
    $r = Invoke-MCPTool -ToolName 'ui_bridge_get_state'
    return ($null -ne $r)
}

function Get-IABVMemory {
    <# Uses CIM Win32_Process to capture both python.exe AND pythonw.exe
       belonging to the IABV workspace. The UI runs as pythonw.exe, MCP
       helpers as python.exe -- both must be counted. #>
    $wsNorm = $WorkspaceRoot.Replace('\', '\\').TrimEnd('\')
    $cimProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'iabv_v15' -or $_.CommandLine -match [regex]::Escape($wsNorm) }
    if (-not $cimProcs) {
        $cimProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue
    }
    if (-not $cimProcs) {
        return @{ working_set_mb = 0; private_memory_mb = 0; process_count = 0; pids = @() }
    }
    $pids = @($cimProcs | ForEach-Object { $_.ProcessId })
    $procs = $pids | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue } | Where-Object { $_ }
    if (-not $procs) {
        return @{ working_set_mb = 0; private_memory_mb = 0; process_count = 0; pids = @() }
    }
    $ws = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
    $pm = ($procs | Measure-Object PrivateMemorySize64 -Sum).Sum / 1MB
    return @{
        working_set_mb    = [math]::Round($ws, 1)
        private_memory_mb = [math]::Round($pm, 1)
        process_count     = $procs.Count
        pids              = $pids
    }
}

function Get-WorldModelWithStats {
    <# Calls world_model_snapshot via mcp_probe.py (no args needed). #>
    return Invoke-MCPTool -ToolName 'world_model_snapshot'
}

function Extract-WMFreshness($wm) {
    <# Extracts world model freshness from world_model_snapshot.
       Keys: active_windows (list), focused_window (object with .title),
       detected_blocks (list of strings). #>
    if (-not $wm) { return @{ available = $false; active_window_count = 0; has_focus = $false; focused_window = ''; detected_blocks = @() } }
    $winCount = 0
    if ($wm.active_windows) { $winCount = @($wm.active_windows).Count }
    $focusTitle = ''
    if ($wm.focused_window) {
        if ($wm.focused_window.title) { $focusTitle = [string]$wm.focused_window.title }
        elseif ($wm.focused_window -is [string]) { $focusTitle = $wm.focused_window }
    }
    $hasFocus = [bool]($focusTitle -and $focusTitle -ne '' -and $focusTitle -ne 'unknown')
    $blocks = if ($wm.detected_blocks) { @($wm.detected_blocks) } else { @() }
    return @{
        available           = $true
        active_window_count = $winCount
        has_focus           = $hasFocus
        focused_window      = $focusTitle
        detected_blocks     = $blocks
    }
}

function Get-UIBridgeState {
    <# Calls ui_bridge_get_state via mcp_probe.py.
       Returns: current_page, ui_running, etc. #>
    $raw = Invoke-MCPTool -ToolName 'ui_bridge_get_state'
    if (-not $raw) { return @{ available = $false; current_page = 'unknown'; ui_running = $false } }
    $page = 'unknown'
    if ($raw.current_page) { $page = [string]$raw.current_page }
    return @{
        available    = $true
        current_page = $page
        ui_running   = [bool]$raw.ui_running
    }
}

function Extract-ScanStats($wm) {
    if (-not $wm -or -not $wm.scan_stats) {
        return @{ scan_count = -1; scan_count_full = -1; scan_interval_s = -1; full_scan_interval_s = -1; last_scan_ago_s = -1 }
    }
    $s = $wm.scan_stats
    return @{
        scan_count          = [int]($s.scan_count)
        scan_count_full     = [int]($s.scan_count_full)
        scan_interval_s     = $s.scan_interval_s
        full_scan_interval_s = $s.full_scan_interval_s
        last_scan_ago_s     = $s.last_scan_ago_s
    }
}

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

# --- Detached HEAD safety ---
$gitHeadRef = & git -C $WorkspaceRoot rev-parse --abbrev-ref HEAD 2>$null
if ($gitHeadRef -eq 'HEAD') {
    Write-Host '[measure] WARN: workspace is in detached HEAD -- auto-pull would fail'
}

Write-Host '[measure] Limpiando procesos previos...'
Get-Process python, pythonw, cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host '[measure] Arrancando IABV (-NoAutoPull -SkipHealthChecks)...'
$startTime = Get-Date
$startScript = Join-Path $WorkspaceRoot 'scripts\start_iabv.ps1'
$startArgs = '-ExecutionPolicy Bypass -File "{0}" -StartUI -Quiet -NoAutoPull -SkipHealthChecks' -f $startScript
Start-Process powershell -ArgumentList $startArgs -WindowStyle Minimized

# --- Wait for bridge ---
$bridgeReady = $false
$bridgeWaitStart = Get-Date
Write-Host '[measure] Esperando MCP bridge (max 90s)...'
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 1
    if (Test-MCPBridge) { $bridgeReady = $true; break }
    if ($i % 15 -eq 14) {
        Write-Host ('[measure]   ... {0}s elapsed, last error: {1}' -f ($i + 1), $script:lastProbeError)
    }
}
if ($bridgeReady) {
    $bridgeReadyS = [math]::Round(((Get-Date) - $bridgeWaitStart).TotalSeconds, 1)
} else {
    $bridgeReadyS = -1
}
Write-Host ('[measure] Bridge ready: {0} ({1}s)' -f $bridgeReady, $bridgeReadyS)

# --- Smoke check (3 gates) ---
$smokePass = $true

# Gate 1: ui_bridge_get_state != null
$smokeUI = Invoke-MCPTool -ToolName 'ui_bridge_get_state'
if ($null -eq $smokeUI) {
    Write-Host ('[measure] SMOKE GATE 1 FAILED: ui_bridge_get_state returned null -- {0}' -f $script:lastProbeError)
    $smokePass = $false
} else {
    Write-Host '[measure] SMOKE GATE 1 OK: ui_bridge_get_state responded'
}

# Gate 2: world_model_snapshot != null
$smokeWm = Get-WorldModelWithStats
if ($null -eq $smokeWm) {
    Write-Host ('[measure] SMOKE GATE 2 FAILED: world_model_snapshot returned null -- {0}' -f $script:lastProbeError)
    $smokePass = $false
} else {
    Write-Host '[measure] SMOKE GATE 2 OK: world_model_snapshot responded'
}

# Gate 3: scan_stats.scan_count >= 0
$smokeStats = Extract-ScanStats $smokeWm
if ($smokeStats.scan_count -lt 0) {
    Write-Host ('[measure] SMOKE GATE 3 FAILED: scan_count={0} (expected >= 0)' -f $smokeStats.scan_count)
    $smokePass = $false
} else {
    Write-Host ('[measure] SMOKE GATE 3 OK: scan_count={0}' -f $smokeStats.scan_count)
}

if (-not $smokePass) {
    Write-Host '[measure] SMOKE FAILED -- aborting run. Fix probe errors above before retrying.'
    exit 1
}
Write-Host '[measure] SMOKE PASSED -- proceeding with measurement'

# --- Snapshot at each mark ---
$snapshots = @{}
foreach ($mark in @(30, 60, 120)) {
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    if ($elapsed -lt $mark) { Start-Sleep -Seconds ($mark - $elapsed) }

    $mem = Get-IABVMemory
    $wm  = Get-WorldModelWithStats
    $wmFresh = Extract-WMFreshness $wm
    $stats = Extract-ScanStats $wm
    $uiState = Get-UIBridgeState

    $key = '{0}s' -f $mark
    $snapshots[$key] = @{
        memory      = $mem
        wm_freshness = $wmFresh
        scan_stats  = $stats
        ui_state    = $uiState
    }
    Write-Host ('[measure] {0}s: WS={1}MB PM={2}MB procs={3} scans={4} full={5} windows={6} focus={7} page={8}' -f $mark, $mem.working_set_mb, $mem.private_memory_mb, $mem.process_count, $stats.scan_count, $stats.scan_count_full, $wmFresh.active_window_count, $wmFresh.has_focus, $uiState.current_page)
}

# --- Final scan stats at 180s ---
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 180) {
    Write-Host '[measure] Esperando hasta 180s para conteo final de scans...'
    Start-Sleep -Seconds (180 - $elapsed)
}
$wmFinal = Get-WorldModelWithStats
$statsFinal = Extract-ScanStats $wmFinal
$wmFreshFinal = Extract-WMFreshness $wmFinal
$uiStateFinal = Get-UIBridgeState

Write-Host ('[measure] 180s (final): scans={0} full={1} windows={2} focus={3} page={4}' -f $statsFinal.scan_count, $statsFinal.scan_count_full, $wmFreshFinal.active_window_count, $wmFreshFinal.has_focus, $uiStateFinal.current_page)

# --- Build result ---
$result = @{
    label            = $RunLabel
    workspace        = $WorkspaceRoot
    timestamp        = (Get-Date -Format 'o')
    bridge_ready_s   = $bridgeReadyS
    snapshots        = $snapshots
    final_180s       = @{
        scan_stats    = $statsFinal
        wm_freshness  = $wmFreshFinal
        ui_state      = $uiStateFinal
    }
}

$result | ConvertTo-Json -Depth 6 | Set-Content $runFile -Encoding UTF8

Write-Host ''
Write-Host ('[measure] Resultado guardado: {0}' -f $runFile)
Write-Host ''
Write-Host '[measure] === RESUMEN ==='
$mem30  = $snapshots['30s'].memory
$mem60  = $snapshots['60s'].memory
$mem120 = $snapshots['120s'].memory
Write-Host ('  Bridge ready:   {0}s' -f $bridgeReadyS)
Write-Host ('  Memory 30s:     WS={0}MB PM={1}MB' -f $mem30.working_set_mb, $mem30.private_memory_mb)
Write-Host ('  Memory 60s:     WS={0}MB PM={1}MB' -f $mem60.working_set_mb, $mem60.private_memory_mb)
Write-Host ('  Memory 120s:    WS={0}MB PM={1}MB' -f $mem120.working_set_mb, $mem120.private_memory_mb)
Write-Host ('  Scans total:    {0} (full: {1})' -f $statsFinal.scan_count, $statsFinal.scan_count_full)
Write-Host ('  Interval:       {0}s (full: {1}s)' -f $statsFinal.scan_interval_s, $statsFinal.full_scan_interval_s)
Write-Host ('  WM Freshness:   windows={0} focus={1} focused={2}' -f $wmFreshFinal.active_window_count, $wmFreshFinal.has_focus, $wmFreshFinal.focused_window)
Write-Host ('  UI Bridge:      page={0} ui_running={1}' -f $uiStateFinal.current_page, $uiStateFinal.ui_running)
Write-Host ''
Write-Host ('[measure] Resultados en: {0}' -f $resultsDir)
