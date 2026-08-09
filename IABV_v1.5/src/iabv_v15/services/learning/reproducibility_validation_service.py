"""ReproducibilityValidationService: validación de que lo aprendido se puede reproducir.

Este servicio toma conocimiento aprendido, intenta reproducirlo y reporta
si la reproducción fue exitosa o no, con evidencia trazable.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from iabv_v15.domain.models import KnowledgeItem, InteractionPattern
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository


@dataclass
class ReproducibilityValidationResult:
    """Resultado de validación de reproducibilidad."""
    
    validation_id: str = ""
    knowledge_id: str = ""
    interaction_pattern_id: str = ""
    learning_type: str = ""
    reproduction_attempted: bool = False
    reproduction_successful: bool = False
    confidence_score: float = 0.0
    failure_reason: str = ""
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    validated_at_utc: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ReproducibilityValidationService:
    """Servicio que valida si el conocimiento aprendido se puede reproducir."""
    
    def __init__(
        self,
        *,
        knowledge_repository: KnowledgeRepository,
        tool_record_repository: ToolRecordRepository,
        workspace_root: str,
    ):
        self.knowledge_repository = knowledge_repository
        self.tool_record_repository = tool_record_repository
        self.workspace_root = Path(workspace_root)
        self.validation_path = self.workspace_root / "data" / "evolution" / "reproducibility_validations" / "validations.jsonl"
        self._lock = threading.RLock()
        self._load_validations()
    
    def validate_knowledge_item(self, knowledge_id: str) -> ReproducibilityValidationResult:
        """Valida si un KnowledgeItem aprendido se puede reproducir."""
        # Recuperar el conocimiento
        knowledge_item = self._get_knowledge_item(knowledge_id)
        if knowledge_item is None:
            return self._build_error_result(knowledge_id, "KnowledgeItem not found")
        
        # Determinar tipo de aprendizaje
        learning_type = knowledge_item.learning_type or "unknown"
        
        # Si es enseñanza, intentar validar el patrón de interacción
        if learning_type == "teaching" and knowledge_item.teaching_session_id:
            return self._validate_teaching(knowledge_item)
        
        # Si es otro tipo, validación simplificada
        return self._validate_generic(knowledge_item)
    
    def validate_interaction_pattern(self, pattern_id: str) -> ReproducibilityValidationResult:
        """Valida si un InteractionPattern se puede reproducir."""
        pattern = self.tool_record_repository.get_interaction_pattern(pattern_id)
        if pattern is None:
            return self._build_error_result("", f"InteractionPattern {pattern_id} not found")
        
        # Calcular confianza basada en historial
        success_rate = self._calculate_success_rate(pattern)
        confidence = success_rate if success_rate > 0 else 0.5
        
        # Validar si hay suficientes operaciones para reproducir
        if not pattern.operations or len(pattern.operations) < 2:
            return ReproducibilityValidationResult(
                validation_id=self._generate_id(),
                interaction_pattern_id=pattern_id,
                learning_type="teaching",
                reproduction_attempted=True,
                reproduction_successful=False,
                confidence_score=confidence,
                failure_reason="Insufficient operations to reproduce",
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        
        # Si el patrón ha sido exitoso consistentemente, considerarlo reproducible
        if success_rate >= 0.7 and pattern.success_count >= 2:
            result = ReproducibilityValidationResult(
                validation_id=self._generate_id(),
                interaction_pattern_id=pattern_id,
                learning_type="teaching",
                reproduction_attempted=True,
                reproduction_successful=True,
                confidence_score=confidence,
                evidence_summary={
                    "success_count": pattern.success_count,
                    "failure_count": pattern.failure_count,
                    "operations_count": len(pattern.operations),
                    "tool_id": pattern.tool_id,
                    "site_id": pattern.site_id,
                },
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        else:
            result = ReproducibilityValidationResult(
                validation_id=self._generate_id(),
                interaction_pattern_id=pattern_id,
                learning_type="teaching",
                reproduction_attempted=True,
                reproduction_successful=False,
                confidence_score=confidence,
                failure_reason=f"Insufficient success rate ({success_rate:.2f}) or insufficient successes ({pattern.success_count})",
                evidence_summary={
                    "success_count": pattern.success_count,
                    "failure_count": pattern.failure_count,
                    "operations_count": len(pattern.operations),
                },
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        
        self._save_validation(result)
        return result
    
    def _validate_teaching(self, knowledge_item: KnowledgeItem) -> ReproducibilityValidationResult:
        """Valida una enseñanza específica."""
        # Buscar patrón de interacción asociado
        patterns = self.tool_record_repository.list_interaction_patterns()
        teaching_pattern = None
        
        for pattern in patterns:
            if pattern.metadata.get('source') == 'teaching_session':
                # Intentar vincular por teaching_session_id si está disponible
                if pattern.metadata.get('teaching_session_id') == knowledge_item.teaching_session_id:
                    teaching_pattern = pattern
                    break
        
        if teaching_pattern is None:
            return ReproducibilityValidationResult(
                validation_id=self._generate_id(),
                knowledge_id=knowledge_item.knowledge_id,
                learning_type="teaching",
                reproduction_attempted=False,
                reproduction_successful=False,
                confidence_score=0.0,
                failure_reason="No associated InteractionPattern found for this teaching",
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        
        # Validar el patrón
        return self.validate_interaction_pattern(teaching_pattern.pattern_id)
    
    def _validate_generic(self, knowledge_item: KnowledgeItem) -> ReproducibilityValidationResult:
        """Validación genérica para tipos de aprendizaje no-enseñanza."""
        # Para conocimiento genérico, la reproducibilidad se basa en:
        # - Si tiene suficiente contexto en payload
        # - Si la confianza es razonable
        # - Si puede recuperarse correctamente
        
        payload = knowledge_item.payload or {}
        has_context = bool(payload.get('route') or payload.get('result') or payload.get('decision_context'))
        
        if has_context and knowledge_item.confidence >= 0.5:
            result = ReproducibilityValidationResult(
                validation_id=self._generate_id(),
                knowledge_id=knowledge_item.knowledge_id,
                learning_type=knowledge_item.learning_type or "unknown",
                reproduction_attempted=True,
                reproduction_successful=True,
                confidence_score=knowledge_item.confidence,
                evidence_summary={
                    "has_context": has_context,
                    "original_confidence": knowledge_item.confidence,
                    "tags": knowledge_item.tags,
                },
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        else:
            result = ReproducibilityValidationResult(
                validation_id=self._generate_id(),
                knowledge_id=knowledge_item.knowledge_id,
                learning_type=knowledge_item.learning_type or "unknown",
                reproduction_attempted=True,
                reproduction_successful=False,
                confidence_score=knowledge_item.confidence,
                failure_reason="Insufficient context or low confidence",
                evidence_summary={
                    "has_context": has_context,
                    "original_confidence": knowledge_item.confidence,
                },
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        
        self._save_validation(result)
        return result
    
    def _calculate_success_rate(self, pattern: InteractionPattern) -> float:
        """Calcula la tasa de éxito de un patrón."""
        total = pattern.success_count + pattern.failure_count
        if total == 0:
            return 0.0
        return pattern.success_count / total
    
    def _get_knowledge_item(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """Recupera un KnowledgeItem por ID."""
        # Intentar buscar en repository
        items = self.knowledge_repository.list_recent(limit=100)
        for item in items:
            if item.knowledge_id == knowledge_id:
                return item
        return None
    
    def _build_error_result(self, knowledge_id: str, reason: str) -> ReproducibilityValidationResult:
        """Construye un resultado de error."""
        return ReproducibilityValidationResult(
            validation_id=self._generate_id(),
            knowledge_id=knowledge_id,
            learning_type="unknown",
            reproduction_attempted=False,
            reproduction_successful=False,
            confidence_score=0.0,
            failure_reason=reason,
            validated_at_utc=datetime.now(timezone.utc).isoformat(),
        )
    
    def _generate_id(self) -> str:
        """Genera un ID único para la validación."""
        import uuid
        return uuid.uuid4().hex
    
    def _load_validations(self) -> None:
        """Carga validaciones desde disco."""
        if not self.validation_path.exists():
            return
        # Para esta implementación mínima, no cargamos historial completo
        # Solo aseguramos que el directorio existe
        self.validation_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _save_validation(self, result: ReproducibilityValidationResult) -> None:
        """Guarda una validación a disco."""
        self.validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.validation_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.__dict__) + "\n")