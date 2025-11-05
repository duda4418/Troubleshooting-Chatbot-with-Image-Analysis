from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import chromadb
from chromadb.api import ClientAPI

from app.data.DTO import KnowledgeHit

LOGGER = logging.getLogger(__name__)


class _BagOfWordsEmbedder:
    """Lightweight vocabulary embeddings tailored for the troubleshooting corpus."""

    def __init__(self, knowledge: Dict[str, Dict[str, object]]) -> None:
        self._vocab: Dict[str, int] = {}
        for entry in knowledge.values():
            self._ingest(self._compose_text(entry))
        if not self._vocab:
            self._vocab["__bias__"] = 0

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return [self._vectorize(self._tokenize(text)) for text in documents]

    def embed_query(self, text: str) -> List[float]:
        return self._vectorize(self._tokenize(text))

    def _ingest(self, text: str) -> None:
        for token in self._tokenize(text):
            if token not in self._vocab:
                self._vocab[token] = len(self._vocab)

    @staticmethod
    def _compose_text(entry: Dict[str, object]) -> str:
        parts: List[str] = [str(entry.get("label", ""))]
        for cause in entry.get("causes", []) or []:
            parts.append(str(cause))
        for action in entry.get("actions", []) or []:
            if isinstance(action, dict):
                parts.extend(str(value) for value in action.values())
            else:
                parts.append(str(action))
        for group in entry.get("alternatives", []) or []:
            if isinstance(group, list):
                for step in group:
                    if isinstance(step, dict):
                        parts.extend(str(value) for value in step.values())
                    else:
                        parts.append(str(step))
        return " ".join(parts)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _vectorize(self, tokens: List[str]) -> List[float]:
        if not self._vocab:
            return [0.0]
        vector = [0.0] * len(self._vocab)
        for token in tokens:
            idx = self._vocab.get(token)
            if idx is not None:
                vector[idx] += 1.0
        norm = math.sqrt(sum(val * val for val in vector))
        if norm:
            vector = [val / norm for val in vector]
        return vector or [0.0]


class ChromaService:
    """Wrapper around Chroma that can run locally or against a hosted endpoint."""

    def __init__(
        self,
        *,
        chroma_url: str | None = None,
        chroma_path: str = ".chroma",
        collection_name: str = "troubleshoot-cases",
        knowledge_path: Path | None = None,
        auto_seed: bool = True,
    ) -> None:
        self._index = self._load_knowledge(knowledge_path)
        self._embedder = _BagOfWordsEmbedder(self._index)
        self._client = self._create_client(chroma_url=chroma_url, chroma_path=chroma_path)
        self._collection_name = collection_name
        self._collection = self._client.get_or_create_collection(name=collection_name)

        if auto_seed:
            self._seed_collection()

    async def search(self, query: str, limit: int = 3) -> List[KnowledgeHit]:
        if not query.strip():
            return []
        return await asyncio.to_thread(self._search_sync, query, limit)

    def _search_sync(self, query: str, limit: int) -> List[KnowledgeHit]:
        embedding = self._embedder.embed_query(query)
        try:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                include=["distances"],
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Chroma query failed")
            return []

        ids = result.get("ids", [[]])[0] if result.get("ids") else []
        distances = result.get("distances", [[]])[0] if result.get("distances") else []

        hits: List[KnowledgeHit] = []
        for idx, doc_id in enumerate(ids):
            payload = self._index.get(doc_id)
            if not payload:
                LOGGER.debug("Skipping unknown knowledge id %s", doc_id)
                continue
            distance = distances[idx] if idx < len(distances) else None
            similarity = 0.0
            if distance is not None:
                similarity = max(0.0, min(1.0, 1 - distance))

            causes = payload.get("causes", [])
            actions = payload.get("actions", [])
            action_values = [
                action.get("value", "")
                for action in actions
                if isinstance(action, dict) and action.get("value")
            ]
            max_steps = 2
            steps = action_values[:max_steps]
            if len(action_values) > max_steps:
                steps.append("Additional steps available if needed.")
            hits.append(
                KnowledgeHit(
                    label=payload.get("label", doc_id),
                    similarity=similarity,
                    summary="; ".join(causes[:3]),
                    steps=steps,
                )
            )

        return hits

    def _create_client(self, chroma_url: str | None, chroma_path: str) -> ClientAPI:
        if chroma_url:
            candidate = chroma_url if "://" in chroma_url else f"http://{chroma_url}"
            parsed = urlparse(candidate)
            host = parsed.hostname or chroma_url
            port = parsed.port or (443 if parsed.scheme == "https" else 8000)
            use_ssl = parsed.scheme == "https"
            LOGGER.info("Connecting to Chroma server at %s:%s (ssl=%s)", host, port, use_ssl)
            return chromadb.HttpClient(host=host, port=port, ssl=use_ssl)

        path = Path(chroma_path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Using local Chroma store at %s", path)
        try:
            return chromadb.PersistentClient(path=str(path))
        except Exception:  # noqa: BLE001
            LOGGER.warning("Chroma metadata missing; resetting local store at %s", path, exc_info=True)
            self._reset_local_store(path)
            return chromadb.PersistentClient(path=str(path))

    @staticmethod
    def _reset_local_store(path: Path) -> None:
        for child in path.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except OSError:
                LOGGER.warning("Unable to remove %s during Chroma reset", child, exc_info=True)

    def _load_knowledge(self, knowledge_path: Path | None) -> Dict[str, Dict[str, object]]:
        search_paths: List[Path] = []
        if knowledge_path is not None:
            candidate = knowledge_path if knowledge_path.is_absolute() else (Path.cwd() / knowledge_path)
            search_paths.append(candidate)

        search_paths.extend(
            [
                Path(__file__).resolve().parents[1] / "data" / "troubleshoot_map.json",
                Path(__file__).resolve().parents[2] / "data" / "troubleshoot_map.json",
                Path(__file__).resolve().parents[3] / "data" / "troubleshoot_map.json",
            ]
        )

        attempted: List[Path] = []
        for path in search_paths:
            attempted.append(path)
            if path.exists():
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                LOGGER.info("Loaded %s troubleshooting cases from %s", len(data), path)
                return {label: {"label": label, **payload} for label, payload in data.items()}

        msg = "Knowledge base file not found. Looked in: " + ", ".join(str(p) for p in attempted)
        raise FileNotFoundError(msg)

    def _seed_collection(self) -> None:
        if not self._index:
            return

        try:
            existing = self._collection.count()
        except Exception:  # noqa: BLE001
            existing = None

        desired = len(self._index)
        if existing is not None and existing >= desired:
            LOGGER.info(
                "Chroma collection '%s' already populated (%s items)",
                self._collection_name,
                existing,
            )
            return

        documents_payload = [self._build_document(entry) for entry in self._index.values()]
        if not documents_payload:
            return

        ids, documents = zip(*documents_payload)
        ids_list = list(ids)
        documents_list = list(documents)
        embedded = self._embedder.embed_documents(documents_list)

        metadata = [
            {"label": self._index[_id]["label"], "severity": self._index[_id].get("severity", "")}
            for _id in ids_list
        ]

        self._collection.upsert(
            ids=ids_list,
            documents=documents_list,
            embeddings=embedded,
            metadatas=metadata,
        )
        LOGGER.info(
            "Seeded Chroma collection '%s' with %s troubleshooting cases",
            self._collection_name,
            len(ids_list),
        )
        LOGGER.info(
            "Synced %s knowledge entries into Chroma collection '%s'",
            len(ids_list),
            getattr(self._collection, "name", self._collection_name),
        )

    def _build_document(self, entry: Dict[str, object]) -> Tuple[str, str]:
        label: str = str(entry["label"])
        causes = entry.get("causes", [])
        actions = entry.get("actions", [])
        alternatives = entry.get("alternatives", [])

        cause_text = "\n".join(f"Cause: {cause}" for cause in causes) if isinstance(causes, list) else ""
        action_text = "\n".join(
            f"Action: {action.get('value', '')}"
            for action in actions
            if isinstance(action, dict)
        )
        alternative_text = "\n".join(
            f"Alternative Step: {step.get('value', '')}"
            for group in alternatives
            if isinstance(group, list)
            for step in group
            if isinstance(step, dict)
        )

        parts = [f"Label: {label}"]
        severity = entry.get("severity")
        if isinstance(severity, str) and severity:
            parts.append(f"Severity: {severity}")
        if cause_text:
            parts.append(cause_text)
        if action_text:
            parts.append(action_text)
        if alternative_text:
            parts.append(alternative_text)

        document = "\n".join(parts)
        return label, document
