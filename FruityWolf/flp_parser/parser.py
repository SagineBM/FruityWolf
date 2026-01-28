"""
FLP Parser Module - Enhanced Edition

Maximum accuracy plugin detection from FL Studio Project files (.flp) using pyflp.
This parser extracts ALL plugins (VST2, VST3, CLAP, Native FL) with comprehensive
fallback strategies for maximum detection accuracy.

Features:
- Direct VSTPlugin attribute access (name, plugin_path, vendor, fourcc, guid)
- Native FL Studio plugin detection via internal_name
- Multi-strategy extraction with priority ordering
- Comprehensive debug logging for troubleshooting
- Deduplication and normalization
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

# Apply compatibility patch for Python 3.11+ Enum behavior in construct
try:
    # Use context manager patch for safer execution
    from .compatibility import flp_enum_patch
    
    # Patch during IMPORT to fix class definition (EventEnum)
    with flp_enum_patch():
        import pyflp
        
    HAS_PYFLP = True
except ImportError:
    HAS_PYFLP = False
except Exception as e:
    # Catch any other initialization errors
    logging.getLogger(__name__).error(f"Failed to initialize pyflp: {e}")
    HAS_PYFLP = False

logger = logging.getLogger(__name__)


# =============================================================================
# FL Studio Native Plugins Database
# =============================================================================

# Known native FL Studio generator plugins (instruments)
FL_NATIVE_GENERATORS = {
    # Synthesizers
    'sytrus', '3xosc', 'harmless', 'harmor', 'flex', 'morphine', 'sakura',
    'sawer', 'toxic biohazard', 'poizone', 'directwave', 'directwave player',
    'minisynth live', 'gms', 'fl keys', 'fl slayer',
    # Samplers & Utilities
    'sampler', 'audio clip', 'fruity granulizer', 'fruity slicer',
    'fruity slicex', 'slicex', 'fruity soundfont player', 'soundfont player',
    'fruity dx10', 'dx10', 'beepmap', 'boobass', 'plucked!', 'simsynth',
    'wasp', 'wasp xt', 'fruity drumsynth live', 'drumsynth live',
    'fruity kick', 'transistor bass', 'fruit kick',
    'fpc', 'bassdrum', 'speech synthesizer', 'vocodex',
    # Layers & Automation
    'layer', 'patcher', 'control surface', 'automation clip',
}

# Known native FL Studio effect plugins
FL_NATIVE_EFFECTS = {
    # EQ & Filters
    'fruity parametric eq', 'parametric eq', 'fruity parametric eq 2', 
    'parametric eq 2', 'fruity 7 band eq', 'fruity graphic eq',
    'fruity convolver', 'convolver', 'fruity filter', 'fruity free filter',
    'fruity love philter', 'love philter', 'fruity vocoder',
    # Dynamics
    'fruity limiter', 'limiter', 'fruity compressor', 'compressor',
    'fruity soft clipper', 'soft clipper', 'fruity multiband compressor',
    'multiband compressor', 'maximus', 'soundgoodizer', 'transient processor',
    # Reverb & Delay
    'fruity reverb', 'fruity reverb 2', 'reverb 2', 'fruity reeverb',
    'fruity delay', 'fruity delay 2', 'delay 2', 'fruity delay 3', 'delay 3',
    'fruity delay bank', 'grossbeat', 'gross beat',
    # Modulation
    'fruity chorus', 'chorus', 'fruity flanger', 'flanger', 
    'fruity flangus', 'fruity phaser', 'phaser', 'fruity stereo shaper',
    'stereo shaper', 'fruity stereo enhancer', 'stereo enhancer',
    # Distortion & Saturation
    'fruity blood overdrive', 'blood overdrive', 'fruity fast dist',
    'fast dist', 'fruity squeeze', 'squeeze', 'fruity waveshaper',
    'waveshaper', 'distructor', 'hardcore',
    # Analysis & Utilities
    'fruity spectroman', 'spectroman', 'wave candy', 'fruity db meter',
    'db meter', 'fruity peak controller', 'peak controller', 
    'fruity formula controller', 'formula controller', 'fruity balance',
    'balance', 'fruity center', 'center', 'fruity mute 2', 'mute 2',
    'fruity send', 'send', 'fruity notebook', 'notebook', 'fruity notebook 2',
    'patcher', 'pitcher', 'newtone', 'vocodex', 'edison',
    # Other
    'fruity stereo shaper', 'fruity bass boost', 'bass boost',
    'fruity html notebook', 'html notebook', 'fruity big clock', 'big clock',
    'fruity wrapper', 'wrapper', 'fruity panomatic', 'panomatic',
    'soundgoodizer', 'transient processor', 'fruity scratcher',
}

# Combined set for quick lookup
FL_NATIVE_ALL = FL_NATIVE_GENERATORS | FL_NATIVE_EFFECTS


# =============================================================================
# Plugin Name Extraction Utilities
# =============================================================================

def _is_vst_plugin(plugin_obj) -> bool:
    """Check if plugin object is a VST plugin (VSTPlugin class)."""
    type_name = type(plugin_obj).__name__
    # PyFLP uses VSTPlugin for VST2 and VST3
    return 'VST' in type_name or 'Vst' in type_name


def _extract_vst_info(plugin_obj) -> Dict[str, Any]:
    """
    Extract information from a pyflp VSTPlugin object using documented attributes.
    
    According to pyflp docs, VSTPlugin has:
    - name: str - Factory name of the plugin
    - plugin_path: str - The absolute path to the plugin binary
    - vendor: str - Plugin developer (vendor) name
    - fourcc: str - A unique four character code identifying the plugin
    - guid: bytes - For VST3
    """
    result = {
        'name': None,
        'path': None,
        'vendor': None,
        'fourcc': None,
        'guid': None,
        'format': None,
        'is_vst': True
    }
    
    if not plugin_obj:
        return result
    
    # Direct attribute access for documented VSTPlugin attributes
    try:
        # Name (factory name)
        if hasattr(plugin_obj, 'name'):
            name = plugin_obj.name
            if name and isinstance(name, str) and name.strip():
                result['name'] = name.strip()
                logger.debug(f"VST name from plugin.name: {result['name']}")
    except Exception as e:
        logger.debug(f"Could not get plugin.name: {e}")
    
    try:
        # Plugin path
        if hasattr(plugin_obj, 'plugin_path'):
            path = plugin_obj.plugin_path
            if path and isinstance(path, str) and path.strip():
                result['path'] = path.strip()
                logger.debug(f"VST path from plugin.plugin_path: {result['path']}")
    except Exception as e:
        logger.debug(f"Could not get plugin.plugin_path: {e}")
    
    try:
        # Vendor
        if hasattr(plugin_obj, 'vendor'):
            vendor = plugin_obj.vendor
            if vendor and isinstance(vendor, str) and vendor.strip():
                result['vendor'] = vendor.strip()
                logger.debug(f"VST vendor from plugin.vendor: {result['vendor']}")
    except Exception as e:
        logger.debug(f"Could not get plugin.vendor: {e}")
    
    try:
        # Four character code (VST2)
        if hasattr(plugin_obj, 'fourcc'):
            fourcc = plugin_obj.fourcc
            if fourcc:
                result['fourcc'] = str(fourcc)
    except Exception as e:
        logger.debug(f"Could not get plugin.fourcc: {e}")
    
    try:
        # GUID (VST3)
        if hasattr(plugin_obj, 'guid'):
            guid = plugin_obj.guid
            if guid:
                result['guid'] = guid
    except Exception as e:
        logger.debug(f"Could not get plugin.guid: {e}")
    
    # Determine format from path
    if result['path']:
        path_lower = result['path'].lower()
        if '.vst3' in path_lower:
            result['format'] = 'VST3'
        elif path_lower.endswith('.dll'):
            result['format'] = 'VST2'
        elif path_lower.endswith('.clap'):
            result['format'] = 'CLAP'
        elif path_lower.endswith('.aaxplugin') or '.aax' in path_lower:
            result['format'] = 'AAX'
    
    # Use GUID to detect VST3 if no path
    if not result['format'] and result['guid']:
        result['format'] = 'VST3'
    
    # Build combined name if we have vendor but no full name
    if result['vendor'] and not result['name']:
        result['name'] = result['vendor']
    elif result['vendor'] and result['name']:
        # Don't duplicate vendor if already in name
        if result['vendor'].lower() not in result['name'].lower():
            result['name'] = f"{result['vendor']} {result['name']}"
    
    # Extract name from path if still missing
    if not result['name'] and result['path']:
        result['name'] = _extract_plugin_name_from_path(result['path'])
    
    return result


def _extract_comprehensive_plugin_info(plugin_obj, context: str = "") -> Dict[str, Any]:
    """
    Comprehensive plugin extraction using all available strategies.
    Priority order:
    1. VSTPlugin-specific attributes (name, plugin_path, vendor)
    2. Direct name/display_name attributes
    3. Internal name (for native plugins)
    4. Path extraction
    5. __dict__ inspection
    """
    result = {
        'name': None,
        'path': None,
        'vendor': None,
        'product': None,
        'unique_id': None,
        'format': None,
        'is_native': False
    }
    
    if not plugin_obj:
        return result
    
    plugin_type = type(plugin_obj).__name__
    logger.debug(f"[{context}] Extracting from plugin type: {plugin_type}")
    
    # Strategy 1: Check if it's a VSTPlugin and use documented attributes
    if _is_vst_plugin(plugin_obj):
        vst_info = _extract_vst_info(plugin_obj)
        if vst_info['name']:
            result['name'] = vst_info['name']
            result['path'] = vst_info['path']
            result['vendor'] = vst_info['vendor']
            result['format'] = vst_info['format']
            logger.debug(f"[{context}] VST extraction successful: {result['name']}")
            return result
    
    # Strategy 2: Direct name attributes (priority order)
    name_attrs = [
        'name', 'display_name', 'plugin_name', 'vst_name', 
        'product_name', 'title', 'effect_name'
    ]
    
    for attr in name_attrs:
        try:
            if hasattr(plugin_obj, attr):
                value = getattr(plugin_obj, attr)
                if value and isinstance(value, str) and value.strip():
                    candidate = value.strip()
                    # Skip generic names
                    if candidate.lower() not in ('sampler', 'audio clip', 'layer', 
                                                   'automation', 'empty', 'fruity wrapper'):
                        result['name'] = candidate
                        logger.debug(f"[{context}] Found name via {attr}: {candidate}")
                        break
        except Exception as e:
            logger.debug(f"[{context}] Error accessing {attr}: {e}")
    
    # Strategy 3: Path attributes
    path_attrs = ['plugin_path', 'path', 'dll_path', 'vst_path', 'filename']
    
    for attr in path_attrs:
        try:
            if hasattr(plugin_obj, attr):
                value = getattr(plugin_obj, attr)
                if value and isinstance(value, str) and value.strip():
                    result['path'] = value.strip()
                    logger.debug(f"[{context}] Found path via {attr}: {result['path']}")
                    
                    # Extract name from path if not found yet
                    if not result['name']:
                        extracted = _extract_plugin_name_from_path(result['path'])
                        if extracted:
                            result['name'] = extracted
                            logger.debug(f"[{context}] Extracted name from path: {extracted}")
                    break
        except Exception as e:
            logger.debug(f"[{context}] Error accessing {attr}: {e}")
    
    # Strategy 4: Vendor/Product for combining
    try:
        if hasattr(plugin_obj, 'vendor') and plugin_obj.vendor:
            result['vendor'] = str(plugin_obj.vendor).strip()
        if hasattr(plugin_obj, 'vendor_name') and plugin_obj.vendor_name:
            result['vendor'] = str(plugin_obj.vendor_name).strip()
    except:
        pass
    
    try:
        if hasattr(plugin_obj, 'product_name') and plugin_obj.product_name:
            result['product'] = str(plugin_obj.product_name).strip()
    except:
        pass
    
    # Build name from vendor + product if we don't have one
    if not result['name']:
        if result['vendor'] and result['product']:
            result['name'] = f"{result['vendor']} {result['product']}"
        elif result['product']:
            result['name'] = result['product']
        elif result['vendor']:
            result['name'] = result['vendor']
    
    # Strategy 5: Check __dict__ for any missed attributes
    if not result['name']:
        try:
            if hasattr(plugin_obj, '__dict__'):
                p_dict = plugin_obj.__dict__
                for key in ['name', 'display_name', 'plugin_name', 'product_name']:
                    if key in p_dict and p_dict[key]:
                        candidate = str(p_dict[key]).strip()
                        if candidate and candidate.lower() not in ('sampler', 'audio clip'):
                            result['name'] = candidate
                            logger.debug(f"[{context}] Found name via __dict__.{key}: {candidate}")
                            break
        except Exception as e:
            logger.debug(f"[{context}] Error accessing __dict__: {e}")
    
    # Determine format from path if not set
    if result['path'] and not result['format']:
        path_lower = result['path'].lower()
        if '.vst3' in path_lower:
            result['format'] = 'VST3'
        elif path_lower.endswith('.dll'):
            result['format'] = 'VST2'
        elif path_lower.endswith('.clap'):
            result['format'] = 'CLAP'
    
    return result


def _extract_plugin_name_from_path(path: str) -> Optional[str]:
    """
    Extract plugin name from file path.
    Handles VST2 (.dll), VST3 (.vst3 bundle), CLAP, and AAX paths.
    
    Examples:
    - "C:\\Program Files\\FabFilter\\Pro-Q 3.vst3" -> "Pro-Q 3"
    - "C:\\VSTPlugins\\Serum_x64.dll" -> "Serum"
    - "C:\\path\\to\\Plugin.vst3\\Contents\\x86_64-win\\Plugin.vst3" -> "Plugin"
    """
    if not path:
        return None
    
    p = Path(path)
    
    # VST3 bundle: extract from folder name
    # VST3 paths can be nested: "Plugin.vst3" or "Plugin.vst3/Contents/x86_64-win/Plugin.vst3"
    if '.vst3' in str(p).lower():
        # Find the .vst3 folder name
        parts = str(p).lower().split('.vst3')
        if parts:
            # Get the part before .vst3
            vst3_part = parts[0]
            # Handle both forward and back slashes
            vst3_part = vst3_part.replace('\\', '/')
            vst3_name = vst3_part.split('/')[-1]
            if vst3_name:
                return vst3_name.strip()
    
    # VST2 DLL: extract from filename
    if p.suffix.lower() == '.dll':
        stem = p.stem
        
        # Remove common architecture and platform suffixes
        suffixes_to_remove = [
            '_x64', '_x86', '_win64', '_win32', '-x64', '-x86',
            '_64bit', '_32bit', ' x64', ' x86', '_amd64',
            '_vst2', '_vst', ' VST', ' (x64)', ' (x86)'
        ]
        
        for suffix in suffixes_to_remove:
            if stem.lower().endswith(suffix.lower()):
                stem = stem[:-len(suffix)]
        
        return stem.strip() if stem.strip() else None
    
    # CLAP
    if p.suffix.lower() == '.clap':
        return p.stem.strip() if p.stem.strip() else None
    
    # AAX
    if p.suffix.lower() == '.aaxplugin' or '.aax' in str(p).lower():
        stem = p.stem
        if stem.lower().endswith('.aaxplugin'):
            stem = stem[:-10]
        return stem.strip() if stem.strip() else None
    
    # Fallback: just return stem
    return p.stem.strip() if p.stem.strip() else None


def _normalize_plugin_name(name: str) -> str:
    """
    Normalize plugin name for consistency.
    Removes VST suffixes, normalizes whitespace, and standardizes common patterns.
    """
    if not name:
        return ""
    
    name = name.strip()
    
    # Remove common VST format suffixes
    suffixes_to_remove = [
        ' (VST)', ' (VST2)', ' (VST3)', ' (CLAP)', ' (AAX)', ' (AU)',
        ' [VST]', ' [VST2]', ' [VST3]', ' [CLAP]', ' [AAX]', ' [AU]',
        ' VST', ' VST2', ' VST3', ' CLAP', ' AAX', ' AU',
        ' x64', ' x86', ' (x64)', ' (x86)', ' 64-bit', ' 32-bit',
        '.vst3', '.dll', '.clap'
    ]
    
    for suffix in suffixes_to_remove:
        if name.lower().endswith(suffix.lower()):
            name = name[:-len(suffix)].strip()
    
    # Normalize whitespace
    name = ' '.join(name.split())
    
    return name


def _is_native_fl_plugin(name: str, internal_name: str = None) -> bool:
    """Check if a plugin name corresponds to a native FL Studio plugin."""
    if not name:
        return False
    
    name_lower = name.lower().strip()
    
    # "Fruity Wrapper" means it's a VST/AU plugin, NOT native
    if internal_name and internal_name.lower().strip() == 'fruity wrapper':
        return False
    
    # Skip internal FL names that aren't actual plugins
    skip_internal = {'audioeditortrack', 'audio editor', 'midi out', 'midi in'}
    if name_lower in skip_internal:
        return False
    
    # If name contains third-party vendor names, it's NOT native
    third_party_vendors = {
        'refx', 'native instruments', 'fabfilter', 'waves', 'izotope', 
        'spectrasonics', 'arturia', 'u-he', 'xfer', 'serum', 'massive',
        'kontakt', 'omnisphere', 'sylenth', 'spire', 'nexus', 'diva',
        'vital', 'pigments', 'analog lab', 'komplete', 'maschine',
        'reaktor', 'battery', 'guitar rig', 'absynth', 'fm8', 'razor',
        'soundtoys', 'valhalla', 'antares', 'slate digital', 'voxengo',
        'cla ', 'cla-', 'cymatics', 'ozone', 'neutron', 'nectar',
        'ssl', 'api', 'neve', 'uad', 'plugin alliance', 'brainworx',
    }
    for vendor in third_party_vendors:
        if vendor in name_lower:
            return False
    
    # Direct match in FL native set
    if name_lower in FL_NATIVE_ALL:
        return True
    
    # Check internal_name for native plugins
    if internal_name:
        internal_lower = internal_name.lower().strip()
        if internal_lower in FL_NATIVE_ALL:
            return True
        # Skip if internal_name suggests it's a third-party plugin
        for vendor in third_party_vendors:
            if vendor in internal_lower:
                return False
    
    # Check for "Fruity" prefix (most FL native plugins)
    if name_lower.startswith('fruity '):
        return True
    
    # Very strict partial matches - only for exact word boundaries
    # Avoid matching generic words as native
    for native in FL_NATIVE_ALL:
        # Require exact word match for short names
        if len(native) <= 4:
            if name_lower == native:
                return True
        elif native in name_lower and (
            name_lower.startswith(native + ' ') or 
            name_lower.endswith(' ' + native) or
            name_lower == native
        ):
            return True
    
    return False


def _should_skip_plugin_name(name: str) -> bool:
    """Check if a plugin name should be skipped (too generic or not a real plugin)."""
    if not name:
        return True
    
    name_lower = name.lower().strip()
    
    # Skip empty or very short names
    if len(name_lower) < 2:
        return True
    
    # Skip truly generic names that aren't plugins
    skip_names = {
        'sampler', 'audio clip', 'layer', 'automation', 'empty', 'none',
        'channel', 'track', 'insert', 'master', 'slot', 'send',
        'fruity wrapper',  # This is a wrapper, not a plugin itself
        # FL Studio internal names
        'audioeditortrack', 'audio editor track', 'midiout', 'midi out',
        'midiin', 'midi in', 'patcher', 'control surface',
    }
    
    if name_lower in skip_names:
        return True
    
    return False


def _is_likely_sample_name(name: str) -> bool:
    """
    Check if a name is likely a sample/audio file name rather than a plugin.
    This helps filter out sampler channels that just have sample names.
    """
    if not name:
        return False
    
    name_lower = name.lower().strip()
    
    # Check for audio file extensions (even without the dot)
    audio_indicators = [
        '.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff',
    ]
    for indicator in audio_indicators:
        if name_lower.endswith(indicator):
            return True
    
    # Check for common sample naming patterns
    sample_patterns = [
        # Common prefixes/suffixes
        'loop', 'shot', 'hit', 'one shot', 'oneshot', 'fx ',
        '_bpm', ' bpm', 'bpm_', '-bpm',
        '_key', ' key', 'key_', '-key',
        # Instrument samples (not plugins)
        'recording-', 'rec_', 'take ',
        # Sample pack indicators
        '@', '- @', '- AFRICAN', '- LION', '- Cymbal', '- Ambient',
        'Producer Bundle', 'Sound Pack', 'Sample Pack',
        'KSHMR_', 'Savage Sounds', 'utomp3', 'acapella', 'Acapella',
        # Very short generic percussion names (likely samples)
        'transition', 'riser', 'sweep', 'atmo ', 'ambient ',
        # FL Studio recording/bounce names
        '_insert ', '(consolidated)', '_part_', '- part_',
        # Vocal samples
        '[vocals]', '[music]', '[drums]', '[bass]',
    ]
    
    for pattern in sample_patterns:
        if pattern.lower() in name_lower:
            return True
    
    # Check for very short names that are likely drum/percussion samples
    short_sample_names = {
        'kick', 'snare', 'hihat', 'hi-hat', 'clap', 'tom', 'rim', 
        'perc', 'conga', 'bonga', 'shaker', 'cymbal', 'crash',
        'ride', 'open hat', 'closed hat', 'oh', 'ch', 'hh',
        '808', '909', 'snare2', 'kick2', 'hat', 'hats',
        # Additional common names
        'bass', 'fill', 'fill1', 'fill2', 'fill 1', 'fill 2',
        'ah', 'ooh', 'vocal', 'vox', 'chimes', 'bell',
        # Extended list based on common audio clip naming
        'main rim', 'low rim', 'stereo rim', 'hand drum', 'low hh',
        'reverse vocal', 'reverse synth', 'clock perc', 'dakar vox',
        'backing vocals', 'vocals', 'lead', 'pad', 'arp', 'pluck',
        'strings', 'horns', 'brass', 'fx', 'sfx', 'ambient',
        'sub', 'sub bass', '808 bass', 'melody', 'counter', 'hook',
    }
    
    if name_lower in short_sample_names:
        return True
    
    # Check for compound names that are likely audio clips
    audio_clip_patterns = [
        'rim', 'drum', 'vox', 'vocal', 'perc',
    ]
    for pattern in audio_clip_patterns:
        # Match "main rim", "stereo rim", "low hh" etc.
        if name_lower.endswith(' ' + pattern) or name_lower.startswith(pattern + ' '):
            # But not if it contains known plugin keywords
            if not any(kw in name_lower for kw in ['synth', 'plugin', 'eq', 'comp', 'verb', 'delay']):
                return True
    
    # Check for patterns with numbers suggesting audio clips
    import re
    
    # Pattern: "name_YYYY-MM-DD" (FL Studio recording date pattern)
    if re.search(r'_\d{4}-\d{2}-\d{2}', name):
        return True
    
    # Pattern: "name #2", "name #3" etc. (duplicated audio clips)
    if re.search(r'#\d+$', name.strip()):
        return True
    
    # Pattern: Numbers followed by dash and uppercase (sample packs)
    if re.search(r'\d+\s*-\s*[A-Z]', name):
        return True
    
    # Pattern: Short name + number (likely sample variation)
    # e.g., "Rim 2", "Fill 3" but not "Pro-Q 3"
    if re.match(r'^[A-Za-z]+ \d$', name.strip()) and len(name) < 10:
        # But allow plugin names with version numbers
        if not any(x in name_lower for x in ['pro-', 'pro ', 'vst', 'lab', 'synth']):
            return True
    
    return False


# =============================================================================
# Main FLP Parser Class
# =============================================================================

class FLPParser:
    """
    Enhanced FLP Parser for maximum accuracy plugin detection.
    
    Parses FL Studio project files using pyflp to extract:
    - All VST2, VST3, CLAP, and AAX plugins
    - Native FL Studio plugins
    - Sample/audio paths
    - Project metadata (tempo, time signature, etc.)
    """
    
    def __init__(self, debug_mode: bool = False):
        self.enabled = HAS_PYFLP
        self.debug_mode = debug_mode
        
        if not self.enabled:
            logger.warning("FLPParser initialized but pyflp is not installed")
        
        # Enable debug logging if debug mode is on
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
    
    def is_available(self) -> bool:
        """Check if pyflp is available and parser is enabled."""
        return self.enabled
    
    def parse(self, flp_path: str, match_installed_plugins: bool = True) -> Optional[Dict[str, Any]]:
        """
        Parse an FLP file and return extracted metadata with maximum accuracy.
        
        Args:
            flp_path: Path to the .flp file
            match_installed_plugins: Whether to match found plugins against installed plugins
        
        Returns:
            Dict containing 'plugins', 'samples', 'tempo', etc.
            None if parsing fails.
        """
        if not self.enabled:
            logger.warning("FLP parsing requested but pyflp is not available")
            return None
        
        if not os.path.exists(flp_path):
            logger.warning(f"FLP file not found: {flp_path}")
            return None
        
        try:
            # Parse FLP with compatibility patch context
            with flp_enum_patch():
                project = pyflp.parse(flp_path)
            
            result = {
                'plugins': [],
                'samples': [],
                'tempo': None,
                'time_sig': None,
                'version': None,
                'title': None,
                'artist': None,
                'genre': None,
                'pattern_count': 0,
                'channel_count': 0,
                'mixer_track_count': 0,
                '_debug_info': {}  # For troubleshooting
            }
            
            # Track unique plugins to avoid duplicates
            seen_plugins: Set[str] = set()  # (normalized_name, type, location)
            
            # Statistics for debugging
            stats = {
                'channels_total': 0,
                'channels_with_plugin': 0,
                'channels_skipped_type': 0,
                'channels_skipped_no_name': 0,
                'mixer_slots_total': 0,
                'mixer_slots_with_plugin': 0,
                'mixer_slots_skipped': 0,
                'vst_plugins': 0,
                'native_plugins': 0,
                'unknown_plugins': 0
            }
            
            # =================================================================
            # 1. Project Metadata
            # =================================================================
            if hasattr(project, 'tempo'):
                try:
                    result['tempo'] = float(project.tempo)
                except:
                    pass
            
            if hasattr(project, 'version'):
                try:
                    result['version'] = str(project.version)
                except:
                    pass
            
            if hasattr(project, 'title'):
                result['title'] = project.title
            if hasattr(project, 'artist'):
                result['artist'] = project.artist
            if hasattr(project, 'genre'):
                result['genre'] = project.genre
            
            # =================================================================
            # 2. Channel Rack Plugins (Generators/Instruments)
            # =================================================================
            if hasattr(project, 'channels') and project.channels:
                result['channel_count'] = len(project.channels)
                
                for i, channel in enumerate(project.channels):
                    stats['channels_total'] += 1
                    context = f"channel_{i}"
                    
                    # Get channel type (0=Sampler, 2=Native, 3=Layer, 4=Instrument, 5=Automation)
                    ctype = getattr(channel, 'type', None)
                    
                    # Skip Layer (3) and Automation (5) - they're not actual plugins
                    if ctype in (3, 5):
                        stats['channels_skipped_type'] += 1
                        logger.debug(f"[{context}] Skipping channel type {ctype}")
                        continue
                    
                    plugin_name = None
                    plugin_path = None
                    plugin_vendor = None
                    plugin_format = None
                    is_native = False
                    
                    # Get channel name/display_name first (often contains plugin name in FL)
                    channel_name = getattr(channel, 'name', None)
                    channel_display_name = getattr(channel, 'display_name', None)
                    
                    # Try to get internal_name (identifies native vs wrapper)
                    internal_name = None
                    if hasattr(channel, 'plugin') and channel.plugin:
                        internal_name = getattr(channel.plugin, 'internal_name', None)
                        if not internal_name:
                            internal_name = getattr(channel, 'internal_name', None)
                    
                    # Strategy A: Extract from plugin object (highest priority for VST)
                    if hasattr(channel, 'plugin') and channel.plugin:
                        plugin_obj = channel.plugin
                        stats['channels_with_plugin'] += 1
                        
                        # Check plugin type
                        plugin_type_name = type(plugin_obj).__name__
                        logger.debug(f"[{context}] Plugin object type: {plugin_type_name}")
                        
                        # Check internal_name to determine if VST (Fruity Wrapper)
                        if not internal_name:
                            internal_name = getattr(plugin_obj, 'internal_name', None)
                        
                        # If internal_name is "Fruity Wrapper", it's definitely a VST/AU plugin
                        if internal_name and internal_name.lower() == 'fruity wrapper':
                            is_native = False  # Definitely NOT native
                        
                        # Use comprehensive extraction
                        plugin_info = _extract_comprehensive_plugin_info(plugin_obj, context)
                        
                        if plugin_info['name']:
                            plugin_name = plugin_info['name']
                            plugin_path = plugin_info['path']
                            plugin_vendor = plugin_info['vendor']
                            plugin_format = plugin_info['format']
                    
                    # Strategy B: Use channel name/display_name if no plugin name yet
                    if not plugin_name:
                        for candidate in [channel_name, channel_display_name]:
                            if candidate and isinstance(candidate, str) and candidate.strip():
                                candidate = candidate.strip()
                                # Skip if it's a sample filename or sample name
                                if not any(candidate.lower().endswith(ext) for ext in 
                                          ('.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff', '.mid', '.midi')):
                                    if not _should_skip_plugin_name(candidate) and not _is_likely_sample_name(candidate):
                                        plugin_name = candidate
                                        logger.debug(f"[{context}] Using channel name: {plugin_name}")
                                        break
                    
                    # Strategy C: Check internal_name for native plugins
                    if not plugin_name and internal_name:
                        if internal_name.lower() != 'fruity wrapper':
                            # It's a native plugin
                            plugin_name = internal_name
                            is_native = True
                            logger.debug(f"[{context}] Using internal_name (native): {plugin_name}")
                    
                    # Process the found plugin
                    if plugin_name and not _should_skip_plugin_name(plugin_name):
                        # Skip if it looks like a sample name (not a real plugin)
                        # But only if we don't have a plugin_path (which confirms it's a real plugin)
                        if not plugin_path and _is_likely_sample_name(plugin_name):
                            stats['channels_skipped_no_name'] += 1
                            logger.debug(f"[{context}] Skipping likely sample name: {plugin_name}")
                            continue
                        
                        # Normalize the name
                        plugin_name = _normalize_plugin_name(plugin_name)
                        
                        # Check if native (but respect plugin_path - if we have a path, it's likely VST)
                        if not is_native and not plugin_path:
                            is_native = _is_native_fl_plugin(plugin_name, internal_name)
                        
                        # Update stats
                        if is_native:
                            stats['native_plugins'] += 1
                        elif plugin_format or plugin_path:
                            stats['vst_plugins'] += 1
                        else:
                            stats['unknown_plugins'] += 1
                        
                        # Create dedup key
                        dedup_key = (plugin_name.lower(), 'generator', i)
                        
                        if dedup_key not in seen_plugins:
                            seen_plugins.add(dedup_key)
                            
                            # Get preset name if available
                            preset_name = None
                            try:
                                if hasattr(channel, 'plugin') and channel.plugin:
                                    p = channel.plugin
                                    for attr in ['preset_name', 'preset']:
                                        if hasattr(p, attr):
                                            val = getattr(p, attr)
                                            if val:
                                                preset_name = str(val).strip()
                                                break
                            except:
                                pass
                            
                            result['plugins'].append({
                                'name': plugin_name,
                                'type': 'generator',
                                'path': plugin_path,
                                'vendor': plugin_vendor,
                                'format': plugin_format,
                                'channel_index': i,
                                'slot': None,
                                'mixer_track': None,
                                'preset': preset_name,
                                'is_native': is_native
                            })
                            logger.debug(f"[{context}] Added generator: {plugin_name} "
                                       f"(format={plugin_format}, native={is_native})")
                    else:
                        stats['channels_skipped_no_name'] += 1
                        # Debug: log what we found but couldn't extract
                        if self.debug_mode and hasattr(channel, 'plugin') and channel.plugin:
                            p = channel.plugin
                            attrs = {a: str(getattr(p, a, None))[:100] 
                                   for a in dir(p) if not a.startswith('_')}
                            logger.debug(f"[{context}] Could not extract name. "
                                       f"Plugin type: {type(p).__name__}, "
                                       f"Attrs: {list(attrs.keys())[:10]}")
            
            # =================================================================
            # 3. Mixer Effect Plugins
            # =================================================================
            if hasattr(project, 'mixer') and project.mixer:
                mixer_tracks = project.mixer
                result['mixer_track_count'] = len(mixer_tracks)
                
                for track_idx, track in enumerate(mixer_tracks):
                    track_name = getattr(track, 'name', None)
                    
                    # In pyflp 2.x, iterate directly over Insert to get Slots
                    # Insert.__iter__() returns Iterator[Slot]
                    try:
                        slots_iter = iter(track)
                    except TypeError:
                        # If track is not iterable, skip
                        continue
                    
                    for slot_idx, slot in enumerate(slots_iter):
                        stats['mixer_slots_total'] += 1
                        context = f"mixer_track_{track_idx}_slot_{slot_idx}"
                        
                        if not slot:
                            continue
                        
                        plugin_name = None
                        plugin_path = None
                        plugin_vendor = None
                        plugin_format = None
                        is_native = False
                        
                        # Get slot name (often contains plugin name or "Plugin - Preset")
                        slot_name = getattr(slot, 'name', None)
                        
                        # Get internal_name (identifies native vs Fruity Wrapper)
                        internal_name = getattr(slot, 'internal_name', None)
                        
                        # Strategy A: Extract from slot.plugin object
                        if hasattr(slot, 'plugin') and slot.plugin:
                            plugin_obj = slot.plugin
                            stats['mixer_slots_with_plugin'] += 1
                            
                            plugin_type_name = type(plugin_obj).__name__
                            logger.debug(f"[{context}] Slot plugin type: {plugin_type_name}")
                            
                            # Use comprehensive extraction
                            plugin_info = _extract_comprehensive_plugin_info(plugin_obj, context)
                            
                            if plugin_info['name']:
                                plugin_name = plugin_info['name']
                                plugin_path = plugin_info['path']
                                plugin_vendor = plugin_info['vendor']
                                plugin_format = plugin_info['format']
                        
                        # Strategy B: Parse slot name
                        # FL Studio format is often "Plugin Name" or "Plugin Name - Preset Name"
                        if not plugin_name and slot_name:
                            slot_name = str(slot_name).strip()
                            
                            # Skip if it looks like an audio file
                            if not any(slot_name.lower().endswith(ext) for ext in 
                                      ('.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff')):
                                
                                # Pattern 1: "Plugin - Preset" format
                                if ' - ' in slot_name:
                                    parts = slot_name.split(' - ', 1)
                                    candidate = parts[0].strip()
                                    if candidate and not _should_skip_plugin_name(candidate):
                                        plugin_name = candidate
                                        logger.debug(f"[{context}] Extracted from slot name "
                                                   f"(pattern: Plugin - Preset): {plugin_name}")
                                
                                # Pattern 2: "Plugin (Preset)" format
                                if not plugin_name and ' (' in slot_name:
                                    parts = slot_name.split(' (', 1)
                                    candidate = parts[0].strip()
                                    if candidate and not _should_skip_plugin_name(candidate):
                                        plugin_name = candidate
                                        logger.debug(f"[{context}] Extracted from slot name "
                                                   f"(pattern: Plugin (Preset)): {plugin_name}")
                                
                                # Pattern 3: Use full slot name if reasonable
                                if not plugin_name and not _should_skip_plugin_name(slot_name):
                                    plugin_name = slot_name
                                    logger.debug(f"[{context}] Using full slot name: {plugin_name}")
                        
                        # Strategy C: Check internal_name for native plugins
                        if not plugin_name and internal_name:
                            if internal_name.lower() != 'fruity wrapper':
                                plugin_name = internal_name
                                is_native = True
                                logger.debug(f"[{context}] Using internal_name (native): {plugin_name}")
                        
                        # Process the found plugin
                        if plugin_name and not _should_skip_plugin_name(plugin_name):
                            # Normalize the name
                            plugin_name = _normalize_plugin_name(plugin_name)
                            
                            # Check if native
                            if not is_native:
                                is_native = _is_native_fl_plugin(plugin_name, internal_name)
                            
                            # Update stats
                            if is_native:
                                stats['native_plugins'] += 1
                            elif plugin_format:
                                stats['vst_plugins'] += 1
                            else:
                                stats['unknown_plugins'] += 1
                            
                            # Create dedup key (use mixer_track + slot for uniqueness)
                            dedup_key = (plugin_name.lower(), 'effect', f"{track_idx}_{slot_idx}")
                            
                            if dedup_key not in seen_plugins:
                                seen_plugins.add(dedup_key)
                                
                                # Get preset name if available
                                preset_name = None
                                try:
                                    if hasattr(slot, 'plugin') and slot.plugin:
                                        p = slot.plugin
                                        for attr in ['preset_name', 'preset']:
                                            if hasattr(p, attr):
                                                val = getattr(p, attr)
                                                if val:
                                                    preset_name = str(val).strip()
                                                    break
                                except:
                                    pass
                                
                                result['plugins'].append({
                                    'name': plugin_name,
                                    'type': 'effect',
                                    'path': plugin_path,
                                    'vendor': plugin_vendor,
                                    'format': plugin_format,
                                    'channel_index': None,
                                    'slot': slot_idx,
                                    'mixer_track': track_idx,
                                    'preset': preset_name,
                                    'is_native': is_native
                                })
                                logger.debug(f"[{context}] Added effect: {plugin_name} "
                                           f"(format={plugin_format}, native={is_native})")
                        else:
                            stats['mixer_slots_skipped'] += 1
            
            # =================================================================
            # 4. Samples
            # =================================================================
            if hasattr(project, 'channels') and project.channels:
                unique_samples: Set[str] = set()
                
                for channel in project.channels:
                    sample_path = None
                    
                    try:
                        if hasattr(channel, 'sample_path'):
                            sample_path = channel.sample_path
                        elif hasattr(channel, 'path'):
                            sample_path = channel.path
                    except:
                        pass
                    
                    if sample_path:
                        sp = str(sample_path)
                        if sp and sp not in unique_samples:
                            unique_samples.add(sp)
                            result['samples'].append({
                                'path': sp,
                                'name': Path(sp).name
                            })
            
            # =================================================================
            # 5. Pattern Count
            # =================================================================
            if hasattr(project, 'patterns'):
                result['pattern_count'] = len(project.patterns)
            
            # =================================================================
            # 6. Store Debug Info
            # =================================================================
            result['_debug_info'] = stats
            
            # =================================================================
            # 7. Log Summary
            # =================================================================
            logger.info(
                f"FLP parsing complete for {Path(flp_path).name}: "
                f"{len(result['plugins'])} plugins found "
                f"(VST: {stats['vst_plugins']}, Native: {stats['native_plugins']}, "
                f"Unknown: {stats['unknown_plugins']}), "
                f"{len(result['samples'])} samples, {result['pattern_count']} patterns"
            )
            
            if self.debug_mode:
                logger.info(f"Debug stats: {stats}")
            
            # =================================================================
            # 8. Optional: Match Against Installed Plugins
            # =================================================================
            if match_installed_plugins and result['plugins']:
                try:
                    from ..database import query
                    installed_rows = query("SELECT name FROM installed_plugins WHERE is_active = 1")
                    installed_plugins = [{'name': row['name']} for row in installed_rows]
                    
                    if installed_plugins:
                        self._match_plugins_to_installed(result['plugins'], installed_plugins)
                except Exception as e:
                    logger.debug(f"Could not match plugins against installed: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing FLP {flp_path}: {e}", exc_info=True)
            return None
    
    def _match_plugins_to_installed(
        self, 
        found_plugins: List[Dict], 
        installed_plugins: List[Dict]
    ):
        """
        Match found plugin names against installed plugins for better accuracy.
        Only matches specific patterns to avoid false positives.
        """
        # Build lookup
        installed_names_lower = {p['name'].lower(): p['name'] for p in installed_plugins}
        
        for plugin in found_plugins:
            original_name = plugin.get('name', '')
            if not original_name:
                continue
            
            original_lower = original_name.lower()
            
            # Skip if already an exact match
            if original_lower in installed_names_lower:
                continue
            
            # Skip native plugins - they don't need matching
            if plugin.get('is_native'):
                continue
            
            # Try common FabFilter abbreviation patterns
            fabfilter_patterns = {
                'q3': ['fabfilter pro-q 3', 'pro-q 3'],
                'q2': ['fabfilter pro-q 2', 'pro-q 2'],
                'pro-q': ['fabfilter pro-q', 'fabfilter pro-q 3', 'fabfilter pro-q 2'],
                'pro-r': ['fabfilter pro-r', 'fabfilter pro-r 2'],
                'pro-l': ['fabfilter pro-l', 'fabfilter pro-l 2'],
                'pro-c': ['fabfilter pro-c', 'fabfilter pro-c 2'],
                'pro-ds': ['fabfilter pro-ds'],
                'pro-mb': ['fabfilter pro-mb'],
                'pro-g': ['fabfilter pro-g'],
            }
            
            # Check if original matches a pattern
            matched = False
            for pattern, candidates in fabfilter_patterns.items():
                if original_lower == pattern or original_lower.startswith(pattern):
                    for candidate in candidates:
                        if candidate in installed_names_lower:
                            plugin['name'] = installed_names_lower[candidate]
                            plugin['matched_from'] = original_name
                            logger.debug(f"Matched '{original_name}' -> '{plugin['name']}'")
                            matched = True
                            break
                if matched:
                    break
            
            # Try partial matching for short names (potential abbreviations)
            if not matched and len(original_name) <= 4:
                for installed_lower, installed_name in installed_names_lower.items():
                    if original_lower in installed_lower:
                        # Require the match to be significant
                        if len(original_lower) >= 2:
                            plugin['name'] = installed_name
                            plugin['matched_from'] = original_name
                            logger.debug(f"Partial match '{original_name}' -> '{installed_name}'")
                            break


# =============================================================================
# Utility Functions for External Use
# =============================================================================

def parse_flp(flp_path: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    """Convenience function to parse an FLP file."""
    parser = FLPParser(debug_mode=debug)
    return parser.parse(flp_path)


def get_project_plugins(flp_path: str) -> List[Dict[str, Any]]:
    """Get list of plugins from an FLP file."""
    result = parse_flp(flp_path)
    return result.get('plugins', []) if result else []


def get_project_samples(flp_path: str) -> List[Dict[str, Any]]:
    """Get list of samples from an FLP file."""
    result = parse_flp(flp_path)
    return result.get('samples', []) if result else []
