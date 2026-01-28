"""
Async Job System for Bulk Operations.
"""

import uuid
import time
import logging
import json
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot

from ..database import execute, query, query_one

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkJob(QRunnable):
    """
    Base class for async bulk jobs.
    """
    
    def __init__(self, job_id: str, job_type: str, items: List[Any], signals: 'JobSignals'):
        super().__init__()
        self.job_id = job_id
        self.job_type = job_type
        self.items = items
        self.signals = signals
        
        self._cancel = False
        self.total = len(items)
        self.done = 0
        self.errors = []
        self.start_time = time.time()
        
    def cancel(self):
        self._cancel = True
        
    def run(self):
        self.signals.started.emit(self.job_id)
        
        try:
            self.process()
            
            status = JobStatus.COMPLETED
            if self._cancel:
                status = JobStatus.CANCELLED
            elif self.errors:
                if self.done > 0:
                    status = JobStatus.PARTIALLY_COMPLETED
                else:
                    status = JobStatus.FAILED
                    
            self.signals.finished.emit(self.job_id, status.value, self.errors)
            
        except Exception as e:
            logger.exception(f"Job {self.job_id} failed")
            self.errors.append(str(e))
            self.signals.finished.emit(self.job_id, JobStatus.FAILED.value, self.errors)

    def process(self):
        """Override this method."""
        pass
        
    def report_progress(self):
        self.signals.progress.emit(self.job_id, self.done, self.total)


from ..classifier.engine import ProjectClassifier, ProjectState, ClassificationResult

class BulkUpdateJob(BulkJob):
    """
    Job to update multiple projects/tracks.
    payload: { action: "set_bpm", value: 140 } etc
    """
    def __init__(self, job_id: str, items: List[int], payload: Dict, signals: 'JobSignals'):
        # items are IDs (track ids usually)
        super().__init__(job_id, "bulk_update", items, signals)
        self.payload = payload
        self.classifier = None
        
    def process(self):
        action = self.payload.get("action")
        value = self.payload.get("value")
        
        # Lazy init classifier if needed
        if action == "reclassify":
            self.classifier = ProjectClassifier()
        
        for item_id in self.items:
            if self._cancel: 
                break
                
            try:
                if action == "set_bpm":
                    execute("UPDATE tracks SET bpm_user = ?, updated_at = ? WHERE id = ?", 
                            (float(value), int(time.time()), item_id))
                            
                elif action == "set_key":
                    execute("UPDATE tracks SET key_user = ?, updated_at = ? WHERE id = ?", 
                            (str(value), int(time.time()), item_id))
                            
                elif action == "set_genre":
                    execute("INSERT OR IGNORE INTO track_tags (track_id, tag_id) VALUES (?, ?)",
                           (item_id, int(value)))
                           
                elif action == "set_state":
                    execute("UPDATE tracks SET state = ?, manual_state = ?, updated_at = ? WHERE id = ?",
                           (str(value), str(value), int(time.time()), item_id))

                elif action == "reclassify":
                    # 1. Fetch project signals
                    # Note: items are project_ids for reclassify usually (from ProjectsView)
                    # But could be track_ids if called from track list.
                    # ProjectsView passes project IDs.
                    
                    row = query_one("SELECT signals FROM projects WHERE id = ?", (item_id,))
                    if row and row['signals']:
                        try:
                            signals_data = json.loads(row['signals'])
                            # Handle both old flat format and new {raw, derived} format
                            if "raw" in signals_data:
                                raw = signals_data["raw"]
                                derived = signals_data["derived"]
                            else:
                                # Legacy flat signals - treat all as raw, empty derived?
                                # Or try to split?
                                # Ideally we just pass them as raw and hope for best or migrate.
                                # But classifier expects strict separate args now.
                                raw = signals_data
                                derived = {} 
                                
                            result = self.classifier.classify(raw, derived)
                            
                            # Update DB
                            # We update Project columns
                            cols = {
                                "state_id": result.state_id,
                                "state_confidence": result.state_confidence,
                                "state_reason": json.dumps(result.state_reasons),
                                "score": result.score,
                                "score_breakdown": json.dumps(result.score_breakdown),
                                "next_action_id": result.next_action_id,
                                "next_action_meta": json.dumps(result.next_action_meta),
                                "next_action_reason": json.dumps(result.next_action_reasons),
                                "ruleset_hash": result.ruleset_hash,
                                "classified_at_ts": result.classified_at_ts,
                                # Legacy sync
                                "state": result.state_id,
                                "render_priority_score": result.score
                            }
                            
                            set_clause = ", ".join(f"{k} = ?" for k in cols.keys())
                            values = tuple(cols.values())
                            execute(
                                f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?",
                                values + (int(time.time()), item_id)
                            )
                            
                        except Exception as e:
                            logger.error(f"Reclassify failed for {item_id}: {e}")
                
                # ... other actions
                
                self.done += 1
                if self.done % 5 == 0: # Throttle signals
                    self.report_progress()
                    
            except Exception as e:
                self.errors.append(f"Item {item_id}: {e}")
                
        self.report_progress() # Final emission


class JobSignals(QObject):
    """Signals for jobs must be QObject."""
    started = Signal(str)
    progress = Signal(str, int, int) # id, done, total
    finished = Signal(str, str, list) # id, status, errors


class JobManager(QObject):
    """
    Manages async jobs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self.signals = JobSignals()
        self.active_jobs: Dict[str, BulkJob] = {}
        
        # Connect internal signals to cleanup
        self.signals.finished.connect(self._on_job_finished)
        
    def start_bulk_update(self, ids: List[int], payload: Dict) -> str:
        job_id = str(uuid.uuid4())
        job = BulkUpdateJob(job_id, ids, payload, self.signals)
        self.active_jobs[job_id] = job
        self.pool.start(job)
        return job_id
        
    def cancel_job(self, job_id: str):
        if job_id in self.active_jobs:
            self.active_jobs[job_id].cancel()
            
    def _on_job_finished(self, job_id: str, status: str, errors: List):
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
