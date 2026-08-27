LIMITATIONS
===========

SCOPE LIMITATIONS:
------------------
R8-G4 implements ONLY the CAPABILITY_GAP → STRUCTURED_NEED edge.

NOT IMPLEMENTED:
- Expert selection
- External AI consultation
- Request generation
- Response evaluation
- Development task generation
- Learning
- Next-task generation
- Self-development
- Capability growth

The implementation is a minimum inflection-point that enables IABV to:
1. Detect capability gaps (via existing SelfExaminationFinding)
2. Transform them into structured needs (via NeedFormulationService)
3. Persist them (via StructuredNeedRepository)
4. Report them in human-readable format (via format_human_readable)

TECHNICAL LIMITATIONS:
---------------------
1. Keyword-based detection is heuristic
   - Relies on predefined keyword lists
   - May misclassify edge cases
   - Default behavior: treat as capability-shaped if uncertain

2. Knowledge extraction is simple
   - Uses category as knowledge type prefix
   - Does not perform semantic analysis
   - current_state extraction is basic string parsing

3. Persistence is file-based
   - JSON files in data/evolution/structured_needs/
   - No database indexing
   - No transaction guarantees

4. No deduplication
   - Multiple similar findings may create multiple needs
   - No merging of duplicate needs
   - No need lifecycle management beyond status

5. Human-readable output is static
   - Fixed format (NECESITO/PORQUE/EVIDENCIA)
   - No localization
   - No templating

ENVIRONMENT LIMITATIONS:
------------------------
1. Regression tests failed due to pre-existing issues
   - C2: Authority pipe not available
   - G1/G2/G3: Missing post_action_observer module
   - These are NOT caused by R8-G4 changes

2. Integration into OperationalSelfExaminationService is optional
   - Services initialized only if evolution_dir exists
   - Graceful degradation if initialization fails
   - No hard dependency on new components

FUTURE WORK (OUT OF SCOPE FOR R8-G4):
--------------------------------------
- Need deduplication and merging
- Need lifecycle management (acknowledged → in_progress → resolved)
- Need prioritization based on impact analysis
- Semantic analysis for better knowledge extraction
- Database-backed persistence with indexing
- Need-to-task transformation (later gate)
- Expert selection (later gate)
- AI consultation (later gate)
