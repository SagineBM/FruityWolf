"""
FL Library Pro — Main Application

A beautiful, modern library manager and player for FL Studio project folders.
Full-featured widget-based UI with all prototype features.
"""

import sys
import os
import logging
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QSlider, QFrame, QScrollArea, QMessageBox, QTabWidget, QGroupBox,
    QGridLayout, QComboBox, QSpinBox, QTextEdit, QFileDialog, QProgressBar,
    QStackedWidget, QSizePolicy, QToolButton, QMenu, QDialog, QDialogButtonBox,
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
    MiniWaveformWidget, ProjectDrillDownPanel, TrackInfoCard,
    StatusBadge, CommandPaletteDialog, SettingsView
)
from .ui.style import get_stylesheet
from .ui.panels.plugins_panel import PluginAnalyticsPanel, PluginsPanel
from .ui.panels.plugin_details import PluginDetailsPanel
from .ui.projects_view import ProjectsView
from .ui.sample_overview_view import SampleOverviewView
from .ui.sample_detail_view import SampleDetailView
from .ui.plugin_intelligence_view import PluginIntelligenceView
from .ui.panels.track_details import TrackDetailsPanel
from .ui.panels.project_details import ProjectDetailsPanel
from .ui.panels.sample_projects_panel import SampleProjectsPanel
from .ui.panels.renders_panel import RendersPanel
from .player import get_player, PlayerState, RepeatMode
from .waveform import WaveformThread, get_cached_waveform
from .analysis import AnalyzerThread, format_bpm, format_key, KEYS
from .utils import (
    format_duration, format_file_size, format_timestamp, format_smart_date,
    open_file, open_folder, open_fl_studio, count_files_in_folder,
    get_folder_size, setup_logging, get_icon,
    get_cover_art, get_placeholder_cover
)
from .utils.path_utils import validate_path, resolve_fl_path
from .utils.shortcuts import ShortcutManager, DEFAULT_SHORTCUTS
from .services.folder_watcher import FolderWatcher
from .services.batch_analyzer import BackgroundBatchAnalyzer

logger = logging.getLogger(__name__)


# Premium Sky Blue & Slate Theme - Spotify/iTunes level design
# Centralized in FruityWolf.ui.style
DARK_STYLE = get_stylesheet()


class QueuePanel(QFrame):
    """Collapsible queue panel showing 'Now Playing' and 'Next Up'."""
    
    track_clicked = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("queuePanel")
        
        # FruityWolf Theme Colors
        # Background: #111820 (Sidebar/Dark Slate)
        # Border: #1e293b (Slate Border)
        # Text: #f1f5f9 (White-ish)
        # Subtext: #94a3b8 (Slate 400)
        # Accent: #38bdf8 (Sky 400)
        
        self.setStyleSheet("""
            QFrame#queuePanel {
                background-color: #111820;
                border-top: 1px solid #1e293b;
            }
            QLabel#queueHeader {
                font-size: 16px; 
                font-weight: bold; 
                color: #f1f5f9;
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }
            QLabel#sectionHeader {
                font-size: 11px; 
                font-weight: bold; 
                color: #64748b; 
                letter-spacing: 1px;
                margin-top: 16px;
                margin-bottom: 8px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#queueContent {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #111820;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- HEADER ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background: #151d28; border-bottom: 1px solid #1e293b; padding: 12px 16px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Queue")
        title.setObjectName("queueHeader")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #334155;
                border-radius: 12px;
                color: #94a3b8;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #ef4444;
                color: #ef4444;
            }
        """)
        self.clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(self.clear_btn)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 20px;
                font-weight: 300;
            }
            QPushButton:hover {
                color: #f1f5f9;
            }
        """)
        close_btn.clicked.connect(lambda: self.setVisible(False))
        header_layout.addWidget(close_btn)
        
        self.main_layout.addWidget(header_frame)
        
        # --- SCROLL AREA ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("queueContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 0, 20, 20)
        self.content_layout.setSpacing(0)
        
        # 1. NOW PLAYING Section
        self.np_header = QLabel("NOW PLAYING")
        self.np_header.setObjectName("sectionHeader")
        self.content_layout.addWidget(self.np_header)
        
        self.np_container = QVBoxLayout()
        self.np_container.setSpacing(2)
        self.content_layout.addLayout(self.np_container)
        
        # 2. NEXT UP Section
        self.next_header = QLabel("NEXT UP")
        self.next_header.setObjectName("sectionHeader")
        self.content_layout.addWidget(self.next_header)
        
        self.next_container = QVBoxLayout()
        self.next_container.setSpacing(2)
        self.content_layout.addLayout(self.next_container)
        
        self.content_layout.addStretch() # Push everything up
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        # State
        self.setVisible(False)
        self.setFixedHeight(450)
        self._current_track_widget = None
        self._queue_widgets = []
    
    def set_current_track(self, track):
        """Set the currently playing track."""
        self._clear_layout(self.np_container)
        self._current_track_widget = None
        
        if track:
            # Highlighted card style for Now Playing
            row = self._create_track_row(track, is_now_playing=True)
            self.np_container.addWidget(row)
            self._current_track_widget = row
        else:
             lbl = QLabel("No track playing")
             lbl.setStyleSheet("color: #64748b; padding: 12px; font-style: italic;")
             self.np_container.addWidget(lbl)
    
    def set_queue(self, playlist, current_index):
        """Set the queue tracks (Next Up)."""
        self._clear_layout(self.next_container)
        self._queue_widgets = []
        
        if not playlist:
             return

        # Up Next: tracks AFTER the current index
        next_tracks = playlist[current_index + 1 : current_index + 31] # Show up to 30
        
        if not next_tracks:
            lbl = QLabel("End of queue")
            lbl.setStyleSheet("color: #64748b; padding: 12px; font-style: italic;")
            self.next_container.addWidget(lbl)
            return
            
        for i, track in enumerate(next_tracks):
            # Display index relative to the view list (1, 2, 3...)
            row = self._create_track_row(track, index=i+1)
            self.next_container.addWidget(row)
            self._queue_widgets.append(row)
            
    def _create_track_row(self, track, is_now_playing=False, index=None):
        """Create a track row widget using standard theme."""
        widget = QFrame()
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setFixedHeight(64 if is_now_playing else 52)
        
        # Styling
        if is_now_playing:
            # Active Card Style
            bg_normal = "#1e293b" # Slate 800
            bg_hover = "#243042" # Slightly lighter
            border = "1px solid #38bdf8" # Sky Blue Border
            title_color = "#38bdf8" # Sky Blue
        else:
            # Standard List Style
            bg_normal = "transparent"
            bg_hover = "#1e293b"
            border = "none" #  "1px solid #1e293b" bottom border handled by layout spacing or inner line? 
            # Let's add bottom border to widget
            border = "border-bottom: 1px solid #1e293b"
            title_color = "#f1f5f9"

        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_normal};
                border-radius: 6px;
                {border if is_now_playing else 'border-bottom: 1px solid #1e293b; border-radius: 0px;'}
            }}
            QFrame:hover {{
                background-color: {bg_hover};
            }}
        """)
        
        # Grid Layout for robust alignment
        layout = QGridLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setColumnStretch(2, 1) # Title/Project stretches
        
        # 1. Indicator (Col 0)
        ind_lbl = QLabel()
        if is_now_playing:
             ind_lbl.setText("▶") # Or Pulse Icon
             ind_lbl.setStyleSheet("color: #38bdf8; font-size: 14px;")
        else:
             ind_lbl.setText(str(index) if index else "•")
             ind_lbl.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
        
        ind_lbl.setFixedWidth(24)
        ind_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ind_lbl, 0, 0, 2, 1) # Span 2 rows
        
        # 2. Title (Col 2, Row 0)
        title_text = track.get('title', 'Unknown')
        title_lbl = QLabel(title_text)
        title_lbl.setStyleSheet(f"color: {title_color}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        # Prevent squeezing -> Elide
        # QLabel doesn't auto-elide easily in Layouts without help. 
        # But in Grid with Stretch it should be okay.
        layout.addWidget(title_lbl, 0, 2)
        
        # 3. Project (Col 2, Row 1)
        project_name = track.get('project_name', 'Unknown Project')
        proj_lbl = QLabel(project_name)
        proj_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(proj_lbl, 1, 2)
        
        # 4. BPM/Key (Col 3) - Optional
        info_text = ""
        bpm = track.get('bpm_user') or track.get('bpm_detected')
        key = track.get('key_user') or track.get('key_detected')
        
        tags = []
        if bpm: tags.append(f"{int(bpm)}")
        if key: tags.append(str(key))
        
        if tags:
            info_lbl = QLabel(" • ".join(tags))
            info_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; background: transparent; border: none;")
            info_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(info_lbl, 0, 3, 2, 1) # Right side info
        
        # 5. Duration (Col 4)
        duration_sec = track.get('duration_s', 0)
        dur_str = format_duration(duration_sec) if duration_sec else "--:--"
        dur_lbl = QLabel(dur_str)
        dur_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-family: monospace; background: transparent; border: none;")
        dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(dur_lbl, 0, 4, 2, 1)
        
        # Click Handling
        def mousePressEvent(e):
             self.track_clicked.emit(track)
             
        widget.mousePressEvent = mousePressEvent
        
        return widget
        
    def _clear_layout(self, layout):
        """Clear all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _on_clear(self):
        """Clear the visual queue."""
        self._clear_layout(self.next_container)
        lbl = QLabel("Queue cleared")
        lbl.setStyleSheet("color: #64748b; padding: 12px; font-style: italic;")
        self.next_container.addWidget(lbl)


class MainWindow(QMainWindow):
    """Main application window with full features."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        
        # Set window icon
        from .utils import get_icon
        app_icon = get_icon("app_icon", None, 256)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        else:
            # Fallback to direct path
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.svg")
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
        
        # Setup Services
        self._setup_services()
    
    def _setup_services(self):
        """Setup background services (Watcher, Analyzer)."""
        self.folder_watcher = FolderWatcher(self)
        self.folder_watcher.change_detected.connect(self.rescan_library)
        self._update_watcher_roots()
        
        self.bg_analyzer = BackgroundBatchAnalyzer(self)
        self.bg_analyzer.track_completed.connect(self._on_bg_analysis_complete)
        
    def _update_watcher_roots(self):
        """Update paths in the folder watcher."""
        watch_enabled = get_setting('watch_folders', 'true') == 'true'
        if watch_enabled:
            scanner = LibraryScanner()
            roots = scanner.get_library_roots()
            self.folder_watcher.set_folders(roots)
        else:
            self.folder_watcher.set_folders([])

    def _on_bg_analysis_complete(self, track_id, result):
        """Called when background analysis finishes a track."""
        if self.current_track and self.current_track['id'] == track_id:
            self.current_track['bpm_detected'] = result.bpm
            self.current_track['key_detected'] = result.key
            self.current_track['duration'] = result.duration
            self.update_details_panel(self.current_track)
        
        # Only refresh list if on library or visible
        if self.stack.currentWidget() == self.library_view:
             # This is expensive for every track, but good for UX. 
             # Maybe just update the row if we can find it.
             self.update_track_list()
    
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
        self.shortcuts.register_shortcut('go_projects', lambda: self.set_page('projects'))
        self.shortcuts.register_shortcut('go_insights', lambda: self.set_page('insights'))
        
        # General
        self.shortcuts.register_shortcut('settings', lambda: self.set_page('settings'))
        self.shortcuts.register_shortcut('search', lambda: self.search_input.setFocus())
        self.shortcuts.register_shortcut('search_slash', lambda: self.search_input.setFocus())  # / key
        self.shortcuts.register_shortcut('toggle_queue', self.toggle_queue_panel)
        self.shortcuts.register_shortcut('toggle_details', self.toggle_details_panel)
        self.shortcuts.register_shortcut('command_palette', self.show_command_palette)
    
    def _play_from_start(self):
        """Play current track from the beginning."""
        if self.player.state != PlayerState.STOPPED:
            self.player.seek(0)
            if self.player.state != PlayerState.PLAYING:
                self.player.play()
    
    def toggle_queue_panel(self):
        """Toggle queue panel visibility."""
        self.queue_panel.setVisible(not self.queue_panel.isVisible())
    
    def toggle_details_panel(self):
        """Toggle details panel visibility (Ctrl+B)."""
        self._details_panel_visible = not self._details_panel_visible
        self.details_container.setVisible(self._details_panel_visible)
        # Update toggle button icon
        icon_name = "chevron_right" if self._details_panel_visible else "chevron_left"
        self.details_toggle_btn.setIcon(get_icon(icon_name, QColor("#64748b"), 16))
    
    def show_details_panel(self):
        """Show the details panel."""
        if not self._details_panel_visible:
            self._details_panel_visible = True
            self.details_container.setVisible(True)
            self.details_toggle_btn.setIcon(get_icon("chevron_right", QColor("#64748b"), 16))
    
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
    
    def show_command_palette(self):
        """Show command palette for quick keyboard navigation."""
        success, result_type, result_data = CommandPaletteDialog.show_palette(
            self.tracks_data, self
        )
        
        if not success:
            return
        
        if result_type == "track":
            # Play the selected track
            self.current_track = result_data
            self.play_track(result_data)
            self.update_details_panel(result_data)
        elif result_type == "command":
            # Execute command by ID
            self._execute_palette_command(result_data)
    
    def _execute_palette_command(self, command_id: str):
        """Execute a command palette command."""
        commands = {
            "nav:library": lambda: self.set_page("library"),
            "nav:favorites": lambda: self.set_page("favorites"),
            "nav:projects": lambda: self.set_page("projects"),
            "nav:insights": lambda: self.set_page("insights"),
            "nav:plugins": lambda: self.set_page("plugin_intelligence"),
            "nav:overview": lambda: self.set_page("insights"),
            "nav:settings": lambda: self.set_page("settings"),
            "action:analyze": self.analyze_track,
            "action:edit": self.edit_metadata,
            "action:favorite": self.toggle_favorite,
            "action:open_flp": self.open_flp,
            "action:open_folder": self.open_project_folder,
            "action:rescan": self.rescan_library,
        }
        
        if command_id in commands:
            commands[command_id]()
    
    def _connect_player_signals(self):
        """Connect player signals."""
        self.player.state_changed.connect(self.on_player_state_changed)
        self.player.track_changed.connect(self.on_track_changed)
        self.player.duration_changed.connect(self.on_duration_changed)
        self.player.playlist_changed.connect(self.on_playlist_changed)
    
    def setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        self._create_menu_bar()
        
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
        
        self.nav_playlists = self._create_nav_button("Playlists", "playlist")
        self.nav_playlists.clicked.connect(lambda: self.set_page("playlists"))
        sidebar_layout.addWidget(self.nav_playlists)
        
        self.nav_projects = self._create_nav_button("Projects", "folder_open")
        self.nav_projects.clicked.connect(lambda: self.set_page("projects"))
        sidebar_layout.addWidget(self.nav_projects)

        self.nav_insights = self._create_nav_button("Insights", "analyze")
        self.nav_insights.clicked.connect(lambda: self.set_page("insights"))
        sidebar_layout.addWidget(self.nav_insights)
        
        self.nav_plugin_intel = self._create_nav_button("Plugins", "synthesizer")
        self.nav_plugin_intel.clicked.connect(lambda: self.set_page("plugin_intelligence"))
        sidebar_layout.addWidget(self.nav_plugin_intel)
        
        self.nav_settings = self._create_nav_button("Settings", "settings")
        self.nav_settings.clicked.connect(lambda: self.set_page("settings"))
        sidebar_layout.addWidget(self.nav_settings)
        
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
        
        # Initialize Plugin Intelligence View
        self.plugin_intelligence_view = PluginIntelligenceView()
        self.plugin_intelligence_view.plugin_selected.connect(self._on_plugin_filter_requested)
        self.plugin_intelligence_view.system_scan_requested.connect(self.on_system_plugin_scan_requested)
        self.stack.addWidget(self.plugin_intelligence_view)
        
        # Initialize Analytics Panel (Legacy name, now part of stack)
        self.plugin_analytics_panel = self.plugin_intelligence_view.analytics_panel
        
        # 1. LIBRARY VIEW
        self.library_view = QWidget()
        library_layout = QVBoxLayout(self.library_view)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(0)
        
        # === HEADER BAR with gradient ===
        header_bar = QFrame()
        header_bar.setFixedHeight(70)
        header_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(17, 24, 32, 0.95),
                    stop:0.4 rgba(30, 41, 59, 0.85),
                    stop:0.6 rgba(30, 41, 59, 0.85),
                    stop:1 rgba(17, 24, 32, 0.95));
                border-bottom: 1px solid rgba(30, 41, 59, 0.5);
            }
        """)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 12, 20, 12)
        header_layout.setSpacing(10)
        
        # Search bar inside header - container matches page background
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks, projects...")
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self.on_search)
        header_layout.addWidget(self.search_input)
        
        library_layout.addWidget(header_bar)
        
        # === MAIN CONTENT AREA ===
        main_area = QFrame()
        main_area.setObjectName("mainArea")
        main_layout_inner = QVBoxLayout(main_area)
        main_layout_inner.setContentsMargins(20, 16, 20, 16)
        main_layout_inner.setSpacing(12)
        
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
            # Pill shape: Height around 28px, radius 14px
            btn.setFixedHeight(28)
            btn.setStyleSheet("""
                QPushButton#filterChip {
                    background: rgba(30, 41, 59, 0.5);
                    border: 1px solid #334155;
                    border-radius: 14px;
                    padding: 0px 16px;
                    color: #94a3b8;
                    font-size: 11px;
                }
                QPushButton#filterChip:hover {
                    border-color: #38bdf8;
                    background: rgba(30, 41, 59, 0.8);
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
            
        # Add Stage Chips for filtering
        add_chip("Ideas", "stage:IDEA")
        add_chip("WIPs", "stage:WIP")
        add_chip("Finished", "stage:FINISHED")
            
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
        # Expanded columns: Icon, Track, Project, Date, BPM, Key, Genre, STATUS, +View, +Playlist, +Tags, +Analyze, Edit
        self.track_list.setColumnCount(13)
        # Set text labels for main columns, empty for icon columns
        self.track_list.setHorizontalHeaderLabels([
            "", "TRACK", "PROJECT", "DATE", "BPM", "KEY", "GENRE", "STATUS",
            "", "", "", "", "" 
        ])
        
        # Set icons for action columns
        # 7: Status
        self.track_list.setHorizontalHeaderItem(7, QTableWidgetItem("STATUS"))
        self.track_list.horizontalHeaderItem(7).setTextAlignment(Qt.AlignmentFlag.AlignLeft)

        # 8: View (Eye)
        self.track_list.setHorizontalHeaderItem(8, QTableWidgetItem(get_icon("eye", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(8).setToolTip("View Project")
        
        # 9: Playlist (Folder/Playlist)
        self.track_list.setHorizontalHeaderItem(9, QTableWidgetItem(get_icon("playlist", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(9).setToolTip("Add to Playlist")
        
        # 10: Tags (Tag)
        self.track_list.setHorizontalHeaderItem(10, QTableWidgetItem(get_icon("tag", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(10).setToolTip("Edit Tags")
        
        # 11: Analyze (Audio/Waveform)
        self.track_list.setHorizontalHeaderItem(11, QTableWidgetItem(get_icon("analyze", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(11).setToolTip("Analyze Audio")
        
        # 12: Edit (Pen)
        self.track_list.setHorizontalHeaderItem(12, QTableWidgetItem(get_icon("edit", QColor("#94a3b8"), 16), ""))
        self.track_list.horizontalHeaderItem(12).setToolTip("Edit Metadata")
        self.track_list.verticalHeader().setVisible(False)
        self.track_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Track
        self.track_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Project
        self.track_list.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Status
        self.track_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        # Action columns fixed width
        for col in range(8, 13):
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
        self.project_panel.back_requested.connect(lambda: self.stack.setCurrentWidget(self.library_view))
        self.project_panel.track_play_requested.connect(self._play_external_file)
        self.project_panel.sample_clicked.connect(self._on_sample_discovery_requested)
        self.stack.addWidget(self.project_panel)
        
        # 3. PROJECTS VIEW (New)
        self.projects_view = ProjectsView()
        self.projects_view.project_opened.connect(self.open_project_folder_path)
        self.projects_view.project_selected.connect(self.update_details_panel)
        self.projects_view.play_requested.connect(self._on_projects_view_play_requested)
        self.projects_view.view_requested.connect(self.open_project_drill_down)
        self.stack.addWidget(self.projects_view)
        
        # 4. INSIGHTS VIEW
        self.insights_view = SampleOverviewView()
        self.insights_view.sample_selected.connect(self._navigate_to_sample)
        self.insights_view.sample_play_requested.connect(self._play_external_file)
        self.stack.addWidget(self.insights_view)
        
        # 5. SAMPLE DETAIL VIEW
        self.sample_detail_view = SampleDetailView()
        self.sample_detail_view.back_requested.connect(self._back_to_insights)
        self.sample_detail_view.sample_play_requested.connect(self._play_external_file)
        self.sample_detail_view.render_play_requested.connect(self._play_external_file)
        self.stack.addWidget(self.sample_detail_view)
        
        content.addWidget(self.stack, 1)  # Stretch
        
        # === DETAILS PANEL (Right side) - Toggleable ===
        # Beautiful gradient background to distinguish from main content
        self.details_container = QFrame()
        self.details_container.setObjectName("detailsContainer")
        self.details_container.setFixedWidth(340)
        self.details_container.setStyleSheet("""
            QFrame#detailsContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(30, 41, 59, 0.8),
                    stop:0.5 rgba(51, 65, 85, 0.9),
                    stop:1 rgba(30, 41, 59, 0.8));
                border-left: 1px solid rgba(167, 139, 250, 0.3);
            }
        """)
        
        details_main_layout = QVBoxLayout(self.details_container)
        details_main_layout.setContentsMargins(0, 0, 0, 0)
        details_main_layout.setSpacing(0)
        
        # Header with toggle button - unified smooth background matching sidebar
        details_header = QFrame()
        details_header.setFixedHeight(52)
        details_header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(30, 41, 59, 0.8),
                    stop:0.5 rgba(51, 65, 85, 0.9),
                    stop:1 rgba(30, 41, 59, 0.8));
                border-bottom: 1px solid rgba(30, 41, 59, 0.6);
            }
            QFrame > QLabel {
                background: transparent;
                border: none;
            }
        """)
        header_layout = QHBoxLayout(details_header)
        header_layout.setContentsMargins(16, 0, 12, 0)
        header_layout.setSpacing(0)
        
        details_title = QLabel("Details")
        details_title.setStyleSheet("""
            QLabel {
                background: transparent !important;
                color: #94a3b8;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1px;
                padding: 0px;
                margin: 0px;
                border: none;
            }
        """)
        header_layout.addWidget(details_title)
        header_layout.addStretch()
        
        # Toggle button
        self.details_toggle_btn = QPushButton()
        self.details_toggle_btn.setIcon(get_icon("chevron_right", QColor("#64748b"), 16))
        self.details_toggle_btn.setFixedSize(28, 28)
        self.details_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.details_toggle_btn.setToolTip("Hide panel (Ctrl+B)")
        self.details_toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(148, 163, 184, 0.1);
            }
        """)
        self.details_toggle_btn.clicked.connect(self.toggle_details_panel)
        header_layout.addWidget(self.details_toggle_btn)
        
        details_main_layout.addWidget(details_header)
        
        # Stack for different panel types
        self.details_stack = QStackedWidget()
        self.details_stack.setStyleSheet("""
            QStackedWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(30, 41, 59, 0.8),
                    stop:0.5 rgba(51, 65, 85, 0.9),
                    stop:1 rgba(30, 41, 59, 0.8));
            }
            QStackedWidget > QWidget {
                background: transparent;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QGroupBox {
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(30, 41, 59, 0.6);
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 8px;
            }
            QGroupBox::title {
                color: #64748b;
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
        
        # 1. Track Panel
        self.track_panel = TrackDetailsPanel()
        self.track_panel.edit_clicked.connect(self.edit_metadata)
        self.track_panel.play_clicked.connect(self.play_track)
        self.track_panel.favorite_clicked.connect(self.toggle_favorite)
        self.track_panel.add_playlist_clicked.connect(self.show_add_to_playlist)
        self.track_panel.open_flp_clicked.connect(self.open_flp)
        self.track_panel.open_folder_clicked.connect(self.open_project_folder_path)
        self.details_stack.addWidget(self.track_panel)
        
        # 2. Project Panel
        self.project_details_panel = ProjectDetailsPanel()
        self.project_details_panel.open_folder_clicked.connect(self.open_project_folder_path)
        self.project_details_panel.open_flp_clicked.connect(self.open_flp)
        self.details_stack.addWidget(self.project_details_panel)
        
        # 3. Sample Discovery Panel
        self.sample_projects_panel = SampleProjectsPanel()
        self.sample_projects_panel.project_clicked.connect(self.open_project_drill_down)
        self.details_stack.addWidget(self.sample_projects_panel)
        
        # 4. Plugin Details Panel
        self.plugin_details_panel = PluginDetailsPanel()
        self.plugin_details_panel.project_clicked.connect(self.open_project_drill_down)
        self.plugin_details_panel.play_requested.connect(self._on_plugin_project_play_requested)
        self.details_stack.addWidget(self.plugin_details_panel)
        
        details_main_layout.addWidget(self.details_stack, 1)
        
        content.addWidget(self.details_container)
        
        # Hide details panel by default
        self.details_container.hide()
        self._details_panel_visible = False
        
        main_layout.addLayout(content, 1)

        # Import locally to avoid circulars if any (though usually top level is fine)
        from .ui.playlists_view import PlaylistsView
        self.playlists_view = PlaylistsView()
        self.playlists_view.play_requested.connect(self.play_playlist)
        self.stack.addWidget(self.playlists_view) # Index 3
        
        # === QUEUE PANEL ===
        self.queue_panel = QueuePanel()
        self.queue_panel.track_clicked.connect(self.play_track)
        main_layout.addWidget(self.queue_panel)
        
        # === PLAYER BAR ===
        
        # 6. SETTINGS VIEW
        self.settings_view = SettingsView()
        self.settings_view.settings_changed.connect(self.on_settings_changed)
        self.stack.addWidget(self.settings_view)
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
        
        center_layout.addLayout(controls)
        
        # Row 2: Waveform visualization with Time
        waveform_row = QHBoxLayout()
        waveform_row.setSpacing(12)
        
        self.time_current = QLabel("0:00")
        self.time_current.setObjectName("timeLabel")
        waveform_row.addWidget(self.time_current)
        
        self.mini_waveform = MiniWaveformWidget()
        self.mini_waveform.setFixedHeight(30)
        self.mini_waveform.setFixedWidth(450)
        self.mini_waveform.seek_requested.connect(self._on_waveform_seek)
        waveform_row.addWidget(self.mini_waveform)
        
        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("timeLabel")
        waveform_row.addWidget(self.time_total)
        
        center_layout.addLayout(waveform_row)
        
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
        # Update sidebar button states
        self.nav_home.setChecked(page in ["library", "favorites"])
        self.nav_playlists.setChecked(page == "playlists")
        self.nav_projects.setChecked(page == "projects")
        self.nav_insights.setChecked(page == "insights")
        self.nav_plugin_intel.setChecked(page in ["analytics", "plugin_intelligence"])
        
        # Reset states for clean navigation
        if hasattr(self, 'projects_view'):
            self.projects_view.reset_state()
            
        if page == "library":
            # Only load if empty to prevent freeze on switch
            if self.track_list.rowCount() == 0:
                self.load_tracks()
            self.stack.setCurrentWidget(self.library_view)
            
        elif page == "projects":
            if self.projects_view.model.rowCount() == 0:
                self.projects_view.refresh_data()
            self.stack.setCurrentWidget(self.projects_view)
            
        elif page == "favorites":
            self.load_favorites()
            self.stack.setCurrentWidget(self.library_view)
            
        elif page == "settings":
            # Switch to settings page
            self.settings_view.refresh()
            self.stack.setCurrentWidget(self.settings_view)
            
        elif page == "playlists":
            self.playlists_view.refresh()
            self.stack.setCurrentWidget(self.playlists_view)
            
        elif page == "overview":
            # Overview redirection? Usually insights
            self.insights_view.refresh_data()
            self.stack.setCurrentWidget(self.insights_view)
            
        elif page in ["analytics", "plugin_intelligence"]:
            # Show the unified plugin intelligence view
            self.plugin_intelligence_view.refresh()
            self.stack.setCurrentWidget(self.plugin_intelligence_view)
            
        elif page == "insights":
            self.insights_view.refresh_data()
            self.stack.setCurrentWidget(self.insights_view)


    def on_system_plugin_scan_requested(self):
        """Trigger a system-wide plugin scan."""
        from .utils.plugin_scanner import scan_system_plugins
        
        self.scan_status.setText("Scanning system for plugins...")
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)
        
        class PluginScanThread(QThread):
            finished = Signal(int)
            def run(self):
                try:
                    count = scan_system_plugins()
                    self.finished.emit(count)
                except Exception as e:
                    logger.error(f"System plugin scan failed: {e}")
                    self.finished.emit(0)
                
        self._plugin_scan_thread = PluginScanThread(self)
        self._plugin_scan_thread.finished.connect(self._on_system_plugin_scan_finished)
        self._plugin_scan_thread.start()

    def _on_system_plugin_scan_finished(self, count):
        self.scan_progress.setVisible(False)
        self.scan_status.setText(f"System scan complete: {count} VSTs found")
        if hasattr(self, 'plugin_intelligence_view'):
            self.plugin_intelligence_view.refresh()
        self._plugin_scan_thread = None

    def load_recently_added(self):
        """Load tracks sorted by date added (newest first)."""
        from .scanner import get_recently_added_tracks
        self.tracks_data = get_recently_added_tracks(limit=100)
        self.update_track_list()
        
    def load_missing_metadata(self):
        """Load tracks with missing BPM or Key."""
        from .scanner import get_missing_metadata_tracks
        self.tracks_data = get_missing_metadata_tracks(limit=500)
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
            self.stack.setCurrentWidget(self.library_view)

    
    def load_tracks(self):
        """Load all tracks from database."""
        self.tracks_data = get_all_tracks(limit=200) # Reduced from 5000 for performance
        self.update_track_list()
    
    def load_favorites(self):
        """Load favorite tracks."""
        self.tracks_data = get_favorite_tracks()
        self.update_track_list()
    
    def on_settings_changed(self):
        """Handle settings changes."""
        self.update_track_list()
        # Update player if needed
        volume = int(get_setting('volume', '80'))
        self.player.volume = volume / 100.0
        self.volume_slider.setValue(volume)
        self._update_watcher_roots()
        
        # P13: Trigger rescan when folders might have changed
        self.rescan_library()
        
    def update_track_list(self):
        """Update the track list widget."""
        self.track_list.setUpdatesEnabled(False)
        self.track_list.setSortingEnabled(False)
        
        try:
            self.track_list.setRowCount(0)
            self.track_list.setRowCount(len(self.tracks_data))
            
            show_camelot = get_setting('camelot_notation', 'true') == 'true'
            
            for row, track in enumerate(self.tracks_data):
                title = track.get('title', 'Unknown')
                project = track.get('project_name', '')
                # Use mtime for date added/created
                date_added = format_smart_date(track.get('mtime', 0))
                bpm = track.get('bpm_user') or track.get('bpm_detected')
                key = track.get('key_user') or track.get('key_detected')
                
                bpm_str = f"{bpm:.0f}" if bpm else ""
                key_str = format_key(key, show_camelot=show_camelot) if key else ""
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
                
                # 7. Status (Badges)
                status_widget = StatusBadge()
                badges = []
                
                # State Badge (First and prominent)
                state = track.get('state')
                if state:
                    # Color mapping for states
                    state_colors = {
                        'FINISHED': '#22c55e', # Green
                        'MIXED': '#3b82f6',    # Blue
                        'READY_TO_MIX': '#6366f1', # Indigo
                        'DRAFT': '#a855f7',    # Purple
                        'WIP': '#f59e0b',      # Amber
                        'IDEA': '#eab308',     # Yellow
                        'SAMPLE': '#94a3b8',   # Slate
                        'DEAD': '#475569',     # Dark Slate
                        'BROKEN': '#ef4444',   # Red
                        'MISSING_RENDER': '#ef4444',
                        'ORPHAN_RENDER': '#f97316', # Orange
                    }
                    color = state_colors.get(state, '#64748b')
                    reason = track.get('state_reason', 'Unknown reason')
                    badges.append({'text': state, 'color': color, 'tooltip': f"State: {state}\nWhy: {reason}"})
                
                if track.get('flp_path') and os.path.exists(track.get('flp_path')):
                    badges.append({'text': 'FLP', 'color': '#22c55e', 'tooltip': 'Has FL Studio Project'})
                if track.get('stems_dir') and os.path.isdir(track.get('stems_dir')):
                    count = len([f for f in os.listdir(track.get('stems_dir')) 
                                if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS])
                    if count > 0:
                        badges.append({'text': 'STEMS', 'color': '#a855f7', 'tooltip': f'{count} Stems available'})
                if track.get('backup_dir') and os.path.isdir(track.get('backup_dir')):
                    badges.append({'text': 'BACKUP', 'color': '#64748b', 'tooltip': 'Has Backups'})
                
                status_widget.set_badges(badges)
                self.track_list.setCellWidget(row, 7, status_widget)
                
                # 8. View
                self._create_action_btn(row, 8, "eye", "#facc15", lambda r: self.show_project_details(r))
                
                # 9. Playlist
                self._create_action_btn(row, 9, "playlist", "#38bdf8", lambda r: self.show_add_to_playlist_row(r))
                
                # 10. Tags
                self._create_action_btn(row, 10, "tag", "#22c55e", lambda r: self.show_tag_editor_row(r))
                
                # 11. Analyze
                self._create_action_btn(row, 11, "analyze", "#a855f7", lambda r: self.analyze_track_row(r))
                
                # 12. Edit
                self._create_action_btn(row, 12, "edit", "#64748b", lambda r: self.edit_metadata_row(r))
        
        finally:
            self.track_list.setSortingEnabled(True)
            self.track_list.setUpdatesEnabled(True)
        
        self.track_count_label.setText(f"{len(self.tracks_data)} tracks")
        
    def _create_action_btn(self, row, col, icon_name, color, callback):
        """Helper to create an action button in the table."""
        item = QTableWidgetItem()
        # Fallback for missing icons
        if icon_name == "eye": icon_name = "search" 
        
        item.setIcon(get_icon(icon_name, QColor(color), 14))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.track_list.setItem(row, col, item)
    
    def on_track_double_clicked_table(self, row, col):
        """Handle table double click."""
        # If double clicking an action column, do nothing (single click handles it)
        if col >= 7: return
        
        # Get track ID
        item = self.track_list.item(row, 0)
        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.play_track({'id': track_id})

    def show_project_details(self, row):
        item = self.track_list.item(row, 0)
        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.show_project_drilldown(track_id)
        
    def show_add_to_playlist_row(self, row):
        item = self.track_list.item(row, 0)
        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_track = get_track_by_id(track_id)
        self.show_add_to_playlist()

    def show_add_to_playlist(self, track=None):
        """Show menu to add current track(s) to playlist."""
        if track:
            self.current_track = track
            
        if not self.current_track:
            return
            
        from .ui.playlist_dialogs import AddToPlaylistMenu
        from PySide6.QtGui import QCursor
        
        # Detect if multiple selection? For now just current track.
        # Ideally we check self.track_list.selectedItems()
        
        menu = AddToPlaylistMenu(self)
        menu.set_tracks([self.current_track['id']])
        menu.exec(QCursor.pos())

    def show_tag_editor_row(self, row):
        item = self.track_list.item(row, 0)
        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_track = get_track_by_id(track_id)
        self.show_tag_editor()

    def analyze_track_row(self, row):
        item = self.track_list.item(row, 0)
        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_track = get_track_by_id(track_id)
        self.analyze_track()

    def edit_metadata_row(self, row):
        item = self.track_list.item(row, 0)
        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_track = get_track_by_id(track_id)
        self.edit_metadata()
        
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
        if col == 8:  # View Project
            self.project_panel.set_track(track['id'])
            # self.project_panel.set_project(...) redundant if set_track works, 
            # and project view might not need explicit set_project if track implies it.
            # But we added set_project method now, so we CAN use it? 
            # Actually set_track updates UI perfectly for a track context.
            self.stack.setCurrentWidget(self.project_panel)
            return
        elif col == 9:  # Playlist
            self.show_add_to_playlist()
            return
        elif col == 10:  # Tags
            self.show_tag_editor()
            return
        elif col == 11:  # Analyze
            self.analyze_track()
            return
        elif col == 12:  # Edit
            self.edit_metadata()
            return
        
        # Regular click - update details panel
        self.update_details_panel(track)
        
        # P12 Fix: Respect auto_play setting on single click
        if get_setting('auto_play', 'true') == 'true':
            self.play_track(track)
            
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
        stages = []
        
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
                elif data.startswith("stage:"):
                    stages.append(data.split(":", 1)[1])
        
        # 1. Base Search
        results = search_tracks(
            term=text,
            key=None,
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
            
            if stages:
                # Track state is in 'state' field (e.g. 'IDEA', 'WIP')
                # Check if track state matches ANY selected stage
                track_state = t.get('state', '')
                if not track_state:
                    continue # Filter out if empty state when filtering
                if track_state not in stages:
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
    
    def update_details_panel(self, item_data):
        """Update the details panel with track OR project info."""
        if not item_data:
            self.track_panel.clear()
            return
        
        # Show the details panel when content is available
        self.show_details_panel()
        
        # Detect type: Project or Track
        # Tracks from search_tracks HAVE 'project_id' (joined).
        # Projects from get_all_projects DO NOT have 'project_id' (they have 'id').
        # Also tracks have extensions, projects don't.
        
        is_project = 'project_id' not in item_data
        
        # P7 Fix: If we are on Plugin Intelligence page, don't auto-switch unless 
        # specifically requested by the click (handled in signals).
        # Actually, if item_data is a PROJECT but we are on PLUGIN page, 
        # it usually means we clicked "Explore" in the Plugin detail panel.
        # In that case, we SHOULD show project panels.
        # But if we were PLAYING a track and update_details_panel 
        # was called automatically, we might want to stay.
        
        if is_project:
            self.current_track = None 
            self.project_details_panel.set_project(item_data)
            self.details_stack.setCurrentWidget(self.project_details_panel)
            self.current_project_path = item_data.get('path')
        else:
            # It's a Track
            track = item_data
            if 'id' in track and len(track.keys()) < 5:
                 full = get_track_by_id(track['id'])
                 if full: track = full
            
            self.current_track = track
            self.track_panel.set_track(track)
            
            # If on Plugin page OR Projects page and we just started playing a project render, 
            # we DON'T want the side panel to switch to TrackDetails.
            # We want to keep seeing why we are here (the plugin or projects list).
            current_page = self.stack.currentWidget()
            if current_page not in [self.plugin_intelligence_view, self.projects_view]:
                self.details_stack.setCurrentWidget(self.track_panel)
        
        # Update buttons
        # self.update_detail_buttons(track) # This call is now commented out or removed if the method is gone
    
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
        # Ensure we have a dictionary as sqlite3.Row doesn't support .get()
        if not isinstance(track, dict):
            try:
                track = dict(track)
            except:
                pass
        
        path = track.get('path') if hasattr(track, 'get') else track.get('path') if isinstance(track, dict) else getattr(track, 'path', None)
        project_path = track.get('project_path')
        
        if not validate_path(path, "Track", self, project_path=project_path):
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
    
    def open_flp(self, track_or_path=None):
        """Open the FLP file in FL Studio."""
        target = track_or_path or self.current_track
        
        path = None
        if isinstance(target, str):
            path = target
        elif isinstance(target, dict):
            path = target.get('flp_path')
            
        if validate_path(path, "FLP", self):
            fl_path = get_setting('fl_studio_path', '')
            open_fl_studio(path, fl_path if fl_path else None)
    
    def open_project_folder(self):
        """Open the project folder."""
        path = self.current_track.get('project_path') if self.current_track else None
        if validate_path(path, "Project folder", self):
            open_folder(path)

    def play_project_render(self, project: dict):
        """Find the best render for a project and play it."""
        if not project: return
        project_id = project.get('id')
        if not project_id: return
        
        # 1. Find the best track (prefer longest duration > 0 if multiple)
        rows = query("""
            SELECT * FROM tracks 
            WHERE project_id = ? AND ext != '.flp'
            ORDER BY duration DESC LIMIT 1
        """, (project_id,))
        
        if not rows:
            logger.warning(f"No renders found for project {project_id}")
            QMessageBox.information(self, "No Render", f"Project '{project.get('name')}' has no audio renders yet.\n\nExport an audio file from FL Studio to enable previews.")
            return
            
        track_row = dict(rows[0])
        track_id = track_row.get('id')
        
        # 2. Play it
        self.play_track(track_row)
        now = int(time.time())
        execute("UPDATE projects SET last_played_ts = ?, updated_at = ? WHERE id = ?", (now, now, project_id))
        if track_id:
            execute("UPDATE tracks SET play_count = play_count + 1, last_played = ?, updated_at = ? WHERE id = ?", (now, now, track_id))

    def _on_plugin_project_play_requested(self, project: dict):
        """Play a project render and set up a queue of all projects in the plugin list."""
        if not project or not hasattr(self.plugin_details_panel, 'current_projects_list'):
            self.play_project_render(project)
            return
            
        projects_list = self.plugin_details_panel.current_projects_list
        if not projects_list:
            self.play_project_render(project)
            return
            
        # Build queue of best renders for each project
        queue = []
        target_track = None
        
        for p in projects_list:
            rows = query("""
                SELECT * FROM tracks 
                WHERE project_id = ? AND ext != '.flp'
                ORDER BY duration DESC LIMIT 1
            """, (p['id'],))
            
            if rows:
                track = dict(rows[0])
                queue.append(track)
                if p['id'] == project['id']:
                    target_track = track
                    
        if queue:
            self.player.set_playlist(queue)
            if target_track:
                # Find index
                for i, t in enumerate(queue):
                    if t['id'] == target_track['id']:
                        self.player.play_at_index(i)
                        break
            else:
                self.player.play_at_index(0)
        else:
            # Fallback to single play (which shows No Render error)
            self.play_project_render(project)

    def _on_projects_view_play_requested(self, project: dict):
        """Play a project render - use primary render from renders table if available."""
        if not project:
            return
        
        project_id = project.get('id')
        if not project_id:
            return
        
        # Check if renders table exists and has renders
        try:
            test_row = query("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
            has_renders_table = len(test_row) > 0
        except:
            has_renders_table = False
        
        if has_renders_table:
            # Try to get primary render from renders table
            from .scanner.library_scanner import get_primary_render
            primary_render = get_primary_render(project_id)
            
            if primary_render and primary_render.get('path'):
                # Play the primary render
                render_path = primary_render['path']
                if os.path.exists(render_path):
                    # Use _play_external_file which accepts a path string
                    self._play_external_file(render_path)
                    
                    # Update last played timestamp
                    now = int(time.time())
                    execute("UPDATE projects SET last_played_ts = ?, updated_at = ? WHERE id = ?", 
                           (now, now, project_id))
                    self.projects_view.refresh_data()
                    return
        
        # Fallback to legacy tracks table
        self.play_project_render(project)

    def open_project_drill_down(self, project):
        """Show renders panel for a project."""
        if not project: return
        
        project_id = project.get('id')
        project_name = project.get('name', 'Unknown Project')
        
        if project_id:
            # Check if renders table exists
            try:
                test_row = query("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
                has_renders_table = len(test_row) > 0
            except:
                has_renders_table = False
            
            if has_renders_table:
                # Create or reuse renders panel
                if not hasattr(self, '_renders_panel') or self._renders_panel is None:
                    self._renders_panel = RendersPanel(project_id, project_name, self)
                    self._renders_panel.primary_changed.connect(self._on_primary_render_changed)
                
                # Update renders panel with current project
                self._renders_panel.project_id = project_id
                self._renders_panel.project_name = project_name
                self._renders_panel._load_renders()
                
                # Show as dialog
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Renders: {project_name}")
                dialog.setModal(False)
                dialog.setStyleSheet("""
                    QDialog {
                        background-color: #0f172a;
                    }
                """)
                dialog_layout = QVBoxLayout(dialog)
                dialog_layout.setContentsMargins(0, 0, 0, 0)
                dialog_layout.addWidget(self._renders_panel)
                dialog.resize(900, 600)
                dialog.show()
                # Store reference so it doesn't get garbage collected
                self._renders_dialog = dialog
            else:
                # Fallback to project drill-down if renders table doesn't exist
                try:
                    self.project_panel.set_project(project_id)
                    self.stack.setCurrentWidget(self.project_panel)
                except AttributeError:
                    rows = query("SELECT id FROM tracks WHERE project_id = ? LIMIT 1", (project_id,))
                    if rows:
                        self.project_panel.set_track(rows[0]['id'])
                        self.stack.setCurrentWidget(self.project_panel)
    
    def _on_primary_render_changed(self, project_id):
        """Handle primary render change - refresh projects view."""
        if hasattr(self, 'projects_view'):
            self.projects_view.refresh_data()
                
    def _on_sample_discovery_requested(self, sample_name):
        """Handle sample discovery from drill-down."""
        # Show projects using this sample in the right sidebar
        self.sample_projects_panel.set_sample(sample_name)
        self.details_stack.setCurrentWidget(self.sample_projects_panel)
        self.show_details_panel()

    def _on_sample_filter_requested(self, sample_name):
        """Handle sample click from overview dashboard."""
        self.set_page("projects")
        self.projects_view.active_sample_filter = sample_name
        # Fetch all project IDs that use this sample
        rows = query("SELECT project_id FROM project_samples WHERE sample_name = ?", (sample_name,))
        self.projects_view.active_sample_project_ids = {row['project_id'] for row in rows}
        self.projects_view._apply_filters()

    def open_project_folder_path(self, path):
        """Open project folder by path."""
        open_folder(path)
    
    def _on_plugin_filter_requested(self, plugin_name):
        """Handle plugin click from analytics dashboard."""
        # stay on current page (Plugins) but update panel
        self.plugin_details_panel.set_plugin(plugin_name)
        self.details_stack.setCurrentWidget(self.plugin_details_panel)
        self.show_details_panel()
        # Probably not. Let's add a quick attribute to the view instance.
        
        if hasattr(self.projects_view, 'active_plugin_filter'):
             self.projects_view.active_plugin_filter = plugin_name
             self.projects_view._apply_filters()
        else:
             # Fallback: Just search for it
             self.projects_view.search_input.setText(f"plugin:{plugin_name}")
    
    def toggle_favorite(self, track: dict = None):
        """Toggle favorite status."""
        target_track = track or self.current_track
        if target_track:
            new_state = toggle_favorite(target_track['id'])
            target_track['favorite'] = new_state
            
            # Update UI
            self.update_details_panel(target_track)
            
            # Update list icon if visible
            # (Requires finding the row, which is expensive, so we just refresh search if needed or rely on next refresh)
            self.on_search(self.search_input.text())
    
    
    def on_playlist_changed(self):
        """Handle playlist changes."""
        self.queue_panel.set_queue(self.player.playlist, self.player.playlist_index)
    # --- Player Signal Handlers ---
    
    def on_player_state_changed(self, state):
        """Handle player state changes."""
        # Update play/pause button
        if state == PlayerState.PLAYING:
            self.btn_play_pause.setIcon(get_icon("pause", QColor("#0c1117"), 28))
            if hasattr(self, 'track_panel'):
                self.track_panel.btn_play.setText(" Pause")
                self.track_panel.btn_play.setIcon(get_icon("pause", QColor("#f1f5f9"), 16))
        else:
            self.btn_play_pause.setIcon(get_icon("play", QColor("#0c1117"), 28))
            if hasattr(self, 'track_panel'):
                self.track_panel.btn_play.setText(" Play")
                self.track_panel.btn_play.setIcon(get_icon("play", QColor("#f1f5f9"), 16))
    
    def on_track_changed(self, track):
        """Handle track change."""
        # Update queue panel first
        try:
            self.queue_panel.set_current_track(track)
            self.queue_panel.set_queue(self.player.playlist, self.player.playlist_index)
        except Exception as e:
            logger.error(f"Error updating queue panel: {e}")

        if not track:
            self.player_title.setText("No track playing")
            self.player_project.setText("")
            self.time_current.setText("0:00")
            self.time_total.setText("0:00")
            # self.progress_slider.setValue(0) # Removed if progress_slider doesn't exist
            self.mini_waveform.clear()
            if hasattr(self, 'player_bpm_label'): self.player_bpm_label.hide()
            if hasattr(self, 'player_key_label'): self.player_key_label.hide()
            self.highlight_playing_row(None)
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
        try:
            self.mini_waveform.clear()
            if track.get('path'):
                self.mini_waveform.load_waveform(track['path'])
        except Exception as e:
            logger.error(f"Error loading waveform: {e}")
            
        # Highlight the playing row in the table
        try:
            self.highlight_playing_row(track.get('id'))
        except Exception as e:
            logger.error(f"Error highlighting row: {e}")
    
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
                # Update waveform
                self.mini_waveform.set_position(pos)
    


    
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
        """Play a file internally using the audio engine."""
        # #region agent log
        import json
        debug_log = {"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app.py:2148", "message": "_play_external_file called", "data": {"original_path": path}, "timestamp": int(time.time() * 1000)}
        try:
            with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(debug_log) + "\n")
        except: pass
        # #endregion
        
        # Try to get project_path from current project panel context
        project_path = None
        if hasattr(self, 'project_panel') and hasattr(self.project_panel, 'current_project'):
            current_project = self.project_panel.current_project
            if current_project:
                # #region agent log
                debug_log = {"sessionId": "debug-session", "runId": "run2", "hypothesisId": "F", "location": "app.py:2163", "message": "current_project keys", "data": {"keys": list(current_project.keys()) if isinstance(current_project, dict) else "not_dict", "has_project_path": 'project_path' in current_project if isinstance(current_project, dict) else False, "has_samples_dir": 'samples_dir' in current_project if isinstance(current_project, dict) else False}, "timestamp": int(time.time() * 1000)}
                try:
                    with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps(debug_log) + "\n")
                except: pass
                # #endregion
                
                # Try multiple possible keys for project path
                project_path = (current_project.get('project_path') or 
                               current_project.get('path') or
                               None)
                # If still None, try to derive from samples_dir or other paths
                if not project_path:
                    samples_dir = current_project.get('samples_dir')
                    if samples_dir and os.path.isdir(samples_dir):
                        # samples_dir is typically project_path/Samples, so go up one level
                        project_path = os.path.dirname(samples_dir)
                
                # Also try to derive from the incoming path if it's in a Samples folder
                if not project_path and path and os.path.sep in path:
                    # Check if path contains "Samples" - if so, extract project path
                    if 'Samples' in path:
                        parts = path.split(os.path.sep)
                        try:
                            samples_idx = parts.index('Samples')
                            project_path = os.path.sep.join(parts[:samples_idx])
                            if not os.path.isdir(project_path):
                                project_path = None
                        except ValueError:
                            pass
        
        # Fallback: Extract project_path from path even if current_project is not available
        if not project_path and path and ('Samples' in path or 'Audio' in path):
            # Use os.path.normpath to handle Windows paths correctly
            norm_path = os.path.normpath(path)
            parts = norm_path.split(os.path.sep)
            
            # #region agent log
            debug_log = {"sessionId": "debug-session", "runId": "run2", "hypothesisId": "G", "location": "app.py:2200", "message": "extracting project_path from path", "data": {"path": path, "norm_path": norm_path, "parts": parts, "has_samples": 'Samples' in parts, "has_audio": 'Audio' in parts}, "timestamp": int(time.time() * 1000)}
            try:
                with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps(debug_log) + "\n")
            except: pass
            # #endregion
            
            try:
                # Look for Samples or Audio folder
                folder_idx = None
                if 'Samples' in parts:
                    folder_idx = parts.index('Samples')
                elif 'Audio' in parts:
                    folder_idx = parts.index('Audio')
                
                if folder_idx is not None and folder_idx > 0:
                    # Join parts up to (but not including) Samples/Audio folder
                    # Use os.path.join which handles Windows drive letters correctly
                    project_path = os.path.join(*parts[:folder_idx])
                    
                    # #region agent log
                    debug_log = {"sessionId": "debug-session", "runId": "run2", "hypothesisId": "H", "location": "app.py:2215", "message": "project_path extracted", "data": {"folder_idx": folder_idx, "project_path": project_path, "exists": os.path.isdir(project_path) if project_path else False}, "timestamp": int(time.time() * 1000)}
                    try:
                        with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                            f.write(json.dumps(debug_log) + "\n")
                    except: pass
                    # #endregion
                    
                    if not os.path.isdir(project_path):
                        project_path = None
            except (ValueError, IndexError) as e:
                # #region agent log
                debug_log = {"sessionId": "debug-session", "runId": "run2", "hypothesisId": "I", "location": "app.py:2225", "message": "extraction failed", "data": {"error": str(e)}, "timestamp": int(time.time() * 1000)}
                try:
                    with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps(debug_log) + "\n")
                except: pass
                # #endregion
                pass
        
        # #region agent log
        debug_log = {"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "app.py:2155", "message": "project_path retrieved", "data": {"project_path": project_path, "has_project_panel": hasattr(self, 'project_panel'), "has_current_project": hasattr(self.project_panel, 'current_project') if hasattr(self, 'project_panel') else False}, "timestamp": int(time.time() * 1000)}
        try:
            with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(debug_log) + "\n")
        except: pass
        # #endregion
        
        # Use show_error=False to suppress UI messages for missing files (we handle silently)
        # Pass project_path so resolve_fl_path can check project_path/Samples/filename
        validation_result = validate_path(path, "External file", self, show_error=False, project_path=project_path)
        
        # #region agent log
        debug_log = {"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app.py:2160", "message": "validate_path result", "data": {"validation_result": validation_result, "path": path, "project_path": project_path}, "timestamp": int(time.time() * 1000)}
        try:
            with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(debug_log) + "\n")
        except: pass
        # #endregion
        
        if not validation_result:
            return
        
        # Resolve the path (handles FL Studio variables and project-local lookups)
        # This ensures we use the resolved path for playback
        resolved_path = resolve_fl_path(path, project_path)
        
        # #region agent log
        debug_log = {"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "app.py:2165", "message": "path resolved", "data": {"original_path": path, "resolved_path": resolved_path, "project_path": project_path, "resolved_exists": os.path.exists(resolved_path) if resolved_path else False}, "timestamp": int(time.time() * 1000)}
        try:
            with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(debug_log) + "\n")
        except: pass
        # #endregion

        # Create ad-hoc track for preview using the resolved path
        track = {
            'id': f"preview_{hash(resolved_path)}",
            'title': os.path.basename(resolved_path),
            'path': resolved_path,
            'duration_s': 0,
            'project_name': 'Sample Preview',
            'artist': 'System'
        }
        
        # #region agent log
        debug_log = {"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "app.py:2176", "message": "loading track", "data": {"track_path": track['path'], "track_exists": os.path.exists(track['path'])}, "timestamp": int(time.time() * 1000)}
        try:
            with open(r"f:\SagaLab\FruityWolf\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(debug_log) + "\n")
        except: pass
        # #endregion
        
        self.player.load_track(track)
    
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
            
    def save_lyrics(self):
        """Save lyrics for current track."""
        if self.current_track:
            lyrics = self.lyrics_edit.toPlainText()
            update_track_metadata(self.current_track['id'], lyrics=lyrics)
    
    
    
    def rescan_single_project(self, project_id: int):
        """Rescan a single project (for on-demand FLP parsing)."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.warning(self, "Busy", "A scan is already in progress.")
            return
            
        # Get path
        from .scanner.library_scanner import get_all_projects
        # This is inefficient, should use get_project_by_id logic or similar
        # But we don't have a direct helper exposed in app imports easily
        # Let's direct query or reuse scanner logic
        from .database import query_one
        
        row = query_one("SELECT path FROM projects WHERE id = ?", (project_id,))
        if not row:
            return
            
        path = Path(row['path'])
        if not path.exists():
            QMessageBox.warning(self, "Error", "Project path no longer exists.")
            return
            
        # UI Feedback
        self.scan_status.setText(f"Scanning {path.name}...")
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)
        
        # Use a temporary thread or the main scanner thread in a specialized mode?
        # Reusing the main scanner thread class is safest but it scans ALL.
        # We need to add a mode to scanner thread or just run a quick job.
        
        # Let's create a quick worker for single project
        # Ideally we'd modify ScannerThread to accept a target
        
        # Quick inline thread class for single project
        class SingleScanThread(QThread):
            finished = Signal(dict)
            
            def run(self):
                # Import here to avoid issues
                from .scanner.library_scanner import LibraryScanner
                scanner = LibraryScanner()
                # We need to manually trigger _scan_project logic
                # LibraryScanner doesn't expose public single scan easily that returns result properly 
                # effectively. But _scan_project is internal.
                # Actually _scan_project is what we want.
                try:
                    res = scanner._scan_project(path)
                    self.finished.emit(res or {})
                except Exception as e:
                    logger.error(f"Single scan error: {e}")
                    self.finished.emit({})

        self._single_scan_thread = SingleScanThread(self)
        self._single_scan_thread.finished.connect(lambda res: self._on_single_scan_finished(res, project_id))
        self._single_scan_thread.start()
        
    def _on_single_scan_finished(self, result, project_id):
        """Handle completion of single project scan."""
        self.scan_progress.setVisible(False)
        self.scan_status.setText("Scan complete")
        
        if self.stack.currentWidget() == self.project_drill_down:
            if self.project_drill_down.current_project and \
               (self.project_drill_down.current_project.get('id') == project_id or \
                self.project_drill_down.current_project.get('project_id') == project_id):
                
                # Retrieve updated data
                from .scanner.library_scanner import get_track_by_id
                # We need to refresh the view. Calling set_track again is the easiest way
                # provided we have the track_id.
                tid = self.project_drill_down.current_track_id
                if tid:
                    self.project_drill_down.set_track(tid)
        
        # Also clean up thread ref
        self._single_scan_thread = None
        
    
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
        else:
             # P12 Fix: Respect scan_on_startup
             if get_setting('scan_on_startup', 'false') == 'true':
                 self.rescan_library()
    
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
            # Update details if different
            # Note: might be redundant if selection triggers detail update, but safer
            self.update_details_panel(track)
            
            # Load waveform for mini player
            self.mini_waveform.clear_waveform()
            if track.get('path'):
                if hasattr(self, '_mini_waveform_thread') and self._mini_waveform_thread:
                    self._mini_waveform_thread.terminate()
                    self._mini_waveform_thread = None
                
                self._mini_waveform_thread = WaveformThread(track['path'])
                self._mini_waveform_thread.finished.connect(self._on_mini_waveform_ready)
                self._mini_waveform_thread.start()
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
            
            self.time_current.setText(format_duration(pos * dur))
            
            # Update waveforms
            self.mini_waveform.set_position(pos)
            
            if self.project_panel.isVisible() and self.player.current_track:
                viewed_id = self.project_panel.current_track_id
                playing_id = self.player.current_track.get('id')
                if viewed_id == playing_id:
                     self.project_panel.header.waveform.set_position(pos)
    
    def _on_mini_waveform_ready(self, waveform):
        if waveform:
            self.mini_waveform.set_waveform(
                waveform.peaks_min,
                waveform.peaks_max,
                waveform.duration
            )

    def _on_waveform_seek(self, position):
        self.player.seek(position)
        
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
        play_action = menu.addAction(get_icon("play", QColor("#38bdf8"), 16), "Play")
        play_action.triggered.connect(lambda: self.play_track(track))
        
        menu.addSeparator()
        
        # Favorite
        fav_icon = get_icon("heart", QColor("#ef4444"), 16) if track.get('favorite') else get_icon("heart", QColor("#94a3b8"), 16)
        fav_text = "Remove Favorite" if track.get('favorite') else "Add Favorite"
        fav_action = menu.addAction(fav_icon, fav_text)
        fav_action.triggered.connect(self.toggle_favorite)
        
        # Add to playlist submenu
        playlist_menu = AddToPlaylistMenu(self)
        playlist_menu.set_tracks([track['id']])
        playlist_menu = QMenu(menu)
        playlist_menu.setTitle("Add to Playlist")
        playlist_menu.setIcon(get_icon("playlist", QColor("#38bdf8"), 16))
        
        # Populate playlists
        # Note: playlists are handled via AddToPlaylistMenu above
        # Removed self.backend.get_playlists() call as backend is not initialized here
        
        # Tags
        tags_action = menu.addAction(get_icon("tag", QColor("#94a3b8"), 16), "Edit Tags (T)")
        tags_action.triggered.connect(self.show_tag_editor)
        
        menu.addSeparator()
        
        # Analysis
        analyze_action = menu.addAction(get_icon("analyze", QColor("#a855f7"), 16), "Analyze BPM/Key (B)")
        analyze_action.triggered.connect(self.analyze_track)
        
        # Edit metadata
        edit_action = menu.addAction(get_icon("edit", QColor("#94a3b8"), 16), "Edit Metadata (E)")
        edit_action.triggered.connect(self.edit_metadata)
        
        menu.addSeparator()
        
        # Open actions
        folder_action = menu.addAction(get_icon("folder_open", QColor("#38bdf8"), 16), "Open Folder (O)")
        folder_action.triggered.connect(self.open_project_folder)
        
        if track.get('flp_path'):
            flp_action = menu.addAction(get_icon("fl_studio", None, 16), "Open FLP")
            flp_action.triggered.connect(self.open_flp)
        
        menu.addSeparator()
        
        # Delete action (danger zone)
        delete_action = menu.addAction(get_icon("trash", QColor("#ef4444"), 16), "Remove from Library")
        delete_action.triggered.connect(self.delete_current_track)
        delete_action.triggered.connect(self.delete_current_track)
        
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

    def delete_current_track(self):
        """Remove current track from the library database."""
        if not self.current_track:
            return
        
        track_id = self.current_track['id']
        track_title = self.current_track.get('title', 'Unknown')
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Remove Track",
            f"Remove '{track_title}' from the library?\n\n(This will NOT delete the actual file)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete from database
            execute("DELETE FROM track_tags WHERE track_id = ?", (track_id,))
            execute("DELETE FROM playlist_tracks WHERE track_id = ?", (track_id,))
            execute("DELETE FROM tracks WHERE id = ?", (track_id,))
            
            # Clear current selection
            self.current_track = None
            self.update_details_panel(None)
            
            # Refresh list
            self.on_search(self.search_input.text())
    
    def clean_missing_files(self):
        """Remove all tracks whose files no longer exist."""
        # Find missing tracks
        all_tracks = query("SELECT id, path, title FROM tracks")
        missing = []
        for t in all_tracks:
            path = t['path'] if 'path' in t.keys() else None
            if path and not os.path.exists(path):
                missing.append(t)
        
        if not missing:
            QMessageBox.information(self, "Clean Library", "No missing files found!")
            return
        
        reply = QMessageBox.question(
            self, "Clean Library",
            f"Found {len(missing)} tracks with missing files.\n\nRemove them from the library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for t in missing:
                track_id = t['id']
                execute("DELETE FROM track_tags WHERE track_id = ?", (track_id,))
                execute("DELETE FROM playlist_tracks WHERE track_id = ?", (track_id,))
                execute("DELETE FROM tracks WHERE id = ?", (track_id,))
            
            QMessageBox.information(self, "Clean Library", f"Removed {len(missing)} tracks.")
            self.on_search(self.search_input.text())

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # Tools Menu
        tools_menu = menubar.addMenu("Tools")
        
        # Analyze Library
        analyze_action = QAction("Analyze Library (BPM/Key)...", self)
        analyze_action.triggered.connect(self.show_batch_analysis)
        tools_menu.addAction(analyze_action)
        
        # Clean missing files
        clean_action = QAction("Clean Missing Files...", self)
        clean_action.triggered.connect(self.clean_missing_files)
        tools_menu.addAction(clean_action)
        
        tools_menu.addSeparator()
        
        # Rescan
        rescan_action = QAction("Rescan Library", self)
        rescan_action.triggered.connect(self.rescan_library)
        tools_menu.addAction(rescan_action)
        
    def show_batch_analysis(self):
        """Show batch analysis dialog for all tracks."""
        # Get all track IDs
        rows = query("SELECT id FROM tracks")
        track_ids = [row['id'] for row in rows]
        
        if not track_ids:
            QMessageBox.information(self, "Analysis", "No tracks found in library.")
            return
            
        BatchAnalysisDialog.analyze_tracks(track_ids, self)
        
        # Refresh current view
        self.on_search(self.search_input.text())
        if self.current_track:
            self.update_details_panel(self.current_track)

    def rescan_library(self):
        """Trigger library rescan."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A library scan is already running.")
            return
        
        self.rescan_btn.setEnabled(False)
        self.rescan_btn.setText("Scanning...")
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)
        
        # Create and start scanner thread
        self.scanner_thread = ScannerThread(self)
        self.scanner_thread.progress.connect(self._on_scan_progress)
        self.scanner_thread.finished.connect(self._on_scan_finished)
        self.scanner_thread.error.connect(self._on_scan_error)
        self.scanner_thread.start()
        
        logger.info("Library rescan started")
    
    def _on_scan_progress(self, current, total, message):
        """Handle scan progress updates."""
        self.scan_progress.setRange(0, total)
        self.scan_progress.setValue(current)
        self.scan_status.setText(message)
        logger.debug(f"Scan progress: {message} ({current}/{total})")
    
    def _on_scan_finished(self, result):
        """Handle scan completion."""
        self.rescan_btn.setEnabled(True)
        self.rescan_btn.setText("Rescan Library")
        self.scan_progress.setVisible(False)
        self.scan_status.setText(f"{result.projects_found} projects, {result.tracks_found} tracks")
        
        logger.info(f"Scan complete: {result.projects_found} projects, {result.tracks_found} tracks")
        self.load_tracks()
        
        # P12 Fix: Handle auto_analyze
        if result.added_track_ids and get_setting('auto_analyze', 'false') == 'true':
            logger.info(f"Queuing {len(result.added_track_ids)} new tracks for auto-analysis")
            self.bg_analyzer.add_tracks(result.added_track_ids)
    
    def _on_scan_error(self, error_msg):
        """Handle scan error."""
        self.rescan_btn.setEnabled(True)
        self.rescan_btn.setText("Rescan Library")
        self.scan_progress.setVisible(False)
        self.scan_status.setText(f"Error: {error_msg}")
        logger.error(f"Scan error: {error_msg}")
        QMessageBox.warning(self, "Scan Error", error_msg)

    def show_command_palette(self):
        """Show command palette for quick keyboard navigation."""
        success, result_type, result_data = CommandPaletteDialog.show_palette(
            self.tracks_data, self
        )
        
        if not success:
            return
        
        if result_type == "track":
            # Play the selected track
            self.current_track = result_data
            self.play_track(result_data)
            self.update_details_panel(result_data)
        elif result_type == "command":
            # Execute command by ID
            self._execute_palette_command(result_data)
    
    def _execute_palette_command(self, command_id: str):
        """Execute a command palette command."""
        commands = {
            "nav:library": lambda: self.set_page("library"),
            "nav:favorites": lambda: self.set_page("favorites"),
            "nav:projects": lambda: self.set_page("projects"),
            "nav:insights": lambda: self.set_page("insights"),
            "nav:settings": lambda: self.set_page("settings"),
            "action:analyze": self.analyze_track,
            "action:edit": self.edit_metadata,
            "action:favorite": self.toggle_favorite,
            "action:open_flp": self.open_flp,
            "action:open_folder": self.open_project_folder,
            "action:rescan": self.rescan_library,
        }
        
        if command_id in commands:
            commands[command_id]()


    def _navigate_to_sample(self, sample_id):
        """Navigate to Sample Detail view (stable ID contract)."""
        self.sample_detail_view.set_sample(sample_id)
        self.stack.setCurrentWidget(self.sample_detail_view)

    def _back_to_insights(self):
        """Navigate back to Insights overview."""
        self.stack.setCurrentWidget(self.insights_view)

    def keyPressEvent(self, event):
        """Keyboard support for navigation."""
        if self.stack.currentWidget() == self.sample_detail_view:
            if event.key() == Qt.Key.Key_Escape:
                self._back_to_insights()
                return
        super().keyPressEvent(event)


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
    
    # Set application icon
    try:
        # Try to load icon from resources
        from .utils import get_icon
        app_icon = get_icon("app_icon", None, 256)
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
        else:
            # Fallback: try direct path
            icon_paths = [
                os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.svg"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "FruityWolf_icons", "app_icon.svg"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.svg"),
            ]
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    app.setWindowIcon(QIcon(icon_path))
                    break
    except Exception as e:
        logger.warning(f"Could not set application icon: {e}")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Cleanup on exit
    app.aboutToQuit.connect(db.close)
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
