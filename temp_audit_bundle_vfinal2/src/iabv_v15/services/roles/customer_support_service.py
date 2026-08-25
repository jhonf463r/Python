from __future__ import annotations

from typing import Any

from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService


class CustomerSupportService:
    def __init__(
        self,
        knowledge_repository: KnowledgeRepository,
        embedding_service: EmbeddingIndexService,
        sql_service: SqlQueryAdvisorService,
    ) -> None:
        self.knowledge_repository = knowledge_repository
        self.embedding_service = embedding_service
        self.sql_service = sql_service

    def build_context(self, text: str) -> dict[str, Any]:
        knowledge_items = self.knowledge_repository.search(text, limit=8)
        documents = [
            {
                'title': item.title,
                'summary': item.summary,
                'body': str(item.payload),
                'source': f'knowledge:{item.title}',
            }
            for item in knowledge_items
        ]
        semantic_hits = self.embedding_service.search(text, documents, limit=4)
        sql_context = self.sql_service.advise(text)
        sources = [hit['source'] for hit in semantic_hits]
        sources.extend(sql_context.get('sources', []))
        response_template = (
            'Respuesta propuesta al cliente basada en conocimiento interno y datos locales. '
            'Si falta informacion, pide una aclaracion corta antes de comprometer una accion.'
        )
        return {
            'knowledge_hits': semantic_hits,
            'sql_context': sql_context,
            'response_template': response_template,
            'sources': sources,
        }
