
import os
import logging
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize
from PySide6.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)

class IconManager:
    """Helper to load and tint SVG icons."""
    
    _instance = None
    
    def __init__(self):
        # Base path to assets
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "FruityWolf_icons")
        self._cache = {}
        
        # Color palette
        self.COLOR_PRIMARY = QColor("#38bdf8")  # Sky Blue
        self.COLOR_TEXT = QColor("#94a3b8")     # Muted Slate
        self.COLOR_WHITE = QColor("#f1f5f9")    # White
        self.COLOR_DANGER = QColor("#ef4444")   # Red
        
        # Icon mapping
        self.ICONS = {
            "play": "play-circle-svgrepo-com.svg",
            "pause": "pause-circle-svgrepo-com.svg", # Note: Might need to find this if missing, fallback to play
            "next": "skip-next-svgrepo-com.svg",
            "prev": "skip-previous-svgrepo-com.svg",
            "repeat": "repeat-svgrepo-com.svg", 
            "repeat_one": "repeat-one-svgrepo-com.svg",
            "library": "checklist-minimalistic-svgrepo-com.svg",
            "playlist": "plaaylist-minimalistic-svgrepo-com.svg",
            "heart": "red-heart-svgrepo-com.svg",
            "folder": "folder-2-svgrepo-com.svg", 
            "folder_open": "folder-open-svgrepo-com.svg",
            "add": "add-circle-svgrepo-com.svg",
            "volume": "volume-svgrepo-com.svg",
            "volume_mute": "volume-cross-svgrepo-com.svg",
            "settings": "settings-svgrepo-com.svg", # Placeholder for settings
            "trash": "trash-bin-trash-svgrepo-com.svg",
            "waveform": "soundwave-svgrepo-com.svg",
            "fl_studio": "fl-studio-mobile-svgrepo-com.svg",
            "search": "search-svgrepo-com.svg", # Fallback
            "sort_alpha": "sort-by-alphabet-svgrepo-com.svg",
            "sort_time": "sort-by-time-svgrepo-com.svg",
            "analyze": "soundwave-svgrepo-com.svg",
            "shuffle": "restart-svgrepo-com.svg",
            "edit": "pen-edit-square-svgrepo-com.svg",
            "scan": "scan-svgrepo-com.svg",
            "tag": "tag-svgrepo-com.svg",
            "audio": "music-note-3-svgrepo-com.svg",
            "back": "arrow-left-svgrepo-com.svg",
            "refresh": "restart-svgrepo-com.svg", 
            "folder_open": "folder-open-svgrepo-com.svg",
            "eye": "eye-svgrepo-com.svg",
            "back-up-database": "back-up-database-svgrepo-com.svg",
            "time-clock": "time-clock-circle-svgrepo-com.svg",
            "time": "time-clock-circle-svgrepo-com.svg",
            "verified-check": "verified-check-svgrepo-com.svg",
            "tuning-2": "tuning-2-svgrepo-com.svg",
            "tuning-3": "tuning-3-svgrepo-com.svg",
            "alert": "alert-circle-svgrepo-com.svg",
        }

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = IconManager()
        return cls._instance

    def icon(self, name, color=None, size=24):
        """Get a QIcon by name, optionally tinted."""
        cache_key = f"{name}_{color.name() if color else 'orig'}_{size}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        filename = self.ICONS.get(name)
        if not filename:
            logger.warning(f"Icon not found in mapping: {name}")
            return QIcon()
            
        path = os.path.join(self.assets_dir, filename)
        if not os.path.exists(path):
            if name == "pause":
                # Generate pause icon
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                
                # Draw two bars
                pen_color = color if color else self.COLOR_TEXT
                painter.setBrush(pen_color)
                painter.setPen(Qt.NoPen)
                
                w = size
                h = size
                bar_w = w * 0.25
                gap = w * 0.2
                x1 = (w - (bar_w * 2 + gap)) / 2
                x2 = x1 + bar_w + gap
                y = h * 0.2
                bar_h = h * 0.6
                
                painter.drawRect(int(x1), int(y), int(bar_w), int(bar_h))
                painter.drawRect(int(x2), int(y), int(bar_w), int(bar_h))
                painter.end()
                
                icon = QIcon(pixmap)
                self._cache[cache_key] = icon
                return icon
                
            logger.warning(f"Icon file missing: {path}")
            return QIcon()
            
        # Render SVG to QPixmap
        renderer = QSvgRenderer(path)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        
        # Tint if needed (source-in composition)
        if color:
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), color)
            
        painter.end()
        
        icon = QIcon(pixmap)
        self._cache[cache_key] = icon
        return icon

# Global accessor
def get_icon(name, color=None, size=24):
    return IconManager.get().icon(name, color, size)
