from __future__ import annotations

import asyncio
import json
import logging
from typing import List

from openai import OpenAI  # type: ignore[import]

from app.core.config import settings
from app.data.DTO.image_analysis_dto import (
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageAnalysisSummary,
)
from app.data.repositories.conversation_image_repository import ConversationImageRepository
from app.data.schemas.models import ConversationImage
from app.services.utils.image_payload import resolve_image_mime, to_data_url

logger = logging.getLogger(__name__)


class ImageAnalysisService:
    """Generate informal image summaries via the OpenAI Responses API and persist them."""

    def __init__(
        self,
        image_repository: ConversationImageRepository,
        *,
        api_key: str | None = None,
        vision_model: str | None = None,
    ) -> None:
        self._image_repository = image_repository
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._vision_model = vision_model or settings.OPENAI_VISION_MODEL
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

    async def analyze_and_store(self, request: ImageAnalysisRequest) -> ImageAnalysisResponse:
        if not request.images_b64:
            raise ValueError("images_b64 cannot be empty")

        if not self._client:
            raise RuntimeError("OpenAI API key is not configured")

        stored_images = await self._persist_images(request)
        summary = await self._generate_summary(request)
        await self._update_images_with_summary(stored_images, summary)

        return ImageAnalysisResponse(
            session_id=request.session_id,
            message_id=request.message_id,
            image_ids=[image.id for image in stored_images],
            summary=summary,
        )

    async def _persist_images(self, request: ImageAnalysisRequest) -> List[ConversationImage]:
        stored: List[ConversationImage] = []
        for index, image_b64 in enumerate(request.images_b64):
            image = ConversationImage(
                session_id=request.session_id,
                message_id=request.message_id,
                storage_uri=f"inline://{request.session_id}/{index}",
                analysis_text=None,
                analysis_metadata={
                    "source": "inline_base64",
                },
            )
            stored.append(await self._image_repository.create(image))
        return stored

    async def _generate_summary(self, request: ImageAnalysisRequest) -> ImageAnalysisSummary:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self._invoke_openai(request))
        return self._parse_summary(response)

    def _invoke_openai(self, request: ImageAnalysisRequest):
        instructions = (
            "You describe appliance-related photos in neutral, observational language. "
            "Return JSON with keys description (short clause of what is visible), confidence (0-1 float), "
            "label (concise subject name), and details (array of brief factual observations about the visuals). "
            "Do not provide troubleshooting advice, next steps, or instructions."
        )

        user_prompt = request.user_prompt or "Summarize what you see and highlight anything unusual."
        content = [
            {"type": "input_text", "text": instructions},
        ]

        for idx, image_b64 in enumerate(request.images_b64):
            hint = None
            if request.image_mime_types and idx < len(request.image_mime_types):
                hint = request.image_mime_types[idx]
            mime = resolve_image_mime(hint, image_b64, logger=logger)
            data_url = to_data_url(image_b64, mime)
            content.append({"type": "input_image", "image_url": data_url})

        locale_line = f"Locale: {request.locale}." if request.locale else ""
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"{locale_line}\n"
                    "Respond with valid JSON only. Keep the description factual and concise. "
                    "Details must be direct visual observations, not recommendations.\n"
                    f"User note: {user_prompt}"
                ).strip(),
            }
        )

        return self._client.responses.create(
            model=self._vision_model,
            input=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            temperature=0.2,
        )

    def _parse_summary(self, response) -> ImageAnalysisSummary:
        text = self._extract_text(response)
        payload = self._coerce_json(text)

        description = str(payload.get("description") or text or "").strip()
        try:
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        label_value = payload.get("label")
        label = str(label_value) if label_value not in (None, "") else None
        details_value = payload.get("details") or []
        if isinstance(details_value, list):
            details = [str(item) for item in details_value]
        else:
            details = [str(details_value)] if details_value else []

        return ImageAnalysisSummary(
            description=description or "",
            confidence=max(0.0, min(confidence, 1.0)),
            label=label,
            details=details,
        )

    async def _update_images_with_summary(
        self,
        images: List[ConversationImage],
        summary: ImageAnalysisSummary,
    ) -> None:
        for image in images:
            image.analysis_text = summary.description
            image.analysis_metadata = {
                "confidence": summary.confidence,
                "label": summary.label,
                "details": summary.details,
                "source": image.analysis_metadata.get("source"),
            }
            await self._image_repository.update(image)

    @staticmethod
    def _extract_text(response) -> str:
        chunks: List[str] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "output_text":
                chunks.append(getattr(item, "text", ""))
        if not chunks and hasattr(response, "output_text"):
            chunks.append(getattr(response, "output_text", ""))
        return "".join(chunks).strip()

    @staticmethod
    def _coerce_json(text: str) -> dict:
        if not text:
            return {}
        snippet = ImageAnalysisService._strip_code_fence(text)
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            extracted = ImageAnalysisService._extract_json_block(snippet)
            if extracted:
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    return {}
            return {}

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        cleaned = text.strip()
        if not cleaned.startswith("```"):
            return cleaned

        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @staticmethod
    def _extract_json_block(text: str) -> str | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]
