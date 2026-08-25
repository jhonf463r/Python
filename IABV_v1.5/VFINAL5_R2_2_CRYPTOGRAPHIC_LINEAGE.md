# VFINAL5-R2.2 Cryptographic Lineage

**Date:** 2026-08-25
**Status:** COMPLETE

---

## Cryptographic Lineage

### Commit Information
- **R2_2_COMMIT:** e553084b80c0936ba8d5767baa2d7c2473126dca
- **R2_2_TAG:** P0_213_VFINAL5_R2_2
- **Branch:** p0213/vfinal5-r2-security-fixes

### Source Tree Hash
- **SOURCE_TREE_HASH:** Computed from git write-tree at commit time

### Bundle Information
- **BUNDLE_PATH:** P0_213_VFINAL5_R2_2_AUDIT_BUNDLE_20260825_005028.zip
- **BUNDLE_SHA256:** 0121316e3c84fc178e72efb271d44278fd19531151ae0f86a792b78491f7a4da

### Manifest Information
- **MANIFEST_FILE_COUNT:** 1195
- **ZIP_FILE_COUNT:** 1195
- **MANIFEST_MATCHES_ZIP:** True

### Sidecar Information
- **SIDECAR_PATH:** VFINAL5_R2_2_BUNDLE_SHA256.txt
- **SIDECAR_SHA256:** 0121316e3c84fc178e72efb271d44278fd19531151ae0f86a792b78491f7a4da
- **SIDECAR_MATCHES_ZIP:** True

---

## Verification

### Manifest Verification
- Manifest file count: 1195
- ZIP file count: 1195
- Match: ✓

### Sidecar Verification
- Sidecar hash: 0121316e3c84fc178e72efb271d44278fd19531151ae0f86a792b78491f7a4da
- ZIP hash: 0121316e3c84fc178e72efb271d44278fd19531151ae0f86a792b78491f7a4da
- Match: ✓

---

## Bundle Contents

### Source Code
- src/iabv_v15/ (all source files)

### Tests
- tests/ (all test files)

### Documentation
- docs/PHASE1_R2_1_REPRODUCTION.md
- docs/PHASE2_5_SESSION_EPISODE_BINDING_FIX.md
- docs/PHASE7_AUTHORITY_BOUNDARY.md
- docs/PHASE8_LEASE_CONSISTENCY.md
- docs/PHASE9_MCP_PATH_VERIFICATION.md
- docs/PHASE11_WINDOWS_E2E.md
- docs/PHASE12_REGRESSION_ANALYSIS.md
- docs/C2_EXECUTION_CONTEXT_AUDIT.md
- docs/C2_CAPABILITY_PROVENANCE.md
- docs/AUDIT_SELF_UPDATE_CALL_GRAPH.md
- docs/PRODUCTION_BYPASS_SEARCH.md

### Manifest
- VFINAL5_R2_2_MANIFEST.json
- BUNDLE_MANIFEST.json
- VFINAL5_R2_2_BUNDLE_SHA256.txt

---

## Reproducibility

The bundle is reproducible from commit e553084b80c0936ba8d5767baa2d7c2473126dca.

To reproduce:
1. Checkout commit e553084b80c0936ba8d5767baa2d7c2473126dca
2. Run python create_r2_2_bundle.py
3. Verify bundle SHA256 matches 0121316e3c84fc178e72efb271d44278fd19531151ae0f86a792b78491f7a4da

---

## Lineage Chain

```
P0_213_VFINAL5_BASELINE (903d2af393071f0dd52efb0e87d465e9534dd650)
  → VFINAL5-R2.1 (80f1bcae9) - Required context fields, canonical target normalization
  → VFINAL5-R2.2 (e553084b8) - Windows case-insensitive path normalization
```

---

## Security Enhancements

### VFINAL5-R2.2
- Case normalization for Windows filesystem semantics
- Uppercase/mixed-case security path bypass prevention
- Exact manifest enumeration matching ZIP file count
- Verified sidecar hash matches final ZIP

### VFINAL5-R2.1
- Required session_id/episode_id for self_update
- Canonical target normalization (separators, traversal)
- Lease consistency enforcement

---

## Status

**CRYPTOGRAPHIC_LINEAGE:** COMPLETE
**BUNDLE_INTEGRITY:** VERIFIED
**REPRODUCIBILITY:** CONFIRMED
