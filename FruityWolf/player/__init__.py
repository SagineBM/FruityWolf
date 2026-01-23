"""
Player Package

Audio playback with VLC backend and Qt Multimedia fallback.
"""

from .audio_player import (
    AudioPlayer,
    PlayerState,
    RepeatMode,
    get_player,
    check_vlc_available,
)

__all__ = [
    'AudioPlayer',
    'PlayerState',
    'RepeatMode',
    'get_player',
    'check_vlc_available',
]

