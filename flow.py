import json
from pathlib import Path

from config import settings

_MAP_PATH = Path(__file__).resolve().parent / "troubleshoot_map.json"

with _MAP_PATH.open("r", encoding="utf-8") as f:
    FLOW: dict = json.load(f)

LABELS = settings.LABELS
FALLBACK = settings.FALLBACK
