# GUI Shell - Windows Setup

This directory contains the GUI Shell application and tools to create a Windows shortcut with an icon.

## Files Included

### Application Files
- `gui_shell.py` - Main application file
- `icon.png` - Source icon image
- `icon.ico` - Converted icon file for Windows

### Batch Scripts
- `run_gui_shell.bat` - Basic script to run the application
- `run_gui_shell_advanced.bat` - Advanced script with virtual environment setup

### Shortcut Creation Tools
- `create_shortcut.vbs` - VBScript to create desktop shortcut
- `create_shortcut_ps.ps1` - PowerShell script to create desktop shortcut
- `create_shortcut_py.py` - Python script to create shortcut (requires pywin32)
- `create_shortcut.reg` - Registry file (for reference only)

## Creating the Desktop Shortcut

The shortcut has already been created on your desktop as "GUI Shell.lnk".

If you need to recreate it, double-click one of these files:

### Method 1: VBScript (Recommended)
Double-click `create_shortcut.vbs` to create the shortcut.

### Method 2: PowerShell
Run `create_shortcut_ps.ps1` with PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File "create_shortcut_ps.ps1"
```

### Method 3: Python
Run the Python script to create the shortcut:
```cmd
python create_shortcut_py.py
```
Note: This requires the pywin32 package. Install it with:
```cmd
pip install pywin32
```

## Running the Application

You can run the application directly:
1. Using the desktop shortcut
2. Double-clicking `run_gui_shell.bat`
3. Using the advanced script `run_gui_shell_advanced.bat`

## Troubleshooting

If the application doesn't run:
1. Make sure Python is installed and in your PATH
2. Run the batch script from Command Prompt to see error messages
3. Check that all requirements are installed (see requirements.txt)

The advanced batch script will attempt to create and set up a virtual environment automatically.

## Building an Executable (Optional)

For a more portable solution, you can create a standalone executable with PyInstaller:
```cmd
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico gui_shell.py
```

This will create an executable in the `dist` folder that can be run directly without requiring Python installation.