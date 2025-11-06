from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from openai import OpenAI  # type: ignore[import]

from app.core.config import settings
from app.data.DTO.image_analysis_dto import (
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageAnalysisSummary,
    ImageObservationSummary,
)
from app.data.DTO.usage_dto import ModelUsageDetails
from pydantic import BaseModel, ConfigDict, Field

from app.data.repositories.conversation_image_repository import ConversationImageRepository
from app.data.schemas.models import ConversationImage
from app.services.utils.image_payload import resolve_image_mime, to_data_url
from app.services.utils.usage_metrics import extract_usage_details

logger = logging.getLogger(__name__)


class ImageObservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(description="Short clause describing what is visible in the image")
    confidence: float = Field(ge=0, le=1, description="Confidence score between 0 and 1")
    label: str | None = Field(default=None, description="Concise subject name if available")
    details: List[str] = Field(default_factory=list, description="List of factual visual observations")


class ImageBatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    images: List[ImageObservationPayload] = Field(
        description="One entry per provided image, in the same order",
        min_length=1,
    )


class ImageAnalysisResult(BaseModel):
    response: ImageAnalysisResponse
    usage: Optional[ModelUsageDetails] = None


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

    async def analyze_and_store(self, request: ImageAnalysisRequest) -> ImageAnalysisResult:
        if not request.images_b64:
            raise ValueError("images_b64 cannot be empty")

        if not self._client:
            raise RuntimeError("OpenAI API key is not configured")

        stored_images = await self._persist_images(request)
        summary, usage_details = await self._generate_summary(request)
        await self._update_images_with_summary(stored_images, summary)

        response_payload = ImageAnalysisResponse(
            session_id=request.session_id,
            message_id=request.message_id,
            image_ids=[image.id for image in stored_images],
            summary=summary,
        )
        return ImageAnalysisResult(response=response_payload, usage=usage_details)

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

    async def _generate_summary(
        self,
        request: ImageAnalysisRequest,
    ) -> tuple[ImageAnalysisSummary, Optional[ModelUsageDetails]]:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self._invoke_openai(request))
        summary = self._parse_summary(response)
        usage_details = extract_usage_details(
            response,
            default_model=self._vision_model,
            request_type="image_analysis",
        )
        return summary, usage_details

    def _invoke_openai(self, request: ImageAnalysisRequest):
        user_prompt = request.user_prompt or "Summarize what you see and highlight anything unusual."
        content: List[dict] = []

        for idx, image_b64 in enumerate(request.images_b64):
            hint = None
            if request.image_mime_types and idx < len(request.image_mime_types):
                hint = request.image_mime_types[idx]
            mime = resolve_image_mime(hint, image_b64, logger=logger)
            data_url = to_data_url(image_b64, mime)
            content.append({"type": "input_image", "image_url": data_url})

        locale_line = f"Locale: {request.locale}." if request.locale else ""
        image_count = len(request.images_b64)
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"{locale_line}\n"
                    f"You received {image_count} image(s). Respond with valid JSON only. Provide exactly {image_count} entries in the 'images' array, one per image in the same order. "
                    "Each description must remain specific to its image. Provide a 'label' for each entry summarizing key issues or conditions using short keywords (e.g., 'dirty dishes', 'cloudy glass'). "
                    "Details must be direct visual observations, not recommendations.\n"
                    f"User note: {user_prompt}"
                ).strip(),
            }
        )

        instructions = (
            "You describe appliance-related photos in neutral, observational language. "
            "Return JSON with an 'images' array containing one entry for each input image in the same order. "
            "Each entry must include description, confidence, label, and details (list of factual observations). "
            "Labels must be concise issue keywords or conditions (e.g., 'rust spots', 'clean dishes', 'cloudy glass') and must never be empty. "
            "Do not combine observations across images. Do not provide troubleshooting advice, next steps, or instructions." \
            "If the images are unclear or do not contain dishwasher-related content, state this fact in the description and set confidence to 0.0." \
        )

        return self._client.responses.parse(
            model=self._vision_model,
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            #reasoning={"effort": "minimal"},    
            #text={"verbosity": "low"},
            temperature=0.2,
            text_format=ImageBatchPayload,
        )

    def _parse_summary(self, response) -> ImageAnalysisSummary:
        payload = getattr(response, "output_parsed", None)
        if not isinstance(payload, ImageBatchPayload):
            message = "OpenAI response did not include the expected image batch payload"
            logger.error(message)
            raise RuntimeError(message)

        observations: List[ImageObservationSummary] = []
        for item in payload.images:
            description = item.description.strip()
            label = item.label.strip() if item.label and item.label.strip() else ""
            details = [detail.strip() for detail in item.details if detail and detail.strip()]
            observations.append(
                ImageObservationSummary(
                    description=description,
                    confidence=self._coerce_confidence(item.confidence),
                    label=self._derive_label(description, details, label),
                    details=details,
                )
            )

        return ImageAnalysisSummary(images=observations)

    async def _update_images_with_summary(
        self,
        images: List[ConversationImage],
        summary: ImageAnalysisSummary,
    ) -> None:
        summaries = summary.images
        for index, image in enumerate(images):
            observation = summaries[index] if index < len(summaries) else None
            if observation:
                image.analysis_text = observation.description
                metadata_details = observation.details
                metadata_label = observation.label
                metadata_confidence = observation.confidence
            else:
                image.analysis_text = ""
                metadata_details = []
                metadata_label = "unavailable"
                metadata_confidence = 0.0

            image.analysis_metadata = {
                "confidence": metadata_confidence,
                "label": metadata_label,
                "details": metadata_details,
                "image_index": index,
                "source": image.analysis_metadata.get("source"),
            }
            await self._image_repository.update(image)

    @staticmethod
    def _coerce_confidence(value: float) -> float:
        return max(0.0, min(float(value), 1.0))

    @staticmethod
    def _derive_label(description: str, details: List[str], raw_label: str) -> str:
        if raw_label:
            return raw_label

        keywords = ["dirty", "filthy", "greasy", "cloudy", "foggy", "streak", "residue", "rust", "scale", "crack", "broken", "leak", "overflow", "clean", "empty", "full", "soap", "detergent", "foam", "water"]
        text = " ".join([description, *details]).lower()
        matched = []
        for word in keywords:
            if word in text:
                matched.append(word)
        if matched:
            unique = []
            for word in matched:
                if word not in unique:
                    unique.append(word)
            return ", ".join(unique)

        fallback = description.split(".")[0].strip()
        if fallback:
            return fallback[:80]
        return "general observation"
