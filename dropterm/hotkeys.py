import sys
import logging
from PyQt6.QtCore import QAbstractNativeEventFilter, Qt
from PyQt6.QtGui import QKeySequence

# Windows-specific imports
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    # Windows-specific constants
    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
else:
    # For macOS and Linux, we'll implement global hotkey functionality
    # using platform-specific libraries
    if sys.platform == 'darwin':  # macOS
        # On macOS, pynput is often more reliable when accessibility permissions are granted
        try:
            from pynput import keyboard
            GLOBAL_HOTKEY_AVAILABLE = True
            HOTKEY_LIBRARY_USED = "pynput"
        except ImportError:
            try:
                import keyboard
                GLOBAL_HOTKEY_AVAILABLE = True
                HOTKEY_LIBRARY_USED = "keyboard"
            except ImportError:
                GLOBAL_HOTKEY_AVAILABLE = False
                HOTKEY_LIBRARY_USED = None
                logging.warning("Global hotkeys not available: neither 'pynput' nor 'keyboard' module installed")
        except Exception as e:
            GLOBAL_HOTKEY_AVAILABLE = False
            HOTKEY_LIBRARY_USED = None
            logging.warning(f"Global hotkeys not available: {e}")
    else:  # Linux and other platforms
        try:
            import keyboard
            GLOBAL_HOTKEY_AVAILABLE = True
            HOTKEY_LIBRARY_USED = "keyboard"  # Track which library we're using
        except ImportError:
            try:
                from pynput import keyboard
                GLOBAL_HOTKEY_AVAILABLE = True
                HOTKEY_LIBRARY_USED = "pynput"
            except ImportError:
                GLOBAL_HOTKEY_AVAILABLE = False
                HOTKEY_LIBRARY_USED = None
                logging.warning("Global hotkeys not available: neither 'keyboard' nor 'pynput' module installed")
        except Exception as e:
            GLOBAL_HOTKEY_AVAILABLE = False
            HOTKEY_LIBRARY_USED = None
            logging.warning(f"Global hotkeys not available: {e}")

GLOBAL_HOTKEY_ID = 1


class HotkeyEventFilter(QAbstractNativeEventFilter):
    """Receive WM_HOTKEY messages from Windows and dispatch them to a callback."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if sys.platform == 'win32':
            # Windows implementation
            if eventType != "windows_generic_MSG":
                return False, 0

            try:
                msg = wintypes.MSG.from_address(int(message))
            except Exception:
                return False, 0
            if msg.message == WM_HOTKEY:
                self.callback(msg.wParam)
                return True, 0
        # For non-Windows platforms, the hotkey event handling is done differently
        return False, 0


def register_global_hotkey(key, callback):
    """
    Register a global hotkey. This function handles cross-platform implementation.
    Returns True if successful, False otherwise.
    """
    if sys.platform == 'win32':
        return register_windows_hotkey(key, callback)
    else:
        return register_crossplatform_hotkey(key, callback)


def unregister_global_hotkey():
    """
    Unregister the global hotkey.
    """
    if sys.platform == 'win32':
        return unregister_windows_hotkey()
    else:
        return unregister_crossplatform_hotkey()


def register_windows_hotkey(hwnd, key, hotkey_id=GLOBAL_HOTKEY_ID):
    """Register a global hotkey on Windows."""
    if sys.platform != 'win32':
        return False

    parsed = parse_hotkey_to_win(key)
    if not parsed:
        logging.warning("No hotkey set for quake mode; skipping registration.")
        return False

    mods, vk = parsed

    try:
        if ctypes.windll.user32.RegisterHotKey(hwnd, hotkey_id, mods, vk):
            return True
        else:
            logging.warning("Failed to register global hotkey '%s'", key)
            return False
    except Exception as e:
        logging.error(f"Error registering Windows hotkey: {e}")
        return False


def unregister_windows_hotkey(hwnd, hotkey_id=GLOBAL_HOTKEY_ID):
    """Unregister the global hotkey on Windows."""
    if sys.platform != 'win32':
        return True

    try:
        result = ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id)
        return result != 0
    except Exception as e:
        logging.error(f"Error unregistering Windows hotkey: {e}")
        return False


def register_crossplatform_hotkey(key, callback):
    """Register a global hotkey on macOS/Linux using the appropriate primary library based on platform."""
    import sys  # Import sys at the beginning to avoid unbound local error

    if not GLOBAL_HOTKEY_AVAILABLE:
        logging.warning("Global hotkey library not available")
        return False

    # On macOS, prioritize pynput as it generally works better with accessibility permissions
    # On other platforms, prioritize keyboard library
    if sys.platform == 'darwin' and HOTKEY_LIBRARY_USED == "pynput":
        return _register_with_pynput(key, callback)
    elif HOTKEY_LIBRARY_USED == "keyboard":
        try:
            import keyboard

            # Convert the Qt key sequence to a string that the keyboard library understands
            # QKeySequence.toString() provides the standard representation
            seq = QKeySequence(key)
            # Check if the Format attribute exists before using it
            if hasattr(QKeySequence, 'Format') and hasattr(QKeySequence.Format, 'NativeText'):
                hotkey_str = seq.toString(QKeySequence.Format.NativeText)
            elif hasattr(QKeySequence, 'Format') and hasattr(QKeySequence.Format, 'PortableText'):
                hotkey_str = seq.toString(QKeySequence.Format.PortableText)
            else:
                hotkey_str = seq.toString()

            # Handle common special cases in Qt to keyboard library format
            hotkey_str = hotkey_str.replace("Ctrl+", "ctrl+")
            hotkey_str = hotkey_str.replace("Alt+", "alt+")
            hotkey_str = hotkey_str.replace("Shift+", "shift+")
            hotkey_str = hotkey_str.replace("Meta+", "cmd+")  # Cmd key on macOS

            # Special handling for macOS command key
            if sys.platform == 'darwin':  # macOS
                hotkey_str = hotkey_str.replace("Cmd+", "cmd+")
                # Convert common keys to what keyboard library expects
                if len(hotkey_str) > 1 and not any(mod in hotkey_str for mod in ["ctrl", "alt", "shift", "cmd"]):
                    # This is likely a function key or special key
                    hotkey_str = hotkey_str.lower()

            # Register the hotkey using the keyboard library
            keyboard.add_hotkey(hotkey_str, callback)

            # Save reference to the hotkey so we can unregister it later
            setattr(sys.modules[__name__], '_current_hotkey', (hotkey_str, callback, "keyboard"))

            logging.info(f"Successfully registered global hotkey using keyboard library: {hotkey_str}")
            return True
        except Exception as e:
            logging.warning(f"Failed to register hotkey with keyboard library: {e}. Trying pynput as fallback...")
            # If keyboard library fails, try pynput as fallback
            return _register_with_pynput(key, callback)
    else:
        # Use pynput if it's the selected library
        return _register_with_pynput(key, callback)


def _register_with_pynput(key, callback):
    """Register a global hotkey using pynput as fallback."""
    import sys  # Import sys at the beginning of the function
    try:
        # Parse the Qt key sequence to separate modifiers and key
        seq = QKeySequence(key)
        if seq.count() == 0:
            return False

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

        # Map Qt modifiers to pynput keys
        from pynput.keyboard import Key, KeyCode

        # Build the hotkey combination string for pynput GlobalHotKeys
        hotkey_parts = []

        # Add modifiers
        if qt_modifiers & Qt.KeyboardModifier.ControlModifier:
            hotkey_parts.append('<ctrl>')
        if qt_modifiers & Qt.KeyboardModifier.AltModifier:
            hotkey_parts.append('<alt>')
        if qt_modifiers & Qt.KeyboardModifier.ShiftModifier:
            hotkey_parts.append('<shift>')
        if qt_modifiers & Qt.KeyboardModifier.MetaModifier:
            if sys.platform == 'darwin':  # macOS
                hotkey_parts.append('<cmd>')
            else:
                hotkey_parts.append('<super>')  # Usually corresponds to Win/Super key on other platforms

        # Add the main key
        # Get the character corresponding to the Qt key
        key_char = chr(qt_key) if 32 <= qt_key <= 126 else None
        if key_char:
            # For alphanumeric and symbol keys, we'll use the character
            hotkey_parts.append(key_char.lower())
        else:
            # For special keys, we need to map them to pynput equivalents
            # Map Qt key to pynput key
            key_name = qt_key_to_keyboard_key(qt_key)
            if key_name:
                hotkey_parts.append(f'<{key_name}>')

        # Join to create the hotkey string
        hotkey_str = '+'.join(hotkey_parts)

        # Create a GlobalHotKeys instance
        from pynput import keyboard
        hotkeys_dict = {hotkey_str: callback}
        global_hotkeys = keyboard.GlobalHotKeys(hotkeys_dict)

        # Start the hotkey listener
        global_hotkeys.start()

        # Save reference to the hotkey so we can stop it later
        setattr(sys.modules[__name__], '_current_hotkey', (global_hotkeys, "pynput", hotkey_str))

        logging.info(f"Successfully registered global hotkey using pynput library: {hotkey_str} (from {seq.toString()})")
        return True
    except Exception as e:
        logging.error(f"Failed to register global hotkey with pynput: {e}")
        return False


def unregister_crossplatform_hotkey():
    """Unregister the global hotkey on macOS/Linux."""
    if not GLOBAL_HOTKEY_AVAILABLE:
        return False

    import sys  # Import sys at the beginning of the function
    try:
        # Remove the current hotkey if it exists
        hotkey_data = getattr(sys.modules[__name__], '_current_hotkey', None)
        if hotkey_data:
            # Check which library was used based on tuple structure
            if len(hotkey_data) == 3 and hotkey_data[2] == "keyboard":  # Using keyboard library
                import keyboard
                hotkey_str, callback, lib = hotkey_data
                keyboard.remove_hotkey(hotkey_str)
            elif len(hotkey_data) == 3 and hotkey_data[2] == "pynput":  # Using pynput library
                global_hotkeys, lib, hotkey_str = hotkey_data
                # Stop the global hotkey listener
                global_hotkeys.stop()

                # Wait a brief moment to ensure the listener has stopped
                import time
                time.sleep(0.1)

            # Remove the reference to the hotkey
            delattr(sys.modules[__name__], '_current_hotkey')
        return True
    except Exception as e:
        logging.error(f"Failed to unregister global hotkey: {e}")
        return False


def qt_key_to_keyboard_key(qt_key):
    """Convert a Qt key to the corresponding keyboard library key string."""
    # Handle special keys
    if hasattr(qt_key, 'value'):
        qt_key_int = qt_key.value
    else:
        qt_key_int = int(qt_key)

    # Map Qt key codes to keyboard library key strings
    key_map = {
        0x01000000: 'esc',
        0x01000001: 'tab',
        0x01000002: 'backspace',
        0x01000003: 'enter',
        0x01000004: 'enter',  # return
        0x01000005: 'insert',
        0x01000006: 'delete',
        0x01000007: 'pause',
        0x01000008: 'print_screen',
        0x01000009: 'sys_req',
        0x0100000a: 'clear',
        0x01000010: 'home',
        0x01000011: 'end',
        0x01000012: 'left',
        0x01000013: 'up',
        0x01000014: 'right',
        0x01000015: 'down',
        0x01000016: 'page_up',
        0x01000017: 'page_down',
        0x01000020: 'shift',
        0x01000021: 'ctrl',
        0x01000022: 'alt',
        0x01000023: 'cmd',  # On macOS, this maps to cmd
        0x01000024: 'caps_lock',
        0x01000025: 'num_lock',
        0x01000026: 'scroll_lock',
        0x01000030: 'f1',
        0x01000031: 'f2',
        0x01000032: 'f3',
        0x01000033: 'f4',
        0x01000034: 'f5',
        0x01000035: 'f6',
        0x01000036: 'f7',
        0x01000037: 'f8',
        0x01000038: 'f9',
        0x01000039: 'f10',
        0x0100003a: 'f11',
        0x0100003b: 'f12',
        0x0100003c: 'f13',
        0x0100003d: 'f14',
        0x0100003e: 'f15',
        0x0100003f: 'f16',
        0x01000040: 'f17',
        0x01000041: 'f18',
        0x01000042: 'f19',
        0x01000043: 'f20',
        0x01000044: 'f21',
        0x01000045: 'f22',
        0x01000046: 'f23',
        0x01000047: 'f24',
        0x01000053: 'menu',
    }

    # Return special key if it exists in the map
    if qt_key_int in key_map:
        return key_map[qt_key_int]

    # For standard ASCII characters (A-Z, 0-9, etc.)
    if 0x41 <= qt_key_int <= 0x5A:  # A-Z
        return chr(qt_key_int).lower()
    if 0x30 <= qt_key_int <= 0x39:  # 0-9
        return chr(qt_key_int)

    # For other keys, try to get character representation
    return chr(qt_key_int).lower() if 32 <= qt_key_int <= 126 else str(qt_key_int)


def key_string_to_vk(key: str) -> int | None:
    """Map a textual key token (e.g., 'A', 'F1', '`') to a Windows virtual-key code."""
    if sys.platform != 'win32':
        return None  # This function is Windows-specific

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

