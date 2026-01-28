"""
Debug script to inspect what pyflp exposes for plugins in FLP files.

This script provides detailed analysis of an FLP file to help diagnose
plugin detection issues.

Usage:
    python scripts/debug_flp_parser.py <path_to_flp_file>
    python scripts/debug_flp_parser.py <path_to_directory>  # Uses first .flp found

Example:
    python scripts/debug_flp_parser.py "F:\\Projects\\MyProject\\MyProject.flp"
"""

import sys
import os
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from FruityWolf.flp_parser.compatibility import flp_enum_patch
import pyflp


def inspect_object_attributes(obj, prefix="", max_depth=1, current_depth=0):
    """Recursively inspect an object's attributes."""
    if current_depth >= max_depth:
        return {}
    
    result = {}
    try:
        attrs = [a for a in dir(obj) if not a.startswith('_')]
        for attr in attrs:
            try:
                value = getattr(obj, attr)
                if callable(value):
                    continue
                
                # Convert to string for display
                str_value = str(value)
                if len(str_value) > 200:
                    str_value = str_value[:200] + "..."
                
                result[attr] = {
                    'value': str_value,
                    'type': type(value).__name__
                }
            except Exception as e:
                result[attr] = {'error': str(e)}
    except:
        pass
    
    return result


def analyze_channel(channel, index):
    """Analyze a single channel in detail."""
    print(f"\n{'='*60}")
    print(f"CHANNEL {index}")
    print('='*60)
    
    # Basic info
    ctype = getattr(channel, 'type', None)
    name = getattr(channel, 'name', None)
    display_name = getattr(channel, 'display_name', None)
    internal_name = getattr(channel, 'internal_name', None)
    
    type_names = {0: 'Sampler', 2: 'Native', 3: 'Layer', 4: 'Instrument', 5: 'Automation'}
    type_str = type_names.get(ctype, f'Unknown({ctype})')
    
    print(f"  Type: {type_str}")
    print(f"  Name: {name}")
    print(f"  Display Name: {display_name}")
    print(f"  Internal Name: {internal_name}")
    
    has_plugin = hasattr(channel, 'plugin') and channel.plugin is not None
    print(f"  Has Plugin Object: {has_plugin}")
    
    if has_plugin:
        plugin = channel.plugin
        plugin_type = type(plugin).__name__
        print(f"\n  Plugin Object:")
        print(f"    Python Type: {plugin_type}")
        
        # Try documented VSTPlugin attributes
        vst_attrs = ['name', 'plugin_path', 'vendor', 'fourcc', 'guid']
        print(f"\n    VST Attributes (documented):")
        for attr in vst_attrs:
            try:
                value = getattr(plugin, attr, None)
                print(f"      {attr}: {value}")
            except Exception as e:
                print(f"      {attr}: ERROR - {e}")
        
        # All available attributes
        all_attrs = [a for a in dir(plugin) if not a.startswith('_')]
        print(f"\n    All Available Attributes: {all_attrs[:15]}{'...' if len(all_attrs) > 15 else ''}")
        
        # Non-None values
        print(f"\n    Non-Empty Values:")
        for attr in all_attrs:
            try:
                value = getattr(plugin, attr)
                if callable(value):
                    continue
                if value is not None and str(value).strip():
                    str_value = str(value)
                    if len(str_value) > 100:
                        str_value = str_value[:100] + "..."
                    print(f"      {attr} ({type(value).__name__}): {str_value}")
            except:
                pass
    
    return {
        'index': index,
        'type': type_str,
        'name': name,
        'display_name': display_name,
        'has_plugin': has_plugin
    }


def analyze_mixer_slot(slot, track_idx, slot_idx):
    """Analyze a single mixer slot in detail."""
    if not slot:
        return None
    
    print(f"\n  Slot {slot_idx}:")
    
    # Basic info
    slot_name = getattr(slot, 'name', None)
    internal_name = getattr(slot, 'internal_name', None)
    enabled = getattr(slot, 'enabled', None)
    
    print(f"    Name: {slot_name}")
    print(f"    Internal Name: {internal_name}")
    print(f"    Enabled: {enabled}")
    
    has_plugin = hasattr(slot, 'plugin') and slot.plugin is not None
    print(f"    Has Plugin Object: {has_plugin}")
    
    if has_plugin:
        plugin = slot.plugin
        plugin_type = type(plugin).__name__
        print(f"\n    Plugin Object:")
        print(f"      Python Type: {plugin_type}")
        
        # Try documented VSTPlugin attributes
        vst_attrs = ['name', 'plugin_path', 'vendor', 'fourcc', 'guid']
        print(f"\n      VST Attributes:")
        for attr in vst_attrs:
            try:
                value = getattr(plugin, attr, None)
                print(f"        {attr}: {value}")
            except Exception as e:
                print(f"        {attr}: ERROR - {e}")
        
        # Non-None values
        all_attrs = [a for a in dir(plugin) if not a.startswith('_')]
        print(f"\n      Non-Empty Values:")
        for attr in all_attrs:
            try:
                value = getattr(plugin, attr)
                if callable(value):
                    continue
                if value is not None and str(value).strip():
                    str_value = str(value)
                    if len(str_value) > 80:
                        str_value = str_value[:80] + "..."
                    print(f"        {attr} ({type(value).__name__}): {str_value}")
            except:
                pass
    
    return {
        'track': track_idx,
        'slot': slot_idx,
        'name': slot_name,
        'internal_name': internal_name,
        'has_plugin': has_plugin
    }


def debug_flp_detailed(flp_path):
    """Perform detailed debug analysis of an FLP file."""
    print(f"\n{'#'*70}")
    print(f"FLP PARSER DEBUG ANALYSIS")
    print(f"{'#'*70}")
    print(f"File: {flp_path}\n")
    
    try:
        with flp_enum_patch():
            project = pyflp.parse(flp_path)
        
        # Project info
        print(f"Project Type: {type(project).__name__}")
        print(f"Tempo: {getattr(project, 'tempo', 'N/A')}")
        print(f"Version: {getattr(project, 'version', 'N/A')}")
        
        # Channels summary
        channels = project.channels if hasattr(project, 'channels') else []
        print(f"\nChannels: {len(channels)}")
        
        channel_stats = defaultdict(int)
        plugins_found = []
        
        for i, channel in enumerate(channels):
            info = analyze_channel(channel, i)
            ctype = getattr(channel, 'type', None)
            channel_stats[info['type']] += 1
            
            if info['has_plugin']:
                plugins_found.append(info)
        
        # Channel type breakdown
        print(f"\n{'='*60}")
        print("CHANNEL TYPE BREAKDOWN")
        print('='*60)
        for ctype, count in sorted(channel_stats.items()):
            print(f"  {ctype}: {count}")
        
        # Mixer analysis
        mixer = project.mixer if hasattr(project, 'mixer') else None
        if mixer:
            print(f"\n{'='*60}")
            print(f"MIXER TRACKS: {len(mixer)}")
            print('='*60)
            
            total_slots = 0
            slots_with_plugins = 0
            mixer_plugins = []
            
            for track_idx, track in enumerate(mixer):
                track_name = getattr(track, 'name', None)
                
                if not hasattr(track, 'slots'):
                    continue
                
                has_content = False
                for slot_idx, slot in enumerate(track.slots):
                    if slot:
                        slot_info = analyze_mixer_slot(slot, track_idx, slot_idx)
                        if slot_info:
                            total_slots += 1
                            if slot_info['has_plugin']:
                                slots_with_plugins += 1
                                mixer_plugins.append(slot_info)
                            has_content = True
                
                if not has_content and track_idx < 10:  # Show first 10 empty tracks
                    print(f"\n  Track {track_idx} ({track_name or 'unnamed'}): No slots with content")
            
            print(f"\n{'='*60}")
            print("MIXER SUMMARY")
            print('='*60)
            print(f"  Total active slots: {total_slots}")
            print(f"  Slots with plugin objects: {slots_with_plugins}")
            print(f"  Slots without plugin objects: {total_slots - slots_with_plugins}")
        
        # Final summary
        print(f"\n{'#'*70}")
        print("SUMMARY")
        print('#'*70)
        print(f"Total channels: {len(channels)}")
        print(f"Channels with plugin objects: {len(plugins_found)}")
        
        if mixer:
            print(f"Total mixer tracks: {len(mixer)}")
            print(f"Total mixer slots (active): {total_slots}")
            print(f"Mixer slots with plugin objects: {slots_with_plugins}")
        
        # Test our enhanced parser
        print(f"\n{'='*60}")
        print("TESTING ENHANCED PARSER")
        print('='*60)
        
        from FruityWolf.flp_parser.parser import FLPParser
        parser = FLPParser(debug_mode=True)
        result = parser.parse(flp_path, match_installed_plugins=False)
        
        if result:
            print(f"\nPlugins detected: {len(result['plugins'])}")
            print(f"Samples detected: {len(result['samples'])}")
            print(f"Patterns: {result['pattern_count']}")
            
            if result['plugins']:
                print(f"\n--- DETECTED PLUGINS ---")
                
                # Group by type
                generators = [p for p in result['plugins'] if p['type'] == 'generator']
                effects = [p for p in result['plugins'] if p['type'] == 'effect']
                
                print(f"\nGENERATORS ({len(generators)}):")
                for p in generators:
                    native_flag = " [NATIVE]" if p.get('is_native') else ""
                    fmt = f" [{p['format']}]" if p.get('format') else ""
                    vendor = f" ({p['vendor']})" if p.get('vendor') else ""
                    print(f"  - {p['name']}{vendor}{fmt}{native_flag}")
                
                print(f"\nEFFECTS ({len(effects)}):")
                for p in effects:
                    native_flag = " [NATIVE]" if p.get('is_native') else ""
                    fmt = f" [{p['format']}]" if p.get('format') else ""
                    vendor = f" ({p['vendor']})" if p.get('vendor') else ""
                    loc = f" [Track {p['mixer_track']}, Slot {p['slot']}]"
                    print(f"  - {p['name']}{vendor}{fmt}{native_flag}{loc}")
            
            # Debug info
            if '_debug_info' in result:
                print(f"\n--- DEBUG STATISTICS ---")
                for key, value in result['_debug_info'].items():
                    print(f"  {key}: {value}")
        else:
            print("Parser returned None - parsing failed!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def quick_test(flp_path):
    """Quick test of the enhanced parser."""
    print(f"Testing enhanced parser on: {flp_path}\n")
    
    from FruityWolf.flp_parser.parser import FLPParser
    parser = FLPParser(debug_mode=True)
    result = parser.parse(flp_path, match_installed_plugins=False)
    
    if result:
        print(f"Plugins found: {len(result['plugins'])}")
        for p in result['plugins']:
            print(f"  - {p['name']} ({p['type']}) "
                  f"[{'native' if p.get('is_native') else p.get('format', 'unknown')}]")
    else:
        print("Parsing failed!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_flp_parser.py <path_to_flp_file>")
        print("       python scripts/debug_flp_parser.py <path_to_directory>")
        print("\nOptions:")
        print("  --quick    Quick test (less verbose)")
        sys.exit(1)
    
    flp_path = sys.argv[1]
    quick_mode = '--quick' in sys.argv
    
    # Handle directory paths - find first .flp file
    if os.path.isdir(flp_path):
        flp_files = list(Path(flp_path).glob("*.flp"))
        if not flp_files:
            print(f"Error: No .flp files found in directory: {flp_path}")
            sys.exit(1)
        flp_path = str(flp_files[0])
        print(f"Found FLP file: {flp_path}\n")
    elif not os.path.exists(flp_path):
        print(f"Error: File or directory not found: {flp_path}")
        sys.exit(1)
    elif not flp_path.lower().endswith('.flp'):
        print(f"Warning: Path does not end with .flp: {flp_path}")
    
    if quick_mode:
        quick_test(flp_path)
    else:
        debug_flp_detailed(flp_path)
