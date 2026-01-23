"""
Image Utilities
"""

import os
import logging
from typing import Optional
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QLinearGradient

logger = logging.getLogger(__name__)

COVER_NAMES = ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png', 'thumb.jpg', 'artwork.jpg']

def get_cover_art(project_path: str) -> Optional[str]:
    """
    Find cover art in the project folder.
    Returns path to image or None.
    """
    if not project_path or not os.path.isdir(project_path):
        return None
        
    for name in COVER_NAMES:
        path = os.path.join(project_path, name)
        if os.path.exists(path):
            return path
            
    return None

def get_placeholder_cover(size: int = 200, seed: str = "") -> QPixmap:
    """Generate a placeholder gradient cover."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#0f172a"))
    
    painter = QPainter(pixmap)
    gradient = QLinearGradient(0, 0, size, size)
    
    # Generate colors based on seed
    if seed:
        import hashlib
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        hue1 = h % 360
        hue2 = (hue1 + 40) % 360
        c1 = QColor.fromHsl(hue1, 150, 60)
        c2 = QColor.fromHsl(hue2, 200, 40)
    else:
        c1 = QColor("#38bdf8")
        c2 = QColor("#334155")
        
    gradient.setColorAt(0, c1)
    gradient.setColorAt(1, c2)
    
    painter.fillRect(0, 0, size, size, gradient)
    
    # Draw simple icon or text?
    # For now just gradient is fine
    
    painter.end()
    return pixmap
