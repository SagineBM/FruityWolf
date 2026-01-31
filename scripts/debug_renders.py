"""
Debug script to check render data for projects.
Run: python scripts/debug_renders.py "komnditih"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query, query_one, get_db
from FruityWolf.scanner.library_scanner import debug_project_renders

def main():
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        # Find project by name
        project_row = query_one("SELECT * FROM projects WHERE name LIKE ?", (f"%{project_name}%",))
        if not project_row:
            print(f"Project '{project_name}' not found")
            return
        
        # Convert Row to dict
        project = dict(project_row)
        project_id = project['id']
        print(f"\n=== Project: {project['name']} (ID: {project_id}) ===")
        print(f"Path: {project['path']}")
        print(f"State: {project.get('state_id', 'Unknown')}")
    else:
        # Get first project with "Preview Ready" status
        project_row = query_one("SELECT * FROM projects WHERE state_id LIKE '%PREVIEW%' LIMIT 1")
        if not project_row:
            print("No Preview Ready projects found")
            return
        
        # Convert Row to dict
        project = dict(project_row)
        project_id = project['id']
        print(f"\n=== Project: {project['name']} (ID: {project_id}) ===")
        print(f"Path: {project['path']}")
    
    # Get debug info
    debug_info = debug_project_renders(project_id)
    
    print(f"\nRenders table exists: {debug_info['renders_table_exists']}")
    print(f"Renders count: {debug_info['renders_count']}")
    print(f"Tracks count: {debug_info['tracks_count']}")
    
    if debug_info['renders']:
        print("\n=== RENDERS ===")
        for r in debug_info['renders']:
            print(f"  ID: {r['id']}, Path: {r['path']}")
            print(f"    Filename: {r.get('filename', 'N/A')}")
            print(f"    Duration: {r.get('duration_s', 0)}s")
            print(f"    Project ID: {r.get('project_id', 'N/A')}")
    else:
        print("\n=== NO RENDERS FOUND ===")
    
    if debug_info['tracks']:
        print("\n=== TRACKS ===")
        for t in debug_info['tracks'][:5]:  # Show first 5
            print(f"  ID: {t['id']}, Path: {t['path']}")
            print(f"    Render ID: {t.get('render_id', 'N/A')}")
    
    # Check render_count query directly
    print("\n=== DIRECT QUERY ===")
    render_count = query_one(
        "SELECT COUNT(*) as cnt FROM renders WHERE project_id = ?",
        (project_id,)
    )
    print(f"Direct COUNT query: {render_count['cnt'] if render_count else 0}")
    
    # Check if renders exist but with different project_id
    if debug_info['project']:
        project_path = debug_info['project'].get('path')
        if project_path:
            print(f"\n=== Checking renders by path ===")
            renders_by_path = query(
                "SELECT * FROM renders WHERE path LIKE ?",
                (f"%{os.path.basename(project_path)}%",)
            )
            if renders_by_path:
                print(f"Found {len(renders_by_path)} renders with similar path:")
                for r in renders_by_path:
                    print(f"  Render ID: {r['id']}, Project ID: {r.get('project_id', 'N/A')}, Path: {r['path']}")

if __name__ == '__main__':
    main()
