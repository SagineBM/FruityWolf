"""
Plugin Intelligence View

A professional dashboard for analyzing VST usage, tracking project dependencies,
and identifying unused system plugins.

Features:
- Quick stats overview (total, effects, generators, native, VST)
- Search and filter plugins
- Category tabs (All, Effects, Generators, Native, VST, Unused)
- Top plugins with usage visualization
- Click to view projects using a plugin
- No horizontal scrolling - fully responsive
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .panels.plugins_panel import PluginAnalyticsPanel
from .design_system import DesignTokens
from ..utils import get_icon


class PluginIntelligenceView(QWidget):
    """Main view for plugin analytics and management."""
    
    plugin_selected = Signal(str)  # Emits plugin name to show projects using it
    system_scan_requested = Signal()  # Request system-wide plugin scan

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {DesignTokens.BG_MAIN};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        
        # =========================================
        # HERO HEADER
        # =========================================
        header = QHBoxLayout()
        header.setSpacing(16)
        
        # Title section
        title_section = QVBoxLayout()
        title_section.setSpacing(4)
        
        # Icon + Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        
        icon_label = QLabel()
        icon_label.setPixmap(get_icon("tuning-2", QColor("#38bdf8"), 32).pixmap(32, 32))
        title_row.addWidget(icon_label)
        
        title = QLabel("Plugin Intelligence")
        title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: {DesignTokens.TEXT_PRIMARY};
            letter-spacing: -1px;
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        
        title_section.addLayout(title_row)
        
        subtitle = QLabel("See which projects are safe to open and why others might break")
        subtitle.setStyleSheet(f"color: {DesignTokens.TEXT_SECONDARY}; font-size: 14px;")
        title_section.addWidget(subtitle)
        
        header.addLayout(title_section)
        header.addStretch()
        
        layout.addLayout(header)
        
        # =========================================
        # ANALYTICS PANEL (Main Content)
        # =========================================
        self.analytics_panel = PluginAnalyticsPanel()
        self.analytics_panel.plugin_clicked.connect(self.plugin_selected)
        self.analytics_panel.system_scan_requested.connect(self.system_scan_requested)
        layout.addWidget(self.analytics_panel, 1)

    def refresh(self):
        """Refresh the plugin analytics data."""
        self.analytics_panel.refresh()
