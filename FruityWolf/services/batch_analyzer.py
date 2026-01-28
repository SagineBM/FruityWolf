"""
Batch Analyzer Service
Runs audio analysis in the background for a queue of tracks.
"""

import logging
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QThread

from ..analysis import AnalyzerThread, AnalysisResult

logger = logging.getLogger(__name__)

class BackgroundBatchAnalyzer(QObject):
    """
    Analyzes a queue of tracks in the background.
    """
    
    progress = Signal(int, int) # Current, Total
    finished = Signal()
    track_completed = Signal(int, object) # track_id, AnalysisResult
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue: List[int] = []
        self.total = 0
        self.current_idx = 0
        self.thread: Optional[AnalyzerThread] = None
        self._active = False
        
    def add_tracks(self, track_ids: List[int]):
        """Add tracks to the analysis queue."""
        from ..scanner.library_scanner import get_track_by_id
        from ..analysis.detector import MIN_DURATION_FOR_KEY
        import soundfile as sf
        
        # Filter out tracks that are too short or invalid
        valid_track_ids = []
        for track_id in track_ids:
            track = get_track_by_id(track_id)
            if not track or not track.get('path'):
                continue
            
            # Check duration before adding to queue
            try:
                info = sf.info(track['path'])
                if info.duration >= MIN_DURATION_FOR_KEY:
                    valid_track_ids.append(track_id)
                else:
                    logger.debug(f"Skipping track {track_id}: duration {info.duration:.2f}s < {MIN_DURATION_FOR_KEY}s")
            except Exception as e:
                logger.debug(f"Could not check duration for track {track_id}: {e}")
                # Skip if we can't check duration
        
        if not valid_track_ids:
            return
        
        self.queue.extend(valid_track_ids)
        self.total += len(valid_track_ids)
        if not self._active:
            self._start_next()
            
    def _start_next(self):
        if not self.queue:
            self._active = False
            self.finished.emit()
            return
            
        self._active = True
        track_id = self.queue.pop(0)
        self.current_idx += 1
        
        # Get path (require get_track_by_id)
        from ..scanner.library_scanner import get_track_by_id
        track = get_track_by_id(track_id)
        if not track or not track.get('path'):
            self._start_next()
            return
            
        self.thread = AnalyzerThread(track['path'], track_id, parent=self)
        self.thread.finished.connect(lambda res: self._on_complete(track_id, res))
        self.thread.error.connect(lambda err: self._on_error(track_id, err))
        self.thread.start()
        
        self.progress.emit(self.current_idx, self.total)
        
    def _on_complete(self, track_id, result):
        logger.debug(f"Background analysis complete for track {track_id}")
        self.track_completed.emit(track_id, result)
        self._start_next()
        
    def _on_error(self, track_id, error):
        logger.error(f"Background analysis failed for track {track_id}: {error}")
        self._start_next()
        
    def is_running(self):
        return self._active
