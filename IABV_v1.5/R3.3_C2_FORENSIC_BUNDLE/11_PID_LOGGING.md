R3.3 PID LOGGING
================

PID CALCULATION METHODS
-----------------------

CLIENT PID
-----------
Calculated by: os.getpid() from test process
Location: test_c2_real_self_update_authority.py line 65
Code: client_pid = os.getpid()

AUTHORITY PID
-------------
Calculated by: authority_process.pid from multiprocessing.Process
Location: conftest.py line 51
Code: authority_pid = authority_process.pid

OS-OBSERVED CLIENT PID
----------------------
Calculated by: win32pipe.GetNamedPipeClientProcessId(pipe_handle)
Location: authority_server.py line 265
Code: client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)

PID EQUALITY MEANING
--------------------
PID equality = (client_pid == authority_pid)

Meaning: TRUE if client and authority are in the SAME process
Meaning: FALSE if client and authority are in DIFFERENT processes

For security boundary testing, we require PID equality = FALSE (different processes)

R3.3 PID LOGGING CODE
-----------------------
Location: authority_server.py lines 264-271

```python
client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)
authority_pid = os.getpid()
pids_equal = (client_pid == authority_pid)
print(f"[AuthorityServer] Client connected", flush=True)
print(f"[AuthorityServer]   Client PID (OS-observed): {client_pid}", flush=True)
print(f"[AuthorityServer]   Authority PID: {authority_pid}", flush=True)
print(f"[AuthorityServer]   PID equality check: {pids_equal}", flush=True)
```

PREVIOUS ANOMALY (BEFORE R3.3)
-------------------------------
Before R3.3, the PID logging was misleading:

Old code (approximate):
```python
print(f"[AuthorityServer] PID equality check: {client_pid != os.getpid()}", flush=True)
```

This would print "True" when PIDs were different (correct for separation)
but the variable name "equality check" was confusing because it was
showing the NEGATION of equality (inequality).

R3.3 FIX
--------
R3.3 changed the logging to explicitly show the boolean equality value:

New code:
```python
pids_equal = (client_pid == authority_pid)
print(f"[AuthorityServer]   PID equality check: {pids_equal}", flush=True)
```

Now:
- pids_equal = True when PIDs are the same (same process)
- pids_equal = False when PIDs are different (different processes)

This is semantically correct and matches the variable name.
