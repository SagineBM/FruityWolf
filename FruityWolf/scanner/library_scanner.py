"""
Library Scanner

Scans FL Studio project folders and indexes audio files.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time
import json
import math

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker

from ..database import get_db, execute, query, query_one
from ..classifier.engine import ProjectClassifier, ProjectState, ClassificationResult
from .fl_project_detector import detect_fl_project_root, find_all_flp_files
from .fl_render_classifier import (
    find_project_renders, classify_audio_file,
    find_internal_audio, find_source_samples
)

try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# FLP Parser for deep project intelligence
try:
    from ..flp_parser import FLPParser
    HAS_FLP_PARSER = True
except ImportError:
    HAS_FLP_PARSER = False

logger = logging.getLogger(__name__)

# Supported audio formats
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif'}


@dataclass
class ScanResult:
    """Consolidated result of a library scan."""
    projects_found: int = 0
    projects_updated: int = 0
    tracks_found: int = 0
    tracks_added: int = 0
    tracks_removed: int = 0
    renders_added: int = 0
    renders_removed: int = 0
    added_track_ids: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    


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
        self.flp_parser = FLPParser() if HAS_FLP_PARSER else None
    
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
        
        # First pass: detect FL Studio project roots using scoring
        for root in roots:
            if self.is_cancelled():
                return
            
            try:
                for name in os.listdir(root):
                    proj_path = root / name
                    if not proj_path.is_dir():
                        continue
                    
                    # Use FL Studio project detector
                    detection = detect_fl_project_root(proj_path)
                    if detection.is_fl_project:
                        all_projects.append(proj_path)
                        total_projects += 1
                    else:
                        logger.debug(f"Skipping {proj_path.name}: {detection.detection_reason}")
            except PermissionError as e:
                result.errors.append(f"Permission denied: {root}")
                logger.error(f"Permission denied scanning {root}: {e}")
        
        # Second pass: scan projects
        last_emit_time = 0
        
        for idx, proj_path in enumerate(all_projects):
            if self.is_cancelled():
                break
            
            # Throttle progress (max 20fps = 50ms)
            current_time = time.time()
            if current_time - last_emit_time > 0.05 or idx == total_projects - 1:
                self.progress.emit(idx + 1, total_projects, f"Scanning: {proj_path.name}")
                last_emit_time = current_time
            
            try:
                # Log scan time for performance monitoring
                t0 = time.perf_counter()
                project_result = self._scan_project(proj_path)
                t1 = time.perf_counter()
                
                if project_result:
                    result.projects_found += 1
                    result.tracks_found += project_result.get('tracks', 0)
                    if project_result.get('is_new'):
                        result.projects_updated += 1
                    result.tracks_added += project_result.get('tracks_added', 0)
                    result.tracks_removed += project_result.get('tracks_removed', 0)
                    result.renders_added += project_result.get('renders_added', 0)
                    result.renders_removed += project_result.get('renders_removed', 0)
                    result.added_track_ids.extend(project_result.get('added_ids', []))
                    
                    if (t1 - t0) > 0.5: # Log slow scans
                        logger.debug(f"Slow scan ({t1-t0:.2f}s): {proj_path.name}")
                        
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
            return 0, 999999.0
            
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
            
        age_hours = (time.time() - latest_mtime) / 3600 if latest_mtime > 0 else 999999.0
        return count, age_hours

    def _get_folder_size_mb(self, directory: Path) -> float:
        """Get recursive folder size in MB."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception:
            pass
        return total_size / (1024 * 1024)

    def _save_flp_data(self, project_id: int, flp_data: dict, now: int):
        """Save extracted FLP data to database."""
        if not flp_data: return
        
        # 1. Update Project Metadata
        execute(
            """UPDATE projects SET 
               flp_tempo = ?, flp_time_sig = ?, flp_version = ?,
               flp_title = ?, flp_artist = ?, flp_genre = ?,
               flp_pattern_count = ?, flp_parsed_at = ?
               WHERE id = ?""",
            (
                flp_data.get('tempo'),
                flp_data.get('time_sig'),
                flp_data.get('version'),
                flp_data.get('title'),
                flp_data.get('artist'),
                flp_data.get('genre'),
                flp_data.get('pattern_count', 0),
                now,
                project_id
            )
        )
        
        # 2. Save Plugins
        # Clear old ones first (full refresh strategy for simplicity)
        execute("DELETE FROM project_plugins WHERE project_id = ?", (project_id,))
        
        plugins = flp_data.get('plugins', [])
        if plugins:
            values = []
            seen_plugins = set()  # Deduplicate by (name, type, slot, mixer_track)
            
            for p in plugins:
                plugin_name = p.get('name', 'Unknown')
                plugin_type = p.get('type', 'generator')
                channel_idx = p.get('channel_index')
                slot_idx = p.get('slot')
                mixer_track = p.get('mixer_track')
                preset = p.get('preset')
                plugin_path = p.get('path')
                
                # Create deduplication key
                # For generators: (name, type, channel_index)
                # For effects: (name, type, slot, mixer_track)
                if plugin_type == 'generator':
                    dedup_key = (plugin_name, plugin_type, channel_idx)
                else:
                    dedup_key = (plugin_name, plugin_type, slot_idx, mixer_track)
                
                # Skip duplicates
                if dedup_key in seen_plugins:
                    continue
                seen_plugins.add(dedup_key)
                
                values.append((
                    project_id,
                    plugin_name,
                    plugin_type,
                    channel_idx,
                    slot_idx,
                    preset,
                    plugin_path,
                    now
                ))
            
            # Bulk Insert
            if values:
                with get_db().cursor() as cursor:
                    cursor.executemany(
                        """INSERT INTO project_plugins 
                           (project_id, plugin_name, plugin_type, channel_index, mixer_slot, preset_name, plugin_path, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        values
                    )
        
        # 3. Save Samples
        execute("DELETE FROM project_samples WHERE project_id = ?", (project_id,))
        
        samples = flp_data.get('samples', [])
        unique_samples = set() # Avoid duplicates in list
        
        if samples:
            sample_values = []
            for s in samples:
                path = s.get('path') or s.get('filename')
                if not path: continue
                
                # Normalize path for uniqueness check
                try:
                    norm_path = str(Path(path))
                except:
                    norm_path = str(path)
                    
                if norm_path in unique_samples: continue
                unique_samples.add(norm_path)
                
                name = Path(norm_path).name
                sample_values.append((
                    project_id,
                    name,
                    norm_path,
                    now
                ))
                
            if sample_values:
                with get_db().cursor() as cursor:
                    cursor.executemany(
                        """INSERT INTO project_samples 
                           (project_id, sample_name, sample_path, created_at)
                           VALUES (?, ?, ?, ?)""",
                        sample_values
                    )

    def _scan_project(self, proj_path: Path) -> Optional[Dict]:
        """
        Scan a single FL Studio project folder.
        Uses FL Studio-aware detection and render classification.
        """
        # 1. Detect FL Studio project root (with scoring)
        detection = detect_fl_project_root(proj_path)
        if not detection.is_fl_project:
            logger.debug(f"Skipping {proj_path.name}: not an FL Studio project ({detection.detection_reason})")
            return None
        
        # Use detected FLP paths
        flp_path = Path(detection.primary_flp_path) if detection.primary_flp_path else None
        all_flp_paths = detection.flp_paths
        
        # 2. Find RENDERS (root-level audio only, excluding Audio/Samples/Backup)
        render_classifications = find_project_renders(proj_path)
        renders = [Path(c.path) for c in render_classifications if c.classification == 'RENDER']
        
        # 3. Analyze Subfolders (for classification signals, not for renders)
        audio_dir = proj_path / 'Audio'
        samples_dir = proj_path / 'Samples'
        stems_dir = proj_path / 'Stems'
        backup_dir = proj_path / 'Backup'
        
        # Collect Raw Signals
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
            if samples_count == 0 and audio_folder_count == 0 and stems_count == 0 and not renders:
                has_only_backup = True
        
        # 4. Get Main Render Info (latest render by mtime)
        main_render = max(renders, key=lambda p: p.stat().st_mtime) if renders else None
        render_duration = 0
        if main_render and HAS_MUTAGEN:
            try:
                f = MutagenFile(main_render)
                if f and f.info:
                    render_duration = f.info.length
            except: pass
            
        # 5. Classify
        # Split signals into proper raw/derived for updated engine
        signals_raw = {
            "has_flp": bool(flp_path),
            "has_render_root": bool(renders),
            "render_duration_s": render_duration,
            "backup_count": backup_count,
            "samples_count": samples_count,
            "audio_folder_count": audio_folder_count,
            "stems_count": stems_count,
            "flp_size_kb": flp_size_kb,
            "folder_size_mb": folder_size_mb,
            "project_name": proj_path.name,
            "user_tags": [] # TODO: Fetch user tags from DB if available
        }
        
        signals_derived = {
            "project_modified_age_hours": proj_age_hours,
            "backup_latest_age_hours": backup_age,
            "has_only_backup": has_only_backup,
            "is_tiny_render": bool(main_render) and render_duration < 20 # Can logic this
        }
        
        classification = self.classifier.classify(signals_raw, signals_derived)
        
        # Skip garbage
        if classification.state_id == ProjectState.BROKEN_OR_EMPTY:
            has_structure = bool(flp_path) or backup_dir.is_dir() or audio_dir.is_dir()
            if not has_structure and not renders:
                return None
        
        # 6. Database Update
        now = int(time.time())
        
        # Check if primary_render_id column exists (for backwards compatibility)
        try:
            test_col = query_one("PRAGMA table_info(projects)")
            has_primary_render_id = any(col['name'] == 'primary_render_id' for col in test_col if isinstance(test_col, list) or hasattr(test_col, '__iter__'))
            if not has_primary_render_id:
                # Try alternative check
                cols = query("PRAGMA table_info(projects)")
                has_primary_render_id = any(col.get('name') == 'primary_render_id' for col in cols)
        except:
            has_primary_render_id = False
        
        if has_primary_render_id:
            existing = query_one(
                "SELECT id, primary_render_id FROM projects WHERE path = ?",
                (str(proj_path),)
            )
            existing_primary_render_id = existing['primary_render_id'] if existing else None
        else:
            existing = query_one(
                "SELECT id FROM projects WHERE path = ?",
                (str(proj_path),)
            )
            existing_primary_render_id = None
        
        is_new = existing is None
        
        # Combine signals for storage
        full_signals = {"raw": signals_raw, "derived": signals_derived}
        signals_json = json.dumps(full_signals)
        
        # Phase 1: Robust Columns
        cols = {
            "path": str(proj_path),
            "name": proj_path.name,
            "flp_path": str(flp_path) if flp_path else None,
            "audio_dir": str(audio_dir) if audio_dir.is_dir() else None,
            "samples_dir": str(samples_dir) if samples_dir.is_dir() else None,
            "stems_dir": str(stems_dir) if stems_dir.is_dir() else None,
            "backup_dir": str(backup_dir) if backup_dir.is_dir() else None,
            "last_scan": now,
            
            # --- New Robust Fields ---
            "state_id": classification.state_id,
            "state_confidence": classification.state_confidence,
            "state_reason": json.dumps(classification.state_reasons),
            
            "score": classification.score,
            "score_breakdown": json.dumps(classification.score_breakdown),
            
            "next_action_id": classification.next_action_id,
            "next_action_meta": json.dumps(classification.next_action_meta),
            "next_action_reason": json.dumps(classification.next_action_reasons),
            
            "signals": signals_json,
            "classified_at_ts": classification.classified_at_ts,
            "ruleset_hash": classification.ruleset_hash,
            
            # Legacy/Helper Fields - Maintain for existing queries or easy debug
            "state": classification.state_id, 
            "render_priority_score": classification.score, # Alias to completion score for now
            "needs_render": 1 if classification.needs_render else 0,
            
            "backup_count": backup_count,
            "samples_count": samples_count,
            "stems_count": stems_count,
            "flp_size_kb": int(flp_size_kb)
        }
        
        if is_new:
            # Add user_meta default for new projects
            cols["user_meta"] = json.dumps({})
            
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
            # Don't overwrite user_meta on scan!
            
            set_clause = ", ".join(f"{k} = ?" for k in cols.keys())
            values = tuple(cols.values())
            
            
            execute(
                f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?",
                values + (now, project_id)
            )
            
        # 6b. Parse FLP Content (Plugins/Samples) if available
        if flp_path and flp_path.exists():
            try:
                from ..flp_parser.parser import FLPParser
                parser = FLPParser()
                # Only parse if enabled (pyflp installed)
                if parser.enabled:
                    flp_data = parser.parse(str(flp_path))
                    if flp_data:
                        self._save_flp_data(project_id, flp_data, now)
            except Exception as e:
                logger.warning(f"FLP parsing failed for {proj_path.name}: {e}")
                # Don't fail the whole scan for this
            
        # 7. Handle RENDERS (new system)
        # Check if renders table exists
        try:
            test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
            has_renders_table = test_row is not None
        except:
            has_renders_table = False
        
        renders_added = 0
        renders_removed = 0
        existing_renders = {}
        found_render_paths = set()
        
        if has_renders_table:
            try:
                existing_renders = {
                    row['path']: row['id']
                    for row in query("SELECT id, path FROM renders WHERE project_id = ?", (project_id,))
                }
            except Exception as e:
                logger.debug(f"Could not query renders table: {e}")
                has_renders_table = False
        
        # Helper to compute fingerprint for caching
        def compute_fingerprint(path: Path) -> str:
            """Compute fast fingerprint (size + mtime hash) for duration caching."""
            try:
                stat = path.stat()
                import hashlib
                hash_input = f"{stat.st_size}:{stat.st_mtime}"
                return hashlib.md5(hash_input.encode()).hexdigest()
            except:
                return ""
        
        # Helper to get duration (with caching)
        def get_duration_cached(path: Path, fingerprint: str) -> float:
            """Get duration, checking cache first."""
            # Check cache (only if renders table exists)
            if has_renders_table:
                try:
                    cached = query_one(
                        "SELECT duration_s FROM renders WHERE fingerprint_fast = ? AND path = ?",
                        (fingerprint, str(path))
                    )
                    if cached and cached['duration_s']:
                        return float(cached['duration_s'])
                except:
                    pass
            
            # Compute duration
            duration = 0
            if HAS_MUTAGEN:
                try:
                    f = MutagenFile(path)
                    if f and f.info:
                        duration = f.info.length
                except:
                    pass
            
            return duration
        
        # Process renders (only if renders table exists)
        render_ids = []
        if not has_renders_table:
            logger.debug(f"Renders table not available, skipping render processing for {proj_path.name}")
        else:
            for render_path in renders:
                render_path_str = str(render_path)
                found_render_paths.add(render_path_str)
                
                fingerprint = compute_fingerprint(render_path)
                duration = get_duration_cached(render_path, fingerprint)
                
                # Use main_render duration if available
                if render_path == main_render and render_duration > 0:
                    duration = render_duration
                
                stat = render_path.stat()
                filename = render_path.name
                ext = render_path.suffix.lower()
                
                if render_path_str in existing_renders:
                    # Update existing render
                    render_id = existing_renders[render_path_str]
                    execute(
                        """UPDATE renders SET
                           mtime = ?, file_size = ?, duration_s = ?, fingerprint_fast = ?, updated_at = ?
                           WHERE id = ?""",
                        (int(stat.st_mtime), stat.st_size, duration, fingerprint, now, render_id)
                    )
                    render_ids.append(render_id)
                else:
                    # Insert new render
                    cur = execute(
                        """INSERT INTO renders
                           (project_id, path, filename, ext, file_size, mtime, duration_s, fingerprint_fast, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            project_id, render_path_str, filename, ext,
                            stat.st_size, int(stat.st_mtime), duration, fingerprint,
                            now, now
                        )
                    )
                    render_id = cur.lastrowid
                    render_ids.append(render_id)
                    renders_added += 1
            
            # Prune removed renders
            for path_str, render_id in existing_renders.items():
                if path_str not in found_render_paths:
                    try:
                        execute("DELETE FROM renders WHERE id = ?", (render_id,))
                        renders_removed += 1
                    except Exception as e:
                        logger.debug(f"Could not delete render: {e}")
        
        # 8. Determine primary render (only if renders table exists)
        primary_render_id = existing_primary_render_id if has_primary_render_id else None
        
        # If no primary set, use latest render (by default, latest root-level render)
        # This ensures the most recent render in the project root is the primary
        if has_renders_table and not primary_render_id and render_ids:
            try:
                # Get latest render by mtime (should be the newest root-level render)
                latest_render = query_one(
                    "SELECT id FROM renders WHERE project_id = ? ORDER BY mtime DESC LIMIT 1",
                    (project_id,)
                )
                if latest_render:
                    primary_render_id = latest_render['id']
                    # Set it immediately so it's saved
                    if has_primary_render_id:
                        execute(
                            "UPDATE projects SET primary_render_id = ? WHERE id = ?",
                            (primary_render_id, project_id)
                        )
            except Exception as e:
                logger.debug(f"Could not determine latest render: {e}")
        
        # Update primary_render_id if changed (only if column exists)
        if has_primary_render_id and primary_render_id != existing_primary_render_id:
            try:
                execute(
                    "UPDATE projects SET primary_render_id = ? WHERE id = ?",
                    (primary_render_id, project_id)
                )
            except Exception as e:
                logger.debug(f"Could not update primary_render_id (column may not exist): {e}")
        
        # Mark primary render (only if renders table exists)
        if primary_render_id and has_renders_table:
            try:
                execute(
                    "UPDATE renders SET is_primary = 1 WHERE id = ?",
                    (primary_render_id,)
                )
                execute(
                    "UPDATE renders SET is_primary = 0 WHERE project_id = ? AND id != ?",
                    (project_id, primary_render_id)
                )
            except Exception as e:
                logger.debug(f"Could not update render primary flags: {e}")
        
        # 9. Legacy tracks support (for backwards compatibility)
        # Create a placeholder track pointing to primary render for UI compatibility
        tracks_added = 0
        tracks_removed = 0
        added_ids = []
        
        if primary_render_id:
            primary_render = query_one("SELECT path, duration_s FROM renders WHERE id = ?", (primary_render_id,))
            if primary_render:
                primary_path = primary_render['path']
                primary_duration = primary_render['duration_s'] or 0
                
                # Upsert legacy track entry
                existing_tracks = {
                    row['path']: row['id']
                    for row in query("SELECT id, path FROM tracks WHERE project_id = ?", (project_id,))
                }
                
                if primary_path not in existing_tracks:
                    title = Path(primary_path).stem
                    ext = Path(primary_path).suffix.lower()
                    stat = Path(primary_path).stat()
                    
                    track_id = execute(
                        """INSERT INTO tracks
                           (project_id, title, path, ext, file_size, mtime, state, state_reason, duration)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            project_id, title, primary_path, ext,
                            stat.st_size, int(stat.st_mtime),
                            classification.state_id,
                            "; ".join(classification.state_reasons),
                            primary_duration
                        )
                    )
                    if track_id:
                        added_ids.append(track_id)
                        tracks_added += 1
        
        # 8. Index Samples (Phase 2)
        if samples_dir.is_dir():
            try:
                # Clear existing samples to Avoid duplicates/stale links or just INSERT OR IGNORE
                # Better to clear and re-index for this project to be safe
                execute("DELETE FROM project_samples WHERE project_id = ?", (project_id,))
                
                for root, _, files in os.walk(samples_dir):
                    for f in files:
                        if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                            sample_path = os.path.join(root, f)
                            execute(
                                "INSERT OR IGNORE INTO project_samples (project_id, sample_name, sample_path) VALUES (?, ?, ?)",
                                (project_id, f, sample_path)
                            )
            except Exception as e:
                logger.error(f"Failed to index samples for {proj_path.name}: {e}")

        return {
            'is_new': is_new,
            'tracks': len(renders),  # Render count
            'tracks_added': tracks_added,  # Legacy tracks
            'tracks_removed': tracks_removed,
            'added_ids': added_ids,
            'renders_added': renders_added,
            'renders_removed': renders_removed,
            'render_count': len(renders),
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
def get_project_with_renders(project_id: int) -> Optional[Dict]:
    """Get a project with its primary render info."""
    project = query_one(
        """SELECT p.*, 
           r.path as render_path, r.filename as render_filename, 
           r.duration_s as render_duration, r.mtime as render_mtime,
           (SELECT COUNT(*) FROM renders WHERE project_id = p.id) as render_count
           FROM projects p
           LEFT JOIN renders r ON p.primary_render_id = r.id
           WHERE p.id = ?""",
        (project_id,)
    )
    return dict(project) if project else None


def get_all_projects(limit: int = 1000, offset: int = 0) -> List[Dict]:
    """Get all projects with classification info."""
    rows = query(
        """SELECT * FROM projects 
           ORDER BY updated_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    return [dict(row) for row in rows]

def search_projects(
    term: str = '',
    stage_filter: str = 'All Stages',
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """Search projects with filters at the DB level for performance."""
    conditions = []
    params = []
    
    # 1. Stage Filter / Smart Views
    if stage_filter == "High Potential":
        conditions.append("(score >= 60 AND state_id NOT IN ('FINAL', 'BROKEN_OR_EMPTY'))")
    elif stage_filter == "Needs Render":
        conditions.append("next_action_id LIKE '%render%'")
    elif stage_filter == "Almost Finished":
        conditions.append("(score >= 80 AND state_id != 'FINAL')")
    elif stage_filter == "Dead Projects":
        conditions.append("state_id LIKE '%DEAD%'")
    elif stage_filter != "All Stages" and "---" not in stage_filter:
        # Regular stage mapping
        target = stage_filter.upper().replace(" ", "_").replace("/", "_OR_")
        conditions.append("state_id LIKE ?")
        params.append(f"%{target}%")
        
    # 2. Term search (simple name match for now, could use FTS but projects table might not have it)
    if term:
        conditions.append("name LIKE ?")
        params.append(f"%{term}%")
        
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
        
    # Check if renders table exists (for backwards compatibility during migration)
    try:
        test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
        has_renders_table = test_row is not None
    except:
        has_renders_table = False
    
    if has_renders_table:
        rows = query(
            f"""SELECT p.*, 
                       (SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id) as render_count,
                       r.path as render_path, r.filename as render_filename,
                       r.duration_s as render_duration, r.mtime as render_mtime
                FROM projects p 
                LEFT JOIN renders r ON p.primary_render_id = r.id
               {where_clause}
               ORDER BY p.updated_at DESC
               LIMIT ? OFFSET ?""",
            tuple(params) + (limit, offset)
        )
    else:
        # Fallback: use tracks table for render count (legacy behavior)
        rows = query(
            f"""SELECT p.*, 
                       (SELECT COUNT(*) FROM tracks t WHERE t.project_id = p.id AND t.ext != '.flp') as render_count,
                       NULL as render_path, NULL as render_filename,
                       NULL as render_duration, NULL as render_mtime
                FROM projects p 
               {where_clause}
               ORDER BY p.updated_at DESC
               LIMIT ? OFFSET ?""",
            tuple(params) + (limit, offset)
        )
    return [dict(row) for row in rows]

def _has_state_columns() -> bool:
    """Check if tracks table has state classification columns."""
    try:
        from ..database import query_one
        # Check if column exists by trying to query it
        query_one("SELECT state FROM tracks LIMIT 1")
        return True
    except:
        return False

def _get_state_columns_sql() -> str:
    """Get SQL fragment for state columns, handling missing columns gracefully."""
    if _has_state_columns():
        return "t.state, t.state_reason, t.labels,"
    else:
        return "NULL as state, NULL as state_reason, NULL as labels,"

def get_all_tracks(limit: int = 500, offset: int = 0) -> List[Dict]:
    """Get all tracks with project info."""
    state_cols = _get_state_columns_sql()
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.score, p.next_action_id, p.state_id,
           {state_cols}
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

def get_all_tracks(limit: int = 500, offset: int = 0) -> List[Dict]:
    """Get all tracks with project info."""
    state_cols = _get_state_columns_sql()
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.score, p.next_action_id, p.state_id,
           {state_cols}
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
    state_cols = _get_state_columns_sql()
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.score, p.next_action_id, p.state_id,
           {state_cols}
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
    conditions = ["t.ext != '.flp'"]
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
    
    state_cols = _get_state_columns_sql()
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
            p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
            p.score, p.next_action_id, p.state_id,
            {state_cols}
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
    state_cols = _get_state_columns_sql()
    
    row = query_one(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
                  p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
                  p.score, p.next_action_id, p.state_id, p.signals,
                  {state_cols}
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
    state_cols = _get_state_columns_sql()
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.score, p.next_action_id, p.state_id,
           {state_cols}
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
    state_cols = _get_state_columns_sql()
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.score, p.next_action_id, p.state_id,
           {state_cols}
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

def get_project_renders(project_id: int) -> List[Dict]:
    """Get all renders for a project, sorted by newest first."""
    # Check if renders table exists
    try:
        test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
        if not test_row:
            logger.debug("Renders table does not exist")
            return []
    except Exception as e:
        logger.debug(f"Could not check renders table: {e}")
        return []
    
    try:
        rows = query(
            """SELECT * FROM renders 
               WHERE project_id = ? 
               ORDER BY mtime DESC""",
            (project_id,)
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to query renders for project {project_id}: {e}")
        return []


def get_primary_render(project_id: int) -> Optional[Dict]:
    """Get the primary render for a project."""
    row = query_one(
        """SELECT * FROM renders 
           WHERE project_id = ? AND is_primary = 1
           LIMIT 1""",
        (project_id,)
    )
    if row:
        return dict(row)
    
    # Fallback to latest if no primary set
    row = query_one(
        """SELECT * FROM renders 
           WHERE project_id = ? 
           ORDER BY mtime DESC 
           LIMIT 1""",
        (project_id,)
    )
    return dict(row) if row else None


def set_primary_render(project_id: int, render_id: int):
    """Set a render as the primary render for a project."""
    # Unset all other primaries
    execute(
        "UPDATE renders SET is_primary = 0 WHERE project_id = ?",
        (project_id,)
    )
    
    # Set new primary
    execute(
        "UPDATE renders SET is_primary = 1 WHERE id = ?",
        (render_id,)
    )
    
    # Update project's primary_render_id
    execute(
        "UPDATE projects SET primary_render_id = ? WHERE id = ?",
        (render_id, project_id)
    )


def get_sample_usage(limit: int = 20) -> List[Dict]:
    """Get top used samples across projects."""
    rows = query(
        """SELECT sample_name, COUNT(*) as count, GROUP_CONCAT(project_id) as project_ids
           FROM project_samples
           GROUP BY sample_name
           ORDER BY count DESC
           LIMIT ?""",
        (limit,)
    )
    return [dict(row) for row in rows]

def get_project_samples(project_id: int) -> List[Dict]:
    """Get all samples used in a specific project."""
    rows = query(
        "SELECT * FROM project_samples WHERE project_id = ? ORDER BY sample_name",
        (project_id,)
    )
    return [dict(row) for row in rows]


# ============================================================================
# Plugin Query Helpers (PyFLP Integration)
# ============================================================================

def get_plugin_usage(limit: int = 20) -> List[Dict]:
    """Get top used plugins across all projects.
    
    Returns:
        List of dicts with plugin_name, count, plugin_type
    """
    rows = query(
        """SELECT plugin_name, plugin_type, COUNT(*) as count, 
           COUNT(DISTINCT project_id) as project_count
           FROM project_plugins
           GROUP BY plugin_name
           ORDER BY project_count DESC
           LIMIT ?""",
        (limit,)
    )
    return [dict(row) for row in rows]


def get_project_plugins(project_id: int) -> List[Dict]:
    """Get all plugins used in a specific project."""
    rows = query(
        """SELECT plugin_name, plugin_type, channel_index, mixer_slot, preset_name
           FROM project_plugins 
           WHERE project_id = ? 
           ORDER BY plugin_type, plugin_name""",
        (project_id,)
    )
    return [dict(row) for row in rows]


def get_projects_using_plugin(plugin_name: str, limit: int = 50) -> List[Dict]:
    """Find all projects that use a specific plugin."""
    rows = query(
        """SELECT DISTINCT p.id, p.name, p.path, p.state_id, p.score
           FROM projects p
           JOIN project_plugins pp ON p.id = pp.project_id
           WHERE pp.plugin_name = ?
           ORDER BY p.updated_at DESC
           LIMIT ?""",
        (plugin_name, limit)
    )
    return [dict(row) for row in rows]


def get_missing_samples_report(limit: int = 100) -> List[Dict]:
    """Get projects with missing samples (from FLP parsing)."""
    # This would be populated by tracking is_missing flag when parsing
    # For now, we can detect by checking if sample paths don't exist
    rows = query(
        """SELECT p.id as project_id, p.name as project_name, 
           ps.sample_name, ps.sample_path
           FROM project_samples ps
           JOIN projects p ON ps.project_id = p.id
           ORDER BY p.name
           LIMIT ?""",
        (limit,)
    )
    return [dict(row) for row in rows]

