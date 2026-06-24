"""Persistence layer tests — isolated to a temp SQLite DB via file_name."""

from songstem.models import Song
from songstem.state import UiStateStore, song_key


def _store(tmp_path):
    return UiStateStore(file_name=str(tmp_path / "state.db"))


def test_song_key_prefers_persistent_id():
    assert song_key(Song(title="T", artist="A", persistent_id="42")) == "id:42"
    assert song_key(Song(title="T", artist="A")).startswith("name:A")


def test_selected_playlist_round_trips(tmp_path):
    db = str(tmp_path / "state.db")
    UiStateStore(file_name=db).selected_playlist = "Practice"
    # A fresh instance (simulating relaunch) reads it back.
    assert UiStateStore(file_name=db).selected_playlist == "Practice"


def test_unsaved_playlist_returns_none(tmp_path):
    assert _store(tmp_path).get_selected_songs("Never") is None


def test_selected_songs_round_trip(tmp_path):
    db = str(tmp_path / "state.db")
    UiStateStore(file_name=db).set_selected_songs("Practice", ["id:1", "id:3"])
    assert UiStateStore(file_name=db).get_selected_songs("Practice") == ["id:1", "id:3"]


def test_empty_selection_is_distinct_from_unsaved(tmp_path):
    # Saving an empty selection must be remembered as empty, not treated as "never saved".
    store = _store(tmp_path)
    store.set_selected_songs("Practice", [])
    assert store.get_selected_songs("Practice") == []
    assert store.get_selected_songs("Other") is None


def test_default_playlist_is_empty(tmp_path):
    assert _store(tmp_path).selected_playlist == ""
