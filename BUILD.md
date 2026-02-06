# 🏗️ Building FruityWolf

So, you want to build FruityWolf from source? Awesome! Whether you're hacking on a new feature or just prefer compiling things yourself, this guide will walk you through it.

**Builder:** Mohssine Bencaga

---

## 📋 What You'll Need

Before we start, make sure you have these installed:
1.  **Python 3.11 or newer**: The engine that powers everything.
2.  **Git**: To grab the code.
3.  **VLC Media Player**: We use this for audio playback. Make sure the standard version is installed (not the Windows Store version).

---

## ⚡ Quick Start

### 1. Get the Code
Open your terminal and clone the repo:
```bash
git clone https://github.com/SagineBM/FruityWolf.git
cd FruityWolf
```

### 2. Set Up Your Environment
It's always best to use a virtual environment so things don't get messy.
```bash
python -m venv venv
# Activate it:
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate
```

### 3. Install Dependencies
Grab all the libraries we need:
```bash
pip install -r requirements.txt
pip install pyinstaller Pillow cairosvg
```

### 4. Build It!
Now for the magic moment. Run Mohssine's build script:
```bash
python build.py
```

☕ **Time for a coffee.** This might take a minute or two as it bundles Python, Qt, and all our assets into a standalone package.

---

## 📦 What Did I Just Build?

Once the script finishes, check the `dist/` folder. You'll see two things:

1.  **`dist/FruityWolf-Folder/`**: The "unpacked" version. Great for debugging or if you want faster startup times.
2.  **`dist/FruityWolf-SingleFile/FruityWolf.exe`**: One single file that contains *everything*. Perfect for sharing with friends.

### Testing Your Build
Go into `dist/FruityWolf-Folder/` and double-click `FruityWolf.exe`. If the logo appears and the app opens, congratulations! You've successfully built FruityWolf. 🎉

---

## 🔧 Advanced Options

The build script has a few tricks up its sleeve:

-   **Make an Installer:** `python build.py --installer` (Requires NSIS installed)
-   **Clean Slate:** `python build.py --clean` (Wipes the `build` and `dist` folders)
-   **Just Assets:** `python build.py --assets` (Only regenerates icons/assets)

---

## 🆘 Troubleshooting

**"It says missing DLLs!"**
Make sure you ran the build command inside your activated virtual environment.

**"The icon is missing!"**
Run `python scripts/create_icon.py` to regenerate the icon files from the SVGs.

**"The single file is huge!"**
Yep, it bundles Python and Qt. It's usually around 200-300MB. This is normal for a standalone Python app!

Happy building! 🚀
