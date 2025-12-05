from PyQt6.QtWidgets import QSplitter, QWidget
from PyQt6.QtCore import Qt
from .shell_widget import ShellWidget


class SplitTerminalWidget(QWidget):
    """Widget that handles terminal splits with horizontal and vertical splitting."""

    def __init__(self, shell_widget: ShellWidget, settings=None):
        super().__init__()
        self.settings = settings
        self.shell_widget = shell_widget

        # Create the main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Add the initial shell widget to the splitter
        self.splitter.addWidget(self.shell_widget)

        # Set the layout
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

        # Track all shell widgets for management
        self.shell_widgets = [self.shell_widget]

    def split_horizontal(self):
        """Split the current view horizontally (side by side)."""
        current_widget = self._get_focused_widget()
        if current_widget:
            self._create_split(current_widget, Qt.Orientation.Horizontal)

    def split_vertical(self):
        """Split the current view vertically (top/bottom)."""
        current_widget = self._get_focused_widget()
        if current_widget:
            self._create_split(current_widget, Qt.Orientation.Vertical)

    def _get_focused_widget(self):
        """Get the currently focused shell widget."""
        for widget in self.shell_widgets:
            if widget.hasFocus() or widget.output_area.hasFocus():
                return widget
        # If none are focused, use the first one
        return self.shell_widgets[0] if self.shell_widgets else None

    def _create_split(self, source_widget, orientation):
        """Create a new split from the source widget."""
        # Create a new shell widget with same settings
        new_shell = ShellWidget(
            shell_type=source_widget.terminal.shell_type,
            scrollback_lines=source_widget.terminal.history_lines,
            term_override=source_widget.settings.term_override,
            colorterm_value=source_widget.settings.colorterm_value,
            settings=source_widget.settings
        )

        # Add to our tracking list
        self.shell_widgets.append(new_shell)

        # Find the parent splitter of the source widget
        parent_splitter = self._find_parent_splitter(source_widget)

        if parent_splitter:
            # Insert the new widget into the parent splitter with the correct orientation
            index = parent_splitter.indexOf(source_widget)

            # If the orientation doesn't match, we need to create a new nested splitter
            if parent_splitter.orientation() != orientation:
                new_splitter = QSplitter(orientation)
                parent_splitter.insertWidget(index, new_splitter)
                new_splitter.addWidget(source_widget)
                new_splitter.addWidget(new_shell)
            else:
                # Same orientation, just add to the existing splitter
                parent_splitter.insertWidget(index + 1, new_shell)
        else:
            # No parent splitter, set the orientation of the main splitter
            self.splitter.setOrientation(orientation)
            self.splitter.addWidget(new_shell)

    def _find_parent_splitter(self, widget):
        """Find the parent splitter of a widget."""
        parent = widget.parent()
        while parent:
            if isinstance(parent, QSplitter):
                return parent
            parent = parent.parent()
        return self.splitter  # Return main splitter if no parent splitter found

    def hasFocus(self):
        """Check if any of the contained widgets have focus."""
        for widget in self.shell_widgets:
            if widget.hasFocus() or widget.output_area.hasFocus():
                return True
        return False