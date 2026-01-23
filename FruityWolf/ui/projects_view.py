from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QComboBox, QLineEdit, QPushButton, QAbstractItemView,
    QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QBrush

from ..database import get_db, query
from ..utils import get_icon, open_file, open_folder, format_smart_date
from ..scanner.library_scanner import get_all_projects
from ..classifier.engine import ProjectState

class ProjectsView(QWidget):
    """
    Main view for managing FL Studio projects.
    Displays classification stages, scores, and allows filtering.
    """
    
    project_opened = Signal(str) # Path
    project_selected = Signal(dict) # Emit project data for details panel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects_data = []
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
        
        # Table
        self.table = QTableWidget()
        self.table.setObjectName("trackList") # Reuse styles
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "STATE", "NAME", "SCORE", "MODIFIED", "BACKUPS", "SIZE", "ACTIONS"
        ])
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Name
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # State
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed) # Actions
        self.table.setColumnWidth(6, 90)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.table.itemClicked.connect(self._on_item_clicked)
        
        layout.addWidget(self.table)
        
    def refresh_data(self):
        """Fetch data and populate table."""
        self.projects_data = get_all_projects(limit=2000)
        self._populate_table()
        
    def _populate_table(self):
        """Filter and show data."""
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        
        try:
            stage_filter = self.stage_filter.currentText()
            search_text = self.search_input.text().lower()
            
            filtered = []
            for p in self.projects_data:
                # Stage Filter
                p_state = p.get('state', 'Unknown') or 'Unknown'
                # Map UI string to backend enum if needed, or just string match
                
                match = True
                if stage_filter != "All Stages":
                    # Convert "Micro Idea" -> "MICRO_IDEA" approx
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
            
            self.table.setRowCount(len(filtered))
            self.count_label.setText(f"{len(filtered)} projects")
            
            for i, p in enumerate(filtered):
                # 0: State Badge
                state = p.get('state', 'Unknown')
                state_item = QTableWidgetItem(self._format_state(state))
                state_item.setForeground(QBrush(self._get_state_color(state)))
                state_item.setData(Qt.ItemDataRole.UserRole, p)
                self.table.setItem(i, 0, state_item)
                
                # 1: Name
                name_item = QTableWidgetItem(p['name'])
                name_item.setToolTip(p.get('path', ''))
                self.table.setItem(i, 1, name_item)
                
                # 2: Score (Bar or Num)
                score = p.get('render_priority_score', 0)
                score_item = QTableWidgetItem(str(score))
                if score > 70:
                    score_item.setForeground(QBrush(QColor("#22c55e"))) # Green
                elif score > 40:
                    score_item.setForeground(QBrush(QColor("#f59e0b"))) # Orange
                else:
                    score_item.setForeground(QBrush(QColor("#64748b"))) # Gray
                self.table.setItem(i, 2, score_item)
                
                # 3: Modified
                mtime = p.get('updated_at', 0)
                date_str = format_smart_date(mtime)
                self.table.setItem(i, 3, QTableWidgetItem(date_str))
                
                # 4: Backups
                backups = p.get('backup_count', 0)
                self.table.setItem(i, 4, QTableWidgetItem(str(backups)))
                
                # 5: Size
                # Assuming we have folder_size stored or can get flp size
                # We stored `flp_size_kb` in DB
                size_kb = p.get('flp_size_kb', 0)
                self.table.setItem(i, 5, QTableWidgetItem(f"{size_kb} KB"))
                
                # 6: Actions (Icon Buttons)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)
                
                btn_folder = QPushButton()
                btn_folder.setIcon(get_icon("folder_open", QColor("#94a3b8"), 14))
                btn_folder.setToolTip("Open Folder")
                btn_folder.setStyleSheet("border: none; background: transparent;")
                btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
                
                # Capture path in closure
                # Note: lambda inside loop problem, need default arg
                path = p['path']
                btn_folder.clicked.connect(lambda checked=False, p=path: open_folder(p))
                actions_layout.addWidget(btn_folder)
                
                btn_flp = QPushButton()
                if p.get('flp_path') and p.get('flp_path').endswith('.flp'):
                    btn_flp.setIcon(get_icon("fl_studio", QColor("#22c55e"), 14)) # Green for active FLP
                    btn_flp.setToolTip("Open FLP")
                    btn_flp.setCursor(Qt.CursorShape.PointingHandCursor)
                    flp_path = p['flp_path']
                    btn_flp.clicked.connect(lambda checked=False, p=flp_path: open_file(p))
                else:
                    btn_flp.setIcon(get_icon("fl_studio", QColor("#475569"), 14)) # Disabled color
                    btn_flp.setEnabled(False)
                    
                btn_flp.setStyleSheet("border: none; background: transparent;")
                actions_layout.addWidget(btn_flp)
                
                self.table.setCellWidget(i, 6, actions_widget)
        
        finally:
            self.table.setSortingEnabled(True)
            self.table.setUpdatesEnabled(True)

    def _on_item_clicked(self, item):
        """Handle single click to select project."""
        row = item.row()
        item0 = self.table.item(row, 0)
        if item0:
            data = item0.data(Qt.ItemDataRole.UserRole)
            self.project_selected.emit(data)

    def _format_state(self, state: str) -> str:
        """Format state enum to display string."""
        if not state: return "Unknown"
        return state.replace("_", " ").title().replace("Or", "/")

    def _get_state_color(self, state: str) -> QColor:
        """Get color for state."""
        map_ = {
            ProjectState.MICRO_IDEA: QColor("#94a3b8"), # Slate 400
            ProjectState.IDEA: QColor("#38bdf8"),       # Sky 400
            ProjectState.WIP: QColor("#f59e0b"),        # Amber 500
            ProjectState.PREVIEW_READY: QColor("#22c55e"), # Green 500
            ProjectState.ADVANCED: QColor("#a855f7"),   # Purple 500
            ProjectState.BROKEN_OR_EMPTY: QColor("#ef4444"), # Red 500
        }
        return map_.get(state, QColor("#f1f5f9"))
        
    def _on_filter_changed(self):
        self._populate_table()
        
    def _on_row_double_clicked(self, row, col):
        """Open project folder on double click."""
        item = self.table.item(row, 0)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            path = data.get('path')
            if path:
                open_folder(path)
