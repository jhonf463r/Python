# IABV v1.5 Forensic Identity Report
**Date:** 2026-09-02
**Repository:** jhonf463r/Python
**Project:** IABV_v1.5/
**Canonical Branch:** iabv-auto/promote-platform-phase1-abstraction-windows-1787171505
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## Exact Identity

**Repository Root:** C:\Python
**IABV Subtree:** C:\Python\IABV_v1.5
**Parent Git Root:** C:\Python
**Current Branch:** iabv-auto/promote-platform-phase1-abstraction-windows-1787171505
**Current HEAD:** ac56cc3684d039c33caede168af53305fa99de35
**Parent SHA:** (not computed in this snapshot)

## Python Environment

**Python Version:** 3.13.2
**Python Interpreter:** C:\Users\faber\miniconda3\python.exe
**Active Virtual Environment:** None
**PYTHONPATH:** None
**Editable Installations:** (not computed in this snapshot)
**Import Root for iabv_v15:** C:\Python\IABV_v1.5\src

## Git Status

**Working Tree Status:** MODIFIED (contains Patch A + extensive test modifications + untracked artifacts)
**Tracked Modified Files:** 5 source files + 1505 .pyc files
**Untracked Files:** 457+ (test scripts, audit artifacts, calibration data, etc.)
**Staged Files:** None

## Alternate IABV Checkouts Detected

- C:\Python\IABV_v1.5_canonical/
- C:\Python\IABV_v1.5_runtime_p020/
- C:\Python\IABV_v1.5_runtime_p020_dependency_audit/
- C:\Python\IABV_v1.5_runtime_p020o/
- C:\Python\IABV_v1.5_runtime_p021v/

## Active Runtime Source vs Historical Checkout

**ACTIVE_RUNTIME_SOURCE:** C:\Python\IABV_v1.5 (current working tree)
**HISTORICAL_CHECKOUT_PRESENT:** TRUE (multiple historical checkouts exist)

## Patch A Forensic State

**PATCH_A_PRESENT:** TRUE
**PATCH_A_ONLY:** FALSE (mixed with other modifications)
**PATCH_B_PRESENT:** TRUE (ARO prebuild admission present in same commit)
**UNRELATED_SOURCE_CHANGE:** TRUE (extensive test modifications, untracked artifacts)

### Patch A Files Modified

- IABV_v1.5/src/iabv_v15/bootstrap.py (104 lines added)
  - Entry admission in _bg_metacognition (lines 1933-1963)
  - Cooperative checkpoint after _startup_self_examination (lines 1976-1989)
  - Cooperative checkpoint after _run_startup_common_sense (lines 1996-2009)
  - Auto-install admission in _deferred_auto_install_missing_tools (lines 2039-2064)

### Patch B Files Modified

- IABV_v1.5/src/iabv_v15/bootstrap.py (lines 3963-4202)
  - _should_pause_prebuild method
  - ARO lazy VM prebuild admission logic

### Other Source Modifications

- IABV_v1.5/tests/test_adaptive_task_orchestrator.py (731 lines modified)
- IABV_v1.5/tests/test_agent_handoff_trail.py (11 lines modified)
- IABV_v1.5/tests/test_cognitive_metabolic_tick.py (3576 lines modified)
- IABV_v1.5/tests/test_reflection_ordering_fix.py (450 lines modified)
- IABV_v1.5/tests/test_resource_governance_fix.py (284 lines modified)

### Bytecode Artifacts

**Tracked .pyc Files Modified:** 1505 files (various Python versions)
**Note:** These are generated artifacts, not source modifications.

## Source Clean Status

**SOURCE_CLEAN:** FALSE
- Working tree contains extensive modifications beyond Patch A
- Large number of untracked test and audit artifacts
- Bytecode artifacts tracked in git
