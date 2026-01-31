"""
FL Studio Render Classifier
Correctly identifies renders vs internal audio vs source samples.
Also provides smart name matching for associating renders with FLP files.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Set, Optional, Tuple, Dict
from dataclasses import dataclass
from difflib import SequenceMatcher
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


# =============================================================================
# Smart Name Matching for Renders <-> FLP Association
# =============================================================================

# Common render suffixes that should be stripped for matching
RENDER_SUFFIX_TOKENS = {
    # Version labels
    "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10",
    "ver", "version",
    # Final/export labels  
    "final", "finale", "lekher", "done", "finished",
    # Mix/master labels
    "mix", "premix", "master", "mastered", "remaster",
    # Export/render labels
    "bounce", "bounced", "export", "exported", "render", "rendered",
    # Demo/test labels
    "demo", "test", "draft", "wip", "sketch",
    # Vocal variations
    "inst", "instrumental", "acapella", "vocals", "novocals", "no",
    "with", "without",
    # Edit types
    "edit", "radio", "clean", "dirty", "extended", "short",
    # Common Arabic/French suffixes (for Moroccan producers)
    "mixe", "finale", "fini",
}

# Match threshold for associating audio with FLP
MATCH_THRESHOLD = 0.72


def _normalize_name(name: str) -> str:
    """
    Normalize a filename for matching.
    - Lowercase
    - Remove extension
    - Replace separators with spaces
    - Clean up extra whitespace
    """
    name = name.lower()
    # Remove extension
    name = re.sub(r"\.[a-z0-9]{2,5}$", "", name)
    # Replace brackets with spaces
    name = re.sub(r"[\[\]\(\)\{\}]", " ", name)
    # Replace separators with spaces
    name = re.sub(r"[-_.]+", " ", name)
    # Clean up whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _tokenize(clean_name: str) -> List[str]:
    """Split cleaned name into tokens."""
    return clean_name.split()


def _strip_suffix_tokens(tokens: List[str]) -> List[str]:
    """Remove common render suffix tokens from token list."""
    result = []
    for token in tokens:
        # Skip pure numbers (often appended as _1, _2, etc.)
        if token.isdigit():
            continue
        # Skip known suffix tokens
        if token in RENDER_SUFFIX_TOKENS:
            continue
        # Skip version numbers like v12
        if re.fullmatch(r"v\d+", token):
            continue
        result.append(token)
    return result


def match_audio_to_flp(audio_name: str, flp_name: str) -> float:
    """
    Calculate similarity score between an audio filename and an FLP filename.
    
    Score is 0.0 to 1.0 based on:
    - 55% sequence similarity (SequenceMatcher)
    - 45% token overlap
    - +15% bonus if audio starts with FLP stem
    - 50% penalty if core tokens don't overlap (<34%)
    
    Args:
        audio_name: Audio filename (e.g., "MySong_v2_final.wav")
        flp_name: FLP filename (e.g., "MySong.flp")
        
    Returns:
        Similarity score from 0.0 to 1.0
        
    Examples:
        >>> match_audio_to_flp("MySong_v2_final.wav", "MySong.flp")
        0.92  # High match - same base name
        >>> match_audio_to_flp("OtherSong.wav", "MySong.flp")
        0.15  # Low match - different names
    """
    # Normalize names
    audio_clean = _normalize_name(audio_name)
    flp_clean = _normalize_name(flp_name)
    
    # Tokenize
    audio_tokens = _tokenize(audio_clean)
    flp_tokens = _tokenize(flp_clean)
    
    # Strip suffix tokens for core comparison
    audio_core = _strip_suffix_tokens(audio_tokens)
    flp_core = _strip_suffix_tokens(flp_tokens)
    
    if not flp_core:
        return 0.0
    
    # Rebuild strings from core tokens
    audio_core_str = " ".join(audio_core)
    flp_core_str = " ".join(flp_core)
    
    # 1. Sequence similarity (55% weight)
    seq_ratio = SequenceMatcher(None, audio_core_str, flp_core_str).ratio()
    
    # 2. Token overlap (45% weight)
    audio_set = set(audio_core)
    flp_set = set(flp_core)
    overlap = len(audio_set & flp_set) / max(1, len(flp_set))
    
    # 3. Prefix bonus (+15% if audio starts with FLP stem)
    prefix_bonus = 0.15 if audio_core_str.startswith(flp_core_str) else 0.0
    
    # Calculate base score
    score = 0.55 * seq_ratio + 0.45 * overlap + prefix_bonus
    
    # 4. Strong penalty if core tokens don't overlap enough
    if overlap < 0.34:
        score *= 0.5
    
    return max(0.0, min(1.0, score))


def match_renders_in_flat_folder(
    flp_path: Path, 
    audio_files: List[Path],
    threshold: float = MATCH_THRESHOLD
) -> List[Path]:
    """
    Match audio files to an FLP based on name similarity.
    
    Args:
        flp_path: Path to FLP file
        audio_files: List of audio file paths in the same folder
        threshold: Minimum score to consider a match (default 0.72)
        
    Returns:
        List of audio file paths that match the FLP, sorted by score (highest first)
    """
    scored = []
    flp_name = flp_path.name
    
    for audio_path in audio_files:
        score = match_audio_to_flp(audio_path.name, flp_name)
        if score >= threshold:
            scored.append((score, audio_path))
    
    # Sort by score descending
    scored.sort(reverse=True, key=lambda x: x[0])
    
    return [audio_path for score, audio_path in scored]


def arbitrate_flat_folder(
    flp_files: List[Path],
    audio_files: List[Path],
    threshold: float = MATCH_THRESHOLD
) -> Dict[Path, List[Path]]:
    """
    Arbitrate render assignments when multiple FLPs exist in same folder.
    Each audio file is assigned to the highest-scoring FLP only.
    
    Args:
        flp_files: List of FLP file paths
        audio_files: List of audio file paths
        threshold: Minimum score to consider a match
        
    Returns:
        Dict mapping each FLP to its matched audio files
    """
    # Calculate all scores
    all_scores: Dict[Path, List[Tuple[float, Path]]] = {flp: [] for flp in flp_files}
    audio_assignments: Dict[Path, Tuple[float, Path]] = {}  # audio -> (score, best_flp)
    
    for audio_path in audio_files:
        best_score = 0.0
        best_flp = None
        
        for flp_path in flp_files:
            score = match_audio_to_flp(audio_path.name, flp_path.name)
            if score >= threshold and score > best_score:
                best_score = score
                best_flp = flp_path
        
        if best_flp is not None:
            audio_assignments[audio_path] = (best_score, best_flp)
    
    # Build result dict: flp -> list of matched audio
    result: Dict[Path, List[Path]] = {flp: [] for flp in flp_files}
    for audio_path, (score, flp) in audio_assignments.items():
        result[flp].append(audio_path)
    
    # Sort each FLP's audio list by score (implied by assignment order, but let's be explicit)
    for flp in result:
        # Re-score and sort
        scored = [(match_audio_to_flp(a.name, flp.name), a) for a in result[flp]]
        scored.sort(reverse=True, key=lambda x: x[0])
        result[flp] = [a for s, a in scored]
    
    return result
