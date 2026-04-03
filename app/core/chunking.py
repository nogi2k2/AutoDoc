from __future__ import annotations
from typing import List
import re

def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    blocks = re.split(r'\n\n+', text)
    
    chunks: List[str] = []
    current_chunk = []
    current_length = 0

    for block in blocks:
        block_len = len(block)
        
        if current_length + block_len > chunk_size and current_length > 0:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_length = 0
        
        current_chunk.append(block)
        current_length += block_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks