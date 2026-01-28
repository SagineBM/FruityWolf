"""
CLI interface for production-grade plugin scanner.
Outputs normalized JSON inventory of detected plugins.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List

from FruityWolf.utils.plugin_scanner import scan_system_plugins, get_vst_search_paths


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Production-grade Windows plugin scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan and output JSON
  python -m FruityWolf.utils.plugin_scanner_cli
  
  # Scan without cache
  python -m FruityWolf.utils.plugin_scanner_cli --no-cache
  
  # Use more workers for faster scanning
  python -m FruityWolf.utils.plugin_scanner_cli --workers 8
  
  # List scan paths only
  python -m FruityWolf.utils.plugin_scanner_cli --list-paths
        """
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable file metadata caching'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers for PE inspection (default: 4)'
    )
    
    parser.add_argument(
        '--list-paths',
        action='store_true',
        help='List all scan paths and exit'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'jsonl'],
        default='json',
        help='Output format: json (array) or jsonl (one record per line)'
    )
    
    args = parser.parse_args()
    
    # List paths mode
    if args.list_paths:
        paths = get_vst_search_paths()
        print(f"Found {len(paths)} scan paths:")
        for path in sorted(paths):
            print(f"  {path}")
        return 0
    
    # Run scan
    try:
        count = scan_system_plugins(use_cache=not args.no_cache, max_workers=args.workers)
        
        # Fetch results from database
        from FruityWolf.database import query
        rows = query("""
            SELECT name, path, category, format, arch, is_shell, 
                   exports_validated, content_related, plugin_type_tag, vendor
            FROM installed_plugins
            WHERE is_active = 1
            ORDER BY plugin_type_tag, name
        """)
        
        records = []
        for row in rows:
            record = {
                'id': _generate_id_from_path(row['path'], row['plugin_type_tag']),
                'name': row['name'],
                'type': row['plugin_type_tag'],
                'format': row['format'],
                'path': row['path'],
                'arch': row['arch'] or 'unknown',
                'validated': bool(row['exports_validated']),
                'validation_reason': 'PE exports validated' if row['exports_validated'] else 'Structure validated',
                'vendor': (row['vendor'] if 'vendor' in row.keys() else None) or 'unknown',
                'is_shell': bool(row['is_shell']),
                'content_related': bool(row['content_related'])
            }
            records.append(record)
        
        # Output
        output_text = ""
        if args.format == 'json':
            output_text = json.dumps(records, indent=2)
        else:  # jsonl
            output_text = '\n'.join(json.dumps(r) for r in records)
        
        if args.output:
            Path(args.output).write_text(output_text, encoding='utf-8')
            print(f"Scan complete: {count} plugins found. Results written to {args.output}", file=sys.stderr)
        else:
            print(output_text)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _generate_id_from_path(path: str, plugin_type: str) -> str:
    """Generate stable ID from path and type."""
    import hashlib
    normalized = str(Path(path).resolve()).lower().replace('\\', '/')
    hash_input = f"{normalized}:{plugin_type}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


if __name__ == '__main__':
    sys.exit(main())
