# Starting GUI Shell without Visible Console

This directory contains several PowerShell scripts to start `run_gui_shell.bat` without showing a visible console window.

## Available Scripts

### 1. start_hidden.ps1
- Uses .NET Process class to start the batch file
- Sets `CreateNoWindow = $true` and `WindowStyle = Hidden`
- Shows process ID when started

### 2. start_hidden_wsh.ps1
- Uses Windows Script Host (WSH) to run the batch file
- Runs with window style 0 (hidden)
- Most compatible across different Windows versions

### 3. start_hidden_net.ps1
- Uses .NET Process class with redirected output
- Provides maximum control over process creation
- Completely hides the cmd window

## Usage

To use any of these scripts, simply run them from PowerShell:

```powershell
.\start_hidden.ps1
```

Or double-click on them in Windows Explorer (if PowerShell scripts are associated correctly).

## Notes

- All scripts check for the existence of `run_gui_shell.bat` before attempting to run it
- The GUI Shell window itself will still appear (as it's a PyQt application), but the underlying console window will be hidden
- These scripts are particularly useful when creating shortcuts to the application where you don't want to see the console

Choose the script that works best in your environment. The `start_hidden_wsh.ps1` script tends to be the most reliable across different Windows configurations.