"""
FL Library Pro — Main Application

A beautiful, modern library manager and player for FL Studio project folders.
Full-featured widget-based UI with all prototype features.
"""

import sys
import os
import logging

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QSlider, QFrame, QScrollArea, QMessageBox, QTabWidget, QGroupBox,
    QGridLayout, QComboBox, QSpinBox, QTextEdit, QFileDialog, QProgressBar,
    QStackedWidget, QSizePolicy, QToolButton, QMenu, QDialog, QDialogButtonBox,
    QFormLayout, QInputDialog, QSpacerItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QFormLayout, QInputDialog, QSpacerItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QThread
from PySide6.QtGui import QIcon, QFont, QColor, QPalette, QAction, QKeySequence, QBrush, QPixmap

from . import __version__, __app_name__
from .database import get_db, get_app_data_path, query, execute, get_setting, set_setting
from .scanner import (
    ScannerThread, get_all_tracks, get_favorite_tracks, search_tracks,
    toggle_favorite, get_track_by_id, update_track_metadata, LibraryScanner,
    AUDIO_EXTENSIONS
)
from .database.tags import get_all_genres, update_track_tags, add_tag, get_track_tags
from .ui.dialogs import MetadataEditDialog
from .ui.widgets import MarqueeLabel
from .ui import (
    SettingsDialog, TagEditorDialog, AnalysisDialog, BatchAnalysisDialog,
    PlaylistPanel, PlaylistEditDialog, AddToPlaylistMenu,
    MiniWaveformWidget, ProjectDrillDownPanel, TrackInfoCard
)
from .player import get_player, PlayerState, RepeatMode
from .waveform import WaveformThread, get_cached_waveform
from .analysis import AnalyzerThread, format_bpm, format_key, KEYS
from .utils import (
    format_duration, format_file_size, format_timestamp, format_smart_date,
    open_file, open_folder, open_fl_studio, count_files_in_folder,
    get_folder_size, setup_logging, get_icon,
    get_cover_art, get_placeholder_cover
)
from .utils.shortcuts import ShortcutManager, DEFAULT_SHORTCUTS

logger = logging.getLogger(__name__)


# Premium Sky Blue & Slate Theme - Spotify/iTunes level design
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0c1117;
    color: #f1f5f9;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}
*:focus {
    border: 1px solid #38bdf8;
    outline: none;
}

QFrame#sidebar {
    background-color: #111820;
    border-right: 1px solid #1e293b;
}

QLabel {
    background: transparent;
}

QFrame#mainArea {
    background-color: #0c1117;
}

QFrame#playerBar {
    background-color: #151d28;
    border-top: 1px solid #1e293b;
    border-radius: 0px; 
}

QScrollArea#detailsScroll {
    background-color: #111820;
    border-left: 1px solid #1e293b;
    border: none;
}

QScrollArea#detailsScroll > QWidget > QWidget {
    background-color: #111820;
}

QLabel#logo {
    font-size: 18px;
    font-weight: bold;
    color: #38bdf8;
    padding: 8px;
}

QLabel#sectionTitle {
    font-size: 10px;
    font-weight: bold;
    color: #64748b;
    padding: 12px 0 6px 0;
    letter-spacing: 1.5px;
}

QPushButton#navButton {
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: #94a3b8;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#navButton:hover {
    background: #1e2836;
    color: #f1f5f9;
}

QPushButton#navButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(56,189,248,0.15), stop:1 transparent);
    color: #f1f5f9;
    border-left: 3px solid #38bdf8;
}

QPushButton#actionButton {
    padding: 12px 20px;
    border: none;
    border-radius: 22px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0ea5e9);
    color: #0c1117;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#actionButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7dd3fc, stop:1 #38bdf8);
}

QPushButton#actionButton:disabled {
    background: #283344;
    color: #64748b;
}

QPushButton#secondaryButton {
    padding: 8px 16px;
    border: 1px solid #334155;
    border-radius: 12px;
    background: transparent;
    color: #f1f5f9;
    font-size: 12px;
}

QPushButton#secondaryButton:hover {
    border-color: #38bdf8;
    color: #38bdf8;
}

QPushButton#detailButton {
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: #f1f5f9;
    font-size: 13px;
    min-height: 24px;
}

QPushButton#detailButton:hover {
    background: #1e2836;
}

QPushButton#detailButton:disabled {
    background: #111820;
    color: #475569;
}

QLineEdit#searchInput {
    padding: 10px 20px;
    border: 1px solid #334155;
    border-radius: 18px;
    background: #1e2836;
    color: #f1f5f9;
    font-size: 14px;
    selection-background-color: #38bdf8;
}

QLineEdit#searchInput:focus {
    background: #283344;
    border-color: rgba(56,189,248,0.4);
}

QTableWidget#trackList {
    background: transparent;
    border: none;
    font-size: 13px;
    outline: none;
    gridline-color: transparent;
}

QTableWidget#trackList::item {
    padding: 4px;
    border-bottom: 1px solid #1e293b;
}

QTableWidget#trackList::item:selected {
    background: #1e293b;
    color: #f1f5f9;
}

QHeaderView::section {
    background: #0c1117;
    color: #64748b;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
}

QLabel#trackTitle {
    background: transparent;
    font-size: 16px;
    font-weight: bold;
    color: #f1f5f9;
}

QLabel#trackProject {
    background: transparent;
    font-size: 12px;
    color: #94a3b8;
}

QLabel#metadataLabel {
    font-size: 10px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}

QLabel#metadataValue {
    font-size: 20px;
    font-weight: bold;
    color: #38bdf8;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #94a3b8;
}

QPushButton#playerButton {
    min-width: 40px;
    min-height: 40px;
    max-width: 40px;
    max-height: 40px;
    border: none;
    border-radius: 20px;
    background: transparent;
    color: #94a3b8;
    font-size: 18px;
    font-weight: bold;
}

QPushButton#playerButton:hover {
    color: #f1f5f9;
    background: #1e2836;
}

QPushButton#playButton {
    min-width: 48px;
    min-height: 48px;
    max-width: 48px;
    max-height: 48px;
    border: none;
    border-radius: 24px;
    background: #f1f5f9;
    color: #0c1117;
    font-size: 20px;
    font-weight: bold;
}

QPushButton#playButton:hover {
    background: #38bdf8;
}

QSlider#progressSlider::groove:horizontal {
    background: #1e293b;
    height: 4px;
    border-radius: 2px;
}

QSlider#progressSlider::handle:horizontal {
    background: #f1f5f9;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider#progressSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #7dd3fc);
    border-radius: 2px;
}

QSlider#volumeSlider::groove:horizontal {
    background: #1e293b;
    height: 4px;
    border-radius: 2px;
}

QSlider#volumeSlider::handle:horizontal {
    background: #f1f5f9;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}

QSlider#volumeSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 2px;
}

QLabel#timeLabel {
    font-size: 11px;
    color: #64748b;
    font-family: 'Consolas', 'Monaco', monospace;
}

QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 16px;
    margin-top: 14px;
    padding: 10px;
    font-weight: bold;
    font-size: 11px;
    background: transparent;
}

QGroupBox::title {
    color: #64748b;
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
}

QProgressBar {
    border: none;
    border-radius: 4px;
    background: #1e293b;
    height: 6px;
    text-align: center;
}

QProgressBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #7dd3fc);
}

QComboBox {
    padding: 8px 14px;
    border: 1px solid #334155;
    border-radius: 12px;
    background: #151d28;
    color: #f1f5f9;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #38bdf8;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background: #151d28;
    border: 1px solid #1e293b;
    selection-background-color: #283344;
    border-radius: 8px;
}

QTextEdit {
    background: #0c1117;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 10px;
    color: #f1f5f9;
    font-size: 13px;
}

QTextEdit:focus {
    border-color: rgba(56,189,248,0.4);
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QToolTip {
    background: #1e2836;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

QDialog {
    background: #151d28;
}

QDialog QLabel {
    color: #f1f5f9;
}

QDialogButtonBox QPushButton {
    padding: 8px 20px;
    border-radius: 8px;
    font-weight: 500;
}
"""


class QueuePanel(QFrame):
    """Collapsible queue panel showing upcoming tracks."""
    
    track_clicked = Signal(dict)  # Emitted when a track is clicked to play
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("queuePanel")
        self.setStyleSheet("""
            QFrame#queuePanel {
                background-color: #151d28;
                border-top: 1px solid #1e293b;
            }
            QListWidget#queueList {
                background: transparent;
                border: none;
            }
            QListWidget#queueList::item {
                padding: 8px;
                border-bottom: 1px solid #1e293b;
                color: #f1f5f9;
            }
            QListWidget#queueList::item:selected {
                background: rgba(56, 189, 248, 0.15);
            }
            QListWidget#queueList::item:hover {
                background: #1e2836;
            }
        """)
        
        self._current_track = None
        self._queue = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Queue")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(title)
        
        self.count_label = QLabel("0 tracks")
        self.count_label.setStyleSheet("font-size: 12px; color: #64748b;")
        header.addWidget(self.count_label)
        
        header.addStretch()
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #94a3b8;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                border-color: #ef4444;
                color: #ef4444;
            }
        """)
        self.clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self.clear_btn)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f1f5f9;
            }
        """)
        close_btn.clicked.connect(lambda: self.setVisible(False))
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Now Playing section
        self.now_playing = QFrame()
        self.now_playing.setStyleSheet("""
            QFrame {
                background: rgba(56, 189, 248, 0.1);
                border: 1px solid rgba(56, 189, 248, 0.2);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        np_layout = QHBoxLayout(self.now_playing)
        np_layout.setContentsMargins(12, 8, 12, 8)
        
        np_icon = QLabel("▶")
        np_icon.setStyleSheet("color: #38bdf8; font-size: 14px;")
        np_layout.addWidget(np_icon)
        
        np_text = QVBoxLayout()
        self.np_label = QLabel("NOW PLAYING")
        self.np_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        np_text.addWidget(self.np_label)
        
        self.np_title = QLabel("No track")
        self.np_title.setStyleSheet("font-size: 13px; color: #f1f5f9;")
        np_text.addWidget(self.np_title)
        
        np_layout.addLayout(np_text, 1)
        layout.addWidget(self.now_playing)
        
        # Up Next label
        up_next = QLabel("UP NEXT")
        up_next.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; letter-spacing: 1.5px;")
        layout.addWidget(up_next)
        
        # Queue list
        self.queue_list = QListWidget()
        self.queue_list.setObjectName("queueList")
        self.queue_list.setMaximumHeight(150)
        self.queue_list.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self.queue_list)
        
        # Set fixed height when visible
        self.setFixedHeight(280)
        self.setVisible(False)
    
    def set_current_track(self, track):
        """Set the currently playing track."""
        self._current_track = track
        if track:
            self.np_title.setText(track.get('title', 'Unknown'))
        else:
            self.np_title.setText("No track")
    
    def set_queue(self, tracks, current_index=0):
        """Set the queue tracks (showing tracks after current)."""
        self._queue = tracks[current_index + 1:current_index + 21] if tracks else []
        self._update_list()
    
    def _update_list(self):
        """Update the queue list widget."""
        self.queue_list.clear()
        # If no tracks found via slicing, but we have a playlist, show it all (fallback)
        # If no tracks found via slicing, but we have a playlist, show it all (fallback)
        display_queue = self._queue
        
        # Fallback: if queue is empty but playlist exists and we are playing, maybe showing something is better?
        # For now, just rely on valid queue.
        
        self.count_label.setText(f"{len(display_queue)} tracks")
        
        for i, track in enumerate(display_queue[:15]):  # Show max 15
            title = track.get('title', 'Unknown')
            project = track.get('project_name', '')
            item = QListWidgetItem(f"{i + 1}. {title}")
            item.setToolTip(f"{title}\n{project}")
            item.setData(Qt.ItemDataRole.UserRole, track)
            # Explicitly set color just in case stylesheet fails
            item.setForeground(QColor("#f1f5f9"))
            self.queue_list.addItem(item)
    
    def _on_item_clicked(self, item):
        """Handle queue item click."""
        track = item.data(Qt.ItemDataRole.UserRole)
        if track:
            self.track_clicked.emit(track)
    
    def _on_clear(self):
        """Clear the queue."""
        self._queue = []
        self._update_list()


class MainWindow(QMainWindow):
    """Main application window with full features."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setMinimumSize(1200, 700)
        self.resize(1400, 850)
        
        # State
        self.current_track = None
        self.tracks_data = []
        self.scanner_thread = None
        self.analysis_thread = None
        
        # Player
        self.player = get_player()
        self._connect_player_signals()
        
        # Setup UI
        self.setup_ui()
        
        # Load data
        self.load_tracks()
        
        # Check first run
        self.check_first_run()
        
        # Position update timer
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self.update_position)
        self.position_timer.start(100)
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for the application."""
        self.shortcuts = ShortcutManager(self)
        
        # Playback
        self.shortcuts.register_shortcut('play_pause', self.player.toggle_play)
        self.shortcuts.register_shortcut('stop', self.player.stop)
        self.shortcuts.register_shortcut('next_track', self.player.next)
        self.shortcuts.register_shortcut('prev_track', self.player.previous)
        self.shortcuts.register_shortcut('play_from_start', self._play_from_start)
        
        # Track actions
        self.shortcuts.register_shortcut('favorite', self.toggle_favorite)
        self.shortcuts.register_shortcut('tag_editor', self.show_tag_editor)
        self.shortcuts.register_shortcut('add_to_playlist', self.show_add_to_playlist)
        self.shortcuts.register_shortcut('open_project', self.open_project_folder)
        self.shortcuts.register_shortcut('open_folder_alt', self.open_project_folder)  # Alt+Enter
        self.shortcuts.register_shortcut('open_flp', self.open_flp)  # Ctrl+Enter
        self.shortcuts.register_shortcut('analyze_bpm', self.analyze_track)
        self.shortcuts.register_shortcut('edit_metadata', self.edit_metadata)
        
        # Navigation
        self.shortcuts.register_shortcut('go_library', lambda: self.set_page('library'))
        self.shortcuts.register_shortcut('go_favorites', lambda: self.set_page('favorites'))
        self.shortcuts.register_shortcut('go_playlists', lambda: self.set_page('playlists'))
        
        # General
        self.shortcuts.register_shortcut('settings', lambda: self.set_page('settings'))
        self.shortcuts.register_shortcut('search', lambda: self.search_input.setFocus())
        self.shortcuts.register_shortcut('search_slash', lambda: self.search_input.setFocus())  # / key
        self.shortcuts.register_shortcut('toggle_queue', self.toggle_queue_panel)
    
    def _play_from_start(self):
        """Play current track from the beginning."""
        if self.player.state != PlayerState.STOPPED:
            self.player.seek(0)
            if self.player.state != PlayerState.PLAYING:
                self.player.play()
    
    def toggle_queue_panel(self):
        """Toggle queue panel visibility."""
        self.queue_panel.setVisible(not self.queue_panel.isVisible())
    
    def show_tag_editor(self):
        """Show tag editor dialog for current track."""
        if not self.current_track:
            return
        
        dialog = TagEditorDialog(self.current_track['id'], self)
        if dialog.exec():
            # Refresh the track list to show updated tags
            self.on_search(self.search_input.text())
            self.update_details_panel(self.current_track)
    
    def show_add_to_playlist(self):
        """Show add to playlist menu for current track."""
        if not self.current_track:
            return
        
        menu = AddToPlaylistMenu(self)
        menu.set_tracks([self.current_track['id']])
        menu.exec(self.cursor().pos())
    
    def _connect_player_signals(self):
        """Connect player signals."""
        self.player.state_changed.connect(self.on_player_state_changed)
        self.player.track_changed.connect(self.on_track_changed)
        self.player.duration_changed.connect(self.on_duration_changed)
    
    def setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Content area (sidebar + main + details)
        content = QHBoxLayout()
        content.setSpacing(0)
        
        # === SIDEBAR ===
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 12)
        sidebar_layout.setSpacing(2)
        
        # Logo
        logo_layout = QHBoxLayout()
        logo_icon = QLabel()
        logo_icon.setPixmap(get_icon("fl_studio", None, 32).pixmap(32, 32))
        logo_icon.setStyleSheet("padding: 4px;")
        logo_layout.addWidget(logo_icon)
        
        logo_text = QLabel("FruityWolf")
        logo_text.setObjectName("logo")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)
        
        sidebar_layout.addSpacing(16)
        
        # Navigation buttons with better icons
        self.nav_home = self._create_nav_button("Library", "library", True)
        self.nav_home.clicked.connect(lambda: self.set_page("library"))
        sidebar_layout.addWidget(self.nav_home)
        
        self.nav_favorites = self._create_nav_button("Favorites", "heart")
        self.nav_favorites.clicked.connect(lambda: self.set_page("favorites"))
        sidebar_layout.addWidget(self.nav_favorites)
        
        self.nav_playlists = self._create_nav_button("Playlists", "playlist")
        self.nav_playlists.clicked.connect(lambda: self.set_page("playlists"))
        sidebar_layout.addWidget(self.nav_playlists)
        
        self.nav_settings = self._create_nav_button("Settings", "settings")
        self.nav_settings.clicked.connect(lambda: self.set_page("settings"))
        sidebar_layout.addWidget(self.nav_settings)
        
        sidebar_layout.addSpacing(16)
        
        # Smart Views
        smart_views_label = QLabel("SMART VIEWS")
        smart_views_label.setObjectName("sectionTitle")
        sidebar_layout.addWidget(smart_views_label)
        
        self.nav_recent = self._create_nav_button("Recently Added", "time")
        self.nav_recent.clicked.connect(lambda: self.set_page("recent"))
        sidebar_layout.addWidget(self.nav_recent)
        
        self.nav_missing = self._create_nav_button("Missing Metadata", "alert")
        self.nav_missing.clicked.connect(lambda: self.set_page("missing"))
        sidebar_layout.addWidget(self.nav_missing)
        
        sidebar_layout.addStretch()
        
        # Scan section
        scan_label = QLabel("LIBRARY")
        scan_label.setObjectName("sectionTitle")
        sidebar_layout.addWidget(scan_label)
        
        self.rescan_btn = QPushButton(" Rescan Library")
        self.rescan_btn.setObjectName("detailButton")
        self.rescan_btn.setIcon(get_icon("scan", QColor("#f1f5f9"), 20))
        self.rescan_btn.clicked.connect(self.rescan_library)
        sidebar_layout.addWidget(self.rescan_btn)
        
        sidebar_layout.addSpacing(6)
        
        self.add_folder_btn = QPushButton(" Add Folder")
        self.add_folder_btn.setObjectName("detailButton")
        self.add_folder_btn.setIcon(get_icon("add", QColor("#f1f5f9"), 20))
        self.add_folder_btn.clicked.connect(self.add_library_folder)
        sidebar_layout.addWidget(self.add_folder_btn)
        
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        self.scan_progress.setFixedHeight(4)
        self.scan_progress.setTextVisible(False)
        sidebar_layout.addWidget(self.scan_progress)
        
        self.scan_status = QLabel("")
        self.scan_status.setObjectName("statusLabel")
        self.scan_status.setWordWrap(True)
        sidebar_layout.addWidget(self.scan_status)
        
        content.addWidget(sidebar)
        
        # === MAIN STACK (Library / Project Drill-Down) ===
        self.stack = QStackedWidget()
        
        # 1. LIBRARY VIEW
        self.library_view = QWidget()
        library_layout = QVBoxLayout(self.library_view)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(0)
        
        main_area = QFrame()
        main_area.setObjectName("mainArea")
        main_layout_inner = QVBoxLayout(main_area)
        main_layout_inner.setContentsMargins(20, 16, 20, 16)
        main_layout_inner.setSpacing(12)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks, projects...")
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        
        # Add Search Bar to Main Layout
        main_layout_inner.addLayout(search_layout)
        
        # Filter Chips (Scrollable)
        filter_scroll = QScrollArea()
        filter_scroll.setWidgetResizable(True)
        filter_scroll.setFixedHeight(40)
        filter_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
        """)
        filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        filter_container = QWidget()
        self.filter_layout = QHBoxLayout(filter_container)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(8)
        self.filter_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Chip helper
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(False) # Allow multiple? For now let's do single select + toggle
        
        def add_chip(text, data=None):
            btn = QPushButton(text)
            btn.setObjectName("filterChip")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton#filterChip {
                    background: rgba(30, 41, 59, 0.5);
                    border: 1px solid #334155;
                    border-radius: 20px;
                    padding: 4px 16px;
                    color: #94a3b8;
                    font-size: 11px;
                }
                QPushButton#filterChip:hover {
                    border-color: #38bdf8;
                    color: #f1f5f9;
                }
                QPushButton#filterChip:checked {
                    background: rgba(56, 189, 248, 0.2);
                    border-color: #38bdf8;
                    color: #38bdf8;
                }
            """)
            btn.clicked.connect(self.on_filter_chip_clicked)
            if data:
                btn.setProperty("filter_data", data)
            self.filter_layout.addWidget(btn)
            self.filter_group.addButton(btn)
            return btn

        # Add Chips
        self.chip_fav = add_chip("Favorites", "favorites")
        self.chip_fav.setIcon(get_icon("heart", size=12))
        
        # Keys
        # For simplicity, maybe just "No Key" and a few common ones, or keep ComboBox for Keys?
        # Plan says "Chips". Let's do common ones or categories? 
        # Actually user said "Replace ComboBoxes". 
        # Putting ALL keys as chips is too many (12*2 = 24). 
        # Let's keep a "Key" dropdown button? Or just "No Key" chip and maybe "Camelot"?
        # Let's handle Genres as chips and maybe Keep Key as a dropdown or just "Keys..." button?
        # Let's stick to the plan: "Favorites", "No BPM", "No Key" + Genres.
        
        add_chip("No BPM", "no_bpm")
        add_chip("No Key", "no_key")
        
        # Top Genres (Dynamic)
        genres = get_all_genres()
        for g in genres[:8]: # Show top 8
            add_chip(g, f"genre:{g}")
            
        self.filter_layout.addStretch()
        filter_scroll.setWidget(filter_container)
        
        # Replace old filter layout with this
        # We need to remove old widgets first or just insert this instead
        # The previous search_layout had ComboBoxes.
        # We will add filter_scroll BELOW search input, or NEXT to it? 
        # Layouts: [Search Input]
        #          [Filter Chips Scroll]
        
        # Let's restructure:
        # main_layout_inner has [search_layout]
        # search_layout has [input] [combo] [btn] [combo]
        
        # New structure:
        # main_layout_inner has [search_input]
        # main_layout_inner has [filter_scroll] (new row)
        
        main_layout_inner.addWidget(filter_scroll)
        
        # Track count
        self.track_count_label = QLabel("0 tracks")
        self.track_count_label.setObjectName("statusLabel")
        main_layout_inner.addWidget(self.track_count_label)
        
        # Track list (Table View)
        self.track_list = QTableWidget()
        self.track_list.setObjectName("trackList")
        # Expanded columns: Icon, Track, Project, Date, BPM, Key, Genre, +View, +Playlist, +Tags, +Analyze, Edit
        self.track_list.setColumnCount(12)
        # Set text labels for main columns, empty for icon columns
        self.track_list.setHorizontalHeaderLabels([
            "", "TRACK", "PROJECT", "DATE", "BPM", "KEY", "GENRE",
            "", "", "", "", "" 
        ])
        
        # Set icons for action columns
        # 7: View (Eye)
        self.track_list.setHorizontalHeaderItem(7, QTableWidgetItem(get_icon("eye", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(7).setToolTip("View Project")
        
        # 8: Playlist (Folder/Playlist)
        self.track_list.setHorizontalHeaderItem(8, QTableWidgetItem(get_icon("playlist", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(8).setToolTip("Add to Playlist")
        
        # 9: Tags (Tag)
        self.track_list.setHorizontalHeaderItem(9, QTableWidgetItem(get_icon("tag", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(9).setToolTip("Edit Tags")
        
        # 10: Analyze (Audio/Waveform)
        self.track_list.setHorizontalHeaderItem(10, QTableWidgetItem(get_icon("analyze", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(10).setToolTip("Analyze Audio")
        
        # 11: Edit (Pen)
        self.track_list.setHorizontalHeaderItem(11, QTableWidgetItem(get_icon("edit", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(11).setToolTip("Edit Metadata")
        self.track_list.verticalHeader().setVisible(False)
        self.track_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Track
        self.track_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Project
        self.track_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        # Action columns fixed width
        for col in range(7, 12):
            self.track_list.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.track_list.setColumnWidth(col, 32)
        self.track_list.setColumnWidth(0, 30)  # Playing/Fav Icon
        self.track_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.track_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.track_list.setShowGrid(False)
        self.track_list.setSortingEnabled(True)
        
        self.track_list.cellClicked.connect(self.on_track_clicked)
        self.track_list.cellDoubleClicked.connect(self.on_track_double_clicked_table)
        
        # Right-click context menu
        self.track_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_list.customContextMenuRequested.connect(self.show_track_context_menu)
        
        main_layout_inner.addWidget(self.track_list)
        
        library_layout.addWidget(main_area)
        self.stack.addWidget(self.library_view)
        
        # 2. PROJECT VIEW
        self.project_panel = ProjectDrillDownPanel()
        self.project_panel.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
        self.project_panel.track_play_requested.connect(self._play_external_file)
        self.stack.addWidget(self.project_panel)
        
        content.addWidget(self.stack, 1)  # Stretch
        
        # === DETAILS PANEL (Right side) - Scrollable ===
        details_scroll = QScrollArea()
        details_scroll.setObjectName("detailsScroll")
        details_scroll.setFixedWidth(340)
        details_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        details_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        details_scroll.setWidgetResizable(True)
        
        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(12)
        
        # Track info header
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("background-color: #0f172a; border-radius: 8px; border: 1px solid #1e293b;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        details_layout.addSpacing(16)
        
        self.detail_title = QLabel("Select a track")
        self.detail_title.setObjectName("trackTitle")
        self.detail_title.setWordWrap(True)
        details_layout.addWidget(self.detail_title)
        
        self.detail_project = QLabel("")
        self.detail_project.setObjectName("trackProject")
        details_layout.addWidget(self.detail_project)
        
        details_layout.addSpacing(8)
        
        # Metadata grid
        metadata_group = QGroupBox("METADATA")
        metadata_layout = QGridLayout(metadata_group)
        metadata_layout.setSpacing(10)
        metadata_layout.setContentsMargins(12, 16, 12, 12)
        
        # Add Edit button to header
        header_layout = QHBoxLayout()
        self.btn_edit = QPushButton("")
        self.btn_edit.setIcon(get_icon("edit", QColor("#94a3b8"), 16))
        self.btn_edit.setToolTip("Edit Metadata")
        self.btn_edit.setFixedSize(24, 24)
        self.btn_edit.setStyleSheet("background: transparent; border: none;")
        self.btn_edit.clicked.connect(self.edit_metadata)
        # We can add this to details_layout or near title. 
        # Let's put it in the grid for now or make a row for it.
        # Actually better to put it next to metadata title? GroupBox title logic hard.
        # Let's just add it as a small button in the group box top right?
        metadata_layout.addWidget(self.btn_edit, 0, 2) # Top right corner
        
        bpm_label = QLabel("BPM")
        bpm_label.setObjectName("metadataLabel")
        metadata_layout.addWidget(bpm_label, 0, 0)
        self.detail_bpm = QLabel("--")
        self.detail_bpm.setObjectName("metadataValue")
        self.detail_bpm.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.detail_bpm.linkActivated.connect(lambda: self.edit_metadata())
        metadata_layout.addWidget(self.detail_bpm, 1, 0)
        
        key_label = QLabel("KEY")
        key_label.setObjectName("metadataLabel")
        metadata_layout.addWidget(key_label, 0, 1)
        self.detail_key = QLabel("--")
        self.detail_key.setObjectName("metadataValue")
        self.detail_key.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.detail_key.linkActivated.connect(lambda: self.edit_metadata())
        metadata_layout.addWidget(self.detail_key, 1, 1)
        
        dur_label = QLabel("DURATION")
        dur_label.setObjectName("metadataLabel")
        metadata_layout.addWidget(dur_label, 2, 0)
        self.detail_duration = QLabel("--")
        self.detail_duration.setObjectName("metadataValue")
        metadata_layout.addWidget(self.detail_duration, 3, 0)
        
        size_label = QLabel("SIZE")
        size_label.setObjectName("metadataLabel")
        metadata_layout.addWidget(size_label, 2, 1)
        self.detail_size = QLabel("--")
        self.detail_size.setObjectName("metadataValue")
        metadata_layout.addWidget(self.detail_size, 3, 1)

        genre_label = QLabel("GENRE")
        genre_label.setObjectName("metadataLabel")
        metadata_layout.addWidget(genre_label, 4, 0)
        self.detail_genre = QLabel("--")
        self.detail_genre.setObjectName("metadataValue")
        self.detail_genre.setWordWrap(True)
        metadata_layout.addWidget(self.detail_genre, 5, 0, 1, 2)
        
        details_layout.addWidget(metadata_group)
        
        # Action buttons
        actions_group = QGroupBox("ACTIONS")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(8)
        actions_layout.setContentsMargins(10, 14, 10, 10)
        
        # 1. Primary Play Button
        self.btn_play = QPushButton(" Play Render")
        self.btn_play.setIcon(get_icon("play", QColor("#ffffff"), 20))
        self.btn_play.setObjectName("primaryButton")  # Needs styling
        self.btn_play.setFixedHeight(40)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #38bdf8);
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0ea5e9);
            }
            QPushButton:pressed {
                background: #0284c7;
            }
        """)
        self.btn_play.clicked.connect(self.play_current_track)
        actions_layout.addWidget(self.btn_play)
        
        # 2. Project Actions (Row)
        project_row = QHBoxLayout()
        project_row.setSpacing(8)
        
        self.btn_open_flp = QPushButton(" FLP")
        self.btn_open_flp.setIcon(get_icon("fl_studio", QColor("#f1f5f9"), 14))
        self.btn_open_flp.setObjectName("detailButton")
        self.btn_open_flp.clicked.connect(self.open_flp)
        project_row.addWidget(self.btn_open_flp, 1)
        
        self.btn_open_folder = QPushButton(" Folder")
        self.btn_open_folder.setIcon(get_icon("folder_open", QColor("#f1f5f9"), 14))
        self.btn_open_folder.setObjectName("detailButton")
        self.btn_open_folder.clicked.connect(self.open_project_folder)
        project_row.addWidget(self.btn_open_folder, 1)
        
        actions_layout.addLayout(project_row)
        
        # 3. Organize Actions (Row)
        organize_row = QHBoxLayout()
        organize_row.setSpacing(8)
        
        self.btn_tags = QPushButton(" Tags")
        self.btn_tags.setIcon(get_icon("tag", QColor("#22c55e"), 14))
        self.btn_tags.setObjectName("detailButton")
        self.btn_tags.clicked.connect(self.show_tag_editor)
        organize_row.addWidget(self.btn_tags, 1)
        
        self.btn_analyze = QPushButton(" Analyze")
        self.btn_analyze.setIcon(get_icon("analyze", QColor("#a855f7"), 14))
        self.btn_analyze.setObjectName("detailButton")
        self.btn_analyze.clicked.connect(self.analyze_track)
        organize_row.addWidget(self.btn_analyze, 1)
        
        actions_layout.addLayout(organize_row)
        
        # 4. More Actions (Row)
        more_row = QHBoxLayout()
        more_row.setSpacing(8)
        
        self.btn_favorite = QPushButton(" Fav")
        self.btn_favorite.setIcon(get_icon("heart", QColor("#f1f5f9"), 14))
        self.btn_favorite.setObjectName("detailButton")
        self.btn_favorite.clicked.connect(self.toggle_favorite)
        more_row.addWidget(self.btn_favorite, 1)
        
        self.btn_add_playlist = QPushButton(" Playlist")
        self.btn_add_playlist.setIcon(get_icon("playlist", QColor("#38bdf8"), 14))
        self.btn_add_playlist.setObjectName("detailButton")
        self.btn_add_playlist.clicked.connect(self.show_add_to_playlist)
        more_row.addWidget(self.btn_add_playlist, 1)
        
        actions_layout.addLayout(more_row)

        
        details_layout.addWidget(actions_group)
        
        # Project folders section
        folders_group = QGroupBox("PROJECT FOLDERS")
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setSpacing(6)
        folders_layout.setContentsMargins(10, 14, 10, 10)
        
        self.btn_samples = QPushButton("Samples (0)")
        self.btn_samples.setObjectName("detailButton")
        self.btn_samples.clicked.connect(lambda: self.open_subfolder("samples"))
        folders_layout.addWidget(self.btn_samples)
        
        self.btn_stems = QPushButton("Stems (0)")
        self.btn_stems.setObjectName("detailButton")
        self.btn_stems.clicked.connect(lambda: self.open_subfolder("stems"))
        folders_layout.addWidget(self.btn_stems)
        
        self.btn_audio = QPushButton("Audio (0)")
        self.btn_audio.setObjectName("detailButton")
        self.btn_audio.clicked.connect(lambda: self.open_subfolder("audio"))
        folders_layout.addWidget(self.btn_audio)
        
        self.btn_backup = QPushButton("Backup (0)")
        self.btn_backup.setObjectName("detailButton")
        self.btn_backup.clicked.connect(lambda: self.open_subfolder("backup"))
        folders_layout.addWidget(self.btn_backup)
        
        details_layout.addWidget(folders_group)
        
        # Notes section
        notes_group = QGroupBox("NOTES")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setContentsMargins(10, 14, 10, 10)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add notes...")
        self.notes_edit.setMaximumHeight(70)
        self.notes_edit.textChanged.connect(self.save_notes)
        notes_layout.addWidget(self.notes_edit)
        
        details_layout.addWidget(notes_group)
        
        details_layout.addStretch()
        
        details_scroll.setWidget(details_container)
        content.addWidget(details_scroll)
        
        main_layout.addLayout(content, 1)
        
        # === QUEUE PANEL ===
        self.queue_panel = QueuePanel()
        self.queue_panel.track_clicked.connect(self.play_track)
        main_layout.addWidget(self.queue_panel)
        
        # === PLAYER BAR ===
        player_bar = QFrame()
        player_bar.setObjectName("playerBar")
        player_bar.setFixedHeight(120)
        player_layout = QHBoxLayout(player_bar)
        player_layout.setContentsMargins(16, 8, 16, 8)
        player_layout.setSpacing(16)
        
        # Now playing info (enhanced with BPM/Key chips)
        now_playing = QVBoxLayout()
        now_playing.setSpacing(2)
        
        self.player_title = MarqueeLabel("No track playing")
        self.player_title.setObjectName("trackTitle")
        self.player_title.setFixedWidth(200)
        self.player_project = MarqueeLabel("")
        self.player_project.setObjectName("trackProject")
        self.player_project.setFixedWidth(200)
        
        # BPM/Key chips row
        metadata_row = QHBoxLayout()
        metadata_row.setSpacing(8)
        
        self.player_bpm_label = QLabel("")
        self.player_bpm_label.setStyleSheet("""
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.player_bpm_label.hide()
        metadata_row.addWidget(self.player_bpm_label)
        
        self.player_key_label = QLabel("")
        self.player_key_label.setStyleSheet("""
            background: rgba(167, 139, 250, 0.15);
            color: #a78bfa;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.player_key_label.hide()
        metadata_row.addWidget(self.player_key_label)
        metadata_row.addStretch()
        
        now_playing.addWidget(self.player_title)
        now_playing.addWidget(self.player_project)
        now_playing.addLayout(metadata_row)
        player_layout.addLayout(now_playing)
        
        player_layout.addStretch()
        
        # Playback controls
        # Center section (Controls + Progress)
        center_layout = QVBoxLayout()
        center_layout.setSpacing(6)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Row 1: Controls
        controls = QHBoxLayout()
        controls.setSpacing(16)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Shuffle
        self.btn_shuffle = QPushButton("")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setIcon(get_icon("shuffle", QColor("#94a3b8"), 18))
        self.btn_shuffle.setIconSize(QSize(18, 18))
        self.btn_shuffle.setObjectName("playerButton")
        self.btn_shuffle.clicked.connect(self.toggle_shuffle)
        controls.addWidget(self.btn_shuffle)
        
        self.btn_prev = QPushButton("")
        self.btn_prev.setIcon(get_icon("prev", QColor("#94a3b8"), 20))
        self.btn_prev.setIconSize(QSize(20, 20))
        self.btn_prev.setObjectName("playerButton")
        self.btn_prev.clicked.connect(self.player.previous)
        controls.addWidget(self.btn_prev)
        
        self.btn_play_pause = QPushButton("")
        self.btn_play_pause.setIcon(get_icon("play", QColor("#0c1117"), 28))
        self.btn_play_pause.setIconSize(QSize(28, 28))
        self.btn_play_pause.setObjectName("playButton")
        self.btn_play_pause.clicked.connect(self.player.toggle_play)
        controls.addWidget(self.btn_play_pause)
        
        self.btn_next = QPushButton("")
        self.btn_next.setIcon(get_icon("next", QColor("#94a3b8"), 20))
        self.btn_next.setIconSize(QSize(20, 20))
        self.btn_next.setObjectName("playerButton")
        self.btn_next.clicked.connect(self.player.next)
        controls.addWidget(self.btn_next)
        
        # Repeat
        self.btn_repeat = QPushButton("")
        self.btn_repeat.setIcon(get_icon("repeat", QColor("#94a3b8"), 18))
        self.btn_repeat.setIconSize(QSize(18, 18))
        self.btn_repeat.setObjectName("playerButton")
        self.btn_repeat.clicked.connect(self.cycle_repeat)
        controls.addWidget(self.btn_repeat)
        
        # Lock buttons
        self.btn_shuffle.setFixedSize(32, 32)
        self.btn_prev.setFixedSize(32, 32)
        self.btn_play_pause.setFixedSize(40, 40)
        self.btn_next.setFixedSize(32, 32)
        self.btn_repeat.setFixedSize(32, 32)
        
        center_layout.addLayout(controls)
        
        # Row 2: Waveform visualization
        self.mini_waveform = MiniWaveformWidget()
        self.mini_waveform.setFixedHeight(30)
        self.mini_waveform.setFixedWidth(450)
        self.mini_waveform.seek_requested.connect(self._on_waveform_seek)
        center_layout.addWidget(self.mini_waveform)
        
        # Row 3: Progress (Time - Slider - Time)
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        
        self.time_current = QLabel("0:00")
        self.time_current.setObjectName("timeLabel")
        progress_row.addWidget(self.time_current)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setObjectName("progressSlider")
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderReleased.connect(self.seek)
        self.progress_slider.setFixedWidth(400)
        progress_row.addWidget(self.progress_slider)
        
        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("timeLabel")
        progress_row.addWidget(self.time_total)
        
        center_layout.addLayout(progress_row)
        
        player_layout.addLayout(center_layout)
        
        player_layout.addStretch()
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)
        
        self.btn_mute = QPushButton("")
        self.btn_mute.setIcon(get_icon("volume", QColor("#94a3b8"), 20))
        self.btn_mute.setIconSize(QSize(20, 20))
        self.btn_mute.setObjectName("playerButton")
        self.btn_mute.clicked.connect(self.player.toggle_mute)
        volume_layout.addWidget(self.btn_mute)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.valueChanged.connect(self._set_volume)
        volume_layout.addWidget(self.volume_slider)
        
        player_layout.addLayout(volume_layout)
        
        main_layout.addWidget(player_bar)
        
        # Apply stylesheet
        self.setStyleSheet(DARK_STYLE)
        
        # Disable buttons initially
        self.update_detail_buttons(None)
    
    def _set_volume(self, value):
        """Set player volume."""
        self.player.volume = value / 100
    
    def _create_nav_button(self, text, icon_name, checked=False):
        """Create a navigation button."""
        btn = QPushButton(text)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.setChecked(checked)
        if icon_name:
            # Use tint color for icon depending on state? 
            # For now just load generic, maybe tint if we want active state logic
            # Primary = #38bdf8, Text = #94a3b8
            btn.setIcon(get_icon(icon_name, QColor("#94a3b8"), 20))
            btn.setIconSize(QSize(20, 20))
        return btn
    
    def set_page(self, page):
        """Switch between pages."""
        self.nav_favorites.setChecked(page == "favorites")
        self.nav_playlists.setChecked(page == "playlists")
        self.nav_settings.setChecked(page == "settings")
        self.nav_recent.setChecked(page == "recent")
        self.nav_missing.setChecked(page == "missing")
        
        if page == "library":
            self.load_tracks()
        elif page == "favorites":
            self.load_favorites()
        elif page == "settings":
            # Open settings dialog
            SettingsDialog.show_settings(self)
            # Uncheck after dialog closes
            self.nav_settings.setChecked(False)
        elif page == "playlists":
            # Show playlist manager dialog
            self.show_playlist_manager()
        elif page == "recent":
            self.load_recently_added()
            self.stack.setCurrentIndex(0)
        elif page == "missing":
            self.load_missing_metadata()
            self.stack.setCurrentIndex(0)

    def load_recently_added(self):
        """Load tracks sorted by date added (newest first)."""
        # self.tracks_data = sorted(get_all_tracks(limit=500), key=lambda x: x.get('mtime', 0), reverse=True)
        # Assuming get_all_tracks returns unsorted or ID-sorted
        all_tracks = get_all_tracks(limit=1000)
        self.tracks_data = sorted(all_tracks, key=lambda x: x.get('mtime', 0), reverse=True)
        self.update_track_list()
        
    def load_missing_metadata(self):
        """Load tracks with missing BPM or Key."""
        all_tracks = get_all_tracks(limit=5000)
        self.tracks_data = [
            t for t in all_tracks 
            if (not t.get('bpm_user') and not t.get('bpm_detected')) 
            or (not t.get('key_user') and not t.get('key_detected'))
        ]
        self.update_track_list()

    
    def load_recently_added(self):
        """Load tracks sorted by date added (newest first)."""
        self.title_label = self.findChild(QLabel, "sectionTitle") # Update title if we had one? 
        # Actually let's just sort current data or fetch sorted
        self.tracks_data = sorted(get_all_tracks(limit=500), key=lambda x: x.get('mtime', 0), reverse=True)
        self.update_track_list()
        
    def load_missing_metadata(self):
        """Load tracks with missing BPM or Key."""
        all_tracks = get_all_tracks(limit=5000)
        self.tracks_data = [
            t for t in all_tracks 
            if not t.get('bpm_user') and not t.get('bpm_detected') 
            or not t.get('key_user') and not t.get('key_detected')
        ]
        self.update_track_list()
    
    def show_playlist_manager(self):
        """Show playlist manager as a modal dialog."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Playlists")
        dialog.setMinimumSize(400, 500)
        dialog.setStyleSheet("""
            QDialog { background: #0f172a; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        playlist_panel = PlaylistPanel()
        playlist_panel.playlist_play.connect(lambda pid: self.play_playlist(pid))
        layout.addWidget(playlist_panel)
        
        dialog.exec()
        self.nav_playlists.setChecked(False)
    
    def play_playlist(self, playlist_id):
        """Play all tracks in a playlist."""
        from .scanner.playlist_manager import get_playlist_tracks
        tracks = get_playlist_tracks(playlist_id)
        if tracks:
            self.tracks_data = tracks
            self.update_track_list()
            if tracks:
                self.play_track(tracks[0])

    
    def load_tracks(self):
        """Load all tracks from database."""
        self.tracks_data = get_all_tracks(limit=5000)
        self.update_track_list()
    
    def load_favorites(self):
        """Load favorite tracks."""
        self.tracks_data = get_favorite_tracks()
        self.update_track_list()
    
    def update_track_list(self):
        """Update the track list widget."""
        self.track_list.setRowCount(0)
        self.track_list.setRowCount(len(self.tracks_data))
        
        for row, track in enumerate(self.tracks_data):
            title = track.get('title', 'Unknown')
            project = track.get('project_name', '')
            # Use mtime for date added/created
            date_added = format_smart_date(track.get('mtime', 0))
            bpm = track.get('bpm_user') or track.get('bpm_detected')
            key = track.get('key_user') or track.get('key_detected')
            
            bpm_str = f"{bpm:.0f}" if bpm else ""
            key_str = str(key) if key else ""
            genre_str = track.get('genre') or ""
            
            # 0. Icon / Index
            # If playing, show play icon, else show number or favorite heart?
            # Let's show heart if favorite, else logic later
            icon_item = QTableWidgetItem("")
            if track.get('favorite'):
                icon_item.setIcon(get_icon("heart", QColor("#ef4444"), 16))
            else:
                icon_item.setText(str(row + 1))
            icon_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            # Store the track ID in the item data for retrieval after sorting
            icon_item.setData(Qt.ItemDataRole.UserRole, track.get('id'))
            self.track_list.setItem(row, 0, icon_item)
            
            # 1. Title
            title_item = QTableWidgetItem(title)
            title_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            # Store the track ID in all items for easy retrieval
            title_item.setData(Qt.ItemDataRole.UserRole, track.get('id'))
            self.track_list.setItem(row, 1, title_item)
            
            # 2. Project
            proj_item = QTableWidgetItem(project)
            proj_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            # proj_item.setForeground(QBrush(QColor("#94a3b8")))
            self.track_list.setItem(row, 2, proj_item)
            
            # 3. Date
            date_item = QTableWidgetItem(date_added)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            date_item.setForeground(QBrush(QColor("#94a3b8")))
            # Tooltip for full date
            full_date = format_timestamp(track.get('mtime', 0))
            date_item.setToolTip(f"Added: {full_date}")
            self.track_list.setItem(row, 3, date_item)
            
            # 4. BPM
            bpm_item = QTableWidgetItem(bpm_str)
            bpm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bpm_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if bpm:
                bpm_item.setForeground(QBrush(QColor("#38bdf8")))
                bpm_item.setToolTip(f"{bpm} BPM")
            else:
                 bpm_item.setForeground(QBrush(QColor("#475569")))
            self.track_list.setItem(row, 4, bpm_item)
            
            # 5. Key
            key_item = QTableWidgetItem(key_str)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if key:
                key_item.setForeground(QBrush(QColor("#a78bfa")))
                key_item.setToolTip(f"Key: {key}")
            else:
                key_item.setForeground(QBrush(QColor("#475569")))
            self.track_list.setItem(row, 5, key_item)
            
            # 6. Genre
            genre_item = QTableWidgetItem(genre_str)
            genre_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            genre_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if genre_str:
                genre_item.setToolTip(f"Genre: {genre_str}")
            self.track_list.setItem(row, 6, genre_item)
            
            # 7. View icon (Eye)
            view_item = QTableWidgetItem()
            # We don't have an eye icon in ICONS yet, use search/folder or add eye. 
            # I will assume I can add "eye" to icons.py later or reuse search for now.
            # search icon: checklist-minimalistic... let's use "folder_open" temporarily or "search"
            # Actually, let's use "folder_open" but maybe tint it differently or "search"
            # Better to add "eye" to icons.py. For now I'll use "search" (magnifying glass look)
            view_item.setIcon(get_icon("search", QColor("#facc15"), 14)) # Yellow/Gold
            view_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            view_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            view_item.setToolTip("View Project details")
            self.track_list.setItem(row, 7, view_item)
            
            # 8. Add to Playlist icon
            playlist_item = QTableWidgetItem()
            playlist_item.setIcon(get_icon("playlist", QColor("#38bdf8"), 14))
            playlist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            playlist_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            playlist_item.setToolTip("Add to Playlist (P)")
            self.track_list.setItem(row, 8, playlist_item)
            
            # 9. Tags icon
            tags_item = QTableWidgetItem()
            tags_item.setIcon(get_icon("tag", QColor("#22c55e"), 14))
            tags_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tags_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            tags_item.setToolTip("Edit Tags (T)")
            self.track_list.setItem(row, 9, tags_item)
            
            # 10. Analyze icon
            analyze_item = QTableWidgetItem()
            analyze_item.setIcon(get_icon("analyze", QColor("#a855f7"), 14))
            analyze_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            analyze_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            analyze_item.setToolTip("Analyze BPM/Key (B)")
            self.track_list.setItem(row, 10, analyze_item)
            
            # 11. Edit Metadata icon
            edit_item = QTableWidgetItem()
            edit_item.setIcon(get_icon("edit", QColor("#64748b"), 14))
            edit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            edit_item.setToolTip("Edit Metadata (E)")
            self.track_list.setItem(row, 11, edit_item)
        
        self.track_count_label.setText(f"{len(self.tracks_data)} tracks")
        
    def _get_track_from_row(self, row):
        """Get track from visual row (works correctly after sorting).
        
        Retrieves the track ID from the table item's data and looks up
        the full track in the tracks_data list.
        """
        item = self.track_list.item(row, 0)  # Get first column item
        if not item:
            return None
        
        track_id = item.data(Qt.ItemDataRole.UserRole)
        if not track_id:
            return None
        
        # Find track by ID
        for track in self.tracks_data:
            if track.get('id') == track_id:
                return track
        return None
    
    def on_track_clicked(self, row, col):
        """Handle table single click."""
        track = self._get_track_from_row(row)
        if not track:
            return
        
        self.current_track = track
        
        # Handle action column clicks
        if col == 7:  # View Project
            self.project_panel.set_track(track['id'])
            self.stack.setCurrentIndex(1)
            return
        elif col == 8:  # Playlist
            self.show_add_to_playlist()
            return
        elif col == 9:  # Tags
            self.show_tag_editor()
            return
        elif col == 10:  # Analyze
            self.analyze_track()
            return
        elif col == 11:  # Edit
            self.edit_metadata()
            return
        
        # Regular click - update details panel
        self.update_details_panel(track)
            
    def on_track_double_clicked_table(self, row, col):
        """Handle table double click."""
        track = self._get_track_from_row(row)
        if not track:
            return
        
        self.current_track = track
        self.play_track(track)
            
    # ... (skipping some methods untouched) ...
    
    def open_subfolder(self, folder_type):
        """Open a project subfolder in the integrated Project View."""
        if not self.current_track:
            return
            
        # Set track and Switch to project view
        self.project_panel.set_track(self.current_track['id'])
        
        # Switch to the requested tab
        if folder_type == 'stems':
            self.project_panel.tabs.setCurrentIndex(1)
        elif folder_type == 'samples':
            self.project_panel.tabs.setCurrentIndex(2)
        elif folder_type == 'backup':
            self.project_panel.tabs.setCurrentIndex(3)
        else: # audio/renders
            self.project_panel.tabs.setCurrentIndex(0)
            
        self.stack.setCurrentIndex(1)
    
    def on_filter_chip_clicked(self):
        """Handle filter chip click."""
        # Refresh search based on all checked chips
        self.on_search(self.search_input.text())

    def on_search(self, text):
        """Handle search input with chips."""
        # Collect active filters
        favorites_only = self.chip_fav.isChecked()
        tags = []
        
        no_bpm = False
        no_key = False
        
        for btn in self.filter_group.buttons():
            if btn.isChecked():
                data = btn.property("filter_data")
                if not data: continue
                
                if data == "favorites":
                    continue # Handled
                elif data == "no_bpm":
                    no_bpm = True
                elif data == "no_key":
                    no_key = True
                elif data.startswith("genre:"):
                    tags.append(data.split(":", 1)[1])
        
        # Note: search_tracks backend might need updates to handle no_bpm/no_key if not supported
        # Current search_tracks supports: term, key, tags, favorites_only
        # We need to handle no_bpm/key. 
        # If search_tracks doesn't support it, we can filter locally or update search_tracks.
        # Let's filter locally for now to be safe, or update search_tracks if easy.
        # Given we have 5000 limit, local filter is fast enough.
        
        # 1. Base Search
        results = search_tracks(
            term=text,
            key=None, # Filter selection removed, relying on text or no_key
            tags=tags if tags else None,
            favorites_only=favorites_only,
        )
        
        # 2. Apply extended filters
        final_results = []
        for t in results:
            if no_bpm and (t.get('bpm_user') or t.get('bpm_detected')):
                continue
            if no_key and (t.get('key_user') or t.get('key_detected')):
                continue
            final_results.append(t)
            
        self.tracks_data = final_results
        self.update_track_list()
    
    def on_track_selected(self, item):
        """Handle track selection - show details."""
        track = item.data(Qt.ItemDataRole.UserRole)
        self.current_track = track
        self.update_details_panel(track)
    
    def on_track_double_clicked(self, item):
        """Handle track double-click - play it."""
        track = item.data(Qt.ItemDataRole.UserRole)
        self.current_track = track
        self.play_track(track)
    
    def update_details_panel(self, track):
        """Update the details panel with track info."""
        if not track:
            self.detail_title.setText("Select a track")
            self.detail_project.setText("")
            self.update_detail_buttons(None)
            return
        
        # Get full track details
        full_track = get_track_by_id(track['id'])
        if full_track:
            track = full_track
            self.current_track = track
        
        # Cover Art
        project_path = track.get('project_path')
        cover_path = get_cover_art(project_path)
        if cover_path:
            # Load cover
            pixmap = QPixmap(cover_path)
            self.cover_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # Placeholder
            self.cover_label.setPixmap(get_placeholder_cover(200, track.get('title', '')))

        # Basic info
        self.detail_title.setText(track.get('title', 'Unknown'))
        self.detail_project.setText(track.get('project_name', ''))
        
        # Metadata
        bpm = track.get('bpm_user') or track.get('bpm_detected')
        key = track.get('key_user') or track.get('key_detected')
        duration = track.get('duration', 0)
        size = track.get('file_size', 0)
        
        # Helper for quick-fill links
        def make_link(text_id):
            return f'<a href="{text_id}" style="color:#38bdf8; text-decoration:none;">+ Add</a>'

        if bpm:
            self.detail_bpm.setText(format_bpm(bpm))
        else:
            self.detail_bpm.setText(make_link("bpm"))
            
        if key:
            self.detail_key.setText(format_key(key))
        else:
            self.detail_key.setText(make_link("key"))
            
        if duration:
            self.detail_duration.setText(format_duration(duration))
        else:
            self.detail_duration.setText("--") # Duration usually auto-detected, can't manually edit easily yet
            
        self.detail_size.setText(format_file_size(size) if size else "--")
        
        genre = track.get('genre')
        if genre:
            self.detail_genre.setText(genre)
        else:
            self.detail_genre.setText(make_link("genre"))
        
        # Favorite button
        if track.get('favorite'):
            self.btn_favorite.setText("Remove Favorite")
            self.btn_favorite.setIcon(get_icon("heart", QColor("#ef4444"), 16))
        else:
            self.btn_favorite.setText("Add Favorite")
            self.btn_favorite.setIcon(get_icon("heart", QColor("#94a3b8"), 16))
        
        # Count files in subfolders
        samples_dir = track.get('samples_dir') or ''
        stems_dir = track.get('stems_dir') or ''
        audio_dir = track.get('audio_dir') or ''
        backup_dir = track.get('backup_dir') or ''
        
        samples_count = count_files_in_folder(samples_dir, AUDIO_EXTENSIONS) if samples_dir else 0
        stems_count = count_files_in_folder(stems_dir, AUDIO_EXTENSIONS) if stems_dir else 0
        audio_count = count_files_in_folder(audio_dir, AUDIO_EXTENSIONS) if audio_dir else 0
        backup_count = count_files_in_folder(backup_dir, {'.flp'}) if backup_dir else 0
        
        self.btn_samples.setText(f"Samples ({samples_count})")
        self.btn_samples.setEnabled(bool(samples_dir and samples_count > 0))
        
        self.btn_stems.setText(f"Stems ({stems_count})")
        self.btn_stems.setEnabled(bool(stems_dir and stems_count > 0))
        
        self.btn_audio.setText(f"Audio ({audio_count})")
        self.btn_audio.setEnabled(bool(audio_dir and audio_count > 0))
        
        self.btn_backup.setText(f"Backup ({backup_count})")
        self.btn_backup.setEnabled(bool(backup_dir and backup_count > 0))
        
        # Notes
        self.notes_edit.blockSignals(True)
        self.notes_edit.setText(track.get('notes') or '')
        self.notes_edit.blockSignals(False)
        
        # Update buttons
        self.update_detail_buttons(track)
    
    def update_detail_buttons(self, track):
        """Enable/disable action buttons based on track."""
        has_track = track is not None
        has_flp = bool(has_track and track.get('flp_path'))
        
        self.btn_play.setEnabled(bool(has_track))
        self.btn_open_flp.setEnabled(bool(has_flp))
        self.btn_open_folder.setEnabled(bool(has_track))
        self.btn_favorite.setEnabled(bool(has_track))
        self.btn_analyze.setEnabled(bool(has_track))
    
    def play_current_track(self):
        """Play the currently selected track."""
        if self.current_track:
            self.play_track(self.current_track)
    
    def play_track(self, track):
        """Play a specific track.
        
        Builds the playlist from the current visual table order (after sorting)
        so that next/previous navigation works correctly with the sorted view.
        """
        if not track:
            return
            
        # Phase 3: Check file existence
        path = track.get('path')
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", 
                              f"Could not find file:\n{path}\n\nIt may have been moved or deleted.")
            return

        # Build playlist from visual table order (respects sorting)
        visual_tracks = []
        for row in range(self.track_list.rowCount()):
            row_track = self._get_track_from_row(row)
            if row_track:
                visual_tracks.append(row_track)
        
        # Use visual order for playlist, or fall back to tracks_data if empty
        playlist_tracks = visual_tracks if visual_tracks else self.tracks_data
        self.player.set_playlist(playlist_tracks)
        
        # Find index in the visual order
        for i, t in enumerate(playlist_tracks):
            if t.get('id') == track.get('id'):
                self.player.play_at_index(i)
                break
    
    def open_flp(self):
        """Open the FLP file in FL Studio."""
        if self.current_track and self.current_track.get('flp_path'):
            fl_path = get_setting('fl_studio_path', '')
            open_fl_studio(self.current_track['flp_path'], fl_path if fl_path else None)
    
    def open_project_folder(self):
        """Open the project folder."""
        if self.current_track and self.current_track.get('project_path'):
            open_folder(self.current_track['project_path'])
    
    def toggle_favorite(self):
        """Toggle favorite status."""
        if self.current_track:
            new_state = toggle_favorite(self.current_track['id'])
            self.current_track['favorite'] = new_state
            
            # Update UI
            self.update_details_panel(self.current_track)
            
            # Update list icon if visible
            # (Requires finding the row, which is expensive, so we just refresh search if needed or rely on next refresh)
            self.on_search(self.search_input.text())
    
    # --- Player Signal Handlers ---
    
    def on_player_state_changed(self, state):
        """Handle player state changes."""
        # Update play/pause button
        if state == PlayerState.PLAYING:
            self.btn_play_pause.setIcon(get_icon("pause", QColor("#0c1117"), 28))
            self.btn_play.setText(" Pause")
            self.btn_play.setIcon(get_icon("pause", QColor("#f1f5f9"), 16))
        else:
            self.btn_play_pause.setIcon(get_icon("play", QColor("#0c1117"), 28))
            self.btn_play.setText(" Play")
            self.btn_play.setIcon(get_icon("play", QColor("#f1f5f9"), 16))
    
    def on_track_changed(self, track):
        """Handle track change."""
        if not track:
            self.player_title.setText("No track playing")
            self.player_project.setText("")
            self.time_current.setText("0:00")
            self.time_total.setText("0:00")
            self.progress_slider.setValue(0)
            self.mini_waveform.clear()
            self.player_bpm_label.hide()
            self.player_key_label.hide()
            self.highlight_playing_row(None)
            self.queue_panel.set_current_track(None)
            self.queue_panel.set_queue([], 0)
            return
            
        self.player_title.setText(track.get('title', 'Unknown'))
        self.player_project.setText(track.get('project_name', ''))
        
        # Update BPM/Key chips
        bpm = track.get('bpm_user') or track.get('bpm_detected')
        key = track.get('key_user') or track.get('key_detected')
        
        if bpm:
            self.player_bpm_label.setText(f"{bpm:.0f} BPM")
            self.player_bpm_label.show()
        else:
            self.player_bpm_label.hide()
            
        if key:
            self.player_key_label.setText(str(key))
            self.player_key_label.show()
        else:
            self.player_key_label.hide()
        
        # Load waveform
        self.mini_waveform.clear()
        if track.get('path'):
            self.mini_waveform.load_waveform(track['path'])
            
        # Highlight the playing row in the table
        self.highlight_playing_row(track.get('id'))
        
        # Update queue panel
        self.queue_panel.set_current_track(track)
        self.queue_panel.set_queue(self.player.playlist, self.player.playlist_index)
    
    def highlight_playing_row(self, track_id):
        """Highlight the row of the currently playing track."""
        accent_color = QColor(56, 189, 248, 40)  # Semi-transparent accent
        accent_text = QColor(56, 189, 248)  # Accent for title
        default_text = QColor(241, 245, 249)  # Normal text
        
        for row in range(self.track_list.rowCount()):
            item = self.track_list.item(row, 0)
            if not item:
                continue
                
            row_track_id = item.data(Qt.ItemDataRole.UserRole)
            is_playing = (row_track_id == track_id) if track_id else False
            
            # Apply style to all cells in the row
            for col in range(self.track_list.columnCount()):
                cell = self.track_list.item(row, col)
                if cell:
                    if is_playing:
                        cell.setBackground(QBrush(accent_color))
                        if col == 1:  # Title column gets accent text
                            cell.setForeground(QBrush(accent_text))
                    else:
                        cell.setBackground(QBrush(QColor(0, 0, 0, 0)))  # Transparent
                        cell.setForeground(QBrush(default_text))
            
            # Update icon column for playing indicator
            if is_playing:
                item.setIcon(get_icon("play", QColor("#38bdf8"), 14))
                item.setText("")
            elif self.tracks_data:
                # Find track to check if favorite
                for t in self.tracks_data:
                    if t.get('id') == row_track_id:
                        if t.get('favorite'):
                            item.setIcon(get_icon("heart", QColor("#ef4444"), 16))
                            item.setText("")
                        else:
                            item.setIcon(QIcon())
                            item.setText(str(row + 1))
                        break
    
    def on_duration_changed(self, duration):
        """Handle duration update."""
        self.time_total.setText(format_duration(duration))
    
    def update_position(self):
        """Update playback position (timer)."""
        if self.player.state == PlayerState.PLAYING:
            pos = self.player.position
            duration = self.player.duration
            
            # Fix: pos is 0-1 percentage, need seconds for format_duration
            if duration > 0:
                current_seconds = pos * duration
            else:
                # Fallback to track data duration if player hasn't loaded it
                track_duration = self.current_track.get('duration', 0) if self.current_track else 0
                current_seconds = pos * track_duration
                
            self.time_current.setText(format_duration(current_seconds))
            
            if duration > 0:
                # Update slider
                if not self.progress_slider.isSliderDown():
                    value = int((pos) * 1000)
                    self.progress_slider.setValue(value)
                
                # Update waveform
                self.mini_waveform.set_position(pos)
    
    def seek(self):
        """Handle slider seek."""
        value = self.progress_slider.value()
        if self.player.duration > 0:
            pos = (value / 1000) * self.player.duration
            self.player.seek(pos)
    
    def _on_waveform_seek(self, position):
        """Handle waveform seek."""
        if self.player.duration > 0:
            time_pos = position * self.player.duration
            self.player.seek(time_pos)
            
    def cycle_repeat(self):
        """Cycle repeat modes."""
        self.player.cycle_repeat_mode()
        
        mode = self.player.repeat_mode
        color = QColor("#38bdf8") if mode != RepeatMode.OFF else QColor("#94a3b8")
        icon = "repeat_one" if mode == RepeatMode.ONE else "repeat"
        
        self.btn_repeat.setIcon(get_icon(icon, color, 18))
        
    def toggle_shuffle(self):
        """Toggle shuffle."""
        self.player.toggle_shuffle()
        is_on = self.player.shuffle
        color = QColor("#38bdf8") if is_on else QColor("#94a3b8")
        self.btn_shuffle.setIcon(get_icon("shuffle", color, 18))
    
    def _play_external_file(self, path):
        """Play a file from the drill-down panel (not in library)."""
        # For now, just open it using the system default player/handler
        try:
            open_file(path)
        except Exception as e:
            logger.error(f"Failed to play external file: {e}")
    
    def analyze_track(self):
        """Analyze track for BPM and Key."""
        if not self.current_track:
            return
        
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")
        
        self.analysis_thread = AnalyzerThread(
            self.current_track['path'],
            self.current_track['id']
        )
        self.analysis_thread.finished.connect(self.on_analysis_complete)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()
    
    def on_analysis_complete(self, result):
        """Handle analysis completion."""
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("~ Analyze BPM/Key")
        
        if result and not result.error:
            # Update display
            if self.current_track:
                self.current_track['bpm_detected'] = result.bpm
                self.current_track['key_detected'] = result.key
                self.current_track['duration'] = result.duration
                self.update_details_panel(self.current_track)
            
            QMessageBox.information(
                self, "Analysis Complete",
                f"BPM: {format_bpm(result.bpm)}\nKey: {format_key(result.key)}"
            )
    
    def on_analysis_error(self, error_msg):
        """Handle analysis error."""
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("~ Analyze BPM/Key")
        QMessageBox.warning(self, "Analysis Failed", error_msg)
    
    def save_notes(self):
        """Save notes for current track."""
        if self.current_track:
            notes = self.notes_edit.toPlainText()
            update_track_metadata(self.current_track['id'], notes=notes)
    
    def rescan_library(self):
        """Start library rescan."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        
        self.rescan_btn.setEnabled(False)
        self.rescan_btn.setText("Scanning...")
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)  # Indeterminate
        
        self.scanner_thread = ScannerThread()
        self.scanner_thread.progress.connect(self.on_scan_progress)
        self.scanner_thread.finished.connect(self.on_scan_finished)
        self.scanner_thread.error.connect(self.on_scan_error)
        self.scanner_thread.start()
    
    def on_scan_progress(self, current, total, message):
        """Handle scan progress."""
        self.scan_progress.setRange(0, total)
        self.scan_progress.setValue(current)
        self.scan_status.setText(message)
    
    def on_scan_finished(self, result):
        """Handle scan completion."""
        self.rescan_btn.setEnabled(True)
        self.rescan_btn.setText("Rescan Library")
        self.scan_progress.setVisible(False)
        self.scan_status.setText(
            f"{result.projects_found} projects, {result.tracks_found} tracks"
        )
        self.load_tracks()
    
    def on_scan_error(self, error_msg):
        """Handle scan error."""
        self.rescan_btn.setEnabled(True)
        self.rescan_btn.setText("Rescan Library")
        self.scan_progress.setVisible(False)
        self.scan_status.setText(f"Error: {error_msg}")
    
    def add_library_folder(self):
        """Add a new library folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Library Folder"
        )
        if folder:
            scanner = LibraryScanner()
            if scanner.add_library_root(folder):
                self.scan_status.setText(f"Added: {folder}")
                self.rescan_library()
            else:
                QMessageBox.warning(self, "Error", "Failed to add folder")
    
    def check_first_run(self):
        """Check if this is the first run."""
        scanner = LibraryScanner()
        roots = scanner.get_library_roots()
        
        if not roots:
            # Try default folder
            default_root = r"F:\1.Project FL S1"
            if os.path.isdir(default_root):
                scanner.add_library_root(default_root)
                self.scan_status.setText(f"Using: {default_root}")
                self.rescan_library()
            else:
                self.scan_status.setText("Add a folder to start")
    
    # Player event handlers
    def on_player_state_changed(self, state):
        """Handle player state changes."""
        if state == PlayerState.PLAYING:
            self.btn_play_pause.setText("")
            self.btn_play_pause.setIcon(get_icon("pause", QColor("#0c1117"), 32))
        else:
            self.btn_play_pause.setText("")
            self.btn_play_pause.setIcon(get_icon("play", QColor("#0c1117"), 32))
    
    def on_track_changed(self, track):
        """Handle track change in player."""
        if track:
            self.player_title.setText(track.get('title', 'Unknown'))
            self.player_project.setText(track.get('project_name', ''))
            
            # Highlight in list
            for i, t in enumerate(self.tracks_data):
                if t['id'] == track['id']:
                    self.track_list.selectRow(i)
                    break
            
            # Update details if different
            # Note: might be redundant if selection triggers detail update, but safer
            self.update_details_panel(track)
        else:
            self.player_title.setText("No track playing")
            self.player_project.setText("")
    
    def on_duration_changed(self, duration):
        """Handle duration change."""
        self.time_total.setText(format_duration(duration))
    
    def update_position(self):
        """Update playback position display."""
        if self.player.state == PlayerState.PLAYING:
            pos = self.player.position
            dur = self.player.duration
            
            if not self.progress_slider.isSliderDown():
                self.progress_slider.setValue(int(pos * 1000))
            
            self.time_current.setText(format_duration(pos * dur))
    
    def seek(self):
        """Seek to slider position."""
        pos = self.progress_slider.value() / 1000
        self.player.seek(pos)
        
    def toggle_shuffle(self):
        """Toggle shuffle mode."""
        self.player.toggle_shuffle()
        # Update button state
        is_shuffle = self.player.shuffle
        self.btn_shuffle.setChecked(is_shuffle)
        self.btn_shuffle.setIcon(get_icon("shuffle", QColor("#38bdf8") if is_shuffle else QColor("#94a3b8"), 20))
        
    def cycle_repeat(self):
        """Cycle repeat mode."""
        self.player.cycle_repeat()
        # Update button icon
        mode = self.player.repeat
        icon_name = "repeat"
        color = QColor("#94a3b8")
        
        if mode == RepeatMode.ONE:
            icon_name = "repeat_one"
            color = QColor("#38bdf8")
        elif mode == RepeatMode.ALL:
            color = QColor("#38bdf8")
            
        self.btn_repeat.setIcon(get_icon(icon_name, color, 20))
        
    def on_genre_filter(self, genre):
        """Handle genre filter change."""
        self.on_search(self.search_input.text())
        
    def edit_metadata(self):
        """Open metadata edit dialog."""
        if not self.current_track:
            return
            
        dialog = MetadataEditDialog(self.current_track, self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Update DB
            update_track_metadata(
                self.current_track['id'],
                bpm=data['bpm'],
                key=data['key'],
                notes=data['notes']
            )
            
            # Update Tags (Genres)
            if 'tags' in data:
                update_track_tags(self.current_track['id'], data['tags'])
            
            # Refresh UI
            self.load_tracks()
            # Update details panel with fresh data
            new_track = get_track_by_id(self.current_track['id'])
            if new_track:
                self.current_track = new_track
                self.update_details_panel(new_track)
    
    def closeEvent(self, event):
        """Handle window close."""
        self.player.cleanup()
        if self.scanner_thread:
            self.scanner_thread.cancel()
        event.accept()
    
    def show_track_context_menu(self, pos):
        """Show right-click context menu for track list."""
        row = self.track_list.rowAt(pos.y())
        if row < 0:
            return
        
        track = self._get_track_from_row(row)
        if not track:
            return
        
        self.current_track = track
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1e2836;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #f1f5f9;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(56, 189, 248, 0.2);
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """)
        
        # Play
        play_action = menu.addAction("▶️ Play")
        play_action.triggered.connect(lambda: self.play_track(track))
        
        menu.addSeparator()
        
        # Favorite
        fav_text = "💔 Remove Favorite" if track.get('favorite') else "❤️ Add Favorite"
        fav_action = menu.addAction(fav_text)
        fav_action.triggered.connect(self.toggle_favorite)
        
        # Add to playlist submenu
        playlist_menu = AddToPlaylistMenu(self)
        playlist_menu.set_tracks([track['id']])
        playlist_menu.setTitle("📁 Add to Playlist")
        menu.addMenu(playlist_menu)
        
        # Tags
        tags_action = menu.addAction("🏷️ Edit Tags (T)")
        tags_action.triggered.connect(self.show_tag_editor)
        
        menu.addSeparator()
        
        # Analysis
        analyze_action = menu.addAction("🎵 Analyze BPM/Key (B)")
        analyze_action.triggered.connect(self.analyze_track)
        
        # Edit metadata
        edit_action = menu.addAction("✏️ Edit Metadata (E)")
        edit_action.triggered.connect(self.edit_metadata)
        
        menu.addSeparator()
        
        # Open actions
        folder_action = menu.addAction("📂 Open Folder (O)")
        folder_action.triggered.connect(self.open_project_folder)
        
        if track.get('flp_path'):
            flp_action = menu.addAction("🎹 Open FLP")
            flp_action.triggered.connect(self.open_flp)
        
        menu.exec(self.track_list.mapToGlobal(pos))
    
    def analyze_track(self):
        """Analyze BPM/Key for current track using the new dialog."""
        if not self.current_track:
            return
        
        dialog = AnalysisDialog(self.current_track['id'], self)
        dialog.analysis_complete.connect(self._on_analysis_complete)
        dialog.exec()
    
    def _on_analysis_complete(self, track_id, result):
        """Handle analysis completion."""
        # Refresh the track if it's the current one
        if self.current_track and self.current_track['id'] == track_id:
            new_track = get_track_by_id(track_id)
            if new_track:
                self.current_track = new_track
                self.update_details_panel(new_track)
        
        # Refresh track list
        self.on_search(self.search_input.text())


def main():
    """Main application entry point."""
    # Setup logging
    debug = '--debug' in sys.argv or os.environ.get('FL_LIBRARY_DEBUG')
    setup_logging(debug=bool(debug))
    
    logger.info(f"Starting {__app_name__} v{__version__}")
    logger.info(f"App data path: {get_app_data_path()}")
    
    # Initialize database
    db = get_db()
    logger.info(f"Database initialized: {db.db_path}")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Cleanup on exit
    app.aboutToQuit.connect(db.close)
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
