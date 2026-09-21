# CHAT-ARCH 2026-09-21-010 — I0 M3 runtime revision lineage correction

## Provenance finding

Repository: jhonf463r/Python.

Target runtime revision: 7753ce5632370b2a03726aeff63dbcd1ac7afc42.

The earlier STOP CONDITION that classified 7753 as missing the I0 credential binding seam is not supported by the Git ancestry.

## Direct evidence

GitHub compare:
51047cc18b4f3d178e6eb7fa2f5127049d778192...7753ce5632370b2a03726aeff63dbcd1ac7afc42
reports:
- status: ahead
- ahead_by: 9
- behind_by: 0
- merge_base: 51047cc18b4f3d178e6eb7fa2f5127049d778192

The nine commits are:
1. 64260e424b75fc4b0c3677c7a5d85b870ee7cc8c
2. 22d8b1e65b7bd0c1bfa9b4e79d863dc8285f02d7
3. 95a0bf758c9ded1e70bbd7bd1476a978404d90b8
4. e561da2d786daa79170d709da1283b241f39fb4f
5. 2c6549e06350a5cedf7c7a896ee1a0adaeb028a6
6. cae69affc9dc70793101617f0edf3d7e007236da
7. 7b8b52501e5335df8678cf916329a7cdc04e5251
8. 6c8be71c7dc2718802c83f79e03f90bedf3e818b
9. 7753ce5632370b2a03726aeff63dbcd1ac7afc42

Thus 51047cc18 is an ancestor of 7753, even though 7753's immediate parent is 6c8be71c7.

## Production seam at target

At 7753, DevinApiToolAdapter still exposes the I0 seam:
- _headers(api_key: str | None = None)
- run(..., api_key: str | None = None)
- effective_key = invocation override or constructor key
- effective_key is passed to both POST and polling GET boundaries.

Therefore:
commit-local parent != absence of ancestor feature
immediate diff scope != cumulative lineage scope

## M3 test at target

7753 adds the corrected polling coverage:
- POST returns status='running'
- GET returns status='finished'
- POST Authorization asserts invocation key
- GET Authorization asserts invocation key

The mutation described by M3 remains the discriminating test for GET propagation.

## Current working-state implication

Repository current HEAD observed separately: f0c98ca1af756273f14a7fae65fafa9bd69a3a30.
7753 and f0 are on diverged histories. This does not invalidate a deliberately detached runtime worktree pinned to 7753.

## Knowledge delta

Previous hypothesis:
"7753 test correction lacks the production seam."

Corrected state:
"7753 contains both the credential-binding production seam and the corrected M3 test because 51047cc18 is an ancestor of 7753."

## Next causal edge

Do not re-integrate or recreate M3.
Use detached 7753 for the next Windows runtime credential-binding verification, with an explicit provenance gate proving:
- HEAD == 7753ce5632370b2a03726aeff63dbcd1ac7afc42
- 51047cc18b4f3d178e6eb7fa2f5127049d778192 is ancestor of HEAD
- DevinApiToolAdapter.run(..., api_key=...) exists at HEAD
- the M3 GET assertion exists at HEAD.

Runtime result must still be classified independently; no I0 closure is inferred from this lineage correction.
