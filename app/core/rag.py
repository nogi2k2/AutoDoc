from __future__ import annotations

from typing import List

from app.core.models import RetrievedChunk


def format_context(chunks: List[RetrievedChunk], max_chars: int = 12000) -> str:
    parts: List[str] = []
    total = 0
    for i, ch in enumerate(chunks, start=1):
        header = f"\n\n---\nCHUNK {i}\nSOURCE: {ch.metadata.get('source_path','')}\n---\n"
        body = (ch.text or "").strip()
        piece = header + body
        if total + len(piece) > max_chars:
            break
        parts.append(piece)
        total += len(piece)
    return "".join(parts).strip()