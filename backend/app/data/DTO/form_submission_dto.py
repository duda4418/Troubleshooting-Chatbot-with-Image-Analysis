from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _normalize_scalar(value: Any) -> Optional[str]:
    if value is None:
        return None

    current = value
    if isinstance(current, list):
        if not current:
            return None
        current = current[0]

    if isinstance(current, bool):
        return "true" if current else "false"

    if isinstance(current, (int, float)):
        text = str(current).strip()
    elif isinstance(current, str):
        text = current.strip()
    else:
        text = str(current).strip()

    if not text:
        return None

    return text.lower()


class FormSubmissionField(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: Any = None
    label: Optional[str] = None

    def normalized_value(self) -> Optional[str]:
        normalized = _normalize_scalar(self.value)
        if normalized:
            return normalized
        return _normalize_scalar(self.label)


class FormSubmissionPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    replied_to: Optional[str] = None
    value: Any = None
    fields: List[FormSubmissionField] = Field(default_factory=list)
    raw_payload: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    def normalized_status(self) -> Optional[str]:
        return _normalize_scalar(self.status)

    def first_choice(self) -> Optional[str]:
        for field in self.fields:
            normalized = field.normalized_value()
            if normalized:
                return normalized
        return _normalize_scalar(self.value)

    def with_raw_payload(self, payload: Dict[str, Any]) -> "FormSubmissionPayload":
        self.raw_payload = payload
        return self
