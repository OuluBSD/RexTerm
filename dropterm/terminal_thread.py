from PyQt6.QtCore import QThread, pyqtSignal


class TerminalThread(QThread):
    """Thread to handle terminal I/O operations."""

    output_received = pyqtSignal(str)

    def __init__(self, terminal_emulator):
        super().__init__()
        self.terminal = terminal_emulator
        self.running = True

    def run(self):
        while self.running and self.terminal.running:
            try:
                # Check if the terminal process is still alive
                if not self.terminal.pty_process.isalive():
                    # Terminal process has ended
                    break

                output = self.terminal.read(1024)
                if output:
                    self.output_received.emit(output)
            except Exception:
                break

        # Check if the terminal process is dead to trigger exit callback
        if not self.terminal.pty_process.isalive() and self.terminal.exit_callback:
            self.terminal.exit_callback()

        print("Terminal thread ended")

    def stop(self):
        self.running = False

