"""
FruityWolf — Spotify for Producers

A beautiful, modern library manager and player for FL Studio project folders.
Unofficial FL Studio project library manager - not affiliated with Image-Line.
"""

from .core import (
    __app_name__,
    __version__,
    __author__,
    __description__,
    get_app_data_path,
    get_cache_path,
    get_db_path,
)

__all__ = [
    '__app_name__',
    '__version__',
    '__author__',
    '__description__',
    'get_app_data_path',
    'get_cache_path',
    'get_db_path',
]
