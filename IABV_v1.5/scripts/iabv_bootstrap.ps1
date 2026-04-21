# iabv_bootstrap.ps1
#
# Punto de entrada unico "zero-touch" para dejar IABV v1.5 conectado en
# cualquier maquina / cuenta nueva, sin depender de winget, sin pedir
# admin y sin copy-paste manual de tokens.
#
# Que hace (en orden, idempotente):
#   1. Verifica Python y git (si faltan, reporta y aborta limpio).
#   2. Instala GitHub CLI (gh) en modo portable en $HOME\.iabv\tools\gh
#      descargando el ZIP oficial de github.com/cli/cli/releases. No
#      necesita admin ni winget.
#   3. Instala cloudflared portable en $HOME\.iabv\tools\cloudflared\
#      bajando el .exe oficial de github.com/cloudflare/cloudflared.
#   4. Agrega ambos al PATH de la sesion actual y persiste en el $PROFILE.
#   5. Corre scripts\setup_iabv_profile.ps1 (crea ~/.iabv_secrets.ps1
#      desde template + inyecta source-line al $PROFILE).
#   6. Corre scripts\rotate_tokens.ps1 si detecta tokens placeholder o
#      invalidos. Si gh no esta logueado, dispara device-flow (click
#      "Authorize" en el browser = unico paso manual).
#   7. Arranca scripts\start_iabv.ps1 (MCP + tunnel cloudflared) salvo
#      que pases -NoStart.
#
# Flags:
#   -Force           Re-instala gh/cloudflared aunque ya existan.
#   -NoStart         No arranca el MCP al final (solo deja todo listo).
#   -SkipInstalls    Omite instalar gh/cloudflared (asume que ya estan).
#   -PrintTunnelUrl  Al arrancar, intenta capturar la URL trycloudflare
#                    y la imprime al final para compartir con Devin.
#
# Seguridad:
#   - Todos los binarios bajan de dominios oficiales (github.com/cli,
#     github.com/cloudflare/cloudflared). No toca HKLM. No requiere admin.
#   - El PAT de GitHub nunca pasa por stdout ni $clipboard: se guarda en
#     el keyring de `gh` y se lee via `gh auth token` hacia ~/.iabv_secrets.ps1.
#   - La DEVIN_API_KEY usa Read-Host -AsSecureString (input oculto).

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$NoStart,
    [switch]$SkipInstalls,
    [switch]$PrintTunnelUrl
)

$ErrorActionPreference = 'Stop'

function Write-Section($msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}
function Write-Ok($msg)    { Write-Host "[ok]   $msg" -ForegroundColor Green }
function Write-Info($msg)  { Write-Host "[info] $msg" -ForegroundColor Gray }
function Write-Warn2($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-Err2($msg)  { Write-Host "[err]  $msg" -ForegroundColor Red }

$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptDir
$toolsRoot = Join-Path $HOME '.iabv\tools'
$ghDir = Join-Path $toolsRoot 'gh'
$cfDir = Join-Path $toolsRoot 'cloudflared'

# Version fija para reproducibilidad. Subir con PR explicito.
$ghVersion = '2.90.0'
$ghZipName = "gh_${ghVersion}_windows_amd64.zip"
$ghZipUrl = "https://github.com/cli/cli/releases/download/v${ghVersion}/${ghZipName}"
$ghZipSha256 = '73fcae688eb64ae67828536c9be90db1e5be3f11691a6fa1c1e5418fd24ee10b'

$cfUrl = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Invoke-Download {
    param(
        [Parameter(Mandatory)][string]$Url,
        [Parameter(Mandatory)][string]$OutFile,
        [string]$ExpectedSha256
    )
    $outDir = Split-Path -Parent $OutFile
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
    Write-Info "Descargando $Url"
    # TLS 1.2 (default en PS7, explicitu en PS5).
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor [System.Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
    if ($ExpectedSha256) {
        $actual = (Get-FileHash -Path $OutFile -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $ExpectedSha256.ToLower()) {
            Write-Err2 "SHA256 de $OutFile no coincide. Esperado=$ExpectedSha256 Actual=$actual"
            Remove-Item $OutFile -Force -ErrorAction SilentlyContinue
            throw 'SHA256 mismatch'
        }
        Write-Ok "SHA256 OK para $(Split-Path -Leaf $OutFile)"
    }
}

function Install-GhPortable {
    $ghExe = Join-Path $ghDir 'bin\gh.exe'
    if ((Test-Path $ghExe) -and (-not $Force)) {
        Write-Ok "gh ya instalado en $ghExe"
        return $ghExe
    }
    # Limpia version previa si la hay.
    if (Test-Path $ghDir) { Remove-Item -Recurse -Force $ghDir }
    New-Item -ItemType Directory -Force -Path $ghDir | Out-Null

    $zipPath = Join-Path $env:TEMP $ghZipName
    Invoke-Download -Url $ghZipUrl -OutFile $zipPath -ExpectedSha256 $ghZipSha256

    Write-Info "Extrayendo $zipPath -> $ghDir"
    Expand-Archive -Path $zipPath -DestinationPath $ghDir -Force
    Remove-Item $zipPath -Force

    # El zip viene con subdir (ej. gh_2.90.0_windows_amd64/). Movemos el bin\gh.exe al root del ghDir.
    $nested = Get-ChildItem -Path $ghDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'bin\gh.exe') } | Select-Object -First 1
    if ($nested) {
        $innerBin = Join-Path $nested.FullName 'bin'
        $targetBin = Join-Path $ghDir 'bin'
        if (-not (Test-Path $targetBin)) {
            Move-Item -Path $innerBin -Destination $targetBin
        }
        Remove-Item -Recurse -Force $nested.FullName -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path $ghExe)) {
        Write-Err2 "No se encontro gh.exe en $ghExe despues de extraer."
        throw 'gh install failed'
    }
    Write-Ok "gh instalado en $ghExe"
    return $ghExe
}

function Install-CloudflaredPortable {
    $cfExe = Join-Path $cfDir 'cloudflared.exe'
    if ((Test-Path $cfExe) -and (-not $Force)) {
        Write-Ok "cloudflared ya instalado en $cfExe"
        return $cfExe
    }
    if (Test-Path $cfDir) { Remove-Item -Recurse -Force $cfDir }
    New-Item -ItemType Directory -Force -Path $cfDir | Out-Null

    Invoke-Download -Url $cfUrl -OutFile $cfExe
    if (-not (Test-Path $cfExe)) {
        Write-Err2 "No se encontro cloudflared.exe en $cfExe despues de descargar."
        throw 'cloudflared install failed'
    }
    Write-Ok "cloudflared instalado en $cfExe"
    return $cfExe
}

function Add-ToSessionPath([string]$Dir) {
    if (-not (Test-Path $Dir)) { return }
    $parts = $env:Path -split ';'
    if ($parts -notcontains $Dir) {
        $env:Path = "$env:Path;$Dir"
        Write-Info "PATH (sesion) += $Dir"
    }
}

function Add-ToProfilePath([string]$Dir) {
    $profilePath = $PROFILE
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Force -Path $profileDir | Out-Null }
    if (-not (Test-Path $profilePath)) { New-Item -ItemType File -Path $profilePath -Force | Out-Null }

    $marker = "# IABV bootstrap PATH: $Dir"
    $content = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($content -and $content.Contains($marker)) {
        return
    }
    $block = @"

$marker
if ((Test-Path '$Dir') -and ((`$env:Path -split ';') -notcontains '$Dir')) {
    `$env:Path = "`$env:Path;$Dir"
}
"@
    Add-Content -Path $profilePath -Value $block
    Write-Info "PATH persistido en `$PROFILE ($Dir)"
}

# ---------- MAIN ----------
Write-Section 'IABV v1.5 bootstrap'
Write-Info "Repo          : $repoRoot"
Write-Info "Tools root    : $toolsRoot"
Write-Info "Profile target: $PROFILE"

# 1. Sanity: Python + git.
if (-not (Test-Command 'python')) {
    Write-Err2 "python no esta en PATH. Instala Miniconda / Python 3.11+ y volve a correr."
    exit 10
}
if (-not (Test-Command 'git')) {
    Write-Err2 "git no esta en PATH. Instala Git for Windows y volve a correr."
    exit 11
}
Write-Ok "python y git disponibles."

# 2/3. Instala gh + cloudflared portable.
if (-not $SkipInstalls) {
    Write-Section 'Instalando gh (GitHub CLI) portable'
    $ghExe = Install-GhPortable
    Add-ToSessionPath (Split-Path -Parent $ghExe)
    Add-ToProfilePath (Split-Path -Parent $ghExe)

    Write-Section 'Instalando cloudflared portable'
    $cfExe = Install-CloudflaredPortable
    Add-ToSessionPath (Split-Path -Parent $cfExe)
    Add-ToProfilePath (Split-Path -Parent $cfExe)
} else {
    Write-Info 'Skip instalaciones por flag -SkipInstalls.'
}

# 4. Profile + secretos.
Write-Section 'Setup profile + secretos'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir 'setup_iabv_profile.ps1')
if ($LASTEXITCODE -ne 0) {
    Write-Err2 "setup_iabv_profile.ps1 exit=$LASTEXITCODE"
    exit 12
}

# Carga los secretos en la sesion actual (para que rotate_tokens vea lo que ya haya).
$secretsPath = Join-Path $HOME '.iabv_secrets.ps1'
if (Test-Path $secretsPath) { . $secretsPath }

# 5. Rotacion asistida.
Write-Section 'Rotacion de tokens (device-flow + prompt seguro)'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir 'rotate_tokens.ps1')
$rotateExit = $LASTEXITCODE
if ($rotateExit -ne 0) {
    Write-Warn2 "rotate_tokens.ps1 salio con exit=$rotateExit. Revisa mensajes arriba."
    Write-Warn2 "Podes seguir e intentar arrancar igual, pero algun adapter reportara 'missing'."
}

# 6. Start (opcional).
if ($NoStart) {
    Write-Section 'Bootstrap completo (sin arrancar MCP)'
    Write-Info "Para arrancar: scripts\start_iabv.ps1"
    exit 0
}

Write-Section 'Arrancando MCP + tunnel'
if ($PrintTunnelUrl) {
    # start_iabv.ps1 delega a run_mcp_bridge que es interactivo. Para capturar
    # la URL del tunnel hace falta otro diseño (pipe + regex). Dejamos la
    # captura como UNRESOLVED en este PR: por ahora imprimimos una nota.
    Write-Warn2 '-PrintTunnelUrl: captura automatica de URL del tunnel pendiente.'
    Write-Warn2 'Por ahora: la URL aparece en stdout cuando cloudflared imprime'
    Write-Warn2 '  INF Connection registered ... https://<xxx>.trycloudflare.com'
    Write-Warn2 'Copiala y compartila con Devin si queres que audite en vivo.'
}

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir 'start_iabv.ps1')
exit $LASTEXITCODE
