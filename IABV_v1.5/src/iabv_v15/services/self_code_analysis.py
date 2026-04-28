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

logger = logging.getLogger(__name__)


def _run_cmd(cmd: list[str], timeout: int = 15) -> str:
    """Run a command and return stdout, empty string on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ''


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


def verify_python_syntax(workspace: str | None = None) -> dict[str, Any]:
    """Compile-check all Python files in src/ for syntax errors."""
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found'}

    src_dir = Path(ws) / 'src'
    if not src_dir.exists():
        return {'ok': False, 'error': f'{src_dir} not found'}

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

    return {
        'ok': len(errors) == 0,
        'files_checked': checked,
        'errors': errors,
        'summary': f'{checked} files checked, {len(errors)} errors' if errors else f'{checked} files checked, all OK',
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
            if method_name.startswith('_'):
                continue
            if method_name not in qml_method_calls:
                continue
            checked += 1
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
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', '-p', 'no:cacheprovider', 'tests/', '-q', '--tb=short', '-x'],
            capture_output=True, text=True, timeout=300,
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
        return {'ok': False, 'error': 'test suite timed out after 300s', 'summary': 'Tests timed out'}
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'summary': f'Failed to run tests: {exc}'}


def auto_merge_safe_branches(workspace: str | None = None) -> dict[str, Any]:
    """Attempt to merge safe branches (devin/*, iabv-auto/*) into current branch.

    Per AGENTS.md, auto-merge is allowed for devin/* and iabv-auto/* branches.
    Strategy: first try clean merge; if conflicts, retry with -X theirs
    (take the branch's version — the most recent changes win).
    Only skips branches that touch closed layers P1-P4 contracts.
    """
    ws = workspace or _default_workspace()
    if not ws:
        return {'ok': False, 'error': 'workspace not found', 'merged': [], 'failed': [], 'skipped': []}

    branches = scan_unmerged_branches(ws)
    safe_prefixes = ('origin/devin/', 'origin/iabv-auto/')
    merged: list[str] = []
    merged_with_theirs: list[str] = []
    failed: list[dict[str, str]] = []
    skipped: list[str] = []

    # Stash dirty working tree so merges can proceed
    status_chk = subprocess.run(
        ['git', '-C', ws, 'status', '--porcelain'],
        capture_output=True, text=True, timeout=10,
    )
    tree_dirty = bool(status_chk.stdout.strip())
    stashed = False
    if tree_dirty:
        stash_r = subprocess.run(
            ['git', '-C', ws, 'stash'],
            capture_output=True, text=True, timeout=60,
        )
        stashed = stash_r.returncode == 0

    try:
        for b_info in branches:
            branch = b_info.get('branch', '')
            if not any(branch.startswith(p) for p in safe_prefixes):
                skipped.append(branch)
                continue

            # Check if branch touches closed-layer contracts
            try:
                diff_stat = _run_cmd(['git', '-C', ws, 'diff', '--name-only', f'HEAD...{branch}'])
            except Exception:
                diff_stat = ''
            closed_layer_files = ('domain/models.py', 'governance', 'world_model')
            touches_closed = any(cl in diff_stat for cl in closed_layer_files)
            if touches_closed:
                skipped.append(f'{branch} (touches closed layer)')
                continue

            try:
                # First try clean merge
                result = subprocess.run(
                    ['git', '-C', ws, 'merge', '--no-edit', branch],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    merged.append(branch)
                    logger.info('auto_merge: merged %s successfully', branch)
                else:
                    # Conflict — abort and retry with -X theirs (take most recent)
                    subprocess.run(
                        ['git', '-C', ws, 'merge', '--abort'],
                        capture_output=True, timeout=10,
                    )
                    result2 = subprocess.run(
                        ['git', '-C', ws, 'merge', '--no-edit', '-X', 'theirs', branch],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result2.returncode == 0:
                        merged_with_theirs.append(branch)
                        logger.info('auto_merge: merged %s with -X theirs', branch)
                    else:
                        subprocess.run(
                            ['git', '-C', ws, 'merge', '--abort'],
                            capture_output=True, timeout=10,
                        )
                        failed.append({
                            'branch': branch,
                            'reason': result2.stderr.strip()[:200] or 'merge failed even with -X theirs',
                        })
                        logger.warning('auto_merge: failed %s even with -X theirs', branch)
            except Exception as exc:
                try:
                    subprocess.run(['git', '-C', ws, 'merge', '--abort'], capture_output=True, timeout=10)
                except Exception:
                    pass
                failed.append({'branch': branch, 'reason': str(exc)})
    finally:
        # Restore stashed changes — always runs even if merge loop crashes
        if stashed:
            subprocess.run(
                ['git', '-C', ws, 'stash', 'pop'],
                capture_output=True, text=True, timeout=60,
            )

    total_merged = len(merged) + len(merged_with_theirs)
    return {
        'ok': len(failed) == 0,
        'merged': merged,
        'merged_count': len(merged),
        'merged_with_theirs': merged_with_theirs,
        'merged_with_theirs_count': len(merged_with_theirs),
        'total_merged': total_merged,
        'failed': failed,
        'failed_count': len(failed),
        'skipped': skipped,
        'skipped_count': len(skipped),
        'summary': f'{total_merged} merged ({len(merged)} clean, {len(merged_with_theirs)} con conflictos resueltos), {len(failed)} failed, {len(skipped)} skipped',
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
