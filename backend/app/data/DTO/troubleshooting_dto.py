from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field  # type: ignore[import-untyped]

from app.data.DTO.conversation_context_dto import ConversationAIContext


class ProblemCategoryView(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None


class ProblemCauseView(BaseModel):
    id: UUID
    category_id: UUID
    slug: str
    name: str
    description: Optional[str] = None


class ProblemSolutionView(BaseModel):
    id: UUID
    cause_id: UUID
    slug: str
    title: str
    instructions: str
    summary: Optional[str] = None
    step_order: int
    requires_escalation: bool = False


class PlannedSolution(BaseModel):
    solution: ProblemSolutionView
    already_suggested: bool = False


class ProblemClassificationRequest(BaseModel):
    session_id: UUID
    locale: str
    user_text: str
    context: ConversationAIContext

class ProblemRequestType(str, Enum):
    TROUBLESHOOT = "troubleshoot"
    RESOLUTION_CHECK = "resolution_check"
    ESCALATION = "escalation"
    CLARIFICATION = "clarification"


class ProblemClassificationResult(BaseModel):
    category: Optional[ProblemCategoryView] = None
    cause: Optional[ProblemCauseView] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    escalate: bool = False
    escalate_reason: Optional[str] = None
    needs_more_info: bool = False
    next_questions: List[str] = Field(default_factory=list)
    request_type: Optional[ProblemRequestType] = None


class SuggestionPlannerRequest(BaseModel):
    session_id: UUID
    classification: ProblemClassificationResult
    max_suggestions: int = 3


class SuggestionPlan(BaseModel):
    solutions: List[PlannedSolution] = Field(default_factory=list)
    escalate: bool = False
    notes: Optional[str] = None

    def suggested_solution_slugs(self) -> List[str]:
        return [item.solution.slug for item in self.solutions]
