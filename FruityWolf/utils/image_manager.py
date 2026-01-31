"""
Async Image Manager with LRU Cache.
Handles background loading of cover art and images.

Features:
- Async loading with QThreadPool
- LRU cache (default 500 items)
- Request deduplication
- Request cancellation for fast scrolling
- Proper signal handling for thread safety
"""

import os
import logging
from typing import Dict, Optional, Callable, Tuple
from collections import OrderedDict

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot, Qt
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)

class ImageLoadWorker(QRunnable):
    """Worker for loading a single image file."""
    
    def __init__(self, path: str, target_size: Optional[int], callback: Callable[[str, QPixmap], None], request_id: Optional[str] = None):
        super().__init__()
        self.path = path
        self.target_size = target_size
        self.callback = callback
        self.request_id = request_id or path
        self._cancelled = False
        
    def cancel(self):
        """Cancel this load request."""
        self._cancelled = True
        
    def run(self):
        """Load and scale pixmap."""
        try:
            if self._cancelled:
                return
                
            if not os.path.exists(self.path):
                return
                
            pixmap = QPixmap(self.path)
            if self._cancelled:
                return
                
            if not pixmap.isNull() and self.target_size:
                pixmap = pixmap.scaled(
                    self.target_size, self.target_size, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            if not self._cancelled:
                self.callback(self.path, pixmap, self.request_id)
        except Exception as e:
            logger.error(f"Failed to load image {self.path}: {e}")

class ImageManager(QObject):
    """
    Centralized manager for image loading and caching.
    
    Features:
    - Thread pool management
    - LRU Cache of QPixmaps (default 500)
    - Request deduplication
    - Request cancellation for fast scrolling
    """
    
    image_loaded = Signal(str, QPixmap, str)  # path, pixmap, request_id
    
    def __init__(self, cache_size: int = 500):
        super().__init__()
        self._cache: OrderedDict[Tuple[str, int], QPixmap] = OrderedDict()
        self._cache_limit = cache_size
        self._pending_requests: Dict[Tuple[str, int], ImageLoadWorker] = {}
        self._thread_pool = QThreadPool.globalInstance()
        # Set max threads for better performance
        if self._thread_pool.maxThreadCount() < 4:
            self._thread_pool.setMaxThreadCount(4)
        
    def get_image(self, path: str, size: int = 300, request_id: Optional[str] = None) -> Optional[QPixmap]:
        """
        Get image from cache or start loading in background.
        
        Args:
            path: Path to image file
            size: Target size (square)
            request_id: Optional unique ID for this request (for cancellation)
        
        Returns:
            QPixmap if in cache, else None (and starts async load)
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
        req_id = request_id or path
        worker = ImageLoadWorker(path, size, self._on_loaded, req_id)
        self._pending_requests[cache_key] = worker
        self._thread_pool.start(worker)
        
        return None
    
    def cancel_request(self, request_id: str):
        """Cancel pending load requests matching request_id."""
        cancelled = []
        for cache_key, worker in list(self._pending_requests.items()):
            if worker.request_id == request_id:
                worker.cancel()
                cancelled.append(cache_key)
        
        for key in cancelled:
            self._pending_requests.pop(key, None)
    
    def cancel_all(self):
        """Cancel all pending requests."""
        for worker in self._pending_requests.values():
            worker.cancel()
        self._pending_requests.clear()
        
    def clear_cache(self):
        """Clear the image cache."""
        self._cache.clear()
        
    def _on_loaded(self, path: str, pixmap: QPixmap, request_id: str):
        """Callback from worker."""
        # Find cache key for this path (may have different sizes)
        cache_key = None
        for key in list(self._pending_requests.keys()):
            if key[0] == path:
                cache_key = key
                break
        
        if cache_key:
            self._pending_requests.pop(cache_key, None)
            
        if not pixmap.isNull():
            # Find the actual size used (may differ from requested)
            actual_size = max(pixmap.width(), pixmap.height())
            actual_cache_key = (path, actual_size)
            
            # Add to cache
            self._cache[actual_cache_key] = pixmap
            
            # Enforce LRU size
            while len(self._cache) > self._cache_limit:
                self._cache.popitem(last=False)
            
            # Signal on main thread (handled by Qt's signal system)
            self.image_loaded.emit(path, pixmap, request_id)

# Global instance for easy access
_instance = None

def get_image_manager() -> ImageManager:
    global _instance
    if _instance is None:
        _instance = ImageManager()
    return _instance
