"""Canonical tests for reproducibility validation (P1)."""
import sys
sys.path.insert(0, 'C:/Users/faber/Python/IABV_v1.5/src')

from pathlib import Path
import tempfile
import shutil

from iabv_v15.domain.models import KnowledgeItem, InteractionPattern, InteractionChannel, ToolType, UniversalInteractionStep
from iabv_v15.services.learning.reproducibility_validation_service import ReproducibilityValidationService
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage

print('CANONICAL REPRODUCIBILITY VALIDATION TEST - IABV v1.5')
print('='*80)

# TEST 1: ReproducibilityValidationService exists
print('\n[TEST 1] ReproducibilityValidationService exists')
try:
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Setup minimal infrastructure
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
    print('[PASS] ReproducibilityValidationService can be instantiated')
finally:
    shutil.rmtree(temp_path, ignore_errors=True)

# TEST 2: validate_knowledge_item works
print('\n[TEST 2] validate_knowledge_item works')
try:
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
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
    
    # Create a test knowledge item
    item = KnowledgeItem(
        title='Test knowledge',
        summary='Test summary',
        learning_type='teaching',
        teaching_session_id='test_session_123',
        confidence=0.8,
    )
    knowledge_repo.upsert(item)
    
    # Validate it
    result = service.validate_knowledge_item(item.knowledge_id)
    
    assert result.validation_id != '', 'Should have validation_id'
    assert result.knowledge_id == item.knowledge_id, 'Should match knowledge_id'
    assert result.learning_type == 'teaching', 'Should be teaching type'
    # Sin patrón asociado, no se puede intentar reproducción completa
    # pero el servicio sí analiza la situación
    print('[PASS] validate_knowledge_item works correctly')
finally:
    shutil.rmtree(temp_path, ignore_errors=True)

# TEST 3: validate_interaction_pattern works
print('\n[TEST 3] validate_interaction_pattern works')
try:
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
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
    assert result.reproduction_attempted == True, 'Should attempt reproduction'
    # success_rate = 3/4 = 0.75 >= 0.7, success_count = 3 >= 2, debería ser exitoso
    assert result.reproduction_successful == True, f'Should be successful (success_rate=0.75, success_count=3). Got: {result.failure_reason}'
    assert result.confidence_score >= 0.7, 'Should have confidence >= 0.7'
    print('[PASS] validate_interaction_pattern works correctly')
finally:
    shutil.rmtree(temp_path, ignore_errors=True)

# TEST 4: Validation result structure
print('\n[TEST 4] Validation result structure')
try:
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
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
        learning_type='discovery',
        confidence=0.3,
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
    print('[PASS] Validation result has all required fields')
finally:
    shutil.rmtree(temp_path, ignore_errors=True)

# TEST 5: Validation persists to disk
print('\n[TEST 5] Validation persists to disk')
try:
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
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
        learning_type='teaching',
        confidence=0.9,
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
    
    print('[PASS] Validation persists to disk correctly')
finally:
    shutil.rmtree(temp_path, ignore_errors=True)

print('\n' + '='*80)
print('ALL TESTS PASSED')
print('='*80)

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)
print('[OK] CANONICAL REPRODUCIBILITY VALIDATION TEST PASSED')
print('[INFO] ReproducibilityValidationService exists and works')
print('[INFO] validate_knowledge_item works correctly')
print('[INFO] validate_interaction_pattern works correctly')
print('[INFO] Validation result has all required fields')
print('[INFO] Validation persists to disk correctly')
print('[INFO] P1 gap for reproducibility validation is now closed')
print('='*80)