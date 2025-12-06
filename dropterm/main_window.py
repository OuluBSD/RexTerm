import sys
import ctypes
import logging

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QDialog,
)

from .app_settings import AppSettings
from .hotkeys import GLOBAL_HOTKEY_ID, HotkeyEventFilter, parse_hotkey_to_win
from .settings_dialog import SettingsDialog
from .shell_widget import ShellWidget
from .split_widget import SplitTerminalWidget


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, shell_type='auto', scrollback_lines=1000, term_override=None, colorterm_value="truecolor", settings: AppSettings | None = None):
        super().__init__()
        self.settings = settings or AppSettings()
        self.setWindowTitle("GUI Shell")
        self.setGeometry(100, 100, 800, 600)

        # Set the window icon
        import os
        from PyQt6.QtGui import QIcon
        # Try the ICO file first, then fallback to PNG
        # Calculate the project root directory (where gui_shell.py is located)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(project_root, 'icon.ico')
        if not os.path.exists(icon_path):
            icon_path = os.path.join(project_root, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.hotkey_filter = HotkeyEventFilter(self._handle_hotkey)
        self.hotkey_registered = False
        self._native_filter_installed = False
        self.tray_icon: QSystemTrayIcon | None = None
        self.session_shell_type = shell_type
        self.session_scrollback = scrollback_lines
        self.session_term_override = term_override
        self.session_colorterm = colorterm_value
        self._child_windows: list[MainWindow] = []

        self._setup_central_ui()
        self.create_menu()

        self.add_terminal_tab(shell_type=shell_type, scrollback_lines=scrollback_lines)
        self.setup_shortcuts()
        self.apply_window_settings()

    def _setup_central_ui(self):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._tab_changed)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self._tab_context_menu)

        self.menu_button = QToolButton(self)
        self.menu_button.setText("Menu")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_button.hide()

        layout.addWidget(self.tab_widget)
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Initialize split_widget to None - it will be set when we create the first tab
        self.split_widget = None

    def create_menu(self):
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu('File')

        self.new_tab_action = QAction('New Tab', self)
        self.new_tab_action.setShortcut(QKeySequence(self.settings.new_tab_shortcut))
        self.new_tab_action.triggered.connect(self.add_terminal_tab)
        self.file_menu.addAction(self.new_tab_action)

        self.new_window_action = QAction('New Window', self)
        self.new_window_action.setShortcut(QKeySequence(self.settings.new_window_shortcut))
        self.new_window_action.triggered.connect(self.open_new_window)
        self.file_menu.addAction(self.new_window_action)

        settings_action = QAction('Settings...', self)
        settings_action.triggered.connect(self.open_settings)
        self.file_menu.addAction(settings_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.terminal_menu = menubar.addMenu('Terminal')

        self.close_tab_action = QAction(f'Close Tab [{self.settings.close_tab_shortcut}]', self)
        self.close_tab_action.triggered.connect(lambda: self._close_tab(self.tab_widget.currentIndex()))
        self.terminal_menu.addAction(self.close_tab_action)

        clear_action = QAction('Clear Screen', self)
        clear_action.triggered.connect(self.clear_screen)
        self.terminal_menu.addAction(clear_action)

        # Add split actions
        self.split_horizontal_action_menu = QAction(f'Split Horizontal (|) [{self.settings.split_horizontal_shortcut}]', self)
        self.split_horizontal_action_menu.triggered.connect(self.split_horizontal)
        self.terminal_menu.addAction(self.split_horizontal_action_menu)

        self.split_vertical_action_menu = QAction(f'Split Vertical (-) [{self.settings.split_vertical_shortcut}]', self)
        self.split_vertical_action_menu.triggered.connect(self.split_vertical)
        self.terminal_menu.addAction(self.split_vertical_action_menu)

        self.help_menu = menubar.addMenu('Help')

        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        self.help_menu.addAction(about_action)

        self.menu_popup = QMenu(self)
        for menu in (self.file_menu, self.terminal_menu, self.help_menu):
            self.menu_popup.addMenu(menu)
        self.menu_button.setMenu(self.menu_popup)

    def setup_shortcuts(self):
        # Set up keyboard shortcuts for splitting
        self.split_horizontal_action = QAction("Split Horizontal", self)
        self.split_horizontal_action.setShortcut(QKeySequence(self.settings.split_horizontal_shortcut))
        self.split_horizontal_action.triggered.connect(self.split_horizontal)
        self.addAction(self.split_horizontal_action)

        self.split_vertical_action = QAction("Split Vertical", self)
        self.split_vertical_action.setShortcut(QKeySequence(self.settings.split_vertical_shortcut))
        self.split_vertical_action.triggered.connect(self.split_vertical)
        self.addAction(self.split_vertical_action)

        # Set up keyboard shortcuts for tab switching
        self.next_tab_action = QAction("Next Tab", self)
        self.next_tab_action.setShortcut(QKeySequence(self.settings.next_tab_shortcut))
        self.next_tab_action.triggered.connect(self.next_tab)
        self.addAction(self.next_tab_action)

        self.previous_tab_action = QAction("Previous Tab", self)
        self.previous_tab_action.setShortcut(QKeySequence(self.settings.previous_tab_shortcut))
        self.previous_tab_action.triggered.connect(self.previous_tab)
        self.addAction(self.previous_tab_action)

        # Set up keyboard shortcut for closing tab
        self.close_tab_action = QAction("Close Tab", self)
        self.close_tab_action.setShortcut(QKeySequence(self.settings.close_tab_shortcut))
        self.close_tab_action.triggered.connect(lambda: self._close_tab(self.tab_widget.currentIndex()))
        self.addAction(self.close_tab_action)

        # The Ctrl+Tab shortcut is handled directly in the ShellWidget to enable switching
        # between split terminals on the current tab. There is no need to add it as an action
        # because ShellWidget handles the key event directly.

    def split_horizontal(self):
        """Split the current terminal horizontally."""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'split_horizontal'):
            current_widget.split_horizontal()

    def split_vertical(self):
        """Split the current terminal vertically."""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'split_vertical'):
            current_widget.split_vertical()

    def next_tab(self):
        """Switch to the next tab."""
        current_index = self.tab_widget.currentIndex()
        next_index = (current_index + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)

    def previous_tab(self):
        """Switch to the previous tab."""
        current_index = self.tab_widget.currentIndex()
        prev_index = (current_index - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)

    def add_terminal_tab(self, shell_type=None, scrollback_lines=None, use_split_widget=False):
        shell_type = shell_type or self.session_shell_type or self.settings.default_shell
        scrollback_lines = self.settings.scrollback_lines if scrollback_lines is None else scrollback_lines
        shell = ShellWidget(
            shell_type=shell_type,
            scrollback_lines=scrollback_lines,
            term_override=self.session_term_override,
            colorterm_value=self.session_colorterm,
            settings=self.settings,
        )

        # If this is the first tab, initialize the split widget with it
        if not use_split_widget or self.tab_widget.count() == 0:
            # Initialize the split widget with the first shell
            self.split_widget = SplitTerminalWidget(shell, settings=self.settings)
            index = self.tab_widget.addTab(self.split_widget, f"Tab {self.tab_widget.count() + 1}")
            self.tab_widget.setCurrentIndex(index)
        else:
            # Add a new tab with a new split widget
            split_widget = SplitTerminalWidget(shell, settings=self.settings)
            index = self.tab_widget.addTab(split_widget, f"Tab {self.tab_widget.count() + 1}")
            self.tab_widget.setCurrentIndex(index)

        shell.apply_settings(self.settings)
        shell.output_area.setFocus()
        self._renumber_tabs()
        return shell

    def open_new_window(self):
        new_settings = self.settings.copy()
        win = MainWindow(
            shell_type=self.session_shell_type,
            scrollback_lines=self.session_scrollback,
            term_override=self.session_term_override,
            colorterm_value=self.session_colorterm,
            settings=new_settings,
        )
        self._child_windows.append(win)

        def _cleanup(_obj=None, win_ref=win):
            if win_ref in self._child_windows:
                self._child_windows.remove(win_ref)

        win.destroyed.connect(_cleanup)
        win.show()
        return win

    def _renumber_tabs(self):
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabText(i, f"Tab {i + 1}")

    def _close_tab(self, index):
        if index < 0:
            return
        widget = self.tab_widget.widget(index)
        if widget:
            widget.close()
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.close()
            return
        self._renumber_tabs()
        self._tab_changed(self.tab_widget.currentIndex())

    def _iter_shell_widgets(self):
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, ShellWidget):
                yield widget

    def current_shell_widget(self):
        widget = self.tab_widget.currentWidget()
        return widget if isinstance(widget, ShellWidget) else None

    def _tab_context_menu(self, position):
        tab_index = self.tab_widget.tabBar().tabAt(position)
        if tab_index != -1:
            menu = QMenu(self)
            close_action = menu.addAction("Close Tab")
            close_action.triggered.connect(lambda: self._close_tab(tab_index))
            menu.exec(self.tab_widget.mapToGlobal(position))

    def _tab_changed(self, index):
        widget = self.tab_widget.widget(index)
        if isinstance(widget, ShellWidget):
            widget.output_area.setFocus()

    def apply_window_settings(self):
        for widget in self._iter_shell_widgets():
            widget.apply_settings(self.settings)

        # Update the shortcuts based on new settings
        self.new_tab_action.setShortcut(QKeySequence(self.settings.new_tab_shortcut))
        self.new_window_action.setShortcut(QKeySequence(self.settings.new_window_shortcut))
        self.split_horizontal_action.setShortcut(QKeySequence(self.settings.split_horizontal_shortcut))
        self.split_vertical_action.setShortcut(QKeySequence(self.settings.split_vertical_shortcut))
        self.next_tab_action.setShortcut(QKeySequence(self.settings.next_tab_shortcut))
        self.previous_tab_action.setShortcut(QKeySequence(self.settings.previous_tab_shortcut))
        self.close_tab_action.setShortcut(QKeySequence(self.settings.close_tab_shortcut))
        self.close_tab_action.setText(f'Close Tab [{self.settings.close_tab_shortcut}]')

        opacity = max(0.05, 1 - (self.settings.window_transparency / 100))
        self.setWindowOpacity(opacity)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.settings.always_on_top)
        self._apply_quake_chrome()

        # If not in quake mode, ensure the window is visible and not hidden
        if not self.settings.quake_enabled:
            self.showNormal()

            # Ensure the window is visible if it was previously hidden
            if not self.isVisible():
                self.show()
        else:
            # When in quake mode, ensure the window is shown if it was hidden
            if not self.isVisible():
                self.show()

        if self.isVisible():
            self.show()
        self._ensure_tray_icon()
        self._register_global_hotkey()
        self._update_tray_visibility()

    def _apply_quake_chrome(self):
        is_quake = self.settings.quake_enabled

        self.tab_widget.setTabPosition(
            QTabWidget.TabPosition.South if is_quake else QTabWidget.TabPosition.North
        )

        if is_quake:
            corner = Qt.Corner.BottomRightCorner
            self.tab_widget.setCornerWidget(self.menu_button, corner)
            self.menu_button.show()
        else:
            self.tab_widget.setCornerWidget(None, Qt.Corner.TopRightCorner)
            self.tab_widget.setCornerWidget(None, Qt.Corner.BottomRightCorner)
            self.menu_button.hide()

        self.menuBar().setVisible(not is_quake)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, is_quake)
        if is_quake:
            self._apply_quake_height()
        else:
            # Restore normal window properties when not in quake mode
            self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)

    def _ensure_tray_icon(self):
        if self.tray_icon is None:
            icon = self.windowIcon()
            if icon.isNull():
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            self.tray_icon = QSystemTrayIcon(icon, self)
            menu = QMenu(self)
            toggle_action = menu.addAction("Show/Hide")
            toggle_action.triggered.connect(self._toggle_visibility)
            quit_action = menu.addAction("Quit")
            quit_action.triggered.connect(self._exit_from_tray)
            self.tray_icon.setContextMenu(menu)
            self.tray_icon.activated.connect(self._tray_activated)

        self._update_tray_visibility()

    def showEvent(self, event):
        """Override to ensure window is shown properly when not in quake mode"""
        super().showEvent(event)
        if not self.settings.quake_enabled:
            self.showNormal()

    def _update_tray_visibility(self):
        if not self.tray_icon:
            return
        if self.settings.quake_enabled:
            if not self.tray_icon.isVisible():
                self.tray_icon.show()
        else:
            # Only hide tray icon if explicitly disabled in settings or not needed
            # Most users prefer having the tray icon available to access the app
            if not self.tray_icon.isVisible():
                self.tray_icon.show()

    def _apply_quake_height(self):
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        percent = max(10, min(100, self.settings.quake_height_percent))
        target_height = max(100, int(avail.height() * (percent / 100.0)))
        self.setGeometry(avail.left(), avail.top(), avail.width(), target_height)

    def adjust_quake_height(self, delta_percent: int):
        if not self.settings.quake_enabled:
            return
        new_percent = max(10, min(100, self.settings.quake_height_percent + delta_percent))
        if new_percent != self.settings.quake_height_percent:
            self.settings.quake_height_percent = new_percent
            self.settings.save()
            self._apply_quake_height()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _exit_from_tray(self):
        if self.tray_icon:
            self.tray_icon.hide()
        self.close()

    def _toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            if self.settings.quake_enabled:
                self._apply_quake_height()
                # In quake mode, ensure the window is shown after applying height
                self.show()
            else:
                # When not in quake mode, ensure proper window visibility
                self.showNormal()
            self.raise_()
            self.activateWindow()

    def _handle_hotkey(self, hotkey_id):
        if hotkey_id == GLOBAL_HOTKEY_ID and self.settings.quake_enabled:
            self._toggle_visibility()

    def _register_global_hotkey(self):
        self._unregister_global_hotkey()
        if not self.settings.quake_enabled:
            return

        # Only register global hotkey on Windows
        if sys.platform == 'win32':
            parsed = parse_hotkey_to_win(self.settings.quake_hotkey)
            if not parsed:
                logging.warning("No hotkey set for quake mode; skipping registration.")
                return

            mods, vk = parsed

            hwnd = int(self.winId())
            if ctypes.windll.user32.RegisterHotKey(hwnd, GLOBAL_HOTKEY_ID, mods, vk):
                if not self._native_filter_installed:
                    QCoreApplication.instance().installNativeEventFilter(self.hotkey_filter)
                    self._native_filter_installed = True
                self.hotkey_registered = True
            else:
                logging.warning("Failed to register global hotkey '%s'", self.settings.quake_hotkey)
        else:
            # On non-Windows systems, we use Qt's standard hotkey functionality or skip
            logging.info("Global hotkey is Windows only. Using application hotkey instead.")
            # TODO: Consider implementing cross-platform hotkey solution for non-Windows systems

    def _unregister_global_hotkey(self):
        if sys.platform == 'win32' and self.hotkey_registered:
            ctypes.windll.user32.UnregisterHotKey(int(self.winId()), GLOBAL_HOTKEY_ID)
            self.hotkey_registered = False

        if self._native_filter_installed and not self.hotkey_registered:
            QCoreApplication.instance().removeNativeEventFilter(self.hotkey_filter)
            self._native_filter_installed = False

    def clear_screen(self):
        shell = self.current_shell_widget()
        if shell:
            shell.clear_screen()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings = dialog.build_settings()
            self.settings.save()
            self.apply_window_settings()

    def show_about(self):
        QMessageBox.about(self, "About GUI Shell",
                         "GUI Shell - A terminal emulator built with Python, PyQt6, and pywinpty")

    def closeEvent(self, event):
        self._unregister_global_hotkey()
        if self.tray_icon:
            self.tray_icon.hide()
        for widget in self._iter_shell_widgets():
            widget.close()
        for win in list(self._child_windows):
            try:
                win.close()
            except Exception:
                pass
        super().closeEvent(event)
