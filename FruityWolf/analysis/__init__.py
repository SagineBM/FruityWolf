"""
Analysis Package
"""

from .detector import (
    AnalysisResult,
    AnalyzerThread,
    analyze_audio,
    analyze_bpm_simple,
    analyze_bpm_librosa,
    analyze_key_simple,
    analyze_key_librosa,
    get_camelot,
    format_bpm,
    format_key,
    KEYS,
    CAMELOT_MAPPING,
)

__all__ = [
    'AnalysisResult',
    'AnalyzerThread',
    'analyze_audio',
    'analyze_bpm_simple',
    'analyze_bpm_librosa',
    'analyze_key_simple',
    'analyze_key_librosa',
    'get_camelot',
    'format_bpm',
    'format_key',
    'KEYS',
    'CAMELOT_MAPPING',
]
