"""
Project Details Panel

Displays detailed information for FL Studio Projects (Projects View).
Phase 1: Added Next Action CTA, Project Memory, Debug Mode.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QGroupBox, QProgressBar, QTextEdit,
    QLineEdit, QComboBox, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPixmap

from ...utils import get_icon, format_smart_date, get_placeholder_cover, get_cover_art
from ...utils.image_manager import get_image_manager
from ...classifier.engine import ProjectState
from ...database import execute, query_one

logger = logging.getLogger(__name__)

class ProjectDetailsPanel(QWidget):
    """Side panel for displaying Project details."""
    
    open_folder_clicked = Signal(str)
    open_flp_clicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project = None
        self.image_manager = get_image_manager()
        self.image_manager.image_loaded.connect(self._on_image_loaded)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("QWidget { background: transparent; }")
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("QWidget { background: transparent; }")
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
        # 1. HEADER (Cover + Title)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #1e293b;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.title_label = QLabel("Select a project")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)
        
        self.date_label = QLabel("")
        self.date_label.setStyleSheet("font-size: 13px; color: #64748b;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.date_label)
        
        # 2. STATUS (State + Score)
        self.status_group = QGroupBox("STATUS")
        self.status_layout = QVBoxLayout(self.status_group)
        self.status_layout.setSpacing(12)
        
        self.state_label = QLabel("Unknown")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setFixedHeight(28)
        self.status_layout.addWidget(self.state_label)
        
        # Score
        score_row = QHBoxLayout()
        score_lbl = QLabel("Completion")
        score_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        score_row.addWidget(score_lbl)
        
        self.score_val = QLabel("0%")
        self.score_val.setStyleSheet("color: #f1f5f9; font-weight: bold;")
        score_row.addWidget(self.score_val)
        score_row.addStretch()
        self.status_layout.addLayout(score_row)
        
        self.score_bar = QProgressBar()
        self.score_bar.setTextVisible(False)
        self.score_bar.setFixedHeight(6)
        self.status_layout.addWidget(self.score_bar)
        
        self.main_layout.addWidget(self.status_group)
        
        # 3. NEXT ACTION CTA
        self.cta_frame = QFrame()
        self.cta_frame.setObjectName("ctaFrame")
        self.cta_frame.setStyleSheet("""
            #ctaFrame {
                background-color: #1e293b;
                border: 1px solid #38bdf8;
                border-radius: 8px;
            }
        """)
        cta_layout = QVBoxLayout(self.cta_frame)
        
        lbl_next = QLabel("SUGGESTED NEXT STEP")
        lbl_next.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        cta_layout.addWidget(lbl_next)
        
        self.action_label = QLabel("Open Project")
        self.action_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.action_label.setWordWrap(True)
        cta_layout.addWidget(self.action_label)
        
        self.btn_do_action = QPushButton("Do It")
        self.btn_do_action.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #7dd3fc; }
        """)
        self.btn_do_action.clicked.connect(self._on_open_flp) # Default logic
        cta_layout.addWidget(self.btn_do_action)
        
        self.main_layout.addWidget(self.cta_frame)
        
        # 4. PROJECT MEMORY
        self.memory_group = QGroupBox("PROJECT MEMORY")
        mem_layout = QVBoxLayout(self.memory_group)
        mem_layout.setSpacing(12)
        
        # Vision
        mem_layout.addWidget(QLabel("Creative Vision", objectName="formLabel"))
        self.txt_vision = QTextEdit()
        self.txt_vision.setPlaceholderText("What is the goal of this track?")
        self.txt_vision.setFixedHeight(60)
        self.txt_vision.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; color: #e2e8f0;")
        mem_layout.addWidget(self.txt_vision)
        
        # Moods
        mem_layout.addWidget(QLabel("Moods (comma separated)", objectName="formLabel"))
        self.inp_moods = QLineEdit()
        self.inp_moods.setPlaceholderText("Dark, Energetic, Trap...")
        self.inp_moods.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; color: #e2e8f0; padding: 4px;")
        mem_layout.addWidget(self.inp_moods)
        
        # Energy
        mem_layout.addWidget(QLabel("Energy Level", objectName="formLabel"))
        self.combo_energy = QComboBox()
        self.combo_energy.addItems(["Low", "Medium", "High", "Extreme"])
        self.combo_energy.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; color: #e2e8f0; padding: 4px;")
        mem_layout.addWidget(self.combo_energy)
        
        # Todo
        mem_layout.addWidget(QLabel("Producer Checklist (one per line)", objectName="formLabel"))
        self.txt_todo = QTextEdit()
        self.txt_todo.setPlaceholderText("- Fix kick drum\n- Record vocals")
        self.txt_todo.setFixedHeight(80)
        self.txt_todo.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; color: #e2e8f0;")
        mem_layout.addWidget(self.txt_todo)
        
        self.btn_save_mem = QPushButton("Save Memory")
        self.btn_save_mem.clicked.connect(self._save_memory)
        self.btn_save_mem.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        mem_layout.addWidget(self.btn_save_mem)
        
        self.main_layout.addWidget(self.memory_group)

        # 5. CONTENT STATS
        self.stats_group = QGroupBox("CONTENTS")
        self.stats_layout = QGridLayout(self.stats_group)
        self.audio_count_label = self._add_stat("Audio Files", 0, 0)
        self.backup_count_label = self._add_stat("Backups", 0, 1)
        self.size_label = self._add_stat("Size", 1, 0)
        self.main_layout.addWidget(self.stats_group)
        
        # 6. ACTIONS (Folder/FLP)
        self.actions_layout = QVBoxLayout()
        self.btn_folder = QPushButton(" Open Folder")
        self.btn_folder.setIcon(get_icon("folder_open", QColor("#94a3b8"), 16))
        self.btn_folder.clicked.connect(self._on_open_folder)
        self.actions_layout.addWidget(self.btn_folder)
        
        self.btn_flp = QPushButton(" Open FLP")
        self.btn_flp.setIcon(get_icon("fl_studio", QColor("#94a3b8"), 16))
        self.btn_flp.clicked.connect(self._on_open_flp)
        self.actions_layout.addWidget(self.btn_flp)
        self.main_layout.addLayout(self.actions_layout)
        
        # 7. DEBUG
        self.chk_debug = QCheckBox("Debug Mode")
        self.chk_debug.setStyleSheet("color: #64748b; font-size: 11px;")
        self.chk_debug.toggled.connect(self._toggle_debug)
        self.main_layout.addWidget(self.chk_debug)
        
        self.debug_info = QTextEdit()
        self.debug_info.setReadOnly(True)
        self.debug_info.setVisible(False)
        self.debug_info.setFixedHeight(120)
        self.debug_info.setStyleSheet("background-color: #0f172a; color: #bef264; font-family: Consolas; font-size: 10px;")
        self.main_layout.addWidget(self.debug_info)
        
        self.main_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        # Styles
        self.setStyleSheet("""
            QGroupBox {
                color: #94a3b8;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #334155;
                border-radius: 6px;
                margin-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel#formLabel {
                color: #94a3b8;
                font-size: 11px;
                margin-top: 4px;
            }
        """)
        
    def set_project(self, project: dict):
        self.current_project = project
        if not project:
            self.clear()
            return
            
        # Basic Info
        # Cover - Async
        path = project.get('path')
        self.current_cover_path = get_cover_art(path)
        
        if self.current_cover_path:
            pix = self.image_manager.get_image(self.current_cover_path, 200)
            if pix:
                self.cover_label.setPixmap(pix)
            else:
                self.cover_label.setPixmap(get_placeholder_cover(200, project.get('name', ''), is_project=True))
        else:
            self.cover_label.setPixmap(get_placeholder_cover(200, project.get('name', ''), is_project=True))
        self.title_label.setText(project.get('name', 'Unknown'))
        self.date_label.setText(format_smart_date(project.get('updated_at', 0)))
        
        # State
        state = project.get('state_id') or project.get('state') or 'Unknown'
        self.state_label.setText(state.replace("_", " ").title().replace("Or", "/"))
        self.state_label.setStyleSheet(f"""
            background-color: {self._get_state_color_hex(state)}33; 
            color: {self._get_state_color_hex(state)}; 
            border-radius: 12px; 
            padding: 4px 12px;
            font-weight: bold;
            border: 1px solid {self._get_state_color_hex(state)}66;
        """)
        
        # Score
        score = project.get('score') or project.get('render_priority_score') or 0
        self.score_val.setText(f"{score}%")
        self.score_bar.setValue(score)
        
        # Next Action
        next_action = project.get('next_action_id', '')
        self.action_label.setText(ProjectState.format_action_id(next_action) or "Open Project")
        
        # Memory
        meta_json = project.get('user_meta')
        meta = json.loads(meta_json) if meta_json else {}
        
        self.txt_vision.setText(meta.get('vision', ''))
        self.inp_moods.setText(meta.get('moods', ''))
        
        idx = self.combo_energy.findText(meta.get('energy', 'Medium'))
        if idx >= 0: self.combo_energy.setCurrentIndex(idx)
        
        todo_list = meta.get('todo', [])
        if isinstance(todo_list, list):
            self.txt_todo.setText("\n".join(todo_list))
        else:
            self.txt_todo.setText(str(todo_list))
            
        # Stats
        self.size_label.setText(f"{project.get('flp_size_kb', 0)} KB")
        self.audio_count_label.setText(str(project.get('audio_folder_count', '-')))
        self.backup_count_label.setText(str(project.get('backup_count', '-')))
        
        # Debug
        if self.chk_debug.isChecked():
            self._update_debug_info()
            
        # Buttons
        flp_path = project.get('flp_path')
        has_flp = bool(flp_path) and os.path.exists(flp_path)
        self.btn_flp.setEnabled(has_flp)
        self.btn_folder.setEnabled(bool(project.get('path')))

    def _save_memory(self):
        if not self.current_project: return
        
        # Build JSON
        meta = {
            "vision": self.txt_vision.toPlainText(),
            "moods": self.inp_moods.text(),
            "energy": self.combo_energy.currentText(),
            "todo": [line for line in self.txt_todo.toPlainText().split('\n') if line.strip()]
        }
        
        # Save to DB (Synchronous for now for UI panel simplicity, or use Backend slot if available)
        # Using helper method
        try:
            new_json = json.dumps(meta)
            pid = self.current_project['id']
            execute(
                "UPDATE projects SET user_meta = ?, updated_at = strftime('%s', 'now') WHERE id = ?",
                (new_json, pid)
            )
            # Update local object
            self.current_project['user_meta'] = new_json
            # Feedback?
            self.btn_save_mem.setText("Saved!")
            QTimer.singleShot(1000, lambda: self.btn_save_mem.setText("Save Memory"))
        except Exception as e:
            logger.error(f"Failed to save meta: {e}")
            self.btn_save_mem.setText("Error")

    def _toggle_debug(self, checked):
        self.debug_info.setVisible(checked)
        if checked:
            self._update_debug_info()
            
    def _update_debug_info(self):
        if not self.current_project: return
        p = self.current_project
        info = f"ID: {p.get('id')}\n"
        info += f"Path: {p.get('path')}\n"
        info += f"State Reasons: {p.get('state_reason')}\n"
        info += f"Score Breakdown: {p.get('score_breakdown')}\n"
        info += f"Signals: {str(p.get('signals'))[:200]}..." 
        self.debug_info.setText(info)

    def _add_stat(self, label, row, col):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        vbox.addWidget(lbl)
        val = QLabel("0")
        val.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: 500;")
        vbox.addWidget(val)
        self.stats_layout.addWidget(container, row, col)
        return val

    def clear(self):
        self.current_project = None
        self.title_label.setText("Select a project")
        self.date_label.setText("")
        self.state_label.setText("Unknown")
        self.score_val.setText("0%")
        self.score_bar.setValue(0)
        self.txt_vision.clear()
        self.txt_todo.clear()
        self.inp_moods.clear()
        
    def _get_state_color_hex(self, state: str) -> str:
        map_ = {
            ProjectState.MICRO_IDEA: "#94a3b8",
            ProjectState.IDEA: "#38bdf8",
            ProjectState.WIP: "#f59e0b",
            ProjectState.PREVIEW_READY: "#22c55e",
            ProjectState.ADVANCED: "#a855f7",
            ProjectState.BROKEN_OR_EMPTY: "#ef4444",
        }
        return map_.get(state, "#f1f5f9")
    
    def _on_open_folder(self):
        if self.current_project and self.current_project.get('path'):
            self.open_folder_clicked.emit(self.current_project.get('path'))

    def _on_open_flp(self):
        if self.current_project and self.current_project.get('flp_path'):
            self.open_flp_clicked.emit(self.current_project.get('flp_path'))

    def _on_image_loaded(self, path: str, pixmap: QPixmap):
        """Update cover if it matches current project."""
        if hasattr(self, 'current_cover_path') and path == self.current_cover_path:
            if not pixmap.isNull():
                self.cover_label.setPixmap(pixmap)

# Missing imports for QTimer
from PySide6.QtCore import QTimer
