from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.data.DTO.message_flow_dto import AssistantAnswer, GeneratedForm


class AssistantMessageMetadata(BaseModel):
    """Structured view of assistant message metadata prior to persistence."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    suggested_actions: List[str] = Field(default_factory=list)
    follow_up_form: Optional[GeneratedForm] = None
    confidence: Optional[float] = None
    client_hidden: Optional[bool] = None
    follow_up_type: Optional[str] = None
    follow_up_reason: Optional[str] = None
    form_kind: Optional[str] = None
    follow_up_form_summary: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    escalation: Optional[Dict[str, Any]] = None
    ticket: Optional[Dict[str, Any]] = None

    @classmethod
    def from_answer(
        cls,
        answer: AssistantAnswer,
    ) -> "AssistantMessageMetadata":
        instance = cls(
            suggested_actions=list(answer.suggested_actions or []),
            follow_up_form=answer.follow_up_form,
            confidence=answer.confidence,
            follow_up_type=_clean_str(answer.follow_up_type),
            follow_up_reason=_clean_str(answer.follow_up_reason),
        )
        instance._consume_metadata(answer.metadata)
        return instance

    def _consume_metadata(self, metadata: Optional[Dict[str, Any]]) -> None:
        if not isinstance(metadata, dict):
            return

        remaining = dict(metadata)

        client_hidden = remaining.pop("client_hidden", None)
        if isinstance(client_hidden, bool):
            self.client_hidden = client_hidden

        follow_up_type = _clean_str(remaining.pop("follow_up_type", None))
        if follow_up_type and not self.follow_up_type:
            self.follow_up_type = follow_up_type

        follow_up_reason = _clean_str(remaining.pop("follow_up_reason", None))
        if follow_up_reason and not self.follow_up_reason:
            self.follow_up_reason = follow_up_reason

        form_kind = _clean_str(remaining.pop("form_kind", None))
        if form_kind:
            self.form_kind = form_kind

        summary = _clean_str(remaining.pop("follow_up_form_summary", None))
        if summary:
            self.follow_up_form_summary = summary

        escalation = remaining.pop("escalation", None)
        if isinstance(escalation, dict):
            self.escalation = escalation

        ticket = remaining.pop("ticket", None)
        if isinstance(ticket, dict):
            self.ticket = ticket

        if remaining:
            self.extra = remaining

    def to_message_metadata(self) -> Dict[str, Any]:
        """Serialize to the dictionary shape stored on ConversationMessage."""

        payload = self.model_dump(exclude_none=True)
        if not payload.get("extra"):
            payload.pop("extra", None)
        return payload


def _clean_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
