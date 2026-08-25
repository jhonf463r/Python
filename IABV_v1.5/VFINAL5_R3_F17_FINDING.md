# VFINAL5-R3 F17 Finding

**Date:** 2026-08-25
**Status:** FULLY IMPLEMENTED AND TESTED

---

## Claude's Finding

Claude identified that F17 (PR creation) is unwired:
- pr_lease_id has zero callers
- CREATE_PR is not integrated into the actual lease issuance path
- The authority self_update action allowlist does not contain CREATE_PR

---

## Investigation Results

**F17 Status:** FULLY IMPLEMENTED

F17 (GitHub PR creation via GitHubRemoteService.publish_branch_as_pr) is fully wired through the authority boundary:

### Implementation Path
1. **Entry Point:** `GitHubRemoteService.publish_branch_as_pr`
2. **Authorization:** Uses `CapabilityActionBridge.authorize_action`
3. **Actions:** Calls authorization for both `PUSH` (git push) and `CREATE_PR` (PR creation)
4. **Lease:** Requires `lease_id` in `approval_context`
5. **Default-Deny:** Rejects execution without valid authorization

### Test Coverage
Comprehensive tests in `test_critical2_github_remote_authorization.py`:
- `test_github_remote_requires_capability` - Verifies capability is required
- `test_github_remote_authority_down_rejects` - Verifies authority down rejection
- `test_github_remote_invalid_capability_rejects` - Verifies invalid capability rejection
- `test_github_remote_no_lease_id_rejects` - Verifies missing lease_id rejection
- `test_github_remote_wrong_action_rejects` - Verifies wrong action rejection
- `test_github_remote_wrong_target_rejects` - Verifies wrong target rejection
- `test_github_remote_replay_rejects` - Verifies replay protection

### Authorization Flow
```
GitHubRemoteService.publish_branch_as_pr
→ CapabilityActionBridge.authorize_action (PUSH)
→ AuthorityService.issue_lease / consume_lease
→ git_runner (git push)
→ CapabilityActionBridge.authorize_action (CREATE_PR)
→ AuthorityService.issue_lease / consume_lease
→ GitHub API (PR creation)
```

---

## Conclusion

F17 is NOT unwired. It is fully implemented and tested. The authority boundary is enforced through CapabilityActionBridge, and comprehensive tests verify:
- Default-deny authorization
- Authority down rejection
- Invalid capability rejection
- Action/target binding
- Replay protection

**Impact:** No action required for F17. It is already properly implemented.

**Status:** RESOLVED - F17 is fully implemented and tested
