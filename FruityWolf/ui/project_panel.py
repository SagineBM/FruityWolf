"""
Project Drill-Down Panel

A detailed view panel for FL Studio projects showing:
- Project info (name, path, FLP location)
- Tabs for: Renders, Stems, Samples, Backups
- Open in Explorer / Open FLP buttons
- Quick actions (scan, refresh)
"""

import os
import logging
import subprocess
from typing import List, Dict, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QMessageBox, QGridLayout, QSizePolicy,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from ..scanner.library_scanner import get_track_by_id, AUDIO_EXTENSIONS
from ..database import query
from ..utils import format_file_size, format_timestamp, get_icon

logger = logging.getLogger(__name__)


# =============================================================================
# Styles
# =============================================================================

PANEL_STYLE = """
    QFrame#DrillDownPanel {
        background: #0f172a;
        border-radius: 0;
    }
    QLabel {
        color: #f1f5f9;
    }
    QLabel#Title {
        font-size: 18px;
        font-weight: bold;
        color: #f1f5f9;
    }
    QLabel#Subtitle {
        font-size: 12px;
        color: #94a3b8;
    }
    QTabWidget::pane {
        border: 1px solid #334155;
        border-top: none;
        background: #0f172a;
    }
    QTabBar::tab {
        padding: 10px 20px;
        background: transparent;
        color: #94a3b8;
        border: none;
        border-bottom: 2px solid transparent;
        font-weight: 500;
        font-size: 13px;
    }
    QTabBar::tab:selected {
        color: #38bdf8;
        border-bottom: 2px solid #38bdf8;
    }
    QTabBar::tab:hover {
        color: #e2e8f0;
        background: rgba(255,255,255,0.03);
    }
    QTableWidget {
        background-color: #0f172a;
        border: none;
        gridline-color: #1e293b;
        color: #f1f5f9;
    }
    QTableWidget::item {
        padding: 6px;
        border-bottom: 1px solid #1e293b;
    }
    QTableWidget::item:selected {
        background-color: rgba(56, 189, 248, 0.15);
        color: #f1f5f9;
        border-bottom: 1px solid #38bdf8;
    }
    QHeaderView::section {
        background-color: #0f172a;
        color: #94a3b8;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #334155;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
    }
"""

BUTTON_STYLE = """
    QPushButton {
        padding: 6px 12px;
        background: #1e293b;
        color: #94a3b8;
        border: 1px solid #334155;
        border-radius: 6px;
        font-weight: 500;
    }
    QPushButton:hover {
        background: #334155;
        color: #f1f5f9;
        border-color: #475569;
    }
    QPushButton#Primary {
        background: #38bdf8;
        color: #0f172a;
        border: none;
    }
    QPushButton#Primary:hover {
        background: #22d3ee;
    }
"""


# =============================================================================
# File Table Widget
# =============================================================================

class FileTableWidget(QTableWidget):
    """A detailed table of files with double-click actions."""
    
    file_selected = Signal(str)  # path
    file_double_clicked = Signal(str)  # path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder_path: Optional[str] = None
        self.files: List[str] = []
        
        # Setup table
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["", "NAME", "SIZE", "DATE"])
        
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.setColumnWidth(0, 40)
        
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setStyleSheet("alternate-background-color: #162032;")
        
        self.cellDoubleClicked.connect(self._on_double_click)
    
    def set_folder(self, folder_path: Optional[str], extensions: set = AUDIO_EXTENSIONS):
        """Load files from a folder."""
        self.setRowCount(0)
        self.folder_path = folder_path
        self.files = []
        
        if not folder_path or not os.path.isdir(folder_path):
            return
        
        try:
            entries = []
            for name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, name)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(name)[1].lower()
                    if extensions is None or ext in extensions:
                        stat = os.stat(file_path)
                        entries.append({
                            'name': name,
                            'path': file_path,
                            'size': stat.st_size,
                            'mtime': stat.st_mtime,
                            'ext': ext
                        })
            
            # Sort by name
            entries.sort(key=lambda x: x['name'].lower())
            
            self.setRowCount(len(entries))
            
            for row, entry in enumerate(entries):
                self.files.append(entry['path'])
                
                # 0. Icon
                if entry['ext'] == '.flp':
                    # Use FL Studio icon
                    icon = get_icon("fl_studio", None, 20)
                elif entry['ext'] in AUDIO_EXTENSIONS:
                    # Use Audio icon (Blue)
                    icon = get_icon("audio", QColor("#38bdf8"), 18)
                else:
                    # Fallback
                    icon = get_icon("tag", QColor("#94a3b8"), 16)
                
                icon_item = QTableWidgetItem()
                icon_item.setIcon(icon)
                icon_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row, 0, icon_item)
                
                # 1. Name
                name_item = QTableWidgetItem(entry['name'])
                self.setItem(row, 1, name_item)
                
                # 2. Size
                size_item = QTableWidgetItem(format_file_size(entry['size']))
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                size_item.setForeground(QColor("#94a3b8"))
                self.setItem(row, 2, size_item)
                
                # 3. Date
                date_str = format_timestamp(entry['mtime'])
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                date_item.setForeground(QColor("#64748b"))
                self.setItem(row, 3, date_item)
                
                # Store path
                name_item.setData(Qt.ItemDataRole.UserRole, entry['path'])
                
        except PermissionError:
            pass
    
    def _on_double_click(self, row, col):
        """Handle double-click to open/play file."""
        item = self.item(row, 1) # Name item has data
        if item:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                self.file_double_clicked.emit(path)


# =============================================================================
# Project Info Header
# =============================================================================

class ProjectInfoHeader(QFrame):
    """Header showing project name, path, and quick actions."""
    
    back_requested = Signal()  # New signal
    open_in_explorer = Signal(str)  # path
    open_flp = Signal(str)  # FLP path
    play_track = Signal(dict)  # track dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_data: Optional[Dict] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)
        
        # Title row
        title_row = QHBoxLayout()
        
        # Back button
        # Back button
        self.back_btn = QPushButton()
        self.back_btn.setIcon(get_icon("back", QColor("#94a3b8"), 16))
        self.back_btn.setFixedSize(30, 30)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: 1px solid #334155;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #334155;
                color: #f1f5f9;
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        title_row.addWidget(self.back_btn)
        
        self.title_label = QLabel("Select a track")
        self.title_label.setObjectName("Title")
        title_row.addWidget(self.title_label)
        
        title_row.addStretch()
        
        # Action buttons
        self.open_folder_btn = QPushButton(" Open Folder")
        self.open_folder_btn.setIcon(get_icon("folder_open", QColor("#94a3b8"), 16))
        self.open_folder_btn.setStyleSheet(BUTTON_STYLE)
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.setVisible(False)
        title_row.addWidget(self.open_folder_btn)
        
        self.open_flp_btn = QPushButton(" Open FLP")
        self.open_flp_btn.setIcon(get_icon("fl_studio", None, 16))
        self.open_flp_btn.setStyleSheet(BUTTON_STYLE.replace("#334155", "#8b5cf6"))
        self.open_flp_btn.clicked.connect(self._open_flp)
        self.open_flp_btn.setVisible(False)
        title_row.addWidget(self.open_flp_btn)
        
        layout.addLayout(title_row)
        
        # Subtitle (path)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("Subtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)
        
        # Stats row
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("Subtitle")
        layout.addWidget(self.stats_label)
    
    def set_project(self, project_data: Dict):
        """Set the project to display."""
        self.project_data = project_data
        
        name = project_data.get('project_name', 'Unknown Project')
        path = project_data.get('project_path', '')
        flp = project_data.get('flp_path', '')
        
        self.title_label.setText(name)
        self.subtitle_label.setText(path)
        
        # Build stats
        stats = []
        if project_data.get('audio_dir') and os.path.isdir(project_data['audio_dir']):
            count = len([f for f in os.listdir(project_data['audio_dir']) 
                        if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS])
            stats.append(f"{count} audio files")
        
        if project_data.get('samples_dir') and os.path.isdir(project_data['samples_dir']):
            count = len(os.listdir(project_data['samples_dir']))
            stats.append(f"{count} samples")
        
        if project_data.get('stems_dir') and os.path.isdir(project_data['stems_dir']):
            count = len([f for f in os.listdir(project_data['stems_dir']) 
                        if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS])
            stats.append(f"{count} stems")
        
        self.stats_label.setText("  •  ".join(stats) if stats else "")
        
        # Show/hide buttons
        self.open_folder_btn.setVisible(bool(path))
        self.open_flp_btn.setVisible(bool(flp) and os.path.exists(flp))
    
    def clear_project(self):
        """Clear the project display."""
        self.project_data = None
        self.title_label.setText("Select a track")
        self.subtitle_label.setText("")
        self.stats_label.setText("")
        self.open_folder_btn.setVisible(False)
        self.open_flp_btn.setVisible(False)
    
    def _open_folder(self):
        """Open project folder in Explorer."""
        if self.project_data and self.project_data.get('project_path'):
            path = self.project_data['project_path']
            if os.path.isdir(path):
                self.open_in_explorer.emit(path)
                try:
                    os.startfile(path)
                except Exception as e:
                    logger.error(f"Failed to open folder: {e}")
    
    def _open_flp(self):
        """Open FL Studio project file."""
        if self.project_data and self.project_data.get('flp_path'):
            flp = self.project_data['flp_path']
            if os.path.exists(flp):
                self.open_flp.emit(flp)
                try:
                    os.startfile(flp)
                except Exception as e:
                    logger.error(f"Failed to open FLP: {e}")


# =============================================================================
# Project Drill-Down Panel
# =============================================================================

class ProjectDrillDownPanel(QFrame):
    """
    Main panel for drilling down into project details.
    
    Shows:
    - Project header with name, path, quick actions
    - Tabbed view of: Renders, Stems, Samples, Backups
    - File lists with double-click to play
    """
    
    track_play_requested = Signal(str)  # audio path
    back_requested = Signal()  # New signal to propagate back request
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DrillDownPanel")
        self.setStyleSheet(PANEL_STYLE)
        
        self.current_track_id: Optional[int] = None
        self.current_project: Optional[Dict] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = ProjectInfoHeader()
        self.header.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 12px 12px 0 0;")
        self.header.back_requested.connect(self.back_requested)  # Connect signal
        layout.addWidget(self.header)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        
        # Create tabs
        # Create tabs
        self.renders_list = FileTableWidget()
        self.renders_list.file_double_clicked.connect(self.track_play_requested)
        self.tabs.addTab(self.renders_list, get_icon("audio", QColor("#38bdf8"), 16), "Renders")
        
        self.stems_list = FileTableWidget()
        self.stems_list.file_double_clicked.connect(self.track_play_requested)
        self.tabs.addTab(self.stems_list, get_icon("audio", QColor("#a855f7"), 16), "Stems")
        
        self.samples_list = FileTableWidget()
        self.samples_list.file_double_clicked.connect(self.track_play_requested)
        self.tabs.addTab(self.samples_list, get_icon("folder_open", QColor("#facc15"), 16), "Samples")
        
        self.backups_list = FileTableWidget()
        self.backups_list.file_double_clicked.connect(self._open_backup)
        self.tabs.addTab(self.backups_list, get_icon("folder_open", QColor("#22c55e"), 16), "Backups")
    
    def set_track(self, track_id: int):
        """Load project details for a track."""
        self.current_track_id = track_id
        
        track_data = get_track_by_id(track_id)
        if not track_data:
            self.clear()
            return
        
        self.current_project = track_data
        
        # Update header
        self.header.set_project(track_data)
        
        # Load file lists
        project_path = track_data.get('project_path', '')
        
        # Renders (audio files in project root)
        if project_path and os.path.isdir(project_path):
            self.renders_list.set_folder(project_path)
        else:
            self.renders_list.set_folder(None)
        
        # Stems
        stems_dir = track_data.get('stems_dir')
        self.stems_list.set_folder(stems_dir)
        
        # Samples
        samples_dir = track_data.get('samples_dir')
        self.samples_list.set_folder(samples_dir)
        
        # Backups (FLP files)
        backup_dir = track_data.get('backup_dir')
        self.backups_list.set_folder(backup_dir, extensions={'.flp'})
    
    def clear(self):
        """Clear the panel."""
        self.current_track_id = None
        self.current_project = None
        self.header.clear_project()
        self.renders_list.clear()
        self.stems_list.clear()
        self.samples_list.clear()
        self.backups_list.clear()
    
    def _open_backup(self, path: str):
        """Open a backup FLP file."""
        try:
            os.startfile(path)
        except Exception as e:
            logger.error(f"Failed to open backup FLP: {e}")
            QMessageBox.warning(self, "Error", f"Could not open file:\n{e}")


# =============================================================================
# Compact Info Card (for sidebar)
# =============================================================================

class TrackInfoCard(QFrame):
    """
    A compact info card showing current track details.
    
    Displays: Title, Project, BPM, Key, Duration, Tags
    """
    
    edit_requested = Signal(int)  # track_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.track_id: Optional[int] = None
        
        self.setStyleSheet("""
            TrackInfoCard {
                background: #1e2836;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Title
        self.title_label = QLabel("No track selected")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # Project
        self.project_label = QLabel("")
        self.project_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(self.project_label)
        
        # Metadata grid
        self.meta_grid = QGridLayout()
        self.meta_grid.setSpacing(8)
        layout.addLayout(self.meta_grid)
        
        # BPM
        self.bpm_label = QLabel("--")
        self._add_meta_row(0, "BPM", self.bpm_label)
        
        # Key
        self.key_label = QLabel("--")
        self._add_meta_row(1, "Key", self.key_label)
        
        # Duration
        self.duration_label = QLabel("--")
        self._add_meta_row(0, "Duration", self.duration_label, col=2)
        
        # Tags
        self.tags_label = QLabel("")
        self.tags_label.setWordWrap(True)
        self.tags_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.tags_label)
        
        layout.addStretch()
        
        # Edit button
        edit_btn = QPushButton(" Edit Metadata")
        edit_btn.setIcon(get_icon("edit", QColor("#94a3b8"), 16))
        edit_btn.setStyleSheet(BUTTON_STYLE)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.track_id) if self.track_id else None)
        layout.addWidget(edit_btn)
    
    def _add_meta_row(self, row: int, label_text: str, value_label: QLabel, col: int = 0):
        """Add a metadata row to the grid."""
        label = QLabel(label_text)
        label.setStyleSheet("color: #64748b; font-size: 11px;")
        value_label.setStyleSheet("color: #f1f5f9; font-weight: 500;")
        self.meta_grid.addWidget(label, row, col)
        self.meta_grid.addWidget(value_label, row, col + 1)
    
    def set_track(self, track_id: int):
        """Set track to display."""
        self.track_id = track_id
        track = get_track_by_id(track_id)
        
        if not track:
            self.clear()
            return
        
        self.title_label.setText(track.get('title', 'Unknown'))
        self.project_label.setText(f"{track.get('project_name', 'Unknown')}")
        
        # BPM
        bpm = track.get('bpm_user') or track.get('bpm_detected')
        self.bpm_label.setText(f"{int(bpm)}" if bpm else "--")
        
        # Key
        key = track.get('key_user') or track.get('key_detected')
        self.key_label.setText(key if key else "--")
        
        # Duration
        duration = track.get('duration', 0)
        if duration:
            mins = int(duration // 60)
            secs = int(duration % 60)
            self.duration_label.setText(f"{mins}:{secs:02d}")
        else:
            self.duration_label.setText("--")
        
        # Tags
        genre = track.get('genre', '')
        self.tags_label.setText(f"{genre}" if genre else "")
    
    def clear(self):
        """Clear the display."""
        self.track_id = None
        self.title_label.setText("No track selected")
        self.project_label.setText("")
        self.bpm_label.setText("--")
        self.key_label.setText("--")
        self.duration_label.setText("--")
        self.tags_label.setText("")
