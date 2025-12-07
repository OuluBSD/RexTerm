#!/usr/bin/env python3
"""Direct test of keyboard library functionality."""

import sys
import os

# Add the project root to the path so we can import dropterm
sys.path.insert(0, '/Users/sblo/dropterm_macos')

def test_keyboard_direct():
    try:
        import keyboard
        print("Keyboard library imported successfully")
        
        # Define a simple callback
        def my_callback():
            print("Hotkey pressed!")
            # Stop the listener after first activation for testing purposes
            keyboard.unhook_all()
        
        # Try to register a simple hotkey
        print("Attempting to register Ctrl+Shift+H as hotkey...")
        keyboard.add_hotkey('ctrl+shift+h', my_callback)
        print("Hotkey registered! Press Ctrl+Shift+H to test, or Ctrl+C to exit.")
        
        # Keep the script running
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            keyboard.unhook_all()
            
    except ImportError:
        print("Keyboard library is not available")
        print("Try installing it with: pip install keyboard")
    except Exception as e:
        print(f"Error: {e}")
        print("This may be due to insufficient permissions on macOS.")
        print("You need to grant accessibility permissions to the terminal/app.")

if __name__ == "__main__":
    test_keyboard_direct()