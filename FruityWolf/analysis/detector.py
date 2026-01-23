"""
BPM and Key Detection

Audio analysis for tempo and musical key detection.
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QThread

from ..database import execute

logger = logging.getLogger(__name__)

# Musical keys
KEYS = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
    'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm',
]

# Camelot wheel mapping (for DJ mixing)
CAMELOT_MAPPING = {
    'C': '8B', 'Am': '8A',
    'G': '9B', 'Em': '9A',
    'D': '10B', 'Bm': '10A',
    'A': '11B', 'F#m': '11A',
    'E': '12B', 'C#m': '12A',
    'B': '1B', 'G#m': '1A',
    'F#': '2B', 'D#m': '2A',
    'Db': '3B', 'Bbm': '3A',
    'Ab': '4B', 'Fm': '4A',
    'Eb': '5B', 'Cm': '5A',
    'Bb': '6B', 'Gm': '6A',
    'F': '7B', 'Dm': '7A',
}


@dataclass
class AnalysisResult:
    """Result of audio analysis."""
    bpm: Optional[float] = None
    bpm_confidence: Optional[float] = None
    key: Optional[str] = None
    key_confidence: Optional[float] = None
    duration: Optional[float] = None
    error: Optional[str] = None


def analyze_bpm_simple(audio_path: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Simple BPM detection using onset detection.
    
    Returns (bpm, confidence) tuple.
    """
    try:
        import numpy as np
        import soundfile as sf
        from scipy import signal
        
        # Load audio
        data, sample_rate = sf.read(audio_path, dtype='float32')
        
        # Convert to mono
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Limit to first 60 seconds for speed
        max_samples = sample_rate * 60
        if len(data) > max_samples:
            data = data[:max_samples]
        
        # Compute envelope using RMS
        frame_size = int(sample_rate * 0.02)  # 20ms frames
        hop_size = frame_size // 2
        
        num_frames = (len(data) - frame_size) // hop_size + 1
        envelope = np.zeros(num_frames)
        
        for i in range(num_frames):
            start = i * hop_size
            frame = data[start:start + frame_size]
            envelope[i] = np.sqrt(np.mean(frame ** 2))
        
        # Compute onset strength (derivative of envelope)
        onset_env = np.diff(envelope)
        onset_env = np.maximum(0, onset_env)
        
        # Autocorrelation for tempo
        min_bpm = 60
        max_bpm = 200
        
        # Convert BPM range to lag samples
        sr_env = sample_rate / hop_size
        min_lag = int(60 * sr_env / max_bpm)
        max_lag = int(60 * sr_env / min_bpm)
        
        # Compute autocorrelation
        autocorr = np.correlate(onset_env, onset_env, mode='full')
        autocorr = autocorr[len(autocorr) // 2:]
        
        # Find peaks in valid range
        if max_lag > len(autocorr):
            max_lag = len(autocorr) - 1
        
        valid_autocorr = autocorr[min_lag:max_lag]
        if len(valid_autocorr) == 0:
            return None, None
        
        peak_idx = np.argmax(valid_autocorr) + min_lag
        
        # Convert lag to BPM
        bpm = 60 * sr_env / peak_idx
        
        # Estimate confidence
        peak_val = autocorr[peak_idx]
        mean_val = np.mean(valid_autocorr)
        confidence = min(1.0, (peak_val / mean_val - 1) / 2) if mean_val > 0 else 0.5
        
        return round(bpm, 1), round(confidence, 2)
        
    except Exception as e:
        logger.error(f"BPM detection failed for {audio_path}: {e}")
        return None, None


def analyze_bpm_librosa(audio_path: str) -> Tuple[Optional[float], Optional[float]]:
    """
    BPM detection using librosa (more accurate but slower).
    
    Returns (bpm, confidence) tuple.
    """
    try:
        import librosa
        import numpy as np
        
        # Load audio (limit to 60 seconds)
        y, sr = librosa.load(audio_path, duration=60, sr=22050)
        
        # Detect tempo
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        
        # Estimate confidence based on beat strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        pulse = librosa.beat.plp(onset_envelope=onset_env, sr=sr)
        confidence = min(1.0, np.max(pulse) * 2)
        
        return round(float(tempo), 1), round(float(confidence), 2)
        
    except ImportError:
        logger.warning("librosa not available, using simple BPM detection")
        return analyze_bpm_simple(audio_path)
    except Exception as e:
        logger.error(f"librosa BPM detection failed: {e}")
        return analyze_bpm_simple(audio_path)


def analyze_key_simple(audio_path: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Simple key detection using chroma features.
    
    Returns (key, confidence) tuple.
    """
    try:
        import numpy as np
        import soundfile as sf
        from scipy.fft import fft
        
        # Load audio
        data, sample_rate = sf.read(audio_path, dtype='float32')
        
        # Convert to mono
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Use middle section for analysis
        start = len(data) // 4
        end = 3 * len(data) // 4
        data = data[start:end]
        
        # Limit to 30 seconds
        max_samples = sample_rate * 30
        if len(data) > max_samples:
            data = data[:max_samples]
        
        # Compute chroma features using FFT
        frame_size = 4096
        hop_size = frame_size // 2
        
        chroma_sum = np.zeros(12)
        num_frames = 0
        
        for i in range(0, len(data) - frame_size, hop_size):
            frame = data[i:i + frame_size] * np.hanning(frame_size)
            spectrum = np.abs(fft(frame)[:frame_size // 2])
            
            # Map frequencies to chroma
            for bin_idx, magnitude in enumerate(spectrum):
                freq = bin_idx * sample_rate / frame_size
                if freq < 65 or freq > 2000:  # Focus on relevant range
                    continue
                
                # Convert frequency to MIDI note and then to chroma
                midi = 12 * np.log2(freq / 440) + 69
                chroma_idx = int(round(midi)) % 12
                chroma_sum[chroma_idx] += magnitude
            
            num_frames += 1
        
        if num_frames == 0:
            return None, None
        
        # Normalize
        chroma = chroma_sum / num_frames
        chroma = chroma / (np.max(chroma) + 1e-10)
        
        # Key profiles (Krumhansl-Kessler)
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # Correlate with all keys
        correlations = []
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        for i in range(12):
            # Rotate chroma to align with key
            rotated = np.roll(chroma, -i)
            
            # Major correlation
            major_corr = np.corrcoef(rotated, major_profile)[0, 1]
            correlations.append((f"{key_names[i]}", major_corr, 'major'))
            
            # Minor correlation
            minor_corr = np.corrcoef(rotated, minor_profile)[0, 1]
            correlations.append((f"{key_names[i]}m", minor_corr, 'minor'))
        
        # Find best match
        best = max(correlations, key=lambda x: x[1])
        key = best[0]
        confidence = max(0, min(1, (best[1] + 1) / 2))  # Normalize to 0-1
        
        return key, round(confidence, 2)
        
    except Exception as e:
        logger.error(f"Key detection failed for {audio_path}: {e}")
        return None, None


def analyze_key_librosa(audio_path: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Key detection using librosa (more accurate).
    
    Returns (key, confidence) tuple.
    """
    try:
        import librosa
        import numpy as np
        
        # Load audio
        y, sr = librosa.load(audio_path, duration=30, sr=22050)
        
        # Compute chroma
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Key profiles (Krumhansl-Kessler)
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        major_profile = major_profile / np.linalg.norm(major_profile)
        minor_profile = minor_profile / np.linalg.norm(minor_profile)
        chroma_norm = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-10)
        
        # Correlate with all keys
        correlations = []
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        for i in range(12):
            rotated = np.roll(chroma_norm, -i)
            major_corr = np.dot(rotated, major_profile)
            minor_corr = np.dot(rotated, minor_profile)
            
            correlations.append((key_names[i], major_corr))
            correlations.append((f"{key_names[i]}m", minor_corr))
        
        best = max(correlations, key=lambda x: x[1])
        confidence = max(0, min(1, best[1]))
        
        return best[0], round(float(confidence), 2)
        
    except ImportError:
        logger.warning("librosa not available, using simple key detection")
        return analyze_key_simple(audio_path)
    except Exception as e:
        logger.error(f"librosa key detection failed: {e}")
        return analyze_key_simple(audio_path)


def analyze_audio(audio_path: str, use_librosa: bool = True) -> AnalysisResult:
    """
    Perform full audio analysis (BPM + Key).
    
    Args:
        audio_path: Path to audio file
        use_librosa: Use librosa if available (more accurate but slower)
    
    Returns:
        AnalysisResult with detected values
    """
    result = AnalysisResult()
    
    try:
        import soundfile as sf
        
        # Get duration
        info = sf.info(audio_path)
        result.duration = info.duration
        
    except Exception as e:
        result.error = f"Failed to read audio info: {e}"
        return result
    
    # BPM detection
    if use_librosa:
        result.bpm, result.bpm_confidence = analyze_bpm_librosa(audio_path)
    else:
        result.bpm, result.bpm_confidence = analyze_bpm_simple(audio_path)
    
    # Key detection
    if use_librosa:
        result.key, result.key_confidence = analyze_key_librosa(audio_path)
    else:
        result.key, result.key_confidence = analyze_key_simple(audio_path)
    
    return result


class AnalyzerThread(QThread):
    """Thread for audio analysis."""
    
    finished = Signal(object)  # AnalysisResult
    error = Signal(str)
    
    def __init__(self, audio_path: str, track_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.track_id = track_id
    
    def run(self):
        try:
            result = analyze_audio(self.audio_path)
            
            # Update database if track_id provided
            if self.track_id and not result.error:
                execute(
                    """UPDATE tracks SET
                       bpm_detected = ?, bpm_confidence = ?,
                       key_detected = ?, key_confidence = ?,
                       duration = ?, updated_at = strftime('%s', 'now')
                       WHERE id = ?""",
                    (
                        result.bpm, result.bpm_confidence,
                        result.key, result.key_confidence,
                        result.duration, self.track_id
                    )
                )
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.exception(f"Analysis thread error for {self.audio_path}")
            self.error.emit(str(e))


def get_camelot(key: str) -> Optional[str]:
    """Get Camelot wheel notation for a key."""
    return CAMELOT_MAPPING.get(key)


def format_bpm(bpm: Optional[float]) -> str:
    """Format BPM for display."""
    if bpm is None:
        return '--'
    return f"{bpm:.0f}"


def format_key(key: Optional[str], show_camelot: bool = False) -> str:
    """Format key for display."""
    if key is None:
        return '--'
    if show_camelot:
        camelot = get_camelot(key)
        return f"{key} ({camelot})" if camelot else key
    return key
