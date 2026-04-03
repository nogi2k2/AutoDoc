from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from app.core.config import AppConfig
from app.core.embeddings import EmbeddingModel
from app.core.export import merge_release_document, save_text
from app.core.generation import generate_section, load_document_spec
from app.core.ingestion import ingest_uploaded_files
from app.core.llm import OllamaClient
from app.core.project_store import ensure_dirs, get_paths
from app.core.vectordb import ChromaVectorDB


@dataclass
class SectionState:
    idx: int = 0
    approved: list[tuple[str, str]] = None

    def __post_init__(self):
        if self.approved is None:
            self.approved = []


class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg

        self.embedder = EmbeddingModel(cfg.embedding_model_path)
        self.vectordb = ChromaVectorDB(cfg.chroma_dir)
        self.ollama = OllamaClient()

        self.uploaded_files: list[Path] = []
        self.section_state = SectionState()

        self.setWindowTitle("AutoDoc (POC)")
        self.setMinimumSize(1000, 750)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        row1 = QHBoxLayout()
        layout.addLayout(row1)
        row1.addWidget(QLabel("Project:"))
        self.project_edit = QLineEdit("DemoProject")
        row1.addWidget(self.project_edit)

        row1.addWidget(QLabel("Doc ID:"))
        self.doc_id_edit = QLineEdit("TBD")
        row1.addWidget(self.doc_id_edit)

        row1.addWidget(QLabel("Version:"))
        self.version_edit = QLineEdit("0.1")
        row1.addWidget(self.version_edit)

        row2 = QHBoxLayout()
        layout.addLayout(row2)
        row2.addWidget(QLabel("Document type:"))
        self.doc_type = QComboBox()
        self.doc_type.addItems(["release_document"])
        row2.addWidget(self.doc_type, 1)

        row3 = QHBoxLayout()
        layout.addLayout(row3)

        self.upload_files_btn = QPushButton("Select Files")
        self.upload_files_btn.clicked.connect(self.on_select_files)
        row3.addWidget(self.upload_files_btn)

        self.upload_folder_btn = QPushButton("Select Folder")
        self.upload_folder_btn.clicked.connect(self.on_select_folder)
        row3.addWidget(self.upload_folder_btn)

        self.ingest_btn = QPushButton("Ingest Selected")
        self.ingest_btn.clicked.connect(self.on_ingest)
        row3.addWidget(self.ingest_btn)

        row4 = QHBoxLayout()
        layout.addLayout(row4)

        self.start_btn = QPushButton("Start Section Workflow")
        self.start_btn.clicked.connect(self.on_start_sections)
        row4.addWidget(self.start_btn)

        self.generate_btn = QPushButton("Generate / Regenerate Current Section")
        self.generate_btn.clicked.connect(self.on_generate_current_section)
        row4.addWidget(self.generate_btn)

        self.approve_btn = QPushButton("Approve & Next")
        self.approve_btn.clicked.connect(self.on_approve_next)
        row4.addWidget(self.approve_btn)

        self.skip_btn = QPushButton("Skip (N/A) & Next")
        self.skip_btn.clicked.connect(self.on_skip_next)
        row4.addWidget(self.skip_btn)

        self.finish_btn = QPushButton("Finish & Save Document")
        self.finish_btn.clicked.connect(self.on_finish)
        row4.addWidget(self.finish_btn)

        self.section_label = QLabel("Current section: (not started)")
        layout.addWidget(self.section_label)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.context_view = QTextEdit()
        self.context_view.setReadOnly(True)
        self.context_view.setPlaceholderText("Retrieved Context")
        self.context_view.setFontFamily("Consolas")

        self.editor = QTextEdit()
        self.editor.setFontFamily("Consolas")
        self.editor.setPlaceholderText("Generated Section Content")

        self.splitter.addWidget(self.context_view)
        self.splitter.addWidget(self.editor)
        self.splitter.setSizes([400, 600]) 
        
        layout.addWidget(self.splitter, 1)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(180)
        self.log.setFontFamily("Consolas")
        layout.addWidget(self.log)

    def logln(self, msg: str) -> None:
        self.log.append(msg)

    def _ctx(self):
        document_type = self.doc_type.currentText().strip()
        project = self.project_edit.text().strip() or "DemoProject"
        collection_name = f"{document_type}__{project}"
        paths = get_paths(self.cfg.projects_dir, document_type, project)
        ensure_dirs(paths)
        return document_type, project, collection_name, paths

    def _spec_ctx(self):
        document_type = self.doc_type.currentText().strip()
        spec_path = self.cfg.project_root / "app" / "document_specs" / f"{document_type}.yml"
        prompt_dir = self.cfg.project_root / "app" / "prompt_templates" / document_type
        spec = load_document_spec(spec_path)
        return spec, spec_path, prompt_dir

    def _set_selected(self, files: list[Path], label: str) -> None:
        self.uploaded_files = files
        self.logln(label)
        for f in files:
            self.logln(f"  - {str(f)}")

    def on_select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select input documents",
            str(self.cfg.project_root),
            "Documents (*.md *.markdown *.pdf *.docx *.xlsx);;All Files (*.*)",
        )
        if not files:
            return
        self._set_selected([Path(f) for f in files], "Selected files:")

    def on_select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select input folder",
            str(self.cfg.project_root),
        )
        if not folder:
            return
        # ingestion function only copies direct file paths; expand folder here
        p = Path(folder)
        files = [x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in (".md", ".markdown", ".pdf", ".docx", ".xlsx")]
        if not files:
            QMessageBox.information(self, "No files", "No supported files found in selected folder.")
            return
        self._set_selected(files, f"Selected folder: {folder}\nFiles:")

    def on_ingest(self) -> None:
        if not self.uploaded_files:
            QMessageBox.warning(self, "Nothing selected", "Select files or a folder first.")
            return

        document_type, project, collection_name, paths = self._ctx()

        try:
            counts = ingest_uploaded_files(
                project=project,
                document_type=document_type,
                project_paths=paths,
                uploaded_files=self.uploaded_files,
                embedder=self.embedder,
                vectordb=self.vectordb,
                collection_name=collection_name,
                chunk_size=self.cfg.chunk_size,
                chunk_overlap=self.cfg.chunk_overlap,
                docling_artifacts_path=self.cfg.docling_artifacts_path,
            )
        except Exception as e:
            QMessageBox.critical(self, "Ingestion failed", str(e))
            return

        self.logln(f"Ingestion complete: {counts}")

    def on_start_sections(self) -> None:
        spec, _, _ = self._spec_ctx()
        self.section_state = SectionState(idx=0)
        self._update_section_label(spec)
        self.editor.setPlainText("")
        self.logln("Section workflow started.")

    def _update_section_label(self, spec):
        if self.section_state.idx >= len(spec.sections):
            self.section_label.setText("Current section: (done)")
            return
        sec = spec.sections[self.section_state.idx]
        self.section_label.setText(f"Current section: {sec.title} ({sec.id})")

    def on_generate_current_section(self) -> None:
        _, project, collection_name, _ = self._ctx()
        spec, _, prompt_dir = self._spec_ctx()

        if self.section_state.idx >= len(spec.sections):
            QMessageBox.information(self, "Done", "No more sections.")
            return

        sec = spec.sections[self.section_state.idx]
        template_path = prompt_dir / f"{sec.id}.md"

        variables = {
            "project_name": project,
            "doc_id": self.doc_id_edit.text().strip(),
            "version": self.version_edit.text().strip(),
            "context": "",
        }

        try:
            md, context_used = generate_section( 
                spec_title=spec.title,
                section_title=sec.title,
                template_path=template_path,
                project_name=project,
                vectordb=self.vectordb,
                embedder=self.embedder,
                ollama=self.ollama,
                ollama_model=self.cfg.ollama_model,
                top_k=self.cfg.top_k,
                variables=variables,
            )
        except Exception as e:
            QMessageBox.critical(self, "Generation failed", str(e))
            return

        self.editor.setPlainText(md)
        self.context_view.setPlainText(context_used) 
        self.logln(f"Generated section: {sec.id}")

    def on_approve_next(self) -> None:
        spec, _, _ = self._spec_ctx()
        if self.section_state.idx >= len(spec.sections):
            return
        sec = spec.sections[self.section_state.idx]
        self.section_state.approved.append((sec.title, self.editor.toPlainText()))
        self.section_state.idx += 1
        self.editor.setPlainText("")
        self._update_section_label(spec)

    def on_skip_next(self) -> None:
        spec, _, _ = self._spec_ctx()
        if self.section_state.idx >= len(spec.sections):
            return
        sec = spec.sections[self.section_state.idx]
        self.section_state.approved.append((sec.title, "N/A"))
        self.section_state.idx += 1
        self.editor.setPlainText("")
        self._update_section_label(spec)

    def on_finish(self) -> None:
        document_type, _, _, paths = self._ctx()
        spec, _, _ = self._spec_ctx()

        merged = merge_release_document(spec.title, self.section_state.approved)

        out_dir = paths.outputs_dir / document_type
        out_path = out_dir / "release_document.docx"  
        
        from app.core.export import save_docx 
        
        try:
            save_docx(out_path, merged) 
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return

        self.logln(f"Saved: {out_path}")
        QMessageBox.information(self, "Saved", f"Saved:\n{out_path}")