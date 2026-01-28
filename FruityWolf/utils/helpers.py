"""
Utility Functions

Common utilities for FL Library Pro.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_timestamp(timestamp: Optional[int]) -> str:
    """Format Unix timestamp to readable date."""
    if timestamp is None:
        return "--"
    
    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    
    # If today, show time
    if dt.date() == now.date():
        return dt.strftime("Today %H:%M")
    
    # If yesterday
    yesterday = now.date().replace(day=now.day - 1) if now.day > 1 else now.date()
    if dt.date() == yesterday:
        return dt.strftime("Yesterday %H:%M")
    
    # If this year, show month and day
    if dt.year == now.year:
        return dt.strftime("%b %d")
    
    # Otherwise show full date
    return dt.strftime("%Y-%m-%d")


def format_smart_date(timestamp: Optional[float]) -> str:
    """
    Format timestamp using smart relative dating.
    
    < 1 min: "Just now"
    < 1 hr: "5m ago"
    < 24 hr: "2h ago"
    < 7 days: "3d ago"
    This year: "Jan 19"
    Else: "2023" (Year only)
    """
    if not timestamp:
        return "--"
        
    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    elif seconds < 604800: # 7 days
        return f"{int(seconds / 86400)}d ago"
    
    if dt.year == now.year:
        return dt.strftime("%b %d")
    
    return dt.strftime("%Y")


def open_file(path: str) -> bool:
    """Open a file with the default system application."""
    if not path or not os.path.exists(path):
        logger.warning(f"File not found: {path}")
        return False
    
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # Linux/Mac
            subprocess.run(['xdg-open', path], check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to open file {path}: {e}")
        return False


def open_folder(path: str) -> bool:
    """Open a folder in the file explorer."""
    if not path or not os.path.exists(path):
        logger.warning(f"Folder not found: {path}")
        return False
    
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # Linux/Mac
            subprocess.run(['xdg-open', path], check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to open folder {path}: {e}")
        return False


def open_fl_studio(flp_path: str, fl_studio_path: Optional[str] = None) -> bool:
    """Open an FLP file in FL Studio."""
    if not flp_path or not os.path.exists(flp_path):
        logger.warning(f"FLP not found: {flp_path}")
        return False
    
    try:
        if fl_studio_path and os.path.exists(fl_studio_path):
            subprocess.Popen([fl_studio_path, flp_path])
        else:
            # Try default association
            open_file(flp_path)
        return True
    except Exception as e:
        logger.error(f"Failed to open FL Studio: {e}")
        return False


def count_files_in_folder(folder_path: str, extensions: Optional[set] = None) -> int:
    """Count files in a folder, optionally filtered by extension."""
    if not folder_path or not os.path.isdir(folder_path):
        return 0
    
    count = 0
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                if extensions is None:
                    count += 1
                elif os.path.splitext(item)[1].lower() in extensions:
                    count += 1
    except PermissionError:
        pass
    
    return count


def get_folder_size(folder_path: str) -> int:
    """Get total size of files in a folder."""
    if not folder_path or not os.path.isdir(folder_path):
        return 0
    
    total_size = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                try:
                    total_size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except PermissionError:
        pass
    
    return total_size


def generate_gradient_color(text: str) -> tuple:
    """Generate a gradient color pair based on text hash."""
    import hashlib
    
    # Hash the text
    hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
    
    # Generate hue (0-360)
    hue = hash_val % 360
    
    # Convert HSL to RGB (simplified)
    def hsl_to_rgb(h, s, l):
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    
    # Generate two colors (slightly different hues)
    color1 = hsl_to_rgb(hue, 0.7, 0.5)
    color2 = hsl_to_rgb((hue + 30) % 360, 0.6, 0.4)
    
    return color1, color2


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


# Keyboard shortcut helper
class KeyboardShortcut:
    """Helper for keyboard shortcut handling."""
    
    SHORTCUTS = {
        'play_pause': 'Space',
        'next': 'Right',
        'previous': 'Left',
        'volume_up': 'Up',
        'volume_down': 'Down',
        'mute': 'M',
        'search': 'Ctrl+F',
        'favorite': 'Ctrl+L',
        'rescan': 'F5',
        'settings': 'Ctrl+,',
    }
    
    @classmethod
    def get_shortcut(cls, action: str) -> str:
        return cls.SHORTCUTS.get(action, '')
    
    @classmethod
    def get_display_text(cls, action: str) -> str:
        shortcut = cls.get_shortcut(action)
        if not shortcut:
            return ''
        
        # Format for display
        return shortcut.replace('Ctrl+', '⌃').replace('Shift+', '⇧').replace('Alt+', '⌥')


def setup_logging(debug: bool = False):
    """Setup application logging."""
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )
    
    # Reduce noise from other libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('vlc').setLevel(logging.WARNING)
