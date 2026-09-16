# Knowledge Delta — Synaptic Assistant Identity Mapping

## Previous Model

**Edge:** `selected_assistant_kind → ToolRegistry.pick_card_for_task() → ToolCard → ToolTask.tool_id`

**Behavior:**
- `SynapticRouter.decide()` produces assistant kinds like `'chatgpt_web'`, `'claude_web'`, `'ollama_local'`
- `ToolCard.metadata.assistant_kind` uses short names like `'chatgpt'`, `'claude'`, `'ollama'`
- `ToolRegistry.pick_card_for_task()` does exact match on `assistant_kind`
- When no exact match exists, falls back to keyword scoring on objective/title
- If keyword scoring produces score=0, returns `cards[0]` (first card in registry)

**Contract:**
- `None` in `ToolCard` return → no match
- Non-`None` in `ToolCard` return → implies authoritative selection

## Observed Runtime Failure

**Execution:**
```
ToolTeachService.build_task_from_request()
  routing_enabled=True
  goal_parameters['tool_id'] absent
  task_kind='code_generation'
  candidate_assistant_kinds=['chatgpt_web']
    ↓
SynapticRouter.decide()
  selected_assistant_kind='chatgpt_web'
    ↓
ToolRegistry.pick_card_for_task(task, preferred_assistant_kind='chatgpt_web')
  Exact match: card.metadata.assistant_kind == 'chatgpt_web' → NO MATCH
  Keyword scoring: score=0
  Fallback: cards[0] → unrelated ToolCard (e.g., claude_installed with assistant_kind='claude')
    ↓
ToolTask.tool_id = 'claude_installed'
```

**Defect:**
`selected_assistant_kind='chatgpt_web'` → `ToolCard with assistant_kind='claude'` → silent substitution

**Root Cause:**
1. SynapticRouter produces names with suffixes (`_web`, `_local`)
2. ToolCard metadata uses short names without suffixes
3. No identity mapping between these naming conventions
4. Fallback `cards[0]` produces false authority for non-matching selections

## Intervention

**File:** `src/iabv_v15/services/tools/tool_registry.py`
**Method:** `pick_card_for_task()`

**Change:**
```python
# BEFORE
preferred_assistant_kind = str(preferred_assistant_kind or '').strip().lower()
if preferred_assistant_kind:
    for card in self.list_cards():
        card_kind = str(card.metadata.get('assistant_kind') or '').strip().lower()
        if card_kind == preferred_assistant_kind:
            return self.refresh_card(card)

# AFTER
preferred_assistant_kind = str(preferred_assistant_kind or '').strip().lower()
# Identity mapping: normalize synaptic router names to ToolCard metadata names
# SynapticRouter may produce names like 'chatgpt_web', 'claude_web', 'ollama_local'
# but ToolCard metadata uses short names like 'chatgpt', 'claude', 'ollama'
identity_mapping = {
    'chatgpt_web': 'chatgpt',
    'claude_web': 'claude',
    'ollama_local': 'ollama',
}
preferred_assistant_kind = identity_mapping.get(preferred_assistant_kind, preferred_assistant_kind)
if preferred_assistant_kind:
    for card in self.list_cards():
        card_kind = str(card.metadata.get('assistant_kind') or '').strip().lower()
        if card_kind == preferred_assistant_kind:
            return self.refresh_card(card)
```

**Scope:**
- Only affects `preferred_assistant_kind` resolution
- Does not change keyword scoring fallback
- Does not change `cards[0]` fallback for unmapped kinds
- Applies globally to all callers of `pick_card_for_task()`

## Pre-Fix Evidence

**Test:** `tests/test_synaptic_assistant_identity.py::test_assistant_identity_mapping_chatgpt_web`

**Execution:**
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5
PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src
/c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_assistant_identity.py::test_assistant_identity_mapping_chatgpt_web -v
```

**Result:** FAILED - `assert 'claude' == 'chatgpt'`

**Interpretation:**
`preferred_assistant_kind='chatgpt_web'` → returned ToolCard with `assistant_kind='claude'`
This confirms silent substitution via `cards[0]` fallback.

## Post-Fix Evidence

**Test:** Same test file, all 8 cases

**Execution:**
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5
PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src
/c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_assistant_identity.py -v
```

**Result:** 8 passed

**Cases covered:**
1. `codex` → `codex_installed` ✓
2. `chatgpt` → `chatgpt_installed` or `chatgpt_web_assisted` ✓
3. `claude` → `claude_installed` or `claude_web_assisted` ✓
4. `ollama` → `ollama_llm` ✓
5. `chatgpt_web` → `chatgpt_installed` or `chatgpt_web_assisted` ✓ (FIXED)
6. `claude_web` → `claude_installed` or `claude_web_assisted` ✓ (FIXED)
7. `ollama_local` → `ollama_llm` ✓ (FIXED)
8. `unknown_assistant_xyz` → does not claim semantic match ✓

## Regression

**Test suites:**
- `test_synaptic_router.py`: 39 passed
- `test_p0_b_external_action_authorization.py`: 14 passed

**No regression detected.**

## Semantic Matrix

| Input preferred_assistant_kind | Expected ToolCard assistant_kind | Observed pre-fix | Observed post-fix |
|-------------------------------|----------------------------------|------------------|-------------------|
| `codex` | `codex` | `codex` | `codex` |
| `chatgpt` | `chatgpt` | `chatgpt` | `chatgpt` |
| `claude` | `claude` | `claude` | `claude` |
| `ollama` | `ollama` | `ollama` | `ollama` |
| `chatgpt_web` | `chatgpt` | `claude` (BUG) | `chatgpt` (FIXED) |
| `claude_web` | `claude` | (unrelated) | `claude` (FIXED) |
| `ollama_local` | `ollama` | (unrelated) | `ollama` (FIXED) |
| `unknown_assistant_xyz` | no semantic match | `cards[0]` (fallback) | `cards[0]` (fallback, not claimed as match) |

## Epistemic Status

**implemented:** YES - identity mapping added to `pick_card_for_task()`
**proven:** YES - pre-fix test failed, post-fix test passed
**observed:** YES - test traverses real `ToolRegistry.pick_card_for_task()`
**caused:** YES - identity mapping causes correct semantic match

## ΔK

1. **Identity Mapping Required:** SynapticRouter produces names with suffixes (`_web`, `_local`) that don't match ToolCard metadata names. A mapping layer is required to preserve semantic identity.

2. **False Authority via Fallback:** `cards[0]` fallback in `pick_card_for_task()` produces false authority for non-matching assistant kinds. The contract "non-None ToolCard = authoritative selection" is violated when fallback is used.

3. **Non-None ≠ Semantic Match:** A non-None ToolCard is not evidence of semantic match. The distinction between "match" and "fallback" must be preserved in the selection path.

## Δπ

**Policy Change:**
- Before: Exact match only, no normalization of naming conventions
- After: Identity mapping normalizes synaptic router names to ToolCard metadata names before exact match

**Preserved:**
- Keyword scoring fallback unchanged
- `cards[0]` fallback unchanged
- Exact match semantics for unmapped kinds unchanged

## ΔB

**NOT MEASURED** - Requires evidence of routing end-to-end including `adapter.run()` and outcome.

## ΔY

**NOT MEASURED** - Requires outcome measurement real.

## Remaining Uncertainty

1. **Both Keys Precedence:** The test case for both `candidate_assistant_kinds` and `allowed_assistant_kinds` present was not explicitly tested. The existing code prioritizes `candidate_assistant_kinds` when present.

2. **Fallback Authority:** The `cards[0]` fallback still exists for unmapped kinds. This should be replaced with explicit None or a fallback classification in metadata, but that was out of scope for this edge.

3. **End-to-End Routing:** This fix only closes the identity mapping edge. The complete routing chain including `adapter.run()` and outcome remains unverified.

## Next Causal Edge

Once assistant identity is preserved:
```
correct selected_assistant_kind + correct ToolCard
→ SynapticRouter.decide() operational selection
→ ToolTask.tool_id semantic correspondence
→ adapter.run()
→ result
→ outcome
```

The next edge to verify is whether the routing now produces correct operational tool selection end-to-end.

## Memory Operating Protocol

**source historical record:** KD-SYNAPTIC-ASSISTANT-IDENTITY.md
**CURRENT-STATE impact:** Identity mapping in ToolRegistry preserves synaptic assistant semantics
**CONTEXT-INDEX impact:** NOT DETERMINADO (no ejecutado en este ciclo)
**UNRESOLVED-KNOWLEDGE impact:** Fallback authority (`cards[0]`) remains partially unresolved
**next-AI routing impact:** Should observe correct semantic mapping from SynapticRouter to ToolCard

**Nota:** Este ciclo fue exclusivamente de implementación. No se ejecutó la absorción completa de memoria.
