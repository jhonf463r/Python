# R10 v0.7.6 change map

| File | Field / row | Previous | New | Finding | Class |
|---|---|---|---|---|---|
| `R10_V0_7_5_CONTRACT.md` (logical contract v0.7.5) | Opening metadata `Artifact ID` | `R10_V0_7_4_CONTRACT` | `R10_V0_7_5_CONTRACT` | HI-01 | Authorized identity repair |
| `R10_V0_7_5_TEST_MATRIX_T123_T246.csv` | T157 `crash_retry_conflict_oracle` | Generic before/after atomic boundary | Post-durable-P2-commit crash; replay retains C1 retracted and C2 active; one visible contribution; no reapplication/revival; explicit falsifier | HI-02 | Authorized oracle repair |
| same | T222 `normative_basis` | `§17` | `§17.7` | HI-03 | Traceability repair |
| same | T223 `normative_basis` | `§17` | `§1.3; §8.3` | HI-03 | Traceability repair |
| same | T224 `normative_basis` | `§17` | `§17.7` | HI-03 | Traceability repair |
| same | T225 `normative_basis` | `§17` | `§17.7` | HI-03 | Traceability repair |
| same | T226 `normative_basis` | `§17` | `§4.1; §17.2` | HI-03 | Traceability repair |
| same | T227 `normative_basis` | `§17` | `§7.1; §17.2` | HI-03 | Traceability repair |
| same | T228 `normative_basis` | `§17` | `§7.1; §17.2` | HI-03 | Traceability repair |
| same | T229 `normative_basis` | `§17` | `§8.2` | HI-03 | Narrowed to supporting clause; proposed §17.4 omitted as non-supporting |
| same | T230 `normative_basis` | `§17` | `§2.2; §17.2` | HI-03 | Traceability repair |
| same | T231 `normative_basis` | `§17` | `§3.2; §17.1` | HI-03 | Traceability repair |
| same | T232 `normative_basis` | `§17` | `§17.2` | HI-03 | Traceability repair |
| same | T233 `normative_basis` | `§17` | `§8.3; §17.4` | HI-03 | Traceability repair |
| `README.md`, changelog, consistency report, review prompt, change map, preflight report, manifest | Packaging metadata / evidence | v0.7.5 package labels and hashes | v0.7.6 package identity and recomputed hashes; contract explicitly stays logical v0.7.5 | Packaging | Non-normative |

No other matrix cells or contract clauses are authorized to change. Historical payloads are retained byte-for-byte.