"""
Playlist Management

Playlist CRUD operations and track management.
"""

import os
import logging
from typing import List, Dict, Optional
from pathlib import Path

from ..database import execute, query, query_one, get_cache_path

logger = logging.getLogger(__name__)


def create_playlist(name: str, description: str = '') -> int:
    """Create a new playlist. Returns the playlist ID."""
    cur = execute(
        "INSERT INTO playlists (name, description) VALUES (?, ?)",
        (name, description)
    )
    return cur.lastrowid


def get_playlist(playlist_id: int) -> Optional[Dict]:
    """Get a playlist by ID."""
    row = query_one("""
        SELECT p.*, COUNT(pt.track_id) as track_count
        FROM playlists p
        LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
        WHERE p.id = ?
        GROUP BY p.id
    """, (playlist_id,))
    return dict(row) if row else None


def get_all_playlists() -> List[Dict]:
    """Get all playlists with track counts."""
    rows = query("""
        SELECT p.*, COUNT(pt.track_id) as track_count
        FROM playlists p
        LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
        GROUP BY p.id
        ORDER BY p.name
    """)
    return [dict(row) for row in rows]


def update_playlist(playlist_id: int, name: Optional[str] = None, description: Optional[str] = None):
    """Update playlist details."""
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if updates:
        updates.append("updated_at = strftime('%s', 'now')")
        params.append(playlist_id)
        execute(
            f"UPDATE playlists SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )


def delete_playlist(playlist_id: int):
    """Delete a playlist and its track associations."""
    execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))


def add_track_to_playlist(playlist_id: int, track_id: int, position: Optional[int] = None):
    """Add a track to a playlist."""
    if position is None:
        # Get max position
        row = query_one(
            "SELECT MAX(position) as max_pos FROM playlist_tracks WHERE playlist_id = ?",
            (playlist_id,)
        )
        position = (row['max_pos'] or 0) + 1
    
    execute(
        "INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
        (playlist_id, track_id, position)
    )
    
    # Update playlist timestamp
    execute(
        "UPDATE playlists SET updated_at = strftime('%s', 'now') WHERE id = ?",
        (playlist_id,)
    )


def remove_track_from_playlist(playlist_id: int, track_id: int):
    """Remove a track from a playlist."""
    execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id)
    )
    
    # Update playlist timestamp
    execute(
        "UPDATE playlists SET updated_at = strftime('%s', 'now') WHERE id = ?",
        (playlist_id,)
    )


def get_playlist_tracks(playlist_id: int) -> List[Dict]:
    """Get all tracks in a playlist, ordered by position."""
    rows = query("""
        SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
               pt.position
        FROM tracks t
        JOIN projects p ON t.project_id = p.id
        JOIN playlist_tracks pt ON t.id = pt.track_id
        WHERE pt.playlist_id = ?
        ORDER BY pt.position
    """, (playlist_id,))
    return [dict(row) for row in rows]


def reorder_playlist_track(playlist_id: int, track_id: int, new_position: int):
    """Move a track to a new position in the playlist."""
    # Get current position
    row = query_one(
        "SELECT position FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id)
    )
    
    if not row:
        return
    
    old_position = row['position']
    
    if new_position == old_position:
        return
    
    if new_position < old_position:
        # Moving up - shift others down
        execute("""
            UPDATE playlist_tracks 
            SET position = position + 1
            WHERE playlist_id = ? AND position >= ? AND position < ?
        """, (playlist_id, new_position, old_position))
    else:
        # Moving down - shift others up
        execute("""
            UPDATE playlist_tracks 
            SET position = position - 1
            WHERE playlist_id = ? AND position > ? AND position <= ?
        """, (playlist_id, old_position, new_position))
    
    # Update track position
    execute(
        "UPDATE playlist_tracks SET position = ? WHERE playlist_id = ? AND track_id = ?",
        (new_position, playlist_id, track_id)
    )


def export_playlist_m3u(playlist_id: int, output_path: str) -> bool:
    """Export playlist to M3U file."""
    playlist = get_playlist(playlist_id)
    if not playlist:
        return False
    
    tracks = get_playlist_tracks(playlist_id)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            f.write(f'#PLAYLIST:{playlist["name"]}\n\n')
            
            for track in tracks:
                duration = int(track.get('duration', 0))
                title = track.get('title', 'Unknown')
                path = track.get('path', '')
                
                f.write(f'#EXTINF:{duration},{title}\n')
                f.write(f'{path}\n')
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to export playlist: {e}")
        return False


def generate_playlist_cover(playlist_id: int) -> Optional[str]:
    """Generate a collage cover image for a playlist."""
    try:
        from PIL import Image
        
        tracks = get_playlist_tracks(playlist_id)[:4]
        if not tracks:
            return None
        
        # Get track cover images or generate gradients
        size = 300
        collage = Image.new('RGB', (size, size), (24, 24, 24))
        
        cell_size = size // 2
        
        for i, track in enumerate(tracks):
            x = (i % 2) * cell_size
            y = (i // 2) * cell_size
            
            # Generate gradient based on track title
            title = track.get('title', 'A')
            hue = (ord(title[0]) * 137) % 360
            
            cell = Image.new('RGB', (cell_size, cell_size))
            for py in range(cell_size):
                for px in range(cell_size):
                    # Simple gradient
                    r = int(29 + (py / cell_size) * 20)
                    g = int(185 - (py / cell_size) * 30)
                    b = int(84 + (px / cell_size) * 20)
                    cell.putpixel((px, py), (r, g, b))
            
            collage.paste(cell, (x, y))
        
        # Save to cache
        cache_path = get_cache_path() / 'playlist_covers'
        cache_path.mkdir(exist_ok=True)
        cover_path = cache_path / f'playlist_{playlist_id}.png'
        collage.save(cover_path)
        
        # Update playlist
        execute(
            "UPDATE playlists SET cover_path = ? WHERE id = ?",
            (str(cover_path), playlist_id)
        )
        
        return str(cover_path)
        
    except ImportError:
        logger.warning("Pillow not installed, cannot generate playlist cover")
        return None
    except Exception as e:
        logger.error(f"Failed to generate playlist cover: {e}")
        return None
