"""
Tests for Utility Functions
"""

import pytest


def test_format_duration():
    """Test duration formatting."""
    from FruityWolf.utils import format_duration
    
    assert format_duration(0) == "0:00"
    assert format_duration(59) == "0:59"
    assert format_duration(60) == "1:00"
    assert format_duration(65) == "1:05"
    assert format_duration(3600) == "1:00:00"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(None) == "--:--"
    assert format_duration(-1) == "--:--"


def test_format_file_size():
    """Test file size formatting."""
    from FruityWolf.utils import format_file_size
    
    assert format_file_size(0) == "0 B"
    assert format_file_size(512) == "512 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1536) == "1.5 KB"
    assert format_file_size(1024 * 1024) == "1.0 MB"
    assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"


def test_format_timestamp():
    """Test timestamp formatting."""
    from FruityWolf.utils import format_timestamp
    import time
    
    # None returns "--"
    assert format_timestamp(None) == "--"
    
    # Today returns "Today HH:MM"
    now = int(time.time())
    result = format_timestamp(now)
    assert "Today" in result or ":" in result


def test_sanitize_filename():
    """Test filename sanitization."""
    from FruityWolf.utils import sanitize_filename
    
    assert sanitize_filename("normal.txt") == "normal.txt"
    assert sanitize_filename("file<>name") == "file__name"
    assert sanitize_filename("path/to\\file") == "path_to_file"
    assert sanitize_filename("file:name?") == "file_name_"


def test_generate_gradient_color():
    """Test gradient color generation."""
    from FruityWolf.utils import generate_gradient_color
    
    color1, color2 = generate_gradient_color("Test")
    
    # Should return RGB tuples
    assert len(color1) == 3
    assert len(color2) == 3
    
    # Values should be 0-255
    for val in color1 + color2:
        assert 0 <= val <= 255
    
    # Same input should give same output
    color1_again, color2_again = generate_gradient_color("Test")
    assert color1 == color1_again
    assert color2 == color2_again


def test_rgb_to_hex():
    """Test RGB to hex conversion."""
    from FruityWolf.utils import rgb_to_hex
    
    assert rgb_to_hex(0, 0, 0) == "#000000"
    assert rgb_to_hex(255, 255, 255) == "#ffffff"
    assert rgb_to_hex(255, 0, 0) == "#ff0000"
    assert rgb_to_hex(0, 255, 0) == "#00ff00"
    assert rgb_to_hex(0, 0, 255) == "#0000ff"
    assert rgb_to_hex(29, 185, 84) == "#1db954"  # Spotify green


def test_keyboard_shortcuts():
    """Test keyboard shortcut helper."""
    from FruityWolf.utils import KeyboardShortcut
    
    assert KeyboardShortcut.get_shortcut('play_pause') == 'Space'
    assert KeyboardShortcut.get_shortcut('search') == 'Ctrl+F'
    assert KeyboardShortcut.get_shortcut('nonexistent') == ''
