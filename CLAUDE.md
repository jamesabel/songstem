# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current State

**Scaffolded, mostly stubs.** The package, interfaces, build config, and a passing test
suite exist; the heavy pieces (Demucs separation, iTunes COM, the PySide UI) are stubbed
with `NotImplementedError` / `TODO` and are the work to be filled in. `songstem.md` is the
product spec and remains the source of truth for requirements.

### Commands

```pwsh
pip install -e ".[dev]"   # install with dev tools (pytest, ruff)
pytest                    # run all tests
pytest tests/test_mixer.py::test_muted_sums_all_but_target   # single test
ruff check .              # lint
python -m songstem        # launch the GUI (also: the `songstem` gui-script)
```

The dependency-light modules (`audio.mixer`, `utils.naming`, `itunes.FakeLibrary`) are
covered by tests and run without the ML/Qt stack installed.

## Layered architecture

Data flows **iTunes → separation → mixing → output**, orchestrated by `pipeline.batch`.
The design keeps every heavy/platform dependency (PySide, Demucs, win32com, soundfile)
behind a seam so the core logic stays importable and testable in isolation:

- `models.py` — backend-agnostic dataclasses (`Song`, `AudioClip`, `SeparationJob`,
  `JobResult`) and the `StemType` enum. Imports nothing heavy. `AudioClip.samples` is
  `(channels, frames)` float32 — note the I/O layer transposes to/from soundfile's
  `(frames, channels)`.
- `separation/` — the **pluggable backend** seam. `base.Separator` is the ABC; new engines
  register a factory in `registry.py` and are selected by name from `Settings.backend`.
  `demucs_backend` is the default (lazy-imports Demucs inside `separate`).
- `itunes/` — the **playlist source** seam. `library.LibrarySource` is the ABC; `ITunesLibrary`
  is the Windows COM impl (lazy `win32com`), `FakeLibrary` is the in-memory test/dev double.
- `audio/` — `io` (soundfile read/write), `mixer` (pure-NumPy `build_solo` /
  `build_muted_mix`; muted = sum of all stems except the target, with per-stem gains, clipped
  to [-1, 1]), `player` (Qt Multimedia wrapper).
- `pipeline/batch.py` — `BatchProcessor.run` drives jobs one song at a time; per-song failures
  become `JobResult.error` instead of aborting the batch.
- `gui/` + `app.py` + `__main__.py` — PySide bootstrap and main window (scaffold).

### Conventions that matter

- **Heavy/platform imports are local**, not module-level — Demucs, PySide, soundfile, and
  win32com are imported inside the function that needs them. Keep it that way so headless and
  non-Windows environments can still import and test the rest.
- When adding a separation backend, return clips for exactly `supported_stems`, all sharing
  the input's sample rate / channels / frame count so the mixer can sum them directly.

## What This Project Is

A Windows GUI desktop application that automates audio **stem separation** for music practice. Given an **Apple Music / iTunes playlist**, it processes each song in batch and produces, for a selected instrument (bass, guitar, vocals, etc.), two output files per song:

- **Solo** — the selected stem isolated.
- **Muted** — the mix with the selected stem removed/attenuated.

Optimized for instrument/vocal practice and cover-song rehearsal. **Low latency is explicitly a non-goal** — batch processing is acceptable, which should bias design decisions toward correctness and quality over real-time performance.

## Architecture Constraints (from the spec)

These are fixed requirements that shape the design — honor them unless the user changes the spec:

- **Language:** Python.
- **GUI:** PySide is the expected toolkit.
- **Source input:** Apple Music / iTunes on Windows (assume an active subscription and a local install). Playlist name is the unit of input.
- **Stem separation:** Must support pluggable separation backends — design for swappable libraries (e.g. Open-Unmix, Demucs), not a single hardcoded model.
- **Output:** Standard music files written to disk (solo + muted per song). Include an in-app audio player for these outputs, plus per-stem volume adjustment.
- **Dependencies:** Any PyPI library/license is acceptable.
- **Target platform:** Windows on x86 (Intel/AMD), modern capable hardware. Not mobile, not cross-platform.

## Working Notes

- The environment is Windows with PowerShell as the primary shell; a Bash tool is also available for POSIX scripts.
- Because separation backends and the iTunes integration are the two riskiest/most coupled areas, keep them behind clear interfaces so backends can be swapped and the iTunes ingestion can be tested independently of the GUI.
