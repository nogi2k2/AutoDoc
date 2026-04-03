import configparser
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:
    # paths
    project_root: Path
    data_dir: Path
    projects_dir: Path
    chroma_dir: Path
    
    # app
    default_project: str
    
    # models
    embedding_model_path: str
    ollama_model: str
    
    # rag
    top_k: int
    
    # parsing
    docling_artifacts_path: str

def load_config(ini_path: Path) -> AppConfig:
    parser = configparser.ConfigParser()
    parser.read(ini_path)

    root = Path(parser.get("paths", "project_root"))

    return AppConfig(
        project_root=root,
        data_dir=root / parser.get("paths", "data_dir"),
        projects_dir=root / parser.get("paths", "projects_dir"),
        chroma_dir=root / parser.get("paths", "chroma_dir"),
        default_project=parser.get("app", "default_project", fallback="DemoProject"),
        embedding_model_path=parser.get("models", "embedding_model_path"),
        ollama_model=parser.get("models", "ollama_model"),
        top_k=parser.getint("rag", "top_k"),
        docling_artifacts_path=parser.get("parsing", "docling_artifacts_path"),
    )