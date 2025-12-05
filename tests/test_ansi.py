#!/usr/bin/env python3
"""Test ANSI to HTML conversion functionality"""

import html
import re

def ansi_to_html(text):
    """
    Convert ANSI escape codes to HTML for display in QTextEdit
    """
    # Define ANSI color codes
    ansi_colors = {
        '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
        '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
        '90': 'darkgray', '91': 'lightred', '92': 'lightgreen', '93': 'lightyellow',
        '94': 'lightblue', '95': 'lightmagenta', '96': 'lightcyan', '97': 'lightgray',
        '40': 'black', '41': 'red', '42': 'green', '43': 'yellow',
        '44': 'blue', '45': 'magenta', '46': 'cyan', '47': 'white'
    }

    # Replace special characters to HTML entities first
    text = html.escape(text)

    # Handle multiple ANSI code sequences in the text
    # This pattern matches all ANSI escape sequences starting with ESC[
    pattern = r'(\x1b\[[\?]?[\d;]*[a-zA-Z])'
    parts = re.split(pattern, text)

    result = []
    current_fg = None
    current_bg = None
    is_bold = False

    for part in parts:
        if part.startswith('\x1b[') and part[-1].isalpha():
            # This is an ANSI escape sequence
            sequence = part[2:-1]  # Extract the code without \x1b[ and the final letter

            # Handle sequences that end with 'm' (color/formatting codes)
            if part.endswith('m'):
                # Handle special mode sequences that don't affect display
                if sequence.startswith('?'):
                    # These are mode setting sequences (like ?2004h), ignore them for display
                    continue

                # Split codes if there are multiple (e.g., \x1b[1;32m)
                codes = [c for c in sequence.split(';') if c]  # Remove empty strings

                if not codes or '0' in codes:
                    # Reset all formatting if no codes or '0' is present
                    current_fg = None
                    current_bg = None
                    is_bold = False
                    continue

                for code in codes:
                    if code == '1':
                        # Bold
                        is_bold = True
                    elif code == '22':
                        # Normal weight (not bold)
                        is_bold = False
                    elif code == '39':
                        # Default foreground color
                        current_fg = None
                    elif code == '49':
                        # Default background color
                        current_bg = None
                    elif code.startswith('3') and (code.isdigit() or code in ['90', '91', '92', '93', '94', '95', '96', '97']):
                        # Foreground color
                        if code in ansi_colors:
                            current_fg = ansi_colors[code]
                    elif code.startswith('4') and code.isdigit() and code in ['40', '41', '42', '43', '44', '45', '46', '47']:
                        # Background color
                        if code in ansi_colors:
                            current_bg = ansi_colors[code]
            else:
                # Other ANSI sequences (cursor movement, etc.) - ignore for display
                continue
        else:
            # Regular text content
            if current_fg or current_bg or is_bold:
                style = ""
                if current_fg:
                    style += f"color:{current_fg};"
                if current_bg:
                    style += f"background-color:{current_bg};"
                if is_bold:
                    style += "font-weight:bold;"

                result.append(f'<span style="{style}">{part}</span>')
            else:
                result.append(part)

    return ''.join(result)


def test_ansi_conversion():
    print("Testing ANSI to HTML conversion...")
    
    # Test common ANSI sequences
    test_cases = [
        "\x1b[32mGreen text\x1b[0m",
        "\x1b[35mPurple text\x1b[0m", 
        "\x1b[33mYellow text\x1b[0m",
        "\x1b[1;32mBold green text\x1b[0m",
        "\x1b[32msb\x1b[35mlo@Gen2-Win10\x1b[33mCLANG64\x1b[0m",
        "\x1b[?2004h",  # Should be handled properly
        "Regular text with \x1b[31mred\x1b[0m color"
    ]
    
    for i, test_str in enumerate(test_cases):
        print(f"Test {i+1}: {repr(test_str)}")
        result = ansi_to_html(test_str)
        print(f"  Converted: {repr(result)}")
        print()


if __name__ == "__main__":
    test_ansi_conversion()