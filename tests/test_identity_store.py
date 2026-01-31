"""
Tests for Identity Store

Tests database operations for the identity system.
"""

import pytest
import tempfile
from pathlib import Path

from FruityWolf.scanner.identity.identity_store import IdentityStore
from FruityWolf.scanner.identity import compute_fingerprint, extract_file_signals
from FruityWolf.database import get_db, execute, query_one
from FruityWolf.database.migrations import run_migrations


@pytest.fixture(autouse=True)
def ensure_migrations():
    """Ensure migrations are run before identity store tests."""
    # Get database connection - this will initialize DB and run migrations
    db = get_db()
    # Ensure migrations are applied (init_db calls run_migrations)
    db.init_db()
    yield


def test_ensure_project_pid():
    """Test PID generation for projects."""
    store = IdentityStore()
    
    # Create a test project
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "TestProject"
        project_path.mkdir()
        
        # Insert test project
        from FruityWolf.database import execute, query_one
        
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_path), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        assert project_row is not None
        project_id = project_row['id']
        
        # Ensure PID
        pid = store.ensure_project_pid(project_id)
        
        assert pid is not None
        assert len(pid) == 36  # UUID format
        assert isinstance(pid, str)
        
        # Verify PID is stored
        project_row2 = query_one("SELECT pid FROM projects WHERE id = ?", (project_id,))
        assert project_row2['pid'] == pid
        
        # Cleanup
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_upsert_project_file():
    """Test upserting a file record."""
    store = IdentityStore()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "TestProject"
        project_path.mkdir()
        
        # Create test project
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_path), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        project_id = project_row['id']
        
        # Create test file
        test_file = project_path / "test.flp"
        test_file.touch()
        fingerprint = compute_fingerprint(test_file)
        
        # Upsert file
        file_id = store.upsert_project_file(
            project_id=project_id,
            file_path=test_file,
            fingerprint=fingerprint or "test_fp",
            file_role='flp',
            file_ext='.flp',
            file_size=1000,
            file_mtime=1234567890,
            is_primary=True
        )
        
        assert file_id is not None
        
        # Verify file was inserted
        file_row = query_one(
            "SELECT * FROM project_files WHERE id = ?",
            (file_id,)
        )
        assert file_row is not None
        assert file_row['project_id'] == project_id
        assert file_row['file_role'] == 'flp'
        assert file_row['is_primary'] == 1
        
        # Cleanup
        execute("DELETE FROM project_files WHERE id = ?", (file_id,))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_write_signals():
    """Test writing signals for a file."""
    store = IdentityStore()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "TestProject"
        project_path.mkdir()
        
        # Create test project and file
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_path), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        project_id = project_row['id']
        
        test_file = project_path / "test.wav"
        test_file.touch()
        fingerprint = compute_fingerprint(test_file)
        
        file_id = store.upsert_project_file(
            project_id=project_id,
            file_path=test_file,
            fingerprint=fingerprint or "test_fp",
            file_role='render',
            file_ext='.wav'
        )
        
        # Extract and write signals
        signals = extract_file_signals(test_file)
        store.write_signals(file_id, signals)
        
        # Verify signals were written
        from FruityWolf.database import query
        
        signal_rows = query(
            "SELECT * FROM file_signals WHERE file_id = ?",
            (file_id,)
        )
        
        assert len(signal_rows) > 0
        
        # Cleanup
        execute("DELETE FROM file_signals WHERE file_id = ?", (file_id,))
        execute("DELETE FROM project_files WHERE id = ?", (file_id,))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_set_primary_render():
    """Test setting primary render (transactional)."""
    store = IdentityStore()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "TestProject"
        project_path.mkdir()
        
        # Create test project
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_path), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        project_id = project_row['id']
        
        # Create two render files
        render1 = project_path / "render1.wav"
        render1.touch()
        render2 = project_path / "render2.wav"
        render2.touch()
        
        fp1 = compute_fingerprint(render1) or "fp1"
        fp2 = compute_fingerprint(render2) or "fp2"
        
        file_id1 = store.upsert_project_file(
            project_id=project_id,
            file_path=render1,
            fingerprint=fp1,
            file_role='render',
            file_ext='.wav',
            is_primary=False
        )
        
        file_id2 = store.upsert_project_file(
            project_id=project_id,
            file_path=render2,
            fingerprint=fp2,
            file_role='render',
            file_ext='.wav',
            is_primary=False
        )
        
        # Set render1 as primary
        store.set_primary_render(project_id, file_id1)
        
        # Verify only render1 is primary
        file1_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id1,))
        file2_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id2,))
        
        assert file1_row['is_primary'] == 1
        assert file2_row['is_primary'] == 0
        
        # Set render2 as primary (should clear render1)
        store.set_primary_render(project_id, file_id2)
        
        file1_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id1,))
        file2_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id2,))
        
        assert file1_row['is_primary'] == 0
        assert file2_row['is_primary'] == 1
        
        # Cleanup
        execute("DELETE FROM project_files WHERE id IN (?, ?)", (file_id1, file_id2))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_get_primary_render():
    """Test getting primary render."""
    store = IdentityStore()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "TestProject"
        project_path.mkdir()
        
        # Create test project
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_path), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        project_id = project_row['id']
        
        # Create render and set as primary
        render = project_path / "render.wav"
        render.touch()
        fingerprint = compute_fingerprint(render) or "test_fp"
        
        file_id = store.upsert_project_file(
            project_id=project_id,
            file_path=render,
            fingerprint=fingerprint,
            file_role='render',
            file_ext='.wav',
            is_primary=True
        )
        
        # Get primary render
        primary = store.get_primary_render(project_id)
        
        assert primary is not None
        assert primary['id'] == file_id
        assert primary['file_path'] == str(render)
        
        # Cleanup
        execute("DELETE FROM project_files WHERE id = ?", (file_id,))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_is_project_locked():
    """Test checking if project is locked."""
    store = IdentityStore()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "TestProject"
        project_path.mkdir()
        
        # Create test project (unlocked by default)
        execute(
            "INSERT INTO projects (path, name, user_locked) VALUES (?, ?, ?)",
            (str(project_path), "TestProject", 0)
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        project_id = project_row['id']
        
        # Should be unlocked
        assert not store.is_project_locked(project_id)
        
        # Lock project
        execute(
            "UPDATE projects SET user_locked = 1 WHERE id = ?",
            (project_id,)
        )
        
        # Should be locked
        assert store.is_project_locked(project_id)
        
        # Cleanup
        execute("DELETE FROM projects WHERE id = ?", (project_id,))
