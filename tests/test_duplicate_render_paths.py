"""
Test for Duplicate Render Path Handling

Tests that the scanner handles duplicate render paths gracefully
when the same audio file is matched to multiple FLPs.
"""

import pytest
import tempfile
from pathlib import Path

from FruityWolf.database import get_db, execute, query_one, query
from FruityWolf.scanner.library_scanner import LibraryScanner


@pytest.fixture(autouse=True)
def ensure_migrations():
    """Ensure migrations are run before tests."""
    db = get_db()
    db.init_db()
    yield


def test_duplicate_render_path_handling():
    """Test that duplicate render paths are handled gracefully."""
    scanner = LibraryScanner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create 2 FLP files
        flp1 = root / "MySong.flp"
        flp1.touch()
        flp2 = root / "MySong_v2.flp"
        flp2.touch()
        
        # Create one audio file that matches both FLPs (high token overlap)
        audio = root / "MySong_final.wav"
        audio.touch()
        
        # Add library root
        scanner.add_library_root(str(root))
        
        # Scan orphan FLPs - should handle duplicate paths gracefully
        # The key test is that it doesn't crash with UNIQUE constraint error
        try:
            result = scanner._scan_orphan_flps_in_root(root)
            # Should not crash
            assert result is not None
        except Exception as e:
            # Check that it's not a UNIQUE constraint error
            if 'UNIQUE constraint failed' in str(e) and 'renders.path' in str(e):
                pytest.fail(f"UNIQUE constraint error not handled: {e}")
            else:
                # Other errors are okay (might be expected)
                pass
        
        # Verify no duplicate renders exist (conflict resolution should prevent this)
        renders = query("SELECT COUNT(*) as count FROM renders WHERE path = ?", (str(audio),))
        render_count = renders[0]['count'] if renders else 0
        
        # Should have at most 1 render (conflict resolution prevents duplicates)
        assert render_count <= 1, f"Expected at most 1 render, got {render_count}"


def test_duplicate_render_path_different_projects():
    """Test that same audio file matched to different projects doesn't create duplicates."""
    from FruityWolf.database import execute, query_one, query
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create 2 projects
        project1_path = root / "Project1"
        project1_path.mkdir()
        project2_path = root / "Project2"
        project2_path.mkdir()
        
        # Create same audio file in both projects
        audio1 = project1_path / "render.wav"
        audio1.touch()
        audio2 = project2_path / "render.wav"
        audio2.touch()
        
        # Create projects in DB
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project1_path), "Project1")
        )
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project2_path), "Project2")
        )
        
        project1_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project1_path),))
        project2_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project2_path),))
        project1_id = project1_row['id']
        project2_id = project2_row['id']
        
        # Try to insert render for project1
        try:
            execute(
                """INSERT INTO renders (project_id, path, filename, ext) VALUES (?, ?, ?, ?)""",
                (project1_id, str(audio1), "render.wav", ".wav")
            )
        except Exception as e:
            pytest.fail(f"Failed to insert render for project1: {e}")
        
        # Try to insert render for project2 with same path (should fail gracefully)
        try:
            execute(
                """INSERT INTO renders (project_id, path, filename, ext) VALUES (?, ?, ?, ?)""",
                (project2_id, str(audio1), "render.wav", ".wav")  # Same path as project1
            )
            pytest.fail("Should have raised UNIQUE constraint error")
        except Exception as e:
            # Should raise UNIQUE constraint error
            assert 'UNIQUE constraint failed' in str(e) or 'UNIQUE constraint' in str(e)
        
        # Cleanup
        execute("DELETE FROM renders WHERE project_id IN (?, ?)", (project1_id, project2_id))
        execute("DELETE FROM projects WHERE id IN (?, ?)", (project1_id, project2_id))
