"""
Playlist Tracks Model

QAbstractListModel implementation for the Playlist Detail View (Tracks).
Supports drag-and-drop reordering.
"""

import logging
from typing import List
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Signal, QObject, QThread, QMimeData
from PySide6.QtGui import QDrag

from ...scanner.playlist_manager import get_playlist_tracks, reorder_playlist_tracks_batch, remove_track_from_playlist
from ...utils import format_duration

logger = logging.getLogger(__name__)

class TracksWorker(QObject):
    """Worker to fetch tracks."""
    finished = Signal(list)
    
    def __init__(self, playlist_id):
        super().__init__()
        self.playlist_id = playlist_id
        
    def run(self):
        try:
            data = get_playlist_tracks(self.playlist_id)
            self.finished.emit(data)
        except Exception as e:
            logger.error(f"Error fetching tracks: {e}")
            self.finished.emit([])

class PlaylistTracksModel(QAbstractListModel):
    """List model for tracks in a playlist."""
    
    TrackIdRole = Qt.ItemDataRole.UserRole + 1
    DurationRole = Qt.ItemDataRole.UserRole + 2
    ProjectNameRole = Qt.ItemDataRole.UserRole + 3
    TrackDataRole = Qt.ItemDataRole.UserRole + 4
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks = []
        self._playlist_id = None
        self._worker_thread = None
        
    def set_playlist(self, playlist_id):
        self._playlist_id = playlist_id
        self.refresh()
        
    def refresh(self):
        if not self._playlist_id:
            self.beginResetModel()
            self._tracks = []
            self.endResetModel()
            return

        if self._worker_thread is not None:
             if self._worker_thread.isRunning():
                 return
             self._worker_thread = None

        self._worker_thread = QThread()
        self._worker = TracksWorker(self._playlist_id)
        self._worker.moveToThread(self._worker_thread)
        
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._on_worker_finished)
        
        self._worker_thread.start()
        
    def _on_worker_finished(self):
        self._worker_thread = None
        self._worker = None
        
    def _on_data_loaded(self, data):
        self.beginResetModel()
        self._tracks = data
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._tracks)
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._tracks)):
            return None
            
        track = self._tracks[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # For list view main text
            return f"{index.row()+1}. {track.get('title', 'Unknown')}"
            
        elif role == self.TrackIdRole:
            return track['id']
            
        elif role == self.DurationRole:
            return format_duration(track.get('duration', 0))
            
        elif role == self.ProjectNameRole:
            return track.get('project_name', '')
            
        elif role == self.TrackDataRole:
            return track
            
        return None

    # Drag & Drop Support
    
    def flags(self, index):
        if not index.isValid():
             # Drop onto empty space?
             return Qt.ItemFlag.ItemIsDropEnabled
        return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | 
                Qt.ItemFlag.ItemIsDragEnabled)

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return ['application/x-playlist-track']

    def mimeData(self, indexes):
        mime = QMimeData()
        # Encode row index
        if indexes:
            row = indexes[0].row()
            mime.setData('application/x-playlist-track', str(row).encode('utf-8'))
        return mime

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.DropAction.IgnoreAction:
            return True
        if not data.hasFormat('application/x-playlist-track'):
            return False
            
        # Decode source row
        try:
            src_row = int(data.data('application/x-playlist-track').data().decode('utf-8'))
        except (ValueError, IndexError):
            return False
            
        # Determine strict destination row
        if row != -1:
            dest_row = row
        elif parent.isValid():
            dest_row = parent.row()
        else:
            dest_row = len(self._tracks)

        # If dropping on itself
        if dest_row == src_row:
            return False

        # If dest > src, we need to adjust because src is removed
        # QAbstractItemModel mechanics usually handle this logic in view or we handle logically
        # Standard reorder logic: 
        # beginMoveRows(parent, src, src, parent, dest)
        
        # NOTE: standard beginMoveRows "dest" is index *before which* item is placed.
        # If moving down: moving row 0 to index 3 (after row 2).
        
        if not self.beginMoveRows(QModelIndex(), src_row, src_row, QModelIndex(), dest_row):
            return False
            
        # Move item in list
        item = self._tracks.pop(src_row)
        
        # Adjust insertion index if src was before dest
        insert_idx = dest_row
        if src_row < dest_row:
            insert_idx -= 1
            
        self._tracks.insert(insert_idx, item)
        self.endMoveRows()
        
        # Update DB batch
        # We need to update positions for ALL tracks or just range.
        # To be safe and simple with our Batch API:
        track_ids = [t['id'] for t in self._tracks]
        
        # Run DB update in background thread to avoid freeze
        # Ideally we use a worker, but for now simple fire-and-forget logic if we had a global thread pool
        # Or just spawn a quick thread
        
        ReorderWorker(self._playlist_id, track_ids).start()
        
        return True
        
    def removeRow(self, row, parent=QModelIndex()):
        if 0 <= row < len(self._tracks):
            self.beginRemoveRows(parent, row, row)
            track = self._tracks.pop(row)
            self.endRemoveRows()
            
            # DB remove
            remove_track_from_playlist(self._playlist_id, track['id'])
            return True
        return False

# Helper worker for reorder to not block UI drag drop
class ReorderWorker(QThread):
    def __init__(self, playlist_id, track_ids):
        super().__init__()
        self.pid = playlist_id
        self.tids = track_ids
        
    def run(self):
        reorder_playlist_tracks_batch(self.pid, self.tids)
