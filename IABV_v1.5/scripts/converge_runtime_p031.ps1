# P0.31: Runtime Convergence Script
# Run this from: C:\Python\IABV_v1.5_runtime_main
# Preserves local commits, integrates origin/main (P0.29 + P0.30)
#
# Prerequisites: close IABV before running.

$ErrorActionPreference = 'Stop'
$runtime = 'C:\Python\IABV_v1.5_runtime_main'

Write-Host '=== P0.31 Runtime Convergence ===' -ForegroundColor Cyan

# 1. Verify state
Set-Location $runtime
Write-Host "`n--- Pre-merge state ---"
git rev-parse HEAD
git rev-parse origin/main
git rev-list --left-right --count HEAD...origin/main
git log --left-right --cherry-pick --oneline HEAD...origin/main

# 2. Fetch latest
Write-Host "`n--- Fetching origin ---"
git fetch origin

# 3. Merge origin/main preserving local commits
Write-Host "`n--- Merging origin/main ---"
git merge origin/main -m "P0.31: Converge runtime with origin/main (P0.29 + P0.30)"

# If conflicts occur, resolve manually and run:
#   git add .
#   git commit -m "P0.31: Resolve merge conflicts preserving local fixes"

# 4. Verify result
Write-Host "`n--- Post-merge verification ---"
$head = git rev-parse HEAD
Write-Host "HEAD: $head"
git log --oneline -5
git rev-list --left-right --count HEAD...origin/main

Write-Host "`n--- Checking P0.30 marker ---"
$hasGuard = Select-String -Path "IABV_v1.5\src\iabv_v15\ui\viewmodels\control_center_viewmodel.py" -Pattern '_try_handle_structured_self_audit' -Quiet
if ($hasGuard) {
    Write-Host 'P0.30 _try_handle_structured_self_audit: PRESENT' -ForegroundColor Green
} else {
    Write-Host 'P0.30 _try_handle_structured_self_audit: MISSING' -ForegroundColor Red
}

Write-Host "`n=== Done. Open IABV and test: ===" -ForegroundColor Cyan
Write-Host '1. "haz una autoauditoria y dime el estado de tests, self audit y portable context"'
Write-Host '   -> Must respond <5s from artifacts, not Adaptive local orchestrator'
Write-Host '2. "haz una consulta a ChatGPT: responde solo S si entiendes"'
Write-Host '   -> Must route as new external consultation'
Write-Host '3. Check data/logs/runtime_audit.jsonl for structured_self_audit_answered'
