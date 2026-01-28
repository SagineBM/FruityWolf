"""
FL Studio Render Classifier
Correctly identifies renders vs internal audio vs source samples.
"""

import os
import logging
from pathlib import Path
from typing import List, Set, Optional, Tuple
from dataclasses import dataclass
try:
    from ..database import get_setting
except ImportError:
    # Fallback if get_setting not available
    def get_setting(key: str, default: str = '') -> str:
        return default

logger = logging.getLogger(__name__)

# Audio extensions for renders
RENDER_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif'}

# Excluded directories (audio here is NOT a render)
EXCLUDED_DIRS = {'Audio', 'Samples', 'Backup'}

# Optional render subfolders (user-configurable, default disabled)
DEFAULT_RENDER_SUBFOLDERS = ['Render', 'Renders', 'Exports', 'Bounces', 'Mixdowns']


@dataclass
class AudioFileClassification:
    """Classification result for an audio file."""
    path: str
    classification: str  # 'RENDER', 'INTERNAL_AUDIO', 'SOURCE_SAMPLE', 'UNKNOWN'
    relative_path: str  # Relative to project root
    is_in_excluded_dir: bool
    is_in_render_subfolder: bool


def get_render_subfolders_allowed() -> List[str]:
    """
    Get list of allowed render subfolders from settings.
    Default: empty list (only root renders allowed).
    """
    try:
        setting = get_setting('render_subfolders_allowed', '')
        if not setting:
            return []
        # Parse comma-separated list
        folders = [f.strip() for f in setting.split(',') if f.strip()]
        return folders
    except:
        return []


def classify_audio_file(
    audio_path: Path,
    project_root: Path,
    render_subfolders_allowed: Optional[List[str]] = None
) -> AudioFileClassification:
    """
    Classify an audio file as RENDER, INTERNAL_AUDIO, SOURCE_SAMPLE, or UNKNOWN.
    
    Rules:
    1. RENDER: Audio in project root OR in allowed render subfolders
    2. INTERNAL_AUDIO: Audio under Audio/**
    3. SOURCE_SAMPLE: Audio under Samples/**
    4. UNKNOWN: Audio elsewhere (e.g., Stems/, other subfolders)
    
    Args:
        audio_path: Absolute path to audio file
        project_root: Absolute path to project root
        render_subfolders_allowed: Optional list of allowed subfolder names
        
    Returns:
        AudioFileClassification
    """
    if render_subfolders_allowed is None:
        render_subfolders_allowed = get_render_subfolders_allowed()
    
    try:
        relative_path = audio_path.relative_to(project_root)
    except ValueError:
        # File is not under project root (shouldn't happen, but handle gracefully)
        return AudioFileClassification(
            path=str(audio_path),
            classification='UNKNOWN',
            relative_path=str(audio_path),
            is_in_excluded_dir=False,
            is_in_render_subfolder=False
        )
    
    parts = relative_path.parts
    
    # Check if in excluded directories (Audio/, Samples/, Backup/)
    if len(parts) > 1:
        first_dir = parts[0]
        if first_dir in EXCLUDED_DIRS:
            if first_dir == 'Audio':
                classification = 'INTERNAL_AUDIO'
            elif first_dir == 'Samples':
                classification = 'SOURCE_SAMPLE'
            else:  # Backup
                classification = 'UNKNOWN'  # Backup files are not renders or samples
            
            return AudioFileClassification(
                path=str(audio_path),
                classification=classification,
                relative_path=str(relative_path),
                is_in_excluded_dir=True,
                is_in_render_subfolder=False
            )
        
        # Check if in allowed render subfolder
        if first_dir in render_subfolders_allowed:
            return AudioFileClassification(
                path=str(audio_path),
                classification='RENDER',
                relative_path=str(relative_path),
                is_in_excluded_dir=False,
                is_in_render_subfolder=True
            )
    
    # Root-level audio file = RENDER
    if len(parts) == 1:
        return AudioFileClassification(
            path=str(audio_path),
            classification='RENDER',
            relative_path=str(relative_path),
            is_in_excluded_dir=False,
            is_in_render_subfolder=False
        )
    
    # Audio in other subfolders = UNKNOWN (not a render, not internal audio)
    return AudioFileClassification(
        path=str(audio_path),
        classification='UNKNOWN',
        relative_path=str(relative_path),
        is_in_excluded_dir=False,
        is_in_render_subfolder=False
    )


def find_project_renders(
    project_root: Path,
    render_subfolders_allowed: Optional[List[str]] = None
) -> List[AudioFileClassification]:
    """
    Find all render candidates in a project root.
    
    Returns:
        List of AudioFileClassification objects classified as RENDER
    """
    if render_subfolders_allowed is None:
        render_subfolders_allowed = get_render_subfolders_allowed()
    
    renders = []
    
    # 1. Scan root level
    try:
        for item in project_root.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                if ext in RENDER_EXTENSIONS:
                    classification = classify_audio_file(item, project_root, render_subfolders_allowed)
                    if classification.classification == 'RENDER':
                        renders.append(classification)
    except PermissionError:
        logger.warning(f"Permission denied scanning root: {project_root}")
    
    # 2. Scan allowed render subfolders (if any)
    for subfolder_name in render_subfolders_allowed:
        subfolder = project_root / subfolder_name
        if subfolder.exists() and subfolder.is_dir():
            try:
                for item in subfolder.rglob('*'):  # Recursive search in render subfolder
                    if item.is_file():
                        ext = item.suffix.lower()
                        if ext in RENDER_EXTENSIONS:
                            classification = classify_audio_file(item, project_root, render_subfolders_allowed)
                            if classification.classification == 'RENDER':
                                renders.append(classification)
            except PermissionError:
                logger.warning(f"Permission denied scanning render subfolder: {subfolder}")
    
    return renders


def find_internal_audio(project_root: Path) -> List[str]:
    """
    Find all internal audio files under Audio/ directory.
    
    Returns:
        List of audio file paths
    """
    audio_files = []
    audio_dir = project_root / 'Audio'
    
    if not audio_dir.exists() or not audio_dir.is_dir():
        return audio_files
    
    try:
        for item in audio_dir.rglob('*'):
            if item.is_file():
                ext = item.suffix.lower()
                if ext in RENDER_EXTENSIONS:
                    audio_files.append(str(item))
    except PermissionError:
        logger.warning(f"Permission denied scanning Audio/: {audio_dir}")
    
    return audio_files


def find_source_samples(project_root: Path) -> List[str]:
    """
    Find all source sample files under Samples/ directory.
    Note: This is already handled by project_samples table, but useful for classification.
    
    Returns:
        List of sample file paths
    """
    sample_files = []
    samples_dir = project_root / 'Samples'
    
    if not samples_dir.exists() or not samples_dir.is_dir():
        return sample_files
    
    try:
        for item in samples_dir.rglob('*'):
            if item.is_file():
                ext = item.suffix.lower()
                if ext in RENDER_EXTENSIONS:
                    sample_files.append(str(item))
    except PermissionError:
        logger.warning(f"Permission denied scanning Samples/: {samples_dir}")
    
    return sample_files
