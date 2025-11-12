"""Simplified response generator that just creates friendly text.

This service receives classification decisions and generates user-friendly responses.
It does NOT make decisions - all decision-making happens in the classifier.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.data.DTO.simplified_flow_dto import (
    NextAction,
    ResponseRequest,
    ResponseResult,
    UserIntent,
)
from app.services.utils.usage_metrics import extract_usage_details

logger = logging.getLogger(__name__)


class ResponsePayload(BaseModel):
    """AI-generated response text."""
    reply: str = Field(description="User-facing response message. Friendly, concise, 2-3 sentences max.")
    suggested_action: Optional[str] = Field(
        default=None,
        description="Short USER action (what the USER should do). Example: 'Lower rinse aid to level 1'. NOT what the AI does. Null if no user action needed."
    )


class UnifiedResponseService:
    """Generates friendly responses based on classification decisions."""
    
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_RESPONSE_MODEL
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None
    
    async def generate(self, request: ResponseRequest) -> ResponseResult:
        """Generate response text based on classification."""
        
        if not self._client:
            raise RuntimeError("OpenAI API key not configured")
        
        logger.info(f"[UnifiedResponse] Generating for action: {request.classification.next_action.value}")
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._invoke_openai(request),
        )
        
        payload = self._parse_response(response)
        
        usage = extract_usage_details(
            response,
            default_model=self._model,
            request_type="unified_response",
        )
        
        return ResponseResult(
            reply=payload.reply,
            suggested_action=payload.suggested_action,
            usage=usage,
        )
    
    def _invoke_openai(self, request: ResponseRequest):
        """Call OpenAI to generate response text."""
        
        instructions = self._build_instructions(request)
        content = self._build_content(request)
        
        request_kwargs = {
            "model": self._model,
            "instructions": instructions,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": content}]}],
            "text_format": ResponsePayload,
        }
        
        model_name = (self._model or "").lower()
        if "gpt-5" in model_name:
            request_kwargs["reasoning"] = {"effort": "minimal"}
            request_kwargs["text"] = {"verbosity": "low"}
        else:
            request_kwargs["temperature"] = 0.3
        
        return self._client.responses.parse(**request_kwargs)
    
    def _build_instructions(self, request: ResponseRequest) -> str:
        """Build response generation instructions based on next action."""
        
        classification = request.classification
        action = classification.next_action
        
        base_instructions = """You are a friendly dishwasher troubleshooting assistant.
Generate a conversational response based on the classification decisions provided.

IMPORTANT RULES:
- Keep responses SHORT: 2-3 sentences maximum
- Be friendly and natural, not robotic
- Vary your language - don't repeat the same phrases
- Always explain WHY before WHAT when suggesting solutions
- Only include information relevant to the next_action

SUGGESTED ACTIONS:
- suggested_action should be USER-FACING (what the user should do)
- Examples: "Lower rinse aid to level 1", "Run empty hot cycle with vinegar", "Check spray arms"
- NOT AI actions like "Ask for details" or "Present form"
- Set to null if there's no concrete action for the user to take

"""
        
        if action == NextAction.SUGGEST_SOLUTION:
            return base_instructions + """
TASK: Suggest a solution to try

Structure:
1. First sentence: Briefly explain what you think the problem/cause is
2. Second sentence: Suggest ONE clear action to try

Example: "This looks like rinse aid overdosing, which leaves waxy residue on glass. Try lowering the rinse-aid setting to level 1."

Use the solution_title and solution_steps from classification.
"""
        
        elif action == NextAction.ASK_CLARIFYING_QUESTION:
            return base_instructions + """
TASK: Ask for clarification

Use the clarifying_question from classification.
Make it friendly and conversational.
Explain briefly why you're asking if helpful.

NOTE: Set suggested_action to null (we're asking a question, not suggesting an action).
"""
        
        elif action == NextAction.REQUEST_CLEAR_INPUT:
            return base_instructions + """
TASK: Request clearer input

The input was unintelligible or contradictory.
Use the reasoning and contradiction_details to explain what's unclear.
Ask the user to provide clearer information.
"""
        
        elif action == NextAction.DECLINE_OUT_OF_SCOPE:
            return base_instructions + """
TASK: Politely decline out-of-scope question

Explain that you're specifically for dishwasher troubleshooting.
Invite them to ask dishwasher-related questions.
"""
        
        elif action == NextAction.PRESENT_RESOLUTION_FORM:
            return base_instructions + """
TASK: Lead into resolution check

User indicated the problem might be fixed.
Express that you're glad to hear it.
Mention that a confirmation form will appear.
"""
        
        elif action == NextAction.PRESENT_ESCALATION_FORM:
            return base_instructions + """
TASK: Lead into escalation offer

Explain that you've tried available solutions or the issue requires human help.
Mention that an escalation form will appear.
"""
        
        elif action == NextAction.PRESENT_FEEDBACK_FORM:
            return base_instructions + """
TASK: Lead into feedback form

You just suggested a solution.
Keep it brief - the feedback form will appear asking if it helped.
"""
        
        elif action == NextAction.CLOSE_RESOLVED:
            return base_instructions + """
TASK: Confirm resolution and close

Congratulate the user on resolving the issue.
Let them know they can start a new conversation if needed.
"""
        
        elif action == NextAction.ESCALATE:
            return base_instructions + """
TASK: Confirm escalation

Let the user know their issue is being handed to a specialist.
Mention they'll be contacted with next steps.
"""
        
        return base_instructions
    
    def _build_content(self, request: ResponseRequest) -> str:
        """Build content for response generation."""
        
        classification = request.classification
        
        lines = [
            f"Intent: {classification.intent.value}",
            f"Next Action: {classification.next_action.value}",
            f"Confidence: {classification.confidence}",
            f"Reasoning: {classification.reasoning}",
        ]
        
        if classification.problem_cause_name:
            lines.append(f"Problem Cause: {classification.problem_cause_name}")
        
        if classification.solution_title:
            lines.append(f"Solution: {classification.solution_title}")
            if classification.solution_steps:
                # Only show first step/instruction
                first_step = classification.solution_steps.split('\n')[0] if classification.solution_steps else ""
                lines.append(f"First Step: {first_step}")
        
        if classification.clarifying_question:
            lines.append(f"Clarifying Question: {classification.clarifying_question}")
        
        if classification.contradiction_details:
            lines.append(f"Contradiction: {classification.contradiction_details}")
        
        if classification.out_of_scope_reason:
            lines.append(f"Out of Scope: {classification.out_of_scope_reason}")
        
        if classification.escalation_reason:
            lines.append(f"Escalation Reason: {classification.escalation_reason}")
        
        return "\n".join(lines)
    
    def _parse_response(self, response) -> ResponsePayload:
        """Parse AI response."""
        payload = getattr(response, "output_parsed", None)
        if not isinstance(payload, ResponsePayload):
            raise RuntimeError("Invalid response format")
        return payload
