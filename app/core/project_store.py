from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_VALID_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\- ]{0,80}$")


@dataclass(frozen=True)
class ProjectPaths:
    base_dir: Path
    raw_dir: Path
    markdown_dir: Path
    outputs_dir: Path
    meta_dir: Path


def validate_name(name: str, label: str) -> str:
    name = name.strip()
    if not _VALID_NAME.match(name):
        raise ValueError(f"Invalid {label}. Use letters/numbers/space/_/- and keep it short.")
    return name


def get_paths(projects_dir: Path, document_type: str, project: str) -> ProjectPaths:
    document_type = validate_name(document_type, "document type")
    project = validate_name(project, "project name")

    base = (projects_dir / document_type / project).resolve()
    return ProjectPaths(
        base_dir=base,
        raw_dir=base / "raw",
        markdown_dir=base / "markdown",
        outputs_dir=base / "outputs",
        meta_dir=base / "meta",
    )


def ensure_dirs(paths: ProjectPaths) -> None:
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    paths.markdown_dir.mkdir(parents=True, exist_ok=True)
    paths.outputs_dir.mkdir(parents=True, exist_ok=True)
    paths.meta_dir.mkdir(parents=True, exist_ok=True)