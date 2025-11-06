from __future__ import annotations

import logging
from typing import Dict, List
from uuid import UUID

from app.data.DTO.troubleshooting_dto import (
    PlannedSolution,
    ProblemClassificationResult,
    ProblemSolutionView,
    SuggestionPlan,
    SuggestionPlannerRequest,
)
from app.data.repositories import ProblemSolutionRepository
from app.data.repositories.session_suggestion_repository import SessionSuggestionRepository
from app.data.schemas.models import SessionSuggestion

logger = logging.getLogger(__name__)


class SuggestionPlannerService:
    """Plan deterministic troubleshooting steps based on classification output."""

    def __init__(
        self,
        *,
        solution_repository: ProblemSolutionRepository,
        session_suggestion_repository: SessionSuggestionRepository,
    ) -> None:
        self._solution_repository = solution_repository
        self._session_suggestion_repository = session_suggestion_repository

    async def plan(self, request: SuggestionPlannerRequest) -> SuggestionPlan:
        classification = request.classification
        plan = SuggestionPlan(escalate=classification.escalate, notes=classification.escalate_reason)

        if classification.escalate:
            return plan

        cause = classification.cause
        if not cause:
            plan.notes = classification.rationale or plan.notes
            return plan

        existing = await self._session_suggestion_repository.list_by_session(request.session_id)
        existing_by_solution: Dict[UUID, SessionSuggestion] = {item.solution_id: item for item in existing}

        solutions = await self._solution_repository.list_by_cause(cause.id, limit=25)
        new_planned: List[PlannedSolution] = []

        for solution in solutions:
            already = solution.id in existing_by_solution
            if already:
                continue
            new_planned.append(
                PlannedSolution(
                    solution=ProblemSolutionView(
                        id=solution.id,
                        cause_id=solution.cause_id,
                        slug=solution.slug,
                        title=solution.title,
                        instructions=solution.instructions,
                        summary=solution.summary,
                        step_order=solution.step_order,
                        requires_escalation=solution.requires_escalation,
                    ),
                    already_suggested=False,
                )
            )
            if len(new_planned) >= request.max_suggestions:
                break

        plan.solutions = new_planned
        if classification.needs_more_info and not plan.solutions:
            plan.notes = classification.rationale or "Classifier requires more details before proposing steps."
        elif not plan.solutions and existing_by_solution:
            plan.notes = "All catalog steps for this cause have already been suggested."
            plan.escalate = True

        return plan

    async def persist_new_suggestions(self, session_id: UUID, plan: SuggestionPlan) -> None:
        if not plan.solutions:
            return

        for item in plan.solutions:
            if item.already_suggested:
                continue
            suggestion = SessionSuggestion(
                session_id=session_id,
                solution_id=item.solution.id,
            )
            try:
                await self._session_suggestion_repository.create(suggestion)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to record suggestion %s for session %s", item.solution.slug, session_id)
