"""
Custom UI Widgets
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QLayout, QSizePolicy, QStyle, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QRect, QSize, QPoint
from PySide6.QtGui import QPainter, QFontMetrics

class MarqueeLabel(QLabel):
    """Label that scrolls text if it's too long."""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scroll)
        self._timer.setInterval(50)  # 20fps
        self._wait_timer = QTimer(self)
        self._wait_timer.setSingleShot(True)
        self._wait_timer.timeout.connect(self._start_scroll)
        
        self.paused = False
        self.setFixedHeight(30) # Fixed height to avoid jumps
        
    def setText(self, text):
        super().setText(text)
        self._offset = 0
        self._timer.stop()
        self._wait_timer.start(2000) # Wait 2s before scrolling
        self.update()
        
    def _start_scroll(self):
        if self.fontMetrics().horizontalAdvance(self.text()) > self.width():
            self._timer.start()
            
    def _scroll(self):
        if self.paused:
            return
            
        self._offset += 1
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        if self._offset > text_width + 50:
            self._offset = -self.width()
            
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        
        if text_width < self.width():
            # Center text if fits
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
            return
            
        # Draw scrolled
        y = (self.height() + self.fontMetrics().ascent() - self.fontMetrics().descent()) / 2
        painter.drawText(int(-self._offset), int(y), self.text())
        
    def resizeEvent(self, event):
        self._offset = 0
        self._timer.stop()
        self._wait_timer.start(2000)
        super().resizeEvent(event)

class FlowLayout(QLayout):
    """Layout that arranges items in a flowing grid."""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

class TagChip(QPushButton):
    """Checkable button representing a tag."""
    def __init__(self, text, color="#6366f1", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.color = color
        
        # Style
        # We'll use styleSheet for simplicity
        base_style = f"""
            QPushButton {{
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 6px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {color};
                color: {color};
            }}
            QPushButton:checked {{
                background-color: {color};
                color: #ffffff;
                border-color: {color};
            }}
        """
        self.setStyleSheet(base_style)


class StatusBadge(QWidget):
    """
    A widget displaying status badges (FLP, Stems, Backup, etc.) 
    as small pills in a flow layout (horizontal).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
    def set_badges(self, badges: list):
        """
        Set status badges.
        
        Args:
            badges: List of dicts with 'text', 'color', 'tooltip'
            Example: [{'text': 'FLP', 'color': '#22c55e', 'tooltip': 'Project file available'}]
        """
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        for badge in badges:
            lbl = QLabel(badge['text'])
            color = badge.get('color', '#94a3b8')
            tooltip = badge.get('tooltip', '')
            
            lbl.setToolTip(tooltip)
            # Use semi-transparent background (hex+20 = ~12% alpha) and border
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {color}20; 
                    color: {color};
                    border: 1px solid {color}40;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            self._layout.addWidget(lbl)
            
        self._layout.addStretch()

