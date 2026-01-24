"""
Project Details Panel

Displays detailed information for FL Studio Projects (Projects View).
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QGroupBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ...utils import get_icon, format_smart_date, get_placeholder_cover
from ...classifier.engine import ProjectState

class ProjectDetailsPanel(QWidget):
    """Side panel for displaying Project details."""
    
    open_folder_clicked = Signal(str)
    open_flp_clicked = Signal(str)
    rescan_clicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
        # Icon / Placeholder
        # Detailed projects don't usually have "cover art" unless we implement screenshotting later.
        # For now, a large stylized icon or placeholder.
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #1e293b;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Titles
        self.title_label = QLabel("Select a project")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)
        
        self.date_label = QLabel("")
        self.date_label.setStyleSheet("font-size: 13px; color: #64748b;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.date_label)
        
        # Status / Score Section
        self.status_group = QGroupBox("STATUS")
        self.status_layout = QVBoxLayout(self.status_group)
        self.status_layout.setSpacing(12)
        
        # Project State Badge (Pill)
        self.state_label = QLabel("Unknown")
        self.state_label.setStyleSheet("""
            background-color: #1e293b; 
            color: #f1f5f9; 
            border-radius: 12px; 
            padding: 4px 12px;
            font-weight: bold;
        """)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setFixedHeight(28)
        self.status_layout.addWidget(self.state_label)
        
        # Score Bar
        score_row = QHBoxLayout()
        score_lbl = QLabel("Score")
        score_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        score_row.addWidget(score_lbl)
        
        self.score_val = QLabel("0")
        self.score_val.setStyleSheet("color: #f1f5f9; font-weight: bold;")
        score_row.addWidget(self.score_val)
        score_row.addStretch()
        self.status_layout.addLayout(score_row)
        
        self.score_bar = QProgressBar()
        self.score_bar.setTextVisible(False)
        self.score_bar.setFixedHeight(6)
        self.score_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 3px;
            }
        """)
        self.status_layout.addWidget(self.score_bar)
        
        self.main_layout.addWidget(self.status_group)
        
        # Stats Grid
        self.stats_group = QGroupBox("CONTENTS")
        self.stats_layout = QGridLayout(self.stats_group)
        
        self.audio_count_label = self._add_stat("Audio Files", 0, 0)
        self.backup_count_label = self._add_stat("Backups", 0, 1)
        self.size_label = self._add_stat("Size", 1, 0)
        
        self.main_layout.addWidget(self.stats_group)
        
        self.main_layout.addStretch()
        
        # Actions
        self.actions_layout = QVBoxLayout()
        self.actions_layout.setSpacing(8)
        
        self.btn_folder = QPushButton(" Open Folder")
        self.btn_folder.setIcon(get_icon("folder_open", QColor("#94a3b8"), 16))
        self.btn_folder.setStyleSheet(self._btn_style())
        self.btn_folder.clicked.connect(self._on_open_folder)
        self.actions_layout.addWidget(self.btn_folder)
        
        self.btn_flp = QPushButton(" Open FLP")
        self.btn_flp.setIcon(get_icon("fl_studio", QColor("#94a3b8"), 16))
        self.btn_flp.setStyleSheet(self._btn_style())
        self.btn_flp.clicked.connect(self._on_open_flp)
        self.actions_layout.addWidget(self.btn_flp)
        
        self.main_layout.addLayout(self.actions_layout)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
    def _add_stat(self, label, row, col):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)
        
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        vbox.addWidget(lbl)
        
        val = QLabel("0")
        val.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: 500;")
        vbox.addWidget(val)
        
        self.stats_layout.addWidget(container, row, col)
        return val
        
    def _btn_style(self):
        return """
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 8px;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #0f172a;
            }
            QPushButton:disabled {
                color: #475569;
                background-color: #0f172a;
                border: 1px solid #1e293b;
            }
        """

    def set_project(self, project: dict):
        """Display project data."""
        self.current_project = project
        if not project:
            self.clear()
            return
            
        # Placeholder Icon
        self.cover_label.setPixmap(get_placeholder_cover(200, project.get('name', ''), is_project=True))
            
        self.title_label.setText(project.get('name', 'Unknown Project'))
        self.date_label.setText(format_smart_date(project.get('updated_at', 0)))
        
        # State
        state = project.get('state', 'Unknown')
        self.state_label.setText(state.replace("_", " ").title().replace("Or", "/"))
        self.state_label.setStyleSheet(f"""
            background-color: {self._get_state_color_hex(state)}33; 
            color: {self._get_state_color_hex(state)}; 
            border-radius: 12px; 
            padding: 4px 12px;
            font-weight: bold;
            border: 1px solid {self._get_state_color_hex(state)}66;
        """)
        
        # Score
        score = project.get('render_priority_score', 0)
        self.score_val.setText(str(score))
        self.score_bar.setValue(score)
        
        # Color score bar
        if score > 70:
            color = "#22c55e"
        elif score > 40:
            color = "#f59e0b"
        else:
            color = "#64748b"
            
        self.score_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1e293b;
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        
        # Stats
        # Need to check what fields we have
        # Assuming we might have count fields, otherwise placeholders
        self.size_label.setText(f"{project.get('flp_size_kb', 0)} KB")
        self.backup_count_label.setText(str(project.get('backup_count', '-')))
        # Audio count isn't always in project summary dict, might need separate query or assume 0
        self.audio_count_label.setText("-") 
        
        # Actions
        flp_path = project.get('flp_path')
        self.btn_flp.setEnabled(bool(flp_path) and os.path.exists(flp_path))
        self.btn_folder.setEnabled(bool(project.get('path')))
        
    def clear(self):
        self.current_project = None
        self.title_label.setText("Select a project")
        self.date_label.setText("")
        self.state_label.setText("Unknown")
        self.score_val.setText("0")
        self.score_bar.setValue(0)
        self.size_label.setText("0 KB")
        self.backup_count_label.setText("0")
        self.btn_flp.setEnabled(False)
        self.btn_folder.setEnabled(False)
        
    def _get_state_color_hex(self, state: str) -> str:
        map_ = {
            ProjectState.MICRO_IDEA: "#94a3b8",
            ProjectState.IDEA: "#38bdf8",
            ProjectState.WIP: "#f59e0b",
            ProjectState.PREVIEW_READY: "#22c55e",
            ProjectState.ADVANCED: "#a855f7",
            ProjectState.BROKEN_OR_EMPTY: "#ef4444",
        }
        return map_.get(state, "#f1f5f9")

    def _on_open_folder(self):
        if self.current_project and self.current_project.get('path'):
            self.open_folder_clicked.emit(self.current_project.get('path'))

    def _on_open_flp(self):
        if self.current_project and self.current_project.get('flp_path'):
            self.open_flp_clicked.emit(self.current_project.get('flp_path'))
