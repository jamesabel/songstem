"""QApplication bootstrap."""

from __future__ import annotations

import sys

from songstem.config import Settings


def run() -> int:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from songstem.gui import MainWindow
    from songstem.itunes.library import default_source
    from songstem.utils.ffmpeg import ensure_ffmpeg

    settings = Settings()
    settings.ensure_dirs()

    app = QApplication.instance() or QApplication(sys.argv)

    # ffmpeg is needed to decode iTunes .m4a input; install it if missing. The app still
    # runs without it (WAV/FLAC input works), so this warns rather than blocks.
    status = ensure_ffmpeg()
    if not status.available:
        QMessageBox.warning(
            None,
            "Songstem — ffmpeg not available",
            f"{status.message}\n\n{status.manual_steps}",
        )

    window = MainWindow(settings, default_source())
    if status.available:
        window._log(status.message)
    else:
        window._log("ffmpeg unavailable — Apple Music (.m4a) input will not decode.")
    window.show()
    return app.exec()
