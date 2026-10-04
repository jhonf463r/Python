# CHAT-ARCH-2026-10-04-045 — FRESH BLIND RUN BLOCKED BY CONDITION LEAKAGE AND CONTAMINATION

## PURPOSE

Record the first attempted execution of the corrected fresh-blind continuity package and reconcile why it is not eligible as a blinded participant run.

## PROVENANCE

The result is preserved from the participant response supplied in the collaboration transcript.

This is not an independently captured filesystem artifact.

Canonical experiment package target:
`1de114420c2b078c401fca2d45ecdb5e73b6cb80`

## OBSERVED PARTICIPANT REPORT

The participant reported that its supplied ZIP contained:

`TASK.txt` plus eight corpus files, including record 043.

The participant therefore had enough structural information to distinguish the FULL condition from the ABLATION condition because the two prior packages differed by corpus membership.

The participant also explicitly reported:

`This chat was not clean-room.`

It disclosed prior exposure to:
- a repository clone;
- an earlier copy of the experiment task prompt.

It stated that it did not use those materials for A–L, but absence of influence is not independently provable.

## DISPOSITION

`INVALID FOR PRIMARY BLIND SCORING`

Do not score this response as the FULL or ABLATION participant in the experimental pair.

Do not use its claim scores as evidence of continuity performance.

It may be retained as a harness/debugging observation.

## FAILURE MODES

### F1 — Condition leakage

Opaque ZIP filenames were insufficient because the corpus structures differed:
- FULL had eight corpus files;
- ABLATION had seven.

A participant inspecting the supplied corpus could infer the condition from file presence.

Therefore:
`opaque package name != blinded condition`

### F2 — Freshness contamination

The participant was not clean-room with respect to the experiment context.

Therefore:
`new response != fresh participant`

when prior project/task context was present in the conversation.

### F3 — Source-level blinding is not yet adequate

Future conditions must preserve identical file paths and corpus cardinality.

The experimental perturbation must occur in content, not by deleting a uniquely named file.

## METHOD DELTA

Replace:
`FULL = file present / ABLATION = file absent`

with a structure-preserving perturbation:

`same path + same file count + same package structure + controlled content perturbation`

The perturbation must be preregistered before execution and must not itself reveal the condition.

This is more precisely a:
`SOURCE-CONTENT ABLATION / PLACEBO CONTROL`

rather than a pure availability ablation.

The interpretation remains behavioral source dependence, not proof of internal activation.

## FRESHNESS CONTROL

Each participant must start in a genuinely new conversation with no prior project or experiment context.

Do not reuse the contaminated session.

Do not let a participant inspect a prior task prompt outside the current task delivery.

## CURRENT EXPERIMENTAL EDGE

`relevant source content → differential fresh-chat reconstruction`

## NEXT ACTION

Codex must rebuild the package with:
- identical corpus structure in both conditions;
- identical TASK.txt;
- identical file names and counts;
- a controlled, non-revealing perturbation in the content of record 043;
- operator-only condition key;
- no participant execution.

Then two genuinely fresh Sonnet/Claude sessions execute the two conditions.

## STOP CONDITION

Stop package construction if the participant can infer the condition from filenames, file count, directory structure or obvious placeholder text.

No participant scoring until blinding and freshness controls pass.
