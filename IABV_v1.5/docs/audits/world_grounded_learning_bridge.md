# World-grounded learning bridge (branch-local experiment)

## Observation

G3 can perform a protected action, independently observe filesystem state, and
classify the expected-versus-observed transition as `verified` or
`verification_failed`.

## Gap

That verification previously stopped in the returned G1 trace and did not
reach the B-loop interaction learner.

## Intervention

`VerifiedTransition` persists identity, action, target, expected and observed
state, verification, and provenance.  `InteractionLearningService` records it
and updates dedicated verified-transition counters on `InteractionPattern`.
`InteractionModeSelector` considers those counters without changing legacy
`success_count`, `failure_count`, or `ExperimentRun.success` semantics.

## What this proves

The producer has a bounded production path from a G3 verified transition to
the existing B-loop persistence and selector data model.

## What this does not prove

It does not prove universal learning, a world model, autonomy, P0-B closure,
or structural evolution.  Runtime acceptance remains blocked here by the
pre-existing missing `post_action_observer` module imported by
`ToolTeachService` during test collection.

## Invariant

`actor_reported_success != independent observation`; a verified outcome is not
generic execution success.
