# Quick Build Guide - For WhatsApp/Sharing

## Option 1: Single File (Best for WhatsApp) ✅

Build a **single .exe file** that you can send directly:

```bash
python build.py --onefile
```

**Output**: `dist/FruityWolf.exe` (single file, ~200-300 MB)

**Pros**:
- ✅ Can send via WhatsApp/email as ONE file
- ✅ Friend just double-clicks it
- ✅ No folder structure needed

**Cons**:
- ⚠️ Slower startup (extracts files on first run)
- ⚠️ Larger file size

**How to share**:
1. Build: `python build.py --onefile`
2. Find: `dist/FruityWolf.exe`
3. Send via WhatsApp/email
4. Friend downloads and double-clicks

## Option 2: Folder Distribution (Current Default)

Build a folder with .exe + dependencies:

```bash
python build.py
```

**Output**: `dist/FruityWolf/` folder

**Pros**:
- ✅ Faster startup
- ✅ Better for distribution

**Cons**:
- ❌ Need to send entire folder (or zip it)
- ❌ Can't send just the .exe

**How to share**:
1. Build: `python build.py`
2. Zip the `dist/FruityWolf/` folder
3. Send the zip file
4. Friend extracts and runs `FruityWolf.exe`

## Recommendation for WhatsApp

**Use `--onefile` mode** - it's perfect for sharing!

```bash
python build.py --onefile
```

Then send `dist/FruityWolf.exe` directly via WhatsApp.
