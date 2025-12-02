import sys
import os
import queue
import argparse
import re
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QScrollBar, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtGui import QFont, QAction, QKeyEvent
import winpty as pywinpty  # In MSYS2/MinGW environments, pywinpty is installed as winpty
import signal
import winreg


def find_msys64_path():
    """
    Find the MSYS64 installation path by checking common locations.

    Returns:
        str: Path to MSYS64 installation, or None if not found
    """
    # Common MSYS64 installation locations
    common_paths = [
        r"E:\active\msys64",  # User-specified path
        r"C:\msys64",
        r"D:\msys64",
        r"C:\Tools\msys64",
        os.path.expanduser(r"~\msys64"),
    ]

    # Check if any of the common paths exist
    for path in common_paths:
        if path and os.path.exists(path):
            bash_path = os.path.join(path, "usr", "bin", "bash.exe")
            if os.path.exists(bash_path):
                return path

    # Try to find MSYS64 in registry (if it was properly registered)
    try:
        # Check both 32-bit and 64-bit views of the registry
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ)
        ]

        for hkey, subkey, access_key in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey, 0, access_key) as key:
                    i = 0
                    while True:
                        try:
                            reg_subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(hkey, f"{subkey}\\{reg_subkey_name}", 0, winreg.KEY_READ) as subkey_handle:
                                try:
                                    display_name, _ = winreg.QueryValueEx(subkey_handle, "DisplayName")
                                    if display_name and ("MSYS2" in display_name or "MSYS-64" in display_name):
                                        install_location, _ = winreg.QueryValueEx(subkey_handle, "InstallLocation")
                                        if install_location and os.path.exists(install_location):
                                            bash_path = os.path.join(install_location, "usr", "bin", "bash.exe")
                                            if os.path.exists(bash_path):
                                                return install_location
                                except (winreg.FileNotFoundError, OSError):
                                    # Some registry entries might not have these values
                                    pass
                            i += 1
                        except OSError:
                            # No more subkeys
                            break
            except OSError:
                # This registry path doesn't exist or isn't accessible
                continue
    except Exception:
        # Fallback silently if registry access fails
        pass

    return None


def ansi_to_html(text):
    """
    Convert ANSI escape codes to HTML for display in QTextEdit
    """
    # Define ANSI color codes
    ansi_colors = {
        '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
        '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
        '90': 'darkgray', '91': 'lightred', '92': 'lightgreen', '93': 'lightyellow',
        '94': 'lightblue', '95': 'lightmagenta', '96': 'lightcyan', '97': 'lightgray',
        '40': 'black', '41': 'red', '42': 'green', '43': 'yellow',
        '44': 'blue', '45': 'magenta', '46': 'cyan', '47': 'white'
    }

    # Replace special characters to HTML entities first
    text = html.escape(text)

    # Handle multiple ANSI code sequences in the text
    # This pattern matches all ANSI escape sequences starting with ESC[
    pattern = r'(\x1b\[[\?]?[\d;]*[a-zA-Z])'
    parts = re.split(pattern, text)

    result = []
    current_fg = None
    current_bg = None
    is_bold = False

    for part in parts:
        if part.startswith('\x1b[') and part[-1].isalpha():
            # This is an ANSI escape sequence
            sequence = part[2:-1]  # Extract the code without \x1b[ and the final letter

            # Handle sequences that end with 'm' (color/formatting codes)
            if part.endswith('m'):
                # Handle special mode sequences that don't affect display
                if sequence.startswith('?'):
                    # These are mode setting sequences (like ?2004h), ignore them for display
                    continue

                # Split codes if there are multiple (e.g., \x1b[1;32m)
                codes = [c for c in sequence.split(';') if c]  # Remove empty strings

                if not codes or '0' in codes:
                    # Reset all formatting if no codes or '0' is present
                    current_fg = None
                    current_bg = None
                    is_bold = False
                    continue

                for code in codes:
                    if code == '1':
                        # Bold
                        is_bold = True
                    elif code == '22':
                        # Normal weight (not bold)
                        is_bold = False
                    elif code == '39':
                        # Default foreground color
                        current_fg = None
                    elif code == '49':
                        # Default background color
                        current_bg = None
                    elif code.startswith('3') and (code.isdigit() or code in ['90', '91', '92', '93', '94', '95', '96', '97']):
                        # Foreground color
                        if code in ansi_colors:
                            current_fg = ansi_colors[code]
                    elif code.startswith('4') and code.isdigit() and code in ['40', '41', '42', '43', '44', '45', '46', '47']:
                        # Background color
                        if code in ansi_colors:
                            current_bg = ansi_colors[code]
            else:
                # Other ANSI sequences (cursor movement, etc.) - ignore for display
                continue
        else:
            # Regular text content
            if current_fg or current_bg or is_bold:
                style = ""
                if current_fg:
                    style += f"color:{current_fg};"
                if current_bg:
                    style += f"background-color:{current_bg};"
                if is_bold:
                    style += "font-weight:bold;"

                result.append(f'<span style="{style}">{part}</span>')
            else:
                result.append(part)

    return ''.join(result)


import html


class TerminalEmulator:
    """A wrapper for winpty to handle Windows terminal operations"""

    def __init__(self, cols=80, rows=24, shell_type='cmd'):
        self.cols = cols
        self.rows = rows
        self.running = False
        self.pty_process = None
        self.command_queue = queue.Queue()
        self.shell_type = shell_type  # 'cmd', 'bash', or 'auto'
        self.msys64_path = find_msys64_path() if shell_type in ['bash', 'auto'] else None

    def start(self):
        """Start the terminal session"""
        try:
            # Determine which shell to use
            if self.shell_type == 'bash' or (self.shell_type == 'auto' and self.msys64_path):
                # Use MSYS2 bash
                if self.msys64_path:
                    bash_path = os.path.join(self.msys64_path, "usr", "bin", "bash.exe")
                    # Use login shell to get full environment
                    self.pty_process = pywinpty.ptyprocess.PtyProcess.spawn([bash_path, "--login", "-i"])
                else:
                    # Fallback to cmd if MSYS64 path not found
                    self.pty_process = pywinpty.ptyprocess.PtyProcess.spawn(['cmd.exe'])
            else:
                # Use cmd.exe as default
                self.pty_process = pywinpty.ptyprocess.PtyProcess.spawn(['cmd.exe'])

            self.running = True
            return True
        except Exception as e:
            print(f"Failed to start terminal: {e}")
            import traceback
            traceback.print_exc()
            return False

    def read(self, size=1024):
        """Read output from the terminal"""
        if not self.running or not self.pty_process.isalive():
            return ''
        try:
            # Only read if data is available
            return self.pty_process.read(size)
        except Exception as e:
            print(f"Read error: {e}")
            # Check if process is still alive
            if not self.pty_process.isalive():
                self.running = False
            return ''

    def write(self, data):
        """Write input to the terminal"""
        if not self.running or not self.pty_process.isalive():
            return
        try:
            self.pty_process.write(data)
        except Exception as e:
            print(f"Write error: {e}")
            # Check if process is still alive
            if not self.pty_process.isalive():
                self.running = False

    def resize(self, cols, rows):
        """Resize the terminal"""
        # Note: ptyprocess doesn't directly support resizing
        self.cols = cols
        self.rows = rows

    def close(self):
        """Close the terminal session"""
        self.running = False
        if self.pty_process and self.pty_process.isalive():
            try:
                # Try to exit gracefully first
                self.pty_process.write('exit\r\n')
                import time
                time.sleep(0.1)
                if self.pty_process.isalive():
                    # Force terminate if still alive
                    self.pty_process.terminate(force=True)
            except:
                pass


class TerminalThread(QThread):
    """Thread to handle terminal I/O operations"""
    output_received = pyqtSignal(str)
    
    def __init__(self, terminal_emulator):
        super().__init__()
        self.terminal = terminal_emulator
        self.running = True
    
    def run(self):
        """Continuously read from the terminal and emit output"""
        while self.running and self.terminal.running:
            try:
                output = self.terminal.read(1024)
                if output:
                    self.output_received.emit(output)
            except Exception:
                break
        print("Terminal thread ended")
    
    def stop(self):
        """Stop the thread"""
        self.running = False


class ShellWidget(QWidget):
    """Main shell widget with terminal emulation"""

    def __init__(self, shell_type='auto'):
        super().__init__()

        # Buffer to handle partial lines from terminal (initialize before using append_output)
        self.output_buffer = ""

        # Tracking for command echo to prevent double display
        self.waiting_for_command_echo = False
        self.last_command = ""

        # Setup terminal emulator
        self.terminal = TerminalEmulator(cols=80, rows=24, shell_type=shell_type)
        if not self.terminal.start():
            raise Exception("Could not start terminal emulator")

        # Setup UI
        self.setup_ui()

        # Start terminal thread
        self.terminal_thread = TerminalThread(self.terminal)
        self.terminal_thread.output_received.connect(self.append_output)
        self.terminal_thread.start()

        # Initial prompt
        self.append_output("$ ")

        # Command history
        self.command_history = []
        self.history_index = -1

        # Current command being edited
        self.current_command = ""
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Terminal output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.output_area.setFont(font)
        
        # Make it act more like a terminal
        self.output_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Input line
        self.input_line = QLineEdit()
        self.input_line.setFont(font)
        self.input_line.returnPressed.connect(self.execute_command)
        
        layout.addWidget(self.output_area)
        layout.addWidget(self.input_line)
        
        self.setLayout(layout)
    
    def append_output(self, text):
        """Append output to the text area"""
        # Add new text to the buffer
        self.output_buffer += text

        # Split the buffer by newlines
        lines = self.output_buffer.split('\n')

        # Keep the last incomplete line in the buffer
        self.output_buffer = lines[-1]

        # Process all complete lines
        complete_lines = lines[:-1]

        for line in complete_lines:
            # Normalize line endings and handle special characters
            line = line.replace('\r', '')  # Remove carriage returns
            line = line.replace('\b', '')  # Remove backspace characters

            # Check if this line is an echo of the last command (to avoid duplication)
            if self.waiting_for_command_echo and line == self.last_command:
                # Skip this line as it's the command echo
                self.waiting_for_command_echo = False
                continue

            # Convert ANSI codes to HTML if needed
            has_ansi = '\x1b[' in line
            if has_ansi:
                html_line = ansi_to_html(line)
                self.output_area.textCursor().insertHtml(html_line)
            else:
                self.output_area.insertPlainText(line)

            # Add newline after each complete line
            self.output_area.insertPlainText('\n')

        # Auto-scroll to bottom
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def execute_command(self):
        """Execute the command entered by the user"""
        command = self.input_line.text()
        if command:
            # Add command to history
            self.command_history.append(command)
            self.history_index = len(self.command_history)  # Point to just after the last command

            # Track that we're waiting for command echo to avoid duplication
            self.waiting_for_command_echo = True
            self.last_command = command

            # Send command to terminal
            self.terminal.write(command + '\r\n')

            # Clear the input line
            self.input_line.clear()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for terminal-like behavior"""
        key = event.key()
        
        if key == Qt.Key.Key_Up:
            # Previous command in history
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                self.input_line.setText(self.command_history[self.history_index])
                self.input_line.setCursorPosition(len(self.input_line.text()))  # Move cursor to end
        elif key == Qt.Key.Key_Down:
            # Next command in history
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.input_line.setText(self.command_history[self.history_index])
                self.input_line.setCursorPosition(len(self.input_line.text()))  # Move cursor to end
            else:
                # Clear input if at current command
                self.history_index = len(self.command_history)
                self.input_line.clear()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.execute_command()
        elif key == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+C sends interrupt signal
            self.terminal.write('\x03')  # Send SIGINT (Ctrl+C)
            event.accept()
        elif key == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+L clears the screen
            self.clear_screen()
            event.accept()
        else:
            # For other keys, let the default behavior occur
            super().keyPressEvent(event)
    
    def clear_screen(self):
        """Clear the terminal output area"""
        self.output_area.clear()
        # Also send clear command to actual terminal process
        self.terminal.write('cls\r\n')
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Process any remaining content in the buffer before closing
        if self.output_buffer:
            # Convert ANSI codes to HTML if needed for the final partial line
            has_ansi = '\x1b[' in self.output_buffer
            if has_ansi:
                html_line = ansi_to_html(self.output_buffer)
                self.output_area.textCursor().insertHtml(html_line)
            else:
                self.output_area.insertPlainText(self.output_buffer)
            self.output_buffer = ""

        self.terminal_thread.stop()
        self.terminal.close()
        event.accept()
        

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, shell_type='auto'):
        super().__init__()
        self.setWindowTitle("GUI Shell")
        self.setGeometry(100, 100, 800, 600)

        # Create and set the central widget
        self.shell_widget = ShellWidget(shell_type=shell_type)
        self.setCentralWidget(self.shell_widget)
        
        # Create menu
        self.create_menu()
        
        # Set up keyboard shortcuts
        self.setup_shortcuts()
    
    def create_menu(self):
        """Create the application menu"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Terminal menu
        terminal_menu = menubar.addMenu('Terminal')
        
        clear_action = QAction('Clear Screen', self)
        clear_action.triggered.connect(self.clear_screen)
        terminal_menu.addAction(clear_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Clear screen with Ctrl+L (already handled in ShellWidget)
        pass
    
    def clear_screen(self):
        """Clear the terminal screen"""
        self.shell_widget.clear_screen()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About GUI Shell", 
                         "GUI Shell - A terminal emulator built with Python, PyQt6, and pywinpty")


def main():
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("GUI Shell")
    app.setApplicationVersion("1.0")

    # Parse command-line arguments to determine shell type
    import argparse

    parser = argparse.ArgumentParser(description='GUI Shell with MSYS2 support')
    parser.add_argument('--shell', '-s', choices=['cmd', 'bash', 'auto'], default='auto',
                        help='Shell type to use: cmd, bash, or auto (default: auto)')

    args = parser.parse_args(sys.argv[1:])

    # Create and show the main window with specified shell type
    window = MainWindow(shell_type=args.shell)
    window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()