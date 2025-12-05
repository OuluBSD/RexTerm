import argparse
import logging
import queue
import sys
import time
import threading

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .app_settings import AppSettings
from .main_window import MainWindow
from .terminal_emulator import TerminalEmulator


def setup_debug_logging(debug_file):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(debug_file, mode='w'),
            logging.StreamHandler()
        ]
    )


def _run_eval_mode(args, colorterm):
    terminal = TerminalEmulator(
        cols=80,
        rows=24,
        shell_type=args.shell,
        history_lines=args.scrollback,
        term_override=args.term,
        colorterm_value=colorterm,
    )
    if not terminal.start():
        print("Could not start terminal emulator", file=sys.stderr)
        sys.exit(1)

    output_queue = queue.Queue()

    def read_terminal():
        start_time = time.time()
        while time.time() - start_time < args.timeout and terminal.running:
            try:
                output = terminal.read(1024)
                if output:
                    output_queue.put(output)
                time.sleep(0.01)
            except Exception:
                break

    reader_thread = threading.Thread(target=read_terminal, daemon=True)
    reader_thread.start()

    terminal.write(args.eval + '\n')

    reader_thread.join(timeout=args.timeout)
    terminal.close()

    all_output = []
    while not output_queue.empty():
        all_output.append(output_queue.get_nowait())

    final_output = ''.join(all_output)
    if args.dump:
        print(final_output)
    else:
        print(final_output.strip())

    sys.exit(0)


def _run_headless_eval(args, session_settings, app):
    window = MainWindow(
        shell_type=args.shell,
        scrollback_lines=args.scrollback,
        term_override=args.term,
        colorterm_value=session_settings.colorterm_value,
        settings=session_settings,
    )
    if not args.debug:
        window.show()

    shell_widget = window.current_shell_widget()

    if args.debug and shell_widget:
        shell_widget.debug_enabled = True
        shell_widget.debug_file = args.debug
        shell_widget.logger = logging.getLogger(__name__)

    def send_command():
        if args.headless_eval and shell_widget:
            shell_widget.terminal.write(args.headless_eval + '\n')

        def dump_and_exit():
            if args.dump:
                content = shell_widget.output_area.toPlainText()
                print(content)
            else:
                content = shell_widget.output_area.toPlainText()
                print(content.strip())
            app.quit()

        QTimer.singleShot(args.headless_timeout * 1000, dump_and_exit)

    QTimer.singleShot(500, send_command)
    sys.exit(app.exec())


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("OuluBSD")
    app.setApplicationName("GUI Shell")
    app.setApplicationVersion("1.0")

    settings = AppSettings.load()

    parser = argparse.ArgumentParser(description='GUI Shell with MSYS2 support')
    parser.add_argument('--shell', '-s', choices=['cmd', 'bash', 'auto'], default=settings.default_shell,
                        help='Shell type to use: cmd, bash, or auto (default: auto)')
    parser.add_argument('--eval', help='Command to evaluate in non-interactive mode')
    parser.add_argument('--dump', action='store_true', help='Dump screen content to stdout in non-interactive mode')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout in seconds for non-interactive mode (default: 10)')
    parser.add_argument('--headless-eval', help='Command to evaluate in headless GUI mode')
    parser.add_argument('--headless-timeout', type=int, default=10, help='Timeout for headless GUI mode (default: 10)')
    parser.add_argument('--debug', help='Enable debug logging to specified file')
    parser.add_argument('--scrollback', type=int, default=settings.scrollback_lines,
                        help='Number of scrollback lines to keep in the terminal buffer (default: 1000)')
    parser.add_argument('--term', default=settings.term_override, help='TERM value to export to the child shell (default: inherit TERM or use xterm-256color)')
    parser.add_argument('--colorterm', default=settings.colorterm_value,
                        help='COLORTERM value to export (use "none" to omit, default: truecolor)')

    args = parser.parse_args(sys.argv[1:])

    session_settings = settings.copy()
    session_settings.default_shell = args.shell
    session_settings.scrollback_lines = args.scrollback
    session_settings.term_override = args.term
    effective_colorterm = None if (args.colorterm and args.colorterm.lower() == "none") else args.colorterm
    session_settings.colorterm_value = effective_colorterm
    args.colorterm = effective_colorterm

    if args.debug:
        setup_debug_logging(args.debug)

    if args.eval:
        _run_eval_mode(args, effective_colorterm)
    elif args.headless_eval:
        _run_headless_eval(args, session_settings, app)
    else:
        window = MainWindow(
            shell_type=args.shell,
            scrollback_lines=args.scrollback,
            term_override=args.term,
            colorterm_value=effective_colorterm,
            settings=session_settings,
        )
        window.show()

        if args.debug:
            shell_widget = window.current_shell_widget()
            if shell_widget:
                shell_widget.debug_enabled = True
                shell_widget.debug_file = args.debug
                shell_widget.logger = logging.getLogger(__name__)

        sys.exit(app.exec())


if __name__ == '__main__':
    main()
