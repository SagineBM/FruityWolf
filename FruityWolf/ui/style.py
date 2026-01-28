"""
Stylesheet Generator for FruityWolf.
Compiles design tokens into QSS.
"""

from .style_tokens import DARK_THEME, ThemeColors, RADIUS_LG, RADIUS_MD, RADIUS_SM, RADIUS_PILL, FONT_MAIN, FONT_MONO

def get_stylesheet(theme: ThemeColors = DARK_THEME) -> str:
    """Generate the application stylesheet based on tokens."""
    
    return f"""
QMainWindow, QWidget {{
    background-color: {theme.bg_base};
    color: {theme.text_main};
    font-family: {FONT_MAIN};
    font-size: 13px;
}}

QMenuBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(17, 24, 32, 0.95),
        stop:0.4 rgba(30, 41, 59, 0.85),
        stop:0.6 rgba(30, 41, 59, 0.85),
        stop:1 rgba(17, 24, 32, 0.95));
    border-bottom: 1px solid rgba(30, 41, 59, 0.5);
    color: {theme.text_main};
    padding: 4px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background: rgba(30, 41, 59, 0.6);
}}

QMenuBar::item:pressed {{
    background: rgba(51, 65, 85, 0.7);
}}

QMenu {{
    background: rgba(17, 24, 32, 0.98);
    border: 1px solid rgba(30, 41, 59, 0.6);
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background: rgba(30, 41, 59, 0.6);
}}

*:focus {{
    border: 1px solid {theme.border_focus};
    outline: none;
}}

QFrame#sidebar {{
    background-color: {theme.bg_sidebar};
    border-right: 1px solid {theme.border_subtle};
}}

QLabel {{
    background: transparent;
}}

QFrame#mainArea {{
    background-color: {theme.bg_base};
}}

QFrame#playerBar {{
    background-color: {theme.bg_player};
    border-top: 1px solid {theme.border_subtle};
    border-radius: 0px; 
}}

QScrollArea#detailsScroll {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(30, 41, 59, 0.8),
        stop:0.5 rgba(51, 65, 85, 0.9),
        stop:1 rgba(30, 41, 59, 0.8));
    border: none;
}}

QScrollArea#detailsScroll > QWidget > QWidget {{
    background: transparent;
}}

QLabel#logo {{
    font-size: 18px;
    font-weight: bold;
    color: {theme.accent_primary};
    padding: 8px;
}}

QLabel#sectionTitle {{
    font-size: 10px;
    font-weight: bold;
    color: {theme.text_dim};
    padding: 12px 0 6px 0;
    letter-spacing: 1.5px;
}}

QPushButton#navButton {{
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: {theme.text_muted};
    font-size: 14px;
    font-weight: 500;
}}

QPushButton#navButton:hover {{
    background: {theme.bg_card};
    color: {theme.text_main};
}}

QPushButton#navButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(56,189,248,0.15), stop:1 transparent);
    color: {theme.text_main};
    border-left: 3px solid {theme.accent_primary};
}}

QPushButton#actionButton {{
    padding: 12px 20px;
    border: none;
    border-radius: {RADIUS_PILL};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme.accent_primary}, stop:1 {theme.accent_secondary});
    color: {theme.bg_base};
    font-weight: bold;
    font-size: 13px;
}}

QPushButton#actionButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7dd3fc, stop:1 {theme.accent_primary});
}}

QPushButton#actionButton:disabled {{
    background: #283344;
    color: {theme.text_dim};
}}

QPushButton#secondaryButton {{
    padding: 8px 16px;
    border: 1px solid #334155;
    border-radius: {RADIUS_MD};
    background: transparent;
    color: {theme.text_main};
    font-size: 12px;
}}

QPushButton#secondaryButton:hover {{
    border-color: {theme.accent_primary};
    color: {theme.accent_primary};
}}

QLineEdit#searchInput {{
    padding: 10px 20px;
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 18px;
    background: rgba(30, 41, 59, 0.7);
    color: {theme.text_main};
    font-size: 14px;
    selection-background-color: {theme.accent_primary};
}}

QLineEdit#searchInput:focus {{
    background: rgba(51, 65, 85, 0.8);
    border-color: rgba(56,189,248,0.5);
}}

QTableWidget#trackList, QTableView#trackList {{
    background: transparent;
    border: none;
    font-size: 13px;
    outline: none;
    gridline-color: transparent;
}}

QTableWidget#trackList::item, QTableView#trackList::item {{
    padding: 4px;
    border-bottom: 1px solid {theme.border_subtle};
}}

QHeaderView::section {{
    background: {theme.bg_base};
    color: {theme.text_dim};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {theme.border_subtle};
    font-weight: bold;
    font-size: 11px;
}}

QPushButton#playerButton {{
    min-width: 40px;
    min-height: 40px;
    max-width: 40px;
    max-height: 40px;
    border: none;
    border-radius: 20px;
    background: transparent;
    color: {theme.text_muted};
    font-size: 18px;
    font-weight: bold;
}}

QPushButton#playerButton:hover {{
    color: {theme.text_main};
    background: {theme.bg_card};
}}

QPushButton#playButton {{
    min-width: 48px;
    min-height: 48px;
    max-width: 48px;
    max-height: 48px;
    border: none;
    border-radius: 24px;
    background: {theme.text_main};
    color: {theme.bg_base};
    font-size: 20px;
    font-weight: bold;
}}

QPushButton#playButton:hover {{
    background: {theme.accent_primary};
}}

QProgressBar {{
    border: none;
    border-radius: 4px;
    background: {theme.border_subtle};
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme.accent_primary}, stop:1 #7dd3fc);
}}

QComboBox {{
    padding: 8px 14px;
    border: 1px solid #334155;
    border-radius: {RADIUS_MD};
    background: {theme.bg_player};
    color: {theme.text_main};
    font-size: 13px;
}}

QComboBox QAbstractItemView {{
    background: {theme.bg_player};
    border: 1px solid {theme.border_subtle};
    selection-background-color: #283344;
    border-radius: 8px;
}}

QToolTip {{
    background: {theme.bg_card};
    color: {theme.text_main};
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

QDialog {{
    background: {theme.bg_player};
}}
    """
