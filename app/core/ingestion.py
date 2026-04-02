from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Sequence, Union

from parser_lib import DocumentParser

from app.core.chunking import chunk_text
from app.core.embeddings import EmbeddingModel
from app.core.project_store import ProjectPaths, ensure_dirs
from app.core.vectordb import ChromaVectorDB


PathLike = Union[str, Path]


def _is_markdown(p: Path) -> bool:
    return p.suffix.lower() in (".md", ".markdown")


def _is_supporting_doc(p: Path) -> bool:
    return p.suffix.lower() in (".docx", ".pdf", ".xlsx")


def _copy_uploads_into(raw_dir: Path, uploads: Sequence[PathLike]) -> List[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    copied: List[Path] = []
    for item in uploads:
        src = Path(item)
        if not src.is_file():
            continue
        dst = raw_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def ingest_uploaded_files(
    *,
    project: str,
    document_type: str,
    project_paths: ProjectPaths,
    uploaded_files: Sequence[PathLike],
    embedder: EmbeddingModel,
    vectordb: ChromaVectorDB,
    collection_name: str,
    chunk_size: int,
    chunk_overlap: int,
    docling_artifacts_path: PathLike | None = None,
) -> dict:
    ensure_dirs(project_paths)

    copied = _copy_uploads_into(project_paths.raw_dir, uploaded_files)

    md_inputs = [p for p in copied if _is_markdown(p)]
    support_inputs = [p for p in copied if _is_supporting_doc(p)]

    counts = {
        "uploads_copied": len(copied),
        "markdown_inputs": len(md_inputs),
        "supporting_inputs": len(support_inputs),
        "markdown_docs_ingested": 0,
        "supporting_docs_parsed": 0,
        "supporting_markdown_ingested": 0,
        "chunks_upserted": 0,
    }

    # Ingest uploaded markdown directly
    c1 = _ingest_markdown_files(
        project=project,
        document_type=document_type,
        project_paths=project_paths,
        md_files=md_inputs,
        embedder=embedder,
        vectordb=vectordb,
        collection_name=collection_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        source_kind="source_md",
        copy_into_markdown_dir=True,
    )
    counts["markdown_docs_ingested"] += c1["docs"]
    counts["chunks_upserted"] += c1["chunks"]

    # Parse supporting docs -> markdown -> ingest
    if support_inputs:
        parsed_dir = project_paths.markdown_dir / "_parsed"
        parsed_dir.mkdir(parents=True, exist_ok=True)

        parser = DocumentParser(
            output_dir=str(parsed_dir),
            artifacts_path=str(docling_artifacts_path) if docling_artifacts_path else None,
        )

        for f in support_inputs:
            parser.parse(str(f))
            counts["supporting_docs_parsed"] += 1

        parsed_md = [p for p in parsed_dir.rglob("*") if p.is_file() and _is_markdown(p)]
        c2 = _ingest_markdown_files(
            project=project,
            document_type=document_type,
            project_paths=project_paths,
            md_files=parsed_md,
            embedder=embedder,
            vectordb=vectordb,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            source_kind="supporting_doc",
            copy_into_markdown_dir=False,
        )
        counts["supporting_markdown_ingested"] += c2["docs"]
        counts["chunks_upserted"] += c2["chunks"]

    return counts


def _ingest_markdown_files(
    *,
    project: str,
    document_type: str,
    project_paths: ProjectPaths,
    md_files: List[Path],
    embedder: EmbeddingModel,
    vectordb: ChromaVectorDB,
    collection_name: str,
    chunk_size: int,
    chunk_overlap: int,
    source_kind: str,
    copy_into_markdown_dir: bool,
) -> dict:
    upsert_ids: List[str] = []
    upsert_texts: List[str] = []
    upsert_metas: List[dict] = []

    docs_ingested = 0
    chunks_ingested = 0

    for p in md_files:
        if not p.exists() or not _is_markdown(p):
            continue

        md_path = p
        if copy_into_markdown_dir:
            dst = project_paths.markdown_dir / p.name
            shutil.copy2(p, dst)
            md_path = dst

        text = md_path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            continue

        doc_id = md_path.stem
        for i, ch in enumerate(chunks):
            cid = f"{doc_id}::chunk::{i}"
            upsert_ids.append(cid)
            upsert_texts.append(ch)
            upsert_metas.append(
                {
                    "document_type": document_type,
                    "project": project,
                    "doc_id": doc_id,
                    "chunk_id": i,
                    "source_path": str(md_path),
                    "source_kind": source_kind,
                }
            )
            chunks_ingested += 1

        docs_ingested += 1

    if upsert_texts:
        vectors = embedder.embed(upsert_texts)
        vectordb.upsert_texts(
            collection_name=collection_name,
            ids=upsert_ids,
            texts=upsert_texts,
            embeddings=vectors,
            metadatas=upsert_metas,
        )

    return {"docs": docs_ingested, "chunks": chunks_ingested}