from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.models import RetrievedChunk


class ChromaVectorDB:
    def __init__(self, chroma_dir: Path):
        self.chroma_dir = Path(chroma_dir)
        self._client = chromadb.PersistentClient(path=str(self.chroma_dir))

    def get_or_create_collection(self, name: str) -> Collection:
        return self._client.get_or_create_collection(name=name)
    
    def get_project_collections(self, project: str) -> List[str]:
        suffix = f"__{project}"
        return [c.name for c in self._client.list_collections() if c.name.endswith(suffix)]

    def upsert_texts(
        self,
        collection_name: str,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
    ) -> None:
        col = self.get_or_create_collection(collection_name)
        col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int,
        where: Optional[dict] = None,
    ) -> List[RetrievedChunk]:
        col = self.get_or_create_collection(collection_name)
        res = col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        out: List[RetrievedChunk] = []
        for doc, meta, dist in zip(docs, metas, dists):
            out.append(RetrievedChunk(text=doc, metadata=meta or {}, score=dist))
        return out