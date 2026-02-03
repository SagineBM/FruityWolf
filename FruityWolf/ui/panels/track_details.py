"""
Track Details Panel

Displays detailed information for audio tracks (Library View).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QGroupBox, QSizePolicy, QTextEdit,
    QFileDialog, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor, QAction

from ...utils import get_icon, format_duration, get_cover_art, get_placeholder_cover, format_file_size
from ...utils.image_manager import get_image_manager
from ...services.cover_manager import (
    save_cover_image, set_track_cover, get_track_cover_path
)

class TrackDetailsPanel(QWidget):
    """Side panel for displaying Track details."""
    
    edit_clicked = Signal()
    play_clicked = Signal(dict)
    favorite_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    open_flp_clicked = Signal(dict)
    open_folder_clicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_track = None
        self.current_cover_path = None
        self.current_cover_request_id = None
        self.image_manager = get_image_manager()
        self.image_manager.image_loaded.connect(self._on_image_loaded)
        self._setup_ui()
        
    def _setup_ui(self):
        # Scroll Area Wrapper
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("QWidget { background: transparent; }")
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("QWidget { background: transparent; }")
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)
        
        # Cover Art
        cover_container = QWidget()
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(8)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #1e293b;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cover_label.customContextMenuRequested.connect(self._show_cover_menu)
        cover_layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.cover_btn = QPushButton("Change Cover")
        self.cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f1f5f9;
            }
        """)
        self.cover_btn.clicked.connect(self._change_cover)
        self.cover_btn.hide()
        cover_layout.addWidget(self.cover_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(cover_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addSpacing(8)
        
        # Titles
        self.title_label = QLabel("Select a track")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)
        
        self.project_label = QLabel("")
        self.project_label.setStyleSheet("font-size: 13px; color: #94a3b8;")
        self.project_label.setWordWrap(True)
        self.project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.project_label)
        
        self.main_layout.addSpacing(8)
        
        # === ACTIONS ===
        self.actions_layout = QVBoxLayout()
        self.actions_layout.setSpacing(8)
        
        # Play Button
        self.btn_play = QPushButton(" Play Track")
        self.btn_play.setIcon(get_icon("play", QColor("#ffffff"), 20))
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
        self.btn_play.clicked.connect(self._on_play)
        self.actions_layout.addWidget(self.btn_play)
        
        # Secondary Actions Row
        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)
        
        self.btn_fav = QPushButton(" Fav")
        self.btn_fav.setIcon(get_icon("heart", QColor("#94a3b8"), 16))
        self.btn_fav.setStyleSheet(self._secondary_btn_style())
        self.btn_fav.clicked.connect(self._on_fav)
        row_actions.addWidget(self.btn_fav, 1)
        
        self.btn_playlist = QPushButton(" Playlist")
        self.btn_playlist.setIcon(get_icon("playlist", QColor("#94a3b8"), 16))
        self.btn_playlist.setStyleSheet(self._secondary_btn_style())
        self.btn_playlist.clicked.connect(self._on_playlist)
        row_actions.addWidget(self.btn_playlist, 1)

        self.btn_open_flp = QPushButton(" FLP")
        self.btn_open_flp.setIcon(get_icon("fl_studio", QColor("#94a3b8"), 16))
        self.btn_open_flp.setStyleSheet(self._secondary_btn_style())
        self.btn_open_flp.clicked.connect(self._on_open_flp)
        row_actions.addWidget(self.btn_open_flp, 1)
        
        self.actions_layout.addLayout(row_actions)
        self.main_layout.addLayout(self.actions_layout)
        
        self.main_layout.addSpacing(8)
        
        # === METADATA ===
        self.meta_group = QGroupBox("METADATA")
        self.meta_layout = QGridLayout(self.meta_group)
        self.meta_layout.setSpacing(12)
        
        # Edit Button (Top Right of Group)
        self.btn_edit = QPushButton("")
        self.btn_edit.setIcon(get_icon("edit", QColor("#94a3b8"), 16))
        self.btn_edit.setToolTip("Edit Metadata")
        self.btn_edit.setFixedSize(24, 24)
        self.btn_edit.setStyleSheet("background: transparent; border: none;")
        self.btn_edit.clicked.connect(self.edit_clicked.emit)
        self.meta_layout.addWidget(self.btn_edit, 0, 2)
        
        # Fields
        self.bpm_label = self._add_field("BPM", 0, 0)
        self.key_label = self._add_field("KEY", 0, 1)
        self.duration_label = self._add_field("DURATION", 2, 0)
        self.size_label = self._add_field("SIZE", 2, 1)
        self.genre_label = self._add_field("GENRE", 4, 0, colspan=2)
        
        self.main_layout.addWidget(self.meta_group)
        
        # === PROJECT FOLDERS ===
        self.folders_group = QGroupBox("PROJECT FOLDERS")
        self.folders_layout = QVBoxLayout(self.folders_group)
        self.folders_layout.setSpacing(4)
        
        self.btn_samples = self._create_folder_btn("Samples")
        self.folders_layout.addWidget(self.btn_samples)
        
        self.btn_audio = self._create_folder_btn("Audio")
        self.folders_layout.addWidget(self.btn_audio)
        
        self.btn_stems = self._create_folder_btn("Stems")
        self.folders_layout.addWidget(self.btn_stems)
        
        self.btn_backup = self._create_folder_btn("Backup")
        self.folders_layout.addWidget(self.btn_backup)
        
        self.main_layout.addWidget(self.folders_group)
        
        # === LYRICS / NOTES ===
        self.lyrics_group = QGroupBox("LYRICS & NOTES")
        self.lyrics_layout = QVBoxLayout(self.lyrics_group)
        
        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setPlaceholderText("Add lyrics or notes...")
        self.lyrics_edit.setMinimumHeight(100)
        self.lyrics_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #cbd5e1;
                padding: 8px;
            }
        """)
        # We need a save mechanism? Or auto-save?
        # For now read-only or just editable but not connected to save
        # Connecting textChanged might be spammy, but standard practice in this app
        self.lyrics_layout.addWidget(self.lyrics_edit)
        
        self.main_layout.addWidget(self.lyrics_group)
        
        self.main_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
    def _add_field(self, label_text, row, col, colspan=1):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        self.meta_layout.addWidget(lbl, row, col, 1, colspan)
        
        val = QLabel("--")
        val.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: 500;")
        val.setWordWrap(True)
        self.meta_layout.addWidget(val, row + 1, col, 1, colspan)
        return val
    
    def _secondary_btn_style(self):
        return """
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94a3b8;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f1f5f9;
                border-color: #475569;
            }
        """

    def _create_folder_btn(self, text):
        btn = QPushButton(f" {text}")
        btn.setIcon(get_icon("folder_open", QColor("#94a3b8"), 14))
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                color: #94a3b8;
                padding: 4px;
            }
            QPushButton:hover {
                color: #38bdf8;
                background: rgba(56, 189, 248, 0.1);
                border-radius: 4px;
            }
            QPushButton:disabled {
                color: #475569;
            }
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("folder_path", "")
        btn.clicked.connect(self._on_folder_btn_clicked)
        return btn

    def _on_folder_btn_clicked(self):
        """Emit open_folder with path from sender (avoids disconnect/connect per track)."""
        btn = self.sender()
        if btn and isinstance(btn, QPushButton):
            path = btn.property("folder_path")
            if path:
                self.open_folder_clicked.emit(path)
        
    def set_track(self, track: dict):
        """Display track data."""
        self.current_track = track
        if not track:
            self.clear()
            return
        
        self.btn_play.setEnabled(True)
        self.btn_fav.setEnabled(True)
        self.btn_playlist.setEnabled(True)
        
        # Check if project path exists for FLP button
        import os
        flp_path = track.get('project_path')
        self.btn_open_flp.setEnabled(bool(flp_path and os.path.exists(flp_path)))
        if self.btn_open_flp.isEnabled():
             self.btn_open_flp.setToolTip(f"Open Project: {flp_path}")
        else:
             self.btn_open_flp.setToolTip("Project file not found")
            
        # Cover - Async loading
        track_id = track.get('id')
        project_path = track.get('project_path')
        
        # Cancel previous cover request
        if self.current_cover_request_id:
            self.image_manager.cancel_request(self.current_cover_request_id)
        
        # Get cover path (custom first, then project cover)
        self.current_cover_path = get_track_cover_path(track_id, project_path) if track_id else get_cover_art(project_path)
        self.current_cover_request_id = f"track_{track_id}_{project_path}"
        
        # Show placeholder immediately
        self.cover_label.setPixmap(get_placeholder_cover(200, track.get('title', '')))
        self.cover_btn.show()
        
        # Load cover asynchronously
        if self.current_cover_path:
            pix = self.image_manager.get_image(self.current_cover_path, 200, self.current_cover_request_id)
            if pix:
                # Found in cache, use immediately
                self.cover_label.setPixmap(pix)
            
        # Info
        self.title_label.setText(track.get('title', 'Unknown Title'))
        self.project_label.setText(track.get('project_name', 'Unknown Project'))
        
        # Meta
        bpm = track.get('bpm_user') or track.get('bpm_detected')
        self.bpm_label.setText(f"{int(bpm)}" if bpm else "--")
        
        key = track.get('key_user') or track.get('key_detected')
        self.key_label.setText(key if key else "--")
        
        duration = track.get('duration', 0)
        if duration:
            self.duration_label.setText(format_duration(duration))
        else:
            self.duration_label.setText("--")
            
        size = track.get('file_size', 0)
        self.size_label.setText(format_file_size(size) if size else "--")
        
        self.genre_label.setText(track.get('genre', '--'))
        
        # Folders
        self._setup_folder_btn(self.btn_samples, track.get('samples_dir'))
        self._setup_folder_btn(self.btn_audio, track.get('audio_dir'))
        self._setup_folder_btn(self.btn_stems, track.get('stems_dir'))
        self._setup_folder_btn(self.btn_backup, track.get('backup_dir'))
        
        # Lyrics/Notes
        # Ideally we merge them or have tabs? 
        # User said "lyrics part", assume combined notes/lyrics for now
        text = ""
        if track.get('lyrics'):
            text += f"[Lyrics]\n{track['lyrics']}\n\n"
        if track.get('notes'):
            text += f"[Notes]\n{track['notes']}"
            
        self.lyrics_edit.setPlainText(text.strip())
        
        # Favorite state
        if track.get('favorite'):
            self.btn_fav.setIcon(get_icon("heart", QColor("#ef4444"), 16))
            self.btn_fav.setStyleSheet(self._secondary_btn_style().replace("#94a3b8", "#ef4444"))
        else:
            self.btn_fav.setIcon(get_icon("heart", QColor("#94a3b8"), 16))
            self.btn_fav.setStyleSheet(self._secondary_btn_style())
            
    def _setup_folder_btn(self, btn, path):
        import os
        exists = bool(path and os.path.exists(path))
        btn.setEnabled(exists)
        btn.setProperty("folder_path", path or "")
        btn.setToolTip(path if exists else "Folder not found")
        
    def clear(self):
        """Reset fields."""
        self.current_track = None
        self.current_cover_path = None
        self.current_cover_request_id = None
        self.cover_btn.hide()
        self.title_label.setText("Select a track")
        self.project_label.setText("")
        self.cover_label.setPixmap(get_placeholder_cover(200, ""))
        self.bpm_label.setText("--")
        self.key_label.setText("--")
        self.duration_label.setText("--")
        self.size_label.setText("--")
        self.genre_label.setText("--")
        self.btn_play.setEnabled(False)
        self.btn_fav.setEnabled(False)
        self.btn_playlist.setEnabled(False)
        self.btn_open_flp.setEnabled(False)
        
    def _on_play(self):
        if self.current_track:
            self.play_clicked.emit(self.current_track)
    
    def _on_fav(self):
        if self.current_track:
            self.favorite_clicked.emit(self.current_track)
            
    def _on_playlist(self):
        if self.current_track:
            self.add_playlist_clicked.emit(self.current_track)

    def _on_open_flp(self):
        if self.current_track:
            self.open_flp_clicked.emit(self.current_track)

    def _on_image_loaded(self, path: str, pixmap: QPixmap, request_id: str):
        """Update cover if it matches current track."""
        if request_id == self.current_cover_request_id and path == self.current_cover_path:
            if not pixmap.isNull():
                self.cover_label.setPixmap(pixmap)
    
    def _show_cover_menu(self, pos):
        """Show context menu for cover."""
        if not self.current_track:
            return
        
        menu = QMenu(self)
        
        change_action = QAction("Change Cover...", self)
        change_action.triggered.connect(self._change_cover)
        menu.addAction(change_action)
        
        remove_action = QAction("Remove Custom Cover", self)
        remove_action.triggered.connect(self._remove_cover)
        menu.addAction(remove_action)
        
        menu.exec(self.cover_label.mapToGlobal(pos))
    
    def _change_cover(self):
        """Open file dialog to select new cover image."""
        if not self.current_track:
            return
        
        track_id = self.current_track.get('id')
        if not track_id:
            return
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Image",
            "",
            "Image Files (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Save cover image
            saved_path = save_cover_image(file_path, 'track', track_id)
            if saved_path:
                # Update database
                if set_track_cover(track_id, saved_path):
                    # Update UI
                    self.current_cover_path = saved_path
                    self.current_cover_request_id = f"track_{track_id}_{saved_path}"
                    
                    # Load new cover
                    pix = self.image_manager.get_image(saved_path, 200, self.current_cover_request_id)
                    if pix:
                        self.cover_label.setPixmap(pix)
                    else:
                        # Will be loaded async
                        self.cover_label.setPixmap(get_placeholder_cover(200, self.current_track.get('title', '')))
                else:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error("Failed to update track cover in database")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to change cover: {e}")
    
    def _remove_cover(self):
        """Remove custom cover and revert to project cover."""
        if not self.current_track:
            return
        
        track_id = self.current_track.get('id')
        if not track_id:
            return
        
        try:
            if set_track_cover(track_id, None):
                # Reload cover (will use project cover)
                project_path = self.current_track.get('project_path')
                self.current_cover_path = get_track_cover_path(track_id, project_path)
                self.current_cover_request_id = f"track_{track_id}_{project_path}"
                
                if self.current_cover_path:
                    pix = self.image_manager.get_image(self.current_cover_path, 200, self.current_cover_request_id)
                    if pix:
                        self.cover_label.setPixmap(pix)
                    else:
                        self.cover_label.setPixmap(get_placeholder_cover(200, self.current_track.get('title', '')))
                else:
                    self.cover_label.setPixmap(get_placeholder_cover(200, self.current_track.get('title', '')))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to remove cover: {e}")
