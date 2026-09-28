# R32-G Provenance Manifest

## Evidence Branch
devin/bio-universal-09-11-r32g-evidence-2026-09-28

## Evidence Commit SHA
3c8b32a4d7240d3370d16423324d542443e81f16

## Parent SHA
707388053dcc760dbcec017357f1b6001994bd57

## Baseline SHA
707388053dcc760dbcec017357f1b6001994bd57

## Artifact Path
IABV_v1.5/test_r32_g_local_experience.py

## Artifact SHA-256
5168db986e48cf722e5361e3ef38c3afa988a2ce0da6a481b64ad19bd7dc175c

## Artifact Byte Length
10635 bytes

## Repository
jhonf463r/Python

## Worktree
C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5

## Working Tree State
Modified data files and __pycache only, no production source changes

## Python Executable
C:\Users\faber\miniconda3\python.exe

## Python Version
Python 3.13.2

## PYTHONPATH
C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5/src

## Ollama Endpoint
http://127.0.0.1:11434

## Ollama Model
phi3:latest

## Runtime Command
```powershell
$env:PYTHONPATH='C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5/src';
$env:IABV_OLLAMA_BASE_URL='http://127.0.0.1:11434';
$env:IABV_OLLAMA_MODEL='phi3:latest';
& 'C:\Users\faber\miniconda3\python.exe' test_r32_g_local_experience.py
```

## Execution Timestamp
2026-09-27

## Fresh Execution RunRecord ID
63e5075b-3413-46f9-93de-bd5c555df9dc

## Fresh Execution AdaptiveSession ID
9def5f02-f37f-4aea-aa42-38b45b0b8f65

## Fresh Execution ExperimentRun ID
f1791232-c430-4e3a-98a5-9c83c0e84346

## Fresh Execution Metacognitive Evaluation
```json
{
  "predicted_outcome": "failure",
  "actual_outcome": "success",
  "confidence": 0.0,
  "calibration_error": 1.0,
  "uncertainty_proxy": 0.0,
  "false_positive": false,
  "false_negative": true,
  "recommended_action": "continue_with_same_worker"
}
```

## Persistence Location
C:\IABV_WORKTREES\bio-universal-09.11-r22b-runtime\IABV_v1.5\data\r32_g_isolated\test_57f8d07f68494e6d808f2a63914f4cab

## Persistence Readback
PASSED — ExperimentRun reloadado desde ExperimentLabRepository.list_runs(), metadata metacognitive_evaluation presente e idéntico al valor generado

## Historical Artifact Status
The test script artifact was recovered from the historical worktree with SHA-256 verification.

## Historical Execution Status
NOT PRESERVED — The historical execution data (RunRecord ID 6556c7fc-cedd-4f28-b1a0-0125950c2d5e, ExperimentRun ID 46a47e94-2bbf-472d-afe3-601851f064f7) is not independently verifiable because the execution data was not preserved in the committed worktree.

## Distinction
This evidence branch contains:
1. The recovered test artifact (historical script)
2. The fresh execution record (new runtime data with full provenance)

These are NOT the same execution event. The historical execution remains REPORTED_ONLY. The fresh execution is independently attributable through this branch.

## No Secrets
This manifest contains no API keys, credentials, or sensitive environment contents.
