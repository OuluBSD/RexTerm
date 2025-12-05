import os
import queue
import time
import winreg

import pyte
from pyte import screens
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


class TerminalEmulator:
    """Wrapper for winpty with pyte terminal emulation."""

    def __init__(self, cols=80, rows=24, shell_type='cmd', history_lines=1000, term_override=None, colorterm_value="truecolor"):
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

        self.screen = screens.HistoryScreen(cols, rows, history=history_lines)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

    def start(self):
        try:
            env_vars = os.environ.copy()
            term_value = self.term_override or "xterm-256color"
            env_vars["TERM"] = term_value
            if self.colorterm_value and self.colorterm_value.lower() != "none":
                env_vars["COLORTERM"] = self.colorterm_value
            env_vars.setdefault("TERM_PROGRAM", "dropterm")
            env_vars.setdefault("TERM_PROGRAM_VERSION", "0.1")

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
        if not self.running or not self.pty_process.isalive():
            return ''
        try:
            raw_data = self.pty_process.read(size)
            if raw_data:
                self.stream.feed(raw_data)
            return raw_data
        except Exception as e:
            print(f"Read error: {e}")
            if not self.pty_process.isalive():
                self.running = False
            return ''

    def write(self, data):
        if not self.running or not self.pty_process.isalive():
            return
        try:
            self.pty_process.write(data)
        except Exception as e:
            print(f"Write error: {e}")
            if not self.pty_process.isalive():
                self.running = False

    def resize(self, cols, rows):
        self.cols = cols
        self.rows = rows

        if self.pty_process:
            try:
                self.pty_process.setwinsize(rows, cols)
            except Exception as e:
                print(f"Resize error: {e}")

        try:
            self.screen.resize(rows, cols)
        except Exception as e:
            print(f"pyte resize error: {e}")

    def close(self):
        self.running = False
        if self.pty_process and self.pty_process.isalive():
            try:
                self.pty_process.write('exit\r\n')
                time.sleep(0.1)
                if self.pty_process.isalive():
                    self.pty_process.terminate(force=True)
            except Exception:
                pass

