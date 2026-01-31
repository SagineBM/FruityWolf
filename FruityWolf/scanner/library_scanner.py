"""
Library Scanner

Scans FL Studio project folders and indexes audio files.

Performance optimizations:
- Schema caching (eliminates repeated PRAGMA queries)
- Incremental scanning (skips unchanged projects)
- Batch transactions (50 projects per commit)
- FLP parse caching (skips re-parsing unchanged FLPs)
- Parallel scanning (optional, uses ThreadPoolExecutor)
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
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker

from ..database import get_db, execute, execute_many, query, query_one, batch_transaction
from ..classifier.engine import ProjectClassifier, ProjectState, ClassificationResult
from ..utils.path_utils import normalize_path
from ..utils.helpers import log_exception
from .fl_project_detector import detect_fl_project_root, find_all_flp_files
from .fl_render_classifier import (
    find_project_renders, classify_audio_file,
    find_internal_audio, find_source_samples,
    arbitrate_flat_folder, match_audio_to_flp,
    RENDER_EXTENSIONS
)
from .identity import IdentityStore, compute_fingerprint, extract_file_signals
from .adapters import get_adapter

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

# Module-level schema cache for UI helper functions
# These are checked once and cached to avoid repeated queries
_schema_cache = {
    'renders_table': None,
    'state_columns': None,
    'file_created_at_projects': None,
    'file_created_at_tracks': None,
}

def _get_cached_renders_table_exists() -> bool:
    """Check if renders table exists (cached)."""
    if _schema_cache['renders_table'] is None:
        try:
            test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
            _schema_cache['renders_table'] = test_row is not None
        except:
            _schema_cache['renders_table'] = False
    return _schema_cache['renders_table']

def _get_cached_state_columns_exist() -> bool:
    """Check if tracks table has state columns (cached)."""
    if _schema_cache['state_columns'] is None:
        try:
            query_one("SELECT state FROM tracks LIMIT 1")
            _schema_cache['state_columns'] = True
        except:
            _schema_cache['state_columns'] = False
    return _schema_cache['state_columns']

def _get_cached_file_created_at_projects() -> bool:
    """Check if projects table has file_created_at column (cached)."""
    if _schema_cache['file_created_at_projects'] is None:
        try:
            query_one("SELECT file_created_at FROM projects LIMIT 1")
            _schema_cache['file_created_at_projects'] = True
        except:
            _schema_cache['file_created_at_projects'] = False
    return _schema_cache['file_created_at_projects']

def _get_cached_file_created_at_tracks() -> bool:
    """Check if tracks table has file_created_at column (cached)."""
    if _schema_cache['file_created_at_tracks'] is None:
        try:
            query_one("SELECT file_created_at FROM tracks LIMIT 1")
            _schema_cache['file_created_at_tracks'] = True
        except:
            _schema_cache['file_created_at_tracks'] = False
    return _schema_cache['file_created_at_tracks']


def get_file_created_at(path: Path) -> int:
    """
    Get the original file creation timestamp (Date created in Windows Explorer).
    
    On Windows, uses st_birthtime if available, otherwise st_ctime.
    On Unix, st_ctime is inode change time, but we use it as best effort.
    
    Returns:
        Unix timestamp of file creation date
    """
    try:
        stat = path.stat()
        # Windows: st_birthtime is the true creation time
        # Python 3.12+ on Windows supports st_birthtime
        if hasattr(stat, 'st_birthtime'):
            return int(stat.st_birthtime)
        # Fallback: st_ctime (creation time on Windows, inode change time on Unix)
        return int(stat.st_ctime)
    except:
        return int(time.time())


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
        
        # Identity system
        self.identity_store = IdentityStore()
        self.adapter = get_adapter('fl_studio')
        
        # Schema cache - populated once at scan start to avoid repeated queries
        self._schema_cached = False
        self._has_renders_table = False
        self._has_primary_render_id = False
        self._has_file_created_at_projects = False
        self._has_file_created_at_tracks = False
        self._has_state_columns = False
        
        # Last scan times cache for incremental scanning
        self._project_last_scans: Dict[str, int] = {}
        
        # Performance settings
        # Skip expensive folder size calculation (os.walk is slow on large directories)
        # Set to False only if folder_size_mb is critical for classification
        self.skip_folder_size_calc = True
    
    def _cache_schema_info(self):
        """Cache database schema info once at scan start to avoid repeated queries."""
        if self._schema_cached:
            return
        
        try:
            # Check if renders table exists
            test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
            self._has_renders_table = test_row is not None
        except:
            self._has_renders_table = False
        
        try:
            # Check if primary_render_id column exists in projects
            cols = query("PRAGMA table_info(projects)")
            col_names = [col['name'] for col in cols]
            self._has_primary_render_id = 'primary_render_id' in col_names
            self._has_file_created_at_projects = 'file_created_at' in col_names
        except:
            self._has_primary_render_id = False
            self._has_file_created_at_projects = False
        
        try:
            # Check if file_created_at column exists in tracks
            cols = query("PRAGMA table_info(tracks)")
            col_names = [col['name'] for col in cols]
            self._has_file_created_at_tracks = 'file_created_at' in col_names
            self._has_state_columns = 'state' in col_names
        except:
            self._has_file_created_at_tracks = False
            self._has_state_columns = False
        
        self._schema_cached = True
        logger.debug(f"Schema cache: renders_table={self._has_renders_table}, "
                    f"primary_render_id={self._has_primary_render_id}, "
                    f"file_created_at_projects={self._has_file_created_at_projects}")
    
    def _load_project_last_scans(self):
        """Load last scan times for all projects for incremental scanning."""
        try:
            rows = query("SELECT path, last_scan FROM projects WHERE last_scan IS NOT NULL")
            self._project_last_scans = {row['path']: row['last_scan'] for row in rows}
            logger.debug(f"Loaded {len(self._project_last_scans)} project last scan times")
        except Exception as e:
            logger.warning(f"Could not load project last scans: {e}")
            self._project_last_scans = {}
    
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
    
    def _project_needs_scan(self, proj_path: Path) -> bool:
        """
        Check if a project needs to be scanned based on folder modification time.
        Returns True if the project is new or has been modified since last scan.
        """
        proj_path_str = str(proj_path)
        
        # Check if we have a last scan time for this project
        last_scan = self._project_last_scans.get(proj_path_str)
        if last_scan is None:
            return True  # New project, needs scan
        
        # Get the folder's modification time
        try:
            folder_mtime = int(proj_path.stat().st_mtime)
            
            # Also check the most recent file modification in the root folder
            # This catches cases where files are added/removed but folder mtime doesn't change
            latest_mtime = folder_mtime
            for item in proj_path.iterdir():
                if item.is_file():
                    item_mtime = int(item.stat().st_mtime)
                    if item_mtime > latest_mtime:
                        latest_mtime = item_mtime
            
            # If folder or any root file was modified after last scan, rescan
            return latest_mtime > last_scan
        except (PermissionError, OSError):
            return True  # If we can't check, assume it needs scan
    
    def scan_all(self, force_full_scan: bool = False, parallel_workers: int = 1):
        """
        Scan all library roots.
        
        Args:
            force_full_scan: If True, scan all projects regardless of modification time.
                           If False (default), only scan projects modified since last scan.
            parallel_workers: Number of parallel workers for scanning. Default 1 (sequential).
                            Set to 4-8 for faster scanning on multi-core systems.
                            Note: Database writes are still serialized, but file I/O is parallel.
        """
        self._cancel = False
        result = ScanResult()
        
        # Cache schema info once at scan start (eliminates thousands of repeated queries)
        self._cache_schema_info()
        self._load_project_last_scans()
        
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
        
        # Filter to only projects that need scanning (incremental scan optimization)
        if not force_full_scan:
            projects_to_scan = [p for p in all_projects if self._project_needs_scan(p)]
            skipped_count = total_projects - len(projects_to_scan)
            if skipped_count > 0:
                logger.info(f"Incremental scan: {len(projects_to_scan)} projects to scan, "
                          f"{skipped_count} unchanged projects skipped")
        else:
            projects_to_scan = all_projects
            logger.info(f"Full scan: scanning all {total_projects} projects")
        
        # Second pass: scan projects in batched transactions
        # Process in batches of 50 projects per transaction for optimal performance
        BATCH_SIZE = 50
        last_emit_time = 0
        scan_total = len(projects_to_scan)
        
        # Use parallel scanning if enabled (parallel_workers > 1)
        use_parallel = parallel_workers > 1
        if use_parallel:
            logger.info(f"Parallel scanning enabled with {parallel_workers} workers")
        
        for batch_start in range(0, scan_total, BATCH_SIZE):
            if self.is_cancelled():
                break
            
            batch_end = min(batch_start + BATCH_SIZE, scan_total)
            batch = projects_to_scan[batch_start:batch_end]
            
            # Update progress for batch start
            current_time = time.time()
            if current_time - last_emit_time > 0.05:
                self.progress.emit(batch_start + 1, scan_total, f"Scanning batch...")
                last_emit_time = current_time
            
            # Process entire batch in a single transaction (major performance boost)
            with batch_transaction():
                if use_parallel and len(batch) > 1:
                    # Parallel scanning: use ThreadPoolExecutor for file I/O
                    # Note: Database writes are serialized by SQLite WAL, but I/O is parallel
                    batch_results = []
                    with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                        # Submit all tasks
                        future_to_path = {
                            executor.submit(self._scan_project, proj_path): proj_path 
                            for proj_path in batch
                        }
                        
                        # Collect results as they complete
                        for future in as_completed(future_to_path):
                            proj_path = future_to_path[future]
                            try:
                                project_result = future.result()
                                if project_result:
                                    batch_results.append((proj_path, project_result))
                            except Exception as e:
                                result.errors.append(f"Error scanning {proj_path}: {e}")
                                logger.exception(f"Error scanning project {proj_path}")
                    
                    # Process results (update counters)
                    for proj_path, project_result in batch_results:
                        result.projects_found += 1
                        result.tracks_found += project_result.get('tracks', 0)
                        if project_result.get('is_new'):
                            result.projects_updated += 1
                        result.tracks_added += project_result.get('tracks_added', 0)
                        result.tracks_removed += project_result.get('tracks_removed', 0)
                        result.renders_added += project_result.get('renders_added', 0)
                        result.renders_removed += project_result.get('renders_removed', 0)
                        result.added_track_ids.extend(project_result.get('added_ids', []))
                else:
                    # Sequential scanning (default)
                    for idx, proj_path in enumerate(batch, start=batch_start):
                        if self.is_cancelled():
                            break
                        
                        # Throttle progress (max 20fps = 50ms)
                        current_time = time.time()
                        if current_time - last_emit_time > 0.05 or idx == scan_total - 1:
                            self.progress.emit(idx + 1, scan_total, f"Scanning: {proj_path.name}")
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
            
            # Update progress for batch end
            current_time = time.time()
            if current_time - last_emit_time > 0.05:
                self.progress.emit(batch_end, scan_total, f"Batch complete")
                last_emit_time = current_time
            
            # Log batch completion
            logger.debug(f"Batch {batch_start//BATCH_SIZE + 1} complete: "
                        f"{batch_end}/{scan_total} projects processed")
        
        # Third pass: scan for orphan FLPs directly in library roots
        # These are flat folder structures where FLPs and audio are in the same folder
        for root in roots:
            if self.is_cancelled():
                break
            
            try:
                orphan_result = self._scan_orphan_flps_in_root(root)
                if orphan_result:
                    result.projects_found += orphan_result.get('projects_added', 0)
                    result.tracks_added += orphan_result.get('tracks_added', 0)
                    result.renders_added += orphan_result.get('renders_added', 0)
                    result.added_track_ids.extend(orphan_result.get('added_ids', []))
            except Exception as e:
                logger.warning(f"Error scanning orphan FLPs in {root}: {e}")
        
        # Update library root last scan time
        now = int(time.time())
        for root in roots:
            execute(
                "UPDATE library_roots SET last_scan = ? WHERE path = ?",
                (now, str(root))
            )
        
        # Verify actual database count matches scan result
        # This ensures accuracy - count what's actually in the database
        try:
            db_project_count = query_one("SELECT COUNT(*) as count FROM projects")
            if db_project_count:
                # Use database count as source of truth
                result.projects_found = db_project_count['count']
                logger.debug(f"Scan complete: {result.projects_found} projects in database (scanned {total_projects} folders)")
        except Exception as e:
            logger.warning(f"Could not verify project count: {e}")
        
        # Reconcile identity system with legacy tables after full scan
        try:
            reconciled = self.reconcile_identity_with_legacy_tables()
            if reconciled > 0:
                logger.debug(f"Reconciled {reconciled} projects after full scan")
        except Exception as e:
            logger.debug(f"Error reconciling after full scan: {e}")
        
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
        except Exception as e:
            logger.debug(f"Error counting files in {directory}: {e}")
            
        age_hours = (time.time() - latest_mtime) / 3600 if latest_mtime > 0 else 999999.0
        return count, age_hours

    def _get_folder_size_mb(self, directory: Path, skip_expensive: bool = True) -> float:
        """
        Get recursive folder size in MB.
        
        Args:
            directory: Path to directory
            skip_expensive: If True, returns 0 to skip expensive os.walk operation.
                          The folder size is only used for classification signals
                          and is not critical for core functionality.
        
        Note: This operation is expensive (uses os.walk) and can significantly
        slow down scanning on large directories. Set skip_expensive=False only
        if folder size is critical for your classification needs.
        """
        if skip_expensive:
            return 0.0
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception as e:
            logger.debug(f"Error getting folder size for {directory}: {e}")
        return total_size / (1024 * 1024)

    def _populate_identity_files(
        self,
        project_id: int,
        proj_path: Path,
        flp_path: Optional[Path],
        all_flp_paths: List[Path],
        renders: List[Path],
        backup_dir: Path,
        stems_dir: Path,
        samples_dir: Path
    ) -> None:
        """
        Populate project_files table with all files found in project.
        This is the write-through layer that catalogs everything.
        """
        try:
            # 1. Catalog FLP files
            for flp in all_flp_paths:
                if not flp.exists():
                    continue
                
                fingerprint = compute_fingerprint(flp)
                if not fingerprint:
                    continue
                
                stat = flp.stat()
                file_id = self.identity_store.upsert_project_file(
                    project_id=project_id,
                    file_path=flp,
                    fingerprint=fingerprint,
                    file_role='flp',
                    file_ext='.flp',
                    file_size=stat.st_size,
                    file_mtime=int(stat.st_mtime),
                    is_primary=(flp == flp_path)
                )
                
                # Extract and write signals
                signals = extract_file_signals(flp)
                self.identity_store.write_signals(file_id, signals)
            
            # 2. Catalog renders
            primary_render_id = None
            primary_score = 0
            
            for render in renders:
                if not render.exists():
                    continue
                
                fingerprint = compute_fingerprint(render)
                if not fingerprint:
                    continue
                
                stat = render.stat()
                file_id = self.identity_store.upsert_project_file(
                    project_id=project_id,
                    file_path=render,
                    fingerprint=fingerprint,
                    file_role='render',
                    file_ext=render.suffix.lower(),
                    file_size=stat.st_size,
                    file_mtime=int(stat.st_mtime),
                    is_primary=False,  # Will set primary after scoring
                    confidence_score=100  # Default, will be updated by matching
                )
                
                # Extract signals (with FLP reference for matching)
                flp_mtime = int(flp_path.stat().st_mtime) if flp_path and flp_path.exists() else None
                signals = extract_file_signals(
                    render,
                    project_flp_path=flp_path,
                    reference_mtime=flp_mtime
                )
                self.identity_store.write_signals(file_id, signals)
                
                # Compute match score for primary selection
                if flp_path:
                    score, reasons = self.adapter.compute_match_score(
                        render,
                        flp_path,
                        {'signals': signals, 'flp_mtime': flp_mtime}
                    )
                    # Update confidence score in project_files
                    execute(
                        "UPDATE project_files SET confidence_score = ? WHERE id = ?",
                        (score, file_id)
                    )
                    if score > primary_score:
                        primary_score = score
                        primary_render_id = file_id
            
            # Set primary render (transactional)
            if primary_render_id:
                self.identity_store.set_primary_render(project_id, primary_render_id)
            
            # 3. Catalog backups (evidence, not library items)
            if backup_dir.exists():
                try:
                    for backup_file in backup_dir.rglob('*'):
                        if backup_file.is_file() and backup_file.suffix.lower() == '.flp':
                            fingerprint = compute_fingerprint(backup_file)
                            if fingerprint:
                                stat = backup_file.stat()
                                self.identity_store.upsert_project_file(
                                    project_id=project_id,
                                    file_path=backup_file,
                                    fingerprint=fingerprint,
                                    file_role='backup',
                                    file_ext='.flp',
                                    file_size=stat.st_size,
                                    file_mtime=int(stat.st_mtime)
                                )
                except Exception as e:
                    logger.debug(f"Error cataloging backups: {e}")
            
            # 4. Catalog stems (if any)
            if stems_dir.exists():
                try:
                    for stem_file in stems_dir.rglob('*'):
                        if stem_file.is_file() and stem_file.suffix.lower() in {'.wav', '.mp3', '.flac'}:
                            fingerprint = compute_fingerprint(stem_file)
                            if fingerprint:
                                stat = stem_file.stat()
                                self.identity_store.upsert_project_file(
                                    project_id=project_id,
                                    file_path=stem_file,
                                    fingerprint=fingerprint,
                                    file_role='stem',
                                    file_ext=stem_file.suffix.lower(),
                                    file_size=stat.st_size,
                                    file_mtime=int(stat.st_mtime)
                                )
                except Exception as e:
                    logger.debug(f"Error cataloging stems: {e}")
            
            # 5. Update project confidence based on match quality
            if flp_path and renders:
                # For structured folders: 90-95
                # For flat: based on top match score
                has_fingerprint_match = any(
                    s.signal_type.value == 'previously_seen_fingerprint'
                    for render in renders
                    for s in extract_file_signals(render)
                )
                confidence = self.adapter.compute_flat_folder_confidence(primary_score, has_fingerprint_match)
                self.identity_store.update_project_confidence(project_id, confidence)
            
        except Exception as e:
            logger.warning(f"Error populating identity files for {proj_path.name}: {e}")
            # Don't fail scan on identity errors
    
    def _populate_identity_files_orphan(
        self,
        project_id: int,
        flp_path: Path,
        matched_audio: List[Path],
        root: Path
    ) -> None:
        """
        Populate identity system for orphan FLP (flat folder structure).
        Similar to _populate_identity_files but for orphan FLPs.
        """
        try:
            # 1. Catalog FLP file
            if flp_path.exists():
                fingerprint = compute_fingerprint(flp_path)
                if fingerprint:
                    stat = flp_path.stat()
                    file_id = self.identity_store.upsert_project_file(
                        project_id=project_id,
                        file_path=flp_path,
                        fingerprint=fingerprint,
                        file_role='flp',
                        file_ext='.flp',
                        file_size=stat.st_size,
                        file_mtime=int(stat.st_mtime),
                        is_primary=True
                    )
                    signals = extract_file_signals(flp_path)
                    self.identity_store.write_signals(file_id, signals)
            
            # 2. Catalog renders with confidence scores
            primary_render_id = None
            primary_score = 0
            
            flp_mtime = int(flp_path.stat().st_mtime) if flp_path.exists() else None
            
            for render in matched_audio:
                if not render.exists():
                    continue
                
                fingerprint = compute_fingerprint(render)
                if not fingerprint:
                    continue
                
                stat = render.stat()
                
                # Compute match score using adapter
                score, reasons = self.adapter.compute_match_score(
                    render,
                    flp_path,
                    {
                        'signals': extract_file_signals(
                            render,
                            project_flp_path=flp_path,
                            reference_mtime=flp_mtime
                        ),
                        'flp_mtime': flp_mtime
                    }
                )
                
                file_id = self.identity_store.upsert_project_file(
                    project_id=project_id,
                    file_path=render,
                    fingerprint=fingerprint,
                    file_role='render',
                    file_ext=render.suffix.lower(),
                    file_size=stat.st_size,
                    file_mtime=int(stat.st_mtime),
                    is_primary=False,
                    confidence_score=score
                )
                
                # Extract and write signals
                signals = extract_file_signals(
                    render,
                    project_flp_path=flp_path,
                    reference_mtime=flp_mtime
                )
                self.identity_store.write_signals(file_id, signals)
                
                # Track primary render
                if score > primary_score:
                    primary_score = score
                    primary_render_id = file_id
            
            # Set primary render (transactional)
            if primary_render_id:
                self.identity_store.set_primary_render(project_id, primary_render_id)
            
            # 3. Update project confidence
            has_fingerprint_match = any(
                s.signal_type.value == 'previously_seen_fingerprint'
                for render in matched_audio
                for s in extract_file_signals(render)
            )
            confidence = self.adapter.compute_flat_folder_confidence(primary_score, has_fingerprint_match)
            self.identity_store.update_project_confidence(project_id, confidence)
            
        except Exception as e:
            logger.warning(f"Error populating identity files for orphan FLP {flp_path.name}: {e}")
    
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
        
        # Use detected FLP paths (detector returns str; ensure Path for .exists() etc.)
        flp_path = Path(detection.primary_flp_path) if detection.primary_flp_path else None
        all_flp_paths = [Path(p) for p in detection.flp_paths]
        
        # 2. Find RENDERS (root-level audio only, excluding Audio/Samples/Backup)
        render_classifications = find_project_renders(proj_path)
        renders = [Path(c.path) for c in render_classifications if c.classification == 'RENDER']
        
        # Log render detection for debugging
        if renders:
            logger.debug(f"Found {len(renders)} renders for {proj_path.name}: {[str(r) for r in renders]}")
        else:
            logger.debug(f"No renders found for {proj_path.name} (classifications: {[c.classification for c in render_classifications]})")
        
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
        
        # Skip expensive folder size calculation by default (uses os.walk)
        folder_size_mb = self._get_folder_size_mb(proj_path, skip_expensive=self.skip_folder_size_calc)
        
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
        
        # Normalize path for DB operations
        normalized_path = normalize_path(str(proj_path))
        
        # Use cached schema info (eliminates repeated PRAGMA queries)
        has_primary_render_id = self._has_primary_render_id
        
        # Query existing project (include flp_parsed_at for FLP cache check)
        if has_primary_render_id:
            existing_row = query_one(
                "SELECT id, primary_render_id, flp_parsed_at FROM projects WHERE path = ?",
                (normalized_path,)
            )
            if existing_row:
                existing = dict(existing_row)  # Convert Row to dict
                existing_primary_render_id = existing.get('primary_render_id')
                existing_flp_parsed_at = existing.get('flp_parsed_at')
            else:
                existing = None
                existing_primary_render_id = None
                existing_flp_parsed_at = None
        else:
            existing_row = query_one(
                "SELECT id, flp_parsed_at FROM projects WHERE path = ?",
                (normalized_path,)
            )
            if existing_row:
                existing = dict(existing_row)  # Convert Row to dict
                existing_primary_render_id = None
                existing_flp_parsed_at = existing.get('flp_parsed_at')
            else:
                existing = None
                existing_primary_render_id = None
                existing_flp_parsed_at = None
        
        is_new = existing is None
        
        # Combine signals for storage
        full_signals = {"raw": signals_raw, "derived": signals_derived}
        signals_json = json.dumps(full_signals)
        
        # Phase 1: Robust Columns
        cols = {
            "path": normalized_path,
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
        
        # Get original file creation date for sorting (from FLP file or folder)
        project_file_created = now  # fallback
        if flp_path and flp_path.exists():
            project_file_created = get_file_created_at(flp_path)
        elif main_render:
            project_file_created = get_file_created_at(main_render)
        else:
            # Use project folder creation date as fallback
            project_file_created = get_file_created_at(proj_path)
        
        # Always include file_created_at in columns (will use COALESCE for updates)
        cols["file_created_at"] = project_file_created
        
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
            project_id = existing.get('id') if existing else None
            if not project_id:
                logger.error(f"Could not get project_id for {proj_path}")
                return None
            # Don't overwrite user_meta on scan!
            # Use COALESCE for file_created_at to not overwrite if already set
            
            # Build update clause - use COALESCE for file_created_at
            set_parts = []
            values_list = []
            for k, v in cols.items():
                if k == "file_created_at":
                    # Only update if NULL or 0
                    set_parts.append(f"{k} = COALESCE(NULLIF({k}, 0), ?)")
                else:
                    set_parts.append(f"{k} = ?")
                values_list.append(v)
            
            set_clause = ", ".join(set_parts)
            values = tuple(values_list)
            
            execute(
                f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?",
                values + (now, project_id)
            )
            
        # 6a. Populate Identity System (write-through mode)
        # Ensure project has PID
        pid = self.identity_store.ensure_project_pid(project_id)
        
        # Catalog all files in project_files table
        self._populate_identity_files(
            project_id=project_id,
            proj_path=proj_path,
            flp_path=flp_path,
            all_flp_paths=all_flp_paths,
            renders=renders,
            backup_dir=backup_dir,
            stems_dir=stems_dir,
            samples_dir=samples_dir
        )
        
        # 6b. Parse FLP Content (Plugins/Samples) if available
        # Use FLP mtime caching to skip re-parsing unchanged FLPs
        if flp_path and flp_path.exists():
            try:
                flp_mtime = int(flp_path.stat().st_mtime)
                
                # Check if FLP needs parsing (new project or FLP modified since last parse)
                needs_flp_parse = (
                    is_new or 
                    existing_flp_parsed_at is None or 
                    flp_mtime > existing_flp_parsed_at
                )
                
                if needs_flp_parse:
                    from ..flp_parser.parser import FLPParser
                    parser = FLPParser()
                    # Only parse if enabled (pyflp installed)
                    if parser.enabled:
                        flp_data = parser.parse(str(flp_path))
                        if flp_data:
                            self._save_flp_data(project_id, flp_data, now)
                else:
                    logger.debug(f"Skipping FLP parse (unchanged): {proj_path.name}")
            except Exception as e:
                logger.warning(f"FLP parsing failed for {proj_path.name}: {e}")
                # Don't fail the whole scan for this
            
        # 7. Handle RENDERS (new system)
        # Use cached schema info (eliminates repeated queries)
        has_renders_table = self._has_renders_table
        
        renders_added = 0
        renders_removed = 0
        existing_renders = {}
        found_render_paths = set()
        
        if has_renders_table:
            try:
                # Load existing renders with mtime and duration for smart caching
                # Normalize paths for comparison (Windows path case/separator issues)
                existing_renders = {}
                existing_render_data = {}  # path -> {id, mtime, duration}
                for row in query("SELECT id, path, mtime, duration_s FROM renders WHERE project_id = ?", (project_id,)):
                    # Normalize path for comparison (resolve to absolute, normalize separators)
                    db_path = row['path']
                    try:
                        # Normalize to absolute path for comparison
                        normalized_db_path = str(Path(db_path).resolve())
                        existing_renders[normalized_db_path] = row['id']
                        existing_renders[db_path] = row['id']  # Also keep original for compatibility
                        existing_render_data[normalized_db_path] = {
                            'id': row['id'],
                            'mtime': row['mtime'],
                            'duration': row['duration_s']
                        }
                        existing_render_data[db_path] = existing_render_data[normalized_db_path]
                    except:
                        # If path resolution fails, use original
                        existing_renders[db_path] = row['id']
                        existing_render_data[db_path] = {
                            'id': row['id'],
                            'mtime': row['mtime'],
                            'duration': row['duration_s']
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
        
        # Helper to get duration (with smart caching based on mtime)
        def get_duration_smart(path: Path, current_mtime: int) -> float:
            """
            Get duration with smart caching.
            If file mtime hasn't changed, reuse cached duration (skip Mutagen).
            Only compute duration with Mutagen for new/changed files.
            """
            path_str = str(path)
            
            # Check if we have cached data for this render
            if path_str in existing_render_data:
                cached = existing_render_data[path_str]
                cached_mtime = cached.get('mtime')
                cached_duration = cached.get('duration')
                
                # If mtime matches and we have a valid duration, reuse it
                if cached_mtime and cached_duration and cached_mtime == current_mtime:
                    return float(cached_duration)
            
            # File is new or changed - compute duration with Mutagen
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
                # Normalize path for consistent comparison
                try:
                    render_path_normalized = str(render_path.resolve())
                    render_path_str = render_path_normalized
                except:
                    render_path_str = str(render_path)
                found_render_paths.add(render_path_str)
                # Also add original path format for compatibility
                found_render_paths.add(str(render_path))
                
                # Get file stats once (avoid multiple stat() calls)
                stat = render_path.stat()
                current_mtime = int(stat.st_mtime)
                filename = render_path.name
                ext = render_path.suffix.lower()
                
                # Use smart duration caching - skip Mutagen for unchanged files
                duration = get_duration_smart(render_path, current_mtime)
                
                # Use main_render duration if available (pre-computed earlier)
                if render_path == main_render and render_duration > 0:
                    duration = render_duration
                
                # Compute fingerprint for storage
                fingerprint = compute_fingerprint(render_path)
                
                # Get original file creation date
                file_created_at = get_file_created_at(render_path)
                
                # Check both normalized and original path formats
                render_id = existing_renders.get(render_path_str) or existing_renders.get(str(render_path))
                
                if render_id:
                    # Update existing render
                    execute(
                        """UPDATE renders SET
                           mtime = ?, file_size = ?, duration_s = ?, fingerprint_fast = ?,
                           file_created_at = COALESCE(NULLIF(file_created_at, 0), ?), updated_at = ?
                           WHERE id = ?""",
                        (current_mtime, stat.st_size, duration, fingerprint, file_created_at, now, render_id)
                    )
                    render_ids.append(render_id)
                else:
                    # Insert new render
                    # Use normalized path for storage (consistent format)
                    try:
                        storage_path = str(render_path.resolve())
                    except:
                        storage_path = render_path_str
                    
                    # Check if render already exists globally (UNIQUE constraint on path)
                    existing_render_global = query_one(
                        "SELECT id, project_id FROM renders WHERE path = ? LIMIT 1",
                        (storage_path,)
                    )
                    
                    if existing_render_global:
                        # Render already exists - use existing ID
                        render_id = existing_render_global['id']
                        existing_project_id = existing_render_global['project_id']
                        
                        if existing_project_id == project_id:
                            # Belongs to this project - update it
                            execute(
                                """UPDATE renders SET
                                   mtime = ?, file_size = ?, duration_s = ?,
                                   fingerprint_fast = ?, file_created_at = COALESCE(NULLIF(file_created_at, 0), ?),
                                   updated_at = ?
                                   WHERE id = ?""",
                                (current_mtime, stat.st_size, duration, fingerprint, file_created_at, now, render_id)
                            )
                            render_ids.append(render_id)
                        else:
                            # Belongs to another project - skip (prevents duplicate renders)
                            logger.debug(f"Skipping render {storage_path} - already belongs to project {existing_project_id}")
                            continue
                    else:
                        # Insert new render
                        try:
                            cur = execute(
                                """INSERT INTO renders
                                   (project_id, path, filename, ext, file_size, mtime, duration_s, 
                                    fingerprint_fast, file_created_at, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    project_id, storage_path, filename, ext,
                                    stat.st_size, current_mtime, duration, fingerprint,
                                    file_created_at, now, now
                                )
                            )
                            render_id = cur.lastrowid
                            render_ids.append(render_id)
                            renders_added += 1
                            logger.debug(f"Added render for project {project_id}: {storage_path}")
                        except Exception as e:
                            # Handle UNIQUE constraint violation gracefully
                            if 'UNIQUE constraint failed' in str(e) and 'renders.path' in str(e):
                                logger.debug(f"Render {storage_path} already exists (race condition), skipping insert")
                                # Try to get the existing render ID
                                existing = query_one("SELECT id FROM renders WHERE path = ? LIMIT 1", (storage_path,))
                                if existing:
                                    render_id = existing['id']
                                    render_ids.append(render_id)
                                # Continue without adding to renders_added
                            else:
                                raise  # Re-raise if it's a different error
            
            # Prune removed renders (only delete if path truly not found)
            # Use a set of render_ids that were found to avoid deleting renders with path normalization issues
            found_render_ids = set()
            for render_path in renders:
                try:
                    render_path_normalized = str(render_path.resolve())
                    render_id = existing_renders.get(render_path_normalized) or existing_renders.get(str(render_path))
                    if render_id:
                        found_render_ids.add(render_id)
                except:
                    render_id = existing_renders.get(str(render_path))
                    if render_id:
                        found_render_ids.add(render_id)
            
            # Only delete renders that were truly not found (not just path format mismatch)
            for path_str, render_id in existing_renders.items():
                if render_id not in found_render_ids and path_str not in found_render_paths:
                    # Double-check: query if render still exists and file still exists
                    try:
                        render_row = query_one("SELECT path FROM renders WHERE id = ?", (render_id,))
                        if render_row:
                            render_file_path = Path(render_row['path'])
                            if not render_file_path.exists():
                                # File deleted, safe to remove from DB
                                execute("DELETE FROM renders WHERE id = ?", (render_id,))
                                renders_removed += 1
                            # If file exists but path doesn't match, don't delete (path normalization issue)
                    except Exception as e:
                        logger.debug(f"Could not check/delete render {render_id}: {e}")
        
        # 8. Determine primary render (bridge identity system to legacy renders table)
        primary_render_id = existing_primary_render_id if has_primary_render_id else None
        
        # Try to get primary render from identity system first
        if has_renders_table:
            try:
                identity_primary = self.identity_store.get_primary_render(project_id)
                if identity_primary:
                    # Find corresponding render_id in renders table by path
                    render_path = identity_primary.get('file_path')
                    if render_path:
                        render_row = query_one(
                            "SELECT id FROM renders WHERE project_id = ? AND path = ? LIMIT 1",
                            (project_id, render_path)
                        )
                        if render_row:
                            primary_render_id = render_row['id']
                            logger.debug(f"Using primary render from identity system: {render_path}")
            except Exception as e:
                logger.debug(f"Could not get primary render from identity system: {e}")
        
        # Fallback: If no primary from identity system, use latest render by mtime
        if has_renders_table and not primary_render_id and render_ids:
            try:
                # Get latest render by file creation date (should be the newest root-level render)
                latest_render_row = query_one(
                    "SELECT id FROM renders WHERE project_id = ? ORDER BY COALESCE(file_created_at, mtime) DESC LIMIT 1",
                    (project_id,)
                )
                if latest_render_row:
                    latest_render = dict(latest_render_row)  # Convert Row to dict
                    primary_render_id = latest_render.get('id')
                    logger.debug(f"Using latest render as primary (fallback)")
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
        
        # Mark primary render in renders table (bridge from identity system)
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
        
        # 9. Index ALL renders as tracks (full render support)
        # Create a track entry for EACH render, not just the primary
        # Uses render_id as stable identity for idempotency across rescans
        tracks_added = 0
        tracks_removed = 0
        added_ids = []
        
        if has_renders_table:
            try:
                # Get all renders for this project (including file_created_at)
                all_renders = query(
                    "SELECT id, path, filename, duration_s, mtime, file_size, ext, file_created_at FROM renders WHERE project_id = ?",
                    (project_id,)
                )
                
                # Get existing tracks keyed by render_id for efficient lookup
                existing_tracks_by_render = {}
                existing_tracks_by_path = {}
                for row in query("SELECT id, render_id, path FROM tracks WHERE project_id = ?", (project_id,)):
                    row_dict = dict(row)
                    if row_dict.get('render_id'):
                        existing_tracks_by_render[row_dict['render_id']] = row_dict['id']
                    if row_dict.get('path'):
                        existing_tracks_by_path[row_dict['path']] = row_dict['id']
                
                # Track which render_ids we've processed (for cleanup)
                processed_render_ids = set()
                
                for render_row in all_renders:
                    render = dict(render_row)  # Convert Row to dict
                    render_id = render['id']
                    render_path = render['path']
                    processed_render_ids.add(render_id)
                    
                    is_primary_render = (render_id == primary_render_id)
                    title = Path(render['filename']).stem if render.get('filename') else Path(render_path).stem
                    ext = render.get('ext') or Path(render_path).suffix.lower()
                    duration = render.get('duration_s') or 0
                    
                    # Get file_created_at from render (original file creation date)
                    render_file_created = render.get('file_created_at') or now
                    
                    # Try to get file stats (may not exist if file was deleted)
                    try:
                        stat = Path(render_path).stat()
                        file_size = stat.st_size
                        mtime = int(stat.st_mtime)
                        # Update file_created_at if we can get it from the file
                        render_file_created = get_file_created_at(Path(render_path))
                    except:
                        file_size = render['file_size'] or 0
                        mtime = render['mtime'] or now
                    
                    # Check if track already exists for this render
                    existing_track_id = existing_tracks_by_render.get(render_id)
                    
                    if existing_track_id:
                        # Update existing track
                        # Use COALESCE(NULLIF(..., 0), ?) to update if NULL or 0
                        execute(
                            """UPDATE tracks SET
                               title = ?, path = ?, ext = ?, file_size = ?, mtime = ?,
                               duration = ?, is_primary = ?, state = ?, state_reason = ?,
                               file_created_at = COALESCE(NULLIF(file_created_at, 0), ?), updated_at = ?
                               WHERE id = ?""",
                            (
                                title, render_path, ext, file_size, mtime,
                                duration, 1 if is_primary_render else 0,
                                classification.state_id,
                                "; ".join(classification.state_reasons),
                                render_file_created, now, existing_track_id
                            )
                        )
                    else:
                        # Check if track exists by path (legacy migration)
                        legacy_track_id = existing_tracks_by_path.get(render_path)
                        
                        if legacy_track_id:
                            # Update legacy track to link with render
                            # Use COALESCE(NULLIF(..., 0), ?) to update if NULL or 0
                            execute(
                                """UPDATE tracks SET
                                   render_id = ?, is_primary = ?, title = ?,
                                   state = ?, state_reason = ?, 
                                   file_created_at = COALESCE(NULLIF(file_created_at, 0), ?), updated_at = ?
                                   WHERE id = ?""",
                                (
                                    render_id, 1 if is_primary_render else 0, title,
                                    classification.state_id,
                                    "; ".join(classification.state_reasons),
                                    render_file_created, now, legacy_track_id
                                )
                            )
                        else:
                            # Insert new track
                            cur = execute(
                                """INSERT INTO tracks
                                   (project_id, render_id, title, path, ext, file_size, mtime,
                                    state, state_reason, duration, is_primary, 
                                    file_created_at, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    project_id, render_id, title, render_path, ext,
                                    file_size, mtime,
                                    classification.state_id,
                                    "; ".join(classification.state_reasons),
                                    duration, 1 if is_primary_render else 0,
                                    render_file_created, now, now
                                )
                            )
                            if cur and cur.lastrowid:
                                added_ids.append(cur.lastrowid)
                                tracks_added += 1
                
                # Clean up orphaned tracks (renders that no longer exist)
                orphan_tracks = query(
                    """SELECT id FROM tracks 
                       WHERE project_id = ? AND render_id IS NOT NULL 
                       AND render_id NOT IN (SELECT id FROM renders WHERE project_id = ?)""",
                    (project_id, project_id)
                )
                for orphan in orphan_tracks:
                    execute("DELETE FROM tracks WHERE id = ?", (orphan['id'],))
                    tracks_removed += 1
                    
            except Exception as e:
                logger.warning(f"Error indexing tracks for {proj_path.name}: {e}")
                # Fallback to old behavior if new columns don't exist
                if primary_render_id:
                    primary_render_row = query_one("SELECT path, duration_s FROM renders WHERE id = ?", (primary_render_id,))
                    if primary_render_row:
                        primary_render = dict(primary_render_row)  # Convert Row to dict
                        primary_path = primary_render.get('path')
                        primary_duration = primary_render.get('duration_s') or 0
                        
                        existing_tracks = {
                            dict(row).get('path'): dict(row).get('id')
                            for row in query("SELECT id, path FROM tracks WHERE project_id = ?", (project_id,))
                            if dict(row).get('path')
                        }
                        
                        if primary_path not in existing_tracks:
                            title = Path(primary_path).stem
                            ext = Path(primary_path).suffix.lower()
                            try:
                                stat = Path(primary_path).stat()
                                cur = execute(
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
                                if cur and cur.lastrowid:
                                    added_ids.append(cur.lastrowid)
                                    tracks_added += 1
                            except:
                                pass
        
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

        # Update project date from renders (so newest render bubbles project up in sorted lists)
        if renders_added > 0:
            update_project_date_from_renders(project_id)

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
    
    def _scan_orphan_flps_in_root(self, root: Path) -> Optional[Dict]:
        """
        Scan for orphan FLPs directly in a library root.
        
        Orphan FLPs are FLP files that exist directly in the library root (not in a project folder).
        This handles old FL Studio workflows where FLPs and audio are in the same folder.
        
        Uses smart name matching to associate audio files with FLPs.
        """
        result = {
            'projects_added': 0,
            'tracks_added': 0,
            'renders_added': 0,
            'added_ids': []
        }
        
        try:
            # Find orphan FLPs (FLPs directly in root, not in subdirs)
            orphan_flps = []
            audio_files = []
            
            for item in root.iterdir():
                if not item.is_file():
                    continue
                    
                ext = item.suffix.lower()
                if ext == '.flp':
                    # Check if this FLP is NOT already part of a detected project folder
                    # (i.e., it's truly orphan, not in a proper project structure)
                    orphan_flps.append(item)
                elif ext in RENDER_EXTENSIONS:
                    audio_files.append(item)
            
            if not orphan_flps:
                return result
            
            logger.debug(f"Found {len(orphan_flps)} orphan FLPs in {root}")
            
            # Use adapter for signal-based matching (upgraded from simple name matching)
            # Group FLPs by processing them individually with adapter matching
            assignments: Dict[Path, List[Path]] = {}
            matched_audio_set: Set[Path] = set()  # Track which audio files have been assigned
            
            for flp_path in orphan_flps:
                # Use adapter to match audio files to this FLP
                match_results = self.adapter.match_files_to_project(
                    project_files=[flp_path],
                    candidate_files=audio_files,
                    project_root=root
                )
                
                # Filter out already-assigned audio files (conflict prevention)
                available_matches = [
                    m for m in match_results
                    if m.file_path not in matched_audio_set
                ]
                
                # Sort by confidence score descending
                available_matches.sort(key=lambda m: m.confidence_score, reverse=True)
                
                # Assign matched audio files to this FLP
                matched_for_flp = []
                for match in available_matches:
                    if match.confidence_score >= self.adapter.MIN_THRESHOLD:
                        matched_for_flp.append(match.file_path)
                        matched_audio_set.add(match.file_path)
                        logger.debug(
                            f"Matched {match.file_path.name} to {flp_path.name} "
                            f"(score: {match.confidence_score}, reasons: {', '.join(match.match_reasons)})"
                        )
                
                if matched_for_flp:
                    assignments[flp_path] = matched_for_flp
            
            now = int(time.time())
            
            for flp_path, matched_audio in assignments.items():
                if self.is_cancelled():
                    break
                
                try:
                    # Create or update project for this orphan FLP
                    # Use FLP path as stable unique identifier
                    flp_path_str = str(flp_path)
                    normalized_flp_path = normalize_path(flp_path_str)
                    project_name = flp_path.stem
                    
                    # For orphan FLPs, use FLP path as the project path to ensure uniqueness
                    # (since multiple FLPs can be in the same root folder)
                    orphan_project_path = normalized_flp_path
                    
                    # Check if project already exists for this FLP (by flp_path or path)
                    # Note: We use normalized paths for lookup to avoid duplicates
                    existing_row = query_one(
                        "SELECT id FROM projects WHERE path = ?",
                        (orphan_project_path,)
                    )
                    
                    # Get FLP file creation date
                    flp_file_created = get_file_created_at(flp_path)
                    
                    if existing_row:
                        existing = dict(existing_row)  # Convert Row to dict
                        project_id = existing.get('id')
                        if not project_id:
                            continue  # Skip if no ID
                        is_new = False
                        
                        # Update existing project (don't overwrite file_created_at)
                        execute(
                            """UPDATE projects SET
                               name = ?, last_scan = ?, updated_at = ?,
                               file_created_at = COALESCE(NULLIF(file_created_at, 0), ?)
                               WHERE id = ?""",
                            (project_name, now, now, flp_file_created, project_id)
                        )
                    else:
                        # Create new project using FLP path as unique project path
                        cur = execute(
                            """INSERT OR IGNORE INTO projects 
                               (path, name, flp_path, last_scan, state_id, file_created_at, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (orphan_project_path, project_name, flp_path_str, now, 'ORPHAN_FLP', flp_file_created, now, now)
                        )
                        if cur and cur.lastrowid:
                            project_id = cur.lastrowid
                            is_new = True
                            result['projects_added'] += 1
                        else:
                            # INSERT OR IGNORE didn't insert (already exists), find existing
                            existing_row2 = query_one("SELECT id FROM projects WHERE path = ?", (orphan_project_path,))
                            if existing_row2:
                                existing2 = dict(existing_row2)  # Convert Row to dict
                                project_id = existing2.get('id')
                                if project_id:
                                    is_new = False
                                else:
                                    continue  # Skip this FLP if we can't get the project ID
                            else:
                                continue  # Skip this FLP if we can't get the project ID
                    
                    # Use cached schema info (eliminates repeated queries)
                    if not self._has_renders_table:
                        continue
                    
                    # Get existing renders for this project
                    existing_renders = {}
                    for row in query("SELECT id, path FROM renders WHERE project_id = ?", (project_id,)):
                        row_dict = dict(row)
                        if row_dict.get('path'):
                            existing_renders[row_dict['path']] = row_dict.get('id')
                    
                    # Ensure project has PID
                    pid = self.identity_store.ensure_project_pid(project_id)
                    
                    # Populate identity system for orphan FLP
                    self._populate_identity_files_orphan(
                        project_id=project_id,
                        flp_path=flp_path,
                        matched_audio=matched_audio,
                        root=root
                    )
                    
                    # Process matched audio files as renders
                    primary_render_id = None
                    highest_score = 0
                    latest_mtime = 0
                    
                    for audio_path in matched_audio:
                        audio_path_str = str(audio_path)
                        
                        try:
                            stat = audio_path.stat()
                            file_size = stat.st_size
                            mtime = int(stat.st_mtime)
                        except:
                            continue
                        
                        # Get original file creation date
                        audio_file_created = get_file_created_at(audio_path)
                        
                        # Get duration if possible
                        duration = 0
                        if HAS_MUTAGEN:
                            try:
                                f = MutagenFile(audio_path)
                                if f and f.info:
                                    duration = f.info.length
                            except:
                                pass
                        
                        # Compute fingerprint
                        fingerprint = f"{file_size}:{mtime}"
                        
                        # Check if render already exists (globally, not just for this project)
                        # This handles the case where the same audio file is matched to multiple FLPs
                        existing_render_global = query_one(
                            "SELECT id, project_id FROM renders WHERE path = ? LIMIT 1",
                            (audio_path_str,)
                        )
                        
                        if existing_render_global:
                            # Render already exists (possibly from another project/FLP)
                            render_id = existing_render_global['id']
                            existing_project_id = existing_render_global['project_id']
                            
                            # Only update if it belongs to this project
                            if existing_project_id == project_id:
                                execute(
                                    """UPDATE renders SET
                                       mtime = ?, file_size = ?, duration_s = ?,
                                       fingerprint_fast = ?, file_created_at = COALESCE(NULLIF(file_created_at, 0), ?),
                                       updated_at = ?
                                       WHERE id = ?""",
                                    (mtime, file_size, duration, fingerprint, audio_file_created, now, render_id)
                                )
                            else:
                                # Render belongs to another project - skip it
                                # This prevents duplicate renders when same audio matches multiple FLPs
                                logger.debug(f"Skipping render {audio_path_str} - already belongs to project {existing_project_id}")
                                continue
                        elif audio_path_str in existing_renders:
                            # Update existing render for this project
                            render_id = existing_renders[audio_path_str]
                            execute(
                                """UPDATE renders SET
                                   mtime = ?, file_size = ?, duration_s = ?,
                                   fingerprint_fast = ?, file_created_at = COALESCE(NULLIF(file_created_at, 0), ?),
                                   updated_at = ?
                                   WHERE id = ?""",
                                (mtime, file_size, duration, fingerprint, audio_file_created, now, render_id)
                            )
                        else:
                            # Insert new render (with INSERT OR IGNORE to handle race conditions)
                            try:
                                cur = execute(
                                    """INSERT INTO renders
                                       (project_id, path, filename, ext, file_size, mtime, 
                                        duration_s, fingerprint_fast, file_created_at, created_at, updated_at)
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                    (
                                        project_id, audio_path_str, audio_path.name,
                                        audio_path.suffix.lower(), file_size, mtime,
                                        duration, fingerprint, audio_file_created, now, now
                                    )
                                )
                                render_id = cur.lastrowid
                                result['renders_added'] += 1
                            except Exception as e:
                                # Handle UNIQUE constraint violation gracefully
                                if 'UNIQUE constraint failed' in str(e) and 'renders.path' in str(e):
                                    logger.debug(f"Render {audio_path_str} already exists, skipping insert")
                                    # Try to get the existing render ID
                                    existing = query_one("SELECT id FROM renders WHERE path = ? LIMIT 1", (audio_path_str,))
                                    if existing:
                                        render_id = existing['id']
                                    else:
                                        continue  # Skip if we can't find it
                                else:
                                    raise  # Re-raise if it's a different error
                        
                        # Track highest confidence score for primary selection
                        # Get confidence from identity system if available
                        try:
                            fingerprint = compute_fingerprint(audio_path)
                            if fingerprint:
                                identity_file = self.identity_store.find_file_by_fingerprint(
                                    fingerprint,
                                    project_id
                                )
                                confidence = identity_file.get('confidence_score', 100) if identity_file else 100
                                
                                # Use confidence score, tie-breaker by mtime
                                if confidence > highest_score or (confidence == highest_score and mtime > latest_mtime):
                                    highest_score = confidence
                                    primary_render_id = render_id
                                    latest_mtime = mtime
                        except Exception as e:
                            logger.debug(f"Error getting confidence for primary selection: {e}")
                            # Fallback to mtime-based selection
                            if mtime > latest_mtime:
                                latest_mtime = mtime
                                primary_render_id = render_id
                    
                    # Set primary render
                    if primary_render_id:
                        execute(
                            "UPDATE projects SET primary_render_id = ? WHERE id = ?",
                            (primary_render_id, project_id)
                        )
                        execute(
                            "UPDATE renders SET is_primary = 1 WHERE id = ?",
                            (primary_render_id,)
                        )
                        execute(
                            "UPDATE renders SET is_primary = 0 WHERE project_id = ? AND id != ?",
                            (project_id, primary_render_id)
                        )
                    
                    # Index tracks for all renders (same as in _scan_project)
                    all_renders = query(
                        "SELECT id, path, filename, duration_s, mtime, file_size, ext, file_created_at FROM renders WHERE project_id = ?",
                        (project_id,)
                    )
                    
                    existing_tracks = {
                        dict(row)['render_id']: dict(row)['id']
                        for row in query("SELECT id, render_id FROM tracks WHERE project_id = ? AND render_id IS NOT NULL", (project_id,))
                    }
                    
                    for render_row in all_renders:
                        render = dict(render_row)  # Convert Row to dict
                        render_id = render['id']
                        is_primary = (render_id == primary_render_id)
                        title = Path(render.get('filename', 'Unknown')).stem if render.get('filename') else 'Unknown'
                        render_file_created = render.get('file_created_at') or now
                        
                        if render_id in existing_tracks:
                            # Update existing track
                            execute(
                                """UPDATE tracks SET
                                   title = ?, is_primary = ?,
                                   file_created_at = COALESCE(NULLIF(file_created_at, 0), ?), updated_at = ?
                                   WHERE id = ?""",
                                (title, 1 if is_primary else 0, render_file_created, now, existing_tracks[render_id])
                            )
                        else:
                            # Insert new track
                            cur = execute(
                                """INSERT INTO tracks
                                   (project_id, render_id, title, path, ext, file_size, mtime,
                                    duration, is_primary, state, file_created_at, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    project_id, render_id, title, render.get('path'),
                                    render.get('ext'), render.get('file_size'), render.get('mtime'),
                                    render.get('duration_s'), 1 if is_primary else 0,
                                    'ORPHAN_FLP', render_file_created, now, now
                                )
                            )
                            if cur and cur.lastrowid:
                                result['added_ids'].append(cur.lastrowid)
                                result['tracks_added'] += 1
                    
                    # Update project date from renders (so newest render bubbles project up in sorted lists)
                    if result['renders_added'] > 0:
                        update_project_date_from_renders(project_id)
                    
                except Exception as e:
                    logger.warning(f"Error processing orphan FLP {flp_path}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scanning orphan FLPs in {root}: {e}")
        
        return result
    
    def reconcile_identity_with_legacy_tables(self, project_id: Optional[int] = None) -> int:
        """
        Reconcile identity system with legacy renders/tracks tables.
        Ensures primary render is consistent across both systems.
        
        Args:
            project_id: Optional project ID to reconcile. If None, reconciles all projects.
            
        Returns:
            Number of projects reconciled
        """
        reconciled = 0
        
        try:
            if project_id:
                project_ids = [project_id]
            else:
                # Get all projects that have identity data
                rows = query("SELECT DISTINCT project_id FROM project_files")
                project_ids = [row['project_id'] for row in rows]
            
            for pid in project_ids:
                try:
                    # Get primary render from identity system
                    identity_primary = self.identity_store.get_primary_render(pid)
                    
                    if not identity_primary:
                        continue
                    
                    render_path = identity_primary.get('file_path')
                    if not render_path:
                        continue
                    
                    # Find corresponding render in renders table
                    render_row = query_one(
                        "SELECT id FROM renders WHERE project_id = ? AND path = ? LIMIT 1",
                        (pid, render_path)
                    )
                    
                    if render_row:
                        render_id = render_row['id']
                        
                        # Update projects.primary_render_id
                        execute(
                            "UPDATE projects SET primary_render_id = ? WHERE id = ?",
                            (render_id, pid)
                        )
                        
                        # Update renders.is_primary
                        execute(
                            "UPDATE renders SET is_primary = 1 WHERE id = ?",
                            (render_id,)
                        )
                        execute(
                            "UPDATE renders SET is_primary = 0 WHERE project_id = ? AND id != ?",
                            (pid, render_id)
                        )
                        
                        reconciled += 1
                        logger.debug(f"Reconciled primary render for project {pid}")
                        
                except Exception as e:
                    logger.warning(f"Error reconciling project {pid}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in reconcile_identity_with_legacy_tables: {e}")
        
        return reconciled
    
    def incremental_scan(self, parallel_workers: int = 1):
        """
        Perform incremental scan (only projects modified since last scan).
        This is much faster than a full scan as unchanged projects are skipped.
        
        Args:
            parallel_workers: Number of parallel workers (default 1, recommended 4 for speed)
        """
        self.scan_all(force_full_scan=False, parallel_workers=parallel_workers)
    
    def full_scan(self, parallel_workers: int = 1):
        """
        Perform full scan of all projects regardless of modification time.
        Use this when you want to re-index everything.
        
        Args:
            parallel_workers: Number of parallel workers (default 1, recommended 4 for speed)
        """
        self.scan_all(force_full_scan=True, parallel_workers=parallel_workers)
    
    def fast_scan(self):
        """
        Perform fast incremental scan with parallel processing enabled.
        This is the recommended scan mode for regular use.
        """
        # Use 4 workers by default for good balance of speed and resource usage
        self.scan_all(force_full_scan=False, parallel_workers=4)


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
    # Always check renders table directly (more reliable than cache)
    try:
        test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
        has_renders_table = test_row is not None
    except:
        has_renders_table = False
    
    if has_renders_table:
        # Check if primary_render_id column exists
        try:
            test_col = query_one("SELECT primary_render_id FROM projects LIMIT 1")
            has_primary_render_id = True
        except:
            has_primary_render_id = False
        
        if has_primary_render_id:
            project = query_one(
                """SELECT p.*, 
                   COALESCE((SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id), 0) as render_count,
                   r.path as render_path, r.filename as render_filename, 
                   r.duration_s as render_duration, r.mtime as render_mtime
                   FROM projects p
                   LEFT JOIN renders r ON p.primary_render_id = r.id
                   WHERE p.id = ?""",
                (project_id,)
            )
        else:
            project = query_one(
                """SELECT p.*, 
                   COALESCE((SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id), 0) as render_count,
                   NULL as render_path, NULL as render_filename,
                   NULL as render_duration, NULL as render_mtime
                   FROM projects p
                   WHERE p.id = ?""",
                (project_id,)
            )
    else:
        # Fallback: use tracks table
        project = query_one(
            """SELECT p.*, 
               COALESCE((SELECT COUNT(*) FROM tracks t WHERE t.project_id = p.id AND t.ext != '.flp'), 0) as render_count,
               NULL as render_path, NULL as render_filename,
               NULL as render_duration, NULL as render_mtime
               FROM projects p
               WHERE p.id = ?""",
            (project_id,)
        )
    return dict(project) if project else None


def refresh_project_render_count(project_id: int) -> Optional[Dict]:
    """
    Refresh render_count for a single project.
    Useful after scanning to update UI with accurate render data.
    """
    return get_project_with_renders(project_id)


def debug_project_renders(project_id: int) -> Dict:
    """
    Debug function to check render data for a project.
    Returns detailed information about renders and tracks.
    """
    result = {
        'project_id': project_id,
        'renders_table_exists': False,
        'renders_count': 0,
        'renders': [],
        'tracks_count': 0,
        'tracks': [],
    }
    
    # Check if renders table exists
    try:
        test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
        result['renders_table_exists'] = test_row is not None
    except:
        pass
    
    if result['renders_table_exists']:
        # Get renders
        renders = query("SELECT * FROM renders WHERE project_id = ?", (project_id,))
        result['renders'] = [dict(r) for r in renders]
        result['renders_count'] = len(renders)
    
    # Get tracks
    tracks = query("SELECT * FROM tracks WHERE project_id = ? AND ext != '.flp'", (project_id,))
    result['tracks'] = [dict(t) for t in tracks]
    result['tracks_count'] = len(tracks)
    
    # Get project info
    project = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if project:
        result['project'] = dict(project)
    
    return result


def _has_project_file_created_at() -> bool:
    """Check if projects table has file_created_at column (uses cache)."""
    return _get_cached_file_created_at_projects()

def get_all_projects(limit: int = 1000, offset: int = 0) -> List[Dict]:
    """Get all projects with classification info, sorted by original file creation date."""
    # Always check renders table directly (more reliable than cache for UI queries)
    try:
        test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
        has_renders_table = test_row is not None
    except:
        has_renders_table = False
    
    has_file_created = _has_project_file_created_at()
    order_col = "COALESCE(file_created_at, created_at)" if has_file_created else "created_at"
    
    if has_renders_table:
        # Check if primary_render_id column exists
        try:
            test_col = query_one("SELECT primary_render_id FROM projects LIMIT 1")
            has_primary_render_id = True
        except:
            has_primary_render_id = False
        
        if has_primary_render_id:
            # Include render_count, primary render info, and identity system fields
            rows = query(
                f"""SELECT p.*, 
                           COALESCE((SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id), 0) as render_count,
                           r.path as render_path, r.filename as render_filename,
                           r.duration_s as render_duration, r.mtime as render_mtime,
                           COALESCE(p.confidence_score, 100) as confidence_score,
                           COALESCE(p.user_locked, 0) as user_locked
                    FROM projects p
                    LEFT JOIN renders r ON p.primary_render_id = r.id
                    ORDER BY {order_col} DESC
                    LIMIT ? OFFSET ?""",
                (limit, offset)
            )
        else:
            # Include render_count without primary render join, but with identity fields
            rows = query(
                f"""SELECT p.*, 
                           COALESCE((SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id), 0) as render_count,
                           NULL as render_path, NULL as render_filename,
                           NULL as render_duration, NULL as render_mtime,
                           COALESCE(p.confidence_score, 100) as confidence_score,
                           COALESCE(p.user_locked, 0) as user_locked
                    FROM projects p
                    ORDER BY {order_col} DESC
                    LIMIT ? OFFSET ?""",
                (limit, offset)
            )
    else:
        # Fallback: use tracks table for render count (legacy behavior)
        rows = query(
            f"""SELECT p.*, 
                       COALESCE((SELECT COUNT(*) FROM tracks t WHERE t.project_id = p.id AND t.ext != '.flp'), 0) as render_count,
                       NULL as render_path, NULL as render_filename,
                       NULL as render_duration, NULL as render_mtime,
                       COALESCE(p.confidence_score, 100) as confidence_score,
                       COALESCE(p.user_locked, 0) as user_locked
                FROM projects p
                ORDER BY {order_col} DESC
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
        
    # Always check renders table directly (more reliable than cache for UI queries)
    # Cache might be stale when UI queries after scanning
    try:
        test_row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
        has_renders_table = test_row is not None
    except:
        has_renders_table = False
    
    has_file_created = _has_project_file_created_at()
    order_col = "COALESCE(p.file_created_at, p.created_at)" if has_file_created else "p.created_at"
    
    if has_renders_table:
        # Check if primary_render_id column exists
        try:
            test_col = query_one("SELECT primary_render_id FROM projects LIMIT 1")
            has_primary_render_id = True
        except:
            has_primary_render_id = False
        
        if has_primary_render_id:
            # Use renders table with primary_render_id join
            rows = query(
                f"""SELECT p.*, 
                           COALESCE((SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id), 0) as render_count,
                           r.path as render_path, r.filename as render_filename,
                           r.duration_s as render_duration, r.mtime as render_mtime,
                           COALESCE(p.confidence_score, 100) as confidence_score,
                           COALESCE(p.user_locked, 0) as user_locked
                    FROM projects p 
                    LEFT JOIN renders r ON p.primary_render_id = r.id
                   {where_clause}
                   ORDER BY {order_col} DESC
                   LIMIT ? OFFSET ?""",
                tuple(params) + (limit, offset)
            )
        else:
            # Use renders table without primary_render_id join
            rows = query(
                f"""SELECT p.*, 
                           COALESCE((SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id), 0) as render_count,
                           NULL as render_path, NULL as render_filename,
                           NULL as render_duration, NULL as render_mtime,
                           COALESCE(p.confidence_score, 100) as confidence_score,
                           COALESCE(p.user_locked, 0) as user_locked
                    FROM projects p 
                   {where_clause}
                   ORDER BY {order_col} DESC
                   LIMIT ? OFFSET ?""",
                tuple(params) + (limit, offset)
            )
    else:
        # Fallback: use tracks table for render count (legacy behavior)
        rows = query(
            f"""SELECT p.*, 
                       COALESCE((SELECT COUNT(*) FROM tracks t WHERE t.project_id = p.id AND t.ext != '.flp'), 0) as render_count,
                       NULL as render_path, NULL as render_filename,
                       NULL as render_duration, NULL as render_mtime,
                       COALESCE(p.confidence_score, 100) as confidence_score,
                       COALESCE(p.user_locked, 0) as user_locked
                FROM projects p 
               {where_clause}
               ORDER BY {order_col} DESC
               LIMIT ? OFFSET ?""",
            tuple(params) + (limit, offset)
        )
    
    # Ensure render_count is always present and an integer
    result = []
    for row in rows:
        project_dict = dict(row)
        # Ensure render_count is always an integer
        render_count = project_dict.get('render_count')
        if render_count is None:
            # If missing, query directly (shouldn't happen, but safety check)
            project_id = project_dict.get('id')
            if project_id and has_renders_table:
                try:
                    count_row = query_one(
                        "SELECT COUNT(*) as cnt FROM renders WHERE project_id = ?",
                        (project_id,)
                    )
                    render_count = count_row['cnt'] if count_row else 0
                except:
                    render_count = 0
            else:
                render_count = 0
        else:
            try:
                render_count = int(render_count)
            except (ValueError, TypeError):
                render_count = 0
        project_dict['render_count'] = render_count
        result.append(project_dict)
    
    return result

def _has_state_columns() -> bool:
    """Check if tracks table has state classification columns (uses cache)."""
    return _get_cached_state_columns_exist()

def _get_state_columns_sql() -> str:
    """Get SQL fragment for state columns, handling missing columns gracefully."""
    if _has_state_columns():
        return "t.state, t.state_reason, t.labels,"
    else:
        return "NULL as state, NULL as state_reason, NULL as labels,"

def get_all_tracks(limit: int = 500, offset: int = 0) -> List[Dict]:
    """Get all tracks with project info, sorted by original file creation date."""
    state_cols = _get_state_columns_sql()
    
    # Use file_created_at if available, otherwise fall back to created_at
    has_file_created = _has_file_created_at_column()
    order_col = "COALESCE(t.file_created_at, t.created_at)" if has_file_created else "t.created_at"
    
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
           ORDER BY {order_col} DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    return [dict(row) for row in rows]


def _has_file_created_at_column() -> bool:
    """Check if tracks table has file_created_at column (uses cache)."""
    return _get_cached_file_created_at_tracks()

def get_unified_tracks(limit: int = 500, offset: int = 0) -> List[Dict]:
    """
    Get unified tracks view - one track per project (most recent by file creation date).
    This reduces redundancy in the library while keeping everything accessible.
    """
    state_cols = _get_state_columns_sql()
    
    # Use file_created_at if available, otherwise fall back to created_at
    has_file_created = _has_file_created_at_column()
    order_col = "COALESCE(t.file_created_at, t.created_at)" if has_file_created else "t.created_at"
    order_col_t3 = "COALESCE(t3.file_created_at, t3.created_at)" if has_file_created else "t3.created_at"
    
    rows = query(
        f"""SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path,
           p.audio_dir, p.samples_dir, p.stems_dir, p.backup_dir,
           p.score, p.next_action_id, p.state_id,
           {state_cols}
           (SELECT GROUP_CONCAT(tg.name, ', ') 
            FROM track_tags tt 
            JOIN tags tg ON tt.tag_id = tg.id 
            WHERE tt.track_id = t.id) as genre,
           (SELECT COUNT(*) FROM tracks t2 WHERE t2.project_id = t.project_id AND t2.ext != '.flp') as total_renders
           FROM tracks t
           JOIN projects p ON t.project_id = p.id
           WHERE t.ext != '.flp'
           AND t.id = (
               SELECT t3.id FROM tracks t3
               WHERE t3.project_id = t.project_id AND t3.ext != '.flp'
               ORDER BY {order_col_t3} DESC
               LIMIT 1
           )
           ORDER BY {order_col} DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    return [dict(row) for row in rows]


def get_favorite_tracks(limit: int = 500) -> List[Dict]:
    """Get favorite tracks, sorted by original file creation date."""
    state_cols = _get_state_columns_sql()
    
    # Use file_created_at if available, otherwise fall back to created_at
    has_file_created = _has_file_created_at_column()
    order_col = "COALESCE(t.file_created_at, t.created_at)" if has_file_created else "t.created_at"
    
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
           ORDER BY {order_col} DESC
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
    
    # Use file_created_at if available, otherwise fall back to created_at
    has_file_created = _has_file_created_at_column()
    order_col = "COALESCE(t.file_created_at, t.created_at)" if has_file_created else "t.created_at"
    
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
            ORDER BY {order_col} DESC
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
    """Get all renders for a project, sorted by newest first (file creation date)."""
    # Use cached schema info (eliminates repeated queries)
    if not _get_cached_renders_table_exists():
        return []
    
    try:
        # Order by file_created_at (Windows "Date created") with mtime fallback
        rows = query(
            """SELECT * FROM renders 
               WHERE project_id = ? 
               ORDER BY COALESCE(file_created_at, mtime) DESC""",
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
    
    # Fallback to latest if no primary set (use file creation date)
    row = query_one(
        """SELECT * FROM renders 
           WHERE project_id = ? 
           ORDER BY COALESCE(file_created_at, mtime) DESC 
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


def update_project_date_from_renders(project_id: int):
    """
    Update project's file_created_at to the maximum render creation date.
    
    This ensures that when new renders are added, the project's "date" reflects 
    the newest content, so it appears at the top of newest-first sorted lists.
    
    Only increases the date (never makes a project appear "older").
    """
    if not _get_cached_renders_table_exists():
        return
    
    try:
        # Get max file_created_at from renders for this project
        max_row = query_one(
            "SELECT MAX(file_created_at) as max_created FROM renders WHERE project_id = ?",
            (project_id,)
        )
        
        if not max_row or max_row['max_created'] is None:
            return  # No renders or no file_created_at data
        
        max_created = max_row['max_created']
        
        # Update project only if the new date is larger (never make older)
        execute(
            """UPDATE projects 
               SET file_created_at = ?, updated_at = strftime('%s', 'now')
               WHERE id = ? 
                 AND (file_created_at IS NULL OR file_created_at < ?)""",
            (max_created, project_id, max_created)
        )
        
    except Exception as e:
        logger.debug(f"Failed to update project date from renders for project {project_id}: {e}")


def sync_tracks_from_renders() -> int:
    """
    Ensure every render has a corresponding track so the Library view shows all renders.
    
    Creates track rows for renders that don't have one (by render_id or path).
    Returns the number of tracks added or updated.
    """
    if not _get_cached_renders_table_exists():
        return 0
    
    try:
        # Check if tracks has render_id column
        cols = [row['name'] for row in query("PRAGMA table_info(tracks)")]
        has_render_id = 'render_id' in cols
        has_state = 'state' in cols
        has_file_created_at = 'file_created_at' in cols
        
        # Renders that have no track linked by render_id or by path
        if has_render_id:
            missing = query("""
                SELECT r.id as render_id, r.project_id, r.path, r.filename, r.ext,
                       r.file_size, r.mtime, r.duration_s, r.file_created_at, r.is_primary,
                       p.state_id
                FROM renders r
                JOIN projects p ON p.id = r.project_id
                WHERE NOT EXISTS (SELECT 1 FROM tracks t WHERE t.render_id = r.id)
                  AND NOT EXISTS (SELECT 1 FROM tracks t WHERE t.path = r.path)
            """)
        else:
            missing = query("""
                SELECT r.id as render_id, r.project_id, r.path, r.filename, r.ext,
                       r.file_size, r.mtime, r.duration_s, r.file_created_at, r.is_primary,
                       p.state_id
                FROM renders r
                JOIN projects p ON p.id = r.project_id
                WHERE NOT EXISTS (SELECT 1 FROM tracks t WHERE t.path = r.path)
            """)
        
        now = int(datetime.now().timestamp()) if hasattr(datetime, 'now') else 0
        if not now:
            import time
            now = int(time.time())
        
        added = 0
        for row in missing:
            r = dict(row)
            title = Path(r['filename']).stem if r.get('filename') else Path(r['path']).stem
            state = r.get('state_id') or ''
            file_created = r.get('file_created_at') or r.get('mtime') or now
            
            try:
                if has_render_id and has_state and has_file_created_at:
                    cur = execute(
                        """INSERT INTO tracks
                           (project_id, render_id, title, path, ext, file_size, mtime,
                            duration, state, is_primary, file_created_at, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            r['project_id'], r['render_id'], title, r['path'], r.get('ext') or '',
                            r.get('file_size') or 0, r.get('mtime') or now,
                            r.get('duration_s') or 0, state, 1 if r.get('is_primary') else 0,
                            file_created, now, now
                        )
                    )
                else:
                    cur = execute(
                        """INSERT INTO tracks
                           (project_id, title, path, ext, file_size, mtime, duration, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            r['project_id'], title, r['path'], r.get('ext') or '',
                            r.get('file_size') or 0, r.get('mtime') or now,
                            r.get('duration_s') or 0, now, now
                        )
                    )
                if cur and cur.rowcount:
                    added += 1
            except Exception as e:
                if 'UNIQUE constraint' in str(e) and 'path' in str(e):
                    # Track exists by path but without render_id - link it
                    if has_render_id:
                        execute(
                            "UPDATE tracks SET render_id = ?, project_id = ?, file_created_at = COALESCE(NULLIF(file_created_at, 0), ?), updated_at = ? WHERE path = ?",
                            (r['render_id'], r['project_id'], file_created, now, r['path'])
                        )
                        added += 1
                else:
                    logger.warning(f"Sync track from render {r.get('render_id')}: {e}")
        
        if added:
            logger.info(f"Synced {added} tracks from renders for Library view")
        return added
    except Exception as e:
        logger.error(f"sync_tracks_from_renders failed: {e}")
        return 0


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

