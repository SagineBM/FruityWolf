"""
Identity Layer for Project File Tracking

This module provides identity-first scanning capabilities:
- Fast fingerprinting for file identification
- Signal-based matching and attribution
- Project identity (PID) management
- Metadata drift prevention
"""

from .fingerprint import compute_fingerprint, compute_full_hash
from .signals import extract_file_signals, SignalType
from .identity_store import IdentityStore

__all__ = [
    'compute_fingerprint',
    'compute_full_hash',
    'extract_file_signals',
    'SignalType',
    'IdentityStore',
]
