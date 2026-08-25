# PART 6: Self-Update Test Matrix

**Date:** 2026-08-24  
**Task:** PART 6 — Self-Update Test Matrix

---

## Self-Update Test Matrix

### write_repo_file

**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Authority:** ✅ CANONICAL P0.213 (C-2 fixed)
- Action: WRITE_REPOSITORY_FILE
- Target: file:{relative_path}
- Scope: self_update

**Tests Required:**

**A. write_repo_file without capability**
- [ ] Test: Call without capability_action_bridge
- Expected: REJECT
- Expected: file NOT modified

**B. write_repo_file with invalid capability**
- [ ] Test: Call with invalid lease_id
- Expected: REJECT
- Expected: file NOT modified

**C. write_repo_file with wrong action**
- [ ] Test: Call with wrong action in ActionRequest
- Expected: REJECT
- Expected: file NOT modified

**D. write_repo_file with wrong target**
- [ ] Test: Call with wrong target in ActionRequest
- Expected: REJECT
- Expected: file NOT modified

**E. write_repo_file with authority down**
- [ ] Test: Call with authority process down
- Expected: REJECT
- Expected: file NOT modified

**F. write_repo_file with valid capability**
- [ ] Test: Call with valid capability
- Expected: AUTHORIZED
- Expected: file modified

**G. write_repo_file with sensitive path**
- [ ] Test: Call with .git/config path
- Expected: REJECT
- Expected: file NOT modified

**H. write_repo_file with directory traversal**
- [ ] Test: Call with ../../../etc/passwd
- Expected: REJECT
- Expected: file NOT modified

**Status:** ⏳ TESTS NOT IMPLEMENTED

---

### apply_text_patch

**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Authority:** ✅ CANONICAL P0.213 (C-2 fixed)
- Action: APPLY_PATCH
- Target: file:{relative_path}
- Scope: self_update

**Tests Required:**

**A. apply_text_patch without capability**
- [ ] Test: Call without capability_action_bridge
- Expected: REJECT
- Expected: file NOT modified

**B. apply_text_patch with invalid capability**
- [ ] Test: Call with invalid lease_id
- Expected: REJECT
- Expected: file NOT modified

**C. apply_text_patch with wrong action**
- [ ] Test: Call with wrong action in ActionRequest
- Expected: REJECT
- Expected: file NOT modified

**D. apply_text_patch with wrong target**
- [ ] Test: Call with wrong target in ActionRequest
- Expected: REJECT
- Expected: file NOT modified

**E. apply_text_patch with authority down**
- [ ] Test: Call with authority process down
- Expected: REJECT
- Expected: file NOT modified

**F. apply_text_patch with valid capability**
- [ ] Test: Call with valid capability
- Expected: AUTHORIZED
- Expected: patch applied

**G. apply_text_patch with old_text not found**
- [ ] Test: Call with old_text not in file
- Expected: REJECT
- Expected: file NOT modified

**H. apply_text_patch with directory traversal**
- [ ] Test: Call with ../../../etc/passwd
- Expected: REJECT
- Expected: file NOT modified

**Status:** ⏳ TESTS NOT IMPLEMENTED

---

### git_commit_and_push

**Location:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Authority:** ✅ CANONICAL P0.213 (C-2 fixed)
- Action: GIT_COMMIT (commit)
- Action: GIT_PUSH (push)
- Target: git:workspace
- Scope: self_update

**Tests Required:**

**A. git_commit_and_push without capability**
- [ ] Test: Call without capability_action_bridge
- Expected: REJECT
- Expected: no commit
- Expected: no push

**B. git_commit_and_push with invalid capability**
- [ ] Test: Call with invalid lease_id
- Expected: REJECT
- Expected: no commit
- Expected: no push

**C. git_commit_and_push with wrong action**
- [ ] Test: Call with wrong action in ActionRequest
- Expected: REJECT
- Expected: no commit
- Expected: no push

**D. git_commit_and_push with wrong target**
- [ ] Test: Call with wrong target in ActionRequest
- Expected: REJECT
- Expected: no commit
- Expected: no push

**E. git_commit_and_push with authority down**
- [ ] Test: Call with authority process down
- Expected: REJECT
- Expected: no commit
- Expected: no push

**F. git_commit_and_push with valid capability**
- [ ] Test: Call with valid capability
- Expected: AUTHORIZED
- Expected: commit created
- Expected: push executed

**G. git_commit_and_push with commit only**
- [ ] Test: Call with push=False
- Expected: AUTHORIZED for commit
- Expected: commit created
- Expected: no push

**H. git_commit_and_push with invalid commit message**
- [ ] Test: Call with message < 5 chars
- Expected: REJECT
- Expected: no commit
- Expected: no push

**I. git_commit_and_push with nothing to commit**
- [ ] Test: Call with no changes
- Expected: OK
- Expected: no commit
- Expected: no push

**Status:** ⏳ TESTS NOT IMPLEMENTED

---

## Real Side-Effect Proof

For negative cases, tests must prove:

**Filesystem unchanged:**
- [ ] File modification time unchanged
- [ ] File hash unchanged
- [ ] File content unchanged

**Git state unchanged:**
- [ ] Git commit NOT created
- [ ] Git push NOT attempted
- [ ] Git log unchanged

**Patch NOT applied:**
- [ ] File content unchanged
- [ ] Old text still present
- [ ] New text NOT present

**Do NOT rely only on authorization=False.**

---

## PART 6 Status

**Status:** ⏳ COMPLETE (Documentation Only)

The self-update test matrix has been documented. The actual security tests have not been implemented. The C-2 code changes are correct, but comprehensive security tests are pending.
