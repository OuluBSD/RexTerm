import html
import re


def ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML for display in QTextEdit."""
    ansi_colors = {
        '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
        '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
        '90': 'darkgray', '91': 'lightred', '92': 'lightgreen', '93': 'lightyellow',
        '94': 'lightblue', '95': 'lightmagenta', '96': 'lightcyan', '97': 'lightgray',
        '40': 'black', '41': 'red', '42': 'green', '43': 'yellow',
        '44': 'blue', '45': 'magenta', '46': 'cyan', '47': 'white'
    }

    text = html.escape(text)
    pattern = r'(\x1b\[[\?]?[\d;]*[a-zA-Z])'
    parts = re.split(pattern, text)

    result = []
    current_fg = None
    current_bg = None
    is_bold = False

    for part in parts:
        if part.startswith('\x1b[') and part[-1].isalpha():
            sequence = part[2:-1]

            if part.endswith('m'):
                if sequence.startswith('?'):
                    continue

                codes = [c for c in sequence.split(';') if c]

                if not codes or '0' in codes:
                    current_fg = None
                    current_bg = None
                    is_bold = False
                    continue

                for code in codes:
                    if code == '1':
                        is_bold = True
                    elif code == '22':
                        is_bold = False
                    elif code == '39':
                        current_fg = None
                    elif code == '49':
                        current_bg = None
                    elif code.startswith('3') and (code.isdigit() or code in ['90', '91', '92', '93', '94', '95', '96', '97']):
                        if code in ansi_colors:
                            current_fg = ansi_colors[code]
                    elif code.startswith('4') and code.isdigit() and code in ['40', '41', '42', '43', '44', '45', '46', '47']:
                        if code in ansi_colors:
                            current_bg = ansi_colors[code]
            else:
                continue
        else:
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

