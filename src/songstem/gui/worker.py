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
        jobs: list[SeparationJob],
        config: dict,
        *,
        separator: Separator | None = None,  # in-thread fallback only
        cheat_sheet_maker=None,  # in-thread fallback only
        use_subprocess: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BatchWorker")  # so a "Destroyed while running" warning names it
        self._jobs = jobs
        self._config = config
        self._separator = separator
        self._cheat_sheet_maker = cheat_sheet_maker
        self._use_subprocess = use_subprocess

    def run(self) -> None:  # executed on the worker thread
        try:
            if self._use_subprocess:
                results = self._run_in_subprocess()
            else:
                results = self._run_in_thread()
            if results is not None:  # None means already reported via `failed`
                self.completed.emit(results)
        except Exception as exc:  # pragma: no cover - GUI-thread safety net
            self.failed.emit(str(exc))

    def _run_in_thread(self) -> list[JobResult]:
        processor = BatchProcessor(self._separator, self._cheat_sheet_maker)
        return processor.run(
            self._jobs, on_result=self.progress.emit, should_stop=self.isInterruptionRequested
        )

    def _run_in_subprocess(self) -> list[JobResult] | None:
        import multiprocessing as mp
        from queue import Empty

        from songstem.pipeline.process_runner import DONE, JobFailure, run_jobs

        ctx = mp.get_context("spawn")
        queue = ctx.Queue()
        proc = ctx.Process(
            target=run_jobs, args=(self._jobs, self._config, queue), daemon=True
        )
        proc.start()
        results: list[JobResult] = []
        try:
            while True:
                if self.isInterruptionRequested():
                    proc.terminate()
                    return results
                try:
                    item = queue.get(timeout=0.2)
                except Empty:
                    continue  # keep checking for interruption
                if item == DONE:
                    return results
                if isinstance(item, JobFailure):
                    self.failed.emit(item.message)
                    return None
                results.append(item)
                self.progress.emit(item)
        finally:
            if proc.is_alive():
                proc.terminate()
            proc.join(5)


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
        self.setObjectName("RecordWorker")  # names it in any QThread warning
        self._controller = controller
        self._recorder = recorder
        self._playlist_name = playlist_name
        self._output_dir = output_dir

    def run(self) -> None:  # executed on the worker thread
        try:
            import pythoncom  # Windows only; absent elsewhere
        except ImportError:  # pragma: no cover - non-Windows / no pywin32
            pythoncom = None
        try:
            # iTunes is driven over COM, which must be initialized on *this* thread (Qt does
            # not do it for worker QThreads) or every track.Play() raises "CoInitialize has
            # not been called". A real CoInitialize failure surfaces via the `failed` signal.
            if pythoncom is not None:
                pythoncom.CoInitialize()
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
        except Exception as exc:  # boundary catch-all: report rather than kill the thread
            self.failed.emit(str(exc))
        finally:
            if pythoncom is not None:
                pythoncom.CoUninitialize()
