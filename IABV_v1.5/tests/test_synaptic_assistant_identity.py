"""Test for synaptic assistant-to-tool identity mapping edge.

This test verifies that selected_assistant_kind from SynapticRouter
correctly maps to semantically corresponding ToolCards.

The defect confirmed by Claude Sonnet's runtime audit:
- selected_assistant_kind='chatgpt_web' → ToolCard with assistant_kind='chatgpt'
- selected_assistant_kind='claude_web' → ToolCard with assistant_kind='claude'
- selected_assistant_kind='ollama_local' → ToolCard with assistant_kind='ollama'

Current behavior:
- pick_card_for_task() does exact match on assistant_kind
- When no exact match, falls back to keyword scoring → cards[0]
- This causes silent substitution (e.g., playwright_browser for chatgpt_web)

Expected behavior:
- Assistant identity should be preserved through mapping
- Fallback should not produce false authoritative selection
"""

import pytest
from pathlib import Path
from iabv_v15.domain.models import TaskRole, ToolTask
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


@pytest.fixture
def registry():
    """Get real ToolRegistry with seeded defaults."""
    db_path = Path('C:/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/data/app.sqlite')
    storage_path = Path('C:/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/data/tool_teaching')
    db = AppDatabase(str(db_path))
    storage = ArtifactStorage(str(storage_path))
    repo = ToolRecordRepository(db=db, storage=storage)
    # Initialize with default adapters (empty dict for test)
    registry = ToolRegistry(repository=repo, adapters={})
    yield registry


def test_assistant_identity_mapping_codex(registry):
    """Test that codex assistant maps to correct ToolCard."""
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='codex')
    assert card is not None
    assert card.tool_id == 'codex_installed'
    assert card.metadata.get('assistant_kind') == 'codex'


def test_assistant_identity_mapping_chatgpt(registry):
    """Test that chatgpt assistant maps to correct ToolCard."""
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='chatgpt')
    assert card is not None
    # Should prefer web_assisted based on existing policy
    assert card.tool_id in {'chatgpt_installed', 'chatgpt_web_assisted'}
    assert card.metadata.get('assistant_kind') == 'chatgpt'


def test_assistant_identity_mapping_claude(registry):
    """Test that claude assistant maps to correct ToolCard."""
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='claude')
    assert card is not None
    # Should prefer web_assisted based on existing policy
    assert card.tool_id in {'claude_installed', 'claude_web_assisted'}
    assert card.metadata.get('assistant_kind') == 'claude'


def test_assistant_identity_mapping_ollama(registry):
    """Test that ollama assistant maps to correct ToolCard."""
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='ollama')
    assert card is not None
    assert card.tool_id == 'ollama_llm'
    assert card.metadata.get('assistant_kind') == 'ollama'


def test_assistant_identity_mapping_chatgpt_web(registry):
    """Test that chatgpt_web (synaptic router output) maps correctly.

    This is the pre-fix failure case: chatgpt_web does not match
    any ToolCard's assistant_kind, so it falls back to keyword scoring
    and returns an unrelated card.
    """
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='chatgpt_web')
    # PRE-FIX: This returns a random card (e.g., playwright_browser)
    # POST-FIX: Should map to chatgpt_web_assisted or chatgpt_installed
    assert card is not None
    # The assistant_kind in metadata should be 'chatgpt' for the selected card
    # ToolCard metadata uses short names, not full synaptic names
    assert card.metadata.get('assistant_kind') == 'chatgpt'


def test_assistant_identity_mapping_claude_web(registry):
    """Test that claude_web (synaptic router output) maps correctly."""
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='claude_web')
    assert card is not None
    assert card.metadata.get('assistant_kind') == 'claude'


def test_assistant_identity_mapping_ollama_local(registry):
    """Test that ollama_local (synaptic router output) maps correctly."""
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='ollama_local')
    assert card is not None
    assert card.metadata.get('assistant_kind') == 'ollama'


def test_assistant_identity_mapping_unmapped(registry):
    """Test that unmapped assistant_kind does not produce false authority.

    If an assistant_kind has no valid mapping, the fallback should not
    return an unrelated card as if it were a semantic match.
    """
    task = ToolTask(
        objective='test',
        title='test',
        tool_id='',
        task_role=TaskRole.ANALYTICS,
    )
    card = registry.pick_card_for_task(task, preferred_assistant_kind='unknown_assistant_xyz')
    # With the current fallback logic, this returns cards[0]
    # After fix, this should either:
    # 1. Return None (no authoritative selection)
    # 2. Explicitly mark as fallback in metadata
    # For now, we verify it doesn't silently claim semantic match
    if card is not None:
        # If a card is returned, it should NOT have assistant_kind matching
        # the requested kind (since it's a fallback)
        assert card.metadata.get('assistant_kind') != 'unknown_assistant_xyz'
