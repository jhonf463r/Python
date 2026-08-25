"""Focused tests for evidence_basis in PortableContext.

Covers:
- _evidence_basis_snapshot with observed / inferred / unresolved states
- _evidence_basis_section renders correctly
- build_package metadata includes evidence_basis
- evidence_basis section appears in sections list
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    PortableContextPackage,
    TaskContext,
    ToolLiveStatus,
    WorldModelSnapshot,
)


from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _live_tool() -> ToolLiveStatus:
    return ToolLiveStatus(tool_id='ollama', available=True, status='ready')


def _service(
    *,
    world_model: WorldModelSnapshot | None = None,
    environment: EnvironmentSelfModel | None = None,
    task_context_assembler: Any = None,
) -> PortableContextService:
    storage = MagicMock(spec=ArtifactStorage)
    storage.resolve.return_value = '/tmp/test'
    storage.exists.return_value = False
    storage.save_json_atomic = MagicMock()
    storage.save_bytes = MagicMock()

    wm_service = None
    if world_model is not None:
        wm_service = MagicMock()
        wm_service.current_model.return_value = world_model

    env_service = None
    if environment is not None:
        env_service = MagicMock()
        env_service.current_model.return_value = environment

    svc = PortableContextService(
        workspace_root='/tmp/test',
        storage=storage,
        world_model_service=wm_service,
        environment_self_awareness_service=env_service,
        task_context_assembler=task_context_assembler,
    )
    return svc


# ─── _evidence_basis_snapshot ────────────────────────────────


def test_snapshot_observed_with_world_model_and_environment() -> None:
    svc = _service()
    world = WorldModelSnapshot(confidence=0.8, tool_live_status=[_live_tool()])
    env = EnvironmentSelfModel(environment_id='test-env-001')
    result = svc._evidence_basis_snapshot(
        environment=env,
        world=world,
    )
    assert result['state'] == 'observed'
    assert 'world_model' in result['live_sources']
    assert 'environment_self_model' in result['live_sources']


def test_snapshot_inferred_with_learning_only() -> None:
    svc = _service()
    world = WorldModelSnapshot()
    env = EnvironmentSelfModel()
    tc = TaskContext(metadata={'adaptive_learning_summary': {'best': 'ollama'}})
    result = svc._evidence_basis_snapshot(
        environment=env,
        world=world,
        task_context=tc,
    )
    assert result['state'] == 'inferred'
    assert 'adaptive_learning' in result['persisted_sources']
    assert result['live_sources'] == []


def test_snapshot_unresolved_with_nothing() -> None:
    svc = _service()
    world = WorldModelSnapshot()
    env = EnvironmentSelfModel()
    result = svc._evidence_basis_snapshot(
        environment=env,
        world=world,
    )
    assert result['state'] == 'unresolved'
    assert result['live_sources'] == []
    assert result['persisted_sources'] == []


def test_snapshot_delegates_to_assembler_when_available() -> None:
    assembler = MagicMock()
    assembler._classify_evidence_basis.return_value = {
        'state': 'observed',
        'live_sources': ['world_model'],
        'persisted_sources': [],
        'unresolved': [],
    }
    svc = _service(task_context_assembler=assembler)
    world = WorldModelSnapshot(confidence=0.9, tool_live_status=[_live_tool()])
    env = EnvironmentSelfModel(environment_id='test')
    result = svc._evidence_basis_snapshot(environment=env, world=world)
    assert result['state'] == 'observed'
    assembler._classify_evidence_basis.assert_called_once()


def test_snapshot_propagates_unresolved_fields() -> None:
    svc = _service()
    world = WorldModelSnapshot(
        confidence=0.8,
        tool_live_status=[_live_tool()],
        unresolved_fields=['UNRESOLVED:visual_signal'],
    )
    env = EnvironmentSelfModel(
        environment_id='test',
        unresolved_fields=['UNRESOLVED:runtime_signals'],
    )
    result = svc._evidence_basis_snapshot(environment=env, world=world)
    assert result['state'] == 'observed'
    assert 'UNRESOLVED:visual_signal' in result['unresolved']
    assert 'UNRESOLVED:runtime_signals' in result['unresolved']


# ─── _evidence_basis_section ────────────────────────────────


def test_section_observed_renders_correctly() -> None:
    svc = _service()
    from iabv_v15.domain.models import utc_now
    now = utc_now()
    section = svc._evidence_basis_section(
        evidence={
            'state': 'observed',
            'live_sources': ['world_model', 'environment_self_model'],
            'persisted_sources': ['adaptive_learning'],
            'unresolved': [],
        },
        now=now,
    )
    assert section.section_id == 'evidence_basis'
    assert section.confidence == 0.9
    assert 'observada en vivo' in section.summary
    assert any(item.get('label') == 'state' and item.get('value') == 'observed' for item in section.items)
    assert any(item.get('label') == 'live_sources' for item in section.items)
    assert section.unresolved_fields == []


def test_section_inferred_renders_correctly() -> None:
    svc = _service()
    from iabv_v15.domain.models import utc_now
    now = utc_now()
    section = svc._evidence_basis_section(
        evidence={
            'state': 'inferred',
            'live_sources': [],
            'persisted_sources': ['ia_trace'],
            'unresolved': [],
        },
        now=now,
    )
    assert section.confidence == 0.6
    assert 'inferida' in section.summary
    assert section.unresolved_fields == []


def test_section_unresolved_renders_with_marker() -> None:
    svc = _service()
    from iabv_v15.domain.models import utc_now
    now = utc_now()
    section = svc._evidence_basis_section(
        evidence={
            'state': 'unresolved',
            'live_sources': [],
            'persisted_sources': [],
            'unresolved': ['UNRESOLVED:world_model'],
        },
        now=now,
    )
    assert section.confidence == 0.0
    assert 'Sin evidencia confirmada' in section.summary
    assert 'UNRESOLVED:evidence_basis_no_sources' in section.unresolved_fields


def test_section_metadata_matches_evidence_dict() -> None:
    svc = _service()
    from iabv_v15.domain.models import utc_now
    now = utc_now()
    evidence = {
        'state': 'observed',
        'live_sources': ['world_model'],
        'persisted_sources': [],
        'unresolved': [],
    }
    section = svc._evidence_basis_section(evidence=evidence, now=now)
    assert section.metadata['state'] == 'observed'
    assert section.metadata['live_sources'] == ['world_model']


# ─── build_package integration ───────────────────────────────


def test_build_package_includes_evidence_basis_in_metadata() -> None:
    world = WorldModelSnapshot(confidence=0.8, tool_live_status=[_live_tool()])
    env = EnvironmentSelfModel(environment_id='test-env')
    svc = _service(world_model=world, environment=env)
    package = svc.build_package(
        environment_self_model=env,
        world_model=world,
    )
    assert 'evidence_basis' in package.metadata
    eb = package.metadata['evidence_basis']
    assert eb['state'] == 'observed'
    assert 'world_model' in eb['live_sources']


def test_build_package_has_evidence_basis_section() -> None:
    world = WorldModelSnapshot(confidence=0.8, tool_live_status=[_live_tool()])
    env = EnvironmentSelfModel(environment_id='test-env')
    svc = _service(world_model=world, environment=env)
    package = svc.build_package(
        environment_self_model=env,
        world_model=world,
    )
    section_ids = [s.section_id for s in package.sections]
    assert 'evidence_basis' in section_ids
    eb_section = next(s for s in package.sections if s.section_id == 'evidence_basis')
    assert eb_section.metadata['state'] == 'observed'


def test_build_package_unresolved_evidence_basis() -> None:
    world = WorldModelSnapshot()
    env = EnvironmentSelfModel()
    svc = _service(world_model=world, environment=env)
    package = svc.build_package(
        environment_self_model=env,
        world_model=world,
    )
    eb = package.metadata['evidence_basis']
    assert eb['state'] == 'unresolved'
    eb_section = next(s for s in package.sections if s.section_id == 'evidence_basis')
    assert 'UNRESOLVED:evidence_basis_no_sources' in eb_section.unresolved_fields
