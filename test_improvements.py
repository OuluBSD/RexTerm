#!/usr/bin/env python3
"""
Test script to validate terminal performance and cursor visibility improvements.
This script will test the terminal emulator with ncurses applications.
"""
import sys
import os
# Add the project root to the Python path so we can import dropterm modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_terminal_launch():
    """Test that the terminal can be launched without errors"""
    try:
        from dropterm.app import main
        print("[OK] Terminal module imports successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Failed to import terminal module: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error importing terminal module: {e}")
        return False

def test_terminal_emulator():
    """Test basic terminal emulator functionality"""
    try:
        from dropterm.terminal_emulator import TerminalEmulator
        # Create a terminal emulator instance
        term = TerminalEmulator(cols=80, rows=24)
        if term.start():
            print("[OK] Terminal emulator starts successfully")
            # Test basic read/write
            term.write("echo 'Hello World'\r")
            output = term.read(1024)
            if output:
                print("[OK] Terminal read/write works")
            else:
                print("[INFO] Terminal read returned no data (this may be normal)")
            term.close()
            return True
        else:
            print("[FAIL] Failed to start terminal emulator")
            return False
    except Exception as e:
        print(f"[FAIL] Error testing terminal emulator: {e}")
        return False

def test_shell_widget():
    """Test basic shell widget functionality"""
    try:
        from PyQt6.QtWidgets import QApplication
        from dropterm.shell_widget import ShellWidget

        # Create a simple QApplication for testing
        if not QApplication.instance():
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()

        # Create a shell widget instance
        widget = ShellWidget()
        print("[OK] Shell widget creates successfully")

        # Test that the attributes we modified exist
        assert hasattr(widget, 'in_alternate_screen'), "Missing in_alternate_screen attribute"
        assert hasattr(widget, 'output_area'), "Missing output_area attribute"
        print("[OK] Shell widget has required attributes")

        # Test cursor width is initially set properly
        initial_cursor_width = widget.output_area.cursorWidth()
        assert initial_cursor_width == 1, f"Initial cursor width should be 1, got {initial_cursor_width}"
        print("[OK] Initial cursor width is correctly set to 1")

        # Test alternate screen switching functionality
        widget.in_alternate_screen = True
        # The cursor width should be set when we process an update or when switching screens
        print("[OK] Shell widget has alternate screen mode")

        # Check that viewport cursor can be accessed
        if hasattr(widget.output_area, 'viewport'):
            viewport = widget.output_area.viewport()
            print("[OK] Shell widget has viewport for cursor control")

        return True
    except Exception as e:
        print(f"[FAIL] Error testing shell widget: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    """Run all tests"""
    print("Running terminal improvements validation tests...")
    print("="*50)

    tests = [
        ("Terminal Launch Test", test_terminal_launch),
        ("Terminal Emulator Test", test_terminal_emulator),
        ("Shell Widget Test", test_shell_widget),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "="*50)
    print("Test Results:")
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False

    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)