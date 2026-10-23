# M1A G1 — TPM projection-capture mechanism static review

- **Date:** 2026-10-23 (America/Bogota)
- **Task:** `M1A_G1_TPM_PROJECTION_CAPTURE_MECHANISM_STATIC_REVIEW`
- **Authorization:** Owner authorized this bounded review in chat; this did not authorize a new TPM command execution.
- **Active frontier:** `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`
- **Mode:** Static review of prior prompts/receipts, official cmdlet documentation, and canonical project state
- **Verdict:** `STATIC_REVIEW_COMPLETE_WITH_EXPLICIT_CAPTURE_REPAIR`
- **Runtime / PowerShell executed by coordinator:** `NOT_RUN`
- **Baseline:** `21907359cefd4582c4692f8e60f6348661e39b18`
- **Governance:** `KEEP_BLOCKED`

## 1. Whole-project frame — control tower, not a new brain

The North Star remains `GOVERNED_IABV_CODEX_BRIDGE`: a governed loop from IABV contextual request through an existing dispatch route, correlated Codex response, safe ingestion, evidence persistence/reload, and later decision effect.

The active frontier remains `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`. This local TPM observation is a diagnostic input, not the bridge itself and must not displace the primary outcome.

The dependency chain is:

`Owner authority → authenticated Windows principal → independently trusted issuer credential → exact IABV server-instance binding → independent reader enforcement → authoritative revocation → governed action`.

A TPM/EKCert observation would answer only limited questions about whether Windows reports a TPM object and whether EK certificate material is present. It cannot establish the end-to-end authority chain. Even local certificate-chain success does not identify the exact running IABV server process or prove independent Owner enrollment.

Previously investigated routes remain closed unless new evidence emerges: broad Windows bootstrap feasibility; GitHub-manifest/TPM trust design; Google OIDC; personal phone/passkey setup; independent TPM identity-pin design. No broad inventory, new credentials, self-reported target fingerprint as trust root, additional service, or unapproved spend.

## 2. Evidence boundary

### Owner-reported receipts

The Owner supplied the initial preflight, a recoverability check, and a corrected-capture retry. The latest retry reports one `Get-Tpm` invocation with `SUCCESS`, but `TPM_PRESENT`, `TPM_READY`, `TPM_ENABLED`, `TPM_ACTIVATED`, and `TPM_OWNED` are all `UNKNOWN`. `Get-TpmEndorsementKeyInfo` was not run; EKCert count and chain result have not been evaluated.

The coordinator did not run PowerShell or observe the Windows host. These results remain `OWNER_REPORTED`, not independently verified local observations.

### Public-source evidence

Microsoft documents `Get-Tpm` as returning a `TpmObject`; its example output includes the requested fields `TpmPresent`, `TpmReady`, `TpmEnabled`, `TpmActivated`, `TpmOwned`, `ManufacturerIdTxt` and `ManufacturerVersionFull20` ([Get-Tpm](https://learn.microsoft.com/en-us/powershell/module/trustedplatformmodule/get-tpm?view=windowsserver2025-ps)). Microsoft documents `Get-TpmEndorsementKeyInfo` as returning an `EndorsementKeyObject` with a `ManufacturerCertificates` X.509 certificate collection ([Get-TpmEndorsementKeyInfo](https://learn.microsoft.com/en-us/powershell/module/trustedplatformmodule/get-tpmendorsementkeyinfo)).

Microsoft's attestation guidance distinguishes EKCert verification from EK public-key trust and describes verification at a CA trust boundary ([TPM Key Attestation](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/component-updates/tpm-key-attestation)). Local presence or local chain construction alone is not independent Owner-to-exact-server trust.

### Repository/source-code limitation

A bounded public-repository search for `Get-Tpm`, `TpmPresent`, and the preflight task identifier returned no matching script/code artifact. That is a bounded search result, not proof that no such code exists elsewhere. The actual Codex execution script, raw safe diagnostic trace, tool invocation identifier, and property-capture implementation were not supplied. The original technical root cause is therefore `UNRESOLVED`.

## 3. Static findings

### F-CAP-01 — The “corrected capture” was not a reproducible implementation

The prior prompt described projection work in prose but did not include exact executable capture code or a per-field capture-state schema. A task name containing `CAPTURE_FIX` does not prove the mechanism was corrected.

### F-CAP-02 — The receipt collapses failure stages

`GET_TPM_RESULT=SUCCESS` and projected booleans `UNKNOWN` describe different stages. The receipt lacks the returned object count/type, property-existence observations, runtime value types, and projection/serialization status. It cannot distinguish command execution from property extraction or result transport.

### F-CAP-03 — Hardware state is still unknown

The reported `UNKNOWN` values do not mean `TPM_PRESENT=false`. Microsoft's documented output supports investigating the capture/projection boundary first, but does not prove whether the fault lies in the Codex execution context, object shape, capture code, host-result transport, or underlying environment.

### F-CAP-04 — No EK inspection follows from this receipt

Since `TPM_PRESENT` is not a captured Boolean `true`, the condition for querying EK info is unmet. No EK query or chain construction is justified under the supplied receipts. This diagnostic branch remains stopped pending a distinct authorization after the capture method is concretely specified.

## 4. Corrected capture design — proposed, not executed

The capture must separate command execution from projection status and emit a single JSON record built only from a new allowlisted projection:

1. Check cmdlet availability without invoking it.
2. Record the declared call count immediately before the one invocation.
3. Keep the returned value in memory and require exactly one non-null output object.
4. Inspect properties by explicit `PSObject.Properties['Name']` keys.
5. For each field, return `BOOLEAN_CAPTURED`, `PROPERTY_MISSING`, `NULL_VALUE`, `TYPE_MISMATCH`, or `PROPERTY_ACCESS_ERROR`, and a safe type name. Serialize the Boolean only when the actual value type is `System.Boolean`.
6. Report `GET_TPM_RESULT`, `OUTPUT_COUNT`, `OBJECT_TYPE`, and `PROJECTION_RESULT` separately.
7. Report manufacturer/version presence only; never disclose their values.
8. Serialize only the allowlisted projection. Never format or serialize the raw TPM object; never include `OwnerAuth`, raw exception messages, machine identifiers, key material, certificate subjects, serials or fingerprints.
9. Emit one JSON record on success or failure, and never retry or chain into `Get-TpmEndorsementKeyInfo`.
10. Keep EK inspection out of this task. Any future local chain check must separately guarantee certificate downloads are disabled before chain construction.

Static candidate code (not executed, installed or added to the product):

```powershell
$summary = [ordered]@{
  TASK = 'M1A_G1_TPM_CAPTURE_PROJECTION_DIAGNOSTIC'
  GET_TPM_CMDLET = 'UNRESOLVED'
  GET_TPM_CALL_COUNT = 0
  GET_TPM_RESULT = 'NOT_RUN'
  OUTPUT_COUNT = 0
  OBJECT_TYPE = 'NOT_AVAILABLE'
  PROJECTION_RESULT = 'NOT_RUN'
  FIELDS = [ordered]@{}
  MANUFACTURER = 'NOT_REPORTED'
  TPM_VERSION = 'NOT_REPORTED'
  ERROR_TYPE = 'NONE'
  STOP_REASON = 'NONE'
}
$commands = @(Get-Command -Name Get-Tpm -CommandType Cmdlet -ErrorAction SilentlyContinue)
if ($commands.Count -eq 0) {
  $summary['GET_TPM_CMDLET'] = 'UNAVAILABLE'
  $summary['STOP_REASON'] = 'CMDLET_UNAVAILABLE'
}
else {
  $summary['GET_TPM_CMDLET'] = 'AVAILABLE'
  $summary['GET_TPM_CALL_COUNT'] = 1
  try {
    # The only TPM query in this script. Keep its object in memory.
    $items = @(Get-Tpm -ErrorAction Stop)
    $summary['GET_TPM_RESULT'] = 'SUCCESS'
    $summary['OUTPUT_COUNT'] = $items.Count
    if ($items.Count -ne 1 -or $null -eq $items[0]) {
      $summary['PROJECTION_RESULT'] = 'UNRESOLVED_CARDINALITY'
      $summary['STOP_REASON'] = 'EXPECTED_EXACTLY_ONE_NON_NULL_OBJECT'
    }
    else {
      $tpmObject = $items[0]
      $summary['OBJECT_TYPE'] = $tpmObject.GetType().FullName
      $fieldNames = @('TpmPresent','TpmReady','TpmEnabled','TpmActivated','TpmOwned','LockedOut')
      foreach ($name in $fieldNames) {
        $entry = [ordered]@{ VALUE='UNKNOWN'; CAPTURE_STATE='NOT_PROCESSED'; VALUE_TYPE='NOT_AVAILABLE' }
        try {
          $property = $tpmObject.PSObject.Properties[$name]
          if ($null -eq $property) {
            $entry['CAPTURE_STATE'] = 'PROPERTY_MISSING'
          }
          else {
            $value = $property.Value
            if ($null -eq $value) {
              $entry['CAPTURE_STATE'] = 'NULL_VALUE'
              $entry['VALUE_TYPE'] = 'NULL'
            }
            elseif ($value -is [bool]) {
              $entry['VALUE'] = $value.ToString().ToUpperInvariant()
              $entry['CAPTURE_STATE'] = 'BOOLEAN_CAPTURED'
              $entry['VALUE_TYPE'] = 'System.Boolean'
            }
            else {
              $entry['CAPTURE_STATE'] = 'TYPE_MISMATCH'
              $entry['VALUE_TYPE'] = $value.GetType().FullName
            }
          }
        }
        catch {
          $entry['CAPTURE_STATE'] = 'PROPERTY_ACCESS_ERROR'
          $entry['VALUE_TYPE'] = 'UNAVAILABLE'
        }
        $summary['FIELDS'][$name] = $entry
      }
      foreach ($spec in @(
        @{ Name='ManufacturerIdTxt'; Target='MANUFACTURER' },
        @{ Name='ManufacturerVersionFull20'; Target='TPM_VERSION' }
      )) {
        try {
          $property = $tpmObject.PSObject.Properties[$spec.Name]
          if ($null -ne $property -and $null -ne $property.Value -and
              -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            $summary[$spec.Target] = 'REPORTED'
          }
        }
        catch { $summary[$spec.Target] = 'NOT_REPORTED' }
      }
      $allCaptured = $true
      foreach ($name in $fieldNames) {
        if ($summary['FIELDS'][$name]['CAPTURE_STATE'] -ne 'BOOLEAN_CAPTURED') { $allCaptured = $false }
      }
      if ($allCaptured) { $summary['PROJECTION_RESULT'] = 'COMPLETE' }
      else {
        $summary['PROJECTION_RESULT'] = 'PARTIAL'
        $summary['STOP_REASON'] = 'ONE_OR_MORE_FIELDS_NOT_CAPTURED_AS_BOOLEAN'
      }
    }
  }
  catch {
    if ($summary['GET_TPM_RESULT'] -eq 'NOT_RUN') { $summary['GET_TPM_RESULT'] = 'ERROR' }
    else { $summary['PROJECTION_RESULT'] = 'ERROR' }
    $summary['ERROR_TYPE'] = $_.Exception.GetType().FullName
    $summary['STOP_REASON'] = 'EXCEPTION_NO_RETRY'
  }
}
# Serialize only the allowlisted projection; never serialize or display the TPM object.
$json = ConvertTo-Json -InputObject ([pscustomobject]$summary) -Depth 7 -Compress
[Console]::Out.WriteLine($json)
```

## 5. Acceptance and stop criteria

A future, separately authorized run is acceptable for the capture subtask only if:
- the call count reflects exactly one attempted invocation when the cmdlet was available;
- command result, object count/type, projection result and every field's capture state are separately reported;
- the raw TPM object and sensitive fields never leave memory;
- all missing/unknown/type-error cases remain explicit and fail-closed;
- the exact single JSON record is returned, not reconstructed from model prose;
- no EK cmdlet, network, file writes, configuration changes, authentication, key creation, tests, build, product runtime or automatic follow-on occurs in this capture subtask.

This review does **not** authorize a new invocation. The next action is an Owner decision: `AUTHORIZE_ONE_FIXED_TPM_CAPTURE_RUN` or `CLOSE_TPM_PREFLIGHT_BRANCH`. Do not ask the Owner to run PowerShell manually; use the intended Codex session only if it is actually available and can return a correlated execution receipt. If unavailable, report `NOT_RUN`, never invent a run.

## 6. UAAL / space-time causal update

This is a method refinement under `UAAL-ROOT-001`, not a parallel coordinator or new “brain”. Derivation:

`repeated UNKNOWN projection → source-grounded object/property contract → separate execution/output/projection states → fail-closed decision → future falsifier`.

The future falsifier is one separately authorized run returning these precise structural diagnostics. Saving this method is not proof of runtime learning: `COORDINATOR_RUNTIME=NOT_PROVEN` and `CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN` remain in force until a later run demonstrates the revised schema actually distinguishes the previously hidden failure stage.

## 7. Reconciled state

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
LAST_TERMINAL_TASK=M1A_G1_TPM_PROJECTION_CAPTURE_MECHANISM_STATIC_REVIEW
CAPTURE_MECHANISM_REVIEW=STATIC_REVIEW_COMPLETE_WITH_EXPLICIT_CAPTURE_REPAIR
CAPTURE_IMPLEMENTATION=PROPOSED_NOT_EXECUTED
CAPTURE_ROOT_CAUSE=UNRESOLVED
TPM_AVAILABILITY=UNVERIFIED
EKCERT_AVAILABILITY=UNVERIFIED
TPM_ATTESTATION_TRUST=NOT_ESTABLISHED
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
NEXT_ACTION=OWNER_DECISION_ONLY
AUTOMATIC_FOLLOW_ON=FALSE
COORDINATOR_RUNTIME=NOT_PROVEN
CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN
```

No product code, tests, build, runtime, local checkout or real transport was accessed by the coordinator during this review.
