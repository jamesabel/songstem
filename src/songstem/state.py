"""SQLite-backed persistence of GUI selection state via the `pref` library.

Remembers the last-selected playlist and, per playlist, which songs were checked, so the
selection is restored when the app is relaunched. Data lives in a local SQLite database under
the user's app-data directory (managed by `pref`); pass `file_name` to redirect it — used in
tests.

`PrefOrderedSet.get(default=None)` returns the default only when the set was never written, so
"never touched → select all songs by default" stays cleanly distinct from "user unchecked
everything → restore the empty selection". Each access is wrapped in a context manager so the
underlying SQLite handles are closed promptly.
"""

from __future__ import annotations

import hashlib
import json

from attr import attrib, attrs
from pref import Pref, PrefStore

from songstem.config import APP_AUTHOR, APP_NAME
from songstem.models import Song

# Unit separator keeps the artist/title fallback key unambiguous.
_SEP = "\x1f"


def song_key(song: Song) -> str:
    """Stable identity for a song's selection state across relaunches.

    Prefers the iTunes persistent/database id; falls back to artist+title.
    """
    if song.persistent_id:
        return f"id:{song.persistent_id}"
    return f"name:{song.artist}{_SEP}{song.title}"


@attrs
class _GeneralPref(Pref):
    selected_playlist: str = attrib(default="")
    isolate_stem: str = attrib(default="")  # StemType value, e.g. "bass"
    output_dir: str = attrib(default="")
    stem_gains_json: str = attrib(default="")  # JSON {stem_value: percent}
    window_geometry: str = attrib(default="")  # base64 of QMainWindow.saveGeometry()


def _songs_table(playlist: str) -> str:
    # Hash so arbitrary playlist names map to safe, fixed-length SQL table identifiers.
    digest = hashlib.sha1(playlist.encode("utf-8")).hexdigest()[:16]
    return f"songs_{digest}"


class UiStateStore:
    """Reads/writes UI selection state. Every write persists immediately to SQLite."""

    def __init__(self, file_name: str | None = None) -> None:
        self._store = PrefStore(APP_NAME, APP_AUTHOR, file_name)
        self._general = self._store.bind(_GeneralPref)

    # selected playlist -------------------------------------------------

    @property
    def selected_playlist(self) -> str:
        return self._general.selected_playlist

    @selected_playlist.setter
    def selected_playlist(self, name: str) -> None:
        self._general.selected_playlist = name

    # window geometry (base64 of QMainWindow.saveGeometry()) -----------

    @property
    def window_geometry(self) -> str:
        return self._general.window_geometry

    @window_geometry.setter
    def window_geometry(self, value: str) -> None:
        self._general.window_geometry = value

    # separation widget settings ---------------------------------------

    @property
    def isolate_stem(self) -> str:
        """Saved isolate-stem value (e.g. "bass"), or "" if never saved."""
        return self._general.isolate_stem

    @isolate_stem.setter
    def isolate_stem(self, stem: str) -> None:
        self._general.isolate_stem = stem

    @property
    def output_dir(self) -> str:
        """Saved output directory, or "" if never saved."""
        return self._general.output_dir

    @output_dir.setter
    def output_dir(self, path: str) -> None:
        self._general.output_dir = path

    def get_stem_gains(self) -> dict[str, int] | None:
        """Saved per-stem gain percentages, or None if never saved."""
        raw = self._general.stem_gains_json
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        return {str(k): int(v) for k, v in data.items()}

    def set_stem_gains(self, gains: dict[str, int]) -> None:
        self._general.stem_gains_json = json.dumps(gains)

    # selected songs per playlist --------------------------------------

    def get_selected_songs(self, playlist: str) -> list[str] | None:
        """Saved checked-song keys for `playlist`, or None if it was never saved."""
        if not playlist:
            return None
        with self._store.ordered_set(_songs_table(playlist)) as songs:
            return songs.get(default=None)

    def set_selected_songs(self, playlist: str, keys: list[str]) -> None:
        if not playlist:
            return
        with self._store.ordered_set(_songs_table(playlist)) as songs:
            songs.set(keys)
