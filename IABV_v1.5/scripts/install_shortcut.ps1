# install_shortcut.ps1
#
# Creates desktop + Start Menu shortcuts for IABV v1.5 with the BURVE icon.
# Called automatically by iabv_bootstrap.ps1 -- no manual execution needed.
# Idempotent: safe to call multiple times (overwrites existing shortcuts).

function Install-IABVShortcut {
    param(
        [string]$ScriptDir = $PSScriptRoot,
        [switch]$Quiet
    )

    $iabvRoot = Split-Path -Parent $ScriptDir
    $vbsPath  = Join-Path $ScriptDir 'IABV.vbs'
    $icoPath  = Join-Path (Join-Path $iabvRoot 'assets') 'burve.ico'

    # Fallback: legacy icon location
    if (-not (Test-Path $icoPath)) {
        $icoPath = Join-Path $ScriptDir 'iabv.ico'
    }

    $desktopLnk  = Join-Path ([Environment]::GetFolderPath('Desktop')) 'BURVE - IABV v1.5.lnk'
    $startMenuDir = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'
    $startMenuLnk = Join-Path $startMenuDir 'BURVE - IABV v1.5.lnk'

    if (-not (Test-Path $vbsPath)) {
        if (-not $Quiet) { Write-Host "[warn] No encontre $vbsPath -- omitiendo acceso directo." -ForegroundColor Yellow }
        return $false
    }

    # Remove old shortcut name if it exists
    $oldDesktopLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'IABV v1.5.lnk'
    if (Test-Path $oldDesktopLnk) {
        Remove-Item $oldDesktopLnk -Force -ErrorAction SilentlyContinue
        if (-not $Quiet) { Write-Host "[ok]   Acceso directo antiguo removido: $oldDesktopLnk" -ForegroundColor Gray }
    }

    $WshShell = New-Object -ComObject WScript.Shell

    # Desktop shortcut
    $shortcut = $WshShell.CreateShortcut($desktopLnk)
    $shortcut.TargetPath       = 'wscript.exe'
    $shortcut.Arguments        = """$vbsPath"""
    $shortcut.WorkingDirectory = $iabvRoot
    $shortcut.Description      = 'BURVE - IABV v1.5 - Asistente IA Autonomo'
    if (Test-Path $icoPath) {
        $shortcut.IconLocation = "$icoPath,0"
    }
    $shortcut.Save()

    if (-not $Quiet) {
        Write-Host "[ok]   Acceso directo escritorio: $desktopLnk" -ForegroundColor Green
    }

    # Start Menu shortcut
    if (Test-Path $startMenuDir) {
        $startShortcut = $WshShell.CreateShortcut($startMenuLnk)
        $startShortcut.TargetPath       = 'wscript.exe'
        $startShortcut.Arguments        = """$vbsPath"""
        $startShortcut.WorkingDirectory = $iabvRoot
        $startShortcut.Description      = 'BURVE - IABV v1.5 - Asistente IA Autonomo'
        if (Test-Path $icoPath) {
            $startShortcut.IconLocation = "$icoPath,0"
        }
        $startShortcut.Save()

        if (-not $Quiet) {
            Write-Host "[ok]   Acceso directo menu Start: $startMenuLnk" -ForegroundColor Green
        }
    }

    return $true
}

# Allow direct invocation for testing, but primary use is via iabv_bootstrap.ps1
if ($MyInvocation.InvocationName -ne '.') {
    Install-IABVShortcut
}
