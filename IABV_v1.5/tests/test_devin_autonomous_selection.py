"""Tests para primera selección operacional autónoma de Devin.

Objetivo: Demostrar que IABV puede seleccionar Devin mediante su mecanismo
existente de experimentación/recomendación sin que el humano indique "usa Devin".

Flujo buscado:
evidencia/historial ExperimentLab
→ StrategySelector.recommend()
→ ExperimentRecommendation
→ ToolTeachService._external_lab_recommendation()
→ _preferred_external_tool_id()
→ devin_api
→ delegación Devin

NO crear nueva arquitectura de selección.
NO introducir ContractVerifier/Coordinator/Registry.
NO integrar Claim/Event como requisito de esta fase.
"""

from datetime import datetime, timezone

import pytest

from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRecommendation,
    ExperimentRun,
)
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager


@pytest.fixture
def tool_teach_service(workspace):
    """Fixture que crea una instancia básica de ToolTeachService."""
    from pathlib import Path
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    
    # Crear repositorio mock
    from iabv_v15.domain.models import ToolCard, ToolCapability, ToolType
    repo = ToolRecordRepository()
    
    # Crear card devin_api
    devin_card = ToolCard(
        tool_id='devin_api',
        name='Devin API',
        description='Devin AI agent via API',
        tool_type=ToolType.AGENT,
        capabilities=[ToolCapability.CODE_EDITING, ToolCapability.FILE_OPERATIONS],
        metadata={
            'api_endpoint': 'https://api.devin.ai/v1/sessions',
            'requires_auth': True,
            'auth_env_var': 'DEVIN_API_KEY',
        },
    )
    repo.save_card(devin_card)
    
    registry = ToolRegistry(repository=repo, adapters={})
    memory = ToolMemory()
    sandbox = ToolSandbox()
    validator = ToolValidator()
    approval_policy = ToolApprovalPolicy()
    rollback_manager = ToolRollbackManager()
    
    service = ToolTeachService(
        registry=registry,
        memory=memory,
        sandbox=sandbox,
        validator=validator,
        approval_policy=approval_policy,
        rollback_manager=rollback_manager,
        adapters={},
        workspace_root=str(workspace),
        experiment_lab=None,  # No necesitamos lab real para esta prueba
    )
    return service


@pytest.fixture
def workspace():
    """Fixture que usa el workspace real del checkout actual."""
    from pathlib import Path
    test_file = Path(__file__).resolve()
    workspace = test_file.parent.parent
    return str(workspace)


def test_strategy_selector_can_recommend_devin():
    """Test A: StrategySelector puede recomendar Devin cuando hay evidencia favorable.
    
    Preparar:
    - Dos configuraciones/candidatos: devin_api y chatgpt_web_assisted
    - Historial donde devin_api tiene mejor score
    - Ejecutar StrategySelector.recommend()
    - Verificar que recommended_assistant_kind == 'devin'
    
    LIMITACIÓN:
    Los ExperimentRun usados en este test son sintéticos/fabricados.
    Esto demuestra que el algoritmo puede seleccionar Devin cuando recibe evidencia histórica favorable,
    pero NO demuestra evidencia histórica real de Devin en producción.
    """
    selector = StrategySelector()
    
    # Configuración Devin
    devin_config = AssistantConfigurationSnapshot(
        planning_mode='with_plan',
        attachments_mode='without_files',
        reasoning_level='extended',
        context_mode='long',
        tools_mode='with_tools',
        browser_mode='without_browser',
        assistant_mode='code',
        origin_mode='external',
        unresolved_fields=[],
        metadata={'assistant_kind': 'devin', 'tool_id': 'devin_api'},
    )
    
    # Configuración ChatGPT
    chatgpt_config = AssistantConfigurationSnapshot(
        planning_mode='with_plan',
        attachments_mode='without_files',
        reasoning_level='normal',
        context_mode='short',
        tools_mode='without_tools',
        browser_mode='with_browser',
        assistant_mode='general',
        origin_mode='external',
        unresolved_fields=[],
        metadata={'assistant_kind': 'chatgpt', 'tool_id': 'chatgpt_web_assisted'},
    )
    
    # Runs históricos donde Devin tiene mejor performance
    now = datetime.now(timezone.utc)
    
    devin_runs = [
        ExperimentRun(
            run_id='devin_run_1',
            suite_name='test_suite',
            objective='refactor_function',
            domain=ExperimentDomain.CODE,
            subject_key='test:refactor_function',
            route=EvaluationRoute.DEVIN_API,
            assistant_kind='devin',
            config_signature='with_plan|without_files|extended|long|with_tools|without_browser|code|external',
            assistant_configuration=devin_config,
            metrics=ExperimentMetric(total_score=0.92, execution_ms=15000),
            success=True,
            started_at=now,
            completed_at=now,
            metadata={},
        ),
        ExperimentRun(
            run_id='devin_run_2',
            suite_name='test_suite',
            objective='refactor_function',
            domain=ExperimentDomain.CODE,
            subject_key='test:refactor_function',
            route=EvaluationRoute.DEVIN_API,
            assistant_kind='devin',
            config_signature='with_plan|without_files|extended|long|with_tools|without_browser|code|external',
            assistant_configuration=devin_config,
            metrics=ExperimentMetric(total_score=0.88, execution_ms=12000),
            success=True,
            started_at=now,
            completed_at=now,
            metadata={},
        ),
        ExperimentRun(
            run_id='devin_run_3',
            suite_name='test_suite',
            objective='refactor_function',
            domain=ExperimentDomain.CODE,
            subject_key='test:refactor_function',
            route=EvaluationRoute.DEVIN_API,
            assistant_kind='devin',
            config_signature='with_plan|without_files|extended|long|with_tools|without_browser|code|external',
            assistant_configuration=devin_config,
            metrics=ExperimentMetric(total_score=0.90, execution_ms=14000),
            success=True,
            started_at=now,
            completed_at=now,
            metadata={},
        ),
    ]
    
    chatgpt_runs = [
        ExperimentRun(
            run_id='chatgpt_run_1',
            suite_name='test_suite',
            objective='refactor_function',
            domain=ExperimentDomain.CODE,
            subject_key='test:refactor_function',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            assistant_kind='chatgpt',
            config_signature='with_plan|without_files|normal|short|without_tools|with_browser|general|external',
            assistant_configuration=chatgpt_config,
            metrics=ExperimentMetric(total_score=0.75, execution_ms=20000),
            success=True,
            started_at=now,
            completed_at=now,
            metadata={},
        ),
        ExperimentRun(
            run_id='chatgpt_run_2',
            suite_name='test_suite',
            objective='refactor_function',
            domain=ExperimentDomain.CODE,
            subject_key='test:refactor_function',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            assistant_kind='chatgpt',
            config_signature='with_plan|without_files|normal|short|without_tools|with_browser|general|external',
            assistant_configuration=chatgpt_config,
            metrics=ExperimentMetric(total_score=0.70, execution_ms=18000),
            success=True,
            started_at=now,
            completed_at=now,
            metadata={},
        ),
    ]
    
    # Ejecutar recommend
    recommendation = selector.recommend(
        domain=ExperimentDomain.CODE,
        subject_key='test:refactor_function',
        candidate_runs=devin_runs + chatgpt_runs,
        historical_runs=chatgpt_runs,
    )
    
    # Verificar que StrategySelector recomienda Devin
    assert recommendation is not None
    assert recommendation.recommended_assistant_kind == 'devin'
    assert recommendation.recommended_route == EvaluationRoute.DEVIN_API
    assert recommendation.score > 0.85  # Devin debe tener mejor score


def test_tool_teach_service_converts_devin_recommendation_to_tool_id():
    """Test B: ToolTeachService convierte recomendación Devin → devin_api.
    
    Flujo:
    - Crear ExperimentRecommendation con recommended_assistant_kind='devin'
    - Ejecutar realmente _preferred_external_tool_id()
    - Verificar que devuelve 'devin_api' SIN assistant_preference manual
    """
    from iabv_v15.domain.models import ExperimentRecommendation
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.infra.persistence.database import AppDatabase
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock
    
    # Crear recomendación simulada de StrategySelector
    lab_recommendation = ExperimentRecommendation(
        domain=ExperimentDomain.CODE,
        subject_key='test:refactor_function',
        recommended_route=EvaluationRoute.DEVIN_API,
        recommended_assistant_kind='devin',
        recommended_assistant_configuration=AssistantConfigurationSnapshot(
            planning_mode='with_plan',
            attachments_mode='without_files',
            reasoning_level='extended',
            context_mode='long',
            tools_mode='with_tools',
            browser_mode='without_browser',
            assistant_mode='code',
            origin_mode='external',
            unresolved_fields=[],
            metadata={'assistant_kind': 'devin', 'tool_id': 'devin_api'},
        ),
        recommended_config_signature='with_plan|without_files|extended|long|with_tools|without_browser|code|external',
        score=0.90,
        confidence=0.85,
        rationale='Devin tiene mejor score historico para esta tarea.',
        supporting_run_ids=['devin_run_1', 'devin_run_2'],
        metadata={},
    )
    
    # Crear ToolTeachService con mocks mínimos
    temp_dir = Path(tempfile.mkdtemp(prefix="test_tool_teach_"))
    db_path = temp_dir / "test_tool_records.sqlite"
    db = AppDatabase(str(db_path))
    repo = ToolRecordRepository(db=db, storage=temp_dir)
    
    # Crear registry
    registry = ToolRegistry(repository=repo, adapters={})
    
    # Crear mocks para dependencias que no necesitamos
    mock_memory = Mock()
    mock_sandbox = Mock()
    mock_validator = Mock()
    mock_approval_policy = Mock()
    mock_rollback_manager = Mock()
    
    # Crear servicio con dependencias mínimas
    service = ToolTeachService(
        registry=registry,
        memory=mock_memory,
        sandbox=mock_sandbox,
        validator=mock_validator,
        approval_policy=mock_approval_policy,
        rollback_manager=mock_rollback_manager,
        adapters={},
        workspace_root=str(temp_dir),
        experiment_lab=None,
    )
    
    try:
        # Ejecutar _preferred_external_tool_id realmente
        preferred_tool_id = service._preferred_external_tool_id(
            assistant_preference='',  # VACIO - NO hay override manual
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=lab_recommendation,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        
        # Verificar resultado real
        assert preferred_tool_id == 'devin_api'
    finally:
        # Cleanup
        try:
            db.close()
            if db_path.exists():
                db_path.unlink()
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass


def test_manual_override_still_works():
    """Test C: Override manual assistant_preference='devin' todavía funciona.
    
    Demostrar que la ruta existente de override manual no se rompió.
    Ejecuta realmente _preferred_external_tool_id() con assistant_preference='devin'.
    """
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.infra.persistence.database import AppDatabase
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock
    
    # Crear ToolTeachService con mocks mínimos
    temp_dir = Path(tempfile.mkdtemp(prefix="test_tool_teach_override_"))
    db_path = temp_dir / "test_tool_records_override.sqlite"
    db = AppDatabase(str(db_path))
    repo = ToolRecordRepository(db=db, storage=temp_dir)
    registry = ToolRegistry(repository=repo, adapters={})
    
    # Crear mocks para dependencias que no necesitamos
    mock_memory = Mock()
    mock_sandbox = Mock()
    mock_validator = Mock()
    mock_approval_policy = Mock()
    mock_rollback_manager = Mock()
    
    service = ToolTeachService(
        registry=registry,
        memory=mock_memory,
        sandbox=mock_sandbox,
        validator=mock_validator,
        approval_policy=mock_approval_policy,
        rollback_manager=mock_rollback_manager,
        adapters={},
        workspace_root=str(temp_dir),
        experiment_lab=None,
    )
    
    try:
        # Ejecutar con override manual real
        preferred_tool_id = service._preferred_external_tool_id(
            assistant_preference='devin',  # OVERRIDE MANUAL EXPLÍCITO
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        
        # Verificar resultado real
        assert preferred_tool_id == 'devin_api'
    finally:
        # Cleanup
        try:
            db.close()
            if db_path.exists():
                db_path.unlink()
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass


def test_existing_routes_not_regressed():
    """Test D: Rutas existentes (codex, claude, chatgpt, ollama) no regresaron.
    
    Verificar que las rutas existentes siguen funcionando sin cambios.
    Ejecuta realmente _preferred_external_tool_id() para cada ruta.
    """
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.infra.persistence.database import AppDatabase
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock
    
    # Crear ToolTeachService con mocks mínimos
    temp_dir = Path(tempfile.mkdtemp(prefix="test_tool_teach_regression_"))
    db_path = temp_dir / "test_tool_records_regression.sqlite"
    db = AppDatabase(str(db_path))
    repo = ToolRecordRepository(db=db, storage=temp_dir)
    registry = ToolRegistry(repository=repo, adapters={})
    
    # Crear mocks para dependencias que no necesitamos
    mock_memory = Mock()
    mock_sandbox = Mock()
    mock_validator = Mock()
    mock_approval_policy = Mock()
    mock_rollback_manager = Mock()
    
    service = ToolTeachService(
        registry=registry,
        memory=mock_memory,
        sandbox=mock_sandbox,
        validator=mock_validator,
        approval_policy=mock_approval_policy,
        rollback_manager=mock_rollback_manager,
        adapters={},
        workspace_root=str(temp_dir),
        experiment_lab=None,
    )
    
    try:
        # Test Codex - ejecuta producción real
        codex_tool_id = service._preferred_external_tool_id(
            assistant_preference='codex',
            diagnostic_category='need_codex_fix',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        assert codex_tool_id == 'codex_installed'
        
        # Test ChatGPT - ejecuta producción real
        chatgpt_tool_id = service._preferred_external_tool_id(
            assistant_preference='chatgpt',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        assert chatgpt_tool_id == 'chatgpt_web_assisted'
        
        # Test Claude - ejecuta producción real
        claude_tool_id = service._preferred_external_tool_id(
            assistant_preference='claude',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        assert claude_tool_id == 'claude_web_assisted'
        
        # Test Ollama - ejecuta producción real
        ollama_tool_id = service._preferred_external_tool_id(
            assistant_preference='ollama',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        assert ollama_tool_id == 'ollama_llm'
    finally:
        # Cleanup
        try:
            db.close()
            if db_path.exists():
                db_path.unlink()
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass


def test_trace_route_for_devin():
    """Test E: _trace_route mapea devin/devin_api a EvaluationRoute.DEVIN_API.
    
    Verificar que el routing de traza funciona correctamente para Devin.
    Ejecuta realmente _trace_route() y verifica el resultado.
    """
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.infra.persistence.database import AppDatabase
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock
    
    # Crear ToolTeachService con mocks mínimos
    temp_dir = Path(tempfile.mkdtemp(prefix="test_tool_teach_trace_"))
    db_path = temp_dir / "test_tool_records_trace.sqlite"
    db = AppDatabase(str(db_path))
    repo = ToolRecordRepository(db=db, storage=temp_dir)
    registry = ToolRegistry(repository=repo, adapters={})
    
    # Crear mocks para dependencias que no necesitamos
    mock_memory = Mock()
    mock_sandbox = Mock()
    mock_validator = Mock()
    mock_approval_policy = Mock()
    mock_rollback_manager = Mock()
    
    service = ToolTeachService(
        registry=registry,
        memory=mock_memory,
        sandbox=mock_sandbox,
        validator=mock_validator,
        approval_policy=mock_approval_policy,
        rollback_manager=mock_rollback_manager,
        adapters={},
        workspace_root=str(temp_dir),
        experiment_lab=None,
    )
    
    try:
        # Test via assistant_kind - ejecuta producción real
        route_via_kind = service._trace_route(tool_id='', assistant_kind='devin')
        assert route_via_kind == EvaluationRoute.DEVIN_API.value
        
        # Test via tool_id - ejecuta producción real
        route_via_tool = service._trace_route(tool_id='devin_api', assistant_kind='')
        assert route_via_tool == EvaluationRoute.DEVIN_API.value
    finally:
        # Cleanup
        try:
            db.close()
            if db_path.exists():
                db_path.unlink()
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass
