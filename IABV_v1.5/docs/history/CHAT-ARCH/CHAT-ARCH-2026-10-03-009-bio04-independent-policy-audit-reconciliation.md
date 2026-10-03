# CHAT-ARCH-2026-10-03-009 — BIO-04 Independent Policy Audit Reconciliation / Method Correction

## SOURCE

Actor: Sonnet / Claude-class
Mode: independent read-only source/contract audit
Target technical SHA: d1a55897bf7f758914b8237d48ae43f245f06592
Compared against canonical main: 69b1b5b9c6f8f3c52a202ec373afe39e87f2017a
No production runtime, no provider execution, no external network.

## PRIMARY RESULT

Sonnet independently confirms the main Codex characterization, but narrows several claims and explicitly corrects its own previous recommendation.

Classification remains:

GOVERNANCE SEMANTIC GAP

First open edge remains:

OSES context construction → request-level data classification / policy.

The key refinement is that the gap is not generic selector wiring. Existing privacy-related mechanisms are partial, distributed across other domains, and not causally connected to OSES.

## INDEPENDENTLY VERIFIED FACTS

- OSES has two relevant context construction routes that eventually reach the cloud-first reasoning helper.
- Cloud use on that path is conditioned on presence of provider credentials, with no additional request-level privacy gate identified.
- OSES context can include identity, browser/session metadata, local environment metadata, tool/resource information, provider state and free-form operational findings.
- Runtime values were not observed in this audit.
- ProviderRouter exists in source but has no production instantiation in the audited source tree.
- contains_sensitive_data and redacted_for_cloud have no production producer in src; they appear in tests and ProviderRouter consumption.
- Production callers inspected do not pass exclude or world_model to AdaptiveModelSelector.
- AdaptiveModelSelector.exclude is a filtering mechanism, not an expressive request-level privacy policy.
- When all cloud candidates are excluded, the selector still returns ollama_local; excluding ollama_local does not produce an empty permitted set in the tested fixture.
- No repository test covers the OSES cloud-first context route.

## CONTEXT REFINEMENT

Codex's description of local/browser data is narrowed:
- process data is keyword-matched;
- Windows window titles are filtered and capped;
- cookie values are never read, only counts;
- only specific environment metadata enters the rendered context;
- full_name may be collected by a scanner without being rendered.

All such data remain SOURCE-PROVEN as possible context content, while concrete runtime presence remains NOT PROVEN.

## PARTIAL POLICY SEMANTICS

Existing but disconnected precedents include:
- email masking in other orchestration/capture domains;
- RedactionEngine in browser capture flows;
- browser-teach/capture-related local-only behavior in ProviderRouter;
- ObservationPermissionGate for permission to observe assistant windows.

These are partial precedents, not an OSES transmission policy.

Critical distinction:

observation permission != transmission permission.

## OWNERSHIP RECONCILIATION

The repository does not demonstrate:

context category → request-level policy → permitted realization set

for OSES.

Therefore the semantic owner remains unresolved.

## IMPORTANT METHOD CORRECTION

Sonnet explicitly corrected its own earlier recommendation.

Previous premature interpretation:
ProviderRouter privacy predicates → existing exclusion seam → next implementation.

Reconciled interpretation:
The privacy classification itself has no demonstrated upstream producer on OSES. Therefore implementation should not be dispatched before the policy semantics are defined.

New method invariant:

existing parameter ≠ existing semantic ownership.

Additional invariant:

existing policy precedent in another domain ≠ policy coverage in the target causal path.

## DEVELOPMENTAL-FIELD OBSERVATION

This episode provides a concrete method-level observation:

The newly established method rule caused the audit to inspect producer/consumer ownership before treating an existing filter as reusable policy. Sonnet also identified and retracted its own prior premature recommendation.

This demonstrates an observable method change in the participating collaboration.

It does NOT by itself prove that the method change was caused by persistent GitHub state rather than the explicit prompt/context. Therefore classify:

method-use observed = YES
causal learning from persistent field = NOT PROVEN

## HUMAN POLICY BOUNDARY

The next decision is normative and must remain human-owned.

Questions:
1. Which OSES context categories are local-only?
2. Which may be remote/cloud permitted?
3. Which require redaction/transformation?
4. Which require explicit authorization?
5. What is the behavior when classification is unknown?
6. What happens when no allowed realization remains?
7. Is the local endpoint itself required to satisfy a locality/integrity contract?

No actor should silently choose these policies as an implementation convenience.

## MINIMUM POST-POLICY EXPERIMENT

After the human policy is specified:

synthetic OSES context
→ policy classification
→ permitted realization set
→ selector behavior
→ transport stub assertion

with:
- no real network;
- no credentials;
- no provider execution;
- no selector scoring change;
- all-remote-excluded case;
- explicit locality test if local-only is selected.

Baseline expectation should be captured before implementation. Current OSES helper is expected not to honor the policy because it bypasses the selector/governance seam.

## DEVELOPMENTAL FRONTIERS

DOMAIN FRONTIER:
human policy definition for OSES request-level data handling.

DEVELOPMENTAL FRONTIER:
does the shared methodological delta change the next cycle after it is persisted and reactivated, rather than merely appearing in prompts?

## NEGATIVE KNOWLEDGE

- ProviderRouter privacy logic does not govern OSES.
- No-production-producer flags are not a policy.
- exclude cannot express an empty permitted set in the current selector behavior.
- ObservationPermissionGate is not transmission authorization.
- Redaction in capture is not proof of redaction in OSES.
- Credentials imply ability to attempt a provider, not semantic permission.
- Static cloud path is not runtime transmission proof.
- A method correction inside an audit is not yet causal learning by IABV.

## ROUTING DELTA

Implementation actor remains blocked.

The next required capability is not source archaeology unless contradictory source evidence appears.

The immediate next step is human policy definition. After that decision, routing must be recomputed from the resulting contract and first technical edge.

## STATUS

Codex result: reconciled
Sonnet result: independently reconciled
Governance classification: GOVERNANCE SEMANTIC GAP
Human policy: OPEN
Implementation: NOT AUTHORIZED
Runtime transmission: NOT PROVEN
Method-use observation: YES
Persistent causal learning: NOT PROVEN

END OF RECORD
