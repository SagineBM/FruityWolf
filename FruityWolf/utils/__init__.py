"""
Utils Package
"""

from .helpers import (
    format_duration,
    format_file_size,
    format_timestamp,
    format_smart_date,
    format_absolute_date,
    format_date_with_tooltip,
    open_file,
    open_folder,
    open_fl_studio,
    count_files_in_folder,
    get_folder_size,
    generate_gradient_color,
    rgb_to_hex,
    sanitize_filename,
    KeyboardShortcut,
    setup_logging,
)
from .icons import get_icon

__all__ = [
    'format_duration',
    'format_file_size',
    'format_timestamp',
    'format_smart_date',
    'format_absolute_date',
    'format_date_with_tooltip',
    'open_file',
    'open_folder',
    'open_fl_studio',
    'count_files_in_folder',
    'get_folder_size',
    'generate_gradient_color',
    'rgb_to_hex',
    'sanitize_filename',
    'KeyboardShortcut',
    'setup_logging',
    'get_icon',
]

from .images import get_cover_art, get_placeholder_cover
__all__.extend(['get_cover_art', 'get_placeholder_cover'])
