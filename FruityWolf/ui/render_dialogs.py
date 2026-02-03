"""
Render Dialogs

UI components for batch rendering progress and control.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot

from ..rendering.engine import get_render_queue, RenderJob, RenderStatus

logger = logging.getLogger(__name__)

class RenderProgressDialog(QDialog):
    """
    Modal dialog showing batch render progress.
    Provides controls to Pause, Skip, and Stop.
    """
    
    def __init__(self, total_jobs: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rendering Projects")
        self.setFixedSize(500, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self.queue = get_render_queue()
        self.total_jobs = total_jobs
        self.completed_jobs = 0
        self.is_paused = False
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        self.lbl_current_file = QLabel("")
        self.lbl_current_file.setStyleSheet("color: #94a3b8;")
        self.lbl_current_file.setWordWrap(True)
        layout.addWidget(self.lbl_current_file)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_jobs)
        layout.addWidget(self.progress_bar)
        
        self.lbl_counter = QLabel(f"0 / {self.total_jobs}")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_counter)
        
        # Log View
        layout.addWidget(QLabel("Log output:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background: #0f172a; color: #cbd5e1; font-family: Consolas;")
        layout.addWidget(self.txt_log)
        
        # Controls
        btn_layout = QHBoxLayout()
        
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self.btn_pause)
        
        self.btn_skip = QPushButton("Skip Current")
        self.btn_skip.clicked.connect(self._skip_current)
        btn_layout.addWidget(self.btn_skip)
        
        self.btn_stop = QPushButton("Stop All")
        self.btn_stop.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_stop.clicked.connect(self._stop_all)
        btn_layout.addWidget(self.btn_stop)
        
        layout.addLayout(btn_layout)
        
        # Close button (hidden initially, shown when done)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.hide()
        layout.addWidget(self.btn_close)

    def _connect_signals(self):
        self.queue.job_started.connect(self._on_job_started)
        self.queue.job_finished.connect(self._on_job_finished)
        self.queue.queue_finished.connect(self._on_queue_finished)
        
    def _disconnect_signals(self):
        try:
            self.queue.job_started.disconnect(self._on_job_started)
            self.queue.job_finished.disconnect(self._on_job_finished)
            self.queue.queue_finished.disconnect(self._on_queue_finished)
        except:
            pass

    @Slot(RenderJob)
    def _on_job_started(self, job: RenderJob):
        self.lbl_status.setText("Rendering...")
        self.lbl_current_file.setText(job.source_flp.name)
        self._log(f"Started: {job.source_flp.name}")
        
    @Slot(RenderJob)
    def _on_job_finished(self, job: RenderJob):
        self.completed_jobs += 1
        self.progress_bar.setValue(self.completed_jobs)
        self.lbl_counter.setText(f"{self.completed_jobs} / {self.total_jobs}")
        
        status_icon = "✅" if job.status == RenderStatus.COMPLETED else "❌"
        msg = f"{status_icon} Finished: {job.source_flp.name} ({job.status.value})"
        if job.error_message:
            msg += f" - {job.error_message}"
        self._log(msg)

    @Slot()
    def _on_queue_finished(self):
        self.lbl_status.setText("Batch Render Completed")
        self.lbl_current_file.setText("All jobs processed.")
        self.btn_pause.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.btn_stop.hide()
        self.btn_close.show()
        self._log("Queue finished.")
        self._disconnect_signals()

    def _toggle_pause(self):
        if self.is_paused:
            self.queue.resume_queue()
            self.btn_pause.setText("Pause")
            self.lbl_status.setText("Resuming...")
            self._log("Queue resumed.")
        else:
            self.queue.pause_queue()
            self.btn_pause.setText("Resume")
            self.lbl_status.setText("Paused")
            self._log("Queue paused.")
        self.is_paused = not self.is_paused

    def _skip_current(self):
        # Implementation in engine for skip is tricky because it involves killing process
        # For now, we rely on the user knowing this might just flag it
        self._log("Skip requested (not fully implemented in engine yet, wait for timeout or next job).")
        # To really skip, we'd need access to the running process handle or flag
        # Engine's stop_queue stops AFTER current. 
        pass

    def _stop_all(self):
        reply = QMessageBox.question(
            self, "Stop Batch Render", 
            "Are you sure you want to stop the remaining jobs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.queue.stop_queue()
            self.lbl_status.setText("Stopping...")
            self._log("Stop requested. Waiting for current job to finish/terminate...")
            self.btn_pause.setEnabled(False)
            self.btn_skip.setEnabled(False)
            self.btn_stop.setEnabled(False)

    def _log(self, text: str):
        self.txt_log.append(text)
        # Auto scroll
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def closeEvent(self, event):
        # Prevent closing if running
        if self.btn_stop.isVisible() and self.btn_stop.isEnabled():
            event.ignore()
            return
        super().closeEvent(event)
