# CHAT-ARCH-2026-10-07-139 — CAPABILITY → REALIZATION EXISTING-DOMAIN CONTRACT RECHECK

## PROVENANCE

Direct static source recheck after Claude design closure.
Executable baseline: 07ebffc8f866fc99a3f78091dcd1edd456a0da00
Tree: f0e1294982479426b140eab21f16f2f839504413
Documentation main at recheck: latest docs-only writebacks after episode 138.
No runtime/tests/source modifications.

## ADDITIONAL EXISTING MODELS AUDITED

### ToolCapability
ToolCapability is a typed enum used in RoleRoute.tool_chain and LocalRoleRouter/tool-teach route construction. It represents coarse tool-chain/role capability such as TOOL_EXECUTION, TOOL_SANDBOX, LOCAL_LLM, BROWSER_OBSERVATION, KNOWLEDGE_SEARCH and CODE_EDIT.
It is not currently a required-capability ID produced by CapabilityReadinessService and is not a ToolCard realization declaration. No semantic equivalence is established.
Decision: reuse only as contextual route/role evidence; do not repurpose as the universal abstract capability vocabulary.

### CapabilityDescriptor
CapabilityDescriptor already contains capability_id, channel, tool_ids, primary_operations and reusable_pattern_ids.
Direct repository search found no executable construction or consumer of CapabilityDescriptor in the inspected baseline beyond its model definition and historical documentation mentions.
Therefore it is a defined but operationally orphaned model. It cannot be treated as an existing operative capability→realization bridge without adding a new owner/consumer contract.
Decision: do not silently revive it as the runtime registry/bridge. Doing so would create a new operational organ rather than reuse an existing behaviorally proven path.

## RECONCILIATION WITH EPISODES 136–138

The independent empty-set closure remains valid.
ToolCard.realizes_capability_ids remains justified as the explicit realization declaration because the existing alternatives are either heterogeneous implementation labels (ToolCard.capabilities), coarse role/tool-chain labels (ToolCapability), or an unused domain model (CapabilityDescriptor).

The correction against Claude's response remains active:
eligible_tool_ids must not become durable ToolTask truth.

## CURRENT FIRST OPEN IMPLEMENTATION EDGE

Implement only after fresh human authorization: exact minimal diff for selector outcome, task DEFERRED propagation, fail-closed preference/Synaptic/registry paths, and executor preflight semantics.

No new registry/manager/brain.

## CLASSIFICATION

STATIC / DESIGN RECHECKED / IMPLEMENTATION REVIEW READY / NO NEW ORGAN JUSTIFIED
