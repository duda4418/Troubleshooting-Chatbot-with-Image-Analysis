import json
from typing import Optional

from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def structured_label_from_openai(data_url: str, user_text: Optional[str], labels: list[str], fallback: str) -> tuple[str, float]:
    """
    Returns (label, confidence)
    Uses Responses API first; falls back to Chat Completions JSON mode for compatibility.
    """
    prompt_text = (
        "You are a careful vision classifier. "
        f"Classify into {labels + [fallback]}. "
        "If unsure, return 'inconclusive'. "
        "Return only JSON with keys label, confidence."
    )
    if user_text:
        prompt_text += f"\nUser note: {user_text}"

    try:
        # Preferred: Responses API + json_schema (kept close to your original)
        resp = client.responses.create(
            model=settings.OPENAI_VISION_MODEL,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": prompt_text},
                {"type": "input_image", "image_data": data_url}
            ]}],
            response_format={"type": "json_schema", "json_schema": {
                "name": "dishwasher_issue", "strict": True, "schema": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "label": {"type": "string", "enum": labels + [fallback]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    },
                    "required": ["label", "confidence"]
                }
            }},
            temperature=0.2, seed=7,
        )
        content = resp.output[0].content[0]
        obj = getattr(content, "json", None) or json.loads(content.text)
        return obj["label"], float(obj["confidence"])
    except TypeError:
        # Fallback: Chat Completions + JSON mode
        chat = client.chat.completions.create(
            model=settings.OPENAI_VISION_MODEL,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]}],
            temperature=0.2,
        )
        obj = json.loads(chat.choices[0].message.content)
        return obj["label"], float(obj["confidence"])
