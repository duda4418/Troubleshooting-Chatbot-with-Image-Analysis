from typing import List, Optional
from pydantic import BaseModel, Field

class AnalyzeResp(BaseModel):
    label: str = Field(description="One of the known classes or 'inconclusive'")
    confidence: float = Field(ge=0, le=1)
    session_id: str

class ChatReq(BaseModel):
    session_id: str
    user_input: Optional[str] = None
    event: str = Field(pattern="^(start|confirm|not_solved|try_again|done)$")

class ChatResp(BaseModel):
    message: str
    quick_replies: List[str]
    actions: List[dict]

class FeedbackReq(BaseModel):
    session_id: str
    solved: bool
    final_label: Optional[str] = None
    notes: Optional[str] = None
