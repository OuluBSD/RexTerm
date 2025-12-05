import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter
from PyQt6.QtGui import QKeySequence

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
    seq = QKeySequence(hotkey)
    try:
        text = seq.toString(QKeySequence.Format.PortableText)  # PyQt6 6.5+
    except AttributeError:
        text = seq.toString()
    if not text:
        return None

    parts = [p.strip() for p in text.split('+') if p.strip()]
    mods = 0
    key_token = None
    for part in parts:
        lower = part.lower()
        if lower in ('ctrl', 'control', 'ctl'):
            mods |= MOD_CONTROL
        elif lower == 'alt':
            mods |= MOD_ALT
        elif lower == 'shift':
            mods |= MOD_SHIFT
        elif lower in ('meta', 'win', 'windows', 'super', 'command', 'cmd'):
            mods |= MOD_WIN
        else:
            key_token = part

    if key_token is None:
        return None

    vk = key_string_to_vk(key_token)
    if vk is None:
        return None

    return mods, vk

