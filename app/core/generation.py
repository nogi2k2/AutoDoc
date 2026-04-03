from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from app.core.embeddings import EmbeddingModel
from app.core.llm import OllamaClient
from app.core.rag import format_context
from app.core.vectordb import ChromaVectorDB


@dataclass(frozen=True)
class DocSectionSpec:
    id: str
    title: str


@dataclass(frozen=True)
class DocumentSpec:
    document_type: str
    title: str
    sections: List[DocSectionSpec]


def load_document_spec(path: Path) -> DocumentSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sections = [DocSectionSpec(id=s["id"], title=s["title"]) for s in data["sections"]]
    return DocumentSpec(
        document_type=data["document_type"],
        title=data.get("title", data["document_type"]),
        sections=sections,
    )


def render_prompt_template(template_text: str, variables: Dict[str, str]) -> str:
    out = template_text
    for k, v in variables.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def generate_section(
    *,
    spec_title: str,
    section_title: str,
    template_path: Path,
    project_name: str,
    vectordb: ChromaVectorDB,
    embedder: EmbeddingModel,
    ollama: OllamaClient,
    ollama_model: str,
    top_k: int,
    variables: Dict[str, str],
) -> Tuple[str, str]:
    if not template_path.exists():
        raise FileNotFoundError(f"Missing prompt template: {template_path}")

    template = template_path.read_text(encoding="utf-8", errors="ignore")

    query_text = f"{spec_title} - {section_title}: generate this section based on available context."
    q_emb = embedder.embed([query_text])[0]
    
    project_collections = vectordb.get_project_collections(project_name)
    all_retrieved = []
    for col in project_collections:
        all_retrieved.extend(vectordb.query(collection_name=col, query_embedding=q_emb, top_k=top_k))
    
    all_retrieved.sort(key=lambda x: x.score if x.score is not None else float('inf'))
    best_retrieved = all_retrieved[:top_k]

    formatted_context = format_context(best_retrieved)
    variables = dict(variables)
    variables["context"] = formatted_context

    prompt = render_prompt_template(template, variables)

    system = (
        "You are a technical documentation assistant for regulated software tool documentation.\n"
        "Output Markdown only."
    )
    generated_md = ollama.generate_markdown_only(
        model=ollama_model,
        system=system,
        prompt=prompt,
    )
    
    return generated_md, formatted_context