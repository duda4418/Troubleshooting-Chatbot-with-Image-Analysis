from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.data.DTO import AssistantToolResult


class BaseTool(ABC):
    """Base abstraction for assistant tools."""

    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs: Any) -> AssistantToolResult:
        """Execute the tool with arbitrary keyword arguments."""
        raise NotImplementedError
