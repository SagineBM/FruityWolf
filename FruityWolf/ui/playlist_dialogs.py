"""
Playlist Dialogs and Widgets

UI components for playlist management:
- Create/Edit playlist dialog
- Add to playlist menu
- Playlist track list with drag-drop reordering
"""

import logging
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QMenu,
    QMessageBox, QDialogButtonBox, QWidget, QFrame, QFileDialog,
    QAbstractItemView, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag, QPixmap, QColor, QAction

from ..scanner.playlist_manager import (
    create_playlist, get_playlist, get_all_playlists,
    update_playlist, delete_playlist, add_track_to_playlist,
    remove_track_from_playlist, get_playlist_tracks,
    reorder_playlist_track, export_playlist_m3u, generate_playlist_cover
)
from ..utils import get_icon

logger = logging.getLogger(__name__)


# =============================================================================
# Styles
# =============================================================================

DIALOG_STYLE = """
    QDialog {
        background: #0f172a;
    }
    QLabel {
        color: #f1f5f9;
    }
    QLineEdit, QTextEdit {
        padding: 8px 12px;
        border: 1px solid #334155;
        border-radius: 8px;
        background: #1e2836;
        color: #f1f5f9;
        font-size: 14px;
    }
    QLineEdit:focus, QTextEdit:focus {
        border-color: #38bdf8;
    }
    QListWidget {
        background: #1e2836;
        border: 1px solid #334155;
        border-radius: 8px;
        color: #f1f5f9;
    }
    QListWidget::item {
        padding: 8px 12px;
        border-bottom: 1px solid #1e293b;
    }
    QListWidget::item:selected {
        background: rgba(56, 189, 248, 0.2);
    }
    QListWidget::item:hover {
        background: rgba(56, 189, 248, 0.1);
    }
"""


# =============================================================================
# Create/Edit Playlist Dialog
# =============================================================================

class PlaylistEditDialog(QDialog):
    """Dialog for creating or editing a playlist."""
    
    playlist_saved = Signal(int)  # Emits playlist ID
    
    def __init__(self, playlist_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.playlist_id = playlist_id
        self.is_new = playlist_id is None
        
        self.setWindowTitle("New Playlist" if self.is_new else "Edit Playlist")
        self.setMinimumSize(400, 250)
        self.setStyleSheet(DIALOG_STYLE)
        
        self._setup_ui()
        
        if not self.is_new:
            self._load_playlist()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Name input
        name_label = QLabel("Playlist Name")
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Playlist")
        layout.addWidget(self.name_input)
        
        # Description input
        desc_label = QLabel("Description (optional)")
        desc_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(desc_label)
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Add a description...")
        self.desc_input.setMaximumHeight(80)
        layout.addWidget(self.desc_input)
        
        # Spacer
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        
        # Style buttons
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background: #22c55e;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background: #16a34a; }
        """)
        
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background: #475569;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background: #64748b; }
        """)
        
        layout.addWidget(button_box)
    
    def _load_playlist(self):
        """Load existing playlist data."""
        playlist = get_playlist(self.playlist_id)
        if playlist:
            self.name_input.setText(playlist.get('name', ''))
            self.desc_input.setPlainText(playlist.get('description', ''))
    
    def _save(self):
        """Save the playlist."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a playlist name.")
            return
        
        description = self.desc_input.toPlainText().strip()
        
        if self.is_new:
            self.playlist_id = create_playlist(name, description)
        else:
            update_playlist(self.playlist_id, name, description)
        
        self.playlist_saved.emit(self.playlist_id)
        self.accept()
    
    @staticmethod
    def create_new(parent=None) -> Optional[int]:
        """Show dialog and create a new playlist. Returns playlist ID or None."""
        dialog = PlaylistEditDialog(parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.playlist_id
        return None
    
    @staticmethod
    def edit_existing(playlist_id: int, parent=None) -> bool:
        """Show dialog and edit an existing playlist. Returns True if saved."""
        dialog = PlaylistEditDialog(playlist_id, parent=parent)
        return dialog.exec() == QDialog.DialogCode.Accepted


# =============================================================================
# Add to Playlist Menu
# =============================================================================

class AddToPlaylistMenu(QMenu):
    """A popup menu for adding tracks to playlists."""
    
    track_added = Signal(int, int)  # playlist_id, track_id
    
    def __init__(self, parent=None):
        super().__init__("Add to Playlist", parent)
        self.track_ids: List[int] = []
        self.setStyleSheet("""
            QMenu {
                background: #1e2836;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
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
    
    def set_tracks(self, track_ids: List[int]):
        """Set the track IDs to add when an item is selected."""
        self.track_ids = track_ids
        self._rebuild_menu()
    
    def _rebuild_menu(self):
        """Rebuild menu items."""
        self.clear()
        
        # New playlist option
        new_action = QAction("Create New Playlist...", self)
        new_action.setIcon(get_icon("add", QColor("#f1f5f9"), 16))
        new_action.triggered.connect(self._create_new_and_add)
        self.addAction(new_action)
        
        self.addSeparator()
        
        # Existing playlists
        playlists = get_all_playlists()
        
        if playlists:
            for playlist in playlists:
                action = QAction(f"{playlist['name']} ({playlist['track_count']})", self)
                action.setIcon(get_icon("playlist", QColor("#94a3b8"), 16))
                action.setData(playlist['id'])
                action.triggered.connect(self._add_to_playlist)
                self.addAction(action)
        else:
            no_playlists = QAction("No playlists yet", self)
            no_playlists.setEnabled(False)
            self.addAction(no_playlists)
    
    def _create_new_and_add(self):
        """Create a new playlist and add tracks to it."""
        playlist_id = PlaylistEditDialog.create_new(self.parent())
        if playlist_id:
            for track_id in self.track_ids:
                add_track_to_playlist(playlist_id, track_id)
                self.track_added.emit(playlist_id, track_id)
    
    def _add_to_playlist(self):
        """Add tracks to the selected playlist."""
        action = self.sender()
        playlist_id = action.data()
        if playlist_id:
            for track_id in self.track_ids:
                add_track_to_playlist(playlist_id, track_id)
                self.track_added.emit(playlist_id, track_id)


# =============================================================================
# Playlist Track List (with drag-drop reordering)
# =============================================================================

class PlaylistTrackList(QListWidget):
    """
    A list widget for displaying and reordering playlist tracks.
    
    Features:
    - Drag-drop reordering
    - Remove track on delete key
    - Double-click to play
    """
    
    track_removed = Signal(int)  # track_id
    track_double_clicked = Signal(dict)  # track dict
    order_changed = Signal()
    
    def __init__(self, playlist_id: int, parent=None):
        super().__init__(parent)
        self.playlist_id = playlist_id
        self.tracks: List[Dict] = []
        
        # Enable drag-drop
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # Styling
        self.setStyleSheet("""
            QListWidget {
                background: #1e2836;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #1e293b;
            }
            QListWidget::item:selected {
                background: rgba(56, 189, 248, 0.2);
            }
            QListWidget::item:hover {
                background: rgba(56, 189, 248, 0.1);
            }
        """)
        
        # Connections
        self.model().rowsMoved.connect(self._on_rows_moved)
        self.itemDoubleClicked.connect(self._on_double_clicked)
        
        # Load tracks
        self.refresh()
    
    def refresh(self):
        """Reload tracks from database."""
        self.clear()
        self.tracks = get_playlist_tracks(self.playlist_id)
        
        for i, track in enumerate(self.tracks):
            title = track.get('title', 'Unknown')
            project = track.get('project_name', '')
            duration = track.get('duration', 0)
            
            # Format duration
            mins = int(duration // 60)
            secs = int(duration % 60)
            duration_str = f"{mins}:{secs:02d}"
            
            item = QListWidgetItem(f"{i+1}. {title} — {project} [{duration_str}]")
            item.setData(Qt.ItemDataRole.UserRole, track)
            self.addItem(item)
    
    def _on_rows_moved(self, parent, start, end, destination, row):
        """Handle drag-drop reordering."""
        # Get the new order and update in database
        for i in range(self.count()):
            item = self.item(i)
            track = item.data(Qt.ItemDataRole.UserRole)
            if track:
                reorder_playlist_track(self.playlist_id, track['id'], i + 1)
        
        self.order_changed.emit()
    
    def _on_double_clicked(self, item: QListWidgetItem):
        """Handle double-click to play."""
        track = item.data(Qt.ItemDataRole.UserRole)
        if track:
            self.track_double_clicked.emit(track)
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item:
                track = item.data(Qt.ItemDataRole.UserRole)
                if track:
                    remove_track_from_playlist(self.playlist_id, track['id'])
                    self.track_removed.emit(track['id'])
                    self.refresh()
        else:
            super().keyPressEvent(event)


# =============================================================================
# Playlist Manager Panel
# =============================================================================

class PlaylistPanel(QWidget):
    """
    A panel showing all playlists with management controls.
    
    Features:
    - List of playlists
    - Create/Edit/Delete buttons
    - Export to M3U
    """
    
    playlist_selected = Signal(int)  # playlist_id
    playlist_play = Signal(int)  # playlist_id to play
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with buttons
        header = QHBoxLayout()
        
        title = QLabel("Playlists")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(title)
        header.addStretch()
        
        # Create button
        create_btn = QPushButton("+ New")
        create_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                background: #38bdf8;
                color: #0f172a;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #22d3ee; }
        """)
        create_btn.clicked.connect(self._create_playlist)
        header.addWidget(create_btn)
        
        layout.addLayout(header)
        
        # Playlist list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #f1f5f9;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 8px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background: rgba(56, 189, 248, 0.2);
            }
            QListWidget::item:hover {
                background: rgba(56, 189, 248, 0.1);
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.list_widget)
    
    def refresh(self):
        """Reload playlists from database."""
        self.list_widget.clear()
        playlists = get_all_playlists()
        
        for playlist in playlists:
            name = playlist.get('name', 'Untitled')
            count = playlist.get('track_count', 0)
            
            
            item = QListWidgetItem(f"{name} ({count} tracks)")
            item.setIcon(get_icon("playlist", QColor("#94a3b8"), 16))
            item.setData(Qt.ItemDataRole.UserRole, playlist)
            self.list_widget.addItem(item)
    
    def _create_playlist(self):
        """Create a new playlist."""
        playlist_id = PlaylistEditDialog.create_new(self)
        if playlist_id:
            self.refresh()
            self.playlist_selected.emit(playlist_id)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle playlist selection."""
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if playlist:
            self.playlist_selected.emit(playlist['id'])
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click to play playlist."""
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if playlist:
            self.playlist_play.emit(playlist['id'])
    
    def _show_context_menu(self, pos):
        """Show context menu for playlist."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if not playlist:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1e2836;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                color: #f1f5f9;
            }
            QMenu::item:selected {
                background: rgba(56, 189, 248, 0.2);
            }
        """)
        
        play_action = menu.addAction("Play")
        play_action.setIcon(get_icon("play", QColor("#38bdf8"), 16))
        play_action.triggered.connect(lambda: self.playlist_play.emit(playlist['id']))
        
        edit_action = menu.addAction("Edit")
        edit_action.setIcon(get_icon("edit", QColor("#94a3b8"), 16))
        edit_action.triggered.connect(lambda: self._edit_playlist(playlist['id']))
        
        menu.addSeparator()
        
        export_action = menu.addAction("Export M3U")
        export_action.setIcon(get_icon("folder_open", QColor("#94a3b8"), 16))
        export_action.triggered.connect(lambda: self._export_playlist(playlist['id']))
        
        cover_action = menu.addAction("Generate Cover")
        cover_action.setIcon(get_icon("eye", QColor("#94a3b8"), 16))
        cover_action.triggered.connect(lambda: self._generate_cover(playlist['id']))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(get_icon("trash", QColor("#ef4444"), 16))
        delete_action.triggered.connect(lambda: self._delete_playlist(playlist['id']))
        
        menu.exec(self.list_widget.mapToGlobal(pos))
    
    def _edit_playlist(self, playlist_id: int):
        """Edit a playlist."""
        if PlaylistEditDialog.edit_existing(playlist_id, self):
            self.refresh()
    
    def _delete_playlist(self, playlist_id: int):
        """Delete a playlist with confirmation."""
        playlist = get_playlist(playlist_id)
        if not playlist:
            return
        
        reply = QMessageBox.question(
            self, "Delete Playlist",
            f"Are you sure you want to delete '{playlist['name']}'?\n\n"
            "This will not delete any audio files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_playlist(playlist_id)
            self.refresh()
    
    def _export_playlist(self, playlist_id: int):
        """Export playlist to M3U file."""
        playlist = get_playlist(playlist_id)
        if not playlist:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Playlist",
            f"{playlist['name']}.m3u",
            "M3U Playlist (*.m3u)"
        )
        
        if filename:
            if export_playlist_m3u(playlist_id, filename):
                QMessageBox.information(self, "Export Complete", 
                    f"Playlist exported to:\n{filename}")
            else:
                QMessageBox.warning(self, "Export Failed", 
                    "Failed to export playlist.")
    
    def _generate_cover(self, playlist_id: int):
        """Generate cover art for playlist."""
        cover_path = generate_playlist_cover(playlist_id)
        if cover_path:
            QMessageBox.information(self, "Cover Generated", 
                f"Cover art saved to:\n{cover_path}")
        else:
            QMessageBox.warning(self, "Generation Failed", 
                "Failed to generate cover art.\nMake sure Pillow is installed.")


# =============================================================================
# Add Tracks Dialog
# =============================================================================

class AddTracksDialog(QDialog):
    """Dialog to search and add tracks to a playlist."""
    
    tracks_added = Signal()
    
    def __init__(self, playlist_id: int, parent=None):
        super().__init__(parent)
        self.playlist_id = playlist_id
        
        self.setWindowTitle("Add Songs to Playlist")
        self.resize(600, 500)
        self.setStyleSheet(DIALOG_STYLE)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search library...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Results List
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #1e2836;
                border: 1px solid #334155;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1e293b;
            }
            QListWidget::item:selected {
                background: #38bdf8;
                color: #0f172a;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #475569;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background: #64748b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        add_btn = QPushButton("Add Selected")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #22c55e;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #16a34a; }
        """)
        add_btn.clicked.connect(self._add_selected)
        
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(add_btn)
        
        layout.addLayout(btn_box)
        
        # Initial Search (show some tracks)
        self._on_search("")
        
    def _on_search(self, text):
        from ..database import query
        
        self.list_widget.clear()
        
        if not text:
            # Show recent or top tracks? limiting to 50
             sql = "SELECT id, title, path FROM tracks LIMIT 50"
             params = ()
        else:
             sql = "SELECT id, title, path FROM tracks WHERE title LIKE ? OR path LIKE ? LIMIT 50"
             wildcard = f"%{text}%"
             params = (wildcard, wildcard)
             
        tracks = query(sql, params)
        
        for t in tracks:
            item = QListWidgetItem(t['title'])
            item.setData(Qt.ItemDataRole.UserRole, t['id'])
            item.setToolTip(t['path'])
            self.list_widget.addItem(item)
            
    def _add_selected(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
            
        count = 0
        for item in items:
            tid = item.data(Qt.ItemDataRole.UserRole)
            if tid:
                add_track_to_playlist(self.playlist_id, tid)
                count += 1
                
        if count > 0:
            QMessageBox.information(self, "Added", f"Added {count} tracks to playlist.")
            self.tracks_added.emit()
            self.accept()
