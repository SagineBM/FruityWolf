"""
Check if render files exist in a project folder.
Run: python scripts/check_project_files.py "komnditih"
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query_one
from FruityWolf.scanner.fl_render_classifier import find_project_renders, RENDER_EXTENSIONS

def main():
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_row = query_one("SELECT * FROM projects WHERE name LIKE ?", (f"%{project_name}%",))
        if not project_row:
            print(f"Project '{project_name}' not found")
            return
        
        project = dict(project_row)
        project_path = Path(project['path'])
    else:
        print("Usage: python scripts/check_project_files.py <project_name>")
        return
    
    print(f"\n=== Checking files in: {project_path} ===")
    
    if not project_path.exists():
        print(f"[ERROR] Project path does not exist: {project_path}")
        return
    
    # Use the same render detection logic as the scanner
    render_classifications = find_project_renders(project_path)
    renders = [Path(c.path) for c in render_classifications if c.classification == 'RENDER']
    
    print(f"\nFound {len(renders)} renders:")
    for r in renders:
        if r.exists():
            stat = r.stat()
            print(f"  [OK] {r.name} ({stat.st_size / 1024 / 1024:.2f} MB)")
            print(f"       Path: {r}")
        else:
            print(f"  [MISSING] {r.name} (FILE NOT FOUND)")
    
    # Also check all audio files in root
    print(f"\nAll audio files in root:")
    audio_files = []
    for item in project_path.iterdir():
        if item.is_file():
            ext = item.suffix.lower()
            if ext in RENDER_EXTENSIONS:
                audio_files.append(item)
                stat = item.stat()
                print(f"  {item.name} ({stat.st_size / 1024 / 1024:.2f} MB)")
    
    if not audio_files:
        print("  (none found)")
    
    # Check subdirectories
    print(f"\nSubdirectories:")
    for item in project_path.iterdir():
        if item.is_dir():
            print(f"  {item.name}/")

if __name__ == '__main__':
    main()
