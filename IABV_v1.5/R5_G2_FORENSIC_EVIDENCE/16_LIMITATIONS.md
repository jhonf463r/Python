# G2 Forensic Evidence - Limitations

## Scope Limitations
1. G2 is a proof-of-path for action plan completeness
2. G2 does NOT implement learning loops, rollback, or multi-agent deliberation
3. G2 does NOT modify C2, Authority, Ed25519, leases, process identity, or Named Pipe
4. G2 does NOT implement autonomous self-development or capability growth
5. G2 is currently a single-tool proof (write_repo_file only)

## Test Limitations
1. G2 positive test uses real Groq provider with openai/gpt-oss-120b model
2. G2 verification-negative test uses a controlled planner (NegativeVerificationPlanner) to inject wrong expected_result
3. The controlled planner is explicitly marked as NEGATIVE TEST ONLY
4. The verification logic compares expected_result against observed_result but does not perform rollback

## Evidence Limitations
1. Provider runtime and Authority runtime are included in the full G2 runtime output
2. Separate provider/authority runtime files reference the main runtime file
3. Repository state captures include temporary test files used for evidence collection

## Implementation Limitations
1. G2 requires the planner to generate complete action plans with target, parameters, expected_result, rationale
2. G2 maintains backward compatibility with G1 (human-provided tool_parameters)
3. G2 uses plan_parameters only when they are non-empty and human didn't provide tool_parameters
4. G2 does NOT automatically discover or register tools
5. G2 requires explicit container setup with capability_action_bridge

## Security Limitations
1. G2 relies on Authority for all authorization decisions
2. G2 does NOT bypass or mock Authority in any way
3. G2 uses real REGISTER_EXECUTION and ISSUE_LEASE calls
4. G2 uses real CONSUME_LEASE calls via CapabilityActionBridge
5. G2 verification is informational only - it does not trigger rollback or remediation

## Verification Limitations
1. G2 verification compares expected_result against observed_result
2. Hash comparison is approximate (checks if expected hash is contained in observed or matches exactly)
3. Verification failure does NOT prevent action execution
4. Verification failure is reported but does NOT trigger automatic rollback
5. The system distinguishes between ACTION COMPLETED and ACTION VERIFIED AS CORRECT
