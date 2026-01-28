"""
Create ICO file from SVG for Windows executable.
Uses PySide6's built-in SVG support (no external dependencies needed).
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import QSize, QBuffer, QIODevice
except ImportError as e:
    print(f"ERROR: Required packages not installed!")
    print(f"Missing: {e}")
    print("Install with: pip install Pillow")
    print("(PySide6 should already be installed for FruityWolf)")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / 'assets'
ICON_SVG = ASSETS_DIR / 'FruityWolf_icons' / 'app_icon.svg'
ICON_ICO = ASSETS_DIR / 'icon.ico'

def svg_to_ico(svg_path, ico_path, sizes=[256, 128, 64, 48, 32, 16]):
    """Convert SVG to ICO with multiple sizes using PySide6."""
    if not svg_path.exists():
        print(f"ERROR: SVG file not found: {svg_path}")
        return False
    
    print(f"Converting {svg_path.name} to ICO using PySide6...")
    
    # Load SVG
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        print(f"ERROR: Invalid SVG file: {svg_path}")
        return False
    
    # Convert SVG to PNG for each size
    images = []
    for size in sizes:
        try:
            # Create QImage
            image = QImage(size, size, QImage.Format.Format_ARGB32)
            image.fill(0x00000000)  # Transparent background
            
            # Render SVG to QImage
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            
            # Convert QImage to PIL Image
            # Save QImage to QBuffer and load with PIL
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if image.save(buffer, 'PNG'):
                buffer.close()
                # Get bytes from QBuffer
                img_bytes = buffer.data().data()
                # Load with PIL
                from io import BytesIO
                pil_img = Image.open(BytesIO(img_bytes))
                images.append(pil_img)
            else:
                buffer.close()
                raise Exception("Failed to save QImage to buffer")
            print(f"  Created {size}x{size} icon")
        except Exception as e:
            print(f"  Warning: Failed to create {size}x{size}: {e}")
    
    if not images:
        print("ERROR: No icon sizes created!")
        return False
    
    # Save as ICO
    try:
        ico_path.parent.mkdir(parents=True, exist_ok=True)
        images[0].save(
            str(ico_path),
            format='ICO',
            sizes=[(img.width, img.height) for img in images]
        )
        print(f"\nSuccessfully created: {ico_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to save ICO: {e}")
        return False

if __name__ == '__main__':
    if not ICON_SVG.exists():
        print(f"ERROR: Icon SVG not found at {ICON_SVG}")
        print("Please ensure the app_icon.svg exists in assets/FruityWolf_icons/")
        sys.exit(1)
    
    success = svg_to_ico(ICON_SVG, ICON_ICO)
    sys.exit(0 if success else 1)
