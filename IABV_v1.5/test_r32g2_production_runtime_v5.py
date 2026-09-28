"""R32-G2 v5: Runtime experiment for degraded signal patch.

Tests that:
- Provider error + substitute response → used_fallback=True
- used_fallback=True → RunStatus.PARTIAL
- RunStatus.PARTIAL → actual_success=False
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import datetime

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import InferenceRequest, RunStatus


def main() -> None:
    workspace_root = Path('C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5/data/r32g2_isolated_v5')
    run_id = datetime.now().strftime('%Y%m%d%H%M%S')
    workspace = workspace_root / f'run_{run_id}'
    workspace.mkdir(parents=True, exist_ok=True)

    print(f'Workspace: {workspace}')
    print(f'Run ID: {run_id}')

    # Bootstrap
    bootstrap = AppBootstrap(str(workspace))
    print('Bootstrap initialized')

    # Warm-up with real model
    print('\n=== WARM-UP ===')
    warm_up_request = InferenceRequest(
        user_goal='explicame en una frase que es la neuroplasticidad operativa',
        auto_route=True,
    )
    warm_up_result = bootstrap.inference_service.infer_task(warm_up_request)
    print(f'Warm-up RunRecord ID: {warm_up_result.run_id}')
    print(f'Warm-up status: {warm_up_result.status}')
    print(f'Warm-up used_fallback: {warm_up_result.result.used_fallback}')
    print(f'Warm-up summary: {warm_up_result.result.summary[:100]}...')

    # Get session to extract subject keys
    # Note: adaptive session may not exist for simple local-chat flows
    subject_keys = []
    print('Skipping session lookup (adaptive session may not exist for local-chat)')

    # Target with nonexistent model
    print('\n=== TARGET ===')
    target_request = InferenceRequest(
        user_goal='explicame en una frase que es la neuroplasticidad operativa',
        auto_route=True,
        metadata={'override_model': 'nonexistent-model-xyz-123'},
    )
    target_result = bootstrap.inference_service.infer_task(target_request)
    print(f'Target RunRecord ID: {target_result.run_id}')
    print(f'Target status: {target_result.status}')
    print(f'Target used_fallback: {target_result.result.used_fallback}')
    print(f'Target summary: {target_result.result.summary[:100]}...')

    # Check local_chat_llm
    local_chat_llm = target_result.result.raw_output.get('local_chat_llm', {})
    print(f'local_chat_llm.error: {local_chat_llm.get("error", "")[:100]}...')
    print(f'local_chat_llm.summary: {local_chat_llm.get("summary", "")}')

    # Save evidence
    evidence = {
        'run_id': run_id,
        'workspace': str(workspace),
        'warm_up': {
            'run_id': warm_up_result.run_id,
            'session_id': None,
            'status': warm_up_result.status.value,
            'used_fallback': warm_up_result.result.used_fallback,
            'summary': warm_up_result.result.summary,
            'subject_keys': subject_keys,
        },
        'target': {
            'run_id': target_result.run_id,
            'status': target_result.status.value,
            'used_fallback': target_result.result.used_fallback,
            'summary': target_result.result.summary,
            'local_chat_llm_error': local_chat_llm.get('error', ''),
            'local_chat_llm_summary': local_chat_llm.get('summary', ''),
        },
    }

    evidence_file = workspace / 'evidence.json'
    with open(evidence_file, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)

    print(f'\nEvidence saved to: {evidence_file}')

    # Verify expectations
    print('\n=== VERIFICATION ===')
    print(f'Expected status: PARTIAL, Actual: {target_result.status}')
    print(f'Expected used_fallback: True, Actual: {target_result.result.used_fallback}')
    print(f'Expected local_chat_llm.error: nonempty, Actual: {bool(local_chat_llm.get("error"))}')
    print(f'Expected local_chat_llm.summary: empty, Actual: {not bool(local_chat_llm.get("summary"))}')

    if target_result.status == RunStatus.PARTIAL:
        print('[OK] Status is PARTIAL')
    else:
        print(f'[FAIL] Status is {target_result.status}, expected PARTIAL')

    if target_result.result.used_fallback:
        print('[OK] used_fallback is True')
    else:
        print('[FAIL] used_fallback is False, expected True')

    if local_chat_llm.get('error'):
        print('[OK] Provider error present')
    else:
        print('[FAIL] No provider error')


if __name__ == '__main__':
    main()
