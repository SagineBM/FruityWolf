"""
Renders Panel
Displays all renders for a project with ability to set primary render.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor

from ...scanner.library_scanner import get_project_renders, set_primary_render
from ...utils import get_icon, format_smart_date, open_file
from ...database import execute
import logging

logger = logging.getLogger(__name__)


class RendersPanel(QWidget):
    """Panel showing all renders for a project."""
    
    render_selected = Signal(dict)  # Emit render data when selected
    primary_changed = Signal(int)  # Emit project_id when primary changes
    
    def __init__(self, project_id: int, project_name: str, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_name = project_name
        self._setup_ui()
        self._load_renders()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(f"Renders: {self.project_name}")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e2e8f0;")
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #94a3b8;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #e2e8f0;
                background-color: #334155;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Filename", "Date", "Duration", "Size", "Actions"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        
        # Style
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                gridline-color: #334155;
            }
            QTableWidget::item {
                padding: 6px;
                color: #e2e8f0;
            }
            QTableWidget::item:selected {
                background-color: #334155;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #334155;
            }
        """)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 100)
        
        layout.addWidget(self.table)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        layout.addWidget(self.info_label)
    
    def _load_renders(self):
        """Load renders for the project."""
        try:
            renders = get_project_renders(self.project_id)
            logger.debug(f"Loaded {len(renders)} renders for project {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to load renders for project {self.project_id}: {e}")
            renders = []
        
        self.table.setRowCount(len(renders))
        
        if len(renders) == 0:
            # Show message if no renders
            self.info_label.setText("No renders found. Renders are audio files in the project root (excluding Audio/, Samples/, Backup/ folders).")
            self.info_label.setStyleSheet("color: #f59e0b; font-size: 11px;")
            return
        
        # Reset info label style
        self.info_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        
        for row, render in enumerate(renders):
            # Filename
            filename_item = QTableWidgetItem(render['filename'])
            filename_item.setData(Qt.ItemDataRole.UserRole, render['id'])
            self.table.setItem(row, 0, filename_item)
            
            # Date
            mtime = render.get('mtime')
            date_str = format_smart_date(mtime) if mtime else "-"
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # Duration
            duration = render.get('duration_s', 0)
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "-"
            self.table.setItem(row, 2, QTableWidgetItem(duration_str))
            
            # Size
            size_bytes = render.get('file_size', 0)
            if size_bytes:
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = "-"
            self.table.setItem(row, 3, QTableWidgetItem(size_str))
            
            # Actions (Set as Primary button)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)
            
            # Check is_primary (can be 0/1 from DB or True/False)
            is_primary_val = render.get('is_primary', 0)
            is_primary = bool(is_primary_val) if isinstance(is_primary_val, (int, bool)) else False
            
            primary_btn = QPushButton("⭐ Set Primary" if not is_primary else "⭐ Primary")
            primary_btn.setEnabled(not is_primary)
            primary_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QPushButton:disabled {
                    background-color: #475569;
                    color: #94a3b8;
                }
            """)
            primary_btn.clicked.connect(lambda checked, r=render: self._set_primary(r['id']))
            actions_layout.addWidget(primary_btn)
            
            open_btn = QPushButton("Open")
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #334155;
                    color: #e2e8f0;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #475569;
                }
            """)
            open_btn.clicked.connect(lambda checked, r=render: open_file(r['path']))
            actions_layout.addWidget(open_btn)
            
            self.table.setCellWidget(row, 4, actions_widget)
        
        # Update info label
        count = len(renders)
        self.info_label.setText(f"{count} render{'s' if count != 1 else ''} found")
    
    def _set_primary(self, render_id: int):
        """Set a render as the primary render."""
        try:
            set_primary_render(self.project_id, render_id)
            self._load_renders()  # Refresh to show updated primary status
            self.primary_changed.emit(self.project_id)
            QMessageBox.information(self, "Primary Render Set", "Primary render has been updated.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set primary render: {e}")
