# BIO-R13B independent runtime evidence — 2026-09-21

## A. Provenance

- Repository: `jhonf463r/Python`
- Worktree: `C:\Python\IABV_v1.5_bio_r13b_independent_runtime_2026_09_21\IABV_v1.5`
- Source read directly from `origin/main`: `23f17bd2a1895fe12412f20884951cc0b5ccebfa`
- Parent: `4e5f1c57671cb9342929fc47e2b939eb5185b8df`
- Experimental branch: `audit/bio-r13b-independent-runtime-2026-09-21`
- Working tree before artifacts: clean.
- Python: `Python 3.13.2`; platform: `win32`.
- Timestamp: 2026-09-21 UTC.
- Commands, each in a fresh Python process with `PYTHONPATH=<worktree>\src`:

```powershell
& C:\Users\faber\miniconda3\python.exe tests\experiments\test_bio_r13b_independent_runtime.py --case control
& C:\Users\faber\miniconda3\python.exe tests\experiments\test_bio_r13b_independent_runtime.py --case treatment
& C:\Users\faber\miniconda3\python.exe tests\experiments\test_bio_r13b_independent_runtime.py --case negative
& C:\Users\faber\miniconda3\python.exe -m pytest -p no:cacheprovider tests\experiments\test_bio_r13b_independent_runtime.py -q
```

The raw stdout from the three direct commands is preserved without hand-copying in the companion `.txt` artifact.

## B. Control

The fixed candidate universe was A/Codex (`CLOUD`, score `.85`), B/Ollama (`LOCAL`, `.84`), and C/ChatGPT (`CLOUD`, `.70`), all successful. Every run used the same subject, domain, configuration signature, comparison scope, timestamp, and controlled environment metadata. A alone also has the fixed fixture flags `reused_later=True` and `used_fallback=True`; B has `execution_ms=1000`. These fixed fields make A the selected baseline while its fallback rate makes it degraded under the existing monitor rule.

- `successful_keys`: `chatgpt`, `codex`, `ollama`
- selector recommendation: Codex / `cloud`, weighted score `1.098`, adaptive weight `.248`, sample count `1`
- monitor ranking: Codex `1`, Ollama `2`, ChatGPT `3`
- baseline: Codex; alternative: Ollama
- proposal: `validate_local_first`
- proposal key: `bio_r13b_independent_2026_09_21|validate_local_first|cloud|codex|test_config_v1|local|ollama|test_config_v1`

## C. Treatment

The treatment was instantiated in a separate clean process and fresh `AdaptiveWeightLayer` instance. The sole changed fixture value was `A.success: True -> False`.

- `successful_keys`: `chatgpt`, `ollama`; Codex is excluded by the selector's successful-run eligibility.
- selector recommendation: Ollama / `local`, weighted score `1.0733`, adaptive weight `.2333`, sample count `1`
- monitor ranking: Ollama `1`, ChatGPT `2`, Codex `3`
- baseline: Ollama; alternative: ChatGPT
- proposal: absent (`null`)

The monitor deliberately still reports failed Codex in its diagnostic ranking. It is not selected by `StrategySelector.recommend()` because that method rebuilds its scoring universe from groups having at least one successful run. This observed distinction is why ChatGPT, rather than failed Codex, is the treatment alternative.

## D. Differential

| Variable | Control | Treatment | Delta |
| --- | --- | --- | --- |
| A.success | true | false | changed input |
| A eligible | true | false | excluded by selector |
| A weighted_score | 1.098 | .602 | -.496 |
| B weighted_score | 1.0733 | 1.0733 | 0 |
| C weighted_score | .96 | .96 | 0 |
| rank(A) | 1 | 3 | +2 |
| rank(B) | 2 | 1 | -1 |
| rank(C) | 3 | 2 | -1 |
| recommendation | Codex/cloud | Ollama/local | changed |
| baseline | Codex | Ollama | changed |
| alternative | Ollama | ChatGPT | changed |
| margin | -.0247 | no proposal margin | proposal eliminated |
| proposal_kind | validate_local_first | null | changed |
| proposal_key | present | null | changed |

## E. Causal trace

First divergent edge: `A.success`.

Observed source-aligned chain:

```text
A.success
  -> StrategySelector successful_keys
  -> eligible grouped_runs and adaptive profile
  -> weighted recommendation
  -> ToolEvolutionMonitor grouped_runs/profiles/ranking
  -> baseline and alternative
  -> ToolEvolutionProposal
```

In control, eligible Codex is the degraded external baseline and nearby local Ollama produces `validate_local_first`. In treatment, Codex is no longer eligible for the recommendation; Ollama becomes the non-degraded local baseline, so `_proposal_for_subject()` returns `None`.

## F. Negative control

All outcomes remained successful and only `metadata.trace_id` changed. The current production decision surfaces were unchanged: recommendation, baseline, alternative, proposal kind, proposal key, current assistant, and candidate assistant. The test compares that decision projection rather than UUID and timestamp fields generated for each proposal instance.

## G. Artifacts

The versioned `BIO-R13B-INDEPENDENT-RUNTIME-SHA256-2026-09-21.txt` manifest records SHA-256 for these artifacts.

- `tests/experiments/test_bio_r13b_independent_runtime.py`
- `docs/history/CHAT-ARCH/BIO-R13B-INDEPENDENT-RUNTIME-STDOUT-2026-09-21.txt`
- `docs/history/CHAT-ARCH/BIO-R13B-INDEPENDENT-RUNTIME-EVIDENCE-2026-09-21.md`

## H. Reproducibility

- current-main runtime reproduced: **YES**
- historical Devin script reproduced: **NO**; the historical script is unrecoverable and was not reconstructed.

## I. Verdict

**CAUSAL_RUNTIME_CONFIRMED — INDEPENDENTLY_REPRODUCED.** The control and treatment executed current production methods against equivalent clean fixtures whose only treatment change was A's `success`, and the downstream recommendation, baseline, alternative, and proposal changed.

## J. First open edge

`ToolEvolutionProposal -> SandboxExperimentService.validate_recommendation()` remains **NOT_TESTED**.

## K. Negative knowledge

- proposal -> experiment execution: NOT_TESTED
- experiment -> validated outcome: NOT_TESTED
- outcome -> next-cycle proposal: NOT_TESTED
- sandbox promotion: NOT_TESTED
- development: NOT_PROVEN
- evolution: NOT_PROVEN
- self-reproduction: NOT_PROVEN
- open-ended development: NOT_PROVEN

## L. Next actor

An independent runtime auditor is the appropriate next actor: the remaining uncertainty is whether the committed harness and raw stdout accurately support this limited causal claim. No specialized external access is required; the audit cost is low and does not require a sandbox execution.
