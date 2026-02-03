from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QLabel, 
    QComboBox, QLineEdit, QPushButton, QAbstractItemView, QFrame,
    QCheckBox, QStyle, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor, QIcon, QBrush

import logging
from typing import List
from ..database import get_db, query

logger = logging.getLogger(__name__)
from ..utils import get_icon, open_file, open_folder, format_smart_date
from ..utils.path_utils import validate_path
from ..scanner.library_scanner import get_all_projects, get_sample_usage
from ..classifier.engine import ProjectState
from .jobs import JobManager

from .view_models.projects_model import ProjectsModel
from .delegates.projects_delegate import ProjectsDelegate

class ProjectsView(QWidget):
    """
    Main view for managing FL Studio projects.
    Displays classification stages, scores, and allows filtering.
    Phase 1: Added Bulk Action Bar.
    """
    
    project_opened = Signal(str) # Path
    project_selected = Signal(dict) # Emit project data for details panel
    play_requested = Signal(dict)
    view_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_size = 100
        self.current_offset = 0
        self.is_loading = False
        self.active_plugin_filter = None  # Set by app when a plugin is selected (Phase 1)
        
        self.job_manager = JobManager(self)
        self.job_manager.signals.finished.connect(self._on_job_finished)
        
        self._setup_ui()
        self.refresh_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("PROJECTS")
        title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; letter-spacing: 1.5px;")
        header.addWidget(title)
        
        self.count_label = QLabel("0 projects")
        self.count_label.setStyleSheet("color: #94a3b8; margin-left: 8px;")
        header.addWidget(self.count_label)
        
        header.addStretch()
        
        # Filters
        self.stage_filter = QComboBox()
        self.stage_filter.setFixedWidth(160)
        self.stage_filter.addItems([
            "All Projects", 
            "--- WORKFLOW ---",
            "My current weapons", "Old vault", "Dangerous potential", "Unstable",
            "--- HEAT ---",
            "Hot", "Warm", "Cold",
            "--- SIGNALS ---",
            "Preview Ready", "Unheard", "OK", "Unknown"
        ])
        self.stage_filter.currentTextChanged.connect(self._on_filter_changed)
        header.addWidget(self.stage_filter)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setFixedWidth(200)
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self._on_filter_changed)
        header.addWidget(self.search_input)
        
        # Phase 1: Safe to open only (plugin-page-analysis.md §10.2)
        self.safe_to_open_only_check = QCheckBox("Safe to open only")
        self.safe_to_open_only_check.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.safe_to_open_only_check.stateChanged.connect(self._on_filter_changed)
        header.addWidget(self.safe_to_open_only_check)
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setIcon(get_icon("refresh", QColor("#94a3b8"), 14))
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Main Content Row (Now just the Table)
        # Directly add the table to the layout to take full width
        self.table = QTableView()
        self.table.setObjectName("trackList") # Reuse styles
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        
        # Model
        self.model = ProjectsModel(parent=self)
        self.model.dataChanged.connect(self._on_model_data_changed)
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        
        # Store sort state for queue building - default to CREATED DESC (newest first)
        self._current_sort_column = ProjectsModel.COL_CREATED
        self._current_sort_order = Qt.SortOrder.DescendingOrder
        
        # Set default sort indicator on header
        self.table.horizontalHeader().setSortIndicator(ProjectsModel.COL_CREATED, Qt.SortOrder.DescendingOrder)
        
        # Connect header sort indicator to track current sort state
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)
        
        # Delegate
        self.delegate = ProjectsDelegate(self.table)
        self.delegate.open_folder_clicked.connect(self._on_open_folder)
        self.delegate.open_flp_clicked.connect(self._on_open_flp)
        self.delegate.play_clicked.connect(self.play_requested.emit)
        self.delegate.view_clicked.connect(self.view_requested.emit)
        self.table.setItemDelegate(self.delegate)
        
        # Header setup - Optimized for full width
        h = self.table.horizontalHeader()
        h.setStretchLastSection(False) # We want specific columns to stretch
        
        h.setSectionResizeMode(ProjectsModel.COL_SELECT, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(ProjectsModel.COL_SELECT, 32)
        
        h.setSectionResizeMode(ProjectsModel.COL_NAME, QHeaderView.ResizeMode.Stretch)
        
        h.setSectionResizeMode(ProjectsModel.COL_HEAT, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(ProjectsModel.COL_HEAT, 100)
        
        h.setSectionResizeMode(ProjectsModel.COL_AUDIBILITY, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(ProjectsModel.COL_AUDIBILITY, 80)
        
        h.setSectionResizeMode(ProjectsModel.COL_SAFETY, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(ProjectsModel.COL_SAFETY, 80)
        
        h.setSectionResizeMode(ProjectsModel.COL_LAST_TOUCHED, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(ProjectsModel.COL_LAST_TOUCHED, 120)
        
        h.setSectionResizeMode(ProjectsModel.COL_PLAYS, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(ProjectsModel.COL_PLAYS, 60)
        
        h.setSectionResizeMode(ProjectsModel.COL_OPENS, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(ProjectsModel.COL_OPENS, 60)
        
        h.setSectionResizeMode(ProjectsModel.COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(ProjectsModel.COL_ACTIONS, 120)  # Increased to fit all 4 buttons
        
        # Events
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.clicked.connect(self._on_item_clicked)
        self.table.setMouseTracking(True)
        
        # Infinite Scroll
        self.table.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        layout.addWidget(self.table, 1) # Added directly to main layout
        
        # Floating Bulk Action Bar
        self.bulk_bar = QFrame()
        self.bulk_bar.setObjectName("bulkBar")
        self.bulk_bar.setStyleSheet("""
            #bulkBar {
                background-color: #1e293b;
                border-top: 1px solid #334155;
                border-radius: 6px;
            }
        """)
        self.bulk_bar.setVisible(False)
        
        bulk_layout = QHBoxLayout(self.bulk_bar)
        bulk_layout.setContentsMargins(16, 8, 16, 8)
        
        self.bulk_label = QLabel("0 selected")
        self.bulk_label.setStyleSheet("color: white; font-weight: bold;")
        bulk_layout.addWidget(self.bulk_label)
        
        bulk_layout.addStretch()
        
        # Actions
        btn_reclassify = QPushButton("Reclassify")
        btn_reclassify.clicked.connect(self._on_bulk_reclassify)
        bulk_layout.addWidget(btn_reclassify)
        
        # Could add more: Set State, Add Tag...
        
        layout.addWidget(self.bulk_bar)
    
    def _on_sort_changed(self, column: int, order: Qt.SortOrder):
        """Handle sort column/order changes."""
        self._current_sort_column = column
        self._current_sort_order = order
        # Note: Sorting is handled by QTableView when sortingEnabled is True
        
    def refresh_data(self):
        """Fetch data and populate model."""
        self._apply_filters()
        
    def reset_state(self):
        """Reset filters and search."""
        self.stage_filter.setCurrentIndex(0)
        self.search_input.clear()
        self.active_sample_filter = None
        self.active_sample_project_ids = set()
        self._apply_filters()
        
    def _apply_filters(self):
        """Filter data and update model using DB-level search."""
        self.current_offset = 0
        self.is_loading = True
        
        stage_filter = self.stage_filter.currentText()
        search_text = self.search_input.text()
        
        from ..scanner.library_scanner import search_projects
        projects = search_projects(
            term=search_text,
            stage_filter=stage_filter,
            limit=self.page_size,
            offset=self.current_offset,
            plugin_name=self.active_plugin_filter,
            safe_to_open_only=self.safe_to_open_only_check.isChecked(),
        )
        
        self.filtered_projects = projects
        self.model.set_projects(projects)
        self.count_label.setText(f"{len(projects)} projects")
        
        # Ensure consistent sort state after loading (data comes pre-sorted from DB)
        # This syncs the model and header indicator with the DB's default ordering
        self.model.sort(ProjectsModel.COL_CREATED, Qt.SortOrder.DescendingOrder)
        self.table.horizontalHeader().setSortIndicator(ProjectsModel.COL_CREATED, Qt.SortOrder.DescendingOrder)
        
        self.is_loading = False
        self._on_model_data_changed()

    def _on_scroll(self, value):
        """Handle scroll to implement infinite loading."""
        if self.is_loading:
            return
            
        scrollbar = self.table.verticalScrollBar()
        if value > scrollbar.maximum() * 0.8: # Threshold to load more
            self._load_more()

    def _load_more(self):
        """Load next batch of projects."""
        if self.is_loading:
            return
            
        self.is_loading = True
        self.current_offset += self.page_size
        
        stage_filter = self.stage_filter.currentText()
        search_text = self.search_input.text()
        
        from ..scanner.library_scanner import search_projects
        projects = search_projects(
            term=search_text,
            stage_filter=stage_filter,
            limit=self.page_size,
            offset=self.current_offset,
            plugin_name=self.active_plugin_filter,
            safe_to_open_only=self.safe_to_open_only_check.isChecked(),
        )
        
        if projects:
            self.model.append_projects(projects)
            self.filtered_projects.extend(projects)
            self.count_label.setText(f"{len(self.filtered_projects)} projects")
            
            # Re-sort after appending to maintain consistent order
            self.model.sort(ProjectsModel.COL_CREATED, Qt.SortOrder.DescendingOrder)
            self.table.horizontalHeader().setSortIndicator(ProjectsModel.COL_CREATED, Qt.SortOrder.DescendingOrder)
        
        self.is_loading = False

    def _on_item_clicked(self, index: QModelIndex):
        """Handle single click to select project."""
        if not index.isValid(): return
        
        # If click on check box, model handles it.
        # If click on audibility column, show renders panel (legacy behavior logic, or maybe just select)
        if index.column() == ProjectsModel.COL_AUDIBILITY:
            project = index.data(Qt.ItemDataRole.UserRole)
            if project:
                if project.get('render_count', 0) > 0 or project.get('has_render'):
                    self.view_requested.emit(project)  # Show renders panel
            return
        
        # If click on body, we emit selected.
        if index.column() != ProjectsModel.COL_SELECT:
             project = index.data(Qt.ItemDataRole.UserRole)
             if project:
                 self.project_selected.emit(project)
            
    def _on_filter_changed(self):
        self._apply_filters()
        
    def _on_row_double_clicked(self, index: QModelIndex):
        """Open project folder on double click."""
        if not index.isValid(): return
        if index.column() == ProjectsModel.COL_SELECT: return
        
        project = index.data(Qt.ItemDataRole.UserRole)
        if project:
            path = project.get('path')
            if validate_path(path, "Project folder", self):
                open_folder(path)
    
    def get_sorted_projects(self) -> List[dict]:
        """Get projects in current sorted order (for queue building)."""
        sorted_projects = []
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if index.isValid():
                project = self.model.data(index, Qt.ItemDataRole.UserRole)
                if project:
                    sorted_projects.append(project)
        return sorted_projects
                
    def _on_open_folder(self, project: dict):
        path = project.get('path')
        project_id = project.get('id')
        if validate_path(path, "Project folder", self):
            open_folder(path)
            # Update stats
            if project_id:
                try:
                    now = int(time.time())
                    execute(
                        "UPDATE projects SET last_opened_at = ?, open_count = COALESCE(open_count, 0) + 1, updated_at = ? WHERE id = ?", 
                        (now, now, project_id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to update stats for open folder: {e}")
            
    def _on_open_flp(self, project: dict):
        flp_path = project.get('flp_path')
        project_id = project.get('id')
        if validate_path(flp_path, "FLP", self):
            open_file(flp_path)
            # Update stats
            if project_id:
                try:
                    now = int(time.time())
                    execute(
                        "UPDATE projects SET last_opened_at = ?, open_count = COALESCE(open_count, 0) + 1, updated_at = ? WHERE id = ?", 
                        (now, now, project_id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to update stats for open FLP: {e}")
            
    def _on_model_data_changed(self):
        """Update UI based on model state (selection)."""
        selected = self.model.get_checked_projects()
        count = len(selected)
        
        if count > 0:
            self.bulk_bar.setVisible(True)
            self.bulk_label.setText(f"{count} selected")
        else:
            self.bulk_bar.setVisible(False)
            
    def _on_bulk_reclassify(self):
        """Reclassify selected projects."""
        selected = self.model.get_checked_projects()
        ids = [p['id'] for p in selected]
        if not ids: return
        
        # Start job
        self.job_manager.start_bulk_update(ids, {"action": "reclassify", "value": True})
        # Note: logic for 'reclassify' action needs to be in BulkUpdateJob (jobs.py)
        # I need to verify jobs.py handles 'reclassify'.
        
    def _on_job_finished(self, job_id, status, errors):
        if status == "completed":
            self.refresh_data()
        elif status == "failed":
            pass # Show error?
            
