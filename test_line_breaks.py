#!/usr/bin/env python3
"""Test script to verify line break handling"""

def test_line_processing():
    # Example of what terminal output might look like
    raw_output = "$ ls\ntest_file1.txt\ntest_file2.txt\n$ "
    
    print("Raw output:")
    print(repr(raw_output))
    
    # Process like our function does
    text = raw_output.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    
    print(f"\nSplit into {len(lines)} lines:")
    for i, line in enumerate(lines):
        print(f"  Line {i}: {repr(line)}")
    
    # Simulate processing
    result = []
    for i, line in enumerate(lines):
        result.append(line)
        if i < len(lines) - 1:
            result.append('\\n')  # Showing explicit newlines
    
    print(f"\nProcessed output: {''.join(result)}")

if __name__ == "__main__":
    test_line_processing()