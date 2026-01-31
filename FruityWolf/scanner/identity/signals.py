"""
File Signals for Matching and Attribution

Signals are evidence used to match files to projects and determine confidence.
Examples: name tokens, mtime delta, duration, BPM, previously seen fingerprint.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of signals that can be extracted from files."""
    NAME_TOKENS = "name_tokens"
    MTIME_DELTA = "mtime_delta"
    DURATION = "duration"
    BPM = "bpm"
    KEY = "key"
    PREVIOUSLY_SEEN_FINGERPRINT = "previously_seen_fingerprint"
    FILE_SIZE = "file_size"
    FILE_EXT = "file_ext"


# Common render suffixes that should be stripped for tokenization
RENDER_SUFFIX_TOKENS = {
    "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10",
    "ver", "version",
    "final", "finale", "lekher", "done", "finished",
    "mix", "premix", "master", "mastered", "remaster",
    "bounce", "bounced", "export", "exported", "render", "rendered",
    "demo", "test", "draft", "wip", "sketch",
    "inst", "instrumental", "acapella", "vocals", "novocals", "no",
    "with", "without",
    "edit", "radio", "clean", "dirty", "extended", "short",
    "mixe", "finale", "fini",
}


@dataclass
class FileSignal:
    """A single signal extracted from a file."""
    signal_type: SignalType
    value_text: Optional[str] = None
    value_num: Optional[float] = None
    weight: int = 10


def _normalize_name(name: str) -> str:
    """
    Normalize a filename for tokenization.
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


def extract_name_tokens(file_path: Path) -> List[str]:
    """
    Extract normalized name tokens from a file path.
    
    Returns:
        List of core tokens (suffix tokens stripped)
    """
    name = file_path.stem  # filename without extension
    normalized = _normalize_name(name)
    tokens = _tokenize(normalized)
    core_tokens = _strip_suffix_tokens(tokens)
    return core_tokens


def compute_token_overlap(tokens1: List[str], tokens2: List[str]) -> float:
    """
    Compute token overlap ratio between two token lists.
    
    Returns:
        Overlap ratio from 0.0 to 1.0
    """
    if not tokens1 or not tokens2:
        return 0.0
    
    set1 = set(tokens1)
    set2 = set(tokens2)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def extract_file_signals(
    file_path: Path,
    project_flp_path: Optional[Path] = None,
    reference_mtime: Optional[int] = None,
    duration: Optional[float] = None,
    bpm: Optional[float] = None,
    key: Optional[str] = None,
    previously_seen_fingerprint: Optional[str] = None
) -> List[FileSignal]:
    """
    Extract all relevant signals from a file.
    
    Args:
        file_path: Path to the file
        project_flp_path: Optional FLP path for name token comparison
        reference_mtime: Optional reference mtime for delta calculation
        duration: Optional audio duration in seconds
        bpm: Optional detected BPM
        key: Optional detected key
        previously_seen_fingerprint: Optional fingerprint if file was seen before
        
    Returns:
        List of FileSignal objects
    """
    signals = []
    
    try:
        stat = file_path.stat()
        file_size = stat.st_size
        file_mtime = int(stat.st_mtime)
        file_ext = file_path.suffix.lower()
        
        # 1. Name tokens signal (weight 40)
        name_tokens = extract_name_tokens(file_path)
        if name_tokens:
            signals.append(FileSignal(
                signal_type=SignalType.NAME_TOKENS,
                value_text=" ".join(name_tokens),
                weight=40
            ))
        
        # 2. Mtime delta signal (weight up to 30)
        if reference_mtime is not None:
            delta_seconds = abs(file_mtime - reference_mtime)
            signals.append(FileSignal(
                signal_type=SignalType.MTIME_DELTA,
                value_num=delta_seconds,
                weight=30 if delta_seconds <= 3600 else (15 if delta_seconds <= 86400 else 5)
            ))
        
        # 3. Duration signal (optional, weight 10)
        if duration is not None:
            signals.append(FileSignal(
                signal_type=SignalType.DURATION,
                value_num=duration,
                weight=10
            ))
        
        # 4. BPM signal (optional, weight 15)
        if bpm is not None:
            signals.append(FileSignal(
                signal_type=SignalType.BPM,
                value_num=bpm,
                weight=15
            ))
        
        # 5. Key signal (optional, weight 10)
        if key is not None:
            signals.append(FileSignal(
                signal_type=SignalType.KEY,
                value_text=key,
                weight=10
            ))
        
        # 6. Previously seen fingerprint (weight 40)
        if previously_seen_fingerprint:
            signals.append(FileSignal(
                signal_type=SignalType.PREVIOUSLY_SEEN_FINGERPRINT,
                value_text=previously_seen_fingerprint,
                weight=40
            ))
        
        # 7. File size signal (weight 5)
        signals.append(FileSignal(
            signal_type=SignalType.FILE_SIZE,
            value_num=file_size,
            weight=5
        ))
        
        # 8. File extension signal (weight 5)
        signals.append(FileSignal(
            signal_type=SignalType.FILE_EXT,
            value_text=file_ext,
            weight=5
        ))
        
    except Exception as e:
        logger.warning(f"Error extracting signals from {file_path}: {e}")
    
    return signals
