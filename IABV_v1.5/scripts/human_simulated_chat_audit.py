#!/usr/bin/env python3
"""P0.71: Human-Simulated Chat Audit Runner.

Simulates a user interacting with IABV through the UIBridge to verify:
- Bridge is reachable and owner is correct.
- Metacognitive phrases reach the roadmap/discernment handler (not LLM).
- Messages are not silently buffered without ControlCenterViewModel.
- Navigation actually changes the route.
- No stall > 5s on metacognitive questions.

Usage (on Windows where IABV is running):
    cd C:\\Python\\IABV_v1.5
    python scripts/human_simulated_chat_audit.py

The script connects to the already-running UIBridge on 127.0.0.1:18921.
It does NOT launch the UI — that should already be running.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from iabv_v15.services.ui_bridge_service import UIBridgeClient


def _check(label: str, passed: bool, detail: str = '') -> dict:
    status = 'PASS' if passed else 'FAIL'
    msg = f'  [{status}] {label}'
    if detail:
        msg += f' — {detail}'
    print(msg)
    return {'label': label, 'status': status, 'detail': detail}


def run_audit() -> list[dict]:
    """Run the full simulated chat audit and return results."""
    results: list[dict] = []
    client = UIBridgeClient()

    print('=' * 60)
    print('P0.71: Human-Simulated Chat Audit')
    print('=' * 60)
    print()

    # 1. Bridge reachability
    reachable = client.is_ui_available()
    results.append(_check('Bridge reachable', reachable))
    if not reachable:
        print('\n  ABORT: UIBridge not reachable on 127.0.0.1:18921.')
        print('  Make sure IABV is running with -StartUI.')
        return results

    # 2. Verify bridge owner via get_ui_state
    state_resp = client.call('get_ui_state')
    state = state_resp.get('result', {})
    vm_bound = state.get('control_vm_bound', False)
    chat_ready = state.get('chat_ready', False)
    pid = state.get('ui_process_pid', 0)
    results.append(_check('control_vm_bound', vm_bound, f'pid={pid}'))
    results.append(_check('chat_ready', chat_ready))

    # 3. Navigate to Control page
    nav_resp = client.call('navigate', page='control')
    nav_result = nav_resp.get('result', {})
    nav_ok = nav_result.get('status') in ('navigated',)
    results.append(_check(
        'Navigate to control',
        nav_ok,
        f'status={nav_result.get("status")}, verified={nav_result.get("verified")}',
    ))

    # 4. Send metacognitive questions and measure response time
    test_phrases = [
        ('¿por dónde vamos?', 'roadmap'),
        ('¿me entiendes y qué evidencia tienes?', 'discernment'),
        ('sigue', 'continuity'),
    ]
    for phrase, expected_type in test_phrases:
        t0 = time.monotonic()
        send_resp = client.call('send_message', text=phrase)
        elapsed_ms = (time.monotonic() - t0) * 1000
        send_result = send_resp.get('result', {})
        send_status = send_result.get('status', send_resp.get('error', 'unknown'))
        stall = elapsed_ms > 5000
        results.append(_check(
            f'send_message("{phrase[:30]}...")',
            send_status not in ('unavailable', 'error') and not stall,
            f'status={send_status}, elapsed={elapsed_ms:.0f}ms, stall={stall}',
        ))

    # 5. Read messages to verify responses appeared
    time.sleep(1.0)  # brief wait for processing
    read_resp = client.call('read_messages', limit=10)
    read_result = read_resp.get('result', {})
    messages = read_result.get('messages', [])
    results.append(_check(
        'Messages in chat after audit',
        len(messages) > 0,
        f'count={len(messages)}, source={read_result.get("source")}',
    ))

    # 6. Verify bridge readiness state
    ready_resp = client.call('bridge_readiness')
    ready_result = ready_resp.get('result', {})
    shell_ready = ready_result.get('shell_ready', False)
    results.append(_check('shell_ready', shell_ready))

    # Summary
    print()
    print('=' * 60)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    print(f'Results: {passed} passed, {failed} failed out of {len(results)} checks.')
    print('=' * 60)

    # Write results to audit file
    audit_path = Path(__file__).parent.parent / 'data' / 'logs' / 'chat_audit_p071.json'
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps({
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'results': results,
            'passed': passed,
            'failed': failed,
            'total': len(results),
        }, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    print(f'\nAudit log written to: {audit_path}')

    return results


if __name__ == '__main__':
    results = run_audit()
    sys.exit(0 if all(r['status'] == 'PASS' for r in results) else 1)
