"""QApplication bootstrap."""

from __future__ import annotations

import sys

from songstem.config import Settings


def run() -> int:
    from PySide6.QtWidgets import QApplication

    from songstem.gui import MainWindow

    settings = Settings()
    settings.ensure_dirs()

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(settings)
    window.show()
    return app.exec()
