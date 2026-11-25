"""Local FastEmbed embeddings for ResolveAI policies."""

from __future__ import annotations

from threading import Lock
from typing import List, Optional, Sequence

from app.core.config import Settings, get_settings
from app.core.logging import logger


class EmbeddingService:
    def __init__(self, settings: Optional[Settings] = None, model=None):
        self.settings = settings or get_settings()
        self._model = model
        self._lock = Lock()

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding

                logger.info("Initializing ResolveAI FastEmbed model: %s", self.settings.embedding_model)
                self._model = TextEmbedding(model_name=self.settings.embedding_model)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        vectors = list(model.embed(list(texts)))
        result = []
        for vector in vectors:
            values = [float(v) for v in vector]
            if len(values) != self.settings.embedding_dimension:
                raise ValueError("Embedding dimension mismatch")
            result.append(values)
        return result

    def embed_query(self, query: str) -> List[float]:
        return self.embed_documents([f"query: {query.strip()}"])[0]


_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service
