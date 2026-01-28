"""
Sample Intelligence View (Insights)

A cinematic dashboard showing library-wide sample intelligence, 
health metrics, and usage-based insights.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QScrollArea, QGridLayout, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from ..core.stats_service import StatsService
from ..utils import get_icon
from .design_system import DesignTokens, BaseCard

class HealthChip(QFrame):
    """Small chip showing library health status."""
    def __init__(self, status: str, score: float, parent=None):
        super().__init__(parent)
        color = DesignTokens.ACCENT_SUCCESS
        if status == "Critical": color = DesignTokens.ACCENT_DANGER
        elif status == "Warning": color = DesignTokens.ACCENT_WARNING
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {color}22;
                border: 1px solid {color}44;
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QLabel {{
                color: {color};
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        self.label = QLabel(f"{status} • {int(score)}%")
        layout.addWidget(self.label)

class InsightItem(QPushButton):
    """Row item for overused/underused lists."""
    clicked_sample = Signal(str)
    play_requested = Signal(str)

    def __init__(self, data: dict, type: str = "usage", parent=None):
        super().__init__(parent)
        self.sample_id = data['id']
        self.sample_path = data.get('path')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border-radius: 8px;
                padding: 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {DesignTokens.BG_PANEL_HOVER};
            }}
            QLabel#Name {{ color: {DesignTokens.TEXT_PRIMARY}; font-weight: 500; font-size: 13px; }}
            QLabel#Meta {{ color: {DesignTokens.TEXT_MUTED}; font-size: 11px; }}
        """)
        
        layout = QHBoxLayout(self)
        
        # Play Button
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setIcon(get_icon("play", QColor(DesignTokens.ACCENT_PRIMARY), 18))
        self.play_btn.setStyleSheet(f"background: rgba(255,255,255,0.05); border-radius: 16px; border: none;")
        self.play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.play_btn)
        
        info = QVBoxLayout()
        name = QLabel(data['name'])
        name.setObjectName("Name")
        info.addWidget(name)
        
        meta_text = ""
        if type == "usage":
            meta_text = f"Used in {data['usage_count']} projects ({data['usage_pct']}%)"
        else:
            meta_text = f"Last used: {data['last_used']}"
            
        meta = QLabel(meta_text)
        meta.setObjectName("Meta")
        info.addWidget(meta)
        layout.addLayout(info)
        layout.addStretch()
        
        arrow = QLabel()
        arrow.setPixmap(get_icon("chevron_right", QColor(DesignTokens.TEXT_MUTED), 16).pixmap(16, 16))
        layout.addWidget(arrow)
        
        self.clicked.connect(lambda: self.clicked_sample.emit(self.sample_id))

    def _on_play_clicked(self):
        if self.sample_path:
            self.play_requested.emit(self.sample_path)

class SampleOverviewView(QWidget):
    """Refined Sample Intelligence dashboard."""
    
    sample_selected = Signal(str) # Stable ID emitted for navigation
    sample_play_requested = Signal(str) # Path emitted for preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_data()
        
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {DesignTokens.BG_MAIN};")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(DesignTokens.L, DesignTokens.L, DesignTokens.L, DesignTokens.L)
        main_layout.setSpacing(DesignTokens.L)
        
        # 1. HERO HEADER
        header = QHBoxLayout()
        title_v = QVBoxLayout()
        title = QLabel("Sample Intelligence")
        title.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {DesignTokens.TEXT_PRIMARY}; letter-spacing: -1px;")
        subtitle = QLabel("Understand which sounds shape your music habitats")
        subtitle.setStyleSheet(f"color: {DesignTokens.TEXT_SECONDARY}; font-size: 14px;")
        title_v.addWidget(title)
        title_v.addWidget(subtitle)
        header.addLayout(title_v)
        
        header.addStretch()
        
        self.health_container = QHBoxLayout()
        header.addLayout(self.health_container)
        
        main_layout.addLayout(header)
        
        # Scrollable Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(DesignTokens.L)
        
        # 2. KEY METRICS ROW
        self.metrics_layout = QHBoxLayout()
        self.metrics_layout.setSpacing(DesignTokens.M)
        self.content_layout.addLayout(self.metrics_layout)
        
        # 3. INSIGHTS GRID
        sections = QHBoxLayout()
        sections.setSpacing(DesignTokens.L)
        
        # Left: Overused Samples (Risk)
        self.overused_card = BaseCard(hover_effect=False)
        overused_v = QVBoxLayout(self.overused_card)
        overused_v.setContentsMargins(DesignTokens.M, DesignTokens.M, DesignTokens.M, DesignTokens.M)
        
        ov_title = QLabel("OVERUSED SAMPLES")
        ov_title.setStyleSheet(f"color: {DesignTokens.TEXT_MUTED}; font-weight: bold; font-size: 10px; letter-spacing: 1.5px;")
        overused_v.addWidget(ov_title)
        
        self.overused_list = QVBoxLayout()
        overused_v.addLayout(self.overused_list)
        overused_v.addStretch()
        
        sections.addWidget(self.overused_card, 1)
        
        # Right: Underused Gems (Opportunity)
        self.gems_card = BaseCard(hover_effect=False)
        gems_v = QVBoxLayout(self.gems_card)
        gems_v.setContentsMargins(DesignTokens.M, DesignTokens.M, DesignTokens.M, DesignTokens.M)
        
        gems_title = QLabel("UNDERUSED GEMS")
        gems_title.setStyleSheet(f"color: {DesignTokens.TEXT_MUTED}; font-weight: bold; font-size: 10px; letter-spacing: 1.5px;")
        gems_v.addWidget(gems_title)
        
        self.gems_list = QVBoxLayout()
        gems_v.addLayout(self.gems_list)
        gems_v.addStretch()
        
        sections.addWidget(self.gems_card, 1)
        
        self.content_layout.addLayout(sections)
        self.content_layout.addStretch()
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """Fetch versioned stats and update UI."""
        metrics_data = StatsService.get_extended_library_metrics()
        overused_data = StatsService.get_overused_samples()
        gems_data = StatsService.get_underused_gems()
        
        # Update Health Chip
        self._clear_layout(self.health_container)
        health = metrics_data['health']
        self.health_container.addWidget(HealthChip(health['status'], health['score']))
        
        # Update Metrics
        self._clear_layout(self.metrics_layout)
        for m in metrics_data['metrics']:
            card = BaseCard(hover_effect=False)
            card.setMinimumWidth(160)
            v = QVBoxLayout(card)
            
            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon(m['icon'], QColor(m['color']), 20).pixmap(20, 20))
            v.addWidget(icon_lbl)
            
            val = QLabel(m['value'])
            val.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {DesignTokens.TEXT_PRIMARY};")
            v.addWidget(val)
            
            lbl = QLabel(m['label'])
            lbl.setStyleSheet(f"color: {DesignTokens.TEXT_MUTED}; font-size: 11px;")
            v.addWidget(lbl)
            self.metrics_layout.addWidget(card)
            
        # Update Overused
        self._clear_layout(self.overused_list)
        for s in overused_data:
            item = InsightItem(s, type="usage")
            item.clicked_sample.connect(self.sample_selected)
            item.play_requested.connect(self.sample_play_requested)
            self.overused_list.addWidget(item)
            
        # Update Gems
        self._clear_layout(self.gems_list)
        for s in gems_data:
            item = InsightItem(s, type="gems")
            item.clicked_sample.connect(self.sample_selected)
            item.play_requested.connect(self.sample_play_requested)
            self.gems_list.addWidget(item)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
