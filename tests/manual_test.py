import sys
from PyQt6.QtWidgets import QApplication
from gui_shell import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow(shell_type='auto')
    window.show()
    print("GUI Shell is now running. Try typing 'ls' and pressing Enter.")
    print("Check the console for any debug output.")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()