import io
import uuid
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, Form
from PIL import Image

from config import settings
from flow import LABELS, FALLBACK
from models import AnalyzeResp, AnalyzeTextReq
from services.openai_service import structured_label_from_openai, detect_intent_from_text
from state import SESSIONS
from utils.image_utils import pil_to_data_url

analyze_router = APIRouter(prefix="", tags=["analyze"])

@analyze_router.post("/analyze", response_model=AnalyzeResp)
async def analyze(
    image: Optional[UploadFile] = File(None),
    user_text: Optional[str] = Form(None)
):
    if not image and not user_text:
        raise HTTPException(400, "You need to provide either an image or some text input.")

    image_label = None
    image_conf = None
    text_intent = None
    text_conf = None

    # Process image only (does not mix user_text into vision prompt unless both provided)
    if image:
        if image.content_type not in settings.ALLOWED_TYPES:
            raise HTTPException(400, f"Invalid file type: {image.content_type}")
        raw = await image.read()
        if len(raw) > settings.MAX_IMAGE_BYTES:
            raise HTTPException(400, "File too large (max 8MB)")
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        data_url = pil_to_data_url(img)
        # For pure image (without text) we pass None; if both we pass user_text for richer context
        vision_text = user_text if user_text else None
        v_label, v_conf = structured_label_from_openai(data_url, vision_text, LABELS, FALLBACK)
        if v_label not in LABELS and v_label != FALLBACK:
            v_label = FALLBACK
        image_label = v_label
        image_conf = v_conf

    # Process text intent if provided
    if user_text:
        intent_result = detect_intent_from_text(user_text)
        intent_label_raw = intent_result.get("intent", FALLBACK)
        intent_label = intent_label_raw.lower().replace(" ", "_")
        intent_conf = float(intent_result.get("confidence", 0))
        if intent_label not in LABELS and intent_label != FALLBACK:
            intent_label = FALLBACK
        text_intent = intent_label
        text_conf = intent_conf

    # Decide unified label/confidence priority: image first (if present), else text
    if image_label is not None:
        final_label = image_label
        final_conf = image_conf if image_conf is not None else 0.0
    else:
        final_label = text_intent or FALLBACK
        final_conf = text_conf if text_conf is not None else 0.0

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "label": final_label,
        "confidence": final_conf,
        "image_label": image_label,
        "image_confidence": image_conf,
        "text_intent": text_intent,
        "text_intent_confidence": text_conf,
        "history": [],
        "status": "new",
        "sources": {
            "image": bool(image),
            "text": bool(user_text)
        }
    }

    return {
        "label": final_label,
        "confidence": round(final_conf, 3),
        "session_id": session_id,
        "image_label": image_label,
        "image_confidence": image_conf if image_conf is None else round(image_conf, 3),
        "text_intent": text_intent,
        "text_intent_confidence": text_conf if text_conf is None else round(text_conf, 3)
    }

@analyze_router.post("/analyze-text", response_model=AnalyzeResp)
async def analyze_text(req: AnalyzeTextReq):
    intent_result = detect_intent_from_text(req.user_text)
    intent_label_raw = intent_result.get("intent", FALLBACK)
    intent_label = intent_label_raw.lower().replace(" ", "_")
    intent_conf = float(intent_result.get("confidence", 0))
    if intent_label not in LABELS and intent_label != FALLBACK:
        intent_label = FALLBACK

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "label": intent_label,
        "confidence": intent_conf,
        "image_label": None,
        "image_confidence": None,
        "text_intent": intent_label,
        "text_intent_confidence": intent_conf,
        "history": [],
        "status": "new",
        "sources": {"image": False, "text": True}
    }
    return {
        "label": intent_label,
        "confidence": round(intent_conf, 3),
        "session_id": session_id,
        "image_label": None,
        "image_confidence": None,
        "text_intent": intent_label,
        "text_intent_confidence": round(intent_conf, 3)
    }
