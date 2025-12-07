#!/usr/bin/env python3
"""Test script to verify keyboard library works for global hotkeys on macOS."""

import sys
import os

# Add the project root to the path so we can import dropterm
sys.path.insert(0, '/Users/sblo/dropterm_macos')

from PyQt6.QtGui import QKeySequence
from dropterm.hotkeys import register_crossplatform_hotkey, unregister_crossplatform_hotkey

def test_callback():
    print("Global hotkey triggered!")
    
def test_hotkey():
    print("Testing keyboard library for global hotkeys...")
    
    # Test registering a simple hotkey
    hotkey = "Ctrl+Shift+H"  # Using a non-conflicting hotkey for testing
    success = register_crossplatform_hotkey(QKeySequence(hotkey).toString(), test_callback)
    
    if success:
        print(f"Successfully registered hotkey: {hotkey}")
        print("Try pressing the hotkey combination now...")
        print("Press Enter to unregister and exit.")
        
        # Wait for user input
        input()
        
        # Unregister the hotkey
        unregister_crossplatform_hotkey()
        print("Hotkey unregistered.")
    else:
        print(f"Failed to register hotkey: {hotkey}")
        print("This could be due to missing permissions on macOS.")
        print("You may need to grant accessibility permissions to your terminal/app.")

if __name__ == "__main__":
    test_hotkey()