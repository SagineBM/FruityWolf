"""
Playlists View

Full-page Spotify-like playlist management.
Refactored for performance with Model/View architecture.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QListView, QMenu, QAbstractItemView, QStyledItemDelegate,
    QStyle, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QBrush, QPen, QFont, QPainterPath

from ..scanner.playlist_manager import (
    get_playlist, create_playlist, delete_playlist,
    export_playlist_m3u
)
from ..utils import get_icon, format_duration, get_placeholder_cover
from .playlist_dialogs import PlaylistEditDialog
from .view_models.playlists_model import PlaylistsModel
from .view_models.playlist_tracks_model import PlaylistTracksModel

# =============================================================================
# Playlist Grid Delegate
# =============================================================================

class PlaylistDelegate(QStyledItemDelegate):
    """Custom delegate for rendering playlist cards."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.padding = 10
        self.radius = 12
        
    def sizeHint(self, option, index):
        return QSize(200, 240)
        
    def paint(self, painter, option, index):
        if not index.isValid():
            return
            
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Data
        title = index.data(Qt.ItemDataRole.DisplayRole)
        count = index.data(PlaylistsModel.TrackCountRole)
        cover_path = index.data(PlaylistsModel.CoverPathRole)
        
        # Areas
        rect = option.rect
        # Margin
        card_rect = rect.adjusted(5, 5, -5, -5)
        
        # Background
        is_hover = option.state & QStyle.StateFlag.State_MouseOver
        is_selected = option.state & QStyle.StateFlag.State_Selected
        
        bg_color = QColor("#1e293b")
        if is_selected:
            bg_color = QColor("#334155")
        elif is_hover:
            bg_color = QColor("#283548")
            
        path = QPainterPath()
        path.addRoundedRect(card_rect, self.radius, self.radius)
        
        painter.fillPath(path, bg_color)
        
        if is_selected:
            pen = QPen(QColor("#38bdf8"), 2)
            painter.strokePath(path, pen)
            
        # Content Rect
        content_rect = card_rect.adjusted(10, 10, -10, -10)
        
        # Cover (Top Square)
        cover_size = content_rect.width()
        cover_rect = QRect(content_rect.left(), content_rect.top(), cover_size, cover_size)
        
        # Draw Cover
        if cover_path and os.path.exists(cover_path):
             # In a real high-perf scenario, we'd cache the scaled pixmap in the model or a cache manager
             # For now, we load - assumes async model/cache handles file IO or we bear small UI hit
             # Optimization: Cached pixmap from index.data if model supports it
             pixmap = QPixmap(cover_path)
        else:
            pixmap = get_placeholder_cover(cover_size, title)
            
        if not pixmap.isNull():
             # Rounded clip for cover
             p = QPainterPath()
             p.addRoundedRect(cover_rect, 8, 8)
             painter.setClipPath(p)
             painter.drawPixmap(cover_rect, pixmap.scaled(cover_size, cover_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
             painter.setClipping(False)
             
        # Text (Below Cover)
        text_rect = QRect(content_rect.left(), cover_rect.bottom() + 10, content_rect.width(), content_rect.height() - cover_size - 10)
        
        # Title
        painter.setPen(QColor("#f1f5f9"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        
        title_rect = painter.boundingRect(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, title)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, title)
        
        # Count
        painter.setPen(QColor("#94a3b8"))
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        
        count_str = f"{count} tracks"
        # Draw below title
        sub_rect = QRect(text_rect.left(), title_rect.bottom() + 4, text_rect.width(), 20)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft, count_str)
        
        painter.restore()

# =============================================================================
# Track List Delegate
# =============================================================================

class TrackDelegate(QStyledItemDelegate):
    """Delegate for playlist tracks with Title, Artist/Project, Duration."""
    
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 56)
        
    def paint(self, painter, option, index):
        if not index.isValid():
            return
            
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Data
        title = index.data(Qt.ItemDataRole.DisplayRole)
        # DisplayRole in model currently returns "1. Title", let's parse or use custom role if we improve model
        # The model returns "idx. Title". Let's rely on that for now or strip.
        # Actually proper way is separate index role.
        # Re-using DisplayRole string for simplicity but splitting it visually?
        # Model returns "1. Title".
        
        project = index.data(PlaylistTracksModel.ProjectNameRole) or "Unknown Project"
        duration = index.data(PlaylistTracksModel.DurationRole) or "0:00"
        
        # Style
        rect = option.rect
        is_hover = option.state & QStyle.StateFlag.State_MouseOver
        is_selected = option.state & QStyle.StateFlag.State_Selected
        
        # Background
        if is_selected:
            painter.fillRect(rect, QColor("#334155"))
        elif is_hover:
            painter.fillRect(rect, QColor("#1e293b"))
            
        # Text Logic
        # Left margin for index/title
        left_margin = 16
        right_margin = 16
        
        # Title (Top)
        title_rect = QRect(rect.left() + left_margin, rect.top() + 10, rect.width() - 80, 20)
        painter.setPen(QColor("#f1f5f9"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        
        # Project (Bottom)
        subtitle_rect = QRect(rect.left() + left_margin, rect.top() + 32, rect.width() - 80, 16)
        painter.setPen(QColor("#94a3b8"))
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, project)
        
        # Duration (Right)
        dur_rect = QRect(rect.right() - 60 - right_margin, rect.top(), 60, rect.height())
        painter.setPen(QColor("#cbd5e1"))
        painter.drawText(dur_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, duration)
        
        # Divider
        painter.setPen(QColor("#1e293b"))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        
        painter.restore()


# =============================================================================
# Playlist Grid (The "Gallery")
# =============================================================================

class PlaylistGridWidget(QWidget):
    """Grid view of all playlists using QListView."""
    
    playlist_clicked = Signal(int)  # playlist_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.model = PlaylistsModel()
        self.grid.setModel(self.model)
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Playlists")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(title)
        header.addStretch()
        
        new_btn = QPushButton(" Create Playlist")
        new_btn.setIcon(get_icon("add", QColor("#0f172a"), 16))
        new_btn.setFixedSize(140, 36)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                border-radius: 18px;
                color: #0f172a;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #22d3ee; }
        """)
        new_btn.clicked.connect(self._create_playlist)
        header.addWidget(new_btn)
        layout.addLayout(header)
        
        # Grid View
        self.grid = QListView()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setSpacing(10)
        self.grid.setUniformItemSizes(True)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid.setStyleSheet("QListView { background: transparent; border: none; outline: none; }")
        
        # Delegate
        self.delegate = PlaylistDelegate()
        self.grid.setItemDelegate(self.delegate)
        
        self.grid.clicked.connect(self._on_item_clicked)
        layout.addWidget(self.grid)
        
    def refresh(self):
        """Reload playlists."""
        self.model.refresh()
            
    def _create_playlist(self):
        pid = PlaylistEditDialog.create_new(self)
        if pid:
            self.refresh()
            
    def _on_item_clicked(self, index):
        pid = self.model.data(index, PlaylistsModel.PlaylistIdRole)
        if pid:
            self.playlist_clicked.emit(pid)


# =============================================================================
# Playlist Detail (Full Page)
# =============================================================================

class PlaylistDetailWidget(QWidget):
    """Detailed view of a single playlist using QListView/Model."""
    
    back_clicked = Signal()
    play_requested = Signal(int) # playlist_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.playlist_id = None
        self._setup_ui()
        self.model = PlaylistTracksModel()
        self.track_list.setModel(self.model)
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header Frame - Cleaner Style
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(240)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-bottom: 1px solid #1e293b;
            }
        """)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(32, 32, 32, 32)
        header_layout.setSpacing(24)
        
        # Cover
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(160, 160)
        self.cover_label.setStyleSheet("background: #0f172a; border-radius: 12px; border: 1px solid #334155;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.cover_label)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        info_layout.setSpacing(4)
        
        lbl_type = QLabel("PLAYLIST")
        lbl_type.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; letter-spacing: 1px; background: transparent;")
        info_layout.addWidget(lbl_type)
        
        self.title_label = QLabel("Playlist Name")
        self.title_label.setStyleSheet("font-size: 40px; font-weight: 800; color: #ffffff; background: transparent;")
        info_layout.addWidget(self.title_label)
        
        self.desc_label = QLabel("")
        self.desc_label.setStyleSheet("font-size: 14px; color: #94a3b8; background: transparent;")
        self.desc_label.setWordWrap(True)
        info_layout.addWidget(self.desc_label)
        
        # Action Stats
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        # Play
        self.btn_play = QPushButton()
        self.btn_play.setIcon(get_icon("play", QColor("#ffffff"), 24))
        self.btn_play.setFixedSize(56, 56)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                border-radius: 28px;
                border: none;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
                transform: scale(1.05);
            }
        """)
        self.btn_play.clicked.connect(self._on_play)
        stats_layout.addWidget(self.btn_play)
        
        # Add Songs
        self.btn_add_songs = QPushButton("Add Songs")
        self.btn_add_songs.setIcon(get_icon("add", QColor("#ffffff"), 16))
        self.btn_add_songs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_songs.setFixedSize(120, 40)
        self.btn_add_songs.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: white;
                border: 1px solid #334155;
                border-radius: 20px;
                font-weight: bold;
                padding-left: 10px;
                padding-right: 10px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
                color: #38bdf8;
            }
        """)
        self.btn_add_songs.clicked.connect(self._on_add_songs)
        stats_layout.addWidget(self.btn_add_songs)
        
        # Edit / More
        self.btn_edit = self._create_action_btn("edit", "Edit")
        self.btn_edit.clicked.connect(self._on_edit)
        stats_layout.addWidget(self.btn_edit)
        
        self.btn_more = self._create_action_btn("more_vert", "More")
        self.btn_more.setText("...")
        self.btn_more.clicked.connect(self._on_more)
        stats_layout.addWidget(self.btn_more)
        
        info_layout.addLayout(stats_layout)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        layout.addWidget(self.header_frame)
        
        # Track List Style (Custom list view)
        self.track_list = QListView()
        self.track_list.setStyleSheet("""
            QListView {
                background: transparent;
                border: none;
                outline: none;
                padding: 0px;
            }
        """)
        self.track_list.setDragEnabled(True)
        self.track_list.setAcceptDrops(True)
        self.track_list.setDropIndicatorShown(True)
        self.track_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.track_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        self.track_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_list.customContextMenuRequested.connect(self._on_track_context_menu)
        
        self.track_delegate = TrackDelegate()
        self.track_list.setItemDelegate(self.track_delegate)
        
        self.track_list.doubleClicked.connect(self._on_track_double_click)
        
        
        layout.addWidget(self.track_list)
        
        # Back Button
        self.btn_back = QPushButton(self.header_frame)
        self.btn_back.setText(" Back")
        self.btn_back.setIcon(get_icon("arrow_left", QColor("#94a3b8"), 16))
        self.btn_back.setGeometry(16, 16, 80, 32)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,0.3);
                color: #94a3b8;
                border-radius: 16px;
                border: none;
                font-weight: bold;
                padding-left: 8px;
                padding-right: 12px;
            }
            QPushButton:hover {
                background: rgba(0,0,0,0.5);
                color: #ffffff;
            }
        """)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        
    def _create_action_btn(self, icon_name, tooltip):
        btn = QPushButton()
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #475569;
                border-radius: 20px;
                color: #94a3b8;
                font-weight: bold;
            }
            QPushButton:hover {
                border-color: #94a3b8;
                color: #ffffff;
            }
        """)
        return btn
        
    def set_playlist(self, playlist_id: int):
        self.playlist_id = playlist_id
        self.refresh()
        
    def refresh(self):
        if not self.playlist_id:
            return
            
        playlist = get_playlist(self.playlist_id)
        if not playlist:
            return
            
        self.title_label.setText(playlist.get('name', 'Untitled'))
        self.desc_label.setText(playlist.get('description', ''))
        
        # Cover
        # TODO: Async cover loading
        pixmap = get_placeholder_cover(160, playlist.get('name'))
        self.cover_label.setPixmap(pixmap)
        
        # Update model
        self.model.set_playlist(self.playlist_id)
        
    def _on_play(self):
        if self.playlist_id:
            self.play_requested.emit(self.playlist_id)
            
    def _on_add_songs(self):
        if not self.playlist_id:
            return
        from .playlist_dialogs import AddTracksDialog
        dialog = AddTracksDialog(self.playlist_id, self)
        dialog.tracks_added.connect(self.refresh)
        dialog.exec()

    def _on_edit(self):
        if self.playlist_id:
            if PlaylistEditDialog.edit_existing(self.playlist_id, self):
                self.refresh()
                
    def _on_more(self):
        menu = QMenu(self)
        
        act_export = menu.addAction("Export to M3U")
        act_export.triggered.connect(lambda: export_playlist_m3u(self.playlist_id, "playlist.m3u")) # Simplified
        
        act_delete = menu.addAction("Delete Playlist")
        act_delete.triggered.connect(lambda: self._delete())
        
        menu.exec(self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft()))

    def _delete(self):
        playlist = get_playlist(self.playlist_id)
        if not playlist:
            return
            
        reply = QMessageBox.question(
            self, "Delete Playlist",
            f"Are you sure you want to delete '{playlist['name']}'?\n\n"
            "This will not delete any audio files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_playlist(self.playlist_id)
            self.back_clicked.emit()
            
    def _on_track_context_menu(self, pos):
        index = self.track_list.indexAt(pos)
        if not index.isValid():
            return
            
        menu = QMenu(self)
        
        act_remove = menu.addAction("Remove from Playlist")
        act_remove.setIcon(get_icon("trash", QColor("#ef4444"), 16))
        act_remove.triggered.connect(lambda: self._remove_track(index.row()))
        
        menu.exec(self.track_list.mapToGlobal(pos))
        
    def _remove_track(self, row):
        self.model.removeRow(row)

    def _on_track_double_click(self, index):
        self.play_requested.emit(self.playlist_id)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.track_list.hasFocus():
            idx = self.track_list.currentIndex()
            if idx.isValid():
                self.model.removeRow(idx.row())
        else:
            super().keyPressEvent(event)



# =============================================================================
# Main View Container
# =============================================================================

class PlaylistsView(QStackedWidget):
    """Main Playlists View managing Grid vs Detail."""
    
    play_requested = Signal(int) # playlist_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.grid = PlaylistGridWidget()
        self.detail = PlaylistDetailWidget()
        
        self.grid.playlist_clicked.connect(self.show_detail)
        self.detail.back_clicked.connect(self.show_grid)
        self.detail.play_requested.connect(self.play_requested)
        
        self.addWidget(self.grid)
        self.addWidget(self.detail)
        
    def show_grid(self):
        self.grid.refresh()
        self.setCurrentWidget(self.grid)
        
    def show_detail(self, playlist_id):
        self.detail.set_playlist(playlist_id)
        self.setCurrentWidget(self.detail)
        
    def refresh(self):
        if self.currentWidget() == self.grid:
            self.grid.refresh()
        else:
            self.detail.refresh()
