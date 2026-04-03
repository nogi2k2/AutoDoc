from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import pypandoc

def merge_release_document(title: str, sections: List[Tuple[str, str]]) -> str:
    parts: List[str] = [f"# {title}\n"]
    for section_title, section_md in sections:
        parts.append(f"\n\n## {section_title}\n\n{(section_md or '').strip()}\n")
    return "".join(parts).strip() + "\n"

def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def save_docx(path: Path, markdown_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pypandoc.convert_text(markdown_text, 'docx', format='md', outputfile=str(path))