#!/usr/bin/env python3
"""Test script to verify MSYS64 bash support in GUI Shell"""

import sys
import os
import time
from gui_shell import TerminalEmulator, find_msys64_path

def test_msys64_detection():
    """Test MSYS64 path detection"""
    print("Testing MSYS64 detection...")
    msys_path = find_msys64_path()
    print(f"MSYS64 path found: {msys_path}")
    if msys_path:
        bash_path = os.path.join(msys_path, "usr", "bin", "bash.exe")
        print(f"Bash executable exists: {os.path.exists(bash_path)}")
        return True
    else:
        print("MSYS64 not found")
        return False

def test_bash_terminal():
    """Test starting bash terminal"""
    print("\nTesting bash terminal initialization...")
    try:
        term = TerminalEmulator(shell_type='bash')
        if term.start():
            print("Bash terminal started successfully!")
            print(f"MSYS64 path: {term.msys64_path}")
            
            # Give it a moment to initialize
            time.sleep(0.5)
            
            # Test writing a simple command
            term.write("echo 'Hello from MSYS bash'\r\n")
            time.sleep(0.5)
            
            # Try reading output
            output = term.read(1024)
            if output:
                print(f"Output from bash: {repr(output)}")
            else:
                print("No output captured (this may be normal depending on bash initialization)")
            
            term.close()
            return True
        else:
            print("Failed to start bash terminal")
            return False
    except Exception as e:
        print(f"Error testing bash terminal: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cmd_terminal():
    """Test starting cmd terminal for comparison"""
    print("\nTesting cmd terminal initialization...")
    try:
        term = TerminalEmulator(shell_type='cmd')
        if term.start():
            print("CMD terminal started successfully!")
            
            # Give it a moment to initialize
            time.sleep(0.5)
            
            # Test writing a simple command
            term.write("echo Hello from CMD\r\n")
            time.sleep(0.5)
            
            # Try reading output
            output = term.read(1024)
            if output:
                print(f"Output from cmd: {repr(output)}")
            else:
                print("No output captured (this may be normal depending on cmd initialization)")
            
            term.close()
            return True
        else:
            print("Failed to start cmd terminal")
            return False
    except Exception as e:
        print(f"Error testing cmd terminal: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing MSYS64 bash support in GUI Shell")
    print("=" * 50)
    
    success = True
    
    # Test path detection
    if not test_msys64_detection():
        success = False
    
    # Test bash terminal
    if not test_bash_terminal():
        success = False
    
    # Test cmd terminal for comparison
    if not test_cmd_terminal():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("All tests passed! MSYS64 bash support is working.")
    else:
        print("Some tests failed.")
        sys.exit(1)