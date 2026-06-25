"""Run a list of SeparationJobs end to end.

This is the seam between the GUI and the heavy lifting: the GUI builds jobs and hands them
here (off the UI thread), receiving a JobResult per song via the optional progress callback.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from songstem.audio import io, mixer
from songstem.models import JobResult, SeparationJob
from songstem.separation.base import Separator
from songstem.utils.naming import output_filename

if TYPE_CHECKING:
    from songstem.analysis.session import CheatSheetMaker

ProgressCallback = Callable[[JobResult], None]


class BatchProcessor:
    def __init__(
        self,
        separator: Separator,
        cheat_sheet_maker: CheatSheetMaker | None = None,
    ) -> None:
        self._separator = separator
        self._cheat_sheet_maker = cheat_sheet_maker

    def run(
        self,
        jobs: Iterable[SeparationJob],
        on_result: ProgressCallback | None = None,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> list[JobResult]:
        results: list[JobResult] = []
        for job in jobs:
            if should_stop():  # checked between songs so the UI can cancel a long batch
                break
            result = self._run_one(job)
            results.append(result)
            if on_result is not None:
                on_result(result)
        return results

    def _run_one(self, job: SeparationJob) -> JobResult:
        if job.song.location is None:
            return JobResult(job=job, error="song has no local file (cloud-only track)")
        try:
            mix = io.load(job.song.location)
            stems = self._separator.separate(mix)

            solo = mixer.build_solo(stems, job.target)
            muted = mixer.build_muted_mix(stems, job.target, job.stem_gains)

            # Atomic so terminating the batch mid-write never leaves a partial output .wav.
            solo_path = io.save_atomic(solo, job.output_dir / output_filename(job, "solo"))
            muted_path = io.save_atomic(muted, job.output_dir / output_filename(job, "muted"))
            cheatsheet_path = self._make_cheat_sheet(job, solo)
            return JobResult(
                job=job,
                solo_path=solo_path,
                muted_path=muted_path,
                cheatsheet_path=cheatsheet_path,
            )
        except Exception as exc:  # surfaced per-song so one failure doesn't abort the batch
            return JobResult(job=job, error=str(exc))

    def _make_cheat_sheet(self, job: SeparationJob, solo):
        """Best-effort cheat sheet from the in-memory solo; never fails the separation job."""
        if self._cheat_sheet_maker is None:
            return None
        try:
            return self._cheat_sheet_maker.make(solo, job.song, job.target, job.output_dir)
        except Exception:
            return None
