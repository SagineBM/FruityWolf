"""
Waveform Extraction and Caching

Extracts waveform peaks from audio files for Spotify-grade visualization.
Uses file signatures (path + size + mtime) for cache invalidation.
"""

import os
import logging
import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple, List
import numpy as np

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker

# Use core module for paths
try:
    from ..core import get_waveform_cache_path as get_waveform_cache_dir, WAVEFORM_BINS
except ImportError:
    from ..database import get_cache_path
    def get_waveform_cache_dir() -> Path:
        path = get_cache_path() / 'waveforms'
        path.mkdir(parents=True, exist_ok=True)
        return path
    WAVEFORM_BINS = 4000

from ..database import execute, query_one

logger = logging.getLogger(__name__)

# Waveform configuration
SAMPLES_PER_PIXEL = 256  # Audio samples per waveform pixel
TARGET_WIDTH = WAVEFORM_BINS  # Target waveform width in pixels (2000-8000 range)
MAX_CACHE_SIZE_MB = 500  # Maximum cache size

def get_file_signature(audio_path: str) -> str:
    """
    Generate a signature for a file based on path, size, and mtime.
    Used for cache invalidation.
    """
    try:
        stat = os.stat(audio_path)
        signature_data = f"{audio_path}|{stat.st_size}|{stat.st_mtime}"
        return hashlib.md5(signature_data.encode()).hexdigest()[:16]
    except OSError:
        # File doesn't exist or can't be accessed
        return hashlib.md5(audio_path.encode()).hexdigest()[:16]


def get_waveform_cache_path(audio_path: str) -> Path:
    """Get cache path for a waveform using file signature."""
    signature = get_file_signature(audio_path)
    filename = Path(audio_path).stem
    # Sanitize filename for filesystem safety
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")[:50]
    cache_file = f"{safe_name}_{signature}.npz"
    return get_waveform_cache_dir() / cache_file


def ensure_waveform_cache_dir():
    """Ensure waveform cache directory exists."""
    cache_dir = get_waveform_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def is_cache_valid(audio_path: str, cache_path: Path) -> bool:
    """
    Check if a cached waveform is still valid.
    Returns False if the source file has changed since caching.
    """
    if not cache_path.exists():
        return False
    
    # The cache filename includes the file signature,
    # so if the file changed, the cache path would be different
    expected_path = get_waveform_cache_path(audio_path)
    return cache_path == expected_path


class WaveformData:
    """Container for waveform peak data."""
    
    def __init__(self, peaks_min: np.ndarray, peaks_max: np.ndarray, sample_rate: int, duration: float):
        self.peaks_min = peaks_min
        self.peaks_max = peaks_max
        self.sample_rate = sample_rate
        self.duration = duration
        self.width = len(peaks_min)
    
    def get_peaks_for_range(self, start: float, end: float, width: int) -> Tuple[np.ndarray, np.ndarray]:
        """Get peaks for a time range, resampled to target width."""
        if self.duration <= 0 or width <= 0:
            return np.zeros(width), np.zeros(width)
        
        # Calculate sample indices
        start_idx = int((start / self.duration) * self.width)
        end_idx = int((end / self.duration) * self.width)
        
        start_idx = max(0, min(start_idx, self.width - 1))
        end_idx = max(start_idx + 1, min(end_idx, self.width))
        
        # Extract range
        range_min = self.peaks_min[start_idx:end_idx]
        range_max = self.peaks_max[start_idx:end_idx]
        
        if len(range_min) == 0:
            return np.zeros(width), np.zeros(width)
        
        # Resample to target width
        if len(range_min) != width:
            indices = np.linspace(0, len(range_min) - 1, width).astype(int)
            range_min = range_min[indices]
            range_max = range_max[indices]
        
        return range_min, range_max
    
    def save(self, path: Path):
        """Save waveform data to file."""
        ensure_waveform_cache_dir()
        np.savez_compressed(
            path,
            peaks_min=self.peaks_min,
            peaks_max=self.peaks_max,
            sample_rate=self.sample_rate,
            duration=self.duration,
        )
    
    @classmethod
    def load(cls, path: Path) -> Optional['WaveformData']:
        """Load waveform data from file."""
        try:
            if not path.exists():
                return None
            
            data = np.load(path)
            return cls(
                peaks_min=data['peaks_min'],
                peaks_max=data['peaks_max'],
                sample_rate=int(data['sample_rate']),
                duration=float(data['duration']),
            )
        except Exception as e:
            logger.error(f"Failed to load waveform cache: {e}")
            return None


def extract_waveform(audio_path: str, target_width: int = TARGET_WIDTH) -> Optional[WaveformData]:
    """
    Extract waveform peaks from an audio file.
    
    Returns min/max peaks for efficient rendering.
    """
    try:
        import soundfile as sf
        
        # Read audio file
        data, sample_rate = sf.read(audio_path, dtype='float32')
        
        # Convert stereo to mono
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        duration = len(data) / sample_rate
        
        # Calculate chunk size for target width
        chunk_size = max(1, len(data) // target_width)
        
        # Pad data to make it evenly divisible
        padded_length = ((len(data) + chunk_size - 1) // chunk_size) * chunk_size
        padded_data = np.zeros(padded_length, dtype=np.float32)
        padded_data[:len(data)] = data
        
        # Reshape and compute peaks
        reshaped = padded_data.reshape(-1, chunk_size)
        peaks_min = reshaped.min(axis=1)
        peaks_max = reshaped.max(axis=1)
        
        return WaveformData(peaks_min, peaks_max, sample_rate, duration)
        
    except ImportError:
        logger.error("soundfile not installed, cannot extract waveform")
        return None
    except Exception as e:
        logger.error(f"Failed to extract waveform from {audio_path}: {e}")
        return None


def get_or_extract_waveform(audio_path: str) -> Optional[WaveformData]:
    """Get waveform from cache or extract it."""
    cache_path = get_waveform_cache_path(audio_path)
    
    # Try to load from cache
    waveform = WaveformData.load(cache_path)
    if waveform:
        return waveform
    
    # Extract waveform
    waveform = extract_waveform(audio_path)
    if waveform:
        # Save to cache
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        waveform.save(cache_path.with_suffix('.npz'))
        
        # Update database
        execute(
            "UPDATE tracks SET waveform_cache_path = ? WHERE path = ?",
            (str(cache_path.with_suffix('.npz')), audio_path)
        )
    
    return waveform


class WaveformExtractor(QObject):
    """Background waveform extractor with progress signals."""
    
    progress = Signal(int, int)  # current, total
    finished = Signal(object)  # WaveformData or None
    error = Signal(str)
    
    def __init__(self, audio_path: str, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self._cancel = False
    
    def cancel(self):
        self._cancel = True
    
    def run(self):
        """Extract waveform (call from thread)."""
        try:
            waveform = get_or_extract_waveform(self.audio_path)
            if not self._cancel:
                self.finished.emit(waveform)
        except Exception as e:
            if not self._cancel:
                self.error.emit(str(e))


class WaveformThread(QThread):
    """Thread for waveform extraction."""
    
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, audio_path: str, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
    
    def run(self):
        try:
            waveform = get_or_extract_waveform(self.audio_path)
            self.finished.emit(waveform)
        except Exception as e:
            self.error.emit(str(e))


class WaveformCache:
    """
    LRU cache for waveform data.
    
    Keeps recently accessed waveforms in memory for fast access.
    """
    
    def __init__(self, max_items: int = 50):
        self.max_items = max_items
        self._cache: dict = {}
        self._access_order: List[str] = []
        self._mutex = QMutex()
    
    def get(self, audio_path: str) -> Optional[WaveformData]:
        """Get waveform from cache."""
        with QMutexLocker(self._mutex):
            if audio_path in self._cache:
                # Move to end of access order
                self._access_order.remove(audio_path)
                self._access_order.append(audio_path)
                return self._cache[audio_path]
        return None
    
    def put(self, audio_path: str, waveform: WaveformData):
        """Put waveform in cache."""
        with QMutexLocker(self._mutex):
            if audio_path in self._cache:
                self._access_order.remove(audio_path)
            elif len(self._cache) >= self.max_items:
                # Remove least recently used
                oldest = self._access_order.pop(0)
                del self._cache[oldest]
            
            self._cache[audio_path] = waveform
            self._access_order.append(audio_path)
    
    def clear(self):
        """Clear the cache."""
        with QMutexLocker(self._mutex):
            self._cache.clear()
            self._access_order.clear()


# Global waveform cache
_waveform_cache = WaveformCache()


def get_cached_waveform(audio_path: str) -> Optional[WaveformData]:
    """Get waveform from memory cache or disk."""
    # Check memory cache
    waveform = _waveform_cache.get(audio_path)
    if waveform:
        return waveform
    
    # Check disk cache
    cache_path = get_waveform_cache_path(audio_path).with_suffix('.npz')
    waveform = WaveformData.load(cache_path)
    if waveform:
        _waveform_cache.put(audio_path, waveform)
        return waveform
    
    return None


def cleanup_waveform_cache(max_size_mb: int = MAX_CACHE_SIZE_MB):
    """Clean up old waveform cache files if over size limit."""
    cache_dir = get_waveform_cache_dir()
    if not cache_dir.exists():
        return
    
    # Get all cache files with modification times
    files = []
    total_size = 0
    
    for f in cache_dir.glob('*.npz'):
        stat = f.stat()
        files.append((f, stat.st_mtime, stat.st_size))
        total_size += stat.st_size
    
    # Sort by modification time (oldest first)
    files.sort(key=lambda x: x[1])
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Remove oldest files until under limit
    while total_size > max_size_bytes and files:
        path, _, size = files.pop(0)
        try:
            path.unlink()
            total_size -= size
            logger.info(f"Removed old waveform cache: {path.name}")
        except Exception as e:
            logger.error(f"Failed to remove cache file {path}: {e}")
