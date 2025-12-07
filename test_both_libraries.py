#!/usr/bin/env python3
"""Test script to verify hotkey functionality on macOS."""

import sys
import os

# Add the project root to the path so we can import dropterm
sys.path.insert(0, '/Users/sblo/dropterm_macos')

def test_pynput_directly():
    """Test pynput directly to see if hotkeys work."""
    try:
        from pynput import keyboard
        print("pynput keyboard imported successfully")
        
        def on_activate():
            print("Hotkey activated!")
            # In a real application, you'd do something here
            # For this test, we'll just print and continue listening
        
        # Register the hotkey - using a non-conflicting combination
        hotkey = keyboard.GlobalHotKeys({
            '<cmd>+<shift>+h': on_activate,  # Cmd+Shift+H
        })
        
        print("Hotkey registered. Press Cmd+Shift+H to test.")
        print("Press Ctrl+C to exit.")
        
        hotkey.start()
        
        try:
            # Keep the script running
            while True:
                pass
        except KeyboardInterrupt:
            print("\nStopping hotkey listener...")
            hotkey.stop()
            print("Done.")
            
    except Exception as e:
        print(f"Error with pynput: {e}")
        print("Make sure you've granted accessibility permissions to your terminal/app in System Preferences > Security & Privacy > Privacy > Accessibility")

def test_keyboard_directly():
    """Test keyboard library directly."""
    try:
        import keyboard
        print("keyboard library imported successfully")
        
        def on_activate():
            print("Hotkey activated with keyboard library!")
        
        # Try to register a hotkey
        print("Trying to register Ctrl+Shift+K...")
        keyboard.add_hotkey('ctrl+shift+k', on_activate)
        print("Hotkey registered. Press Ctrl+Shift+K to test.")
        print("Press Ctrl+C to exit.")
        
        # Keep the script running
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            keyboard.unhook_all()
            
    except Exception as e:
        print(f"Error with keyboard library: {e}")

if __name__ == "__main__":
    print("Testing pynput...")
    test_pynput_directly()
    
    print("\nTesting keyboard library...")
    test_keyboard_directly()