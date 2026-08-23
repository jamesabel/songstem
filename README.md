# Songstem

Instrument removal for Apple Music on Windows. A GUI desktop app that takes an
Apple Music / iTunes playlist and, for a selected instrument or vocal, batch-produces two
files per song:

- **Solo** — the selected stem isolated.
- **Muted** — the mix with the selected stem removed/attenuated.

Built for instrument/vocal practice and cover-song rehearsal. See [`songstem.md`](songstem.md)
for the full specification.

## Requirements

- Windows (x86, Intel/AMD), **Python 3.11+** (use the regular CPython build, not the
  free-threaded `3.14t`)
- Apple Music / iTunes installed (used to read playlists)
- **ffmpeg** — needed to decode iTunes/Apple Music `.m4a` (AAC/ALAC) input; WAV/FLAC work
  without it. On startup songstem checks for it and, if missing, attempts a non-interactive
  `winget install Gyan.FFmpeg`; if that fails it shows manual install steps.

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

If a track is captured as silence, songstem discards it and stops the run rather than
re-recording the whole playlist into empty files — a silent capture means audio isn't reaching
the recording device (routing, or RDP — see below). Re-recording is **resumable**: a track is skipped if its output WAV already exists, has
real audio, and is long enough (compared to the iTunes track length, or ≥1s if unknown). Each
file is written atomically (temp file, then moved into place), so a crash or shutdown never
leaves a partial file — the next run simply re-records whatever isn't complete.

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

## Cheat sheets

After each separation, songstem writes a one-page Markdown **cheat sheet** next to the solo
stem (`Artist - Title [bass cheatsheet].md`) with the song's **key**, **tempo**, scale, and —
for monophonic stems (bass, vocals) — the **note patterns** and a **lyrics-with-notes** table
mapping the notes to what's being sung. Polyphonic stems (guitar/piano/other) get a reduced
sheet (key/tempo/scale only), since per-note detection isn't reliable for them.

Lyrics are fetched best-effort over the network (synced lyrics, personal-use) and silently
omitted if unavailable. Note/key accuracy is best on clean isolated bass/vocals. Disable the
feature or lyric fetching via `Settings.make_cheatsheet` / `Settings.fetch_lyrics`.

## Pitch shifting

Each song in the list has an optional **Pitch** control (in half-steps, −12…+12) — ½ step = ±1,
a full step = ±2. Set a non-zero value for the songs you want transposed, make sure they are
**checked**, and click **"Create pitch-shifted WAVs"** to write a new transposed copy next to
each song's source file, with the shift in the name, e.g. `Artist - Title [+2st].wav` /
`[-1st]`. Unchecked songs and songs left at 0 are skipped, so nothing is written unless you
ask for it.

Handy for practicing in a comfortable key or matching an alternate tuning. The shift applies to
the song's resolved source (its DRM-free original, or a re-recorded WAV) and runs in the
background; finished files are added to the built-in player so you can audition them. Each per-song
setting is remembered between launches. This is independent of separation — the pitch-shifted WAVs
are written to disk only; to separate one, load its folder as the source and press **Run**.

## Setup

Easiest — creates `.venv` with **Python 3.14** and installs everything:

```pwsh
.\setup_venv.bat
```

Or manually (use the regular build, **not** the free-threaded `3.14t`):

```pwsh
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```pwsh
songstem            # via the installed gui-script entry point
# or
python -m songstem
```

## Using the app

1. **Pick a playlist** at the top. Songstem lists its songs in the playlist's iTunes order;
   check the ones to process (**Select all** / **Select none** help). Songs with no usable
   audio (DRM-protected, cloud-only) are greyed out with a tooltip explaining what to do.
2. **Choose the stem** to isolate and adjust the per-stem **muted-mix levels**.
3. Press **Run**. Separation runs in a background process so the window stays responsive; the
   progress bar shows `N / M songs`. Press **Stop** to cancel.
4. Each song yields a **solo** and a **muted** WAV (plus a cheat sheet) in the output folder —
   preview them in the built-in player. Your selections, output folder, and window
   size/position are remembered between launches.

Optionally set a per-song **Pitch** (half-steps) and click **"Create pitch-shifted WAVs"** to
write transposed copies — see [Pitch shifting](#pitch-shifting) above.

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
  models.py        Core data types (Song, AudioClip, SeparationJob, JobResult)
  state.py         SQLite-backed persistence of UI state (via the `pref` library)
  icon.py          Application icon loader
  itunes/          Apple Music / iTunes playlist access + playback (COM automation)
  folder_source.py LibrarySource over a folder of audio files (recorded WAVs, CD rips)
  separation/      Pluggable stem-separation backends (ABC + registry + Demucs)
  audio/           Audio I/O (incl. atomic + DRM detection), solo/mute mixing, pitch shift, playback
  pipeline/        Batch orchestration; runs separation in a subprocess
  recording/       Loopback re-recording of playlists to DRM-free WAVs
  analysis/        Key/tempo/note analysis and cheat-sheet generation
  utils/           Filename helpers, ffmpeg detection/install
  gui/             PySide windows, widgets, and worker threads
  resources/       App icon (svg/ico/png)
scripts/           Dev scripts (e.g. generate_icon.py)
tests/             Unit tests
```
