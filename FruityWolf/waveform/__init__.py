"""
Waveform Package

Waveform extraction and caching for Spotify-grade visualization.
"""

from .extractor import (
    WaveformData,
    WaveformExtractor,
    WaveformThread,
    WaveformCache,
    extract_waveform,
    get_or_extract_waveform,
    get_cached_waveform,
    get_waveform_cache_path,
    get_file_signature,
    is_cache_valid,
    cleanup_waveform_cache,
)

__all__ = [
    'WaveformData',
    'WaveformExtractor',
    'WaveformThread',
    'WaveformCache',
    'extract_waveform',
    'get_or_extract_waveform',
    'get_cached_waveform',
    'get_waveform_cache_path',
    'get_file_signature',
    'is_cache_valid',
    'cleanup_waveform_cache',
]
