"""
Path Utilities for FruityWolf.
"""

import os
import logging
from typing import Optional
from PySide6.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)

def resolve_fl_path(path: str, project_path: Optional[str] = None) -> str:
    r"""
    Expand FL Studio specific environment variables and handle project-local lookups.
    Example: %FLStudioFactoryData% -> C:\Program Files\...\FL Studio\Data
    """
    if not path:
        return path
        
    resolved = path
    
    # 1. Project-local lookup (Prioritize user feedback: "samples are always on the folder called sample on the project folder")
    if project_path and os.path.isdir(project_path):
        filename = os.path.basename(path)
        # Check standard locations in project
        candidates = [
            os.path.join(project_path, "Samples", filename),
            os.path.join(project_path, "Audio", filename),
            os.path.join(project_path, filename)
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

    # 2. Expand environment variables
    if '%' in resolved:
        # Try standard expansion first
        resolved = os.path.expandvars(resolved)
        
        # If expansion didn't happen (still has %), try manual lookup from settings
        if '%' in resolved:
            try:
                from ..database import get_setting
                fl_base = get_setting('fl_studio_path')
                if fl_base:
                    # Replace both variants
                    resolved = resolved.replace('%FLStudioFactoryData%', fl_base)
                    resolved = resolved.replace('%FLSTUDIOFACTORYDATA%', fl_base)
            except:
                pass
            
    return resolved

def validate_path(
    path: Optional[str], 
    context: str = "File", 
    parent_widget: Optional[QWidget] = None,
    show_error: bool = True,
    project_path: Optional[str] = None
) -> bool:
    """
    Strict path validation with FL Studio variable resolution and project context.
    """
    if not path:
        logger.warning(f"{context} path is empty or None")
        if show_error and parent_widget:
             QMessageBox.warning(parent_widget, "Empty Path", f"{context} path is missing.")
        return False
        
    resolved_path = resolve_fl_path(path, project_path)
    if not os.path.exists(resolved_path):
        # Only log warnings when explicitly showing errors to user
        # When show_error=False, use debug level to avoid noise
        if show_error:
            logger.warning(f"{context} not found: {resolved_path}")
        else:
            logger.debug(f"{context} not found: {resolved_path}")
        if show_error and parent_widget:
            QMessageBox.warning(
                parent_widget, 
                "Not Found", 
                f"Could not find {context.lower()}:\n{os.path.basename(resolved_path)}\n\nIt may have been moved or deleted."
            )
        return False
        
    return True

def is_valid_path(path: Optional[str]) -> bool:
    """Quick check for existence without logging or UI."""
    if not path:
        return False
    return os.path.exists(resolve_fl_path(path))
