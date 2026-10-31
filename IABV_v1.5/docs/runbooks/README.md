# IABV v1.5 — Reusable technical runbooks

This directory stores cross-task capabilities that participating AI sessions can retrieve when their objective matches. These are documented methods unless a runbook explicitly provides verified automation and tests.

## Manufacturing and digital fabrication

- [Laser-cut vector topology and manufacturability](./laser-cut-vector-topology-skill.md) — interpret SVG/DXF/CAM semantics; distinguish stock, retained material, cutouts and detached slugs; model kerf-aware cut sweeps; validate connected components, bridges, opaque engraved faces, assembly geometry and release readiness.
  - Learning receipt: [BURVE / María case absorption](../history/CHAT-ARCH/CHAT-ARCH-2026-10-31-LASER-CUT-VECTOR-TOPOLOGY-KNOWLEDGE-ABSORPTION.md)

## Activation contract

When a new task concerns laser cutting, vector preparation, material retention/removal, engraving, topology, bridges, or CAM handoff, retrieve the laser-cut skill and activate the relevant sections before designing or reviewing. Do not assume that GitHub persistence means another AI session has already received or applied the skill. Record the exact revision retrieved and the concrete decision it changes. Keep concept imagery, parsed vectors, digital topology validation, CAM review, coupon testing and production approval as separate evidence stages.

The live task route and authorization remain governed only by `docs/history/CHAT-ARCH/CURRENT-STATE.md`.
