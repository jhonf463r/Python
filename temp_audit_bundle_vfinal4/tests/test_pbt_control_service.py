from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.services.training.pbt_control_service import PBTControlService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_pbt_control_service_creates_checkpoint() -> None:
    root = _workspace('pbt')

    service = PBTControlService(str(root))
    result = service.run_cycle({'episodes': 4, 'knowledge': 3, 'artifacts': 12, 'runs': 5})

    assert result['generation'] == 1
    assert len(result['candidates']) == 4
    assert Path(result['checkpoint_path']).exists()
    assert service.load_state()['generation'] == 1
