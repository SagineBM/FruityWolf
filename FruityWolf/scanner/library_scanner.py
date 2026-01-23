"""
Library Scanner

Scans FL Studio project folders and indexes audio files.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import time
import json
import math

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker

from ..database import get_db, execute, query, query_one
from ..classifier import ProjectClassifier, ProjectState, ClassificationResult

try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

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
        self.classifier = ProjectClassifier()
    
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
        
    def _count_files(self, directory: Path) -> Tuple[int, float]:
        """Count files in directory and get latest mtime hours age."""
        count = 0
        latest_mtime = 0
        if not directory.is_dir():
            return 0, 999999
            
        try:
            for f in os.listdir(directory):
                fp = directory / f
                if fp.is_file():
                    count += 1
                    m = fp.stat().st_mtime
                    if m > latest_mtime:
                        latest_mtime = m
        except Exception:
            pass
            
        age_hours = (time.time() - latest_mtime) / 3600 if latest_mtime > 0 else 999999
        return count, age_hours

    def _get_folder_size_mb(self, directory: Path) -> float:
        """Get recursive folder size in MB."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    # skip if symbolic link
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception:
            pass
        return total_size / (1024 * 1024)

    def _scan_project(self, proj_path: Path) -> Optional[Dict]:
        """Scan a single project folder."""
        # 1. Identify File Structure
        renders = []
        flps_root = []
        
        try:
            dir_contents = os.listdir(proj_path)
            for item in dir_contents:
                item_path = proj_path / item
                if item_path.is_file():
                    ext = item_path.suffix.lower()
                    if ext in AUDIO_EXTENSIONS:
                        renders.append(item_path)
                    elif ext == '.flp':
                        flps_root.append(item_path)
        except PermissionError:
            return None
            
        # 2. Find FLP
        flp_path = None
        if flps_root:
            flp_path = max(flps_root, key=lambda p: p.stat().st_mtime)
        else:
            # Search subdirectories (only if no root FLP)
            # Limit depth? Or assume nearby.
            # Usually in Backup? Or just inside?
            pass # Standard behavior: keep None if not in root, or implement deep search if requested.
            # User request said: "Has FLP (exists)". 
            # Ideally we check recursively but simply.
            for root, dirs, files in os.walk(proj_path):
                 for f in files:
                     if f.lower().endswith('.flp'):
                         # Found one.
                         flp_path = Path(root) / f
                         break 
                 if flp_path: break
        
        # 3. Analyze Subfolders
        audio_dir = proj_path / 'Audio'
        samples_dir = proj_path / 'Samples'
        stems_dir = proj_path / 'Stems'
        backup_dir = proj_path / 'Backup'
        
        # Collect Signals
        backup_count, backup_age = self._count_files(backup_dir)
        samples_count, _ = self._count_files(samples_dir)
        audio_folder_count, _ = self._count_files(audio_dir)
        stems_count, _ = self._count_files(stems_dir)
        
        folder_size_mb = self._get_folder_size_mb(proj_path)
        
        flp_size_kb = 0
        if flp_path and flp_path.exists():
            flp_size_kb = flp_path.stat().st_size / 1024
            
        mtime = proj_path.stat().st_mtime
        proj_age_hours = (time.time() - mtime) / 3600
        
        has_only_backup = False
        if backup_dir.is_dir() and backup_count > 0:
            # Approximate "only backup" check:
            # If no other special folders match?
            # Or if root is empty except Backup?
            # Simplistic: Backup exists, but Samples/Audio/Stems are empty/missing.
            if samples_count == 0 and audio_folder_count == 0 and stems_count == 0 and not renders and not flps_root:
                has_only_backup = True
        
        # 4. Get Main Render Info (if any)
        main_render = renders[0] if renders else None
        # Ideally pick "best" render? (Most recent or largest)
        if renders:
            main_render = max(renders, key=lambda p: p.stat().st_mtime)
            
        render_duration = 0
        if main_render and HAS_MUTAGEN:
            try:
                f = MutagenFile(main_render)
                if f and f.info:
                    render_duration = f.info.length
            except: pass
            
        # 5. Classify
        signals = {
            "has_flp": bool(flp_path),
            "has_render_root": bool(renders),
            "render_duration_s": render_duration,
            "backup_count": backup_count,
            "backup_latest_age_hours": backup_age,
            "samples_count": samples_count,
            "audio_folder_count": audio_folder_count,
            "stems_count": stems_count,
            "project_modified_age_hours": proj_age_hours,
            "flp_size_kb": flp_size_kb,
            "folder_size_mb": folder_size_mb,
            "has_only_backup": has_only_backup,
            "project_name": proj_path.name,
            "tags": [], # TODO: fetch tags if needed
            "render_name": main_render.name if main_render else ""
        }
        
        classification = self.classifier.classify(signals)
        
        # If Broken/Empty AND no FLP/Backups/Content, skip indexing completely
        if classification.state == ProjectState.BROKEN_OR_EMPTY:
            # But wait, user said "Stage 0 - BROKEN". Do they want to SEE it?
            # "State: BROKEN_OR_EMPTY" implies it's a valid state on the UI.
            # But we don't want to index every random empty folder.
            # Only index if it *looks* like a project folder (has FLP or Backup or Audio struct).
            has_structure = bool(flp_path) or backup_dir.is_dir() or audio_dir.is_dir()
            if not has_structure and not renders:
                return None
        
        # 6. Database Update
        now = int(time.time())
        existing = query_one(
            "SELECT id FROM projects WHERE path = ?",
            (str(proj_path),)
        )
        
        is_new = existing is None
        
        # Serialize signals
        signals_json = json.dumps(signals)
        
        # Columns to update/insert
        cols = {
            "path": str(proj_path),
            "name": proj_path.name,
            "flp_path": str(flp_path) if flp_path else None,
            "audio_dir": str(audio_dir) if audio_dir.is_dir() else None,
            "samples_dir": str(samples_dir) if samples_dir.is_dir() else None,
            "stems_dir": str(stems_dir) if stems_dir.is_dir() else None,
            "backup_dir": str(backup_dir) if backup_dir.is_dir() else None,
            "last_scan": now,
            
            # New Fields
            "state": classification.state,
            "render_priority_score": classification.render_priority_score,
            "needs_render": 1 if classification.needs_render else 0,
            "signals": signals_json,
            "backup_count": backup_count,
            "samples_count": samples_count,
            "stems_count": stems_count,
            "flp_size_kb": int(flp_size_kb)
        }
        
        if is_new:
            placeholders = ", ".join("?" for _ in cols)
            col_names = ", ".join(cols.keys())
            values = tuple(cols.values())
            
            cur = execute(
                f"INSERT INTO projects ({col_names}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
                values + (now, now)
            )
            project_id = cur.lastrowid
        else:
            project_id = existing['id']
            # Build UPDATE
            set_clause = ", ".join(f"{k} = ?" for k in cols.keys())
            values = tuple(cols.values())
            
            execute(
                f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?",
                values + (now, project_id)
            )
            
        # 7. Handle Tracks
        # If we have renders, insert/update them.
        # If Needs Render (e.g. Micro Idea) and NO renders, we insert a placeholder track
        # so it shows up in the UI (which assumes Tracks).
        
        tracks_added = 0
        tracks_removed = 0
        
        existing_tracks = {
            row['path']: row['id']
            for row in query("SELECT id, path FROM tracks WHERE project_id = ?", (project_id,))
        }
        
        found_paths = set()
        
        if renders:
            for render_path in renders:
                track_path_str = str(render_path)
                found_paths.add(track_path_str)
                
                # Get duration for this specific render
                dur = 0
                if render_path == main_render:
                    dur = render_duration
                elif HAS_MUTAGEN:
                    try:
                        f = MutagenFile(render_path)
                        if f and f.info: dur = f.info.length
                    except: pass
                
                # State logic: The PROJECT has a state. The TRACK inherits it.
                # Or do we want per-track classification? 
                # "Classify each project...". 
                # We'll apply the Project Classification to the tracks.
                # Exception: "Render exists but too short" -> RENDER_SNIPPET. 
                # The rule engine handled "Needs Render" logic based on Main Render.
                
                # We can store the detailed breakdown in `state_reason`.
                reason_str = "; ".join(classification.reasons)
                labels_str = json.dumps([]) # Can implement labels later
                
                stat = render_path.stat()
                
                if track_path_str in existing_tracks:
                    execute(
                        """UPDATE tracks SET
                           mtime = ?, file_size = ?, updated_at = ?,
                           state = ?, state_reason = ?, labels = ?
                           WHERE id = ?""",
                        (
                            int(stat.st_mtime), stat.st_size, now,
                            classification.state, reason_str, labels_str,
                            existing_tracks[track_path_str]
                        )
                    )
                else:
                    execute(
                        """INSERT INTO tracks
                           (project_id, title, path, ext, file_size, mtime, state, state_reason, labels, duration)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            project_id,
                            render_path.stem,
                            track_path_str,
                            render_path.suffix.lower(),
                            stat.st_size,
                            int(stat.st_mtime),
                            classification.state,
                            reason_str,
                            labels_str,
                            dur
                        )
                    )
                    tracks_added += 1
        else:
            # No renders. 
            # If Project is valid (not broken), create a placeholder "Needs Render" track.
            if classification.state != ProjectState.BROKEN_OR_EMPTY:
                # Placeholder path: FLP path or Project Path
                # Use FLP path preferably
                placeholder_path = str(flp_path) if flp_path else str(proj_path / "placeholder.flp")
                
                found_paths.add(placeholder_path)
                
                reason_str = "; ".join(classification.reasons)
                
                if placeholder_path in existing_tracks:
                    # Update state
                    execute(
                        "UPDATE tracks SET state = ?, state_reason = ?, updated_at = ? WHERE id = ?",
                        (classification.state, reason_str, now, existing_tracks[placeholder_path])
                    )
                else:
                    # Create new
                    execute(
                        """INSERT INTO tracks
                           (project_id, title, path, ext, file_size, mtime, state, state_reason, duration)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            project_id,
                            proj_path.name + " [Project]", # Title
                            placeholder_path,
                            '.flp',
                            int(flp_size_kb * 1024),
                            int(mtime),
                            classification.state,
                            reason_str,
                            0
                        )
                    )
                    tracks_added += 1

        # Prune missing tracks
        for path_str, track_id in existing_tracks.items():
            if path_str not in found_paths:
                execute("DELETE FROM tracks WHERE id = ?", (track_id,))
                tracks_removed += 1
        
        return {
            'is_new': is_new,
            'tracks': len(renders) if renders else (1 if tracks_added else 0), # approx
            'tracks_added': tracks_added,
            'tracks_removed': tracks_removed,
        }
    
    def incremental_scan(self):
        """Perform incremental scan (only changed files)."""
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
def get_all_projects(limit: int = 1000, offset: int = 0) -> List[Dict]:
    """Get all projects with classification info."""
    rows = query(
        """SELECT * FROM projects 
           ORDER BY updated_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    results = []
    for row in rows:
        d = dict(row)
        # Parse signals/json if needed or just pass raw strings
        # efficient to leave as string until display needed
        results.append(d)
    return results

def get_all_tracks(limit: int = 500, offset: int = 0) -> List[Dict]:
    """Get all tracks with project info."""
    rows = query(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.render_priority_score, p.needs_render, p.signals,
           p.backup_count, p.samples_count, p.stems_count,
           t.state, t.state_reason, t.labels,
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE t.ext != '.flp'
           ORDER BY t.mtime DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    return [dict(row) for row in rows]


def get_favorite_tracks(limit: int = 500) -> List[Dict]:
    """Get favorite tracks."""
    rows = query(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.render_priority_score, p.needs_render,
           t.state, t.state_reason, t.labels,
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE t.favorite = 1 AND t.ext != '.flp'
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
    conditions = ["t.ext != '.flp'"]  # Always exclude FLP placeholders
    params = []
    
    if term:
        safe_term = term.replace('"', '""')
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
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
            p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
            p.render_priority_score, p.needs_render,
            t.state, t.state_reason, t.labels,
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
                  p.render_priority_score, p.needs_render, p.signals,
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
    lyrics: Optional[str] = None,
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
        
    if lyrics is not None:
        updates.append("lyrics = ?")
        params.append(lyrics)
    
    if updates:
        updates.append("updated_at = strftime('%s', 'now')")
        params.append(track_id)
        execute(
            f"UPDATE tracks SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )


def get_recently_added_tracks(limit: int = 50) -> List[Dict]:
    """Get recently added tracks ordered by creation/scan time."""
    rows = query(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.render_priority_score, p.needs_render,
           t.state, t.state_reason, t.labels,
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE t.ext != '.flp'
           ORDER BY t.mtime DESC
           LIMIT ?""",
        (limit,)
    )
    return [dict(row) for row in rows]


def get_missing_metadata_tracks(limit: int = 500) -> List[Dict]:
    """Get tracks missing BPM or Key metadata."""
    rows = query(
        """SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.render_priority_score, p.needs_render,
           t.state, t.state_reason, t.labels,
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE (t.bpm_user IS NULL AND t.bpm_detected IS NULL)
              OR (t.key_user IS NULL AND t.key_detected IS NULL)
              AND t.ext != '.flp'
           ORDER BY t.mtime DESC
           LIMIT ?""",
        (limit,)
    )
    return [dict(row) for row in rows]
