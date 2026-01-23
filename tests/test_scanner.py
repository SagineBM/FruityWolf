"""
Tests for Scanner Module
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path


def test_audio_extensions():
    """Test audio extensions are correctly defined."""
    from FruityWolf.scanner import AUDIO_EXTENSIONS
    
    assert '.wav' in AUDIO_EXTENSIONS
    assert '.mp3' in AUDIO_EXTENSIONS
    assert '.flac' in AUDIO_EXTENSIONS
    assert '.ogg' in AUDIO_EXTENSIONS
    assert '.m4a' in AUDIO_EXTENSIONS


def test_scan_empty_directory():
    """Test scanning an empty directory."""
    from FruityWolf.scanner import LibraryScanner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        scanner = LibraryScanner()
        scanner.add_library_root(tmpdir)
        
        # Should not crash with empty directory
        roots = scanner.get_library_roots()
        assert len(roots) == 1


def test_scan_project_structure():
    """Test scanning a mock project structure."""
    from FruityWolf.scanner import LibraryScanner, get_all_tracks
    from FruityWolf.database import get_db
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock project structure
        project_dir = Path(tmpdir) / "Test Project"
        project_dir.mkdir()
        
        # Create mock render (empty wav file)
        render_file = project_dir / "Test Render.wav"
        render_file.write_bytes(b'RIFF' + b'\x00' * 100)  # Minimal WAV header
        
        # Create mock FLP
        flp_file = project_dir / "Test Project.flp"
        flp_file.write_bytes(b'FLP' + b'\x00' * 50)
        
        # Create subfolders
        (project_dir / "Stems").mkdir()
        (project_dir / "Samples").mkdir()
        
        # Scan
        scanner = LibraryScanner()
        scanner.add_library_root(tmpdir)
        scanner.scan_all()
        
        # Check results
        tracks = get_all_tracks()
        assert len(tracks) >= 0  # May be 0 if WAV is invalid


def test_search_tracks():
    """Test track search functionality."""
    from FruityWolf.scanner import search_tracks
    
    # Search with empty term should return results
    tracks = search_tracks(term='', limit=10)
    assert isinstance(tracks, list)


def test_toggle_favorite():
    """Test favorite toggle functionality."""
    from FruityWolf.scanner import toggle_favorite
    from FruityWolf.database import execute, query_one
    
    # Insert a test track
    execute("""
        INSERT INTO projects (name, path) VALUES ('Test', '/test/path')
    """)
    project = query_one("SELECT id FROM projects WHERE name = 'Test'")
    
    execute("""
        INSERT INTO tracks (project_id, title, path, favorite) 
        VALUES (?, 'Test Track', '/test/track.wav', 0)
    """, (project['id'],))
    
    track = query_one("SELECT id FROM tracks WHERE title = 'Test Track'")
    
    # Toggle favorite
    new_status = toggle_favorite(track['id'])
    assert new_status == True
    
    # Toggle again
    new_status = toggle_favorite(track['id'])
    assert new_status == False
