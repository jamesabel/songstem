# Songstem

Real-time instrument removal for Apple Music on Windows. A GUI desktop app that takes an
Apple Music / iTunes playlist and, for a selected instrument or vocal, batch-produces two
files per song:

- **Solo** — the selected stem isolated.
- **Muted** — the mix with the selected stem removed/attenuated.

Built for instrument/vocal practice and cover-song rehearsal. See [`songstem.md`](songstem.md)
for the full specification.

## Requirements

- Windows (x86, Intel/AMD), Python 3.11+
- Apple Music / iTunes installed (used to read playlists)

## Supported audio sources (important)

Songstem can only separate audio it can actually decode, which means **DRM-free** files:

- ✅ CD rips, DRM-free purchases (`.m4a`), and `.mp3` files in your iTunes library
- ❌ **DRM-protected `.m4p` files** — Apple Music subscription downloads and older
  protected iTunes Store purchases use Apple FairPlay encryption (`drms`). Their audio
  stream cannot be decoded by any tool, so they **cannot be separated**. Songstem detects
  these, marks them `(DRM-protected)` in the song list, and skips them.

An active Apple Music subscription does **not** make subscription tracks processable — those
downloads are DRM-protected. To use a protected track, obtain a DRM-free copy of it.

## Setup

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```pwsh
songstem            # via the installed gui-script entry point
# or
python -m songstem
```

## Test & lint

```pwsh
pytest
ruff check .
```

## Project layout

```
src/songstem/
  __main__.py      Application entry point (boots the PySide app)
  app.py           QApplication bootstrap
  config.py        Paths and user settings
  models.py        Core data types (Song, AudioClip, SeparationJob)
  itunes/          Apple Music / iTunes playlist access (COM automation)
  separation/      Pluggable stem-separation backends (ABC + registry + Demucs)
  audio/           Audio I/O, solo/mute mixing, and playback
  pipeline/        Batch job orchestration
  gui/             PySide windows and widgets
tests/             Unit tests
```
