"""Refactored DTOs for simplified classification and response flow.

New Architecture:
- Classification: Does ALL decision-making (intent, actions, forms, solutions)
- Response: Just generates friendly text based on classification decisions
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.data.DTO.conversation_context_dto import ConversationAIContext
from app.data.DTO.usage_dto import ModelUsageDetails


# ============================================================================
# ENUMS - User Intent & Next Actions
# ============================================================================

class UserIntent(str, Enum):
    """What the user is trying to do."""
    NEW_PROBLEM = "new_problem"  # Reporting a new dishwasher issue
    CLARIFYING = "clarifying"  # Answering a previous question
    FEEDBACK_POSITIVE = "feedback_positive"  # Solution worked/helped
    FEEDBACK_NEGATIVE = "feedback_negative"  # Solution didn't work
    REQUEST_ESCALATION = "request_escalation"  # Wants human help
    CONFIRM_RESOLVED = "confirm_resolved"  # Says problem is fixed
    CONFIRM_UNRESOLVED = "confirm_unresolved"  # Says problem still exists
    OUT_OF_SCOPE = "out_of_scope"  # Not dishwasher-related
    UNINTELLIGIBLE = "unintelligible"  # Can't understand input
    CONTRADICTORY = "contradictory"  # Text conflicts with image/context


class NextAction(str, Enum):
    """What the assistant should do next."""
    SUGGEST_SOLUTION = "suggest_solution"  # Provide a fix to try
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question"  # Need more info
    PRESENT_RESOLUTION_FORM = "present_resolution_form"  # Check if resolved
    PRESENT_ESCALATION_FORM = "present_escalation_form"  # Offer escalation
    PRESENT_FEEDBACK_FORM = "present_feedback_form"  # Ask if suggestion helped
    CLOSE_RESOLVED = "close_resolved"  # Mark as resolved
    ESCALATE = "escalate"  # Hand off to human
    DECLINE_OUT_OF_SCOPE = "decline_out_of_scope"  # Not our domain
    REQUEST_CLEAR_INPUT = "request_clear_input"  # Ask for clearer description


# ============================================================================
# CLASSIFICATION REQUEST & RESULT
# ============================================================================

class ClassificationRequest(BaseModel):
    """Input to classification service."""
    session_id: UUID
    user_text: str
    locale: str
    context: ConversationAIContext


class ClassificationResult(BaseModel):
    """Complete classification with all decisions made."""
    
    # === Core Intent & Action ===
    intent: UserIntent
    next_action: NextAction
    confidence: float
    
    # === Reasoning (for response generation) ===
    reasoning: str  # Why this classification was made
    
    # === Problem Identification ===
    problem_category_slug: Optional[str] = None
    problem_category_name: Optional[str] = None
    problem_cause_slug: Optional[str] = None
    problem_cause_name: Optional[str] = None
    
    # === Solution to Suggest ===
    solution_slug: Optional[str] = None
    solution_title: Optional[str] = None
    solution_summary: Optional[str] = None  # Brief explanation of why/what
    solution_steps: Optional[str] = None  # Full instructions
    solution_already_tried: bool = False
    
    # === Clarification ===
    clarifying_question: Optional[str] = None
    
    # === Context Issues ===
    contradiction_details: Optional[str] = None  # What's contradictory
    out_of_scope_reason: Optional[str] = None
    
    # === Escalation ===
    should_escalate: bool = False
    escalation_reason: Optional[str] = None
    
    # === Conversation State ===
    attempted_solutions: List[str] = Field(default_factory=list)  # Solution slugs tried
    attempted_causes: List[str] = Field(default_factory=list)  # Cause slugs explored
    
    # === Metadata ===
    usage: Optional[ModelUsageDetails] = None


# ============================================================================
# RESPONSE GENERATION REQUEST & RESULT
# ============================================================================

class ResponseRequest(BaseModel):
    """Input to response generation service - just needs classification decisions."""
    classification: ClassificationResult
    locale: str


class ResponseResult(BaseModel):
    """Generated response text only - no decisions."""
    reply: str  # User-facing message
    suggested_action: Optional[str] = None  # Single action summary for UI
    usage: Optional[ModelUsageDetails] = None

