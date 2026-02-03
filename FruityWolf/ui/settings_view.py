"""
Settings View
Dedicated page for application settings and preferences.
"""

import logging
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QSpinBox, QCheckBox, QComboBox, QLineEdit,
    QGroupBox, QFileDialog, QScrollArea, QFrame, QSlider,
    QStackedWidget, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QSize, QThread, QTimer
from PySide6.QtGui import QColor, QIcon

from ..database import get_setting, set_setting, query, execute
from ..utils import get_icon
from ..scanner.library_scanner import LibraryScanner
from ..utils.plugin_scanner import add_plugin_root, remove_plugin_root, scan_system_plugins

logger = logging.getLogger(__name__)

class SettingsView(QWidget):
    """
    Application settings page.
    Replaces the modal SettingsDialog with a full-page experience.
    """
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings: Dict[str, Any] = {}
        self._load_settings()
        self._setup_ui()
        
    def _load_settings(self):
        """Load current settings from database."""
        volume_str = get_setting('volume', '80')
        try:
            volume = float(volume_str)
            if volume <= 1.0: volume = int(volume * 100)
            else: volume = int(volume)
        except: volume = 80
        
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
            'library_roots': self._get_library_roots(),
            'plugin_roots': self._get_plugin_roots(),
        }
        
    def _get_library_roots(self) -> List[Dict]:
        """Fetch roots from DB."""
        rows = query("SELECT id, path, name FROM library_roots WHERE enabled = 1")
        return [dict(r) for r in rows]
        
    def _get_plugin_roots(self) -> List[Dict]:
        """Fetch plugin roots from DB."""
        try:
            rows = query("SELECT id, path, name FROM plugin_scan_roots WHERE enabled = 1")
            return [dict(r) for r in rows]
        except:
            return []
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Sidebar for Navigation
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setObjectName("settingsSidebar")
        self.sidebar.setStyleSheet("""
            QWidget#settingsSidebar {
                background-color: rgba(15, 23, 42, 0.5);
                border-right: 1px solid #1e293b;
            }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 24, 12, 12)
        sidebar_layout.setSpacing(4)
        
        title = QLabel("SETTINGS")
        title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; letter-spacing: 1.5px; margin-bottom: 12px; margin-left: 8px;")
        sidebar_layout.addWidget(title)
        
        self._nav_list = QListWidget()
        self._nav_list.setIconSize(QSize(18, 18))
        self._nav_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                color: #94a3b8;
                font-weight: 500;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background: rgba(56, 189, 248, 0.05);
                color: #f1f5f9;
            }
            QListWidget::item:selected {
                background: rgba(56, 189, 248, 0.1);
                color: #38bdf8;
            }
        """)
        
        items = [
            ("General", "settings"),
            ("Playback", "play"),
            ("Library", "folder"),
            ("Shortcuts", "keyboard")
        ]
        
        for text, icon in items:
            item = QListWidgetItem(get_icon(icon, QColor("#94a3b8"), 18), text)
            self._nav_list.addItem(item)
            
        self._nav_list.setCurrentRow(0)
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self._nav_list)
        sidebar_layout.addStretch()
        
        layout.addWidget(self.sidebar)
        
        # 2. Main Content Stack
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_general_page())
        self.stack.addWidget(self._create_playback_page())
        self.stack.addWidget(self._create_library_page())
        self.stack.addWidget(self._create_shortcuts_page())
        
        layout.addWidget(self.stack, 1)
        
    def _create_page_container(self, title_text: str) -> tuple[QWidget, QVBoxLayout]:
        """Helper to create a standard settings page layout."""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #f1f5f9; margin-bottom: 8px;")
        layout.addWidget(title)
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        return page, layout

    def _create_general_page(self) -> QWidget:
        page, layout = self._create_page_container("General")
        
        # Appearance Group
        group = self._create_group("Appearance")
        form = QFormLayout(group)
        
        self.camelot_check = self._add_checkbox("Show Camelot notation for keys", 'camelot_notation', form)
        layout.addWidget(group)
        
        # Behavior Group
        group = self._create_group("Behavior")
        form = QFormLayout(group)
        
        self.scan_startup_check = self._add_checkbox("Scan library on startup", 'scan_on_startup', form)
        layout.addWidget(group)
        
        return page

    def _create_playback_page(self) -> QWidget:
        page, layout = self._create_page_container("Playback")
        
        # Audio Group
        group = self._create_group("Audio")
        form = QFormLayout(group)
        
        # Volume
        vol_widget = QWidget()
        vol_layout = QHBoxLayout(vol_widget)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self._settings['volume'])
        self.volume_label = QLabel(f"{self._settings['volume']}%")
        self.volume_label.setFixedWidth(40)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        vol_layout.addWidget(self.volume_slider)
        vol_layout.addWidget(self.volume_label)
        form.addRow("Default Volume", vol_widget)
        
        self.auto_play_check = self._add_checkbox("Start playback on click", 'auto_play', form)
        layout.addWidget(group)
        
        # Visuals Group
        group = self._create_group("Visuals")
        form = QFormLayout(group)
        self.show_waveform_check = self._add_checkbox("Show waveform in player", 'show_waveform', form)
        self.mini_waveform_check = self._add_checkbox("Show mini waveform in player bar", 'waveform_mini', form)
        layout.addWidget(group)
        
        return page

    def _create_library_page(self) -> QWidget:
        page, layout = self._create_page_container("Library")
        
        # Paths Group
        group = self._create_group("Paths")
        form = QFormLayout(group)
        
        fl_widget = QWidget()
        fl_layout = QHBoxLayout(fl_widget)
        fl_layout.setContentsMargins(0, 0, 0, 0)
        self.fl_path_edit = QLineEdit(self._settings['fl_studio_path'])
        self.fl_path_edit.textChanged.connect(lambda t: self._save_setting('fl_studio_path', t))
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_fl_path)
        fl_layout.addWidget(self.fl_path_edit)
        fl_layout.addWidget(btn_browse)
        form.addRow("FL Studio Path", fl_widget)
        
        layout.addWidget(group)
        
        # Library Folders Group
        self.library_group = self._create_library_folder_group()
        layout.addWidget(self.library_group)
        
        # Plugin Folders Group
        self.plugin_group = self._create_plugin_folder_group()
        layout.addWidget(self.plugin_group)
        
        # Render Subfolders Group
        self.render_subfolders_group = self._create_render_subfolders_group()
        layout.addWidget(self.render_subfolders_group)
        
        # Automation Group
        group = self._create_group("Automation")
        form = QFormLayout(group)
        self.watch_folders_check = self._add_checkbox("Watch folders for new files (Real-time)", 'watch_folders', form)
        self.auto_analyze_check = self._add_checkbox("Auto-analyze new tracks (BPM/Key)", 'auto_analyze', form)
        
        layout.addWidget(group)
        
        return page

    def _create_shortcuts_page(self) -> QWidget:
        page, layout = self._create_page_container("Shortcuts")
        
        from ..utils.shortcuts import SHORTCUT_CATEGORIES, DEFAULT_SHORTCUTS
        
        for category, shortcuts in SHORTCUT_CATEGORIES.items():
            group = self._create_group(category)
            form = QFormLayout(group)
            
            for action_name, display_name in shortcuts:
                key = DEFAULT_SHORTCUTS.get(action_name, '--')
                key_label = QLabel(key)
                key_label.setStyleSheet("color: #38bdf8; font-family: monospace; font-weight: bold;")
                form.addRow(display_name, key_label)
            
            layout.addWidget(group)
            
        return page

    def _create_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #f1f5f9;
                border: 1px solid #1e293b;
                border-radius: 12px;
                margin-top: 12px;
                padding: 24px;
                background-color: rgba(30, 41, 59, 0.2);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
            QLabel { color: #94a3b8; font-weight: normal; }
            QCheckBox { color: #e2e8f0; spacing: 8px; }
            QLineEdit {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f1f5f9;
            }
        """)
        return group

    def _create_library_folder_group(self) -> QGroupBox:
        """Create the multi-folder management group."""
        group = self._create_group("Library Folders")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(24, 32, 24, 24)
        
        desc = QLabel("FruityWolf monitors these folders for FL Studio projects and audio renders.")
        desc.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(desc)
        
        # Folder List
        self.folder_list_layout = QVBoxLayout()
        self.folder_list_layout.setSpacing(8)
        layout.addLayout(self.folder_list_layout)
        
        self._refresh_folder_list()
        
        # Add Button
        add_btn = QPushButton(" Add Library Folder")
        add_btn.setIcon(get_icon("plus", QColor("#0f172a"), 16))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #38bdf8;
                color: #0f172a;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 700;
                margin-top: 12px;
            }
            QPushButton:hover { background: #7dd3fc; }
        """)
        add_btn.clicked.connect(self._add_folder)
        layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignLeft)
        
        return group

    def _refresh_folder_list(self):
        """Re-render the folder entries."""
        # Clear existing
        while self.folder_list_layout.count():
            item = self.folder_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        roots = self._get_library_roots()
        if not roots:
             lbl = QLabel("No folders added yet.")
             lbl.setStyleSheet("color: #475569; font-style: italic;")
             self.folder_list_layout.addWidget(lbl)
             return
             
        for root in roots:
            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background: #0f172a;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)
            
            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon("folder", QColor("#38bdf8"), 20).pixmap(20, 20))
            row_layout.addWidget(icon_lbl)
            
            path_lbl = QLabel(root['path'])
            path_lbl.setStyleSheet("color: #f1f5f9; font-weight: 500;")
            row_layout.addWidget(path_lbl, 1)
            
            remove_btn = QPushButton()
            remove_btn.setFixedSize(32, 32)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setIcon(get_icon("trash", QColor("#ef4444"), 16))
            remove_btn.setToolTip("Remove Folder")
            remove_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 4px; }
                QPushButton:hover { background: rgba(239, 68, 68, 0.1); }
            """)
            remove_btn.clicked.connect(lambda checked=False, p=root['path']: self._remove_folder(p))
            row_layout.addWidget(remove_btn)
            
            self.folder_list_layout.addWidget(row)

    def _add_folder(self):
        """Open dialog and add a folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Library Folder")
        if path:
            scanner = LibraryScanner()
            if scanner.add_library_root(path):
                self._refresh_folder_list()
                self.settings_changed.emit()
            
    def _remove_folder(self, path: str):
        """Remove a folder root."""
        scanner = LibraryScanner()
        scanner.remove_library_root(path)
        self._refresh_folder_list()
        self.settings_changed.emit()

    def _create_plugin_folder_group(self) -> QGroupBox:
        """Create the plugin folder management group."""
        group = self._create_group("Plugin Scan Folders")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(24, 32, 24, 24)
        
        desc = QLabel("Add custom folders for VST plugins and Kontakt libraries to be included in system scans.")
        desc.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(desc)
        
        # Folder List
        self.plugin_folder_list_layout = QVBoxLayout()
        self.plugin_folder_list_layout.setSpacing(8)
        layout.addLayout(self.plugin_folder_list_layout)
        
        self._refresh_plugin_folder_list()
        
        # Add Button
        add_btn = QPushButton(" Add Plugin Folder")
        add_btn.setIcon(get_icon("plus", QColor("#0f172a"), 16))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #a78bfa;
                color: #0f172a;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 700;
                margin-top: 12px;
            }
            QPushButton:hover { background: #c4b5fd; }
        """)
        add_btn.clicked.connect(self._add_plugin_folder)
        layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Scan Now Button
        self.scan_plugins_btn = QPushButton(" Scan Plugins Now")
        self.scan_plugins_btn.setIcon(get_icon("analyze", QColor("#f1f5f9"), 16))
        self.scan_plugins_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_plugins_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #f1f5f9;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
                margin-top: 8px;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.scan_plugins_btn.clicked.connect(self._scan_plugins)
        layout.addWidget(self.scan_plugins_btn, 0, Qt.AlignmentFlag.AlignLeft)
        
        return group
    
    def _create_render_subfolders_group(self) -> QGroupBox:
        """Create the render subfolders configuration group."""
        group = self._create_group("Render Subfolders (Optional)")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(24, 32, 24, 24)
        
        desc = QLabel("By default, only root-level audio files are treated as renders. You can optionally allow specific subfolders (e.g., Render, Renders, Exports) to also be treated as renders. Audio files in Audio/, Samples/, and Backup/ are never treated as renders.")
        desc.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        self.render_subfolders_input = QLineEdit()
        self.render_subfolders_input.setPlaceholderText("Render, Renders, Exports, Bounces, Mixdowns")
        render_subfolders_value = get_setting('render_subfolders_allowed', '')
        self.render_subfolders_input.setText(render_subfolders_value)
        self.render_subfolders_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 10px 12px;
                color: #f1f5f9;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.render_subfolders_input.textChanged.connect(
            lambda: self._save_setting('render_subfolders_allowed', self.render_subfolders_input.text())
        )
        layout.addWidget(self.render_subfolders_input)
        
        hint = QLabel("Comma-separated list of folder names. Leave empty to only use root-level renders.")
        hint.setStyleSheet("color: #475569; font-size: 11px; font-style: italic; margin-top: 4px;")
        layout.addWidget(hint)
        
        return group

    def _scan_plugins(self):
        """Trigger a plugin scan in a background thread so the UI never freezes."""
        self.scan_plugins_btn.setEnabled(False)
        self.scan_plugins_btn.setText(" Scanning...")

        class PluginScanThread(QThread):
            finished_count = Signal(int)

            def run(self):
                try:
                    count = scan_system_plugins()
                    self.finished_count.emit(count)
                except Exception as e:
                    logger.error("Plugin scan failed: %s", e, exc_info=True)
                    self.finished_count.emit(-1)

        self._plugin_scan_thread = PluginScanThread(self)
        self._plugin_scan_thread.finished_count.connect(self._on_plugin_scan_finished)
        self._plugin_scan_thread.finished.connect(self._plugin_scan_thread.deleteLater)
        self._plugin_scan_thread.start()

    def _on_plugin_scan_finished(self, count: int):
        if count >= 0:
            self.scan_plugins_btn.setText(f" Scan Complete ({count} found)")
        else:
            self.scan_plugins_btn.setText(" Scan Failed")
        QTimer.singleShot(3000, lambda: self.scan_plugins_btn.setText(" Scan Plugins Now"))
        QTimer.singleShot(3000, lambda: self.scan_plugins_btn.setEnabled(True))
        self._plugin_scan_thread = None

    def _refresh_plugin_folder_list(self):
        """Re-render the plugin folder entries."""
        # Clear existing
        while self.plugin_folder_list_layout.count():
            item = self.plugin_folder_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        roots = self._get_plugin_roots()
        if not roots:
             lbl = QLabel("No custom plugin folders added yet.")
             lbl.setStyleSheet("color: #475569; font-style: italic;")
             self.plugin_folder_list_layout.addWidget(lbl)
             return
             
        for root in roots:
            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background: #0f172a;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)
            
            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon("folder", QColor("#a78bfa"), 20).pixmap(20, 20))
            row_layout.addWidget(icon_lbl)
            
            path_lbl = QLabel(root['path'])
            path_lbl.setStyleSheet("color: #f1f5f9; font-weight: 500;")
            row_layout.addWidget(path_lbl, 1)
            
            remove_btn = QPushButton()
            remove_btn.setFixedSize(32, 32)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setIcon(get_icon("trash", QColor("#ef4444"), 16))
            remove_btn.setToolTip("Remove Folder")
            remove_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 4px; }
                QPushButton:hover { background: rgba(239, 68, 68, 0.1); }
            """)
            remove_btn.clicked.connect(lambda checked=False, p=root['path']: self._remove_plugin_folder(p))
            row_layout.addWidget(remove_btn)
            
            self.plugin_folder_list_layout.addWidget(row)

    def _add_plugin_folder(self):
        """Open dialog and add a plugin folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Plugin/Library Folder")
        if path:
            if add_plugin_root(path):
                self._refresh_plugin_folder_list()
                self.settings_changed.emit()
            
    def _remove_plugin_folder(self, path: str):
        """Remove a plugin root."""
        remove_plugin_root(path)
        self._refresh_plugin_folder_list()
        self.settings_changed.emit()

    def _add_checkbox(self, text: str, setting_key: str, layout: QFormLayout) -> QCheckBox:
        cb = QCheckBox(text)
        cb.setChecked(self._settings.get(setting_key, False))
        cb.toggled.connect(lambda v: self._save_setting(setting_key, v))
        layout.addRow("", cb)
        return cb

    def _on_nav_changed(self, row):
        self.stack.setCurrentIndex(row)
        
    def _on_volume_changed(self, value):
        self.volume_label.setText(f"{value}%")
        self._save_setting('volume', str(value))
        
    def _browse_fl_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select FL Studio Executable (FL64.exe)", 
            "", 
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            self.fl_path_edit.setText(path)
            self._save_setting('fl_studio_path', path)
            
    def _save_setting(self, key: str, value: Any):
        """Save to DB and notify."""
        val_str = 'true' if value is True else 'false' if value is False else str(value)
        set_setting(key, val_str)
        self._settings[key] = value
        self.settings_changed.emit()
        
    def refresh(self):
        """Called when page is shown."""
        self._load_settings()
        # Update UI if needed, though signals handle most
