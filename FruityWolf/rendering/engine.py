"""
Rendering Engine

Manages the render job queue, execution, and state.
"""

import os
import time
import logging
import subprocess
import threading
from enum import Enum
from pathlib import Path
from typing import List, Optional, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QThread

from .fl_cli import resolve_fl_executable, build_render_argv, get_expected_preview_path, get_expected_output_path
from .backup_exclusion import is_eligible_flp
from ..database import execute

logger = logging.getLogger(__name__)

class RenderStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

@dataclass
class RenderJob:
    source_flp: Path
    job_type: str = "audio"  # audio, midi, zip
    format_type: str = "mp3" # mp3, wav
    id: str = field(default_factory=lambda: str(time.time()))
    status: RenderStatus = RenderStatus.PENDING
    timeout_seconds: int = 600 # 10 minutes default
    
    # Results
    output_path: Optional[Path] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    exit_code: Optional[int] = None
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def __post_init__(self):
        # Determine output path immediately for determinism
        try:
            self.output_path = get_expected_output_path(self.source_flp, self.job_type, self.format_type)
        except Exception:
            # Fallback or leave None if unknown type (though helper raises ValueError)
            self.output_path = None

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        logger.debug(f"[Job {self.source_flp.name}] {message}")

class RenderQueue(QObject):
    """
    Manages the sequential execution of render jobs.
    Emits signals for UI updates.
    """
    job_added = Signal(RenderJob)
    job_started = Signal(RenderJob)
    job_progress = Signal(RenderJob, str) # job, status message
    job_finished = Signal(RenderJob) # success or failure
    queue_finished = Signal()
    
    def __init__(self):
        super().__init__()
        self._queue: List[RenderJob] = []
        self._current_job: Optional[RenderJob] = None
        self._stop_requested = False
        self._is_running = False
        self._thread = None
        
        # Pause control
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set() # Initially running (not paused)

    def add_job(self, job: RenderJob):
        self._queue.append(job)
        self.job_added.emit(job)

    def start_queue(self):
        if self._is_running:
            return
            
        self._stop_requested = False
        self._is_running = True
        self._paused = False
        self._pause_event.set()
        
        # Run in background thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop_queue(self):
        """Stop after current job."""
        self._stop_requested = True
        self._pause_event.set() # Unpause to allow exit

    def pause_queue(self):
        self._paused = True
        self._pause_event.clear()

    def resume_queue(self):
        self._paused = False
        self._pause_event.set()
        
    def skip_current(self):
        # This is tricky with subprocess, we need to kill the process
        # The _run_job method handles the actual process
        pass 

    def _run_loop(self):
        while self._queue and not self._stop_requested:
            # Check pause
            self._pause_event.wait()
            
            if self._stop_requested:
                break
                
            job = self._queue.pop(0)
            self._current_job = job
            
            try:
                self._run_job(job)
            except Exception as e:
                job.status = RenderStatus.FAILED
                job.error_message = str(e)
                job.log(f"CRITICAL ERROR: {e}")
                self.job_finished.emit(job)
            
            self._current_job = None
            
        self._is_running = False
        self.queue_finished.emit()

    def _run_job(self, job: RenderJob):
        job.status = RenderStatus.RUNNING
        job.start_time = time.time()
        self.job_started.emit(job)
        
        fl_exe = resolve_fl_executable()
        if not fl_exe:
            job.status = RenderStatus.FAILED
            job.error_message = "FL Studio executable not found in settings"
            job.log(job.error_message)
            self.job_finished.emit(job)
            return

        if not is_eligible_flp(job.source_flp):
            job.status = RenderStatus.SKIPPED
            job.error_message = "File matches backup exclusion rules"
            job.log(job.error_message)
            self.job_finished.emit(job)
            return

        try:
            argv = build_render_argv(fl_exe, job.source_flp, job.format_type, job.job_type)
            job.log(f"Executing: {' '.join(argv)}")
            
            # Start process
            # We use subprocess.Popen to allow timeout monitoring
            process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            try:
                # Wait for completion with timeout
                stdout, stderr = process.communicate(timeout=job.timeout_seconds)
                job.exit_code = process.returncode
                
                if stdout: job.log(f"STDOUT: {stdout}")
                if stderr: job.log(f"STDERR: {stderr}")
                
                # Check output file (FL Studio may write shortly after process exits)
                if job.exit_code == 0:
                    # Wait up to 5s for file to appear (poll every 0.5s)
                    for _ in range(10):
                        if job.output_path and job.output_path.exists():
                            break
                        time.sleep(0.5)
                    # Fallback: FL writes same name, different extension (e.g. project.flp -> project.mp3)
                    if not (job.output_path and job.output_path.exists()) and job.source_flp:
                        simple = job.source_flp.parent / f"{job.source_flp.stem}.{job.format_type.lower()}"
                        if simple.exists():
                            job.output_path = simple
                            job.log(f"Found output at: {simple}")
                    if job.output_path and job.output_path.exists():
                        # Verify size
                        size = job.output_path.stat().st_size
                        min_size = 200 * 1024 # 200KB for mp3
                        if job.format_type == 'wav':
                            min_size = 1024 * 1024 # 1MB for wav
                            
                        if size > min_size:
                            job.status = RenderStatus.COMPLETED
                            job.log("Render successful. Output verified.")
                            self._update_db_success(job)
                        else:
                            job.status = RenderStatus.FAILED
                            job.error_message = f"Output file too small ({size} bytes)"
                            job.log(job.error_message)
                            self._update_db_failure(job)
                    else:
                        job.status = RenderStatus.FAILED
                        job.error_message = "Output file not found after render"
                        job.log(job.error_message)
                        self._update_db_failure(job)
                else:
                    job.status = RenderStatus.FAILED
                    job.error_message = f"FL Studio exited with code {job.exit_code}"
                    job.log(job.error_message)
                    self._update_db_failure(job)

            except subprocess.TimeoutExpired:
                process.kill()
                job.status = RenderStatus.FAILED
                job.error_message = f"Timeout reached ({job.timeout_seconds}s)"
                job.log(job.error_message)
                self._update_db_failure(job)
                
        except Exception as e:
            job.status = RenderStatus.FAILED
            job.error_message = str(e)
            job.log(f"Execution exception: {e}")
            self._update_db_failure(job)
            
        job.end_time = time.time()
        self.job_finished.emit(job)

    def _update_db_success(self, job: RenderJob):
        """
        Update database to reflect new render.
        """
        try:
            # Update project status and activity signals
            execute(
                """
                UPDATE projects 
                SET render_status = 'preview_ready', 
                    last_rendered_at = strftime('%s', 'now'),
                    render_attempted_count = COALESCE(render_attempted_count, 0) + 1,
                    last_render_failed_at = NULL,
                    last_render_failed_reason = NULL,
                    updated_at = strftime('%s', 'now') 
                WHERE flp_path = ?
                """,
                (str(job.source_flp),)
            )
            
            # 2. Insert into renders table (if migration 17+ applied)
            # This makes it immediately available as a primary render
            if job.output_path and job.output_path.exists():
                stat = job.output_path.stat()
                execute(
                    """
                    INSERT INTO renders (
                        project_id, path, filename, ext, file_size, mtime, 
                        is_primary, created_at, updated_at
                    )
                    SELECT id, ?, ?, ?, ?, ?, 1, strftime('%s', 'now'), strftime('%s', 'now')
                    FROM projects WHERE flp_path = ?
                    ON CONFLICT(path) DO UPDATE SET
                        file_size = excluded.file_size,
                        mtime = excluded.mtime,
                        updated_at = excluded.updated_at,
                        is_primary = 1
                    """,
                    (
                        str(job.output_path),
                        job.output_path.name,
                        job.output_path.suffix.lower(),
                        stat.st_size,
                        int(stat.st_mtime),
                        str(job.source_flp)
                    )
                )
                
                # Also ensure project links to this render as primary
                execute(
                    """
                    UPDATE projects
                    SET primary_render_id = (SELECT id FROM renders WHERE path = ?)
                    WHERE flp_path = ?
                    """,
                    (str(job.output_path), str(job.source_flp))
                )
                
        except Exception as e:
            logger.error(f"Failed to update DB after render: {e}")

    def _update_db_failure(self, job: RenderJob):
        """
        Update database to record render failure.
        """
        try:
            execute(
                """
                UPDATE projects 
                SET last_render_failed_at = strftime('%s', 'now'),
                    last_render_failed_reason = ?,
                    render_attempted_count = COALESCE(render_attempted_count, 0) + 1,
                    render_status = CASE 
                        WHEN render_status = 'preview_ready' THEN 'preview_ready' 
                        ELSE 'render_failed' 
                    END,
                    updated_at = strftime('%s', 'now')
                WHERE flp_path = ?
                """,
                (str(job.error_message), str(job.source_flp))
            )
        except Exception as e:
            logger.error(f"Failed to update DB after render failure: {e}")

# Global Queue Instance
_render_queue = RenderQueue()

def get_render_queue() -> RenderQueue:
    return _render_queue
