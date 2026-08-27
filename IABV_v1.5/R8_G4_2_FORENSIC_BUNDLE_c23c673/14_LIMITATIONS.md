LIMITATIONS
===========

SCOPE LIMITATIONS:
------------------
R8-G4.2 implements ONLY the category reconciliation between real OSES findings and NeedFormulationService.

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

REAL RUNTIME LIMITATIONS:
-------------------------
1. No real build_review execution
   - Requires full IABV runtime environment
   - Requires runtime audit data (runtime_audit.jsonl)
   - Requires chat research backlog (chat_research_backlog/)
   - Requires environment capability data
   - Requires world model snapshot
   - Requires experiment lab data

2. No real production yield measurement
   - Cannot measure REAL_OSES_FINDINGS_COUNT
   - Cannot measure REAL_CAPABILITY_FINDINGS_COUNT
   - Cannot measure REAL_NEEDS_CREATED
   - Cannot measure REAL_NEEDS_REJECTED
   - Cannot measure REJECTION_REASONS

3. No real provenance verification for runtime needs
   - Unit tests use synthetic findings
   - No verification of real OSES findings traversing the pipeline
   - No evidence of real finding → need transformation in production

SEMANTIC LIMITATIONS:
---------------------
1. Category-based classification only
   - Relies on explicit finding category
   - No semantic analysis of finding content
   - Fail-closed for ambiguous findings (no needs created)

2. Knowledge extraction is minimal
   - Uses category directly as knowledge_required
   - No semantic analysis of what knowledge is actually needed
   - Empty string if category is not capability-shaped

3. State extraction is pattern-based
   - current_state only extracted if "cannot" pattern exists in summary
   - desired_state only uses recommendation if present
   - Empty strings if patterns not found

4. No deduplication
   - Multiple similar findings may create multiple needs
   - No merging of duplicate needs
   - No need lifecycle management beyond status

5. No confidence tracking
   - Does not track finding confidence in need
   - Does not weight needs by confidence
   - All needs treated equally regardless of source confidence

CATEGORY RECONCILIATION LIMITATIONS:
------------------------------------
1. Manual category mapping
   - Categories manually added to CAPABILITY_SHAPED_CATEGORIES
   - Categories manually added to OPERATIONAL_CATEGORIES
   - No automated taxonomy discovery
   - No normalization layer

2. Static category lists
   - Categories hardcoded in need_formulation_service.py
   - No dynamic category discovery from OSES
   - No category versioning
   - No category deprecation mechanism

3. Semantic interpretation required
   - functional_gap classified as operational (underutilized resources)
   - configuration_gap classified as operational (missing config/secrets)
   - research_gap classified as capability-shaped (knowledge gap)
   - These interpretations may need review as OSES evolves

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
   - These are NOT caused by R8-G4.2 changes

2. Integration is optional
   - Services initialized only if evolution_dir exists
   - Graceful degradation if initialization fails
   - No hard dependency on new components

FUTURE WORK (OUT OF SCOPE FOR R8-G4.2):
---------------------------------------
- Real build_review execution with runtime data
- Production yield measurement
- Need deduplication and merging
- Need lifecycle management (acknowledged → in_progress → resolved)
- Need prioritization based on impact analysis
- Semantic analysis for better knowledge extraction
- Database-backed persistence with indexing
- Need-to-task transformation (later gate)
- Expert selection (later gate)
- AI consultation (later gate)
