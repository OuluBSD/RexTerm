from PyQt6.QtCore import QThread, pyqtSignal
import time


class TerminalThread(QThread):
    """Thread to handle terminal I/O operations."""

    output_received = pyqtSignal(str)

    def __init__(self, terminal_emulator):
        super().__init__()
        self.terminal = terminal_emulator
        self.running = True
        # Buffer to collect output before emitting to reduce UI update frequency
        self.output_buffer = ""
        # Time threshold for output buffering (in seconds)
        self.buffer_time_threshold = 0.005  # 5ms - reduced from 10ms for faster response
        # Size threshold for output buffering
        self.buffer_size_threshold = 512  # Reduced from 1024 for more frequent updates

    def run(self):
        last_emit_time = time.time()

        while self.running and self.terminal.running:
            try:
                # Check if the terminal process is still alive
                if not self.terminal.pty_process.isalive():
                    # Terminal process has ended
                    break

                output = self.terminal.read(1024)
                if output:
                    self.output_buffer += output
                    current_time = time.time()

                    # Check if we're getting a lot of output (like in ncurses applications)
                    # Reduce delay if we have substantial output
                    adjusted_threshold = self.buffer_time_threshold
                    if len(self.output_buffer) > self.buffer_size_threshold / 2:
                        adjusted_threshold = min(adjusted_threshold, 0.003)  # 3ms for larger chunks

                    # Emit output if buffer is large enough or enough time has passed
                    if (len(self.output_buffer) >= self.buffer_size_threshold or
                        current_time - last_emit_time >= adjusted_threshold):
                        self.output_received.emit(self.output_buffer)
                        self.output_buffer = ""
                        last_emit_time = current_time
                else:
                    # If no output, sleep briefly to avoid busy waiting
                    time.sleep(0.001)  # 1ms sleep when no output
            except Exception:
                # If there's an error and we have buffered data, emit it before breaking
                if self.output_buffer:
                    self.output_received.emit(self.output_buffer)
                    self.output_buffer = ""
                break

        # Emit any remaining buffered output
        if self.output_buffer:
            self.output_received.emit(self.output_buffer)
            self.output_buffer = ""

        # Check if the terminal process is dead to trigger exit callback
        if not self.terminal.pty_process.isalive() and self.terminal.exit_callback:
            self.terminal.exit_callback()

        print("Terminal thread ended")

    def stop(self):
        self.running = False
        # Emit any remaining buffer if we're stopping
        if self.output_buffer:
            self.output_received.emit(self.output_buffer)
            self.output_buffer = ""

