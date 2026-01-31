"""
Tests for Identity Fingerprinting

Tests fast fingerprint computation and full hash computation.
"""

import pytest
import tempfile
from pathlib import Path

from FruityWolf.scanner.identity.fingerprint import compute_fingerprint, compute_full_hash


def test_compute_fingerprint_basic():
    """Test basic fingerprint computation."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.flp') as f:
        f.write(b'FL Studio Project File' + b'\x00' * 1000)
        f.flush()
        file_path = Path(f.name)
    
    try:
        fingerprint = compute_fingerprint(file_path)
        
        assert fingerprint is not None
        assert len(fingerprint) == 64  # SHA256 hex = 64 chars
        assert isinstance(fingerprint, str)
    finally:
        file_path.unlink()


def test_compute_fingerprint_consistency():
    """Test fingerprint is consistent for same file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.flp') as f:
        content = b'Test content' + b'\x00' * 5000
        f.write(content)
        f.flush()
        file_path = Path(f.name)
    
    try:
        fp1 = compute_fingerprint(file_path)
        fp2 = compute_fingerprint(file_path)
        
        assert fp1 == fp2, "Fingerprint should be consistent"
    finally:
        file_path.unlink()


def test_compute_fingerprint_different_files():
    """Test different files produce different fingerprints."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.flp') as f1:
        f1.write(b'File 1 content')
        f1.flush()
        file1 = Path(f1.name)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.flp') as f2:
        f2.write(b'File 2 content')
        f2.flush()
        file2 = Path(f2.name)
    
    try:
        fp1 = compute_fingerprint(file1)
        fp2 = compute_fingerprint(file2)
        
        assert fp1 != fp2, "Different files should have different fingerprints"
    finally:
        file1.unlink()
        file2.unlink()


def test_compute_fingerprint_changes_with_mtime():
    """Test fingerprint changes when mtime changes."""
    import time
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.flp') as f:
        f.write(b'Same content')
        f.flush()
        file_path = Path(f.name)
    
    try:
        fp1 = compute_fingerprint(file_path)
        
        # Change mtime
        time.sleep(1.1)  # Ensure mtime changes
        file_path.touch()
        
        fp2 = compute_fingerprint(file_path)
        
        assert fp1 != fp2, "Fingerprint should change when mtime changes"
    finally:
        file_path.unlink()


def test_compute_full_hash():
    """Test full hash computation."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
        content = b'RIFF' + b'Test audio content' * 100
        f.write(content)
        f.flush()
        file_path = Path(f.name)
    
    try:
        full_hash = compute_full_hash(file_path)
        
        assert full_hash is not None
        assert len(full_hash) == 64  # SHA256 hex = 64 chars
        assert isinstance(full_hash, str)
    finally:
        file_path.unlink()


def test_compute_fingerprint_nonexistent_file():
    """Test fingerprint computation handles nonexistent file gracefully."""
    nonexistent = Path('/nonexistent/file.flp')
    fingerprint = compute_fingerprint(nonexistent)
    
    assert fingerprint is None


def test_compute_full_hash_nonexistent_file():
    """Test full hash computation handles nonexistent file gracefully."""
    nonexistent = Path('/nonexistent/file.wav')
    full_hash = compute_full_hash(nonexistent)
    
    assert full_hash is None
