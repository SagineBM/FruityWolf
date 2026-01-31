"""
Identity Store - Database Operations for Identity System

Manages project_files and file_signals tables as the source of truth
for file tracking and attribution.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from ...database import get_db, execute, query, query_one, batch_transaction
from .signals import FileSignal, SignalType

logger = logging.getLogger(__name__)


class IdentityStore:
    """Manages identity system database operations."""
    
    def __init__(self):
        self.db = get_db()
    
    def ensure_project_pid(self, project_id: int) -> Optional[str]:
        """
        Ensure a project has a PID (Project Identity).
        Creates one if missing.
        
        Args:
            project_id: Database ID of the project
            
        Returns:
            PID string (UUID), or None if project doesn't exist
        """
        # Check if project exists and has PID
        row = query_one(
            "SELECT pid FROM projects WHERE id = ?",
            (project_id,)
        )
        
        if not row:
            return None
        
        pid = row['pid']
        
        # Generate PID if missing
        if not pid:
            pid = str(uuid.uuid4())
            execute(
                "UPDATE projects SET pid = ? WHERE id = ?",
                (pid, project_id)
            )
            logger.debug(f"Generated PID {pid} for project {project_id}")
        
        return pid
    
    def upsert_project_file(
        self,
        project_id: int,
        file_path: Path,
        fingerprint: str,
        file_role: str,
        file_ext: Optional[str] = None,
        file_size: Optional[int] = None,
        file_mtime: Optional[int] = None,
        is_primary: bool = False,
        confidence_score: int = 100,
        file_hash: Optional[str] = None
    ) -> int:
        """
        Upsert a file record in project_files table.
        
        Uses file_path as primary key (with project_id).
        Updates last_seen timestamp on each call.
        
        Args:
            project_id: Database ID of the project
            file_path: Absolute path to the file
            fingerprint: Fast fingerprint (from compute_fingerprint)
            file_role: Role of file (flp, render, backup, stem, sample, internal_audio, unknown)
            file_ext: File extension (e.g., '.flp', '.wav')
            file_size: File size in bytes
            file_mtime: File modification time (Unix timestamp)
            is_primary: Whether this is the primary file of its role
            confidence_score: Confidence score (0-100)
            file_hash: Optional full hash (computed lazily)
            
        Returns:
            Database ID of the file record
        """
        file_path_str = str(file_path)
        now = int(datetime.now().timestamp())
        
        # Try to find existing record
        existing = query_one(
            "SELECT id FROM project_files WHERE project_id = ? AND file_path = ?",
            (project_id, file_path_str)
        )
        
        if existing:
            file_id = existing['id']
            # Update existing record
            execute(
                """
                UPDATE project_files SET
                    fingerprint = ?,
                    file_hash = COALESCE(?, file_hash),
                    file_role = ?,
                    file_ext = ?,
                    file_size = ?,
                    file_mtime = ?,
                    is_primary = ?,
                    confidence_score = ?,
                    last_seen = ?
                WHERE id = ?
                """,
                (
                    fingerprint,
                    file_hash,
                    file_role,
                    file_ext,
                    file_size,
                    file_mtime,
                    1 if is_primary else 0,
                    confidence_score,
                    now,
                    file_id
                )
            )
            return file_id
        else:
            # Insert new record
            cur = execute(
                """
                INSERT INTO project_files (
                    project_id, file_path, fingerprint, file_hash,
                    file_role, file_ext, file_size, file_mtime,
                    is_primary, confidence_score, created_at, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    file_path_str,
                    fingerprint,
                    file_hash,
                    file_role,
                    file_ext,
                    file_size,
                    file_mtime,
                    1 if is_primary else 0,
                    confidence_score,
                    now,
                    now
                )
            )
            return cur.lastrowid
    
    def write_signals(self, file_id: int, signals: List[FileSignal]) -> None:
        """
        Write signals for a file (replace existing signals of same type).
        
        Args:
            file_id: Database ID of the file record
            signals: List of FileSignal objects
        """
        for signal in signals:
            execute(
                """
                INSERT OR REPLACE INTO file_signals (
                    file_id, signal_type, signal_value_text, signal_value_num, weight
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    signal.signal_type.value,
                    signal.value_text,
                    signal.value_num,
                    signal.weight
                )
            )
    
    def get_file_signals(self, file_id: int) -> List[FileSignal]:
        """
        Get all signals for a file.
        
        Args:
            file_id: Database ID of the file record
            
        Returns:
            List of FileSignal objects
        """
        rows = query(
            "SELECT signal_type, signal_value_text, signal_value_num, weight FROM file_signals WHERE file_id = ?",
            (file_id,)
        )
        
        signals = []
        for row in rows:
            try:
                signal_type = SignalType(row['signal_type'])
                signals.append(FileSignal(
                    signal_type=signal_type,
                    value_text=row['signal_value_text'],
                    value_num=row['signal_value_num'],
                    weight=row['weight']
                ))
            except ValueError:
                logger.warning(f"Unknown signal type: {row['signal_type']}")
        
        return signals
    
    def set_primary_render(self, project_id: int, file_id: int) -> None:
        """
        Set a render as primary for a project.
        Ensures only one primary render per project (transactional).
        
        Args:
            project_id: Database ID of the project
            file_id: Database ID of the file to set as primary
        """
        with batch_transaction():
            # Clear all primary flags for renders of this project
            execute(
                """
                UPDATE project_files SET is_primary = 0
                WHERE project_id = ? AND file_role = 'render'
                """,
                (project_id,)
            )
            
            # Set the chosen file as primary
            execute(
                """
                UPDATE project_files SET is_primary = 1
                WHERE id = ? AND project_id = ? AND file_role = 'render'
                """,
                (file_id, project_id)
            )
    
    def get_primary_render(self, project_id: int) -> Optional[Dict]:
        """
        Get the primary render for a project.
        
        Args:
            project_id: Database ID of the project
            
        Returns:
            Dict with file record data, or None if no primary render
        """
        row = query_one(
            """
            SELECT id, file_path, fingerprint, file_hash, file_ext, file_size, file_mtime, confidence_score
            FROM project_files
            WHERE project_id = ? AND file_role = 'render' AND is_primary = 1
            LIMIT 1
            """,
            (project_id,)
        )
        
        return dict(row) if row else None
    
    def find_file_by_fingerprint(self, fingerprint: str, project_id: Optional[int] = None) -> Optional[Dict]:
        """
        Find a file record by fingerprint.
        
        Args:
            fingerprint: File fingerprint
            project_id: Optional project ID to limit search
            
        Returns:
            Dict with file record data, or None if not found
        """
        if project_id:
            row = query_one(
                "SELECT * FROM project_files WHERE fingerprint = ? AND project_id = ? LIMIT 1",
                (fingerprint, project_id)
            )
        else:
            row = query_one(
                "SELECT * FROM project_files WHERE fingerprint = ? LIMIT 1",
                (fingerprint,)
            )
        
        return dict(row) if row else None
    
    def get_project_files(self, project_id: int, file_role: Optional[str] = None) -> List[Dict]:
        """
        Get all files for a project, optionally filtered by role.
        
        Args:
            project_id: Database ID of the project
            file_role: Optional role filter (flp, render, backup, stem, sample, internal_audio, unknown)
            
        Returns:
            List of file record dicts
        """
        if file_role:
            rows = query(
                "SELECT * FROM project_files WHERE project_id = ? AND file_role = ? ORDER BY is_primary DESC, file_mtime DESC",
                (project_id, file_role)
            )
        else:
            rows = query(
                "SELECT * FROM project_files WHERE project_id = ? ORDER BY file_role, is_primary DESC, file_mtime DESC",
                (project_id,)
            )
        
        return [dict(row) for row in rows]
    
    def mark_files_missing(self, project_id: int, seen_file_ids: List[int], days_threshold: int = 30) -> int:
        """
        Mark files as missing if they haven't been seen in N days.
        This is a soft delete - files remain in DB but are marked as missing.
        
        Args:
            project_id: Database ID of the project
            seen_file_ids: List of file IDs that were seen in current scan
            days_threshold: Number of days before marking as missing
            
        Returns:
            Number of files marked as missing
        """
        # For now, we'll use last_seen to track. In future, we could add a 'missing' flag.
        # This is a placeholder - actual implementation would check last_seen vs threshold
        # and potentially delete old records or mark them.
        return 0  # TODO: Implement if needed
    
    def update_project_confidence(self, project_id: int, confidence_score: int) -> None:
        """
        Update confidence score for a project.
        
        Args:
            project_id: Database ID of the project
            confidence_score: Confidence score (0-100)
        """
        execute(
            "UPDATE projects SET confidence_score = ? WHERE id = ?",
            (confidence_score, project_id)
        )
    
    def is_project_locked(self, project_id: int) -> bool:
        """
        Check if a project is user-locked (metadata should not be auto-updated).
        
        Args:
            project_id: Database ID of the project
            
        Returns:
            True if locked, False otherwise
        """
        row = query_one(
            "SELECT user_locked FROM projects WHERE id = ?",
            (project_id,)
        )
        
        return bool(row['user_locked']) if row else False
