R3.3 CALL GRAPH FORENSIC
=======================

This document reconstructs the call graph from the audited code at commit 5870015c0.

CAPABILITY ACQUISITION PATH
---------------------------

test_real_self_update_authorized (test_c2_real_self_update_authority.py:70-145)
  ↓
acquire_capability_for_execution() (capability_lifecycle.py:22-99)
  ↓
AuthorityClient() (authority_client.py:~line 60)
  ↓
client.connect() (authority_client.py:~line 62)
  ↓
Named Pipe: \\.\pipe\IABV_Authority (authority_client.py:~line 130)
  ↓
AuthorityServer._handle_client() (authority_server.py:263-359)
  ↓
AuthorityService.register_execution() (authority_service.py:~line 200)
  ↓
client.issue_lease() (authority_client.py:~line 360)
  ↓
AuthorityService.issue_lease() (authority_service.py:~line 300)
  ↓
returns: {run_id, execution_id, lease_id, action, target, authorized_scope}
  ↓
client.disconnect() (capability_lifecycle.py:99)

AUTHORIZATION PATH
-----------------

test_real_self_update_authorized (test_c2_real_self_update_authority.py:107-128)
  ↓
AuthorityClient() (test line 107)
  ↓
client.connect() (test line 108)
  ↓
CapabilityActionBridge(authority_client=client) (test line 110)
  ↓
write_repo_file_impl(..., capability_action_bridge=bridge, ...) (test line 112-121)
  ↓
write_repo_file_impl() (self_update_tools.py:44-110)
  ↓
ActionRequest(lease_id=..., execution_id=..., action='WRITE_REPOSITORY_FILE', ...) (self_update_tools.py:69-75)
  ↓
capability_action_bridge.authorize_action(action_request) (self_update_tools.py:76)
  ↓
CapabilityActionBridge.authorize_action() (capability_action_bridge.py:94-142)
  ↓
ConsumeLeaseRequest(..., lease_id, execution_id, requested_action, requested_target) (capability_action_bridge.py:111-116)
  ↓
self._authority_client.consume_lease(...) (capability_action_bridge.py:119-124)
  ↓
AuthorityClient.consume_lease() (authority_client.py:~line 400)
  ↓
Named Pipe: \\.\pipe\IABV_Authority
  ↓
AuthorityServer._handle_client()
  ↓
AuthorityService.consume_lease() (authority_service.py:~line 400)
  ↓
returns: ActionAuthorization(authorized=True/False, consumed_at=...)
  ↓
client.disconnect() (test line 128)

PROTECTED EFFECT PATH
---------------------

write_repo_file_impl() (self_update_tools.py:44-110)
  ↓
auth_result.authorized == True (self_update_tools.py:77)
  ↓
target.write_text(content, encoding="utf-8") (self_update_tools.py:102)
  ↓
returns: {"status": "ok", "path": ..., "bytes_written": ...}

NEGATIVE PATH (UNAUTHORIZED)
-----------------------------

unauthorized request (e.g., wrong_session_denied test)
  ↓
AuthorityClient.verify_execution_context() (test line 167)
  ↓
AuthorityService.verify_execution_context() (authority_service.py:~line 350)
  ↓
returns: {valid: False, error: "Session ID mismatch"}
  ↓
assert not verification.get('valid') (test line 175)
  ↓
NO EFFECT - file not modified

OR

unauthorized request (e.g., missing_lease_denied test)
  ↓
CapabilityActionBridge.authorize_action(action_request with lease_id=None) (test line 322)
  ↓
AuthorityService.consume_lease() with lease_id=None
  ↓
returns: ActionAuthorization(authorized=False, error="...")
  ↓
assert auth_result.authorized == False (test line 325)
  ↓
NO EFFECT - file not modified
