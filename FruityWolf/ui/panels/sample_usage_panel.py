"""
Sample Usage Panel

Visualizes the top used samples across projects with a custom bar chart.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QScrollArea, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont

from ...utils import get_icon

class SampleBar(QFrame):
    """A custom styled bar for the usage graph."""
    clicked = Signal(str) # Emits sample name

    def __init__(self, name: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.sample_name = name
        self.count = count
        
        self.setObjectName("sampleBar")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)
        
        # Name
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.name_label.setFixedWidth(120)
        layout.addWidget(self.name_label)
        
        # Bar Container
        self.bar_container = QFrame()
        self.bar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.bar_container.setFixedHeight(8)
        self.bar_container.setStyleSheet("background: #1e293b; border-radius: 4px;")
        
        bar_layout = QHBoxLayout(self.bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Actual Bar Fill
        self.fill = QFrame()
        self.fill.setFixedHeight(8)
        # Gradient or solid color
        percentage = (count / max_count) * 100 if max_count > 0 else 0
        self.fill.setFixedWidth(int(200 * (percentage / 100))) # Base width for visual
        
        # Color based on frequency?
        color = "#38bdf8" # Sky blue
        if percentage > 80: color = "#22c55e" # Green
        elif percentage < 30: color = "#64748b" # Slate
        
        self.fill.setStyleSheet(f"background: {color}; border-radius: 4px;")
        bar_layout.addWidget(self.fill)
        bar_layout.addStretch()
        
        layout.addWidget(self.bar_container)
        
        # Count
        self.count_label = QLabel(str(count))
        self.count_label.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        self.count_label.setFixedWidth(24)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.count_label)
        
        self.setStyleSheet("""
            #sampleBar:hover {
                background: rgba(56, 189, 248, 0.1);
                border-radius: 4px;
            }
        """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.sample_name)

class SampleUsagePanel(QWidget):
    """Panel showing the top sample usage graph."""
    filter_requested = Signal(str) # Emits sample name to filter projects

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(16, 8, 16, 0)
        
        title = QLabel("SAMPLE USAGE")
        title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; letter-spacing: 1.5px;")
        header.addWidget(title)
        header.addStretch()
        
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(get_icon("refresh", QColor("#94a3b8"), 14))
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.setStyleSheet("background: transparent; border: none;")
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Scroll Area for the list of bars
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.bars_layout = QVBoxLayout(self.container)
        self.bars_layout.setContentsMargins(12, 4, 12, 12)
        self.bars_layout.setSpacing(4)
        self.bars_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        self.setStyleSheet("background: #0f172a; border-left: 1px solid #1e293b;")
        self.setFixedWidth(320)

    def set_data(self, samples: list):
        """Update the graph with new data."""
        # Clear existing
        while self.bars_layout.count() > 1: # Keep the stretch
            item = self.bars_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not samples:
             empty = QLabel("No sample data available.\nRun a library scan.")
             empty.setStyleSheet("color: #64748b; font-size: 11px; padding: 20px;")
             empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
             self.bars_layout.insertWidget(0, empty)
             return

        max_count = max(s['count'] for s in samples) if samples else 0
        
        for s in samples:
            bar = SampleBar(s['sample_name'], s['count'], max_count)
            bar.clicked.connect(self.filter_requested.emit)
            self.bars_layout.insertWidget(self.bars_layout.count() - 1, bar)
