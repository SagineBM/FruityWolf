"""
FruityWolf Core Configuration

Centralized app configuration, paths, and version info.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# =============================================================================
# App Metadata
# =============================================================================

__app_name__ = "FruityWolf"
__version__ = "2.0.0"
__author__ = "FruityWolf Team"
__description__ = "Unofficial FL Studio project library manager"

# =============================================================================
# Path Configuration
# =============================================================================

def get_app_data_path() -> Path:
    """
    Get the application data directory.
    
    Windows: %APPDATA%/FruityWolf
    Linux: ~/.local/share/FruityWolf  
    macOS: ~/Library/Application Support/FruityWolf
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    
    path = Path(base) / __app_name__
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_path() -> Path:
    """Get the cache directory for waveforms and thumbnails."""
    path = get_app_data_path() / 'cache'
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_waveform_cache_path() -> Path:
    """Get the waveform cache directory."""
    path = get_cache_path() / 'waveforms'
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Get the database file path."""
    return get_app_data_path() / 'library.db'


def get_config_path() -> Path:
    """Get the config file path."""
    return get_app_data_path() / 'config.json'


def get_log_path() -> Path:
    """Get the log file path."""
    return get_app_data_path() / 'fruity.log'


# =============================================================================
# Settings Dataclasses
# =============================================================================

@dataclass
class PlayerSettings:
    """Audio player settings."""
    volume: float = 0.8
    shuffle: bool = False
    repeat_mode: str = 'none'  # 'none', 'one', 'all'
    muted: bool = False


@dataclass
class UISettings:
    """User interface settings."""
    theme: str = 'dark'
    sidebar_visible: bool = True
    details_visible: bool = True
    window_width: int = 1400
    window_height: int = 900
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    window_maximized: bool = False


@dataclass
class ScanSettings:
    """Library scanning settings."""
    auto_scan_on_startup: bool = True
    watch_for_changes: bool = True
    scan_interval_minutes: int = 30


@dataclass
class AnalysisSettings:
    """Audio analysis settings."""
    auto_detect_bpm: bool = True
    auto_detect_key: bool = True
    use_librosa: bool = False  # Requires optional dependency


@dataclass
class AppSettings:
    """Complete application settings."""
    player: PlayerSettings = field(default_factory=PlayerSettings)
    ui: UISettings = field(default_factory=UISettings)
    scan: ScanSettings = field(default_factory=ScanSettings)
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)


# =============================================================================
# Audio Constants
# =============================================================================

AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif'}
PROJECT_EXTENSIONS = {'.flp'}

# Waveform configuration
WAVEFORM_BINS = 4000  # Number of peaks to extract
WAVEFORM_CACHE_MAX_MB = 500  # Maximum cache size

# =============================================================================
# Key/Scale Definitions
# =============================================================================

KEYS = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
    'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm'
]

# =============================================================================
# Default Tags
# =============================================================================

DEFAULT_MOOD_TAGS = [
    ('dark', '#1e293b'),
    ('rage', '#ef4444'),
    ('sad', '#6366f1'),
    ('afro', '#f59e0b'),
    ('club', '#ec4899'),
    ('cinematic', '#8b5cf6'),
    ('upbeat', '#22c55e'),
    ('chill', '#06b6d4'),
    ('aggressive', '#dc2626'),
    ('melodic', '#3b82f6'),
    ('ethereal', '#a855f7'),
    ('hype', '#f97316'),
]

DEFAULT_GENRE_TAGS = [
    ('Hip Hop', '#eab308'),
    ('Trap', '#f43f5e'),
    ('R&B', '#a855f7'),
    ('Pop', '#ec4899'),
    ('Electronic', '#06b6d4'),
    ('House', '#22c55e'),
    ('Drill', '#64748b'),
    ('Afrobeats', '#f59e0b'),
    ('Reggaeton', '#10b981'),
    ('Soul', '#8b5cf6'),
    ('Jazz', '#0ea5e9'),
    ('Rock', '#ef4444'),
]
