#!/usr/bin/env python3
"""
Optional integration tests for the terminal backend.

Set RUN_TERMINAL_TESTS=1 to execute these tests. They are skipped by default
because they rely on an interactive shell environment.
"""

import os
import time
import unittest
from gui_shell import TerminalEmulator


RUN_TERMINAL_TESTS = os.environ.get("RUN_TERMINAL_TESTS") == "1"


@unittest.skipUnless(RUN_TERMINAL_TESTS, "Set RUN_TERMINAL_TESTS=1 to run terminal integration tests.")
class TerminalBackendIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.term = TerminalEmulator(cols=80, rows=24, shell_type="bash")

    def tearDown(self):
        try:
            self.term.close()
        except Exception:
            pass

    def test_can_start_and_close_terminal(self):
        self.assertTrue(self.term.start(), "Terminal failed to start in integration test")

    def test_echo_command(self):
        self.assertTrue(self.term.start(), "Terminal failed to start for echo command")

        # Give the shell a moment to initialize and clear any welcome text
        time.sleep(0.5)
        self.term.read(1024)

        self.term.write("echo test\r")
        time.sleep(1)
        output = self.term.read(2048)

        self.assertIsInstance(output, str)
        self.assertIn("test", output)


if __name__ == "__main__":
    unittest.main()
