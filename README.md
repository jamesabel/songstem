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

## Loopback re-recording (personal use)

For tracks you can play but not decode, songstem can **re-record an entire playlist** into
DRM-free WAVs by capturing playback through a virtual audio cable, then load those WAVs as the
separation source. This records audio output as it plays — it does **not** remove DRM — and is
intended for **personal use only, not redistribution**.

One-time setup:

1. Install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) (free).
2. Route iTunes' audio into the cable: Windows **Settings → System → Sound → Volume mixer**,
   set iTunes' output device to **CABLE Input** (or set CABLE Input as the system default
   output). To still hear playback, enable "Listen to this device" on **CABLE Output**, or use
   VB-Audio Voicemeeter.
3. Set iTunes volume to 100% and disable any sound enhancements.

Then in songstem: select the playlist and click **"Re-record playlist → WAV (loopback)"**.
Each track is played start-to-finish and captured to `…/output/recordings/<playlist>/`. When
it finishes, that folder is loaded as the active source — select it and press **Run** to
separate. (Capture is real-time, so a playlist takes about as long as its total runtime.)

If a track is captured as silence, songstem flags it rather than saving an empty file — see
below.

### Recording over Remote Desktop (RDP)

RDP redirects the remote machine's audio to your **local** client by default, making
"Remote Audio" the default playback device. iTunes then plays into the RDP channel instead of
the cable, so captures come out **silent**. To record over RDP:

1. In the Remote Desktop client *before connecting*: **Local Resources → Remote audio →
   Settings → "Play on remote computer."**
2. On the remote machine, route iTunes to the cable — either set the **default** playback
   device to **CABLE Input (VB-Audio)**, or per-app in **Settings → Sound → Volume mixer →
   iTunes → Output → CABLE Input**.

(Routing iTunes specifically to CABLE Input is what matters; it must not be playing to
"Remote Audio".)

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
