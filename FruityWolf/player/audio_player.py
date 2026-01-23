"""
Audio Player

Cross-platform audio playback using VLC with fallback to Qt Multimedia.
"""

import os
import logging
from enum import Enum, auto
from typing import Optional, List, Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QUrl, Qt

logger = logging.getLogger(__name__)


def check_vlc_available() -> tuple[bool, str]:
    """
    Check if VLC is available for audio playback.
    
    Returns:
        Tuple of (is_available, message)
    """
    try:
        import vlc
        # Try to create an instance to verify VLC libraries are available
        instance = vlc.Instance(['--quiet'])
        if instance:
            instance.release()
            return True, "VLC is available"
        return False, "VLC library found but failed to initialize"
    except ImportError:
        return False, "python-vlc package not installed. Install with: pip install python-vlc"
    except Exception as e:
        error_msg = str(e)
        if 'VLCRC' in error_msg or 'found' in error_msg.lower():
            return False, "VLC not installed. Please install VLC media player from https://www.videolan.org/"
        return False, f"VLC initialization failed: {error_msg}"


class PlayerState(Enum):
    """Player state enumeration."""
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    LOADING = auto()
    ERROR = auto()


class RepeatMode(Enum):
    """Repeat mode enumeration."""
    NONE = 'none'
    ONE = 'one'
    ALL = 'all'


class AudioPlayer(QObject):
    """
    Audio player with VLC backend.
    
    Signals:
        state_changed(PlayerState): Emitted when player state changes
        position_changed(float): Emitted when playback position changes (0-1)
        duration_changed(float): Emitted when track duration is loaded (seconds)
        track_changed(dict): Emitted when current track changes
        volume_changed(float): Emitted when volume changes (0-1)
        error_occurred(str): Emitted on playback error
    """
    
    # Signals
    state_changed = Signal(object)  # PlayerState
    position_changed = Signal(float)  # 0-1 normalized position
    duration_changed = Signal(float)  # seconds
    track_changed = Signal(object)  # track dict
    volume_changed = Signal(float)  # 0-1
    error_occurred = Signal(str)
    playlist_changed = Signal()
    
    # Internal signals for thread safety
    _sig_vlc_ended = Signal()
    _sig_vlc_error = Signal(str)
    _sig_skip_to_next = Signal()  # For skipping missing files
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._vlc_instance = None
        self._vlc_player = None
        self._use_vlc = False
        
        # State
        self._state = PlayerState.STOPPED
        self._volume = 0.8
        self._shuffle = False
        self._repeat = RepeatMode.NONE
        self._muted = False
        self._mute_volume = 0.8
        
        # Current track
        self._current_track: Optional[dict] = None
        self._duration = 0.0
        
        # Playlist
        self._playlist: List[dict] = []
        self._playlist_index = -1
        self._shuffle_order: List[int] = []
        
        # Position update timer
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(100)  # 10fps position updates
        self._position_timer.timeout.connect(self._update_position)
        
        # Connect internal signals
        self._sig_vlc_ended.connect(self._on_track_end, Qt.ConnectionType.QueuedConnection)
        self._sig_vlc_error.connect(self._handle_vlc_error, Qt.ConnectionType.QueuedConnection)
        self._sig_skip_to_next.connect(self.next, Qt.ConnectionType.QueuedConnection)
        
        # Initialize backend
        self._init_backend()
    
    @property
    def backend_name(self) -> str:
        """Get the name of the active audio backend."""
        if self._use_vlc:
            return "VLC"
        elif hasattr(self, '_qt_player'):
            return "Qt Multimedia"
        return "None"
    
    @property
    def has_backend(self) -> bool:
        """Check if any audio backend is available."""
        return self._use_vlc or hasattr(self, '_qt_player')
    
    def _init_backend(self):
        """Initialize VLC backend."""
        try:
            import vlc
            
            # Create VLC instance with options
            self._vlc_instance = vlc.Instance([
                '--no-xlib',  # Disable X11
                '--quiet',
                '--no-video',  # Audio only
            ])
            self._vlc_player = self._vlc_instance.media_player_new()
            self._use_vlc = True
            
            # Set up event manager
            events = self._vlc_player.event_manager()
            events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
            events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)
            
            logger.info("VLC backend initialized successfully")
            
        except ImportError:
            logger.warning("python-vlc not available, using Qt Multimedia fallback")
            self._init_qt_fallback()
        except Exception as e:
            logger.error(f"Failed to initialize VLC: {e}")
            self._init_qt_fallback()
    
    def _init_qt_fallback(self):
        """Initialize Qt Multimedia fallback."""
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            
            self._qt_player = QMediaPlayer(self)
            self._qt_audio = QAudioOutput(self)
            self._qt_player.setAudioOutput(self._qt_audio)
            
            self._qt_player.positionChanged.connect(self._qt_position_changed)
            self._qt_player.durationChanged.connect(self._qt_duration_changed)
            self._qt_player.playbackStateChanged.connect(self._qt_state_changed)
            self._qt_player.errorOccurred.connect(self._qt_error_occurred)
            
            self._use_vlc = False
            logger.info("Qt Multimedia fallback initialized")
            
        except ImportError:
            logger.error("Neither VLC nor Qt Multimedia available!")
    
    # VLC callbacks
    def _on_end_reached(self, event):
        """Handle track end (called from VLC thread)."""
        self._sig_vlc_ended.emit()
    
    def _on_error(self, event):
        """Handle VLC error (called from VLC thread)."""
        self._sig_vlc_error.emit("Playback error occurred")
        
    def _handle_vlc_error(self, msg):
        """Handle VLC error on main thread."""
        self.error_occurred.emit(msg)
        self._set_state(PlayerState.ERROR)
    
    def _on_track_end(self):
        """Handle track end - play next or stop."""
        if self._repeat == RepeatMode.ONE:
            self.seek(0)
            self.play()
        elif self._playlist_index < len(self._playlist) - 1 or self._repeat == RepeatMode.ALL:
            self.next()
        else:
            self._set_state(PlayerState.STOPPED)
    
    # Qt Multimedia callbacks
    def _qt_position_changed(self, position):
        """Qt position callback."""
        if self._duration > 0:
            normalized = position / 1000.0 / self._duration
            self.position_changed.emit(min(1.0, max(0.0, normalized)))
    
    def _qt_duration_changed(self, duration):
        """Qt duration callback."""
        self._duration = duration / 1000.0
        self.duration_changed.emit(self._duration)
    
    def _qt_state_changed(self, state):
        """Qt state callback."""
        from PySide6.QtMultimedia import QMediaPlayer
        
        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: PlayerState.STOPPED,
            QMediaPlayer.PlaybackState.PlayingState: PlayerState.PLAYING,
            QMediaPlayer.PlaybackState.PausedState: PlayerState.PAUSED,
        }
        self._set_state(state_map.get(state, PlayerState.STOPPED))
    
    def _qt_error_occurred(self, error, message):
        """Qt error callback."""
        self.error_occurred.emit(message)
        self._set_state(PlayerState.ERROR)
    
    def _set_state(self, state: PlayerState):
        """Set player state and emit signal."""
        if self._state != state:
            self._state = state
            self.state_changed.emit(state)
            
            # Start/stop position timer
            if state == PlayerState.PLAYING:
                self._position_timer.start()
            else:
                self._position_timer.stop()
    
    def _update_position(self):
        """Update position from VLC."""
        if not self._use_vlc or not self._vlc_player:
            return
        
        pos = self._vlc_player.get_position()
        if pos >= 0:
            self.position_changed.emit(pos)
    
    # Properties
    @property
    def state(self) -> PlayerState:
        return self._state
    
    @property
    def current_track(self) -> Optional[dict]:
        return self._current_track
    
    @property
    def duration(self) -> float:
        return self._duration
    
    @property
    def position(self) -> float:
        """Get current position (0-1)."""
        if self._use_vlc and self._vlc_player:
            return max(0, self._vlc_player.get_position())
        elif hasattr(self, '_qt_player'):
            if self._duration > 0:
                return self._qt_player.position() / 1000.0 / self._duration
        return 0
    
    @property
    def position_seconds(self) -> float:
        """Get current position in seconds."""
        return self.position * self._duration
    
    @property
    def volume(self) -> float:
        return self._volume
    
    @volume.setter
    def volume(self, value: float):
        value = max(0.0, min(1.0, value))
        self._volume = value
        
        if self._use_vlc and self._vlc_player:
            self._vlc_player.audio_set_volume(int(value * 100))
        elif hasattr(self, '_qt_audio'):
            self._qt_audio.setVolume(value)
        
        self.volume_changed.emit(value)
    
    @property
    def shuffle(self) -> bool:
        return self._shuffle
    
    @shuffle.setter
    def shuffle(self, value: bool):
        self._shuffle = value
        if value:
            self._generate_shuffle_order()
    
    @property
    def repeat(self) -> RepeatMode:
        return self._repeat
    
    @repeat.setter
    def repeat(self, value: RepeatMode):
        self._repeat = value
    
    @property
    def muted(self) -> bool:
        return self._muted
    
    @muted.setter
    def muted(self, value: bool):
        self._muted = value
        if value:
            self._mute_volume = self._volume
            self.volume = 0
        else:
            self.volume = self._mute_volume
    
    @property
    def playlist(self) -> List[dict]:
        return self._playlist
    
    @property
    def playlist_index(self) -> int:
        return self._playlist_index
    
    # Playback control
    @Slot(dict)
    def load_track(self, track: dict):
        """Load and play a track."""
        if not track or 'path' not in track:
            return
        
        path = track['path']
        if not os.path.exists(path):
            error_msg = f"File not found: {os.path.basename(path)}"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            # Auto-skip to next track if available
            if len(self._playlist) > 1:
                self._sig_skip_to_next.emit()
            return
        
        self._current_track = track
        self._set_state(PlayerState.LOADING)
        
        if self._use_vlc and self._vlc_instance:
            import vlc
            media = self._vlc_instance.media_new(path)
            self._vlc_player.set_media(media)
            
            # Parse media to get duration
            media.parse_with_options(vlc.MediaParseFlag.local, 5000)
            
            # Get duration
            duration = self._vlc_player.get_length()
            if duration > 0:
                self._duration = duration / 1000.0
                self.duration_changed.emit(self._duration)
            
            self._vlc_player.play()
            self._vlc_player.audio_set_volume(int(self._volume * 100))
            
        elif hasattr(self, '_qt_player'):
            self._qt_player.setSource(QUrl.fromLocalFile(path))
            self._qt_audio.setVolume(self._volume)
            self._qt_player.play()
        
        self._set_state(PlayerState.PLAYING)
        self.track_changed.emit(track)
    
    @Slot()
    def play(self):
        """Resume playback."""
        if self._state == PlayerState.PAUSED:
            if self._use_vlc and self._vlc_player:
                self._vlc_player.play()
            elif hasattr(self, '_qt_player'):
                self._qt_player.play()
            self._set_state(PlayerState.PLAYING)
        elif self._state == PlayerState.STOPPED and self._current_track:
            self.load_track(self._current_track)
    
    @Slot()
    def pause(self):
        """Pause playback."""
        if self._state == PlayerState.PLAYING:
            if self._use_vlc and self._vlc_player:
                self._vlc_player.pause()
            elif hasattr(self, '_qt_player'):
                self._qt_player.pause()
            self._set_state(PlayerState.PAUSED)
    
    @Slot()
    def toggle_play(self):
        """Toggle play/pause."""
        if self._state == PlayerState.PLAYING:
            self.pause()
        else:
            self.play()
    
    @Slot()
    def stop(self):
        """Stop playback."""
        if self._use_vlc and self._vlc_player:
            self._vlc_player.stop()
        elif hasattr(self, '_qt_player'):
            self._qt_player.stop()
        self._set_state(PlayerState.STOPPED)
    
    @Slot(float)
    def seek(self, position: float):
        """Seek to position (0-1)."""
        position = max(0.0, min(1.0, position))
        
        if self._use_vlc and self._vlc_player:
            self._vlc_player.set_position(position)
        elif hasattr(self, '_qt_player') and self._duration > 0:
            self._qt_player.setPosition(int(position * self._duration * 1000))
        
        self.position_changed.emit(position)
    
    @Slot(float)
    def seek_seconds(self, seconds: float):
        """Seek to position in seconds."""
        if self._duration > 0:
            self.seek(seconds / self._duration)
    
    # Playlist control
    def set_playlist(self, tracks: List[dict], start_index: int = 0):
        """Set playlist and optionally start playing."""
        self._playlist = tracks
        self._playlist_index = -1
        
        if self._shuffle:
            self._generate_shuffle_order()
        
        self.playlist_changed.emit()
        
        if tracks and 0 <= start_index < len(tracks):
            self.play_at_index(start_index)
    
    def _generate_shuffle_order(self):
        """Generate shuffle order."""
        import random
        self._shuffle_order = list(range(len(self._playlist)))
        random.shuffle(self._shuffle_order)
    
    def _get_next_index(self) -> int:
        """Get next track index respecting shuffle."""
        if not self._playlist:
            return -1
        
        if self._shuffle:
            current_shuffle_pos = -1
            if self._playlist_index in self._shuffle_order:
                current_shuffle_pos = self._shuffle_order.index(self._playlist_index)
            
            next_shuffle_pos = (current_shuffle_pos + 1) % len(self._shuffle_order)
            return self._shuffle_order[next_shuffle_pos]
        else:
            return (self._playlist_index + 1) % len(self._playlist)
    
    def _get_prev_index(self) -> int:
        """Get previous track index respecting shuffle."""
        if not self._playlist:
            return -1
        
        if self._shuffle:
            current_shuffle_pos = -1
            if self._playlist_index in self._shuffle_order:
                current_shuffle_pos = self._shuffle_order.index(self._playlist_index)
            
            prev_shuffle_pos = (current_shuffle_pos - 1) % len(self._shuffle_order)
            return self._shuffle_order[prev_shuffle_pos]
        else:
            return (self._playlist_index - 1) % len(self._playlist)
    
    def play_at_index(self, index: int):
        """Play track at playlist index."""
        if 0 <= index < len(self._playlist):
            self._playlist_index = index
            self.load_track(self._playlist[index])
    
    @Slot()
    def next(self):
        """Play next track."""
        if not self._playlist:
            return
        
        next_idx = self._get_next_index()
        if next_idx >= 0:
            self.play_at_index(next_idx)
    
    @Slot()
    def previous(self):
        """Play previous track (or restart if > 3s in)."""
        if self.position_seconds > 3:
            self.seek(0)
        elif self._playlist:
            prev_idx = self._get_prev_index()
            if prev_idx >= 0:
                self.play_at_index(prev_idx)
    
    @Slot()
    def toggle_shuffle(self):
        """Toggle shuffle mode."""
        self.shuffle = not self._shuffle
    
    @Slot()
    def cycle_repeat(self):
        """Cycle through repeat modes."""
        modes = [RepeatMode.NONE, RepeatMode.ONE, RepeatMode.ALL]
        current_idx = modes.index(self._repeat)
        self._repeat = modes[(current_idx + 1) % len(modes)]
    
    @Slot()
    def toggle_mute(self):
        """Toggle mute."""
        self.muted = not self._muted
    
    def cleanup(self):
        """Cleanup resources."""
        self.stop()
        self._position_timer.stop()
        
        if self._vlc_player:
            self._vlc_player.release()
        if self._vlc_instance:
            self._vlc_instance.release()


# Global player instance
_player_instance: Optional[AudioPlayer] = None


def get_player() -> AudioPlayer:
    """Get the global player instance."""
    global _player_instance
    if _player_instance is None:
        _player_instance = AudioPlayer()
    return _player_instance
