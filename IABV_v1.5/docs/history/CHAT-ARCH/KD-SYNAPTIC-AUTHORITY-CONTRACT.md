# Knowledge Delta — Synaptic Authority Contract

## Previous Model

**Edge:** `preferred_assistant_kind → ToolRegistry.pick_card_for_task() → ToolCard | None`

**Contract (Implicit, Incorrect):**
- `ToolCard | None` return type
- Callers interpreted: `preferred_card is not None` → semantic match / authoritative selection

**Actual Tiers:**
- Tier 1: explicit `task.tool_id`
- Tier 2: `preferred_assistant_kind` exact match (with identity mapping)
- Tier 3: keyword scoring on objective/title
- Tier 4: `cards[0]` fallback

**Defect:**
The return type does not indicate which tier produced the selection. Callers with `preferred_assistant_kind != ''` could receive a fallback card (Tier 3 or 4) and incorrectly treat it as a semantic match (Tier 2).

## Observed Runtime Failure

**Execution:**
```
candidate_assistant_kinds=["unknown_assistant_xyz"]
        ↓
SynapticRouter.decide()
        ↓
selected_assistant_kind="unknown_assistant_xyz"
        ↓
ToolRegistry.pick_card_for_task(task, preferred_assistant_kind="unknown_assistant_xyz")
        ↓
Tier 2: exact match → NO MATCH
        ↓
Tier 3: keyword scoring → score=0
        ↓
Tier 4: cards[0] → ollama_llm (unrelated card)
        ↓
ToolCard returned != None
        ↓
ToolTeachService interprets:
if preferred_card is not None:
    synaptic_selection_authoritative = True
        ↓
FALSE AUTHORITY
```

**Root Cause:**
`ToolCard | None` does not distinguish semantic match from fallback. The contract `preferred_card is not None` is insufficient evidence of authority.

## Architectural Adjudication

**Decision (Opus 5):**
The minimal correction is to separate contracts based on caller intent:

**Contract A (Empty preferred_assistant_kind):**
- Caller provides no preference → historical fallback allowed
- Tiers 3–4 execute as before
- Compatibility: preserves behavior for `tool_operational_executor.py` callers

**Contract B (Non-empty preferred_assistant_kind):**
- Caller wants semantic match → only semantic match allowed
- If Tier 2 fails → return `None`
- Tiers 3–4 skipped
- Authority: `preferred_card is not None` now implies semantic match by construction

**Rationale:**
- `ToolRegistry` knows which tier produced the selection
- Making `preferred_assistant_kind != ''` imply "only semantic match" allows existing code to be correct without changes
- No need for new `MatchResult` type or changes in `ToolTeachService`

## Minimal Intervention

**File:** `src/iabv_v15/services/tools/tool_registry.py`
**Method:** `pick_card_for_task()`

**Change:**
```python
# BEFORE
preferred_assistant_kind = str(preferred_assistant_kind or '').strip().lower()
# Identity mapping...
preferred_assistant_kind = identity_mapping.get(preferred_assistant_kind, preferred_assistant_kind)
if preferred_assistant_kind:
    for card in self.list_cards():
        card_kind = str(card.metadata.get('assistant_kind') or '').strip().lower()
        if card_kind == preferred_assistant_kind:
            return self.refresh_card(card)
# Tiers 3–4 always execute...

# AFTER
# Track original caller intent for authority contract
original_preferred = str(preferred_assistant_kind or '').strip().lower()
preferred_assistant_kind = original_preferred
# Identity mapping...
preferred_assistant_kind = identity_mapping.get(preferred_assistant_kind, preferred_assistant_kind)
if preferred_assistant_kind:
    for card in self.list_cards():
        card_kind = str(card.metadata.get('assistant_kind') or '').strip().lower()
        if card_kind == preferred_assistant_kind:
            return self.refresh_card(card)
    # Authority contract: if caller provided preferred_assistant_kind != ''
    # and no semantic match exists, return None to prevent false authority
    # Fallback (keyword scoring, cards[0]) only allowed when original_preferred == ''
    if original_preferred:
        return None
# Tiers 3–4 only execute when original_preferred == ''...
```

**Scope:**
- Only affects `preferred_assistant_kind` resolution
- Does not change identity mapping
- Does not change tiers 3–4 when `preferred_assistant_kind == ''`
- Applies globally to all callers

## Pre-Fix Evidence

**Test:** `tests/test_synaptic_assistant_identity.py::test_assistant_identity_mapping_unmapped`

**Execution:**
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5
PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src
/c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_assistant_identity.py::test_assistant_identity_mapping_unmapped -v
```

**Result:** FAILED - `assert card is None` failed, got `ToolCard(tool_id='ollama_llm', ...)`

**Interpretation:**
`preferred_assistant_kind='unknown_assistant_xyz'` → returned `ollama_llm` (cards[0] fallback) instead of `None`, producing false authority.

## Post-Fix Evidence

**Test:** Same test file, all 9 cases

**Execution:**
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5
PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src
/c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_assistant_identity.py -v
```

**Result:** 9 passed

**Cases covered:**
1. `codex` → match ✓
2. `chatgpt` → match ✓
3. `claude` → match ✓
4. `ollama` → match ✓
5. `chatgpt_web` → match via identity mapping ✓
6. `claude_web` → match via identity mapping ✓
7. `ollama_local` → match via identity mapping ✓
8. `unknown_assistant_xyz` → None (authority contract) ✓ (FIXED)
9. `preferred_assistant_kind=''` → historical fallback preserved ✓

## Case Matrix

| Input preferred_assistant_kind | Original preferred | Expected behavior | Observed pre-fix | Observed post-fix |
|-------------------------------|-------------------|------------------|------------------|-------------------|
| `codex` | non-empty | Semantic match or None | match | match |
| `chatgpt` | non-empty | Semantic match or None | match | match |
| `claude` | non-empty | Semantic match or None | match | match |
| `ollama` | non-empty | Semantic match or None | match | match |
| `chatgpt_web` | non-empty | Semantic match or None | match (via mapping) | match (via mapping) |
| `claude_web` | non-empty | Semantic match or None | match (via mapping) | match (via mapping) |
| `ollama_local` | non-empty | Semantic match or None | match (via mapping) | match (via mapping) |
| `unknown_assistant_xyz` | non-empty | None (no match) | `ollama_llm` (BUG) | None (FIXED) |
| `''` (empty) | empty | Historical fallback (tiers 3–4) | fallback | fallback (preserved) |

## Fallback Regression

**Test:** `test_authority_contract_empty_preferred_assistant`

**Purpose:** Verify that empty `preferred_assistant_kind` preserves historical fallback behavior for caller compatibility.

**Result:** PASSED - Empty `preferred_assistant_kind` still uses keyword scoring → `cards[0]` fallback when appropriate.

**Caller Compatibility:**
- `tool_operational_executor.py:18` - no `preferred_assistant_kind` → preserved
- `tool_operational_executor.py:29` - no `preferred_assistant_kind` → preserved

## Test Regression

- `test_synaptic_assistant_identity.py`: 9 passed
- `test_synaptic_router.py`: 39 passed
- `test_tool_registry.py`: 13 passed
- `test_e05_synaptic_routing_to_devin_selection.py`: 1 passed
- `test_p0_b_external_action_authorization.py`: 14 passed

**No regression detected.**

## Epistemic Status

**implemented:** YES - authority contract separation added to `pick_card_for_task()`
**proven:** YES - pre-fix test failed (fallback non-None), post-fix test passed (None)
**observed:** YES - test traverses real `ToolRegistry.pick_card_for_task()`
**caused:** YES - authority contract causes `preferred_assistant_kind != ''` to only return semantic matches

## ΔK

1. **Return Type Insufficient:** `ToolCard | None` does not indicate which tier produced the selection. Non-None does not imply semantic match.

2. **Authority by Construction:** By making `preferred_assistant_kind != ''` imply "only semantic match", the invariant `preferred_card is not None` → semantic match becomes true by construction.

3. **Fallback ≠ Authority:** Historical fallback (tiers 3–4) is legitimate for callers without preference, but illegitimate for callers with explicit preference.

4. **Contract Separation:** Empty vs non-empty `preferred_assistant_kind` now has explicit, distinct semantics.

## Δπ

**Policy Change:**
- Before: All callers could receive fallback cards regardless of `preferred_assistant_kind`
- After: Only callers with `preferred_assistant_kind == ''` can receive fallback cards; callers with non-empty preference only receive semantic matches or None

**Preserved:**
- Identity mapping unchanged
- Tiers 3–4 unchanged when `preferred_assistant_kind == ''`
- Caller compatibility for `tool_operational_executor.py` preserved

## ΔB

**NOT MEASURED** - Requires evidence of routing end-to-end including `adapter.run()` and outcome.

## ΔY

**NOT MEASURED** - Requires outcome measurement real.

## Remaining Namespace Governance Defect

Multiple alias maps exist in the codebase:
- `ToolRegistry.pick_card_for_task()` identity mapping
- `ToolTeachService._external_tool_ids()` tool_id mapping
- `ToolTeachService._preferred_external_tool_id()` explicit_family mapping
- `ControlCenterViewModel._PROVIDER_ALIASES`

These maps are not consolidated and may have inconsistencies. This is registered as an open knowledge defect but left out of scope for this commit.

## Next Causal Edge

Once authority contract is closed:
```
correct selected_assistant_kind
→ correct ToolCard (semantic match only when preferred_assistant_kind != '')
→ ToolTask.tool_id
→ adapter.run()
→ result
→ outcome
```

The next edge to verify is whether the routing now produces correct operational tool selection end-to-end with the new authority contract.

## Memory Operating Protocol

**source historical record:** KD-SYNAPTIC-AUTHORITY-CONTRACT.md
**CURRENT-STATE impact:** Authority contract in ToolRegistry prevents false authority for synaptic routing
**CONTEXT-INDEX impact:** NOT DETERMINADO (no ejecutado en este ciclo)
**UNRESOLVED-KNOWLEDGE impact:** Namespace governance defect (multiple alias maps) registered
**next-AI routing impact:** Should observe correct authority: `preferred_card is not None` now implies semantic match

**Nota:** Este ciclo fue exclusivamente de implementación. No se ejecutó la absorción completa de memoria.
