from __future__ import annotations

import base64
import logging
from typing import Optional

DEFAULT_IMAGE_MIME = "image/png"

_SUPPORTED_MIMES: set[str] = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/bmp",
}

_CANONICAL_MIMES: dict[str, str] = {
    "image/jpg": "image/jpeg",
}

_MAGIC_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
)

_WEBP_CONTAINER_PREFIX = b"RIFF"
_WEBP_TAG = b"WEBP"


def resolve_image_mime(
    hint: Optional[str],
    image_b64: str,
    *,
    logger: Optional[logging.Logger] = None,
    default: str = DEFAULT_IMAGE_MIME,
) -> str:
    """Return a supported mime type by preferring the hint, then magic-byte detection."""

    normalized_hint = _normalize_mime(hint)
    if normalized_hint and normalized_hint in _SUPPORTED_MIMES:
        return normalized_hint

    if normalized_hint and logger:
        logger.debug("Image hint %s not supported; attempting detection", normalized_hint)

    detected = detect_image_mime(image_b64)
    if detected:
        if logger and detected != normalized_hint:
            logger.debug("Detected mime %s from image data", detected)
        return detected

    if logger:
        logger.debug("Falling back to default mime %s", default)
    return default


def detect_image_mime(image_b64: str) -> Optional[str]:
    """Best-effort mime detection using file signatures."""

    try:
        header = base64.b64decode(image_b64[:96], validate=True)
    except Exception:  # noqa: BLE001
        return None

    for magic, mime in _MAGIC_SIGNATURES:
        if header.startswith(magic):
            return mime

    if header.startswith(_WEBP_CONTAINER_PREFIX) and len(header) >= 12 and header[8:12] == _WEBP_TAG:
        return "image/webp"

    return None


def to_data_url(image_b64: str, mime: str) -> str:
    """Wrap base64 data into a data URL understood by the OpenAI Responses API."""

    return f"data:{mime};base64,{image_b64}"


def _normalize_mime(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    return _CANONICAL_MIMES.get(normalized, normalized)
