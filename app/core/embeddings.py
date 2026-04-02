from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
        self._model: Optional[SentenceTransformer] = None

    def load(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(str(self.model_path))

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            self.load()
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()