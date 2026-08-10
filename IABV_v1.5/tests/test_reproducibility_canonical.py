"""Canonical tests for reproducibility validation (P1).

Tests validate that ReproducibilityValidationService works correctly
with the actual KnowledgeItem model contract (historical validation).
"""
import sys
from pathlib import Path

# Add src directory to path relative to this test file
test_dir = Path(__file__).resolve().parent
src_dir = test_dir.parent / 'src'
sys.path.insert(0, str(src_dir))

import tempfile
import shutil
import pytest

from iabv_v15.domain.models import KnowledgeItem, InteractionPattern, InteractionChannel, ToolType, UniversalInteractionStep
from iabv_v15.services.learning.reproducibility_validation_service import ReproducibilityValidationService
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


def test_service_instantiation():
    """TEST 1: Service instantiation."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        db_path = temp_path / "test.db"
        db = AppDatabase(str(db_path))
        knowledge_repo = KnowledgeRepository(db)
        storage = ArtifactStorage(str(temp_path))
        tool_repo = ToolRecordRepository(db, storage)
        
        service = ReproducibilityValidationService(
            knowledge_repository=knowledge_repo,
            tool_record_repository=tool_repo,
            workspace_root=str(temp_path),
        )
        
        assert service is not None, 'Service should be instantiated'
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def test_validate_knowledge_item_with_actual_model():
    """TEST 2: validate_knowledge_item works with actual KnowledgeItem model."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        db_path = temp_path / "test.db"
        db = AppDatabase(str(db_path))
        knowledge_repo = KnowledgeRepository(db)
        storage = ArtifactStorage(str(temp_path))
        tool_repo = ToolRecordRepository(db, storage)
        
        service = ReproducibilityValidationService(
            knowledge_repository=knowledge_repo,
            tool_record_repository=tool_repo,
            workspace_root=str(temp_path),
        )
        
        # Create a test knowledge item with actual model fields
        item = KnowledgeItem(
            title='Test knowledge',
            summary='Test summary',
            confidence=0.8,
            payload={'route': 'test_route', 'result': 'test_result'},
        )
        knowledge_repo.upsert(item)
        
        # Validate it
        result = service.validate_knowledge_item(item.knowledge_id)
        
        assert result.validation_id != '', 'Should have validation_id'
        assert result.knowledge_id == item.knowledge_id, 'Should match knowledge_id'
        assert result.learning_type == 'generic', 'Should be generic type'
        assert result.reproduction_attempted == True, 'Should attempt reproduction'
        assert result.reproduction_successful == True, 'Should be successful with good context'
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def test_validate_interaction_pattern_historical():
    """TEST 3: validate_interaction_pattern works with historical validation."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        db_path = temp_path / "test.db"
        db = AppDatabase(str(db_path))
        knowledge_repo = KnowledgeRepository(db)
        storage = ArtifactStorage(str(temp_path))
        tool_repo = ToolRecordRepository(db, storage)
        
        service = ReproducibilityValidationService(
            knowledge_repository=knowledge_repo,
            tool_record_repository=tool_repo,
            workspace_root=str(temp_path),
        )
        
        # Create a test interaction pattern with successful history
        pattern = InteractionPattern(
            signature='test_signature',
            title='Test pattern',
            channel=InteractionChannel.UI,
            tool_id='test_tool',
            tool_type=ToolType.BROWSER,
            site_id='test_site',
            operations=[
                UniversalInteractionStep(
                    channel=InteractionChannel.UI,
                    operation='click',
                    target='#button',
                ),
                UniversalInteractionStep(
                    channel=InteractionChannel.UI,
                    operation='input',
                    target='#username',
                ),
            ],
            reusable=True,
            success_count=3,
            failure_count=1,
        )
        saved_pattern = tool_repo.save_interaction_pattern(pattern)
        
        # Validate it
        result = service.validate_interaction_pattern(saved_pattern.pattern_id)
        
        assert result.validation_id != '', 'Should have validation_id'
        assert result.interaction_pattern_id == saved_pattern.pattern_id, 'Should match pattern_id'
        assert result.reproduction_attempted == True, 'Should attempt validation'
        # success_rate = 3/4 = 0.75 >= 0.7, success_count = 3 >= 2, debería ser exitoso
        assert result.reproduction_successful == True, f'Should be successful (success_rate=0.75, success_count=3). Got: {result.failure_reason}'
        assert result.confidence_score >= 0.7, 'Should have confidence >= 0.7'
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def test_validation_result_structure():
    """TEST 4: Validation result structure."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        db_path = temp_path / "test.db"
        db = AppDatabase(str(db_path))
        knowledge_repo = KnowledgeRepository(db)
        storage = ArtifactStorage(str(temp_path))
        tool_repo = ToolRecordRepository(db, storage)
        
        service = ReproducibilityValidationService(
            knowledge_repository=knowledge_repo,
            tool_record_repository=tool_repo,
            workspace_root=str(temp_path),
        )
        
        # Create a knowledge item with low confidence
        item = KnowledgeItem(
            title='Low confidence knowledge',
            summary='Test summary',
            confidence=0.3,
            payload={'route': 'test'},
        )
        knowledge_repo.upsert(item)
        
        # Validate it
        result = service.validate_knowledge_item(item.knowledge_id)
        
        assert hasattr(result, 'validation_id'), 'Should have validation_id'
        assert hasattr(result, 'knowledge_id'), 'Should have knowledge_id'
        assert hasattr(result, 'learning_type'), 'Should have learning_type'
        assert hasattr(result, 'reproduction_attempted'), 'Should have reproduction_attempted'
        assert hasattr(result, 'reproduction_successful'), 'Should have reproduction_successful'
        assert hasattr(result, 'confidence_score'), 'Should have confidence_score'
        assert hasattr(result, 'failure_reason'), 'Should have failure_reason'
        assert hasattr(result, 'evidence_summary'), 'Should have evidence_summary'
        assert hasattr(result, 'validated_at_utc'), 'Should have validated_at_utc'
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def test_validation_persists_to_disk():
    """TEST 5: Validation persists to disk."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        db_path = temp_path / "test.db"
        db = AppDatabase(str(db_path))
        knowledge_repo = KnowledgeRepository(db)
        storage = ArtifactStorage(str(temp_path))
        tool_repo = ToolRecordRepository(db, storage)
        
        service = ReproducibilityValidationService(
            knowledge_repository=knowledge_repo,
            tool_record_repository=tool_repo,
            workspace_root=str(temp_path),
        )
        
        # Create and validate a knowledge item
        item = KnowledgeItem(
            title='Test persistence',
            summary='Test summary',
            confidence=0.9,
            payload={'route': 'test_route'},
        )
        knowledge_repo.upsert(item)
        
        result = service.validate_knowledge_item(item.knowledge_id)
        
        # Check that validation file was created
        validation_path = temp_path / "data" / "evolution" / "reproducibility_validations" / "validations.jsonl"
        assert validation_path.exists(), 'Validation file should be created'
        
        # Check that it contains data
        with open(validation_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 0, 'Validation file should contain data'
        assert result.validation_id in content, 'Validation ID should be in file'
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)