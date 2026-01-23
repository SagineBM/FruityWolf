"""
Waveform Widget

A Qt widget for displaying Spotify-grade waveform visualization with:
- Click-to-seek
- Playhead indicator
- Hover time tooltip
- Optional zoom support
"""

import logging
from typing import Optional, Tuple
import numpy as np

from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Signal, Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QLinearGradient, 
    QMouseEvent, QPaintEvent, QResizeEvent
)

logger = logging.getLogger(__name__)


class WaveformWidget(QWidget):
    """
    Interactive waveform display widget.
    
    Features:
    - Renders waveform peaks as filled bars
    - Shows playhead position
    - Click-to-seek support
    - Hover tooltip with time
    - Smooth gradient coloring
    
    Signals:
        seek_requested(float): Position 0-1 where user clicked
        position_hovered(float): Position 0-1 where mouse is hovering
    """
    
    seek_requested = Signal(float)
    position_hovered = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Waveform data
        self._peaks_min: Optional[np.ndarray] = None
        self._peaks_max: Optional[np.ndarray] = None
        self._duration: float = 0.0
        
        # Playback position (0-1)
        self._position: float = 0.0
        
        # Visual settings
        self._waveform_color = QColor("#38bdf8")  # Sky blue
        self._played_color = QColor("#22d3ee")     # Cyan blue
        self._playhead_color = QColor("#f1f5f9")   # White
        self._background_color = QColor("#1e2836") # Dark slate
        self._hover_color = QColor(255, 255, 255, 80)
        
        # Interaction state
        self._hover_pos: Optional[float] = None
        self._is_dragging = False
        
        # Enable mouse tracking for hover
        self.setMouseTracking(True)
        
        # Minimum size
        self.setMinimumHeight(40)
        self.setMinimumWidth(100)
        
        # Cursor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def set_waveform(self, peaks_min: np.ndarray, peaks_max: np.ndarray, duration: float):
        """Set waveform data to display."""
        self._peaks_min = peaks_min
        self._peaks_max = peaks_max
        self._duration = duration
        self.update()
    
    def clear_waveform(self):
        """Clear waveform data."""
        self._peaks_min = None
        self._peaks_max = None
        self._duration = 0.0
        self._position = 0.0
        self.update()
    
    def set_position(self, position: float):
        """Set playhead position (0-1)."""
        self._position = max(0.0, min(1.0, position))
        self.update()
    
    def set_colors(self, waveform: str = None, played: str = None, 
                   playhead: str = None, background: str = None):
        """Set custom colors for the waveform."""
        if waveform:
            self._waveform_color = QColor(waveform)
        if played:
            self._played_color = QColor(played)
        if playhead:
            self._playhead_color = QColor(playhead)
        if background:
            self._background_color = QColor(background)
        self.update()
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the waveform."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        center_y = height / 2
        
        # Background
        painter.fillRect(rect, self._background_color)
        
        # If no waveform data, draw placeholder
        if self._peaks_min is None or self._peaks_max is None or len(self._peaks_min) == 0:
            painter.setPen(QColor("#475569"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No waveform")
            return
        
        # Resample waveform to widget width
        num_bars = min(width, len(self._peaks_min))
        if num_bars <= 0:
            return
        
        indices = np.linspace(0, len(self._peaks_min) - 1, num_bars).astype(int)
        peaks_min = self._peaks_min[indices]
        peaks_max = self._peaks_max[indices]
        
        # Normalize peaks to fit height
        max_amplitude = max(abs(peaks_min.min()), abs(peaks_max.max()), 0.001)
        scale = (height * 0.4) / max_amplitude
        
        # Bar width
        bar_width = max(1, width / num_bars)
        
        # Playhead position in pixels
        playhead_x = self._position * width
        
        # Draw waveform bars
        for i in range(num_bars):
            x = i * bar_width
            
            # Peak values scaled to pixels
            y_min = peaks_min[i] * scale
            y_max = peaks_max[i] * scale
            
            # Draw bar from center
            bar_top = center_y - y_max
            bar_bottom = center_y - y_min
            bar_height = max(1, bar_bottom - bar_top)
            
            # Color based on position (played vs unplayed)
            if x < playhead_x:
                color = self._played_color
            else:
                color = self._waveform_color
            
            # Draw with slight transparency gradient
            color.setAlpha(200)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(x, bar_top, bar_width - 0.5, bar_height))
        
        # Draw playhead line
        if self._position > 0:
            painter.setPen(self._playhead_color)
            painter.drawLine(int(playhead_x), 0, int(playhead_x), height)
        
        # Draw hover indicator
        if self._hover_pos is not None:
            hover_x = self._hover_pos * width
            hover_color = QColor(255, 255, 255, 100)
            painter.setPen(hover_color)
            painter.drawLine(int(hover_x), 0, int(hover_x), height)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for seeking."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._seek_to_event(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        self._is_dragging = False
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for hover tooltip and drag seeking."""
        pos = event.position()
        position = max(0.0, min(1.0, pos.x() / self.width()))
        self._hover_pos = position
        self.position_hovered.emit(position)
        
        # Show time tooltip
        if self._duration > 0:
            time_at_pos = position * self._duration
            time_str = self._format_time(time_at_pos)
            QToolTip.showText(event.globalPosition().toPoint(), time_str, self)
        
        # Drag seeking
        if self._is_dragging:
            self._seek_to_event(event)
        
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover_pos = None
        self.update()
    
    def _seek_to_event(self, event: QMouseEvent):
        """Emit seek signal based on mouse position."""
        pos = event.position()
        position = max(0.0, min(1.0, pos.x() / self.width()))
        self.seek_requested.emit(position)


class MiniWaveformWidget(WaveformWidget):
    """
    Compact waveform widget for player bar.
    
    Same functionality as WaveformWidget but with:
    - Smaller default height
    - Thinner bars
    - More compact styling
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(24)
        self.setMaximumHeight(40)
        
        # Slightly different colors for mini version
        self._waveform_color = QColor("#64748b")  # Slate
        self._played_color = QColor("#38bdf8")     # Sky blue
    
    def paintEvent(self, event: QPaintEvent):
        """Paint mini waveform with simpler style."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        center_y = height / 2
        
        # Background (transparent or very subtle)
        painter.fillRect(rect, QColor(0, 0, 0, 0))
        
        # If no waveform data, draw simple progress bar
        if self._peaks_min is None or self._peaks_max is None:
            # Draw empty track line
            painter.setPen(QColor("#334155"))
            painter.drawLine(0, int(center_y), width, int(center_y))
            
            # Draw played portion
            if self._position > 0:
                playhead_x = int(self._position * width)
                painter.setPen(self._played_color)
                painter.drawLine(0, int(center_y), playhead_x, int(center_y))
            return
        
        # Draw simplified waveform (fewer bars, centered envelope)
        num_bars = min(width // 2, len(self._peaks_min))
        if num_bars <= 0:
            return
        
        indices = np.linspace(0, len(self._peaks_min) - 1, num_bars).astype(int)
        peaks_max = np.abs(self._peaks_max[indices])
        
        max_amplitude = max(peaks_max.max(), 0.001)
        scale = (height * 0.35) / max_amplitude
        
        bar_width = max(1, width / num_bars)
        playhead_x = self._position * width
        
        for i in range(num_bars):
            x = i * bar_width
            bar_height = max(2, peaks_max[i] * scale)
            
            color = self._played_color if x < playhead_x else self._waveform_color
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(x, center_y - bar_height, bar_width - 1, bar_height * 2))
        
        # Playhead
        if self._position > 0:
            painter.setPen(self._playhead_color)
            painter.drawLine(int(playhead_x), 0, int(playhead_x), height)
