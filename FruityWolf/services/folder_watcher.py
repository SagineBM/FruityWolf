"""
Folder Watcher Service
Monitors library roots for changes.
"""

import os
import logging
from PySide6.QtCore import QObject, Signal, QFileSystemWatcher, QTimer

logger = logging.getLogger(__name__)

class FolderWatcher(QObject):
    """
    Service that watches library folders for changes.
    Triggers a rescan when something changes.
    """
    
    change_detected = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self.watcher.fileChanged.connect(self._on_file_changed)
        
        # Debounce timer to avoid multiple rescans
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(2000) # 2 seconds
        self.debounce_timer.timeout.connect(self.change_detected.emit)
        
        self._roots = []
        
    def set_folders(self, folders: list):
        """Set the list of folders to watch."""
        # Remove old paths
        if self._roots:
            self.watcher.removePaths(self._roots)
            
        self._roots = [f for f in folders if os.path.isdir(f)]
        if self._roots:
            self.watcher.addPaths(self._roots)
            logger.info(f"Watching {len(self._roots)} library roots")
            
    def _on_directory_changed(self, path):
        logger.debug(f"Folder changed: {path}")
        self._trigger_debounce()
        
    def _on_file_changed(self, path):
        logger.debug(f"File changed: {path}")
        self._trigger_debounce()
        
    def _trigger_debounce(self):
        self.debounce_timer.start()
