"""
Projects Model

QAbstractTableModel implementation for high-performance projects list.
"""

from typing import List, Dict, Any
from datetime import datetime
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush

from ...classifier.engine import ProjectState
from ...utils import format_smart_date


class ProjectsModel(QAbstractTableModel):
    """Table model for displaying projects."""
    
    # Columns
    COL_STATE = 0
    COL_NAME = 1
    COL_SCORE = 2
    COL_MODIFIED = 3
    COL_BACKUPS = 4
    COL_SIZE = 5
    COL_ACTIONS = 6
    
    COLUMNS = ["STATE", "NAME", "SCORE", "MODIFIED", "BACKUPS", "SIZE", "ACTIONS"]
    
    def __init__(self, projects: List[Dict] = None, parent=None):
        super().__init__(parent)
        self._projects = projects or []
        
    def set_projects(self, projects: List[Dict]):
        """Update data efficiently."""
        self.beginResetModel()
        self._projects = projects
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._projects)
        
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)
        
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
            
        row = index.row()
        col = index.column()
        project = self._projects[row]
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_STATE:
                return self._format_state(project.get('state'))
            elif col == self.COL_NAME:
                return project.get('name', '')
            elif col == self.COL_SCORE:
                return str(project.get('render_priority_score', 0))
            elif col == self.COL_MODIFIED:
                return format_smart_date(project.get('updated_at', 0))
            elif col == self.COL_BACKUPS:
                return str(project.get('backup_count', 0))
            elif col == self.COL_SIZE:
                size_kb = project.get('flp_size_kb', 0)
                return f"{size_kb} KB"
            elif col == self.COL_ACTIONS:
                return "" # Handled by delegate
                
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_STATE:
                state = project.get('state')
                return QBrush(self._get_state_color(state))
            elif col == self.COL_SCORE:
                score = project.get('render_priority_score', 0)
                if score > 70:
                    return QBrush(QColor("#22c55e"))
                elif score > 40:
                    return QBrush(QColor("#f59e0b"))
                else:
                    return QBrush(QColor("#64748b"))
            elif col == self.COL_NAME:
                return QBrush(QColor("#f1f5f9"))
            else:
                return QBrush(QColor("#94a3b8"))
                
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [self.COL_SCORE, self.COL_BACKUPS, self.COL_SIZE]:
                return int(Qt.AlignmentFlag.AlignCenter)
            elif col == self.COL_STATE:
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
        elif role == Qt.ItemDataRole.ToolTipRole:
            if col == self.COL_NAME:
                return project.get('path', '')
            elif col == self.COL_ACTIONS:
                return "Open Folder / Open FLP"
        
        elif role == Qt.ItemDataRole.UserRole:
            # Return raw project data for finding it later
            return project
            
        return None
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None
        
    def _format_state(self, state: str) -> str:
        if not state: return "Unknown"
        return state.replace("_", " ").title().replace("Or", "/")
        
    def _get_state_color(self, state: str) -> QColor:
        map_ = {
            ProjectState.MICRO_IDEA: QColor("#94a3b8"),
            ProjectState.IDEA: QColor("#38bdf8"),
            ProjectState.WIP: QColor("#f59e0b"),
            ProjectState.PREVIEW_READY: QColor("#22c55e"),
            ProjectState.ADVANCED: QColor("#a855f7"),
            ProjectState.BROKEN_OR_EMPTY: QColor("#ef4444"),
        }
        return map_.get(state, QColor("#f1f5f9"))
