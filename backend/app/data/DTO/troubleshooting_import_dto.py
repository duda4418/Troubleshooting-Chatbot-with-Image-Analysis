from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TroubleshootingImportAction(BaseModel):
    slug: str
    title: str
    summary: Optional[str] = None
    instructions: List[str] = Field(default_factory=list)
    requires_escalation: bool = False


class TroubleshootingImportCause(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    detection_hints: List[str] = Field(default_factory=list)
    priority: Optional[int] = None
    actions: List[TroubleshootingImportAction] = Field(default_factory=list)


class TroubleshootingImportProblem(BaseModel):
    slug: str
    name: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    description: Optional[str] = None
    causes: List[TroubleshootingImportCause] = Field(default_factory=list)


class TroubleshootingCatalog(BaseModel):
    version: str = "1.0"
    problems: List[TroubleshootingImportProblem] = Field(default_factory=list)


class TroubleshootingImportResult(BaseModel):
    categories_created: int = 0
    categories_updated: int = 0
    causes_created: int = 0
    causes_updated: int = 0
    solutions_created: int = 0
    solutions_updated: int = 0
    solutions_removed: int = 0
    warnings: List[str] = Field(default_factory=list)
