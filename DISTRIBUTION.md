# Distribution Guide - FruityWolf

## What Gets Bundled ✅

When you build FruityWolf with `python build.py`, the following are **automatically included**:

### ✅ Fully Bundled (No Additional Setup Needed)
- **Python Runtime** - Complete Python interpreter
- **PySide6 Qt Libraries** - All GUI components and widgets
- **All Python Dependencies**:
  - NumPy, SciPy, Librosa (audio analysis)
  - SoundFile, Mutagen (audio file handling)
  - Watchdog (file system monitoring)
  - Pillow (image processing)
- **Application Assets**:
  - Icons, images, QML files
  - All resources and fonts
- **Application Icon** - Shows in taskbar, window, and file explorer

### ⚠️ Partially Bundled (May Need Additional Setup)

**VLC Player** - Audio Playback Backend:
- The `python-vlc` Python package is bundled
- **BUT**: VLC requires native DLLs that may not be bundled
- **Fallback**: App will use Qt Multimedia if VLC fails (may have limited codec support)

## What Users Need

### Minimum Requirements
- **Windows 10 or later** (64-bit)
- **No Python installation needed** ✅
- **No additional software needed** for basic functionality ✅

### Optional (For Best Audio Playback)
- **VLC Media Player** installed separately
  - Download from: https://www.videolan.org/vlc/
  - The app will automatically detect and use it
  - If not installed, Qt Multimedia fallback will be used

### Visual C++ Redistributables
- Usually already installed on Windows 10/11
- If missing, Windows will prompt to install automatically
- Can be manually installed: https://aka.ms/vs/17/release/vc_redist.x64.exe

## Distribution Methods

### Option 1: Standalone Executable (Recommended)
**File**: `dist/FruityWolf/FruityWolf.exe`

**Pros**:
- ✅ Single folder to distribute
- ✅ No installation needed
- ✅ Users can run directly

**Cons**:
- ❌ Larger file size (~200-300 MB)
- ❌ No Start Menu shortcuts
- ❌ No uninstaller

**How to Distribute**:
1. Zip the entire `dist/FruityWolf/` folder
2. Users extract and run `FruityWolf.exe`

### Option 2: Windows Installer (Professional)
**File**: `dist/FruityWolf-Setup.exe`

**Pros**:
- ✅ Professional installation experience
- ✅ Start Menu shortcuts
- ✅ Desktop shortcut
- ✅ Add/Remove Programs entry
- ✅ Uninstaller included

**Cons**:
- ❌ Requires NSIS to build
- ❌ Users need admin rights to install

**How to Distribute**:
1. Build installer: `python build.py --installer`
2. Distribute `FruityWolf-Setup.exe`
3. Users run installer (may need admin rights)

## Testing Before Distribution

### ✅ Test Checklist

1. **On a Clean Windows Machine** (or VM):
   - [ ] Extract/install the app
   - [ ] Run without Python installed
   - [ ] Verify app icon appears
   - [ ] Test library scanning
   - [ ] Test audio playback (with and without VLC)
   - [ ] Test all UI features
   - [ ] Check for missing DLL errors

2. **Test Audio Playback**:
   - [ ] With VLC installed: Should work perfectly
   - [ ] Without VLC: Should use Qt Multimedia fallback
   - [ ] Test various audio formats (MP3, WAV, FLAC, etc.)

3. **Test File Operations**:
   - [ ] Opening FL Studio projects
   - [ ] Opening folders
   - [ ] File system watching

## Known Limitations

### VLC Dependency
- **Issue**: VLC DLLs may not be fully bundled
- **Solution**: App has Qt Multimedia fallback
- **User Impact**: Some audio formats may not play without VLC installed
- **Recommendation**: Include VLC installation instructions in README

### File Size
- **Typical Size**: 200-300 MB (includes Python runtime)
- **Reason**: Bundles complete Python interpreter and all dependencies
- **Mitigation**: Use UPX compression (already enabled in build)

### First Launch
- **May be slower**: First launch extracts/caches files
- **Subsequent launches**: Much faster

## User Instructions

### For Standalone Executable:
```
1. Extract FruityWolf.zip
2. Double-click FruityWolf.exe
3. (Optional) Install VLC for best audio playback
```

### For Installer:
```
1. Run FruityWolf-Setup.exe
2. Follow installation wizard
3. Launch from Start Menu or Desktop
4. (Optional) Install VLC for best audio playback
```

## Troubleshooting for End Users

### "Missing DLL" Errors
- **Solution**: Install Visual C++ Redistributables
- **Link**: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Audio Not Playing
- **Solution**: Install VLC Media Player
- **Link**: https://www.videolan.org/vlc/
- **Note**: App will still work, but with limited codec support

### App Won't Start
- **Check**: Windows 10/11 (64-bit) required
- **Check**: Antivirus may be blocking (add exception)
- **Check**: Run as administrator if needed

## Summary

✅ **Yes, users can run it without Python or any other dependencies!**

The executable is **fully standalone** and includes:
- Python runtime
- All Python libraries
- Qt GUI framework
- All assets and resources

⚠️ **Optional**: VLC installation recommended for best audio playback experience

The app will work without VLC, but some audio formats may not be supported.
