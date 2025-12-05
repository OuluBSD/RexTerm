#!/usr/bin/env python3
"""Pyte display expectations that underpin our terminal renderer."""

import pyte


def make_screen(cols=80, rows=24):
    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream()
    stream.attach(screen)
    return screen, stream


def test_prompt_trailing_space_is_visible():
    screen, stream = make_screen(cols=10, rows=2)
    stream.feed("$ ")

    line = screen.display[0]
    assert line.startswith("$ ")
    # pyte pads the rest of the line with spaces, so rstrip collapses to the raw prompt
    assert line.rstrip() == "$"
    assert screen.buffer[0][0].data == "$"
    assert screen.buffer[0][1].data == " "


def test_display_tracks_command_output():
    screen, stream = make_screen(cols=40, rows=4)
    stream.feed("$ ls\n")
    stream.feed("file1.txt file2.txt\n")
    stream.feed("$ ")

    display = screen.display
    assert display[0].rstrip() == "$ ls"
    assert "file1.txt" in display[1]
    assert display[2].rstrip() == "$"


def test_buffer_characters_expose_data_attribute():
    screen, stream = make_screen(cols=5, rows=1)
    stream.feed("abc")

    for i, expected in enumerate("abc"):
        char = screen.buffer[0][i]
        assert hasattr(char, "data")
        assert char.data == expected
