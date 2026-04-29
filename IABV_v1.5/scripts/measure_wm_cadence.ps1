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
$resultsDir = Join-Path $WorkspaceRoot "data\perf_evidence"
$runFile = Join-Path $resultsDir "$RunLabel`_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$mcpUrl = 'http://127.0.0.1:8000/mcp'

if (-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null }

Write-Host "[measure] Run:       $RunLabel"
Write-Host "[measure] Workspace: $WorkspaceRoot"
Write-Host "[measure] Results:   $runFile"
Write-Host ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-IABVMemory {
    $procs = Get-Process python -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'iabv_v15' -or $_.MainWindowTitle -match 'IABV' }
    if (-not $procs) { $procs = Get-Process python -ErrorAction SilentlyContinue }
    if (-not $procs) { return @{ working_set_mb = 0; private_memory_mb = 0; process_count = 0 } }
    $ws = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
    $pm = ($procs | Measure-Object PrivateMemorySize64 -Sum).Sum / 1MB
    return @{ working_set_mb = [math]::Round($ws, 1); private_memory_mb = [math]::Round($pm, 1); process_count = $procs.Count }
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

Write-Host "[measure] Limpiando procesos previos..."
Get-Process python, pythonw, cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "[measure] Arrancando IABV..."
$startTime = Get-Date
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$WorkspaceRoot\scripts\start_iabv.ps1`" -StartUI -Quiet" -WindowStyle Minimized

# --- Wait for bridge ---
$bridgeReady = $false
$bridgeWaitStart = Get-Date
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (Test-UIBridge) { $bridgeReady = $true; break }
}
$bridgeReadyS = if ($bridgeReady) { [math]::Round(((Get-Date) - $bridgeWaitStart).TotalSeconds, 1) } else { -1 }
Write-Host "[measure] Bridge ready: $bridgeReady (${bridgeReadyS}s)"

# --- Snapshot at each mark ---
$snapshots = @{}
foreach ($mark in @(30, 60, 120)) {
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    if ($elapsed -lt $mark) { Start-Sleep -Seconds ($mark - $elapsed) }

    $mem = Get-IABVMemory
    $wm  = Get-WorldModelWithStats
    $fresh = Extract-Freshness $wm
    $stats = Extract-ScanStats $wm

    $snapshots["${mark}s"] = @{
        memory    = $mem
        freshness = $fresh
        scan_stats = $stats
    }
    Write-Host "[measure] ${mark}s: WS=$($mem.working_set_mb)MB PM=$($mem.private_memory_mb)MB scans=$($stats.scan_count) full=$($stats.scan_count_full) windows=$($fresh.windows_count) focus=$($fresh.has_focus)"
}

# --- Final scan stats at 180s ---
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 180) {
    Write-Host "[measure] Esperando hasta 180s para conteo final de scans..."
    Start-Sleep -Seconds (180 - $elapsed)
}
$wmFinal = Get-WorldModelWithStats
$statsFinal = Extract-ScanStats $wmFinal
$freshFinal = Extract-Freshness $wmFinal

Write-Host "[measure] 180s (final): scans=$($statsFinal.scan_count) full=$($statsFinal.scan_count_full) windows=$($freshFinal.windows_count) focus=$($freshFinal.has_focus)"

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

Write-Host ""
Write-Host "[measure] Resultado guardado: $runFile"
Write-Host ""
Write-Host "[measure] === RESUMEN ==="
Write-Host "  Bridge ready:   ${bridgeReadyS}s"
Write-Host "  Memory 30s:     WS=$($snapshots['30s'].memory.working_set_mb)MB PM=$($snapshots['30s'].memory.private_memory_mb)MB"
Write-Host "  Memory 60s:     WS=$($snapshots['60s'].memory.working_set_mb)MB PM=$($snapshots['60s'].memory.private_memory_mb)MB"
Write-Host "  Memory 120s:    WS=$($snapshots['120s'].memory.working_set_mb)MB PM=$($snapshots['120s'].memory.private_memory_mb)MB"
Write-Host "  Scans total:    $($statsFinal.scan_count) (full: $($statsFinal.scan_count_full))"
Write-Host "  Interval:       $($statsFinal.scan_interval_s)s (full: $($statsFinal.full_scan_interval_s)s)"
Write-Host "  Frescura 180s:  windows=$($freshFinal.windows_count) focus=$($freshFinal.has_focus) page=$($freshFinal.has_current_page)"
Write-Host ""
Write-Host "[measure] Para comparar:"
Write-Host "  Get-ChildItem '$resultsDir' -Filter '*.json' | ForEach-Object { Write-Host `$_.Name; (Get-Content `$_.FullName | ConvertFrom-Json).snapshots.'120s'.scan_stats }"
