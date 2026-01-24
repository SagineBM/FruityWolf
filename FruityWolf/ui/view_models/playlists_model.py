"""
Playlists Model

QAbstractListModel implementation for the Playlists Grid.
"""

import logging
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Signal, QObject, QThread
from PySide6.QtGui import QIcon, QPixmap

from ...scanner.playlist_manager import get_all_playlists, get_playlist_cover_path
from ...utils import get_placeholder_cover

logger = logging.getLogger(__name__)

class PlaylistsWorker(QObject):
    """Worker to fetch playlists in background."""
    finished = Signal(list)
    
    def run(self):
        try:
            data = get_all_playlists()
            self.finished.emit(data)
        except Exception as e:
            logger.error(f"Error fetching playlists: {e}")
            self.finished.emit([])

class PlaylistsModel(QAbstractListModel):
    """List model for playlists."""
    
    PlaylistIdRole = Qt.ItemDataRole.UserRole + 1
    TrackCountRole = Qt.ItemDataRole.UserRole + 2
    CoverPathRole = Qt.ItemDataRole.UserRole + 3
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlists = []
        self._worker_thread = None
        self._worker = None
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._playlists)
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._playlists)):
            return None
            
        playlist = self._playlists[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            return playlist.get('name', 'Untitled')
            
        elif role == self.PlaylistIdRole:
            return playlist['id']
            
        elif role == self.TrackCountRole:
            return playlist.get('track_count', 0)
            
        elif role == self.CoverPathRole:
            # Check if we have a path stored or accessible
            # We relying on the view/delegate to fetch or cache
            return get_playlist_cover_path(playlist['id'])
            
        return None

    def refresh(self):
        """Start async refresh."""
        if self._worker_thread is not None:
             if self._worker_thread.isRunning():
                 return
             # If it exists but not running (finished but not cleaned?), clean it
             self._worker_thread = None

        self._worker_thread = QThread()
        self._worker = PlaylistsWorker()
        self._worker.moveToThread(self._worker_thread)
        
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        # Clean up reference
        self._worker_thread.finished.connect(self._on_worker_finished)
        
        self._worker_thread.start()
        
    def _on_worker_finished(self):
        self._worker_thread = None
        self._worker = None

    def _on_data_loaded(self, data):
        self.beginResetModel()
        self._playlists = data
        self.endResetModel()

    def get_playlist_by_index(self, index):
        if 0 <= index.row() < len(self._playlists):
            return self._playlists[index.row()]
        return None
