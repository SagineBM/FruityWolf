"""
Settings Dialog

Application settings and preferences UI.
"""

import logging
from typing import Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFormLayout, QSpinBox, QCheckBox,
    QComboBox, QLineEdit, QGroupBox, QDialogButtonBox,
    QFileDialog, QScrollArea, QFrame, QSlider
)
from PySide6.QtCore import Qt, Signal

from ..database import get_setting, set_setting

logger = logging.getLogger(__name__)


# =============================================================================
# Styles
# =============================================================================

DIALOG_STYLE = """
    QDialog {
        background: #0f172a;
    }
    QLabel {
        color: #f1f5f9;
    }
    QTabWidget::pane {
        border: 1px solid #334155;
        border-radius: 8px;
        background: #1e2836;
    }
    QTabBar::tab {
        padding: 10px 20px;
        background: transparent;
        color: #94a3b8;
        border: none;
        border-bottom: 2px solid transparent;
    }
    QTabBar::tab:selected {
        color: #38bdf8;
        border-bottom: 2px solid #38bdf8;
    }
    QGroupBox {
        font-weight: bold;
        color: #f1f5f9;
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 24px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
    }
    QLineEdit, QSpinBox, QComboBox {
        padding: 8px 12px;
        border: 1px solid #334155;
        border-radius: 6px;
        background: #0f172a;
        color: #f1f5f9;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border-color: #38bdf8;
    }
    QCheckBox {
        color: #f1f5f9;
    }
    QSlider::groove:horizontal {
        height: 6px;
        background: #334155;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        width: 16px;
        height: 16px;
        margin: -5px 0;
        background: #38bdf8;
        border-radius: 8px;
    }
    QSlider::sub-page:horizontal {
        background: #38bdf8;
        border-radius: 3px;
    }
"""

BUTTON_STYLE = """
    QPushButton {
        padding: 8px 16px;
        background: #334155;
        color: #f1f5f9;
        border: none;
        border-radius: 6px;
        font-weight: 500;
    }
    QPushButton:hover {
        background: #475569;
    }
"""


# =============================================================================
# Settings Dialog
# =============================================================================

class SettingsDialog(QDialog):
    """
    Application settings dialog.
    
    Tabs:
    - General: Theme, language, startup behavior
    - Playback: Volume, crossfade, auto-play
    - Library: Scan settings, file associations
    - Shortcuts: Keyboard shortcuts (read-only for now)
    """
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(DIALOG_STYLE)
        
        self._settings: Dict[str, Any] = {}
        self._load_settings()
        self._setup_ui()
    
    def _load_settings(self):
        """Load current settings from database."""
        # Handle volume which might be stored as float (0.8) or int (80)
        volume_str = get_setting('volume', '80')
        try:
            volume = float(volume_str)
            if volume <= 1.0:  # It's a decimal, convert to percentage
                volume = int(volume * 100)
            else:
                volume = int(volume)
        except (ValueError, TypeError):
            volume = 80
        
        self._settings = {
            'volume': volume,
            'auto_play': get_setting('auto_play', 'true') == 'true',
            'show_waveform': get_setting('show_waveform', 'true') == 'true',
            'waveform_mini': get_setting('waveform_mini', 'true') == 'true',
            'auto_analyze': get_setting('auto_analyze', 'false') == 'true',
            'scan_on_startup': get_setting('scan_on_startup', 'false') == 'true',
            'watch_folders': get_setting('watch_folders', 'true') == 'true',
            'camelot_notation': get_setting('camelot_notation', 'true') == 'true',
            'fl_studio_path': get_setting('fl_studio_path', ''),
        }
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_playback_tab(), "Playback")
        tabs.addTab(self._create_library_tab(), "Library")
        tabs.addTab(self._create_shortcuts_tab(), "Shortcuts")
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background: #22c55e;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }
        """)
        
        layout.addWidget(button_box)
    
    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        # Theme (future feature)
        theme_combo = QComboBox()
        theme_combo.addItems(["Dark (Default)", "Light", "System"])
        theme_combo.setEnabled(False)  # TODO: Implement themes
        appearance_layout.addRow("Theme:", theme_combo)
        
        # Camelot notation
        self.camelot_check = QCheckBox("Show Camelot notation for keys")
        self.camelot_check.setChecked(self._settings.get('camelot_notation', True))
        appearance_layout.addRow("", self.camelot_check)
        
        layout.addWidget(appearance_group)
        
        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout(behavior_group)
        
        self.scan_startup_check = QCheckBox("Scan library on startup")
        self.scan_startup_check.setChecked(self._settings.get('scan_on_startup', False))
        behavior_layout.addRow("", self.scan_startup_check)
        
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        return widget
    
    def _create_playback_tab(self) -> QWidget:
        """Create playback settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Volume group
        volume_group = QGroupBox("Audio")
        volume_layout = QFormLayout(volume_group)
        
        # Default volume
        volume_row = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self._settings.get('volume', 80))
        self.volume_label = QLabel(f"{self._settings.get('volume', 80)}%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%"))
        volume_row.addWidget(self.volume_slider)
        volume_row.addWidget(self.volume_label)
        volume_layout.addRow("Default Volume:", volume_row)
        
        # Auto-play
        self.auto_play_check = QCheckBox("Start playback when clicking a track")
        self.auto_play_check.setChecked(self._settings.get('auto_play', True))
        volume_layout.addRow("", self.auto_play_check)
        
        layout.addWidget(volume_group)
        
        # Waveform group
        waveform_group = QGroupBox("Waveform")
        waveform_layout = QFormLayout(waveform_group)
        
        self.show_waveform_check = QCheckBox("Show waveform in player")
        self.show_waveform_check.setChecked(self._settings.get('show_waveform', True))
        waveform_layout.addRow("", self.show_waveform_check)
        
        self.mini_waveform_check = QCheckBox("Show mini waveform in player bar")
        self.mini_waveform_check.setChecked(self._settings.get('waveform_mini', True))
        waveform_layout.addRow("", self.mini_waveform_check)
        
        layout.addWidget(waveform_group)
        
        layout.addStretch()
        return widget
    
    def _create_library_tab(self) -> QWidget:
        """Create library settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Paths Group
        paths_group = QGroupBox("Paths")
        paths_layout = QFormLayout(paths_group)
        
        fl_path_layout = QHBoxLayout()
        self.fl_path_edit = QLineEdit(self._settings.get('fl_studio_path', ''))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_fl_path)
        fl_path_layout.addWidget(self.fl_path_edit)
        fl_path_layout.addWidget(browse_btn)
        
        paths_layout.addRow("FL Studio Path:", fl_path_layout)
        layout.addWidget(paths_group)
        
        # Scanning group
        scan_group = QGroupBox("Scanning")
        scan_layout = QFormLayout(scan_group)
        
        self.watch_folders_check = QCheckBox("Watch folders for new files")
        self.watch_folders_check.setChecked(self._settings.get('watch_folders', True))
        scan_layout.addRow("", self.watch_folders_check)
        
        layout.addWidget(scan_group)
        
        # Analysis group
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QFormLayout(analysis_group)
        
        self.auto_analyze_check = QCheckBox("Auto-analyze new tracks (BPM/Key)")
        self.auto_analyze_check.setChecked(self._settings.get('auto_analyze', False))
        analysis_layout.addRow("", self.auto_analyze_check)
        
        analysis_note = QLabel("Note: Auto-analysis requires librosa (optional dependency)")
        analysis_note.setStyleSheet("color: #64748b; font-size: 11px;")
        analysis_layout.addRow("", analysis_note)
        
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        return widget
    
    def _create_shortcuts_tab(self) -> QWidget:
        """Create shortcuts reference tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        
        # Import shortcuts reference
        from ..utils.shortcuts import SHORTCUT_CATEGORIES, DEFAULT_SHORTCUTS
        
        for category, shortcuts in SHORTCUT_CATEGORIES.items():
            group = QGroupBox(category)
            group_layout = QFormLayout(group)
            
            for action_name, display_name in shortcuts:
                key = DEFAULT_SHORTCUTS.get(action_name, '--')
                key_label = QLabel(key)
                key_label.setStyleSheet("""
                    padding: 4px 8px;
                    background: #334155;
                    border-radius: 4px;
                    font-family: monospace;
                """)
                group_layout.addRow(display_name, key_label)
            
            scroll_layout.addWidget(group)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def _browse_fl_path(self):
        """Browse for FL Studio executable."""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select FL Studio Executable", 
            "", 
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            self.fl_path_edit.setText(path)

    def _save(self):
        """Save settings."""
        set_setting('fl_studio_path', self.fl_path_edit.text())
        set_setting('volume', str(self.volume_slider.value()))
        set_setting('auto_play', 'true' if self.auto_play_check.isChecked() else 'false')
        set_setting('show_waveform', 'true' if self.show_waveform_check.isChecked() else 'false')
        set_setting('waveform_mini', 'true' if self.mini_waveform_check.isChecked() else 'false')
        set_setting('auto_analyze', 'true' if self.auto_analyze_check.isChecked() else 'false')
        set_setting('scan_on_startup', 'true' if self.scan_startup_check.isChecked() else 'false')
        set_setting('watch_folders', 'true' if self.watch_folders_check.isChecked() else 'false')
        set_setting('camelot_notation', 'true' if self.camelot_check.isChecked() else 'false')
        
        self.settings_changed.emit()
        self.accept()
    
    @staticmethod
    def show_settings(parent=None) -> bool:
        """Show settings dialog. Returns True if settings were saved."""
        dialog = SettingsDialog(parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
