# _mcp_port_utils.ps1
#
# Utilidad compartida (capa 2.1.1): libera el puerto del MCP matando
# cualquier proceso zombi que haya quedado escuchando de una sesion
# previa. Se importa via dot-source desde los entry points que pueden
# spawnear un MCP nuevo:
#
#   . (Join-Path $PSScriptRoot '_mcp_port_utils.ps1')
#   Stop-McpZombies -Port 8000
#
# El prefijo `_` en el nombre del archivo marca que es privado del
# bundle de scripts; no es un entry point que el usuario corra solo.
#
# Contratos:
#   - Idempotente: si no hay listener, no hace nada y no falla.
#   - Tolerante: si Get-NetTCPConnection no existe en esta edicion de
#     Windows, loggea y sigue (no mata el bootstrap).
#   - No requiere admin si el proceso zombi corre como el mismo user.
#   - No usa $pids (variable automatica en PowerShell); usa $zombiePids.

function Stop-McpZombies {
    param(
        [Parameter(Mandatory)][int]$Port
    )
    $listeners = $null
    try {
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    } catch {
        Write-Host "[info] Get-NetTCPConnection no disponible; omitiendo kill de zombies en :$Port." -ForegroundColor Gray
        return
    }
    if (-not $listeners) {
        Write-Host "[info] Puerto :$Port libre (no hay MCP zombi)." -ForegroundColor Gray
        return
    }
    # Deduplica por PID: varias conexiones pueden apuntar al mismo proceso.
    $zombiePids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($zombiePid in $zombiePids) {
        if (-not $zombiePid -or $zombiePid -le 0) { continue }
        try {
            $proc = Get-Process -Id $zombiePid -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { '<desconocido>' }
            Write-Host "[warn] Matando MCP zombi en :$Port (PID=$zombiePid, name=$name)..." -ForegroundColor Yellow
            Stop-Process -Id $zombiePid -Force -ErrorAction Stop
            Write-Host "[ok]   PID $zombiePid terminado." -ForegroundColor Green
        } catch {
            Write-Host "[warn] No pude matar PID $zombiePid (: ${_}). Continuando." -ForegroundColor Yellow
        }
    }
    # Gracia corta para que Windows libere el socket en TIME_WAIT.
    Start-Sleep -Seconds 2
}
