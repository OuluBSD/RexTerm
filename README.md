# GUI Shell

A Python-based graphical terminal emulator that provides a GUI interface for executing shell commands on Windows.

## Features

- Graphical terminal interface built with PyQt6
- Command history with up/down arrow navigation
- Support for common terminal commands (cls to clear screen)
- Keyboard shortcuts (Ctrl+C for interrupt, Ctrl+L to clear)
- Real-time command execution and output display

## Dependencies

- Python 3.8+
- PyQt6
- pywinpty (installed as winpty in MSYS2/MinGW environments)

## Installation

If you're using MSYS2/MinGW environment, you can install the required packages using pacman:

```bash
# For UCRT64 environment
pacman -S mingw-w64-ucrt-x86_64-python-pyqt6 mingw-w64-ucrt-x86_64-python-pywinpty

# For CLANG64 environment  
pacman -S mingw-w64-clang-x86_64-python-pyqt6 mingw-w64-clang-x86_64-python-pywinpty
```

## Usage

To run the GUI Shell:

```bash
python gui_shell.py
```

## How to Use

1. Type commands in the input field at the bottom
2. Press Enter to execute the command
3. Use Up/Down arrows to navigate command history
4. Use Ctrl+L to clear the terminal screen
5. Use Ctrl+C to send an interrupt signal to the running process

## Technical Details

The application uses:
- PyQt6 for the GUI components
- winpty (pywinpty) for Windows terminal virtualization
- Threading to handle terminal I/O operations asynchronously

The terminal emulator handles command execution, output display, and basic terminal features while providing a user-friendly graphical interface.