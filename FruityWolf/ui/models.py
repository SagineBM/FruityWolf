"""
UI Models

Qt models for data binding between Python and QML.
"""

from typing import List, Dict, Any, Optional
from enum import IntEnum
from PySide6.QtCore import (
    QAbstractListModel, Qt, QModelIndex, Property, Signal, Slot, QObject,
    QSortFilterProxyModel
)


class TrackRoles(IntEnum):
    """Roles for track model."""
    IdRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    ProjectNameRole = Qt.ItemDataRole.UserRole + 3
    ProjectPathRole = Qt.ItemDataRole.UserRole + 4
    PathRole = Qt.ItemDataRole.UserRole + 5
    FlpPathRole = Qt.ItemDataRole.UserRole + 6
    DurationRole = Qt.ItemDataRole.UserRole + 7
    BpmRole = Qt.ItemDataRole.UserRole + 8
    KeyRole = Qt.ItemDataRole.UserRole + 9
    FavoriteRole = Qt.ItemDataRole.UserRole + 10
    TagsRole = Qt.ItemDataRole.UserRole + 11
    NotesRole = Qt.ItemDataRole.UserRole + 12
    MtimeRole = Qt.ItemDataRole.UserRole + 13
    FileSizeRole = Qt.ItemDataRole.UserRole + 14
    CoverPathRole = Qt.ItemDataRole.UserRole + 15
    AudioDirRole = Qt.ItemDataRole.UserRole + 16
    SamplesDirRole = Qt.ItemDataRole.UserRole + 17
    StemsDirRole = Qt.ItemDataRole.UserRole + 18
    BackupDirRole = Qt.ItemDataRole.UserRole + 19


class TrackListModel(QAbstractListModel):
    """Model for displaying tracks in QML."""
    
    tracksChanged = Signal()
    countChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: List[Dict] = []
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._tracks)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._tracks):
            return None
        
        track = self._tracks[index.row()]
        
        role_map = {
            TrackRoles.IdRole: 'id',
            TrackRoles.TitleRole: 'title',
            TrackRoles.ProjectNameRole: 'project_name',
            TrackRoles.ProjectPathRole: 'project_path',
            TrackRoles.PathRole: 'path',
            TrackRoles.FlpPathRole: 'flp_path',
            TrackRoles.DurationRole: 'duration',
            TrackRoles.FavoriteRole: 'favorite',
            TrackRoles.NotesRole: 'notes',
            TrackRoles.MtimeRole: 'mtime',
            TrackRoles.FileSizeRole: 'file_size',
            TrackRoles.CoverPathRole: 'cover_path',
            TrackRoles.AudioDirRole: 'audio_dir',
            TrackRoles.SamplesDirRole: 'samples_dir',
            TrackRoles.StemsDirRole: 'stems_dir',
            TrackRoles.BackupDirRole: 'backup_dir',
        }
        
        if role in role_map:
            return track.get(role_map[role])
        
        # Special handling for BPM/Key (user override or detected)
        if role == TrackRoles.BpmRole:
            return track.get('bpm_user') or track.get('bpm_detected')
        
        if role == TrackRoles.KeyRole:
            return track.get('key_user') or track.get('key_detected')
        
        if role == TrackRoles.TagsRole:
            return track.get('tags', [])
        
        return None
    
    def roleNames(self):
        return {
            TrackRoles.IdRole: b'trackId',
            TrackRoles.TitleRole: b'title',
            TrackRoles.ProjectNameRole: b'projectName',
            TrackRoles.ProjectPathRole: b'projectPath',
            TrackRoles.PathRole: b'path',
            TrackRoles.FlpPathRole: b'flpPath',
            TrackRoles.DurationRole: b'duration',
            TrackRoles.BpmRole: b'bpm',
            TrackRoles.KeyRole: b'key',
            TrackRoles.FavoriteRole: b'favorite',
            TrackRoles.TagsRole: b'tags',
            TrackRoles.NotesRole: b'notes',
            TrackRoles.MtimeRole: b'mtime',
            TrackRoles.FileSizeRole: b'fileSize',
            TrackRoles.CoverPathRole: b'coverPath',
            TrackRoles.AudioDirRole: b'audioDir',
            TrackRoles.SamplesDirRole: b'samplesDir',
            TrackRoles.StemsDirRole: b'stemsDir',
            TrackRoles.BackupDirRole: b'backupDir',
        }
    
    @Slot(list)
    def setTracks(self, tracks: List[Dict]):
        """Set the track list."""
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()
        self.tracksChanged.emit()
        self.countChanged.emit()
    
    @Slot(int, result='QVariant')
    def getTrack(self, index: int) -> Optional[Dict]:
        """Get track at index."""
        if 0 <= index < len(self._tracks):
            return self._tracks[index]
        return None
    
    @Slot(int, result='QVariant')
    def getTrackById(self, track_id: int) -> Optional[Dict]:
        """Get track by ID."""
        for track in self._tracks:
            if track.get('id') == track_id:
                return track
        return None
    
    @Slot(int, bool)
    def updateFavorite(self, track_id: int, favorite: bool):
        """Update favorite status for a track."""
        for i, track in enumerate(self._tracks):
            if track.get('id') == track_id:
                self._tracks[i]['favorite'] = 1 if favorite else 0
                index = self.index(i)
                self.dataChanged.emit(index, index, [TrackRoles.FavoriteRole])
                break
    
    @Property(int, notify=countChanged)
    def count(self):
        return len(self._tracks)
    
    @property
    def tracks(self) -> List[Dict]:
        return self._tracks


class PlaylistRoles(IntEnum):
    """Roles for playlist model."""
    IdRole = Qt.ItemDataRole.UserRole + 1
    NameRole = Qt.ItemDataRole.UserRole + 2
    DescriptionRole = Qt.ItemDataRole.UserRole + 3
    CoverPathRole = Qt.ItemDataRole.UserRole + 4
    TrackCountRole = Qt.ItemDataRole.UserRole + 5
    CreatedAtRole = Qt.ItemDataRole.UserRole + 6


class PlaylistListModel(QAbstractListModel):
    """Model for displaying playlists in QML."""
    
    playlistsChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlists: List[Dict] = []
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._playlists)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._playlists):
            return None
        
        playlist = self._playlists[index.row()]
        
        role_map = {
            PlaylistRoles.IdRole: 'id',
            PlaylistRoles.NameRole: 'name',
            PlaylistRoles.DescriptionRole: 'description',
            PlaylistRoles.CoverPathRole: 'cover_path',
            PlaylistRoles.TrackCountRole: 'track_count',
            PlaylistRoles.CreatedAtRole: 'created_at',
        }
        
        if role in role_map:
            return playlist.get(role_map[role])
        
        return None
    
    def roleNames(self):
        return {
            PlaylistRoles.IdRole: b'playlistId',
            PlaylistRoles.NameRole: b'name',
            PlaylistRoles.DescriptionRole: b'description',
            PlaylistRoles.CoverPathRole: b'coverPath',
            PlaylistRoles.TrackCountRole: b'trackCount',
            PlaylistRoles.CreatedAtRole: b'createdAt',
        }
    
    @Slot(list)
    def setPlaylists(self, playlists: List[Dict]):
        """Set the playlist list."""
        self.beginResetModel()
        self._playlists = playlists
        self.endResetModel()
        self.playlistsChanged.emit()
    
    @Slot(int, result='QVariant')
    def getPlaylist(self, index: int) -> Optional[Dict]:
        """Get playlist at index."""
        if 0 <= index < len(self._playlists):
            return self._playlists[index]
        return None


class TagListModel(QAbstractListModel):
    """Model for displaying tags in QML."""
    
    tagsChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: List[Dict] = []
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._tags)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._tags):
            return None
        
        tag = self._tags[index.row()]
        
        if role == Qt.ItemDataRole.UserRole + 1:
            return tag.get('id')
        elif role == Qt.ItemDataRole.UserRole + 2:
            return tag.get('name')
        elif role == Qt.ItemDataRole.UserRole + 3:
            return tag.get('color')
        elif role == Qt.ItemDataRole.UserRole + 4:
            return tag.get('category')
        
        return None
    
    def roleNames(self):
        return {
            Qt.ItemDataRole.UserRole + 1: b'tagId',
            Qt.ItemDataRole.UserRole + 2: b'name',
            Qt.ItemDataRole.UserRole + 3: b'color',
            Qt.ItemDataRole.UserRole + 4: b'category',
        }
    
    @Slot(list)
    def setTags(self, tags: List[Dict]):
        """Set the tag list."""
        self.beginResetModel()
        self._tags = tags
        self.endResetModel()
        self.tagsChanged.emit()


class TrackFilterModel(QSortFilterProxyModel):
    """Proxy model for filtering and sorting tracks."""
    
    filterChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_text = ""
        self._favorites_only = False
        self._bpm_min = None
        self._bpm_max = None
        self._key_filter = None
        self._tag_filter = []
        
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    
    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        model = self.sourceModel()
        
        # Text search (title + project name + notes)
        if self._search_text:
            title = model.data(index, TrackRoles.TitleRole) or ""
            project = model.data(index, TrackRoles.ProjectNameRole) or ""
            notes = model.data(index, TrackRoles.NotesRole) or ""
            
            search_lower = self._search_text.lower()
            if (search_lower not in title.lower() and 
                search_lower not in project.lower() and
                search_lower not in notes.lower()):
                return False
        
        # Favorites filter
        if self._favorites_only:
            favorite = model.data(index, TrackRoles.FavoriteRole)
            if not favorite:
                return False
        
        # BPM range filter
        bpm = model.data(index, TrackRoles.BpmRole)
        if bpm:
            if self._bpm_min is not None and bpm < self._bpm_min:
                return False
            if self._bpm_max is not None and bpm > self._bpm_max:
                return False
        
        # Key filter
        if self._key_filter:
            key = model.data(index, TrackRoles.KeyRole)
            if key != self._key_filter:
                return False
        
        # Tag filter
        if self._tag_filter:
            tags = model.data(index, TrackRoles.TagsRole) or []
            if not any(tag in tags for tag in self._tag_filter):
                return False
        
        return True
    
    @Slot(str)
    def setSearchText(self, text: str):
        self._search_text = text
        self.invalidateFilter()
        self.filterChanged.emit()
    
    @Slot(bool)
    def setFavoritesOnly(self, value: bool):
        self._favorites_only = value
        self.invalidateFilter()
        self.filterChanged.emit()
    
    @Slot(float, float)
    def setBpmRange(self, min_bpm: float, max_bpm: float):
        self._bpm_min = min_bpm if min_bpm > 0 else None
        self._bpm_max = max_bpm if max_bpm > 0 else None
        self.invalidateFilter()
        self.filterChanged.emit()
    
    @Slot(str)
    def setKeyFilter(self, key: str):
        self._key_filter = key if key else None
        self.invalidateFilter()
        self.filterChanged.emit()
    
    @Slot(list)
    def setTagFilter(self, tags: list):
        self._tag_filter = tags
        self.invalidateFilter()
        self.filterChanged.emit()
    
    @Slot()
    def clearFilters(self):
        self._search_text = ""
        self._favorites_only = False
        self._bpm_min = None
        self._bpm_max = None
        self._key_filter = None
        self._tag_filter = []
        self.invalidateFilter()
        self.filterChanged.emit()
    
    @Slot(int, result='QVariant')
    def get(self, index: int) -> Optional[Dict]:
        """Get track at filtered/sorted index (for QML access)."""
        if index < 0 or index >= self.rowCount():
            return None
        
        source_index = self.mapToSource(self.index(index, 0))
        source_model = self.sourceModel()
        source_row = source_index.row()
        
        if hasattr(source_model, 'tracks') and 0 <= source_row < len(source_model.tracks):
            return source_model.tracks[source_row]
        return None
