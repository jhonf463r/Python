# install_shortcut.ps1
#
# Creates a desktop shortcut for IABV v1.5 with the BURVE icon
# and offers to pin it to the taskbar.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_shortcut.ps1

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$iabvRoot  = Split-Path -Parent $scriptDir

$vbsPath  = Join-Path $scriptDir 'IABV.vbs'
$icoPath  = Join-Path $scriptDir 'iabv.ico'
$lnkPath  = Join-Path ([Environment]::GetFolderPath('Desktop')) 'IABV v1.5.lnk'

if (-not (Test-Path $vbsPath)) {
    Write-Error "No encontre $vbsPath. Asegurate de estar en el repo correcto."
}

Write-Host '=== IABV v1.5 — Instalando acceso directo ===' -ForegroundColor Cyan

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($lnkPath)
$shortcut.TargetPath       = 'wscript.exe'
$shortcut.Arguments        = """$vbsPath"""
$shortcut.WorkingDirectory = $iabvRoot
$shortcut.Description      = 'IABV v1.5 - Asistente IA Autonomo'

if (Test-Path $icoPath) {
    $shortcut.IconLocation = "$icoPath,0"
    Write-Host "  Icono      : $icoPath" -ForegroundColor Green
} else {
    Write-Host '  Icono      : (no encontrado, usando default)' -ForegroundColor Yellow
}

$shortcut.Save()

Write-Host "  Acceso directo creado: $lnkPath" -ForegroundColor Green
Write-Host ''
Write-Host 'Para anclar a la barra de tareas:' -ForegroundColor Cyan
Write-Host '  Click derecho en el icono del escritorio > "Anclar a la barra de tareas"'
Write-Host ''
Write-Host 'Listo! Doble-click en el icono para iniciar IABV.' -ForegroundColor Green
