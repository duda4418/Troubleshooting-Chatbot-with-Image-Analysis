import io
import uuid
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

from config import settings
from flow import LABELS, FALLBACK
from models import AnalyzeResp
from services.openai_service import structured_label_from_openai
from state import SESSIONS
from utils.image_utils import pil_to_data_url

analyze_router = APIRouter(prefix="", tags=["analyze"])

@analyze_router.post("/analyze", response_model=AnalyzeResp)
async def analyze(image: UploadFile = File(...), user_text: Optional[str] = None):
    if image.content_type not in settings.ALLOWED_TYPES:
        raise HTTPException(400, f"Invalid file type: {image.content_type}")

    raw = await image.read()
    if len(raw) > settings.MAX_IMAGE_BYTES:
        raise HTTPException(400, "File too large (max 8MB)")

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    data_url = pil_to_data_url(img)

    label, conf = structured_label_from_openai(data_url, user_text, LABELS, FALLBACK)
    if label not in LABELS and label != FALLBACK:
        label = FALLBACK

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "label": label,
        "confidence": conf,
        "history": [],
        "status": "new",
    }

    return {"label": label, "confidence": round(conf, 3), "session_id": session_id}
