from __future__ import annotations

from typing import Any

from app.data.DTO import AssistantToolResult
from app.tools.base import BaseTool


class MachineConfigTool(BaseTool):
    """Mock tool that would update dishwasher parameters remotely."""

    name = "machine_config"
    description = "Adjust dishwasher parameters (mock implementation)."

    async def run(self, **kwargs: Any) -> AssistantToolResult:
        parameters = kwargs.get("parameters")
        if not parameters:
            return AssistantToolResult(
                tool_name=self.name,
                success=False,
                details={"reason": "missing_parameters"},
            )

        return AssistantToolResult(
            tool_name=self.name,
            success=True,
            details={
                "applied_parameters": parameters,
            },
        )
