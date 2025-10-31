from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Optional

from app.data.DTO import AssistantAnswer, GeneratedForm, GeneratedFormField, GeneratedFormOption
from app.data.schemas.models import ConversationMessage
from app.services.form_submission_service import FormProcessingResult


@dataclass
class FollowUpHandlingDecision:
    handled: bool
    answer: Optional[AssistantAnswer] = None
    completed_status: Optional[str] = None


class FeedbackFlowService:
    """Manage follow-up form logic and deterministic assistant replies."""

    def __init__(self, *, random_fn: Optional[Callable[[], float]] = None) -> None:
        self._random_fn = random_fn or random.random

    def handle_form_submission(self, result: FormProcessingResult) -> FollowUpHandlingDecision:
        kind = (result.form_kind or "").lower()

        if kind == "feedback" and result.feedback_helped is True:
            return FollowUpHandlingDecision(handled=True, answer=self._build_resolution_prompt())

        if kind == "resolution_check":
            if result.resolution_confirmed is True:
                return FollowUpHandlingDecision(
                    handled=True,
                    answer=self._build_resolution_confirmation(),
                    completed_status="resolved",
                )
            # If the user says the problem is not fixed yet, let the AI continue troubleshooting.
            if result.resolution_confirmed is False:
                return FollowUpHandlingDecision(handled=False)

        return FollowUpHandlingDecision(handled=False)

    def maybe_attach_feedback_form(
        self,
        answer: AssistantAnswer,
        *,
        prior_messages: List[ConversationMessage],
    ) -> None:
        if answer.follow_up_form is not None:
            return
        if not answer.suggested_actions:
            return
        if self._recent_form_kind(prior_messages, "feedback", limit=2):
            return
        if self._random_fn() > 0.5:
            return

        metadata = dict(answer.metadata or {})
        metadata["form_kind"] = "feedback"
        answer.metadata = metadata
        answer.follow_up_form = self._build_feedback_form()

    @staticmethod
    def _recent_form_kind(
        messages: List[ConversationMessage],
        kind: str,
        *,
        limit: int,
    ) -> bool:
        target = kind.lower()
        for index, message in enumerate(messages):
            if index >= limit:
                break
            metadata = message.message_metadata or {}
            if not isinstance(metadata, dict):
                continue
            value = metadata.get("form_kind")
            if isinstance(value, str) and value.strip().lower() == target:
                return True
            extra = metadata.get("extra")
            if isinstance(extra, dict):
                nested = extra.get("form_kind")
                if isinstance(nested, str) and nested.strip().lower() == target:
                    return True
        return False

    @staticmethod
    def _build_feedback_form() -> GeneratedForm:
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
    def _build_resolution_form() -> GeneratedForm:
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

    def _build_resolution_prompt(self) -> AssistantAnswer:
        return AssistantAnswer(
            reply="I'm glad that helped! Did it fix the issue completely?",
            suggested_actions=[],
            follow_up_form=self._build_resolution_form(),
            confidence=None,
            metadata={"form_kind": "resolution_check"},
        )

    @staticmethod
    def _build_resolution_confirmation() -> AssistantAnswer:
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
