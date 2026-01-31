"""
Cover Art Management Service

Handles user-uploaded covers for projects, tracks, and playlists.
Stores covers in a dedicated directory and manages database references.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..database import execute, query_one

logger = logging.getLogger(__name__)

# Cover storage directory (relative to user data directory)
COVERS_DIR = "covers"

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def get_covers_directory() -> Path:
    """Get the directory where covers are stored."""
    # Get user data directory from config
    try:
        from ..core.config import get_app_data_path
        app_data_dir = get_app_data_path()
    except ImportError:
        # Fallback to app directory
        app_data_dir = Path(__file__).parent.parent.parent
    
    covers_dir = app_data_dir / COVERS_DIR
    covers_dir.mkdir(parents=True, exist_ok=True)
    return covers_dir


def save_cover_image(source_path: str, entity_type: str, entity_id: int) -> Optional[str]:
    """
    Copy and save a cover image for an entity.
    
    Args:
        source_path: Path to source image file
        entity_type: 'project', 'track', or 'playlist'
        entity_id: ID of the entity
    
    Returns:
        Path to saved cover image, or None on error
    """
    try:
        source = Path(source_path)
        if not source.exists():
            logger.error(f"Source cover image not found: {source_path}")
            return None
        
        # Validate format
        ext = source.suffix.lower()
        if ext not in SUPPORTED_FORMATS:
            logger.error(f"Unsupported image format: {ext}")
            return None
        
        # Generate destination filename: {entity_type}_{id}_{timestamp}.{ext}
        timestamp = int(datetime.now().timestamp())
        dest_filename = f"{entity_type}_{entity_id}_{timestamp}{ext}"
        dest_path = get_covers_directory() / dest_filename
        
        # Copy file
        shutil.copy2(source, dest_path)
        logger.info(f"Saved cover: {dest_path}")
        
        return str(dest_path)
    except Exception as e:
        logger.error(f"Failed to save cover image: {e}")
        return None


def delete_cover_image(cover_path: str) -> bool:
    """
    Delete a cover image file.
    
    Args:
        cover_path: Path to cover image
    
    Returns:
        True if deleted, False on error
    """
    try:
        if not cover_path:
            return False
        
        path = Path(cover_path)
        # Only delete if in covers directory (safety check)
        covers_dir = get_covers_directory()
        if covers_dir in path.parents or path.parent == covers_dir:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted cover: {cover_path}")
                return True
        else:
            logger.warning(f"Refusing to delete cover outside covers directory: {cover_path}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete cover image: {e}")
        return False


def set_project_cover(project_id: int, cover_path: Optional[str]) -> bool:
    """
    Set custom cover for a project.
    
    Args:
        project_id: Project ID
        cover_path: Path to cover image (None to remove)
    
    Returns:
        True on success
    """
    try:
        if cover_path:
            execute(
                "UPDATE projects SET custom_cover_path = ? WHERE id = ?",
                (cover_path, project_id)
            )
        else:
            # Remove custom cover
            row = query_one("SELECT custom_cover_path FROM projects WHERE id = ?", (project_id,))
            if row and row['custom_cover_path']:
                delete_cover_image(row['custom_cover_path'])
            execute(
                "UPDATE projects SET custom_cover_path = NULL WHERE id = ?",
                (project_id,)
            )
        # execute() already commits automatically (unless in batch mode)
        return True
    except Exception as e:
        logger.error(f"Failed to set project cover: {e}")
        return False


def set_track_cover(track_id: int, cover_path: Optional[str]) -> bool:
    """
    Set custom cover for a track.
    
    Args:
        track_id: Track ID
        cover_path: Path to cover image (None to remove)
    
    Returns:
        True on success
    """
    try:
        if cover_path:
            execute(
                "UPDATE tracks SET cover_path = ? WHERE id = ?",
                (cover_path, track_id)
            )
        else:
            # Remove custom cover
            row = query_one("SELECT cover_path FROM tracks WHERE id = ?", (track_id,))
            if row and row['cover_path']:
                delete_cover_image(row['cover_path'])
            execute(
                "UPDATE tracks SET cover_path = NULL WHERE id = ?",
                (track_id,)
            )
        # execute() already commits automatically (unless in batch mode)
        return True
    except Exception as e:
        logger.error(f"Failed to set track cover: {e}")
        return False


def set_playlist_cover(playlist_id: int, cover_path: Optional[str]) -> bool:
    """
    Set custom cover for a playlist.
    
    Args:
        playlist_id: Playlist ID
        cover_path: Path to cover image (None to remove)
    
    Returns:
        True on success
    """
    try:
        if cover_path:
            execute(
                "UPDATE playlists SET cover_path = ? WHERE id = ?",
                (cover_path, playlist_id)
            )
        else:
            # Remove custom cover
            row = query_one("SELECT cover_path FROM playlists WHERE id = ?", (playlist_id,))
            if row and row['cover_path']:
                delete_cover_image(row['cover_path'])
            execute(
                "UPDATE playlists SET cover_path = NULL WHERE id = ?",
                (playlist_id,)
            )
        # execute() already commits automatically (unless in batch mode)
        return True
    except Exception as e:
        logger.error(f"Failed to set playlist cover: {e}")
        return False


def get_project_cover_path(project_id: int, project_path: Optional[str] = None) -> Optional[str]:
    """
    Get cover path for a project (custom first, then auto-detected).
    
    Args:
        project_id: Project ID
        project_path: Optional project folder path for auto-detection
    
    Returns:
        Path to cover image, or None
    """
    # Check custom cover first
    row = query_one("SELECT custom_cover_path FROM projects WHERE id = ?", (project_id,))
    if row and row['custom_cover_path']:
        custom_path = row['custom_cover_path']
        if os.path.exists(custom_path):
            return custom_path
    
    # Fall back to auto-detection
    if project_path:
        from ..utils.images import get_cover_art
        return get_cover_art(project_path)
    
    return None


def get_track_cover_path(track_id: int, project_path: Optional[str] = None) -> Optional[str]:
    """
    Get cover path for a track (custom first, then project cover).
    
    Args:
        track_id: Track ID
        project_path: Optional project folder path for fallback
    
    Returns:
        Path to cover image, or None
    """
    # Check custom cover first
    row = query_one("SELECT cover_path FROM tracks WHERE id = ?", (track_id,))
    if row and row['cover_path']:
        custom_path = row['cover_path']
        if os.path.exists(custom_path):
            return custom_path
    
    # Fall back to project cover
    if project_path:
        from ..utils.images import get_cover_art
        return get_cover_art(project_path)
    
    return None


def get_playlist_cover_path(playlist_id: int) -> Optional[str]:
    """
    Get cover path for a playlist.
    
    Args:
        playlist_id: Playlist ID
    
    Returns:
        Path to cover image, or None
    """
    row = query_one("SELECT cover_path FROM playlists WHERE id = ?", (playlist_id,))
    if row and row['cover_path']:
        cover_path = row['cover_path']
        if os.path.exists(cover_path):
            return cover_path
    return None
