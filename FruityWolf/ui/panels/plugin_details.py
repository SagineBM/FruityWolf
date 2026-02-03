"""
Plugin Details Panel — Phase 1 Triage

Title + status badge, danger summary, then Projects table:
Project | Heat | Audibility | Safety | Safe to open.
"""

import logging
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QTableView, QHeaderView, QAbstractItemView,
    QStyleOptionViewItem, QStyledItemDelegate,
)
from PySide6.QtCore import Qt, Signal, QThread, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QPainter

from ...utils import get_icon, format_smart_date
from ...utils.plugin_scanner import (
    get_plugin_state_for_name,
    PLUGIN_STATE_SAFE,
    PLUGIN_STATE_RISKY,
    PLUGIN_STATE_MISSING,
    PLUGIN_STATE_UNKNOWN,
    PLUGIN_STATE_UNUSED,
)
from ...scanner.library_scanner import (
    get_projects_using_plugin_for_triage,
    get_safe_to_open_project_ids,
)
from ...core.activity_heat import calculate_activity_heat, get_heat_color
from .plugins_panel import get_cached_plugin_state

logger = logging.getLogger(__name__)

# Status colors (match plugins_panel)
STATUS_COLORS = {
    PLUGIN_STATE_SAFE: "#166534",
    PLUGIN_STATE_RISKY: "#b45309",
    PLUGIN_STATE_MISSING: "#b91c1c",
    PLUGIN_STATE_UNKNOWN: "#4b5563",
    PLUGIN_STATE_UNUSED: "#64748b",
}

DANGER_TEMPLATES = {
    PLUGIN_STATE_MISSING: "Referenced by {n} project(s), not found on this machine. You can still preview projects that have renders, but opening in FL may change the sound.",
    PLUGIN_STATE_RISKY: "Present, but projects using it have recent render failures. Check before opening.",
    PLUGIN_STATE_UNKNOWN: "FruityWolf can't confirm presence (name or path ambiguous). Treat as risk, not failure.",
    PLUGIN_STATE_SAFE: "Present and only used in projects that are not Unstable.",
    PLUGIN_STATE_UNUSED: "Present on disk but not referenced by any project.",
}


class PluginTriageTableModel(QAbstractTableModel):
    """Table model for plugin-detail triage: Project | Heat | Audibility | Safety | Safe to open."""
    COL_PROJECT = 0
    COL_HEAT = 1
    COL_AUDIBILITY = 2
    COL_SAFETY = 3
    COL_SAFE_TO_OPEN = 4
    HEADERS = ["Project", "Heat", "Audibility", "Safety", "Safe to open"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = []  # precomputed {project, heat_label, heat_color, audibility, aud_color, safety, safety_color, safe_to_open}

    def set_projects(self, projects: List[Dict], safe_ids: set) -> None:
        self.beginResetModel()
        self._rows = []
        for proj in projects:
            heat_data = calculate_activity_heat(
                proj.get("file_created_at"),
                proj.get("last_opened_at"),
                None,
                proj.get("open_count") or 0,
                proj.get("play_count") or 0,
                proj.get("last_played_ts"),
            )
            heat_label = heat_data.get("label") or "Cold"
            render_count = proj.get("render_count") or 0
            audibility = "Preview Ready" if render_count > 0 else "Unheard"
            safety = "Unstable" if proj.get("last_render_failed_at") else "OK"
            pid = proj.get("id")
            safe_to_open = "✅" if (pid and pid in safe_ids) else "⚠️"
            self._rows.append({
                "project": proj,
                "name": proj.get("name") or "—",
                "heat_label": heat_label,
                "heat_color": get_heat_color(heat_label),
                "audibility": audibility,
                "aud_color": "#22c55e" if render_count > 0 else "#64748b",
                "safety": safety,
                "safety_color": "#ef4444" if proj.get("last_render_failed_at") else "#22c55e",
                "safe_to_open": safe_to_open,
            })
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
            if col == self.COL_PROJECT:
                return row["name"]
            if col == self.COL_HEAT:
                return row["heat_label"]
            if col == self.COL_AUDIBILITY:
                return row["audibility"]
            if col == self.COL_SAFETY:
                return row["safety"]
            if col == self.COL_SAFE_TO_OPEN:
                return row["safe_to_open"]
        if role == Qt.ItemDataRole.UserRole:
            return row["project"]
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_HEAT:
                return QColor(row["heat_color"])
            if col == self.COL_AUDIBILITY:
                return QColor(row["aud_color"])
            if col == self.COL_SAFETY:
                return QColor(row["safety_color"])
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < 5:
            return self.HEADERS[section]
        return None


class _PluginDetailLoadThread(QThread):
    """Load state, projects, and safe_ids in background so UI never blocks."""
    result_ready = Signal(str, object)  # (plugin_name, (state_row, projects, safe_ids))

    def __init__(self, plugin_name: str):
        super().__init__(None)
        self.plugin_name = (plugin_name or "").strip()

    def run(self):
        try:
            state = get_cached_plugin_state(self.plugin_name)
            if state is None:
                state = get_plugin_state_for_name(self.plugin_name)
            projects = get_projects_using_plugin_for_triage(self.plugin_name, limit=100)
            safe_ids = get_safe_to_open_project_ids()
            self.result_ready.emit(
                self.plugin_name,
                (state, projects, safe_ids),
            )
        except Exception as e:
            logger.exception("Plugin detail load: %s", e)
            self.result_ready.emit(self.plugin_name, (None, [], set()))


class PluginDetailsPanel(QWidget):
    """Right panel: plugin name + status, danger text, triage table (Project | Heat | Audibility | Safety | Safe to open)."""
    
    project_clicked = Signal(dict)
    play_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugin_name: Optional[str] = None
        self.current_projects_list: List[Dict] = []
        self._safe_ids: set = set()
        self._load_thread: Optional[QThread] = None
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
        
        # Header: title + status badge
        self.header_label = QLabel("PLUGIN DETAILS")
        self.header_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #38bdf8; letter-spacing: 1.5px;")
        self.main_layout.addWidget(self.header_label)
        
        title_row = QHBoxLayout()
        self.name_label = QLabel("--")
        self.name_label.setStyleSheet("font-size: 18px; color: #f1f5f9; font-weight: 800;")
        self.name_label.setWordWrap(True)
        title_row.addWidget(self.name_label)
        self.status_badge = QLabel("")
        self.status_badge.setStyleSheet("font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px;")
        title_row.addWidget(self.status_badge)
        title_row.addStretch()
        self.main_layout.addLayout(title_row)
        
        # Danger summary
        self.danger_label = QLabel("")
        self.danger_label.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        self.danger_label.setWordWrap(True)
        self.main_layout.addWidget(self.danger_label)
        
        self.line = QFrame()
        self.line.setFixedHeight(1)
        self.line.setStyleSheet("background-color: rgba(51, 65, 85, 0.5);")
        self.main_layout.addWidget(self.line)
        
        # Triage table: Project | Heat | Audibility | Safety | Safe to open (Model/View for virtualization)
        self.triage_model = PluginTriageTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.triage_model)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableView { background: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #f1f5f9; }
            QTableView::item { padding: 8px; }
            QHeaderView::section { background: #1e293b; color: #64748b; padding: 10px; font-weight: 700; font-size: 11px; border: none; border-bottom: 1px solid #334155; }
        """)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 72)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 72)
        self.table.setColumnWidth(4, 88)
        self.table.doubleClicked.connect(self._on_double_clicked)
        self.main_layout.addWidget(self.table, 1)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
    
    def set_plugin(self, plugin_name: str):
        """Request plugin details; load state + projects in background so UI never blocks."""
        self.plugin_name = (plugin_name or "").strip()
        self.name_label.setText(self.plugin_name or "--")
        self.status_badge.setText("Loading…")
        self.status_badge.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; "
            "background: #475569; color: #94a3b8; border: 1px solid transparent;"
        )
        self.danger_label.setText("")
        self.current_projects_list = []
        self.triage_model.set_projects([], set())
        self._safe_ids = set()

        if not self.plugin_name:
            self.status_badge.setText("")
            return

        thread = _PluginDetailLoadThread(self.plugin_name)
        thread.result_ready.connect(self._on_detail_loaded)
        thread.finished.connect(thread.deleteLater)
        self._load_thread = thread
        thread.start()

    def _on_detail_loaded(self, loaded_name: str, payload):
        """Apply loaded state, projects, safe_ids on main thread. Ignore stale responses."""
        if loaded_name != self.plugin_name:
            return
        state_row, projects, safe_ids = payload
        if not self.plugin_name:
            return
        self._safe_ids = safe_ids
        self.current_projects_list = projects
        self.triage_model.set_projects(projects, safe_ids)

        if state_row:
            state = (state_row.get("state") or "unknown").lower()
            state_label = state.capitalize()
            self.status_badge.setText(state_label)
            self.status_badge.setStyleSheet(
                f"font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; "
                f"background: {STATUS_COLORS.get(state, '#475569')}; color: #fff; border: 1px solid transparent;"
            )
            n = state_row.get("project_count") or 0
            danger_text = DANGER_TEMPLATES.get(state, "").format(n=n)
            self.danger_label.setText(danger_text)
        else:
            self.status_badge.setText("Unknown")
            self.status_badge.setStyleSheet(
                f"font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; "
                f"background: {STATUS_COLORS.get(PLUGIN_STATE_UNKNOWN, '#475569')}; color: #fff; border: 1px solid transparent;"
            )
            self.danger_label.setText(DANGER_TEMPLATES.get(PLUGIN_STATE_UNKNOWN, ""))

        self._load_thread = None

    def _on_double_clicked(self, index: QModelIndex):
        if index.isValid():
            project = self.triage_model.data(index, Qt.ItemDataRole.UserRole)
            if project:
                self.project_clicked.emit(project)
    
    def clear(self):
        self.plugin_name = None
        self.name_label.setText("--")
        self.status_badge.setText("")
        self.danger_label.setText("")
        self.current_projects_list = []
        self.triage_model.set_projects([], set())
