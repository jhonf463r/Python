# G1 Forensic Evidence - Limitations

## Scope Limitations
1. G1 is currently a proof-of-path for write_repo_file only
2. G1 does NOT implement self-development or autonomous capability growth
3. G1 does NOT implement learning loops, rollback, or multi-agent deliberation
4. G1 does NOT modify C2, Authority, Ed25519, leases, process identity, or Named Pipe implementation

## Test Limitations
1. Negative test uses a controlled planner (NegativeMockPlanner) to inject unsupported tool
2. This is explicitly marked as NEGATIVE TEST ONLY in the code
3. The negative test does NOT use the real cloud provider for plan generation
4. The positive test uses real Groq provider with openai/gpt-oss-120b model

## Evidence Limitations
1. Provider runtime and Authority runtime are included in the full G1 runtime output
2. Separate provider/authority runtime files reference the main runtime file
3. Repository state captures include temporary test files used for evidence collection

## Implementation Limitations
1. G1 requires manual tool registration via register_self_update_tools
2. G1 does not automatically discover or register tools
3. G1 requires explicit container setup with capability_action_bridge
4. G1 does NOT implement dynamic capability growth or learning

## Security Limitations
1. G1 relies on Authority for all authorization decisions
2. G1 does NOT bypass or mock Authority in any way
3. G1 uses real REGISTER_EXECUTION and ISSUE_LEASE calls
4. G1 uses real CONSUME_LEASE calls via CapabilityActionBridge
