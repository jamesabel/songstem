"""Background worker that runs a batch off the Qt UI thread.

Separation is CPU-heavy and per-song slow, so it must not block the event loop. The worker
emits one `progress` signal per finished song and a final `completed` signal with all
results. The Demucs model is loaded lazily on this thread the first time a song is processed.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from songstem.models import JobResult, SeparationJob
from songstem.pipeline import BatchProcessor
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
