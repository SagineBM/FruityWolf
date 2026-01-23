"""
Library Scanner

Scans FL Studio project folders and indexes audio files.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass
from datetime import datetime
import time

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker

from ..database import get_db, execute, query, query_one

logger = logging.getLogger(__name__)

# Supported audio formats
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif'}


@dataclass
class ScanResult:
    """Result of a library scan."""
    projects_found: int = 0
    tracks_found: int = 0
    projects_updated: int = 0
    tracks_added: int = 0
    tracks_removed: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class LibraryScanner(QObject):
    """Background library scanner with progress signals."""
    
    # Signals
    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(ScanResult)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = False
        self._mutex = QMutex()
    
    def cancel(self):
        """Cancel the current scan."""
        with QMutexLocker(self._mutex):
            self._cancel = True
    
    def is_cancelled(self) -> bool:
        """Check if scan was cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancel
    
    def get_library_roots(self) -> List[Path]:
        """Get all enabled library root paths."""
        rows = query("SELECT path FROM library_roots WHERE enabled = 1")
        return [Path(row['path']) for row in rows if os.path.isdir(row['path'])]
    
    def add_library_root(self, path: str, name: Optional[str] = None) -> bool:
        """Add a new library root directory."""
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            return False
        
        if name is None:
            name = os.path.basename(path)
        
        try:
            execute(
                "INSERT OR IGNORE INTO library_roots (path, name) VALUES (?, ?)",
                (path, name)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add library root: {e}")
            return False
    
    def remove_library_root(self, path: str):
        """Remove a library root directory."""
        execute("DELETE FROM library_roots WHERE path = ?", (path,))
    
    def scan_all(self):
        """Scan all library roots."""
        self._cancel = False
        result = ScanResult()
        
        roots = self.get_library_roots()
        if not roots:
            # Add default root if none configured
            default_root = r"F:\1.Project FL S1"
            if os.path.isdir(default_root):
                self.add_library_root(default_root)
                roots = [Path(default_root)]
        
        total_projects = 0
        all_projects = []
        
        # First pass: count projects
        for root in roots:
            if self.is_cancelled():
                return
            
            try:
                for name in os.listdir(root):
                    proj_path = root / name
                    if proj_path.is_dir():
                        all_projects.append(proj_path)
                        total_projects += 1
            except PermissionError as e:
                result.errors.append(f"Permission denied: {root}")
                logger.error(f"Permission denied scanning {root}: {e}")
        
        # Second pass: scan projects
        for idx, proj_path in enumerate(all_projects):
            if self.is_cancelled():
                break
            
            self.progress.emit(idx + 1, total_projects, f"Scanning: {proj_path.name}")
            
            try:
                project_result = self._scan_project(proj_path)
                if project_result:
                    result.projects_found += 1
                    result.tracks_found += project_result.get('tracks', 0)
                    if project_result.get('is_new'):
                        result.projects_updated += 1
                    result.tracks_added += project_result.get('tracks_added', 0)
                    result.tracks_removed += project_result.get('tracks_removed', 0)
            except Exception as e:
                result.errors.append(f"Error scanning {proj_path}: {e}")
                logger.exception(f"Error scanning project {proj_path}")
        
        # Update library root last scan time
        now = int(time.time())
        for root in roots:
            execute(
                "UPDATE library_roots SET last_scan = ? WHERE path = ?",
                (now, str(root))
            )
        
        self.finished.emit(result)
    
    def _scan_project(self, proj_path: Path) -> Optional[Dict]:
        """Scan a single project folder."""
        # Check for renders (audio files in project root)
        renders = []
        flps_root = []
        
        try:
            for item in os.listdir(proj_path):
                item_path = proj_path / item
                if not item_path.is_file():
                    continue
                
                ext = item_path.suffix.lower()
                if ext in AUDIO_EXTENSIONS:
                    renders.append(item_path)
                elif ext == '.flp':
                    flps_root.append(item_path)
        except PermissionError:
            return None
        
        # Skip if no renders found
        if not renders:
            return None
        
        # Find FLP: prefer root, else search subdirectories
        flp_path = None
        if flps_root:
            flp_path = max(flps_root, key=lambda p: p.stat().st_mtime)
        else:
            # Search for FLP in subdirectories (usually Backup)
            flps_any = []
            for root, dirs, files in os.walk(proj_path):
                for f in files:
                    if f.lower().endswith('.flp'):
                        flps_any.append(Path(root) / f)
            if flps_any:
                flp_path = max(flps_any, key=lambda p: p.stat().st_mtime)
        
        # Detect subfolders
        audio_dir = proj_path / 'Audio'
        samples_dir = proj_path / 'Samples'
        stems_dir = proj_path / 'Stems'
        backup_dir = proj_path / 'Backup'
        
        # Insert or update project
        existing = query_one(
            "SELECT id, updated_at FROM projects WHERE path = ?",
            (str(proj_path),)
        )
        
        is_new = existing is None
        now = int(time.time())
        
        if is_new:
            cur = execute(
                """INSERT INTO projects 
                   (name, path, flp_path, audio_dir, samples_dir, stems_dir, backup_dir, last_scan)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    proj_path.name,
                    str(proj_path),
                    str(flp_path) if flp_path else None,
                    str(audio_dir) if audio_dir.is_dir() else None,
                    str(samples_dir) if samples_dir.is_dir() else None,
                    str(stems_dir) if stems_dir.is_dir() else None,
                    str(backup_dir) if backup_dir.is_dir() else None,
                    now,
                )
            )
            project_id = cur.lastrowid
        else:
            project_id = existing['id']
            execute(
                """UPDATE projects SET
                   flp_path = ?, audio_dir = ?, samples_dir = ?, stems_dir = ?, 
                   backup_dir = ?, last_scan = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    str(flp_path) if flp_path else None,
                    str(audio_dir) if audio_dir.is_dir() else None,
                    str(samples_dir) if samples_dir.is_dir() else None,
                    str(stems_dir) if stems_dir.is_dir() else None,
                    str(backup_dir) if backup_dir.is_dir() else None,
                    now,
                    now,
                    project_id,
                )
            )
        
        # Insert tracks
        tracks_added = 0
        existing_tracks = {
            row['path']: row['id']
            for row in query("SELECT id, path FROM tracks WHERE project_id = ?", (project_id,))
        }
        
        for render_path in renders:
            track_path_str = str(render_path)
            
            if track_path_str in existing_tracks:
                # Update existing track
                stat = render_path.stat()
                execute(
                    """UPDATE tracks SET
                       mtime = ?, file_size = ?, updated_at = ?
                       WHERE id = ?""",
                    (int(stat.st_mtime), stat.st_size, now, existing_tracks[track_path_str])
                )
            else:
                # Insert new track
                stat = render_path.stat()
                execute(
                    """INSERT INTO tracks
                       (project_id, title, path, ext, file_size, mtime)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        project_id,
                        render_path.stem,
                        track_path_str,
                        render_path.suffix.lower(),
                        stat.st_size,
                        int(stat.st_mtime),
                    )
                )
                tracks_added += 1

        
        # Prune missing tracks
        tracks_removed = 0
        found_paths = {str(p) for p in renders}
        for path_str, track_id in existing_tracks.items():
            if path_str not in found_paths:
                execute("DELETE FROM tracks WHERE id = ?", (track_id,))
                tracks_removed += 1
        
        return {
            'is_new': is_new,
            'tracks': len(renders),
            'tracks_added': tracks_added,
            'tracks_removed': tracks_removed,
        }
    
    def incremental_scan(self):
        """Perform incremental scan (only changed files)."""
        # TODO: Implement incremental scanning based on mtime
        self.scan_all()


class ScannerThread(QThread):
    """Thread for running library scanner."""
    
    progress = Signal(int, int, str)
    finished = Signal(ScanResult)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = LibraryScanner()
        
        # Forward signals
        self.scanner.progress.connect(self.progress.emit)
        self.scanner.finished.connect(self.finished.emit)
        self.scanner.error.connect(self.error.emit)
    
    def run(self):
        """Run the scanner."""
        try:
            self.scanner.scan_all()
        except Exception as e:
            logger.exception("Scanner thread error")
            self.error.emit(str(e))
    
    def cancel(self):
        """Cancel the scan."""
        self.scanner.cancel()


# Track query helpers
def get_all_tracks(limit: int = 500, offset: int = 0) -> List[Dict]:
    """Get all tracks with project info."""
    rows = query(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           ORDER BY t.mtime DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    return [dict(row) for row in rows]


def get_favorite_tracks(limit: int = 500) -> List[Dict]:
    """Get favorite tracks."""
    rows = query(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE t.favorite = 1
           ORDER BY t.mtime DESC
           LIMIT ?""",
        (limit,)
    )
    return [dict(row) for row in rows]


def search_tracks(
    term: str = '',
    bpm_min: Optional[float] = None,
    bpm_max: Optional[float] = None,
    key: Optional[str] = None,
    tags: Optional[List[str]] = None,
    favorites_only: bool = False,
    limit: int = 500,
) -> List[Dict]:
    """Search tracks with filters."""
    conditions = []
    params = []
    
    if term:
        # Escape FTS5 special characters by quoting the term
        # FTS5 special chars: AND OR NOT ( ) " * : / -
        # Using double-quote escaping for safety
        safe_term = term.replace('"', '""')  # Escape quotes
        # Use FTS for text search with properly escaped term
        conditions.append("""t.id IN (
            SELECT rowid FROM tracks_fts WHERE tracks_fts MATCH ?
        )""")
        params.append(f'"{safe_term}"*')
    
    if bpm_min is not None:
        conditions.append("COALESCE(t.bpm_user, t.bpm_detected) >= ?")
        params.append(bpm_min)
    
    if bpm_max is not None:
        conditions.append("COALESCE(t.bpm_user, t.bpm_detected) <= ?")
        params.append(bpm_max)
    
    if key:
        conditions.append("COALESCE(t.key_user, t.key_detected) = ?")
        params.append(key)
    
    if tags:
        placeholders = ','.join('?' * len(tags))
        conditions.append(f"""t.id IN (
            SELECT tt.track_id FROM track_tags tt
            JOIN tags tg ON tt.tag_id = tg.id
            WHERE tg.name IN ({placeholders})
        )""")
        params.extend(tags)
    
    if favorites_only:
        conditions.append("t.favorite = 1")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
            (SELECT GROUP_CONCAT(tg.name, ', ') 
             FROM track_tags tt 
             JOIN tags tg ON tt.tag_id = tg.id 
             WHERE tt.track_id = t.id) as genre
            FROM tracks t
            JOIN projects p ON t.project_id = p.id
            {where_clause}
            ORDER BY t.mtime DESC
            LIMIT ?""",
        tuple(params) + (limit,)
    )
    return [dict(row) for row in rows]


def toggle_favorite(track_id: int) -> bool:
    """Toggle track favorite status. Returns new status."""
    row = query_one("SELECT favorite FROM tracks WHERE id = ?", (track_id,))
    if row is None:
        return False
    
    new_status = 0 if row['favorite'] else 1
    execute(
        "UPDATE tracks SET favorite = ?, updated_at = strftime('%s', 'now') WHERE id = ?",
        (new_status, track_id)
    )
    return new_status == 1


def get_track_by_id(track_id: int) -> Optional[Dict]:
    """Get a single track by ID."""
    row = query_one(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
                  p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
                  (SELECT GROUP_CONCAT(tg.name, ', ') 
                   FROM track_tags tt 
                   JOIN tags tg ON tt.tag_id = tg.id 
                   WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE t.id = ?""",
        (track_id,)
    )
    return dict(row) if row else None


def update_track_metadata(
    track_id: int,
    bpm: Optional[float] = None,
    key: Optional[str] = None,
    notes: Optional[str] = None,
):
    """Update track metadata."""
    updates = []
    params = []
    
    if bpm is not None:
        updates.append("bpm_user = ?")
        params.append(bpm)
    
    if key is not None:
        updates.append("key_user = ?")
        params.append(key)
    
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    
    if updates:
        updates.append("updated_at = strftime('%s', 'now')")
        params.append(track_id)
        execute(
            f"UPDATE tracks SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
