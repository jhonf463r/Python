<#
.SYNOPSIS
    Mide rendimiento post-startup de IABV v1.5 con foco en WorldModelService.

.DESCRIPTION
    Corridas de evidencia para comparar cadencia de WorldModel.
    Consume scan_stats directamente via MCP (world_model_snapshot tool).
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
$mcpUrl = 'http://127.0.0.1:8000/mcp'

if (-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null }

Write-Host ('[measure] Run:       {0}' -f $RunLabel)
Write-Host ('[measure] Workspace: {0}' -f $WorkspaceRoot)
Write-Host ('[measure] Results:   {0}' -f $runFile)
Write-Host ''

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-IABVMemory {
    <# Uses CIM Win32_Process to capture both python.exe AND pythonw.exe
       belonging to the IABV workspace. The UI runs as pythonw.exe, MCP
       helpers as python.exe -- both must be counted. #>
    $wsNorm = $WorkspaceRoot.Replace('\', '\\').TrimEnd('\')
    $cimProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'iabv_v15' -or $_.CommandLine -match [regex]::Escape($wsNorm) }
    if (-not $cimProcs) {
        # Broad fallback: any python/pythonw process
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

function Test-UIBridge {
    try {
        $body = '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_ui_state","arguments":{}}}'
        Invoke-RestMethod -Uri $mcpUrl -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 3 | Out-Null
        return $true
    } catch { return $false }
}

function Get-WorldModelWithStats {
    <# Calls world_model_snapshot MCP tool. Returns parsed object with scan_stats. #>
    try {
        $body = '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"world_model_snapshot","arguments":{"refresh":false}}}'
        $resp = Invoke-RestMethod -Uri $mcpUrl -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5
        $content = $resp.result.content
        if ($content -is [array] -and $content.Count -gt 0) {
            $text = $content[0].text
            if ($text) { return ($text | ConvertFrom-Json) }
        }
        if ($resp.result -is [hashtable] -or $resp.result -is [PSCustomObject]) {
            return $resp.result
        }
        return $null
    } catch { return $null }
}

function Extract-Freshness($wm) {
    <# Extracts P1 freshness evidence from a world model snapshot. #>
    if (-not $wm) { return @{ available = $false; windows_count = 0; has_focus = $false; has_current_page = $false; detected_blocks = @() } }
    $windows = if ($wm.open_windows) { @($wm.open_windows).Count } else { 0 }
    $focus = [bool]($wm.focused_window -and $wm.focused_window -ne '' -and $wm.focused_window -ne 'unknown')
    $page = [bool]($wm.current_page -and $wm.current_page -ne '' -and $wm.current_page -ne 'unknown')
    $blocks = if ($wm.detected_blocks) { @($wm.detected_blocks) } else { @() }
    return @{
        available      = $true
        windows_count  = $windows
        has_focus      = $focus
        has_current_page = $page
        detected_blocks = $blocks
    }
}

function Extract-ScanStats($wm) {
    <# Extracts scan_stats from world model snapshot response. #>
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
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (Test-UIBridge) { $bridgeReady = $true; break }
}
if ($bridgeReady) {
    $bridgeReadyS = [math]::Round(((Get-Date) - $bridgeWaitStart).TotalSeconds, 1)
} else {
    $bridgeReadyS = -1
}
Write-Host ('[measure] Bridge ready: {0} ({1}s)' -f $bridgeReady, $bridgeReadyS)

# --- Snapshot at each mark ---
$snapshots = @{}
foreach ($mark in @(30, 60, 120)) {
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    if ($elapsed -lt $mark) { Start-Sleep -Seconds ($mark - $elapsed) }

    $mem = Get-IABVMemory
    $wm  = Get-WorldModelWithStats
    $fresh = Extract-Freshness $wm
    $stats = Extract-ScanStats $wm

    $key = '{0}s' -f $mark
    $snapshots[$key] = @{
        memory    = $mem
        freshness = $fresh
        scan_stats = $stats
    }
    Write-Host ('[measure] {0}s: WS={1}MB PM={2}MB procs={3} pids={4} scans={5} full={6} windows={7} focus={8}' -f $mark, $mem.working_set_mb, $mem.private_memory_mb, $mem.process_count, ($mem.pids -join ','), $stats.scan_count, $stats.scan_count_full, $fresh.windows_count, $fresh.has_focus)
}

# --- Final scan stats at 180s ---
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 180) {
    Write-Host '[measure] Esperando hasta 180s para conteo final de scans...'
    Start-Sleep -Seconds (180 - $elapsed)
}
$wmFinal = Get-WorldModelWithStats
$statsFinal = Extract-ScanStats $wmFinal
$freshFinal = Extract-Freshness $wmFinal

Write-Host ('[measure] 180s (final): scans={0} full={1} windows={2} focus={3}' -f $statsFinal.scan_count, $statsFinal.scan_count_full, $freshFinal.windows_count, $freshFinal.has_focus)

# --- Build result ---
$result = @{
    label            = $RunLabel
    workspace        = $WorkspaceRoot
    timestamp        = (Get-Date -Format 'o')
    bridge_ready_s   = $bridgeReadyS
    snapshots        = $snapshots
    final_180s       = @{
        scan_stats = $statsFinal
        freshness  = $freshFinal
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
Write-Host ('  Frescura 180s:  windows={0} focus={1} page={2}' -f $freshFinal.windows_count, $freshFinal.has_focus, $freshFinal.has_current_page)
Write-Host ''
Write-Host ('[measure] Resultados en: {0}' -f $resultsDir)
