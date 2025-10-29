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
            ]}]
        )
        obj = json.loads(chat.choices[0].message.content)
        return obj["label"], float(obj["confidence"])

# --- New function for NLP intent detection from free text ---
def detect_intent_from_text(user_text: str) -> dict:
    """Extracts an intent mapped to known dishwasher issue labels.

    Returns dict: {intent: <label|inconclusive>, confidence: float, raw: <original model JSON>}
    """
    labels = settings.LABELS
    fallback = settings.FALLBACK

    # Basic synonym mapping to help normalize model output / user phrasing
    synonyms = {
        "cloudy": "cloudy_glass",
        "cloudy_glass": "cloudy_glass",
        "film": "residue",
        "residue": "residue",
        "grease": "greasy",
        "greasy": "greasy",
        "spots": "spots",
        "stains": "spots",
        "dirty": "dirty",
        "unclean": "dirty",
        "oily": "greasy",
    }

    constraint_list = labels + [fallback]
    prompt = (
        "You are an expert dishwasher troubleshooting intent classifier. "
        f"Valid intents: {constraint_list}. "
        "Map user description to the closest valid intent (use semantic similarity). If none match confidently, use 'inconclusive'. "
        "Return ONLY JSON with keys intent (one of the valid intents) and confidence (0-1). "
        f"User text: '{user_text}'"
    )

    chat = client.chat.completions.create(
        model=settings.OPENAI_TEXT_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    raw_content = chat.choices[0].message.content
    try:
        obj = json.loads(raw_content)
    except json.JSONDecodeError:
        obj = {"intent": fallback, "confidence": 0.0}

    intent_raw = str(obj.get("intent", fallback)).lower().strip()
    # Normalize via synonyms mapping
    intent_norm = synonyms.get(intent_raw, intent_raw)
    if intent_norm not in constraint_list:
        intent_norm = fallback
    conf = float(obj.get("confidence", 0))

    debug_payload = {"raw": obj, "prompt_used": prompt}
    print(f"[INTENT_DEBUG] input='{user_text}' model_raw={obj} normalized_intent={intent_norm} confidence={conf}")

    return {"intent": intent_norm, "confidence": conf, "_debug": debug_payload}
