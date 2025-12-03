import sys
import os
import queue
import argparse
import re
import html
import time
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QScrollBar, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QEvent, QTimer
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


class TerminalEmulator:
    """A wrapper for winpty to handle Windows terminal operations with pyte terminal emulation"""

    def __init__(self, cols=80, rows=24, shell_type='cmd', history_lines=1000):
        self.cols = cols
        self.rows = rows
        self.history_lines = history_lines
        self.running = False
        self.pty_process = None
        self.command_queue = queue.Queue()
        self.shell_type = shell_type  # 'cmd', 'bash', or 'auto'
        self.msys64_path = find_msys64_path() if shell_type in ['bash', 'auto'] else None

        # Initialize pyte for proper terminal emulation with scrollback
        self.screen = screens.HistoryScreen(cols, rows, history=history_lines)
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
            try:
                self.pty_process.setwinsize(self.rows, self.cols)
            except Exception as e:
                print(f"Failed to set initial pty size: {e}")
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
        self.cols = cols
        self.rows = rows

        # Resize underlying pty if possible
        if self.pty_process:
            try:
                # Note: winpty expects (rows, cols) ordering
                self.pty_process.setwinsize(rows, cols)
            except Exception as e:
                print(f"Resize error: {e}")

        # Resize pyte screen to keep rendering in sync
        try:
            self.screen.resize(rows, cols)
        except Exception as e:
            print(f"pyte resize error: {e}")

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

    def __init__(self, shell_type='auto', scrollback_lines=1000):
        super().__init__()

        # Buffer to handle partial lines from terminal (initialize before using append_output)
        self.output_buffer = ""

        # Tracking for command echo to prevent double display
        self.waiting_for_command_echo = False
        self.last_command = ""

        # Track if we're expecting a new prompt
        self.expecting_new_prompt = False

        # Drop preserved input after commands so stale text doesn't linger
        self.clear_pending_input = False

        # Track whether we're in an alternate screen (ncurses, full-screen apps)
        self.in_alternate_screen = False

        # Pick an Enter sequence suitable for the active shell
        self.enter_sequence = '\n' if (self.terminal.shell_type in ['bash', 'auto'] and self.terminal.msys64_path) else '\r'

        # Setup terminal emulator
        self.terminal = TerminalEmulator(cols=80, rows=24, shell_type=shell_type, history_lines=scrollback_lines)
        if not self.terminal.start():
            raise Exception("Could not start terminal emulator")

        # Debugging attributes
        self.debug_enabled = False
        self.debug_file = None
        self.logger = None

        # Precompute a color map for HTML rendering
        self.color_map = {
            'black': '#000000',
            'red': '#cc0000',
            'green': '#009900',
            'yellow': '#999900',
            'blue': '#0000cc',
            'magenta': '#cc00cc',
            'cyan': '#009999',
            'white': '#cccccc',
            'brightblack': '#555555',
            'brightred': '#ff5555',
            'brightgreen': '#55ff55',
            'brightyellow': '#ffff55',
            'brightblue': '#5555ff',
            'brightmagenta': '#ff55ff',
            'brightcyan': '#55ffff',
            'brightwhite': '#ffffff'
        }

        # Setup UI
        self.setup_ui()

        # Start terminal thread
        self.terminal_thread = TerminalThread(self.terminal)
        self.terminal_thread.output_received.connect(self.append_output)
        self.terminal_thread.start()

        # Command history
        self.command_history = []
        self.history_index = -1

        # Current command being edited
        self.current_command = ""

        # Initial size sync once the widget has been laid out
        QTimer.singleShot(0, self.update_terminal_size)
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()

        # Terminal output area - read only; we forward keys to the PTY directly
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        # Route key events through our handler
        self.output_area.installEventFilter(self)
        self.output_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.output_area.setFocus()
        font = QFont("Courier New", 10)
        self.output_area.setFont(font)

        # Make it act more like a terminal
        self.output_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # Allow normal context menu so text can be copied
        self.output_area.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

        # Track where user input starts in the text
        self.input_start_position = 0

        # Input line is no longer needed as input will be part of the output area
        # self.input_line = QLineEdit()
        # self.input_line.setFont(font)
        # self.input_line.returnPressed.connect(self.execute_command)

        layout.addWidget(self.output_area)

        self.setLayout(layout)

    def update_terminal_size(self):
        """Resize the underlying terminal to match the visible area."""
        if not self.output_area:
            return

        viewport = self.output_area.viewport()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return

        metrics = self.output_area.fontMetrics()
        char_width = max(1, metrics.horizontalAdvance("M"))
        char_height = max(1, metrics.lineSpacing())

        new_cols = max(2, viewport.width() // char_width)
        new_rows = max(2, viewport.height() // char_height)

        if new_cols != self.terminal.cols or new_rows != self.terminal.rows:
            self.terminal.resize(new_cols, new_rows)
            # Re-render the screen to respect the new geometry
            self.append_output("")

    def _wrap_html(self, body: str) -> str:
        """Wrap rendered HTML in a <pre> so whitespace is preserved."""
        return (
            "<pre style=\"margin:0; white-space: pre; font-family:'Courier New', monospace; font-size:10pt;\">"
            f"{body}"
            "</pre>"
        )

    def _style_for_char(self, char) -> str:
        """Return CSS style string for a pyte character."""
        fg = self.color_map.get(char.fg, None)
        bg = self.color_map.get(char.bg, None)

        # Handle reverse video
        if getattr(char, "reverse", False):
            fg, bg = bg, fg

        styles = []
        if fg:
            styles.append(f"color:{fg}")
        if bg:
            styles.append(f"background-color:{bg}")
        if getattr(char, "bold", False):
            styles.append("font-weight:bold")
        if getattr(char, "italics", False):
            styles.append("font-style:italic")
        if getattr(char, "underscore", False):
            styles.append("text-decoration: underline")
        return ";".join(styles)

    def _render_line(self, line_map):
        """Render a single pyte line map to plain text and HTML."""
        plain_chars = []
        html_parts = []
        current_style = None

        for col in range(self.terminal.screen.columns):
            char = line_map[col]
            ch = char.data if char.data is not None else " "
            plain_chars.append(ch)

            style = self._style_for_char(char) or None
            if style != current_style:
                if current_style is not None:
                    html_parts.append("</span>")
                if style:
                    html_parts.append(f'<span style="{style}">')
                current_style = style

            html_parts.append(html.escape(ch))

        if current_style is not None:
            html_parts.append("</span>")

        raw_line = "".join(plain_chars)
        html_line = "".join(html_parts)

        return raw_line, html_line

    def _render_screen(self):
        """Render the pyte screen to both plain text and HTML strings."""
        plain_lines = []
        html_lines = []

        screen = self.terminal.screen
        line_sources = []

        if isinstance(screen, screens.HistoryScreen):
            line_sources.extend(list(screen.history.top))

        for row in range(screen.lines):
            line_sources.append(screen.buffer[row])

        if isinstance(screen, screens.HistoryScreen) and screen.history.bottom:
            line_sources.extend(list(screen.history.bottom))

        for line in line_sources:
            plain_line, html_line = self._render_line(line)
            plain_lines.append(plain_line)
            html_lines.append(html_line)

        return "\n".join(plain_lines), "\n".join(html_lines)
    
    def append_output(self, text):
        """Append output to the text area using pyte for proper terminal rendering"""

        # Log the output if debugging is enabled
        if self.debug_enabled and self.logger:
            self.logger.debug(f"append_output called with text length: {len(text) if text else 0}")
            if text:
                self.logger.debug(f"append_output raw text: {repr(text[:200])}")  # Log first 200 chars

        # Track alternate screen toggles to better support full-screen ncurses apps
        if text:
            if any(seq in text for seq in ("\x1b[?1049h", "\x1b[?47h", "\x1b[?1047h")):
                self.in_alternate_screen = True
            if any(seq in text for seq in ("\x1b[?1049l", "\x1b[?47l", "\x1b[?1047l")):
                self.in_alternate_screen = False

        scrollbar = self.output_area.verticalScrollBar()
        previous_scroll_value = scrollbar.value()
        at_bottom = previous_scroll_value >= scrollbar.maximum()

        display_text, display_html = self._render_screen()

        # Update the output area with the new content, preserving ANSI colors via HTML
        self.output_area.setHtml(self._wrap_html(display_html))

        # Update the input start position to after the terminal output (in plain text)
        doc_text = self.output_area.toPlainText()
        self.input_start_position = len(doc_text)

        # Log the output text for debugging
        if self.debug_enabled and self.logger:
            self.logger.debug(f"Terminal screen display output: {repr(display_text[:500])}")
            self.logger.debug(f"Updated input_start_position to: {self.input_start_position}")

        # Create a new cursor and move it to the end to position for user input
        new_cursor = self.output_area.textCursor()
        new_cursor.movePosition(new_cursor.MoveOperation.End)
        self.output_area.setTextCursor(new_cursor)
        self.output_area.setFocus()

        # Respect the user's scroll position: only stick to bottom if they were there
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(min(previous_scroll_value, scrollbar.maximum()))
    
    def execute_command(self):
        """Execute the command entered by the user"""
        # Get the command from the input area
        full_text = self.output_area.toPlainText()
        command = full_text[self.input_start_position:]

        if command:
            # Add command to history
            self.command_history.append(command)
            self.history_index = len(self.command_history)  # Point to just after the last command

            # Send command to terminal - try using \n which is more standard for most shells
            # \r should work for Windows cmd, \n for bash, so we'll try to determine based on shell type
            if hasattr(self.terminal, 'shell_type') and self.terminal.shell_type in ['bash', 'auto'] and self.terminal.msys64_path:
                # For bash, use \n
                self.terminal.write(command + '\n')
            else:
                # For cmd, use \r
                self.terminal.write(command + '\r')

            # After sending the command, clear any preserved input on next redraw
            self.clear_pending_input = True

            # Immediately clear the typed command from the UI; the shell will echo it back
            self.update_input_area("")

        # Clear the input area after command execution
        # We need to update the input_start_position to reflect the new end of the output
        # This will be handled in append_output when new data comes from the terminal
    
    def eventFilter(self, obj, event):
        """Route key presses from the text area through our handler"""
        if obj is self.output_area and event.type() == QEvent.Type.KeyPress:
            return self.handle_key_press(event)
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """Keep terminal geometry in sync with widget size."""
        super().resizeEvent(event)
        self.update_terminal_size()

    def handle_key_press(self, event: QKeyEvent):
        """Send key presses directly to the PTY for full terminal compatibility."""
        key = event.key()
        modifiers = event.modifiers()
        cursor = self.output_area.textCursor()

        # Allow normal copy shortcuts when text is selected
        if cursor.hasSelection():
            if (modifiers == Qt.KeyboardModifier.ControlModifier and key in (Qt.Key.Key_C, Qt.Key.Key_Insert)) or \
               (modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_C):
                return False  # Let QTextEdit handle the copy

        # Handle paste shortcuts: Ctrl+V or Shift+Insert
        if (modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V) or \
           (modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_Insert):
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                normalized = text.replace("\r\n", "\n").replace("\r", "\n")
                self.terminal.write(normalized)
            event.accept()
            return True

        # Helper to build CSI modifier parameters for arrows/home/end/page keys
        def modifier_param():
            param = 1
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                param += 1
            if modifiers & Qt.KeyboardModifier.AltModifier:
                param += 2
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                param += 4
            return None if param == 1 else param

        def csi_with_mod(base_letter: str) -> str:
            param = modifier_param()
            if param:
                return f"\x1b[1;{param}{base_letter}"
            return f"\x1b[{base_letter}"

        # Arrow keys, Home/End with modifier support
        arrow_map = {
            Qt.Key.Key_Up: "A",
            Qt.Key.Key_Down: "B",
            Qt.Key.Key_Right: "C",
            Qt.Key.Key_Left: "D",
        }
        if key in arrow_map:
            self.terminal.write(csi_with_mod(arrow_map[key]))
            event.accept()
            return True

        if key == Qt.Key.Key_Home:
            self.terminal.write(csi_with_mod("H"))
            event.accept()
            return True
        if key == Qt.Key.Key_End:
            self.terminal.write(csi_with_mod("F"))
            event.accept()
            return True

        # Page keys with modifiers
        if key == Qt.Key.Key_PageUp:
            param = modifier_param()
            seq = f"\x1b[5;{param}~" if param else "\x1b[5~"
            self.terminal.write(seq)
            event.accept()
            return True
        if key == Qt.Key.Key_PageDown:
            param = modifier_param()
            seq = f"\x1b[6;{param}~" if param else "\x1b[6~"
            self.terminal.write(seq)
            event.accept()
            return True

        # Delete/Insert
        if key == Qt.Key.Key_Delete:
            param = modifier_param()
            seq = f"\x1b[3;{param}~" if param else "\x1b[3~"
            self.terminal.write(seq)
            event.accept()
            return True
        if key == Qt.Key.Key_Insert:
            param = modifier_param()
            seq = f"\x1b[2;{param}~" if param else "\x1b[2~"
            self.terminal.write(seq)
            event.accept()
            return True

        # Function keys
        function_map = {
            Qt.Key.Key_F1: "\x1bOP",
            Qt.Key.Key_F2: "\x1bOQ",
            Qt.Key.Key_F3: "\x1bOR",
            Qt.Key.Key_F4: "\x1bOS",
            Qt.Key.Key_F5: "\x1b[15~",
            Qt.Key.Key_F6: "\x1b[17~",
            Qt.Key.Key_F7: "\x1b[18~",
            Qt.Key.Key_F8: "\x1b[19~",
            Qt.Key.Key_F9: "\x1b[20~",
            Qt.Key.Key_F10: "\x1b[21~",
            Qt.Key.Key_F11: "\x1b[23~",
            Qt.Key.Key_F12: "\x1b[24~",
        }
        if key in function_map:
            self.terminal.write(function_map[key])
            event.accept()
            return True

        # Common control keys
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.terminal.write(self.enter_sequence)
            event.accept()
            return True
        if key == Qt.Key.Key_Backspace:
            self.terminal.write("\x7f")
            event.accept()
            return True
        if key == Qt.Key.Key_Tab:
            self.terminal.write("\t")
            event.accept()
            return True
        if key == Qt.Key.Key_Backtab:
            self.terminal.write("\x1b[Z")
            event.accept()
            return True
        if key == Qt.Key.Key_Escape:
            self.terminal.write("\x1b")
            event.accept()
            return True

        # Ctrl+<letter> when Qt doesn't populate text()
        if not event.text() and (modifiers & Qt.KeyboardModifier.ControlModifier) and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            ctrl_char = chr(key - Qt.Key.Key_A + 1)
            self.terminal.write(ctrl_char)
            event.accept()
            return True

        # Regular text (including control characters provided by Qt)
        if event.text():
            text = event.text()
            if modifiers & Qt.KeyboardModifier.AltModifier and not text.startswith("\x1b"):
                text = "\x1b" + text
            self.terminal.write(text)
            event.accept()
            return True

        return True

    def update_input_area(self, text):
        """Update only the input part of the text area"""
        # Get the display part (everything before the input)
        display_text, display_html = self._render_screen()

        # Set the full content: display + new input
        full_content_html = display_html + html.escape(text)
        self.output_area.setHtml(self._wrap_html(full_content_html))

        # Position the cursor at the end of the content
        cursor = self.output_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_area.setTextCursor(cursor)

        # Update input start position
        doc_text = self.output_area.toPlainText()
        self.input_start_position = max(0, len(doc_text) - len(text))
    
    def clear_screen(self):
        """Clear the terminal output area"""
        # Reset the pyte screen
        self.terminal.screen.reset()

        # Update the display without input
        display_text, display_html = self._render_screen()
        self.output_area.setHtml(self._wrap_html(display_html))
        self.input_start_position = len(self.output_area.toPlainText())

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

    def __init__(self, shell_type='auto', scrollback_lines=1000):
        super().__init__()
        self.setWindowTitle("GUI Shell")
        self.setGeometry(100, 100, 800, 600)

        # Create and set the central widget
        self.shell_widget = ShellWidget(shell_type=shell_type, scrollback_lines=scrollback_lines)
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


def setup_debug_logging(debug_file):
    """Setup logging for debugging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(debug_file, mode='w'),
            logging.StreamHandler()  # This will also print to console
        ]
    )

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
    parser.add_argument('--eval', help='Command to evaluate in non-interactive mode')
    parser.add_argument('--dump', action='store_true', help='Dump screen content to stdout in non-interactive mode')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout in seconds for non-interactive mode (default: 10)')
    # Additional arguments for headless GUI operation
    parser.add_argument('--headless-eval', help='Command to evaluate in headless GUI mode')
    parser.add_argument('--headless-timeout', type=int, default=10, help='Timeout for headless GUI mode (default: 10)')
    # Argument for debugging mode
    parser.add_argument('--debug', help='Enable debug logging to specified file')
    parser.add_argument('--scrollback', type=int, default=1000,
                        help='Number of scrollback lines to keep in the terminal buffer (default: 1000)')

    args = parser.parse_args(sys.argv[1:])

    # Initialize debug logging if specified
    if args.debug:
        setup_debug_logging(args.debug)

    # If eval is specified, run in non-interactive mode
    if args.eval:
        # Create a temporary terminal emulator
        terminal = TerminalEmulator(cols=80, rows=24, shell_type=args.shell, history_lines=args.scrollback)
        if not terminal.start():
            print("Could not start terminal emulator", file=sys.stderr)
            sys.exit(1)

        # Create a thread to read terminal output
        output_queue = queue.Queue()

        def read_terminal():
            start_time = time.time()
            while time.time() - start_time < args.timeout and terminal.running:
                try:
                    output = terminal.read(1024)
                    if output:
                        output_queue.put(output)
                    time.sleep(0.01)  # Small delay to prevent busy waiting
                except Exception:
                    break

        import threading
        reader_thread = threading.Thread(target=read_terminal)
        reader_thread.daemon = True
        reader_thread.start()

        # Send the command with a newline
        terminal.write(args.eval + '\n')

        # Wait for output or timeout
        reader_thread.join(timeout=args.timeout)
        terminal.close()

        # Collect and print all output
        all_output = []
        while not output_queue.empty():
            all_output.append(output_queue.get_nowait())

        final_output = ''.join(all_output)

        if args.dump:
            print(final_output)
        else:
            print(final_output.strip())

        sys.exit(0)
    elif args.headless_eval:
        # Run in headless GUI mode - start GUI, execute command, dump output after timeout
        window = MainWindow(shell_type=args.shell, scrollback_lines=args.scrollback)
        # Only show window if not in debug mode
        if not args.debug:
            window.show()

        # Access the shell widget to send the command
        shell_widget = window.shell_widget

        # If debugging, set the debug file
        if args.debug:
            shell_widget.debug_enabled = True
            shell_widget.debug_file = args.debug
            shell_widget.logger = logging.getLogger(__name__)

        # Schedule the command to be sent after a brief moment to allow GUI to initialize
        def send_command():
            # Send the command directly to the PTY
            if args.headless_eval:
                shell_widget.terminal.write(args.headless_eval + '\n')

            # After the timeout, dump the screen content and exit
            def dump_and_exit():
                if args.dump:
                    # For GUI mode, we get the content from the output area
                    content = shell_widget.output_area.toPlainText()
                    print(content)
                else:
                    content = shell_widget.output_area.toPlainText()
                    print(content.strip())

                # Close the application
                app.quit()

            # Use singleShot timer to delay the dump and exit
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(args.headless_timeout * 1000, dump_and_exit)

        # Use singleShot timer to delay sending the command after GUI initialization
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, send_command)  # 500ms delay to allow GUI to initialize

        # Run the application event loop
        sys.exit(app.exec())
    else:
        # Create and show the main window with specified shell type for GUI mode
        window = MainWindow(shell_type=args.shell, scrollback_lines=args.scrollback)
        window.show()

        # If debugging, enable it on the shell widget
        if args.debug:
            shell_widget = window.shell_widget
            shell_widget.debug_enabled = True
            shell_widget.debug_file = args.debug
            shell_widget.logger = logging.getLogger(__name__)

        # Run the application
        sys.exit(app.exec())


if __name__ == '__main__':
    main()
