# IABV v1.5 — CHAT-ARCH Historical Record Registry

## PURPOSE

This registry prevents the historical archive from becoming a flat pile of Markdown files.

The registry is a **pointer layer**, not a replacement for source records. It records where historical knowledge lives and how it should be reached.

## IMPORTANT REPOSITORY REALITY

Historical `CHAT-ARCH-*` records currently exist in more than one path. This is intentional legacy state and must be reconciled by navigation, not by silently moving or renaming records.

Known locations:

- `IABV_v1.5/docs/history/CHAT-ARCH/`
- `IABV_v1.5/docs/history/`
- `IABV_v1.5/docs/CHAT-ARCH-*.md`

## CANONICAL NAVIGATION FILES

| File | Function |
|---|---|
| `README.md` | Entry rules and continuity contract |
| `CONTEXT-INDEX.md` | Objective-driven historical routing |
| `CURRENT-STATE.md` | Reconciled active project state |
| `SYMBIOSIS-MAP.md` | Cross-IA capability/learning transfer |
| `ARCHIVE-REGISTRY.md` | Historical source registry |

## HIGH-VALUE SOURCE RECORDS

### Cognitive control / symbiosis / continuity

- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-11-001-cognitive-symbiosis.md`
- `IABV_v1.5/docs/history/CHAT-ARCH-2026-09-11-001-cognitive-control-plane-p0b-symbiosis.md`
- `IABV_v1.5/docs/history/CHAT-ARCH-2026-09-11-001-cognitive-symbiosis.md` is the detailed R5/MCP/exact-runtime record.
- `IABV_v1.5/docs/history/2026-09-03_conversation_cognitive_continuity_self_development.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-006_iabv-continuity-directed-evolution.md`

### Scientific / metacognitive evolution

- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-011_multi-tool-scientific-metacognition-coordination.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-005_r10-4_resource-metacognition-cognitive-governor.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-005_cognitive-metabolism-self-development.md`

### Evidence / verification / forensic continuity

- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-007_adaptive-evidence-adequacy-and-forensic-continuity.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-005_canonical-perception-learning-forensic.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-005_iabv-self-operation-runtime-reconciliation.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-012_iabv-runtime-integration-and-stabilization.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-012_persistence-verification.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-011_github-persistence-deletion-gate.md`

### Authority / trust / P0.213 / P0-B

- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-004_p0213-trust-boundary-evolution.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-005_p0213-c2-authority-chokepoint-evolution.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-012_p0213-phase2-phase3-authority-authorization.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-008_p0213-authority-execution-self-development-forensic.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-012_p0213-lifecycle-trust-autoevolution-forensic.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-011_p0213-phase3-adversarial-design-loop.md`
- `IABV_v1.5/docs/CHAT-ARCH-2026-09-03-CLAUDE-P0-213-RECONCILIATION.md`
- `IABV_v1.5/docs/CHAT-ARCH-2026-09-03-CLAUDE-P0-213-RECONCILIATION-v2.md`

### Architecture → runtime construction

- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-0903-002_iabv-architecture-to-runtime-construction.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-0903-001_p0213-phase3-windows-runtime-forensic.md`

### Decision / broader forensic records

- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-005_p0213-r3-r10-decision-expert.md`
- `IABV_v1.5/docs/history/2026-09-03_CHAT-ARCH-2026-006_adaptive-meta-orchestrator-forensic.md`
- `IABV_v1.5/docs/history/2026-09-03_conversation_knowledge_sync.md`
- additional `CHAT-ARCH-*` records under `IABV_v1.5/docs/history/` should be added to the registry when discovered as relevant to a new domain.

## DUPLICATE / COLLIDING IDS

Several historical files use the same numeric `CHAT-ARCH-YYYY-MM-DD-NNN` identifier for different subjects. Therefore:

- **file path + exact filename is the durable identity**;
- the numeric CHAT-ARCH ID alone is not a unique identifier;
- do not merge records solely because their numeric ID matches;
- preserve all source records unless an evidence-backed supersession is recorded.

Examples already observed include multiple `CHAT-ARCH-2026-09-11-001` records with different subject suffixes and multiple `CHAT-ARCH-2026-09-03-012` / `011` subject variants.

## RECORD STATUS MODEL

For routing, every historical source should conceptually be classifiable as:

`SOURCE_RECORD | SYNTHESIS | ADDENDUM | CORRECTION | RECONCILIATION | PERSISTENCE_PROOF`

The classification does not alter the source content.

## DISCOVERY RULE

The registry is not expected to be perfectly exhaustive forever. When a new chat discovers another historical record that materially affects a domain, the new record should be added here and to `CONTEXT-INDEX.md` as appropriate.

The goal is a **self-expanding navigable knowledge graph**, not a frozen table of contents.

## REMOTE-READBACK RULE

A record is considered durable only when its GitHub path and commit provenance can be independently read back. Local existence, a user report, or a prior chat assertion is insufficient.
