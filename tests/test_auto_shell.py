#!/usr/bin/env python3
"""Test auto detection of shell type"""

import sys
from gui_shell import TerminalEmulator

def test_auto_terminal():
    """Test auto terminal initialization"""
    print("Testing auto terminal initialization...")
    term = TerminalEmulator(shell_type='auto')
    
    # We can't start the terminal in this context since it might require GUI,
    # but we can test the msys64_path detection
    print(f"MSYS64 path detected in auto mode: {term.msys64_path}")
    print(f"Will use bash: {term.msys64_path is not None}")
    
    # Try to start the terminal
    try:
        success = term.start()
        print(f"Terminal start success: {success}")
        if success:
            print("Auto terminal started successfully!")
            print('MSYS64 path detected:', term.msys64_path)
            print('Shell type used:', 'bash' if term.msys64_path else 'cmd')
            term.close()
        else:
            print('Failed to start auto terminal')
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    return True

if __name__ == "__main__":
    test_auto_terminal()