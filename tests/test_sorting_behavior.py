"""
Tests for Library Sorting Behavior

Verifies that:
1. Renders are sorted by file_created_at (newest first)
2. Projects model sorts by CREATED column descending by default
3. Project date is updated from newest render
"""

import os
import time

# Set test database path before importing
os.environ['FL_LIBRARY_TEST'] = '1'


def test_render_ordering_uses_file_created_at():
    """Test get_project_renders() orders by file_created_at, not mtime."""
    from FruityWolf.database import execute, query, get_db
    
    # Initialize database
    db = get_db()
    
    # Check if renders table exists
    try:
        query("SELECT 1 FROM renders LIMIT 1")
    except:
        # Create renders table if it doesn't exist (for test)
        execute("""
            CREATE TABLE IF NOT EXISTS renders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                ext TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                mtime INTEGER,
                duration_s REAL DEFAULT 0,
                fingerprint_fast TEXT,
                file_created_at INTEGER,
                is_primary INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
    
    # Create a test project
    cur = execute("""
        INSERT OR REPLACE INTO projects (path, name, created_at) 
        VALUES ('test_project_sorting', 'Test Project Sorting', strftime('%s', 'now'))
    """)
    project_id = cur.lastrowid
    
    now = int(time.time())
    
    # Clean up old test data
    execute("DELETE FROM renders WHERE project_id = ?", (project_id,))
    
    # Insert renders with file_created_at in REVERSE order of mtime
    # Render A: older mtime, but NEWER file_created_at (should appear first)
    execute("""
        INSERT INTO renders (project_id, path, filename, ext, mtime, file_created_at)
        VALUES (?, ?, 'render_a.mp3', '.mp3', ?, ?)
    """, (project_id, f'test_render_a_{now}.mp3', now - 100, now + 1000))
    
    # Render B: newer mtime, but OLDER file_created_at (should appear second)
    execute("""
        INSERT INTO renders (project_id, path, filename, ext, mtime, file_created_at)
        VALUES (?, ?, 'render_b.mp3', '.mp3', ?, ?)
    """, (project_id, f'test_render_b_{now}.mp3', now + 100, now - 1000))
    
    # Get renders using the function under test
    from FruityWolf.scanner.library_scanner import get_project_renders
    renders = get_project_renders(project_id)
    
    assert len(renders) >= 2, f"Expected at least 2 renders, got {len(renders)}"
    
    # Find our test renders
    render_a = next((r for r in renders if 'render_a' in r.get('filename', '')), None)
    render_b = next((r for r in renders if 'render_b' in r.get('filename', '')), None)
    
    assert render_a is not None, "Could not find render_a"
    assert render_b is not None, "Could not find render_b"
    
    # Render A should come before Render B (newer file_created_at = first)
    idx_a = next(i for i, r in enumerate(renders) if 'render_a' in r.get('filename', ''))
    idx_b = next(i for i, r in enumerate(renders) if 'render_b' in r.get('filename', ''))
    
    assert idx_a < idx_b, f"Render A (newer file_created_at) should appear before Render B. idx_a={idx_a}, idx_b={idx_b}"
    
    # Cleanup
    execute("DELETE FROM renders WHERE project_id = ?", (project_id,))
    execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_projects_model_sort_by_created():
    """Test ProjectsModel.sort() properly sorts by file_created_at."""
    import time
    
    # Create mock projects with different file_created_at values
    now = int(time.time())
    
    projects = [
        {'id': 1, 'name': 'Project A', 'file_created_at': now - 1000, 'created_at': now},
        {'id': 2, 'name': 'Project B', 'file_created_at': now, 'created_at': now - 1000},  # Newer file, older db
        {'id': 3, 'name': 'Project C', 'file_created_at': now - 500, 'created_at': now},
    ]
    
    from FruityWolf.ui.view_models.projects_model import ProjectsModel
    from PySide6.QtCore import Qt
    
    model = ProjectsModel(projects)
    
    # Sort by CREATED column descending (newest first)
    model.sort(ProjectsModel.COL_CREATED, Qt.SortOrder.DescendingOrder)
    
    # Project B should be first (newest file_created_at)
    # Project C should be second
    # Project A should be last (oldest file_created_at)
    
    assert model._projects[0]['id'] == 2, f"Expected Project B (id=2) first, got id={model._projects[0]['id']}"
    assert model._projects[1]['id'] == 3, f"Expected Project C (id=3) second, got id={model._projects[1]['id']}"
    assert model._projects[2]['id'] == 1, f"Expected Project A (id=1) last, got id={model._projects[2]['id']}"


def test_project_date_bump_from_render():
    """Test update_project_date_from_renders() increases project file_created_at."""
    from FruityWolf.database import execute, query, query_one, get_db
    
    # Initialize database
    db = get_db()
    
    # Check if renders table exists
    try:
        query("SELECT 1 FROM renders LIMIT 1")
    except:
        # Create renders table if it doesn't exist (for test)
        execute("""
            CREATE TABLE IF NOT EXISTS renders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                ext TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                mtime INTEGER,
                duration_s REAL DEFAULT 0,
                fingerprint_fast TEXT,
                file_created_at INTEGER,
                is_primary INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
    
    now = int(time.time())
    old_date = now - 10000
    new_date = now + 5000
    
    # Create project with old file_created_at
    cur = execute("""
        INSERT OR REPLACE INTO projects (path, name, file_created_at, created_at) 
        VALUES (?, 'Test Project Date Bump', ?, ?)
    """, (f'test_project_date_bump_{now}', old_date, now))
    project_id = cur.lastrowid
    
    # Clean up old test data
    execute("DELETE FROM renders WHERE project_id = ?", (project_id,))
    
    # Insert render with newer file_created_at
    execute("""
        INSERT INTO renders (project_id, path, filename, ext, file_created_at)
        VALUES (?, ?, 'new_render.mp3', '.mp3', ?)
    """, (project_id, f'test_new_render_{now}.mp3', new_date))
    
    # Run update function
    from FruityWolf.scanner.library_scanner import update_project_date_from_renders
    update_project_date_from_renders(project_id)
    
    # Check project date was updated
    project = query_one("SELECT file_created_at FROM projects WHERE id = ?", (project_id,))
    
    assert project is not None, "Project not found"
    assert project['file_created_at'] == new_date, \
        f"Expected file_created_at to be {new_date}, got {project['file_created_at']}"
    
    # Cleanup
    execute("DELETE FROM renders WHERE project_id = ?", (project_id,))
    execute("DELETE FROM projects WHERE id = ?", (project_id,))


def test_project_date_not_decreased():
    """Test update_project_date_from_renders() never makes a project older."""
    from FruityWolf.database import execute, query, query_one, get_db
    
    # Initialize database
    db = get_db()
    
    now = int(time.time())
    new_date = now + 10000
    old_date = now - 5000
    
    # Create project with NEWER file_created_at
    cur = execute("""
        INSERT OR REPLACE INTO projects (path, name, file_created_at, created_at) 
        VALUES (?, 'Test Project No Decrease', ?, ?)
    """, (f'test_project_no_decrease_{now}', new_date, now))
    project_id = cur.lastrowid
    
    # Clean up old test data
    execute("DELETE FROM renders WHERE project_id = ?", (project_id,))
    
    # Insert render with OLDER file_created_at
    execute("""
        INSERT INTO renders (project_id, path, filename, ext, file_created_at)
        VALUES (?, ?, 'old_render.mp3', '.mp3', ?)
    """, (project_id, f'test_old_render_{now}.mp3', old_date))
    
    # Run update function
    from FruityWolf.scanner.library_scanner import update_project_date_from_renders
    update_project_date_from_renders(project_id)
    
    # Check project date was NOT changed (still new_date)
    project = query_one("SELECT file_created_at FROM projects WHERE id = ?", (project_id,))
    
    assert project is not None, "Project not found"
    assert project['file_created_at'] == new_date, \
        f"Expected file_created_at to remain {new_date}, but got {project['file_created_at']}"
    
    # Cleanup
    execute("DELETE FROM renders WHERE project_id = ?", (project_id,))
    execute("DELETE FROM projects WHERE id = ?", (project_id,))
