# install_shortcut.ps1
#
# Creates a desktop shortcut for IABV v1.5 with the BURVE icon.
# Called automatically by iabv_bootstrap.ps1 -- no manual execution needed.
# Idempotent: safe to call multiple times (overwrites existing shortcut).

function Install-IABVShortcut {
    param(
        [string]$ScriptDir = $PSScriptRoot,
        [switch]$Quiet
    )

    $iabvRoot = Split-Path -Parent $ScriptDir
    $vbsPath  = Join-Path $ScriptDir 'IABV.vbs'
    $icoPath  = Join-Path $ScriptDir 'iabv.ico'
    $lnkPath  = Join-Path ([Environment]::GetFolderPath('Desktop')) 'IABV v1.5.lnk'

    if (-not (Test-Path $vbsPath)) {
        if (-not $Quiet) { Write-Host "[warn] No encontre $vbsPath -- omitiendo acceso directo." -ForegroundColor Yellow }
        return $false
    }

    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut($lnkPath)
    $shortcut.TargetPath       = 'wscript.exe'
    $shortcut.Arguments        = """$vbsPath"""
    $shortcut.WorkingDirectory = $iabvRoot
    $shortcut.Description      = 'IABV v1.5 - Asistente IA Autonomo'

    if (Test-Path $icoPath) {
        $shortcut.IconLocation = "$icoPath,0"
    }

    $shortcut.Save()

    if (-not $Quiet) {
        Write-Host "[ok]   Acceso directo creado: $lnkPath" -ForegroundColor Green
    }
    return $true
}

# Allow direct invocation for testing, but primary use is via iabv_bootstrap.ps1
if ($MyInvocation.InvocationName -ne '.') {
    Install-IABVShortcut
}
