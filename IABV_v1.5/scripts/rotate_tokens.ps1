# rotate_tokens.ps1
#
# Rotacion asistida de secretos locales IABV sin copy-paste manual del token.
#
# Que hace:
#   1. Verifica que GitHub CLI (`gh`) este instalado. Si no, te da el comando
#      exacto para instalarlo via winget (no lo instala sin tu permiso).
#   2. Si no estas logueado en `gh`, dispara device-flow: abre el navegador,
#      te muestra un codigo corto de 8 chars (p.ej. ABCD-1234), lo pegas en
#      la pagina y listo. GitHub emite un PAT scope=repo automaticamente.
#      El token se guarda en el store seguro de `gh`; NO lo copiamos al
#      portapapeles ni lo imprimimos por pantalla.
#   3. Lee el token con `gh auth token` y actualiza
#      $HOME\.iabv_secrets.ps1 reemplazando la linea de GITHUB_TOKEN_IABV.
#      El archivo se crea desde template si no existe.
#   4. Para Devin API key: si la que esta en el archivo responde 200 OK
#      se queda como esta. Si falla o no existe, te pide pegarla en un
#      campo oculto (Read-Host -AsSecureString). No queda en el historial
#      de PowerShell. Link directo: https://app.devin.ai/settings/api-keys
#   5. Valida con curl que ambos tokens respondan 200 OK antes de salir.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\rotate_tokens.ps1
#
# Flags:
#   -ForceGitHub   fuerza re-login en gh aun si ya estabas autenticado.
#   -ForceDevin    fuerza rotacion de la Devin API key aun si la actual anda.
#   -SkipGitHub    no toca GitHub (util si solo queres rotar Devin).
#   -SkipDevin     no toca Devin (util si solo queres rotar GitHub).

[CmdletBinding()]
param(
    [switch]$ForceGitHub,
    [switch]$ForceDevin,
    [switch]$SkipGitHub,
    [switch]$SkipDevin
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
$templatePath = Join-Path $scriptDir 'iabv_secrets.template.ps1'
$secretsPath = Join-Path $HOME '.iabv_secrets.ps1'

if (-not (Test-Path $templatePath)) {
    Write-Err2 "No encontre el template en $templatePath."
    Write-Err2 "Correr desde la raiz del repo IABV (C:\Python\IABV_v1.5)."
    exit 1
}

# Asegura que el archivo de secretos exista; si no, lo crea desde template.
if (-not (Test-Path $secretsPath)) {
    Copy-Item $templatePath $secretsPath
    Write-Info "Cree $secretsPath desde template."
}

function Get-SecretsContent { Get-Content $secretsPath -Raw }

function Set-SecretLine {
    param(
        [Parameter(Mandatory)][string]$VariableName,
        [Parameter(Mandatory)][string]$NewValue
    )
    $content = Get-SecretsContent
    $pattern = "(?m)^\s*\`$env:$VariableName\s*=\s*'.*'\s*$"
    $replacement = "`$env:$VariableName = '$NewValue'"
    if ($content -match $pattern) {
        $updated = [regex]::Replace($content, $pattern, $replacement)
    } else {
        # Linea no existe: la agregamos al final.
        $updated = $content.TrimEnd() + "`n$replacement`n"
    }
    Set-Content -Path $secretsPath -Value $updated -NoNewline
}

# ---------- GitHub ----------
$githubTokenRotated = $false
if ($SkipGitHub) {
    Write-Info "Skip GitHub (flag -SkipGitHub)."
} else {
    Write-Section "GitHub PAT via gh device-flow"

    $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $ghCmd) {
        Write-Warn2 "GitHub CLI (gh) no esta instalado."
        Write-Host "  Instalarlo con:" -ForegroundColor Yellow
        Write-Host "    winget install --id GitHub.cli" -ForegroundColor Yellow
        Write-Host "  Despues volve a correr: scripts\rotate_tokens.ps1" -ForegroundColor Yellow
        exit 2
    }
    Write-Ok "gh disponible: $($ghCmd.Source)"

    # Chequeo si hace falta login. `gh auth status` escribe a stderr cuando no
    # hay login, lo cual con $ErrorActionPreference='Stop' dispara un terminating
    # error antes de que podamos leer $LASTEXITCODE. Bajamos el preference
    # localmente y leemos solo el exit code.
    $needsLogin = $ForceGitHub
    if (-not $needsLogin) {
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & gh auth status --hostname github.com *> $null
            $ghStatusExit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $prevEAP
        }
        if ($ghStatusExit -ne 0) { $needsLogin = $true }
    }

    if ($needsLogin) {
        Write-Info "Disparando device-flow. Se abre el navegador y te da un codigo corto."
        Write-Info "Pegalo en la pagina de GitHub y confirmas. Scope pedido: repo."
        & gh auth login --hostname github.com --git-protocol https --scopes repo --web
        if ($LASTEXITCODE -ne 0) {
            Write-Err2 "gh auth login fallo (exit=$LASTEXITCODE)."
            exit 3
        }
        $githubTokenRotated = $true
    } else {
        Write-Ok "gh ya estaba autenticado. Reuso el token existente (usa -ForceGitHub para forzar rotacion)."
    }

    # Lee el token desde gh y escribilo al archivo de secretos.
    $ghToken = (& gh auth token).Trim()
    if (-not $ghToken) {
        Write-Err2 "gh auth token devolvio vacio."
        exit 4
    }

    Set-SecretLine -VariableName 'GITHUB_TOKEN_IABV' -NewValue $ghToken
    Write-Ok "GITHUB_TOKEN_IABV escrito a $secretsPath (len=$($ghToken.Length))."

    # Validacion en vivo.
    $env:GITHUB_TOKEN_IABV = $ghToken
    $code = (& curl.exe -s -o NUL -w '%{http_code}' `
        -H "Authorization: token $ghToken" `
        https://api.github.com/repos/jhonf463r/Python)
    if ($code -eq '200') {
        Write-Ok "GitHub API responde 200 OK."
    } else {
        Write-Err2 "GitHub API respondio HTTP $code. El token no quedo bien."
        exit 5
    }
}

# ---------- Devin ----------
$devinTokenRotated = $false
if ($SkipDevin) {
    Write-Info "Skip Devin (flag -SkipDevin)."
} else {
    Write-Section "Devin API key"

    # Recarga el archivo de secretos para conocer el valor actual.
    . $secretsPath

    $currentDevin = $env:DEVIN_API_KEY
    $needsDevin = $ForceDevin -or `
        (-not $currentDevin) -or `
        ($currentDevin -match 'REEMPLAZAR')

    if (-not $needsDevin) {
        $code = (& curl.exe -s -o NUL -w '%{http_code}' `
            -H "Authorization: Bearer $currentDevin" `
            'https://api.devin.ai/v1/sessions?limit=1')
        if ($code -ne '200') {
            Write-Warn2 "Devin API responde HTTP $code con la key actual. Hay que rotarla."
            $needsDevin = $true
        } else {
            Write-Ok "Devin API responde 200 OK con la key actual. No rota."
        }
    }

    if ($needsDevin) {
        Write-Host ""
        Write-Host "Abri https://app.devin.ai/settings/api-keys -> Create new API key -> Copy." -ForegroundColor Yellow
        Write-Host "Luego pega el valor abajo. El input esta oculto y NO queda en el historial." -ForegroundColor Yellow
        Write-Host ""
        $secure = Read-Host -AsSecureString -Prompt 'DEVIN_API_KEY'
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            $devinToken = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim()
        } finally {
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }

        if (-not $devinToken) {
            Write-Err2 "Input vacio. Aborto."
            exit 6
        }

        # Validacion ANTES de escribir a disco.
        $env:DEVIN_API_KEY = $devinToken
        $code = (& curl.exe -s -o NUL -w '%{http_code}' `
            -H "Authorization: Bearer $devinToken" `
            'https://api.devin.ai/v1/sessions?limit=1')
        if ($code -ne '200') {
            Write-Err2 "Devin API respondio HTTP $code. La key no es valida. No la escribo al archivo."
            exit 7
        }

        Set-SecretLine -VariableName 'DEVIN_API_KEY' -NewValue $devinToken
        Write-Ok "DEVIN_API_KEY escrita a $secretsPath (len=$($devinToken.Length))."
        $devinTokenRotated = $true
    }
}

# ---------- Cierre ----------
Write-Section "Resumen"
if (-not $SkipGitHub) { Write-Host "  GitHub rotado en esta corrida: $githubTokenRotated" }
if (-not $SkipDevin)  { Write-Host "  Devin rotado en esta corrida : $devinTokenRotated" }
Write-Host ""
Write-Host "Proximo paso: abri una PowerShell nueva (para que cargue los valores frescos) y corre" -ForegroundColor Cyan
Write-Host "  scripts\start_iabv.ps1" -ForegroundColor Cyan
Write-Host "El archivo $secretsPath nunca se commitea (esta fuera del repo)." -ForegroundColor Gray
