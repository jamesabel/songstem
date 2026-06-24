"""Application paths and user-tunable settings.

Kept deliberately small for now; persistence (e.g. a QSettings-backed store) can be added
later without changing call sites that read these defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "Songstem"


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
    # Output audio format/container written by audio.io.
    output_format: str = "wav"

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
