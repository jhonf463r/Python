# R10 v0.7.7 change map

| Artifact | Field | Before (frozen v0.7.5) | After (v0.7.7) | Classification |
|---|---|---|---|---|
| `R10_V0_7_5_CONTRACT.md` | Opening `Artifact ID` | `R10_V0_7_4_CONTRACT` | `R10_V0_7_5_CONTRACT` | HI-01 identity repair |
| `R10_V0_7_5_TEST_MATRIX_T123_T246.csv` | T157 `crash_retry_conflict_oracle` | Generic before/after commit-boundary text | Post-durable-marker-only P2 crash; committed C1/C2 state retained; one visible contribution; no reapply/revival; explicit falsifiers | HI-02 oracle repair |
| Same | T222 `normative_basis` | `§17` | `§17.7` in field 12 | HI-03 |
| Same | T223 `normative_basis` | `§17` | `§1.3; §8.3` in field 12 | HI-03 |
| Same | T224 `normative_basis` | `§17` | `§17.7` in field 12 | HI-03 |
| Same | T225 `normative_basis` | `§17` | `§17.7` in field 12 | HI-03 |
| Same | T226 `normative_basis` | `§17` | `§4.1; §17.2` in field 12 | HI-03 |
| Same | T227 `normative_basis` | `§17` | `§7.1; §17.2` in field 12 | HI-03 |
| Same | T228 `normative_basis` | `§17` | `§7.1; §17.2` in field 12 | HI-03 |
| Same | T229 `normative_basis` | `§17` | `§8.2` in field 12; §17.4 omitted as non-supporting | HI-03 |
| Same | T230 `normative_basis` | `§17` | `§2.2; §17.2` in field 12 | HI-03 |
| Same | T231 `normative_basis` | `§17` | `§3.2; §17.1` in field 12 | HI-03 |
| Same | T232 `normative_basis` | `§17` | `§17.2` in field 12 | HI-03 |
| Same | T233 `normative_basis` | `§17` | `§8.3; §17.4` in field 12 | HI-03 |
| All v0.7.6 artifacts | Disposition | Published candidate claimed preflight complete | Frozen failed preflight; coordinator found 13 CSV fields in T222–T233 | Provenance correction; v0.7.6 unchanged |
| v0.7.7 package docs/manifest | Outer release metadata | v0.7.5 package labels | v0.7.7 package labels; logical contract/matrix stay v0.7.5 | Packaging only |

These are the only permitted content-cell differences from frozen v0.7.5: the contract Artifact ID and 13 matrix cells (T157 oracle and T222–T233 normative bases). CSV quoting/serialization may be normalized by the structured writer; parsed cell values outside the authorized delta are identical.
