from __future__ import annotations

from typing import Any, List

from app.data.DTO import AssistantToolResult, KnowledgeHit
from app.services.chroma_service import ChromaService
from app.tools.base import BaseTool


class KnowledgeSearchTool(BaseTool):
    """Tool that queries the knowledge base for similar issues."""

    name = "knowledge_search"
    description = "Search known dishwasher troubleshooting cases."

    def __init__(self, chroma_service: ChromaService) -> None:
        self._chroma_service = chroma_service

    async def run(self, **kwargs: Any) -> AssistantToolResult:
        query: str = kwargs.get("query", "")
        if not query:
            return AssistantToolResult(tool_name=self.name, success=False, details={"reason": "missing_query"})

        hits: List[KnowledgeHit] = await self._chroma_service.search(query)
        return AssistantToolResult(
            tool_name=self.name,
            success=True,
            details={
                "hits": [hit.model_dump() for hit in hits],
            },
        )
