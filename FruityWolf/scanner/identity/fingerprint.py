"""
Fast Fingerprinting for File Identification

Provides fast fingerprint computation using first 64KB + metadata,
and optional full hash computation for exact matching.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Size of file chunk to read for fast fingerprinting (64KB)
FINGERPRINT_CHUNK_SIZE = 64 * 1024


def compute_fingerprint(file_path: Path) -> Optional[str]:
    """
    Compute a fast fingerprint for a file.
    
    Uses SHA256 of:
    - First 64KB of file content
    - File size
    - File mtime (modification time)
    
    This is fast enough to run during scanning without blocking.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hex string of SHA256 hash (32 bytes = 64 hex chars), or None if error
    """
    try:
        stat = file_path.stat()
        file_size = stat.st_size
        mtime = int(stat.st_mtime)
        
        # Read first chunk (up to 64KB)
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(FINGERPRINT_CHUNK_SIZE)
                hasher.update(chunk)
        except (IOError, OSError) as e:
            logger.warning(f"Error reading {file_path} for fingerprint: {e}")
            return None
        
        # Add metadata to hash
        hasher.update(str(file_size).encode('utf-8'))
        hasher.update(str(mtime).encode('utf-8'))
        
        return hasher.hexdigest()
        
    except Exception as e:
        logger.warning(f"Error computing fingerprint for {file_path}: {e}")
        return None


def compute_full_hash(file_path: Path) -> Optional[str]:
    """
    Compute full SHA256 hash of file content.
    
    WARNING: This reads the entire file and should NOT be called during scanning.
    Use only for on-demand exact matching or when fingerprint is insufficient.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hex string of SHA256 hash, or None if error
    """
    try:
        hasher = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            while True:
                chunk = f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                hasher.update(chunk)
        
        return hasher.hexdigest()
        
    except Exception as e:
        logger.warning(f"Error computing full hash for {file_path}: {e}")
        return None
