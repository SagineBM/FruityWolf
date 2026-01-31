"""
Base DAW Adapter Interface

Defines the contract for DAW-specific adapters that handle:
- File role detection
- Signal-based matching
- Confidence scoring
- Conflict resolution
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FileRole(Enum):
    """File roles in a DAW project."""
    PROJECT_FILE = "flp"  # Main project file (FLP, .song, etc.)
    RENDER = "render"  # Audio render/export
    BACKUP = "backup"  # Backup file
    STEM = "stem"  # Stem export
    SAMPLE = "sample"  # Source sample
    INTERNAL_AUDIO = "internal_audio"  # Internal audio (Audio/ subfolder)
    UNKNOWN = "unknown"  # Unknown role


@dataclass
class MatchResult:
    """Result of matching a file to a project."""
    file_path: Path
    project_id: Optional[int]  # None if new project
    confidence_score: int  # 0-100
    match_reasons: List[str]  # Human-readable reasons for match
    signals: Dict[str, any]  # Signal data used for matching


class DAWAdapter(ABC):
    """Base class for DAW-specific adapters."""
    
    @abstractmethod
    def detect_file_role(self, file_path: Path, project_root: Path) -> FileRole:
        """
        Detect the role of a file within a project.
        
        Args:
            file_path: Path to the file
            project_root: Root directory of the project
            
        Returns:
            FileRole enum value
        """
        pass
    
    @abstractmethod
    def match_files_to_project(
        self,
        project_files: List[Path],
        candidate_files: List[Path],
        project_root: Path
    ) -> List[MatchResult]:
        """
        Match candidate files to a project using signal-based scoring.
        
        Args:
            project_files: List of known project files (e.g., FLP files)
            candidate_files: List of candidate files to match (e.g., audio renders)
            project_root: Root directory of the project
            
        Returns:
            List of MatchResult objects
        """
        pass
    
    @abstractmethod
    def compute_match_score(
        self,
        candidate_file: Path,
        project_file: Path,
        signals: Dict[str, any]
    ) -> Tuple[int, List[str]]:
        """
        Compute confidence score for matching a candidate file to a project file.
        
        Args:
            candidate_file: Path to candidate file
            project_file: Path to project file (e.g., FLP)
            signals: Dictionary of signal data
            
        Returns:
            Tuple of (confidence_score, match_reasons)
        """
        pass
    
    @abstractmethod
    def resolve_conflicts(
        self,
        matches: List[MatchResult]
    ) -> List[MatchResult]:
        """
        Resolve conflicts when multiple candidates match the same project.
        Ensures one-to-one mapping where possible.
        
        Args:
            matches: List of match results (may have conflicts)
            
        Returns:
            List of resolved match results
        """
        pass
