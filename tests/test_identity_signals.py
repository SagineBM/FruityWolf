"""
Tests for Identity Signals

Tests signal extraction, tokenization, and token overlap computation.
"""

import pytest
import tempfile
from pathlib import Path

from FruityWolf.scanner.identity.signals import (
    extract_name_tokens,
    compute_token_overlap,
    extract_file_signals,
    SignalType
)


def test_extract_name_tokens_basic():
    """Test basic name token extraction."""
    file_path = Path("MySong_v2_final.wav")
    tokens = extract_name_tokens(file_path)
    
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert 'mysong' in tokens or 'song' in tokens


def test_extract_name_tokens_strips_suffixes():
    """Test that suffix tokens are stripped."""
    file_path = Path("MySong_v2_final_mix.wav")
    tokens = extract_name_tokens(file_path)
    
    # Should strip: v2, final, mix
    assert 'v2' not in tokens
    assert 'final' not in tokens
    assert 'mix' not in tokens


def test_extract_name_tokens_normalizes():
    """Test name normalization."""
    file_path = Path("My-Song_With.Dots (2024).wav")
    tokens = extract_name_tokens(file_path)
    
    # Should normalize separators and remove brackets
    assert isinstance(tokens, list)
    # Check that separators are handled
    assert all('-' not in token for token in tokens)
    assert all('_' not in token for token in tokens)


def test_compute_token_overlap_identical():
    """Test token overlap for identical names."""
    tokens1 = ['my', 'song', 'beat']
    tokens2 = ['my', 'song', 'beat']
    
    overlap = compute_token_overlap(tokens1, tokens2)
    
    assert overlap == 1.0, "Identical tokens should have 1.0 overlap"


def test_compute_token_overlap_partial():
    """Test token overlap for partial matches."""
    tokens1 = ['my', 'song', 'beat']
    tokens2 = ['my', 'song']
    
    overlap = compute_token_overlap(tokens1, tokens2)
    
    assert 0.0 < overlap < 1.0
    assert overlap > 0.5  # Should be high since 2/3 tokens match


def test_compute_token_overlap_no_match():
    """Test token overlap for no matches."""
    tokens1 = ['my', 'song']
    tokens2 = ['other', 'track']
    
    overlap = compute_token_overlap(tokens1, tokens2)
    
    assert overlap == 0.0, "No matching tokens should have 0.0 overlap"


def test_compute_token_overlap_empty():
    """Test token overlap with empty lists."""
    assert compute_token_overlap([], []) == 0.0
    assert compute_token_overlap(['token'], []) == 0.0
    assert compute_token_overlap([], ['token']) == 0.0


def test_extract_file_signals_basic():
    """Test basic signal extraction."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
        f.write(b'RIFF' + b'\x00' * 1000)
        f.flush()
        file_path = Path(f.name)
    
    try:
        signals = extract_file_signals(file_path)
        
        assert isinstance(signals, list)
        assert len(signals) > 0
        
        # Should have at least name tokens, file size, file ext
        signal_types = [s.signal_type for s in signals]
        assert SignalType.NAME_TOKENS in signal_types
        assert SignalType.FILE_SIZE in signal_types
        assert SignalType.FILE_EXT in signal_types
    finally:
        file_path.unlink()


def test_extract_file_signals_with_reference_mtime():
    """Test signal extraction with reference mtime."""
    import time
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
        f.write(b'RIFF' + b'\x00' * 1000)
        f.flush()
        file_path = Path(f.name)
    
    try:
        reference_mtime = int(time.time())
        signals = extract_file_signals(file_path, reference_mtime=reference_mtime)
        
        # Should have mtime_delta signal
        signal_types = [s.signal_type for s in signals]
        assert SignalType.MTIME_DELTA in signal_types
        
        # Find mtime_delta signal
        mtime_signal = next((s for s in signals if s.signal_type == SignalType.MTIME_DELTA), None)
        assert mtime_signal is not None
        assert mtime_signal.value_num is not None
    finally:
        file_path.unlink()


def test_extract_file_signals_with_flp_reference():
    """Test signal extraction with FLP reference for matching."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f1:
        f1.write(b'RIFF' + b'\x00' * 1000)
        f1.flush()
        audio_path = Path(f1.name)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.flp') as f2:
        f2.write(b'FL Studio' + b'\x00' * 1000)
        f2.flush()
        flp_path = Path(f2.name)
    
    try:
        signals = extract_file_signals(
            audio_path,
            project_flp_path=flp_path,
            reference_mtime=int(flp_path.stat().st_mtime)
        )
        
        assert isinstance(signals, list)
        assert len(signals) > 0
        
        # Should have mtime_delta signal
        signal_types = [s.signal_type for s in signals]
        assert SignalType.MTIME_DELTA in signal_types
    finally:
        audio_path.unlink()
        flp_path.unlink()


def test_extract_file_signals_with_metadata():
    """Test signal extraction with optional metadata."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
        f.write(b'RIFF' + b'\x00' * 1000)
        f.flush()
        file_path = Path(f.name)
    
    try:
        signals = extract_file_signals(
            file_path,
            duration=180.5,
            bpm=128.0,
            key='C major'
        )
        
        # Should have duration, BPM, and key signals
        signal_types = [s.signal_type for s in signals]
        assert SignalType.DURATION in signal_types
        assert SignalType.BPM in signal_types
        assert SignalType.KEY in signal_types
        
        # Check values
        duration_signal = next((s for s in signals if s.signal_type == SignalType.DURATION), None)
        assert duration_signal is not None
        assert duration_signal.value_num == 180.5
        
        bpm_signal = next((s for s in signals if s.signal_type == SignalType.BPM), None)
        assert bpm_signal is not None
        assert bpm_signal.value_num == 128.0
        
        key_signal = next((s for s in signals if s.signal_type == SignalType.KEY), None)
        assert key_signal is not None
        assert key_signal.value_text == 'C major'
    finally:
        file_path.unlink()
