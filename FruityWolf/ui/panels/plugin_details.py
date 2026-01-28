"""
Plugin Details Panel
Shows projects using a specific plugin with quick actions.
"""

import logging
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ...database import query
from ...utils import get_icon, format_smart_date

logger = logging.getLogger(__name__)

class PluginDetailsPanel(QWidget):
    """Side panel for displaying projects using a specific plugin."""
    
    project_clicked = Signal(dict)
    play_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugin_name = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("QWidget { background: transparent; }")
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("QWidget { background: transparent; }")
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)
        
        # Header
        self.header_label = QLabel("PLUGIN DETAILS")
        self.header_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #38bdf8; letter-spacing: 1.5px;")
        self.main_layout.addWidget(self.header_label)
        
        self.name_label = QLabel("--")
        self.name_label.setStyleSheet("font-size: 18px; color: #f1f5f9; font-weight: 800; margin-bottom: 8px;")
        self.name_label.setWordWrap(True)
        self.main_layout.addWidget(self.name_label)
        
        self.line = QFrame()
        self.line.setFixedHeight(1)
        self.line.setStyleSheet("background-color: rgba(51, 65, 85, 0.5);")
        self.main_layout.addWidget(self.line)
        
        # Project List
        self.projects_layout = QVBoxLayout()
        self.projects_layout.setSpacing(8)
        self.main_layout.addLayout(self.projects_layout)
        
        self.main_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
    def set_plugin(self, plugin_name: str):
        """Fetch projects using this plugin and display them."""
        self.plugin_name = plugin_name
        self.name_label.setText(plugin_name)
        
        # Clear existing
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not plugin_name:
            return
            
        # Query projects from the project_plugins table, joining tracks to see if renders exist
        rows = query(
            """SELECT p.*, 
                      (SELECT COUNT(*) FROM tracks t WHERE t.project_id = p.id AND t.ext != '.flp') as render_count
               FROM projects p
               JOIN project_plugins pp ON p.id = pp.project_id
               WHERE pp.plugin_name = ?
               GROUP BY p.id
               ORDER BY p.updated_at DESC""",
            (plugin_name,)
        )
        
        if not rows:
            lbl = QLabel("No projects found using this plugin.")
            lbl.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
            self.projects_layout.addWidget(lbl)
            return
            
        count_lbl = QLabel(f"Used in {len(rows)} projects:")
        count_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; margin-top: 8px;")
        self.projects_layout.addWidget(count_lbl)
        
        self.current_projects_list = []
        for row in rows:
            proj = dict(row)
            self.current_projects_list.append(proj)
            self._add_project_card(proj)
            
    def _add_project_card(self, project: dict):
        """Create a compact card for a project with actions."""
        has_render = project.get('render_count', 0) > 0
        
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(30, 41, 59, 0.4);
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
            }}
            QFrame:hover {{
                background-color: {"rgba(51, 65, 85, 0.4)" if has_render else "rgba(30, 41, 59, 0.4)"};
                border-color: {"#475569" if has_render else "#334155"};
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)
        
        # Top Row: Title + Date
        top_row = QHBoxLayout()
        name_lbl = QLabel(project['name'])
        name_lbl.setStyleSheet("font-weight: bold; color: #f1f5f9; font-size: 13px; border: none; background: transparent;")
        name_lbl.setWordWrap(True)
        top_row.addWidget(name_lbl, 1)
        
        date_lbl = QLabel(format_smart_date(project.get('updated_at', 0)))
        date_lbl.setStyleSheet("color: #64748b; font-size: 10px; border: none; background: transparent;")
        top_row.addWidget(date_lbl)
        card_layout.addLayout(top_row)
        
        # Actions Row
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 4, 0, 0)
        
        # Play Button (Preview) - Only show if render exists
        if has_render:
            btn_play = QPushButton(" Preview")
            btn_play.setFixedHeight(28)
            btn_play.setIcon(get_icon("play", QColor("#38bdf8"), 14))
            btn_play.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    color: #e2e8f0;
                    font-size: 11px;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    border-color: #38bdf8;
                    color: #38bdf8;
                }
            """)
            btn_play.clicked.connect(lambda: self.play_requested.emit(project))
            actions.addWidget(btn_play)
        else:
            no_render_lbl = QLabel("No Render")
            no_render_lbl.setStyleSheet("color: #475569; font-size: 10px; font-style: italic;")
            actions.addWidget(no_render_lbl)
        
        # Explore Button
        btn_view = QPushButton(" Explore")
        btn_view.setFixedHeight(28)
        btn_view.setIcon(get_icon("eye", QColor("#94a3b8"), 14))
        btn_view.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94a3b8;
                font-size: 11px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background-color: rgba(51, 65, 85, 0.4);
                color: #f1f5f9;
                border-color: #475569;
            }
        """)
        btn_view.clicked.connect(lambda: self.project_clicked.emit(project))
        actions.addWidget(btn_view)
        actions.addStretch()
        
        card_layout.addLayout(actions)
        self.projects_layout.addWidget(card)

    def clear(self):
        self.plugin_name = None
        self.name_label.setText("--")
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
