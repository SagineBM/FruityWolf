# Building FruityWolf for Distribution

This guide explains how to build FruityWolf into a standalone executable and installer for Windows.

## Prerequisites

1. **Python 3.11+** installed
2. **All dependencies** installed:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller Pillow cairosvg
   ```

3. **NSIS** (for creating installer - optional):
   - Download from https://nsis.sourceforge.io/
   - Install and add to PATH

## Quick Build

### Step 1: Create Icon (if needed)

If `assets/icon.ico` doesn't exist, create it from SVG:

```bash
python scripts/create_icon.py
```

### Step 2: Build Executable

```bash
python build.py
```

This will:
- Create the ICO icon if missing
- Bundle all assets, resources, and dependencies
- Create a standalone executable in `dist/FruityWolf/`

### Step 3: Create Installer (Optional)

```bash
python build.py --installer
```

Or manually:
```bash
makensis installer.nsi
```

The installer will be created at `dist/FruityWolf-Setup.exe`

## Build Options

```bash
# Clean build directories
python build.py --clean

# Create placeholder assets
python build.py --assets

# Build with installer
python build.py --installer
```

## What Gets Bundled

The build process automatically includes:

- ✅ All Python code (`FruityWolf/` directory)
- ✅ QML files (`qml/` directory)
- ✅ Assets (`assets/` directory)
- ✅ Resources/icons (`FruityWolf/resources/` directory)
- ✅ PySide6 Qt libraries and plugins
- ✅ VLC player binaries (if available)
- ✅ NumPy, SoundFile, Mutagen, Watchdog
- ✅ Application icon (Windows .ico file)

## Output Structure

After building:

```
dist/
└── FruityWolf/
    ├── FruityWolf.exe          # Main executable
    ├── _internal/              # Python runtime and libraries
    ├── qml/                    # QML files
    ├── assets/                 # Application assets
    └── FruityWolf/resources/   # Icons and resources
```

## Testing the Build

1. Navigate to `dist/FruityWolf/`
2. Run `FruityWolf.exe`
3. Verify:
   - App icon appears in taskbar
   - All features work correctly
   - No missing file errors

## Distribution

### Standalone Distribution

Simply zip the entire `dist/FruityWolf/` folder and distribute it. Users can extract and run `FruityWolf.exe` directly.

### Installer Distribution

Distribute `dist/FruityWolf-Setup.exe`. Users can:
1. Run the installer
2. Choose installation directory
3. Get Start Menu and Desktop shortcuts
4. Uninstall via Windows Settings

## Troubleshooting

### Icon Not Showing

- Ensure `assets/icon.ico` exists
- Run `python scripts/create_icon.py` to create it
- Check that icon path in spec file is correct

### Missing Dependencies

If users report missing DLLs or modules:
- Ensure `--collect-all PySide6` is in build command
- Check that all hidden imports are listed
- Verify VLC binaries are bundled if audio playback is needed

### Large File Size

The executable includes Python runtime and all dependencies. Typical size:
- Executable folder: 150-300 MB
- Installer: 100-200 MB (compressed)

To reduce size:
- Use `--exclude-module` for unused modules
- Enable UPX compression (already enabled)

## Advanced: Custom Build

Edit `FruityWolf.spec` for custom build configuration:

```python
# Add custom data files
datas += [('path/to/data', 'destination')]

# Add custom hidden imports
hiddenimports += ['custom.module']

# Modify icon
icon = 'path/to/custom.ico'
```

Then build with:
```bash
pyinstaller FruityWolf.spec
```

## Notes

- The app icon is set both in the executable (via PyInstaller) and at runtime (via QApplication)
- All paths are resolved relative to the project root
- The build script handles Windows path separators automatically
- First-time builds may take 5-10 minutes
