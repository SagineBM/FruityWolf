"""
Analysis Dialog

UI for BPM and Key detection with:
- Single track or batch analysis
- Progress indication
- Results display with Camelot notation
- Save to database option
"""

import logging
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QDialogButtonBox, QCheckBox,
    QGroupBox, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread

from ..analysis import (
    AnalysisResult, analyze_audio, get_camelot, 
    format_bpm, format_key, AnalyzerThread
)
from ..scanner.library_scanner import get_track_by_id, update_track_metadata
from ..database import execute

logger = logging.getLogger(__name__)


# =============================================================================
# Styles
# =============================================================================

DIALOG_STYLE = """
    QDialog {
        background: #0f172a;
    }
    QLabel {
        color: #f1f5f9;
    }
    QLabel#Title {
        font-size: 18px;
        font-weight: bold;
    }
    QLabel#Value {
        font-size: 24px;
        font-weight: bold;
        color: #38bdf8;
    }
    QLabel#Subtitle {
        font-size: 12px;
        color: #94a3b8;
    }
    QGroupBox {
        font-weight: bold;
        color: #f1f5f9;
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
    }
    QProgressBar {
        border: none;
        border-radius: 4px;
        background: #334155;
        text-align: center;
        color: white;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #38bdf8, stop:1 #22d3ee);
        border-radius: 4px;
    }
    QCheckBox {
        color: #f1f5f9;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
"""

BUTTON_STYLE = """
    QPushButton {
        padding: 10px 20px;
        background: #334155;
        color: #f1f5f9;
        border: none;
        border-radius: 8px;
        font-weight: 500;
    }
    QPushButton:hover {
        background: #475569;
    }
    QPushButton:disabled {
        background: #1e293b;
        color: #64748b;
    }
    QPushButton#Primary {
        background: #38bdf8;
        color: #0f172a;
    }
    QPushButton#Primary:hover {
        background: #22d3ee;
    }
    QPushButton#Success {
        background: #22c55e;
        color: white;
    }
"""


# =============================================================================
# Single Track Analysis Dialog
# =============================================================================

class AnalysisDialog(QDialog):
    """
    Dialog for analyzing BPM and Key of a single track.
    
    Shows results with confidence indicators and Camelot notation.
    """
    
    analysis_complete = Signal(int, object)  # track_id, AnalysisResult
    
    def __init__(self, track_id: int, parent=None):
        super().__init__(parent)
        self.track_id = track_id
        self.track = get_track_by_id(track_id)
        self.result: Optional[AnalysisResult] = None
        self.analyzer_thread: Optional[AnalyzerThread] = None
        
        self.setWindowTitle("Audio Analysis")
        self.setMinimumSize(400, 350)
        self.setStyleSheet(DIALOG_STYLE)
        
        self._setup_ui()
        
        if self.track:
            self._start_analysis()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("Analyzing Audio")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Track name
        track_name = self.track.get('title', 'Unknown') if self.track else 'Unknown'
        subtitle = QLabel(track_name)
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)
        
        self.status_label = QLabel("Detecting BPM and Key...")
        self.status_label.setObjectName("Subtitle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Results group
        results_group = QGroupBox("Detection Results")
        results_layout = QGridLayout(results_group)
        results_layout.setSpacing(16)
        
        # BPM
        results_layout.addWidget(QLabel("BPM"), 0, 0)
        self.bpm_value = QLabel("--")
        self.bpm_value.setObjectName("Value")
        results_layout.addWidget(self.bpm_value, 0, 1)
        self.bpm_confidence = QLabel("--")
        self.bpm_confidence.setObjectName("Subtitle")
        results_layout.addWidget(self.bpm_confidence, 0, 2)
        
        # Key
        results_layout.addWidget(QLabel("Key"), 1, 0)
        self.key_value = QLabel("--")
        self.key_value.setObjectName("Value")
        results_layout.addWidget(self.key_value, 1, 1)
        self.key_confidence = QLabel("--")
        self.key_confidence.setObjectName("Subtitle")
        results_layout.addWidget(self.key_confidence, 1, 2)
        
        # Camelot
        results_layout.addWidget(QLabel("Camelot"), 2, 0)
        self.camelot_value = QLabel("--")
        self.camelot_value.setObjectName("Value")
        results_layout.addWidget(self.camelot_value, 2, 1)
        
        layout.addWidget(results_group)
        
        # Options
        self.save_checkbox = QCheckBox("Save results to library")
        self.save_checkbox.setChecked(True)
        layout.addWidget(self.save_checkbox)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(BUTTON_STYLE)
        self.cancel_btn.clicked.connect(self._cancel)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet(BUTTON_STYLE)
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _start_analysis(self):
        """Start the analysis thread."""
        if not self.track:
            return
        
        audio_path = self.track.get('path', '')
        if not audio_path:
            self.status_label.setText("Error: No audio path")
            return
        
        self.analyzer_thread = AnalyzerThread(audio_path, parent=self)
        self.analyzer_thread.finished.connect(self._on_analysis_complete)
        self.analyzer_thread.error.connect(self._on_analysis_error)
        self.analyzer_thread.start()
    
    def _on_analysis_complete(self, result: AnalysisResult):
        """Handle analysis completion."""
        self.result = result
        
        # Update UI
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status_label.setText("Analysis complete!")
        
        # BPM
        if result.bpm:
            self.bpm_value.setText(f"{result.bpm:.0f}")
            conf = result.bpm_confidence or 0
            self.bpm_confidence.setText(f"{conf*100:.0f}% confidence")
        
        # Key
        if result.key:
            self.key_value.setText(result.key)
            conf = result.key_confidence or 0
            self.key_confidence.setText(f"{conf*100:.0f}% confidence")
            
            # Camelot
            camelot = get_camelot(result.key)
            if camelot:
                self.camelot_value.setText(camelot)
        
        # Save to database if checked
        if self.save_checkbox.isChecked() and self.track_id:
            execute(
                """UPDATE tracks SET
                   bpm_detected = ?, bpm_confidence = ?,
                   key_detected = ?, key_confidence = ?,
                   duration = ?, updated_at = strftime('%s', 'now')
                   WHERE id = ?""",
                (
                    result.bpm, result.bpm_confidence,
                    result.key, result.key_confidence,
                    result.duration, self.track_id
                )
            )
        
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
        
        self.analysis_complete.emit(self.track_id, result)
    
    def _on_analysis_error(self, error: str):
        """Handle analysis error."""
        self.status_label.setText(f"Error: {error}")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
    
    def _cancel(self):
        """Cancel analysis."""
        if self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.terminate()
            self.analyzer_thread.wait()
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close."""
        self._cancel()
        super().closeEvent(event)
    
    @staticmethod
    def analyze_track(track_id: int, parent=None) -> Optional[AnalysisResult]:
        """Convenience method to show dialog and analyze a track."""
        dialog = AnalysisDialog(track_id, parent)
        dialog.exec()
        return dialog.result


# =============================================================================
# Batch Analysis Dialog
# =============================================================================

class BatchAnalysisDialog(QDialog):
    """
    Dialog for analyzing multiple tracks at once.
    """
    
    def __init__(self, track_ids: List[int], parent=None):
        super().__init__(parent)
        self.track_ids = track_ids
        self.current_index = 0
        self.results: List[AnalysisResult] = []
        self.analyzer_thread: Optional[AnalyzerThread] = None
        self._cancelled = False
        
        self.setWindowTitle("Batch Analysis")
        self.setMinimumSize(450, 300)
        self.setStyleSheet(DIALOG_STYLE)
        
        self._setup_ui()
        self._start_next()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel(f"Analyzing {len(self.track_ids)} Tracks")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Current track
        self.track_label = QLabel("")
        self.track_label.setObjectName("Subtitle")
        self.track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.track_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.track_ids))
        self.progress.setValue(0)
        self.progress.setFixedHeight(24)
        self.progress.setFormat("%v / %m tracks")
        layout.addWidget(self.progress)
        
        # Stats
        stats_layout = QHBoxLayout()
        
        self.completed_label = QLabel("Completed: 0")
        stats_layout.addWidget(self.completed_label)
        
        stats_layout.addStretch()
        
        self.errors_label = QLabel("Errors: 0")
        stats_layout.addWidget(self.errors_label)
        
        layout.addLayout(stats_layout)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(BUTTON_STYLE)
        self.cancel_btn.clicked.connect(self._cancel)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Done")
        self.close_btn.setStyleSheet(BUTTON_STYLE + """
            QPushButton#Success { background: #22c55e; }
        """)
        self.close_btn.setObjectName("Success")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _start_next(self):
        """Start analyzing the next track."""
        if self._cancelled or self.current_index >= len(self.track_ids):
            self._finish()
            return
        
        track_id = self.track_ids[self.current_index]
        track = get_track_by_id(track_id)
        
        if not track:
            self.current_index += 1
            self._start_next()
            return
        
        self.track_label.setText(f"{track.get('title', 'Unknown')}")
        
        audio_path = track.get('path', '')
        if not audio_path:
            self.current_index += 1
            self._start_next()
            return
        
        self.analyzer_thread = AnalyzerThread(audio_path, track_id, parent=self)
        self.analyzer_thread.finished.connect(self._on_track_complete)
        self.analyzer_thread.error.connect(self._on_track_error)
        self.analyzer_thread.start()
    
    def _on_track_complete(self, result: AnalysisResult):
        """Handle single track completion."""
        self.results.append(result)
        self.current_index += 1
        self.progress.setValue(self.current_index)
        
        completed = len([r for r in self.results if r.bpm or r.key])
        self.completed_label.setText(f"Completed: {completed}")
        
        self._start_next()
    
    def _on_track_error(self, error: str):
        """Handle single track error."""
        self.results.append(AnalysisResult(error=error))
        self.current_index += 1
        self.progress.setValue(self.current_index)
        
        errors = len([r for r in self.results if r.error])
        self.errors_label.setText(f"Errors: {errors}")
        
        self._start_next()
    
    def _finish(self):
        """Finish batch analysis."""
        self.track_label.setText("Analysis complete!")
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
        
        completed = len([r for r in self.results if r.bpm or r.key])
        QMessageBox.information(
            self, "Batch Analysis Complete",
            f"Analyzed {completed} of {len(self.track_ids)} tracks successfully."
        )
    
    def _cancel(self):
        """Cancel batch analysis."""
        self._cancelled = True
        if self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.terminate()
            self.analyzer_thread.wait()
        self.reject()
    
    @staticmethod
    def analyze_tracks(track_ids: List[int], parent=None) -> List[AnalysisResult]:
        """Convenience method for batch analysis."""
        dialog = BatchAnalysisDialog(track_ids, parent)
        dialog.exec()
        return dialog.results
