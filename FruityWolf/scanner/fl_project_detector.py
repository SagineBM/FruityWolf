"""
FL Studio Project Root Detector
Implements scoring-based detection of FL Studio project folders.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FLProjectDetectionResult:
    """Result of FL Studio project root detection."""
    is_fl_project: bool
    score: int
    flp_paths: List[str]  # All FLP files found (root + backup)
    primary_flp_path: Optional[str]  # Best FLP (newest in root, fallback to backup)
    has_audio_dir: bool
    has_samples_dir: bool
    has_backup_dir: bool
    detection_reason: str


def detect_fl_project_root(folder_path: Path) -> FLProjectDetectionResult:
    """
    Detect if a folder is an FL Studio project root using scoring.
    
    Scoring rules:
    - +5 if root contains *.flp
    - +3 if Backup/ contains *.flp
    - +1 for each directory present: Audio/, Samples/, Backup/
    - Mark as FL project if score >= 5
    
    Args:
        folder_path: Path to folder to check
        
    Returns:
        FLProjectDetectionResult with detection info
    """
    if not folder_path.exists() or not folder_path.is_dir():
        return FLProjectDetectionResult(
            is_fl_project=False,
            score=0,
            flp_paths=[],
            primary_flp_path=None,
            has_audio_dir=False,
            has_samples_dir=False,
            has_backup_dir=False,
            detection_reason="Not a directory"
        )
    
    score = 0
    flp_paths = []
    root_flps = []
    backup_flps = []
    
    # Check root for FLP files
    try:
        for item in folder_path.iterdir():
            if item.is_file() and item.suffix.lower() == '.flp':
                root_flps.append(str(item))
                flp_paths.append(str(item))
                score += 5
                break  # Only need one FLP in root for +5
    except PermissionError:
        pass
    
    # Check for standard FL Studio directories
    audio_dir = folder_path / 'Audio'
    samples_dir = folder_path / 'Samples'
    backup_dir = folder_path / 'Backup'
    
    has_audio_dir = audio_dir.exists() and audio_dir.is_dir()
    has_samples_dir = samples_dir.exists() and samples_dir.is_dir()
    has_backup_dir = backup_dir.exists() and backup_dir.is_dir()
    
    if has_audio_dir:
        score += 1
    if has_samples_dir:
        score += 1
    if has_backup_dir:
        score += 1
        
        # Check Backup/ for FLP files
        try:
            for item in backup_dir.iterdir():
                if item.is_file() and item.suffix.lower() == '.flp':
                    backup_flps.append(str(item))
                    if str(item) not in flp_paths:
                        flp_paths.append(str(item))
                    score += 3
                    break  # Only need one FLP in backup for +3
        except PermissionError:
            pass
    
    # Determine primary FLP (prefer root, fallback to newest backup)
    primary_flp_path = None
    if root_flps:
        # Use newest FLP from root
        primary_flp_path = max(root_flps, key=lambda p: Path(p).stat().st_mtime)
    elif backup_flps:
        # Fallback to newest FLP from backup
        primary_flp_path = max(backup_flps, key=lambda p: Path(p).stat().st_mtime)
    
    is_fl_project = score >= 5
    
    reason_parts = []
    if root_flps:
        reason_parts.append(f"FLP in root ({len(root_flps)})")
    if backup_flps:
        reason_parts.append(f"FLP in Backup ({len(backup_flps)})")
    if has_audio_dir:
        reason_parts.append("Audio/")
    if has_samples_dir:
        reason_parts.append("Samples/")
    if has_backup_dir:
        reason_parts.append("Backup/")
    
    detection_reason = f"Score: {score} ({', '.join(reason_parts)})" if reason_parts else f"Score: {score} (insufficient)"
    
    return FLProjectDetectionResult(
        is_fl_project=is_fl_project,
        score=score,
        flp_paths=flp_paths,
        primary_flp_path=primary_flp_path,
        has_audio_dir=has_audio_dir,
        has_samples_dir=has_samples_dir,
        has_backup_dir=has_backup_dir,
        detection_reason=detection_reason
    )


def find_all_flp_files(project_root: Path) -> List[str]:
    """
    Find all FLP files in a project (root + Backup/).
    Does NOT recursively search other subdirectories.
    
    Returns:
        List of FLP file paths
    """
    flp_files = []
    
    # Root level
    try:
        for item in project_root.iterdir():
            if item.is_file() and item.suffix.lower() == '.flp':
                flp_files.append(str(item))
    except PermissionError:
        pass
    
    # Backup directory only
    backup_dir = project_root / 'Backup'
    if backup_dir.exists() and backup_dir.is_dir():
        try:
            for item in backup_dir.iterdir():
                if item.is_file() and item.suffix.lower() == '.flp':
                    flp_files.append(str(item))
        except PermissionError:
            pass
    
    return flp_files
