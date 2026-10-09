# CHAT-ARCH-2026-10-09-213 — RQ212 ADJUDICATION: LAUNCHER, UVICORN GAP, AND SOURCE PROVENANCE

## PROVENANCE / CANONICAL RECONCILIATION

Repository: `jhonf463r/Python`.
Canonical `main` observed before adjudication: `871baaa5b1ecccceb196c9ad9ce1480a1da2102f`.
Governing authorization: [RQ212](https://github.com/jhonf463r/Python/blob/871baaa5b1ecccceb196c9ad9ce1480a1da2102f/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-212-owner-authorization-static-launcher-uvicorn-and-source-hashes.md).
Prior technical adjudication: [RQ211](https://github.com/jhonf463r/Python/blob/871baaa5b1ecccceb196c9ad9ce1480a1da2102f/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-211-rq210-adjudication-fastmcp-lifecycle-and-permission-gates.md).

The Owner supplied the RQ212 Codex supplement in this conversation. Codex reports the target worktree as `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python`, detached at `e46d8304167708bed0764d3bf2be8fd6643e8944`, tree `52e51064967b8923dc7f200c10809971af9c558a`, with 386 porcelain-status entries. It reports modifications to `server.py`, `task_context_assembler.py`, two tests, cache and runtime/data files, and no worktree mutation. Canonical RQ209-RQ212 documents were absent from that local checkout; Codex did not retrieve them over the network, in accordance with RQ212.

The local identity, exact source hashes and source-state results are actor-reported evidence from Codex. The coordinator checked canonical GitHub memory but did not mount or hash the Windows worktree bytes independently. Preserve this provenance distinction.

## CLASSIFICATION

- Launcher/interpreter/transport static configuration: `COMPLETE_WITH_FINDINGS` within the RQ212 scope.
- Uvicorn exact version/source for the default interpreter: `BLOCKED_EXACT_SOURCE_UNAVAILABLE` at the reported local installation.
- SHA-256 supplementation for RQ210-cited files: `COMPLETE_WITH_ACTOR_REPORTED_HASHES`; local identities are provided by Codex, not independently rehashed by the coordinator.
- Overall MCP readiness: `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. Isolation and runtime readiness remain unestablished.
- RQ21.200 remains independent.

## LAUNCHER AND CONFIGURATION FINDINGS

The report states that `run_mcp_bridge.ps1` accepts `IABV_PYTHON`, defaulting to `C:\Users\faber\miniconda3\python.exe`, and `IABV_MCP_TRANSPORT`, defaulting to `streamable-http`. The script checks the interpreter path and starts `python -m iabv_v15.infra.mcp.server` through that selected interpreter. This is static launcher configuration only; it does not establish which interpreter or transport any live process used.

The report identifies a default-port discrepancy:
- PowerShell launcher default: port `8000`.
- `mcp_bridge_service.py` service default: `127.0.0.1:8765`.
- `docs/mcp-bridge.md` describes the script mode at port `8765`.

Treat this as a demonstrated source/documentation configuration inconsistency according to the submitted inspection. Its effective impact on a particular start is unresolved. The report further notes that the bridge service runs FastMCP in a daemon thread, and its `stop()` marks intent/clears references but does not itself prove FastMCP shutdown. The PowerShell script performs MCP process cleanup in `finally` after the tunnel command exits; this does not prove a universal guarantee that Ctrl+C always stops both processes under every condition.

The exact runtime launch parameters, loaded interpreter, actual transport and process-level effect remain unresolved. Do not investigate or inspect live processes under this record.

## UVICORN

The submitted report says no Uvicorn package/distribution metadata was found under `C:\Users\faber\miniconda3\Lib\site-packages`, which corresponds to the script's default interpreter path. The repository's `pyproject.toml` and root `requirements.txt` do not declare/pin `mcp` or `uvicorn`; bridge docs recommend installing them without fixed versions. The inspected default interpreter reportedly has local `mcp 1.27.0` metadata, but that is not proof of the dependencies available to an interpreter override or any target process.

Therefore exact Uvicorn version/source and its HTTP shutdown behavior remain blocked. The absence of Uvicorn in the inspected path does not, by itself, prove that every possible configured launch fails, nor that the HTTP server ran successfully. Do not install/download packages or use runtime execution to close this gap.

## SOURCE HASHES / PROVENANCE

The supplied report provides these local SHA-256 values:

| File | SHA-256 reported by Codex | Reported status |
|---|---|---|
| `src/iabv_v15/domain/models.py` | `9DF8859529D2C70BCA92C20E57FF18DC5B64049F357B82A2EB9FB9B150795449` | Clean |
| `src/iabv_v15/services/evolution/world_model_service.py` | `1EC9D521B560F06165D84D320FEBE82E1671FF80068CD045A13F8B6EEA29209F` | Clean |
| `src/iabv_v15/infra/mcp/server.py` | `434FEC9BC7C42759424C232FBC8042450218ABFDB6696F80DD6DCFE1FA61687C` | Modified |
| `src/iabv_v15/infra/mcp/self_update_tools.py` | `C70B186FF087C891930398D1A8BF3DA9DC071F1CB59E26FC7D5C272BFCC6FE32` | Clean |
| `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py` | `DC2FAF760ACC27A15DBB3FF8C6E50655473E69C6ADF63D0CF0FE3E593AA3548E` | Clean |
| `src/iabv_v15/services/evolution/mcp_bridge_service.py` | `0E88C865AF2469A78CAD9A36C4768021C4FE317E376650F0ECACEC0D31BE02F7` | Clean |
| `scripts/run_mcp_bridge.ps1` | `AEEE674DD33A1074B04961E19DFB8A403AD5EA11265B400D965736E08F07D29C` | Clean |
| `docs/mcp-bridge.md` | `BCED3217183650E5205EB67299532F9F7687518A47A0CE751F5B8A1CECE372A2` | Clean |
| `pyproject.toml` | `94EDC64627759AF8FD2297D680CF8223B9AE7ABAE6F79194CE2AE096BAE92BC0` | Not stated |
| `requirements.txt` | `D1535CB0505B1C298B96390E86171BAAB1E33B19E1B55BCD9C431E9CC897D5A8` | Not stated |

Paths above are relative to `IABV_v1.5`. The submitted report says `server.py` baseline blob was `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`; because the local file is modified, the current worktree hash cannot authenticate the baseline content. The report states that the other clean focal files match verified baseline blobs, but this adjudication does not independently remeasure the local files. Do not replace any of these reported local hashes with remote-main hashes.

The hashes close the deliverable gap as an actor-reported source inventory. Exact source-byte verification by the coordinator remains unperformed.

## FINDINGS

### DEMONSTRATED IN THE REPORTED STATIC SOURCE

- The script supports explicit interpreter and transport selection; its stated defaults are Miniconda Python and `streamable-http`.
- The report observes a source/documentation port-default mismatch: script `8000` versus bridge service/docs `8765`.
- Uvicorn was not found in the inspected default interpreter's site-packages.
- `server.py` is dirty and its current SHA-256 does not attribute its current content to the recorded baseline blob.
- No IABV code was run and the worktree was not changed, according to the supplied report.

### CONDITIONAL

- Whether the HTTP launch can start and what cleanup occurs depend on the actual selected interpreter, installed dependencies, transport path and tunnel exit path. Those runtime conditions were not established.
- The documented Ctrl+C shutdown claim is not proven for every case by the described script finalizer.

### UNRESOLVED

- Which interpreter, SDK version, transport and dependencies any target process uses.
- Exact Uvicorn source/version and its shutdown semantics under the selected interpreter.
- Actual effect of the port-default mismatch on a configured/real launch.
- Independent coordinator verification of the supplied local hashes and line anchors, due the Windows worktree not being directly available here.
- Any safe process isolation or runtime readiness conclusion.

## NEXT ROUTE

RQ212's authorized static supplement is complete to the extent that local files were available. The Uvicorn subquestion remains explicitly blocked because its exact source/version was absent from the inspected default interpreter and dependencies are not pinned. No further action in the existing scope can truthfully prove the dependencies of a live process. If stronger runtime attribution is later desired, it requires a separate owner authorization and a separate safety review; do not infer or perform it from this record.

Do not repeat RQ210/RQ212 wholesale. No MCP start/reconnect, MCP tool listing/call, SDK/runtime import/call, process inspection, probe, refresh, DB/secret/snapshot read, package installation/download, tests/builds, worktree change or source mutation. No RQ21.200 work.

END OF RECORD