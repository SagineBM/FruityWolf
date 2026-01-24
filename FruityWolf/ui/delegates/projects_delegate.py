"""
Projects Delegate

QStyledItemDelegate for rendering action buttons and handling clicks.
"""

from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QApplication, QAbstractItemView
from PySide6.QtCore import Qt, QModelIndex, QRect, QPoint, Signal, QAbstractItemModel, QEvent
from PySide6.QtGui import QPainter, QIcon, QMouseEvent, QColor

from ...utils import get_icon

class ProjectsDelegate(QStyledItemDelegate):
    """Delegate for drawing action buttons in the last column."""
    
    # Signals to communicate actions back to View
    open_folder_clicked = Signal(dict)
    open_flp_clicked = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.btn_size = 24
        self.spacing = 8
        self.hover_row = -1
        self.hover_col = -1
        self.hover_btn = None # 'folder' or 'flp'
        
    def paint(self, painter: QPainter, option: "QStyleOptionViewItem", index: QModelIndex):
        if index.column() != 6: # Actions column
            super().paint(painter, option, index)
            return
            
        project = index.data(Qt.ItemDataRole.UserRole)
        if not project:
            return
            
        painter.save()
        
        # Determine geometry
        rect = option.rect
        center_y = rect.y() + rect.height() // 2
        
        # Calculate button positions (centered)
        total_width = (self.btn_size * 2) + self.spacing
        start_x = rect.x() + (rect.width() - total_width) // 2
        
        folder_rect = QRect(start_x, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
        flp_rect = QRect(start_x + self.btn_size + self.spacing, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
        
        # Check hover state
        is_hover_row = (index.row() == self.hover_row)
        
        # Draw Folder Button
        folder_icon = get_icon("folder_open", QColor("#94a3b8"), 16)
        if is_hover_row and self.hover_btn == 'folder':
            folder_icon = get_icon("folder_open", QColor("#38bdf8"), 16)
            
        folder_icon.paint(painter, folder_rect, Qt.AlignmentFlag.AlignCenter)
        
        # Draw FLP Button
        has_flp = project.get('flp_path') and project.get('flp_path').endswith('.flp')
        if has_flp:
            flp_color = QColor("#22c55e") # Green
            if is_hover_row and self.hover_btn == 'flp':
                flp_color = QColor("#4ade80") # Lighter green
                
            flp_icon = get_icon("fl_studio", flp_color, 16)
            flp_icon.paint(painter, flp_rect, Qt.AlignmentFlag.AlignCenter)
        else:
            # Disabled state
            flp_icon = get_icon("fl_studio", QColor("#334155"), 16)
            flp_icon.paint(painter, flp_rect, Qt.AlignmentFlag.AlignCenter)
            
        painter.restore()
        
    def editorEvent(self, event: QEvent, model: QAbstractItemModel, option: "QStyleOptionViewItem", index: QModelIndex) -> bool:
        if index.column() != 6:
            return False
            
        if event.type() == QEvent.Type.MouseButtonRelease:
             # Handle Click
             project = index.data(Qt.ItemDataRole.UserRole)
             if not project: return False
             
             mouse_pos = event.pos()
             
             # Re-calc geometry (must match paint)
             rect = option.rect
             center_y = rect.y() + rect.height() // 2
             total_width = (self.btn_size * 2) + self.spacing
             start_x = rect.x() + (rect.width() - total_width) // 2
             
             folder_rect = QRect(start_x, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
             flp_rect = QRect(start_x + self.btn_size + self.spacing, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
             
             if folder_rect.contains(mouse_pos):
                 self.open_folder_clicked.emit(project)
                 return True
                 
             if flp_rect.contains(mouse_pos):
                 has_flp = project.get('flp_path') and project.get('flp_path').endswith('.flp')
                 if has_flp:
                     self.open_flp_clicked.emit(project)
                 return True
                 
        elif event.type() == QEvent.Type.MouseMove:
            # Handle Hover
            mouse_pos = event.pos()
            self.hover_row = index.row()
            self.hover_col = index.column()
            
            # Re-calc geometry
            rect = option.rect
            center_y = rect.y() + rect.height() // 2
            total_width = (self.btn_size * 2) + self.spacing
            start_x = rect.x() + (rect.width() - total_width) // 2
            
            folder_rect = QRect(start_x, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
            flp_rect = QRect(start_x + self.btn_size + self.spacing, center_y - self.btn_size // 2, self.btn_size, self.btn_size)
            
            if folder_rect.contains(mouse_pos):
                self.hover_btn = 'folder'
            elif flp_rect.contains(mouse_pos):
                self.hover_btn = 'flp'
            else:
                self.hover_btn = None
                
            # Trigger repaint
            option.widget.update(index)
            return True
            
        return False
