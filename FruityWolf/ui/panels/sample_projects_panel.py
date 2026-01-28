"""
Sample Projects Panel

Shows a list of projects that use a specific sample.
Used in the right sidebar for dynamic discovery.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ...database import query
from ...utils import get_icon

class SampleProjectsPanel(QWidget):
    """Side panel for displaying projects using a specific sample."""
    
    project_clicked = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample_name = None
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
        self.header_label = QLabel("SAMPLE DISCOVERY")
        self.header_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #38bdf8; letter-spacing: 1.5px;")
        self.main_layout.addWidget(self.header_label)
        
        self.sample_label = QLabel("--")
        self.sample_label.setStyleSheet("font-size: 14px; color: #f1f5f9; font-weight: 700; margin-bottom: 8px;")
        self.sample_label.setWordWrap(True)
        self.main_layout.addWidget(self.sample_label)
        
        self.line = QFrame()
        self.line.setFixedHeight(1)
        self.line.setStyleSheet("background-color: rgba(51, 65, 85, 0.5);")
        self.main_layout.addWidget(self.line)
        
        self.projects_layout = QVBoxLayout()
        self.projects_layout.setSpacing(8)
        self.main_layout.addLayout(self.projects_layout)
        
        self.main_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
    def set_sample(self, sample_name: str):
        """Fetch projects using this sample and display them."""
        self.sample_name = sample_name
        self.sample_label.setText(sample_name)
        
        # Clear existing
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not sample_name:
            return
            
        # Query projects
        rows = query(
            """SELECT p.* FROM projects p
               JOIN project_samples ps ON p.id = ps.project_id
               WHERE ps.sample_name = ?
               ORDER BY p.updated_at DESC""",
            (sample_name,)
        )
        
        if not rows:
            lbl = QLabel("No other projects found.")
            lbl.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
            self.projects_layout.addWidget(lbl)
            return
            
        count_lbl = QLabel(f"Found in {len(rows)} projects:")
        count_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.projects_layout.addWidget(count_lbl)
        
        for row in rows:
            proj = dict(row)
            btn = QPushButton(f" {proj['name']}")
            btn.setIcon(get_icon("folder", QColor("#94a3b8"), 14))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 41, 59, 0.4);
                    border: 1px solid #334155;
                    border-radius: 8px;
                    color: #e2e8f0;
                    text-align: left;
                    padding: 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.1);
                    border-color: #38bdf8;
                    color: #38bdf8;
                }
            """)
            btn.clicked.connect(lambda p=proj: self.project_clicked.emit(p))
            self.projects_layout.addWidget(btn)
            
    def clear(self):
        self.sample_name = None
        self.sample_label.setText("--")
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
