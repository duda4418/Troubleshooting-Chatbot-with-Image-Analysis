# services/openai_service.py

import json
from typing import Optional, Tuple, Dict, Any

from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# --- i18n helpers -------------------------------------------------------------

LANG_NAME = {"en": "English", "ro": "Romanian", "de": "German"}

def lang_directive(lang: Optional[str]) -> str:
    """Return a short instruction for the model to answer only in the selected language."""
    code = (lang or "en").lower()
    name = LANG_NAME.get(code, "English")
    return f" Respond ONLY in {name}. Keep the tone concise and helpful."

# --- Vision classification ----------------------------------------------------

def structured_label_from_openai(
    data_url: str,
    user_text: Optional[str],
    labels: list[str],
    fallback: str,
    lang: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Returns (label, confidence).

    Tries the Responses API with json_schema first (newer API).
    Falls back to Chat Completions JSON mode for compatibility/use in older runtimes.

    `lang` controls the language of any free-form text the model might emit internally;
    we still require a strict JSON, but we instruct language for consistency and future logs.
    """
    # Build classification instruction
    valid = labels + [fallback]
    prompt_text = (
        "You are a careful vision classifier for dishwasher troubleshooting."
        f" Classify the issue into one of: {valid}."
        " If unsure, return 'inconclusive'."
        " Return only JSON with keys: label (enum), confidence (0..1)."
        + lang_directive(lang)
    )
    if user_text:
        prompt_text += f"\nUser note: {user_text}"

    # --- Preferred path: Responses API with JSON schema ---
    try:
        resp = client.responses.create(
            model=settings.OPENAI_VISION_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt_text},
                        {"type": "input_image", "image_data": data_url},
                    ],
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "dishwasher_issue",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string", "enum": valid},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["label", "confidence"],
                    },
                },
            },
            temperature=0.2,
            seed=7,
        )

        # Responses API can return either a .json attr or .text
        content = resp.output[0].content[0]
        obj = getattr(content, "json", None) or json.loads(content.text)
        label = str(obj["label"])
        conf = float(obj["confidence"])
        return label, conf

    except Exception as e:
        # Fall back to Chat Completions JSON mode (also works for vision)
        try:
            chat = client.chat.completions.create(
                model=settings.OPENAI_VISION_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a dishwasher troubleshooting vision assistant." + lang_directive(lang),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                temperature=0.2,
            )
            raw = chat.choices[0].message.content
            obj = json.loads(raw)
            label = str(obj["label"])
            conf = float(obj["confidence"])
            return label, conf
        except Exception as e2:
            # Final safety: return fallback with low confidence
            print(f"[VISION_FALLBACK_ERROR] {e} | {e2}")
            return fallback, 0.0

# --- Text intent detection ----------------------------------------------------

def detect_intent_from_text(user_text: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts an intent mapped to known dishwasher issue labels.

    Returns:
      {
        "intent": <label|inconclusive>,
        "confidence": float,
        "_debug": { "raw": <model_json_or_minimal>, "prompt_used": <str> }
      }
    """
    labels: list[str] = settings.LABELS
    fallback: str = settings.FALLBACK
    constraint_list = labels + [fallback]

    # Optional normalization map (kept from your original approach)
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

    prompt = (
        "You are an expert dishwasher troubleshooting intent classifier."
        f" Valid intents: {constraint_list}."
        " Map the user description to the closest valid intent (use semantic similarity)."
        " If none match confidently, use 'inconclusive'."
        " Return ONLY JSON with keys: intent (enum), confidence (0..1)."
        + lang_directive(lang)
        + f"\nUser text: '{user_text}'"
    )

    try:
        chat = client.chat.completions.create(
            model=settings.OPENAI_TEXT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You classify user text into a dishwasher issue intent." + lang_directive(lang)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        raw_content = chat.choices[0].message.content
        obj = json.loads(raw_content)
    except Exception as e:
        print(f"[INTENT_MODEL_ERROR] {e}")
        obj = {"intent": fallback, "confidence": 0.0}

    intent_raw = str(obj.get("intent", fallback)).lower().strip()
    intent_norm = synonyms.get(intent_raw, intent_raw)
    if intent_norm not in constraint_list:
        intent_norm = fallback
    conf = float(obj.get("confidence", 0))

    debug_payload = {"raw": obj, "prompt_used": prompt}
    print(f"[INTENT_DEBUG] input='{user_text}' model_raw={obj} normalized_intent={intent_norm} confidence={conf}")

    return {"intent": intent_norm, "confidence": conf, "_debug": debug_payload}
