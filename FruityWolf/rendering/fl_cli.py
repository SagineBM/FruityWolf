"""
FL Studio CLI Integration

Handles resolution of FL Studio executable and construction of CLI arguments.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

from ..database import get_setting

logger = logging.getLogger(__name__)

def resolve_fl_executable() -> Optional[Path]:
    """
    Resolve the path to FL Studio 64-bit executable.
    
    Checks:
    1. Setting 'fl_studio_path'
    2. If setting is a directory, looks for FL64.exe inside
    
    Returns:
        Path to FL64.exe or None if not found/invalid.
    """
    path_str = get_setting('fl_studio_path')
    if not path_str:
        return None
        
    path = Path(path_str)
    
    if not path.exists():
        return None
        
    # If it's the exe itself
    if path.is_file() and path.name.lower() == 'fl64.exe':
        return path
        
    # If it's the directory
    if path.is_dir():
        exe_path = path / 'FL64.exe'
        if exe_path.exists():
            return exe_path
            
    return None

def build_render_argv(
    fl_exe: Path, 
    flp_path: Path, 
    format_type: str = 'mp3',
    job_type: str = 'audio'
) -> List[str]:
    """
    Build the command line arguments for FL Studio rendering.
    
    Args:
        fl_exe: Path to FL64.exe
        flp_path: Path to project file
        format_type: 'mp3' or 'wav' (only for audio job_type)
        job_type: 'audio', 'midi', or 'zip'
        
    Returns:
        List of command line arguments
    """
    args = [str(fl_exe)]
    
    # Verify FLP exists (sanity check)
    if not flp_path.exists():
        raise FileNotFoundError(f"Project file not found: {flp_path}")
        
    if job_type == 'audio':
        # Audio Render: /Emp3 or /Ewav
        if format_type.lower() == 'wav':
            args.append('/Ewav')
        else:
            args.append('/Emp3')
            
        # /R command implies "Render project file"
        args.append('/R')
        args.append(str(flp_path))
        
    elif job_type == 'midi':
        # MIDI Export: /M
        args.append(f'/M"{str(flp_path)}"')
        
    elif job_type == 'zip':
        # ZIP Export: /Z
        args.append(f'/Z"{str(flp_path)}"')
        
    else:
        raise ValueError(f"Unknown job_type: {job_type}")
        
    return args

def get_expected_preview_path(flp_path: Path, format_type: str = 'mp3') -> Path:
    """
    Get the path where FL Studio writes the render (default behavior).
    Same folder and stem as the FLP, only the extension changes: .mp3 or .wav.
    Example: F:\\...\\khassni nfeya9fateen.flp -> F:\\...\\khassni nfeya9fateen.mp3
    """
    ext = format_type.lower().lstrip('.')
    return flp_path.with_suffix(f'.{ext}')

def get_expected_output_path(flp_path: Path, job_type: str = 'audio', format_type: str = 'mp3') -> Path:
    """
    Get the path where FL Studio writes the render (default behavior).
    - Audio: same path as FLP, extension .mp3 or .wav
    - MIDI:  same folder, {stem}.mid
    - ZIP:   same folder, {stem}.zip
    """
    if job_type == 'audio':
        return get_expected_preview_path(flp_path, format_type)
    stem = flp_path.stem
    parent = flp_path.parent
    if job_type == 'midi':
        return parent / f"{stem}.mid"
    if job_type == 'zip':
        return parent / f"{stem}.zip"
    raise ValueError(f"Unknown job_type: {job_type}")
