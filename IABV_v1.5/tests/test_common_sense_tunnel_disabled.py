from __future__ import annotations

from unittest.mock import patch

from iabv_v15.services import common_sense_engine


def test_common_sense_reasoning_never_launches_tunnel_even_when_execute_true(monkeypatch) -> None:
    monkeypatch.setattr(
        common_sense_engine,
        'extract_facts',
        lambda **_kwargs: {'cloudflared_installed', 'tunnel_not_running', 'tunnel_expected'},
    )
    monkeypatch.setattr(common_sense_engine, 'consult_history', lambda items: items)
    monkeypatch.setattr(common_sense_engine, '_register_with_experiment_lab', lambda _result: {})

    with patch.object(common_sense_engine.subprocess, 'Popen') as popen:
        result = common_sense_engine.run_common_sense_reasoning(execute=True)

    popen.assert_not_called()
    assert 'start_tunnel' not in common_sense_engine._ACTION_EXECUTORS
    assert any(
        item.get('action') == 'tunnel_start_prohibited'
        and item.get('reason') == 'no executor registered'
        for item in result['actions_skipped']
    )
