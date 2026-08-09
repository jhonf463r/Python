from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import IssueSeverity, ProviderHealth, ProviderStatus
from iabv_v15.services.evolution.environment_self_awareness_service import EnvironmentSelfAwarenessService


REPO_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_environment_self_awareness_service_persists_known_environment() -> None:
    workspace = _workspace('environment_self_model')
    try:
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._scan_hardware = lambda *, full: ({  # type: ignore[method-assign]
            'hostname': 'cyborg15',
            'machine': 'AMD64',
            'processor_name': 'Intel i7',
            'memory_total_bytes': 16 * 1024**3,
            'memory_free_bytes': 6 * 1024**3,
            'disk_free_bytes': 80 * 1024**3,
            'disk_total_bytes': 512 * 1024**3,
            'gpu_name': 'RTX 4050',
            'gpu_memory_total_mb': 6144,
        }, [])
        service._scan_runtime = lambda *, full: ({  # type: ignore[method-assign]
            'python_executable': 'C:/Users/faber/miniconda3/python.exe',
            'python_version': '3.13.2',
            'workspace_writeable': True,
            'missing_project_dependencies': [],
        }, [])
        service._provider_health = lambda: [  # type: ignore[method-assign]
            ProviderHealth(provider_name='Ollama', status=ProviderStatus.READY, available=True, detail='ok')
        ]
        service._tool_cards = lambda: ([  # type: ignore[method-assign]
            {'tool_id': 'ollama_llm', 'title': 'Ollama local', 'tool_type': 'llm_local', 'available': True, 'assistant_kind': 'ollama', 'launch_mode': 'local_provider', 'supports_write': False, 'supports_sandbox': True}
        ], [])
        service._scan_ai_capacity = lambda **_: ({  # type: ignore[method-assign]
            'preferred_local_assistant_kind': 'ollama',
            'safe_models': ['4B safe', '8B with caution'],
            'max_recommended_model': '8B q4/q5',
            'local_runtime': {'available': True, 'models': [{'name': 'qwen3:8b', 'size': '5.2 GB'}]},
            'avoid_heavy_models': False,
        }, [])

        first = service.scan_now(reason='manual', full=True)

        assert first.environment_id
        assert first.known_environment is False
        assert first.available_tools[0]['tool_id'] == 'ollama_llm'
        assert first.ai_capacity['max_recommended_model'] == '8B q4/q5'

        second = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        second._scan_hardware = service._scan_hardware  # type: ignore[method-assign]
        second._scan_runtime = service._scan_runtime  # type: ignore[method-assign]
        second._provider_health = service._provider_health  # type: ignore[method-assign]
        second._tool_cards = service._tool_cards  # type: ignore[method-assign]
        second._scan_ai_capacity = service._scan_ai_capacity  # type: ignore[method-assign]

        repeated = second.scan_now(reason='manual', full=True)

        assert repeated.environment_id == first.environment_id
        assert repeated.known_environment is True
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_environment_self_awareness_service_surfaces_memory_pressure() -> None:
    workspace = _workspace('environment_risk')
    try:
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._scan_hardware = lambda *, full: ({  # type: ignore[method-assign]
            'hostname': 'cyborg15',
            'machine': 'AMD64',
            'processor_name': 'Intel i7',
            'memory_total_bytes': 16 * 1024**3,
            'memory_free_bytes': 1 * 1024**3,
            'disk_free_bytes': 80 * 1024**3,
            'disk_total_bytes': 512 * 1024**3,
            'gpu_name': 'RTX 4050',
            'gpu_memory_total_mb': 6144,
            'cpu_usage_percent': 22.0,
            'throttling_detected': False,
        }, [])
        service._scan_runtime = lambda *, full: ({  # type: ignore[method-assign]
            'python_executable': 'python',
            'python_version': '3.13.2',
            'workspace_writeable': True,
            'missing_project_dependencies': [],
        }, [])
        service._provider_health = lambda: []  # type: ignore[method-assign]
        service._tool_cards = lambda: ([], [])  # type: ignore[method-assign]
        service._scan_ai_capacity = lambda **_: ({  # type: ignore[method-assign]
            'preferred_local_assistant_kind': 'ollama',
            'safe_models': ['4B safe'],
            'max_recommended_model': '4B q4/q5',
            'local_runtime': {'available': False, 'models': []},
            'avoid_heavy_models': True,
        }, [])

        model = service.scan_now(reason='manual', full=True)

        assert any(signal.kind == 'ram_critical' for signal in model.risk_signals)
        assert any(signal.severity == IssueSeverity.CRITICAL for signal in model.risk_signals)
        assert model.notifications
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_environment_self_awareness_light_scan_reuses_cached_provider_health() -> None:
    workspace = _workspace('environment_provider_cache')
    try:
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._scan_hardware = lambda *, full: ({  # type: ignore[method-assign]
            'hostname': 'cyborg15',
            'machine': 'AMD64',
            'processor_name': 'Intel i7',
            'memory_total_bytes': 16 * 1024**3,
            'memory_free_bytes': 6 * 1024**3,
            'disk_free_bytes': 80 * 1024**3,
            'disk_total_bytes': 512 * 1024**3,
            'gpu_name': 'RTX 4050',
            'gpu_memory_total_mb': 6144,
        }, [])
        service._scan_runtime = lambda *, full: ({  # type: ignore[method-assign]
            'python_executable': 'python',
            'python_version': '3.13.2',
            'workspace_writeable': True,
            'missing_project_dependencies': [],
        }, [])
        service._tool_cards = lambda: ([], [])  # type: ignore[method-assign]
        service._scan_ai_capacity = lambda **_: ({  # type: ignore[method-assign]
            'preferred_local_assistant_kind': 'ollama',
            'safe_models': ['4B safe'],
            'max_recommended_model': '4B q4/q5',
            'local_runtime': {'available': True, 'models': [{'name': 'qwen3:8b'}]},
            'avoid_heavy_models': False,
        }, [])

        calls = {'count': 0}

        def provider_health() -> list[ProviderHealth]:
            calls['count'] += 1
            return [ProviderHealth(provider_name='Ollama', status=ProviderStatus.READY, available=True, detail='ok')]

        service._provider_health = provider_health  # type: ignore[method-assign]

        full_model = service.scan_now(reason='manual', full=True)
        light_model = service.scan_now(reason='scheduled_light', full=False)

        assert calls['count'] == 1
        assert full_model.metadata.get('provider_health')
        assert light_model.metadata.get('provider_health')
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_gpu_degradation_when_nvidia_smi_fails_but_windows_detects_gpu() -> None:
    """Test that GPU degradation is detected when nvidia-smi fails but Windows sees GPU."""
    workspace = _workspace('gpu_degradation')
    try:
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )

        # Mock nvidia-smi failure (presence of nvidia-smi.exe indicates NVIDIA hardware)
        service._run_command = lambda cmd, **_: {  # type: ignore[method-assign]
            'returncode': 1,
            'stdout': '',
            'stderr': 'NVIDIA-SMI has failed because it couldn\'t communicate with the NVIDIA driver',
        }

        service._scan_runtime = lambda *, full: ({  # type: ignore[method-assign]
            'python_executable': 'python',
            'python_version': '3.13.2',
            'workspace_writeable': True,
            'missing_project_dependencies': [],
        }, [])

        hardware, unresolved = service._scan_hardware(full=True)

        # Verify GPU is marked as degraded
        assert hardware.get('gpu_status') == 'degraded'
        assert hardware.get('gpu_name') == 'NVIDIA GPU'
        assert hardware.get('gpu_degradation_reason') == 'nvidia_smi_failed'
        assert 'nvidia-smi falló' in hardware.get('gpu_degradation_detail', '')
        assert 'DEGRADED:gpu_nvidia_smi_failed' in unresolved
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_gpu_healthy_when_nvidia_smi_succeeds() -> None:
    """Test that GPU is marked as healthy when nvidia-smi succeeds."""
    workspace = _workspace('gpu_healthy')
    try:
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )

        # Mock Windows detecting NVIDIA GPU
        service._windows_detect_nvidia_gpu = lambda: {  # type: ignore[method-assign]
            'name': 'NVIDIA GeForce RTX 4050',
            'driver_version': '31.0.15.3229',
            'driver_date': '20240101',
        }

        # Mock nvidia-smi success
        service._run_command = lambda cmd, **_: {  # type: ignore[method-assign]
            'returncode': 0,
            'stdout': 'RTX 4050,31.0.15.3229,45,6144,2048,12',
            'stderr': '',
        }

        service._scan_runtime = lambda *, full: ({  # type: ignore[method-assign]
            'python_executable': 'python',
            'python_version': '3.13.2',
            'workspace_writeable': True,
            'missing_project_dependencies': [],
        }, [])

        hardware, unresolved = service._scan_hardware(full=True)

        # Verify GPU is marked as healthy
        assert hardware.get('gpu_status') == 'healthy'
        assert hardware.get('gpu_name') == 'RTX 4050'
        assert hardware.get('gpu_driver') == '31.0.15.3229'
        assert hardware.get('gpu_memory_total_mb') == 6144
        assert hardware.get('gpu_memory_free_mb') == 4096
        assert hardware.get('gpu_temperature_c') == 45
        assert hardware.get('gpu_utilization_pct') == 12
        assert 'DEGRADED:gpu_nvidia_smi_failed' not in unresolved
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_gpu_degradation_preserves_real_stderr() -> None:
    """Test that real nvidia-smi stderr is preserved in gpu_degradation_detail."""
    workspace = _workspace('gpu_stderr_preservation')
    try:
        service = EnvironmentSelfAwarenessService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )

        # Mock nvidia-smi failure with real stderr
        real_stderr = 'Unable to determine the device handle for GPU0: 0000:01:00.0: GPU is lost.  Reboot the system to recover this GPU'
        service._run_command = lambda cmd, **_: {  # type: ignore[method-assign]
            'returncode': 6,
            'stdout': '',
            'stderr': real_stderr,
        }

        service._scan_runtime = lambda *, full: ({  # type: ignore[method-assign]
            'python_executable': 'python',
            'python_version': '3.13.2',
            'workspace_writeable': True,
            'missing_project_dependencies': [],
        }, [])

        hardware, unresolved = service._scan_hardware(full=True)

        # Verify GPU is marked as degraded
        assert hardware.get('gpu_status') == 'degraded'
        assert hardware.get('gpu_degradation_reason') == 'nvidia_smi_failed'

        # Verify real stderr is preserved in detail
        detail = hardware.get('gpu_degradation_detail', '')
        assert 'GPU is lost' in detail
        assert 'Unable to determine the device handle' in detail
        assert real_stderr in detail

        # Verify unresolved fields includes degradation signal
        assert 'DEGRADED:gpu_nvidia_smi_failed' in unresolved
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
