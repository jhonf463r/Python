# M1A G1 — TPM/EKCert corrected-capture preflight failure

- **Date:** 2026-10-23 (America/Bogota)
- **Task:** `M1A_G1_TPM_EKCERT_READ_ONLY_PREFLIGHT_RETRY_CAPTURE_FIX`
- **Parent:** `M1A_G1_TPM_EKCERT_OUTPUT_RECOVERABILITY_CHECK`
- **Active frontier:** `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`
- **Mode:** One-call read-only retry with sanitized in-memory projection
- **Result:** `BLOCKED_TPM_FIELDS_NOT_CAPTURED`
- **Governance:** `KEEP_BLOCKED`
- **Baseline before this documentation-only writeback:** `deaccf614cbf5cbd9a0159b1cd49835d84e00a9a`

## 1. Verdict

The corrected-capture retry did not produce a usable TPM-state projection. The supplied receipt says `Get-Tpm` was available and completed successfully with exactly one call in this retry, yet `TPM_PRESENT`, `TPM_READY`, `TPM_ENABLED`, `TPM_ACTIVATED`, and `TPM_OWNED` all remain `UNKNOWN`. Since the presence test was not unequivocally true, `Get-TpmEndorsementKeyInfo` was not run and EK certificate count/validity and offline-chain validation remain `NOT_RUN`.

This is an **evidence-capture/projection failure**, not evidence that the TPM is absent, broken, or present. The specific reason why the requested properties were not captured is unresolved. The successful command status alone does not establish a boolean property value.

## 2. Evidence and provenance

**OWNER_REPORTED** — this receipt records the JSON result supplied by the Owner at approximately 09:52 America/Bogota; the coordinator did not independently invoke a command on the target Windows host.

The preceding recoverability check reported that an execution trace existed but contained only the sanitized JSON projection; the original output/object was unavailable. That check did not re-run `Get-Tpm`. The corrected-capture retry then reported:

- `TARGET_CONTEXT=CONFIRMED`
- `GET_TPM_CMDLET=AVAILABLE`, `GET_TPM_RESULT=SUCCESS`, `GET_TPM_CALL_COUNT=1`
- All five requested TPM Boolean fields: `UNKNOWN`
- `EK_INFO_CMDLET=AVAILABLE`, `EK_INFO_RESULT=NOT_RUN`, `EK_INFO_CALL_COUNT=0`
- `EKCERT_COUNT=UNKNOWN`, `EKCERT_VALIDITY=NOT_RUN`, `LOCAL_OFFLINE_CHAIN=NOT_RUN`
- `NETWORK_USED=NO`, `FILES_WRITTEN=NONE`, `CONFIGURATION_OR_TRUST_STORE_CHANGED=NONE`
- Authentication/credential creation, product changes, tests, build, and product runtime: none/not run as reported.

No certificate-chain verdict can be inferred from a check that was never performed. The reported absence of network and filesystem side effects has not been independently measured by this coordinator.

## 3. Reconciled state

```text
LAST_PREFLIGHT_RESULT=BLOCKED_TPM_FIELDS_NOT_CAPTURED
TPM_AVAILABILITY=UNVERIFIED
TPM_ATTESTATION_TRUST=NOT_ESTABLISHED
EKCERT_AVAILABILITY=UNVERIFIED
EKCERT_CHAIN_VALIDITY=NOT_EVALUATED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
OWNER_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
READER_VERIFICATION=NOT_ESTABLISHED_END_TO_END
REVOCATION_AUTHORITY_AND_CONSISTENCY=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

## 4. Stop rule / anti-repeat

The initial preflight and the later corrected-capture retry both left the TPM-state projection unknown. Treat this read-only preflight branch as **terminal for now**. Do not repeat `Get-Tpm`, perform another recovery lookup, or run `Get-TpmEndorsementKeyInfo` under the same unsuccessful capture method. A future attempt requires a demonstrably corrected capture mechanism and separate explicit authorization. No implementation, tests, build, runtime, credential creation, installation, configuration change, or trust-store change is authorized by this receipt.

The project's main blocker remains the independent authority chain from Owner authorization to a Windows principal and issuer credential, binding to the exact IABV server instance, plus reader-side enforcement and revocation. Even a future successful TPM/EKCert check would be only one input; it would not, by itself, establish G1.

## 5. Canonical lineage

This report is a terminal task receipt and a routing update, not a new design baseline. The canonical route remains `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`, with `NEXT_ACTION=OWNER_DECISION_ONLY`. The five canonical source files were re-fetched and their existing blob IDs checked immediately before this documentation-only writeback.

| Canonical file | Parent blob |
|---|---|
| `IABV_v1.5/AGENTS.md` | `d466ff3319ee5ac985cb45b0e8bc015ec9059fb9` |
| `IABV_v1.5/docs/history/CHAT-ARCH/README.md` | `754ec8f7970a51b49e97cc56d0a2d3438a58c040` |
| `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` | `bd4f4b8934fc664a19e40da8c439a73f397cfdcb` |
| `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md` | `14774901ab0ff8c49638d4e17342741d91db5066` |
| `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md` | `cfae23c3d35e3196d5df80aea8c3c819517f48a0` |

No product code or runtime behavior was changed.
