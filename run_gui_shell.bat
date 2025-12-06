@echo off
REM Batch script to run the GUI Shell application

REM Change to the directory containing the script
cd /d "%~dp0"

REM Activate the Python virtual environment if it exists
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo Warning: Virtual environment not found, using system Python
)

REM Install dependencies if requirements.txt exists and packages aren't installed
python -c "import pkg_resources; pkg_resources.require(open('requirements.txt'))" 2>nul
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
)

REM Run the GUI Shell application
python gui_shell.py

REM Pause to see any error messages (optional, remove if not needed)
REM pause