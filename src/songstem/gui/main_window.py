"""Main application window.

Layout: a playlist/song picker on the left, separation controls on the right, and a
progress log plus an output player along the bottom. Batch work runs on a BatchWorker
thread so the UI stays responsive; the separator is built only when Run is pressed so
torch/Demucs are not imported at startup.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from dataclasses import replace

from songstem.audio.io import is_drm_protected
from songstem.audio.player import Player
from songstem.config import Settings
from songstem.folder_source import FolderLibrary
from songstem.gui.worker import BatchWorker, RecordWorker
from songstem.itunes.library import LibrarySource
from songstem.itunes.playback import ITunesPlaybackController
from songstem.models import JobResult, SeparationJob, Song, StemType
from songstem.recording.loopback import LoopbackRecorder
from songstem.recording.session import wav_filename
from songstem.separation import get_backend
from songstem.state import UiStateStore, song_key
from songstem.utils.naming import sanitize

_RECORD_LABEL = "Re-record playlist → WAV (loopback)"
# Item data role holding the resolved audio source path (str), or None if unavailable.
_SOURCE_ROLE = Qt.UserRole + 1
_NEEDS_AUDIO_TOOLTIP = (
    "No usable audio for this song. Either add a DRM-free version of it to your library, "
    "or use “Re-record playlist → WAV (loopback)” to capture it first."
)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, source: LibrarySource) -> None:
        super().__init__()
        self.settings = settings
        self.source = source
        self.player = Player()
        self._worker: BatchWorker | None = None
        self._record_worker: RecordWorker | None = None
        self._recordings_dir: Path | None = None
        self._gain_sliders: dict[StemType, QSlider] = {}
        self._total_jobs = 0
        self._done_jobs = 0

        # Persisted selection state. _populating suppresses save signals while the song
        # list is being filled; _restoring does the same while playlists are first loaded;
        # _settings_loaded gates separation-widget saves until the initial restore is done.
        self.state = UiStateStore()
        self._populating = False
        self._restoring = False
        self._settings_loaded = False

        self.setWindowTitle("Songstem")
        self.resize(960, 640)
        self._build_ui()
        self._restore_separation_settings()
        self._refresh_playlists()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._build_top_row())
        root.addLayout(self._build_middle_row(), stretch=1)
        root.addWidget(self._build_progress_group())
        root.addWidget(self._build_player_group())

    def _build_top_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Playlist:"))
        self.playlist_combo = QComboBox()
        self.playlist_combo.currentTextChanged.connect(self._on_playlist_changed)
        row.addWidget(self.playlist_combo, stretch=1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._refresh_playlists)
        row.addWidget(refresh)
        return row

    def _build_middle_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        songs_group = QGroupBox("Songs (checked are processed)")
        songs_layout = QVBoxLayout(songs_group)

        select_row = QHBoxLayout()
        select_all = QPushButton("Select all")
        select_all.clicked.connect(lambda: self._set_all_checked(True))
        select_none = QPushButton("Select none")
        select_none.clicked.connect(lambda: self._set_all_checked(False))
        select_row.addWidget(select_all)
        select_row.addWidget(select_none)
        select_row.addStretch(1)
        songs_layout.addLayout(select_row)

        self.song_list = QListWidget()
        self.song_list.itemChanged.connect(self._on_item_changed)
        songs_layout.addWidget(self.song_list)
        row.addWidget(songs_group, stretch=2)

        row.addWidget(self._build_controls_group(), stretch=1)
        return row

    def _build_controls_group(self) -> QGroupBox:
        group = QGroupBox("Separation")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Isolate stem:"))
        self.stem_combo = QComboBox()
        for stem in StemType:
            self.stem_combo.addItem(stem.value.capitalize(), stem)
        self.stem_combo.currentIndexChanged.connect(self._save_separation_settings)
        layout.addWidget(self.stem_combo)

        layout.addWidget(QLabel("Muted-mix levels (per stem):"))
        for stem in StemType:
            layout.addLayout(self._build_gain_row(stem))

        out_row = QHBoxLayout()
        self.output_label = QLabel(str(self.settings.output_dir))
        self.output_label.setWordWrap(True)
        out_row.addWidget(self.output_label, stretch=1)
        browse = QPushButton("Output…")
        browse.clicked.connect(self._choose_output_dir)
        out_row.addWidget(browse)
        layout.addLayout(out_row)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._run)
        layout.addWidget(self.run_button)

        self.record_button = QPushButton(_RECORD_LABEL)
        self.record_button.setToolTip(
            "Capture the current playlist to DRM-free WAVs via VB-Audio Virtual Cable, then "
            "load them as the source for separation. Personal use only."
        )
        self.record_button.clicked.connect(self._on_record_button)
        layout.addWidget(self.record_button)

        layout.addStretch(1)
        return group

    def _build_gain_row(self, stem: StemType) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(stem.value.capitalize()), stretch=1)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(100)
        value_label = QLabel("100%")
        slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v}%"))
        slider.valueChanged.connect(self._save_separation_settings)
        row.addWidget(slider, stretch=2)
        row.addWidget(value_label)
        self._gain_sliders[stem] = slider
        return row

    def _build_progress_group(self) -> QGroupBox:
        group = QGroupBox("Progress")
        layout = QVBoxLayout(group)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setFixedHeight(110)
        layout.addWidget(self.log)
        return group

    def _build_player_group(self) -> QGroupBox:
        group = QGroupBox("Player")
        layout = QHBoxLayout(group)
        self.output_combo = QComboBox()
        self.output_combo.currentIndexChanged.connect(self._load_selected_output)
        layout.addWidget(self.output_combo, stretch=1)

        for text, handler in (
            ("Play", self.player.play),
            ("Pause", self.player.pause),
            ("Stop", self.player.stop),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            layout.addWidget(button)

        layout.addWidget(QLabel("Vol"))
        volume = QSlider(Qt.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(80)
        volume.setFixedWidth(120)
        volume.valueChanged.connect(lambda v: self.player.set_volume(v / 100.0))
        self.player.set_volume(0.8)
        layout.addWidget(volume)
        return group

    # ------------------------------------------------------------------ data load

    def _refresh_playlists(self) -> None:
        self._restoring = True
        try:
            self.playlist_combo.clear()
            try:
                names = self.source.playlist_names()
            except Exception as exc:
                self._log(f"Could not read playlists: {exc}")
                self.run_button.setEnabled(False)
                return
            self.run_button.setEnabled(True)
            self.playlist_combo.addItems(names)
            if not names:
                self._log("No playlists found.")
                return
            # Restore the previously selected playlist (which restores its song checks).
            saved = self.state.selected_playlist
            if saved in names and self.playlist_combo.currentText() != saved:
                self.playlist_combo.setCurrentText(saved)
        finally:
            self._restoring = False

    def _on_playlist_changed(self, playlist_name: str) -> None:
        self._load_songs(playlist_name)
        if not self._restoring:
            self.state.selected_playlist = playlist_name  # persists immediately

    def _load_songs(self, playlist_name: str) -> None:
        self._populating = True  # suppress per-item save signals during fill
        try:
            self.song_list.clear()
            if not playlist_name:
                return
            try:
                songs = self.source.songs_in_playlist(playlist_name)
            except Exception as exc:
                self._log(f"Could not read songs: {exc}")
                return
            saved = self.state.get_selected_songs(playlist_name)  # list[str] | None
            for song in songs:
                source = self._resolve_source_path(song, playlist_name)  # Path | None
                blocked = source is None
                rerecorded = source is not None and not _is_original(song, source)
                note = "needs re-record" if blocked else ("re-recorded" if rerecorded else None)

                item = QListWidgetItem(self._song_label(song, note))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if blocked:
                    checked = False
                elif saved is None:
                    checked = True  # never saved → default to selected
                else:
                    checked = song_key(song) in saved
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                if blocked:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                    item.setToolTip(_NEEDS_AUDIO_TOOLTIP)
                item.setData(Qt.UserRole, song)
                item.setData(_SOURCE_ROLE, str(source) if source is not None else None)
                self.song_list.addItem(item)
        finally:
            self._populating = False

    def _recordings_dir_for(self, playlist_name: str) -> Path:
        return self.settings.output_dir / "recordings" / sanitize(playlist_name)

    def _resolve_source_path(self, song: Song, playlist_name: str) -> Path | None:
        return resolve_source(song, self._recordings_dir_for(playlist_name))

    def _set_all_checked(self, checked: bool) -> None:
        """Check/uncheck every processable (enabled) song, then persist once."""
        state = Qt.Checked if checked else Qt.Unchecked
        self._populating = True  # suppress per-item save signals during the bulk change
        try:
            for i in range(self.song_list.count()):
                item = self.song_list.item(i)
                if item.flags() & Qt.ItemIsEnabled:  # skip greyed-out (unavailable) songs
                    item.setCheckState(state)
        finally:
            self._populating = False
        self._save_current_songs()

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        if self._populating:
            return
        self._save_current_songs()

    def _save_current_songs(self) -> None:
        name = self.playlist_combo.currentText()
        if name:
            self.state.set_selected_songs(name, self._checked_song_keys())

    def _checked_song_keys(self) -> list[str]:
        keys: list[str] = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if item.checkState() == Qt.Checked:
                keys.append(song_key(item.data(Qt.UserRole)))
        return keys

    # ------------------------------------------------------------------ run batch

    def _run(self) -> None:
        # StemType subclasses str, so Qt stores the item data as a plain str — coerce back.
        target = StemType(self.stem_combo.currentData())
        jobs = self._collect_jobs(target)
        if not jobs:
            QMessageBox.information(self, "Songstem", "No songs selected to process.")
            return

        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        separator = get_backend(self.settings.backend)
        if hasattr(separator, "device"):
            separator.device = self.settings.device

        maker = None
        if self.settings.make_cheatsheet:
            from songstem.analysis.session import default_maker

            maker = default_maker(fetch_lyrics=self.settings.fetch_lyrics)

        self._total_jobs = len(jobs)
        self._done_jobs = 0
        self.progress_bar.setRange(0, self._total_jobs)
        self.progress_bar.setValue(0)
        self._set_busy(True)
        self._log(f"Processing {self._total_jobs} song(s) — isolating {target.value}…")

        # Parent to the window so dropping the Python reference (in the completed/failed slot)
        # can't delete the QThread while run() is still executing — that aborts the process
        # ("QThread: Destroyed while thread is still running"). finished -> deleteLater frees it
        # safely once run() has returned.
        self._worker = BatchWorker(separator, jobs, maker, parent=self)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _collect_jobs(self, target: StemType) -> list[SeparationJob]:
        gains = {stem: slider.value() / 100.0 for stem, slider in self._gain_sliders.items()}
        jobs: list[SeparationJob] = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if item.checkState() != Qt.Checked:
                continue
            song: Song = item.data(Qt.UserRole)
            source = item.data(_SOURCE_ROLE)
            if source:
                # Process the resolved source (a re-recorded WAV when the original is DRM /
                # missing), keeping the title/artist for output naming.
                song = replace(song, location=Path(source))
            jobs.append(
                SeparationJob(
                    song=song,
                    target=target,
                    output_dir=self.settings.output_dir,
                    stem_gains=gains,
                )
            )
        return jobs

    def _on_progress(self, result: JobResult) -> None:
        self._done_jobs += 1
        self.progress_bar.setValue(self._done_jobs)
        title = result.job.song.title
        if result.ok:
            self._log(f"✓ {title}")
            for path in (result.solo_path, result.muted_path):
                if path is not None:
                    self.output_combo.addItem(path.name, path)
            if result.cheatsheet_path is not None:
                self._log(f"📝 cheat sheet → {result.cheatsheet_path.name}")
        else:
            self._log(f"✗ {title}: {result.error}")

    def _on_completed(self, results: list[JobResult]) -> None:
        ok = sum(1 for r in results if r.ok)
        self._log(f"Done. {ok}/{len(results)} succeeded.")
        self._set_busy(False)
        self._worker = None

    def _on_failed(self, message: str) -> None:
        self._log(f"Batch failed: {message}")
        self._set_busy(False)
        self._worker = None

    # ------------------------------------------------------------ loopback recording

    def _on_record_button(self) -> None:
        # The button toggles: start a re-record, or stop one already in progress.
        if self._record_worker is not None:
            self._record_worker.requestInterruption()
            self.record_button.setEnabled(False)
            self.record_button.setText("Stopping…")
            self._log("Stopping after the current track…")
            return

        playlist = self.playlist_combo.currentText()
        if not playlist:
            QMessageBox.information(self, "Songstem", "Select a playlist to re-record.")
            return
        self._recordings_dir = self._recordings_dir_for(playlist)
        self.run_button.setEnabled(False)
        self.record_button.setText("Stop recording")
        self.progress_bar.setRange(0, 0)  # indeterminate until the first track reports a total
        self._log(
            f"Re-recording '{playlist}' via loopback → {self._recordings_dir}. "
            f"Ensure iTunes output is routed to 'CABLE Input'."
        )
        self._record_worker = RecordWorker(
            ITunesPlaybackController(), LoopbackRecorder(), playlist, self._recordings_dir,
            parent=self,  # owned by the window; see _run for why
        )
        self._record_worker.finished.connect(self._record_worker.deleteLater)
        self._record_worker.started_track.connect(self._on_record_started)
        self._record_worker.progress.connect(self._on_record_progress)
        self._record_worker.completed.connect(self._on_record_completed)
        self._record_worker.failed.connect(self._on_record_failed)
        self._record_worker.start()

    def _on_record_started(self, song, index: int, total: int) -> None:
        # Switch to a determinate bar now that the track count is known, and show the song
        # currently being captured (recording is real-time, so this is the only live signal).
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(index - 1)
        self.progress_bar.setFormat(f"Recording {index}/{total}…")
        self.progress_bar.setTextVisible(True)
        self._log(f"▶ recording {song.title} ({index}/{total})…")

    def _on_record_progress(self, result) -> None:
        if getattr(result, "skipped", False):
            self._log(f"↷ skipped {result.song.title} (already recorded)")
        elif result.ok:
            self._log(f"✓ recorded {result.song.title}")
        elif result.error == "cancelled":
            self._log(f"■ stopped during {result.song.title}")
        else:
            self._log(f"✗ {result.song.title}: {result.error}")

    def _on_record_completed(self, results: list) -> None:
        ok = sum(1 for r in results if r.ok)
        silent = next((r for r in results if getattr(r, "silent", False)), None)
        stopped = any(r.error == "cancelled" for r in results)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self._reset_record_ui()

        if silent is not None:
            # Aborted early because audio wasn't reaching the recorder — tell the user why so
            # they can fix routing before retrying, instead of recording the whole playlist.
            self._log(f"Re-recording aborted after a silent capture ({silent.song.title}).")
            QMessageBox.warning(
                self,
                "Songstem — no audio captured",
                "Re-recording was stopped because the first capture was silent — no audio is "
                "reaching the recorder.\n\n"
                "Check that iTunes' output is routed to 'CABLE Input', and if you are connected "
                "over Remote Desktop, set remote audio to play on the remote computer. Then try "
                "again.",
            )
            return

        skipped = sum(1 for r in results if getattr(r, "skipped", False))
        recorded = ok - skipped
        verb = "stopped" if stopped else "done"
        skipped_note = f", {skipped} already present" if skipped else ""
        self._log(
            f"Re-recording {verb}. {recorded} recorded{skipped_note} "
            f"→ {self._recordings_dir}"
        )
        if ok and self._recordings_dir is not None:
            # Load the recorded folder as the active source so it can be separated.
            self.source = FolderLibrary(self._recordings_dir)
            self._refresh_playlists()
            self._log("Loaded recorded folder as source — select it and press Run to separate.")

    def _on_record_failed(self, message: str) -> None:
        self._log(f"Re-recording failed: {message}")
        self._reset_record_ui()

    def _reset_record_ui(self) -> None:
        self._record_worker = None
        self.progress_bar.setFormat("")  # clear the "Recording N/M…" text
        self.progress_bar.setTextVisible(False)
        self.record_button.setText(_RECORD_LABEL)
        self.record_button.setEnabled(True)
        self.run_button.setEnabled(True)

    def _set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.record_button.setEnabled(not busy)

    # ------------------------------------------------------------------ misc

    def _choose_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose output folder", str(self.settings.output_dir)
        )
        if chosen:
            self.settings.output_dir = Path(chosen)
            self.output_label.setText(chosen)
            self._save_separation_settings()

    def _restore_separation_settings(self) -> None:
        """Restore the Separation widget (isolate stem, gains, output dir) from preferences."""
        self._settings_loaded = False  # suppress saves while we set widget values
        saved_out = self.state.output_dir
        if saved_out:
            self.settings.output_dir = Path(saved_out)
            self.output_label.setText(saved_out)

        stem = self.state.isolate_stem
        if stem:
            index = self.stem_combo.findData(stem)
            if index >= 0:
                self.stem_combo.setCurrentIndex(index)

        gains = self.state.get_stem_gains()
        if gains:
            for stem_type, slider in self._gain_sliders.items():
                if stem_type.value in gains:
                    slider.setValue(int(gains[stem_type.value]))

        self._settings_loaded = True  # subsequent widget changes now persist

    def _save_separation_settings(self, *_args) -> None:
        if not self._settings_loaded:
            return  # ignore signals fired while building/restoring the UI
        data = self.stem_combo.currentData()
        if data is not None:
            self.state.isolate_stem = data.value if hasattr(data, "value") else str(data)
        self.state.set_stem_gains(
            {stem.value: slider.value() for stem, slider in self._gain_sliders.items()}
        )
        self.state.output_dir = str(self.settings.output_dir)

    def _load_selected_output(self, index: int) -> None:
        path = self.output_combo.itemData(index)
        if path is not None:
            self.player.load(Path(path))

    def closeEvent(self, event) -> None:
        # Stop any in-progress worker and wait for it to finish before the window (its parent)
        # is destroyed — otherwise the still-running QThread is torn down and aborts the process.
        # Separation checks the interrupt between songs; re-record stops within a poll cycle.
        for worker in (self._record_worker, self._worker):
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                worker.wait()
        # Saves happen incrementally on change; persist once more on exit as a safety net.
        name = self.playlist_combo.currentText()
        if name:
            self.state.selected_playlist = name
            self.state.set_selected_songs(name, self._checked_song_keys())
        super().closeEvent(event)

    @staticmethod
    def _song_label(song: Song, note: str | None = None) -> str:
        label = f"{song.artist} — {song.title}" if song.artist else song.title
        return label + (f"  ({note})" if note else "")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)


def _is_original(song: Song, source: Path) -> bool:
    """True if `source` is the song's own (DRM-free) file rather than a re-recorded WAV."""
    return song.location is not None and Path(song.location) == source


def resolve_source(song: Song, recordings_dir: Path) -> Path | None:
    """The audio file songstem would actually process for `song`, or None if unavailable.

    Prefers a DRM-free original file (present and not `.m4p`); falls back to a previously
    re-recorded WAV in `recordings_dir`. Returns None only when neither exists — that is the
    sole condition under which a song is greyed out in the list.
    """
    location = song.location
    if location is not None and not is_drm_protected(location) and Path(location).exists():
        return Path(location)
    wav = recordings_dir / wav_filename(song)
    if wav.exists():
        return wav
    return None
