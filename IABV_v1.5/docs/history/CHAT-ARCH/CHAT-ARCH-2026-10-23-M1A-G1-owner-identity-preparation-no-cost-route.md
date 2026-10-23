# M1A G1 — Owner identity preparation and no-cost route

- Date: 2026-10-23 (America/Bogota).
- Task: M1A_G1_OWNER_IDENTITY_PREPARATION_NO_COST_ROUTE.
- Source provenance: Owner-reported in the active conversation; no independent portal or runtime capture.
- Privacy: exact tenant domain, user principal name, tenant/object IDs, and authentication artifacts are intentionally omitted from this public record.

## 1. Owner-reported progress

The Owner reports:
- A Microsoft Azure/Entra organizational directory was created.
- A dedicated user for the IABV Owner role was created in that directory.
- Microsoft Authenticator was enrolled for that user.
- A subsequent sign-in and Authenticator verification succeeded.

These are user-reported setup facts. This record does not independently verify the directory, the user, the tenant configuration, or the authentication event.

## 2. Correct interpretation

Microsoft Entra ID is now a candidate identity provider for a no-cost design path, not an established IABV trust anchor or an authorization service for protected reads.

Successful MFA demonstrates only that the Owner reports control of the enrolled identity at sign-in. It does not establish:
- a trusted issuer configuration in the exact IABV runtime instance;
- an independently governed Owner-to-Windows-principal binding;
- an issuer-to-exact-server binding or server-side operation-to-target resolver;
- trusted catalogue/producer policy, authoritative revocation, or complete active-block-set attestation;
- independent per-block release, read authorization, a durable correlated operation receipt, or later causal reuse.

The directory was created and is controlled by the Owner; its existence alone is not proof of an independent authority over IABV. Tenant-scoped token issuer and audience validation, a governance-owned bootstrap ceremony, exact instance binding, and explicit authority separation would need a design review before any integration is implemented.

## 3. Cost and change limits

The Owner has stated that the project budget for paid applications or subscriptions is zero. No paid service, Azure resource, application registration, credential, or product-code change is authorized by this record. The actual Azure subscription type, spending limit, billing state, and any potentially billable resource inventory have not been independently verified; do not claim that cost exposure is eliminated.

Next actions must remain no-cost by default: do not upgrade to Pay-As-You-Go, remove spending limits, deploy resources, purchase licences, or create client secrets. Do not put tenant identifiers, user IDs, tokens, QR codes, recovery codes, private keys, or other credentials into the public repository.

## 4. Canonical state

```text
TASK=M1A_G1_OWNER_IDENTITY_PREPARATION_NO_COST_ROUTE
ENTRA_DIRECTORY=OWNER_REPORTED_CREATED
DEDICATED_IABV_OWNER_USER=OWNER_REPORTED_CREATED
AUTHENTICATOR=OWNER_REPORTED_ENROLLED
AUTHENTICATOR_SIGN_IN=OWNER_REPORTED_SUCCESS
IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID; NOT_YET_TRUSTED_BY_IABV
TENANT_ID_AND_USER_ID=NOT_STORED_IN_PUBLIC_REPOSITORY
AZURE_BILLING_STATE=NOT_VERIFIED
PAID_RESOURCES=NOT_REPORTED; NOT_INDEPENDENTLY_VERIFIED
APP_REGISTRATION=NOT_CREATED_OR_NOT_REPORTED; NOT_AUTHORIZED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=NO_PAID_SERVICES; BILLING_GUARDS_NOT_VERIFIED
AUTOMATIC_FOLLOW_ON=FALSE
```

## 5. Next bounded task

Perform a design-only, no-cost feasibility review of tenant-scoped Microsoft Entra authentication against the existing IABV trust and Entry 274 requirements. Use only an already-supported, authorized, non-sensitive source route; do not invoke the IABV reader/list tools, inspect local protected data, or perform a broad scan. Identify the smallest missing design and authority decisions, including exact issuer/tenant/audience validation, how the Owner and local Windows principal are bound, exact server-instance identity, revocation, audit/receipt semantics, and whether any part requires a paid feature. If there is no supported route, report that precise gap and stop.

This is not implementation authorization. Keep all gates open and all protected operations denied until each distinct prerequisite is evidenced and separately authorized.
