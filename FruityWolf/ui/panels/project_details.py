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
    QLineEdit, QComboBox, QCheckBox, QSizePolicy, QFileDialog, QMenu,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPixmap, QAction

from ...utils import get_icon, format_smart_date, format_absolute_date, get_placeholder_cover, get_cover_art
from ...utils.image_manager import get_image_manager
from ...classifier.engine import ProjectState
from ...database import execute, query_one
from ...services.cover_manager import (
    save_cover_image, set_project_cover, get_project_cover_path
)
from ...rendering.engine import get_render_queue, RenderJob, RenderStatus
from ...rendering.fl_cli import resolve_fl_executable, get_expected_preview_path
from ...rendering.backup_exclusion import is_eligible_flp
from ...core.activity_heat import calculate_activity_heat, get_heat_color
from pathlib import Path

logger = logging.getLogger(__name__)

class ProjectDetailsPanel(QWidget):
    """Side panel for displaying Project details."""
    
    open_folder_clicked = Signal(str)
    open_flp_clicked = Signal(str)
    project_updated = Signal(int)  # project_id, emitted after successful render so UI can refresh
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project = None
        self.current_cover_path = None
        self.current_cover_request_id = None
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
        cover_container = QWidget()
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(8)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #1e293b;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cover_label.customContextMenuRequested.connect(self._show_cover_menu)
        cover_layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.cover_btn = QPushButton("Change Cover")
        self.cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f1f5f9;
            }
        """)
        self.cover_btn.clicked.connect(self._change_cover)
        self.cover_btn.hide()  # Show only when project is selected
        cover_layout.addWidget(self.cover_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(cover_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.title_label = QLabel("Select a project")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)
        
        self.date_label = QLabel("")
        self.date_label.setStyleSheet("font-size: 13px; color: #64748b;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.date_label)
        
        # 2. TRUTH SIGNALS (Heat + Audibility + Safety)
        self.signals_frame = QFrame()
        self.signals_frame.setObjectName("signalsFrame")
        self.signals_frame.setStyleSheet("""
            #signalsFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        sig_layout = QVBoxLayout(self.signals_frame)
        sig_layout.setContentsMargins(12, 12, 12, 12)
        sig_layout.setSpacing(12)
        
        # Top Row: Heat Label + Badges
        top_row = QHBoxLayout()
        self.heat_label = QLabel("Cold")
        self.heat_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 2px 8px; border-radius: 4px; background: #1e293b;")
        top_row.addWidget(self.heat_label)
        top_row.addStretch()
        
        self.audibility_badge = QLabel("Unheard")
        self.audibility_badge.setStyleSheet("color: #94a3b8; font-size: 11px;")
        top_row.addWidget(self.audibility_badge)
        
        self.safety_badge = QLabel("Unknown")
        self.safety_badge.setStyleSheet("color: #94a3b8; font-size: 11px;")
        top_row.addWidget(self.safety_badge)
        
        sig_layout.addLayout(top_row)
        
        # Stats Grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        
        self.lbl_last_touch = QLabel("Never")
        self.lbl_plays = QLabel("0")
        self.lbl_opens = QLabel("0")
        
        def add_stat_lbl(row, col, label, value_widget):
            l = QLabel(label)
            l.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
            value_widget.setStyleSheet("color: #e2e8f0; font-size: 12px;")
            stats_grid.addWidget(l, row, col)
            stats_grid.addWidget(value_widget, row + 1, col)
            
        add_stat_lbl(0, 0, "LAST TOUCHED", self.lbl_last_touch)
        add_stat_lbl(0, 1, "PLAYS", self.lbl_plays)
        add_stat_lbl(0, 2, "OPENS", self.lbl_opens)
        
        sig_layout.addLayout(stats_grid)
        self.main_layout.addWidget(self.signals_frame)
        
        # 3. ACTIONS (Replaces Next Action CTA)
        self.actions_frame = QFrame()
        self.actions_frame.setObjectName("actionsFrame")
        self.actions_frame.setStyleSheet("""
            #actionsFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        actions_layout = QVBoxLayout(self.actions_frame)
        actions_layout.setSpacing(8)
        
        lbl_actions = QLabel("ACTIONS")
        lbl_actions.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        actions_layout.addWidget(lbl_actions)
        
        # Primary Action: Open FLP
        self.btn_flp = QPushButton(" Open Project in FL Studio")
        self.btn_flp.setIcon(get_icon("fl_studio", QColor("#0f172a"), 16))
        self.btn_flp.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover { background-color: #7dd3fc; }
        """)
        self.btn_flp.clicked.connect(self._on_open_flp)
        actions_layout.addWidget(self.btn_flp)
        
        # Secondary Actions: Render, Folder
        row_sec = QHBoxLayout()
        row_sec.setSpacing(8)
        
        self.btn_render = QPushButton(" Render Preview")
        self.btn_render.setIcon(get_icon("play_circle", QColor("#e2e8f0"), 16))
        self.btn_render.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_render.clicked.connect(self._on_render_preview)
        row_sec.addWidget(self.btn_render)
        
        self.btn_folder = QPushButton(" Folder")
        self.btn_folder.setIcon(get_icon("folder_open", QColor("#e2e8f0"), 16))
        self.btn_folder.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_folder.clicked.connect(self._on_open_folder)
        row_sec.addWidget(self.btn_folder)
        
        actions_layout.addLayout(row_sec)
        self.main_layout.addWidget(self.actions_frame)
        
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
        
        # 6. (ACTIONS moved to top, removing old actions block)
        
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
        
        # Cancel previous cover request
        if self.current_cover_request_id:
            self.image_manager.cancel_request(self.current_cover_request_id)
        
        # Basic Info
        # Cover - Async loading
        project_id = project.get('id')
        path = project.get('path')
        
        # Get cover path (custom first, then auto-detected)
        self.current_cover_path = get_project_cover_path(project_id, path) if project_id else get_cover_art(path)
        self.current_cover_request_id = f"project_{project_id}_{path}"
        
        # Show placeholder immediately
        self.cover_label.setPixmap(get_placeholder_cover(200, project.get('name', ''), is_project=True))
        self.cover_btn.show()
        
        # Load cover asynchronously
        if self.current_cover_path:
            pix = self.image_manager.get_image(self.current_cover_path, 200, self.current_cover_request_id)
            if pix:
                # Found in cache, use immediately
                self.cover_label.setPixmap(pix)
        self.title_label.setText(project.get('name', 'Unknown'))
        # Use file_created_at for creation date, with updated_at as fallback
        created_ts = project.get('file_created_at') or project.get('created_at') or project.get('updated_at', 0)
        self.date_label.setText(format_smart_date(created_ts))
        self.date_label.setToolTip(f"Created: {format_absolute_date(created_ts)}")
        
        # --- TRUTH SIGNALS ---
        
        # 1. Activity Heat
        # Use pre-calculated heat_data from model if available, otherwise calculate
        heat_data = project.get('heat_data')
        if not heat_data:
            flp_mtime = project.get('updated_at')
            heat_data = calculate_activity_heat(
                flp_mtime=flp_mtime,
                last_opened_at=project.get('last_opened_at'),
                last_rendered_at=project.get('last_rendered_at'),
                open_count=project.get('open_count', 0) or 0,
                play_count=project.get('play_count', 0) or 0
            )
            
        heat_label = heat_data['label']
        heat_score = heat_data['score']
        heat_color = get_heat_color(heat_label)
        
        self.heat_label.setText(heat_label.upper())
        self.heat_label.setStyleSheet(f"font-weight: bold; font-size: 14px; padding: 2px 8px; border-radius: 4px; background: {heat_color}; color: #0f172a;")
        self.heat_label.setToolTip(f"Activity Heat: {heat_score}/100")
        
        # 2. Audibility
        is_preview_ready = project.get('render_status') == 'preview_ready' or project.get('has_render')
        if is_preview_ready:
            self.audibility_badge.setText("● Preview Ready")
            self.audibility_badge.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 11px;")
        else:
            self.audibility_badge.setText("○ Unheard")
            self.audibility_badge.setStyleSheet("color: #64748b; font-size: 11px;")
            
        # 3. Safety
        last_failed = project.get('last_render_failed_at')
        attempted = project.get('render_attempted_count', 0) > 0
        
        if last_failed:
            self.safety_badge.setText("● Unstable")
            self.safety_badge.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
            reason = project.get('last_render_failed_reason', 'Unknown error')
            self.safety_badge.setToolTip(f"Last render failed: {reason}")
        elif attempted:
            self.safety_badge.setText("● OK")
            self.safety_badge.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 11px;")
            self.safety_badge.setToolTip("Last render successful")
        else:
            self.safety_badge.setText("○ Unknown")
            self.safety_badge.setStyleSheet("color: #64748b; font-size: 11px;")
            self.safety_badge.setToolTip("No renders attempted")
            
        # 4. Stats
        last_touch_ts = heat_data.get('last_touch_ts')
        self.lbl_last_touch.setText(format_smart_date(last_touch_ts) if last_touch_ts else "Never")
        self.lbl_plays.setText(str(project.get('play_count', 0) or 0))
        self.lbl_opens.setText(str(project.get('open_count', 0) or 0))
        
        # Next Action
        # Replaced by ACTIONS frame, but logic remains in model for reference
        # We can remove this block if we don't display "Next Action" text specifically
        # The user wanted buttons instead of "Do It"
        pass
        
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
            
        # Debug
        if self.chk_debug.isChecked():
            self._update_debug_info()
            
        # Buttons
        flp_path = project.get('flp_path')
        has_flp = bool(flp_path) and os.path.exists(flp_path)
        self.btn_flp.setEnabled(has_flp)
        self.btn_render.setEnabled(has_flp)
        self.btn_folder.setEnabled(bool(project.get('path') or project.get('flp_path')))

    def _on_render_preview(self):
        """Handle single project render request."""
        if not self.current_project or not self.current_project.get('flp_path'):
            return
            
        flp_path = Path(self.current_project.get('flp_path'))
        
        # 1. Resolve FL Exe
        if not resolve_fl_executable():
            QMessageBox.warning(
                self, 
                "FL Studio Not Found", 
                "Please configure the FL Studio executable path in Settings."
            )
            return

        # 2. Check Backup Exclusion
        if not is_eligible_flp(flp_path):
            QMessageBox.warning(
                self,
                "Cannot Render Backup",
                "This project appears to be a backup or autosave.\n"
                "Rendering is disabled for safety."
            )
            return

        # 3. Format selection
        format_options = ("MP3", "WAV")
        format_choice, ok = QInputDialog.getItem(
            self,
            "Render Preview",
            "Output format:",
            format_options,
            0,
            False
        )
        if not ok:
            return
        format_type = format_choice.strip().lower() if format_choice else "mp3"
        if format_type not in ("mp3", "wav"):
            format_type = "mp3"
            
        # 4. Confirmation
        preview_path = get_expected_preview_path(flp_path, format_type)
        msg = (
            f"Ready to render preview for:\n{self.current_project.get('name')}\n\n"
            f"Format: {format_type.upper()}\n"
            f"Output: {preview_path.name}\n\n"
            "WARNING:\n"
            "• FL Studio will open visibly and may take focus.\n"
            "• If plugins/samples are missing, it may block.\n"
            "• No existing user files will be touched (only __fw_preview).\n"
            "\nProceed?"
        )
        
        reply = QMessageBox.question(
            self, 
            "Render Preview", 
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            job = RenderJob(
                source_flp=flp_path,
                job_type='audio',
                format_type=format_type
            )
            queue = get_render_queue()
            
            # Connect signals for immediate feedback (simple approach for now)
            # Ideally we'd have a global job monitor, but for single project this works
            queue.job_started.connect(self._on_render_started)
            queue.job_finished.connect(self._on_render_finished)
            
            queue.add_job(job)
            queue.start_queue()
            
            self.btn_render.setText("Queueing...")
            self.btn_render.setEnabled(False)

    def _on_render_started(self, job: RenderJob):
        if self.current_project and str(job.source_flp) == self.current_project.get('flp_path'):
            self.btn_render.setText("Rendering...")
            
    def _on_render_finished(self, job: RenderJob):
        # Disconnect signals to avoid duplicates next time
        # (This is a bit quick-and-dirty, cleaner would be a dedicated job manager UI)
        try:
            queue = get_render_queue()
            queue.job_started.disconnect(self._on_render_started)
            queue.job_finished.disconnect(self._on_render_finished)
        except:
            pass
            
        if self.current_project and str(job.source_flp) == self.current_project.get('flp_path'):
            self.btn_render.setEnabled(True)
            self.btn_render.setText(" Render Preview...")
            
            if job.status == RenderStatus.COMPLETED:
                QMessageBox.information(self, "Render Complete", "Preview rendered successfully!")
                project_id = self.current_project.get('id')
                if project_id is not None:
                    self.project_updated.emit(project_id)
            else:
                QMessageBox.warning(self, "Render Failed", f"Render failed: {job.error_message}")

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
        self.current_cover_path = None
        self.current_cover_request_id = None
        self.cover_btn.hide()
        self.title_label.setText("Select a project")
        self.date_label.setText("")
        
        # Clear Truth Signals
        self.heat_label.setText("Cold")
        self.heat_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 2px 8px; border-radius: 4px; background: #1e293b; color: #94a3b8;")
        self.audibility_badge.setText("Unknown")
        self.safety_badge.setText("Unknown")
        self.lbl_last_touch.setText("-")
        self.lbl_plays.setText("0")
        self.lbl_opens.setText("0")
        
        self.txt_vision.clear()
        self.txt_todo.clear()
        self.inp_moods.clear()
        self.cover_label.setPixmap(get_placeholder_cover(200, "", is_project=True))
        
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
        path = (self.current_project.get('path') or
                (os.path.dirname(self.current_project.get('flp_path') or '')
                 if self.current_project.get('flp_path') else None))
        if self.current_project and path:
            self.open_folder_clicked.emit(self.current_project)

    def _on_open_flp(self):
        if self.current_project and self.current_project.get('flp_path'):
            self.open_flp_clicked.emit(self.current_project)

    def _on_image_loaded(self, path: str, pixmap: QPixmap, request_id: str):
        """Update cover if it matches current project."""
        # Only update if this is the current request
        if request_id == self.current_cover_request_id and path == self.current_cover_path:
            if not pixmap.isNull():
                self.cover_label.setPixmap(pixmap)
    
    def _show_cover_menu(self, pos):
        """Show context menu for cover."""
        if not self.current_project:
            return
        
        menu = QMenu(self)
        
        change_action = QAction("Change Cover...", self)
        change_action.triggered.connect(self._change_cover)
        menu.addAction(change_action)
        
        remove_action = QAction("Remove Custom Cover", self)
        remove_action.triggered.connect(self._remove_cover)
        menu.addAction(remove_action)
        
        menu.exec(self.cover_label.mapToGlobal(pos))
    
    def _change_cover(self):
        """Open file dialog to select new cover image."""
        if not self.current_project:
            return
        
        project_id = self.current_project.get('id')
        if not project_id:
            return
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Image",
            "",
            "Image Files (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Save cover image
            saved_path = save_cover_image(file_path, 'project', project_id)
            if saved_path:
                # Update database
                if set_project_cover(project_id, saved_path):
                    # Update UI
                    self.current_cover_path = saved_path
                    self.current_cover_request_id = f"project_{project_id}_{saved_path}"
                    
                    # Load new cover
                    pix = self.image_manager.get_image(saved_path, 200, self.current_cover_request_id)
                    if pix:
                        self.cover_label.setPixmap(pix)
                    else:
                        # Will be loaded async
                        self.cover_label.setPixmap(get_placeholder_cover(200, self.current_project.get('name', ''), is_project=True))
                else:
                    logger.error("Failed to update project cover in database")
        except Exception as e:
            logger.error(f"Failed to change cover: {e}")
    
    def _remove_cover(self):
        """Remove custom cover and revert to auto-detected."""
        if not self.current_project:
            return
        
        project_id = self.current_project.get('id')
        if not project_id:
            return
        
        try:
            if set_project_cover(project_id, None):
                # Reload cover (will use auto-detected)
                path = self.current_project.get('path')
                self.current_cover_path = get_project_cover_path(project_id, path)
                self.current_cover_request_id = f"project_{project_id}_{path}"
                
                if self.current_cover_path:
                    pix = self.image_manager.get_image(self.current_cover_path, 200, self.current_cover_request_id)
                    if pix:
                        self.cover_label.setPixmap(pix)
                    else:
                        self.cover_label.setPixmap(get_placeholder_cover(200, self.current_project.get('name', ''), is_project=True))
                else:
                    self.cover_label.setPixmap(get_placeholder_cover(200, self.current_project.get('name', ''), is_project=True))
        except Exception as e:
            logger.error(f"Failed to remove cover: {e}")
