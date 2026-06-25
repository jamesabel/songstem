"""Application icon, loaded from the packaged resources."""

from __future__ import annotations

from importlib.resources import files


def icon_path() -> str:
    """Filesystem path to the multi-resolution app icon (.ico)."""
    return str(files("songstem") / "resources" / "songstem.ico")


def app_icon():
    """The application QIcon (Qt imported lazily so this module stays import-light)."""
    from PySide6.QtGui import QIcon

    return QIcon(icon_path())
