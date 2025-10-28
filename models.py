from typing import List, Optional
from pydantic import BaseModel, Field

class AnalyzeResp(BaseModel):
    # Unified best-effort label/confidence used by downstream flow
    label: str = Field(description="Primary label chosen from image/text analyses or 'inconclusive'")
    confidence: float = Field(ge=0, le=1)
    session_id: str
    # Optional separate sources
    image_label: Optional[str] = Field(default=None, description="Label from image analysis if image provided")
    image_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    text_intent: Optional[str] = Field(default=None, description="Intent extracted from user text if text provided")
    text_intent_confidence: Optional[float] = Field(default=None, ge=0, le=1)

class AnalyzeTextReq(BaseModel):
    user_text: str = Field(min_length=1, description="Free text describing the issue.")

class ChatReq(BaseModel):
    session_id: str
    user_input: Optional[str] = None
    # Extindem pattern-ul pentru a include si 'solved' (folosit in fluxul de finalizare) si 'done'.
    event: str = Field(pattern="^(start|confirm|not_solved|try_again|solved|done)$")

class ChatResp(BaseModel):
    message: str
    quick_replies: List[str]
    actions: List[dict]

class FeedbackReq(BaseModel):
    session_id: str
    solved: bool
    final_label: Optional[str] = None
    notes: Optional[str] = None
