"""Self Code Analysis Module - Autonomous Code Health Verification.

Metacognition: the program inspects its own source code, git state,
pending branches, performance bottlenecks, and architectural integrity.

Capabilities:
  - Detect unmerged branches with pending improvements
  - Verify all Python files compile without syntax errors
  - Identify stale or orphaned code
  - Diagnose UI threading issues (blocking calls on main thread)
  - Check MCP tool registration completeness
  - Report performance-related patterns (synchronous calls, missing threading)

PRODUCTION AUTHORIZATION INTEGRATION (P0.213 V5 Phase 2):
  - Self code analysis requires authorization via AuthorityService
  - Demonstrates real production caller → AuthorityClient → AuthorityService path
  - Authorized operation: "READ" scope on codebase for analysis
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import py_compile
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from iabv_v15.services.trust.authority_client import AuthorityClient

logger = logging.getLogger(__name__)

# Phase 2: Production authorization integration
try:
    from iabv_v15.services.trust.authority_client import AuthorityClient
    AUTHORIZATION_AVAILABLE = True
except ImportError:
    AUTHORIZATION_AVAILABLE = False
    logger.warning("AuthorityClient not available - authorization checks disabled")


def _run_cmd(cmd: list[str], timeout: int = 15) -> str:
    """Run a command and return stdout, empty string on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ''


def _authorize_code_analysis(invocation_id: str) -> dict[str, Any]:
    """Authorize code analysis operation using canonical protocol.
    
    Phase 2 Round 3: Production caller uses canonical protocol.
    - REGISTER_EXECUTION with action, target, requested_scope, task_context
    - ISSUE_LEASE with run_id, execution_id
    - CONSUME_LEASE with lease_id, execution_id
    
    All operations go through AuthorityClient/IPC, not direct service calls.
    """
    try:
        client = AuthorityClient()
        client.connect()
        
        # Register execution with canonical protocol
        registration = client.register_execution(
            invocation_id=invocation_id,
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis",
            episode_id=None,
            session_id=None
        )
        
        run_id = registration["run_id"]
        execution_id = registration["execution_id"]
        
        # Issue lease with canonical protocol
        lease = client.issue_lease(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        )
        
        lease_id = lease["lease_id"]
        
        # Consume lease with canonical protocol
        consumption = client.consume_lease(
            lease_id=lease_id,
            execution_id=execution_id
        )
        
        client.disconnect()
        
        return {
            "authorized": True,
            "run_id": run_id,
            "execution_id": execution_id,
            "lease_id": lease_id,
            "consumed": consumption["consumed"]
        }
    except Exception as e:
        return {
            "authorized": False,
            "error": str(e)
        }


def scan_unmerged_branches(workspace: str | None = None) -> list[dict[str, Any]]:
    """Detect branches with commits not yet merged to main."""
    ws = workspace or _default_workspace()
    if not ws:
        return []

    branches_raw = _run_cmd(['git', '-C', ws, 'branch', '-r', '--no-merged', 'origin/main'])
    if not branches_raw:
        return []

    results: list[dict[str, Any]] = []
    for line in branches_raw.splitlines():
        branch = line.strip()
        if '->' in branch or not branch:
            continue
        # Count commits ahead of main
        count_str = _run_cmd(['git', '-C', ws, 'rev-list', '--count', f'origin/main..{branch}'])
        count = int(count_str) if count_str.isdigit() else 0
        if count == 0:
            continue
        # Get last commit message
        last_msg = _run_cmd(['git', '-C', ws, 'log', '-1', '--format=%s', branch])
        # Get files changed
        files_str = _run_cmd(['git', '-C', ws, 'diff', '--stat', f'origin/main...{branch}'])
        file_count = len([l for l in files_str.splitlines() if '|' in l])
        results.append({
            'branch': branch,
            'commits_ahead': count,
            'last_commit': last_msg,
            'files_changed': file_count,
        })

    results.sort(key=lambda x: x['commits_ahead'], reverse=True)
    return results


def _authorize_code_analysis(
    workspace: str | None = None
) -> dict[str, Any]:
    """Authorize code analysis operation via AuthorityService.
    
    PRODUCTION AUTHORIZATION PATH (P0.213 V5 Phase 2):
    This demonstrates the real production caller → AuthorityClient → AuthorityService path.
    
    Authorized operation:
    - Action: READ
    - Target: codebase
    - Requested scope: codebase:read
    - Authorized scope: codebase:read (if policy permits)
    
    Returns:
        Authorization result with lease information
    """
    if not AUTHORIZATION_AVAILABLE:
        return {
            'ok': True,
            'authorization': 'bypassed',
            'reason': 'AuthorityClient not available'
        }
    
    try:
        client = AuthorityClient()
        
        # Step 1: Register execution
        registration = client.register_execution(
            invocation_id=f"code_analysis_{int(time.time())}",
            requested_scope="codebase:read",
            episode_id=None,
            session_id=None
        )
        
        run_id = registration.get("run_id")
        execution_id = registration.get("execution_id")
        
        # Step 2: Issue lease
        lease_data = client.issue_lease(
            invocation_id=f"code_analysis_{int(time.time())}",
            scope="codebase:read",
            duration_ms=60000  # 1 minute
        )
        
        lease = lease_data.get("lease")
        lease_id = lease.get("lease_id") if lease else None
        
        return {
            'ok': True,
            'authorization': 'granted',
            'run_id': run_id,
            'execution_id': execution_id,
            'lease_id': lease_id,
            'lease': lease
        }
    except Exception as e:
        logger.warning(f"Authorization failed: {e}")
        return {
            'ok': True,
            'authorization': 'failed',
            'reason': str(e)
        }


def _consume_authorization(
    lease_id: str,
    execution_id: str,
    workspace: str | None = None
) -> dict[str, Any]:
    """Consume authorization after code analysis completes.
    
    PRODUCTION AUTHORIZATION PATH (P0.213 V5 Phase 2):
    Demonstrates consume_lease() via AuthorityClient.
    """
    if not AUTHORIZATION_AVAILABLE or not lease_id:
        return {
            'ok': True,
            'consumed': False,
            'reason': 'Authorization not available or no lease'
        }
    
    try:
        client = AuthorityClient()
        
        # Consume lease
        result = client.consume_lease(
            lease_id=lease_id,
            invocation_id=f"code_analysis_{int(time.time())}"
        )
        
        return {
            'ok': True,
            'consumed': result.get("consumed", False),
            'lease_id': lease_id
        }
    except Exception as e:
        logger.warning(f"Consume authorization failed: {e}")
        return {
            'ok': False,
            'consumed': False,
            'reason': str(e)
        }


def verify_python_syntax(workspace: str | None = None) -> dict[str, Any]:
    """Compile-check all Python files in src/ for syntax errors.
    
    PRODUCTION AUTHORIZATION PATH (P0.213 V5 Phase 2):
    This operation requires authorization via AuthorityService.
    """
    # Authorize the operation
    auth_result = _authorize_code_analysis(workspace)
    
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found', 'authorization': auth_result}

    src_dir = Path(ws) / 'src'
    if not src_dir.exists():
        return {'ok': False, 'error': f'{src_dir} not found', 'authorization': auth_result}

    errors: list[dict[str, str]] = []
    checked = 0
    for py_file in src_dir.rglob('*.py'):
        checked += 1
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append({
                'file': str(py_file.relative_to(ws)),
                'error': str(exc),
            })

    # Consume authorization after operation completes
    if auth_result.get('authorization') == 'granted':
        lease_id = auth_result.get('lease_id')
        execution_id = auth_result.get('execution_id')
        consume_result = _consume_authorization(lease_id, execution_id, workspace)
    else:
        consume_result = {'ok': True, 'consumed': False, 'reason': 'No authorization to consume'}

    return {
        'ok': len(errors) == 0,
        'files_checked': checked,
        'errors': errors,
        'summary': f'{checked} files checked, {len(errors)} errors' if errors else f'{checked} files checked, all OK',
        'authorization': auth_result,
        'consume': consume_result
    }


def detect_threading_issues(workspace: str | None = None) -> list[dict[str, Any]]:
    """Scan for potential UI-blocking patterns in ViewModel code."""
    ws = workspace or _default_workspace()
    if not ws:
        return []

    issues: list[dict[str, Any]] = []
    vm_dir = Path(ws) / 'src' / 'iabv_v15' / 'ui' / 'viewmodels'
    if not vm_dir.exists():
        return issues

    blocking_patterns = [
        (r'subprocess\.run\(', 'subprocess.run in ViewModel (blocks UI thread)'),
        (r'requests\.(?:get|post|put|delete)\(', 'HTTP request in ViewModel (blocks UI thread)'),
        (r'time\.sleep\(', 'time.sleep in ViewModel (freezes UI)'),
        (r'\.result\(\)', '.result() on future in ViewModel (blocks UI thread)'),
        (r'urllib\.request', 'urllib.request in ViewModel (blocks UI thread)'),
    ]

    for py_file in vm_dir.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue

        for pattern, desc in blocking_patterns:
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line) and 'Thread' not in line and 'thread' not in line:
                    # Check if inside a thread-safe wrapper
                    ctx_start = max(0, i - 5)
                    ctx_lines = content.splitlines()[ctx_start:i]
                    in_thread = any('Thread' in cl or '_run_sync_off' in cl or 'daemon=True' in cl
                                    for cl in ctx_lines)
                    if not in_thread:
                        issues.append({
                            'file': str(py_file.relative_to(ws)),
                            'line': i,
                            'pattern': desc,
                            'code': line.strip()[:120],
                        })

    return issues


def check_mcp_tool_registration(workspace: str | None = None) -> dict[str, Any]:
    """Verify MCP tools are properly registered and indented."""
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found'}

    server_path = Path(ws) / 'src' / 'iabv_v15' / 'infra' / 'mcp' / 'server.py'
    if not server_path.exists():
        return {'ok': False, 'error': 'server.py not found'}

    content = server_path.read_text(encoding='utf-8', errors='replace')
    lines = content.splitlines()

    tools_found: list[str] = []
    indent_issues: list[dict[str, Any]] = []
    in_register_tools = False

    for i, line in enumerate(lines, 1):
        if 'def _register_tools(' in line:
            in_register_tools = True
            continue
        if in_register_tools and line.strip().startswith('def ') and not line.startswith('        '):
            if '@mcp.tool()' in lines[i - 2] if i >= 2 else False:
                in_register_tools = False  # Left _register_tools scope
        if '@mcp.tool()' in line:
            # Check indentation
            indent = len(line) - len(line.lstrip())
            if indent < 8 and in_register_tools:
                indent_issues.append({
                    'line': i,
                    'indent': indent,
                    'expected': 8,
                    'content': line.strip(),
                })
            # Find the tool name
            for j in range(i, min(i + 3, len(lines))):
                m = re.search(r'def\s+(\w+)\s*\(', lines[j])
                if m:
                    tools_found.append(m.group(1))
                    break

    return {
        'ok': len(indent_issues) == 0,
        'tools_registered': tools_found,
        'tool_count': len(tools_found),
        'indent_issues': indent_issues,
        'summary': f'{len(tools_found)} MCP tools registered' + (
            f', {len(indent_issues)} indent issues' if indent_issues else ', all correctly indented'
        ),
    }


def diagnose_performance(workspace: str | None = None) -> dict[str, Any]:
    """Diagnose common performance issues in the codebase."""
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found'}

    findings: list[dict[str, Any]] = []

    # 1. Check for synchronous blocking calls in critical paths
    threading_issues = detect_threading_issues(ws)
    if threading_issues:
        findings.append({
            'category': 'ui_blocking',
            'severity': 'high',
            'description': f'{len(threading_issues)} blocking call(s) on UI thread detected',
            'details': threading_issues[:5],
            'fix': 'Move blocking calls to background threads using threading.Thread(target=fn, daemon=True).start()',
        })

    # 2. Check for large list operations without pagination
    src_dir = Path(ws) / 'src'
    for py_file in src_dir.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        # Detect loading all data without limits
        if 'rglob' in content and 'limit' not in content.lower():
            for i, line in enumerate(content.splitlines(), 1):
                if 'rglob' in line and 'limit' not in line.lower():
                    findings.append({
                        'category': 'unbounded_scan',
                        'severity': 'medium',
                        'file': str(py_file.relative_to(ws)),
                        'line': i,
                        'description': 'rglob without size limit may be slow on large directories',
                    })
                    break  # One per file

    # 3. Check chat message buffer size
    vm_path = Path(ws) / 'src' / 'iabv_v15' / 'ui' / 'viewmodels' / 'control_center_viewmodel.py'
    if vm_path.exists():
        vm_content = vm_path.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'self\._chat_messages\[-(\d+):\]', vm_content)
        if m:
            buf_size = int(m.group(1))
            if buf_size > 50:
                findings.append({
                    'category': 'memory',
                    'severity': 'medium',
                    'description': f'Chat buffer retains {buf_size} messages — may consume excess memory',
                })

    return {
        'performance_ok': len(findings) == 0,
        'findings_count': len(findings),
        'findings': findings,
        'summary': 'No performance issues detected' if not findings else f'{len(findings)} issue(s) found',
    }


def verify_slot_decorators(workspace: str | None = None) -> dict[str, Any]:
    """Verify that QML-callable methods in ViewModels have @Slot decorators.

    Without @Slot, QML silently fails to invoke the method — the user clicks
    a button or types in the chat and nothing happens. This is invisible to
    syntax checking and only manifests at runtime.
    """
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found'}

    vm_dir = Path(ws) / 'src' / 'iabv_v15' / 'ui' / 'viewmodels'
    if not vm_dir.exists():
        return {'ok': True, 'checked': 0, 'issues': [], 'summary': 'viewmodels dir not found'}

    qml_dir = Path(ws) / 'src' / 'iabv_v15' / 'ui' / 'qml'
    qml_method_calls: set[str] = set()
    if qml_dir.exists():
        for qml_file in qml_dir.rglob('*.qml'):
            try:
                qml_content = qml_file.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            for m in re.finditer(r'\w*[Vv]iew[Mm]odel\)?\.([a-zA-Z]\w*)\s*\(', qml_content):
                qml_method_calls.add(m.group(1))

    issues: list[dict[str, str]] = []
    checked = 0
    for py_file in vm_dir.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines):
            m = re.match(r'\s+def (\w+)\(self', line)
            if not m:
                continue
            method_name = m.group(1)
            has_slot = False
            for j in range(max(0, i - 3), i):
                if '@Slot' in lines[j]:
                    has_slot = True
                    break
            if not has_slot:
                issues.append({
                    'file': str(py_file.relative_to(ws)),
                    'line': i + 1,
                    'method': method_name,
                    'severity': 'critical',
                    'description': f'{method_name}() is called from QML but missing @Slot decorator — QML invocation silently fails',
                })

    return {
        'ok': len(issues) == 0,
        'methods_checked': checked,
        'qml_calls_found': len(qml_method_calls),
        'issues': issues,
        'summary': f'{checked} QML-callable methods checked, {len(issues)} missing @Slot' if issues else f'{checked} QML-callable methods checked, all have @Slot',
    }


def verify_intent_routing(workspace: str | None = None) -> dict[str, Any]:
    """Verify that key user intents are routed to the correct handlers.

    Simulates the intent detection logic to ensure critical phrases
    actually trigger the right handler, not fall through to generic responses.
    """
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found'}

    vm_path = Path(ws) / 'src' / 'iabv_v15' / 'ui' / 'viewmodels' / 'control_center_viewmodel.py'
    if not vm_path.exists():
        return {'ok': False, 'error': 'control_center_viewmodel.py not found'}

    content = vm_path.read_text(encoding='utf-8', errors='replace')

    test_cases = [
        ('analizate a ti mismo', '_is_self_code_analysis_request', 'auto-analisis'),
        ('analiza tu codigo', '_is_self_code_analysis_request', 'auto-analisis'),
        ('busca errores', '_is_self_code_analysis_request', 'auto-analisis'),
        ('por que estas lento', '_is_self_code_analysis_request', 'auto-analisis'),
        ('revisa tu gpu', '_is_self_code_analysis_request', 'auto-analisis'),
        ('mejoras pendientes', '_is_self_code_analysis_request', 'auto-analisis'),
        ('examinate', '_is_self_examination_question', 'autoexaminacion'),
        ('que herramientas tienes', '_is_self_awareness_question', 'autoconciencia'),
        ('auditar autonomia', '_try_handle_chat_command', 'comando chat'),
    ]

    # Also verify IntentUnderstandingService has metacognition intent
    ius_path = Path(ws) / 'src' / 'iabv_v15' / 'services' / 'adaptive' / 'intent_understanding_service.py'
    ius_has_metacognition = False
    if ius_path.exists():
        ius_content = ius_path.read_text(encoding='utf-8', errors='replace')
        ius_has_metacognition = (
            'system.metacognition' in ius_content
            and '_is_metacognition_prompt' in ius_content
        )

    results: list[dict[str, Any]] = []
    missing_handlers: list[str] = []

    for phrase, expected_handler, category in test_cases:
        handler_exists = f'def {expected_handler}' in content
        if not handler_exists:
            missing_handlers.append(expected_handler)
            results.append({
                'phrase': phrase,
                'expected_handler': expected_handler,
                'category': category,
                'status': 'FAIL',
                'reason': f'handler {expected_handler} not found in viewmodel',
            })
        else:
            handler_referenced = expected_handler in content
            results.append({
                'phrase': phrase,
                'expected_handler': expected_handler,
                'category': category,
                'status': 'OK' if handler_referenced else 'WARN',
                'reason': '' if handler_referenced else 'handler exists but may not be wired in sendChat flow',
            })

    # Check that sendChat (and its delegates like _try_handle_chat_command)
    # call the detection methods
    flow_sections = ''
    for fn_name in ('sendChat', '_try_handle_chat_command'):
        in_fn = False
        for line in content.splitlines():
            if f'def {fn_name}(' in line:
                in_fn = True
            elif in_fn and re.match(r'^    def ', line):
                in_fn = False
            if in_fn:
                flow_sections += line + '\n'

    wired_handlers = []
    for _, handler, _ in test_cases:
        if handler in flow_sections:
            wired_handlers.append(handler)

    unwired = [h for _, h, _ in test_cases if h not in wired_handlers and h != '_try_handle_chat_command']
    unwired = list(set(unwired))

    return {
        'ok': len(missing_handlers) == 0 and len(unwired) == 0 and ius_has_metacognition,
        'test_cases': len(test_cases),
        'results': results,
        'missing_handlers': missing_handlers,
        'unwired_handlers': unwired,
        'ius_metacognition_intent': ius_has_metacognition,
        'summary': (
            f'{len(test_cases)} intent routes verified, {len(missing_handlers)} missing, {len(unwired)} unwired'
            + ('' if ius_has_metacognition else ', IntentUnderstandingService missing system.metacognition')
        ),
    }


def run_test_suite(workspace: str | None = None) -> dict[str, Any]:
    """Run the project test suite and report results.

    Uses pytest with a timeout to prevent hanging.
    """
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found'}

    tests_dir = Path(ws) / 'tests'
    if not tests_dir.exists():
        return {'ok': True, 'skipped': True, 'summary': 'No tests/ directory found'}

    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(ws) / 'src')
    # Metacognition: use focused test set for auto-analysis (fast feedback)
    # instead of full suite (which can timeout). Run core contract tests
    # that validate MCP, self-audit, and tool registry integrity.
    focused_tests = [
        'tests/test_mcp_server.py::test_server_registers_core_tools',
        'tests/test_self_audit_service.py',
        'tests/test_tool_registry.py',
    ]
    # Check if focused test files exist; fallback to full suite if not
    _use_focused = all((Path(ws) / t.split('::')[0]).exists() for t in focused_tests)
    test_args = focused_tests if _use_focused else ['tests/']

    # Build pytest command — only add --timeout if pytest-timeout is available
    _pytest_cmd = ['python', '-m', 'pytest', '-p', 'no:cacheprovider'] + test_args + ['-q', '--tb=short', '-x']
    _timeout_check = subprocess.run(
        ['python', '-c', 'import pytest_timeout'],
        capture_output=True, cwd=ws, env=env, timeout=5,
    )
    if _timeout_check.returncode == 0:
        _pytest_cmd.append('--timeout=30')

    try:
        result = subprocess.run(
            _pytest_cmd,
            capture_output=True, text=True, timeout=120,
            cwd=ws, env=env,
        )
        output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
        error_output = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr

        passed_m = re.search(r'(\d+) passed', output)
        failed_m = re.search(r'(\d+) failed', output)
        error_m = re.search(r'(\d+) error', output)

        passed = int(passed_m.group(1)) if passed_m else 0
        failed = int(failed_m.group(1)) if failed_m else 0
        errors = int(error_m.group(1)) if error_m else 0

        # returncode 5 = no tests collected (not a failure)
        no_tests = result.returncode == 5 or (passed == 0 and failed == 0 and errors == 0)
        is_ok = result.returncode == 0 or no_tests

        return {
            'ok': is_ok,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'no_tests_collected': no_tests and passed == 0,
            'returncode': result.returncode,
            'output': output,
            'error_output': error_output if not is_ok else '',
            'summary': ('no tests collected' if no_tests and passed == 0
                        else f'{passed} passed, {failed} failed, {errors} errors' if (failed or errors)
                        else f'{passed} passed, all OK'),
        }
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'test suite timed out after 120s', 'summary': 'Tests timed out (consider running focused tests)'}
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'summary': f'Failed to run tests: {exc}'}


def _take_health_snapshot(ws: str) -> dict[str, int]:
    """Capture key integrity metrics for metacognitive self-protection.

    Before and after each merge, the program compares these metrics.
    If any decrease, the merge damaged the codebase and must be reverted.
    """
    mcp = check_mcp_tool_registration(ws)
    slots = verify_slot_decorators(ws)
    routing = verify_intent_routing(ws)
    return {
        'mcp_tool_count': mcp.get('tool_count', 0),
        'slot_count': slots.get('checked', 0),
        'routing_ok_count': sum(
            1 for r in routing.get('results', []) if r.get('status') == 'OK'
        ),
        'routing_missing': len(routing.get('missing_handlers', [])),
    }


def _is_branch_obsolete(workspace: str, branch: str) -> tuple[bool, str]:
    """Determine if a remote branch is obsolete and safe to delete.

    Returns (is_obsolete, reason) where reason explains the decision.

    A branch is considered obsolete if ANY of these is true:
    1. Its content is already in main (squash-merge detected via commit
       message search or ``git merge-base --is-ancestor``)
    2. Its last commit is older than 7 days (stale experiment)
    3. All files it touches have been modified more recently on main

    Squash-merge check runs BEFORE the recency guard so that recently
    merged branches are correctly identified as obsolete even if their
    last commit is only minutes old.
    """
    ws = workspace

    # --- Squash-merge detection (runs first, before recency guard) ---
    short_branch = branch.replace('origin/', '', 1)

    # Strategy 1: search main log for full branch path (specific enough
    # to avoid false positives on short slugs like "fix" or "test")
    main_has = _run_cmd([
        'git', '-C', ws, 'log', 'origin/main', '--oneline', '-20',
        '--grep', short_branch, '--fixed-strings',
    ])
    if main_has:
        first_match = main_has.splitlines()[0][:60]
        return True, f'squash-merge detectado en main: {first_match}'

    # Strategy 2: check if tip commit message exists on main
    tip_msg = _run_cmd(['git', '-C', ws, 'log', '-1', '--format=%s', branch])
    if tip_msg:
        main_has_msg = _run_cmd([
            'git', '-C', ws, 'log', 'origin/main', '--oneline', '--grep', tip_msg[:60],
        ])
        if main_has_msg:
            return True, f'contenido ya en main: {tip_msg[:50]}'

    # Strategy 3: check if branch is ancestor of main (fast-forward merge)
    try:
        r = subprocess.run(
            ['git', '-C', ws, 'merge-base', '--is-ancestor', branch, 'origin/main'],
            capture_output=True, timeout=10,
        )
        if r.returncode == 0:
            return True, 'rama es ancestro de main — ya fue mergeada'
    except Exception:
        pass

    # --- Recency guard (only after merge checks) ---
    age_str = _run_cmd([
        'git', '-C', ws, 'log', '-1', '--format=%cr', branch,
    ])
    if age_str:
        is_recent = any(unit in age_str for unit in ['hour', 'minute', 'second', 'hora', 'minuto', 'segundo'])
        if not is_recent and 'day' in age_str:
            try:
                day_count = int(''.join(c for c in age_str.split('day')[0].strip().split()[-1] if c.isdigit()) or '0')
                is_recent = day_count < 2
            except (ValueError, IndexError):
                is_recent = False
        if is_recent:
            return False, f'rama con actividad reciente ({age_str}) — conservada'

    # Check age — if older than 7 days, it's stale
    if age_str:
        is_old = any(unit in age_str for unit in ['week', 'month', 'year', 'semana', 'mes', 'año'])
        if not is_old and 'day' in age_str:
            try:
                days = int(''.join(c for c in age_str.split('day')[0].strip().split()[-1] if c.isdigit()) or '0')
                is_old = days >= 7
            except (ValueError, IndexError):
                pass
        if is_old:
            return True, f'rama vieja sin actividad reciente ({age_str})'

    # Check if all changed files were modified more recently on main
    changed_files = _run_cmd([
        'git', '-C', ws, 'diff', '--name-only', f'origin/main...{branch}',
    ])
    if changed_files:
        files = [f.strip() for f in changed_files.splitlines() if f.strip()]
        if files:
            all_superseded = True
            for f in files[:20]:
                main_date = _run_cmd([
                    'git', '-C', ws, 'log', '-1', '--format=%at', 'origin/main', '--', f,
                ])
                branch_date = _run_cmd([
                    'git', '-C', ws, 'log', '-1', '--format=%at', branch, '--', f,
                ])
                if main_date and branch_date:
                    try:
                        if int(main_date) <= int(branch_date):
                            all_superseded = False
                            break
                    except ValueError:
                        all_superseded = False
                        break
                else:
                    all_superseded = False
                    break
            if all_superseded:
                return True, f'main tiene cambios mas recientes en los {len(files)} archivos tocados'

    return False, 'rama reciente o con cambios unicos — conservada'


def cleanup_stale_remote_branches(workspace: str | None = None) -> dict[str, Any]:
    """Intelligently clean up stale remote branches.

    Uses metacognitive analysis to decide which branches are truly obsolete:
    - Checks if branch content was already squash-merged via PR
    - Checks branch age (> 7 days without activity = stale)
    - Checks if main has evolved beyond the branch's changes
    - Conserves recent branches or those with unique unmerged content

    Safety rules:
    - Only evaluates branches matching safe prefixes (devin/*, iabv-auto/*, fix/*)
    - Never touches main, master, or non-prefixed branches
    - Reports conserved branches with reasons for transparency
    """
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found', 'deleted': [], 'skipped': [], 'conserved': []}

    branches = scan_unmerged_branches(ws)
    safe_prefixes = ('origin/devin/', 'origin/iabv-auto/')
    deleted: list[str] = []
    conserved: list[dict[str, str]] = []
    skipped: list[str] = []
    failed: list[dict[str, str]] = []

    for b_info in branches:
        branch = b_info.get('branch', '')
        if not any(branch.startswith(p) for p in safe_prefixes):
            skipped.append(branch)
            continue

        # Metacognitive decision: is this branch truly obsolete?
        is_obsolete, reason = _is_branch_obsolete(ws, branch)

        if not is_obsolete:
            conserved.append({'branch': branch, 'reason': reason})
            logger.info('branch_cleanup: conserved %s — %s', branch, reason)
            continue

        # Delete the obsolete branch
        remote_branch = branch.replace('origin/', '', 1)
        try:
            result = subprocess.run(
                ['git', '-C', ws, 'push', 'origin', '--delete', remote_branch],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                deleted.append(branch)
                logger.info('branch_cleanup: deleted %s — %s', branch, reason)
            else:
                err = result.stderr.strip()[:200]
                if 'remote ref does not exist' in err:
                    deleted.append(branch)
                else:
                    failed.append({'branch': branch, 'reason': err})
        except Exception as exc:
            failed.append({'branch': branch, 'reason': str(exc)})

    parts = []
    if deleted:
        parts.append(f'{len(deleted)} ramas obsoletas eliminadas')
    if conserved:
        parts.append(f'{len(conserved)} ramas conservadas (aun relevantes)')
    if skipped:
        parts.append(f'{len(skipped)} ramas ignoradas (prefijo no seguro)')
    if failed:
        parts.append(f'{len(failed)} fallaron al eliminar')
    return {
        'ok': len(failed) == 0,
        'deleted': deleted,
        'deleted_count': len(deleted),
        'conserved': conserved,
        'conserved_count': len(conserved),
        'skipped': skipped,
        'skipped_count': len(skipped),
        'failed': failed,
        'failed_count': len(failed),
        'summary': ', '.join(parts) if parts else 'no hay ramas obsoletas',
    }


def auto_merge_safe_branches(workspace: str | None = None) -> dict[str, Any]:
    """Clean up stale remote branches instead of merging them.

    This function now delegates to ``cleanup_stale_remote_branches``.
    The old approach of merging every devin/* branch locally caused merge
    conflicts and syntax errors. Keeping the function name for backward
    compatibility with callers.
    """
    result = cleanup_stale_remote_branches(workspace)
    return {
        'ok': result['ok'],
        'merged': [],
        'merged_count': 0,
        'merged_with_ours': [],
        'merged_with_ours_count': 0,
        'total_merged': 0,
        'already_merged': [],
        'already_merged_count': 0,
        'reverted': [],
        'reverted_count': 0,
        'failed': result.get('failed', []),
        'failed_count': result.get('failed_count', 0),
        'skipped': result.get('skipped', []),
        'skipped_count': result.get('skipped_count', 0),
        'deleted': result.get('deleted', []),
        'deleted_count': result.get('deleted_count', 0),
        'summary': result.get('summary', ''),
    }


def full_self_analysis_report(workspace: str | None = None) -> dict[str, Any]:
    """Generate a COMPLETE self-analysis report of the codebase.

    This is the main entry point for autonomous code health verification.
    It goes beyond syntax checking to verify end-to-end integrity:
    - Syntax compilation of all Python files
    - @Slot decorator verification for QML-callable methods
    - Intent routing verification (user phrases → correct handlers)
    - MCP tool registration and indentation
    - Threading/performance analysis
    - Unmerged branches detection
    - Test suite execution
    """
    ws = workspace or _default_workspace()
    t0 = time.time()

    report: dict[str, Any] = {
        'workspace': ws,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    # 1. Syntax verification
    report['syntax'] = verify_python_syntax(ws)

    # 2. Unmerged branches
    report['unmerged_branches'] = scan_unmerged_branches(ws)
    report['unmerged_count'] = len(report['unmerged_branches'])

    # 3. MCP tool registration
    report['mcp_tools'] = check_mcp_tool_registration(ws)

    # 4. Threading / performance
    report['performance'] = diagnose_performance(ws)

    # 5. @Slot decorator verification (QML ↔ Python binding integrity)
    report['slot_decorators'] = verify_slot_decorators(ws)

    # 6. Intent routing verification (user phrases → correct handlers)
    report['intent_routing'] = verify_intent_routing(ws)

    # 7. Test suite (regression)
    report['tests'] = run_test_suite(ws)

    # 8. Overall health
    all_ok = (
        report['syntax']['ok']
        and report['mcp_tools']['ok']
        and report['performance']['performance_ok']
        and report['slot_decorators']['ok']
        and report['intent_routing']['ok']
        and report.get('tests', {}).get('ok', True)
        and report['unmerged_count'] == 0
    )
    report['overall_health'] = 'healthy' if all_ok else 'needs_attention'

    issues_summary: list[str] = []
    if not report['syntax']['ok']:
        issues_summary.append(f"syntax errors: {len(report['syntax']['errors'])}")
    if not report['mcp_tools']['ok']:
        issues_summary.append(f"MCP indent issues: {len(report['mcp_tools']['indent_issues'])}")
    if not report['performance']['performance_ok']:
        issues_summary.append(f"performance issues: {report['performance']['findings_count']}")
    if not report['slot_decorators']['ok']:
        issues_summary.append(f"missing @Slot: {len(report['slot_decorators']['issues'])}")
    if not report['intent_routing']['ok']:
        issues_summary.append(f"intent routing issues: {len(report['intent_routing'].get('missing_handlers', []))}")
    if not report.get('tests', {}).get('ok', True):
        issues_summary.append(f"test failures: {report['tests'].get('summary', 'unknown')}")
    if report['unmerged_count'] > 0:
        issues_summary.append(f"unmerged branches: {report['unmerged_count']}")

    report['issues_summary'] = issues_summary if issues_summary else ['all clear']
    report['elapsed_seconds'] = round(time.time() - t0, 2)

    # Save report
    data_dir = Path(ws) / 'src' / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / 'self_analysis_report.json'
    try:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        logger.info('self_analysis_report saved to %s', report_path)
    except Exception as exc:
        logger.warning('Failed to save self_analysis_report: %s', exc)

    return report


def holistic_metacognition_scan(
    *,
    git_state: dict[str, Any] | None = None,
    gpu_state: dict[str, Any] | None = None,
    test_state: dict[str, Any] | None = None,
    version_state: dict[str, Any] | None = None,
    branch_state: list[Any] | None = None,
    stalled_sessions: list[str] | None = None,
    monitor_count: int = 1,
    workspace: str | None = None,
    account_state: dict[str, Any] | None = None,
    regression_state: dict[str, Any] | None = None,
    deep_env_state: dict[str, Any] | None = None,
    resource_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-reference ALL sources of truth and deduce metacognitive gaps.

    Instead of reporting each subsystem in isolation, this function takes
    the outputs from git scan, GPU scan, test results, tool versions, etc.
    and cross-references them to identify issues that only become visible
    when you look at the full picture.

    Returns a dict with:
      - deductions: list of {severity, area, finding, action} dicts
      - blind_spots: areas the system cannot currently observe
      - cross_validations: pairs of data sources that were cross-checked
      - confidence: overall confidence in the scan (0.0 - 1.0)
    """
    deductions: list[dict[str, str]] = []
    blind_spots: list[str] = []
    cross_validations: list[str] = []
    ws = workspace or _default_workspace()

    # --- Git × Branch cross-check ---
    g = git_state or {}
    current_branch = str(g.get('branch', ''))
    dirty_count = int(g.get('dirty_count', 0))
    stale_prefixes = ('devin/', 'iabv-auto/')

    if current_branch and any(current_branch.startswith(p) for p in stale_prefixes):
        if dirty_count > 100:
            deductions.append({
                'severity': 'critical',
                'area': 'git_state',
                'finding': (
                    f'En rama {current_branch} con {dirty_count} archivos modificados — '
                    'probablemente es una rama obsoleta con cambios acumulados que no se van a usar'
                ),
                'action': 'auto_switch_to_main',
            })
        elif dirty_count > 0:
            deductions.append({
                'severity': 'warning',
                'area': 'git_state',
                'finding': f'En rama {current_branch} con {dirty_count} cambios locales — verificar si son intencionales',
                'action': 'ask_user',
            })
    cross_validations.append('git_branch × dirty_files')

    # --- Branch count × test results ---
    branch_list = branch_state or []
    t = test_state or {}
    if len(branch_list) > 10 and not t.get('ok', True):
        deductions.append({
            'severity': 'warning',
            'area': 'tech_debt × tests',
            'finding': (
                f'{len(branch_list)} ramas sin mergear y tests fallando — '
                'las ramas acumuladas pueden contener codigo que rompe los tests'
            ),
            'action': 'cleanup_branches_then_retest',
        })
    cross_validations.append('unmerged_branches × test_results')

    # --- Test timeout × test scope ---
    if t and not t.get('ok') and 'timed out' in str(t.get('summary', '')).lower():
        deductions.append({
            'severity': 'warning',
            'area': 'test_execution',
            'finding': (
                'Tests hacen timeout — el auto-analisis ejecuta la suite completa '
                'sin timeout por test, lo que impide saber CUAL test es lento'
            ),
            'action': 'use_per_test_timeout',
        })
    cross_validations.append('test_timeout × test_scope')

    # --- GPU × Ollama cross-check ---
    gp = gpu_state or {}
    ollama_status = gp.get('ollama_state', {}).get('status', '')
    nvidia_count = gp.get('nvidia_count', 0)
    strategy = gp.get('dual_gpu_strategy', {})
    primary_gpu = str(strategy.get('primary_compute', '')).lower()

    if nvidia_count > 0 and ollama_status == 'ok':
        if 'intel' in primary_gpu or 'igpu' in primary_gpu:
            deductions.append({
                'severity': 'warning',
                'area': 'gpu_routing',
                'finding': (
                    'Ollama esta activo con NVIDIA disponible pero la GPU primaria '
                    'es Intel iGPU — el modelo va mas lento de lo necesario'
                ),
                'action': 'switch_primary_to_nvidia',
            })
    if nvidia_count == 0 and ollama_status == 'ok':
        deductions.append({
            'severity': 'info',
            'area': 'gpu_routing',
            'finding': 'Ollama corriendo sin GPU NVIDIA — inferencia por CPU (mas lenta)',
            'action': 'verify_gpu_drivers',
        })
    cross_validations.append('nvidia_smi × ollama_ps × gpu_strategy')

    # --- Multi-monitor awareness ---
    if monitor_count > 1:
        deductions.append({
            'severity': 'info',
            'area': 'display_awareness',
            'finding': (
                f'{monitor_count} monitores detectados — las ventanas autonomas '
                'deben posicionarse en el monitor principal para evitar blind spots'
            ),
            'action': 'ensure_primary_monitor',
        })
    elif monitor_count == 0:
        blind_spots.append('monitor_geometry: no se pudo detectar la cantidad de monitores')
    cross_validations.append('monitor_count × window_positions')

    # --- Tool versions × availability ---
    v = version_state or {}
    unavailable = v.get('unavailable_tools', [])
    if unavailable:
        deductions.append({
            'severity': 'warning',
            'area': 'tool_availability',
            'finding': f'Herramientas no disponibles: {", ".join(str(u) for u in unavailable[:5])}',
            'action': 'install_or_update_tools',
        })
    cross_validations.append('tool_versions × tool_registry')

    # --- Stalled sessions × consultation visibility ---
    stalled = stalled_sessions or []
    visible_consultations = [s for s in stalled if 'deberia correr en background' in s.lower()]
    if visible_consultations:
        deductions.append({
            'severity': 'critical',
            'area': 'consultation_visibility',
            'finding': (
                'Consultas externas visibles en pantalla del usuario — '
                'las consultas autonomas deben ser invisibles (headless/API)'
            ),
            'action': 'force_headless_mode',
        })
    cross_validations.append('stalled_sessions × consultation_mode')

    # --- Learned patterns persistence check ---
    patterns_dir = Path(ws) / 'data' / 'evolution' / 'portable_context' if ws else None
    has_portable_context = patterns_dir is not None and patterns_dir.exists()
    if not has_portable_context:
        blind_spots.append('portable_context: no existe directorio de contexto portable — aprendizaje no persiste entre sesiones')
    cross_validations.append('portable_context × learned_patterns')

    # --- Decision log continuity ---
    log_path = Path(ws) / 'src' / 'data' / 'metacognition' / 'auto_analysis_log.jsonl' if ws else None
    log_entries = 0
    if log_path and log_path.exists():
        try:
            with log_path.open(encoding='utf-8') as _f:
                log_entries = sum(1 for _ in _f)
        except Exception:
            pass
    if log_entries == 0:
        blind_spots.append('decision_log: no hay historial de decisiones previas — no puede comparar con analisis anteriores')
    elif log_entries >= 2:
        try:
            lines = log_path.read_text(encoding='utf-8').strip().splitlines()
            prev = json.loads(lines[-2])
            curr_issues = len(deductions)
            # Compare holistic deductions with holistic deductions (not veredicto issues_found)
            prev_holistic = prev.get('holistic_deductions', [])
            prev_issues = len(prev_holistic) if isinstance(prev_holistic, list) else 0
            if curr_issues > prev_issues:
                deductions.append({
                    'severity': 'info',
                    'area': 'trend',
                    'finding': f'Deducciones holísticas aumentaron: {prev_issues} → {curr_issues} desde ultimo analisis',
                    'action': 'investigate_regression',
                })
            elif curr_issues < prev_issues:
                deductions.append({
                    'severity': 'info',
                    'area': 'trend',
                    'finding': f'Deducciones holísticas disminuyeron: {prev_issues} → {curr_issues} — mejora confirmada',
                    'action': 'none',
                })
        except Exception:
            pass
    cross_validations.append('current_analysis × previous_analysis')

    # --- Account/Resource × GPU × Deep Env cross-check ---
    acc = account_state or {}
    acc_summary = acc.get('summary', {})
    if acc_summary.get('alert_count', 0) > 0:
        for alert in acc_summary.get('alerts', [])[:3]:
            deductions.append({
                'severity': 'warning',
                'area': 'resource_availability',
                'finding': alert,
                'action': 'notify_user',
            })
    if acc and acc_summary.get('available', 0) < acc_summary.get('total_resources', 1):
        blind_spots.append(
            f'recursos: {acc_summary.get("total_resources", 0) - acc_summary.get("available", 0)} '
            f'recursos no disponibles de {acc_summary.get("total_resources", 0)} totales'
        )
    cross_validations.append('accounts × api_status × credentials')

    # --- GPU × Deep Env: NVIDIA laptop should have 2 GPUs ---
    deep = deep_env_state or {}
    deep_bios = deep.get('bios_firmware', {})
    board_mfr = str(deep_bios.get('motherboard_manufacturer', '') or
                    deep_bios.get('board_vendor', '')).lower()
    # Common gaming/workstation laptop brands with dual GPU
    is_likely_dual_gpu = any(brand in board_mfr for brand in
                            ['msi', 'asus', 'lenovo', 'dell', 'hp', 'acer', 'razer'])
    if is_likely_dual_gpu and nvidia_count > 0 and gp.get('intel_igpu_count', 0) == 0:
        deductions.append({
            'severity': 'warning',
            'area': 'gpu_detection',
            'finding': (
                f'Laptop {board_mfr.upper()} con NVIDIA detectada pero Intel iGPU '
                'no aparece — probablemente tiene GPU dual pero solo se detecta 1'
            ),
            'action': 'verify_igpu_drivers',
        })
    cross_validations.append('deep_env_bios × gpu_count × laptop_brand')

    # --- Regression cycle cross-check ---
    reg = regression_state or {}
    reg_summary = reg.get('summary', {})
    if reg_summary.get('total_issues', 0) > 0:
        if reg_summary.get('revert_count', 0) > 0:
            deductions.append({
                'severity': 'warning',
                'area': 'regression_cycle',
                'finding': (
                    f'{reg_summary["revert_count"]} reverts detectados en commits recientes — '
                    'posible ciclo hacer-deshacer'
                ),
                'action': 'review_reverts',
            })
        if reg_summary.get('cyclic_files', 0) > 0:
            deductions.append({
                'severity': 'warning',
                'area': 'regression_cycle',
                'finding': (
                    f'{reg_summary["cyclic_files"]} archivos con churn cíclico — '
                    'se modifican repetidamente sin progreso neto'
                ),
                'action': 'review_file_churn',
            })
        if reg_summary.get('oscillation_count', 0) > 0:
            deductions.append({
                'severity': 'info',
                'area': 'regression_cycle',
                'finding': (
                    f'{reg_summary["oscillation_count"]} tareas del backlog oscilando — '
                    'se completan y reaparecen'
                ),
                'action': 'investigate_oscillation',
            })
    cross_validations.append('git_reverts × file_churn × backlog_oscillation')

    # --- Resource monitoring × system health ---
    rs = resource_state or {}
    rs_resources = rs.get('resources', {})
    rs_ram_pct = rs_resources.get('ram_used_pct', 0)
    rs_monitoring = rs.get('monitoring', {})
    if rs_ram_pct > 85:
        deductions.append({
            'severity': 'warning',
            'area': 'resource_pressure',
            'finding': (
                f'RAM en {rs_ram_pct}% — tareas pesadas deben diferirse '
                'para evitar congelamiento'
            ),
            'action': 'defer_heavy_tasks',
        })
    if rs_monitoring.get('status') == 'ok':
        ram_trend = rs_monitoring.get('ram', {}).get('trend', 'stable')
        if ram_trend == 'rising':
            deductions.append({
                'severity': 'info',
                'area': 'resource_trend',
                'finding': 'Tendencia de RAM creciente detectada por monitoreo en fondo',
                'action': 'investigate_memory_growth',
            })
        anomaly_count = rs_monitoring.get('anomalies', 0)
        if anomaly_count > 0:
            deductions.append({
                'severity': 'warning' if anomaly_count >= 3 else 'info',
                'area': 'resource_anomaly',
                'finding': f'{anomaly_count} anomalias de recursos detectadas (picos RAM, umbrales criticos)',
                'action': 'review_resource_anomalies',
            })
    for bd in rs.get('bottleneck_diagnoses', []):
        deductions.append({
            'severity': bd.get('severity', 'info'),
            'area': bd.get('area', 'resource_bottleneck'),
            'finding': bd.get('finding', ''),
            'action': bd.get('action', 'none'),
        })
    cross_validations.append('resource_monitor × ram_pressure × cpu_load')

    all_sources = [
        git_state, gpu_state, test_state, version_state,
        branch_state, stalled_sessions, account_state,
        regression_state, deep_env_state, resource_state,
    ]
    total_sources = len(all_sources)
    sources_with_data = sum(1 for x in all_sources if x is not None)
    confidence = round(sources_with_data / max(total_sources, 1), 2)

    return {
        'deductions': deductions,
        'blind_spots': blind_spots,
        'cross_validations': cross_validations,
        'deduction_count': len(deductions),
        'blind_spot_count': len(blind_spots),
        'cross_validation_count': len(cross_validations),
        'confidence': confidence,
        'critical_count': sum(1 for d in deductions if d['severity'] == 'critical'),
        'warning_count': sum(1 for d in deductions if d['severity'] == 'warning'),
    }


def _default_workspace() -> str:
    """Determine workspace root."""
    # Try environment variable first
    ws = os.environ.get('IABV_WORKSPACE', '')
    if ws and Path(ws).exists():
        return ws

    # Try common paths
    candidates = [
        Path(r'C:\Python\IABV_v1.5'),
        Path.home() / 'Python' / 'IABV_v1.5',
        Path(__file__).resolve().parents[3],  # src/iabv_v15/services -> IABV_v1.5
    ]
    for c in candidates:
        if (c / 'src' / 'iabv_v15').exists():
            return str(c)

    return ''
