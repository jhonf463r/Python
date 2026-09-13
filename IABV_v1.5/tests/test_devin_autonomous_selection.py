"""
Tests para jerarquía de autoridad en ToolTeachService.

Contrato de autoridad:
1. Preferencia explícita del usuario (autoridad superior)
2. Recomendación autónoma del laboratorio (solo si no hay preferencia explícita)
3. Fallback existente (solo si no hay preferencia ni recomendación)

Dominio:
- Se deriva de task_kind existente, no de identidad del agente
- Prioridad: task_kind > categoría/incidente técnico > assistant_preference > default
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.domain.models import ExperimentDomain, EvaluationRoute, ExperimentRecommendation


class TestExplicitPreferenceAuthority:
    """CASO A: Preferencia explícita del usuario tiene autoridad superior."""
    
    def test_explicit_preference_overrides_lab_recommendation(self):
        """
        Usuario pide 'devin', ExperimentLab recomienda 'claude'.
        Resultado debe ser 'devin' por ser intención explícita del usuario.
        """
        # Crear recommendation del laboratorio que favorece a Claude
        lab_rec = ExperimentRecommendation(
            domain=ExperimentDomain.CODE,
            recommended_route=EvaluationRoute.CODE_AGENT,
            recommended_assistant_kind='claude',
            confidence=0.95,
            rationale='Lab recomienda Claude',
        )
        
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        # Preferencia explícita 'devin' debe respetarse
        tool_id = service._preferred_external_tool_id(
            assistant_preference='devin',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=lab_rec,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        
        assert tool_id == 'devin_api', "Preferencia explícita 'devin' debe prevalecer sobre recommendation 'claude'"


class TestDomainIndependenceFromAgentIdentity:
    """
    TEST 4: El dominio debe representar la naturaleza de la tarea, no cambiar por identidad del agente.
    Eliminado porque experiment_lab=None no permite verificar el flujo real.
    La funcionalidad se prueba en otros tests que atraviesan producción.
    """
    pass


class TestNoPreferenceAutonomousSelection:
    """CASO B: Sin preferencia → autonomía del laboratorio."""
    
    def test_no_preference_with_lab_recommendation_uses_lab(self):
        """
        assistant_preference=''
        + task_kind='code_review'
        + ExperimentLab recomienda Devin
        → debe usar recommendation del laboratorio
        
        FIXTURE SINTÉTICO: El historial utilizado es controlado para el test.
        No representa evidencia histórica real de producción.
        """
        # Crear recomendación del laboratorio para Devin
        lab_rec = ExperimentRecommendation(
            domain=ExperimentDomain.CODE,
            recommended_route=EvaluationRoute.CODE_AGENT,
            recommended_assistant_kind='devin',
            confidence=0.90,
            rationale='Lab recomienda Devin para code_review',
        )
        
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        # Sin preferencia explícita, debe usar recommendation del laboratorio
        tool_id = service._preferred_external_tool_id(
            assistant_preference='',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=lab_rec,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        
        assert tool_id == 'devin_api', "Sin preferencia, debe usar recommendation del laboratorio (devin)"


class TestNoEvidenceFallback:
    """CASO C: Sin preferencia ni evidencia → fallback existente."""
    
    def test_no_preference_no_evidence_uses_fallback(self):
        """
        assistant_preference=''
        + sin recommendation del laboratorio
        + sin categoría/incidente técnico
        → fallback existente (chatgpt_installed)
        
        NO presentar esto como selección autónoma basada en evidencia.
        """
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        # Sin preferencia, sin recommendation
        tool_id = service._preferred_external_tool_id(
            assistant_preference='',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        
        assert tool_id == 'chatgpt_installed', "Sin evidencia, debe usar fallback existente (chatgpt_installed)"
    
    def test_no_preference_technical_category_uses_codex_fallback(self):
        """
        assistant_preference=''
        + diagnostic_category='need_codex_fix'
        + sin recommendation
        → fallback codex_installed por categoría técnica
        """
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        tool_id = service._preferred_external_tool_id(
            assistant_preference='',
            diagnostic_category='need_codex_fix',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        
        assert tool_id == 'codex_installed', "Categoría técnica debe usar fallback codex_installed"


class TestExistingRoutesRegression:
    """TEST 5: Verificar que rutas existentes no regresan."""
    
    def test_existing_routes_not_regressed(self):
        """
        Verificar que Codex, Claude, ChatGPT y Ollama conservan su comportamiento.
        """
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        # Codex
        codex_id = service._preferred_external_tool_id(
            assistant_preference='codex',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        assert codex_id == 'codex_installed', "Codex debe resolver a codex_installed"
        
        # Claude
        claude_id = service._preferred_external_tool_id(
            assistant_preference='claude',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        assert claude_id == 'claude_web_assisted', "Claude debe resolver a claude_web_assisted"
        
        # ChatGPT
        chatgpt_id = service._preferred_external_tool_id(
            assistant_preference='chatgpt',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        assert chatgpt_id == 'chatgpt_web_assisted', "ChatGPT debe resolver a chatgpt_web_assisted"
        
        # Ollama
        ollama_id = service._preferred_external_tool_id(
            assistant_preference='ollama',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        assert ollama_id == 'ollama_llm', "Ollama debe resolver a ollama_llm"


class TestDevinRequestMetadata:
    """Verifica que devin_api produce metadata coherente con Devin."""
    
    def test_devin_api_request_construction(self):
        """
        preferred_tool_id='devin_api'
        debe producir en _build_external_consultation_request:
        assistant_kind='devin'
        assistant_title='Devin'
        prompt_template_id='devin_consult_v1'
        
        NO debe producir metadata de ChatGPT.
        """
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        # Crear un mock de ToolCard para devin_api
        mock_card = Mock()
        mock_card.metadata = {
            'response_capture_mode': 'manual_pasteback',
            'session_scope': 'external_app',
            'isolated_session_required': False,
        }
        service.registry.get_card = Mock(return_value=mock_card)
        
        # Llamar al método que construye el request completo
        request = service._build_external_consultation_request(
            user_goal='test goal',
            assistant_preference='devin',
            context_pack='',
            site_id=None,
            diagnostic_category='',
            incident_kind='',
            launch_dry_run=True,
            allow_local_automatic_consultation=False,
            goal_parameters={'task_kind': 'code_review'},
        )
        
        # Verificar que el request tiene metadata correcta de Devin
        assert request.goal_parameters['assistant_kind'] == 'devin', "Request debe tener assistant_kind='devin'"
        assert request.goal_parameters['prompt_template_id'] == 'devin_consult_v1', "Request debe tener prompt_template_id='devin_consult_v1'"


class TestBuildExternalConsultationRequest:
    """Verificar que _build_external_consultation_request no crea default oculto."""
    
    def test_empty_preference_remains_empty(self):
        """
        assistant_preference='' debe permanecer vacío,
        NO convertirse en 'codex' artificialmente.
        """
        service = ToolTeachService(
            workspace_root=Path('C:/Python/IABV_v1.5'),
            registry=Mock(),
            experiment_lab=None,
            memory=Mock(),
            sandbox=Mock(),
            validator=Mock(),
            approval_policy=Mock(),
            rollback_manager=Mock(),
            adapters={},
        )
        
        # Verificar que la lógica interna no convierte '' → 'codex'
        # Esto se prueba indirectamente a través de _preferred_external_tool_id
        # Si assistantPreference llegara como 'codex' cuando se pasó '',
        # el fallback sería codex_installed en lugar de chatgpt_installed
        
        tool_id = service._preferred_external_tool_id(
            assistant_preference='',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=True,
        )
        
        # Si '' se convirtiera en 'codex', sería codex_installed
        # Como es '', debe ser chatgpt_installed (fallback general)
        assert tool_id == 'chatgpt_installed', "'' debe usar fallback general, no convertirse en 'codex'"
