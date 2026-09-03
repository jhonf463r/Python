# IABV v1.5 Adaptive Protocol Persistence Audit
**Date:** 2026-09-02
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## Persistence Round-Trip Verification

### Learn → Persist → Process Restart → Load → Recommendation

**Service:** AdaptiveProtocolService
**File:** `src/iabv_v15/services/adaptive/adaptive_protocol.py`
**Evidence:** OBSERVED

### Persistence Implementation

**Storage Location:** `evolution/adaptive_protocol/rules.json`
**Format:** JSON
**Method:** `_persist_rules()` (lines 305-312)
**Load Method:** `_load_rules()` (lines 277-303)

### Serialization

**to_dict() Method:** Lines 45-58
**Fields Serialized:**
- rule_id
- rule_key
- rule_value
- confidence
- observation_count
- success_count
- last_observation
- last_result
- created_at
- updated_at
- metadata

### Deserialization

**_load_rules() Method:** Lines 277-303
**Fields Deserialized:**
- rule_id (from "rule_id")
- rule_key (from " rule_key") - **DEFECT DETECTED**
- rule_value (from "rule_value")
- confidence (from "confidence")
- observation_count (from "observation_count")
- success_count (from "success_count")
- last_observation (from "last_observation")
- last_result (from "last_result")
- created_at (from "created_at")
- updated_at (from "updated_at")
- metadata (from "metadata")

## CRITICAL DEFECT

**Location:** Line 289
**Issue:** Typo in field name: `" rule_key"` instead of `"rule_key"`
**Impact:** Deserialization failure - rule_key will be loaded as empty string
**Evidence:** OBSERVED

**Code:**
```python
rule_key=rule_data.get(" rule_key", ""),  # Line 289 - has leading space
```

**Expected:**
```python
rule_key=rule_data.get("rule_key", ""),  # Should not have leading space
```

**Consequence:**
- Rules loaded from disk will have empty rule_key
- Rule lookup by rule_key will fail
- Learned rules will be lost after process restart
- Recommendation generation will fail for persisted rules

## Recommendation Generation Verification

**Method:** `get_recommendation()` (lines 200-270)

**Basis for Recommendation:**
1. Confidence threshold (0.7)
2. Observation count threshold (3)
3. Success rate threshold (0.8)

**Evidence:** OBSERVED

**Recommendation Logic:**
- Confidence < 0.7 → apply=False
- Observations < 3 → apply=False
- Success rate < 0.8 → apply=False
- All thresholds met → apply=True

**Verification:** Recommendation is based on actual result (success/failure), observation count, and confidence - NOT merely narrative metadata.

## Summary

**PERSISTENCE ROUND-TRIP:** BROKEN (due to rule_key typo)
**SERIALIZATION:** CORRECT
**DESERIALIZATION:** BROKEN (line 289 typo)
**RECOMMENDATION BASIS:** CORRECT (based on actual metrics, not metadata)

**CRITICAL DEFECT:** Line 289 typo prevents rule_key from being loaded correctly, breaking the entire persistence round-trip. This defect must be fixed before adaptive protocol can function correctly across process restarts.

**SEVERITY:** CRITICAL - Adaptive protocol cannot persist and restore learned rules.
