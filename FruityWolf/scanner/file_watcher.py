"""
File Watcher

Watches library folders for changes and triggers incremental scans.
"""

import os
import logging
from pathlib import Path
from typing import Set, Callable
import time

from PySide6.QtCore import QObject, Signal, QThread

logger = logging.getLogger(__name__)

# Audio extensions to watch
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.flp'}


class FileWatcher(QObject):
    """
    Watches library directories for file changes.
    
    Uses watchdog if available, falls back to polling.
    """
    
    file_created = Signal(str)
    file_modified = Signal(str)
    file_deleted = Signal(str)
    directory_created = Signal(str)
    directory_deleted = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._watching = False
        self._paths: Set[str] = set()
        self._observer = None
        self._use_watchdog = False
        
        self._init_backend()
    
    def _init_backend(self):
        """Initialize file watching backend."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            self._use_watchdog = True
            self._observer = Observer()
            
            # Create event handler
            class Handler(FileSystemEventHandler):
                def __init__(self, watcher):
                    self.watcher = watcher
                
                def on_created(self, event):
                    path = event.src_path
                    if event.is_directory:
                        self.watcher.directory_created.emit(path)
                    elif self._is_relevant(path):
                        self.watcher.file_created.emit(path)
                
                def on_modified(self, event):
                    if not event.is_directory:
                        path = event.src_path
                        if self._is_relevant(path):
                            self.watcher.file_modified.emit(path)
                
                def on_deleted(self, event):
                    path = event.src_path
                    if event.is_directory:
                        self.watcher.directory_deleted.emit(path)
                    elif self._is_relevant(path):
                        self.watcher.file_deleted.emit(path)
                
                def _is_relevant(self, path):
                    ext = Path(path).suffix.lower()
                    return ext in AUDIO_EXTENSIONS
            
            self._handler = Handler(self)
            logger.info("Using watchdog for file watching")
            
        except ImportError:
            logger.warning("watchdog not installed, file watching disabled")
            self._use_watchdog = False
    
    def add_path(self, path: str):
        """Add a path to watch."""
        if not os.path.isdir(path):
            logger.warning(f"Path is not a directory: {path}")
            return
        
        self._paths.add(path)
        
        if self._use_watchdog and self._observer:
            self._observer.schedule(self._handler, path, recursive=True)
            logger.info(f"Watching: {path}")
    
    def remove_path(self, path: str):
        """Remove a path from watching."""
        self._paths.discard(path)
        # Note: watchdog doesn't easily support unscheduling specific paths
    
    def start(self):
        """Start watching."""
        if self._use_watchdog and self._observer:
            self._observer.start()
            self._watching = True
            logger.info("File watcher started")
    
    def stop(self):
        """Stop watching."""
        if self._use_watchdog and self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._watching = False
            logger.info("File watcher stopped")
    
    @property
    def is_watching(self) -> bool:
        return self._watching


class WatcherThread(QThread):
    """Thread for running file watcher."""
    
    file_changed = Signal(str, str)  # path, event_type
    
    def __init__(self, paths: list = None, parent=None):
        super().__init__(parent)
        self._paths = paths or []
        self._running = False
        self._watcher = None
    
    def run(self):
        self._watcher = FileWatcher()
        
        # Connect signals
        self._watcher.file_created.connect(lambda p: self.file_changed.emit(p, 'created'))
        self._watcher.file_modified.connect(lambda p: self.file_changed.emit(p, 'modified'))
        self._watcher.file_deleted.connect(lambda p: self.file_changed.emit(p, 'deleted'))
        
        # Add paths
        for path in self._paths:
            self._watcher.add_path(path)
        
        # Start watching
        self._watcher.start()
        self._running = True
        
        # Keep thread alive
        while self._running:
            self.msleep(1000)
        
        self._watcher.stop()
    
    def stop(self):
        self._running = False
