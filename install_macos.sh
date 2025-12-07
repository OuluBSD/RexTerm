#!/bin/bash

# RexTerm macOS Installation Script
# This script installs all required packages for RexTerm using Homebrew

set -e  # Exit immediately if a command exits with a non-zero status

echo "Installing RexTerm dependencies on macOS..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew is not installed. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # For macOS with Apple Silicon, add Homebrew to PATH
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.bash_profile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

echo "Updating Homebrew..."
brew update

echo "Installing Python 3..."
brew install python3

echo "Installing additional useful tools for development..."
brew install git

# Check if we're on Apple Silicon Mac and install additional packages if needed
if [[ $(uname -m) == "arm64" ]]; then
    echo "Apple Silicon Mac detected. Installing additional packages if needed..."
    # No additional packages required specifically for ARM64 for this application
fi

echo "Creating Python virtual environment in home directory..."
python3 -m venv ~/venv
echo "Virtual environment created at ~/venv/"

echo "Upgrading pip in the virtual environment..."
~/venv/bin/pip install --upgrade pip

echo "Installing requirements to virtual environment..."
~/venv/bin/pip install -r requirements_unix.txt
~/venv/bin/pip install pynput

echo "Installation completed!"

echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source ~/venv/bin/activate"
echo ""
echo "To start RexTerm, run:"
echo "  source ~/venv/bin/activate && python gui_shell.py"
echo ""