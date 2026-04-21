# iabv_secrets.template.ps1
#
# Template para secretos locales de IABV. NO se commitea con valores reales.
#
# Flujo de uso:
#   1. Copiar este archivo a ~\.iabv_secrets.ps1 (fuera del repo).
#        Copy-Item scripts\iabv_secrets.template.ps1 $HOME\.iabv_secrets.ps1
#   2. Editar $HOME\.iabv_secrets.ps1 y reemplazar los placeholders con
#      los valores reales (obtenidos una sola vez).
#   3. Cargarlo al abrir PowerShell agregando al $PROFILE:
#        . "$HOME\.iabv_secrets.ps1"
#      (scripts\setup_iabv_profile.ps1 hace este paso por vos).
#
# Seguridad:
#   - $HOME\.iabv_secrets.ps1 queda fuera del repo; nunca commitearlo.
#   - Si exponis un token (chat, screenshot, etc) revocalo inmediatamente.
#   - Los adapters aceptan multiples alias; exportar UNO de cada familia
#     alcanza. El orden de preferencia esta documentado en bootstrap.py.

# --- GitHub PAT (F2.1 github_api adapter) ---
# Scope minimo requerido: `repo`.
# Generar en: https://github.com/settings/tokens/new?scopes=repo&description=IABV
$env:GITHUB_TOKEN_IABV = 'ghp_REEMPLAZAR_CON_PAT_REAL'

# --- Devin API key (F2.4 devin_api adapter) ---
# Generar en: https://app.devin.ai/settings/api-keys
$env:DEVIN_API_KEY = 'devin_REEMPLAZAR_CON_KEY_REAL'

# --- Flags operativos IABV v1.5 ---
# Abre PR documental automatico cuando el ciclo de validacion promueve
# un candidato. Branch: `iabv-auto/promote-<slug>-<ts>`.
$env:IABV_AUTO_PROMOTION_PR_ENABLED = '1'

# Enciende el routing sinaptico adaptativo del orquestador.
$env:IABV_SYNAPTIC_ROUTING_ENABLED = '1'

# Hot-reload del MCP: cuando cambian archivos en src/iabv_v15, el server
# se reinicia solo. Util durante desarrollo; opcional.
# $env:IABV_MCP_HOT_RELOAD = '1'
