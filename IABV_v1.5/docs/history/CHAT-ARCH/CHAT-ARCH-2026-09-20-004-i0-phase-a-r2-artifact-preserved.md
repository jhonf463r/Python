# IABV v1.5 — I0 PHASE A R2 ARTIFACT PRESERVED

## DATE
2026-09-20

## PURPOSE

Reconcile the second Windows runtime evidence capture after the prior independent audit classified the first report **C — INCONCLUSIVE** because its artifact was not repository-preserved.

## VERIFIED REPOSITORY FACTS

Artifact commit:

`99d670b0dd2ecea04bc691e09bb2444c7721bff7`

Artifact path:

`IABV_v1.5/data/evolution/I0_PHASE_A_RUNTIME_EVIDENCE_2026-09-20-R2.json`

The artifact commit is exactly one commit ahead of the tested code revision:

`4710a668541225ffe3b9d1335d31bb5da8b1e685`

The commit adds only the R2 artifact.

The remotely read artifact records:

- tested_code_sha = `4710a668541225ffe3b9d1335d31bb5da8b1e685`
- runtime branch = `devin/i0-canonical-tool-registry-resolution-fix-2026-09-20`
- runtime parent = `a7ae929ae476469c1467f3ac4a29d83aeb16f87d`
- Python executable = `C:\\Python314\\python.exe`
- Python version = `3.14.4`
- workspace = `C:\\Python\\IABV_v1.5`
- all three supported Devin credential variables marked absent
- production resolver marked invoked and empty
- network marked not attempted

Artifact SHA-256, independently recomputed from the exact remotely read CRLF bytes:

`8ed7b1e43065a85d91142350ad82b28f9d8fba82075ddeb74c330a71bd3fd074`

This matches the SHA-256 stated in the artifact-preserving commit message.

## IMPORTANT LIMIT

Artifact preservation verifies **repository provenance and byte integrity**, not the truthfulness of the Windows process observations.

The following remain process-reported claims awaiting independent forensic adjudication:

`effective Windows environment`

`production resolver actually invoked during that process`

`no HTTP request actually attempted during that process`

Thus:

`artifact preserved ≠ runtime observation independently proven`.

## CURRENT EVIDENCE STATE

Previous independent classification:

**C — INCONCLUSIVE**

After R2 preservation:

- artifact provenance = CLOSED
- artifact byte/hash integrity = VERIFIED
- target-to-artifact lineage = VERIFIED
- runtime environment truth = pending independent audit
- Phase A causal closure = pending independent audit

## NEXT ACTOR

**SONNET** performs the independent forensic audit of the preserved R2 artifact against the exact source revision.

Do not reopen the already closed ToolCard/ToolRegistry/resource-resolution seam.

Do not attempt real authentication.

Do not advance to I1/I2.

## NEGATIVE KNOWLEDGE

Still not proven:

- real Devin authentication
- external Devin execution
- I1 automatic round-trip
- I2 dynamic symbiosis
- external-world effect
- independently verified external result
- cognitive influence on external Devin behavior
- P0-B authorization
