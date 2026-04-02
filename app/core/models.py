from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


SourceKind = Literal["supporting_doc", "source_md"]


@dataclass(frozen=True)
class IngestedDoc:
    project: str
    source_path: Path
    markdown_path: Path
    source_kind: SourceKind


@dataclass(frozen=True)
class Chunk:
    project: str
    doc_id: str
    source_path: str
    chunk_id: int
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    score: Optional[float]
    metadata: dict