R7 G3 RUNTIME VERIFIED BUNDLE - LIMITATIONS
==========================================

1. MOCK CONTAINER USED:
   - The G3 positive test uses a MockContainer with mocked services.
   - This is necessary because the test does not use the full bootstrap.
   - However, the test uses real CloudReasoningPlannerService and real MCP server.
   - The capability_action_bridge is mocked with authorize_action returning authorized=True.
   - This is a limitation but acceptable for testing G3 verification logic.

2. G3 POSITIVE TEST CONTENT:
   - The test uses content_contains for verification (partial match).
   - This is not a tautology - the expected content comes from plan parameters,
     while the observed content comes from independent filesystem observation.
   - The hash verification is exact and demonstrates independent calculation.

3. FORENSIC DISCIPLINE:
   - All derived documents were regenerated from the same execution.
   - No recycling of PIDs, hashes, timestamps.
   - DERIVED_EVIDENCE used for summaries, not RAW.
   - No git history rewriting.

4. C2 NOT MODIFIED:
   - As required, C2 components were not modified.
   - Authority, Named Pipe, lease semantics, Ed25519, exactly-once, process identity, capability authorization all preserved.
   - C2 regression tests passed (10/10).

5. TOOL VOCABULARY PRESERVED:
   - No tools were removed from the planner vocabulary.
   - codex, chatgpt, claude, devin, ollama_local remain available.
   - write_repo_file remains the single protected-action proof.

6. G2 FUNCTIONALITY PRESERVED:
   - All G2 functionality is preserved.
   - G2 regression test passed.
   - Deterministic hash calculation working correctly.

7. G1 FUNCTIONALITY PRESERVED:
   - All G1 functionality is preserved.
   - G1 regression test passed.

8. NEXT STEPS:
   - No next steps required. G3 positive test now passes.
   - All regression tests pass.
   - G3 verification logic is working correctly.
