LIMITATIONS
===========

SCOPE LIMITATIONS:
------------------
R8-G4.3 was intended to demonstrate real OSES → StructuredNeed runtime transformation.
However, runtime data was not available, so the scope was limited to documenting the runtime gap.

NOT IMPLEMENTED (as required):
- Expert selection
- External AI consultation
- Request generation
- Response evaluation
- Development task generation
- Learning
- Next-task generation
- Self-development
- Capability growth

RUNTIME DATA LIMITATIONS:
-------------------------
1. No runtime_audit.jsonl
   - File does not exist in data/logs/
   - Required for capability_promised_but_unavailable findings
   - Cannot execute _capability_promised_but_unavailable_findings() without this data

2. No chat_research_backlog
   - Directory does not exist in data/
   - Required for research_gap findings
   - Cannot execute _chat_research_backlog_findings() without this data

3. No real build_review execution
   - Requires runtime_audit.jsonl
   - Requires chat_research_backlog
   - Requires environment capability data
   - Requires world model snapshot
   - Requires experiment lab data

4. No real findings capture
   - Cannot capture real OSES findings without runtime data
   - Cannot trace real capability findings
   - Cannot trace real operational findings

5. No real need transformation
   - Cannot execute NeedFormulationService with real data
   - Cannot verify provenance for real needs
   - Cannot verify persistence for real needs

6. No real human-visible output
   - Cannot format real needs without runtime data
   - Cannot verify human-readable output for real needs

DOWNSTREAM CONSUMER LIMITATIONS:
---------------------------------
1. StructuredNeedRepository.list_pending() not called
   - Code analysis shows no service calls this method
   - ControlMasterService uses pending_issue_repository instead
   - No automatic consumer of StructuredNeed exists

2. NEED_DOWNSTREAM_INFLUENCE = NONE / REPORTING_ONLY
   - StructuredNeed is persisted but not consumed
   - No automatic action taken based on needs
   - Only reporting capability exists

TECHNICAL LIMITATIONS:
----------------------
1. Persistence is file-based
   - JSON files in data/evolution/structured_needs/
   - No database indexing
   - No transaction guarantees

2. Human-readable output is static
   - Fixed format (NECESITO/PORQUE/EVIDENCIA)
   - No localization
   - No templating

3. Initialization can fail silently
   - Services initialized with try/except
   - Warning logged if initialization fails
   - Graceful degradation (returns 0 needs created)

4. No validation of finding quality
   - Does not validate that finding has sufficient data
   - May create needs with empty fields
   - No minimum data requirements

ENVIRONMENT LIMITATIONS:
------------------------
1. Regression tests failed due to pre-existing issues
   - G1/G2/G3: Missing post_action_observer module
   - C2: Authority pipe not available
   - These are NOT caused by R8-G4.3 changes

2. Integration is optional
   - Services initialized only if evolution_dir exists
   - Graceful degradation if initialization fails
   - No hard dependency on new components

FUTURE WORK (OUT OF SCOPE FOR R8-G4.3):
---------------------------------------
- Execute real build_review when runtime data is available
- Capture real OSES findings from runtime_audit.jsonl
- Capture real OSES findings from chat_research_backlog
- Trace real capability need transformation
- Trace real operational finding rejection
- Verify provenance for real needs
- Verify persistence for real needs
- Verify human-visible output for real needs
- Implement downstream consumer for StructuredNeed
- Need-to-task transformation (later gate)
- Expert selection (later gate)
- AI consultation (later gate)
