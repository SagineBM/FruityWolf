"""
Services Module

Business logic services for FruityWolf.
"""

from .cover_manager import (
    get_covers_directory,
    save_cover_image,
    delete_cover_image,
    set_project_cover,
    set_track_cover,
    set_playlist_cover,
    get_project_cover_path,
    get_track_cover_path,
    get_playlist_cover_path,
)

__all__ = [
    'get_covers_directory',
    'save_cover_image',
    'delete_cover_image',
    'set_project_cover',
    'set_track_cover',
    'set_playlist_cover',
    'get_project_cover_path',
    'get_track_cover_path',
    'get_playlist_cover_path',
]
