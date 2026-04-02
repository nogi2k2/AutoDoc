from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    projects_dir: Path
    chroma_dir: Path

    embedding_model_path: Path
    ollama_model: str

    top_k: int
    chunk_size: int
    chunk_overlap: int

    docling_artifacts_path: Path | None


def load_config(config_path: str | Path) -> AppConfig:
    config_path = Path(config_path)
    cp = configparser.ConfigParser()
    cp.read(config_path, encoding="utf-8")

    project_root = Path(cp["paths"]["project_root"]).expanduser()
    data_dir = (project_root / cp["paths"]["data_dir"]).resolve()
    projects_dir = (project_root / cp["paths"]["projects_dir"]).resolve()
    chroma_dir = (project_root / cp["paths"]["chroma_dir"]).resolve()

    embedding_model_path = Path(cp["models"]["embedding_model_path"]).expanduser()
    ollama_model = cp["models"]["ollama_model"].strip()

    top_k = int(cp["rag"]["top_k"])
    chunk_size = int(cp["rag"]["chunk_size"])
    chunk_overlap = int(cp["rag"]["chunk_overlap"])

    docling_artifacts_path = None
    if cp.has_section("parsing") and cp["parsing"].get("docling_artifacts_path", "").strip():
        docling_artifacts_path = Path(cp["parsing"]["docling_artifacts_path"]).expanduser()

    return AppConfig(
        project_root=project_root,
        data_dir=data_dir,
        projects_dir=projects_dir,
        chroma_dir=chroma_dir,
        embedding_model_path=embedding_model_path,
        ollama_model=ollama_model,
        top_k=top_k,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        docling_artifacts_path=docling_artifacts_path,
    )