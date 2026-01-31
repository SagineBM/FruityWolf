# Contributing to FruityWolf

Thank you for your interest in contributing to FruityWolf. This document explains how to get set up, run the app and tests, follow our code style, and submit changes.

## Getting started

### Prerequisites

- **Python 3.11+**
- **VLC** (for audio playback) — [download](https://www.videolan.org/vlc/)
- **Git**

### Clone and install

```bash
git clone https://github.com/FruityWolf/FruityWolf.git
cd FruityWolf

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

For optional BPM/Key analysis support:

```bash
pip install "fruitywolf[analysis]"
```

For development (formatting, linting, tests, build):

```bash
pip install "fruitywolf[dev]"
```

### Run the application

```bash
python -m FruityWolf
```

### Run tests

```bash
pytest tests/
```

Run with verbose output:

```bash
pytest tests/ -v
```

## Code style

We use **Black** and **Ruff** (see [pyproject.toml](pyproject.toml)).

- **Black**: line length 100, targets Python 3.11+
- **Ruff**: pycodestyle, Pyflakes, isort, flake8-bugbear, comprehensions; E501 ignored (handled by Black)

Format and lint before submitting:

```bash
black FruityWolf tests scripts
ruff check FruityWolf tests scripts
```

## Pull request process

1. **Fork** the repository and create a branch from `master`.
2. **Make your changes** — keep commits focused and messages clear.
3. **Run tests** — `pytest tests/` must pass.
4. **Format and lint** — run Black and Ruff as above.
5. **Open a pull request** against `master` with a short description of the change and any related issue.

We may ask for adjustments. Once approved, a maintainer will merge.

## Where to discuss

- **Bugs and features**: [GitHub Issues](https://github.com/FruityWolf/FruityWolf/issues)
- **Security**: see [SECURITY.md](SECURITY.md)

## Documentation and architecture

- **User and developer docs**: [docs/](docs/) — installation, building, architecture, development, configuration.
- **Building for distribution**: [BUILD.md](BUILD.md)
- **Roadmap**: [ROADMAP.md](ROADMAP.md)

## Code of conduct

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.
