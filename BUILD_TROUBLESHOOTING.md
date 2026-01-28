# Build Troubleshooting Guide

## Common Build Errors

### PermissionError: Access Denied

**Error**: `PermissionError: [WinError 5] Access is denied`

**Cause**: Files in `dist/FruityWolf` are locked by another process.

**Solutions**:

1. **Close the app if running**:
   - Make sure FruityWolf.exe is not running
   - Check Task Manager for any FruityWolf processes

2. **Close File Explorer**:
   - Close any File Explorer windows showing the `dist` folder
   - Navigate away from the folder

3. **Disable Antivirus temporarily**:
   - Some antivirus software locks files during scanning
   - Temporarily disable real-time protection
   - Or add `dist` folder to exclusions

4. **Manually delete the folder**:
   ```powershell
   # Close everything, then:
   Remove-Item -Recurse -Force dist\FruityWolf
   ```

5. **Use force clean**:
   ```bash
   python build.py --force-clean
   ```

6. **Restart your computer** (if nothing else works)

### Build Hangs or Takes Forever

**Cause**: PyInstaller is analyzing many dependencies (PySide6, NumPy, SciPy, etc.)

**Solution**: This is normal! The build can take 5-10 minutes. Be patient.

### Missing DLL Warnings

**Warnings like**:
- `Library not found: could not resolve 'MIMAPI64.dll'`
- `Library not found: could not resolve 'LIBPQ.dll'`
- `Library not found: could not resolve 'tbb12.dll'`

**Solution**: These are **normal warnings** for optional dependencies. They won't affect your build unless you specifically need those features.

### Icon Not Found

**Error**: `WARNING: Icon not found`

**Solution**:
```bash
python scripts/create_icon.py
```

## Quick Fixes

### Before Building

1. **Close FruityWolf** if it's running
2. **Close File Explorer** windows showing dist folder
3. **Run clean**:
   ```bash
   python build.py --clean
   ```

### If Build Fails

1. **Try force clean**:
   ```bash
   python build.py --force-clean
   ```

2. **Manually delete**:
   - Close everything
   - Delete `dist` and `build` folders manually
   - Run build again

3. **Check for locked files**:
   - Use Process Explorer or Handle.exe to find what's locking files
   - Or restart your computer

## Build Commands Reference

```bash
# Clean build directories
python build.py --clean

# Force clean before building
python build.py --force-clean

# Build folder distribution
python build.py

# Build single-file executable
python build.py --onefile

# Build with installer
python build.py --installer

# Create icon
python scripts/create_icon.py
```

## Still Having Issues?

1. Check that you're in the project root directory
2. Make sure virtual environment is activated
3. Verify PyInstaller is installed: `pip install pyinstaller`
4. Try building in a fresh terminal/command prompt
5. Check Windows Event Viewer for file system errors
