from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QLabel, 
    QComboBox, QLineEdit, QPushButton, QAbstractItemView, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QModelIndex
from PySide6.QtGui import QColor, QIcon, QBrush

from ..database import get_db, query
from ..utils import get_icon, open_file, open_folder, format_smart_date
from ..scanner.library_scanner import get_all_projects
from ..classifier.engine import ProjectState

from .view_models.projects_model import ProjectsModel
from .delegates.projects_delegate import ProjectsDelegate

class ProjectsView(QWidget):
    """
    Main view for managing FL Studio projects.
    Displays classification stages, scores, and allows filtering.
    """
    
    project_opened = Signal(str) # Path
    project_selected = Signal(dict) # Emit project data for details panel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_projects_data = [] # Full dataset
        self.filtered_projects = [] # Filtered dataset
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
        self.stage_filter.setFixedWidth(140)
        self.stage_filter.addItems(["All Stages", "Micro Idea", "Idea", "WIP", "Preview Ready", "Advanced", "Broken/Empty"])
        self.stage_filter.currentTextChanged.connect(self._on_filter_changed)
        header.addWidget(self.stage_filter)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setFixedWidth(200)
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self._on_filter_changed)
        header.addWidget(self.search_input)
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setIcon(get_icon("refresh", QColor("#94a3b8"), 14))
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Table View
        self.table = QTableView()
        self.table.setObjectName("trackList") # Reuse styles
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        
        # Model
        self.model = ProjectsModel(parent=self)
        self.table.setModel(self.model)
        
        # Delegate
        self.delegate = ProjectsDelegate(self.table)
        self.delegate.open_folder_clicked.connect(self._on_open_folder)
        self.delegate.open_flp_clicked.connect(self._on_open_flp)
        self.table.setItemDelegate(self.delegate)
        
        # Header setup
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(ProjectsModel.COL_NAME, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(ProjectsModel.COL_STATE, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(ProjectsModel.COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(ProjectsModel.COL_ACTIONS, 90)
        
        # Events
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.clicked.connect(self._on_item_clicked)
        # Enable mouse tracking for delegate hover
        self.table.setMouseTracking(True)
        
        layout.addWidget(self.table)
        
    def refresh_data(self):
        """Fetch data and populate model."""
        import time
        import logging
        logger = logging.getLogger(__name__)
        
        t0 = time.perf_counter()
        # TODO: Add pagination if > 2000 items
        self.raw_projects_data = get_all_projects(limit=2000)
        t_fetch = time.perf_counter()
        
        self._apply_filters()
        t_end = time.perf_counter()
        
        logger.info(f"[Perf] refresh_data: Fetch={t_fetch-t0:.3f}s, Filter/Render={t_end-t_fetch:.3f}s, TotalItems={len(self.raw_projects_data)}")
        
    def _apply_filters(self):
        """Filter data and update model."""
        stage_filter = self.stage_filter.currentText()
        search_text = self.search_input.text().lower()
        
        filtered = []
        for p in self.raw_projects_data:
            # Stage Filter
            p_state = p.get('state', 'Unknown') or 'Unknown'
            
            match = True
            if stage_filter != "All Stages":
                target = stage_filter.upper().replace(" ", "_").replace("/", "_OR_")
                if target not in p_state:
                    match = False
            
            # Search Filter
            if match and search_text:
                if search_text not in p['name'].lower():
                    match = False
            
            if match:
                filtered.append(p)
                
        # Sort by Modified Date default
        filtered.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
        
        self.filtered_projects = filtered
        self.model.set_projects(filtered)
        self.count_label.setText(f"{len(filtered)} projects")

    def _on_item_clicked(self, index: QModelIndex):
        """Handle single click to select project."""
        if not index.isValid(): return
        
        # Get project from model
        # We can get it from user role or just index into our list if sorted same way
        # Best to rely on model index mapping
        project = index.data(Qt.ItemDataRole.UserRole)
        if project:
            self.project_selected.emit(project)
            
    def _on_filter_changed(self):
        self._apply_filters()
        
    def _on_row_double_clicked(self, index: QModelIndex):
        """Open project folder on double click."""
        if not index.isValid(): return
        
        project = index.data(Qt.ItemDataRole.UserRole)
        if project:
            path = project.get('path')
            if path:
                open_folder(path)
                
    def _on_open_folder(self, project: dict):
        path = project.get('path')
        if path:
            open_folder(path)
            
    def _on_open_flp(self, project: dict):
        flp_path = project.get('flp_path')
        if flp_path:
            open_file(flp_path)

