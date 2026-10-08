# CHAT-ARCH-2026-10-08-142 — RQ21.28/RQ21.29 PRE-SELECTION CAPABILITY CONTRACT RECONCILIATION

## PURPOSE

Absorb the RQ21.28 and RQ21.29 Codex audits into canonical IABV continuity memory and correct the provenance state of the prior panorama writeback.

This record supersedes the routing implications of the unpromoted 2026-10-07-141 writeback while preserving its durable methodological lessons.

## CANONICAL PROVENANCE

- Current remote main: 5b1d89022ee4cdc63c1f88e050f086b40a42875c
- Current executable tree: ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61
- Commit 781f2f62da376cfbdd37e0ae847a4ccba12c7374 exists and has parent 5b1d89022ee4cdc63c1f88e050f086b40a42875c, but remote main currently still points to 5b1d890.
- Therefore 781f2f62 is historical/unpromoted for canonical-main purposes; its knowledge is absorbed by this record and the accompanying documentation updates.
- No executable source change is authorized by this record.

## RQ21.28 — ADJUDICATION

RQ21.28 tested the exact semantic unit behind ToolTask → required capability.

Outcome: D — no existing candidate defines an exact operative R_task.

Directly reconciled facts:
- CapabilityReadinessService._required_capabilities() is intent-key based and does not inspect task operations.
- AdaptiveSession.capability_readiness exists upstream but is not transported into ToolTask.
- StrategyPack.required_capabilities is a parallel intent/pack declaration, not proven task authority.
- PlaybookStep.capability_id is singular and is not consumed as a complete task requirement set.
- ToolCard.capabilities describes offered operations, not abstract task requirements.
- CapabilityDescriptor is not proven operative.
- ToolTask has no first-class requirement identity.

RQ21.28 therefore closed the question 'is there already an exact reusable task-level capability contract?' as NO / D for the inspected paths.

## RQ21.29 — NEW FACTS

RQ21.29 tested the semantic source available before concrete ToolCard selection.

### Causal order

For ToolTeachService.build_task_from_request() the observed order is:

1. receive InferenceRequest;
2. derive suggested_tool_id;
3. create draft ToolTask and invoke InteractionModeSelector.select();
4. apply Synaptic/explicit external overrides where applicable;
5. determine final tool_id;
6. call _build_actions(request, tool_id, reusable_pattern);
7. construct final ToolTask;
8. execution later re-resolves through ToolRegistry.pick_card_for_task().

### Critical correction

ToolTask.actions is MIXED:

- explicit goal_parameters.actions can exist before selection;
- generated actions in _build_actions() can depend on the selected tool_id.

Therefore ToolTask.actions is not, in the general route, an independent source of R_task.

Using post-selection generated actions to justify the same selection would be circular.

### Pre-selection semantic candidates

The audited candidates were:

- InferenceRequest: contains objective, role, scope, site and goal parameters; no capability IDs.
- TaskIntent: contains intent semantics/metadata but is projected incompletely into the request.
- goal_parameters.actions: can express concrete operations such as RUN_COMMAND, LLM_QUERY and MCP_CALL; no operation→abstract-capability transform is present in the inspected path.
- execution_scope, task_role and site_hint: contextual constraints, not complete capability requirements.
- CapabilityReadiness / StrategyPack.required_capabilities: exist upstream but are not used as per-task eligibility inputs.
- ToolCard.capabilities: candidate offers, not requirements.

### Discrimination result

- tools.local_workflow: same broad intent with different operations can be represented through request actions; the readiness mapping cannot distinguish them into different abstract capability requirements.
- tools.sandbox: distinct operations can be represented, but no pre-selection operation→capability mapping consumes them.
- system.metacognition: producer metadata requires_mcp_tools exists, but build_task_for_session() does not transfer it; no capability transformation was found.

Thus R_task = f(intent_key) is insufficient whenever one intent can contain materially different operations.

### A–E capability-source test

No candidate in the focal path passed all five conditions:

A. exists;
B. is available before selection;
C. has an operative consumer;
D. is independent of the selected realization;
E. expresses required capabilities rather than offered capabilities.

## RQ21.29 ADJUDICATION

C — the operation semantics can be represented pre-selection, but the baseline lacks an operative transformation from those semantics to abstract capability IDs.

This is more precise than the prior D-level finding.

The first-open edge is now:

concrete pre-selection operation semantics → consumed operation→capability transformation → R_task

not simply:

intent → R_task.

## NON-CIRCULARITY RULE

Never derive the requirement contract from a realization chosen using that same requirement.

Reject paths of the form:

selected ToolCard → generated ToolTask.actions → inferred R_task → justification of selected ToolCard

as circular.

Likewise, ToolCard.capabilities are supply/realization properties and cannot retroactively define the demand side of the task.

## HARD INVARIANTS REINFORCED

- session capability set ≠ per-ToolTask requirement set
- intent_key ≠ exact task requirement
- task operation semantics ≠ capability IDs unless an operative mapping exists
- ToolTask.actions = MIXED and cannot automatically be treated as independent demand semantics
- ToolCard.capabilities ≠ R_task
- post-selection artifact ≠ independent pre-selection oracle
- selection → generated actions → inferred requirement is circular
- candidate eligibility ≠ scoring
- empty candidate set ≠ unrestricted fallback
- selector result ≠ final route when downstream resolution can overwrite it

## KNOWLEDGE DELTA

Closed:
1. No exact existing R_task rule is operative in the inspected task-selection path.
2. Intent-level readiness is too coarse to represent materially different operations inside one intent.
3. Concrete operation semantics can exist before ToolCard selection.
4. No valid pre-selection operation→abstract-capability transformation was found in the focal path.
5. ToolTask.actions cannot safely serve as the universal independent requirement source because generation is partly post-selection.
6. The capability-realization problem is therefore a demand-side semantic translation gap, not merely a missing selector score or empty-set branch.

## METHOD DELTA

The routing protocol gains a mandatory causal-order test:

pre-selection semantics → requirement transformation → eligibility → selection → realization-specific artifacts

Before treating any artifact as R_task, establish that it exists independently of the realization whose eligibility it is supposed to constrain.

A useful discrimination test is same intent + different operation. If the desired requirements differ, an intent-key-only requirement function is too coarse.

## ROUTING DELTA

Current actor: CODEX.

Reason:
- uncertainty is source/causal-order semantics;
- no runtime evidence is required;
- no independent adversarial audit is yet needed to choose the next narrow source trace.

Next experiment:
A single read-only trace of one real caller for each focal intent that establishes:
1. whether goal_parameters.actions is actually produced before build_task_from_request();
2. whether those actions are stable request semantics or merely tool-specific generation inputs;
3. whether any existing consumer before selection transforms an operation into a capability identity.

Target callers:
- tools.local_workflow
- tools.sandbox
- system.metacognition

No implementation.
No runtime.
No selector-scoring changes.

## INFORMATION-GAIN JUSTIFICATION

The remaining competing hypotheses are:
- H1: existing callers already provide a sufficiently explicit task-operation contract;
- H2: caller semantics are present but not stable/complete enough;
- H3: operation semantics exist but capability identity must be introduced as a minimal composition/wiring step;
- H4: the real task unit is upstream of the inspected request path.

The caller trace has lower intervention cost and higher discrimination than another broad repository audit or runtime experiment.

## CURRENT STATUS

RQ21.28 = CLOSED / D
RQ21.29 = CLOSED / C
CAPABILITY → REALIZATION IMPLEMENTATION = BLOCKED
RUNTIME = NOT AUTHORIZED
NEXT = RQ21.30 NARROW CALLER-PROVENANCE TRACE

## NO-GO

Do not yet:
- add required_capability_ids;
- add realizes_capability_ids;
- create a universal capability manager/registry;
- use ToolTask.actions as a circular requirement oracle;
- modify selector scoring;
- repeat RQ21.27C;
- run runtime experiments before the demand-side semantic contract is closed.