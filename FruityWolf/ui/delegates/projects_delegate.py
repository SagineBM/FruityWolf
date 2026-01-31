"""
Projects Delegate

QStyledItemDelegate for rendering:
- Action Buttons
- Score Bars
- Next Action Icons
"""

from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QApplication, QAbstractItemView
from PySide6.QtCore import Qt, QModelIndex, QRect, QPoint, Signal, QAbstractItemModel, QEvent
from PySide6.QtGui import QPainter, QIcon, QMouseEvent, QColor, QFont, QBrush

from ...utils import get_icon
from ...classifier.engine import ProjectState
from ..view_models.projects_model import ProjectsModel

class ProjectsDelegate(QStyledItemDelegate):
    """Delegate for drawing rich cells in projects table."""
    
    # Signals
    open_folder_clicked = Signal(dict)
    open_flp_clicked = Signal(dict)
    play_clicked = Signal(dict)
    view_clicked = Signal(dict) # Eye button - shows renders panel
    renders_clicked = Signal(dict) # Renders button
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.btn_size = 24
        self.spacing = 8
        self.hover_row = -1
        self.hover_col = -1
        self.hover_btn = None
        
    def paint(self, painter: QPainter, option: "QStyleOptionViewItem", index: QModelIndex):
        col = index.column()
        
        # 1. SCORE BAR
        if col == ProjectsModel.COL_SCORE:
            self._paint_score(painter, option, index)
            return

        # 2. ACTIONS
        if col == ProjectsModel.COL_ACTIONS:
            self._paint_actions(painter, option, index)
            return
            
        # 3. NEXT ACTION
        if col == ProjectsModel.COL_NEXT_ACTION:
             self._paint_next_action(painter, option, index)
             return
        
        # 4. STATE (with confidence/lock indicators)
        if col == ProjectsModel.COL_STATE:
            self._paint_state_with_indicators(painter, option, index)
            return
            
        super().paint(painter, option, index)
        
    def _paint_score(self, painter: QPainter, option, index):
        painter.save()
        
        # Data
        try:
            score = int(index.data(Qt.ItemDataRole.DisplayRole) or 0)
        except: score = 0
        
        # Config
        rect = option.rect
        bar_height = 6
        bar_width = rect.width() - 20
        x = rect.x() + 10
        y = rect.y() + (rect.height() - bar_height) // 2
        
        # Bg
        bg_rect = QRect(x, y, bar_width, bar_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1e293b"))
        painter.drawRoundedRect(bg_rect, 3, 3)
        
        # Fill
        fill_width = int(bar_width * (score / 100))
        fill_rect = QRect(x, y, fill_width, bar_height)
        
        # Color based on score
        color = QColor("#64748b")
        if score > 80: color = QColor("#22c55e")
        elif score > 50: color = QColor("#38bdf8")
        elif score > 20: color = QColor("#f59e0b")
        
        painter.setBrush(color)
        painter.drawRoundedRect(fill_rect, 3, 3)
        
        # Text? Tooltip? 
        # Plan says "Score Bar".
        
        painter.restore()

    def _paint_next_action(self, painter: QPainter, option, index):
        # Draw Icon + Text manually for better control
        painter.save()
        
        project = index.data(Qt.ItemDataRole.UserRole)
        action_id = project.get('next_action_id')
        label = index.data(Qt.ItemDataRole.DisplayRole)
        
        rect = option.rect
        
        # Icon
        icon_size = 14
        icon_x = rect.x() + 4
        icon_y = rect.y() + (rect.height() - icon_size) // 2
        
        # Simple color circle for now, or fetch icon?
        # get_icon("play", ...) 
        # Actions: render_preview_30s, finish_arrangement, etc.
        # We need a map. For now Generic Action Icon.
        
        action_color = QColor("#cbd5e1")
        if action_id:
            if "render" in action_id: action_color = QColor("#f43f5e")
            if "finish" in action_id: action_color = QColor("#a855f7")
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(action_color)
        painter.drawEllipse(icon_x, icon_y, icon_size, icon_size)
        
        # Text
        text_rect = QRect(icon_x + icon_size + 8, rect.y(), rect.width() - icon_size - 12, rect.height())
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        
        painter.restore()

    def _paint_actions(self, painter: QPainter, option, index):
        # Similar to before
        project = index.data(Qt.ItemDataRole.UserRole)
        if not project: return
        
        painter.save()
        rect = option.rect
        center_y = rect.y() + rect.height() // 2
        
        # Calculate total width needed for all buttons
        total_width = (self.btn_size * 4) + (self.spacing * 3)
        # Ensure buttons fit - if column is too narrow, start from left edge
        if total_width > rect.width():
            start_x = rect.x() + 2  # Small padding from left
        else:
            start_x = rect.x() + (rect.width() - total_width) // 2
        
        play_rect = QRect(start_x, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
        view_rect = QRect(start_x + self.btn_size + self.spacing, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
        folder_rect = QRect(start_x + (self.btn_size * 2) + (self.spacing * 2), center_y - self.btn_size // 2, self.btn_size, self.btn_size)
        flp_rect = QRect(start_x + (self.btn_size * 3) + (self.spacing * 3), center_y - self.btn_size // 2, self.btn_size, self.btn_size)
        
        is_hover_row = (index.row() == self.hover_row)
        
        # Play (if render exists)
        has_render = project.get('has_render_root', False) or project.get('has_render', False)
        play_color = QColor("#38bdf8") if (is_hover_row and self.hover_btn == 'play') else QColor("#94a3b8")
        if not has_render: play_color = QColor("#1e293b") # Dimmed
        get_icon("play", play_color, 16).paint(painter, play_rect, Qt.AlignmentFlag.AlignCenter)
        
        # View (Eye)
        view_color = QColor("#38bdf8") if (is_hover_row and self.hover_btn == 'view') else QColor("#94a3b8")
        get_icon("eye", view_color, 16).paint(painter, view_rect, Qt.AlignmentFlag.AlignCenter)
        
        # Folder
        folder_color = QColor("#38bdf8") if (is_hover_row and self.hover_btn == 'folder') else QColor("#94a3b8")
        get_icon("folder_open", folder_color, 16).paint(painter, folder_rect, Qt.AlignmentFlag.AlignCenter)
        
        # FLP
        has_flp = project.get('flp_path')
        if has_flp:
            flp_color = QColor("#22c55e")
            if is_hover_row and self.hover_btn == 'flp': flp_color = QColor("#4ade80")
            get_icon("fl_studio", flp_color, 16).paint(painter, flp_rect, Qt.AlignmentFlag.AlignCenter)
        else:
            get_icon("fl_studio", QColor("#334155"), 16).paint(painter, flp_rect, Qt.AlignmentFlag.AlignCenter)
            
        painter.restore()
    
    def _paint_state_with_indicators(self, painter: QPainter, option, index):
        """Paint state column with confidence/lock indicators."""
        painter.save()
        
        project = index.data(Qt.ItemDataRole.UserRole)
        if not project:
            super().paint(painter, option, index)
            painter.restore()
            return
        
        rect = option.rect
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        
        # Draw state text
        text_rect = QRect(rect.x() + 4, rect.y(), rect.width() - 40, rect.height())
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        
        # Draw indicators on the right (using Unicode symbols for reliability)
        indicator_x = rect.right() - 36
        indicator_y = rect.y() + (rect.height() - 16) // 2
        
        # Lock indicator (highest priority) - use Unicode pin symbol
        if project.get('user_locked'):
            painter.setPen(QColor("#f59e0b"))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.drawText(QRect(indicator_x, indicator_y, 16, 16), Qt.AlignmentFlag.AlignCenter, "📌")
            indicator_x -= 20
        
        # Confidence indicator - use Unicode symbols
        confidence = project.get('confidence_score', 100)
        painter.setFont(QFont("Arial", 12))
        if confidence >= 80:
            # High confidence - green check
            painter.setPen(QColor("#22c55e"))
            painter.drawText(QRect(indicator_x, indicator_y, 16, 16), Qt.AlignmentFlag.AlignCenter, "✅")
        elif confidence >= 50:
            # Medium confidence - yellow warning
            painter.setPen(QColor("#f59e0b"))
            painter.drawText(QRect(indicator_x, indicator_y, 16, 16), Qt.AlignmentFlag.AlignCenter, "⚠️")
        else:
            # Low confidence - question mark
            painter.setPen(QColor("#64748b"))
            painter.drawText(QRect(indicator_x, indicator_y, 16, 16), Qt.AlignmentFlag.AlignCenter, "❓")
        
        painter.restore()

    def editorEvent(self, event: QEvent, model: QAbstractItemModel, option: "QStyleOptionViewItem", index: QModelIndex) -> bool:
        col = index.column()
        
        if col == ProjectsModel.COL_ACTIONS:
            if event.type() == QEvent.Type.MouseButtonRelease:
                project = index.data(Qt.ItemDataRole.UserRole)
                if not project: return False
                
                mouse_pos = event.pos()
                rect = option.rect
                center_y = rect.y() + rect.height() // 2
                total_width = (self.btn_size * 4) + (self.spacing * 3)
                # Ensure buttons fit - if column is too narrow, start from left edge
                if total_width > rect.width():
                    start_x = rect.x() + 2  # Small padding from left
                else:
                    start_x = rect.x() + (rect.width() - total_width) // 2
                
                play_rect = QRect(start_x, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                view_rect = QRect(start_x + self.btn_size + self.spacing, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                folder_rect = QRect(start_x + (self.btn_size * 2) + (self.spacing * 2), center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                flp_rect = QRect(start_x + (self.btn_size * 3) + (self.spacing * 3), center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                
                if play_rect.contains(mouse_pos):
                    # Always emit play_clicked - let the handler decide if render exists
                    self.play_clicked.emit(project)
                    return True
                if view_rect.contains(mouse_pos):
                    self.view_clicked.emit(project)
                    return True
                if folder_rect.contains(mouse_pos):
                    self.open_folder_clicked.emit(project)
                    return True
                if flp_rect.contains(mouse_pos) and project.get('flp_path'):
                    self.open_flp_clicked.emit(project)
                    return True
                     
            elif event.type() == QEvent.Type.MouseMove:
                self.hover_row = index.row()
                self.hover_col = col
                # Calc logic duped, should factor out
                mouse_pos = event.pos()
                rect = option.rect
                center_y = rect.y() + rect.height() // 2
                total_width = (self.btn_size * 4) + (self.spacing * 3)
                # Ensure buttons fit - if column is too narrow, start from left edge
                if total_width > rect.width():
                    start_x = rect.x() + 2  # Small padding from left
                else:
                    start_x = rect.x() + (rect.width() - total_width) // 2
                play_rect = QRect(start_x, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                view_rect = QRect(start_x + self.btn_size + self.spacing, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                folder_rect = QRect(start_x + (self.btn_size * 2) + (self.spacing * 2), center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                flp_rect = QRect(start_x + (self.btn_size * 3) + (self.spacing * 3), center_y - self.btn_size // 2, self.btn_size, self.btn_size)
                
                if play_rect.contains(mouse_pos): self.hover_btn = 'play'
                elif view_rect.contains(mouse_pos): self.hover_btn = 'view'
                elif folder_rect.contains(mouse_pos): self.hover_btn = 'folder'
                elif flp_rect.contains(mouse_pos): self.hover_btn = 'flp'
                else: self.hover_btn = None
                
                option.widget.update(index)
                return True
                
        return False
