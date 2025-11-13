from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelUsageDetails(BaseModel):
    """Structured view of model usage and cost estimates returned by OpenAI."""

    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_input: Optional[float] = None
    cost_output: Optional[float] = None
    cost_total: Optional[float] = None
    pricing_model: Optional[str] = Field(
        default=None,
        description="Pricing key used to derive costs (model name or prefix).",
    )
    currency: str = "USD"
    raw_usage: Dict[str, Any] = Field(default_factory=dict)
    request_type: str = "response_generation"
