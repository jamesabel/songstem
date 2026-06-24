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

from songstem.audio.io import is_drm_protected
from songstem.audio.player import Player
from songstem.config import Settings
from songstem.gui.worker import BatchWorker
from songstem.itunes.library import LibrarySource
from songstem.models import JobResult, SeparationJob, Song, StemType
from songstem.separation import get_backend
from songstem.state import UiStateStore, song_key


def _unprocessable_reason(song: Song) -> str | None:
    """Why a song can't be processed, or None if it can.

    Used to disable the song in the list up front rather than failing during the batch.
    """
    if song.location is None:
        return "no local file"
    if is_drm_protected(song.location):
        return "DRM-protected"
    return None


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, source: LibrarySource) -> None:
        super().__init__()
        self.settings = settings
        self.source = source
        self.player = Player()
        self._worker: BatchWorker | None = None
        self._gain_sliders: dict[StemType, QSlider] = {}
        self._total_jobs = 0
        self._done_jobs = 0

        # Persisted selection state. _populating suppresses save signals while the song
        # list is being filled; _restoring does the same while playlists are first loaded.
        self.state = UiStateStore()
        self._populating = False
        self._restoring = False

        self.setWindowTitle("Songstem")
        self.resize(960, 640)
        self._build_ui()
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
                blocked = _unprocessable_reason(song)  # None if the song can be processed
                item = QListWidgetItem(self._song_label(song, blocked))
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
                item.setData(Qt.UserRole, song)
                self.song_list.addItem(item)
        finally:
            self._populating = False

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

        self._total_jobs = len(jobs)
        self._done_jobs = 0
        self.progress_bar.setRange(0, self._total_jobs)
        self.progress_bar.setValue(0)
        self.run_button.setEnabled(False)
        self._log(f"Processing {self._total_jobs} song(s) — isolating {target.value}…")

        self._worker = BatchWorker(separator, jobs)
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
        else:
            self._log(f"✗ {title}: {result.error}")

    def _on_completed(self, results: list[JobResult]) -> None:
        ok = sum(1 for r in results if r.ok)
        self._log(f"Done. {ok}/{len(results)} succeeded.")
        self.run_button.setEnabled(True)
        self._worker = None

    def _on_failed(self, message: str) -> None:
        self._log(f"Batch failed: {message}")
        self.run_button.setEnabled(True)
        self._worker = None

    # ------------------------------------------------------------------ misc

    def _choose_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose output folder", str(self.settings.output_dir)
        )
        if chosen:
            self.settings.output_dir = Path(chosen)
            self.output_label.setText(chosen)

    def _load_selected_output(self, index: int) -> None:
        path = self.output_combo.itemData(index)
        if path is not None:
            self.player.load(Path(path))

    def closeEvent(self, event) -> None:
        # Saves happen incrementally on change; persist once more on exit as a safety net.
        name = self.playlist_combo.currentText()
        if name:
            self.state.selected_playlist = name
            self.state.set_selected_songs(name, self._checked_song_keys())
        super().closeEvent(event)

    @staticmethod
    def _song_label(song: Song, blocked: str | None = None) -> str:
        label = f"{song.artist} — {song.title}" if song.artist else song.title
        return label + (f"  ({blocked})" if blocked else "")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)
