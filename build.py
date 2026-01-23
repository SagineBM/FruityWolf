"""
FruityWolf — Build Script

Build the application for distribution using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / 'FruityWolf'
QML_DIR = PROJECT_ROOT / 'qml'
ASSETS_DIR = PROJECT_ROOT / 'assets'
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'

APP_NAME = "FruityWolf"
APP_VERSION = "2.0.0"
APP_ICON = ASSETS_DIR / 'icon.ico'


def clean():
    """Clean build directories."""
    print("Cleaning build directories...")
    
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")


def build():
    """Build the application using PyInstaller."""
    print(f"\n{'='*60}")
    print(f"Building {APP_NAME} v{APP_VERSION}")
    print(f"{'='*60}\n")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller not installed!")
        print("Run: pip install pyinstaller")
        sys.exit(1)
    
    # Build command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--windowed',  # No console window
        '--noconfirm',  # Overwrite without asking
        '--clean',  # Clean cache
        
        # Icon
        '--icon', str(APP_ICON) if APP_ICON.exists() else '',
        
        # Add data files
        '--add-data', f'{QML_DIR};qml',
        '--add-data', f'{ASSETS_DIR};assets',
        
        # Hidden imports (PySide6 plugins)
        '--hidden-import', 'PySide6.QtQuick',
        '--hidden-import', 'PySide6.QtQml',
        '--hidden-import', 'PySide6.QtQuickControls2',
        '--hidden-import', 'PySide6.QtMultimedia',
        
        # VLC handling
        '--hidden-import', 'vlc',
        
        # Collect all PySide6 plugins
        '--collect-all', 'PySide6',
        
        # Entry point
        str(SRC_DIR / '__main__.py'),
    ]
    
    # Filter empty arguments
    cmd = [arg for arg in cmd if arg]
    
    print("Running PyInstaller...")
    print(f"Command: {' '.join(cmd[:10])}...")
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode != 0:
        print("\nERROR: Build failed!")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("Build complete!")
    print(f"Output: {DIST_DIR / APP_NAME}")
    print(f"{'='*60}")


def create_installer():
    """Create NSIS installer (requires NSIS installed)."""
    print("\nCreating installer with NSIS...")
    
    nsis_script = PROJECT_ROOT / 'installer.nsi'
    
    # Check if NSIS is available
    nsis_path = shutil.which('makensis')
    if not nsis_path:
        print("NSIS not found. Skipping installer creation.")
        print("To create an installer, install NSIS and add it to PATH.")
        return
    
    # Create NSIS script
    nsis_content = f'''
!include "MUI2.nsh"

Name "{APP_NAME}"
OutFile "dist\\{APP_NAME.replace(' ', '-')}-Setup.exe"
InstallDir "$PROGRAMFILES\\{APP_NAME}"
RequestExecutionLevel admin

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath $INSTDIR
    
    ; Copy files
    File /r "dist\\{APP_NAME}\\*.*"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\{APP_NAME}"
    CreateShortCut "$SMPROGRAMS\\{APP_NAME}\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    CreateShortCut "$DESKTOP\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    ; Registry entries
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayName" "{APP_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayVersion" "{APP_VERSION}"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\\{APP_NAME}\\{APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\\{APP_NAME}"
    Delete "$DESKTOP\\{APP_NAME}.lnk"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}"
SectionEnd
'''
    
    nsis_script.write_text(nsis_content)
    
    # Run NSIS
    result = subprocess.run([nsis_path, str(nsis_script)], cwd=PROJECT_ROOT)
    
    if result.returncode == 0:
        print(f"Installer created: dist/{APP_NAME.replace(' ', '-')}-Setup.exe")
    else:
        print("Installer creation failed.")
    
    # Cleanup
    nsis_script.unlink()


def create_assets():
    """Create placeholder assets if they don't exist."""
    ASSETS_DIR.mkdir(exist_ok=True)
    
    # Create placeholder icon if missing
    icon_path = ASSETS_DIR / 'icon.png'
    if not icon_path.exists():
        print("Creating placeholder icon...")
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a gradient icon
            size = 256
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw gradient background
            for i in range(size):
                color = (
                    int(29 + (30 - 29) * i / size),
                    int(185 + (215 - 185) * i / size),
                    int(84 + (96 - 84) * i / size),
                    255
                )
                draw.ellipse([i//4, i//4, size-i//4, size-i//4], fill=color)
            
            # Draw text
            try:
                font = ImageFont.truetype("arial.ttf", 80)
            except:
                font = ImageFont.load_default()
            
            draw.text((size//2, size//2), "FL", fill=(0, 0, 0, 255), anchor="mm", font=font)
            
            img.save(icon_path)
            
            # Also save ICO for Windows
            ico_path = ASSETS_DIR / 'icon.ico'
            img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            
            print(f"  Created: {icon_path}")
            print(f"  Created: {ico_path}")
            
        except ImportError:
            print("  Pillow not installed, skipping icon generation")
    
    # Create fonts directory
    fonts_dir = ASSETS_DIR / 'fonts'
    fonts_dir.mkdir(exist_ok=True)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build FL Library Pro')
    parser.add_argument('--clean', action='store_true', help='Clean build directories')
    parser.add_argument('--installer', action='store_true', help='Create NSIS installer')
    parser.add_argument('--assets', action='store_true', help='Create placeholder assets')
    
    args = parser.parse_args()
    
    if args.assets:
        create_assets()
        return
    
    if args.clean:
        clean()
        return
    
    # Ensure assets exist
    create_assets()
    
    # Build
    build()
    
    # Create installer if requested
    if args.installer:
        create_installer()


if __name__ == '__main__':
    main()
