# RexTerm

Cross-platform drop-down terminal for Windows, macOS, and Linux. It can float down from the top of the screen like Guake or run as a normal terminal window.

We wanted to just fork Guake, but the Linux-first codebase proved too difficult to adapt across platforms. A Qt6 + winpty core worked immediately on Windows, so we built a new app that follows Guake’s spirit while targeting all major desktops.

## Features
- Drop-down quake-style terminal or standard windowed terminal
- PyQt6 UI with tabs and configurable shortcuts
- Truecolor/TERM export and scrollback via pyte + winpty backend (Windows)
- Global hotkey for toggling the quake window
- Settings dialog for fonts, themes, quake behavior, and shortcuts

## Dependencies
- Python 3.8+
- PyQt6
- pywinpty (packaged as winpty in MSYS2/MinGW environments for Windows)

## Installation (Windows / MSYS2 examples)
```bash
# UCRT64
pacman -S mingw-w64-ucrt-x86_64-python-pyqt6 mingw-w64-ucrt-x86_64-python-pywinpty

# CLANG64
pacman -S mingw-w64-clang-x86_64-python-pyqt6 mingw-w64-clang-x86_64-python-pywinpty
```

## Usage
Run the app:
```bash
python gui_shell.py
```

## Notes
- Default behavior follows Guake: quake-style drop-down when enabled, otherwise a standard window.
- On Windows the PTY layer uses winpty; on other platforms Qt/pty integration is expected to take over as support is added.
