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
from ...utils import format_smart_date, format_absolute_date
from ...core.activity_heat import calculate_activity_heat, get_heat_color

class ProjectsModel(QAbstractTableModel):
    """Table model for displaying projects."""
    
    # Columns
    COL_SELECT = 0
    COL_NAME = 1
    COL_HEAT = 2
    COL_AUDIBILITY = 3
    COL_SAFETY = 4
    COL_LAST_TOUCHED = 5
    COL_CREATED = 6
    COL_PLAYS = 7
    COL_OPENS = 8
    COL_ACTIONS = 9
    
    COLUMNS = ["", "NAME", "HEAT", "AUDIBILITY", "SAFETY", "LAST TOUCHED", "CREATED", "PLAYS", "OPENS", "ACTIONS"]
    
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

    def update_project(self, project_id: int, updated_dict: Dict) -> bool:
        """Update a single project row by id (e.g. after render). Returns True if row was found."""
        for i, p in enumerate(self._projects):
            if p.get('id') == project_id:
                self._projects[i] = updated_dict
                self._prepare_projects([updated_dict])
                top_left = self.index(i, 0)
                bottom_right = self.index(i, self.columnCount() - 1)
                self.dataChanged.emit(top_left, bottom_right, [])
                return True
        return False
        
    def _prepare_projects(self, projects: List[Dict]):
        """Pre-process project data for UI."""
        for p in projects:
            # Ensure render_count is always an integer (handle None, missing, or string)
            render_count = p.get('render_count')
            
            # Convert to int if it's a string or other type, default to 0 if None/missing
            try:
                render_count = int(render_count) if render_count is not None else 0
            except (ValueError, TypeError):
                render_count = 0
            
            p['render_count'] = render_count
            p['has_render'] = bool(render_count > 0)
            
            # Calculate Activity Heat
            # We use updated_at as proxy for flp_mtime if not available, 
            # or try to get file_created_at if that's more appropriate for modification time? No.
            # Ideally scanner puts flp_mtime in signals or we use updated_at.
            # Using updated_at is safe as scanner updates it on scan.
            flp_mtime = p.get('updated_at')
            
            heat_data = calculate_activity_heat(
                flp_mtime=flp_mtime,
                last_opened_at=p.get('last_opened_at'),
                last_rendered_at=p.get('last_rendered_at'),
                open_count=p.get('open_count', 0) or 0,
                play_count=p.get('play_count', 0) or 0,
                last_played_ts=p.get('last_played_ts')
            )
            p['heat_data'] = heat_data
            p['heat_label'] = heat_data['label']
            p['heat_score'] = heat_data['score']
            
            # Prepare confidence and lock data
            confidence_score = p.get('confidence_score')
            try:
                confidence_score = int(confidence_score) if confidence_score is not None else 100
            except (ValueError, TypeError):
                confidence_score = 100
            p['confidence_score'] = confidence_score
            
            user_locked = p.get('user_locked')
            p['user_locked'] = bool(user_locked) if user_locked is not None else False
            
            # Get match reasons from identity system (for tooltip)
            p['match_reasons'] = self._get_match_reasons(p.get('id'))
            
            # Legacy fallback for older cached signals if needed (only if still no render)
            # This helps with projects scanned before renders table existed
            if not p['has_render'] and 'signals' in p and p['signals']:
                try:
                    s = json.loads(p['signals']) if isinstance(p['signals'], str) else p['signals']
                    raw = s.get('raw', {})
                    p['has_render_root'] = raw.get('has_render_root', False)
                    # Only use legacy fallback if render_count is truly 0
                    if render_count == 0:
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
            if col == self.COL_NAME:
                return project.get('name', '')
            elif col == self.COL_HEAT:
                return project.get('heat_label', 'Cold')
            elif col == self.COL_AUDIBILITY:
                # Delegate renders dot
                return ""
            elif col == self.COL_SAFETY:
                # Delegate renders dot
                return ""
            elif col == self.COL_LAST_TOUCHED:
                data = project.get('heat_data', {})
                ts = data.get('last_touch_ts')
                return format_smart_date(ts) if ts else "-"
            elif col == self.COL_CREATED:
                ts = project.get('file_created_at') or project.get('created_at')
                return format_smart_date(ts) if ts else "-"
            elif col == self.COL_PLAYS:
                return str(project.get('play_count', 0) or 0)
            elif col == self.COL_OPENS:
                return str(project.get('open_count', 0) or 0)
            elif col == self.COL_ACTIONS:
                return ""
                
        elif role == Qt.ItemDataRole.ToolTipRole:
            if col == self.COL_HEAT:
                data = project.get('heat_data', {})
                return f"Score: {data.get('score', 0)}/100"
            elif col == self.COL_CREATED:
                # Show exact date/time on hover (Windows Explorer style)
                ts = project.get('file_created_at') or project.get('created_at')
                if ts:
                    return f"Created: {format_absolute_date(ts)}"
                return None
            elif col == self.COL_AUDIBILITY:
                ready = project.get('render_status') == 'preview_ready' or project.get('has_render')
                return "Preview Ready" if ready else "Unheard"
            elif col == self.COL_SAFETY:
                failed = project.get('last_render_failed_at')
                attempted = project.get('render_attempted_count', 0) > 0
                if failed: return f"Unstable: {project.get('last_render_failed_reason')}"
                if attempted: return "OK"
                return "Unknown (Never rendered)"
            elif col == self.COL_NAME:
                return project.get('path', '')
                
        elif role == Qt.ItemDataRole.CheckStateRole:
            if col == self.COL_SELECT:
                pid = project.get('id')
                return Qt.CheckState.Checked if pid in self._checked_ids else Qt.CheckState.Unchecked
                
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_HEAT:
                label = project.get('heat_label', 'Cold')
                return QBrush(QColor(get_heat_color(label)))
            elif col == self.COL_NAME:
                return QBrush(QColor("#f1f5f9"))
            elif col == self.COL_CREATED:
                return QBrush(QColor("#94a3b8"))
            elif col in [self.COL_LAST_TOUCHED, self.COL_PLAYS, self.COL_OPENS]:
                return QBrush(QColor("#94a3b8"))
                
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [self.COL_HEAT, self.COL_CREATED, self.COL_LAST_TOUCHED, self.COL_PLAYS, self.COL_OPENS, self.COL_AUDIBILITY, self.COL_SAFETY]:
                return int(Qt.AlignmentFlag.AlignCenter)
            elif col == self.COL_NAME:
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
    
    def _get_match_reasons(self, project_id: int) -> List[str]:
        """Get top match reasons from file_signals for a project."""
        if not project_id:
            return []
        
        try:
            from ...database import query
            from ...scanner.identity.identity_store import IdentityStore
            
            store = IdentityStore()
            primary_render = store.get_primary_render(project_id)
            
            if not primary_render:
                return []
            
            file_id = primary_render.get('id')
            if not file_id:
                return []
            
            signals = store.get_file_signals(file_id)
            
            # Extract top reasons from signals
            reasons = []
            for signal in signals:
                if signal.signal_type.value == 'name_tokens' and signal.value_text:
                    reasons.append(f"Name tokens: {signal.value_text[:30]}")
                elif signal.signal_type.value == 'mtime_delta' and signal.value_num is not None:
                    delta_hours = signal.value_num / 3600
                    if delta_hours <= 1:
                        reasons.append(f"Modified within 1 hour")
                    elif delta_hours <= 24:
                        reasons.append(f"Modified within {int(delta_hours)} hours")
                elif signal.signal_type.value == 'previously_seen_fingerprint':
                    reasons.append("Previously seen (fingerprint match)")
            
            return reasons[:3]  # Top 3 reasons
            
        except Exception:
            return []
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort the model by the given column."""
        self.beginResetModel()
        
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        # Define sort key based on column
        def get_sort_key(project):
            if column == self.COL_NAME:
                return (project.get('name', '') or '').lower()
            elif column == self.COL_HEAT:
                return project.get('heat_score', 0)
            elif column == self.COL_LAST_TOUCHED:
                data = project.get('heat_data', {})
                return data.get('last_touch_ts', 0)
            elif column == self.COL_CREATED:
                # Use file_created_at for sorting (original file creation date)
                return project.get('file_created_at') or project.get('created_at', 0) or 0
            elif column == self.COL_PLAYS:
                return project.get('play_count', 0)
            elif column == self.COL_OPENS:
                return project.get('open_count', 0)
            elif column == self.COL_AUDIBILITY:
                return project.get('has_render', False)
            elif column == self.COL_SAFETY:
                # OK > Unknown > Failed
                failed = project.get('last_render_failed_at')
                attempted = project.get('render_attempted_count', 0) > 0
                if failed: return 0 # Unstable
                if attempted: return 2 # OK
                return 1 # Unknown
            else:
                return project.get('name', '') or ''
        
        try:
            self._projects.sort(key=get_sort_key, reverse=reverse)
        except Exception:
            pass  # If sort fails, keep original order
        
        self.endResetModel()
