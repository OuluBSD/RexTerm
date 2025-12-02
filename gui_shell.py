import sys
import os
import queue
import argparse
import re
import html
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QScrollBar, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtGui import QFont, QAction, QKeyEvent
import winpty as pywinpty  # In MSYS2/MinGW environments, pywinpty is installed as winpty
import signal
import winreg
import pyte
from pyte import streams, screens


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
    """A wrapper for winpty to handle Windows terminal operations with pyte terminal emulation"""

    def __init__(self, cols=80, rows=24, shell_type='cmd'):
        self.cols = cols
        self.rows = rows
        self.running = False
        self.pty_process = None
        self.command_queue = queue.Queue()
        self.shell_type = shell_type  # 'cmd', 'bash', or 'auto'
        self.msys64_path = find_msys64_path() if shell_type in ['bash', 'auto'] else None

        # Initialize pyte for proper terminal emulation
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

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
            # Read raw data from pty
            raw_data = self.pty_process.read(size)

            # Process the raw data with pyte for proper terminal emulation
            if raw_data:
                self.stream.feed(raw_data)

            return raw_data
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

        # Track if we're expecting a new prompt
        self.expecting_new_prompt = False

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

        # Terminal output area - now will act as both output and input
        self.output_area = QTextEdit()
        # Make it NOT read-only so users can type at the end
        self.output_area.setReadOnly(False)
        font = QFont("Courier New", 10)
        self.output_area.setFont(font)

        # Make it act more like a terminal
        self.output_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # Add custom context menu to hide paste, etc. if needed
        self.output_area.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        # Track where user input starts in the text
        self.input_start_position = 0

        # Input line is no longer needed as input will be part of the output area
        # self.input_line = QLineEdit()
        # self.input_line.setFont(font)
        # self.input_line.returnPressed.connect(self.execute_command)

        layout.addWidget(self.output_area)

        self.setLayout(layout)
    
    def append_output(self, text):
        """Append output to the text area using pyte for proper terminal rendering"""
        # Add new text to the pyte stream to process terminal escape sequences
        if text:
            self.terminal.stream.feed(text)

        # Get the current cursor position to maintain it after update
        cursor = self.output_area.textCursor()
        original_position = cursor.position()

        # Get the current user input at the end (if any) and preserve it
        full_text = self.output_area.toPlainText()
        preserved_input = ""

        # Store current user input for later restoration
        if self.input_start_position < len(full_text):
            preserved_input = full_text[self.input_start_position:]

        # Generate content from pyte screen that preserves colors and formatting
        output_lines = []
        for line_idx in range(self.terminal.screen.lines):
            # Get the line from the buffer to access character attributes
            line = self.terminal.screen.buffer[line_idx]

            line_html_parts = []
            # Process each character position in the line
            for col_idx in range(self.terminal.screen.columns):
                char = line[col_idx]  # This gets the character at position (line_idx, col_idx)

                # Get character and attributes (pyte Char object)
                char_data = char.data
                fg = char.fg if char.fg != 'default' else 'white'
                bg = char.bg if char.bg != 'default' else 'black'
                bold = char.bold
                italic = char.italics  # Note: pyte uses 'italics' not 'italic'
                underline = char.underscore

                # Map pyte colors to standard CSS colors
                color_map = {
                    'black': 'black',
                    'red': 'red',
                    'green': 'green',
                    'yellow': 'yellow',
                    'blue': 'blue',
                    'magenta': 'magenta',
                    'cyan': 'cyan',
                    'white': 'white',
                    # Some additional mappings
                    'default': 'currentColor'
                }

                fg_color = color_map.get(fg, fg)
                bg_color = color_map.get(bg, bg)

                # Build style string
                styles = []
                if fg_color != 'currentColor':
                    styles.append(f"color: {fg_color}")
                if bg_color != 'black':
                    styles.append(f"background-color: {bg_color}")
                if bold:
                    styles.append("font-weight: bold")
                if italic:
                    styles.append("font-style: italic")
                if underline:
                    styles.append("text-decoration: underline")

                if styles:
                    style_str = "; ".join(styles)
                    line_html_parts.append(f'<span style="{style_str}">{html.escape(char_data)}</span>')
                else:
                    line_html_parts.append(html.escape(char_data))

            # Join all HTML parts for this line and add to output
            output_lines.append("".join(line_html_parts).rstrip())

        # Join all lines and set HTML content
        output_html = "\n".join(output_lines)

        # Append the preserved input after the new output
        if preserved_input:
            output_html += preserved_input

        # Update the output area with the new content
        self.output_area.setHtml(output_html)

        # Update the input start position to after all the terminal output
        # Find the length of the text corresponding to terminal content
        output_text = "\n".join(self.terminal.screen.display).rstrip()
        self.input_start_position = len(output_text)

        # Move cursor to the end to maintain position for user input
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_area.setTextCursor(cursor)

        # Auto-scroll to bottom
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def execute_command(self):
        """Execute the command entered by the user"""
        # Get the command from the input area
        full_text = self.output_area.toPlainText()
        command = full_text[self.input_start_position:]

        if command:
            # Add command to history
            self.command_history.append(command)
            self.history_index = len(self.command_history)  # Point to just after the last command

            # Send command to terminal - use only \n which is standard for Unix-like terminals
            # This should help reduce duplicate prompts
            self.terminal.write(command + '\n')

            # Clear the input area by updating with just the display content
            display_text = "\n".join(self.terminal.screen.display).rstrip()
            self.output_area.setPlainText(display_text)
            self.input_start_position = len(display_text)

            # Position cursor at the end for next input
            cursor = self.output_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.output_area.setTextCursor(cursor)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for terminal-like behavior with integrated input"""
        key = event.key()
        cursor = self.output_area.textCursor()

        # Check if cursor is at the input area (after the input start position)
        is_at_input_area = cursor.position() >= self.input_start_position

        if key == Qt.Key.Key_Up and is_at_input_area:
            # Previous command in history
            if self.command_history and self.history_index > 0:
                if self.history_index == len(self.command_history):
                    # Store current input before navigating history
                    current_input = self.output_area.toPlainText()[self.input_start_position:]
                    self.current_command = current_input
                self.history_index -= 1
                # Update the current input area with the history command
                self.update_input_area(self.command_history[self.history_index])
        elif key == Qt.Key.Key_Down and is_at_input_area:
            # Next command in history
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                # Update the current input area with the history command
                self.update_input_area(self.command_history[self.history_index])
            else:
                # Clear input if at current command
                self.history_index = len(self.command_history)
                if self.current_command:
                    self.update_input_area(self.current_command)
                    self.current_command = ""
                else:
                    self.update_input_area("")
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and is_at_input_area:
            # Execute command when Enter is pressed in the input area
            self.execute_command()
        elif key == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+C sends interrupt signal
            self.terminal.write('\x03')  # Send SIGINT (Ctrl+C)
            event.accept()
        elif key == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+L clears the screen
            self.clear_screen()
            event.accept()
        elif is_at_input_area:
            # For all other keys when in the input area, allow normal input
            super().keyPressEvent(event)
        else:
            # If not in input area, only allow navigation keys
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
                      Qt.Key.Key_PageUp, Qt.Key.Key_PageDown, Qt.Key.Key_Home, Qt.Key.Key_End):
                super().keyPressEvent(event)

    def update_input_area(self, text):
        """Update only the input part of the text area"""
        # Get the display part (everything before the input)
        display_text = "\n".join(self.terminal.screen.display).rstrip()

        # Set the full content: display + new input
        full_content = display_text + text
        self.output_area.setPlainText(full_content)

        # Position the cursor at the end of the content
        cursor = self.output_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_area.setTextCursor(cursor)

        # Update input start position
        self.input_start_position = len(display_text)
    
    def clear_screen(self):
        """Clear the terminal output area"""
        # Reset the pyte screen
        self.terminal.screen.reset()

        # Update the display without input
        display_text = "\n".join(self.terminal.screen.display).rstrip()
        self.output_area.setPlainText(display_text)
        self.input_start_position = len(display_text)

        # Also send clear command to actual terminal process
        # Use \n instead of \r\n for Unix-like terminals
        if hasattr(self.terminal, 'shell_type') and self.terminal.shell_type in ['bash', 'auto'] and self.terminal.msys64_path:
            self.terminal.write('clear\n')
        else:
            self.terminal.write('cls\n')
    
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