# Space-Time Signal and Temporal Provenance R1 — candidate receipt

Date: 2026-11-04 (America/Bogota)
Task: IABV_SPACE_TIME_SIGNAL_AND_TEMPORAL_PROVENANCE_R1_20261104
Base main: 56e4d8b11846a8d8f3cb8cda08efd773ec235651
Scope: isolated candidate branch; no merge, production activation or M1A gate change.
Owner authorization: explicit approval in the current conversation for ST-M01 through ST-M04.
Status: CANDIDATE_CODE_AND_TESTS_PREPARED; TESTS_NOT_RUN.

## Advance contract (UAAL-D019 / D020)

Objective: preserve Control Master decision signals across full and compact prompts and preserve temporal/source provenance in portable and task context.

First open edge: the Control Master digest is built but omitted from compact prompts; queue read errors collapse into empty lists; partial startup-health flushes renew whole-package freshness; recommendation source time is omitted from the task projection.

Expected observable: full and compact prompts include queue status and next actions; failures remain UNAVAILABLE; section-only writes preserve the last complete-generation time; portable-context output exposes freshness against the caller's requested window; task insight projections retain the original recommendation creation timestamp.

Stop: do not merge, activate runtime, or run CI while GitHub Support billing review is pending. No force-push, history rewrite, secret export, protected read or M1A gate change.

## Changes

ST-M01 — PortableContextPackage now distinguishes last full generation from last partial mutation. The MCP response includes FRESH, STALE or UNVERIFIED, the age, the requested/effective age windows and whether the rich-snapshot extension was used. Legacy full snapshots fall back to created_at_utc; lightweight unresolved packages remain UNVERIFIED and cannot renew full-context freshness.

ST-M02 — the compact prompt now accepts the existing ControlMasterDigest and includes its queue, objective and risk signals. The full prompt renders the queue status and work items.

ST-M03 — TaskContextAssembler preserves ExperimentRecommendation.created_at_utc.

ST-M04 — queue statuses distinguish AVAILABLE, EMPTY_QUEUE, UNAVAILABLE and UNVERIFIED. A failed queue read no longer becomes an empty list.

Follow-on hardening commit: 2f7f48437f7a9d9251ee798bd15ff576b786805a. It ensures lightweight unresolved packages remain UNVERIFIED (not fresh) and moves compact-prompt next actions ahead of lower-priority summary fields so they survive truncation.

## Source and regression baseline

| Path | Base blob | Candidate blob |
|---|---|---|
| IABV_v1.5/src/iabv_v15/domain/models.py | a9033d21052c519e09f482097599c704a62ea916 | 84c19ae819bbb25e9dc1a5d6ad950d4b001faf5f |
| IABV_v1.5/src/iabv_v15/services/evolution/control_master_digest_builder.py | a7bd6d8390095e5dff22dcaa6fcb79d22378df15 | 36e5cb09d6ae257031f049d9e5c9f564a53eae4b |
| IABV_v1.5/src/iabv_v15/services/llm/system_prompt_builder.py | 8dfded0bfb1e08fbb691e293f566a1551bf71ed3 | 8b1073c2ac9b64b6f248172ee5c730085952416b |
| IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py | 41f6f7b6157226a1c6004591ddff4e36ff6f6da5 | 1bfbd36c30598ffd1015f6749852603f3fa6f159 |
| IABV_v1.5/src/iabv_v15/services/evolution/portable_context_service.py | 021cbe829e96099494444b33275423f8d6319dc6 | 4957f22364ff8d9b46cce399dd287a201afa8b59 |
| IABV_v1.5/src/iabv_v15/infra/mcp/server.py | 17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c | 22a26601fa44bb554f7bc25b3b9f0c9e0b4dc052 |
| IABV_v1.5/src/iabv_v15/services/adaptive/task_context_assembler.py | c5a6852a6a82a0c60886ea4bb6c236f50fe4a57c | 39e601ededea5adcd1d01a65964988825b21be30 |
| IABV_v1.5/tests/test_canonical_work_queue.py | acc8f162b44234ad55893c4cbcf7b8f62db59560 | 654954d7dba713822d4c35237d1081d7bdcd7bbe |
| IABV_v1.5/tests/test_system_prompt_builder.py | 98557d8cbdac45e47529fb1133c8d9276e0e2408 | 7f7bbec0a37144a82aac3cd77fdf6057af4d1d23 |
| IABV_v1.5/tests/test_portable_context_service.py | e03732d5d447218bb50988ed42a1e5ab9e0ecdf5 | 0f713383e2241464a66b9d910195bddf565a1b68 |
| IABV_v1.5/tests/test_mcp_server.py | 93c11837d39eaee60d2c818e522284f0f9c261d6 | 6770c9920f8e1ddb1141fa2cb033bd2ed442739b |
| IABV_v1.5/tests/test_space_time_context_contracts.py | new | 2cdd4ff5773109d8ca21b65682396787ac170933 |

## Control Master and support signal intake

Committed Control Master snapshot last observed: 2026-04-19T19:23:46.389095Z; status STALE. Live runtime digest UNAVAILABLE; no runtime, CLI, tunnel or bridge was started. The stale snapshot did not determine this action.

GitHub Support ticket #4910849: acknowledgement received; resolution pending. No Actions workflow was run or retried.

## No-merge / no-activation receipt

main remains at 56e4d8b11846a8d8f3cb8cda08efd773ec235651. G1/G2/G3 remain NOT_ESTABLISHED. OPTION_D=RATIFIED_NO_BOOTSTRAP. PROTECTED_READS=FAIL_CLOSED. BRIDGE=NOT_READY. M1A permissions unchanged. Tests/build/runtime NOT_RUN. No credentials or payment data included. Merge is not authorized by this receipt.