"""
Command Palette Dialog

A fuzzy-search command palette for quick keyboard-driven navigation,
similar to VS Code's Ctrl+P.
"""

import logging
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QKeyEvent, QColor

from ..utils.icons import get_icon

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Type of command palette entry."""
    TRACK = "track"
    ACTION = "action"
    NAVIGATION = "navigation"
    

@dataclass
class CommandEntry:
    """A command palette entry."""
    id: str
    title: str
    subtitle: str = ""
    icon: str = ""
    type: CommandType = CommandType.ACTION
    data: Optional[Dict] = None
    action: Optional[Callable] = None


class CommandPaletteDialog(QDialog):
    """
    Fuzzy-search command palette dialog.
    
    Features:
    - Type to search tracks and commands
    - Arrow keys to navigate
    - Enter to execute
    - Escape to close
    - ">" prefix for commands only
    
    Signals:
        track_selected(dict): Track was selected
        command_executed(str): Command ID was executed
    """
    
    track_selected = Signal(dict)
    command_executed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMaximumHeight(400)
        
        self._tracks: List[Dict] = []
        self._commands: List[CommandEntry] = []
        self._all_entries: List[CommandEntry] = []
        self._filtered_entries: List[CommandEntry] = []
        
        self._setup_ui()
        self._setup_default_commands()
    
    def _setup_ui(self):
        """Setup the UI."""
        self.setStyleSheet("""
            QDialog {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLineEdit {
                background: #1e293b;
                border: none;
                border-bottom: 1px solid #334155;
                padding: 16px;
                color: #f1f5f9;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-bottom-color: #38bdf8;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 16px;
                border-radius: 6px;
                margin: 2px 8px;
            }
            QListWidget::item:selected {
                background: rgba(56, 189, 248, 0.15);
            }
            QListWidget::item:hover {
                background: rgba(56, 189, 248, 0.08);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks or type > for commands...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.installEventFilter(self)
        layout.addWidget(self.search_input)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self.results_list)
        
        # Hint label
        self.hint_label = QLabel("↑↓ navigate • Enter select • Esc close • > commands")
        self.hint_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 8px 16px;")
        layout.addWidget(self.hint_label)
    
    def _setup_default_commands(self):
        """Setup default navigation commands."""
        self._commands = [
            CommandEntry("nav:library", "Go to Library", "Show all tracks", "library", CommandType.NAVIGATION),
            CommandEntry("nav:favorites", "Go to Favorites", "Show favorite tracks", "heart", CommandType.NAVIGATION),
            CommandEntry("nav:recent", "Recently Added", "Show newest tracks", "time", CommandType.NAVIGATION),
            CommandEntry("nav:missing", "Missing Metadata", "Tracks without BPM/Key", "alert", CommandType.NAVIGATION),
            CommandEntry("nav:settings", "Settings", "Open settings dialog", "settings", CommandType.NAVIGATION),
            CommandEntry("action:analyze", "Analyze Track", "Detect BPM and Key", "analyze", CommandType.ACTION),
            CommandEntry("action:edit", "Edit Metadata", "Edit track metadata", "edit", CommandType.ACTION),
            CommandEntry("action:favorite", "Toggle Favorite", "Add or remove from favorites", "heart", CommandType.ACTION),
            CommandEntry("action:open_flp", "Open FLP", "Open FL Studio project file", "fl_studio", CommandType.ACTION),
            CommandEntry("action:open_folder", "Open Folder", "Open project in Explorer", "folder", CommandType.ACTION),
            CommandEntry("action:rescan", "Rescan Library", "Scan library folders", "scan", CommandType.ACTION),
        ]
    
    def set_tracks(self, tracks: List[Dict]):
        """Set the available tracks for searching."""
        self._tracks = tracks
        self._rebuild_entries()
    
    def _rebuild_entries(self):
        """Rebuild the full entries list."""
        self._all_entries = []
        
        # Add tracks
        for track in self._tracks[:200]:  # Limit to first 200 for performance
            self._all_entries.append(CommandEntry(
                id=f"track:{track.get('id')}",
                title=track.get('title', 'Unknown'),
                subtitle=track.get('project_name', ''),
                icon="music",
                type=CommandType.TRACK,
                data=track
            ))
        
        # Add commands
        self._all_entries.extend(self._commands)
    
    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self._filter_results(text)
        self._update_list()
    
    def _filter_results(self, query: str):
        """Filter entries based on query."""
        query = query.lower().strip()
        
        if not query:
            # Show recent tracks and commands
            self._filtered_entries = self._all_entries[:15]
            return
        
        # Check for command prefix
        if query.startswith(">"):
            query = query[1:].strip()
            entries = [e for e in self._all_entries if e.type in (CommandType.ACTION, CommandType.NAVIGATION)]
        else:
            entries = self._all_entries
        
        # Fuzzy match
        scored = []
        for entry in entries:
            score = self._fuzzy_score(query, entry.title.lower())
            if score > 0:
                scored.append((score, entry))
            elif query in entry.subtitle.lower():
                scored.append((0.5, entry))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        self._filtered_entries = [e for _, e in scored[:20]]
    
    def _fuzzy_score(self, query: str, target: str) -> float:
        """Simple fuzzy matching score."""
        if query == target:
            return 2.0
        if target.startswith(query):
            return 1.5
        if query in target:
            return 1.0
        
        # Character-by-character match
        qi = 0
        for char in target:
            if qi < len(query) and char == query[qi]:
                qi += 1
        
        if qi == len(query):
            return 0.8
        return 0.0
    
    def _update_list(self):
        """Update the results list widget."""
        self.results_list.clear()
        
        for entry in self._filtered_entries:
            item = QListWidgetItem()
            
            # Create custom widget for item
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(12)
            
            # Icon
            if entry.icon:
                icon_label = QLabel()
                icon_label.setPixmap(get_icon(entry.icon, QColor("#94a3b8"), 18).pixmap(18, 18))
                icon_label.setFixedSize(24, 24)
                layout.addWidget(icon_label)
            
            # Text
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            text_layout.setContentsMargins(0, 0, 0, 0)
            
            title = QLabel(entry.title)
            title.setStyleSheet("color: #f1f5f9; font-size: 14px;")
            text_layout.addWidget(title)
            
            if entry.subtitle:
                subtitle = QLabel(entry.subtitle)
                subtitle.setStyleSheet("color: #64748b; font-size: 11px;")
                text_layout.addWidget(subtitle)
            
            layout.addLayout(text_layout, 1)
            
            # Type badge
            type_label = QLabel(entry.type.value.upper())
            type_label.setStyleSheet("""
                color: #64748b;
                font-size: 10px;
                background: #1e293b;
                padding: 2px 6px;
                border-radius: 4px;
            """)
            layout.addWidget(type_label)
            
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(widget.sizeHint())
            
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
        
        # Select first item
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
    
    def _on_item_clicked(self, item):
        """Handle item single click."""
        self.results_list.setCurrentItem(item)
    
    def _on_item_activated(self, item):
        """Handle item activation (double-click or Enter)."""
        self._execute_item(item)
    
    def _execute_item(self, item):
        """Execute the selected item."""
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        if entry.type == CommandType.TRACK and entry.data:
            self.track_selected.emit(entry.data)
        else:
            self.command_executed.emit(entry.id)
        
        self.accept()
    
    def eventFilter(self, obj, event):
        """Handle keyboard navigation."""
        if obj == self.search_input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Down:
                current = self.results_list.currentRow()
                if current < self.results_list.count() - 1:
                    self.results_list.setCurrentRow(current + 1)
                return True
            elif event.key() == Qt.Key.Key_Up:
                current = self.results_list.currentRow()
                if current > 0:
                    self.results_list.setCurrentRow(current - 1)
                return True
            elif event.key() == Qt.Key.Key_Return:
                current_item = self.results_list.currentItem()
                if current_item:
                    self._execute_item(current_item)
                return True
            elif event.key() == Qt.Key.Key_Escape:
                self.reject()
                return True
        
        return super().eventFilter(obj, event)
    
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        self.search_input.setFocus()
        self._filter_results("")
        self._update_list()
        
        # Center on parent
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + 100
            self.move(x, y)
    
    @staticmethod
    def show_palette(tracks: List[Dict], parent=None):
        """
        Show the command palette and return the result.
        
        Returns:
            Tuple of (success, result_type, result_data)
            result_type: "track" or "command"
        """
        dialog = CommandPaletteDialog(parent)
        dialog.set_tracks(tracks)
        
        result_data = [None, None]  # [type, data]
        
        def on_track(track):
            result_data[0] = "track"
            result_data[1] = track
        
        def on_command(cmd_id):
            result_data[0] = "command"
            result_data[1] = cmd_id
        
        dialog.track_selected.connect(on_track)
        dialog.command_executed.connect(on_command)
        
        if dialog.exec():
            return True, result_data[0], result_data[1]
        return False, None, None
