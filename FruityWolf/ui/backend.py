"""
Backend Bridge

Exposes Python functionality to QML.
"""

import os
import logging
from typing import Optional, List, Dict
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QUrl
from PySide6.QtQml import QmlElement

from ..database import query, execute, get_setting, set_setting, get_app_data_path
from ..scanner import (
    ScannerThread, get_all_tracks, get_favorite_tracks, search_tracks,
    toggle_favorite, get_track_by_id, update_track_metadata, LibraryScanner
)
from ..player import get_player, PlayerState, RepeatMode
from ..waveform import WaveformThread, get_cached_waveform
from ..analysis import AnalyzerThread, format_bpm, format_key, KEYS
from ..utils import (
    format_duration, format_file_size, format_timestamp,
    open_file, open_folder, open_fl_studio, count_files_in_folder,
    get_folder_size
)
from .models import TrackListModel, PlaylistListModel, TagListModel, TrackFilterModel

logger = logging.getLogger(__name__)


QML_IMPORT_NAME = "FLLibraryPro"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class Backend(QObject):
    """
    Main backend bridge for QML.
    
    Exposes all app functionality to the UI.
    """
    
    # Signals
    tracksLoaded = Signal()
    scanStarted = Signal()
    scanProgress = Signal(int, int, str)  # current, total, message
    scanFinished = Signal(int, int)  # projects, tracks
    scanError = Signal(str)
    
    # Player signals
    playerStateChanged = Signal(str)  # "playing", "paused", "stopped"
    playerPositionChanged = Signal(float)  # 0-1
    playerDurationChanged = Signal(float)  # seconds
    playerTrackChanged = Signal('QVariant')  # track dict
    playerVolumeChanged = Signal(float)  # 0-1
    
    # Waveform signals
    waveformReady = Signal(str, list, list)  # path, peaks_min, peaks_max
    
    # Analysis signals
    analysisComplete = Signal(int, float, str)  # track_id, bpm, key
    
    # Navigation signals
    navigateTo = Signal(str, 'QVariant')  # page, data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Models
        self._track_model = TrackListModel(self)
        self._playlist_model = PlaylistListModel(self)
        self._tag_model = TagListModel(self)
        self._filter_model = TrackFilterModel(self)
        self._filter_model.setSourceModel(self._track_model)
        
        # State
        self._current_page = "library"
        self._selected_track: Optional[Dict] = None
        self._scanner_thread: Optional[ScannerThread] = None
        self._waveform_thread: Optional[WaveformThread] = None
        self._analysis_thread: Optional[AnalyzerThread] = None
        
        # Player
        self._player = get_player()
        self._connect_player_signals()
        
        # Load initial data
        self._load_tags()
        self._load_playlists()
    
    def _connect_player_signals(self):
        """Connect player signals to backend signals."""
        self._player.state_changed.connect(self._on_player_state_changed)
        self._player.position_changed.connect(self.playerPositionChanged.emit)
        self._player.duration_changed.connect(self.playerDurationChanged.emit)
        self._player.track_changed.connect(self.playerTrackChanged.emit)
        self._player.volume_changed.connect(self.playerVolumeChanged.emit)
    
    def _on_player_state_changed(self, state: PlayerState):
        """Convert player state to string for QML."""
        state_map = {
            PlayerState.STOPPED: "stopped",
            PlayerState.PLAYING: "playing",
            PlayerState.PAUSED: "paused",
            PlayerState.LOADING: "loading",
            PlayerState.ERROR: "error",
        }
        self.playerStateChanged.emit(state_map.get(state, "stopped"))
    
    # Properties
    @Property(QObject, constant=True)
    def trackModel(self):
        return self._track_model
    
    @Property(QObject, constant=True)
    def filteredTrackModel(self):
        return self._filter_model
    
    @Property(QObject, constant=True)
    def playlistModel(self):
        return self._playlist_model
    
    @Property(QObject, constant=True)
    def tagModel(self):
        return self._tag_model
    
    @Property(str)
    def currentPage(self):
        return self._current_page
    
    @currentPage.setter
    def currentPage(self, value: str):
        self._current_page = value
    
    # Data loading
    @Slot()
    def loadTracks(self):
        """Load all tracks from database."""
        tracks = get_all_tracks(limit=5000)
        self._track_model.setTracks(tracks)
        self.tracksLoaded.emit()
    
    @Slot()
    def loadFavorites(self):
        """Load favorite tracks."""
        tracks = get_favorite_tracks()
        self._track_model.setTracks(tracks)
        self.tracksLoaded.emit()
    
    @Slot(str, float, float, str, list, bool)
    def searchTracks(
        self,
        term: str = '',
        bpm_min: float = 0,
        bpm_max: float = 0,
        key: str = '',
        tags: list = None,
        favorites_only: bool = False
    ):
        """Search tracks with filters."""
        tracks = search_tracks(
            term=term,
            bpm_min=bpm_min if bpm_min > 0 else None,
            bpm_max=bpm_max if bpm_max > 0 else None,
            key=key if key else None,
            tags=tags if tags else None,
            favorites_only=favorites_only,
        )
        self._track_model.setTracks(tracks)
        self.tracksLoaded.emit()
    
    def _load_tags(self):
        """Load all tags."""
        rows = query("SELECT id, name, color, category FROM tags ORDER BY category, name")
        tags = [dict(row) for row in rows]
        self._tag_model.setTags(tags)
    
    def _load_playlists(self):
        """Load all playlists with track counts."""
        rows = query("""
            SELECT p.id, p.name, p.description, p.cover_path, p.created_at,
                   COUNT(pt.track_id) as track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
            GROUP BY p.id
            ORDER BY p.name
        """)
        playlists = [dict(row) for row in rows]
        self._playlist_model.setPlaylists(playlists)
    
    # Library scanning
    @Slot()
    def rescanLibrary(self):
        """Start library rescan."""
        if self._scanner_thread and self._scanner_thread.isRunning():
            return
        
        self._scanner_thread = ScannerThread(self)
        self._scanner_thread.progress.connect(self.scanProgress.emit)
        self._scanner_thread.finished.connect(self._on_scan_finished)
        self._scanner_thread.error.connect(self.scanError.emit)
        
        self.scanStarted.emit()
        self._scanner_thread.start()
    
    def _on_scan_finished(self, result):
        """Handle scan completion."""
        self.scanFinished.emit(result.projects_found, result.tracks_found)
        self.loadTracks()
    
    @Slot(str, result=bool)
    def addLibraryRoot(self, path: str) -> bool:
        """Add a library root folder."""
        scanner = LibraryScanner()
        return scanner.add_library_root(path)
    
    @Slot(result=list)
    def getLibraryRoots(self) -> List[str]:
        """Get all library root folders."""
        rows = query("SELECT path FROM library_roots WHERE enabled = 1")
        return [row['path'] for row in rows]
    
    # Player controls
    @Slot(int)
    def playTrack(self, track_id: int):
        """Play a track by ID."""
        track = get_track_by_id(track_id)
        if track:
            # Build playlist from filtered/sorted model (matches what user sees)
            # This ensures the playlist order matches the visual order on screen
            filtered_tracks = []
            source_model = self._filter_model.sourceModel()
            for row in range(self._filter_model.rowCount()):
                source_index = self._filter_model.mapToSource(self._filter_model.index(row, 0))
                source_row = source_index.row()
                if 0 <= source_row < len(source_model.tracks):
                    filtered_tracks.append(source_model.tracks[source_row])
            
            # Find the index of the selected track in the filtered list
            index = next((i for i, t in enumerate(filtered_tracks) if t.get('id') == track_id), 0)
            self._player.set_playlist(filtered_tracks, index)
    
    @Slot('QVariant')
    def playTrackDict(self, track: dict):
        """Play a track from dict."""
        self._player.load_track(track)
    
    @Slot()
    def togglePlay(self):
        """Toggle play/pause."""
        self._player.toggle_play()
    
    @Slot()
    def play(self):
        """Resume playback."""
        self._player.play()
    
    @Slot()
    def pause(self):
        """Pause playback."""
        self._player.pause()
    
    @Slot()
    def stop(self):
        """Stop playback."""
        self._player.stop()
    
    @Slot()
    def nextTrack(self):
        """Play next track."""
        self._player.next()
    
    @Slot()
    def previousTrack(self):
        """Play previous track."""
        self._player.previous()
    
    @Slot(float)
    def seek(self, position: float):
        """Seek to position (0-1)."""
        self._player.seek(position)
    
    @Slot(float)
    def setVolume(self, volume: float):
        """Set volume (0-1)."""
        self._player.volume = volume
    
    @Slot()
    def toggleMute(self):
        """Toggle mute."""
        self._player.toggle_mute()
    
    @Slot()
    def toggleShuffle(self):
        """Toggle shuffle mode."""
        self._player.toggle_shuffle()
    
    @Slot()
    def cycleRepeat(self):
        """Cycle repeat mode."""
        self._player.cycle_repeat()
    
    @Property(bool)
    def isPlaying(self) -> bool:
        return self._player.state == PlayerState.PLAYING
    
    @Property(bool)
    def isShuffle(self) -> bool:
        return self._player.shuffle
    
    @Property(str)
    def repeatMode(self) -> str:
        return self._player.repeat.value
    
    @Property(float)
    def volume(self) -> float:
        return self._player.volume
    
    @Property('QVariant')
    def currentTrack(self):
        return self._player.current_track
    
    @Property(float)
    def currentDuration(self) -> float:
        return self._player.duration
    
    @Property(float)
    def currentPosition(self) -> float:
        return self._player.position
    
    # Queue system
    queueChanged = Signal()  # Emitted when queue changes
    
    @Slot(result=list)
    def getQueue(self) -> List[Dict]:
        """Get upcoming tracks in the queue."""
        playlist = self._player.playlist
        index = self._player.playlist_index
        
        if not playlist or index < 0:
            return []
        
        # Return tracks after current (up to 20)
        upcoming = playlist[index + 1:index + 21]
        return upcoming
    
    @Slot()
    def clearQueue(self):
        """Clear the queue (keep only current track)."""
        playlist = self._player.playlist
        index = self._player.playlist_index
        
        if playlist and 0 <= index < len(playlist):
            # Keep only the current track
            current = playlist[index]
            self._player.set_playlist([current], 0)
            self.queueChanged.emit()
    
    @Slot(int)
    def removeFromQueue(self, track_id: int):
        """Remove a track from the queue."""
        playlist = self._player.playlist
        index = self._player.playlist_index
        
        if not playlist:
            return
        
        # Find and remove the track (only from queue, not currently playing)
        new_playlist = []
        new_index = index
        for i, track in enumerate(playlist):
            if track.get('id') == track_id and i > index:
                # Skip this track (remove from queue)
                continue
            else:
                # Adjust index if we removed a track before current
                if i < index and track.get('id') == track_id:
                    new_index -= 1
                new_playlist.append(track)
        
        if len(new_playlist) != len(playlist):
            self._player.set_playlist(new_playlist, new_index)
            self.queueChanged.emit()
    
    @Property(int)
    def queueLength(self) -> int:
        """Get the number of tracks remaining in queue."""
        playlist = self._player.playlist
        index = self._player.playlist_index
        if not playlist or index < 0:
            return 0
        return max(0, len(playlist) - index - 1)

    # Favorites
    @Slot(int, result=bool)
    def toggleFavorite(self, track_id: int) -> bool:
        """Toggle favorite status."""
        new_status = toggle_favorite(track_id)
        self._track_model.updateFavorite(track_id, new_status)
        return new_status
    
    # Waveform
    @Slot(str)
    def loadWaveform(self, audio_path: str):
        """Load waveform for a track (async)."""
        # Try cache first
        waveform = get_cached_waveform(audio_path)
        if waveform:
            peaks_min = waveform.peaks_min.tolist()
            peaks_max = waveform.peaks_max.tolist()
            self.waveformReady.emit(audio_path, peaks_min, peaks_max)
            return
        
        # Extract in background
        if self._waveform_thread and self._waveform_thread.isRunning():
            return
        
        self._waveform_thread = WaveformThread(audio_path, self)
        self._waveform_thread.finished.connect(
            lambda w: self._on_waveform_ready(audio_path, w)
        )
        self._waveform_thread.start()
    
    def _on_waveform_ready(self, audio_path: str, waveform):
        """Handle waveform extraction complete."""
        if waveform:
            peaks_min = waveform.peaks_min.tolist()
            peaks_max = waveform.peaks_max.tolist()
            self.waveformReady.emit(audio_path, peaks_min, peaks_max)
    
    # Analysis
    @Slot(int, str)
    def analyzeTrack(self, track_id: int, audio_path: str):
        """Analyze track for BPM/Key."""
        if self._analysis_thread and self._analysis_thread.isRunning():
            return
        
        self._analysis_thread = AnalyzerThread(audio_path, track_id, self)
        self._analysis_thread.finished.connect(
            lambda r: self._on_analysis_complete(track_id, r)
        )
        self._analysis_thread.start()
    
    def _on_analysis_complete(self, track_id: int, result):
        """Handle analysis complete."""
        if result and not result.error:
            self.analysisComplete.emit(
                track_id,
                result.bpm or 0,
                result.key or ""
            )
    
    # Metadata
    @Slot(int, float)
    def updateTrackBpm(self, track_id: int, bpm: float):
        """Update track BPM."""
        update_track_metadata(track_id, bpm=bpm)
    
    @Slot(int, str)
    def updateTrackKey(self, track_id: int, key: str):
        """Update track key."""
        update_track_metadata(track_id, key=key)
    
    @Slot(int, str)
    def updateTrackNotes(self, track_id: int, notes: str):
        """Update track notes."""
        update_track_metadata(track_id, notes=notes)
    
    # Tags
    @Slot(int, int)
    def addTagToTrack(self, track_id: int, tag_id: int):
        """Add tag to track."""
        execute(
            "INSERT OR IGNORE INTO track_tags (track_id, tag_id) VALUES (?, ?)",
            (track_id, tag_id)
        )
    
    @Slot(int, int)
    def removeTagFromTrack(self, track_id: int, tag_id: int):
        """Remove tag from track."""
        execute(
            "DELETE FROM track_tags WHERE track_id = ? AND tag_id = ?",
            (track_id, tag_id)
        )
    
    @Slot(int, result=list)
    def getTrackTags(self, track_id: int) -> List[Dict]:
        """Get tags for a track."""
        rows = query("""
            SELECT t.id, t.name, t.color, t.category
            FROM tags t
            JOIN track_tags tt ON t.id = tt.tag_id
            WHERE tt.track_id = ?
        """, (track_id,))
        return [dict(row) for row in rows]
    
    # Playlists
    @Slot(str, result=int)
    def createPlaylist(self, name: str) -> int:
        """Create a new playlist."""
        cur = execute(
            "INSERT INTO playlists (name) VALUES (?)",
            (name,)
        )
        self._load_playlists()
        return cur.lastrowid
    
    @Slot(int, str)
    def renamePlaylist(self, playlist_id: int, name: str):
        """Rename a playlist."""
        execute(
            "UPDATE playlists SET name = ?, updated_at = strftime('%s', 'now') WHERE id = ?",
            (name, playlist_id)
        )
        self._load_playlists()
    
    @Slot(int)
    def deletePlaylist(self, playlist_id: int):
        """Delete a playlist."""
        execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self._load_playlists()
    
    @Slot(int, int)
    def addTrackToPlaylist(self, playlist_id: int, track_id: int):
        """Add track to playlist."""
        # Get max position
        row = query("""
            SELECT MAX(position) as max_pos FROM playlist_tracks
            WHERE playlist_id = ?
        """, (playlist_id,))
        max_pos = row[0]['max_pos'] or 0
        
        execute(
            "INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
            (playlist_id, track_id, max_pos + 1)
        )
        self._load_playlists()
    
    @Slot(int, int)
    def removeTrackFromPlaylist(self, playlist_id: int, track_id: int):
        """Remove track from playlist."""
        execute(
            "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id)
        )
        self._load_playlists()
    
    @Slot(int, result=list)
    def getPlaylistTracks(self, playlist_id: int) -> List[Dict]:
        """Get tracks in a playlist."""
        rows = query("""
            SELECT t.*, p.name as project_name, p.path as project_path, p.flp_path
            FROM tracks t
            JOIN projects p ON t.project_id = p.id
            JOIN playlist_tracks pt ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
        """, (playlist_id,))
        return [dict(row) for row in rows]
    
    # File operations
    @Slot(str)
    def openFile(self, path: str):
        """Open a file."""
        open_file(path)
    
    @Slot(str)
    def openFolder(self, path: str):
        """Open a folder."""
        open_folder(path)
    
    @Slot(str)
    def openFlp(self, path: str):
        """Open FLP in FL Studio."""
        fl_path = get_setting('fl_studio_path', '')
        open_fl_studio(path, fl_path if fl_path else None)
    
    # Project details
    @Slot(int, result='QVariant')
    def getProjectDetails(self, track_id: int) -> Optional[Dict]:
        """Get full project details for a track."""
        track = get_track_by_id(track_id)
        if not track:
            return None
        
        # Count files in subfolders
        details = dict(track)
        
        audio_dir = track.get('audio_dir')
        samples_dir = track.get('samples_dir')
        stems_dir = track.get('stems_dir')
        backup_dir = track.get('backup_dir')
        
        audio_exts = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff'}
        
        details['audio_count'] = count_files_in_folder(audio_dir, audio_exts) if audio_dir else 0
        details['samples_count'] = count_files_in_folder(samples_dir, audio_exts) if samples_dir else 0
        details['stems_count'] = count_files_in_folder(stems_dir, audio_exts) if stems_dir else 0
        details['backup_count'] = count_files_in_folder(backup_dir, {'.flp'}) if backup_dir else 0
        
        details['audio_size'] = format_file_size(get_folder_size(audio_dir)) if audio_dir else '0'
        details['samples_size'] = format_file_size(get_folder_size(samples_dir)) if samples_dir else '0'
        details['stems_size'] = format_file_size(get_folder_size(stems_dir)) if stems_dir else '0'
        
        return details
    
    @Slot(str, result=list)
    def getFilesInFolder(self, folder_path: str) -> List[Dict]:
        """Get audio files in a folder."""
        if not folder_path or not os.path.isdir(folder_path):
            return []
        
        files = []
        audio_exts = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff'}
        
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext in audio_exts:
                        stat = os.stat(item_path)
                        files.append({
                            'name': item,
                            'path': item_path,
                            'size': stat.st_size,
                            'size_formatted': format_file_size(stat.st_size),
                            'mtime': int(stat.st_mtime),
                        })
        except PermissionError:
            pass
        
        return sorted(files, key=lambda f: f['name'].lower())
    
    # Settings
    @Slot(str, result=str)
    def getSetting(self, key: str) -> str:
        """Get a setting value."""
        return get_setting(key, '')
    
    @Slot(str, str)
    def setSetting(self, key: str, value: str):
        """Set a setting value."""
        set_setting(key, value)
    
    # Utilities
    @Slot(float, result=str)
    def formatDuration(self, seconds: float) -> str:
        """Format duration to MM:SS."""
        return format_duration(seconds)
    
    @Slot(int, result=str)
    def formatFileSize(self, size: int) -> str:
        """Format file size."""
        return format_file_size(size)
    
    @Slot(int, result=str)
    def formatTimestamp(self, timestamp: int) -> str:
        """Format timestamp."""
        return format_timestamp(timestamp)
    
    @Slot(float, result=str)
    def formatBpm(self, bpm: float) -> str:
        """Format BPM."""
        return format_bpm(bpm)
    
    @Slot(str, result=str)
    def formatKey(self, key: str) -> str:
        """Format key."""
        return format_key(key)
    
    @Slot(result=list)
    def getAvailableKeys(self) -> List[str]:
        """Get list of available keys."""
        return KEYS
    
    @Slot(result=str)
    def getAppDataPath(self) -> str:
        """Get app data path."""
        return str(get_app_data_path())
    
    def cleanup(self):
        """Cleanup resources."""
        if self._scanner_thread:
            self._scanner_thread.cancel()
        if self._waveform_thread:
            self._waveform_thread.terminate()
        if self._analysis_thread:
            self._analysis_thread.terminate()
        self._player.cleanup()
