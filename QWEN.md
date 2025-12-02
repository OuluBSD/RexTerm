# GUI Shell Project - Development Notes

## Project Overview
- **Project Name**: GUI Shell
- **Location**: ~/dropterm
- **Purpose**: A Python-based graphical terminal emulator for Windows
- **Created**: December 2, 2025

## Technical Details
- **GUI Framework**: PyQt6
- **Terminal Backend**: winpty (pywinpty in MSYS2/MinGW)
- **Language**: Python
- **Main File**: gui_shell.py
- **Dependencies**: PyQt6, winpty

## Key Features Implemented
- Graphical terminal interface with output area and input field
- Command execution capabilities
- Command history with up/down arrow navigation
- Keyboard shortcuts (Ctrl+C for interrupt, Ctrl+L to clear)
- Proper terminal I/O handling through winpty
- Threading for asynchronous operations

## Important Notes for Future Development
- In MSYS2/MinGW environments, pywinpty is installed as 'winpty'
- The winpty module has a different API than standard pywinpty:
  - Uses `pywinpty.ptyprocess.PtyProcess` instead of `pywinpty.spawn_process`
  - Read and write methods have different signatures
- The terminal emulator handles command execution, output display, and basic terminal features while providing a user-friendly graphical interface

## File Structure
- `gui_shell.py` - Main application code
- `README.md` - User documentation
- `QWEN.md` - Development notes (this file)

## Known Issues & Considerations
- Terminal might close prematurely under certain conditions
- The winpty API doesn't directly support resizing
- Reading from the terminal requires careful handling of timing and availability

## Running the Application
```bash
python gui_shell.py
```

## Required Setup
```bash
# For UCRT64 environment
pacman -S mingw-w64-ucrt-x86_64-python-pyqt6 mingw-w64-ucrt-x86_64-python-pywinpty

# For CLANG64 environment
pacman -S mingw-w64-clang-x86_64-python-pyqt6 mingw-w64-clang-x86_64-python-pywinpty
```