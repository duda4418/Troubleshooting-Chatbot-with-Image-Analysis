from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.data.DTO import KnowledgeHit


class ChromaService:
    """Mock implementation of a ChromaDB-backed similarity search."""

    def __init__(self, knowledge_path: Path | None = None) -> None:
        if knowledge_path is not None:
            base_path = knowledge_path
        else:
            candidates = [
                Path(__file__).resolve().parents[1] / "data" / "troubleshoot_map.json",
                Path(__file__).resolve().parents[2] / "data" / "troubleshoot_map.json",
            ]
            base_path = next((path for path in candidates if path.exists()), candidates[0])

        if not base_path.exists():
            msg = f"Knowledge base file not found at {base_path}"
            raise FileNotFoundError(msg)

        with base_path.open("r", encoding="utf-8") as handle:
            self._index = json.load(handle)

    async def search(self, query: str, limit: int = 3) -> List[KnowledgeHit]:
        """Return mock results scored by simple token overlap."""
        normalized = query.lower()
        hits: List[KnowledgeHit] = []
        for label, payload in self._index.items():
            causes = " ".join(payload.get("causes", []))
            actions = " ".join(action.get("value", "") for action in payload.get("actions", []))
            text_blob = f"{label} {causes} {actions}".lower()
            overlap = sum(1 for token in normalized.split() if token and token in text_blob)
            if overlap == 0:
                continue
            similarity = min(1.0, overlap / max(1, len(normalized.split())))
            hits.append(
                KnowledgeHit(
                    label=label,
                    similarity=similarity,
                    summary="; ".join(payload.get("causes", [])[:3]),
                    steps=[action.get("value", "") for action in payload.get("actions", [])[:3]],
                )
            )
        hits.sort(key=lambda item: item.similarity, reverse=True)
        return hits[:limit]
