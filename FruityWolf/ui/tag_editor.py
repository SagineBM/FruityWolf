"""
Tag Editor Dialog

A dialog for editing track tags with:
- Tag chip display for current tags
- Autocomplete input for adding tags
- Category tabs (Mood, Genre, Custom)
- Quick-add popular tags
- Remove with single click
"""

import logging
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QCompleter,
    QSizePolicy, QTabWidget, QGridLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import QColor

from ..database.tags import (
    get_all_tags, get_track_tags, get_track_tag_names,
    get_tags_by_category, search_tags, get_popular_tags,
    add_tag_to_track, remove_tag_from_track, update_track_tags
)
from ..utils import get_icon

logger = logging.getLogger(__name__)


class TagChip(QFrame):
    """A clickable tag chip widget."""
    
    clicked = Signal(str)  # Emits tag name when clicked (for removal)
    
    def __init__(self, name: str, color: str = "#6366f1", removable: bool = True, parent=None):
        super().__init__(parent)
        self.tag_name = name
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Tag name label
        label = QLabel(name)
        label.setStyleSheet("color: white; font-weight: 500;")
        layout.addWidget(label)
        
        # Remove button (×)
        # Remove button
        if removable:
            remove_btn = QPushButton("")
            remove_btn.setIcon(get_icon("trash", QColor("#f1f5f9"), 12))
            remove_btn.setFixedSize(20, 20)
            remove_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: white;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.2);
                }
            """)
            remove_btn.clicked.connect(lambda: self.clicked.emit(self.tag_name))
            layout.addWidget(remove_btn)
        
        # Style the chip
        self.setStyleSheet(f"""
            TagChip {{
                background: {color};
                border-radius: 12px;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tag_name)


class TagChipsContainer(QWidget):
    """Container for displaying multiple tag chips in a flow layout."""
    
    tag_removed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.chips: Dict[str, TagChip] = {}
    
    def set_tags(self, tags: List[Dict]):
        """Set the displayed tags."""
        self.clear()
        for tag in tags:
            self.add_chip(tag['name'], tag.get('color', '#6366f1'))
    
    def add_chip(self, name: str, color: str = "#6366f1"):
        """Add a tag chip."""
        if name in self.chips:
            return
        
        chip = TagChip(name, color)
        chip.clicked.connect(self._on_chip_clicked)
        self.chips[name] = chip
        self.layout.addWidget(chip)
    
    def remove_chip(self, name: str):
        """Remove a tag chip."""
        if name in self.chips:
            chip = self.chips.pop(name)
            self.layout.removeWidget(chip)
            chip.deleteLater()
    
    def clear(self):
        """Remove all chips."""
        for chip in list(self.chips.values()):
            self.layout.removeWidget(chip)
            chip.deleteLater()
        self.chips.clear()
    
    def get_tag_names(self) -> List[str]:
        """Get list of current tag names."""
        return list(self.chips.keys())
    
    def _on_chip_clicked(self, name: str):
        self.remove_chip(name)
        self.tag_removed.emit(name)


class TagEditorDialog(QDialog):
    """
    Dialog for editing tags on a track.
    
    Features:
    - Current tags displayed as removable chips
    - Autocomplete input for adding tags
    - Tabs for Mood, Genre, Custom categories
    - Quick-add from popular/suggested tags
    """
    
    tags_changed = Signal(int, list)  # track_id, new_tags
    
    def __init__(self, track_id: int, track_title: str = "", parent=None):
        super().__init__(parent)
        self.track_id = track_id
        self.setWindowTitle(f"Edit Tags — {track_title}" if track_title else "Edit Tags")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        self._load_tags()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Current Tags")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        layout.addWidget(header)
        
        # Current tags chips
        self.chips_container = TagChipsContainer()
        self.chips_container.tag_removed.connect(self._on_tag_removed)
        
        chips_scroll = QScrollArea()
        chips_scroll.setWidget(self.chips_container)
        chips_scroll.setWidgetResizable(True)
        chips_scroll.setMaximumHeight(80)
        chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #334155;
                border-radius: 8px;
                background: #1e2836;
            }
        """)
        layout.addWidget(chips_scroll)
        
        # Add tag input
        input_layout = QHBoxLayout()
        
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Type to add tag...")
        self.tag_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #334155;
                border-radius: 8px;
                background: #1e2836;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        self.tag_input.returnPressed.connect(self._add_typed_tag)
        
        # Setup autocomplete
        self._setup_completer()
        
        input_layout.addWidget(self.tag_input)
        
        add_btn = QPushButton("Add")
        add_btn.setFixedWidth(60)
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background: #38bdf8;
                color: #0f172a;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #22d3ee;
            }
        """)
        add_btn.clicked.connect(self._add_typed_tag)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        # Category tabs for quick-add
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 8px;
                background: #1e2836;
            }
            QTabBar::tab {
                padding: 8px 16px;
                background: #1e2836;
                color: #94a3b8;
                border: none;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
        """)
        
        # Create tabs for each category
        for category, label in [('mood', 'Mood'), ('genre', 'Genre'), ('custom', 'Custom')]:
            tab = self._create_category_tab(category)
            tabs.addTab(tab, label)
        
        # Popular tags tab
        popular_tab = self._create_popular_tab()
        tabs.addTab(popular_tab, "Popular")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_close)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton[text="Save"] {
                background: #22c55e;
                color: white;
            }
            QPushButton[text="Cancel"] {
                background: #475569;
                color: white;
            }
        """)
        layout.addWidget(button_box)
        
        # Dialog styling
        self.setStyleSheet("""
            TagEditorDialog {
                background: #0f172a;
            }
            QLabel {
                color: #f1f5f9;
            }
        """)
    
    def _setup_completer(self):
        """Setup autocomplete for tag input."""
        all_tags = get_all_tags()
        tag_names = [t['name'] for t in all_tags]
        
        completer = QCompleter(tag_names)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.tag_input.setCompleter(completer)
    
    def _create_category_tab(self, category: str) -> QWidget:
        """Create a tab with buttons for tags in a category."""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(8)
        
        tags = get_all_tags(category)
        for i, tag in enumerate(tags):
            btn = QPushButton(tag['name'])
            btn.setStyleSheet(f"""
                QPushButton {{
                    padding: 6px 12px;
                    background: {tag.get('color', '#6366f1')};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            btn.clicked.connect(lambda checked, n=tag['name']: self._add_tag(n))
            layout.addWidget(btn, i // 4, i % 4)
        
        return widget
    
    def _create_popular_tab(self) -> QWidget:
        """Create a tab with popular/frequently used tags."""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(8)
        
        popular = get_popular_tags(16)
        for i, tag in enumerate(popular):
            btn = QPushButton(f"{tag['name']} ({tag.get('usage_count', 0)})")
            btn.setStyleSheet(f"""
                QPushButton {{
                    padding: 6px 12px;
                    background: {tag.get('color', '#6366f1')};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            btn.clicked.connect(lambda checked, n=tag['name']: self._add_tag(n))
            layout.addWidget(btn, i // 4, i % 4)
        
        return widget
    
    def _load_tags(self):
        """Load current tags for the track."""
        tags = get_track_tags(self.track_id)
        self.chips_container.set_tags(tags)
    
    def _add_typed_tag(self):
        """Add the tag typed in the input field."""
        text = self.tag_input.text().strip()
        if text:
            self._add_tag(text)
            self.tag_input.clear()
    
    def _add_tag(self, name: str):
        """Add a tag to the current selection."""
        # Get tag info for color
        tags = get_all_tags()
        tag_info = next((t for t in tags if t['name'] == name), None)
        color = tag_info['color'] if tag_info else '#6366f1'
        self.chips_container.add_chip(name, color)
    
    def _on_tag_removed(self, name: str):
        """Handle tag removal from chips."""
        logger.debug(f"Tag removed: {name}")
    
    def _save_and_close(self):
        """Save tags and close dialog."""
        new_tags = self.chips_container.get_tag_names()
        update_track_tags(self.track_id, new_tags)
        self.tags_changed.emit(self.track_id, new_tags)
        self.accept()
    
    @staticmethod
    def edit_track_tags(track_id: int, track_title: str = "", parent=None) -> bool:
        """
        Convenience method to show dialog and edit tags.
        Returns True if changes were saved.
        """
        dialog = TagEditorDialog(track_id, track_title, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
