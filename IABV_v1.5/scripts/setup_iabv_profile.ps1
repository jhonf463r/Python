# setup_iabv_profile.ps1
#
# One-shot idempotente que deja la PowerShell del usuario lista para arrancar
# IABV sin re-exportar tokens cada vez.
#
# Efectos:
#   1. Si no existe $HOME\.iabv_secrets.ps1, lo crea a partir del template.
#      (El usuario aun debe editar ese archivo con los valores reales.)
#   2. Agrega al $PROFILE una linea que hace `. "$HOME\.iabv_secrets.ps1"`
#      si aun no esta. Asi cualquier ventana nueva de PowerShell ya tiene
#      GITHUB_TOKEN_IABV, DEVIN_API_KEY, IABV_AUTO_PROMOTION_PR_ENABLED, etc.
#
# Uso (una sola vez por maquina):
#   powershell -ExecutionPolicy Bypass -File scripts\setup_iabv_profile.ps1
#
# Reversion: borrar $HOME\.iabv_secrets.ps1 y quitar la linea agregada
# al $PROFILE (el script imprime su ruta exacta).

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$templatePath = Join-Path $PSScriptRoot 'iabv_secrets.template.ps1'
$secretsPath = Join-Path $HOME '.iabv_secrets.ps1'

if (-not (Test-Path $templatePath)) {
    Write-Error "No encontre el template en $templatePath. Esperaba correr desde el repo IABV."
}

Write-Host "=== IABV profile setup ===" -ForegroundColor Cyan
Write-Host "Repo        : $repoRoot"
Write-Host "Template    : $templatePath"
Write-Host "Secrets file: $secretsPath"
Write-Host "Profile     : $PROFILE"
Write-Host ""

# Paso 1: crear $HOME\.iabv_secrets.ps1 si no existe.
if (Test-Path $secretsPath) {
    Write-Host "[ok] $secretsPath ya existe; no lo toco." -ForegroundColor Green
} else {
    Copy-Item $templatePath $secretsPath
    Write-Host "[new] Cree $secretsPath a partir del template." -ForegroundColor Yellow
    Write-Host "      ABRIlo y reemplaza los placeholders antes del siguiente arranque:" -ForegroundColor Yellow
    Write-Host "        notepad `"$secretsPath`"" -ForegroundColor Yellow
}

# Paso 2: asegurar que $PROFILE existe (PowerShell lo crea sobre demanda).
$profileDir = Split-Path -Parent $PROFILE
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Host "[new] Cree directorio $profileDir" -ForegroundColor Yellow
}
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "[new] Cree $PROFILE" -ForegroundColor Yellow
}

# Paso 3: inyectar el source-line si aun no esta.
$sourceLine = ". `"$secretsPath`""
$marker = '# --- IABV secrets (auto-managed by setup_iabv_profile.ps1) ---'
$profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if (-not $profileContent) { $profileContent = '' }

if ($profileContent -match [regex]::Escape($marker)) {
    Write-Host "[ok] $PROFILE ya contiene el bloque IABV; no duplico." -ForegroundColor Green
} else {
    $block = @"

$marker
if (Test-Path "$secretsPath") { $sourceLine }
# --- end IABV block ---
"@
    Add-Content -Path $PROFILE -Value $block
    Write-Host "[new] Agregue bloque IABV al final de $PROFILE" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Listo. Abri una PowerShell nueva y verifica con:" -ForegroundColor Cyan
Write-Host "  echo `"GITHUB_TOKEN_IABV len=`$(`$env:GITHUB_TOKEN_IABV.Length)`""
Write-Host "  echo `"DEVIN_API_KEY     len=`$(`$env:DEVIN_API_KEY.Length)`""
Write-Host "Si imprimen len=0, editá $secretsPath con los valores reales." -ForegroundColor Yellow
