from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, List, Optional, Literal
from uuid import UUID

from openai import OpenAI  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field  # type: ignore[import-untyped]

from app.core.config import settings
from app.data.DTO.troubleshooting_dto import (
    ProblemCategoryView,
    ProblemCauseView,
    ProblemClassificationRequest,
    ProblemClassificationResult,
    ProblemRequestType,
)
from app.data.repositories import ProblemCategoryRepository, ProblemCauseRepository
from app.data.repositories.session_problem_state_repository import SessionProblemStateRepository
from app.data.schemas.models import ProblemCategory, ProblemCause
from app.services.utils.usage_metrics import extract_usage_details

logger = logging.getLogger(__name__)


class ClassificationPayload(BaseModel):
    """Structured schema returned by the Responses API."""

    model_config = ConfigDict(extra="forbid")

    category_slug: Optional[str] = Field(
        default=None,
        description="Slug of the detected problem category. Use null if unsure.",
    )
    cause_slug: Optional[str] = Field(
        default=None,
        description="Slug of the detected cause within the chosen category. Use null when the cause is not yet confirmed.",
    )
    next_questions: List[str] = Field(
        default_factory=list,
        description="Up to two short clarifying questions to narrow down the cause.",
    )
    confidence: Optional[float] = Field(
        default=None, ge=0, le=1,
        description="Classifier confidence in the selected category/cause.",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Short explanation of why the category/cause was selected.",
    )
    escalate: bool = Field(
        default=False,
        description="True when human escalation is recommended immediately.",
    )
    escalate_reason: Optional[str] = Field(
        default=None,
        description="One sentence explaining why escalation is needed.",
    )
    needs_more_info: bool = Field(
        default=False,
        description="Set true when more details are required before suggesting actions.",
    )
    request_type: Optional[Literal["troubleshoot", "resolution_check", "escalation", "clarification"]] = Field(
        default=None,
        description="High-level intent inferred from the latest user input. Defaults to 'troubleshoot' when not specified.",
    )


class _CatalogEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    category: ProblemCategory
    causes: List[ProblemCause]


class ProblemClassifierService:
    """Classifier that maps user issues to structured troubleshooting categories/causes."""

    def __init__(
        self,
        *,
        category_repository: ProblemCategoryRepository,
        cause_repository: ProblemCauseRepository,
        session_state_repository: SessionProblemStateRepository,
        api_key: Optional[str] = None,
        response_model: Optional[str] = None,
    ) -> None:
        self._category_repository = category_repository
        self._cause_repository = cause_repository
        self._session_state_repository = session_state_repository
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = response_model or settings.OPENAI_RESPONSE_MODEL
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

    async def classify(self, request: ProblemClassificationRequest) -> ProblemClassificationResult:
        if not self._client:
            raise RuntimeError("OpenAI API key is not configured")

        catalog = await self._load_catalog()
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._invoke_openai(request, catalog),
        )
        payload = self._parse_response(response)
        result = self._map_result(payload, catalog)
        
        # Extract usage details for tracking
        usage_details = extract_usage_details(
            response,
            default_model=self._model,
            request_type="classification",
        )
        result.usage = usage_details
        
        await self._persist_session_state(request.session_id, result)
        return result

    async def _load_catalog(self) -> List[_CatalogEntry]:
        categories = await self._category_repository.list_all()
        catalog: List[_CatalogEntry] = []
        for category in categories:
            causes = await self._cause_repository.list_by_category(category.id)
            catalog.append(_CatalogEntry(category=category, causes=causes))
        return catalog

    def _invoke_openai(self, request: ProblemClassificationRequest, catalog: List[_CatalogEntry]):
        instructions = (
            "You are a practical dishwasher troubleshooting classifier. "
            "Map the user's problem to a category and cause from the catalog. "
            "\n"
            "Input validation - CHECK FIRST:\n"
            "- If user input is gibberish, random words, or unrelated to dishwashers → request_type='clarification', ask for proper problem description\n"
            "- If user text contradicts image analysis (e.g., says 'dirty' but image shows clean dishes) → request_type='clarification', ask user to clarify the mismatch\n"
            "- If user input is too vague/ambiguous to determine ANY category → request_type='clarification'\n"
            "- For clarification cases: leave category_slug and cause_slug null, provide ONE helpful question\n"
            "\n"
            "Cause selection strategy (ONLY after input is valid):\n"
            "- If symptoms match a cause (even partially), SELECT that cause_slug and set confidence based on certainty\n"
            "- PREFER selecting the most likely cause over asking questions\n"
            "- Only leave cause_slug null if truly unable to determine any likely cause\n"
            "- The system will try one solution at a time - if it doesn't work, we'll try another cause\n"
            "\n"
            "Clarifying questions:\n"
            "- AVOID asking questions unless absolutely necessary\n"
            "- Only ask when you literally cannot determine ANY likely cause\n"
            "- Maximum 1 question, not 2\n"
            "- Never ask questions already answered in conversation context\n"
            "\n"
            "Request types:\n"
            "- troubleshoot: actively diagnosing (default for clear problems)\n"
            "- resolution_check: user indicates problem seems resolved\n"
            "- escalation: user explicitly wants human help\n"
            "- clarification: input is gibberish/contradictory/too vague/unrelated\n"
            "\n"
            "Escalation: Only for hardware failures, no viable catalog path, or explicit user request.")

        catalog_block = self._build_catalog_block(catalog)
        context_block = self._build_context_block(request)
        input_blocks = [
            {"type": "input_text", "text": context_block},
            {"type": "input_text", "text": catalog_block},
        ]
        self._log_prompt_preview(request, instructions, input_blocks)

        request_kwargs = {
            "model": self._model,
            "instructions": instructions,
            "input": [{"role": "user", "content": input_blocks}],
            "text_format": ClassificationPayload,
        }

        model_name = (self._model or "").lower()
        if "gpt-5" in model_name:
            request_kwargs["reasoning"] = {"effort": "minimal"}
            request_kwargs["text"] = {"verbosity": "low"}
        else:
            request_kwargs["temperature"] = 0.0

        return self._client.responses.parse(**request_kwargs)

    def _parse_response(self, response) -> ClassificationPayload:
        payload = getattr(response, "output_parsed", None)
        if not isinstance(payload, ClassificationPayload):
            message = "OpenAI classifier response missing structured payload"
            logger.error(message)
            raise RuntimeError(message)
        return payload

    def _map_result(self, payload: ClassificationPayload, catalog: List[_CatalogEntry]) -> ProblemClassificationResult:
        category_lookup: Dict[str, ProblemCategory] = {
            entry.category.slug: entry.category for entry in catalog
        }
        category_obj = category_lookup.get((payload.category_slug or "").strip()) if payload.category_slug else None

        cause_lookup: Dict[str, ProblemCause] = {}
        if category_obj and payload.cause_slug:
            for entry in catalog:
                if entry.category.id == category_obj.id:
                    cause_lookup = {cause.slug: cause for cause in entry.causes}
                    break
        cause_obj = cause_lookup.get((payload.cause_slug or "").strip()) if cause_lookup else None

        category_view = (
            ProblemCategoryView(
                id=category_obj.id,
                slug=category_obj.slug,
                name=category_obj.name,
                description=category_obj.description,
            )
            if category_obj
            else None
        )
        cause_view = (
            ProblemCauseView(
                id=cause_obj.id,
                category_id=cause_obj.category_id,
                slug=cause_obj.slug,
                name=cause_obj.name,
                description=cause_obj.description,
            )
            if cause_obj
            else None
        )

        request_type = None
        if payload.request_type:
            try:
                request_type = ProblemRequestType(payload.request_type)
            except ValueError:
                request_type = None

        return ProblemClassificationResult(
            category=category_view,
            cause=cause_view,
            confidence=payload.confidence,
            rationale=payload.rationale,
            escalate=payload.escalate,
            escalate_reason=payload.escalate_reason,
            needs_more_info=payload.needs_more_info or bool(payload.next_questions),
            next_questions=self._select_follow_up_questions(payload.next_questions),
            request_type=request_type,
        )

    async def _persist_session_state(self, session_id: UUID, result: ProblemClassificationResult) -> None:
        try:
            await self._session_state_repository.upsert(
                session_id=session_id,
                category_id=result.category.id if result.category else None,
                cause_id=result.cause.id if result.cause else None,
                classification_confidence=result.confidence,
                classification_source="openai_responses_v1",
                manual_override=False,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist session problem state for %s", session_id)

    @staticmethod
    def _build_catalog_block(catalog: Iterable[_CatalogEntry]) -> str:
        lines: List[str] = [
            "Troubleshooting catalog overview",
            "Use the slug values when populating category_slug and cause_slug.",
        ]
        for entry in catalog:
            category = entry.category
            lines.append(f"- {category.slug}: {category.name}")
            if not entry.causes:
                continue
            cause_summaries: List[str] = []
            for cause in entry.causes:
                hints = cause.detection_hints or []
                hint = "; ".join(hints)
                if not hint and cause.description:
                    summary = cause.description.split(".")[0].strip()
                    hint = summary[:80] + ("..." if len(summary) > 80 else "") if summary else ""
                if hint:
                    cause_summaries.append(f"{cause.slug} ({hint})")
                else:
                    cause_summaries.append(cause.slug)
            if cause_summaries:
                lines.append("  Causes: " + ", ".join(cause_summaries))
        return "\n".join(lines)

    @staticmethod
    def _build_context_block(request: ProblemClassificationRequest) -> str:
        lines: List[str] = ["User report"]
        if request.user_text:
            lines.append(request.user_text.strip())
        else:
            lines.append("<no textual input provided>")

        if request.context.events:
            lines.append("\nRecent conversation events:")
            for event in request.context.events[-8:]:
                lines.append(f"- {event}")

        return "\n".join(lines)

    def _log_prompt_preview(self, request: ProblemClassificationRequest, instructions: str, content_blocks: List[dict]) -> None:
        header = f"Classifier prompt preview (session {request.session_id})"
        lines: List[str] = ["=== Instructions ===", instructions.strip(), "=== User Content Blocks ==="]
        for index, block in enumerate(content_blocks, start=1):
            block_type = block.get("type", "unknown")
            lines.append(f"[Block {index} | type={block_type}]")
            if block_type == "input_text":
                lines.append(block.get("text", ""))
            else:
                lines.append(repr(block))
        preview = "\n".join(lines)
        print(f"{header}\n{preview}")
        logger.info("%s\n%s", header, preview)

    @staticmethod
    def _select_follow_up_questions(raw_questions: Iterable[str]) -> List[str]:
        questions: List[str] = []
        seen: set[str] = set()
        for item in raw_questions or []:
            if not item:
                continue
            text = item.strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            questions.append(text)
            if len(questions) >= 2:
                break
        return questions