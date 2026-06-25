"""Application paths and user-tunable settings.

Kept deliberately small for now; persistence (e.g. a QSettings-backed store) can be added
later without changing call sites that read these defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "Songstem"
APP_AUTHOR = "abel.co"  # used by `pref` to locate the SQLite state DB


def _default_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME


@dataclass
class Settings:
    """Runtime configuration. Defaults target a single-user Windows install."""

    # Where generated solo/muted files are written.
    output_dir: Path = field(default_factory=lambda: _default_root() / "output")
    # Cache directory for downloaded separation models.
    model_dir: Path = field(default_factory=lambda: _default_root() / "models")
    # Name of the registered separation backend to use (see separation.registry).
    backend: str = "demucs"
    # Torch device for separation. "cpu" for broad compatibility (default); set to
    # "cuda" once a capable GPU + CUDA torch build are available. Low latency is a
    # non-goal, so CPU batch processing is acceptable.
    device: str = "cpu"
    # Output audio format/container written by audio.io.
    output_format: str = "wav"
    # Generate a player cheat-sheet (.md) next to each solo stem after separation.
    make_cheatsheet: bool = True
    # Download synced lyrics (network) for the cheat sheet's lyrics+notes section.
    fetch_lyrics: bool = True

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
