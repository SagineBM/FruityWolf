"""
Integration Tests for Identity System

Tests the complete identity system integration with scanner.
"""

import pytest
import tempfile
import time
from pathlib import Path

from FruityWolf.scanner.identity import IdentityStore, compute_fingerprint, extract_file_signals
from FruityWolf.scanner.adapters.fl_studio import FLStudioAdapter
from FruityWolf.database import get_db, execute, query_one, query


@pytest.fixture(autouse=True)
def ensure_migrations():
    """Ensure migrations are run before tests."""
    db = get_db()
    db.init_db()
    yield


def test_identity_system_end_to_end():
    """Test complete identity system workflow."""
    store = IdentityStore()
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "TestProject"
        project_root.mkdir()
        
        # Create test project
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_root), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_root),))
        project_id = project_row['id']
        
        # Ensure PID
        pid = store.ensure_project_pid(project_id)
        assert pid is not None
        
        # Create FLP file
        flp_file = project_root / "project.flp"
        flp_file.touch()
        flp_fingerprint = compute_fingerprint(flp_file)
        
        # Catalog FLP
        flp_file_id = store.upsert_project_file(
            project_id=project_id,
            file_path=flp_file,
            fingerprint=flp_fingerprint or "test_fp",
            file_role='flp',
            file_ext='.flp',
            file_size=1000,
            file_mtime=int(flp_file.stat().st_mtime),
            is_primary=True
        )
        
        # Create render file
        render_file = project_root / "project_final.wav"
        render_file.touch()
        render_fingerprint = compute_fingerprint(render_file)
        
        # Extract signals with FLP reference
        signals = extract_file_signals(
            render_file,
            project_flp_path=flp_file,
            reference_mtime=int(flp_file.stat().st_mtime)
        )
        
        # Compute match score
        score, reasons = adapter.compute_match_score(
            render_file,
            flp_file,
            {'signals': signals, 'flp_mtime': flp_file.stat().st_mtime}
        )
        
        # Catalog render with confidence score
        render_file_id = store.upsert_project_file(
            project_id=project_id,
            file_path=render_file,
            fingerprint=render_fingerprint or "test_fp2",
            file_role='render',
            file_ext='.wav',
            file_size=2000,
            file_mtime=int(render_file.stat().st_mtime),
            is_primary=False,
            confidence_score=score
        )
        
        # Write signals
        store.write_signals(render_file_id, signals)
        
        # Set as primary render
        store.set_primary_render(project_id, render_file_id)
        
        # Verify primary render
        primary = store.get_primary_render(project_id)
        assert primary is not None
        assert primary['id'] == render_file_id
        
        # Verify project confidence was updated
        project_row = query_one("SELECT confidence_score FROM projects WHERE id = ?", (project_id,))
        assert project_row['confidence_score'] is not None
        
        # Cleanup
        execute("DELETE FROM file_signals WHERE file_id IN (?, ?)", (flp_file_id, render_file_id))
        execute("DELETE FROM project_files WHERE id IN (?, ?)", (flp_file_id, render_file_id))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_primary_render_enforcement():
    """Test that only one render can be primary per project."""
    store = IdentityStore()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "TestProject"
        project_root.mkdir()
        
        # Create test project
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_root), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_root),))
        project_id = project_row['id']
        
        # Create 3 render files
        render1 = project_root / "render1.wav"
        render1.touch()
        render2 = project_root / "render2.wav"
        render2.touch()
        render3 = project_root / "render3.wav"
        render3.touch()
        
        fp1 = compute_fingerprint(render1) or "fp1"
        fp2 = compute_fingerprint(render2) or "fp2"
        fp3 = compute_fingerprint(render3) or "fp3"
        
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
        
        file_id3 = store.upsert_project_file(
            project_id=project_id,
            file_path=render3,
            fingerprint=fp3,
            file_role='render',
            file_ext='.wav',
            is_primary=False
        )
        
        # Set render1 as primary
        store.set_primary_render(project_id, file_id1)
        
        # Verify only render1 is primary
        primary_count = query_one(
            "SELECT COUNT(*) as count FROM project_files WHERE project_id = ? AND file_role = 'render' AND is_primary = 1",
            (project_id,)
        )
        assert primary_count['count'] == 1
        
        # Set render2 as primary (should clear render1)
        store.set_primary_render(project_id, file_id2)
        
        primary_count = query_one(
            "SELECT COUNT(*) as count FROM project_files WHERE project_id = ? AND file_role = 'render' AND is_primary = 1",
            (project_id,)
        )
        assert primary_count['count'] == 1
        
        # Verify render2 is now primary
        file2_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id2,))
        assert file2_row['is_primary'] == 1
        
        # Verify render1 and render3 are not primary
        file1_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id1,))
        file3_row = query_one("SELECT is_primary FROM project_files WHERE id = ?", (file_id3,))
        assert file1_row['is_primary'] == 0
        assert file3_row['is_primary'] == 0
        
        # Cleanup
        execute("DELETE FROM project_files WHERE id IN (?, ?, ?)", (file_id1, file_id2, file_id3))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_confidence_scoring_workflow():
    """Test confidence scoring workflow from signals to project confidence."""
    store = IdentityStore()
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "TestProject"
        project_root.mkdir()
        
        # Create test project
        execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (str(project_root), "TestProject")
        )
        
        project_row = query_one("SELECT id FROM projects WHERE path = ?", (str(project_root),))
        project_id = project_row['id']
        
        # Create FLP and render with matching names
        flp_file = project_root / "MySong.flp"
        flp_file.touch()
        render_file = project_root / "MySong_final.wav"
        render_file.touch()
        
        # Extract signals and compute score
        signals = extract_file_signals(
            render_file,
            project_flp_path=flp_file,
            reference_mtime=int(flp_file.stat().st_mtime)
        )
        
        score, reasons = adapter.compute_match_score(
            render_file,
            flp_file,
            {'signals': signals, 'flp_mtime': flp_file.stat().st_mtime}
        )
        
        # Catalog render with score
        render_file_id = store.upsert_project_file(
            project_id=project_id,
            file_path=render_file,
            fingerprint=compute_fingerprint(render_file) or "test_fp",
            file_role='render',
            file_ext='.wav',
            confidence_score=score
        )
        
        # Update project confidence
        has_fingerprint_match = any(
            s.signal_type.value == 'previously_seen_fingerprint' for s in signals
        )
        project_confidence = adapter.compute_flat_folder_confidence(score, has_fingerprint_match)
        store.update_project_confidence(project_id, project_confidence)
        
        # Verify project confidence was set
        project_row = query_one("SELECT confidence_score FROM projects WHERE id = ?", (project_id,))
        assert project_row['confidence_score'] == project_confidence
        assert project_confidence >= 0
        assert project_confidence <= 100
        
        # Cleanup
        execute("DELETE FROM project_files WHERE id = ?", (render_file_id,))
        execute("DELETE FROM projects WHERE id = ?", (project_id,))
