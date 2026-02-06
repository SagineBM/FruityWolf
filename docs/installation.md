# 📥 Installation Guide

Getting FruityWolf running on your machine is straightforward.

---

## 🚀 Option 1: The Quickest Way (Recommended)

Most users should stick to this method. No coding knowledge required!

1.  **Download:** Head over to our [**Releases Page**](https://github.com/SagineBM/FruityWolf/releases).
2.  **Choose your flavor:**
    *   **`FruityWolf-Setup.exe`**: Standard installer. Installs to your system, creates shortcuts, the works. (Coming soon!)
    *   **`FruityWolf-Folder.zip`**: The "portable" version. Extract it anywhere and run. **Startup is faster** with this one.
    *   **`FruityWolf.exe`**: A single file. Great for simplicity, but takes a few seconds to unpack every time you run it.
3.  **Run it:** Double-click `FruityWolf.exe`.

*Note: You do **not** need to install Python or VLC separately if you use this method. Everything is included!*

---

## 🐍 Option 2: Running from Source

If you're a developer or on Linux/Mac, you might prefer running the Python code directly.

### Prerequisites
*   **Python 3.11+**: [Download Here](https://www.python.org/downloads/)
*   **VLC Media Player**: Required for audio playback. [Download VLC](https://www.videolan.org/vlc/)
*   **Git**: To grab the code.

### Step-by-Step

1.  **Clone the Repo**
    ```bash
    git clone https://github.com/SagineBM/FruityWolf.git
    cd FruityWolf
    ```

2.  **Set Up Virtual Environment**
    It's good practice to keep dependencies isolated.
    ```bash
    python -m venv venv
    
    # Windows:
    venv\Scripts\activate
    
    # Mac/Linux:
    # source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    *(Optional: To enable advanced analysis features, use `pip install "fruitywolf[analysis]"`. This installs heavier libraries like SciPy.)*

4.  **Launch!**
    ```bash
    python -m FruityWolf
    ```

---

## 🛠️ First Run Setup

When you first launch FruityWolf, it will ask you where your FL Studio projects are.

1.  **Select Folders:** Point it to your main projects folder (e.g., `Documents\Image-Line\FL Studio\Projects`).
2.  **Scan:** Let it scan! This might take a minute if you have thousands of projects.
3.  **Enjoy:** Your library is now indexed and ready to browse.

---

## ⚠️ Troubleshooting

**"VLC not found" Error?**
If running from source, make sure you have the standard 64-bit version of VLC installed. The Windows Store version sometimes causes issues.

**Need Help?**
Open an issue on GitHub if you get stuck!
