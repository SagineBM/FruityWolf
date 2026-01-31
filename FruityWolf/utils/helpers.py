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
    Format timestamp using smart relative dating (Windows Explorer style).
    
    < 1 min: "Just now"
    < 1 hr: "5m ago"
    < 24 hr: "2h ago"
    < 7 days: "3d ago"
    < 30 days: "2w ago" or "Xd ago"
    This year: "Jan 19"
    Else: "Jan 29 2026" (Month and year)
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
    elif seconds < 604800:  # 7 days
        return f"{int(seconds / 86400)}d ago"
    elif seconds < 2592000:  # 30 days
        weeks = int(seconds / 604800)
        if weeks == 1:
            return "1 week ago"
        elif weeks < 4:
            return f"{weeks} weeks ago"
        else:
            return f"{int(seconds / 86400)}d ago"
    
    if dt.year == now.year:
        return dt.strftime("%b %d")
    
    return dt.strftime("%b %d %Y")


def format_absolute_date(timestamp: Optional[float]) -> str:
    """
    Format timestamp as absolute date/time (Windows Explorer style).
    
    Returns: "27/01/2026 21:51" format
    """
    if not timestamp:
        return "--"
    
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, OSError):
        return "--"


def format_date_with_tooltip(timestamp: Optional[float]) -> tuple:
    """
    Returns (display_text, tooltip_text) for date display.
    
    Display: Relative date ("3d ago", "Jan 19")
    Tooltip: Exact date ("27/01/2026 21:51")
    """
    display = format_smart_date(timestamp)
    tooltip = format_absolute_date(timestamp)
    return display, tooltip


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
    """
    Setup application logging.
    
    Logs to both console and a rotating file.
    """
    from ..core.config import get_log_path
    from logging.handlers import RotatingFileHandler
    
    level = logging.DEBUG if debug else logging.INFO
    log_path = get_log_path()
    
    # Formatters
    console_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    file_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%H:%M:%S'
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(console_format, datefmt=date_format))
    root_logger.addHandler(console_handler)
    
    # File Handler (Rotating: 1MB max, 3 backups)
    try:
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=1024*1024, 
            backupCount=3, 
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(file_format))
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Fallback if we can't write to log file
        print(f"Warning: Could not setup file logging: {e}")
    
    # Reduce noise from other libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('vlc').setLevel(logging.WARNING)
    logging.getLogger('watchdog').setLevel(logging.WARNING)


from contextlib import contextmanager

@contextmanager
def log_exception(logger_instance: logging.Logger, context_msg: str = "An error occurred"):
    """
    Context manager to catch and log exceptions.
    
    Usage:
        with log_exception(logger, "Failed to process file"):
            process_file(path)
    """
    try:
        yield
    except Exception as e:
        logger_instance.error(f"{context_msg}: {e}", exc_info=True)


def safe_json_loads(json_str: Optional[str], default=None):
    """Safely load JSON string, returning default on failure."""
    import json
    if not json_str:
        return default if default is not None else {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


