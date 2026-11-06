from __future__ import annotations

from pathlib import Path

from iabv_v15.services.training.pbt_control_service import PBTControlService


def test_pbt_control_service_creates_checkpoint(tmp_path: Path) -> None:
    root = tmp_path

    service = PBTControlService(str(root))
    result = service.run_cycle({'episodes': 4, 'knowledge': 3, 'artifacts': 12, 'runs': 5})

    assert result['generation'] == 1
    assert len(result['candidates']) == 4
    assert Path(result['checkpoint_path']).exists()
    assert service.load_state()['generation'] == 1
