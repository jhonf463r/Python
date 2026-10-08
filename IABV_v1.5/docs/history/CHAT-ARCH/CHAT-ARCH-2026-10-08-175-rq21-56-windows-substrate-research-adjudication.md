# CHAT-ARCH-2026-10-08-175 — RQ21.56 WINDOWS VALIDATION-SUBSTRATE RESEARCH ADJUDICATION

## PROVENANCE

Repository: `jhonf463r/Python`.

Verified remote `main` immediately before this adjudication:
`b432806baa7d184fe7eafda14bb794af6ca9618e`.

Expected research execution identity from the corrected task:
- EXECUTION_ID: `BROWSE_2026-10-08_RQ21-56-WINDOWS-SUBSTRATE_001`
- OBJECT_ID: `RQ21-OBJ-WINDOWS-DYNAMIC-VALIDATION-SUBSTRATE_001`

The supplied result body did not visibly reproduce those identities or provide an auditable claim-level bibliography. This is a provenance/contract observation about the material received, not proof that the research product UI never saw the prompt.

Canonical object lock:
**The minimum Windows realization substrate for running a potentially malicious candidate under bounded containment, observing attributable protected effects E, keeping validation criterion X inaccessible to the candidate, producing independently verifiable evidence, closing observation after quiescence, and binding evidence to the exact candidate/environment.**

Pinned IABV executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
Tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

No IABV source code was modified and no runtime experiment was executed during this adjudication.

## ADJUDICATION

**RQ21.56 = REJECTED AS A COMPLETE TECHNICAL RESEARCH DELIVERABLE; PARTIAL TOPIC DISCOVERY ONLY.**

The report is materially closer to the requested topic than RQ21.55: it addresses Windows sandboxing and runtime monitoring rather than researching Deep Research itself. Therefore this is not the same total object substitution.

It still fails to answer the discriminating object: a source-audited comparison of concrete Windows primitives/compositions against the seven owner-authorized guarantees and a bounded statement of what Windows supplies versus what IABV must add.

### Acceptance-gate results

1. **OBJECT ALIGNMENT: PARTIAL.** The report stays in the broad Windows sandbox/security domain, but expands heavily into generic endpoint defense, malware detection, credential protection and security recommendations. It does not keep the seven-guarantee realization substrate as the controlling object.
2. **REQUIRED COVERAGE: FAIL.** It does not supply the requested seven-row guarantee matrix; does not adequately compare AppContainer/restricted tokens, Job Objects, service identity and delegation, Named Pipes/ACLs, WFP, ETW, Hyper-V/Windows Sandbox, evidence custody, X secrecy, quiescence and artifact/environment binding as a composed system.
3. **SOURCE SUPPORT: FAIL.** The final source statement names categories of sources but omits directly usable primary-source URLs and claim-by-claim attribution. Citations cannot be independently traced from the result as submitted.
4. **EVIDENCE QUALITY: FAIL.** It does not demonstrate exact target-build/API availability, execution/evidence boundary behavior, completeness or loss semantics for observation, or an independently verified composition. Proposed hook/driver ideas remain synthesis, not evidence.
5. **METHODOLOGICAL RIGOR: FAIL.** No attack-test matrix was actually executed or reported with setup, expected result, observed result, and limitation. There is no source audit or falsification table tied to the seven guarantees.
6. **SYNTHESIS QUALITY: PARTIAL.** The report is organized and has some correct background, but length and breadth do not repair the missing technical contract comparison.

## INDEPENDENT CLAIM AUDIT

The following checks were performed independently against Microsoft documentation. They are new coordinator-side source checks, not claims that the submitted report itself supplied verifiable citations.

### A. AppContainer is not limited to packaged/UWP applications

The report's comparison table says AppContainer applies only to Store/UWP apps. That is too categorical and incorrect as a platform-wide claim. Microsoft documents AppContainer for legacy/unpackaged applications and provides APIs for creating AppContainer processes. See:
- https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-
- https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer

### B. Windows Sandbox networking is enabled by default but configurable

The report's broad phrase that Windows Sandbox does not isolate network traffic obscures the actual documented configuration. Networking is enabled by default through a host virtual switch and can be explicitly disabled with a `.wsb` configuration. Enabled networking may expose untrusted applications to the internal network. This distinction matters: default connectivity/exposure is not the same statement as a categorical inability to disable networking.
- https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file

### C. ETW is instrumentation, not proof of complete E observation

ETW logs events emitted by enabled providers; Microsoft also documents cases where ETW events can be lost due to buffer, consumer and storage constraints. Therefore, enabling ETW or using Sysmon does not itself demonstrate complete coverage of protected effect categories E, attribution of all delegated causal paths, or evidence integrity.
- https://learn.microsoft.com/en-us/windows/win32/etw/about-event-tracing

### D. Historical/platform security controls do not automatically implement the IABV predicate

WDAC, HVCI/VBS, Credential Guard, AppContainer, Windows Sandbox and EDR can each provide valuable, distinct restrictions or protections. Their existence does not prove the joint predicate:
`effective containment + complete attributable E observation + hidden X + deterministic X comparison + protected evidence custody + quiescent closure + candidate/environment binding`.

Any claim that a control participates in the required composition must identify the exact guarantee, API/policy, boundary, threat assumption, uncovered path and independently observable failure behavior.

The report's reference to a Microsoft "ResearchKit" mechanism is not substantiated by the supplied bibliography. Do not propagate that named mechanism without a verifiable primary source.

## NEW INDEPENDENTLY DISCOVERED CANDIDATE — NOT APPROVED / NOT PROVEN

During claim verification, Microsoft Learn surfaced a directly relevant experimental Windows API omitted by the supplied report:

**`Experimental_CreateProcessInSandbox` and `Experimental_CreateProcessAsUserInSandbox`**
Primary source:
https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox

The documentation says the APIs create a process using a compiled sandbox specification. It marks them **experimental and subject to change**, lists `processmodel.dll` as the DLL, says the header is not publicly available (use `GetProcAddress`), and lists Windows 11 (experimental) as the minimum supported client. The page was last updated 2026-06-01.

The documented spec includes:
- AppContainer isolation;
- integrity level controls;
- a Win32k system-call disable mitigation;
- Job Object UI restrictions;
- explicit AppContainer capabilities;
- read-write/read-only filesystem path restrictions;
- a network policy/proxy field;
- a unique sandbox identity and a versioned FlatBuffer specification.

The same documentation cautions that a process already in AppContainer cannot call the APIs and that the nested-sandbox threat model is not finalized. A `ui_restrictions` field's documented Job Object use must not be interpreted as proof that all required process-tree lifecycle, delegation, evidence or quiescence guarantees are supplied.

Microsoft's Windows Insider documentation places build family 26300 in the Windows 11 26H2 preview/release-preview family:
https://learn.microsoft.com/en-us/windows-insider/flight-hub
That makes the experimental API a relevant candidate to check on the target; it does **not** establish that the exact supplied image `10.0.26300.0` exports the API or that the feature is enabled there.

### Provisional mapping to the seven guarantees

| Owner-authorized guarantee | What current documentation supports | Status for the complete RQ21 predicate |
|---|---|---|
| 1. Contain candidate and attributable descendants/delegation | AppContainer, filesystem/network restriction fields and an experimental process launcher are documented. Full descendant/delegated IPC/loopback/local-service attribution is not established by this page. | PARTIAL CANDIDATE; NOT PROVEN |
| 2. Observe protected effects E by category | The API page does not define an E observer or a complete category/channel oracle. ETW/WFP are separate possible components, each requiring coverage and loss analysis. | NOT PROVIDED BY THIS API; COMPOSITION UNPROVEN |
| 3. Protect evidence custody/integrity/authenticity/completeness | No independent evidence authority, authenticated origin, anti-erasure guarantee or sealing protocol is established by this API page. | IABV SUBSTRATE REQUIRED / UNPROVEN |
| 4. Keep X inaccessible to candidate | AppContainer/filesystem restrictions may help enforce access boundaries, but no full hidden-reference lifecycle, read-path protection, caller obligations or residual partition is established. | PARTIAL PRIMITIVE; NOT PROVEN |
| 5. Deterministic comparison against X | No X comparator or independent acceptor is part of the documented API. | IABV VALIDATOR REQUIRED |
| 6. Close observation after quiescence/final state check | The documentation does not establish all attributable actors are quiescent or that evidence is sealed after a final state check. | NOT PROVIDED / UNPROVEN |
| 7. Bind evidence to exact candidate/version/configuration/environment | A sandbox identity and process launch data exist, but the page does not establish a verified candidate digest and environment descriptor bound to authenticated evidence. | NOT PROVIDED / IABV EVIDENCE CONTRACT REQUIRED |

This is a bounded mapping of published documentation, not a claim that the API cannot be composed with additional Windows mechanisms. The correct next question is whether this API is present and usable on the exact target, and which of the remaining guarantees require separate mechanisms.

## EPISTEMIC CLASSIFICATION

### FACT — verified from current official documentation
- Microsoft documents the experimental `Experimental_CreateProcessInSandbox` family and its documented AppContainer/filesystem/network/integrity/Win32k/UI-restriction fields.
- The same page marks the APIs experimental, says the header is not public, and names `processmodel.dll`.
- Microsoft documents AppContainer for legacy/unpackaged apps.
- Windows Sandbox networking is enabled by default and can be disabled by configuration.
- Microsoft documents ETW event loss conditions.
- The supplied report, as received, does not provide claim-level source links or the requested seven-guarantee matrix.

### INFERENCE
- The report is not sufficient to close the technical research frontier or authorize a technology choice.
- The experimental process launcher is a plausible candidate for a **subset** of launch-side containment requirements and deserves explicit investigation before IABV implements a parallel launcher.
- The experimental API cannot be treated as the complete RQ21 substrate based on the documented functions above.

### UNPROVEN
- Whether the exact target `10.0.26300.0` exports both required experimental functions and the required SandboxEngine/schema at runtime.
- Whether its actual behavior contains malicious candidates, descendants and delegated IPC/loopback/local-service effects to the owner-authorized boundary.
- Whether this API composes with the required observation, X secrecy, evidence-custody, quiescence and artifact-binding mechanisms.
- Any performance or compatibility estimate for this exact composition.
- The actual execution identity/provenance of the supplied Deep Research run.

## ROUTING

RQ21.56 does not close either open Owner scope point and does not authorize implementation.

The current normative frontier remains the two RQ21.54 Owner confirmations:
1. R8 partition — substrate-guaranteed channels vs caller/interface obligations vs declared residuals;
2. temporal adversary scope — candidate/control/delegation during the validation window, excluding post-window behavior of a promoted candidate from the first guarantee.

After those confirmations:
`Owner decisions → ChatGPT contract freeze → focused feasibility audit of Experimental_CreateProcessInSandbox on the exact target and its seven-guarantee composition → independent verification → Codex implementation only if readiness/coverage supports it`.

Do not route directly to implementation from this report. Do not infer that an experimental API is available solely from the build-family label. Do not change the authorized contract to fit the available API.

## DELTAS

**Knowledge Delta:** The submitted report contains broad background but no accepted complete substrate solution. Independent primary-source verification has surfaced a documented experimental process-sandbox API that was absent from the report and from the bounded substrate comparison; it is a candidate primitive, not a proven solution.

**Method Delta:** For technical platform research, require a table mapping every owner-authorized guarantee to (a) primary source/API/policy, (b) enforcement boundary, (c) observation/evidence source, (d) uncovered channels and failure mode, (e) target version availability, and (f) evidence needed to prove the claim. Reports that omit this mapping cannot close the substrate question.

**Routing Delta:** Preserve Human Domain Owner for the two normative scope confirmations. Before implementation, add a focused target/API-availability and composition-feasibility audit. The submitted report alone does not advance the frontier.

END OF RECORD
