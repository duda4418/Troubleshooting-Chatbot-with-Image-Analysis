from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.data.DTO.usage_dto import ModelUsageDetails

logger = logging.getLogger(__name__)


def extract_usage_details(
    response: Any,
    *,
    default_model: str,
    request_type: str,
) -> Optional[ModelUsageDetails]:
    """Extract structured usage details (tokens and estimated costs) from an OpenAI response."""

    usage_dict = normalize_usage_dict(getattr(response, "usage", None))
    if not usage_dict:
        return None

    model_name = getattr(response, "model", None) or usage_dict.get("model") or default_model
    input_tokens = int(usage_dict.get("input_tokens", 0) or 0)
    output_tokens = int(usage_dict.get("output_tokens", 0) or 0)
    total_tokens = int(usage_dict.get("total_tokens", input_tokens + output_tokens) or 0)

    cost_input, cost_output, cost_total, pricing_key = compute_usage_cost(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return ModelUsageDetails(
        model=model_name or "",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_input=cost_input,
        cost_output=cost_output,
        cost_total=cost_total,
        pricing_model=pricing_key,
        raw_usage=usage_dict,
        request_type=request_type,
    )


def normalize_usage_dict(raw_usage: Any) -> Dict[str, Any]:
    if raw_usage is None:
        return {}
    if isinstance(raw_usage, dict):
        return raw_usage
    for attr in ("model_dump", "dict", "to_dict"):
        method = getattr(raw_usage, attr, None)
        if callable(method):
            try:
                data = method()
            except Exception:  # noqa: BLE001
                logger.debug("Failed to call %s on usage payload", attr, exc_info=True)
                continue
            if isinstance(data, dict):
                return data
    return {}


def compute_usage_cost(
    *,
    model_name: Optional[str],
    input_tokens: int,
    output_tokens: int,
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    pricing = settings.openai_pricing or {}
    if not pricing:
        return None, None, None, None

    key = match_pricing_key(model_name, pricing)
    if not key:
        logger.debug("No pricing entry found for model %s", model_name)
        return None, None, None, None

    rates = pricing.get(key) or {}
    input_rate = float(rates.get("input", 0.0) or 0.0)
    output_rate = float(rates.get("output", 0.0) or 0.0)
    # Rates are expected per 1M tokens.
    cost_input = (input_tokens / 1_000_000.0) * input_rate if input_rate else 0.0
    cost_output = (output_tokens / 1_000_000.0) * output_rate if output_rate else 0.0
    cost_total = cost_input + cost_output
    return cost_input, cost_output, cost_total, key


def match_pricing_key(model_name: Optional[str], pricing: Dict[str, Dict[str, float]]) -> Optional[str]:
    if not model_name:
        return None
    if model_name in pricing:
        return model_name
    lowered = model_name.lower()
    for candidate in pricing:
        if lowered.startswith(candidate.lower()):
            return candidate
    return None


def embed_usage_metadata(payload: Dict[str, Any], usage: ModelUsageDetails) -> Dict[str, Any]:
    metadata = dict(payload or {})
    metadata["usage"] = {
        "model": usage.model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "cost_input": usage.cost_input,
        "cost_output": usage.cost_output,
        "cost_total": usage.cost_total,
        "pricing_model": usage.pricing_model,
        "currency": usage.currency,
        "request_type": usage.request_type,
    }
    return metadata
