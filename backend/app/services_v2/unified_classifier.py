"""Unified classifier that makes ALL decisions about user intent and next actions.

This service analyzes user input and conversation context to determine:
- What the user is trying to do (intent)
- What the assistant should do next (action)
- What problem/cause/solution applies
- What form to show (if any)
- Detailed reasoning for all decisions

The response generation service then just generates friendly text based on these decisions.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.data.DTO.simplified_flow_dto import (
    ClassificationRequest,
    ClassificationResult,
    NextAction,
    UserIntent,
)
from app.data.repositories import (
    ProblemCategoryRepository,
    ProblemCauseRepository,
    ProblemSolutionRepository,
    SessionProblemStateRepository,
)
from app.data.repositories.session_suggestion_repository import SessionSuggestionRepository
from app.services.utils.usage_metrics import extract_usage_details

logger = logging.getLogger(__name__)


class ClassifierPayload(BaseModel):
    """Structured output from AI classifier."""
    
    model_config = ConfigDict(extra="forbid")
    
    intent: str = Field(description="User intent: new_problem, clarifying, feedback_positive, feedback_negative, request_escalation, confirm_resolved, confirm_unresolved, out_of_scope, unintelligible, contradictory")
    next_action: str = Field(description="Next action: suggest_solution, ask_clarifying_question, present_resolution_form, present_escalation_form, present_feedback_form, close_resolved, escalate, decline_out_of_scope, request_clear_input")
    confidence: float = Field(ge=0, le=1, description="Confidence in classification")
    reasoning: str = Field(description="Detailed explanation of why this classification was made")
    
    # Problem details
    problem_category_slug: Optional[str] = None
    problem_cause_slug: Optional[str] = None
    solution_slug: Optional[str] = None
    
    # Clarification
    clarifying_question: Optional[str] = None
    
    # Issues
    contradiction_details: Optional[str] = None
    out_of_scope_reason: Optional[str] = None
    
    # Escalation
    should_escalate: bool = False
    escalation_reason: Optional[str] = None


class UnifiedClassifierService:
    """Unified classifier that makes all decisions."""
    
    def __init__(
        self,
        *,
        category_repository: ProblemCategoryRepository,
        cause_repository: ProblemCauseRepository,
        solution_repository: ProblemSolutionRepository,
        suggestion_repository: SessionSuggestionRepository,
        problem_state_repository: SessionProblemStateRepository,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._category_repo = category_repository
        self._cause_repo = cause_repository
        self._solution_repo = solution_repository
        self._suggestion_repo = suggestion_repository
        self._problem_state_repo = problem_state_repository
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_RESPONSE_MODEL
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None
    
    async def classify(self, request: ClassificationRequest) -> ClassificationResult:
        """Main classification method - makes all decisions."""
        
        if not self._client:
            raise RuntimeError("OpenAI API key not configured")
        
        # Load catalog and history
        catalog = await self._load_catalog()
        attempted_solutions = await self._get_attempted_solutions(request.session_id)
        
        # Detect existing problem state (must be done in async context before executor)
        existing_problem_slug = await self._detect_existing_problem(request.session_id)
        
        # Call AI to classify
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._invoke_openai(request, catalog, attempted_solutions, existing_problem_slug),
        )
        
        # Parse AI response
        payload = self._parse_response(response)
        
        # Enrich with database details
        result = await self._build_result(payload, catalog, attempted_solutions)
        
        # Persist problem state to database
        await self._persist_problem_state(request.session_id, result, catalog, payload.confidence)
        
        # Extract usage
        usage = extract_usage_details(
            response,
            default_model=self._model,
            request_type="unified_classification",
        )
        result.usage = usage
        
        return result
    
    def _invoke_openai(
        self,
        request: ClassificationRequest,
        catalog: Dict,
        attempted_solutions: List[str],
        existing_problem_slug: Optional[str] = None,
    ):
        """Call OpenAI to classify user input."""
        
        instructions = self._build_instructions()
        content = self._build_content(request, catalog, attempted_solutions, existing_problem_slug)
        
        # Print for debugging
        print("\n" + "=" * 80)
        print("CLASSIFIER INPUT")
        print("=" * 80)
        print(f"Session: {request.session_id}")
        print(f"User text: {request.user_text[:100] if request.user_text else '(empty)'}")
        print(f"Context events: {len(request.context.events)}")
        print(f"Attempted solutions: {attempted_solutions}")
        print("-" * 80)
        print("FULL CONTENT SENT TO AI:")
        print(content)
        print("=" * 80 + "\n")
        
        request_kwargs = {
            "model": self._model,
            "instructions": instructions,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": content}]}],
            "text_format": ClassifierPayload,
        }
        
        model_name = (self._model or "").lower()
        if "gpt-5" in model_name:
            request_kwargs["reasoning"] = {"effort": "medium"}
            request_kwargs["text"] = {"verbosity": "low"}
        else:
            request_kwargs["temperature"] = 0.1
        
        return self._client.responses.parse(**request_kwargs)
    
    def _build_instructions(self) -> str:
        """Build classifier instructions."""
        return """Dishwasher troubleshooting classifier. Determine: intent, next_action, problem details, reasoning.

INTENTS: new_problem, clarifying, feedback_positive, feedback_negative, request_escalation, confirm_resolved, confirm_unresolved, out_of_scope, unintelligible, contradictory

ACTIONS: suggest_solution, ask_clarifying_question, present_resolution_form, present_escalation_form, present_feedback_form, close_resolved, escalate, decline_out_of_scope, request_clear_input

KEY RULES:
• Empty text + image analysis = new_problem
• "escalate" first time = new_problem (try to help first)
• After 1-2 fails + user mentions escalate = present_escalation_form
• After 3+ fails = present_escalation_form
• "it worked" = present_resolution_form (confirm before closing)
• After resolution form "yes" = close_resolved
• After escalation form "yes" = escalate
• Check attempted_solutions - don't repeat
• Suggest ONE solution at a time
• After solution → present_feedback_form
• Use image keywords (cloudy/spots/streaks/residue/dirty) for problem category

REASONING: Explain intent, action choice, and evidence."""
    
    def _build_content(
        self,
        request: ClassificationRequest,
        catalog: Dict,
        attempted_solutions: List[str],
        existing_problem_slug: Optional[str] = None,
    ) -> str:
        """Build content for classifier."""
        
        lines = ["=== USER INPUT ==="]
        if request.user_text:
            lines.append(f"User text: {request.user_text}")
        else:
            lines.append("User text: (empty - only image sent)")
        
        lines.append("\n=== CONVERSATION CONTEXT ===")
        if request.context.events:
            for event in request.context.events[-10:]:
                lines.append(f"- {event}")
        else:
            lines.append("(No previous context)")
        
        lines.append("\n=== ATTEMPTED SOLUTIONS ===")
        if attempted_solutions:
            lines.append(f"Already tried: {', '.join(attempted_solutions)}")
        else:
            lines.append("(None yet)")
        
        # Smart catalog formatting - only show what's needed
        lines.append("\n=== AVAILABLE PROBLEMS & SOLUTIONS ===")
        lines.append(self._format_catalog_smart(catalog, existing_problem_slug))
        
        return "\n".join(lines)
    
    def _format_catalog_smart(self, catalog: Dict, existing_problem_slug: Optional[str]) -> str:
        """Smart catalog formatting - show less detail when no problem identified yet."""
        
        if existing_problem_slug:
            # Show full details for the identified problem only
            return self._format_catalog_focused(catalog, existing_problem_slug)
        else:
            # Just list categories briefly
            return self._format_catalog_categories_only(catalog)
    
    async def _detect_existing_problem(self, session_id: UUID) -> str | None:
        """Detect if conversation already has a CONFIRMED problem category from database.
        
        Queries the session_problem_state table to see if we've already identified
        a problem category in previous turns.
        """
        problem_state = await self._problem_state_repo.get_by_session_id(session_id)
        
        if problem_state and problem_state.category_id:
            # We have a confirmed category - fetch its slug
            category = await self._category_repo.get_by_id(problem_state.category_id)
            if category:
                return category.slug
        
        return None
    
    def _format_catalog_categories_only(self, catalog: Dict) -> str:
        """Format catalog showing only category names."""
        lines = ["Categories (brief overview):"]
        for cat_slug, cat_data in catalog.items():
            lines.append(f"  • {cat_slug}: {cat_data['name']}")
        lines.append("\n(Full details will be provided once you identify the problem category)")
        return "\n".join(lines)
    
    def _format_catalog_focused(self, catalog: Dict, problem_category: str) -> str:
        """Format catalog showing full details for ONE category only."""
        if problem_category not in catalog:
            # Fallback to categories only
            return self._format_catalog_categories_only(catalog)
        
        lines = [f"Details for {problem_category}:"]
        cat_data = catalog[problem_category]
        
        for cause in cat_data.get("causes", []):
            lines.append(f"\n  Cause: {cause['slug']} - {cause['name']}")
            for sol in cause.get("solutions", []):
                lines.append(f"    • {sol['slug']}: {sol['title']}")
        
        return "\n".join(lines)
    
    async def _load_catalog(self) -> Dict:
        """Load full problem catalog."""
        categories = await self._category_repo.list_all()
        catalog = {}
        
        for category in categories:
            causes = await self._cause_repo.list_by_category(category.id)
            cat_data = {
                "id": category.id,
                "name": category.name,
                "causes": [],
            }
            
            for cause in causes:
                solutions = await self._solution_repo.list_by_cause(cause.id)
                cause_data = {
                    "id": cause.id,
                    "slug": cause.slug,
                    "name": cause.name,
                    "solutions": [
                        {
                            "id": sol.id,
                            "slug": sol.slug,
                            "title": sol.title,
                            "instructions": sol.instructions,
                        }
                        for sol in solutions
                    ],
                }
                cat_data["causes"].append(cause_data)
            
            catalog[category.slug] = cat_data
        
        return catalog
    
    async def _get_attempted_solutions(self, session_id: UUID) -> List[str]:
        """Get list of solution slugs already tried in this session."""
        suggestions = await self._suggestion_repo.list_by_session(session_id)
        
        # Get solution IDs from suggestions
        solution_ids = [s.solution_id for s in suggestions]
        if not solution_ids:
            return []
        
        # Fetch solution records to get slugs
        solutions = await self._solution_repo.list_by_ids(solution_ids)
        return [sol.slug for sol in solutions]
    
    def _parse_response(self, response) -> ClassifierPayload:
        """Parse AI response."""
        payload = getattr(response, "output_parsed", None)
        if not isinstance(payload, ClassifierPayload):
            raise RuntimeError("Invalid classifier response format")
        
        # Print the AI output
        print("\n" + "=" * 80)
        print("CLASSIFIER OUTPUT")
        print("=" * 80)
        print(f"Intent: {payload.intent}")
        print(f"Next Action: {payload.next_action}")
        print(f"Confidence: {payload.confidence}")
        if payload.problem_category_slug:
            print(f"Category: {payload.problem_category_slug}")
        if payload.problem_cause_slug:
            print(f"Cause: {payload.problem_cause_slug}")
        if payload.solution_slug:
            print(f"Solution: {payload.solution_slug}")
        if payload.clarifying_question:
            print(f"Clarifying Question: {payload.clarifying_question[:100]}")
        if payload.should_escalate:
            print(f"Should Escalate: {payload.should_escalate}")
            if payload.escalation_reason:
                print(f"Escalation Reason: {payload.escalation_reason[:100]}")
        print("-" * 80)
        print("REASONING:")
        print(payload.reasoning)
        print("=" * 80 + "\n")
        
        return payload
    
    async def _build_result(
        self,
        payload: ClassifierPayload,
        catalog: Dict,
        attempted_solutions: List[str],
    ) -> ClassificationResult:
        """Build final classification result with enriched data."""
        
        result = ClassificationResult(
            intent=UserIntent(payload.intent),
            next_action=NextAction(payload.next_action),
            confidence=payload.confidence,
            reasoning=payload.reasoning,
            clarifying_question=payload.clarifying_question,
            contradiction_details=payload.contradiction_details,
            out_of_scope_reason=payload.out_of_scope_reason,
            should_escalate=payload.should_escalate,
            escalation_reason=payload.escalation_reason,
            attempted_solutions=attempted_solutions,
        )
        
        # Enrich with database details
        if payload.problem_category_slug:
            if payload.problem_category_slug in catalog:
                cat_data = catalog[payload.problem_category_slug]
                result.problem_category_slug = payload.problem_category_slug
                result.problem_category_name = cat_data["name"]
                
                if payload.problem_cause_slug:
                    for cause in cat_data.get("causes", []):
                        if cause["slug"] == payload.problem_cause_slug:
                            result.problem_cause_slug = cause["slug"]
                            result.problem_cause_name = cause["name"]
                            result.attempted_causes = [cause["slug"]]  # TODO: track better
                            
                            if payload.solution_slug:
                                for sol in cause.get("solutions", []):
                                    if sol["slug"] == payload.solution_slug:
                                        result.solution_slug = sol["slug"]
                                        result.solution_title = sol["title"]
                                        result.solution_steps = sol["instructions"]
                                        result.solution_already_tried = sol["slug"] in attempted_solutions
                                        break
                            break
        
        return result
    
    async def _persist_problem_state(
        self,
        session_id: UUID,
        result: ClassificationResult,
        catalog: Dict,
        confidence: float,
    ) -> None:
        """Persist the identified problem category and cause to the database."""
        
        # Only persist if we have a problem category
        if not result.problem_category_slug:
            return
        
        # Find the category ID
        category_id = None
        cause_id = None
        
        if result.problem_category_slug in catalog:
            category_id = catalog[result.problem_category_slug]["id"]
            
            # Find cause ID if we have one
            if result.problem_cause_slug:
                for cause in catalog[result.problem_category_slug].get("causes", []):
                    if cause["slug"] == result.problem_cause_slug:
                        cause_id = cause["id"]
                        break
        
        # Update the database
        if category_id:
            await self._problem_state_repo.upsert(
                session_id,
                category_id=category_id,
                cause_id=cause_id,
                classification_confidence=confidence,
                classification_source="ai_classification",
                manual_override=False,
            )

