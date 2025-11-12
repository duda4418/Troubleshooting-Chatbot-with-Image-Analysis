from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.data.DTO import AssistantAnswer, GeneratedForm, GeneratedFormField, GeneratedFormOption
from app.services.form_submission_service import FormProcessingResult


@dataclass
class FollowUpHandlingDecision:
    handled: bool
    answer: Optional[AssistantAnswer] = None
    completed_status: Optional[str] = None


class FeedbackFlowService:
    """Manage follow-up form logic with limited deterministic responses."""

    def handle_form_submission(self, result: FormProcessingResult) -> FollowUpHandlingDecision:
        kind = (result.form_kind or "").lower()

        # Handle form dismissals - return empty handled response (no AI message)
        if result.skip_response:
            return FollowUpHandlingDecision(
                handled=True,
                answer=None,  # No message shown to user
                completed_status=None,
            )

        if kind == "escalation" and result.escalation_confirmed:
            return FollowUpHandlingDecision(
                handled=True,
                answer=self.build_escalation_confirmation(),
                completed_status="escalated",
            )

        if kind == "resolution_check":
            if result.resolution_confirmed is True:
                return FollowUpHandlingDecision(
                    handled=True,
                    answer=self.build_resolution_confirmation(),
                    completed_status="resolved",
                )
            if result.resolution_confirmed is False:
                return FollowUpHandlingDecision(handled=False)

        if kind == "feedback":
            if result.feedback_helped is True:
                return FollowUpHandlingDecision(
                    handled=True,
                    answer=self.build_resolution_request_from_feedback(),
                )
            if result.feedback_helped is False:
                return FollowUpHandlingDecision(handled=False)

        return FollowUpHandlingDecision(handled=False)

    @staticmethod
    def build_feedback_form() -> GeneratedForm:
        return GeneratedForm(
            title="Quick check-in",
            description="Let us know if the latest suggestion helped.",
            fields=[
                GeneratedFormField(
                    question="Did that help?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes"),
                        GeneratedFormOption(value="no", label="No"),
                    ],
                )
            ],
        )

    @staticmethod
    def build_resolution_form() -> GeneratedForm:
        return GeneratedForm(
            title="Confirm resolution",
            description="We want to be sure you're all set.",
            fields=[
                GeneratedFormField(
                    question="Did this fix the problem completely?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes, it's resolved"),
                        GeneratedFormOption(value="no", label="Not yet"),
                    ],
                )
            ],
        )

    @staticmethod
    def build_resolution_confirmation() -> AssistantAnswer:
        return AssistantAnswer(
            reply=(
                "Fantastic—that means everything is resolved. I'll close this conversation now. "
                "If anything else comes up, just start a new chat."
            ),
            suggested_actions=[],
            follow_up_form=None,
            confidence=None,
            metadata={"form_kind": "resolution_check"},
        )

    @staticmethod
    def build_resolution_request_from_feedback() -> AssistantAnswer:
        form = FeedbackFlowService.build_resolution_form()
        return AssistantAnswer(
            reply=(
                "Great news—glad that helped! Could you confirm everything is fully resolved "
                "using the quick check below?"
            ),
            suggested_actions=[],
            follow_up_form=form,
            confidence=None,
            metadata={
                "form_kind": "resolution_check",
                "follow_up_type": "resolution_check",
                "follow_up_reason": "Positive feedback checkpoint",
            },
        )

    @staticmethod
    def build_escalation_form() -> GeneratedForm:
        return GeneratedForm(
            title="Talk to a specialist",
            description="Would you like to hand this over to a human technician?",
            fields=[
                GeneratedFormField(
                    question="Do you want to escalate to a technician?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes, escalate it"),
                        GeneratedFormOption(value="no", label="Not yet"),
                    ],
                )
            ],
        )

    @staticmethod
    def build_escalation_confirmation() -> AssistantAnswer:
        return AssistantAnswer(
            reply=(
                "Understood—we'll hand this over to a specialist. You'll be contacted with next steps shortly."
            ),
            suggested_actions=[],
            follow_up_form=None,
            confidence=None,
            metadata={
                "form_kind": "escalation",
                "follow_up_type": "escalation",
                "follow_up_reason": "User confirmed escalation",
            },
        )
