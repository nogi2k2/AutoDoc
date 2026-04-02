from __future__ import annotations

from typing import List


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    chunks: List[str] = []
    start = 0
    n = len(text)
    step = chunk_size - chunk_overlap

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks