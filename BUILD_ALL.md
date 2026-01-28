# Build All Versions - Quick Guide

## Build Both Single-File AND Installer

To create **both** the single-file executable AND the installer:

```bash
python build.py --both
```

Or:

```bash
python build.py --installer
```

Both commands will create:

### Output Structure

```
dist/
├── FruityWolf-SingleFile/
│   └── FruityWolf.exe          ← Single file (zip this!)
│
├── FruityWolf-Folder/
│   ├── FruityWolf.exe
│   └── _internal/              ← All dependencies
│
└── FruityWolf-Installer/
    └── FruityWolf-Setup.exe    ← Windows installer
```

## What Each Version Is For

### 1. Single-File Executable (`FruityWolf-SingleFile/`)
- **File**: `FruityWolf.exe` (one file, ~200-300 MB)
- **Use**: Zip this ONE file and send via WhatsApp/email
- **Best for**: Quick sharing with friends
- **User experience**: Download → Extract → Double-click

### 2. Folder Distribution (`FruityWolf-Folder/`)
- **Contents**: `FruityWolf.exe` + `_internal/` folder
- **Use**: Zip entire folder and send
- **Best for**: Distribution when you want faster startup
- **User experience**: Download → Extract → Run `FruityWolf.exe`

### 3. Windows Installer (`FruityWolf-Installer/`)
- **File**: `FruityWolf-Setup.exe` (~100-200 MB compressed)
- **Use**: Professional installation
- **Best for**: Official releases, distribution websites
- **User experience**: Run installer → Choose location → Get shortcuts

## Quick Commands

```bash
# Build BOTH single-file AND installer (recommended)
python build.py --both

# Build only single-file executable
python build.py --onefile

# Build only folder distribution
python build.py

# Build only installer (requires folder build first)
python build.py --installer
```

## After Building

1. **For WhatsApp sharing**: 
   - Go to `dist/FruityWolf-SingleFile/`
   - Zip `FruityWolf.exe`
   - Send the zip file

2. **For professional release**:
   - Go to `dist/FruityWolf-Installer/`
   - Send `FruityWolf-Setup.exe`

3. **For both**:
   - You have both ready in separate folders!
   - Name them accordingly when sharing

## Folder Names Explained

- **`FruityWolf-SingleFile`** = One .exe file (easy to identify)
- **`FruityWolf-Folder`** = Folder with dependencies
- **`FruityWolf-Installer`** = Windows installer

Each folder is clearly named so you know what's inside!
