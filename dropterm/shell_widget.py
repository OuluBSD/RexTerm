from __future__ import annotations

import html
import re
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QTimer, Qt
from PyQt6.QtGui import QFont, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget
from pyte import screens

from .ansi import ansi_to_html
from .app_settings import AppSettings
from .terminal_emulator import TerminalEmulator
from .terminal_thread import TerminalThread

if TYPE_CHECKING:
    from .main_window import MainWindow


class ShellWidget(QWidget):
    """Main shell widget with terminal emulation."""

    def __init__(self, shell_type='auto', scrollback_lines=1000, term_override=None, colorterm_value="truecolor", settings: AppSettings | None = None):
        super().__init__()

        self.settings = settings or AppSettings()

        # Track visual prefs
        self.font_family = self.settings.font_family
        self.font_size = self.settings.font_size
        palette = self.settings.palette()
        self.base_bg = palette["background"]
        self.base_fg = palette["foreground"]
        self.cursor_blink = self.settings.cursor_blink

        # Buffer to handle partial lines from terminal (initialize before using append_output)
        self.output_buffer = ""

        # Tracking for command echo to prevent double display
        self.waiting_for_command_echo = False
        self.last_command = ""

        # Track if we're expecting a new prompt
        self.expecting_new_prompt = False

        # Drop preserved input after commands so stale text doesn't linger
        self.clear_pending_input = False

        # Track application keypad mode state for ncurses apps
        self.application_mode = False

        # Set default shell type based on platform - 'bash' is more appropriate for Linux
        effective_shell_type = shell_type if shell_type != 'auto' else ('bash' if sys.platform != 'win32' else 'auto')

        self.terminal = TerminalEmulator(cols=80, rows=24, shell_type=effective_shell_type, history_lines=scrollback_lines, term_override=term_override, colorterm_value=colorterm_value)
        if not self.terminal.start():
            raise Exception("Could not start terminal emulator")

        self.in_alternate_screen = False
        self._alt_history_marker: tuple[int, int] | None = None
        # Use \n for Unix systems and \r for Windows
        self.enter_sequence = '\n' if sys.platform != 'win32' else '\r'

        self.debug_enabled = False
        self.debug_file = None
        self.logger = None

        # Shortcut sequences (user-configurable)
        self.copy_sequence: QKeySequence | None = None
        self.paste_sequence: QKeySequence | None = None
        self.new_window_sequence: QKeySequence | None = None
        self.quake_taller_sequence: QKeySequence | None = None
        self.quake_shorter_sequence: QKeySequence | None = None

        # Precompute a color map for HTML rendering
        self.color_map = {
            'black': '#000000',
            'red': '#cc0000',
            'green': '#009900',
            'yellow': '#999900',
            'brown': '#999900',
            'blue': '#0000cc',
            'magenta': '#cc00cc',
            'cyan': '#009999',
            'white': '#cccccc',
            'lightgray': '#cccccc',
            'lightgrey': '#cccccc',
            'brightblack': '#555555',
            'brightred': '#ff5555',
            'brightgreen': '#55ff55',
            'brightyellow': '#ffff55',
            'brightbrown': '#ffff55',
            'brightblue': '#5555ff',
            'brightmagenta': '#ff55ff',
            'brightcyan': '#55ffff',
            'brightwhite': '#ffffff'
        }
        self.xterm_palette = self._build_xterm_palette()

        self.setup_ui()
        self._update_shortcut_sequences(self.settings)

        self.terminal_thread = TerminalThread(self.terminal)
        self.terminal_thread.output_received.connect(self.append_output)
        self.terminal_thread.start()

        self.command_history = []
        self.history_index = -1
        self.current_command = ""

        QTimer.singleShot(0, self.update_terminal_size)

    def setup_ui(self):
        layout = QVBoxLayout()

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.installEventFilter(self)
        self.output_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.output_area.setFocus()
        font = QFont(self.font_family, self.font_size)
        self.output_area.setFont(font)
        self.output_area.setCursorWidth(0)
        self.output_area.setStyleSheet(f"background-color:{self.base_bg}; color:{self.base_fg};")
        self.output_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.output_area.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.input_start_position = 0

        layout.addWidget(self.output_area)
        self.setLayout(layout)

    def update_terminal_size(self):
        if not self.output_area:
            return

        viewport = self.output_area.viewport()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return

        metrics = self.output_area.fontMetrics()
        char_width = max(1, metrics.horizontalAdvance("M"))
        char_height = max(1, metrics.lineSpacing())

        new_cols = max(2, (viewport.width() // char_width) - 1)
        new_rows = max(2, viewport.height() // char_height)

        if new_cols != self.terminal.cols or new_rows != self.terminal.rows:
            self.terminal.resize(new_cols, new_rows)
            self.append_output("")

    def _wrap_html(self, body: str) -> str:
        blink_rule = "animation: cursor-blink 1s steps(1, start) infinite;" if self.cursor_blink else "animation: none;"
        cursor_css = (
            "<style>"
            f".cursor-block {{ {blink_rule} }}"
            "@keyframes cursor-blink { 0%,49% { opacity: 1; } 50%,100% { opacity: 0; } }"
            "</style>"
        )
        return (
            f"{cursor_css}"
            f"<pre style=\"margin:0; white-space: pre; font-family:'{self.font_family}', monospace; font-size:{self.font_size}pt; background-color:{self.base_bg}; color:{self.base_fg};\">"
            f"{body}"
            "</pre>"
        )

    def apply_settings(self, settings: AppSettings):
        self.settings = settings
        self.font_family = settings.font_family
        self.font_size = settings.font_size
        self._update_shortcut_sequences(settings)
        palette = settings.palette()
        self.base_bg = palette["background"]
        self.base_fg = palette["foreground"]
        self.cursor_blink = settings.cursor_blink

        self.output_area.setFont(QFont(self.font_family, self.font_size))
        self.output_area.setStyleSheet(f"background-color:{self.base_bg}; color:{self.base_fg};")

        if settings.scrollback_lines != getattr(self.terminal, "history_lines", settings.scrollback_lines):
            self.terminal.history_lines = settings.scrollback_lines
            try:
                self.terminal.screen.history.maxlen = settings.scrollback_lines
            except Exception:
                pass

        self.append_output("")
        self.update_terminal_size()

    def _update_shortcut_sequences(self, settings: AppSettings):
        self.copy_sequence = QKeySequence(settings.copy_shortcut) if settings.copy_shortcut else None
        self.paste_sequence = QKeySequence(settings.paste_shortcut) if settings.paste_shortcut else None
        self.new_window_sequence = QKeySequence(settings.new_window_shortcut) if settings.new_window_shortcut else None
        self.quake_taller_sequence = QKeySequence(settings.quake_resize_up_shortcut) if settings.quake_resize_up_shortcut else None
        self.quake_shorter_sequence = QKeySequence(settings.quake_resize_down_shortcut) if settings.quake_resize_down_shortcut else None

    def _css_color(self, value):
        if not value or value == "default":
            return None

        if isinstance(value, int):
            return self.xterm_palette.get(value)
        if isinstance(value, str) and value.isdigit():
            try:
                idx = int(value, 10)
                if 0 <= idx <= 255:
                    return self.xterm_palette.get(idx)
            except ValueError:
                pass

        if isinstance(value, str):
            if value.startswith("#") and len(value) == 7:
                return value.lower()
            if re.fullmatch(r"[0-9a-fA-F]{6}", value):
                return f"#{value.lower()}"

        return self.color_map.get(value, None)

    def _style_for_char(self, char) -> str:
        fg = self._css_color(getattr(char, "fg", None))
        bg = self._css_color(getattr(char, "bg", None))

        if getattr(char, "reverse", False):
            fg, bg = bg, fg

        styles = []
        if fg:
            styles.append(f"color:{fg}")
        if bg:
            styles.append(f"background-color:{bg}")
        if getattr(char, "conceal", False):
            styles.append("color: transparent")
        if getattr(char, "bold", False):
            styles.append("font-weight:bold")
        if getattr(char, "italics", False):
            styles.append("font-style:italic")
        if getattr(char, "underscore", False):
            styles.append("text-decoration: underline")
        return ";".join(styles)

    def _build_xterm_palette(self):
        palette = {}
        base16 = [
            (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
            (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
            (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
            (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
        ]
        for idx, (r, g, b) in enumerate(base16):
            palette[idx] = f"#{r:02x}{g:02x}{b:02x}"

        steps = [0, 95, 135, 175, 215, 255]
        idx = 16
        for r in steps:
            for g in steps:
                for b in steps:
                    palette[idx] = f"#{r:02x}{g:02x}{b:02x}"
                    idx += 1

        for i in range(24):
            level = 8 + i * 10
            palette[232 + i] = f"#{level:02x}{level:02x}{level:02x}"

        return palette

    def _render_line(self, line_map, cursor_col=None):
        plain_chars = []
        html_parts = []
        current_style = None

        for col in range(self.terminal.screen.columns):
            char = line_map[col]
            ch = char.data if char.data is not None else " "
            plain_chars.append(ch)

            is_cursor_cell = cursor_col is not None and col == cursor_col
            style = self._style_for_char(char) or None

            if is_cursor_cell:
                if current_style is not None:
                    html_parts.append("</span>")
                    current_style = None

                base_style = self._style_for_char(char)
                base_parts = [
                    part for part in (base_style.split(";") if base_style else [])
                    if part and not part.startswith("color:") and not part.startswith("background-color:")
                ]

                fg = self._css_color(getattr(char, "fg", None)) or self.base_fg
                bg = self._css_color(getattr(char, "bg", None)) or self.base_bg

                cursor_styles = base_parts + [f"background-color:{fg}", f"color:{bg}"]
                cursor_char = ch if ch != " " else "\u00a0"
                html_parts.append(f'<span class="cursor-block" style="{";".join(cursor_styles)}">')
                html_parts.append(html.escape(cursor_char))
                html_parts.append("</span>")
                continue

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
        plain_lines = []
        html_lines = []

        screen = self.terminal.screen
        line_sources = []

        history_active = isinstance(screen, screens.HistoryScreen) and not self.in_alternate_screen
        if history_active:
            line_sources.extend(list(screen.history.top))
            cursor_row_offset = len(screen.history.top)
        else:
            cursor_row_offset = 0

        cursor_line_index = None
        cursor_col = None
        if getattr(screen, "cursor", None) is not None:
            cursor_col = screen.cursor.x
            cursor_line_index = cursor_row_offset + screen.cursor.y

        for row in range(screen.lines):
            line_sources.append(screen.buffer[row])

        if history_active and screen.history.bottom:
            line_sources.extend(list(screen.history.bottom))

        if cursor_line_index is not None and cursor_line_index >= len(line_sources):
            cursor_line_index = None
            cursor_col = None

        for idx, line in enumerate(line_sources):
            active_cursor_col = cursor_col if cursor_line_index is not None and idx == cursor_line_index else None
            plain_line, html_line = self._render_line(line, cursor_col=active_cursor_col)
            plain_lines.append(plain_line)
            html_lines.append(html_line)

        return "\n".join(plain_lines), "\n".join(html_lines)

    def append_output(self, text):
        if self.debug_enabled and self.logger:
            self.logger.debug(f"append_output called with text length: {len(text) if text else 0}")
            if text:
                self.logger.debug(f"append_output raw text: {repr(text[:200])}")

        if text:
            # Detect application keypad mode changes (DECCKM - DEC Cursor Keys Mode and DECKPAM/DECKPNM - Application/Normal Keypad Mode)
            if "\x1b[?1h" in text or "\x1b[?66h" in text:  # Application cursor keys or Application keypad mode
                self.application_mode = True
            if "\x1b[?1l" in text or "\x1b[?66l" in text:  # Normal cursor keys or Normal keypad mode
                self.application_mode = False

            if any(seq in text for seq in ("\x1b[?1049h", "\x1b[?47h", "\x1b[?1047h")):
                screen = self.terminal.screen
                if isinstance(screen, screens.HistoryScreen):
                    self._alt_history_marker = (len(screen.history.top), len(screen.history.bottom))
                self.in_alternate_screen = True
            if any(seq in text for seq in ("\x1b[?1049l", "\x1b[?47l", "\x1b[?1047l")):
                screen = self.terminal.screen
                if isinstance(screen, screens.HistoryScreen) and self._alt_history_marker:
                    top_len, bottom_len = self._alt_history_marker
                    while len(screen.history.top) > top_len:
                        screen.history.top.pop()
                    while len(screen.history.bottom) > bottom_len:
                        screen.history.bottom.pop()
                self._alt_history_marker = None
                self.in_alternate_screen = False

        scrollbar = self.output_area.verticalScrollBar()
        previous_scroll_value = scrollbar.value()
        at_bottom = previous_scroll_value >= scrollbar.maximum()

        display_text, display_html = self._render_screen()

        self.output_area.setHtml(self._wrap_html(display_html))

        doc_text = self.output_area.toPlainText()
        self.input_start_position = len(doc_text)

        if self.debug_enabled and self.logger:
            self.logger.debug(f"Terminal screen display output: {repr(display_text[:500])}")
            self.logger.debug(f"Updated input_start_position to: {self.input_start_position}")

        new_cursor = self.output_area.textCursor()
        new_cursor.movePosition(new_cursor.MoveOperation.End)
        self.output_area.setTextCursor(new_cursor)
        self.output_area.setFocus()

        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(min(previous_scroll_value, scrollbar.maximum()))

    def execute_command(self):
        full_text = self.output_area.toPlainText()
        command = full_text[self.input_start_position:]

        if command:
            self.command_history.append(command)
            self.history_index = len(self.command_history)

            if hasattr(self.terminal, 'shell_type') and self.terminal.shell_type in ['bash', 'auto'] and self.terminal.msys64_path:
                self.terminal.write(command + '\n')
            else:
                self.terminal.write(command + '\r')

            self.clear_pending_input = True
            self.update_input_area("")

    def eventFilter(self, obj, event):
        if obj is self.output_area and event.type() == QEvent.Type.KeyPress:
            return self.handle_key_press(event)
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_terminal_size()

    def handle_key_press(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()
        cursor = self.output_area.textCursor()

        def _mods_to_int(mods):
            try:
                return int(mods)
            except TypeError:
                return int(getattr(mods, "value", 0))

        event_sequence = QKeySequence(_mods_to_int(modifiers) | int(key))

        main = self.window()
        # Use string comparison to avoid circular import
        if main and main.__class__.__name__ == "MainWindow" and main.settings.quake_enabled:
            if self.quake_taller_sequence and event_sequence.matches(self.quake_taller_sequence) == QKeySequence.SequenceMatch.ExactMatch:
                main.adjust_quake_height(5)
                event.accept()
                return True
            if self.quake_shorter_sequence and event_sequence.matches(self.quake_shorter_sequence) == QKeySequence.SequenceMatch.ExactMatch:
                main.adjust_quake_height(-5)
                event.accept()
                return True
            if not self.quake_taller_sequence and modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Down:
                main.adjust_quake_height(5)
                event.accept()
                return True
            if not self.quake_shorter_sequence and modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Up:
                main.adjust_quake_height(-5)
                event.accept()
                return True

        allow_default_copy = (self.copy_sequence is None) or (
            self.copy_sequence.matches(QKeySequence(AppSettings.copy_shortcut)) == QKeySequence.SequenceMatch.ExactMatch
        )
        allow_default_paste = (self.paste_sequence is None) or (
            self.paste_sequence.matches(QKeySequence(AppSettings.paste_shortcut)) == QKeySequence.SequenceMatch.ExactMatch
        )

        if cursor.hasSelection() and self.copy_sequence:
            if event_sequence.matches(self.copy_sequence) == QKeySequence.SequenceMatch.ExactMatch:
                self.output_area.copy()
                event.accept()
                return True

        if self.paste_sequence and event_sequence.matches(self.paste_sequence) == QKeySequence.SequenceMatch.ExactMatch:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                normalized = text.replace("\r\n", "\n").replace("\r", "\n")
                self.terminal.write(normalized)
            event.accept()
            return True

        if self.new_window_sequence and event_sequence.matches(self.new_window_sequence) == QKeySequence.SequenceMatch.ExactMatch:
            main = self.window()
            if isinstance(main, MainWindow):
                main.open_new_window()
            event.accept()
            return True

        if cursor.hasSelection():
            if allow_default_copy and ((modifiers == Qt.KeyboardModifier.ControlModifier and key in (Qt.Key.Key_C, Qt.Key.Key_Insert)) or \
               (modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_C)):
                return False

        if allow_default_paste and ((modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V) or \
           (modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_Insert)):
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                normalized = text.replace("\r\n", "\n").replace("\r", "\n")
                self.terminal.write(normalized)
            event.accept()
            return True

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

        arrow_map_app = {  # Application mode sequences
            Qt.Key.Key_Up: "\x1bOA",
            Qt.Key.Key_Down: "\x1bOB",
            Qt.Key.Key_Right: "\x1bOC",
            Qt.Key.Key_Left: "\x1bOD",
        }

        arrow_map_normal = {  # Normal mode sequences
            Qt.Key.Key_Up: "A",
            Qt.Key.Key_Down: "B",
            Qt.Key.Key_Right: "C",
            Qt.Key.Key_Left: "D",
        }

        if key in arrow_map_normal:
            # For ncurses applications, we may need to send application mode sequences
            # Check if terminal is in application mode based on escape sequence tracking
            if self.application_mode:
                self.terminal.write(arrow_map_app[key])
            else:
                self.terminal.write(csi_with_mod(arrow_map_normal[key]))
            event.accept()
            return True

        # Handle Home/End keys with application mode consideration
        if key == Qt.Key.Key_Home:
            if self.application_mode:
                self.terminal.write("\x1bOH")  # Application mode sequence
            else:
                self.terminal.write(csi_with_mod("H"))  # Normal sequence
            event.accept()
            return True
        if key == Qt.Key.Key_End:
            if self.application_mode:
                self.terminal.write("\x1bOF")  # Application mode sequence
            else:
                self.terminal.write(csi_with_mod("F"))  # Normal sequence
            event.accept()
            return True

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

        if not event.text() and (modifiers & Qt.KeyboardModifier.ControlModifier) and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            ctrl_char = chr(key - Qt.Key.Key_A + 1)
            self.terminal.write(ctrl_char)
            event.accept()
            return True

        if event.text():
            text = event.text()
            if modifiers & Qt.KeyboardModifier.AltModifier and not text.startswith("\x1b"):
                text = "\x1b" + text
            self.terminal.write(text)
            event.accept()
            return True

        return True

    def update_input_area(self, text):
        display_text, display_html = self._render_screen()

        full_content_html = display_html + html.escape(text)
        self.output_area.setHtml(self._wrap_html(full_content_html))

        cursor = self.output_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_area.setTextCursor(cursor)

        doc_text = self.output_area.toPlainText()
        self.input_start_position = max(0, len(doc_text) - len(text))

    def clear_screen(self):
        self.terminal.screen.reset()

        display_text, display_html = self._render_screen()
        self.output_area.setHtml(self._wrap_html(display_html))
        self.input_start_position = len(self.output_area.toPlainText())

        # Use 'clear' for Unix systems and 'cls' for Windows
        if sys.platform == 'win32':
            self.terminal.write('cls\n')
        else:
            self.terminal.write('clear\n')

    def closeEvent(self, event):
        if self.output_buffer:
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
