# Space-Time protocol revision 2.1 — evidence handoff and communication-friction receipt

- Date: 2026-10-25 (America/Bogota).
- Protocol ID: `CONTINUITY_SPACE_TIME_ANTI_LOOP`.
- Previous living revision: `2.0 — ADAPTIVE_SPACE_TIME_NEUROPLASTICITY`.
- Proposed living revision: `2.1 — ADAPTIVE_SPACE_TIME_NEUROPLASTICITY + MACHINE_GENERATED_EVIDENCE_HANDOFF`.
- Base `main`: `cc4eee3d3b195361d8eb65a193b5d7edd4f41b01`.
- Trigger: Owner directly requested that coordination stop delegating artifact assembly back to the human, use the existing memories/protocol to infer the next communication step, and improve collaboration with Codex/other AIs.
- Scope: protocol sections 9, 12.2 and 26.4 revised in place; synchronized front-door route and consolidated handoff; documentation-only.
- Not a claim of model-weight training. Behavioral reuse remains unproven until a later non-identical task demonstrably applies this rule and reduces transfer steps or Owner effort.

## Observed failure mechanism

The completed G3 candidate report named six source/test diffs and separate pre-existing staged/unstaged preservation artifacts under a Windows temporary directory. Those bytes were not directly available to the ChatGPT review surface. The previous response correctly refused to substitute similarly named older Library diffs, but then asked the Owner to upload/assemble a ZIP rather than first routing an evidence-packet creation task to the existing local Codex session. This transferred packaging work to the Owner and caused an avoidable coordination loop.

The route surfaces were checked:
- Current conversation file list: no attached files.
- Library: `staged.diff.txt` and `unstaged.diff.txt` were present, but were not the six task-specific diff artifacts and were explicitly preserved as non-substitutes.
- GitHub repository `jhonf463r/Python`: visibility independently returned as `public`.

## Adopted operating correction

1. Search supported, already-authorized conversation, Library and exact repository/PR sources by task identity before requesting anything from the Owner.
2. If the producing Codex/local session is available, give it one bounded, read-only, copy-ready instruction to produce a single ZIP evidence packet outside the checkout. Include exact task diffs, separately preserved staged/unstaged diffs, source bytes needed for static review, before/after status/index identity, and a machine-readable SHA-256 manifest. Do not change the checkout, stage files, commit, push, or run tests/build/runtime.
3. Prefer a supported private transfer route. If no such machine-to-machine route is available, reduce the human side to one upload of the producer-generated ZIP; the Owner does not assemble its members manually.
4. Do not treat a public GitHub branch/PR as expiring when deleted. Public staging is not the default for unreviewed security diffs or dirty workspace deltas. Only use it with explicit disclosure authorization for the exact screened packet, a separate evidence-only branch, and an evidenced cleanup operation.
5. When no direct Codex dispatch mechanism is available in the ChatGPT session, state `PREPARED_NOT_SENT` and present the full prompt inline; never claim that the prompt was delivered or read until a correlated receipt supports that state.
6. Keep the review fail-closed: a packet is transport, not approval. Static source claims only upgrade after exact bytes are reviewed; runtime/Windows behavior remains unproven.

## Acceptance and falsifier

The next evidence-transfer event passes this protocol check if the existing producing actor creates the complete package in one bounded task, original diff bytes and pre-existing state are not altered, every member has a manifest digest, transfer requires no manual file-by-file assembly, and the reviewer can reconcile the exact packet. It fails if the assistant again asks the Owner to hand-collect files before checking whether the producer can package them, substitutes a similarly named artifact, publishes security diffs publicly by default, or claims dispatch/expiry without evidence.

```text
LESSON_STATUS=PROMOTED_BY_PROTOCOL_MERGE; CAUSAL_REUSE=NOT_TESTED
ROUTE_SURFACE_MISMATCH=OBSERVED_FOR_EXACT_WINDOWS_TEMP_ARTIFACTS
ASSISTANT_FAILURE=MANUAL_BUNDLE_REQUEST_BEFORE_SOURCE_ACTOR_PACKAGING; RECORDED
PROTOCOL_DELTA=SECTION_9; SECTION_12_2; SECTION_26_4; IN_PLACE
TRANSFER_DEFAULT=PRODUCER_GENERATED_SINGLE_ZIP; OUTSIDE_CHECKOUT
PUBLIC_GITHUB_REPOSITORY=VERIFIED
PUBLIC_GITHUB_TEMP_EXPIRY=NOT_ASSUMED
OWNER_BURDEN=ONE_UPLOAD_ONLY_IF_NO_SUPPORTED_PRIVATE_ROUTE
MODEL_WEIGHT_CHANGE=NOT_CLAIMED
G3_SAME_OBJECT=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
PROTECTED_READS=FAIL_CLOSED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=PREPARE_ONE_BOUNDED_ARTIFACT_CAPTURE_PROMPT_FOR_EXISTING_CODEX_SESSION
```
