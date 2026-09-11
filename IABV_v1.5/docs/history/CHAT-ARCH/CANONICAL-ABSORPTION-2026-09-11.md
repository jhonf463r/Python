# IABV v1.5 — Canonical Absorption Audit — 2026-09-11

## PURPOSE

This is a canonical synthesis record for the historical-chat continuity audit performed against the remote repository.

It does not replace source archives. It records which older chat records are reachable from `main`, which exist only on other branches, which material knowledge has already been absorbed into the operational-memory layer, and which source records still require absorption.

The central correction is:

`source archive on main != only valid form of canonical continuity`

A historical source record may remain on a working branch as provenance-bearing evidence while its materially decision-relevant knowledge is absorbed into the canonical operational-memory layer on `main`.

Therefore deletion safety must evaluate both:

`DIRECT_CANONICAL_SOURCE`

and

`CANONICAL_KNOWLEDGE_ABSORPTION`

provided that provenance to the original source remains recoverable.

## CURRENT REPOSITORY FACT

At audit time, GitHub `main` was directly verified at:

`d9737e308e487823b1321b50a5abf2758ce534fa`

The operational-memory documents currently reachable from `main` include the canonical README, memory protocol, context index, current state, symbiosis map, unresolved-knowledge register and archive registry.

The branch `foundation/reconstruction` currently points to:

`35afa106b1bd9135530efc65f8d88b703066d9ee`

It is not interchangeable with `main`. Its ancestry diverges from current `main` and it contains both archive records and a substantial objective-evidence implementation/test slice. The branch must therefore not be merged wholesale merely to make historical records canonical.

## HISTORICAL CHAT AUDIT

### CHAT-ARCH-2026-09-11-001-cognitive-symbiosis

SOURCE:
`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-11-001-cognitive-symbiosis.md`

STATUS:
`DIRECT_CANONICAL_SOURCE=YES`

The file is reachable from `main` and was independently read back from GitHub.

MATERIAL KNOWLEDGE ABSORBED:
- R5 is technical loopback evidence, not proof of real external-agent cognition.
- exact-runtime provenance is required before runtime state is attributed to a target revision;
- Devin can expose IABV live state through MCP when configured;
- Claude corrected the apparent ToolTeach/briefing dependency-cycle interpretation into an imperative construction-order defect;
- Codex produced a focused late-binding repair;
- live STATE_A is useful evidence but does not prove causal learning/continuity;
- cross-IA collaboration is most valuable when agents provide different evidence modalities;
- evidence-pack-driven handoff and state-A/state-B causal experiments were identified as high-value ideas.

DELETE ASSESSMENT:
`PROJECT_CONTINUITY_DELETE_SAFE=YES`
provided the deletion decision is understood as preservation of material project knowledge rather than byte-for-byte transcript preservation. The source archive itself is already on canonical `main`, and the operational-memory synthesis retains its key lessons.

### CHAT-ARCH-2026-09-11-002-p0b-v4-r2-authority-symbiosis

SOURCE:
`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-11-002-p0b-v4-r2-authority-symbiosis.md`

STATUS:
`DIRECT_CANONICAL_SOURCE=YES`

The file is reachable from `main` and was independently read back from GitHub.

MATERIAL KNOWLEDGE ABSORBED:
- separate authority process plus signature is not enough;
- trust-root ownership must be outside the ordinary caller capability boundary;
- storage uniqueness is not by itself concurrent replay protection;
- plaintext private-key storage is an independent failure;
- self-created trust fixtures do not prove independent trust;
- cryptographic validity, durability and database persistence are not authority legitimacy;
- P0-B must retain independent adversarial verification before promotion.

DELETE ASSESSMENT:
`PROJECT_CONTINUITY_DELETE_SAFE=YES` for the same material-knowledge criterion. The fact that P0-B itself remains technically open does not by itself make the historical chat undeletable when the open state, failures, next steps and provenance are durably preserved.

### CHAT-ARCH-2026-09-11-002-context-activation-architecture

SOURCE:
`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-11-002-context-activation-architecture.md`

STATUS:
`DIRECT_CANONICAL_SOURCE=YES`

MATERIAL KNOWLEDGE ABSORBED:
- a new chat must not depend on the previous transcript;
- the archive must behave as objective-conditioned operational memory;
- relevant history should be activated selectively;
- cross-IA role patterns are capabilities, not fixed assignments;
- unimplemented ideas, negative knowledge and contradictions must remain discoverable.

DELETE ASSESSMENT:
`PROJECT_CONTINUITY_DELETE_SAFE=YES` as a source record because it is on `main` and its methodology is integrated into the operational-memory protocol itself.

### CHAT-ARCH-2026-09-11-018-objective-verifier-continuity

SOURCE SET:
- `...018-objective-verifier-continuity.md`
- `...018-r1-provenance-objective-verifier-correction.md`
- `...018-r2-cacp-v4-delete-gate.md`
- `...018-r3-cacp-v4-provenance-final.md`

STATUS:
`DIRECT_CANONICAL_SOURCE=NO`
`REMOTE_SOURCE_PRESERVED=YES`
`SOURCE_BRANCH=foundation/reconstruction`

GitHub verification established that the four 018 records exist remotely on `foundation/reconstruction` and that the R2/R3 chain is real. The exact primary/r3 records are not reachable at the same paths from current `main`.

The branch is intentionally not mergeable as a pure archival action because comparison shows it contains significant objective-evidence source/test changes in addition to the archive files.

MATERIAL KNOWLEDGE THAT MUST BE ABSORBED CANONICALLY:
- `49c8a87...` used `file_content_changed = bool(changed_files)`, a mechanical proxy that could produce objective-evidence false positives;
- `93a52b4...` materially improved this to BASE-vs-RESULT content comparison against an explicit target file;
- the stronger verifier still proves only a narrower proposition than arbitrary natural-language goal satisfaction;
- unit comment-only and wrong-target controls do not equal production-path adversarial controls;
- the next required negative controls include production-path comment-only, wrong-target and goal-mismatch cases;
- independent Claude audit must remain separate from the implementing agent;
- Experience promotion is blocked until objective evidence is legitimately verified;
- a stronger measurement can still measure the wrong property.

DELETE ASSESSMENT BEFORE ABSORPTION:
`PROJECT_CONTINUITY_DELETE_SAFE=NO`

After canonical absorption of the material knowledge above plus provenance pointers to the source branch, the chat may become deletion-safe even though the exact source archive remains on `foundation/reconstruction`.

### CHAT-ARCH-2026-09-11-013-d0-p0b-r3-symbiosis

STATUS:
`SOURCE_ON_MAIN=NO`

The registry previously listed this file, but direct GitHub read-back at the expected main path returned `404`. It was therefore not treated as canonical merely because the registry named it.

DELETE ASSESSMENT:
`UNKNOWN / NO` until a valid remote source or canonical absorption is established.

The registry entry itself is insufficient evidence of archival persistence.

### CHAT-ARCH-2026-09-11-014

STATUS:
`SOURCE_ON_MAIN=NO`

Direct current-main search for the cited `014` archive did not find a matching canonical file. The historical response that claimed no GitHub persistence is therefore consistent with the present repository evidence.

DELETE ASSESSMENT:
`NO` until its material knowledge is canonically absorbed and remote provenance is preserved.

## IMPORTANT CORRECTION TO OLD DELETE GATES

Several historical responses treated an open technical objective as a deletion blocker.

That is too strong.

The proper distinction is:

`TECHNICAL_WORK_OPEN`

and

`HISTORICAL_KNOWLEDGE_UNPRESERVED`

are separate properties.

A chat may be deleted while an engineering task remains open when the open state, failures, evidence boundaries, decisions, pending experiments, provenance and next actions are all durably preserved.

Conversely, a technically closed task does not make a chat deletable if material historical knowledge still exists only in the transcript.

## CANONICAL DELETION MODEL

`DIRECT_CANONICAL_SOURCE=YES`
OR
`CANONICAL_KNOWLEDGE_ABSORPTION=YES`

AND

`PROVENANCE_TO_SOURCE=YES`

AND

`REMOTE_READBACK=YES`

AND

`KNOWLEDGE_LOSS_TEST=PASS`

AND

`BLIND_RECONSTRUCTION=PASS`

AND

`NO_MATERIAL_KNOWLEDGE_ONLY_IN_CHAT=YES`

Only then:

`PROJECT_CONTINUITY_DELETE_SAFE=YES`

The exact transcript does not need to be reproduced sentence-for-sentence. The requirement is preservation of materially decision-relevant knowledge and the provenance needed to distinguish source history from current truth.

## CURRENT ABSORPTION STATUS

`CHAT-ARCH-2026-09-11-001-cognitive-symbiosis = ABSORBED`
`CHAT-ARCH-2026-09-11-002-p0b-v4-r2-authority-symbiosis = ABSORBED`
`CHAT-ARCH-2026-09-11-002-context-activation-architecture = ABSORBED`
`CHAT-ARCH-2026-09-11-018-objective-verifier-continuity = SOURCE_PRESERVED_BRANCH_ONLY / ABSORPTION_REQUIRED`
`CHAT-ARCH-2026-09-11-013-d0-p0b-r3-symbiosis = SOURCE_NOT_FOUND_ON_MAIN / ABSORPTION_REQUIRED`
`CHAT-ARCH-2026-09-11-014 = SOURCE_NOT_FOUND_ON_MAIN / ABSORPTION_REQUIRED`

## FINAL AUDIT PRINCIPLE

Do not ask merely:

`Is the old chat's archive file on main?`

Ask:

`Can a future AI reconstruct the material knowledge relevant to its objective from canonical GitHub memory, while still being able to trace each historical claim back to its source and current evidence?`

That is the actual continuity property required by IABV.
