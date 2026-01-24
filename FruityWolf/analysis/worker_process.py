"""
Worker Process for Audio Analysis

Runs audio analysis in a separate process to avoid GIL locking the main UI.
Usage: python -m FruityWolf.analysis.worker_process --input "path/to/audio.wav" --json
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parents[2]))

from FruityWolf.analysis.detector import analyze_audio

def main():
    parser = argparse.ArgumentParser(description="Audio Analysis Worker")
    parser.add_argument("--input", required=True, help="Path to audio file")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        result = {"error": "File not found"}
        print(json.dumps(result))
        sys.exit(1)
        
    try:
        # Perform analysis (using librosa if available)
        analysis = analyze_audio(args.input, use_librosa=True)
        
        # Serialize
        result = {
            "bpm": analysis.bpm,
            "bpm_confidence": analysis.bpm_confidence,
            "key": analysis.key,
            "key_confidence": analysis.key_confidence,
            "duration": analysis.duration,
            "error": analysis.error
        }
        
        if args.json:
            print(json.dumps(result))
            
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
