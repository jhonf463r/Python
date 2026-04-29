<#
.SYNOPSIS
    Mide rendimiento post-startup de IABV v1.5 con foco en WorldModelService.

.DESCRIPTION
    Corridas de evidencia para comparar cadencia de WorldModel:
    - Memoria (WorkingSet/PrivateMemory) a 30s, 60s, 120s
    - Tiempo hasta que UI Bridge responde (chat usable)
    - Cantidad de scans de WorldModel en 3 minutos
    - Frescura de foco/ventanas/current_page en snapshots

.PARAMETER RunLabel
    Etiqueta para la corrida (ej: "main_baseline", "pr_45s_cadence")

.EXAMPLE
    .\measure_wm_cadence.ps1 -RunLabel "main_baseline"
    .\measure_wm_cadence.ps1 -RunLabel "pr_45s"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$RunLabel
)

$ErrorActionPreference = 'Stop'
$workspace = 'C:\Python\IABV_v1.5'
$resultsDir = Join-Path $workspace "data\perf_evidence"
$runFile = Join-Path $resultsDir "$RunLabel`_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"

if (-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null }

Write-Host "[measure] Run: $RunLabel"
Write-Host "[measure] Results: $runFile"
Write-Host ""

# --- Helper: get IABV process memory ---
function Get-IABVMemory {
    $procs = Get-Process python -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'iabv_v15' -or $_.MainWindowTitle -match 'IABV' }
    if (-not $procs) {
        # Fallback: all python processes
        $procs = Get-Process python -ErrorAction SilentlyContinue
    }
    $ws = ($procs | Measure-Object WorkingSet64 -Sum).Sum / 1MB
    $pm = ($procs | Measure-Object PrivateMemorySize64 -Sum).Sum / 1MB
    return @{ working_set_mb = [math]::Round($ws, 1); private_memory_mb = [math]::Round($pm, 1); process_count = $procs.Count }
}

# --- Helper: check UI bridge ---
function Test-UIBridge {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/mcp" -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_ui_state","arguments":{}}}' -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

# --- Helper: get world model snapshot via MCP ---
function Get-WorldModelSnapshot {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/mcp" -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_world_model_snapshot","arguments":{}}}' -TimeoutSec 5
        return $resp.result
    } catch {
        return $null
    }
}

# --- Helper: get scan count from logs ---
function Get-ScanCount {
    $logFile = Join-Path $workspace "data\logs\iabv_runtime.log"
    if (Test-Path $logFile) {
        $lines = Get-Content $logFile -Tail 500 | Where-Object { $_ -match 'world_model.*scan' -or $_ -match 'WorldModelService.*_run_scan' }
        return $lines.Count
    }
    # Alternative: check world model evolution dir
    $wmDir = Join-Path $workspace "data\evolution\world_model"
    if (Test-Path $wmDir) {
        $files = Get-ChildItem $wmDir -Filter "*.json" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-4) }
        return $files.Count
    }
    return -1
}

# --- Kill existing processes ---
Write-Host "[measure] Limpiando procesos previos..."
Get-Process python, pythonw, cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# --- Record initial scan count baseline ---
$scanBaseline = Get-ScanCount

# --- Start IABV ---
Write-Host "[measure] Arrancando IABV..."
$startTime = Get-Date
$proc = Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$workspace\scripts\start_iabv.ps1`" -StartUI -Quiet" -PassThru -WindowStyle Minimized

# --- Wait for UI bridge to respond ---
$bridgeReady = $false
$bridgeWaitStart = Get-Date
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (Test-UIBridge) {
        $bridgeReady = $true
        break
    }
}
$bridgeReadyTime = if ($bridgeReady) { ((Get-Date) - $bridgeWaitStart).TotalSeconds } else { -1 }
Write-Host "[measure] Bridge ready: $bridgeReady (${bridgeReadyTime}s)"

# --- Memory snapshots ---
$memorySnapshots = @{}
$freshnessSnapshots = @{}

# 30s mark
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 30) { Start-Sleep -Seconds (30 - $elapsed) }
$memorySnapshots['30s'] = Get-IABVMemory
$wm30 = Get-WorldModelSnapshot
$freshnessSnapshots['30s'] = @{
    has_windows = ($null -ne $wm30 -and $wm30 -match 'windows')
    has_focus   = ($null -ne $wm30 -and $wm30 -match 'focus')
    raw_keys    = if ($wm30) { ($wm30 | ConvertFrom-Json -ErrorAction SilentlyContinue | Get-Member -MemberType NoteProperty).Name -join ',' } else { 'unavailable' }
}
Write-Host "[measure] 30s: WS=$($memorySnapshots['30s'].working_set_mb)MB PM=$($memorySnapshots['30s'].private_memory_mb)MB"

# 60s mark
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 60) { Start-Sleep -Seconds (60 - $elapsed) }
$memorySnapshots['60s'] = Get-IABVMemory
$wm60 = Get-WorldModelSnapshot
$freshnessSnapshots['60s'] = @{
    has_windows = ($null -ne $wm60 -and $wm60 -match 'windows')
    has_focus   = ($null -ne $wm60 -and $wm60 -match 'focus')
    raw_keys    = if ($wm60) { ($wm60 | ConvertFrom-Json -ErrorAction SilentlyContinue | Get-Member -MemberType NoteProperty).Name -join ',' } else { 'unavailable' }
}
Write-Host "[measure] 60s: WS=$($memorySnapshots['60s'].working_set_mb)MB PM=$($memorySnapshots['60s'].private_memory_mb)MB"

# 120s mark
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds (120 - $elapsed) }
$memorySnapshots['120s'] = Get-IABVMemory
$wm120 = Get-WorldModelSnapshot
$freshnessSnapshots['120s'] = @{
    has_windows = ($null -ne $wm120 -and $wm120 -match 'windows')
    has_focus   = ($null -ne $wm120 -and $wm120 -match 'focus')
    raw_keys    = if ($wm120) { ($wm120 | ConvertFrom-Json -ErrorAction SilentlyContinue | Get-Member -MemberType NoteProperty).Name -join ',' } else { 'unavailable' }
}
Write-Host "[measure] 120s: WS=$($memorySnapshots['120s'].working_set_mb)MB PM=$($memorySnapshots['120s'].private_memory_mb)MB"

# Wait until 180s for scan count
$elapsed = ((Get-Date) - $startTime).TotalSeconds
if ($elapsed -lt 180) {
    Write-Host "[measure] Esperando hasta 180s para contar scans..."
    Start-Sleep -Seconds (180 - $elapsed)
}

$scanFinal = Get-ScanCount
$scansDuring3min = $scanFinal - $scanBaseline

Write-Host "[measure] Scans en 3 min: $scansDuring3min"

# --- Build result ---
$result = @{
    label              = $RunLabel
    timestamp          = (Get-Date -Format 'o')
    bridge_ready_s     = [math]::Round($bridgeReadyTime, 1)
    memory             = $memorySnapshots
    freshness          = $freshnessSnapshots
    scans_in_3min      = $scansDuring3min
    scan_baseline      = $scanBaseline
    scan_final         = $scanFinal
    world_model_interval = @{
        note = "Check WorldModelService._DEFAULT_SCAN_INTERVAL in source"
    }
}

$result | ConvertTo-Json -Depth 5 | Set-Content $runFile -Encoding UTF8
Write-Host ""
Write-Host "[measure] Resultado guardado en: $runFile"
Write-Host "[measure] Resumen:"
Write-Host "  Bridge ready: ${bridgeReadyTime}s"
Write-Host "  Memory 30s:  WS=$($memorySnapshots['30s'].working_set_mb)MB PM=$($memorySnapshots['30s'].private_memory_mb)MB"
Write-Host "  Memory 60s:  WS=$($memorySnapshots['60s'].working_set_mb)MB PM=$($memorySnapshots['60s'].private_memory_mb)MB"
Write-Host "  Memory 120s: WS=$($memorySnapshots['120s'].working_set_mb)MB PM=$($memorySnapshots['120s'].private_memory_mb)MB"
Write-Host "  Scans 3min:  $scansDuring3min"
Write-Host ""
Write-Host "[measure] Para comparar corridas:"
Write-Host "  Get-ChildItem '$resultsDir' | ForEach-Object { `$_.Name; Get-Content `$_.FullName | ConvertFrom-Json | Select bridge_ready_s, scans_in_3min }"
