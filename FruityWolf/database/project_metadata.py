"""
Project Metadata Management with No-Drift Policy

Prevents metadata drift by:
- Respecting user locks
- Only updating missing fields
- Requiring high confidence for overwrites
- Queueing uncertain changes for review
"""

import logging
from typing import Optional, Dict, Any

from . import query, query_one, execute

logger = logging.getLogger(__name__)


class MetadataManager:
    """Manages project metadata updates with drift prevention."""
    
    # Confidence thresholds
    OVERWRITE_CONFIDENCE_THRESHOLD = 85  # Require 85%+ confidence to overwrite
    
    # Tolerance for overwrites
    BPM_TOLERANCE = 2  # BPM can differ by up to 2 before requiring review
    KEY_TOLERANCE = 0.5  # Key confidence threshold
    
    def __init__(self, identity_store):
        """
        Initialize metadata manager.
        
        Args:
            identity_store: IdentityStore instance for checking locks
        """
        self.identity_store = identity_store
    
    def update_project_metadata(
        self,
        project_id: int,
        metadata: Dict[str, Any],
        confidence_scores: Dict[str, int]
    ) -> Dict[str, str]:
        """
        Update project metadata with drift prevention.
        
        Rules:
        1. If user_locked: skip all updates
        2. Fill missing fields always
        3. Overwrite only if confidence >= 85 AND change is small/compatible
        4. Otherwise queue for review
        
        Args:
            project_id: Database ID of the project
            metadata: Dict of field -> new value
            confidence_scores: Dict of field -> confidence (0-100)
            
        Returns:
            Dict of field -> action taken ('skipped', 'updated', 'queued')
        """
        results = {}
        
        # Check if project is locked
        if self.identity_store.is_project_locked(project_id):
            logger.debug(f"Project {project_id} is user-locked, skipping metadata updates")
            return {field: 'skipped' for field in metadata.keys()}
        
        # Get current metadata
        current = query_one(
            "SELECT flp_tempo, flp_key, flp_title, flp_artist, flp_genre FROM projects WHERE id = ?",
            (project_id,)
        )
        
        if not current:
            logger.warning(f"Project {project_id} not found")
            return {}
        
        # Process each field
        for field, new_value in metadata.items():
            if new_value is None:
                continue
            
            confidence = confidence_scores.get(field, 0)
            current_value = current.get(field)
            
            # 1. Fill missing fields always
            if current_value is None or current_value == '':
                if self._update_field(project_id, field, new_value):
                    results[field] = 'updated'
                    logger.debug(f"Filled missing {field} = {new_value} for project {project_id}")
                else:
                    results[field] = 'skipped'
            # 2. Overwrite only if high confidence and compatible
            elif confidence >= self.OVERWRITE_CONFIDENCE_THRESHOLD:
                if self._is_compatible_change(field, current_value, new_value):
                    if self._update_field(project_id, field, new_value):
                        results[field] = 'updated'
                        logger.debug(f"Overwrote {field} = {new_value} (confidence {confidence}%) for project {project_id}")
                    else:
                        results[field] = 'skipped'
                else:
                    # Change is too large, queue for review
                    self._queue_for_review(project_id, field, new_value, confidence)
                    results[field] = 'queued'
                    logger.debug(f"Queued {field} change for review (confidence {confidence}%, incompatible)")
            # 3. Low confidence: queue for review
            else:
                self._queue_for_review(project_id, field, new_value, confidence)
                results[field] = 'queued'
                logger.debug(f"Queued {field} change for review (confidence {confidence}%)")
        
        return results
    
    def _update_field(self, project_id: int, field: str, value: Any) -> bool:
        """Update a single field in projects table."""
        try:
            # Map field names to column names
            column_map = {
                'bpm': 'flp_tempo',
                'tempo': 'flp_tempo',
                'key': 'flp_key',
                'title': 'flp_title',
                'artist': 'flp_artist',
                'genre': 'flp_genre',
            }
            
            column = column_map.get(field.lower(), field)
            
            execute(
                f"UPDATE projects SET {column} = ? WHERE id = ?",
                (value, project_id)
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating {field} for project {project_id}: {e}")
            return False
    
    def _is_compatible_change(self, field: str, current_value: Any, new_value: Any) -> bool:
        """
        Check if a metadata change is compatible (small enough to auto-apply).
        
        Args:
            field: Field name
            current_value: Current value
            new_value: Proposed new value
            
        Returns:
            True if change is compatible, False otherwise
        """
        field_lower = field.lower()
        
        # BPM: allow small differences
        if field_lower in ('bpm', 'tempo'):
            try:
                current_bpm = float(current_value)
                new_bpm = float(new_value)
                return abs(new_bpm - current_bpm) <= self.BPM_TOLERANCE
            except (ValueError, TypeError):
                return False
        
        # Key: allow if same tonic/mode (simplified check)
        if field_lower == 'key':
            # Simple check: same value = compatible
            return str(current_value).lower() == str(new_value).lower()
        
        # Text fields: allow if similar (simple check)
        if field_lower in ('title', 'artist', 'genre'):
            # For now, allow any change (could add similarity check later)
            return True
        
        # Default: allow change
        return True
    
    def _queue_for_review(self, project_id: int, field: str, suggested_value: Any, confidence: int) -> None:
        """Queue a metadata change for user review."""
        try:
            execute(
                """
                INSERT OR REPLACE INTO metadata_review_queue (
                    project_id, field, suggested_value, confidence
                ) VALUES (?, ?, ?, ?)
                """,
                (project_id, field, str(suggested_value), confidence)
            )
        except Exception as e:
            logger.error(f"Error queueing {field} for review: {e}")
    
    def get_review_queue(self, project_id: Optional[int] = None) -> list:
        """
        Get metadata review queue items.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            List of review queue items
        """
        if project_id:
            rows = query(
                "SELECT * FROM metadata_review_queue WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,)
            )
        else:
            rows = query(
                "SELECT * FROM metadata_review_queue ORDER BY created_at DESC"
            )
        
        return [dict(row) for row in rows]
    
    def approve_review_item(self, project_id: int, field: str) -> bool:
        """
        Approve a queued metadata change.
        
        Args:
            project_id: Project ID
            field: Field name
            
        Returns:
            True if approved successfully
        """
        # Get queued item
        item = query_one(
            "SELECT suggested_value FROM metadata_review_queue WHERE project_id = ? AND field = ?",
            (project_id, field)
        )
        
        if not item:
            return False
        
        # Update metadata
        if self._update_field(project_id, field, item['suggested_value']):
            # Remove from queue
            execute(
                "DELETE FROM metadata_review_queue WHERE project_id = ? AND field = ?",
                (project_id, field)
            )
            return True
        
        return False
    
    def reject_review_item(self, project_id: int, field: str) -> bool:
        """Reject a queued metadata change."""
        try:
            execute(
                "DELETE FROM metadata_review_queue WHERE project_id = ? AND field = ?",
                (project_id, field)
            )
            return True
        except Exception as e:
            logger.error(f"Error rejecting review item: {e}")
            return False
