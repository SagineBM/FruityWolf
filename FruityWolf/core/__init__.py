"""
FruityWolf Core Module

Core configuration, paths, and dataclasses.
"""

from .config import (
    # App metadata
    __app_name__,
    __version__,
    __author__,
    __description__,
    
    # Path functions
    get_app_data_path,
    get_cache_path,
    get_waveform_cache_path,
    get_db_path,
    get_config_path,
    get_log_path,
    
    # Settings
    PlayerSettings,
    UISettings,
    ScanSettings,
    AnalysisSettings,
    AppSettings,
    
    # Constants
    AUDIO_EXTENSIONS,
    PROJECT_EXTENSIONS,
    WAVEFORM_BINS,
    WAVEFORM_CACHE_MAX_MB,
    KEYS,
    DEFAULT_MOOD_TAGS,
    DEFAULT_GENRE_TAGS,
)

__all__ = [
    '__app_name__',
    '__version__',
    '__author__',
    '__description__',
    'get_app_data_path',
    'get_cache_path',
    'get_waveform_cache_path',
    'get_db_path',
    'get_config_path',
    'get_log_path',
    'PlayerSettings',
    'UISettings',
    'ScanSettings',
    'AnalysisSettings',
    'AppSettings',
    'AUDIO_EXTENSIONS',
    'PROJECT_EXTENSIONS',
    'WAVEFORM_BINS',
    'WAVEFORM_CACHE_MAX_MB',
    'KEYS',
    'DEFAULT_MOOD_TAGS',
    'DEFAULT_GENRE_TAGS',
]
