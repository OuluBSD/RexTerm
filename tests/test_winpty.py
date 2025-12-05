import sys
import winpty

# Try creating a PtyProcess and see if it works
try:
    # Create a pty process running cmd.exe
    child = winpty.ptyprocess.PtyProcess.spawn(['cmd.exe'])
    print(f"Started process with PID: {child.pid}")
    print(f"Is alive: {child.isalive()}")
    
    import time
    # Wait a bit for the prompt to appear
    time.sleep(0.5)
    
    # Try reading initial output (the cmd prompt)
    try:
        initial_output = child.read(1024)  # Read up to 1024 bytes
        print(f"Initial output: {repr(initial_output)}")
    except Exception as e:
        print(f"No initial output or error: {e}")

    # Send a command
    child.write('echo Hello from Python!\r\n')
    time.sleep(0.5)

    # Try reading output
    try:
        output = child.read(1024)  # Read up to 1024 bytes
        print(f"Output: {repr(output)}")
    except Exception as e:
        print(f"Read error: {e}")
            
    # You can also try other commands
    child.write('dir\r\n')
    time.sleep(1)

    try:
        output2 = child.read(1024)  # Read up to 1024 bytes
        print(f"Dir output: {repr(output2)}")
    except Exception as e:
        print(f"Read error for dir: {e}")
    
    # Close the process properly
    child.write('exit\r\n')  # Exit the shell gracefully
    time.sleep(0.3)
    print("Process should be terminated")
    
except Exception as e:
    import traceback
    print(f"Error creating pty process: {e}")
    traceback.print_exc()