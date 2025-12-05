import os
import queue
import time
import sys

import pyte
from pyte import screens

# Import platform-specific modules
if sys.platform == 'win32':
    import winreg
    import winpty as pywinpty

    def find_msys64_path():
        """Find the MSYS64 installation path by checking common locations and registry entries."""
        common_paths = [
            r"E:\active\msys64",
            r"C:\msys64",
            r"D:\msys64",
            r"C:\Tools\msys64",
            os.path.expanduser(r"~\msys64"),
        ]

        for path in common_paths:
            if path and os.path.exists(path):
                bash_path = os.path.join(path, "usr", "bin", "bash.exe")
                if os.path.exists(bash_path):
                    return path

        try:
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ),
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
                                        pass
                                i += 1
                            except OSError:
                                break
                except OSError:
                    continue
        except Exception:
            pass

        return None
else:
    import ptyprocess

    def find_msys64_path():
        """Return None for non-Windows platforms"""
        return None


class TerminalEmulator:
    """Wrapper for cross-platform PTY with pyte terminal emulation."""

    def __init__(self, cols=80, rows=24, shell_type='bash', history_lines=1000, term_override=None, colorterm_value="truecolor", exit_callback=None):
        self.cols = cols
        self.rows = rows
        self.history_lines = history_lines
        self.running = False
        self.pty_process = None
        self.command_queue = queue.Queue()
        self.shell_type = shell_type
        self.msys64_path = find_msys64_path() if shell_type in ['bash', 'auto'] else None
        self.term_override = term_override
        self.colorterm_value = colorterm_value
        self.exit_callback = exit_callback

        self.screen = screens.HistoryScreen(cols, rows, history=history_lines)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        # Mouse tracking state
        self.mouse_tracking_normal = False  # \x1b[?1000h
        self.mouse_tracking_button = False  # \x1b[?1002h
        self.mouse_tracking_any = False     # \x1b[?1003h

    def start(self):
        try:
            env_vars = os.environ.copy()
            term_value = self.term_override or "xterm-256color"
            env_vars["TERM"] = term_value
            if self.colorterm_value and self.colorterm_value.lower() != "none":
                env_vars["COLORTERM"] = self.colorterm_value
            env_vars.setdefault("TERM_PROGRAM", "dropterm")
            env_vars.setdefault("TERM_PROGRAM_VERSION", "0.1")

            if sys.platform == 'win32':
                if self.msys64_path:
                    terminfo_path = os.path.join(self.msys64_path, "usr", "share", "terminfo")
                    env_vars.setdefault("TERMINFO", terminfo_path)
                    env_vars.setdefault("TERMINFO_DIRS", terminfo_path)

                if self.shell_type == 'bash' or (self.shell_type == 'auto' and self.msys64_path):
                    if self.msys64_path:
                        bash_path = os.path.join(self.msys64_path, "usr", "bin", "bash.exe")
                        self.pty_process = pywinpty.ptyprocess.PtyProcess.spawn([bash_path, "--login", "-i"], env=env_vars)
                    else:
                        self.pty_process = pywinpty.ptyprocess.PtyProcess.spawn(['cmd.exe'], env=env_vars)
                else:
                    self.pty_process = pywinpty.ptyprocess.PtyProcess.spawn(['cmd.exe'], env=env_vars)
            else:
                # For Unix-like platforms (Linux, macOS), use ptyprocess
                # Determine which shell to use
                shell_cmd = self._get_shell_command()

                # Create PTY process
                self.pty_process = ptyprocess.PtyProcess.spawn(shell_cmd, env=env_vars)

            self.running = True
            return True
        except Exception as e:
            print(f"Failed to start terminal: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_shell_command(self):
        """Get the appropriate shell command for the current platform"""
        if sys.platform == 'win32':
            # Windows implementation handled separately
            return []

        # For Linux/Unix systems, determine the shell based on user preference or defaults
        if self.shell_type == 'bash':
            return self._find_shell_command(['bash', '/bin/bash', '/usr/bin/bash'], ['--login', '-i'])
        elif self.shell_type == 'zsh':
            return self._find_shell_command(['zsh', '/bin/zsh', '/usr/bin/zsh'], ['--login', '-i'])
        elif self.shell_type == 'cmd':
            # For Linux, if cmd is requested, use sh as a fallback
            return self._find_shell_command(['sh', '/bin/sh', '/usr/bin/sh'], ['--login', '-i'])
        elif self.shell_type == 'auto':
            # Auto-detection: try to get the user's default shell from environment or /etc/passwd
            return self._get_default_shell()
        else:
            # Default fallback
            return self._find_shell_command(['bash', '/bin/bash', '/usr/bin/bash'], ['--login', '-i'])

    def _find_shell_command(self, possible_paths, args):
        """Find the first available shell from a list of possible paths"""
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return [path] + args
        # If none of the specific paths work, return the first one in the list
        return [possible_paths[0]] + args

    def _get_default_shell(self):
        """Get the user's default shell"""
        import pwd

        # First try to get shell from environment
        shell_env = os.environ.get('SHELL')
        if shell_env and os.path.exists(shell_env) and os.access(shell_env, os.X_OK):
            return [shell_env, '--login', '-i']

        # If not available, try to get user's shell from /etc/passwd
        try:
            user_info = pwd.getpwuid(os.getuid())
            user_shell = user_info.pw_shell
            if user_shell and os.path.exists(user_shell) and os.access(user_shell, os.X_OK):
                return [user_shell, '--login', '-i']
        except Exception:
            pass

        # Fallback to bash
        return self._find_shell_command(['bash', '/bin/bash', '/usr/bin/bash'], ['--login', '-i'])

    def read(self, size=1024):
        if not self.running:
            return ''

        try:
            if sys.platform == 'win32':
                if not self.pty_process.isalive():
                    return ''
                raw_data = self.pty_process.read(size)
                if raw_data:
                    self.stream.feed(raw_data)
                return raw_data
            else:
                # For Unix-like systems using ptyprocess
                if not self.pty_process.isalive():
                    return ''
                try:
                    raw_data = self.pty_process.read(size)
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode('utf-8', errors='ignore')
                    if raw_data:
                        self.stream.feed(raw_data)
                    return raw_data
                except:
                    return ''
        except Exception as e:
            print(f"Read error: {e}")
            self.running = False
            return ''

    def write(self, data):
        if not self.running:
            return

        try:
            if sys.platform == 'win32':
                if not self.pty_process.isalive():
                    return
                self.pty_process.write(data)
            else:
                # For Unix-like systems using ptyprocess
                if not self.pty_process.isalive():
                    return
                # Ensure data is bytes for ptyprocess
                if isinstance(data, str):
                    data = data.encode('utf-8')
                self.pty_process.write(data)
        except Exception as e:
            print(f"Write error: {e}")
            self.running = False

    def resize(self, cols, rows):
        self.cols = cols
        self.rows = rows

        if sys.platform == 'win32':
            if self.pty_process:
                try:
                    self.pty_process.setwinsize(rows, cols)
                except Exception as e:
                    print(f"Resize error: {e}")
        else:
            # For Unix-like systems using ptyprocess
            if self.pty_process:
                try:
                    # ptyprocess is already imported at the top for non-Windows platforms
                    self.pty_process.setwinsize(rows, cols)
                except Exception as e:
                    print(f"Resize error: {e}")

        try:
            self.screen.resize(rows, cols)
        except Exception as e:
            print(f"pyte resize error: {e}")

    def close(self):
        self.running = False
        if sys.platform == 'win32':
            if self.pty_process and self.pty_process.isalive():
                try:
                    self.pty_process.write('exit\r\n')
                    time.sleep(0.1)
                    if self.pty_process.isalive():
                        self.pty_process.terminate(force=True)
                except Exception:
                    pass
        else:
            # Unix-like systems
            if self.pty_process and self.pty_process.isalive():
                try:
                    # Ensure data is bytes for ptyprocess
                    self.pty_process.write(b'exit\r\n')
                    time.sleep(0.1)
                    if self.pty_process.isalive():
                        self.pty_process.terminate(force=True)
                except Exception:
                    pass

