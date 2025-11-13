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
    reasoning: str = Field(
        description="Detailed explanation of why this classification was made",
        max_length=500
    )
    
    # Problem details
    problem_category_slug: Optional[str] = None
    problem_cause_slug: Optional[str] = None
    solution_slug: Optional[str] = None
    
    # Clarification
    clarifying_question: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Concise clarifying question (1-2 sentences max)"
    )
    
    # Issues
    contradiction_details: Optional[str] = Field(default=None, max_length=300)
    out_of_scope_reason: Optional[str] = Field(default=None, max_length=300)
    
    # Escalation
    should_escalate: bool = False
    escalation_reason: Optional[str] = Field(default=None, max_length=300)


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
        return """You are a dishwasher troubleshooting assistant. Analyze the situation and determine the next action.

INTENTS:
• new_problem - User reports an issue or sends image of problem
• clarifying - User provides more details about current problem
• feedback_positive - Solution worked or image shows improvement
• feedback_negative - Solution didn't work
• request_escalation - User wants human help
• confirm_resolved - User confirms problem is fixed
• out_of_scope - Not dishwasher related
• unintelligible - Can't understand input

ACTIONS:
• suggest_solution - Recommend a specific solution to try
• ask_clarifying_question - Need more information before proceeding
• present_resolution_form - Ask if problem is resolved
• present_escalation_form - Offer escalation to human support (use when user requests escalation OR after trying all solutions)
• close_resolved - Close session as resolved (only after user confirms via form)
• escalate - Close and transfer to human support (only after user confirms via form)
• decline_out_of_scope - Politely decline non-dishwasher issues

WORKFLOW:
1. NO problem selected yet → Use image analysis + user text to identify problem CATEGORY
   - Set next_action: ask_clarifying_question
   - Wait for confirmation before suggesting solutions
   - DO NOT suggest solutions yet

2. Problem CONFIRMED → Now you see causes/solutions for that category
   - Identify most likely cause based on symptoms
   - Set action: suggest_solution
   - Don't repeat already attempted solutions

3. After suggestion → Evaluate outcome
   - Image analysis indicates resolution → intent: feedback_positive, action: present_resolution_form
   - User reports success → intent: feedback_positive, action: present_resolution_form
   - User reports failure → intent: feedback_negative, action: suggest_solution (try next)
   - After proposed all suggestions and no improvement and no other leads → action: present_escalation_form OR switch to the next likely cause

CATEGORY SWITCHING:
• You CAN switch to a different problem category anytime
• If user repeatedly clarifies different symptoms → Switch category by returning new category slug
• If image shows different problem than selected category → Switch categories
• System automatically updates to new category when you return different slug

RESOLUTION DETECTION (PRIORITY):
• If solution was suggested AND new image shows improvement → intent: feedback_positive, action: present_resolution_form
• Image changing from "issue" to "clean" after solution = likely resolved
• Don't treat improvement as contradictory - treat as positive outcome
• Present resolution form to confirm, keep problem category for statistics

CLARIFYING QUESTIONS:
• Limit clarifying questions - prefer suggesting actionable solutions
• If user indicates no behavior change, assume machine-related cause
• Move to solution quickly rather than gathering excessive details

CRITICAL RULES:
• Prioritize IMAGE ANALYSIS over user text for problem identification
• If image contradicts user text, set intent: contradictory
• Don't use contradictory intent when image shows improvement after solution
• Suggest only ONE solution at a time
• Don't repeat already attempted solutions
• Stay on same cause if user confirms it
• Switch cause only if: solution failed OR user denies the cause
• Detect resolution from context changes, not just explicit user confirmation
• Maintain problem category throughout conversation for tracking, unless another problem detected
• When user requests escalation, use present_escalation_form to show the form first. Only use escalate action after form submission.
• When escalating, try to convince the user to try more troubleshooting, but still provide the form and acknowledge their request.

REASONING: Explain intent, action choice, and evidence."""
    
    def _build_content(
        self,
        request: ClassificationRequest,
        catalog: Dict,
        attempted_solutions: List[str],
        existing_problem_slug: Optional[str] = None,
    ) -> str:
        """Build content for classifier."""
        
        lines = []
        
        # User input
        if request.user_text:
            lines.append(f"User: {request.user_text}")
        else:
            lines.append("User: (sent image only)")
        
        # Recent conversation context (full history)
        if request.context.events:
            lines.append("\nRecent conversation:")
            for event in request.context.events:
                lines.append(f"  {event}")
        
        # Attempted solutions
        if attempted_solutions:
            lines.append(f"\nAlready tried: {', '.join(attempted_solutions)}")
        
        # Catalog
        lines.append("\n" + self._format_catalog_smart(catalog, existing_problem_slug))
        
        return "\n".join(lines)
    
    def _format_catalog_smart(self, catalog: Dict, existing_problem_slug: Optional[str]) -> str:
        """Smart catalog formatting - show category list, then focused details if problem selected."""
        
        # Always show category list
        lines = ["Problem categories:"]
        for cat_slug, cat_data in catalog.items():
            lines.append(f"  • {cat_slug}: {cat_data['name']}")
        
        if existing_problem_slug:
            # Show causes/solutions for selected category
            lines.append(f"\nSelected: {existing_problem_slug}")
            lines.append(self._format_catalog_focused(catalog, existing_problem_slug))
        else:
            # No category selected yet - identify first, then get details
            lines.append("\n→ Identify the problem category, then ask for confirmation.")
        
        return "\n".join(lines)
    
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
    
    def _format_catalog_focused(self, catalog: Dict, problem_category: str) -> str:
        """Format causes and solutions for selected category."""
        if problem_category not in catalog:
            return f"Category '{problem_category}' not found."
        
        cat_data = catalog[problem_category]
        lines = []
        
        for cause in cat_data.get("causes", []):
            lines.append(f"\nCause: {cause['name']}")
            for sol in cause.get("solutions", []):
                lines.append(f"  → {sol['slug']}: {sol['title']}")
        
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
        logger.info(f"Found {len(suggestions)} suggestion records in database for session {session_id}")
        
        # Get solution IDs from suggestions
        solution_ids = [s.solution_id for s in suggestions]
        if not solution_ids:
            logger.info("No suggestions found, returning empty list")
            return []
        
        # Fetch solution records to get slugs
        solutions = await self._solution_repo.list_by_ids(solution_ids)
        slugs = [sol.slug for sol in solutions]
        logger.info(f"Retrieved solution slugs: {slugs}")
        return slugs
    
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

