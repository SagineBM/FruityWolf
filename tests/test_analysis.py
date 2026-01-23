"""
Tests for Analysis Module
"""

import pytest


def test_key_constants():
    """Test key constants are defined."""
    from FruityWolf.analysis import KEYS, CAMELOT_MAPPING
    
    assert 'C' in KEYS
    assert 'Am' in KEYS
    assert len(KEYS) == 24  # 12 major + 12 minor
    
    assert 'C' in CAMELOT_MAPPING
    assert CAMELOT_MAPPING['Am'] == '8A'


def test_format_bpm():
    """Test BPM formatting."""
    from FruityWolf.analysis import format_bpm
    
    assert format_bpm(None) == '--'
    assert format_bpm(120.0) == '120'
    assert format_bpm(128.5) == '129'  # Rounds
    assert format_bpm(0) == '0'


def test_format_key():
    """Test key formatting."""
    from FruityWolf.analysis import format_key
    
    assert format_key(None) == '--'
    assert format_key('') == '--'
    assert format_key('Am') == 'Am'
    assert format_key('Am', show_camelot=True) == 'Am (8A)'
    assert format_key('C', show_camelot=True) == 'C (8B)'


def test_get_camelot():
    """Test Camelot wheel mapping."""
    from FruityWolf.analysis import get_camelot
    
    assert get_camelot('C') == '8B'
    assert get_camelot('Am') == '8A'
    assert get_camelot('G') == '9B'
    assert get_camelot('Em') == '9A'
    assert get_camelot('invalid') is None


def test_analysis_result_dataclass():
    """Test AnalysisResult dataclass."""
    from FruityWolf.analysis import AnalysisResult
    
    result = AnalysisResult()
    assert result.bpm is None
    assert result.key is None
    assert result.duration is None
    assert result.error is None
    
    result = AnalysisResult(bpm=120.0, key='Am', duration=180.0)
    assert result.bpm == 120.0
    assert result.key == 'Am'
    assert result.duration == 180.0
