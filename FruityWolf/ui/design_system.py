"""
Design System for FruityWolf

Centralized tokens and base widgets for a cinematic, premium UI.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor

class DesignTokens:
    # Palette
    BG_MAIN = "#0E1117"
    BG_PANEL = "#1A2230"
    BG_PANEL_HOVER = "#242E3E"
    
    ACCENT_PRIMARY = "#2BD9C5"   # Electric Teal
    ACCENT_SECONDARY = "#8B5CF6" # Vivid Purple
    ACCENT_WARNING = "#F4C430"   # Warm Amber
    ACCENT_SUCCESS = "#3DFF91"   # Neon Green
    ACCENT_DANGER = "#FF5C5C"    # Soft Red
    
    TEXT_PRIMARY = "#E6EDF3"
    TEXT_SECONDARY = "#9BA7B4"
    TEXT_MUTED = "#6B7785"
    
    # Spacing
    XS = 8
    S = 12
    M = 16
    L = 24
    
    # Radius
    RS = 10
    RM = 14
    RL = 18

class BaseCard(QFrame):
    """A premium, reusable card with shadows and hover effects."""
    def __init__(self, parent=None, hover_effect=True):
        super().__init__(parent)
        self.hover_enabled = hover_effect
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("BaseCard")
        
        # Default styling
        self.setStyleSheet(f"""
            #BaseCard {{
                background-color: {DesignTokens.BG_PANEL};
                border-radius: {DesignTokens.RM}px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        # Shadow effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self.shadow)

        if self.hover_enabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        if self.hover_enabled:
            self.setStyleSheet(f"""
                #BaseCard {{
                    background-color: {DesignTokens.BG_PANEL_HOVER};
                    border-radius: {DesignTokens.RM}px;
                    border: 1px solid {DesignTokens.ACCENT_PRIMARY}44;
                }}
            """)
            self.shadow.setBlurRadius(30)
            self.shadow.setColor(QColor(DesignTokens.ACCENT_PRIMARY + "22"))
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.hover_enabled:
            self.setStyleSheet(f"""
                #BaseCard {{
                    background-color: {DesignTokens.BG_PANEL};
                    border-radius: {DesignTokens.RM}px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
            """)
            self.shadow.setBlurRadius(20)
            self.shadow.setColor(QColor(0, 0, 0, 80))
        super().leaveEvent(event)
