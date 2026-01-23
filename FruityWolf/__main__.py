"""
FL Library Pro — Entry Point

Run with: python -m FruityWolf
"""

import sys
import os

# Add parent directory to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.app import main

if __name__ == "__main__":
    sys.exit(main())
