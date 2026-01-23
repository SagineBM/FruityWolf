"""
Tag and Mood Management Helpers

Enhanced tag system for FruityWolf with mood tags, genre tags, custom tags,
and autocomplete support.
"""

from typing import List, Dict, Optional, Set
import logging

from ..database import execute, query, query_one

logger = logging.getLogger(__name__)


# =============================================================================
# Core Tag CRUD
# =============================================================================

def get_all_tags(category: Optional[str] = None) -> List[Dict]:
    """Get all tags, optionally filtered by category."""
    sql = "SELECT * FROM tags"
    params = []
    
    if category:
        sql += " WHERE category = ?"
        params.append(category)
        
    sql += " ORDER BY category, name"
    return [dict(row) for row in query(sql, tuple(params))]


def get_tags_by_category() -> Dict[str, List[Dict]]:
    """Get all tags grouped by category."""
    all_tags = get_all_tags()
    result = {'mood': [], 'genre': [], 'custom': []}
    
    for tag in all_tags:
        category = tag.get('category', 'custom')
        if category not in result:
            result[category] = []
        result[category].append(tag)
    
    return result


def get_track_tags(track_id: int) -> List[Dict]:
    """Get all tags for a track."""
    sql = """
        SELECT t.* FROM tags t
        JOIN track_tags tt ON t.id = tt.tag_id
        WHERE tt.track_id = ?
        ORDER BY t.category, t.name
    """
    return [dict(row) for row in query(sql, (track_id,))]


def get_track_tag_names(track_id: int) -> List[str]:
    """Get just the tag names for a track."""
    tags = get_track_tags(track_id)
    return [t['name'] for t in tags]


def add_tag(name: str, category: str = 'custom', color: str = '#6366f1') -> int:
    """Add a new tag. Returns tag ID."""
    name = name.strip()
    if not name:
        return -1
        
    try:
        cur = execute(
            "INSERT INTO tags (name, category, color) VALUES (?, ?, ?)",
            (name, category, color)
        )
        return cur.lastrowid
    except Exception:
        # Tag might exist, return its ID
        row = query_one("SELECT id FROM tags WHERE name = ?", (name,))
        return row['id'] if row else -1


def delete_tag(tag_id: int):
    """Delete a tag and all its associations."""
    execute("DELETE FROM track_tags WHERE tag_id = ?", (tag_id,))
    execute("DELETE FROM tags WHERE id = ?", (tag_id,))


def update_tag(tag_id: int, name: str = None, color: str = None):
    """Update a tag's name or color."""
    if name:
        execute("UPDATE tags SET name = ? WHERE id = ?", (name.strip(), tag_id))
    if color:
        execute("UPDATE tags SET color = ? WHERE id = ?", (color, tag_id))


# =============================================================================
# Track-Tag Associations
# =============================================================================

def update_track_tags(track_id: int, tags: List[str]):
    """Update tags for a track (replace existing)."""
    # 1. Clear existing tags
    execute("DELETE FROM track_tags WHERE track_id = ?", (track_id,))
    
    # 2. Add new tags
    for tag_name in tags:
        tag_name = tag_name.strip()
        if not tag_name:
            continue
        # Find or create tag
        tag_id = add_tag(tag_name)
        if tag_id > 0:
            execute(
                "INSERT OR IGNORE INTO track_tags (track_id, tag_id) VALUES (?, ?)",
                (track_id, tag_id)
            )


def add_tag_to_track(track_id: int, tag_name: str):
    """Add a single tag to a track."""
    tag_id = add_tag(tag_name)
    if tag_id > 0:
        execute(
            "INSERT OR IGNORE INTO track_tags (track_id, tag_id) VALUES (?, ?)",
            (track_id, tag_id)
        )


def remove_tag_from_track(track_id: int, tag_name: str):
    """Remove a single tag from a track."""
    row = query_one("SELECT id FROM tags WHERE name = ?", (tag_name,))
    if row:
        execute(
            "DELETE FROM track_tags WHERE track_id = ? AND tag_id = ?",
            (track_id, row['id'])
        )


# =============================================================================
# Search and Query Helpers
# =============================================================================

def search_tags(term: str, limit: int = 20) -> List[Dict]:
    """Search tags by name prefix for autocomplete."""
    sql = "SELECT * FROM tags WHERE name LIKE ? ORDER BY name LIMIT ?"
    return [dict(row) for row in query(sql, (f"{term}%", limit))]


def get_popular_tags(limit: int = 20) -> List[Dict]:
    """Get most frequently used tags."""
    sql = """
        SELECT t.*, COUNT(tt.track_id) as usage_count
        FROM tags t
        LEFT JOIN track_tags tt ON t.id = tt.tag_id
        GROUP BY t.id
        ORDER BY usage_count DESC, t.name
        LIMIT ?
    """
    return [dict(row) for row in query(sql, (limit,))]


def get_tracks_by_tag(tag_name: str) -> List[int]:
    """Get track IDs that have a specific tag."""
    sql = """
        SELECT tt.track_id FROM track_tags tt
        JOIN tags t ON tt.tag_id = t.id
        WHERE t.name = ?
    """
    rows = query(sql, (tag_name,))
    return [r['track_id'] for r in rows]


def get_tracks_by_tags(tag_names: List[str], match_all: bool = True) -> List[int]:
    """
    Get track IDs that have specific tags.
    
    Args:
        tag_names: List of tag names to filter by
        match_all: If True, tracks must have ALL tags. If False, tracks with ANY tag.
    """
    if not tag_names:
        return []
    
    placeholders = ','.join('?' * len(tag_names))
    
    if match_all:
        sql = f"""
            SELECT tt.track_id FROM track_tags tt
            JOIN tags t ON tt.tag_id = t.id
            WHERE t.name IN ({placeholders})
            GROUP BY tt.track_id
            HAVING COUNT(DISTINCT t.id) = ?
        """
        params = tag_names + [len(tag_names)]
    else:
        sql = f"""
            SELECT DISTINCT tt.track_id FROM track_tags tt
            JOIN tags t ON tt.tag_id = t.id
            WHERE t.name IN ({placeholders})
        """
        params = tag_names
    
    rows = query(sql, tuple(params))
    return [r['track_id'] for r in rows]


# =============================================================================
# Category Helpers
# =============================================================================

def get_all_genres() -> List[str]:
    """Get list of genre names."""
    rows = get_all_tags(category='genre')
    return [r['name'] for r in rows]


def get_all_moods() -> List[str]:
    """Get list of mood tag names."""
    rows = get_all_tags(category='mood')
    return [r['name'] for r in rows]


def get_all_custom_tags() -> List[str]:
    """Get list of custom tag names."""
    rows = get_all_tags(category='custom')
    return [r['name'] for r in rows]


# =============================================================================
# Bulk Operations
# =============================================================================

def add_tags_to_tracks(track_ids: List[int], tag_names: List[str]):
    """Add tags to multiple tracks at once."""
    for track_id in track_ids:
        for tag_name in tag_names:
            add_tag_to_track(track_id, tag_name)


def remove_tags_from_tracks(track_ids: List[int], tag_names: List[str]):
    """Remove tags from multiple tracks at once."""
    for track_id in track_ids:
        for tag_name in tag_names:
            remove_tag_from_track(track_id, tag_name)


def get_tag_suggestions(track_ids: List[int]) -> List[str]:
    """Get tag suggestions based on other tracks' tags (for bulk tagging)."""
    if not track_ids:
        return []
    
    # Get tags from selected tracks
    placeholders = ','.join('?' * len(track_ids))
    sql = f"""
        SELECT t.name, COUNT(tt.track_id) as count
        FROM tags t
        JOIN track_tags tt ON t.id = tt.tag_id
        WHERE tt.track_id IN ({placeholders})
        GROUP BY t.id
        ORDER BY count DESC
        LIMIT 10
    """
    rows = query(sql, tuple(track_ids))
    return [r['name'] for r in rows]

