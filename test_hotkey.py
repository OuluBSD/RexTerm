#!/usr/bin/env python3
"""Test script to verify the hotkey parsing works correctly."""

from PyQt6.QtGui import QKeySequence
from dropterm.hotkeys import parse_hotkey_to_win

def test_hotkey_parsing():
    print("Testing hotkey parsing...")
    
    # Test various combinations that should work
    test_cases = [
        "Ctrl+§",      # Nordic keyboard: Ctrl + § (same as Ctrl + 1)
        "Alt+§",       # Nordic keyboard: Alt + §
        "Ctrl+Shift+§", # Nordic keyboard: Ctrl + Shift + §
        "Ctrl+`",      # Default value from settings
        "Ctrl+A",      # Standard test
        "Alt+F4",      # Common hotkey
    ]
    
    for hotkey in test_cases:
        print(f"\nTesting: '{hotkey}'")
        seq = QKeySequence(hotkey)
        text = seq.toString(QKeySequence.Format.PortableText) if hasattr(QKeySequence, 'Format') else seq.toString()
        print(f"  QKeySequence.toString(): '{text}'")
        
        result = parse_hotkey_to_win(hotkey)
        if result:
            mods, vk = result
            print(f"  Parsed successfully: modifiers={hex(mods)}, virtual_key={hex(vk)}")
        else:
            print(f"  Failed to parse hotkey: '{hotkey}'")

if __name__ == "__main__":
    test_hotkey_parsing()