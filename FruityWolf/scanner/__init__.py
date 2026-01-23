"""
Scanner Package
"""

from .library_scanner import (
    LibraryScanner,
    ScannerThread,
    ScanResult,
    get_all_tracks,
    get_favorite_tracks,
    search_tracks,
    toggle_favorite,
    get_track_by_id,
    update_track_metadata,
    get_recently_added_tracks,
    get_missing_metadata_tracks,
    AUDIO_EXTENSIONS,
)
from .playlist_manager import (
    create_playlist,
    get_playlist,
    get_all_playlists,
    update_playlist,
    delete_playlist,
    add_track_to_playlist,
    remove_track_from_playlist,
    get_playlist_tracks,
    reorder_playlist_track,
    export_playlist_m3u,
    generate_playlist_cover,
)
from .file_watcher import (
    FileWatcher,
    WatcherThread,
)

__all__ = [
    # Scanner
    'LibraryScanner',
    'ScannerThread',
    'ScanResult',
    'get_all_tracks',
    'get_favorite_tracks',
    'search_tracks',
    'toggle_favorite',
    'get_track_by_id',
    'update_track_metadata',
    'get_recently_added_tracks',
    'get_missing_metadata_tracks',
    'AUDIO_EXTENSIONS',
    
    # Playlists
    'create_playlist',
    'get_playlist',
    'get_all_playlists',
    'update_playlist',
    'delete_playlist',
    'add_track_to_playlist',
    'remove_track_from_playlist',
    'get_playlist_tracks',
    'reorder_playlist_track',
    'export_playlist_m3u',
    'generate_playlist_cover',
    
    # File Watcher
    'FileWatcher',
    'WatcherThread',
]
