#!/usr/bin/env python3
import os
import sys
import time

# Add the project directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dropterm.terminal_emulator import TerminalEmulator

print("Testing terminal emulator...")
terminal = TerminalEmulator(cols=80, rows=24, shell_type='bash', history_lines=1000)
if terminal.start():
    print("Terminal started successfully!")
    time.sleep(1)
    
    # Read any initial output
    output = terminal.read(1024)
    if output:
        print(f"Initial output: {repr(output)}")
    else:
        print("No initial output")
    
    # Close immediately to avoid hanging
    terminal.close()
    print("Terminal closed.")
else:
    print("Failed to start terminal")