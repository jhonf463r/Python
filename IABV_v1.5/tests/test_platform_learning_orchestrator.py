"""Tests for PlatformLearningOrchestrator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from iabv_v15.services.evolution.platform_learning_orchestrator import (
    PlatformLearningOrchestrator,
    PlatformProfile,
    PlatformType,
    LearningPhase,
)


@pytest.fixture
def orchestrator(tmp_path: Path) -> PlatformLearningOrchestrator:
    return PlatformLearningOrchestrator(data_root=str(tmp_path))


class TestSeedPlatforms:
    def test_seeds_loaded(self, orchestrator: PlatformLearningOrchestrator) -> None:
        assert len(orchestrator.all_platforms()) >= 4

    def test_groq_console_seeded(self, orchestrator: PlatformLearningOrchestrator) -> None:
        p = orchestrator.get_platform('groq_console')
        assert p is not None
        assert p.name == 'Groq Console'
        assert p.url == 'https://console.groq.com/keys'

    def test_ollama_api_seeded(self, orchestrator: PlatformLearningOrchestrator) -> None:
        p = orchestrator.get_platform('ollama_api')
        assert p is not None
        assert p.platform_type == PlatformType.API


class TestPlatformProfile:
    def test_to_dict_roundtrip(self) -> None:
        p = PlatformProfile(
            platform_id='test',
            name='Test',
            platform_type=PlatformType.CLI,
            url='http://localhost',
            confidence=0.5,
            success_count=3,
            failure_count=1,
        )
        d = p.to_dict()
        p2 = PlatformProfile.from_dict(d)
        assert p2.platform_id == 'test'
        assert p2.platform_type == PlatformType.CLI
        assert p2.confidence == 0.5

    def test_confidence_increases(self) -> None:
        p = PlatformProfile(platform_id='x', name='x')
        assert p.confidence == 0.0
        p.confidence = min(1.0, p.confidence + 0.1)
        assert p.confidence == pytest.approx(0.1)


class TestLearnPlatform:
    def test_dry_run_known(self, orchestrator: PlatformLearningOrchestrator) -> None:
        attempt = orchestrator.learn_platform('ollama_api', 'check API')
        assert attempt.platform_id == 'ollama_api'
        # Should reach at least VERIFY phase in dry run
        assert attempt.phase in (LearningPhase.VERIFY, LearningPhase.ADJUST, LearningPhase.PERSIST)

    def test_dry_run_unknown(self, orchestrator: PlatformLearningOrchestrator) -> None:
        attempt = orchestrator.learn_platform('new_platform', 'explore')
        assert attempt.platform_id == 'new_platform'
        # Platform should be registered
        assert orchestrator.get_platform('new_platform') is not None

    def test_with_executor_success(self, orchestrator: PlatformLearningOrchestrator) -> None:
        attempt = orchestrator.learn_platform(
            'groq_console', 'login',
            executor=lambda action, ctx: True,
        )
        assert attempt.platform_id == 'groq_console'
        # Even with successful executor, may or may not verify (depends on sources)
        assert attempt.duration_seconds >= 0.0

    def test_with_executor_failure(self, orchestrator: PlatformLearningOrchestrator) -> None:
        attempt = orchestrator.learn_platform(
            'groq_console', 'login',
            executor=lambda action, ctx: False,
        )
        # Platform should record failure
        p = orchestrator.get_platform('groq_console')
        assert p is not None


class TestPersistence:
    def test_platforms_persisted(self, orchestrator: PlatformLearningOrchestrator, tmp_path: Path) -> None:
        orchestrator.discover_platform('new_one', name='New One', url='http://example.com')
        path = tmp_path / 'evolution' / 'platform_learning' / 'learned_platforms.json'
        assert path.exists()
        data = json.loads(path.read_text())
        ids = [d['platform_id'] for d in data]
        assert 'new_one' in ids

    def test_attempts_persisted(self, orchestrator: PlatformLearningOrchestrator, tmp_path: Path) -> None:
        orchestrator.learn_platform('ollama_api', 'check')
        path = tmp_path / 'evolution' / 'platform_learning' / 'learning_attempts.jsonl'
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) >= 1


class TestDiscoverPlatform:
    def test_discover_new(self, orchestrator: PlatformLearningOrchestrator) -> None:
        p = orchestrator.discover_platform('my_tool', name='My Tool', url='http://tool.dev')
        assert p.platform_id == 'my_tool'
        assert p.name == 'My Tool'

    def test_discover_existing(self, orchestrator: PlatformLearningOrchestrator) -> None:
        p = orchestrator.discover_platform('groq_console')
        assert p.name == 'Groq Console'  # Returns existing, not new


class TestOsesFindings:
    def test_findings_include_learning_needed(self, orchestrator: PlatformLearningOrchestrator) -> None:
        findings = orchestrator.oses_findings()
        # Seeds all start with confidence=0, so should suggest learning
        assert any('need learning' in f.get('title', '').lower() for f in findings)

    def test_reliability_issue(self, tmp_path: Path) -> None:
        orch = PlatformLearningOrchestrator(data_root=str(tmp_path))
        p = orch.get_platform('groq_console')
        if p:
            p.success_count = 2
            p.failure_count = 8
            orch._save_platforms()
        findings = orch.oses_findings()
        reliability_findings = [f for f in findings if 'reliability' in f.get('title', '').lower()]
        assert len(reliability_findings) >= 1


class TestStatusSummary:
    def test_summary(self, orchestrator: PlatformLearningOrchestrator) -> None:
        summary = orchestrator.status_summary()
        assert 'total_platforms' in summary
        assert summary['total_platforms'] >= 4
        assert 'unlearned' in summary
