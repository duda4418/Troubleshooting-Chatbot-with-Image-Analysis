from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from app.data.repositories import ConversationMessageRepository

logger = logging.getLogger(__name__)


@dataclass
class FormProcessingResult:
    summary: Optional[str]
    skip_response: bool
    form_kind: Optional[str]
    escalation_confirmed: bool
    metadata_updates: Dict[str, Any]
    resolved: bool
    feedback_helped: Optional[bool] = None
    resolution_confirmed: Optional[bool] = None


class FormSubmissionService:
    """Interpret follow-up form submissions coming from the frontend."""

    def __init__(self, message_repository: ConversationMessageRepository) -> None:
        self._message_repository = message_repository

    async def process(self, session_id: UUID, metadata: Dict[str, Any]) -> FormProcessingResult:
        submission = self._extract_form_submission(metadata)
        if not submission:
            return FormProcessingResult(
                summary=None,
                skip_response=False,
                form_kind=None,
                escalation_confirmed=False,
                metadata_updates={},
                resolved=False,
            )

        form_kind = await self._resolve_form_kind(session_id, metadata, submission)
        status = self._normalize_text(submission.get("status"))
        choice = self._first_form_choice(submission)

        yes_values = {"yes", "y", "true"}
        no_values = {"no", "n", "false"}

        summary: Optional[str] = None
        skip_response = False
        escalation_confirmed = False

        metadata_updates: Dict[str, Any] = {}
        if form_kind:
            metadata_updates["form_kind"] = form_kind

        feedback_helped: Optional[bool] = None
        resolution_confirmed: Optional[bool] = None

        if status == "dismissed":
            skip_response = True
            if form_kind == "escalation":
                summary = "Escalation prompt dismissed; continue troubleshooting without involving a technician yet."
                skip_response = False
            elif form_kind == "feedback":
                summary = "Feedback form dismissed; avoid repeating the last suggestion."
            else:
                summary = "Follow-up form dismissed."
            self._maybe_attach_summary(metadata_updates, summary)
            return FormProcessingResult(
                summary=summary,
                skip_response=skip_response,
                form_kind=form_kind,
                escalation_confirmed=False,
                metadata_updates=metadata_updates,
                resolved=False,
                feedback_helped=feedback_helped,
                resolution_confirmed=resolution_confirmed,
            )

        if form_kind == "escalation":
            summary, escalation_confirmed = self._handle_escalation(choice, status, yes_values, no_values)
            if escalation_confirmed:
                metadata_updates["escalation"] = {"status": "user_confirmed"}
            self._maybe_attach_summary(metadata_updates, summary)
            return FormProcessingResult(
                summary=summary,
                skip_response=False,
                form_kind=form_kind,
                escalation_confirmed=escalation_confirmed,
                metadata_updates=metadata_updates,
                resolved=False,
                feedback_helped=feedback_helped,
                resolution_confirmed=resolution_confirmed,
            )

        if form_kind == "feedback":
            summary, feedback_helped = self._handle_feedback(choice, status, yes_values, no_values)
            self._maybe_attach_summary(metadata_updates, summary)
            return FormProcessingResult(
                summary=summary,
                skip_response=False,
                form_kind=form_kind,
                escalation_confirmed=False,
                metadata_updates=metadata_updates,
                resolved=False,
                feedback_helped=feedback_helped,
                resolution_confirmed=resolution_confirmed,
            )

        if form_kind == "resolution_check":
            summary, resolution_confirmed = self._handle_resolution_check(choice, status, yes_values, no_values)
            self._maybe_attach_summary(metadata_updates, summary)
            resolved = bool(resolution_confirmed)
            return FormProcessingResult(
                summary=summary,
                skip_response=False,
                form_kind=form_kind,
                escalation_confirmed=False,
                metadata_updates=metadata_updates,
                resolved=resolved,
                feedback_helped=feedback_helped,
                resolution_confirmed=resolution_confirmed,
            )

        summary, generic_feedback = self._handle_feedback(choice, status, yes_values, no_values)
        self._maybe_attach_summary(metadata_updates, summary)
        return FormProcessingResult(
            summary=summary,
            skip_response=False,
            form_kind=form_kind,
            escalation_confirmed=False,
            metadata_updates=metadata_updates,
            resolved=False,
            feedback_helped=generic_feedback,
            resolution_confirmed=resolution_confirmed,
        )

    def _handle_escalation(
        self,
        choice: Optional[str],
        status: Optional[str],
        yes_values: set[str],
        no_values: set[str],
    ) -> tuple[Optional[str], bool]:
        if status == "submitted":
            if choice in yes_values:
                return (
                    "User approved escalation to a technician. Confirm the hand-off and outline next steps.",
                    True,
                )
            if choice in no_values:
                return ("User declined escalation; continue troubleshooting with new ideas.", False)
            if choice:
                return (f"Escalation form submitted with value: {choice}.", False)
            return ("Escalation form submitted without a specific answer.", False)

        if choice in yes_values:
            return (
                "User wants escalation to a technician. Confirm the hand-off and set expectations.",
                True,
            )
        if choice in no_values:
            return ("User declined escalation; keep offering alternatives.", False)
        if status:
            return (f"Escalation form status: {status}.", False)
        if choice:
            return (f"Escalation response value: {choice}.", False)
        return (None, False)

    def _handle_feedback(
        self,
        choice: Optional[str],
        status: Optional[str],
        yes_values: set[str],
        no_values: set[str],
    ) -> tuple[Optional[str], Optional[bool]]:
        helped: Optional[bool] = None
        if status == "submitted":
            if choice in yes_values:
                helped = True
                return ("Feedback: the user said the last suggestion helped.", helped)
            if choice in no_values:
                helped = False
                return ("Feedback: the user said the last suggestion did not help. Provide a different approach.", helped)
            if choice:
                return (f"Feedback response provided: {choice}.", helped)
            return ("Feedback form was submitted without a specific answer.", helped)

        if status:
            return (f"Feedback form status: {status}.", helped)
        if choice:
            if choice in yes_values:
                return ("Feedback response provided: yes.", True)
            if choice in no_values:
                return ("Feedback response provided: no.", False)
            return (f"Feedback response provided: {choice}.", helped)
        return (None, helped)

    def _handle_resolution_check(
        self,
        choice: Optional[str],
        status: Optional[str],
        yes_values: set[str],
        no_values: set[str],
    ) -> tuple[Optional[str], Optional[bool]]:
        if status == "submitted":
            if choice in yes_values:
                return ("Resolution check: the user confirmed the issue is fully resolved.", True)
            if choice in no_values:
                return ("Resolution check: the user reported the issue is still present.", False)
            if choice:
                return (f"Resolution check submitted with value: {choice}.", None)
            return ("Resolution check submitted without a specific answer.", None)

        if status:
            return (f"Resolution check status: {status}.", None)
        if choice:
            if choice in yes_values:
                return ("Resolution check response: yes.", True)
            if choice in no_values:
                return ("Resolution check response: no.", False)
            return (f"Resolution check response: {choice}.", None)
        return (None, None)

    @staticmethod
    def _maybe_attach_summary(metadata_updates: Dict[str, Any], summary: Optional[str]) -> None:
        if summary:
            metadata_updates.setdefault("follow_up_form_summary", summary)

    async def _resolve_form_kind(
        self,
        session_id: UUID,
        metadata: Dict[str, Any],
        submission: Dict[str, Any],
    ) -> Optional[str]:
        inline_kind = self._extract_form_kind(metadata)
        if inline_kind:
            return inline_kind

        replied_to = submission.get("replied_to")
        message_id = self._try_parse_uuid(replied_to)
        if not message_id:
            return None

        try:
            message = await self._message_repository.get_by_id(message_id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to fetch message %s while resolving form kind", replied_to)
            return None
        if not message or message.session_id != session_id:
            return None

        origin_metadata = message.message_metadata or {}
        return self._extract_form_kind(origin_metadata)

    @staticmethod
    def _extract_form_submission(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for key in ("follow_up_form_response", "follow_up_form_submission"):
            value = metadata.get(key)
            if isinstance(value, dict):
                return value
        return None

    @staticmethod
    def _first_form_choice(form_submission: Dict[str, Any]) -> Optional[str]:
        fields = form_submission.get("fields")
        if isinstance(fields, list):
            for entry in fields:
                if not isinstance(entry, dict):
                    continue
                if "value" in entry:
                    normalized = FormSubmissionService._normalize_value(entry["value"])
                    if normalized:
                        return normalized
        value = form_submission.get("value")
        return FormSubmissionService._normalize_value(value)

    @staticmethod
    def _normalize_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list):
            if not value:
                return None
            value = value[0]
        if isinstance(value, (int, float)):
            text = str(value).strip()
            return text.lower() if text else None
        if isinstance(value, str):
            text = value.strip()
            return text.lower() if text else None
        return None

    @staticmethod
    def _normalize_text(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        text = value.strip().lower()
        return text or None

    @staticmethod
    def _extract_form_kind(metadata: Any) -> Optional[str]:
        if not isinstance(metadata, dict):
            return None
        value = metadata.get("form_kind")
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        extra = metadata.get("extra")
        if isinstance(extra, dict):
            nested = extra.get("form_kind")
            if isinstance(nested, str) and nested.strip():
                return nested.strip().lower()
        return None

    @staticmethod
    def _try_parse_uuid(value: Any) -> Optional[UUID]:
        if not isinstance(value, str):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None
