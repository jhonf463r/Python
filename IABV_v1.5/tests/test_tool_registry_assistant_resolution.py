"""Tests for ToolRegistry canonical assistant_kind → tool_id resolution.

This tests the I0 seam closure:
assistant_kind → ToolRegistry → ToolCard.metadata["assistant_kind"] → tool_id(s)
"""

import pytest

from iabv_v15.domain.models import ToolCard, ToolType
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_registry import ToolRegistry


@pytest.fixture
def tool_registry(tmp_path):
    """Create a minimal ToolRegistry for testing."""
    db = AppDatabase(str(tmp_path / "app.sqlite"))
    storage = ArtifactStorage(str(tmp_path / "tool_teaching"))
    repo = ToolRecordRepository(db, storage)
    adapters = {}
    registry = ToolRegistry(repository=repo, adapters=adapters)
    return registry


class TestToolRegistryAssistantResolution:
    """Test canonical assistant_kind → tool_id resolution via ToolCard metadata."""

    def test_resolve_devin_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """T1: assistant_kind='devin' should resolve to tool_id='devin_api'."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('devin')
        assert 'devin_api' in tool_ids
        assert len(tool_ids) >= 1

    def test_resolve_unknown_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """T6: unknown assistant_kind should return empty list."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('nonexistent_assistant')
        assert tool_ids == []

    def test_resolve_chatgpt_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """Test that chatgpt resolves to its tool_id(s)."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('chatgpt')
        # chatgpt may have multiple tool_ids (installed, web_assisted)
        assert len(tool_ids) >= 1
        assert any('chatgpt' in tid for tid in tool_ids)

    def test_resolve_claude_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """Test that claude resolves to its tool_id(s)."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('claude')
        # claude may have multiple tool_ids (installed, web_assisted)
        assert len(tool_ids) >= 1
        assert any('claude' in tid for tid in tool_ids)

    def test_resolve_ollama_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """Test that ollama resolves to its tool_id."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('ollama')
        assert 'ollama_llm' in tool_ids

    def test_resolve_codex_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """Test that codex resolves to its tool_id."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('codex')
        assert 'codex_installed' in tool_ids

    def test_case_insensitive_resolution(self, tool_registry: ToolRegistry) -> None:
        """Resolution should be case-insensitive."""
        tool_ids_lower = tool_registry.resolve_tool_ids_by_assistant_kind('devin')
        tool_ids_upper = tool_registry.resolve_tool_ids_by_assistant_kind('DEVIN')
        tool_ids_mixed = tool_registry.resolve_tool_ids_by_assistant_kind('Devin')
        assert tool_ids_lower == tool_ids_upper == tool_ids_mixed

    def test_empty_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """Empty assistant_kind should return empty list."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('')
        assert tool_ids == []

    def test_none_assistant_kind(self, tool_registry: ToolRegistry) -> None:
        """None assistant_kind should return empty list."""
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind(None)  # type: ignore[arg-type]
        assert tool_ids == []
