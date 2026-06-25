"""Run a separation batch in a child process.

CPU-bound work (Demucs, and the librosa/numba cheat-sheet analysis) holds the GIL, so doing
it on a worker QThread still stalls the GUI event loop. Running it in a separate process gives
it its own GIL, leaving the GUI fully responsive. Results are streamed back over a queue as
small `JobResult` objects (audio stays on disk; only file paths cross the boundary).

`run_jobs` is the process target — it must be importable at module level (Windows spawn).
"""

from __future__ import annotations

from dataclasses import dataclass

# String sentinel (not an object): identity is not preserved across the pickle boundary.
DONE = "__songstem_batch_done__"


@dataclass
class JobFailure:
    """An error that aborted the whole batch (vs. a per-song JobResult.error)."""

    message: str


def make_config(settings) -> dict:
    """The picklable subset of Settings the child needs to rebuild the pipeline."""
    return {
        "backend": settings.backend,
        "device": settings.device,
        "make_cheatsheet": settings.make_cheatsheet,
        "fetch_lyrics": settings.fetch_lyrics,
    }


def run_jobs(jobs, config: dict, queue) -> None:
    """Process every job, putting each JobResult (then DONE) on `queue`. Never raises."""
    try:
        from songstem.pipeline import BatchProcessor
        from songstem.separation import get_backend

        separator = get_backend(config["backend"])
        if hasattr(separator, "device"):
            separator.device = config["device"]

        maker = None
        if config["make_cheatsheet"]:
            from songstem.analysis.session import default_maker

            maker = default_maker(fetch_lyrics=config["fetch_lyrics"])

        BatchProcessor(separator, maker).run(jobs, on_result=queue.put)
    except Exception as exc:  # whole-batch failure (e.g. backend won't load)
        queue.put(JobFailure(str(exc)))
    finally:
        queue.put(DONE)
