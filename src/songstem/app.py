"""QApplication bootstrap."""

from __future__ import annotations

import os
import sys

from songstem.config import Settings

# Qt Multimedia's FFmpeg backend prints a one-line version banner and dumps each loaded file's
# stream info ("Input #0 …") to stderr via libav. The `.*` form silences the per-file dump; the
# `.info`/`.debug` forms silence the banner — both are needed. Set before QApplication so Qt
# picks it up; preserve any user-set rules.
_QUIET_FFMPEG_RULES = (
    "qt.multimedia.ffmpeg.*=false"
    ";qt.multimedia.ffmpeg.info=false"
    ";qt.multimedia.ffmpeg.debug=false"
)


def _silence_ffmpeg_logging() -> None:
    existing = os.environ.get("QT_LOGGING_RULES", "")
    if "qt.multimedia.ffmpeg" not in existing:
        os.environ["QT_LOGGING_RULES"] = ";".join(filter(None, [existing, _QUIET_FFMPEG_RULES]))


def _set_windows_app_id() -> None:
    """Give Windows a distinct AppUserModelID so the taskbar uses our icon, not python.exe's."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("abel.co.songstem")
    except Exception:  # pragma: no cover - cosmetic only
        pass


def run() -> int:
    _silence_ffmpeg_logging()
    _set_windows_app_id()
    from PySide6.QtWidgets import QApplication, QMessageBox

    from songstem.gui import MainWindow
    from songstem.icon import app_icon
    from songstem.itunes.library import default_source
    from songstem.utils.ffmpeg import ensure_ffmpeg

    settings = Settings()
    settings.ensure_dirs()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setWindowIcon(app_icon())

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
