"""
Tests for FL Studio Adapter

Tests file role detection, signal-based matching, and confidence scoring.
"""

import pytest
import tempfile
from pathlib import Path

from FruityWolf.scanner.adapters.fl_studio import FLStudioAdapter
from FruityWolf.scanner.adapters.base import FileRole


def test_detect_file_role_flp():
    """Test FLP file role detection."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        flp_file = project_root / "project.flp"
        flp_file.touch()
        
        role = adapter.detect_file_role(flp_file, project_root)
        assert role == FileRole.PROJECT_FILE


def test_detect_file_role_render():
    """Test render file role detection."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        render_file = project_root / "render.wav"
        render_file.touch()
        
        role = adapter.detect_file_role(render_file, project_root)
        assert role == FileRole.RENDER


def test_detect_file_role_internal_audio():
    """Test internal audio file role detection."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        audio_dir = project_root / "Audio"
        audio_dir.mkdir()
        audio_file = audio_dir / "internal.wav"
        audio_file.touch()
        
        role = adapter.detect_file_role(audio_file, project_root)
        assert role == FileRole.INTERNAL_AUDIO


def test_detect_file_role_backup():
    """Test backup file role detection."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        backup_dir = project_root / "Backup"
        backup_dir.mkdir()
        backup_file = backup_dir / "backup.flp"
        backup_file.touch()
        
        role = adapter.detect_file_role(backup_file, project_root)
        assert role == FileRole.BACKUP


def test_detect_file_role_stem():
    """Test stem file role detection."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        stems_dir = project_root / "Stems"
        stems_dir.mkdir()
        stem_file = stems_dir / "stem.wav"
        stem_file.touch()
        
        role = adapter.detect_file_role(stem_file, project_root)
        assert role == FileRole.STEM


def test_detect_file_role_sample():
    """Test sample file role detection."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        samples_dir = project_root / "Samples"
        samples_dir.mkdir()
        sample_file = samples_dir / "sample.wav"
        sample_file.touch()
        
        role = adapter.detect_file_role(sample_file, project_root)
        assert role == FileRole.SAMPLE


def test_compute_match_score_high_match():
    """Test match score computation for high match."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        flp_file = project_root / "MySong.flp"
        flp_file.touch()
        audio_file = project_root / "MySong_final.wav"
        audio_file.touch()
        
        from FruityWolf.scanner.identity.signals import extract_file_signals
        
        signals = extract_file_signals(
            audio_file,
            project_flp_path=flp_file,
            reference_mtime=int(flp_file.stat().st_mtime)
        )
        
        score, reasons = adapter.compute_match_score(
            audio_file,
            flp_file,
            {'signals': signals, 'flp_mtime': flp_file.stat().st_mtime}
        )
        
        assert score >= adapter.CONFIDENT_THRESHOLD, f"High match should score >= {adapter.CONFIDENT_THRESHOLD}, got {score}"
        assert len(reasons) > 0
        assert any('token' in reason.lower() for reason in reasons)


def test_compute_match_score_low_match():
    """Test match score computation for low match."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        flp_file = project_root / "SongA.flp"
        flp_file.touch()
        audio_file = project_root / "CompletelyDifferent.wav"
        audio_file.touch()
        
        from FruityWolf.scanner.identity.signals import extract_file_signals
        
        signals = extract_file_signals(
            audio_file,
            project_flp_path=flp_file,
            reference_mtime=int(flp_file.stat().st_mtime)
        )
        
        score, reasons = adapter.compute_match_score(
            audio_file,
            flp_file,
            {'signals': signals, 'flp_mtime': flp_file.stat().st_mtime}
        )
        
        assert score < adapter.CONFIDENT_THRESHOLD, f"Low match should score < {adapter.CONFIDENT_THRESHOLD}, got {score}"


def test_compute_match_score_with_timestamp_bonus():
    """Test match score includes timestamp proximity bonus."""
    import time
    
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        flp_file = project_root / "Song.flp"
        flp_file.touch()
        
        # Create audio file with recent mtime (within 1 hour)
        audio_file = project_root / "Song.wav"
        audio_file.touch()
        
        # Set mtime to be close
        current_time = time.time()
        flp_file.touch()
        audio_file.touch()
        
        from FruityWolf.scanner.identity.signals import extract_file_signals
        
        signals = extract_file_signals(
            audio_file,
            project_flp_path=flp_file,
            reference_mtime=int(flp_file.stat().st_mtime)
        )
        
        score, reasons = adapter.compute_match_score(
            audio_file,
            flp_file,
            {'signals': signals, 'flp_mtime': flp_file.stat().st_mtime}
        )
        
        assert score > 0
        assert any('mtime' in reason.lower() for reason in reasons)


def test_resolve_conflicts():
    """Test conflict resolution."""
    adapter = FLStudioAdapter()
    
    from FruityWolf.scanner.adapters.base import MatchResult
    
    # Create matches with different scores
    matches = [
        MatchResult(
            file_path=Path("audio1.wav"),
            project_id=None,
            confidence_score=80,
            match_reasons=["high match"],
            signals={}
        ),
        MatchResult(
            file_path=Path("audio2.wav"),
            project_id=None,
            confidence_score=60,
            match_reasons=["medium match"],
            signals={}
        ),
        MatchResult(
            file_path=Path("audio3.wav"),
            project_id=None,
            confidence_score=40,
            match_reasons=["low match"],
            signals={}
        ),
    ]
    
    resolved = adapter.resolve_conflicts(matches)
    
    assert len(resolved) == 3
    # Should be sorted by score descending
    assert resolved[0].confidence_score == 80
    assert resolved[1].confidence_score == 60
    assert resolved[2].confidence_score == 40


def test_compute_flat_folder_confidence():
    """Test flat folder confidence computation."""
    adapter = FLStudioAdapter()
    
    # High score with fingerprint match
    confidence = adapter.compute_flat_folder_confidence(85, True)
    assert confidence <= 85
    assert confidence >= 80
    
    # High score without fingerprint match
    confidence = adapter.compute_flat_folder_confidence(85, False)
    assert confidence <= 80
    
    # Low score
    confidence = adapter.compute_flat_folder_confidence(30, False)
    assert confidence <= 30
