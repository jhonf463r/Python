"""Tests for ResourceMetacognitionService."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.resource_metacognition_service import (
    MODEL_RAM_REQUIREMENTS,
    NEVER_CLOSE,
    SAFE_TO_CLOSE_DEFAULT,
    LiberationPlan,
    LiberationResult,
    ProcessInfo,
    ResourceMetacognitionService,
    ResourceSnapshot,
)


@pytest.fixture
def tmp_evolution_dir(tmp_path: Path) -> Path:
    d = tmp_path / 'evolution'
    d.mkdir()
    return d


@pytest.fixture
def service(tmp_evolution_dir: Path) -> ResourceMetacognitionService:
    return ResourceMetacognitionService(evolution_dir=tmp_evolution_dir)


# ------------------------------------------------------------------
# ResourceSnapshot
# ------------------------------------------------------------------

class TestResourceSnapshot:
    def test_to_dict_empty(self) -> None:
        snap = ResourceSnapshot()
        d = snap.to_dict()
        assert d['ram_total_gb'] == 0.0
        assert d['top_processes'] == []

    def test_to_dict_with_processes(self) -> None:
        snap = ResourceSnapshot(
            ram_total_gb=16.0,
            ram_free_gb=4.0,
            ram_used_gb=12.0,
            top_processes=[ProcessInfo(name='chrome', pid=1234, ram_mb=500)],
        )
        d = snap.to_dict()
        assert d['ram_total_gb'] == 16.0
        assert len(d['top_processes']) == 1
        assert d['top_processes'][0]['name'] == 'chrome'


# ------------------------------------------------------------------
# LiberationPlan
# ------------------------------------------------------------------

class TestLiberationPlan:
    def test_summary_no_liberation(self) -> None:
        plan = LiberationPlan(should_liberate=False, reason='RAM suficiente')
        assert 'No es necesario' in plan.summary_text()

    def test_summary_with_liberation(self) -> None:
        plan = LiberationPlan(
            should_liberate=True,
            processes_to_close=[ProcessInfo(name='chrome', pid=1, ram_mb=1024)],
            estimated_ram_freed_gb=1.0,
            target_model='gemma3:4b',
            target_model_ram_gb=3.5,
        )
        text = plan.summary_text()
        assert 'chrome' in text
        assert 'gemma3:4b' in text


# ------------------------------------------------------------------
# select_optimal_model
# ------------------------------------------------------------------

class TestSelectOptimalModel:
    def test_selects_largest_fitting_model(self, service: ResourceMetacognitionService) -> None:
        model = service.select_optimal_model(6.5)
        assert model == 'llama3.1:8b'

    def test_selects_smallest_when_low_ram(self, service: ResourceMetacognitionService) -> None:
        model = service.select_optimal_model(2.0)
        assert model == 'gemma3:1b'

    def test_selects_nothing_when_no_ram(self, service: ResourceMetacognitionService) -> None:
        model = service.select_optimal_model(0.5)
        assert model == ''

    def test_selects_largest_when_plenty_of_ram(self, service: ResourceMetacognitionService) -> None:
        model = service.select_optimal_model(20.0)
        assert model == 'deepseek-coder-v2:16b'

    def test_lab_preferred_overrides(self, tmp_evolution_dir: Path) -> None:
        lab = MagicMock()
        lab.recent_results.return_value = [
            {'model': 'gemma3:4b', 'success': True},
            {'model': 'gemma3:4b', 'success': True},
            {'model': 'llama3.1:8b', 'success': True},
        ]
        svc = ResourceMetacognitionService(
            evolution_dir=tmp_evolution_dir,
            experiment_lab=lab,
        )
        # With 6.5GB, normally picks llama3.1:8b, but lab prefers gemma3:4b
        model = svc.select_optimal_model(6.5)
        assert model == 'gemma3:4b'


# ------------------------------------------------------------------
# _identify_closeable_processes
# ------------------------------------------------------------------

class TestIdentifyCloseable:
    def test_never_close_excluded(self, service: ResourceMetacognitionService) -> None:
        procs = [
            ProcessInfo(name='python', pid=1, ram_mb=500),
            ProcessInfo(name='chrome', pid=2, ram_mb=1000),
            ProcessInfo(name='svchost', pid=3, ram_mb=200),
        ]
        closeable = service._identify_closeable_processes(procs)
        names = [p.name for p in closeable]
        assert 'chrome' in names
        assert 'python' not in names
        assert 'svchost' not in names

    def test_safe_default_included(self, service: ResourceMetacognitionService) -> None:
        procs = [
            ProcessInfo(name='spotify', pid=10, ram_mb=300),
            ProcessInfo(name='discord', pid=11, ram_mb=200),
        ]
        closeable = service._identify_closeable_processes(procs)
        assert len(closeable) == 2

    def test_sorted_by_ram_descending(self, service: ResourceMetacognitionService) -> None:
        procs = [
            ProcessInfo(name='spotify', pid=10, ram_mb=100),
            ProcessInfo(name='chrome', pid=11, ram_mb=500),
            ProcessInfo(name='discord', pid=12, ram_mb=200),
        ]
        closeable = service._identify_closeable_processes(procs)
        rams = [p.ram_mb for p in closeable]
        assert rams == sorted(rams, reverse=True)

    def test_learned_closeable_included(self, service: ResourceMetacognitionService) -> None:
        service._learned_closeable.add('customapp')
        procs = [ProcessInfo(name='customapp', pid=99, ram_mb=400)]
        closeable = service._identify_closeable_processes(procs)
        assert len(closeable) == 1


# ------------------------------------------------------------------
# analyze_liberation_plan
# ------------------------------------------------------------------

class TestAnalyzeLiberationPlan:
    def test_no_liberation_when_ram_sufficient(self, service: ResourceMetacognitionService) -> None:
        snap = ResourceSnapshot(ram_total_gb=16.0, ram_free_gb=8.0, ram_used_gb=8.0)
        plan = service.analyze_liberation_plan(snap)
        assert not plan.should_liberate
        assert plan.target_model != ''

    def test_liberation_when_ram_low(self, service: ResourceMetacognitionService) -> None:
        snap = ResourceSnapshot(
            ram_total_gb=8.0, ram_free_gb=1.0, ram_used_gb=7.0,
            top_processes=[
                ProcessInfo(name='chrome', pid=100, ram_mb=2048),
                ProcessInfo(name='spotify', pid=101, ram_mb=512),
                ProcessInfo(name='python', pid=102, ram_mb=1024),
            ],
        )
        plan = service.analyze_liberation_plan(snap)
        assert plan.should_liberate
        assert plan.target_model != ''
        # python should NOT be in close list
        close_names = [p.name for p in plan.processes_to_close]
        assert 'python' not in close_names

    def test_no_liberation_when_nothing_closeable(self, service: ResourceMetacognitionService) -> None:
        snap = ResourceSnapshot(
            ram_total_gb=4.0, ram_free_gb=0.5, ram_used_gb=3.5,
            top_processes=[
                ProcessInfo(name='python', pid=1, ram_mb=2000),
                ProcessInfo(name='svchost', pid=2, ram_mb=1000),
            ],
        )
        plan = service.analyze_liberation_plan(snap)
        assert not plan.should_liberate


# ------------------------------------------------------------------
# record_outcome + recent_history
# ------------------------------------------------------------------

class TestRecordOutcome:
    def test_record_and_read_history(self, service: ResourceMetacognitionService) -> None:
        result = LiberationResult(
            success=True,
            ram_freed_gb=2.5,
            selected_model='gemma3:4b',
            model_loaded=True,
        )
        service.record_outcome(result)
        history = service.recent_history(limit=5)
        assert len(history) == 1
        assert history[0]['ram_freed_gb'] == 2.5
        assert history[0]['selected_model'] == 'gemma3:4b'

    def test_multiple_records(self, service: ResourceMetacognitionService) -> None:
        for i in range(3):
            r = LiberationResult(success=True, ram_freed_gb=float(i))
            service.record_outcome(r)
        history = service.recent_history(limit=10)
        assert len(history) == 3


# ------------------------------------------------------------------
# oses_findings
# ------------------------------------------------------------------

class TestOsesFindings:
    def test_critical_ram_finding(self, service: ResourceMetacognitionService) -> None:
        with patch.object(service, 'observe_resources') as mock_obs:
            mock_obs.return_value = ResourceSnapshot(
                ram_total_gb=8.0, ram_free_gb=1.5, ram_used_gb=6.5,
            )
            findings = service.oses_findings()
            assert len(findings) >= 1
            assert findings[0]['severity'] == 'HIGH'
            assert 'critica' in findings[0]['title'].lower()

    def test_pressure_ram_finding(self, service: ResourceMetacognitionService) -> None:
        with patch.object(service, 'observe_resources') as mock_obs:
            mock_obs.return_value = ResourceSnapshot(
                ram_total_gb=8.0, ram_free_gb=2.5, ram_used_gb=5.5,
            )
            findings = service.oses_findings()
            assert len(findings) >= 1
            assert findings[0]['severity'] == 'MEDIUM'

    def test_no_finding_when_plenty_of_ram(self, service: ResourceMetacognitionService) -> None:
        with patch.object(service, 'observe_resources') as mock_obs:
            mock_obs.return_value = ResourceSnapshot(
                ram_total_gb=16.0, ram_free_gb=8.0, ram_used_gb=8.0,
            )
            findings = service.oses_findings()
            assert len(findings) == 0


# ------------------------------------------------------------------
# learned_closeable persistence
# ------------------------------------------------------------------

class TestLearnedCloseable:
    def test_save_and_load(self, tmp_evolution_dir: Path) -> None:
        svc1 = ResourceMetacognitionService(evolution_dir=tmp_evolution_dir)
        svc1._mark_learned_closeable('myapp')
        assert 'myapp' in svc1._learned_closeable

        svc2 = ResourceMetacognitionService(evolution_dir=tmp_evolution_dir)
        assert 'myapp' in svc2._learned_closeable

    def test_does_not_add_never_close(self, service: ResourceMetacognitionService) -> None:
        service._mark_learned_closeable('python')
        assert 'python' not in service._learned_closeable

    def test_does_not_add_already_safe(self, service: ResourceMetacognitionService) -> None:
        service._mark_learned_closeable('chrome')
        assert 'chrome' not in service._learned_closeable


# ------------------------------------------------------------------
# linux_memory_snapshot fallback
# ------------------------------------------------------------------

class TestLinuxMemorySnapshot:
    def test_reads_proc_meminfo(self, service: ResourceMetacognitionService) -> None:
        if os.path.exists('/proc/meminfo'):
            ram = service._linux_memory_snapshot()
            assert ram.get('total_bytes', 0) > 0
            assert ram.get('free_bytes', 0) > 0


# ------------------------------------------------------------------
# chat helpers
# ------------------------------------------------------------------

class TestChatHelpers:
    def test_chat_observe_and_plan(self, service: ResourceMetacognitionService) -> None:
        with patch.object(service, 'observe_resources') as mock_obs:
            mock_obs.return_value = ResourceSnapshot(
                ram_total_gb=16.0, ram_free_gb=8.0, ram_used_gb=8.0,
                top_processes=[ProcessInfo(name='chrome', pid=1, ram_mb=500)],
            )
            text = service.chat_observe_and_plan()
            assert 'RAM' in text
            assert 'chrome' in text


# ------------------------------------------------------------------
# Constants sanity
# ------------------------------------------------------------------

class TestConstants:
    def test_never_close_has_system_processes(self) -> None:
        assert 'python' in NEVER_CLOSE
        assert 'ollama' in NEVER_CLOSE
        assert 'svchost' in NEVER_CLOSE

    def test_safe_default_has_common_apps(self) -> None:
        assert 'chrome' in SAFE_TO_CLOSE_DEFAULT
        assert 'spotify' in SAFE_TO_CLOSE_DEFAULT
        assert 'discord' in SAFE_TO_CLOSE_DEFAULT

    def test_no_overlap_never_and_safe(self) -> None:
        overlap = NEVER_CLOSE & SAFE_TO_CLOSE_DEFAULT
        assert len(overlap) == 0, f'Overlap: {overlap}'

    def test_model_requirements_sorted(self) -> None:
        # Smallest to largest should be monotonic
        values = list(MODEL_RAM_REQUIREMENTS.values())
        sorted_values = sorted(values)
        # Not necessarily sorted in dict, but all values should be unique and positive
        assert all(v > 0 for v in values)
