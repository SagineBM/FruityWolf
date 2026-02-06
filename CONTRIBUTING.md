# 🤝 Contributing to FruityWolf

First off, **thank you!** The fact that you're here reading this means you want to help make this tool better, and that's awesome.

Whether you're fixing a typo, adding a cool new feature, or refactoring our messy code (we know, we know), your help is welcome.

---

## 🛠️ Setting Up Your Dev Environment

We've tried to keep the setup as painless as possible.

### What You Need
-   **Python 3.11+**
-   **VLC Media Player** (Standard desktop version)
-   **Git**

### The Setup Dance
1.  **Fork & Clone:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/FruityWolf.git
    cd FruityWolf
    ```

2.  **Virtual Env (Trust us, do this):**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    ```

3.  **Install Dev Dependencies:**
    ```bash
    pip install -e ".[dev]"
    ```
    This installs everything you need for running tests and linting.

4.  **Run the App:**
    ```bash
    python -m FruityWolf
    ```

---

## 🧪 Testing

Please, *please* run the tests before submitting a PR. We don't want to break Mohssine's hard work!

```bash
pytest tests/
```

If you're adding a new feature, try to add a test for it. If you don't know how, just ask in the PR!

---

## 🎨 Code Style

We use **Black** and **Ruff** to keep things looking sharp.

Before you commit, run:
```bash
black FruityWolf tests scripts
ruff check FruityWolf tests scripts
```

(Or just install pre-commit hooks if you're fancy.)

---

## 📝 Submitting a Pull Request

1.  **Branch out:** Create a new branch for your feature (`git checkout -b feature/cool-new-thing`).
2.  **Commit:** Keep your commit messages clear.
3.  **Push & PR:** Push to your fork and open a Pull Request against our `master` branch.
4.  **Describe it:** Tell us what you changed and why. Screenshots are a bonus!

---

## 🚧 Major Changes

If you're planning a massive overhaul (like rewriting the audio engine or changing the database schema), it's probably a good idea to open an **Issue** first to discuss it. We don't want you wasting weeks on something that might conflict with our roadmap.

**Project Lead:** [Mohssine Bencaga](https://github.com/SagineBM)

---

## 📜 Code of Conduct

Be nice. Be respectful. We're all here to make cool stuff for music producers. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for the fine print.

Happy coding! 🚀
