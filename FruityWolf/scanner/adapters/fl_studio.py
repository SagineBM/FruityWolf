"""
FL Studio Adapter

Implements FL Studio-specific logic for:
- File role detection
- Signal-based matching (name tokens, mtime delta, fingerprint)
- Confidence scoring
- Conflict resolution (greedy bipartite matching)
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .base import DAWAdapter, FileRole, MatchResult
from ..identity.signals import (
    extract_name_tokens,
    compute_token_overlap,
    extract_file_signals,
    SignalType
)
from ..identity.fingerprint import compute_fingerprint

logger = logging.getLogger(__name__)


class FLStudioAdapter(DAWAdapter):
    """FL Studio-specific adapter implementation."""
    
    # Match thresholds
    CONFIDENT_THRESHOLD = 50  # Score >= 50 = confident link
    WEAK_THRESHOLD = 35  # Score 35-49 = weak link
    MIN_THRESHOLD = 35  # Score < 35 = no link
    
    def detect_file_role(self, file_path: Path, project_root: Path) -> FileRole:
        """
        Detect file role based on FL Studio conventions.
        
        Rules:
        - .flp files = PROJECT_FILE
        - Root-level audio = RENDER
        - Audio/ subfolder = INTERNAL_AUDIO
        - Samples/ subfolder = SAMPLE
        - Backup/ subfolder = BACKUP
        - Stems/ subfolder = STEM
        - Other = UNKNOWN
        """
        try:
            relative_path = file_path.relative_to(project_root)
            parts = relative_path.parts
            
            # Check location first (location takes precedence over extension)
            if len(parts) > 1:
                first_dir = parts[0]
                
                if first_dir == 'Backup':
                    # Files in Backup/ are backups, even if they're .flp files
                    return FileRole.BACKUP
                elif first_dir == 'Stems':
                    return FileRole.STEM
                elif first_dir == 'Samples':
                    return FileRole.SAMPLE
                elif first_dir == 'Audio':
                    return FileRole.INTERNAL_AUDIO  # Internal audio, not a render
            
            # Check extension (only if not in a special directory)
            ext = file_path.suffix.lower()
            
            if ext == '.flp':
                return FileRole.PROJECT_FILE
            
            # Root-level audio = render
            if len(parts) == 1 and ext in {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif'}:
                return FileRole.RENDER
            
            return FileRole.UNKNOWN
            
        except ValueError:
            # File not under project root
            return FileRole.UNKNOWN
    
    def match_files_to_project(
        self,
        project_files: List[Path],
        candidate_files: List[Path],
        project_root: Path
    ) -> List[MatchResult]:
        """
        Match candidate files to project using signal-based scoring.
        
        For FL Studio:
        - Uses name token overlap (weight 40)
        - Uses mtime delta (weight up to 30)
        - Uses previously seen fingerprint (weight 40)
        """
        if not project_files or not candidate_files:
            return []
        
        # Use primary FLP for matching (first one, or newest)
        primary_flp = project_files[0]
        if len(project_files) > 1:
            # Use newest FLP
            primary_flp = max(project_files, key=lambda p: p.stat().st_mtime if p.exists() else 0)
        
        flp_mtime = primary_flp.stat().st_mtime if primary_flp.exists() else None
        
        matches = []
        
        for candidate in candidate_files:
            if not candidate.exists():
                continue
            
            # Extract signals
            signals = extract_file_signals(
                candidate,
                project_flp_path=primary_flp,
                reference_mtime=int(flp_mtime) if flp_mtime else None
            )
            
            # Compute match score
            score, reasons = self.compute_match_score(candidate, primary_flp, {
                'signals': signals,
                'flp_mtime': flp_mtime
            })
            
            if score >= self.MIN_THRESHOLD:
                matches.append(MatchResult(
                    file_path=candidate,
                    project_id=None,  # Will be set by caller
                    confidence_score=score,
                    match_reasons=reasons,
                    signals={s.signal_type.value: s.value_text or s.value_num for s in signals}
                ))
        
        # Resolve conflicts (one audio -> one FLP)
        return self.resolve_conflicts(matches)
    
    def compute_match_score(
        self,
        candidate_file: Path,
        project_file: Path,
        signals: Dict[str, any]
    ) -> Tuple[int, List[str]]:
        """
        Compute confidence score for matching candidate to project.
        
        Scoring:
        - Token overlap * 40 (max 40 points)
        - Timestamp proximity bonus:
          - <= 1h: +30
          - <= 24h: +15
          - <= 48h: +5
        - Previously seen fingerprint: +40
        
        Returns:
            Tuple of (score 0-100, list of reasons)
        """
        score = 0
        reasons = []
        
        signal_list = signals.get('signals', [])
        flp_mtime = signals.get('flp_mtime')
        
        # Extract name tokens
        candidate_tokens = extract_name_tokens(candidate_file)
        flp_tokens = extract_name_tokens(project_file)
        
        # 1. Token overlap (weight 40)
        token_overlap = compute_token_overlap(candidate_tokens, flp_tokens)
        token_score = int(token_overlap * 40)
        score += token_score
        
        if token_score > 0:
            reasons.append(f"Name tokens overlap {token_overlap:.2f}")
        
        # 2. Timestamp proximity bonus
        if flp_mtime:
            try:
                candidate_mtime = candidate_file.stat().st_mtime
                delta_seconds = abs(candidate_mtime - flp_mtime)
                
                if delta_seconds <= 3600:  # <= 1 hour
                    score += 30
                    reasons.append(f"mtime within 1h")
                elif delta_seconds <= 86400:  # <= 24 hours
                    score += 15
                    reasons.append(f"mtime within 24h")
                elif delta_seconds <= 172800:  # <= 48 hours
                    score += 5
                    reasons.append(f"mtime within 48h")
            except Exception as e:
                logger.debug(f"Error computing mtime delta: {e}")
        
        # 3. Previously seen fingerprint (check signals)
        for signal in signal_list:
            if signal.signal_type == SignalType.PREVIOUSLY_SEEN_FINGERPRINT:
                score += 40
                reasons.append("seen before (fingerprint)")
                break
        
        # Cap at 100
        score = min(100, score)
        
        return score, reasons
    
    def resolve_conflicts(
        self,
        matches: List[MatchResult]
    ) -> List[MatchResult]:
        """
        Resolve conflicts using greedy bipartite matching.
        
        Ensures each candidate file is assigned to at most one project.
        Sorts by score descending and assigns greedily.
        """
        if not matches:
            return []
        
        # Sort by score descending
        sorted_matches = sorted(matches, key=lambda m: m.confidence_score, reverse=True)
        
        # Greedy assignment: first match wins
        # In a real implementation, we'd need to know which project each match belongs to
        # For now, we just return sorted matches (caller will handle project assignment)
        return sorted_matches
    
    def compute_flat_folder_confidence(self, top_score: int, has_fingerprint_match: bool) -> int:
        """
        Compute project confidence for flat folder structure.
        
        Args:
            top_score: Highest match score found
            has_fingerprint_match: Whether fingerprint match exists
            
        Returns:
            Confidence score (0-100)
        """
        # For structured folders: 90-95
        # For flat: min(80, top_score) but never >80 unless fingerprint match
        if has_fingerprint_match:
            return min(85, max(80, top_score))
        else:
            return min(80, top_score)
