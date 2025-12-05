from dataclasses import dataclass, asdict

from PyQt6.QtCore import QSettings

# Basic color themes for the terminal chrome (background/foreground)
THEME_PRESETS = {
    "Dark": {"background": "#000000", "foreground": "#cccccc"},
    "Light": {"background": "#ffffff", "foreground": "#111111"},
    "Solarized Dark": {"background": "#002b36", "foreground": "#93a1a1"},
    "Solarized Light": {"background": "#fdf6e3", "foreground": "#657b83"},
    "Dracula": {"background": "#282a36", "foreground": "#f8f8f2"},
}


@dataclass
class AppSettings:
    """Persisted user settings for the terminal application."""

    font_family: str = "Courier New"
    font_size: int = 10
    window_transparency: int = 0  # 0-100%
    always_on_top: bool = False
    color_theme: str = "Dark"
    cursor_blink: bool = True
    default_shell: str = "auto"
    scrollback_lines: int = 1000
    quake_enabled: bool = False
    quake_hotkey: str = "Ctrl+`"
    quake_slide: bool = False
    quake_height_percent: int = 40
    quake_resize_up_shortcut: str = "Ctrl+Up"
    quake_resize_down_shortcut: str = "Ctrl+Down"
    copy_shortcut: str = "Ctrl+Shift+C"
    paste_shortcut: str = "Ctrl+Shift+V"
    new_window_shortcut: str = "Ctrl+Shift+N"
    new_tab_shortcut: str = "Ctrl+T"
    split_horizontal_shortcut: str = "Ctrl+-"
    split_vertical_shortcut: str = "Ctrl+Shift+-"
    mouse_reporting: bool = True
    term_override: str | None = None
    colorterm_value: str | None = "truecolor"

    @classmethod
    def load(cls) -> "AppSettings":
        settings = QSettings("OuluBSD", "RexTerm")
        return cls(
            font_family=settings.value("font_family", cls.font_family),
            font_size=int(settings.value("font_size", cls.font_size)),
            window_transparency=int(settings.value("window_transparency", cls.window_transparency)),
            always_on_top=settings.value("always_on_top", cls.always_on_top, type=bool),
            color_theme=settings.value("color_theme", cls.color_theme),
            cursor_blink=settings.value("cursor_blink", cls.cursor_blink, type=bool),
            default_shell=settings.value("default_shell", cls.default_shell),
            scrollback_lines=int(settings.value("scrollback_lines", cls.scrollback_lines)),
            quake_enabled=settings.value("quake_enabled", cls.quake_enabled, type=bool),
            quake_hotkey=settings.value("quake_hotkey", cls.quake_hotkey),
            quake_slide=settings.value("quake_slide", cls.quake_slide, type=bool),
            quake_height_percent=int(settings.value("quake_height_percent", cls.quake_height_percent)),
            quake_resize_up_shortcut=settings.value("quake_resize_up_shortcut", cls.quake_resize_up_shortcut),
            quake_resize_down_shortcut=settings.value("quake_resize_down_shortcut", cls.quake_resize_down_shortcut),
            copy_shortcut=settings.value("copy_shortcut", cls.copy_shortcut),
            paste_shortcut=settings.value("paste_shortcut", cls.paste_shortcut),
            new_window_shortcut=settings.value("new_window_shortcut", cls.new_window_shortcut),
            new_tab_shortcut=settings.value("new_tab_shortcut", cls.new_tab_shortcut),
            split_horizontal_shortcut=settings.value("split_horizontal_shortcut", cls.split_horizontal_shortcut),
            split_vertical_shortcut=settings.value("split_vertical_shortcut", cls.split_vertical_shortcut),
            mouse_reporting=settings.value("mouse_reporting", cls.mouse_reporting, type=bool),
            term_override=settings.value("term_override", cls.term_override),
            colorterm_value=settings.value("colorterm_value", cls.colorterm_value),
        )

    def save(self):
        settings = QSettings("OuluBSD", "RexTerm")
        settings.setValue("font_family", self.font_family)
        settings.setValue("font_size", self.font_size)
        settings.setValue("window_transparency", self.window_transparency)
        settings.setValue("always_on_top", self.always_on_top)
        settings.setValue("color_theme", self.color_theme)
        settings.setValue("cursor_blink", self.cursor_blink)
        settings.setValue("default_shell", self.default_shell)
        settings.setValue("scrollback_lines", self.scrollback_lines)
        settings.setValue("quake_enabled", self.quake_enabled)
        settings.setValue("quake_hotkey", self.quake_hotkey)
        settings.setValue("quake_slide", self.quake_slide)
        settings.setValue("quake_height_percent", self.quake_height_percent)
        settings.setValue("quake_resize_up_shortcut", self.quake_resize_up_shortcut)
        settings.setValue("quake_resize_down_shortcut", self.quake_resize_down_shortcut)
        settings.setValue("copy_shortcut", self.copy_shortcut)
        settings.setValue("paste_shortcut", self.paste_shortcut)
        settings.setValue("new_window_shortcut", self.new_window_shortcut)
        settings.setValue("new_tab_shortcut", self.new_tab_shortcut)
        settings.setValue("split_horizontal_shortcut", self.split_horizontal_shortcut)
        settings.setValue("split_vertical_shortcut", self.split_vertical_shortcut)
        settings.setValue("mouse_reporting", self.mouse_reporting)
        settings.setValue("term_override", self.term_override)
        settings.setValue("colorterm_value", self.colorterm_value)

    def copy(self) -> "AppSettings":
        return AppSettings(**asdict(self))

    def palette(self):
        return THEME_PRESETS.get(self.color_theme, THEME_PRESETS["Dark"])

