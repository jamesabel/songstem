"""Main application window.

Scaffold only: lays out the primary regions (playlist picker, stem selector, run controls,
output player) without wiring behavior. Heavy work must run off the Qt thread — see
gui/worker.py — so the UI stays responsive during batch separation.
"""

from __future__ import annotations

from songstem.config import Settings


class MainWindow:  # will subclass QMainWindow once the UI is built out
    def __init__(self, settings: Settings) -> None:
        from PySide6.QtWidgets import QMainWindow

        self.settings = settings
        self._window = QMainWindow()
        self._window.setWindowTitle("Songstem")
        self._build_ui()

    def _build_ui(self) -> None:
        # TODO: playlist combo (LibrarySource.playlist_names), song list, stem-type
        # selector (StemType), per-stem gain sliders, Run button, progress list, and an
        # embedded player (audio.player.Player).
        pass

    def show(self) -> None:
        self._window.show()
