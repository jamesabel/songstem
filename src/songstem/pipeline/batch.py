"""Run a list of SeparationJobs end to end.

This is the seam between the GUI and the heavy lifting: the GUI builds jobs and hands them
here (off the UI thread), receiving a JobResult per song via the optional progress callback.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from songstem.audio import io, mixer
from songstem.models import JobResult, SeparationJob
from songstem.separation.base import Separator
from songstem.utils.naming import output_filename

ProgressCallback = Callable[[JobResult], None]


class BatchProcessor:
    def __init__(self, separator: Separator) -> None:
        self._separator = separator

    def run(
        self,
        jobs: Iterable[SeparationJob],
        on_result: ProgressCallback | None = None,
    ) -> list[JobResult]:
        results: list[JobResult] = []
        for job in jobs:
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

            solo_path = io.save(solo, job.output_dir / output_filename(job, "solo"))
            muted_path = io.save(muted, job.output_dir / output_filename(job, "muted"))
            return JobResult(job=job, solo_path=solo_path, muted_path=muted_path)
        except Exception as exc:  # surfaced per-song so one failure doesn't abort the batch
            return JobResult(job=job, error=str(exc))
