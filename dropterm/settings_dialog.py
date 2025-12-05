from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QFontComboBox,
    QKeySequenceEdit,
)

from .app_settings import AppSettings


class SettingsDialog(QDialog):
    """Settings dialog with basic terminal options grouped by category."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("Settings")
        self.resize(640, 520)

        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_fonts_tab(), "Fonts")
        self.tabs.addTab(self._build_appearance_tab(), "Appearance")
        self.tabs.addTab(self._build_quake_tab(), "Quake Mode")
        self.tabs.addTab(self._build_shortcuts_tab(), "Shortcuts")
        self.tabs.addTab(self._build_colors_tab(), "Color Theme")
        self.tabs.addTab(self._build_terminal_tab(), "Terminal")

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _build_fonts_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        self.font_picker = QFontComboBox()
        self.font_picker.setCurrentFont(QFont(self.settings.font_family))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 48)
        self.size_spin.setValue(self.settings.font_size)
        form.addRow("Font family", self.font_picker)
        form.addRow("Size", self.size_spin)
        return widget

    def _build_appearance_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100)
        self.transparency_slider.setValue(self.settings.window_transparency)
        self.transparency_label = QLabel(f"{self.settings.window_transparency}%")

        def update_label(value):
            self.transparency_label.setText(f"{value}%")

        self.transparency_slider.valueChanged.connect(update_label)

        row = QHBoxLayout()
        row.addWidget(self.transparency_slider)
        row.addWidget(self.transparency_label)
        form.addRow("Window transparency", row)

        self.always_on_top = QCheckBox("Always on top")
        self.always_on_top.setChecked(self.settings.always_on_top)
        form.addRow(self.always_on_top)

        return widget

    def _build_quake_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.enable_quake = QCheckBox("Enable Quake-style drop-down")
        self.enable_quake.setChecked(self.settings.quake_enabled)
        form.addRow(self.enable_quake)

        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setKeySequence(QKeySequence(self.settings.quake_hotkey))
        form.addRow("Global hotkey", self.hotkey_edit)

        self.slide_checkbox = QCheckBox("Slide down animation")
        self.slide_checkbox.setChecked(self.settings.quake_slide)
        form.addRow(self.slide_checkbox)

        self.quake_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.quake_height_slider.setRange(10, 100)
        self.quake_height_slider.setValue(self.settings.quake_height_percent)
        self.quake_height_value = QLabel(f"{self.settings.quake_height_percent}%")

        def sync_height(value):
            self.quake_height_value.setText(f"{value}%")

        self.quake_height_slider.valueChanged.connect(sync_height)

        row = QHBoxLayout()
        row.addWidget(self.quake_height_slider)
        row.addWidget(self.quake_height_value)
        form.addRow("Quake height", row)

        return widget

    def _build_shortcuts_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.copy_seq = QKeySequenceEdit()
        self.copy_seq.setKeySequence(QKeySequence(self.settings.copy_shortcut))
        form.addRow("Copy", self.copy_seq)

        self.paste_seq = QKeySequenceEdit()
        self.paste_seq.setKeySequence(QKeySequence(self.settings.paste_shortcut))
        form.addRow("Paste", self.paste_seq)

        self.new_window_seq = QKeySequenceEdit()
        self.new_window_seq.setKeySequence(QKeySequence(self.settings.new_window_shortcut))
        form.addRow("New window", self.new_window_seq)

        self.quake_taller_seq = QKeySequenceEdit()
        self.quake_taller_seq.setKeySequence(QKeySequence(self.settings.quake_resize_up_shortcut))
        form.addRow("Quake height +", self.quake_taller_seq)

        self.quake_shorter_seq = QKeySequenceEdit()
        self.quake_shorter_seq.setKeySequence(QKeySequence(self.settings.quake_resize_down_shortcut))
        form.addRow("Quake height -", self.quake_shorter_seq)

        return widget

    def _build_colors_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Solarized Dark", "Solarized Light", "Dracula"])
        index = self.theme_combo.findText(self.settings.color_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        form.addRow("Theme", self.theme_combo)

        self.cursor_blink_cb = QCheckBox("Blinking block cursor")
        self.cursor_blink_cb.setChecked(self.settings.cursor_blink)
        form.addRow(self.cursor_blink_cb)

        return widget

    def _build_terminal_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.default_shell = QComboBox()
        self.default_shell.addItems(["auto", "bash", "cmd"])
        shell_index = self.default_shell.findText(self.settings.default_shell)
        if shell_index >= 0:
            self.default_shell.setCurrentIndex(shell_index)
        form.addRow("Default shell", self.default_shell)

        self.scrollback_spin = QSpinBox()
        self.scrollback_spin.setRange(100, 100000)
        self.scrollback_spin.setValue(self.settings.scrollback_lines)
        form.addRow("Scrollback lines", self.scrollback_spin)

        self.mouse_reporting = QCheckBox("Enable mouse reporting")
        self.mouse_reporting.setChecked(self.settings.mouse_reporting)
        form.addRow(self.mouse_reporting)

        return widget

    def build_settings(self) -> AppSettings:
        updated = self.settings.copy()
        updated.font_family = self.font_picker.currentFont().family()
        updated.font_size = self.size_spin.value()
        updated.window_transparency = self.transparency_slider.value()
        updated.always_on_top = self.always_on_top.isChecked()
        updated.quake_enabled = self.enable_quake.isChecked()
        updated.quake_hotkey = self.hotkey_edit.keySequence().toString()
        updated.quake_slide = self.slide_checkbox.isChecked()
        updated.quake_height_percent = self.quake_height_slider.value()
        updated.copy_shortcut = self.copy_seq.keySequence().toString()
        updated.paste_shortcut = self.paste_seq.keySequence().toString()
        updated.new_window_shortcut = self.new_window_seq.keySequence().toString()
        updated.quake_resize_up_shortcut = self.quake_taller_seq.keySequence().toString()
        updated.quake_resize_down_shortcut = self.quake_shorter_seq.keySequence().toString()
        updated.color_theme = self.theme_combo.currentText()
        updated.cursor_blink = self.cursor_blink_cb.isChecked()
        updated.default_shell = self.default_shell.currentText()
        updated.scrollback_lines = self.scrollback_spin.value()
        updated.mouse_reporting = self.mouse_reporting.isChecked()
        return updated

