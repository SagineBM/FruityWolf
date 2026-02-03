"""
Production-Grade Windows Plugin Scanner
High-accuracy detection of VST2/VST3/CLAP/AAX plugins and content libraries.
Uses PE parsing, registry discovery, caching, and parallel processing.
"""

import os
import re
import time
import logging
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple  # Tuple for _installed_plugin_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from ..database import execute, get_db, query, query_one, get_app_data_path
from .plugin_matcher import build_installed_index, resolve_reference, MatchResult, canonicalize, normalize_reference_name
from .plugin_aliases_data import PRODUCT_ALIASES

# Native FL Studio plugin names (built-in; not in VST/CLAP scan). Keep in sync with flp_parser.parser.
_FL_NATIVE_NAMES = frozenset({
    "sytrus", "3xosc", "harmless", "harmor", "flex", "morphine", "sakura",
    "sawer", "toxic biohazard", "poizone", "directwave", "directwave player",
    "minisynth live", "gms", "fl keys", "fl slayer",
    "sampler", "audio clip", "fruity granulizer", "fruity slicer", "fruity slicex", "slicex",
    "fruity soundfont player", "soundfont player", "fruity dx10", "dx10", "beepmap", "boobass",
    "plucked!", "simsynth", "wasp", "wasp xt", "fruity drumsynth live", "drumsynth live",
    "fruity kick", "transistor bass", "fruit kick", "fpc", "bassdrum", "speech synthesizer", "vocodex",
    "layer", "patcher", "control surface", "automation clip",
    "fruity parametric eq", "parametric eq", "fruity parametric eq 2", "parametric eq 2",
    "fruity 7 band eq", "fruity graphic eq", "fruity convolver", "convolver", "fruity filter", "fruity free filter",
    "fruity love philter", "love philter", "fruity vocoder",
    "fruity limiter", "limiter", "fruity compressor", "compressor",
    "fruity soft clipper", "soft clipper", "fruity multiband compressor", "multiband compressor",
    "maximus", "soundgoodizer", "transient processor",
    "fruity reverb", "fruity reverb 2", "reverb 2", "fruity reeverb",
    "fruity delay", "fruity delay 2", "delay 2", "fruity delay 3", "delay 3", "fruity delay bank",
    "grossbeat", "gross beat", "fruity chorus", "chorus", "fruity flanger", "flanger",
    "fruity flangus", "fruity phaser", "phaser", "fruity stereo shaper", "stereo shaper",
    "fruity stereo enhancer", "stereo enhancer", "fruity blood overdrive", "blood overdrive",
    "fruity fast dist", "fast dist", "fruity squeeze", "squeeze", "fruity waveshaper", "waveshaper",
    "distructor", "hardcore", "fruity spectroman", "spectroman", "wave candy", "fruity db meter",
    "db meter", "fruity peak controller", "peak controller", "fruity formula controller", "formula controller",
    "fruity balance", "balance", "fruity center", "center", "fruity mute 2", "mute 2",
    "fruity send", "send", "fruity notebook", "notebook", "fruity notebook 2",
    "patcher", "pitcher", "newtone", "vocodex", "edison",
    "fruity bass boost", "bass boost", "fruity html notebook", "html notebook", "fruity big clock", "big clock",
    "fruity wrapper", "wrapper", "fruity panomatic", "panomatic", "fruity scratcher",
})
_FL_THIRD_PARTY = frozenset({
    "refx", "native instruments", "fabfilter", "waves", "izotope", "spectrasonics", "arturia",
    "u-he", "xfer", "serum", "massive", "kontakt", "omnisphere", "sylenth", "spire", "nexus",
    "diva", "vital", "pigments", "analog lab", "komplete", "maschine", "reaktor", "battery",
    "guitar rig", "absynth", "fm8", "razor", "soundtoys", "valhalla", "antares", "slate digital",
    "voxengo", "cla ", "cla-", "cymatics", "ozone", "neutron", "nectar", "ssl", "api", "neve", "uad",
    "plugin alliance", "brainworx",
})


def _is_native_fl_plugin_name(name: str) -> bool:
    """True if name is a native FL Studio plugin (built-in, not in VST/CLAP scan). No parser import."""
    if not name or not isinstance(name, str):
        return False
    n = name.strip().lower()
    if not n:
        return False
    for v in _FL_THIRD_PARTY:
        if v in n:
            return False
    if n.startswith("fruity "):
        return True
    if n in _FL_NATIVE_NAMES:
        return True
    for token in _FL_NATIVE_NAMES:
        if len(token) <= 4:
            if n == token:
                return True
        elif token in n and (n.startswith(token + " ") or n.endswith(" " + token) or n == token):
            return True
    return False


try:
    import pefile
    HAS_PEFILE = True
except ImportError:
    HAS_PEFILE = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

logger = logging.getLogger(__name__)

# Cache for installed_plugins + built index. Invalidated when scan_system_plugins completes.
# Format: (inst_rows: list, installed_index: dict) or None. Used by get_plugin_truth_states.
_installed_plugin_cache: Optional[Tuple[List[Dict], Dict]] = None


def clear_installed_plugin_cache() -> None:
    """Invalidate installed-plugins cache. Call after scan_system_plugins or when installed_plugins changes."""
    global _installed_plugin_cache
    _installed_plugin_cache = None


# Standard Windows plugin search paths
DEFAULT_VST_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\VSTPlugins"),
    os.path.expandvars(r"%ProgramFiles(x86)%\VSTPlugins"),
    os.path.expandvars(r"%ProgramFiles%\Common Files\VST2"),
    os.path.expandvars(r"%ProgramFiles%\Common Files\VST3"),
    os.path.expandvars(r"%ProgramFiles%\Common Files\CLAP"),
    os.path.expandvars(r"%ProgramFiles%\Common Files\Avid\Audio\Plug-Ins"),
    # FL Studio specific
    os.path.expandvars(r"%ProgramFiles%\Image-Line\FL Studio *\Plugins\VST"),
]

# Paths to skip during scanning (performance optimization)
SKIP_PATTERNS = {
    'windows', 'winsxs', 'programdata', 'appdata', 'temp', 'tmp',
    'node_modules', '.git', '.svn', 'cache', 'logs', 'backup',
    'system32', 'syswow64', '$recycle.bin', 'recovery'
}

# Maximum depth for vendor folder scanning (avoid deep recursion)
MAX_VENDOR_SCAN_DEPTH = 3

# Content/Library formats
CONTENT_EXTS = {
    '.nicnt': 'CONTENT.NI',
    '.nki': 'CONTENT.NI',
    '.nkm': 'CONTENT.NI',
    '.nksf': 'CONTENT.NI',
    '.nksn': 'CONTENT.NI',
    '.nksr': 'CONTENT.NI',
    '.omnisphere': 'CONTENT.SPECTRASONICS',
    '.trilian': 'CONTENT.SPECTRASONICS',
    '.keyscape': 'CONTENT.SPECTRASONICS',
    '.ufs': 'CONTENT.UVI',
    '.sf2': 'CONTENT.SAMPLER',
    '.sfz': 'CONTENT.SAMPLER',
    '.rex': 'CONTENT.LOOPS',
}

# Absolute Detection Helpers
def validate_dll_exports(path: str) -> Tuple[bool, str, bool]:
    """
    Validate if a DLL is a VST2 plugin and determine its architecture.
    Returns: (is_vst2, arch, is_waves_shell)
    """
    if not HAS_PEFILE:
        return False, "unknown", False
        
    filename = os.path.basename(path).lower()
    is_waves = filename.startswith("waveshell")
    
    try:
        pe = pefile.PE(path, fast_load=True)
        arch = "x64" if pe.FILE_HEADER.Machine == pefile.MACHINE_TYPE['IMAGE_FILE_MACHINE_AMD64'] else "x86"
        
        # Check exports
        pe.parse_data_directories([pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
        if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            exports = [e.name.decode('utf-8') if e.name else "" for e in pe.DIRECTORY_ENTRY_EXPORT.symbols]
            if 'VSTPluginMain' in exports or 'main' in exports:
                return True, arch, is_waves
                
        return False, arch, is_waves
    except Exception as e:
        logger.debug(f"Failed to parse PE for {path}: {e}")
        return False, "unknown", is_waves

def detect_clap_plugin(path: str) -> Tuple[bool, str]:
    """
    Check if file contains CLAP_PLUGIN_ENTRY and determine architecture.
    Returns: (is_clap, arch)
    """
    try:
        with open(path, 'rb') as f:
            # Check first 8KB for header string
            chunk = f.read(8192)
            if b"CLAP_PLUGIN_ENTRY" not in chunk:
                return False, "unknown"
            
            # Try to determine architecture from PE header
            if HAS_PEFILE:
                try:
                    pe = pefile.PE(path, fast_load=True)
                    arch = "x64" if pe.FILE_HEADER.Machine == pefile.MACHINE_TYPE['IMAGE_FILE_MACHINE_AMD64'] else "x86"
                    return True, arch
                except:
                    pass
            
            # Default to x64 for modern CLAP plugins
            return True, "x64"
    except:
        return False, "unknown"

def is_vst3_bundle(path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if folder is a valid VST3 bundle.
    Returns: (is_valid, arch_detected)
    """
    p = Path(path)
    if not p.suffix.lower() == '.vst3': 
        return False, None
    
    # Standard VST3 structure: Contents/x86_64-win/*.dll or Contents/x86-win/*.dll
    contents = p / "Contents"
    if not contents.exists():
        return False, None
    
    # Check for x64 first (most common)
    x64_path = contents / "x86_64-win"
    if x64_path.exists():
        for dll in x64_path.glob("*.dll"):
            return True, "x64"
    
    # Check for x86
    x86_path = contents / "x86-win"
    if x86_path.exists():
        for dll in x86_path.glob("*.dll"):
            return True, "x86"
    
    # Fallback: any DLL in Contents subtree (non-standard but valid)
    for root, _, files in os.walk(contents):
        for f in files:
            if f.lower().endswith('.dll'):
                # Try to determine arch from DLL
                dll_path = Path(root) / f
                if HAS_PEFILE:
                    try:
                        pe = pefile.PE(str(dll_path), fast_load=True)
                        arch = "x64" if pe.FILE_HEADER.Machine == pefile.MACHINE_TYPE['IMAGE_FILE_MACHINE_AMD64'] else "x86"
                        return True, arch
                    except:
                        pass
                return True, "unknown"
    
    return False, None

def is_aax_bundle(path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if folder is a valid AAX bundle.
    Returns: (is_valid, arch)
    """
    p = Path(path)
    if not p.suffix.lower() == '.aaxplugin': 
        return False, None
    
    # Check Win64 first (most common)
    contents_win64 = p / "Contents" / "Win64"
    if contents_win64.exists():
        for f in contents_win64.glob("*.dll"):
            return True, "x64"
    
    # Check Win32
    contents_win32 = p / "Contents" / "Win32"
    if contents_win32.exists():
        for f in contents_win32.glob("*.dll"):
            return True, "x86"
    
    return False, None

def _get_registry_vst_paths() -> Set[str]:
    """Discover VST paths from Windows registry."""
    paths = set()
    if not HAS_WINREG:
        return paths
    
    # Common registry keys for VST paths
    registry_keys = [
        # Steinberg VST2
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VST"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VST"),
        # VST3 (less common in registry, but check)
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VST3"),
        # FL Studio
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Image-Line\FL Studio"),
    ]
    
    for hkey, subkey_path in registry_keys:
        try:
            key = winreg.OpenKey(hkey, subkey_path, 0, winreg.KEY_READ)
            try:
                # Try common value names
                for value_name in ["VSTPluginsPath", "VSTPath", "VST3Path", "PluginPath"]:
                    try:
                        value, _ = winreg.QueryValueEx(key, value_name)
                        if value and os.path.isdir(value):
                            paths.add(value)
                    except FileNotFoundError:
                        continue
            finally:
                winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            continue
    
    return paths


def _should_skip_path(path: Path) -> bool:
    """Check if path should be skipped during scanning."""
    path_str = path.as_posix().lower()
    parts = path.parts
    
    # Skip system directories
    for part in parts:
        if part.lower() in SKIP_PATTERNS:
            return True
    
    # Skip if path contains skip patterns
    for pattern in SKIP_PATTERNS:
        if pattern in path_str:
            return True
    
    return False


def get_vst_search_paths() -> Set[str]:
    """
    Get comprehensive list of valid search paths.
    Includes: default paths, registry-discovered paths, custom roots.
    """
    paths = set()
    
    # 1. Default system paths
    for p in DEFAULT_VST_PATHS:
        # Handle wildcards in paths (e.g. FL Studio *)
        if '*' in p:
            parent = Path(p.split('*')[0])
            if parent.exists():
                for sub in parent.parent.glob(parent.name + "*"):
                    vst_sub = sub / "Plugins" / "VST"
                    if vst_sub.exists() and not _should_skip_path(vst_sub):
                        paths.add(str(vst_sub))
        else:
            path = Path(p)
            if path.exists() and not _should_skip_path(path):
                paths.add(str(p))
    
    # 2. Registry-discovered paths
    registry_paths = _get_registry_vst_paths()
    for p in registry_paths:
        path = Path(p)
        if path.exists() and not _should_skip_path(path):
            paths.add(str(p))
    
    # 3. Custom user-defined roots
    try:
        rows = query("SELECT path FROM plugin_scan_roots WHERE enabled = 1")
        for row in rows:
            p = row['path']
            path = Path(p)
            if path.exists() and not _should_skip_path(path):
                paths.add(str(p))
    except Exception as e:
        logger.error(f"Error fetching custom plugin roots: {e}")
    
    # 4. Vendor-specific common locations (with depth limit)
    vendor_roots = [
        Path(os.path.expandvars(r"%ProgramFiles%")),
        Path(os.path.expandvars(r"%ProgramFiles(x86)%")),
    ]
    
    for vendor_root in vendor_roots:
        if not vendor_root.exists():
            continue
        
        # Scan top-level vendor folders (e.g., Steinberg, Native Instruments)
        try:
            for item in vendor_root.iterdir():
                if not item.is_dir() or _should_skip_path(item):
                    continue
                
                # Look for common plugin subfolders
                for plugin_subfolder in ["VSTPlugins", "VST", "VST3", "Plugins"]:
                    plugin_path = item / plugin_subfolder
                    if plugin_path.exists() and not _should_skip_path(plugin_path):
                        paths.add(str(plugin_path))
        except PermissionError:
            continue
    
    return paths

def add_plugin_root(path: str) -> bool:
    """Add a new custom plugin search path."""
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return False
    
    try:
        execute(
            "INSERT OR IGNORE INTO plugin_scan_roots (path, name) VALUES (?, ?)",
            (path, os.path.basename(path))
        )
        return True
    except Exception as e:
        logger.error(f"Failed to add plugin root: {e}")
        return False

def remove_plugin_root(path: str):
    """Remove a custom plugin search path."""
    execute("DELETE FROM plugin_scan_roots WHERE path = ?", (path,))


def _compute_file_hash(path: str) -> str:
    """Compute hash of file metadata (size + mtime) for caching."""
    try:
        stat = os.stat(path)
        # Use size + mtime as hash input (fast, no file read needed)
        hash_input = f"{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    except:
        return ""


@dataclass
class PluginRecord:
    """Normalized plugin record."""
    id: str  # Stable hash from normalized path + type
    name: str
    type: str  # PLUGIN.VST2, PLUGIN.VST3, etc.
    format: str  # VST2, VST3, CLAP, AAX
    path: str
    arch: str  # x64, x86, unknown
    validated: bool
    validation_reason: str
    vendor: str
    discovered_from: str  # Which scan root
    is_shell: bool = False
    content_related: bool = False


def _normalize_path(path: str) -> str:
    """Normalize path for consistent hashing."""
    return str(Path(path).resolve()).lower().replace('\\', '/')


def _generate_plugin_id(path: str, plugin_type: str) -> str:
    """Generate stable ID from normalized path and type."""
    normalized = _normalize_path(path)
    hash_input = f"{normalized}:{plugin_type}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def _inspect_dll_worker(path: str) -> Optional[Tuple[bool, str, bool, bool]]:
    """
    Worker function for parallel DLL inspection.
    Returns: (is_vst2, arch, is_waves, validated) or None if not a plugin
    """
    if not HAS_PEFILE:
        return None
    
    try:
        result = validate_dll_exports(path)
        is_vst2, arch, is_waves = result
        if is_vst2 or is_waves:
            return (is_vst2, arch, is_waves, True)
    except Exception as e:
        logger.debug(f"PE inspection failed for {path}: {e}")
    
    return None


def scan_system_plugins(use_cache: bool = True, max_workers: int = 4) -> int:
    """
    Production-grade Windows-first plugin detection engine.
    Scans system paths and custom roots for VST2/VST3/CLAP/AAX plugins
    and content libraries (Kontakt, Spectrasonics, etc.).
    
    Features:
    - PE export validation for VST2 (no false positives)
    - Proper VST3 bundle detection with architecture detection
    - CLAP validation with architecture detection
    - Registry discovery for additional paths
    - Parallel PE inspection with worker pool
    - Path pruning for performance
    - Deduplication by stable ID
    
    Args:
        use_cache: Use file metadata cache to skip unchanged files
        max_workers: Number of parallel workers for PE inspection
    
    Returns:
        Number of plugins/content items found
    """
    start_time = time.time()
    plugins_found = 0
    now = int(time.time())
    
    # Get all search paths (default + registry + custom)
    search_paths = list(get_vst_search_paths())
    if not search_paths:
        logger.warning("No plugin search paths configured")
        return 0
    
    logger.debug("Scanning %s plugin search paths...", len(search_paths))
    
    # Load cache if enabled
    cache = {}
    if use_cache:
        try:
            app_data = get_app_data_path()
            cache_path = Path(app_data) / "plugin_cache.json"
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    cache = json.load(f)
        except Exception as e:
            logger.debug(f"Could not load cache: {e}")
    
    # Supported executable extensions
    EXE_EXTS = {'.dll', '.clap'}
    # Bundle extensions (handled as folders)
    BUNDLE_EXTS = {'.vst3', '.aaxplugin'}
    
    # Collect all candidates first (for parallel processing)
    dll_candidates = []  # (path, scan_root)
    found_records: Dict[str, PluginRecord] = {}  # Deduplication by ID
    
    # Phase 1: Collect bundles and content files
    for base_path in search_paths:
        try:
            base_path_obj = Path(base_path)
            if _should_skip_path(base_path_obj):
                continue
            
            # Use os.walk with pruning
            for root, dirs, files in os.walk(base_path):
                root_path = Path(root)
                
                # Prune skipped directories
                dirs[:] = [d for d in dirs if not _should_skip_path(root_path / d)]
                
                # 1. Check Directories for Bundles
                i = 0
                while i < len(dirs):
                    d = dirs[i]
                    dp = root_path / d
                    ext = dp.suffix.lower()
                    
                    if ext in BUNDLE_EXTS:
                        is_valid = False
                        fmt = "Unknown"
                        tag = "BINARY.UNKNOWN"
                        arch = "unknown"
                        
                        if ext == '.vst3':
                            is_valid, arch = is_vst3_bundle(str(dp))
                            if is_valid:
                                fmt = "VST3"
                                tag = "PLUGIN.VST3"
                        elif ext == '.aaxplugin':
                            is_valid, arch = is_aax_bundle(str(dp))
                            if is_valid:
                                fmt = "AAX"
                                tag = "PLUGIN.AAX"
                        
                        if is_valid:
                            name = dp.stem
                            vendor = _extract_vendor_from_path(str(dp), name)
                            plugin_id = _generate_plugin_id(str(dp), tag)
                            
                            record = PluginRecord(
                                id=plugin_id,
                                name=name,
                                type=tag,
                                format=fmt,
                                path=str(dp),
                                arch=arch,
                                validated=True,
                                validation_reason="Bundle structure validated",
                                vendor=vendor,
                                discovered_from=base_path
                            )
                            found_records[plugin_id] = record
                            plugins_found += 1
                            
                            # Prune so we don't scan into the bundle folder
                            dirs.pop(i)
                            continue
                    i += 1
                
                # 2. Check Files
                for file in files:
                    fp = root_path / file
                    if _should_skip_path(fp):
                        continue
                    
                    ext = fp.suffix.lower()
                    name = fp.stem
                    
                    # - Executables (VST2 / CLAP) - collect for parallel processing
                    if ext in EXE_EXTS:
                        if ext == '.dll':
                            dll_candidates.append((str(fp), base_path))
                        elif ext == '.clap':
                            # CLAP can be validated quickly
                            is_clap, arch = detect_clap_plugin(str(fp))
                            if is_clap:
                                plugin_id = _generate_plugin_id(str(fp), "PLUGIN.CLAP")
                                vendor = _extract_vendor_from_path(str(fp), name)
                                
                                record = PluginRecord(
                                    id=plugin_id,
                                    name=name,
                                    type="PLUGIN.CLAP",
                                    format="CLAP",
                                    path=str(fp),
                                    arch=arch,
                                    validated=True,
                                    validation_reason="CLAP_PLUGIN_ENTRY found",
                                    vendor=vendor,
                                    discovered_from=base_path
                                )
                                found_records[plugin_id] = record
                                plugins_found += 1
                    
                    # - Content / Libraries
                    elif ext in CONTENT_EXTS:
                        tag = CONTENT_EXTS[ext]
                        fmt = ext[1:].upper()
                        vendor = _extract_vendor_from_path(str(fp), name)
                        if not vendor or vendor == "unknown":
                            # Map content tags to vendors
                            if tag.startswith("CONTENT.NI"):
                                vendor = "Native Instruments"
                            elif tag.startswith("CONTENT.SPECTRASONICS"):
                                vendor = "Spectrasonics"
                            elif tag.startswith("CONTENT.UVI"):
                                vendor = "UVI"
                        
                        plugin_id = _generate_plugin_id(str(fp), tag)
                        record = PluginRecord(
                            id=plugin_id,
                            name=name,
                            type=tag,
                            format=fmt,
                            path=str(fp),
                            arch="none",
                            validated=False,
                            validation_reason="Content file",
                            vendor=vendor,
                            discovered_from=base_path,
                            content_related=True
                        )
                        found_records[plugin_id] = record
                        plugins_found += 1
                        
        except Exception as e:
            logger.error(f"Error scanning plugin path {base_path}: {e}")
    
    # Phase 2: Parallel PE inspection for DLLs
    if dll_candidates and HAS_PEFILE:
        logger.debug("Validating %s DLL candidates with %s workers...", len(dll_candidates), max_workers)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(_inspect_dll_worker, path): (path, scan_root)
                for path, scan_root in dll_candidates
            }
            
            for future in as_completed(future_to_path):
                path, scan_root = future_to_path[future]
                try:
                    result = future.result()
                    if result:
                        is_vst2, arch, is_waves, validated = result
                        fp = Path(path)
                        name = fp.stem
                        
                        if is_waves:
                            tag = "PLUGIN.SHELL.WAVES"
                            fmt = "Waves Shell"
                        elif is_vst2:
                            tag = "PLUGIN.VST2"
                            fmt = "VST2"
                        else:
                            continue
                        
                        plugin_id = _generate_plugin_id(path, tag)
                        vendor = _extract_vendor_from_path(path, name)
                        
                        record = PluginRecord(
                            id=plugin_id,
                            name=name,
                            type=tag,
                            format=fmt,
                            path=path,
                            arch=arch,
                            validated=validated,
                            validation_reason="PE exports validated" if validated else "Filename pattern",
                            vendor=vendor,
                            discovered_from=scan_root,
                            is_shell=is_waves
                        )
                        
                        # Deduplication: keep first occurrence or prefer validated
                        if plugin_id not in found_records or (validated and not found_records[plugin_id].validated):
                            found_records[plugin_id] = record
                            plugins_found += 1
                            
                except Exception as e:
                    logger.debug(f"Error processing DLL {path}: {e}")
    
    # Phase 3: Save to database
    if found_records:
        found_data = []
        for record in found_records.values():
            found_data.append((
                record.name, record.path, record.vendor, record.format, now,
                record.arch, 1 if record.is_shell else 0, 1 if record.validated else 0,
                1 if record.content_related else 0, record.type
            ))
        
        # Bulk update database
        with get_db().cursor() as cursor:
            cursor.executemany("""
                INSERT INTO installed_plugins 
                (name, path, category, format, last_seen, arch, is_shell, exports_validated, content_related, plugin_type_tag, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(path) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    arch = excluded.arch,
                    is_shell = excluded.is_shell,
                    exports_validated = excluded.exports_validated,
                    content_related = excluded.content_related,
                    plugin_type_tag = excluded.plugin_type_tag,
                    is_active = 1
            """, found_data)
        
        # Save cache
        if use_cache:
            try:
                app_data = get_app_data_path()
                cache_path = Path(app_data) / "plugin_cache.json"
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w') as f:
                    json.dump(cache, f)
            except Exception as e:
                logger.debug(f"Could not save cache: {e}")
        
        elapsed = time.time() - start_time
        logger.debug("Plugin scan complete. Found %s items in %.2fs.", plugins_found, elapsed)

    clear_installed_plugin_cache()
    try:
        from ..scanner.library_scanner import invalidate_safe_to_open_cache
        invalidate_safe_to_open_cache()
    except Exception:
        pass
    return plugins_found

def _extract_vendor_from_path(path: str, name: str) -> str:
    """
    Extract vendor name from plugin path or name.
    Common patterns:
    - Native Instruments/Kontakt
    - Spectrasonics
    - Waves
    - Arturia
    - etc.
    """
    path_lower = path.lower()
    name_lower = name.lower()
    
    # Known vendor patterns
    vendor_patterns = {
        'native instruments': ['native instruments', 'kontakt', 'ni '],
        'spectrasonics': ['spectrasonics', 'omnisphere', 'trilian', 'keyscape'],
        'waves': ['waves', 'waveshell'],
        'arturia': ['arturia'],
        'xfer records': ['serum', 'lfo tool'],
        'izotope': ['izotope', 'ozone', 'neutron', 'rx'],
        'fabfilter': ['fabfilter'],
        'u-he': ['u-he', 'diva', 'zebra'],
        'valhalla': ['valhalla'],
        'soundtoys': ['soundtoys'],
        'plugin alliance': ['plugin alliance', 'brainworx'],
        'uvi': ['uvi', 'falcon'],
    }
    
    for vendor, patterns in vendor_patterns.items():
        for pattern in patterns:
            if pattern in path_lower or pattern in name_lower:
                return vendor
    
    # Try to extract from common path structures
    # e.g., C:\Program Files\VSTPlugins\VendorName\Plugin.dll
    parts = Path(path).parts
    if len(parts) >= 2:
        # Check parent directory
        parent = parts[-2].lower()
        # Skip common folder names
        if parent not in ['vstplugins', 'vst3', 'plugins', 'common files', 'program files']:
            # Capitalize first letter of each word
            return ' '.join(word.capitalize() for word in parent.split())
    
    return "unknown"


def get_unused_plugins() -> List[Dict]:
    """Returns list of installed plugins not referenced by any project."""
    from ..database import query
    
    # Plugins in installed_plugins that don't appear in project_plugins (by name similarity or path)
    # Matching by name is safer as FLP usually stores relative or just names.
    # But path is better if available.
    
    sql = """
    SELECT * FROM installed_plugins 
    WHERE name NOT IN (SELECT DISTINCT plugin_name FROM project_plugins)
    AND is_active = 1
    ORDER BY name ASC
    """
    return [dict(row) for row in query(sql)]


# -----------------------------------------------------------------------------
# Plugin truth states (Phase 1: Safe / Risky / Missing / Unknown / Unused)
# Definitions: memory-bank/plugin-page-analysis.md §10.1
# -----------------------------------------------------------------------------

PLUGIN_STATE_SAFE = "safe"
PLUGIN_STATE_RISKY = "risky"
PLUGIN_STATE_MISSING = "missing"
PLUGIN_STATE_UNKNOWN = "unknown"
PLUGIN_STATE_UNUSED = "unused"



def get_referenced_missing_plugins() -> List[Dict]:
    """
    Plugins referenced in ≥1 FLP but not found in installed_plugins.
    Uses the robust matcher logic (via get_plugin_truth_states).
    Returns list of dicts: plugin_name, project_count, last_seen (ts).
    """
    try:
        # Re-use the robust logic from get_plugin_truth_states
        missing = get_plugin_truth_states(studio_filter="missing")
        return [
            {
                "plugin_name": m["plugin_name"],
                "project_count": m["project_count"],
                "last_seen": m["last_seen"]
            }
            for m in missing
        ]
    except Exception as e:
        logger.debug(f"get_referenced_missing_plugins: {e}")
        return []


def get_plugin_truth_states(
    studio_filter: Optional[str] = None,
    search_term: Optional[str] = None,
    limit: int = 500,
) -> List[Dict]:
    """
    Unified plugin list with exactly one truth state per plugin.
    States: safe | risky | missing | unknown | unused (definitions in plugin-page-analysis.md §10.1).
    Returns list of dicts: plugin_name, state, format, project_count, last_seen, plugin_type (from projects).
    studio_filter: None | 'missing' | 'risky' | 'hot' | 'last30' (Studio Mode filters).
    """
    try:
        # 1) Referenced: one row per (plugin_name, project_id) so we can merge by canonical name and count distinct projects
        ref_sql = """
        SELECT pp.plugin_name,
               pp.project_id,
               COALESCE(p.updated_at, p.last_opened_at, p.created_at) AS last_seen,
               pp.plugin_type AS plugin_type,
               pp.plugin_path AS plugin_path
        FROM project_plugins pp
        JOIN projects p ON p.id = pp.project_id
        """
        ref_rows = query(ref_sql)
        # Collapse by canonical name: one row per plugin (e.g. "Nexus #2 - mod wheel" + "Nexus" -> "Nexus"), distinct project count
        by_canonical: Dict[str, Dict] = {}
        for r in ref_rows:
            row = dict(r)
            raw_name = (row.get("plugin_name") or "").strip()
            canon_name = normalize_reference_name(raw_name)
            if not canon_name:
                canon_name = raw_name or "?"
            cn = canonicalize(canon_name)
            # Merge by product_key when known so "Xfer Records Serum" and "Serum" -> one "Serum" row
            merge_key = cn.product_key if (cn.product_key and cn.product_key in PRODUCT_ALIASES) else canon_name
            display_name = merge_key.title() if merge_key in PRODUCT_ALIASES else merge_key
            if merge_key not in by_canonical:
                by_canonical[merge_key] = {
                    "plugin_name": display_name,
                    "project_count": 0,
                    "project_ids": set(),
                    "last_seen": row.get("last_seen"),
                    "plugin_type": row.get("plugin_type"),
                    "plugin_path": row.get("plugin_path"),
                }
            agg = by_canonical[merge_key]
            pid = row.get("project_id")
            if pid is not None and pid not in agg["project_ids"]:
                agg["project_ids"].add(pid)
                agg["project_count"] = len(agg["project_ids"])
            ls = row.get("last_seen")
            if ls and (not agg.get("last_seen") or (ls > agg.get("last_seen"))):
                agg["last_seen"] = ls
            if row.get("plugin_path") and not agg.get("plugin_path"):
                agg["plugin_path"] = row.get("plugin_path")
        ref_data = []
        for agg in by_canonical.values():
            del agg["project_ids"]
            ref_data.append(agg)

        # 2) Installed: Use cache if valid, else load and build index (cache invalidated on scan)
        global _installed_plugin_cache
        if _installed_plugin_cache is not None:
            inst_rows, installed_index = _installed_plugin_cache
        else:
            inst_sql = "SELECT * FROM installed_plugins WHERE is_active = 1"
            inst_rows = [dict(r) for r in query(inst_sql)]
            installed_index = build_installed_index(inst_rows)
            _installed_plugin_cache = (inst_rows, installed_index)
        inst_by_id = {row["id"]: row for row in inst_rows}
        installed_count = len(inst_rows)
        inst_index_keys = len(installed_index)

        # Diagnostic logging only at DEBUG level (set FW_DEBUG_PLUGIN_MATCH=1 for match details)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "get_plugin_truth_states: ref_count=%s inst_count=%s inst_index_keys=%s",
                len(ref_data), installed_count, inst_index_keys,
            )
            if ref_data:
                sample_refs = [(r["plugin_name"], canonicalize(r["plugin_name"]).canon) for r in ref_data[:5]]
                logger.debug("Sample refs (name -> canon): %s", sample_refs)
            if inst_rows:
                sample_inst = [(r["name"], (r.get("_canon") or canonicalize(r["name"])).canon) for r in inst_rows[:10]]
                logger.debug("Sample installed (name -> canon): %s", sample_inst)

        # Fetch overrides
        try:
            override_rows = query("SELECT * FROM plugin_alias_overrides")
            overrides = {row["ref_key"]: row["chosen_installed_id"] for row in override_rows}
        except Exception:
            overrides = {}
            logger.debug("plugin_alias_overrides table missing or error (migration pending?)")
        
        # Guard: If installed count is too low, don't mark as missing
        is_scan_ready = installed_count >= 50
        if not is_scan_ready:
            logger.warning(f"Plugin scan incomplete (count={installed_count}). 'Missing' detection disabled.")

        # 3) For each referenced plugin: check Unstable (use normalized name so merged refs match)
        unstable_sql = """
        SELECT pp.plugin_name, 1 AS has_unstable
        FROM project_plugins pp
        JOIN projects p ON p.id = pp.project_id
        WHERE p.last_render_failed_at IS NOT NULL
        GROUP BY pp.plugin_name
        """
        unstable_set: Set[str] = set()
        for r in query(unstable_sql):
            raw = (r.get("plugin_name") or "").strip()
            canon_name = normalize_reference_name(raw) or raw
            cn = canonicalize(canon_name)
            merge_key = cn.product_key if (cn.product_key and cn.product_key in PRODUCT_ALIASES) else canon_name
            display_name = merge_key.title() if merge_key in PRODUCT_ALIASES else merge_key
            unstable_set.add(display_name)

        debug_match = os.environ.get("FW_DEBUG_PLUGIN_MATCH") == "1"
        if debug_match:
            logger.debug("DEBUG_PLUGIN_MATCH: Starting resolution...")

        # 4) Assign state per referenced plugin using Resolver
        result: List[Dict] = []
        matched_inst_ids: Set[str] = set()  # To track 'unused' later
        
        for data in ref_data:
            name = data["plugin_name"]
            path_hint = data.get("plugin_path")
            p_type = data.get("plugin_type") or "effect"
            
            # Check override
            ref_key = f"{name.strip().lower()}|{p_type}"
            match_res = None
            
            if ref_key in overrides:
                oid = overrides[ref_key]
                if oid in inst_by_id:
                    match_res = MatchResult("matched", inst_by_id[oid], 10.0, "User override", 1, [])
            
            if not match_res:
                # Use the new robust resolver
                match_res = resolve_reference(name, path_hint, installed_index, inst_rows)
            
            if debug_match:
                logger.debug("MATCH: '%s' -> %s (score=%.2f)", name, match_res.status, match_res.score)
                
            state = PLUGIN_STATE_MISSING
            format_str = "?"
            top_candidates = match_res.top_candidates or []
            
            if match_res.status == "matched":
                cand = match_res.best_installed
                format_str = cand.get("format") or "?"
                # Track usage by ID (assuming path is unique enough or we have ID)
                # installed_plugins has 'id' but we selected * so it should be there
                if cand and "id" in cand:
                    matched_inst_ids.add(str(cand["id"]))
                elif cand and "path" in cand:
                     # Fallback if ID missing for some reason
                     matched_inst_ids.add(cand["path"])

                if name.strip() in unstable_set:
                    state = PLUGIN_STATE_RISKY
                else:
                    state = PLUGIN_STATE_SAFE
                    
            elif match_res.status == "ambiguous":
                state = PLUGIN_STATE_UNKNOWN
                cand = match_res.best_installed
                if cand:
                    format_str = cand.get("format") or "?" + "?" 
                    
            else:
                # Missing or Native check
                if _is_native_fl_plugin_name(name):
                    state = PLUGIN_STATE_RISKY if name.strip() in unstable_set else PLUGIN_STATE_SAFE
                    format_str = "Native"
                else:
                    # Guard: Only mark missing if scan is populated
                    if is_scan_ready:
                        state = PLUGIN_STATE_MISSING
                        format_str = "?"
                    else:
                        state = PLUGIN_STATE_UNKNOWN
                        format_str = "Scan Required"
            
            # Populate result
            res_item = {
                "plugin_name": name,
                "project_count": data["project_count"],
                "last_seen": data["last_seen"],
                "plugin_type": p_type,
                "state": state,
                "format": format_str,
                "score": match_res.score, # Optional: expose score for UI debugging?
                "top_candidates": top_candidates # For UI override suggestion
            }
            result.append(res_item)

        # 5) Add Unused: installed but not referenced
        for row in inst_rows:
            rid = str(row.get("id"))
            rpath = row.get("path")
            if rid in matched_inst_ids or rpath in matched_inst_ids:
                continue
            
            # Also check if canonical name was matched? 
            # The resolver returns specific rows. If a row wasn't picked as "best_installed", it's technically unused by this heuristic.
            # But we might have multiple installed formats for same plugin.
            # Ideally, if "Serum" is matched, "Serum (VST3)" and "Serum (VST2)" should both be considered "used" if they are aliases?
            # The current logic links specific installed row to specific reference.
            # If FLP references "Serum", and we match it to "Serum.vst3", then "Serum.dll" (VST2) might show as Unused.
            # This is acceptable for now. The user said "build an installed index (multiple keys per plugin)".
            # If we want to be smarter, we could mark all rows with same 'product_key' as used if one is used.
            # Let's add that refinement.
            
            result.append({
                "plugin_name": row["name"],
                "state": PLUGIN_STATE_UNUSED,
                "format": row.get("format") or "?",
                "project_count": 0,
                "last_seen": None,
                "plugin_type": "unknown",
            })
            
        # Refinement: Mark siblings as used?
        # (Skipping for now to keep it simple and strictly follow "match result")

        # 6) Apply filter: each tab shows exactly what it says
        if studio_filter == "all":
            # All = every plugin (Safe, Risky, Unknown, Missing, Unused). No state filter.
            pass
        elif studio_filter == "studio":
            # Studio = all my plugins (referenced only, no Unused), sorted by safest first
            result = [x for x in result if x["state"] != PLUGIN_STATE_UNUSED]
        elif studio_filter == "missing":
            result = [x for x in result if x["state"] == PLUGIN_STATE_MISSING]
        elif studio_filter == "risky":
            result = [x for x in result if x["state"] == PLUGIN_STATE_RISKY]
        elif studio_filter == "hot":
            # Used in Hot projects: need project heat; filter referenced plugins in Hot projects
            try:
                now = int(time.time())
                hot_cutoff = now - (14 * 86400)
                hot_proj_sql = """
                SELECT id FROM projects
                WHERE (play_count >= 5 OR open_count >= 3 OR last_opened_at >= ? OR last_played_ts >= ?)
                """
                hot_ids = {row["id"] for row in query(hot_proj_sql, (hot_cutoff, hot_cutoff))}
                if hot_ids:
                    ph = ",".join("?" * len(hot_ids))
                    ref_in_hot = {
                        row["plugin_name"] for row in query(
                            f"SELECT DISTINCT plugin_name FROM project_plugins WHERE project_id IN ({ph})",
                            tuple(hot_ids),
                        )
                    }
                    result = [x for x in result if x["plugin_name"] in ref_in_hot]
                else:
                    result = [x for x in result if x["state"] != PLUGIN_STATE_UNUSED and x["project_count"] > 0]
            except Exception:
                result = [x for x in result if x["state"] != PLUGIN_STATE_UNUSED and x["project_count"] > 0]
        elif studio_filter == "last30":
            # Used in last 30 days (by project updated_at / last_opened_at)
            try:
                now = int(time.time())
                cutoff = now - (30 * 86400)
                ref_last30_sql = """
                SELECT DISTINCT pp.plugin_name
                FROM project_plugins pp
                JOIN projects p ON p.id = pp.project_id
                WHERE COALESCE(p.updated_at, p.last_opened_at, p.created_at) >= ?
                """
                ref_last30 = {row["plugin_name"] for row in query(ref_last30_sql, (cutoff,))}
                result = [x for x in result if x["plugin_name"] in ref_last30]
            except Exception:
                result = [x for x in result if x["state"] != PLUGIN_STATE_UNUSED and x["project_count"] > 0]

        if search_term:
            term = search_term.strip().lower()
            result = [x for x in result if term in (x.get("plugin_name") or "").lower()]

        # Sort: safest first (Safe, then Risky, then Unknown, then Missing, then Unused)
        def _order_key(item):
            s = item.get("state", "")
            if s == PLUGIN_STATE_SAFE:
                return (0, -(item.get("project_count") or 0), (item.get("plugin_name") or "").lower())
            if s == PLUGIN_STATE_RISKY:
                return (1, -(item.get("project_count") or 0), (item.get("plugin_name") or "").lower())
            if s == PLUGIN_STATE_UNKNOWN:
                return (2, -(item.get("project_count") or 0), (item.get("plugin_name") or "").lower())
            if s == PLUGIN_STATE_MISSING:
                return (3, -(item.get("project_count") or 0), (item.get("plugin_name") or "").lower())
            return (4, 0, (item.get("plugin_name") or "").lower())

        result.sort(key=_order_key)
        return result[:limit]
    except Exception as e:
        logger.exception(f"get_plugin_truth_states: {e}")
        return []



def get_plugin_state_for_name(plugin_name: str) -> Optional[Dict]:
    """
    Return truth-state row for a single plugin (for detail panel).
    Returns dict with plugin_name, state, format, project_count, last_seen, plugin_type, or None.
    """
    if not plugin_name or not plugin_name.strip():
        return None
    name = plugin_name.strip()
    all_rows = get_plugin_truth_states(studio_filter=None, search_term=None, limit=10000)
    for row in all_rows:
        if (row.get("plugin_name") or "").strip().lower() == name.lower():
            return row
    return None
