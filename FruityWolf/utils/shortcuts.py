"""
Keyboard Shortcuts Handler

Centralized keyboard shortcut management for FruityWolf.
"""

import logging
from typing import Dict, Callable, Optional

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QAction
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


# =============================================================================
# Default Shortcuts
# =============================================================================

DEFAULT_SHORTCUTS = {
    # Playback
    'play_pause': 'Space',
    'stop': 'Escape',
    'next_track': 'Right',
    'prev_track': 'Left',
    'volume_up': 'Up',
    'volume_down': 'Down',
    'mute': 'M',
    'seek_forward': 'Shift+Right',
    'seek_backward': 'Shift+Left',
    'play_from_start': 'Shift+Return',
    
    # Library
    'search': 'Ctrl+F',
    'search_slash': 'Ctrl+/',  # Quick search (Ctrl+/ avoids typing the character)
    'refresh': 'F5',
    'scan_library': 'Ctrl+Shift+S',
    
    # Track Actions
    'favorite': 'F',
    'tag_editor': 'T',
    'add_to_playlist': 'P',
    'open_project': 'O',
    'open_folder_alt': 'Alt+Return',  # Alt+Enter to open folder
    'open_flp': 'Ctrl+Return',  # Ctrl+Enter to open FLP
    'analyze_bpm': 'B',
    'edit_metadata': 'E',
    
    # Navigation
    'go_library': 'Ctrl+1',
    'go_favorites': 'Ctrl+2',
    'go_playlists': 'Ctrl+3',
    'go_projects': 'Ctrl+4',
    'go_insights': 'Ctrl+5',
    
    # General
    'settings': 'Ctrl+,',
    'quit': 'Ctrl+Q',
    'fullscreen': 'F11',
    'toggle_queue': 'Q',  # Toggle queue panel
    'toggle_details': 'Ctrl+B',  # Toggle details panel
    'command_palette': 'Ctrl+P',  # Command palette
}


# =============================================================================
# Shortcut Manager
# =============================================================================

class ShortcutManager(QObject):
    """
    Manages application keyboard shortcuts.
    
    Allows registering actions and their shortcuts, with customization support.
    """
    
    shortcut_triggered = Signal(str)  # action_name
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.parent_widget = parent
        self._shortcuts: Dict[str, QShortcut] = {}
        self._actions: Dict[str, Callable] = {}
        self._key_sequences: Dict[str, str] = DEFAULT_SHORTCUTS.copy()
    
    def register_shortcut(self, name: str, callback: Callable, 
                         key_sequence: str = None):
        """
        Register a keyboard shortcut.
        
        Args:
            name: Unique action name (e.g., 'play_pause')
            callback: Function to call when shortcut triggered
            key_sequence: Optional custom key sequence (overrides default)
        """
        if key_sequence:
            self._key_sequences[name] = key_sequence
        
        seq = self._key_sequences.get(name)
        if not seq:
            logger.warning(f"No key sequence for shortcut: {name}")
            return
        
        # Create shortcut
        if self.parent_widget:
            shortcut = QShortcut(QKeySequence(seq), self.parent_widget)
            shortcut.activated.connect(lambda: self._on_triggered(name))
            self._shortcuts[name] = shortcut
        
        self._actions[name] = callback
        logger.debug(f"Registered shortcut: {name} -> {seq}")
    
    def _on_triggered(self, name: str):
        """Handle shortcut activation."""
        callback = self._actions.get(name)
        if callback:
            try:
                callback()
            except Exception as e:
                logger.error(f"Shortcut callback error for {name}: {e}")
        self.shortcut_triggered.emit(name)
    
    def update_shortcut(self, name: str, key_sequence: str):
        """Update the key sequence for a shortcut."""
        self._key_sequences[name] = key_sequence
        
        if name in self._shortcuts:
            self._shortcuts[name].setKey(QKeySequence(key_sequence))
    
    def get_shortcut(self, name: str) -> Optional[str]:
        """Get the current key sequence for a shortcut."""
        return self._key_sequences.get(name)
    
    def get_all_shortcuts(self) -> Dict[str, str]:
        """Get all registered shortcuts."""
        return self._key_sequences.copy()
    
    def remove_shortcut(self, name: str):
        """Remove a shortcut."""
        if name in self._shortcuts:
            self._shortcuts[name].setEnabled(False)
            del self._shortcuts[name]
        if name in self._actions:
            del self._actions[name]
    
    def enable(self, name: str):
        """Enable a shortcut."""
        if name in self._shortcuts:
            self._shortcuts[name].setEnabled(True)
    
    def disable(self, name: str):
        """Disable a shortcut."""
        if name in self._shortcuts:
            self._shortcuts[name].setEnabled(False)
    
    def enable_all(self):
        """Enable all shortcuts."""
        for shortcut in self._shortcuts.values():
            shortcut.setEnabled(True)
    
    def disable_all(self):
        """Disable all shortcuts."""
        for shortcut in self._shortcuts.values():
            shortcut.setEnabled(False)


# =============================================================================
# Shortcut Reference
# =============================================================================

SHORTCUT_CATEGORIES = {
    'Playback': [
        ('play_pause', 'Play / Pause'),
        ('stop', 'Stop'),
        ('next_track', 'Next Track'),
        ('prev_track', 'Previous Track'),
        ('volume_up', 'Volume Up'),
        ('volume_down', 'Volume Down'),
        ('mute', 'Mute'),
        ('seek_forward', 'Seek Forward 10s'),
        ('seek_backward', 'Seek Backward 10s'),
    ],
    'Library': [
        ('search', 'Focus Search'),
        ('refresh', 'Refresh View'),
        ('scan_library', 'Scan Library'),
    ],
    'Track Actions': [
        ('favorite', 'Toggle Favorite'),
        ('tag_editor', 'Open Tag Editor'),
        ('add_to_playlist', 'Add to Playlist'),
        ('open_project', 'Open Project Folder'),
        ('analyze_bpm', 'Analyze BPM/Key'),
        ('edit_metadata', 'Edit Metadata'),
    ],
    'Navigation': [
        ('go_library', 'Go to Library'),
        ('go_favorites', 'Go to Favorites'),
        ('go_playlists', 'Go to Playlists'),
        ('go_projects', 'Go to Projects'),
        ('go_insights', 'Go to Insights'),
    ],
    'General': [
        ('settings', 'Open Settings'),
        ('quit', 'Quit Application'),
        ('fullscreen', 'Toggle Fullscreen'),
    ],
}


def format_shortcut_for_display(key_sequence: str) -> str:
    """Format a key sequence for display (e.g., Ctrl+F -> ⌘F on Mac)."""
    # This could be enhanced to use platform-specific symbols
    return key_sequence.replace('Ctrl+', '⌘').replace('Shift+', '⇧').replace('Alt+', '⌥')
