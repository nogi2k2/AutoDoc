from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.core.config import load_config
from app.gui.main_window import MainWindow


def main() -> int:
    cfg = load_config(Path("config") / "app.ini")
    app = QApplication(sys.argv)
    w = MainWindow(cfg)
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())