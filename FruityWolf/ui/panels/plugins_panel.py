"""
Enhanced Plugins Panel - Optimized Version

Professional plugin analytics dashboard for producers.
Uses QTableWidget for performance instead of custom widgets.
"""

import logging
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QScrollArea, QLineEdit, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor

from ...database import query
from ...utils import get_icon

logger = logging.getLogger(__name__)


# =============================================================================
# Design Tokens
# =============================================================================

class Colors:
    BG_DARK = "#0f172a"
    BG_CARD = "#1e293b"
    BG_CARD_HOVER = "#334155"
    
    ACCENT_PRIMARY = "#38bdf8"
    ACCENT_EFFECT = "#22d3ee"
    ACCENT_GENERATOR = "#a855f7"
    ACCENT_NATIVE = "#f59e0b"
    ACCENT_VST = "#3b82f6"
    
    TEXT_PRIMARY = "#f1f5f9"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED = "#64748b"
    
    BORDER = "#334155"


TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {Colors.BG_CARD};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
        gridline-color: transparent;
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: rgba(56, 189, 248, 0.15);
    }}
    QTableWidget::item {{
        padding: 10px 8px;
        border-bottom: 1px solid rgba(51, 65, 85, 0.3);
    }}
    QTableWidget::item:selected {{
        background-color: rgba(56, 189, 248, 0.15);
    }}
    QTableWidget::item:hover {{
        background-color: rgba(51, 65, 85, 0.3);
    }}
    QHeaderView::section {{
        background-color: {Colors.BG_CARD};
        color: {Colors.TEXT_MUTED};
        padding: 12px 8px;
        border: none;
        border-bottom: 1px solid {Colors.BORDER};
        font-weight: 700;
        font-size: 11px;
    }}
"""

SEARCH_STYLE = f"""
    QLineEdit {{
        background: {Colors.BG_DARK};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
        padding: 10px 14px;
        color: {Colors.TEXT_PRIMARY};
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border-color: {Colors.ACCENT_PRIMARY};
    }}
"""

TAB_STYLE = f"""
    QPushButton {{
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: {Colors.TEXT_SECONDARY};
        padding: 10px 14px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        color: {Colors.TEXT_PRIMARY};
    }}
    QPushButton:checked {{
        color: {Colors.ACCENT_PRIMARY};
        border-bottom-color: {Colors.ACCENT_PRIMARY};
    }}
"""


# =============================================================================
# Stat Card Widget - Unified clean design
# =============================================================================

class StatCard(QFrame):
    """A unified statistics card - clean design without inner borders."""
    
    clicked = Signal()
    
    def __init__(self, title: str, value: str = "0", accent: str = Colors.ACCENT_PRIMARY, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(70)
        self.setMaximumHeight(80)
        
        # Clean unified look - no border, subtle background
        self.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(2)
        
        # Large value at top
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {accent}; font-size: 28px; font-weight: 700; background: transparent; border: none;")
        layout.addWidget(self.value_label)
        
        # Title below in muted color
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        layout.addWidget(title_label)
        
        layout.addStretch()
    
    def set_value(self, value: str):
        self.value_label.setText(value)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        self.value_label.setStyleSheet(f"color: {self.accent}; font-size: 28px; font-weight: 700; background: transparent; border: none; opacity: 0.8;")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.value_label.setStyleSheet(f"color: {self.accent}; font-size: 28px; font-weight: 700; background: transparent; border: none;")
        super().leaveEvent(event)


# =============================================================================
# Plugin Chip Widget (for project view)
# =============================================================================

class PluginChip(QFrame):
    """A clickable chip showing a single plugin."""
    
    clicked = Signal(str)
    
    def __init__(self, plugin_name: str, plugin_type: str, count: int = 1, parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(30, 41, 59, 0.8);
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background: rgba(56, 189, 248, 0.1);
                border-color: {Colors.ACCENT_PRIMARY};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)
        
        icon_name = "synthesizer" if plugin_type == 'generator' else "effect"
        icon_color = QColor(Colors.ACCENT_GENERATOR) if plugin_type == 'generator' else QColor(Colors.ACCENT_EFFECT)
        
        icon_label = QLabel()
        icon_label.setPixmap(get_icon(icon_name, icon_color, 14).pixmap(14, 14))
        layout.addWidget(icon_label)
        
        name_label = QLabel(plugin_name)
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        layout.addWidget(name_label)
        
        if count > 1:
            count_label = QLabel(f"×{count}")
            count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
            layout.addWidget(count_label)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.plugin_name)
        super().mousePressEvent(event)


# =============================================================================
# Plugins Panel (for project detail view)
# =============================================================================

class PluginsPanel(QWidget):
    """Panel showing plugins used in a project."""
    
    plugin_clicked = Signal(str)
    rescan_requested = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id: Optional[int] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Plugins Used")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        
        self.count_label = QLabel("0 plugins")
        self.count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        header.addWidget(self.count_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Plugins container
        self.plugins_layout = QVBoxLayout()
        self.plugins_layout.setSpacing(4)
        layout.addLayout(self.plugins_layout)
        layout.addStretch()
        
        # Empty state
        self.empty_label = QLabel("No plugins detected")
        self.empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        self.empty_label.hide()
        layout.addWidget(self.empty_label)
    
    def set_project(self, project_id: int):
        """Load plugins for a project."""
        self.project_id = project_id
        
        # Clear existing
        while self.plugins_layout.count():
            item = self.plugins_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not project_id:
            self._show_empty()
            return
        
        try:
            rows = query(
                """SELECT plugin_name, plugin_type, COUNT(*) as count
                   FROM project_plugins 
                   WHERE project_id = ?
                   GROUP BY plugin_name, plugin_type
                   ORDER BY plugin_type, plugin_name""",
                (project_id,)
            )
            plugins = [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to load plugins: {e}")
            plugins = []
        
        if not plugins:
            self._show_empty()
            return
        
        self.empty_label.hide()
        self.count_label.setText(f"{len(plugins)} plugins")
        
        for p in plugins:
            chip = PluginChip(p['plugin_name'], p.get('plugin_type', 'effect'), p.get('count', 1))
            chip.clicked.connect(self.plugin_clicked)
            self.plugins_layout.addWidget(chip)
    
    def _show_empty(self):
        self.empty_label.show()
        self.count_label.setText("0 plugins")
    
    def clear(self):
        self.project_id = None
        while self.plugins_layout.count():
            item = self.plugins_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._show_empty()


# =============================================================================
# Plugin Analytics Panel (Main Dashboard) - Optimized
# =============================================================================

class PluginAnalyticsPanel(QWidget):
    """Enhanced plugin analytics dashboard using QTableWidget for performance."""
    
    plugin_clicked = Signal(str)
    system_scan_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = "all"
        self.search_term = ""
        self._setup_ui()
        # Defer refresh
        QTimer.singleShot(200, self.refresh)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # =========================================
        # STATS ROW - Unified card container
        # =========================================
        stats_container = QFrame()
        stats_container.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        stats_container.setMaximumHeight(100)
        
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(8, 8, 8, 8)
        stats_layout.setSpacing(0)
        
        self.stat_total = StatCard("Total", "0", Colors.ACCENT_PRIMARY)
        stats_layout.addWidget(self.stat_total)
        
        # Separator
        sep1 = QFrame()
        sep1.setFixedWidth(1)
        sep1.setStyleSheet(f"background: {Colors.BORDER};")
        stats_layout.addWidget(sep1)
        
        self.stat_effects = StatCard("Effects", "0", Colors.ACCENT_EFFECT)
        self.stat_effects.clicked.connect(lambda: self._set_filter("effects"))
        stats_layout.addWidget(self.stat_effects)
        
        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setStyleSheet(f"background: {Colors.BORDER};")
        stats_layout.addWidget(sep2)
        
        self.stat_generators = StatCard("Generators", "0", Colors.ACCENT_GENERATOR)
        self.stat_generators.clicked.connect(lambda: self._set_filter("generators"))
        stats_layout.addWidget(self.stat_generators)
        
        sep3 = QFrame()
        sep3.setFixedWidth(1)
        sep3.setStyleSheet(f"background: {Colors.BORDER};")
        stats_layout.addWidget(sep3)
        
        self.stat_native = StatCard("Native", "0", Colors.ACCENT_NATIVE)
        self.stat_native.clicked.connect(lambda: self._set_filter("native"))
        stats_layout.addWidget(self.stat_native)
        
        sep4 = QFrame()
        sep4.setFixedWidth(1)
        sep4.setStyleSheet(f"background: {Colors.BORDER};")
        stats_layout.addWidget(sep4)
        
        self.stat_vst = StatCard("VST", "0", Colors.ACCENT_VST)
        self.stat_vst.clicked.connect(lambda: self._set_filter("vst"))
        stats_layout.addWidget(self.stat_vst)
        
        layout.addWidget(stats_container)
        
        # =========================================
        # FILTER BAR
        # =========================================
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search plugins...")
        self.search_input.setStyleSheet(SEARCH_STYLE)
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self._on_search_delayed)
        filter_bar.addWidget(self.search_input)
        
        filter_bar.addStretch()
        
        # Tabs
        self.tab_buttons = {}
        for tab_id, tab_label in [("all", "All"), ("effects", "Effects"), ("generators", "Generators"), 
                                   ("native", "Native"), ("vst", "VST"), ("unused", "Unused")]:
            btn = QPushButton(tab_label)
            btn.setCheckable(True)
            btn.setChecked(tab_id == "all")
            btn.setStyleSheet(TAB_STYLE)
            btn.clicked.connect(lambda _, t=tab_id: self._set_filter(t))
            filter_bar.addWidget(btn)
            self.tab_buttons[tab_id] = btn
        
        # Scan button
        self.scan_btn = QPushButton(" Scan")
        self.scan_btn.setIcon(get_icon("scan", QColor(Colors.TEXT_PRIMARY), 14))
        self.scan_btn.clicked.connect(lambda: self.system_scan_requested.emit())
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_CARD};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                background: {Colors.BG_CARD_HOVER};
            }}
        """)
        filter_bar.addWidget(self.scan_btn)
        
        layout.addLayout(filter_bar)
        
        # =========================================
        # TABLE
        # =========================================
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Plugin", "Projects", "Uses"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.setAlternatingRowColors(False)
        
        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 70)
        
        self.table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self.table, 1)
        
        # Search debounce timer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
    
    def _on_search_delayed(self, text: str):
        """Debounce search to avoid lag."""
        self.search_term = text.strip().lower()
        self._search_timer.stop()
        self._search_timer.start(300)  # 300ms debounce
    
    def _do_search(self):
        """Execute the search."""
        self.refresh()
    
    def _set_filter(self, filter_type: str):
        self.current_filter = filter_type
        for tab_id, btn in self.tab_buttons.items():
            btn.setChecked(tab_id == filter_type)
        self.refresh()
    
    def refresh(self):
        """Refresh the plugin list."""
        self.table.setRowCount(0)
        
        try:
            if self.current_filter == "unused":
                self._load_unused()
            else:
                self._load_used()
        except Exception as e:
            logger.error(f"Failed to refresh plugin analytics: {e}")
    
    def _load_used(self):
        """Load used plugins."""
        self.table.setHorizontalHeaderLabels(["", "Plugin", "Projects", "Uses"])
        
        # Build query
        sql = """
            SELECT plugin_name, plugin_type,
                   COUNT(DISTINCT project_id) as project_count,
                   COUNT(*) as total_count
            FROM project_plugins
        """
        
        where = []
        params = []
        
        if self.current_filter == "effects":
            where.append("plugin_type = 'effect'")
        elif self.current_filter == "generators":
            where.append("plugin_type = 'generator'")
        elif self.current_filter == "native":
            where.append("(plugin_name LIKE 'Fruity%' OR plugin_name IN ('Maximus','Edison','Harmor','Sytrus','Vocodex','Gross Beat','Slicex','FPC'))")
        elif self.current_filter == "vst":
            where.append("plugin_name NOT LIKE 'Fruity%' AND plugin_name NOT IN ('Maximus','Edison','Harmor','Sytrus','Vocodex','Gross Beat','Slicex','FPC')")
        
        if self.search_term:
            where.append("LOWER(plugin_name) LIKE ?")
            params.append(f"%{self.search_term}%")
        
        if where:
            sql += " WHERE " + " AND ".join(where)
        
        sql += " GROUP BY plugin_name ORDER BY project_count DESC LIMIT 100"
        
        try:
            if params:
                rows = query(sql, tuple(params))
            else:
                rows = query(sql)
            plugins = [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            plugins = []
        
        self._update_stats()
        
        self.table.setRowCount(len(plugins))
        
        for i, p in enumerate(plugins):
            ptype = p.get('plugin_type', 'effect')
            
            # Icon
            icon_name = "synthesizer" if ptype == 'generator' else "effect"
            icon_color = QColor(Colors.ACCENT_GENERATOR) if ptype == 'generator' else QColor(Colors.ACCENT_EFFECT)
            
            # Check if native
            pname = p.get('plugin_name', '')
            if pname.startswith('Fruity') or pname in ('Maximus','Edison','Harmor','Sytrus','Vocodex','Gross Beat'):
                icon_color = QColor(Colors.ACCENT_NATIVE)
                icon_name = "fl_studio"
            
            icon_item = QTableWidgetItem()
            icon_item.setIcon(get_icon(icon_name, icon_color, 18))
            self.table.setItem(i, 0, icon_item)
            
            # Name
            name_item = QTableWidgetItem(pname)
            name_item.setData(Qt.ItemDataRole.UserRole, pname)
            self.table.setItem(i, 1, name_item)
            
            # Projects
            proj_item = QTableWidgetItem(str(p.get('project_count', 0)))
            proj_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            proj_item.setForeground(QColor(Colors.ACCENT_PRIMARY))
            self.table.setItem(i, 2, proj_item)
            
            # Uses
            uses_item = QTableWidgetItem(str(p.get('total_count', 0)))
            uses_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            uses_item.setForeground(QColor(Colors.TEXT_SECONDARY))
            self.table.setItem(i, 3, uses_item)
    
    def _load_unused(self):
        """Load unused plugins."""
        self.table.setHorizontalHeaderLabels(["", "Plugin", "Format", "Path"])
        
        try:
            from ...utils.plugin_scanner import get_unused_plugins
            items = get_unused_plugins()
        except Exception as e:
            logger.error(f"Failed to get unused plugins: {e}")
            items = []
        
        if self.search_term:
            items = [p for p in items if self.search_term in p.get('name', '').lower()]
        
        self.table.setRowCount(len(items))
        
        for i, p in enumerate(items):
            icon_item = QTableWidgetItem()
            icon_item.setIcon(get_icon("trash", QColor(Colors.TEXT_MUTED), 16))
            self.table.setItem(i, 0, icon_item)
            
            name_item = QTableWidgetItem(p.get('name', 'Unknown'))
            self.table.setItem(i, 1, name_item)
            
            fmt_item = QTableWidgetItem(p.get('format', 'VST'))
            fmt_item.setForeground(QColor(Colors.TEXT_SECONDARY))
            self.table.setItem(i, 2, fmt_item)
            
            # Truncate path
            path = p.get('path', '')
            if len(path) > 60:
                path = "..." + path[-57:]
            path_item = QTableWidgetItem(path)
            path_item.setForeground(QColor(Colors.TEXT_MUTED))
            self.table.setItem(i, 3, path_item)
    
    def _update_stats(self):
        """Update stat cards."""
        try:
            result = query("SELECT COUNT(DISTINCT plugin_name) as c FROM project_plugins")
            self.stat_total.set_value(str(result[0]['c'] if result else 0))
        except:
            self.stat_total.set_value("0")
        
        try:
            result = query("SELECT COUNT(DISTINCT plugin_name) as c FROM project_plugins WHERE plugin_type='effect'")
            self.stat_effects.set_value(str(result[0]['c'] if result else 0))
        except:
            self.stat_effects.set_value("0")
        
        try:
            result = query("SELECT COUNT(DISTINCT plugin_name) as c FROM project_plugins WHERE plugin_type='generator'")
            self.stat_generators.set_value(str(result[0]['c'] if result else 0))
        except:
            self.stat_generators.set_value("0")
        
        try:
            result = query("SELECT COUNT(DISTINCT plugin_name) as c FROM project_plugins WHERE plugin_name LIKE 'Fruity%' OR plugin_name IN ('Maximus','Edison','Harmor','Sytrus')")
            self.stat_native.set_value(str(result[0]['c'] if result else 0))
        except:
            self.stat_native.set_value("0")
        
        try:
            result = query("SELECT COUNT(DISTINCT plugin_name) as c FROM project_plugins WHERE plugin_name NOT LIKE 'Fruity%'")
            self.stat_vst.set_value(str(result[0]['c'] if result else 0))
        except:
            self.stat_vst.set_value("0")
    
    def _on_row_clicked(self, row, col):
        if self.current_filter == "unused":
            return
        item = self.table.item(row, 1)
        if item:
            plugin_name = item.data(Qt.ItemDataRole.UserRole)
            if plugin_name:
                self.plugin_clicked.emit(plugin_name)
