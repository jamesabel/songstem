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


def test_separation_settings_round_trip(tmp_path):
    db = str(tmp_path / "state.db")
    s = UiStateStore(file_name=db)
    s.isolate_stem = "bass"
    s.output_dir = r"C:\out"
    s.set_stem_gains({"bass": 0, "vocals": 80})

    again = UiStateStore(file_name=db)  # simulate relaunch
    assert again.isolate_stem == "bass"
    assert again.output_dir == r"C:\out"
    assert again.get_stem_gains() == {"bass": 0, "vocals": 80}


def test_separation_settings_default_unset(tmp_path):
    s = _store(tmp_path)
    assert s.isolate_stem == ""
    assert s.output_dir == ""
    assert s.get_stem_gains() is None


def test_pitch_shifts_round_trip_per_playlist(tmp_path):
    db = str(tmp_path / "state.db")
    UiStateStore(file_name=db).set_pitch_shifts("Practice", {"id:1": 2, "id:2": -1})
    again = UiStateStore(file_name=db)  # simulate relaunch
    assert again.get_pitch_shifts("Practice") == {"id:1": 2, "id:2": -1}
    assert again.get_pitch_shifts("Other") == {}  # isolated per playlist


def test_pitch_shifts_default_empty(tmp_path):
    assert _store(tmp_path).get_pitch_shifts("Never") == {}


def test_pitch_shifts_drop_zero_entries(tmp_path):
    # Zero means "no shift" — it must not be persisted, so it defaults back to 0 on reload.
    store = _store(tmp_path)
    store.set_pitch_shifts("Practice", {"id:1": 0, "id:2": 3})
    assert store.get_pitch_shifts("Practice") == {"id:2": 3}


def test_window_geometry_round_trips(tmp_path):
    db = str(tmp_path / "state.db")
    assert UiStateStore(file_name=db).window_geometry == ""  # default
    UiStateStore(file_name=db).window_geometry = "AAAA1234=="
    assert UiStateStore(file_name=db).window_geometry == "AAAA1234=="
