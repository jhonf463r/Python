# BIO-R13B — RUNTIME CAUSAL: RECOMMENDATION → TOOL EVOLUTION PROPOSAL

Date: 2026-09-21

## Provenance

- Repository: `jhonf463r/Python`
- Runtime branch executed: `devin/i0-external-route-target-fix-2026-09-20`
- Runtime HEAD: `f0c98ca1af756273f14a7fae65fafa9bd69a3a30`
- Working tree: 5738 untracked files (caches/tmp/test data)
- Runtime: Python 3.14.4, win32
- Exact command: `python temp_bio_r13b_recommendation_to_proposal.py`
- Evidence type: direct runtime control/treatment execution

The current source inspection target is `23f17bd2a1895fe12412f20884951cc0b5ccebfa`. The relevant `strategy_selector.py` and `tool_evolution_monitor.py` logic is consistent with the executed path.

## Control

Subject: `bio_r13b_test_subject`

- Domain: `CLOUD_REASONING`
- A: codex / CLOUD / success=True / total_score=0.85
- B: ollama / LOCAL / success=True / total_score=0.84
- C: chatgpt / CLOUD / success=True / total_score=0.70
- Config: `test_config_v1`

Observed recommendation: codex / CLOUD.

Observed ranking:
1. codex weighted_score=1.0789
2. ollama weighted_score=1.0720
3. chatgpt weighted_score=0.9227

Observed proposal:
- proposal_kind=`validate_local_first`
- current_assistant_kind=`codex`
- candidate_assistant_kind=`ollama`
- proposal_key=`bio_r13b_test_subject|validate_local_first|cloud|codex|test_config_v1|local|ollama|test_config_v1`

## Treatment

Only change from control:

- A: codex / CLOUD / success=False / total_score=0.85

B and C remain unchanged.

Observed recommendation: ollama / LOCAL.

Observed ranking:
1. ollama weighted_score=1.0720
2. chatgpt weighted_score=0.9227
3. codex weighted_score=0.5829

Observed proposal: `None`.

## Differential

- success: A True → False
- eligibility: A included → A excluded by `successful_keys`
- codex weighted_score: 1.0789 → 0.5829
- recommendation: codex → ollama
- baseline row: codex → ollama
- alternative: ollama → chatgpt
- proposal: `validate_local_first` → `None`

The runtime therefore demonstrates a causal propagation chain:

`success → eligibility → adaptive profile/ranking → recommendation → baseline → proposal`

## Verdict

`CAUSAL_RUNTIME_CONFIRMED` for BIO-R13B.

This does not prove proposal execution. It also does not prove that a sandbox proposal corresponds to a real external-agent execution.

## Next open edge

The next discriminating boundary is:

`ToolEvolutionProposal → SandboxExperimentService.validate_recommendation() → observed experiment/result`

Important distinction: the current `SandboxExperimentService.validate_recommendation()` constructs a `SandboxExperiment`, computes a verdict, and records a synthetic/derived `ExperimentRun`; the inspected implementation does not invoke an external agent or real tool execution itself. Existing `AutonomousValidationCycleService` tests use a `_SandboxStub`, so they are not independent proof of real sandbox execution.

Therefore the next investigation must distinguish:

1. proposal → sandbox object/validation call (likely runtime-testable at a small seam);
2. sandbox object → actual executable experiment;
3. actual execution → independently observed outcome.

## Negative knowledge

Not proven by BIO-R13B:

- proposal → real experiment execution
- experiment → independently observed outcome
- outcome → next-cycle proposal across multiple cycles
- sandbox promotion through a real execution
- new verified capability
- development
- evolution
- self-reproduction
- open-ended development

Preserve:
`report != evidence`
`DEFINED != WIRED != INVOKED != OBSERVED != CAUSED`
`persistence != learning`
`learning != development`
