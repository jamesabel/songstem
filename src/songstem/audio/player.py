"""Playback of generated stem files for the in-app audio player.

Wraps Qt Multimedia so the GUI deals in play/pause/seek rather than media internals. Imports
of PySide are local so this module can be imported in headless contexts.
"""

from __future__ import annotations

from pathlib import Path


class Player:
    """Thin wrapper around QMediaPlayer + QAudioOutput."""

    def __init__(self) -> None:
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

        self._output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._output)

    def load(self, path: Path) -> None:
        from PySide6.QtCore import QUrl

        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def set_volume(self, volume: float) -> None:
        """Set output volume in [0.0, 1.0]."""
        self._output.setVolume(max(0.0, min(1.0, volume)))
