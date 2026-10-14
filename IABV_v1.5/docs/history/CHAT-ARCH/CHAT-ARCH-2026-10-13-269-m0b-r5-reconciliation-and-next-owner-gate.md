# CHAT-ARCH-2026-10-13-269 — M0B-R5 reconciliation, source-anchor correction, and next Owner gate

- Episode ID: CHAT-ARCH-2026-10-13-269
- Reported local time (America/Bogota): 2026-10-13, approximately 20:40–20:45
- Documentation baseline before this write: main at d77f04e2fe9a02d28803d95d8856c31effda4ffa
- Pinned source-code baseline: 559f4ea20a9a9163cd9a9839b11d9991933f8c07
- Input: owner-supplied M0B-R5 result, M0B_R5_CONTRACT_SPECIFIED_PUBLIC_SOURCE_BASELINE_PINNED_KEEP_BLOCKED
- Classification: M0B_R5_SOURCE_CLAIMS_RECONCILED; CITATION_ANCHORS_PARTIALLY_MISMATCHED; SCOPED_AUTHORITY_DISCOVERY_OWNER_GATE_PENDING
- Posture: KEEP_BLOCKED for local M0A, implementation, tests/runtime, and Codex/App Server launch

## 1. R5 adjudication

R5's core architecture conclusion is consistent with the pinned public source: audit readers pass through _governance_block_for_route; a refused route can return block metadata; the public observation-permission path is not a repository-read grant; and the inspected public surfaces do not provide a distinct, demonstrated audit-release plus exact-checkout-scoped read decision. This is a bounded source result, not a global claim about all branches or local M0A.

R5's source anchors need correction before reuse. The report says that live main and blob IDs were not independently verified, and several line ranges do not correspond to the named declarations in the pinned commit. A fresh fetch of exact files at 559f4ea20a9a9163cd9a9839b11d9991933f8c07 yields these blob identities and anchors:

| Source | Verified Git blob | Correct anchor in that exact blob | Adjudication |
|---|---|---|---|
| infra/mcp/server.py | 17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c | _governance_block_for_route line 377; world_model_snapshot 493; autonomy_status 510; autonomy_update_task 527; read_repo_file 930; list_repo_directory 950 | R5 reader citation at L853–894 does not point to read_repo_file in this blob. |
| domain/models.py | a9033d21052c519e09f482097599c704a62ea916 | OperationalBlockRecord line 593; fields through line 604 | R5 L557–579 does not point to this model in this blob. |
| services/evolution/world_model_service.py | ba0b5f5d6233330b549e09863975c77c0db735d6 | grant_observation_permission line 154; revoke_observation_permission 176; _block_records 1199 | Grant/revoke claim is corroborated; cite exact declaration ranges. |
| ui/viewmodels/control_center_viewmodel.py | 628848c631e36b47b4a5b63b9e68d62687625235 | _grant_pending_observation_permission line 11843; ingestExternalResponse 14239 | R5 L11312–11358 does not point to the grant declaration in this blob. |
| tests/test_control_center_viewmodel.py | 0d31cb847bde49fcd0287a59419f1e9440ab5c5f | Relevant test starts at 667; assertion for observe_window_content:codex is at 836 | R5 L724–780 does not contain that assertion in this blob. |
| infra/mcp/audit_tools/__init__.py | c1e468f4e504f778e7e9c366a05d549d42be84de | resolve_workspace_path 130; read_repo_file 206; list_repo_directory 272 | Use these anchors for path/reader controls, not R5's unverified L54–82 range. |

This is a provenance/citation defect, not by itself a refutation of R5's main control-flow conclusion. Do not repeat a broad audit; use the corrected blob/line anchors as current source evidence. The public OperationalBlockRecord model has no explicit expires_at field; report expiry as unknown unless a separately proven authority/decision record supplies it.

## 2. Verified source-level facts

- PROVEN_BY_SOURCE: read_repo_file and list_repo_directory call _governance_block_for_route with assistant_kind=audit and requires_network=false before performing the audit-tool operation.
- PROVEN_BY_SOURCE: the gate fails closed when WorldModel is unavailable, its read fails, or its snapshot is missing. Its active-block filter currently checks assistant_kind, not target_scope. This is a separate semantic risk, not a demonstrated cause of the M0A refusal.
- PROVEN_BY_SOURCE: grant_observation_permission records an observation-specific grant. Control Center calls it with observe_window_content:<assistant>, then retries the external consultation. The tested Codex scope is observe_window_content:codex. None of those edges proves repository-read authorization.
- PROVEN_BY_SOURCE: world_model_snapshot exposes a broader operational snapshot; autonomy_status and autonomy_update_task represent continuity/task state, not audit-read authorization.
- PROVEN_BY_SOURCE, bounded: no separate diagnostic-only interface plus separate scoped audit-read-decision interface was found in the inspected MCP/WorldModel/Control Center surfaces.
- UNPROVEN: actual payload from the prior blocked local call; live M0A server identity, checkout root, branch and contents; equivalent mechanisms in uninspected/private/local paths; existence of an issuer/verifier for the proposed scoped read receipt.

Reader guardrails are already meaningful and must be preserved: workspace-contained relative paths, traversal/absolute-path checks, sensitive-file restrictions, a 1 MiB single-file limit and 200-entry directory-list cap. A future scoped grant may narrow those guards, never replace or weaken them.

## 3. Contract result — specified, not implemented

R5 has completed the public contract-design task. Keep these functions separate:

1. Narrow diagnostic: only applicable block/permission identifiers, categories, scopes, statuses, provenance/reason codes and expiry if an actual source provides it. It does not read repository files or grant access.
2. Separate read decision: binds a proven server/workspace/checkout identity, operation class, explicit relative-path allowlist, byte/file/entry/call limits, expiry, issuer/authority provenance and a unique decision ID.
3. Normal reader: revalidates identity, decision, expiry, budget and path before each read/list. Global or otherwise applicable active blockers remain in force unless an explicitly authorized decision mechanism is proven to resolve the specific block; no implicit override.
4. Missing, unknown, mismatched, stale or denied identity/decision fails closed. Observation permission never satisfies repository-read authorization. Diagnostic output cannot be used as permission.

The design is specified; the implementation route and legitimate issuer/verifier have not been found or authorized.

## 4. Reconcile with existing Owner decisions

- RQ219/RQ220 already closed their bounded discovery as NO_EXISTING_TRUSTED_AUTHORITY_FOUND_IN_SCOPE. Do not rerun that same broker/UI/mutator search.
- Current canonical state already records Model A selected for the first supervised MCP prototype. Do not ask A/B again. Model A is a threat-model assumption only; it does not identify an authority, prove a receipt, authorize broader source discovery or grant repository access.
- The separate read-only audit gate is not automatically authorized by RQ223 mutation-authority design.
- Remaining Owner gate: whether to authorize a distinct, tightly bounded, read-only examination of additional existing public identity/authority sources beyond the paths already inspected, solely to locate an existing issuer/verifier for the exact read decision. This decision is not implied by Model A or R5.
- No Owner action should ask for manual code collection. The Owner decides only whether to authorize that scope expansion; Codex performs the technical source investigation if authorized.

## 5. Next actor / next action

Next AI after explicit scope authorization: Codex, as a read-only public-source archaeologist. Follow only direct references/call sites from already known approval/identity types into the smallest adjacent code needed to establish whether an existing authenticated Owner principal/authority producer and decision/receipt verifier can be reused for a read-only repository grant. Stop immediately at a broader identity/auth subsystem, secrets/credentials, or unrelated systems. Do not repeat RQ219/RQ220 paths; do not invent a trust root.

This expanded scope is not yet authorized. Until the Owner gate is resolved, do not send an expanded-source-search prompt as if permission exists. R5's contract and source evidence remain usable; local M0A stays blocked.

## 6. Verification boundary

The coordinator performed read-only GitHub retrieval of exact pinned source objects and current continuity. This episode did not read local M0A, invoke any local reader/MCP tool, launch IABV/Codex/App Server, run tests/builds, edit source/configuration, access credentials, authenticate, install/update software, call an AI model API, incur paid usage or change runtime state. Canonical writeback is documentation-only.

## 7. Exact Owner authorization text for the next phase

If the Owner decides to authorize the bounded scope expansion, the decision should be explicit and limited to this exact action:

AUTORIZO una investigación estática y de solo lectura de las fuentes públicas existentes de identidad/autoridad directamente relacionadas con la emisión o verificación de una decisión de lectura de repositorio, fuera de los caminos ya examinados en RQ219/RQ220 y M0B-R5. El alcance se limita a seguir referencias y llamadas directas necesarias para identificar si ya existe un principal autenticado del propietario y una autoridad/emisor/verificador reutilizable. No autoriza lectura del checkout local M0A, reintento o elusión del lector bloqueado, consulta de secretos/credenciales, ejecución de procesos, pruebas, builds, modificación de archivos, implementación, instalación/actualización, nuevas autenticaciones ni gasto adicional. Detenerse antes de entrar en un subsistema general de identidad/autenticación, y devolver evidencia con blob SHA, líneas exactas y procedencia.

Only after this authorization should Codex receive the bounded prompt. This is an Owner scope decision, not a request for the Owner to perform technical research.
