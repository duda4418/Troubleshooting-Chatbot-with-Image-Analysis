from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ImageAnalysisRequest(BaseModel):
    session_id: UUID
    message_id: Optional[UUID] = None
    images_b64: List[str] = Field(default_factory=list)
    image_mime_types: Optional[List[Optional[str]]] = None
    locale: str = "en"
    user_prompt: Optional[str] = None


class ImageObservationSummary(BaseModel):
    description: str
    confidence: float
    label: str
    condition: Optional[str] = None
    details: List[str] = Field(default_factory=list)


class ImageAnalysisSummary(BaseModel):
    images: List[ImageObservationSummary] = Field(default_factory=list)


class ImageAnalysisResponse(BaseModel):
    session_id: UUID
    message_id: Optional[UUID]
    image_ids: List[UUID] = Field(default_factory=list)
    summary: ImageAnalysisSummary
