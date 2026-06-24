"""Detect (and, on Windows, best-effort install) the ffmpeg binary.

ffmpeg is needed to decode iTunes/Apple Music input (AAC/ALAC in `.m4a`). It is a native
binary, not a pip package, so it can't be pulled in by `pip install`. The app still runs
without it — WAV/FLAC input works — but compressed input will fail until ffmpeg is present.

`ensure_ffmpeg()` checks PATH, tries a non-interactive winget install if missing, rescans
the locations winget drops the binary, and otherwise hands back manual steps for the user.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Gyan.dev is the package winget resolves for "ffmpeg" and the standard Windows build.
_WINGET_ID = "Gyan.FFmpeg"
_MANUAL_STEPS = (
    "ffmpeg is required to read Apple Music / iTunes (.m4a) files.\n\n"
    "Install it one of these ways, then restart Songstem:\n"
    f"  • winget install -e --id {_WINGET_ID}\n"
    "  • Download a build from https://www.gyan.dev/ffmpeg/builds/ and add its\n"
    "    'bin' folder (containing ffmpeg.exe) to your PATH.\n"
    "  • If you use Chocolatey: choco install ffmpeg"
)


@dataclass
class FfmpegStatus:
    available: bool
    path: str | None = None
    # Human-readable note about what happened (installed, found, failed, ...).
    message: str = ""
    # Non-empty only when the user must act manually.
    manual_steps: str = ""


def find_ffmpeg() -> str | None:
    """Return the path to ffmpeg if it can be located, else None.

    Checks PATH first, then the directories winget drops binaries into (which the current
    process's PATH won't reflect until a restart).
    """
    found = shutil.which("ffmpeg")
    if found:
        return found

    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    base = Path(local) / "Microsoft" / "WinGet"
    candidates = [base / "Links" / "ffmpeg.exe"]
    candidates += list((base / "Packages").glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _add_to_path(ffmpeg_path: str) -> None:
    """Expose ffmpeg's directory on PATH for this process so subprocesses find it."""
    directory = str(Path(ffmpeg_path).parent)
    current = os.environ.get("PATH", "")
    if directory not in current.split(os.pathsep):
        os.environ["PATH"] = directory + os.pathsep + current


def _winget_install() -> bool:
    """Attempt a non-interactive winget install. Returns True if winget reported success."""
    if shutil.which("winget") is None:
        return False
    try:
        completed = subprocess.run(
            [
                "winget", "install", "-e", "--id", _WINGET_ID,
                "--accept-package-agreements", "--accept-source-agreements",
                "--disable-interactivity",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    # winget returns 0 on install and a non-zero "already installed / no upgrade" code too;
    # treat a located binary afterward as the real success signal, so just don't hard-fail here.
    return completed.returncode == 0


def ensure_ffmpeg(auto_install: bool = True) -> FfmpegStatus:
    """Ensure ffmpeg is usable, installing it on Windows if needed.

    Idempotent and safe to call at startup. Never raises; reports outcome via FfmpegStatus.
    """
    path = find_ffmpeg()
    if path:
        _add_to_path(path)
        return FfmpegStatus(available=True, path=path, message=f"ffmpeg found: {path}")

    if not auto_install:
        return FfmpegStatus(
            available=False,
            message="ffmpeg not found.",
            manual_steps=_MANUAL_STEPS,
        )

    installed = _winget_install()
    path = find_ffmpeg()  # rescan regardless of winget's exit code
    if path:
        _add_to_path(path)
        note = "ffmpeg installed via winget." if installed else "ffmpeg located after install."
        return FfmpegStatus(available=True, path=path, message=f"{note} ({path})")

    reason = (
        "winget install did not complete." if not installed else
        "ffmpeg installed but could not be located on PATH; a restart may be needed."
    )
    return FfmpegStatus(available=False, message=reason, manual_steps=_MANUAL_STEPS)
