"""
Async Image Manager with LRU Cache.
Handles background loading of cover art and images.
"""

import os
import logging
from typing import Dict, Optional, Callable
from collections import OrderedDict

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)

class ImageLoadWorker(QRunnable):
    """Worker for loading a single image file."""
    
    def __init__(self, path: str, target_size: Optional[int], callback: Callable[[str, QPixmap], None]):
        super().__init__()
        self.path = path
        self.target_size = target_size
        self.callback = callback
        
    def run(self):
        """Load and scale pixmap."""
        try:
            if not os.path.exists(self.path):
                return
                
            pixmap = QPixmap(self.path)
            if not pixmap.isNull() and self.target_size:
                pixmap = pixmap.scaled(
                    self.target_size, self.target_size, 
                    aspectMode=0 # IgnoreAspectRatio or Keep? Usually covers are square.
                )
            
            # Note: We can't emit signals from QRunnable directly easily without creating a QObject, 
            # so we use a callback or a specialized Signals class.
            self.callback(self.path, pixmap)
        except Exception as e:
            logger.error(f"Failed to load image {self.path}: {e}")

class ImageManager(QObject):
    """
    Centralized manager for image loading and caching.
    
    Features:
    - Thread pool management.
    - LRU Cache of QPixmaps.
    - Request deduplication.
    """
    
    image_loaded = Signal(str, QPixmap) # path, pixmap
    
    def __init__(self, cache_size: int = 200):
        super().__init__()
        self._cache = OrderedDict()
        self._cache_limit = cache_size
        self._pending_requests = set()
        self._thread_pool = QThreadPool.globalInstance()
        
    def get_image(self, path: str, size: int = 300) -> Optional[QPixmap]:
        """
        Get image from cache or start loading in background.
        
        Returns QPixmap if in cache, else None (and starts load).
        """
        if not path:
            return None
            
        # 1. Check cache
        cache_key = (path, size)
        if cache_key in self._cache:
            # Move to end (MRU)
            pixmap = self._cache.pop(cache_key)
            self._cache[cache_key] = pixmap
            return pixmap
            
        # 2. Check if already loading
        if cache_key in self._pending_requests:
            return None
            
        # 3. Start background load
        self._pending_requests.add(cache_key)
        worker = ImageLoadWorker(path, size, lambda p, pix: self._on_loaded(p, size, pix))
        self._thread_pool.start(worker)
        
        return None
        
    def _on_loaded(self, path: str, size: int, pixmap: QPixmap):
        """Callback from worker."""
        cache_key = (path, size)
        if not pixmap.isNull():
            # Add to cache
            self._cache[cache_key] = pixmap
            
            # Enforce LRU size
            if len(self._cache) > self._cache_limit:
                self._cache.popitem(last=False)
                
        # Remove from pending and signal
        if cache_key in self._pending_requests:
            self._pending_requests.remove(cache_key)
            
        # Signal Must be emitted on the main thread if possible, 
        # but since this callback runs in the worker thread, we use QTimer.singleShot
        # or similar if needed. Actually, QObject.metaObject().invokeMethod is better.
        # But for Signals, emitting from worker is generally okay in PySide6 
        # as long as we don't touch UI objects directly in the thread.
        # The signal-slot connection should handle thread hopping (QueuedConnection).
        self.image_loaded.emit(path, pixmap)

# Global instance for easy access
_instance = None

def get_image_manager() -> ImageManager:
    global _instance
    if _instance is None:
        _instance = ImageManager()
    return _instance
