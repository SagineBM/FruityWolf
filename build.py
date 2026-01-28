"""
FruityWolf — Build Script

Build the application for distribution using PyInstaller.
Creates a fully bundled executable with all assets and dependencies.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.resolve()
SRC_DIR = PROJECT_ROOT / 'FruityWolf'
QML_DIR = PROJECT_ROOT / 'qml'
ASSETS_DIR = PROJECT_ROOT / 'assets'
RESOURCES_DIR = SRC_DIR / 'resources'
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'

APP_NAME = "FruityWolf"
APP_VERSION = "2.0.0"
APP_ICON = ASSETS_DIR / 'icon.ico'


def clean():
    """Clean build directories."""
    print("Cleaning build directories...")
    
    def remove_readonly(func, path, exc):
        """Handle read-only files on Windows."""
        os.chmod(path, 0o777)
        func(path)
    
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path, onerror=remove_readonly)
                print(f"  Removed: {dir_path}")
            except PermissionError as e:
                print(f"  WARNING: Could not remove {dir_path}")
                print(f"  Error: {e}")
                print(f"  Please close any programs using files in {dir_path}")
                print(f"  Or manually delete the folder and try again")


def ensure_icon():
    """Ensure ICO icon exists, create if needed."""
    if APP_ICON.exists():
        print(f"Icon found: {APP_ICON}")
        return True
    
    print(f"Creating ICO icon from SVG...")
    icon_script = PROJECT_ROOT / 'scripts' / 'create_icon.py'
    
    if icon_script.exists():
        result = subprocess.run([sys.executable, str(icon_script)], cwd=PROJECT_ROOT)
        if result.returncode == 0 and APP_ICON.exists():
            print(f"Icon created: {APP_ICON}")
            return True
    
    print(f"WARNING: Icon not found at {APP_ICON}")
    print("Build will continue without icon. Run: python scripts/create_icon.py")
    return False


def build(onefile=False):
    """
    Build the application using PyInstaller.
    
    Args:
        onefile: If True, create a single .exe file. If False, create a folder with .exe + dependencies.
    """
    build_type = "single-file" if onefile else "folder"
    print(f"\n{'='*60}")
    print(f"Building {APP_NAME} v{APP_VERSION} ({build_type} mode)")
    print(f"{'='*60}\n")
    
    # Ensure icon exists
    ensure_icon()
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}\n")
    except ImportError:
        print("ERROR: PyInstaller not installed!")
        print("Run: pip install pyinstaller")
        sys.exit(1)
    
    # Prepare data files
    data_files = []
    
    # QML files
    if QML_DIR.exists():
        data_files.append(f'{QML_DIR}{os.pathsep}qml')
        print(f"Including QML: {QML_DIR}")
    
    # Assets
    if ASSETS_DIR.exists():
        data_files.append(f'{ASSETS_DIR}{os.pathsep}assets')
        print(f"Including assets: {ASSETS_DIR}")
    
    # Resources (icons, etc.)
    if RESOURCES_DIR.exists():
        data_files.append(f'{RESOURCES_DIR}{os.pathsep}FruityWolf/resources')
        print(f"Including resources: {RESOURCES_DIR}")
    
    # Build command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--windowed',  # No console window
        '--noconfirm',  # Overwrite without asking
        '--clean',  # Clean cache
    ]
    
    # Choose build mode
    if onefile:
        cmd.append('--onefile')  # Single .exe file (can send via WhatsApp)
        print("Mode: Single-file executable (can send .exe alone)")
    else:
        cmd.append('--onedir')  # Folder with .exe + dependencies
        print("Mode: Folder distribution (need to send entire folder)")
    
    # Icon (if exists)
    
    if APP_ICON.exists():
        cmd.extend(['--icon', str(APP_ICON)])
        print(f"Using icon: {APP_ICON}")
    
    # Add data files
    for data in data_files:
        cmd.extend(['--add-data', data])
    
    # Hidden imports
    hidden_imports = [
        'PySide6.QtQuick',
        'PySide6.QtQml',
        'PySide6.QtQuickControls2',
        'PySide6.QtMultimedia',
        'PySide6.QtSvg',
        'vlc',
        'numpy',
        'soundfile',
        'mutagen',
        'watchdog',
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # Collect all PySide6 plugins
    cmd.extend(['--collect-all', 'PySide6'])
    
    # Note: VLC binaries are complex to bundle
    # The app has Qt Multimedia fallback, so VLC is optional
    # Users can install VLC separately for best audio support
    print("Note: VLC is optional - app will use Qt Multimedia fallback if VLC not available")
    
    # Entry point
    cmd.append(str(SRC_DIR / '__main__.py'))
    
    print(f"\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd[:15])}...\n")
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode != 0:
        print("\nERROR: Build failed!")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("Build complete!")
    print(f"{'='*60}\n")
    
    # Verify build
    if onefile:
        exe_path = DIST_DIR / f'{APP_NAME}.exe'
        output_folder = DIST_DIR / f'{APP_NAME}-SingleFile'
    else:
        exe_path = DIST_DIR / APP_NAME / f'{APP_NAME}.exe'
        output_folder = DIST_DIR / f'{APP_NAME}-Folder'
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"Executable size: {size_mb:.1f} MB")
        
        # Organize output into named folder
        if onefile:
            # Move single-file exe to named folder
            output_folder.mkdir(exist_ok=True)
            target_exe = output_folder / f'{APP_NAME}.exe'
            if target_exe.exists():
                target_exe.unlink()
            exe_path.rename(target_exe)
            print(f"\nSingle-file executable ready!")
            print(f"  Location: {output_folder}")
            print(f"  File: {target_exe.name}")
            print(f"  You can zip this ONE file and send via WhatsApp/email")
        else:
            # Rename folder to distinguish it
            if output_folder.exists():
                import shutil
                shutil.rmtree(output_folder)
            (DIST_DIR / APP_NAME).rename(output_folder)
            print(f"\nFolder distribution ready!")
            print(f"  Location: {output_folder}")
            print(f"  Send the ENTIRE folder (or zip it)")
    else:
        print("WARNING: Executable not found!")


def create_installer():
    """Create NSIS installer (requires NSIS installed)."""
    print("\n" + "="*60)
    print("Creating Windows Installer...")
    print("="*60)
    
    nsis_script = PROJECT_ROOT / 'installer.nsi'
    
    if not nsis_script.exists():
        print(f"ERROR: Installer script not found: {nsis_script}")
        print("Please ensure installer.nsi exists in the project root.")
        return
    
    # Check if NSIS is available
    nsis_path = shutil.which('makensis')
    if not nsis_path:
        print("\nERROR: NSIS not found!")
        print("The installer cannot be created without NSIS.")
        print("\nTo create an installer:")
        print("  1. Download NSIS from https://nsis.sourceforge.io/")
        print("  2. Install it and add to PATH")
        print("  3. Re-run: python build.py --both")
        print("\nFor now, you can use:")
        print(f"  - Single-file: dist\\{APP_NAME}-SingleFile\\{APP_NAME}.exe")
        print(f"  - Folder: dist\\{APP_NAME}-Folder\\")
        return
    
    print(f"Using NSIS: {nsis_path}")
    print(f"Script: {nsis_script}\n")
    
    # Look for folder distribution (needed for installer)
    folder_dist = DIST_DIR / f'{APP_NAME}-Folder'
    if not folder_dist.exists():
        # Try old name
        folder_dist = DIST_DIR / APP_NAME
    
    dist_exe = folder_dist / f'{APP_NAME}.exe'
    if not dist_exe.exists():
        print(f"ERROR: Folder distribution not found!")
        print(f"Looking for: {dist_exe}")
        print("Please run build first: python build.py")
        return
    
    # Update installer script to use correct folder name
    installer_output_folder = DIST_DIR / f'{APP_NAME}-Installer'
    installer_output_folder.mkdir(exist_ok=True)
    
    # Create temporary installer script with updated paths
    temp_nsis = PROJECT_ROOT / 'installer_temp.nsi'
    nsis_content = nsis_script.read_text()
    # Update output path and source folder (handle both old and new formats)
    # Replace OutFile path
    if f'OutFile "dist\\{APP_NAME}-Installer\\{APP_NAME}-Setup.exe"' not in nsis_content:
        # Try old format first
        nsis_content = nsis_content.replace(
            f'OutFile "dist\\{APP_NAME}-Setup.exe"',
            f'OutFile "dist\\{APP_NAME}-Installer\\{APP_NAME}-Setup.exe"'
        )
        # Also handle if it's already updated in installer.nsi
        nsis_content = nsis_content.replace(
            f'OutFile "dist\\\\{APP_NAME}-Installer\\\\{APP_NAME}-Setup.exe"',
            f'OutFile "dist\\{APP_NAME}-Installer\\{APP_NAME}-Setup.exe"'
        )
    
    # Replace File source path
    if f'File /r "dist\\{APP_NAME}-Folder\\*.*"' not in nsis_content:
        # Try old format first
        nsis_content = nsis_content.replace(
            f'File /r "dist\\{APP_NAME}\\*.*"',
            f'File /r "dist\\{APP_NAME}-Folder\\*.*"'
        )
        # Also handle if already updated
        nsis_content = nsis_content.replace(
            f'File /r "dist\\\\{APP_NAME}-Folder\\\\*.*"',
            f'File /r "dist\\{APP_NAME}-Folder\\*.*"'
        )
    temp_nsis.write_text(nsis_content)
    
    # Run NSIS
    result = subprocess.run([nsis_path, str(temp_nsis)], cwd=PROJECT_ROOT)
    
    # Cleanup temp script
    if temp_nsis.exists():
        temp_nsis.unlink()
    
    installer_exe = installer_output_folder / f'{APP_NAME}-Setup.exe'
    if result.returncode == 0 and installer_exe.exists():
        size_mb = installer_exe.stat().st_size / (1024 * 1024)
        print(f"\n✓ Installer created successfully!")
        print(f"  Location: {installer_output_folder}")
        print(f"  File: {installer_exe.name}")
        print(f"  Size: {size_mb:.1f} MB")
    else:
        print("\n✗ ERROR: Installer creation failed!")
        print(f"  NSIS exit code: {result.returncode}")
        if not installer_exe.exists():
            print(f"  Expected file not found: {installer_exe}")
        print("\nCheck NSIS installation and try running manually:")
        print(f"  makensis installer.nsi")


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
    
    parser = argparse.ArgumentParser(description='Build FruityWolf')
    parser.add_argument('--clean', action='store_true', help='Clean build directories')
    parser.add_argument('--installer', action='store_true', help='Create NSIS installer (also builds single-file)')
    parser.add_argument('--assets', action='store_true', help='Create placeholder assets')
    parser.add_argument('--onefile', action='store_true', help='Create single .exe file only (can send via WhatsApp)')
    parser.add_argument('--both', action='store_true', help='Build BOTH single-file AND installer (recommended)')
    parser.add_argument('--force-clean', action='store_true', help='Force clean before building')
    
    args = parser.parse_args()
    
    if args.assets:
        create_assets()
        return
    
    if args.clean:
        clean()
        return
    
    # Force clean if requested
    if args.force_clean:
        print("Force cleaning before build...")
        clean()
        import time
        time.sleep(1)  # Give Windows time to release file handles
    
    # Ensure assets exist
    create_assets()
    
    # Build strategy: Create both single-file AND installer
    if args.both:
        # Build both versions
        build_single = True
        build_folder = True
        create_installer_flag = True
        print("\n[INFO] --both flag detected: Will build single-file, folder, AND installer")
    elif args.installer:
        # Build both versions for installer
        build_single = True
        build_folder = True
        create_installer_flag = True
    elif args.onefile:
        # Build only single-file
        build_single = True
        build_folder = False
        create_installer_flag = False
    else:
        # Default: build folder only
        build_single = False
        build_folder = True
        create_installer_flag = False
    
    # Build single-file version
    if build_single:
        print("\n" + "="*60)
        print("Building SINGLE-FILE version...")
        print("="*60)
        build(onefile=True)
    
    # Build folder version (needed for installer)
    if build_folder:
        print("\n" + "="*60)
        print("Building FOLDER version...")
        print("="*60)
        build(onefile=False)
    
    # Create installer if requested
    if create_installer_flag:
        print("\n" + "="*60)
        print("STEP 3: Creating Windows Installer...")
        print("="*60)
        print("[INFO] Calling create_installer()...")
        create_installer()
        print("[INFO] create_installer() completed")
    
    # Summary
    print("\n" + "="*60)
    print("BUILD SUMMARY")
    print("="*60)
    
    single_file = DIST_DIR / f'{APP_NAME}-SingleFile' / f'{APP_NAME}.exe'
    folder_dist = DIST_DIR / f'{APP_NAME}-Folder'
    installer_file = DIST_DIR / f'{APP_NAME}-Installer' / f'{APP_NAME}-Setup.exe'
    
    if single_file.exists():
        size = single_file.stat().st_size / (1024 * 1024)
        print(f"\n[1] Single-File Executable:")
        print(f"    Folder: {APP_NAME}-SingleFile")
        print(f"    File: {APP_NAME}.exe ({size:.1f} MB)")
        print(f"    Use: Zip this ONE file and send via WhatsApp")
    
    if folder_dist.exists():
        print(f"\n[2] Folder Distribution:")
        print(f"    Folder: {APP_NAME}-Folder")
        print(f"    Use: Zip entire folder and send")
    
    if installer_file.exists():
        size = installer_file.stat().st_size / (1024 * 1024)
        print(f"\n[3] Windows Installer:")
        print(f"    Folder: {APP_NAME}-Installer")
        print(f"    File: {APP_NAME}-Setup.exe ({size:.1f} MB)")
        print(f"    Use: Professional installation with shortcuts")
    
    print(f"\nAll builds are in: {DIST_DIR}")
    print("="*60)


if __name__ == '__main__':
    main()
