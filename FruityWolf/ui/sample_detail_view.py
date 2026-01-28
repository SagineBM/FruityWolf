"""
Sample Detail View

Deep-dive into a specific sample's usage, history, and impact.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QScrollArea, QSizePolicy, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..core.stats_service import StatsService
from ..utils import get_icon, format_smart_date
from .design_system import DesignTokens, BaseCard

class TimelineWidget(QWidget):
    """Adaptive dot-strip timeline."""
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data # timeline view-model
        self.setFixedHeight(120)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Track line
        w = self.width()
        h = self.height()
        mid_y = h // 2
        
        pen = QPen(QColor(DesignTokens.TEXT_MUTED))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(40, mid_y, w - 40, mid_y)
        
        if not self.data or not self.data.get('events'):
            return
            
        events = self.data['events']
        min_ts = min(e['ts'] for e in events)
        max_ts = max(e['ts'] for e in events)
        ts_range = max_ts - min_ts if max_ts > min_ts else 1
        
        # Draw dots
        for e in events:
            # Map ts to x
            rel_x = (e['ts'] - min_ts) / ts_range
            x = 40 + int(rel_x * (w - 80))
            
            # Color based on stage
            color = QColor(DesignTokens.ACCENT_PRIMARY)
            if "WIP" in e['stage']: color = QColor(DesignTokens.ACCENT_WARNING)
            elif "FINISHED" in e['stage']: color = QColor(DesignTokens.ACCENT_SUCCESS)
            
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x - 6, mid_y - 6, 12, 12)
            
            # Hover/Tooltip logic usually better handled by actual child widgets, 
            # but for a simple visual strip this works. 
            # In a real pro UI, these dots would be custom QPushButtons or similar if interactive.

class SampleDetailView(QWidget):
    """Deep-dive page for a specific sample."""
    
    back_requested = Signal()
    project_requested = Signal(int) # Emit project_id to open
    sample_play_requested = Signal(str) # Emit path
    render_play_requested = Signal(str) # Emit path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_sample_id = None
        self.current_sample_path = None
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {DesignTokens.BG_MAIN};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(DesignTokens.L, DesignTokens.L, DesignTokens.L, DesignTokens.L)
        layout.setSpacing(DesignTokens.L)
        
        # --- HEADER (Back + Name + Health) ---
        header = QHBoxLayout()
        back_btn = QPushButton()
        back_btn.setIcon(get_icon("chevron_left", QColor(DesignTokens.TEXT_PRIMARY), 24))
        back_btn.setFixedSize(40, 40)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"background: {DesignTokens.BG_PANEL}; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);")
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)
        
        header.addSpacing(DesignTokens.M)
        
        # Play Main Sample Button
        self.hero_play_btn = QPushButton()
        self.hero_play_btn.setFixedSize(48, 48)
        self.hero_play_btn.setIcon(get_icon("play", QColor(DesignTokens.ACCENT_PRIMARY), 24))
        self.hero_play_btn.setStyleSheet(f"background: {DesignTokens.BG_PANEL}; border-radius: 24px; border: 2px solid {DesignTokens.ACCENT_PRIMARY}44;")
        self.hero_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hero_play_btn.clicked.connect(self._on_hero_play_clicked)
        header.addWidget(self.hero_play_btn)

        header.addSpacing(DesignTokens.M)
        
        title_v = QVBoxLayout()
        self.name_lbl = QLabel("--")
        self.name_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {DesignTokens.TEXT_PRIMARY};")
        self.meta_lbl = QLabel("--")
        self.meta_lbl.setStyleSheet(f"color: {DesignTokens.TEXT_MUTED}; font-size: 13px;")
        title_v.addWidget(self.name_lbl)
        title_v.addWidget(self.meta_lbl)
        header.addLayout(title_v)
        
        header.addStretch()
        
        self.health_card = BaseCard(hover_effect=False)
        self.health_card.setFixedSize(100, 80)
        health_v = QVBoxLayout(self.health_card)
        self.health_score = QLabel("--")
        self.health_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.health_score.setStyleSheet(f"font-size: 28px; font-weight: 900; color: {DesignTokens.ACCENT_PRIMARY};")
        health_v.addWidget(self.health_score)
        health_lbl = QLabel("HEALTH")
        health_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        health_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DesignTokens.TEXT_MUTED};")
        health_v.addWidget(health_lbl)
        header.addWidget(self.health_card)
        
        layout.addLayout(header)
        
        # Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(DesignTokens.L)
        
        # 1. TIMELINE
        self.timeline_card = BaseCard(hover_effect=False)
        timeline_v = QVBoxLayout(self.timeline_card)
        tl_title = QLabel("PROJECT IMPACT TIMELINE")
        tl_title.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DesignTokens.TEXT_MUTED}; letter-spacing: 1.5px;")
        timeline_v.addWidget(tl_title)
        
        self.timeline_container = QVBoxLayout()
        timeline_v.addLayout(self.timeline_container)
        
        self.content_layout.addWidget(self.timeline_card)
        
        # 2. MIDDLE ROW (Table + Insights)
        mid_row = QHBoxLayout()
        mid_row.setSpacing(DesignTokens.L)
        
        # Projects Table
        self.projects_card = BaseCard(hover_effect=False)
        proj_v = QVBoxLayout(self.projects_card)
        proj_title = QLabel("INVOLVED PROJECTS")
        proj_title.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DesignTokens.TEXT_MUTED}; letter-spacing: 1.5px;")
        proj_v.addWidget(proj_title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Project Name", "Stage", "Modified", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 40)
        self.table.setStyleSheet(f"""
            QTableWidget {{ 
                background: transparent; border: none; gridline-color: rgba(255,255,255,0.05); 
                color: {DesignTokens.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background: transparent; border: none; color: {DesignTokens.TEXT_MUTED}; 
                font-size: 10px; font-weight: bold;
            }}
        """)
        self.table.verticalHeader().hide()
        proj_v.addWidget(self.table)
        
        mid_row.addWidget(self.projects_card, 2)
        
        # Insights
        self.insights_card = BaseCard(hover_effect=False)
        self.insights_v = QVBoxLayout(self.insights_card)
        in_title = QLabel("HEURISTIC INSIGHTS")
        in_title.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DesignTokens.TEXT_MUTED}; letter-spacing: 1.5px;")
        self.insights_v.addWidget(in_title)
        self.insights_container = QVBoxLayout()
        self.insights_v.addLayout(self.insights_container)
        self.insights_v.addStretch()
        
        mid_row.addWidget(self.insights_card, 1)
        
        self.content_layout.addLayout(mid_row)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_hero_play_clicked(self):
        if self.current_sample_path:
            self.sample_play_requested.emit(self.current_sample_path)

    def set_sample(self, sample_id: str):
        """Load and display sample data."""
        self.current_sample_id = sample_id
        data = StatsService.get_sample_detail(sample_id)
        
        if "error" in data:
            self.name_lbl.setText("Sample Not Found")
            return
            
        hero = data['hero']
        self.name_lbl.setText(hero['name'])
        self.meta_lbl.setText(f"Used in {hero['usage_count']} projects • First used {hero['first_used']}")
        self.current_sample_path = hero.get('path')
        self.hero_play_btn.setEnabled(bool(self.current_sample_path))
        
        self.health_score.setText(str(data['health_score']))
        color = DesignTokens.ACCENT_PRIMARY
        if data['health_score'] < 50: color = DesignTokens.ACCENT_DANGER
        elif data['health_score'] < 80: color = DesignTokens.ACCENT_WARNING
        self.health_score.setStyleSheet(f"font-size: 28px; font-weight: 900; color: {color};")
        
        # Update Timeline
        self._clear_layout(self.timeline_container)
        self.timeline_container.addWidget(TimelineWidget(data['timeline']))
        
        # Update Table
        self.table.setRowCount(len(data['projects']))
        for i, p in enumerate(data['projects']):
            self.table.setItem(i, 0, QTableWidgetItem(p['name']))
            self.table.setItem(i, 1, QTableWidgetItem(p['stage'].replace("_", " ")))
            self.table.setItem(i, 2, QTableWidgetItem(p['date']))
            
            # Play render button
            if p.get('render_path'):
                btn = QPushButton()
                btn.setFixedSize(24, 24)
                btn.setIcon(get_icon("play", QColor(DesignTokens.ACCENT_SECONDARY), 14))
                btn.setStyleSheet("background: rgba(255,255,255,0.05); border: none; border-radius: 12px;")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                # Capture current path in closure
                path = p['render_path']
                btn.clicked.connect(lambda checked=False, p=path: self.render_play_requested.emit(p))
                self.table.setCellWidget(i, 3, btn)
            
        # Update Insights
        self._clear_layout(self.insights_container)
        for ins in data['insights']:
            lbl = QLabel(ins['text'])
            color = DesignTokens.TEXT_PRIMARY
            if ins['type'] == "warning": color = DesignTokens.ACCENT_WARNING
            elif ins['type'] == "danger": color = DesignTokens.ACCENT_DANGER
            lbl.setStyleSheet(f"color: {color}; font-size: 12px; padding: 4px; background: rgba(255,255,255,0.03); border-radius: 4px;")
            lbl.setWordWrap(True)
            self.insights_container.addWidget(lbl)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
