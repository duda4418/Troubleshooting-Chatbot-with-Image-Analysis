from __future__ import annotations

import logging
from typing import Dict, Iterable, Tuple
from uuid import UUID

from app.data.DTO import (
    TroubleshootingCatalog,
    TroubleshootingImportAction,
    TroubleshootingImportCause,
    TroubleshootingImportProblem,
    TroubleshootingImportResult,
)
from app.data.repositories import (
    ProblemCategoryRepository,
    ProblemCauseRepository,
    ProblemSolutionRepository,
)
from app.data.schemas.models import ProblemCategory, ProblemCause, ProblemSolution

logger = logging.getLogger(__name__)


class TroubleshootingImportService:
    """Populate problem taxonomy tables from structured troubleshooting graphs."""

    def __init__(
        self,
        *,
        category_repository: ProblemCategoryRepository,
        cause_repository: ProblemCauseRepository,
        solution_repository: ProblemSolutionRepository,
    ) -> None:
        self._category_repository = category_repository
        self._cause_repository = cause_repository
        self._solution_repository = solution_repository

    async def import_catalog(self, catalog: TroubleshootingCatalog) -> TroubleshootingImportResult:
        result = TroubleshootingImportResult()

        for problem_index, problem in enumerate(catalog.problems):
            category, created = await self._upsert_category(problem)
            if created:
                result.categories_created += 1
            else:
                result.categories_updated += 1

            for cause_index, cause in enumerate(problem.causes):
                cause_model, created_cause = await self._upsert_cause(category.id, cause, problem, cause_index)
                if created_cause:
                    result.causes_created += 1
                else:
                    result.causes_updated += 1

                sync_result = await self._sync_solutions(cause_model.id, cause.actions)
                result.solutions_created += sync_result["created"]
                result.solutions_updated += sync_result["updated"]
                result.solutions_removed += sync_result["removed"]

        return result

    async def _upsert_category(
        self,
        problem: TroubleshootingImportProblem,
    ) -> Tuple[ProblemCategory, bool]:
        existing = await self._category_repository.get_by_slug(problem.slug)
        if existing:
            updated = False
            if existing.name != problem.name:
                existing.name = problem.name
                updated = True
            description = problem.description or existing.description
            if description != existing.description:
                existing.description = description
                updated = True
            if updated:
                existing = await self._category_repository.update(existing)
            return existing, False

        category = ProblemCategory(
            slug=problem.slug,
            name=problem.name,
            description=problem.description,
        )
        created = await self._category_repository.create(category)
        return created, True

    async def _upsert_cause(
        self,
        category_id: UUID,
        cause: TroubleshootingImportCause,
        problem: TroubleshootingImportProblem,
        cause_index: int,
    ) -> Tuple[ProblemCause, bool]:
        existing = await self._cause_repository.get_by_category_and_slug(category_id, cause.slug)
        priority = self._resolve_priority(problem, cause, cause_index)
        detection_hints = list(cause.detection_hints or [])
        description = cause.description or cause.name

        if existing:
            updated = False
            if existing.name != cause.name:
                existing.name = cause.name
                updated = True
            if existing.description != description:
                existing.description = description
                updated = True
            if existing.default_priority != priority:
                existing.default_priority = priority
                updated = True
            if list(existing.detection_hints or []) != detection_hints:
                existing.detection_hints = detection_hints
                updated = True
            if updated:
                existing = await self._cause_repository.update(existing)
            return existing, False

        cause_model = ProblemCause(
            category_id=category_id,
            slug=cause.slug,
            name=cause.name,
            description=description,
            detection_hints=detection_hints,
            default_priority=priority,
        )
        created = await self._cause_repository.create(cause_model)
        return created, True

    async def _sync_solutions(
        self,
        cause_id: UUID,
        actions: Iterable[TroubleshootingImportAction],
    ) -> Dict[str, int]:
        summary = {"created": 0, "updated": 0, "removed": 0}
        actions = list(actions)
        existing_solutions = await self._solution_repository.list_by_cause(cause_id)
        existing_by_slug = {item.slug: item for item in existing_solutions}

        processed_slugs = set()
        for step_order, action in enumerate(actions, start=1):
            instructions = self._render_instructions(action.instructions)
            summary_text = action.summary or None
            requires_escalation = bool(action.requires_escalation)

            if action.slug in existing_by_slug:
                solution = existing_by_slug[action.slug]
                updated = False
                if solution.title != action.title:
                    solution.title = action.title
                    updated = True
                if solution.summary != summary_text:
                    solution.summary = summary_text
                    updated = True
                if solution.instructions != instructions:
                    solution.instructions = instructions
                    updated = True
                if solution.step_order != step_order:
                    solution.step_order = step_order
                    updated = True
                if bool(solution.requires_escalation) != requires_escalation:
                    solution.requires_escalation = requires_escalation
                    updated = True
                if updated:
                    await self._solution_repository.update(solution)
                    summary["updated"] += 1
                processed_slugs.add(action.slug)
                continue

            new_solution = ProblemSolution(
                cause_id=cause_id,
                slug=action.slug,
                title=action.title,
                summary=summary_text,
                instructions=instructions,
                step_order=step_order,
                requires_escalation=requires_escalation,
            )
            await self._solution_repository.create(new_solution)
            summary["created"] += 1
            processed_slugs.add(action.slug)

        for slug, solution in existing_by_slug.items():
            if slug in processed_slugs:
                continue
            try:
                removed = await self._solution_repository.delete_by_id(solution.id)
                if removed:
                    summary["removed"] += 1
            except Exception:  # noqa: BLE001
                logger.exception("Failed to remove solution %s for cause %s", slug, cause_id)

        return summary

    @staticmethod
    def _render_instructions(steps: Iterable[str]) -> str:
        formatted = []
        for raw in steps:
            text = (raw or "").strip()
            if not text:
                continue
            if text.startswith("-"):
                formatted.append(text)
            else:
                formatted.append(f"- {text}")
        return "\n".join(formatted) if formatted else ""

    @staticmethod
    def _resolve_priority(
        problem: TroubleshootingImportProblem,
        cause: TroubleshootingImportCause,
        cause_index: int,
    ) -> int:
        if cause.priority is not None:
            return int(cause.priority)

        severity_weight = {
            "info": 5,
            "low": 10,
            "medium": 20,
            "high": 30,
            "critical": 40,
        }.get(problem.severity, 10)
        return severity_weight + cause_index
