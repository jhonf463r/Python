"""
KnowledgeOperationalExecutor - Clean Knowledge Query Integration

This is a clean implementation of the knowledge.query executor that reuses
existing LocalRoleRouter infrastructure without introducing new authorities
or duplicating persistence.

Scope: knowledge.query only
- P0.212 GPU: OUT
- cross-agent-sync: OUT  
- organism_state_snapshot: OUT
- reproducibility: OUT
"""

from __future__ import annotations

from iabv_v15.domain.models import (
    AdaptiveSession,
    InferenceRequest,
    RunStatus,
    TaskRole,
    ToolCapability,
)
from iabv_v15.services.adaptive.execution_playbook_service import OperationalExecutorResult
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


class KnowledgeOperationalExecutor:
    """Executor for knowledge.query domain using existing LocalRoleRouter infrastructure."""
    
    name = 'knowledge_query_executor'
    
    def __init__(self, role_router: LocalRoleRouter) -> None:
        """Initialize with LocalRoleRouter to reuse existing knowledge query implementation.
        
        Args:
            role_router: LocalRoleRouter that contains execute_knowledge_query() method
        """
        self.role_router = role_router
    
    def supports(self, session: AdaptiveSession) -> bool:
        """Check if this executor supports the given session.
        
        Supports sessions where:
        - chosen_pack_id is 'knowledge.query'
        
        Args:
            session: AdaptiveSession to check
            
        Returns:
            True if this executor can handle the session, False otherwise
        """
        return session.chosen_pack_id == 'knowledge.query'
    
    def describe(self, session: AdaptiveSession) -> str:
        """Describe the executor's capability for the given session.
        
        Args:
            session: AdaptiveSession to describe
            
        Returns:
            Human-readable description of what this executor can do
        """
        if not self.supports(session):
            pack = session.chosen_pack_title or session.chosen_pack_id or 'esta tarea'
            return f'Este executor no soporta {pack}.'
        
        if self._check_preconditions(session):
            return (
                'Consulta local de conocimiento con contexto. '
                'Utiliza KnowledgeRepository, búsqueda semántica y modelo local.'
            )
        else:
            return (
                'Contexto insuficiente para ejecutar knowledge query. '
                'Requiere user_goal válido y contexto inicializado.'
            )
    
    def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
        """Execute knowledge query using existing LocalRoleRouter infrastructure.
        
        This method:
        1. Constructs InferenceRequest from AdaptiveSession
        2. Invokes LocalRoleRouter.execute_knowledge_query()
        3. Converts InferenceResult to OperationalExecutorResult
        4. Does NOT duplicate persistence (handled by InferenceService)
        
        Args:
            session: AdaptiveSession with knowledge.query context
            
        Returns:
            OperationalExecutorResult with execution status and results
        """
        # Check preconditions
        if not self._check_preconditions(session):
            return OperationalExecutorResult(
                executed=False,
                status=RunStatus.PARTIAL,
                summary='Contexto insuficiente para ejecutar knowledge query. Se requiere user_goal válido y contexto inicializado.',
                next_actions=['Ver evolutivo'],
                metadata={'precondition': 'insufficient_context'},
            )
        
        # Construct InferenceRequest from AdaptiveSession
        request = self._build_inference_request(session)
        
        # Execute using existing LocalRoleRouter infrastructure
        try:
            route, result = self.role_router.execute_knowledge_query(request)
            
            # Convert InferenceResult to OperationalExecutorResult
            return self._build_executor_result(result, route)
            
        except Exception as exc:
            return OperationalExecutorResult(
                executed=False,
                status=RunStatus.FAILED,
                summary=f'Error en ejecución de knowledge query: {str(exc)}',
                next_actions=['Ver evolutivo'],
                metadata={
                    'error': str(exc),
                    'error_type': type(exc).__name__,
                },
            )
    
    def _check_preconditions(self, session: AdaptiveSession) -> bool:
        """Check if required context is available for knowledge query execution.
        
        Preconditions:
        - session.user_goal must be valid and non-empty
        - session.context must exist (but can be empty)
        
        The legacy route _route_knowledge() performs its own retrieval via
        KnowledgeRepository.search() and EmbeddingIndexService.search(), so
        pre-existing knowledge_hits or recent_runs are useful context but NOT
        required for execution. A new query on a topic not yet in memory should
        still attempt real retrieval.
        
        Args:
            session: AdaptiveSession to check
            
        Returns:
            True if preconditions are met, False otherwise
        """
        # Require user_goal to be valid and non-empty
        if not session.user_goal or not session.user_goal.strip():
            return False
        
        # Require context to exist (but it can be empty)
        # This allows new queries to attempt retrieval without pre-existing context
        return session.context is not None
    
    def _build_inference_request(self, session: AdaptiveSession):
        """Construct InferenceRequest from AdaptiveSession for knowledge query.
        
        Args:
            session: AdaptiveSession with user_goal and context
            
        Returns:
            InferenceRequest configured for TaskRole.KNOWLEDGE
        """
        from iabv_v15.domain.models import InferenceRequest
        
        return InferenceRequest(
            user_goal=session.user_goal,
            task_role=TaskRole.KNOWLEDGE,
            knowledge_scope=['episodes', 'knowledge_items', 'run_records', 'docs', 'dossiers', 'adaptive_sessions'],
            read_only_sql=True,  # Knowledge role is read-only
            allowed_tools=[ToolCapability.KNOWLEDGE_SEARCH, ToolCapability.EMBEDDINGS],
            # Preserve existing metadata if present
            metadata=session.metadata if session.metadata else {},
        )
    
    def _build_executor_result(self, result, route) -> OperationalExecutorResult:
        """Convert InferenceResult to OperationalExecutorResult.
        
        Args:
            result: InferenceResult from LocalRoleRouter
            route: RoleRoute from LocalRoleRouter
            
        Returns:
            OperationalExecutorResult with appropriate status and metadata
        """
        # Determine status based on result
        if result.used_fallback:
            status = RunStatus.PARTIAL
        else:
            status = RunStatus.SUCCESS
        
        # Extract knowledge hits count
        knowledge_hits = result.raw_output.get('knowledge_hits', []) if result.raw_output else []
        knowledge_hits_count = len(knowledge_hits)
        
        # Determine next actions
        if status == RunStatus.SUCCESS:
            next_actions = ['Ver evidencia relacionada', 'Revisar resultado']
        else:
            next_actions = ['Ver evidencia relacionada', 'Revisar resultado']  # Still show results even with fallback
        
        return OperationalExecutorResult(
            executed=True,
            status=status,
            summary=result.summary,
            next_actions=next_actions,
            metadata={
                'knowledge_hits_count': knowledge_hits_count,
                'sources': result.sources if result.sources else [],
                'inference_result': result.model_dump() if result else {},
                'route_summary': route.model_dump() if route else {},
                'used_fallback': result.used_fallback if hasattr(result, 'used_fallback') else False,
            },
        )
