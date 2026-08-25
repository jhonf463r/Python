# VFINAL5 Artifact Lineage Report

**Date:** 2026-08-24
**Status:** ARTIFACT_LINEAGE_MISMATCH

---

## PHASE 0 — ARTIFACT LINEAGE INVESTIGATION

### Runtime Checkout Information
- **RUNTIME_CHECKOUT_PATH:** C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5
- **RUNTIME_GIT_COMMIT:** 1d7f0508ff6208ef9d241af1c9fb058db5d6286e
- **RUNTIME_SOURCE_TREE_HASH:** [Not computed]

### Bundle Information
- **RUNTIME_BUNDLE_PATH:** C:\temp\P0_213_PHASE3_PHASE4_F14_F15_F16_F17_C1_C2_H1_FINAL_AUDIT_BUNDLE_VFINAL5.zip
- **RUNTIME_BUNDLE_SHA256:** CBCC4000EA586C2048DD952D279C17B966C311241B18CC132A2ACFBA2CDEF048
- **AUDITED_BUNDLE_SHA256:** cbcc4000ea586c2048dd952d279c17b966c311241b18cc132a2acfba2cdef048 (from Claude)

### Bundle Match Verification
- **BUNDLE_MATCHES_RUNTIME_CHECKOUT:** YES (SHA256 matches)
- **BUNDLE_MATCHES_REPORTED_RUNTIME:** YES (SHA256 matches Claude's audit)

---

## CRITICAL FINDING: UNCOMMITTED CHANGES

### Git Status Analysis
The working tree at runtime has **UNCOMMITTED CHANGES**:

**Modified Files (19 files, 1975 insertions, 299 deletions):**
- IABV_v1.5/src/iabv_v15.egg-info/PKG-INFO
- IABV_v1.5/src/iabv_v15.egg-info/SOURCES.txt
- IABV_v1.5/src/iabv_v15.egg-info/requires.txt
- IABV_v1.5/bootstrap.py
- IABV_v1.5/src/iabv_v15/domain/models.py
- IABV_v1.5/src/iabv_v15/infra/mcp/self_update_tools.py
- IABV_v1.5/src/iabv_v15/infra/mcp/server.py
- IABV_v1.5/src/iabv_v15/services/phase3/test_phase3_negative_security.py
- IABV_v1.5/src/iabv_v15/services/tools/github_remote_service.py
- IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py
- IABV_v1.5/src/iabv_v15/services/tools/tool_operational_executor.py
- IABV_v1.5/src/iabv_v15/services/tools/tool_rollback_manager.py
- IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py
- IABV_v1.5/src/iabv_v15/services/trust/authority_client.py
- IABV_v1.5/src/iabv_v15/services/trust/authority_protocol.py
- IABV_v1.5/src/iabv_v15/services/trust/authority_server.py
- IABV_v1.5/src/iabv_v15/services/trust/authority_service.py
- IABV_v1.5/tests/test_github_remote_service.py
- IABV_v1.5/tests/test_v5_phase2_authority.py

**Untracked Files:** (many temporary files, staging directories, old bundles)

---

## LINEAGE MISMATCH DETERMINATION

### STATE = ARTIFACT_LINEAGE_MISMATCH

**Reason:**
The VFINAL5 bundle was created from a **working tree with uncommitted changes**, not from a clean git commit. The bundle SHA256 matches Claude's audit, but the source state is not tied to an immutable git commit.

### Which Commit Produced Runtime Results?
- **Answer:** UNKNOWN (runtime tests were run against uncommitted working tree)

### Which Commit Produced the Bundle?
- **Answer:** NONE (bundle was created from uncommitted working tree)

### Which Working Tree Produced the Bundle?
- **Answer:** C:\Python\IABV_v1.5_runtime_p021v\IABV_v1.5 with 19 modified files (1975 insertions, 299 deletions)

### Which Report Was Generated From Which Tree?
- **Answer:** VFINAL5_FINAL_RUNTIME_REPORT.md was generated from the uncommitted working tree

---

## REQUIRED REMEDIATION

### Before Proceeding with Security Fixes

1. **Commit all changes** to create an immutable source state
2. **Create bundle from committed state** (not working tree)
3. **Regenerate all reports** from the committed state
4. **Verify bundle SHA256** matches the new committed state
5. **Re-run all runtime tests** against the committed state

### Current State Cannot Be Used for External Audit

The current bundle and reports are **NOT tied to an immutable source state** and therefore cannot be used for external audit until the lineage is resolved.

---

## NEXT STEPS

1. Commit all changes to git
2. Create new bundle from committed state
3. Re-run all tests against committed state
4. Regenerate all reports from committed state
5. Verify artifact lineage is coherent
6. Then proceed with security fixes (PHASE 1-17)

---

## CONCLUSION

**STATE = ARTIFACT_LINEAGE_MISMATCH**

**DO NOT claim the runtime results prove the audited bundle.**

**DO NOT proceed with security fixes until lineage is resolved.**

**DO NOT send to external audit until lineage is resolved.**
