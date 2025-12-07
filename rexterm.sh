#!/bin/bash

# RexTerm - GUI Terminal Emulator
# This script launches the GUI shell application

# Activate the virtual environment if it exists
if [ -f "$HOME/venv/bin/activate" ]; then
    source "$HOME/venv/bin/activate"
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the GUI shell using python3
exec python3 "${SCRIPT_DIR}/gui_shell.py" "$@"