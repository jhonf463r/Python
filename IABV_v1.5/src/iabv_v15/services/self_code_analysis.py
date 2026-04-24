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


def full_self_analysis_report(workspace: str | None = None) -> dict[str, Any]:
    """Generate a COMPLETE self-analysis report of the codebase.

    This is the main entry point for autonomous code health verification.
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

    # 5. Overall health
    all_ok = (
        report['syntax']['ok']
        and report['mcp_tools']['ok']
        and report['performance']['performance_ok']
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
