"""
Manual GUI regression test for the Enter key behaviour.

Set RUN_GUI_TESTS=1 to enable this integration test. It is skipped by
default because it requires a GUI environment.
"""
import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from gui_shell import MainWindow


RUN_GUI_TESTS = os.environ.get("RUN_GUI_TESTS") == "1"


@unittest.skipUnless(RUN_GUI_TESTS, "Set RUN_GUI_TESTS=1 to run GUI shell interaction tests.")
class TestEnterKeyIssue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a single QApplication instance for all tests
        if QApplication.instance() is None:
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Create a fresh MainWindow for each test
        self.window = MainWindow(shell_type='auto')
        self.window.show()

    def tearDown(self):
        # Close the window after each test
        self.window.close()

    def test_ls_command_execution(self):
        """
        Test that typing 'ls' and pressing Enter executes the command
        """
        shell_widget = self.window.shell_widget
        output_area = shell_widget.output_area
        
        QTest.qWait(1000)  # Wait 1 second for terminal to be ready

        # Get initial text content
        initial_text = output_area.toPlainText()
        print(f"Initial text: '{initial_text}'")
        
        # Calculate where user input should start
        shell_widget.input_start_position = len(initial_text)
        
        # Type 'ls' into the output area
        QTest.keyClicks(output_area, 'ls')
        
        QTest.qWait(500)

        # Verify text was entered
        current_text = output_area.toPlainText()
        print(f"Text after typing 'ls': '{current_text}'")
        self.assertTrue(current_text.endswith('ls'), f"Expected text to end with 'ls', got '{current_text}'")
        
        # Simulate pressing Enter to execute the command
        QTest.keyPress(output_area, Qt.Key.Key_Enter)
        QTest.keyRelease(output_area, Qt.Key.Key_Enter)
        
        QTest.qWait(2000)  # Wait 2 seconds for command to execute

        # Check if the command was executed by seeing if the text changed appropriately
        updated_text = output_area.toPlainText()
        print(f"Text after pressing Enter: '{updated_text}'")

        # The core issue was that pressing Enter would just add a newline instead of executing.
        # We expect the buffer to change beyond simply appending a newline to "ls".
        self.assertNotEqual(
            updated_text,
            initial_text + 'ls\n',
            "Enter key should execute the command instead of just inserting a newline",
        )


def run_tests():
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnterKeyIssue)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    # This test needs to be run in the Qt event loop context
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
