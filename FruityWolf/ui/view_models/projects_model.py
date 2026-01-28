"""
Projects Model

QAbstractTableModel implementation for high-performance projects list.
Supports Phase 1 Core columns: Selection, State, Score, Next Action.
"""

from typing import List, Dict, Any, Set
from datetime import datetime
import json
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush, QIcon

from ...classifier.engine import ProjectState
from ...utils import format_smart_date

class ProjectsModel(QAbstractTableModel):
    """Table model for displaying projects."""
    
    # Columns
    COL_SELECT = 0
    COL_STATE = 1
    COL_NAME = 2
    COL_SCORE = 3
    COL_NEXT_ACTION = 4
    COL_LAST_PLAYED = 5
    COL_RENDERS = 6  # Render count
    COL_ACTIONS = 7
    
    COLUMNS = ["", "STATE", "NAME", "SCORE", "NEXT ACTION", "PLAYED", "RENDERS", "ACTIONS"]
    
    def __init__(self, projects: List[Dict] = None, parent=None):
        super().__init__(parent)
        self._projects = projects or []
        self._checked_ids: Set[int] = set()
        
    def set_projects(self, projects: List[Dict]):
        """Update data efficiently."""
        self.beginResetModel()
        self._prepare_projects(projects)
        self._projects = projects
        self.endResetModel()
        
    def append_projects(self, projects: List[Dict]):
        """Append more projects for pagination."""
        if not projects: return
        
        start_row = len(self._projects)
        end_row = start_row + len(projects) - 1
        
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        self._prepare_projects(projects)
        self._projects.extend(projects)
        self.endInsertRows()
        
    def _prepare_projects(self, projects: List[Dict]):
        """Pre-process project data for UI."""
        for p in projects:
            # P10 Fix: Prioritize direct render_count from DB query
            p['has_render'] = bool(p.get('render_count', 0) > 0)
            
            # Legacy fallback for older cached signals if needed
            if not p['has_render'] and 'signals' in p and p['signals']:
                try:
                    s = json.loads(p['signals']) if isinstance(p['signals'], str) else p['signals']
                    raw = s.get('raw', {})
                    p['has_render_root'] = raw.get('has_render_root', False)
                    p['has_render'] = bool(raw.get('render_duration_s', 0) > 0) or p['has_render_root']
                except:
                    pass
        
    def get_checked_projects(self) -> List[Dict]:
        """Get list of checked project objects."""
        return [p for p in self._projects if p.get('id') in self._checked_ids]
    
    def clear_selection(self):
        """Uncheck all."""
        if not self._checked_ids: return
        self.beginResetModel() # Heavy hammer but works for update
        self._checked_ids.clear()
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
                return self._format_state(project.get('state_id'))
            elif col == self.COL_NAME:
                return project.get('name', '')
            elif col == self.COL_SCORE:
                # Delegate will paint bar, but text helps sorting/accessibility
                return str(project.get('score', 0))
            elif col == self.COL_NEXT_ACTION:
                # Delegate handles icon, text here
                return ProjectState.format_action_id(project.get('next_action_id'))
            elif col == self.COL_LAST_PLAYED:
                ts = project.get('last_played_ts')
                return format_smart_date(ts) if ts else "-"
            elif col == self.COL_RENDERS:
                count = project.get('render_count', 0)
                return f"Renders ({count})" if count > 0 else "No renders"
            elif col == self.COL_ACTIONS:
                return ""
                
        elif role == Qt.ItemDataRole.CheckStateRole:
            if col == self.COL_SELECT:
                pid = project.get('id')
                return Qt.CheckState.Checked if pid in self._checked_ids else Qt.CheckState.Unchecked
                
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_STATE:
                 return QBrush(self._get_state_color(project.get('state_id')))
            elif col == self.COL_NAME:
                return QBrush(QColor("#f1f5f9"))
            elif col == self.COL_LAST_PLAYED:
                return QBrush(QColor("#94a3b8"))
            elif col == self.COL_RENDERS:
                count = project.get('render_count', 0)
                if count > 0:
                    return QBrush(QColor("#38bdf8"))  # Sky blue for clickable
                return QBrush(QColor("#64748b"))  # Muted if no renders
                
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [self.COL_SCORE, self.COL_LAST_PLAYED, self.COL_RENDERS]:
                return int(Qt.AlignmentFlag.AlignCenter)
            elif col == self.COL_STATE:
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
        elif role == Qt.ItemDataRole.UserRole:
            return project
            
        return None
        
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
            
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == self.COL_SELECT:
            project = self._projects[index.row()]
            pid = project.get('id')
            if value == Qt.CheckState.Checked.value or value == Qt.CheckState.Checked:
                self._checked_ids.add(pid)
            else:
                self._checked_ids.discard(pid)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
            
        return False
        
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.column() == self.COL_SELECT:
            flags |= Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable
        return flags
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None
        
    def _format_state(self, state: str) -> str:
        if not state: return "Unknown"
        # CLEANUP: project_states.json has nice labels? Or logic here.
        # Simple cleanup
        return state.replace("_", " ").title().replace("Or", "/")
        
    def _get_state_color(self, state: str) -> QColor:
        # Should match project_states.json really, but hardcoding for speed/fallback
        map_ = {
            ProjectState.MICRO_IDEA: QColor("#94a3b8"),
            ProjectState.IDEA: QColor("#38bdf8"),
            ProjectState.WIP: QColor("#f59e0b"),
            ProjectState.PREVIEW_READY: QColor("#22c55e"),
            ProjectState.ADVANCED: QColor("#a855f7"),
            ProjectState.BROKEN_OR_EMPTY: QColor("#ef4444"),
        }
        return map_.get(state, QColor("#f1f5f9"))
        
    # Helper for action formatting
    # Can move to ProjectState logic if complex
