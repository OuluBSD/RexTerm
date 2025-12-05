#!/usr/bin/env python3
import os
import sys
import time

# Add the project directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dropterm.terminal_emulator import TerminalEmulator

print("Testing terminal emulator with command...")
terminal = TerminalEmulator(cols=80, rows=24, shell_type='bash', history_lines=1000)
if terminal.start():
    print("Terminal started successfully!")
    
    # Give some time for shell to initialize
    time.sleep(0.5)
    
    # Check initial output
    output = terminal.read(1024)
    if output:
        print(f"Initial output: {repr(output)}")
    else:
        print("No initial output")
    
    # Send a command
    command = 'echo "Hello from Linux terminal"\n'
    if sys.platform != 'win32':
        command = command.encode('utf-8')
    terminal.write(command)
    
    # Wait a bit for command to execute
    time.sleep(1)
    
    # Read the response multiple times to catch output
    for i in range(5):
        output = terminal.read(1024)
        if output:
            print(f"Response {i+1}: {repr(output)}")
        else:
            print(f"No response {i+1}")
        time.sleep(0.2)
        
    terminal.close()
    print("Terminal closed.")
else:
    print("Failed to start terminal")