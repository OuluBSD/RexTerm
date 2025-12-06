@echo off
REM Advanced batch script to run the GUI Shell application with error handling

REM Change to the directory containing the script
cd /d "%~dp0"

echo Setting up GUI Shell environment...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create and activate virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Check if required packages are installed
python -c "import PyQt6, pywinpty, pyte, ptyprocess" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    if exist "requirements.txt" (
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        if errorlevel 1 (
            echo Error: Failed to install required packages
            pause
            exit /b 1
        )
    ) else (
        echo Warning: requirements.txt not found
        echo Installing known required packages...
        pip install PyQt6 pywinpty pyte ptyprocess
    )
)

REM Run the GUI Shell application
echo Starting GUI Shell...
python gui_shell.py
if errorlevel 1 (
    echo Error occurred while running GUI Shell
    pause
    exit /b 1
)

echo GUI Shell closed.
REM Uncomment the next line if you want the window to stay open after exit
REM pause