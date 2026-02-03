"""
Plugin Analytics Panel — Phase 1 Control Room

Unified plugin list with truth state (Safe/Risky/Missing/Unknown/Unused).
Studio Mode chips: Studio, Missing, Risky, Hot, Last 30 days, All.
"""

import logging
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTableView, QListView, QPushButton, QScrollArea, QLineEdit, QCheckBox, QButtonGroup,
    QSizePolicy, QStyleOptionViewItem, QStyledItemDelegate,
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QAbstractTableModel, QAbstractListModel, QModelIndex, QSize
from PySide6.QtGui import QColor, QPainter

from ...database import query
from ...utils import get_icon, format_smart_date
from ...utils.plugin_scanner import (
    get_plugin_truth_states,
    PLUGIN_STATE_SAFE,
    PLUGIN_STATE_RISKY,
    PLUGIN_STATE_MISSING,
    PLUGIN_STATE_UNKNOWN,
    PLUGIN_STATE_UNUSED,
)

logger = logging.getLogger(__name__)

# Keep load threads alive until they finish so they are never destroyed while running
# (avoids "QThread: Destroyed while thread is still running" on tab switch or app close).
_active_load_threads = set()

# Cache of last full plugin list by name (lower) -> row. Filled when main list loads.
# Read by Plugin Details worker to avoid recomputing full get_plugin_truth_states on click.
_plugin_state_cache = {}


def get_cached_plugin_state(plugin_name: str) -> Optional[Dict]:
    """Return cached truth-state row for this plugin if the main list was recently loaded."""
    if not plugin_name or not isinstance(plugin_name, str):
        return None
    return _plugin_state_cache.get((plugin_name or "").strip().lower())


def wait_for_plugin_load_threads(timeout_ms: int = 5000) -> None:
    """Wait for any running plugin list load threads. Call from main window closeEvent."""
    for t in list(_active_load_threads):
        if t.isRunning():
            t.wait(timeout_ms)


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
    QTableView, QTableWidget {{
        background-color: {Colors.BG_CARD};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
        gridline-color: transparent;
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: rgba(56, 189, 248, 0.15);
    }}
    QTableView::item, QTableWidget::item {{
        padding: 10px 8px;
        border-bottom: 1px solid rgba(51, 65, 85, 0.3);
    }}
    QTableView::item:selected, QTableWidget::item:selected {{
        background-color: rgba(56, 189, 248, 0.15);
    }}
    QTableView::item:hover, QTableWidget::item:hover {{
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

# Phase 1: Studio Mode chips (pill style, single-select)
CHIP_STYLE = f"""
    QPushButton {{
        background: {Colors.BG_DARK};
        border: 1px solid {Colors.BORDER};
        border-radius: 999px;
        color: {Colors.TEXT_SECONDARY};
        padding: 8px 12px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        color: {Colors.TEXT_PRIMARY};
        border-color: #475569;
    }}
    QPushButton:checked {{
        background: #1e3a5f;
        border-color: {Colors.ACCENT_PRIMARY};
        color: {Colors.ACCENT_PRIMARY};
    }}
"""

# Status badge colors (plugin-page-analysis.md)
STATUS_COLORS = {
    PLUGIN_STATE_SAFE: "#166534",    # green-800
    PLUGIN_STATE_RISKY: "#b45309",   # amber-700
    PLUGIN_STATE_MISSING: "#b91c1c", # red-700
    PLUGIN_STATE_UNKNOWN: "#4b5563", # gray-600 (yellow in UI copy)
    PLUGIN_STATE_UNUSED: Colors.TEXT_MUTED,
}


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
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
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
# Plugins Panel (for project detail view) — List model + delegate, no widget-per-row
# =============================================================================

class ProjectPluginsListModel(QAbstractListModel):
    """List model for plugins used in a project. Each row: plugin_name, plugin_type, count."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._plugins: List[Dict] = []

    def set_plugins(self, plugins: List[Dict]) -> None:
        self.beginResetModel()
        self._plugins = list(plugins)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._plugins)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._plugins):
            return None
        row = self._plugins[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return (row.get("plugin_name") or "").strip()
        if role == Qt.ItemDataRole.UserRole:
            return row
        return None


class ProjectPluginsDelegate(QStyledItemDelegate):
    """Paint each row as a chip: icon + name + optional count."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        row = index.data(Qt.ItemDataRole.UserRole)
        if not row:
            super().paint(painter, option, index)
            return
        plugin_name = (row.get("plugin_name") or "").strip()
        plugin_type = row.get("plugin_type") or "effect"
        count = row.get("count") or 1
        rect = option.rect.adjusted(4, 2, -4, -2)
        painter.save()
        # Chip background
        painter.setPen(QColor(Colors.BORDER))
        painter.setBrush(QColor(Colors.BG_CARD))
        painter.drawRoundedRect(rect, 6, 6)
        # Icon
        icon_name = "synthesizer" if plugin_type == "generator" else "effect"
        icon_color = QColor(Colors.ACCENT_GENERATOR) if plugin_type == "generator" else QColor(Colors.ACCENT_EFFECT)
        icon_pix = get_icon(icon_name, icon_color, 14).pixmap(14, 14)
        icon_rect = rect.adjusted(10, (rect.height() - 14) // 2, 10 + 14, 0)
        painter.drawPixmap(icon_rect.left(), icon_rect.top(), icon_pix)
        # Name
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        name_rect = rect.adjusted(10 + 14 + 6, 0, -8, 0)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, plugin_name)
        if count > 1:
            painter.setPen(QColor(Colors.TEXT_MUTED))
            count_text = f"×{count}"
            painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, count_text)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        return QSize(200, 36)


class PluginsPanel(QWidget):
    """Panel showing plugins used in a project (list model + delegate, virtualized)."""
    
    plugin_clicked = Signal(str)
    rescan_requested = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id: Optional[int] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        header = QHBoxLayout()
        title = QLabel("Plugins Used")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        self.count_label = QLabel("0 plugins")
        self.count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        header.addWidget(self.count_label)
        header.addStretch()
        layout.addLayout(header)
        
        self.plugins_model = ProjectPluginsListModel(self)
        self.plugins_list = QListView()
        self.plugins_list.setModel(self.plugins_model)
        self.plugins_list.setItemDelegate(ProjectPluginsDelegate(self.plugins_list))
        self.plugins_list.setFrameShape(QFrame.Shape.NoFrame)
        self.plugins_list.setSpacing(4)
        self.plugins_list.setUniformItemSizes(True)
        self.plugins_list.setStyleSheet(f"""
            QListView {{ background: transparent; border: none; outline: none; }}
            QListView::item {{ height: 36px; }}
            QListView::item:hover {{ background: rgba(51, 65, 85, 0.3); border-radius: 6px; }}
            QScrollBar:vertical {{ background: {Colors.BG_DARK}; width: 8px; border-radius: 4px; }}
            QScrollBar::handle:vertical {{ background: {Colors.BORDER}; border-radius: 4px; min-height: 20px; }}
        """)
        self.plugins_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plugins_list.clicked.connect(self._on_plugin_clicked)
        layout.addWidget(self.plugins_list, 1)
        
        self.empty_label = QLabel("No plugins detected")
        self.empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def _on_plugin_clicked(self, index: QModelIndex):
        if index.isValid():
            name = (self.plugins_model.data(index, Qt.ItemDataRole.UserRole) or {}).get("plugin_name")
            if name:
                self.plugin_clicked.emit((name or "").strip())
    
    def set_project(self, project_id: int):
        """Load plugins for a project."""
        self.project_id = project_id
        if not project_id:
            self.plugins_model.set_plugins([])
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
            self.plugins_model.set_plugins([])
            self._show_empty()
            return
        self.empty_label.hide()
        self.count_label.setText(f"{len(plugins)} plugins")
        self.plugins_model.set_plugins(plugins)

    def _show_empty(self):
        self.empty_label.show()
        self.count_label.setText("0 plugins")

    def clear(self):
        self.project_id = None
        self.plugins_model.set_plugins([])
        self._show_empty()


class LoadThread(QThread):
    result_ready = Signal(int, list)

    def __init__(self, rid, studio_filter, search_term):
        super().__init__()
        self.rid = rid
        self.studio_filter = studio_filter
        self.search_term = search_term

    def run(self):
        try:
            raw = get_plugin_truth_states(
                studio_filter=self.studio_filter,
                search_term=self.search_term or None,
                limit=500,
            )
            self.result_ready.emit(self.rid, raw)
        except Exception as e:
            logger.exception("Plugin list load: %s", e)
            self.result_ready.emit(self.rid, [])


# =============================================================================
# Plugin list: Model + Delegate (virtualized, no widget-per-row)
# =============================================================================

class PluginsTableModel(QAbstractTableModel):
    """Table model for Plugin Analytics list. Columns: Status, Name, Format, Projects, Last seen."""
    COL_STATUS = 0
    COL_NAME = 1
    COL_FORMAT = 2
    COL_PROJECTS = 3
    COL_LAST_SEEN = 4
    HEADERS = ["Status", "Name", "Format", "Projects", "Last seen"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = []

    def set_plugin_list(self, raw: List[Dict]) -> None:
        self.beginResetModel()
        self._rows = list(raw)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return 5

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_STATUS:
                return (row.get("state") or "unknown").capitalize()
            if col == self.COL_NAME:
                return (row.get("plugin_name") or "").strip()
            if col == self.COL_FORMAT:
                return row.get("format") or "?"
            if col == self.COL_PROJECTS:
                return str(row.get("project_count") or 0)
            if col == self.COL_LAST_SEEN:
                last_seen = row.get("last_seen")
                return format_smart_date(last_seen) if last_seen else "—"
        if role == Qt.ItemDataRole.UserRole:
            return (row.get("plugin_name") or "").strip()
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_STATUS:
                state = (row.get("state") or "unknown").lower()
                return QColor(STATUS_COLORS.get(state, Colors.TEXT_MUTED))
            if col in (self.COL_FORMAT, self.COL_LAST_SEEN):
                return QColor(Colors.TEXT_SECONDARY)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < 5:
            return self.HEADERS[section]
        return None


class PluginsTableDelegate(QStyledItemDelegate):
    """Paint status column with status color; others use default."""
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        if index.column() == PluginsTableModel.COL_STATUS:
            painter.save()
            text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            color = index.data(Qt.ItemDataRole.ForegroundRole)
            if color:
                painter.setPen(color)
            rect = option.rect
            painter.drawText(rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            painter.restore()
        else:
            super().paint(painter, option, index)


# =============================================================================
# Plugin Analytics Panel (Phase 1 Control Room)
# =============================================================================

class PluginAnalyticsPanel(QWidget):
    """Unified plugin list with truth state. Studio Mode chips. No vanity stats."""
    
    plugin_clicked = Signal(str)
    system_scan_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_studio_filter = "all"  # default: All (every plugin)
        self.search_term = ""
        self.show_unused = False
        self._active_threads = set() # Keep threads alive until finished
        self._setup_ui()
        QTimer.singleShot(200, self.refresh)
    
    def _setup_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # ---------- Top bar: Search + Studio chips + Show Unused + Scan ----------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search plugins…")
        self.search_input.setStyleSheet(SEARCH_STYLE)
        self.search_input.setMaximumWidth(280)
        self.search_input.textChanged.connect(self._on_search_delayed)
        top_bar.addWidget(self.search_input)
        
        # Filter chips: All = every plugin; Studio = my plugins (safest first); Missing = only missing; etc.
        self.chip_group = QButtonGroup(self)
        self.chip_buttons = {}
        for chip_id, label in [
            ("all", "All"),
            ("studio", "Studio"),
            ("missing", "Missing"),
            ("risky", "Risky"),
            ("hot", "Hot"),
            ("last30", "Last 30 days"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(chip_id == "all")
            btn.setStyleSheet(CHIP_STYLE)
            btn.clicked.connect(lambda _, c=chip_id: self._set_studio_filter(c))
            top_bar.addWidget(btn)
            self.chip_buttons[chip_id] = btn
            self.chip_group.addButton(btn)
        
        top_bar.addStretch()
        
        self.show_unused_check = QCheckBox("Show Unused")
        self.show_unused_check.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        self.show_unused_check.setChecked(False)
        self.show_unused_check.stateChanged.connect(self.refresh)
        top_bar.addWidget(self.show_unused_check)
        
        self.scan_btn = QPushButton(" Scan")
        self.scan_btn.setIcon(get_icon("scan", QColor(Colors.TEXT_PRIMARY), 14))
        self.scan_btn.clicked.connect(self.system_scan_requested.emit)
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 6px; padding: 8px 14px; }}
            QPushButton:hover {{ background: {Colors.BG_CARD_HOVER}; }}
        """)
        top_bar.addWidget(self.scan_btn)
        
        layout.addLayout(top_bar)
        
        # ---------- List header ----------
        list_head = QHBoxLayout()
        list_head.addWidget(QLabel("Plugins"))
        list_head.addStretch()
        list_head.addWidget(QLabel("Safest first"))
        list_head.last_label = list_head.itemAt(list_head.count() - 1).widget()
        list_head.last_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        layout.addLayout(list_head)
        
        # ---------- Table: Status | Name | Format | Projects | Last seen (Model/View for virtualization) ----------
        self.plugins_model = PluginsTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.plugins_model)
        self.table.setItemDelegate(PluginsTableDelegate(self.table))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.setAlternatingRowColors(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 72)
        self.table.setColumnWidth(2, 56)
        self.table.setColumnWidth(3, 64)
        self.table.setColumnWidth(4, 80)
        self.table.clicked.connect(self._on_row_clicked)
        layout.addWidget(self.table, 1)
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.refresh)
    
    def _on_search_delayed(self, text: str):
        self.search_term = text.strip()
        self._search_timer.stop()
        self._search_timer.start(300)
    
    def _set_studio_filter(self, chip_id: str):
        self.current_studio_filter = chip_id
        for cid, btn in self.chip_buttons.items():
            btn.setChecked(cid == chip_id)
        self.refresh()

    def _start_load_thread(self):
        """Run get_plugin_truth_states in a worker thread so the UI never blocks."""
        studio_filter = self.current_studio_filter if self.current_studio_filter != "all" else None
        search_term = self.search_term or None
        show_unused = self.show_unused_check.isChecked()
        request_id = getattr(self, "_load_request_id", 0) + 1
        self._load_request_id = request_id

        class LoadThread(QThread):
            result_ready = Signal(int, list)

            def __init__(self, rid, studio_filter, search_term):
                super().__init__(None)  # No parent: do not destroy with panel or app
                self.rid = rid
                self.studio_filter = studio_filter
                self.search_term = search_term

            def run(self):
                try:
                    raw = get_plugin_truth_states(
                        studio_filter=self.studio_filter,
                        search_term=self.search_term or None,
                        limit=500,
                    )
                    self.result_ready.emit(self.rid, raw)
                except Exception as e:
                    logger.exception("Plugin list load: %s", e)
                    self.result_ready.emit(self.rid, [])

        thread = LoadThread(request_id, studio_filter, search_term)
        _active_load_threads.add(thread)

        def _cleanup(t):
            _active_load_threads.discard(t)
            t.deleteLater()

        thread.result_ready.connect(self._on_plugin_list_loaded)
        thread.finished.connect(lambda t=thread: _cleanup(t))
        thread.start()
        self._load_thread = thread

    def _on_plugin_list_loaded(self, request_id: int, raw: list):
        """Apply plugin list to model on main thread. Ignore stale responses. Update cache for detail panel."""
        if request_id != getattr(self, "_load_request_id", 0):
            return
        show_unused = self.show_unused_check.isChecked()
        if self.current_studio_filter == "all" and not show_unused:
            raw = [r for r in raw if r.get("state") != PLUGIN_STATE_UNUSED]
        _plugin_state_cache.clear()
        for r in raw:
            name = (r.get("plugin_name") or "").strip()
            if name:
                _plugin_state_cache[name.lower()] = dict(r)
        self.plugins_model.set_plugin_list(raw)
        self._load_thread = None

    def refresh(self):
        self.plugins_model.set_plugin_list([])
        self._search_timer.stop()
        try:
            self._start_load_thread()
        except Exception as e:
            logger.exception("Plugin list refresh: %s", e)

    def _on_row_clicked(self, index: QModelIndex):
        if index.isValid():
            plugin_name = self.plugins_model.data(
                self.plugins_model.index(index.row(), PluginsTableModel.COL_NAME),
                Qt.ItemDataRole.UserRole,
            )
            if plugin_name:
                self.plugin_clicked.emit(plugin_name)
