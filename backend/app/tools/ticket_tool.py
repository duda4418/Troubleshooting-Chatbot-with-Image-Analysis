from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.data.DTO import AssistantToolResult
from app.tools.base import BaseTool


class TicketTool(BaseTool):
    """Mock tool for creating internal support tickets with user consent."""

    name = "ticket_tool"
    description = "Create an internal follow-up ticket for unresolved issues."

    async def run(self, **kwargs: Any) -> AssistantToolResult:
        consent = kwargs.get("consent", False)
        summary = kwargs.get("summary", "")
        if not consent:
            return AssistantToolResult(
                tool_name=self.name,
                success=False,
                details={"reason": "consent_required"},
            )

        ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
        return AssistantToolResult(
            tool_name=self.name,
            success=True,
            details={
                "ticket_id": ticket_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "summary": summary,
            },
        )
