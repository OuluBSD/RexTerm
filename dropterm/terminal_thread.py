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
                output = self.terminal.read(1024)
                if output:
                    self.output_received.emit(output)
            except Exception:
                break
        print("Terminal thread ended")

    def stop(self):
        self.running = False

