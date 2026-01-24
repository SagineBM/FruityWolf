# System Patterns

## Architecture Overview
FruityWolf follows a modular desktop application architecture using PySide6 (Qt) for the frontend and Python/SQLite for the backend.

### 1. Presentation Layer (UI)
- **Framework**: PySide6 (Qt for Python).
- **Entry Point**: `app.py` (`MainWindow` class).
- **Structure**:
  - `MainWindow`: Manages global state, players, and page navigation (`QStackedWidget`).
  - `ui/projects_view.py`: Dedicated view for the Projects table.
  - `ui/widgets.py`: Reusable custom widgets (Marquee, etc.).
  - `qml/`: QML files for specific modern UI components (hybrid approach).
- **Styling**: Inline CSS-like QSS (Qt Style Sheets) defined in `app.py` (`DARK_STYLE`).

### 2. Domain Logic
- **Scanner** (`scanner/`):
  - `LibraryScanner`: Core logic for traversing file systems, identifying project structures, and extracting metadata.
  - `ScannerThread`: Runs scanning in a background `QThread` to avoid freezing the UI (though signal intensity causes issues).
- **Classifier** (`classifier/`):
  - `ProjectClassifier`: Rules engine to determine project state (e.g., "WIP", "Idea") based on signals (file counts, sizes, render duration).
- **Player** (`player/`):
  - Wraps `python-vlc` for audio playback.
  - Handles state (PLAYING, PAUSED, STOPPED).

### 3. Data Layer
- **Database**: SQLite (`library.db`).
- **Access Pattern**: Raw SQL queries via `database` module (`query`, `execute`).
- **Schema**:
  - `projects`: Stores folder-level info (path, state, scores).
  - `tracks`: Stores individual audio files (renders).
  - `track_tags`: Many-to-many relationship for categorization.

## Key Design Patterns
- **Signal-Slot**: Used extensively for async communication between threads (Scanner -> UI) and components (Player -> UI).
- **Thread Worker**: Background tasks (Scanning, Waveform generation) are offloaded to `QThread`.
- **Hybrid UI**: Uses both QWidgets (standard desktop controls) and QML (modern fluid UI) where appropriate.

## Known Anti-Patterns (Refactoring Candidates)
- **Monolithic `app.py`**: The main file contains too much UI layout logic.
- **Widget-Heavy Tables**: `ProjectsView` uses `QTableWidget` with `setCellWidget` for large datasets, causing severe performance degradation (Lag).
- **Inline SQL**: SQL queries are scattered in helper functions rather than a dedicated ORM or Repository pattern.
