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

def get_placeholder_cover(size: int = 200, seed: str = "", is_project: bool = False) -> QPixmap:
    """Generate a placeholder gradient cover."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#0f172a"))
    
    painter = QPainter(pixmap)
    gradient = QLinearGradient(0, 0, size, size)
    
    # Generate colors based on seed
    if seed:
        import hashlib
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        if is_project:
             # Golden/Orange theme for projects
             hue1 = (h % 60) + 20 # 20-80 (Orange/Yellow)
             hue2 = (hue1 + 30) % 360
             c1 = QColor.fromHsl(hue1, 200, 40)
             c2 = QColor.fromHsl(hue2, 220, 30)
        else:
             # Blue/Purple theme for tracks
             hue1 = (h % 60) + 200 # 200-260 (Blue/Purple)
             hue2 = (hue1 + 40) % 360
             c1 = QColor.fromHsl(hue1, 150, 60)
             c2 = QColor.fromHsl(hue2, 200, 40)
    else:
        c1 = QColor("#38bdf8")
        c2 = QColor("#334155")
        
    gradient.setColorAt(0, c1)
    gradient.setColorAt(1, c2)
    
    painter.fillRect(0, 0, size, size, gradient)
    
    # Draw simple icon
    from .icons import get_icon
    icon_name = "folder_open" if is_project else "music"
    # Actually we don't have 'music' maybe 'audio'
    if not is_project: icon_name = "audio"
    
    # Draw a centered icon (simplified)
    # We need to import get_icon or use primitives. 
    # For now just the gradient is enough to fix the crash.
    # But let's verify if we can draw an icon.
    # The 'get_icon' returns QIcon, we can paint it.
    
    try:
        from .icons import get_icon
        icon = get_icon(icon_name, QColor(255, 255, 255, 128), size // 2)
        icon.paint(painter, size//4, size//4, size//2, size//2)
    except:
        pass # Fallback to just gradient
    
    painter.end()
    return pixmap
