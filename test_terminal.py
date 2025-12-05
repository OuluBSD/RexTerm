#!/usr/bin/env python3
import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dropterm.terminal_emulator import TerminalEmulator

print("Testing terminal emulator...")
terminal = TerminalEmulator(cols=80, rows=24, shell_type='bash', history_lines=1000)
if terminal.start():
    print("Terminal started successfully!")
    
    # Try to read any initial output
    output = terminal.read(1024)
    if output:
        print(f"Initial output: {repr(output)}")
    else:
        print("No initial output")
    
    # Try to write a command
    terminal.write('echo "Hello from Linux terminal"\n'.encode('utf-8') if isinstance('echo "Hello from Linux terminal"\n', str) else 'echo "Hello from Linux terminal"\n')
    
    # Read the response
    import time
    time.sleep(0.5)
    output = terminal.read(1024)
    if output:
        print(f"Command output: {repr(output)}")
    else:
        print("No command output")
        
    terminal.close()
    print("Terminal closed.")
else:
    print("Failed to start terminal")