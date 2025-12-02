#!/usr/bin/env python3
"""Test script to analyze terminal output patterns"""

def analyze_output(output_str):
    print("Analyzing terminal output:")
    print(f"Raw: {repr(output_str)}")
    print(f"Length: {len(output_str)}")
    
    print("\nCharacter-by-character analysis:")
    for i, char in enumerate(output_str):
        if char == '\n':
            print(f"  [{i:3d}] \\n (newline)")
        elif char == '\r':
            print(f"  [{i:3d}] \\r (carriage return)")
        elif char == '\x1b':
            # Check if this is the start of an escape sequence
            remaining = output_str[i:i+10]  # Look at next 10 chars
            print(f"  [{i:3d}] \\x1b... (ESC sequence: {repr(remaining)})")
        else:
            print(f"  [{i:3d}] '{char}'")
    
    print(f"\nSplit by newlines: {output_str.split(chr(10))}")
    print(f"Split by carriage returns: {output_str.split(chr(13))}")

# Example based on the issue you described
example = "$ ls\nsblo@Gen2-Win10CLANG64/e/active/sblo/Dev/dropterm $0;/e/active/sblo/Dev/droptermls QWEN.md __pycache__ test_ansi.py test_bash_support.py README.md gui_shell.py test_auto_shell.py test_winpty.py sblo@Gen2-Win10 CLANG64 /e/active/sblo/Dev/dropterm $ sblo@Gen2-Win10 CLANG64 /e/active/sblo/Dev/dropterm $"

if __name__ == "__main__":
    analyze_output(example)