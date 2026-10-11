# M0 Windows Sandbox write-containment kit

**State:** preparation only. The write-containment gate remains **BLOCKED_BY_MISSING_WRITE_CONTAINMENT**.

This kit prepares a disposable Windows Sandbox check for a sanitized fixture. It does not launch IABV, QML, Codex, a desktop UI, or an external service. A pass demonstrates mapped-folder behavior inside that Sandbox session only. It does not prove the real Codex process is launched in that context, that credentials are isolated, or that runtime/I2 is ready.

## Contents and scope

- tools/security/m0_write_containment_probe.ps1: harmless probe to run manually inside Windows Sandbox as its default WDAGUtilityAccount.
- tools/security/m0_write_containment.template.wsb: two mapped folders, networking disabled, no logon command.
- This runbook.

The WSB template has deliberately invalid host-path placeholders. Do not open it until both paths are replaced and reviewed.

The guest may write to its own ephemeral filesystem. The intended persistent host mappings are limited to the read-only fixture and the explicitly writable state folder. This is not a claim that the guest process cannot write to its own ephemeral filesystem or that any actual Codex process uses this Sandbox.

## Preconditions

An owner or administrator prepares a disposable fixture and a separate empty state folder under a temporary location. Do not map C:\Python, the normal checkout, a user profile, a home directory, a browser profile, credential stores, or any folder containing secrets.

The fixture must be a sanitized disposable copy of the IABV_v1.5 checkout subtree, or a minimal fixture with the same probe path. It must contain:

1. M0-READ-CANARY.txt with exactly M0_READ_CANARY_V1
2. M0-DELETE-CANARY.txt with exactly M0_DELETE_CANARY_V1
3. tools\security\m0_write_containment_probe.ps1

Create both canaries before mapping. They must have ordinary inherited permissions from the fixture directory. Do not set a Read-only attribute or restrictive/custom ACL on either canary or the fixture to manufacture a denial. Do not put real project data or secrets in the fixture. The state folder must be different and empty, with no symlink/junction to another location.

### Required host write preflight

Before opening Sandbox, the administrator must run a host-side preflight using the same host identity (and non-elevated context) that will open Sandbox. Use only the disposable fixture directory; do not touch the checkout, state folder, ACLs, privileges, or global configuration. The check must prove create, read, modify, and delete access and restore both canaries exactly. An unset `Read-only` file attribute alone is not evidence that host writes work.

For example, in a PowerShell session under that identity, substitute the exact disposable fixture path below. This snippet operates only on the two named canaries and one uniquely named temporary file; it does not use recursive deletion:

```powershell
$fixture = 'C:\path\to\disposable\fixture'
$readPath = Join-Path $fixture 'M0-READ-CANARY.txt'
$deletePath = Join-Path $fixture 'M0-DELETE-CANARY.txt'
$probePath = Join-Path $fixture ('M0-HOST-PREFLIGHT-' + [guid]::NewGuid().ToString('N') + '.tmp')
$readExpected = 'M0_READ_CANARY_V1'
$deleteExpected = 'M0_DELETE_CANARY_V1'
$ok = $false
try {
    if ([IO.File]::ReadAllText($readPath) -cne $readExpected -or
        [IO.File]::ReadAllText($deletePath) -cne $deleteExpected) {
        throw 'Initial canary contents are not exact; stop.'
    }
    [IO.File]::WriteAllText($probePath, 'M0_HOST_CREATE_V1')
    if ([IO.File]::ReadAllText($probePath) -cne 'M0_HOST_CREATE_V1') { throw 'Create/read check failed.' }
    [IO.File]::WriteAllText($readPath, 'M0_HOST_MODIFY_V1')
    if ([IO.File]::ReadAllText($readPath) -cne 'M0_HOST_MODIFY_V1') { throw 'Modify check failed.' }
    [IO.File]::Delete($probePath)
    if ([IO.File]::Exists($probePath)) { throw 'Delete check failed.' }
    [IO.File]::Delete($deletePath)
    if ([IO.File]::Exists($deletePath)) { throw 'Canary delete check failed.' }
    [IO.File]::WriteAllText($readPath, $readExpected)
    [IO.File]::WriteAllText($deletePath, $deleteExpected)
    $ok = $true
} finally {
    # Best-effort restoration is explicit and non-recursive. A failure is a hard stop.
    if ([IO.File]::Exists($probePath)) { [IO.File]::Delete($probePath) }
    if ([IO.File]::ReadAllText($readPath) -cne $readExpected) { [IO.File]::WriteAllText($readPath, $readExpected) }
    if (-not [IO.File]::Exists($deletePath)) { [IO.File]::WriteAllText($deletePath, $deleteExpected) }
    if ([IO.File]::ReadAllText($readPath) -cne $readExpected -or
        [IO.File]::ReadAllText($deletePath) -cne $deleteExpected -or
        [IO.File]::Exists($probePath)) { throw 'Could not restore and verify exact canary state; stop.' }
}
if (-not $ok) { throw 'Host write preflight did not complete; stop.' }
```

The administrator must retain a record that all four operations succeeded and both exact canary contents were restored and verified. If any operation, restoration, or verification fails, stop and do not open Sandbox. The Sandbox result may be attributed to the read-only mapping only after this host preflight succeeds.

Windows Sandbox is supported by Microsoft on Windows Pro, Enterprise, Pro Education/SE, and Education editions, not Home. It requires the Windows Sandbox feature and hardware virtualization. Have the administrator confirm availability through the supported Windows UI. This kit does not run elevated feature queries or enable Windows features.

Microsoft documents .wsb XML configuration, absolute existing host paths, ReadOnly=true for a read-only mapped folder, and network configuration. Networking and clipboard redirection are enabled by default, so this template explicitly disables them. References:
- https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file
- https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview

## Prepare and review disposable host folders

1. Make a new temporary fixture directory and a separate empty temporary state directory. Keep both outside the normal checkout and user profile.
2. Copy only sanitized files into the fixture. Create the two canary files with the exact contents above. Keep the delete canary writable on the host before mapping; the Sandbox mount, not a pre-set file attribute, must enforce denial.
3. Confirm both paths exist, are absolute, distinct, and do not contain or resolve into C:\Python or a user profile. Inspect the fixture for secrets. Do not put the state directory under the fixture.
4. Open the template as text and replace both __REPLACE_WITH_...__ host paths with exact paths. Keep Sandbox destinations C:\M0Fixture and C:\M0State, fixture ReadOnly true, state ReadOnly false, and networking disabled. Do not add a logon command or credential/profile mappings.
5. Review the completed XML as text. Do not launch it if a placeholder remains, a host path is broad, or the state folder is not empty and separate.

## Run manually inside Sandbox

1. The administrator opens the reviewed .wsb manually. This kit does not open it.
2. Inside the guest, check the token identity is WDAGUtilityAccount. The helper independently checks the Windows token identity and stops as INCONCLUSIVE before touching either mapped path if it differs.
3. In a PowerShell window inside the guest, run:

   powershell.exe -NoProfile -File C:\M0Fixture\tools\security\m0_write_containment_probe.ps1 -FixtureRoot C:\M0Fixture -StateRoot C:\M0State

4. On its normal path, the helper writes a JSON report in C:\M0State, reads it back, and emits a stdout summary confirming `report_persisted=true`. Preserve the report and that summary. If a precondition fails before the report can be written (including an identity mismatch), or report read-back cannot be verified, the helper emits JSON only on stdout; that console JSON is not a persisted report. Preserve such output as a screenshot captured by the administrator's approved host-side evidence process into its already authorized evidence location; do not enable clipboard/drive redirection, shell redirection, or additional shared folders just to capture it. If it cannot be preserved and matched to a persisted report, classify the result INCONCLUSIVE. The identity-mismatch path stops before the helper accesses either shared folder.
5. Preserve the completed WSB configuration with host paths redacted to safe labels, the report, Sandbox/Windows version and edition, and safe temporary path identities. Record that networking was disabled and no Codex/IABV process was started.
6. Close Sandbox and confirm its disposable guest state is discarded. Retain the report outside the Sandbox state folder if needed. Remove only the two explicitly created temporary host folders after review using the administrator's normal file-management process; do not use recursive cleanup commands from this kit.

## Report interpretation

The report records read, create, modify, delete, state write, state read, state cleanup, and an overall result.

- PASS: the host write preflight succeeded; the read returned the expected fixture canary; each negative operation raised identifiable Windows access denied (ERROR_ACCESS_DENIED, code 5 / 0x80070005) and its postcondition remained intact; state write/read/explicit cleanup succeeded; and the persisted report was read back and verified.
- FAIL: a prohibited fixture operation unexpectedly succeeded or a required postcondition was violated (including changed/missing canary contents).
- INCONCLUSIVE: a precondition was missing, denial could not be identified as OS access denied, or verifiable persisted evidence is missing. A setup error or absent report is never a PASS.

Only an all-PASS report is evidence that this Sandbox configuration enforced the requested operations against the mounted disposable fixture. A failure means stop and inspect the mount/configuration; do not proceed to Codex. Inconclusive is not evidence of containment or its absence.

## Next gate and limits

This is an environment probe, not an application-launch test. Even a complete pass does not establish that ui_execution_runner uses Sandbox, that Codex runs inside the same guest token, that the isolated guest has the required application/session, or that credentials can be supplied without exposing the real profile. The subsequent integration must route the actual child through a reviewed isolated runner and prove the same security context before any live trial. A live UI trial still requires separate owner authorization.

If Windows Sandbox is unavailable, ask the administrator to provide an equivalent disposable VM/runner with a read-only host checkout fixture, a distinct explicitly writable state mount, network disabled for this probe, a known non-host principal, and a way to run the helper under the exact context the later target would receive. Do not substitute a path check, prompt instruction, or Job Object alone.
