"""Background worker that runs a batch off the Qt UI thread.

Separation is CPU-heavy and per-song slow, so it must not block the event loop. The worker
emits one `progress` signal per finished song and a final `completed` signal with all
results. The Demucs model is loaded lazily on this thread the first time a song is processed.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from songstem.itunes.playback import PlaybackController
from songstem.models import JobResult, SeparationJob
from songstem.pipeline import BatchProcessor
from songstem.recording import Recorder, record_playlist
from songstem.separation.base import Separator


class BatchWorker(QThread):
    progress = Signal(object)  # JobResult, emitted per song
    completed = Signal(list)  # list[JobResult], emitted once at the end
    failed = Signal(str)  # unexpected error that aborted the whole batch

    def __init__(
        self,
        separator: Separator,
        jobs: list[SeparationJob],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._separator = separator
        self._jobs = jobs

    def run(self) -> None:  # executed on the worker thread
        try:
            processor = BatchProcessor(self._separator)
            results: list[JobResult] = processor.run(
                self._jobs, on_result=self.progress.emit
            )
            self.completed.emit(results)
        except Exception as exc:  # pragma: no cover - GUI-thread safety net
            self.failed.emit(str(exc))


class RecordWorker(QThread):
    """Runs a batch loopback re-recording off the UI thread."""

    started_track = Signal(object, int, int)  # (Song, index, total) before each capture
    progress = Signal(object)  # RecordResult, emitted per track
    completed = Signal(list)  # list[RecordResult]
    failed = Signal(str)

    def __init__(
        self,
        controller: PlaybackController,
        recorder: Recorder,
        playlist_name: str,
        output_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._recorder = recorder
        self._playlist_name = playlist_name
        self._output_dir = output_dir

    def run(self) -> None:  # executed on the worker thread
        # iTunes is driven over COM, which must be initialized on *this* thread (Qt does not
        # do it for worker QThreads). Without this, every track.Play() raises
        # "CoInitialize has not been called".
        try:
            import pythoncom

            pythoncom.CoInitialize()
            com_initialized = True
        except Exception:  # pragma: no cover - non-Windows / no pywin32
            com_initialized = False
        try:
            results = record_playlist(
                self._controller,
                self._recorder,
                self._playlist_name,
                self._output_dir,
                on_result=self.progress.emit,
                on_track_start=lambda song, i, n: self.started_track.emit(song, i, n),
                should_stop=self.isInterruptionRequested,
            )
            self.completed.emit(results)
        except Exception as exc:  # pragma: no cover - GUI-thread safety net
            self.failed.emit(str(exc))
        finally:
            if com_initialized:
                import pythoncom

                pythoncom.CoUninitialize()
