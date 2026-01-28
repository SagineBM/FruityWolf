"""
UI Package

Qt widgets and models for FruityWolf UI.
"""

from .models import (
    TrackListModel,
    PlaylistListModel,
    TagListModel,
    TrackFilterModel,
    TrackRoles,
    PlaylistRoles,
)
from .backend import Backend
from .waveform_widget import WaveformWidget, MiniWaveformWidget
from .widgets import StatusBadge
from .tag_editor import TagEditorDialog, TagChip, TagChipsContainer
from .playlist_dialogs import (
    PlaylistEditDialog, AddToPlaylistMenu, 
    PlaylistTrackList, PlaylistPanel
)
from .project_panel import (
    ProjectDrillDownPanel, ProjectInfoHeader,
    TrackInfoCard, FileTableWidget
)
from .analysis_dialog import AnalysisDialog, BatchAnalysisDialog
from .settings_dialog import SettingsDialog
from .settings_view import SettingsView
from .command_palette import CommandPaletteDialog

__all__ = [
    # Models
    'TrackListModel',
    'PlaylistListModel',
    'TagListModel',
    'TrackFilterModel',
    'TrackRoles',
    'PlaylistRoles',
    # Backend
    'Backend',
    # Widgets
    'WaveformWidget',
    'WaveformWidget',
    'MiniWaveformWidget',
    'StatusBadge',
    # Tag Editor
    'TagEditorDialog',
    'TagChip',
    'TagChipsContainer',
    # Playlist
    'PlaylistEditDialog',
    'AddToPlaylistMenu',
    'PlaylistTrackList',
    'PlaylistPanel',
    # Project Panel
    'ProjectDrillDownPanel',
    'ProjectInfoHeader',
    'TrackInfoCard',
    'FileTableWidget',
    # Analysis
    'AnalysisDialog',
    'BatchAnalysisDialog',
    # Settings
    'SettingsDialog',
    'SettingsView',
    # Command Palette
    'CommandPaletteDialog',
]






