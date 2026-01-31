"""
DAW Adapters for Multi-DAW Support

Provides adapter pattern for different DAWs (FL Studio, Studio One, Logic, etc.).
Each adapter implements signal-based matching and attribution logic.
"""

from .base import DAWAdapter, FileRole, MatchResult
from .fl_studio import FLStudioAdapter

__all__ = [
    'DAWAdapter',
    'FileRole',
    'MatchResult',
    'FLStudioAdapter',
]

# Registry of available adapters
ADAPTERS = {
    'fl_studio': FLStudioAdapter,
    # Future: 'studio_one': StudioOneAdapter,
    # Future: 'logic': LogicAdapter,
}


def get_adapter(daw_type: str) -> DAWAdapter:
    """
    Get adapter for a DAW type.
    
    Args:
        daw_type: DAW type string (e.g., 'fl_studio')
        
    Returns:
        DAWAdapter instance
    """
    adapter_class = ADAPTERS.get(daw_type, FLStudioAdapter)  # Default to FL Studio
    return adapter_class()
