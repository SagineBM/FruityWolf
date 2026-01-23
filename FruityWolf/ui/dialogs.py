"""
Dialogs for FL Library Pro
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QDialogButtonBox, QDoubleSpinBox, QComboBox, QFormLayout,
    QTextEdit, QPushButton, QWidget, QScrollArea, QGroupBox,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal

from ..database.tags import get_all_genres, add_tag, get_track_tags
from ..utils.icons import get_icon
from .widgets import FlowLayout, TagChip

class MetadataEditDialog(QDialog):
    """Dialog to edit track metadata."""
    
    def __init__(self, track, parent=None):
        super().__init__(parent)
        self.track = track
        self.setWindowTitle("Edit Metadata")
        self.setMinimumWidth(600)
        self.resize(650, 650)
        
        # Style to fix "dark box" issue and look modern
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f1f5f9; }
            QLabel { color: #94a3b8; font-weight: 500; font-size: 13px; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #334155; 
                border: 1px solid #475569;
                border-radius: 6px;
                color: #f1f5f9;
                padding: 8px;
                selection-background-color: #38bdf8;
                font-size: 13px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border-color: #38bdf8;
                background-color: #1e293b;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 24px;
                font-weight: bold;
                color: #f1f5f9;
                font-size: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: #0f172a; 
            }
            QPushButton#keyBtn {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #94a3b8;
                padding: 6px;
                min-width: 38px;
                font-weight: bold;
            }
            QPushButton#keyBtn:hover {
                background-color: #334155;
                border-color: #475569;
                color: #f1f5f9;
            }
            QPushButton#keyBtn:checked {
                background-color: #38bdf8;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        title_label = QLabel(track.get('title', 'Unknown'))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9; margin-bottom: 8px;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # BPM Section
        bpm_layout = QHBoxLayout()
        bpm_label = QLabel("BPM:")
        self.bpm_spin = QDoubleSpinBox()
        self.bpm_spin.setRange(0, 999)
        self.bpm_spin.setDecimals(1)
        self.bpm_spin.setFixedWidth(100)
        current_bpm = track.get('bpm_user') or track.get('bpm_detected') or 0
        self.bpm_spin.setValue(float(current_bpm))
        bpm_layout.addWidget(bpm_label)
        bpm_layout.addWidget(self.bpm_spin)
        bpm_layout.addStretch()
        layout.addLayout(bpm_layout)
        
        # Key Section (Button Grid)
        self.key_group = QGroupBox("KEY")
        key_layout = QGridLayout(self.key_group)
        key_layout.setSpacing(8)
        key_layout.setContentsMargins(12, 24, 12, 12)
        
        self.key_buttons = []
        self.key_group_btn = None # Currently selected button
        
        keys_major = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        keys_minor = ["Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bm"]
        
        current_key = track.get('key_user') or track.get('key_detected') or ""
        
        # Major Row
        for i, k in enumerate(keys_major):
            btn = QPushButton(k)
            btn.setObjectName("keyBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, b=btn: self._on_key_clicked(b))
            if k == current_key:
                btn.setChecked(True)
                self.key_group_btn = btn
            key_layout.addWidget(btn, 0, i)
            self.key_buttons.append(btn)
            
        # Minor Row
        for i, k in enumerate(keys_minor):
            btn = QPushButton(k)
            btn.setObjectName("keyBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, b=btn: self._on_key_clicked(b))
            if k == current_key:
                btn.setChecked(True)
                self.key_group_btn = btn
            key_layout.addWidget(btn, 1, i)
            self.key_buttons.append(btn)
            
        layout.addWidget(self.key_group)
        
        # Genre Section (Chips)
        self.genre_group = QGroupBox("GENRE & TAGS")
        genre_layout_wrapper = QVBoxLayout(self.genre_group)
        genre_layout_wrapper.setContentsMargins(12, 24, 12, 12)
        genre_layout_wrapper.setSpacing(12)
        
        # Tag Container
        tag_scroll = QScrollArea()
        tag_scroll.setWidgetResizable(True)
        tag_scroll.setStyleSheet("background: transparent; border: none;")
        tag_scroll.setMaximumHeight(150)
        
        tag_container = QWidget()
        tag_container.setStyleSheet("background: transparent;")
        self.tag_layout = FlowLayout(tag_container, margin=0, spacing=8)
        
        # Populate Tags
        self.tag_chips = []
        all_genres = get_all_genres()
        
        # Currently we only store SINGLE genre in simple mode, but let's support selecting one
        # Or ideally store in track_tags. For now we mimic single select or just handle the primary one?
        # User said "select from like button". Let's assume single selection for Genre field compatibility.
        # But we really should use the new track_tags table properly.
        # For this dialog, let's treat it as "Select Primary Genre".
        
        # Fetch existing tags for the track
        current_tags = []
        if 'id' in track:
            tag_rows = get_track_tags(track['id'])
            current_tags = [t['name'] for t in tag_rows]
            
        self.selected_tags = set(current_tags)
        
        for g in all_genres:
            chip = TagChip(g)
            chip.clicked.connect(lambda checked, c=chip: self._on_tag_clicked(c))
            self.tag_layout.addWidget(chip)
            self.tag_chips.append(chip)
            
            if g in self.selected_tags:
                chip.setChecked(True)
            
        tag_scroll.setWidget(tag_container)
        genre_layout_wrapper.addWidget(tag_scroll)
        
        # Add New Tag
        new_tag_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("New Genre...")
        add_btn = QPushButton("+")
        add_btn.clicked.connect(self._add_custom_tag)
        new_tag_layout.addWidget(self.new_tag_input)
        new_tag_layout.addWidget(add_btn)
        genre_layout_wrapper.addLayout(new_tag_layout)
        
        layout.addWidget(self.genre_group)
        
        # Notes
        notes_label = QLabel("Notes:")
        layout.addWidget(notes_label)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setText(track.get('notes') or "")
        layout.addWidget(self.notes_edit)
        
        # Footer buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _on_key_clicked(self, btn):
        if self.key_group_btn and self.key_group_btn != btn:
            self.key_group_btn.setChecked(False)
        self.key_group_btn = btn
        if not btn.isChecked(): # Toggle off
             self.key_group_btn = None
             
    def _on_tag_clicked(self, chip):
        """Toggle tag selection."""
        text = chip.text()
        if chip.isChecked():
            self.selected_tags.add(text)
        else:
            self.selected_tags.discard(text)
            
    def _add_custom_tag(self):
        text = self.new_tag_input.text().strip()
        if text:
            # Add to DB
            add_tag(text, category='genre')
            # Add chip
            chip = TagChip(text)
            chip.clicked.connect(lambda checked, c=chip: self._on_tag_clicked(c))
            self.tag_layout.addWidget(chip)
            # Select it
            chip.setChecked(True)
            self.selected_tags.add(text)
            self.new_tag_input.clear()
            
    def get_data(self):
        """Get updated data."""
        return {
            'bpm': self.bpm_spin.value(),
            'key': self.key_group_btn.text() if self.key_group_btn else "",
            'notes': self.notes_edit.toPlainText(),
            'tags': list(self.selected_tags)
        }
