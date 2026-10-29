# M1A F-556-01 continuity promotion — 2026-10-29

**Status at creation:** proposed continuity update on an isolated documentation branch. It does not update canonical `main`; adoption requires its documentation PR to merge and the result to be fetched back.

## Verified references at preparation

- Repository: `jhonf463r/Python`.
- Live `main`: `79ab8c50eaa7518120d5ebed9db4747d395a21cb`.
- `CURRENT-STATE.md` at that revision: blob `5945b23fdb5c13ce1068ca5d2d9e6513a1a06b95`. The raw-content request returned 404; the exact commit object was read from the existing Git object store after verifying live `main`.
- Root `AGENTS.md` is absent at this revision; `IABV_v1.5/AGENTS.md` is present (blob `1b7b84b86693cfecefbc6c7dc8c3c41f607d5a07`). No deeper `AGENTS.md` applies under the documentation path.
- Entry 274 normative source: `CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md`, blob `5943a87d907436fc7ecac31534cbfcd31fe7de55`. It requires whole-list denial above 200 entries with `LIST_LIMIT_EXCEEDED` and no partial names.
- PR #555: open, draft, unmerged, base `main`, branch `codex/m1b-context-reader`, HEAD `c36ee5ed177a3b5afee764c277cc4a8b243594c8` (`VERIFIED` through authenticated GitHub CLI metadata).
- PR #556: open, draft, unmerged, base `main`, branch `codex/m1a-current-main-fail-closed-20261028`, HEAD `fb635aab18d9c2ef19b20d48e3625d52383fe6af` (`VERIFIED` through authenticated GitHub CLI metadata).

## M1A / PR #556

Commit `c00c1677e7b1f891e757f141450672b04443eba4` changed directory overflow handling from returning partial names to denying the whole listing. Its direct child, `fb635aab18d9c2ef19b20d48e3625d52383fe6af`, aligned the exception reason with `LIST_LIMIT_EXCEEDED` and added a synthetic case with 201 valid entries and `max_entries=250`.

The published PR head and its metadata both identify `fb635aab18d9c2ef19b20d48e3625d52383fe6af`. Fetch-back verified these file blobs:

| File | Blob at published HEAD |
|---|---|
| `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py` | `6c178a1b0644f7a7d33eb794e76f38bf59efe58a` |
| `IABV_v1.5/tests/test_windows_handle_reader.py` | `e20e11a2ae743ad45f18ea2514f61d9e3d27c172` |

Codex reported the focused suite as 31 passed with Python 3.13.2 / pytest 9.0.3, exit code 0, and `git diff --check` successful. These execution claims are `OWNER_CODEX_REPORTED`; this continuity task did not rerun tests. Synthetic records do not establish native Windows enumeration behavior.

## Independent review boundary

The prior Claude R1 report, as supplied in the continuity input, concerns HEAD `e1b430956146c4aa0cadc1df2c3df92150b7f7ea` and records G1-WIN-02 as partial-name disclosure at that older revision (`OWNER_REPORTED`). Independent static review of exact delta `c00c1677e7b1f891e757f141450672b04443eba4` → `fb635aab18d9c2ef19b20d48e3625d52383fe6af` remains pending. G1-WIN-01 and G1-WIN-03 remain separate open findings as reported; this change neither reviews nor repairs them.

## M1B / PR #555

GitHub metadata verifies PR #555 is open, draft, unmerged, based on `main`, at HEAD `c36ee5ed177a3b5afee764c277cc4a8b243594c8`. Its description reports 37 passing tests from an API-backed minimal harness. The harness used its own pytest root and did not load repository-level pytest configuration; this is not a full-checkout suite run. The execution remains `OWNER_CODEX_REPORTED`, not an independent run.

```text
M1B_SOURCE_PUBLICATION=PR_PUBLISHED
M1B_MAIN_INTEGRATION=NOT_DONE
```

This supersedes the older time-specific M1B-local-only statement in the prior continuity record. The historical statement is preserved below the overlays, not deleted.

## Repeated repair attempt

The repeated F-556 repair task stopped because its required starting baseline `c00c1677...` had already advanced to `fb635aab...`. The attempt made no file changes, ran no tests and published nothing. It was scope control, not a product regression (`VERIFIED` from this session's task actions).

## Next causal edge and operational posture

Next edge: independent static review of exact delta `c00c1677...` → `fb635aab...`. This receipt does not start that review.

```text
OPTION_D=RATIFIED_NO_BOOTSTRAP
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
MERGE=NOT_AUTHORIZED
C:\Python=DO_NOT_TOUCH
```
