# CHAT-ARCH-2026-10-03-019 — RSK-01B Prompt Instantiation Correction

## EVENT

Claude's first RSK-01B attempt did not execute the blind continuity test because the supplied prompt retained the literal placeholder `[PEGAR AQUÍ UN SOLO OBJETIVO DE ESTA SESIÓN]`.

Claude correctly refused to invent an objective and only verified that the frozen commit `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442` exists. No repository content was read and no test evidence was generated.

## EPISTEMIC CLASSIFICATION

This is **not** evidence for A, B, C or D. It is a **test-preparation/procedure failure outside the evaluated continuity behavior**.

Important distinction:
`test not executed != continuity failure`
`prompt packaging error != retrieval failure`

## METHOD DELTA

Blind-session prompts must be fully instantiated before handoff. A reusable template may contain placeholders internally, but the actual external execution packet must contain exactly one concrete objective and no unresolved template token.

The operator should receive a complete copy/paste artifact rather than a template plus manual substitution when the experiment is intended to minimize human coordination friction.

## ROUTING DELTA

RSK-01B remains the active experiment. No actor change is justified by this event.

**IA DESTINO:** Sonnet
**CAPABILITY:** independent blind continuity reconstruction
**FIRST OPEN EDGE:** `current objective → complete relevant candidate retrieval`
**ACTION:** execute the fully instantiated Session 1 objective against frozen SHA `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`.

## CONTROL

The frozen corpus remains `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`. Do not use post-writeback routing state as test input.

## STOP CONDITION

Do not score this attempt as one of the five cases. Start Session 1 only with a concrete objective.