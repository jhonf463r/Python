# CHAT-ARCH-2026-10-06-086 — UAAL-RQ13 BOOTSTRAP OBSERVATION AUTHORIZATION BOUNDARY

## STATUS
CANONICAL RECONCILIATION / STATIC SOURCE AUDIT / RUNTIME NOT AUTHORIZED

## OBJECTIVE
Reconcile the independent Sonnet/Claude audit performed against executable baseline `e46d8304167708bed0764d3bf2be8fd6643e8944` after the harness became READY, and determine whether an existing AppBootstrap route can satisfy the current authorization while excluding EnvironmentSelfAwarenessService and WorldModelService observation effects.

## PROVENANCE
- Baseline: `e46d8304167708bed0764d3bf2be8fd6643e8944`.
- Independent audit: source-only; no IABV runtime, AppBootstrap, SQLite runtime read, TASK mutation, MCP or provider execution.
- Audited: `bootstrap.py`, `main.py`, `environment_self_awareness_service.py`, `world_model_service.py`, plus `portable_context_service.py` for the target contract.
- Reported source hashes:
  - `bootstrap.py`: `acaaad95c15423192f6e88abaec6744b84a92514b336c79c24a7a793737e1d0a`
  - `main.py`: `e7b61e95bda9d8c7e5da4de393c19ab5f87b21c6dcaa3e8598653c832806550c`
  - `environment_self_awareness_service.py`: `195a6c91e5f53603915ae6ebfe47b70070811508c178de7f7fce2049438d8d25`
  - `world_model_service.py`: `1ec9d521b560f06165d84d320febe82e1671ff80068cd045a13f8b6eea29209f`
- Source bytes were reported as fetched from raw GitHub URLs containing the fixed commit SHA; no local Git object verification was performed in this audit.

## RECONCILED FACTS

### AppBootstrap
- `AppBootstrap.__init__(..., _defer_services=False)` wires services synchronously when not deferred.
- `main.py` uses `_defer_services=True` and later calls `_wire_services()`.
- `ObjectiveRepository` and `PortableContextService` are created during `_wire_services()`.
- No route in the inspected scope creates those services independently of the full bootstrap wiring.

### EnvironmentSelfAwarenessService
- `bootstrap_scan=True` performs synchronous `scan_now()`.
- `auto_start` can start a monitoring thread.
- `request_refresh()` uses the live thread asynchronously; without a live thread it calls `scan_now()` synchronously.
- `PYTEST_CURRENT_TEST` disables automatic thread start but does not eliminate scans; refreshes can therefore become synchronous.
- The service persists its scan model.

### WorldModelService
- `bootstrap_scan=True` performs synchronous `scan_now()`.
- `auto_start` can start a monitoring thread.
- `request_refresh()` is asynchronous with a live thread and synchronous via `scan_now()` otherwise.
- `IABV_MCP_SUBPROCESS=1` suppresses WorldModel bootstrap_scan but does not suppress the later `request_refresh()` calls.
- The service persists its snapshot.

### Deferred bootstrap
With `_defer_services=True`:
- constructor-level `bootstrap_scan` is disabled for these services;
- `_wire_services()` still performs earlier `request_refresh(reason='role_router_ready', full=False)` calls;
- the end of `_wire_services()` performs `request_refresh(reason='deferred_bootstrap', full=True)`;
- with live threads those refreshes can scan asynchronously and race the target;
- with no live thread they fall through to synchronous `scan_now()`.

### Target
The target `PortableContextService.current_package(refresh=True)` bypasses the cache and reaches `build_package()`; with no `task_context`, goal metadata is obtained through the ObjectiveRepository path.

## ROUTE ADJUDICATION

Primary conclusion within the inspected scope:

`BASELINE ROUTE = NOT AVAILABLE`

No existing inspected baseline route simultaneously provides:
- real AppBootstrap wiring;
- real ObjectiveRepository and PortableContextService;
- no EnvironmentSelfAwareness observation before target;
- no WorldModel observation before target;
- no asynchronous scan that can race the target;
- no production source modification;
- no manual service substitution.

The conclusion is scoped. It does not prove that no unrelated file anywhere in the repository contains another bootstrap route because `load_app_config`, the full tests/docs corpus, and some auxiliary bootstrap helpers were not exhaustively audited.

## EPISTEMIC CLASSIFICATION
- FACT: in the inspected scope, F is the only route adjudication satisfying the stated rule.
- FACT: the current authorization excluding bootstrap scans cannot be satisfied by that inspected baseline route.
- INFERENCE: with live deferred threads, scan completion can race the target.
- INFERENCE: allowing baseline bootstrap scans requires a revised experiment contract and does not by itself prove the target lookup result.
- ASSUMPTION: none.

## CLOSED
- controlled TASK persistence;
- source wiring;
- clean harness and exact SHA `C8DACA7DC0E9E21C63455FA29BA6DB75D579730D101ADDE55340A4933912D14C`;
- wrapper semantics and isolated self-test;
- independent orphan-oracle implementation/self-test;
- static bootstrap contamination audit;
- independent static adjudication that the current no-bootstrap-scan authorization is incompatible with the inspected baseline.

## NOT CLOSED
- runtime identity of AppBootstrap repository/PCS;
- actual SQLite/storage identity;
- actual no-orphan precondition;
- actual `latest_active()` results/exceptions;
- `active_objective_id` propagation.

## CURRENT FIRST OPEN EDGE
`human authorization contract → attributable baseline AppBootstrap observation boundary`

This is now an authorization boundary, not another unresolved source-archaeology question.

## ROUTING
NEXT ACTOR: HUMAN

Required decision:
- either authorize the baseline bootstrap observation effects explicitly;
- or leave the runtime observation NOT PROVEN under the current contract.

No authorization is inferred from prior harness authorization.

## METHOD / SYMBIOSIS DELTA
New invariant:
`deferred ≠ absent`.

New invariant:
`test-mode scan suppression ≠ production-equivalent no-scan route`.

New routing rule:
`baseline route unavailable under current evidence contract → human authorization decision`.

Do not bypass the boundary with monkey-patching, service substitution, private source modification, or hidden environment switches.

## NEXT MINIMUM EXPERIMENT IF AUTHORIZED
A newly authorized single runtime observation may:
1. start the exact baseline worktree with the new harness SHA;
2. record process provenance and real AppBootstrap object identity;
3. explicitly record the permitted EnvironmentSelfAwareness/WorldModel bootstrap effects;
4. establish the independent read-only orphan precondition;
5. observe `ObjectiveRepository.latest_active()` transparently inside exactly one `current_package(refresh=True)`;
6. independently verify post-observation SQLite row survival;
7. stop before P0/DecisionContext/MCP/providers.

END OF RECORD
