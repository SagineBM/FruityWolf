"""
FLP Parser Module

Parses FL Studio project files (.flp) using PyFLP to extract 
plugins, samples, tempo, and other metadata.
"""

from .parser import FLPParser

__all__ = ['FLPParser']
