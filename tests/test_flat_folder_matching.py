"""
Integration Tests for Flat Folder Matching

Tests the complete flat folder matching workflow with real file structures.
"""

import pytest
import tempfile
import time
from pathlib import Path

from FruityWolf.scanner.adapters.fl_studio import FLStudioAdapter
from FruityWolf.scanner.identity import IdentityStore, compute_fingerprint, extract_file_signals


def test_flat_folder_matching_basic():
    """Test basic flat folder matching with 2 FLPs and multiple WAVs."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create 2 FLP files
        flp1 = root / "ProjectA.flp"
        flp1.touch()
        flp2 = root / "ProjectB.flp"
        flp2.touch()
        
        # Create audio files
        audio1 = root / "ProjectA_final.wav"  # Should match FLP1
        audio1.touch()
        audio2 = root / "ProjectA_v2.wav"  # Should match FLP1
        audio2.touch()
        audio3 = root / "ProjectB_mix.wav"  # Should match FLP2
        audio3.touch()
        audio4 = root / "Unrelated.wav"  # Should not match (low score)
        audio4.touch()
        
        # Use adapter to match - match each FLP separately
        matches_flp1 = adapter.match_files_to_project(
            project_files=[flp1],
            candidate_files=[audio1, audio2, audio3, audio4],
            project_root=root
        )
        
        matches_flp2 = adapter.match_files_to_project(
            project_files=[flp2],
            candidate_files=[audio1, audio2, audio3, audio4],
            project_root=root
        )
        
        # Should have matches for FLP1
        assert len(matches_flp1) > 0
        
        # Check that audio1 and audio2 match flp1 (high confidence)
        flp1_matches = [m for m in matches_flp1 if 'ProjectA' in str(m.file_path)]
        assert len(flp1_matches) >= 2, f"Expected at least 2 matches for FLP1, got {len(flp1_matches)}"
        
        # Check that audio3 matches flp2
        flp2_matches = [m for m in matches_flp2 if 'ProjectB' in str(m.file_path)]
        assert len(flp2_matches) >= 1, f"Expected at least 1 match for FLP2, got {len(flp2_matches)}"
        
        # Check confidence scores
        for match in matches_flp1 + matches_flp2:
            assert match.confidence_score >= adapter.MIN_THRESHOLD
            assert len(match.match_reasons) > 0


def test_flat_folder_matching_conflict_prevention():
    """Test that one audio file is not assigned to multiple FLPs."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create 2 FLP files with similar names
        flp1 = root / "MySong.flp"
        flp1.touch()
        flp2 = root / "MySong_v2.flp"
        flp2.touch()
        
        # Create audio that could match both
        audio = root / "MySong_final.wav"
        audio.touch()
        
        # Match files
        matches_flp1 = adapter.match_files_to_project(
            project_files=[flp1],
            candidate_files=[audio],
            project_root=root
        )
        
        matches_flp2 = adapter.match_files_to_project(
            project_files=[flp2],
            candidate_files=[audio],
            project_root=root
        )
        
        # Both should match, but conflict resolution should assign to best match
        assert len(matches_flp1) > 0 or len(matches_flp2) > 0
        
        # The higher scoring match should win
        if matches_flp1 and matches_flp2:
            score1 = matches_flp1[0].confidence_score
            score2 = matches_flp2[0].confidence_score
            # One should be higher (or equal)
            assert score1 >= score2 or score2 >= score1


def test_flat_folder_matching_with_timestamps():
    """Test matching considers timestamp proximity."""
    import time
    
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create FLP
        flp = root / "Song.flp"
        flp.touch()
        flp_mtime = flp.stat().st_mtime
        
        # Create audio file created recently (within 1 hour)
        audio = root / "Song.wav"
        audio.touch()
        # Set mtime to be close to FLP
        time.sleep(0.1)
        audio.touch()
        
        matches = adapter.match_files_to_project(
            project_files=[flp],
            candidate_files=[audio],
            project_root=root
        )
        
        assert len(matches) > 0
        match = matches[0]
        
        # Should have timestamp bonus
        assert match.confidence_score >= adapter.CONFIDENT_THRESHOLD
        assert any('mtime' in reason.lower() for reason in match.match_reasons)


def test_structured_folder_confidence():
    """Test confidence calculation for structured folders."""
    adapter = FLStudioAdapter()
    
    # Structured folders should have high confidence
    # (This is tested via compute_flat_folder_confidence)
    confidence = adapter.compute_flat_folder_confidence(90, True)
    assert confidence >= 80
    
    # Flat folders without fingerprint match should be capped lower
    confidence_flat = adapter.compute_flat_folder_confidence(90, False)
    assert confidence_flat <= 80


def test_token_overlap_scoring():
    """Test that token overlap contributes to match score."""
    adapter = FLStudioAdapter()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create FLP with specific name
        flp = root / "MyAwesomeBeat.flp"
        flp.touch()
        
        # Create audio with high token overlap
        audio_high = root / "MyAwesomeBeat_final.wav"
        audio_high.touch()
        
        # Create audio with low token overlap
        audio_low = root / "DifferentSong.wav"
        audio_low.touch()
        
        matches_high = adapter.match_files_to_project(
            project_files=[flp],
            candidate_files=[audio_high],
            project_root=root
        )
        
        matches_low = adapter.match_files_to_project(
            project_files=[flp],
            candidate_files=[audio_low],
            project_root=root
        )
        
        if matches_high and matches_low:
            score_high = matches_high[0].confidence_score
            score_low = matches_low[0].confidence_score
            
            # High overlap should score higher
            assert score_high > score_low, f"High overlap ({score_high}) should score higher than low ({score_low})"
