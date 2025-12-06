import sys
import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter, Qt
from PyQt6.QtGui import QKeySequence

# Windows-specific constants
if sys.platform == 'win32':
    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008

GLOBAL_HOTKEY_ID = 1


class HotkeyEventFilter(QAbstractNativeEventFilter):
    """Receive WM_HOTKEY messages from Windows and dispatch them to a callback."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if sys.platform != 'win32':
            # On non-Windows systems, we don't handle native hotkey events
            return False, 0

        if eventType != "windows_generic_MSG":
            return False, 0

        try:
            msg = wintypes.MSG.from_address(int(message))
        except Exception:
            return False, 0
        if msg.message == WM_HOTKEY:
            self.callback(msg.wParam)
            return True, 0
        return False, 0


def key_string_to_vk(key: str) -> int | None:
    """Map a textual key token (e.g., 'A', 'F1', '`') to a Windows virtual-key code."""
    if sys.platform != 'win32':
        return None  # Not applicable on non-Windows platforms

    tok = key.upper()
    if len(tok) == 1:
        if 'A' <= tok <= 'Z':
            return ord(tok)
        if '0' <= tok <= '9':
            return ord(tok)
        if tok in ('`', '~'):
            return 0xC0
        if tok == '-':
            return 0xBD
        if tok == '=':
            return 0xBB
        # Handle Nordic keyboard layout where § is on the same physical key as '1'
        # Based on Qt key code 65756 (0x100FC) mapping to Windows VK 0x00FC for Nordic keyboards
        if tok == '§':
            return 0x00FC  # 65756 & 0xFFFF = 0x00FC - confirmed to work on Nordic keyboards
        # Handle other Nordic characters that might be represented with longer codes
        # by checking if ord() works on them, though this is less likely for single char
        try:
            if ord(tok) == 167:  # Unicode code point for §
                return 0x00FC  # 65756 & 0xFFFF = 0x00FC
        except TypeError:
            pass

    if tok.startswith('F') and tok[1:].isdigit():
        num = int(tok[1:])
        if 1 <= num <= 24:
            return 0x70 + (num - 1)

    special_map = {
        'SPACE': 0x20,
        'TAB': 0x09,
        'ESC': 0x1B,
        'ESCAPE': 0x1B,
        'ENTER': 0x0D,
        'RETURN': 0x0D,
        'BACKSPACE': 0x08,
    }
    return special_map.get(tok)


def parse_hotkey_to_win(hotkey: str) -> tuple[int, int] | None:
    """Parse a QKeySequence-style string into (modifiers, vk) for RegisterHotKey."""
    if sys.platform != 'win32':
        return None  # Only applicable on Windows

    seq = QKeySequence(hotkey)
    if seq.count() == 0:
        return None

    # Get the raw key combination from Qt (only use first key combination)
    key_combo = seq[0]

    # In PyQt6, seq[0] returns QKeyCombination, we need to extract the key and modifiers
    try:
        # PyQt6 6.0+ uses QKeyCombination
        qt_key = key_combo.key()
        qt_modifiers = key_combo.keyboardModifiers()
    except AttributeError:
        # Fallback for older versions that return int directly
        key_combo_int = int(key_combo)
        qt_key = key_combo_int & 0xFFFF
        qt_modifiers = key_combo_int >> 16

    # Convert Qt modifiers to Windows modifiers
    mods = 0
    if isinstance(qt_modifiers, int):
        # Old-style integer modifiers
        if qt_modifiers & 0x04000000:  # Qt::ControlModifier
            mods |= MOD_CONTROL
        if qt_modifiers & 0x08000000:  # Qt::AltModifier
            mods |= MOD_ALT
        if qt_modifiers & 0x02000000:  # Qt::ShiftModifier
            mods |= MOD_SHIFT
        if qt_modifiers & 0x10000000:  # Qt::MetaModifier (Win key)
            mods |= MOD_WIN
    else:
        # New-style Qt.KeyboardModifier flags
        if qt_modifiers & Qt.KeyboardModifier.ControlModifier:
            mods |= MOD_CONTROL
        if qt_modifiers & Qt.KeyboardModifier.AltModifier:
            mods |= MOD_ALT
        if qt_modifiers & Qt.KeyboardModifier.ShiftModifier:
            mods |= MOD_SHIFT
        if qt_modifiers & Qt.KeyboardModifier.MetaModifier:
            mods |= MOD_WIN

    # Get the integer value of the key
    if hasattr(qt_key, 'value'):
        qt_key_int = qt_key.value
    else:
        qt_key_int = int(qt_key)

    # For Nordic keyboards, Qt key code 0x00FC maps directly to VK 0x00FC
    # This handles the § key (Qt uses 0x100FC, where 0x01 is Key_* namespace)
    if qt_key_int == 0x00FC or qt_key_int == 0x100FC:
        return mods, 0x00FC

    # For standard keys, try to convert via string representation
    try:
        text = seq.toString(QKeySequence.Format.PortableText)  # PyQt6 6.5+
    except AttributeError:
        text = seq.toString()

    if not text:
        return None

    parts = [p.strip() for p in text.split('+') if p.strip()]
    key_token = None
    for part in parts:
        lower = part.lower()
        if lower not in ('ctrl', 'control', 'ctl', 'alt', 'shift', 'meta', 'win', 'windows', 'super', 'command', 'cmd'):
            key_token = part
            break

    if key_token is None:
        return None

    vk = key_string_to_vk(key_token)
    if vk is None:
        return None

    return mods, vk

