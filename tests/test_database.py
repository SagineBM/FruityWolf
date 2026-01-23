"""
Tests for Database Module
"""

import os
import tempfile
import pytest

# Set test database path before importing
os.environ['FL_LIBRARY_TEST'] = '1'


def test_database_initialization():
    """Test database creates required tables."""
    from FruityWolf.database import get_db, query
    
    db = get_db()
    assert db.db_path.exists()
    
    # Check tables exist
    tables = query("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    table_names = {row['name'] for row in tables}
    
    assert 'projects' in table_names
    assert 'tracks' in table_names
    assert 'tags' in table_names
    assert 'playlists' in table_names
    assert 'playlist_tracks' in table_names
    assert 'library_roots' in table_names
    assert 'settings' in table_names


def test_default_tags_created():
    """Test default tags are inserted."""
    from FruityWolf.database import query
    
    tags = query("SELECT name, category FROM tags")
    tag_names = {row['name'] for row in tags}
    
    # Check some default tags exist
    assert 'Energetic' in tag_names
    assert 'Chill' in tag_names
    assert 'Trap' in tag_names
    assert 'Hip Hop' in tag_names


def test_settings_operations():
    """Test get/set settings."""
    from FruityWolf.database import get_setting, set_setting
    
    # Test default value
    assert get_setting('nonexistent', 'default') == 'default'
    
    # Test set and get
    set_setting('test_key', 'test_value')
    assert get_setting('test_key') == 'test_value'
    
    # Test update
    set_setting('test_key', 'updated_value')
    assert get_setting('test_key') == 'updated_value'
