# LCoder: Multi-Language Modular IDE

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-green?style=flat-square&logo=qt)](https://www.qt.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-success?style=flat-square)](tests/)

**LCoder** is a lightweight, modular and modern Integrated Development Environment designed to deliver a fluid experience across multiple programming languages. Refactored into a modular architecture, the project prioritizes maintainability, extensibility and a professional look.

> **LCoder** é um ambiente de desenvolvimento integrado (IDE) leve, modular e moderno, projetado para oferecer uma experiência fluida em múltiplas linguagens de programação. Refatorado para uma arquitetura modular, o projeto prioriza a facilidade de manutenção, expansão e um visual profissional.

---

## Interface & User Experience

The interface is built with **PySide6 (Qt)**, providing a contemporary look with native theme support and components.

| Feature | Description |
| :--- | :--- |
| **Dynamic Themes** | Choose between **Dark**, **Light** and **Monokai** for the best visual comfort. |
| **File Explorer** | Hierarchical folder navigation with intelligent per-type icons. |
| **Smart Editor** | Syntax highlighting and autocomplete for major languages. |
| **IntelliCode** | Autocomplete with intelligent ranking based on frequency, recency and context. |
| **Auto Import (Python)** | Automatically inserts basic imports when saving Python files. |
| **Auto `.venv`** | Creates `.venv` and installs `requirements.txt` when opening a workspace. |
| **Real Terminal** | Full integration with the system shell (CMD/Bash) in real time. |
| **Extension System** | VS Code-like extension model with manifest, commands, menus and contributions. |

---

## Modular Architecture

The project is split into logical components to guarantee scalability:

- `core/` — The "brain" of the application. Manages JSON configuration, language definitions and color schemes.
- `ui/` — The visual layer. Contains the main window logic, editor component and file explorer.
- `utils/` — Execution engines. Manages external processes, virtual environments and terminal integration.
- `extensions/` — Loaded at startup. Each extension can contribute commands, menus, themes and languages.
- `main.py` — Simplified application entry point.

---

## Integrated Terminal

Unlike previous versions that used limited REPLs, LCoder's terminal offers:

- **Native access**: Runs commands directly in `cmd.exe` (Windows) or `bash/zsh` (Linux/macOS).
- **Cross-platform**: Automatic OS detection to load the correct shell.
- **Asynchronous I/O**: Separate threads for `stdout` and `stderr` keep the UI responsive.
- **Tool support**: Use `git`, `npm`, `pip`, `docker` and any CLI tool installed on your system.

---

## Getting Started

### Prerequisites

- Python 3.8 or higher.
- Core dependencies: `PySide6`, `Pillow`, `watchdog`.

### Installation & Execution

1. Clone the repository:
    ```bash
    git clone https://github.com/arthurlamonattopro/LCoder.git
    cd LCoder
    ```
2. (Optional) Create a virtual environment:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux / macOS
    source .venv/bin/activate
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Start the IDE:
    ```bash
    python main.py
    ```
5. Open a folder containing a `requirements.txt` to auto-generate `.venv` and install dependencies.

> Tip: You can disable IntelliCode, auto-import and auto `.venv` in **Settings**.

### Configuration

The IDE reads its configuration from `ide_config.json` (auto-created on first run). A reference template is provided in [`ide_config.example.json`](ide_config.example.json). Copy it to `ide_config.json` and edit to taste.

> **Security note**: `ide_config.json` is gitignored because it may store local paths and an OpenAI API key. Never commit it.

For the OpenAI Codex tab, you can either enter the API key in the UI or set the `OPENAI_API_KEY` environment variable — the IDE will pick it up automatically.

---

## Building a Native Executable

The repository ships a `main.spec` file for [PyInstaller](https://pyinstaller.org/). To produce a native binary:

```bash
pip install pyinstaller
pyinstaller main.spec
```

The executable will be generated under `dist/main/`.

> On Linux you may need to install `libgl1` first: `sudo apt install libgl1`.

---

## Supported Languages

LCoder currently offers native support (highlighting + execution) for:

- **Lua**
- **Python**
- **JavaScript (Node.js)**
- **Ruby**
- **PHP**
- **Perl**
- **C++** (g++)
- **HTML** (opens in the default browser)

---

## Tests

The project ships a `pytest` suite covering the core utilities. To run it:

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests live in [`tests/`](tests/) and cover `auto_importer`, `ConfigManager` and `ExtensionManager`.

---

## Extensions

LCoder ships a small extension system inspired by VS Code. See [`EXTENSIONS.md`](EXTENSIONS.md) for details on authoring your own extensions. Bundled examples:

- `hello-world` — Minimal sample extension.
- `git-manager` — Full Git GUI (status, diff, stage, unstage, commit, branch, push, pull, fetch, open remote).
- `media-preview` — Preview images, HTML and Markdown files.

> **Security note**: Extensions run arbitrary Python code. Only install extensions you trust.

---

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire and create. Any contribution you make will be **greatly appreciated**.

1. Fork the project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Make your changes and commit (`git commit -m 'Add AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

Please make sure `pytest` passes and `ruff check .` is clean before opening a PR.

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

---

Developed with care by [Arthur Lamonatto](https://github.com/arthurlamonattopro).
