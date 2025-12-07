#!/usr/bin/env python3

try:
    import keyboard
    print('keyboard: OK')
except ImportError as e:
    print(f'keyboard: {e}')

try:
    import pynput
    print('pynput: OK')
except ImportError as e:
    print(f'pynput: {e}')

print("Both libraries appear to be available!")