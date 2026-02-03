"""
Backup Exclusion Module

Provides mandatory exclusion rules for FL Studio project rendering.
Ensures no backup, autosave, or recovery files are ever rendered.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Case-insensitive folder names to exclude
EXCLUDED_FOLDERS = {
    'backup', 'backups', 
    'auto-save', 'autosave', 
    'recovered', 'recovery',
    'temp', 'trash', 'old',
    'history', 'sliced audio', 'rendered audio'
}

# Case-insensitive filename patterns to exclude (glob style)
EXCLUDED_PATTERNS = [
    '*backup*', 
    '*autosave*', 
    '*auto-save*', 
    '*recovery*',
    '*restored*'
]

def is_eligible_flp(flp_path: Path) -> bool:
    """
    Check if an FLP file is eligible for rendering.
    
    Returns False if:
    - Path is not a .flp file
    - Path is inside an excluded folder (Backup, Autosave, etc.)
    - Filename matches excluded patterns (backup, autosave, etc.)
    """
    if not flp_path or flp_path.suffix.lower() != '.flp':
        return False
        
    # Check parent folders
    try:
        parts = flp_path.parent.parts
        for part in parts:
            if part.lower() in EXCLUDED_FOLDERS:
                return False
    except Exception as e:
        logger.error(f"Error checking folder exclusions for {flp_path}: {e}")
        return False
        
    # Check filename patterns
    name = flp_path.name.lower()
    for pattern in EXCLUDED_PATTERNS:
        # Simple wildcard matching
        if _match_pattern(name, pattern):
            return False
            
    return True

def _match_pattern(name: str, pattern: str) -> bool:
    """Simple glob match helper."""
    import fnmatch
    return fnmatch.fnmatch(name, pattern)
