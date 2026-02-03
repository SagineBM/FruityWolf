"""
Plugin matching engine with evidence scoring.
Resolves referenced plugin names (from FLP) to installed plugins using:
- Canonical normalization (strong cleaning)
- Vendor and product aliasing
- Token-based scoring (Jaccard + bonuses)
- Path hints (if available)
- Ambiguity handling (Unknown vs Missing)
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# --- Configuration & Constants (extended data in plugin_aliases_data.py) ---
from .plugin_aliases_data import VENDOR_ALIASES, PRODUCT_ALIASES, TOKEN_REWRITES

STOP_TOKENS = {
    "audio", "plugin", "stereo", "mono", "effect", "generator", 
    "vst", "vst2", "vst3", "clap", "aax", "au", "component",
    "x64", "x86", "64", "32", "bit", "bridge", "bridged", "demo",
    "edition", "version", "ver", "v",
    "llc", "ltd", "inc",  # company suffixes in ref names (e.g. "Valhalla DSP, LLC")
}

GENERIC_TOKENS = {
    "compressor", "limiter", "eq", "equalizer", "reverb", "delay", "filter", 
    "chorus", "flanger", "phaser", "distortion", "saturation", "utility", 
    "gate", "expander", "multiband", "analyzer", "meter", "tuner", "sampler"
}

# --- Data Structures ---

@dataclass
class CanonicalName:
    raw: str
    canon: str
    tokens: Set[str]
    tokens_no_vendor: Set[str]
    vendor_tokens: Set[str]
    version: Optional[str]
    arch: Optional[str]
    product_key: Optional[str]

@dataclass
class MatchResult:
    status: str  # 'matched', 'ambiguous', 'missing', 'native'
    best_installed: Optional[Dict[str, Any]]
    score: float
    reason: str
    candidates_checked: int
    top_candidates: List[Dict[str, Any]] = None


# --- Reference name cleaning (FL stores instance/param junk; we want base plugin name for matching) ---

def normalize_reference_name(name: str) -> str:
    """
    Strip FL-style instance/parameter/slot suffixes from a referenced plugin name
    so "Nexus #2 - mod wheel" and "ValhallaDelay (Insert 13) - Mix level" collapse to
    "Nexus" / "ValhallaDelay" for matching. Use for ref names from DB or parser.
    """
    if not name or not isinstance(name, str):
        return (name or "").strip()
    s = name.strip()
    # (Slot N) - ... to end
    s = re.sub(r"\s*\(Slot\s*\d+\)\s*-.*$", "", s, flags=re.IGNORECASE).strip()
    # (Insert N)
    s = re.sub(r"\s*\(Insert\s*\d+\)\s*$", "", s, flags=re.IGNORECASE).strip()
    # Instance #N anywhere (Nexus #1, Nexus #2 -> Nexus)
    s = re.sub(r"\s*#\d+\s*", " ", s).strip()
    # (Mono) / (Stereo)
    s = re.sub(r"\s*\((?:Mono|Stereo)\)\s*$", "", s, flags=re.IGNORECASE).strip()
    # Trailing " - <param>" in one go (include hyphens: " - flt-mod velocity" -> strip all)
    while True:
        m = re.search(r"\s+-\s+(.+)$", s)
        if not m:
            break
        after = m.group(1).strip().lower()
        if re.match(r"^pro[- ]?[qclrgmbds]\s*\d*", after) or (len(after) <= 4 and re.search(r"\d", after)):
            break
        s = s[: -len(m.group(0))].strip()
    return " ".join(s.split())


# --- Core Functions ---

def canonicalize(name: str) -> CanonicalName:
    """
    Normalize plugin name into canonical form with tokens and metadata.
    deterministic and aggressive.
    """
    if not name:
        return CanonicalName("", "", set(), set(), set(), None, None, None)
    
    raw = name
    s = (name or "").strip()
    # Strip zero-width and other invisible chars that break matching
    s = "".join(c for c in s if c.isprintable() or c.isspace())
    s = s.lower().strip()

    # Token rewrite rules (before alias lookup) so canon aligns ref vs installed
    REWRITES = [
        ("nativeinstruments", "native instruments"),
        ("kontakt7", "kontakt 7"),
        ("serum_x64", "serum"),
        ("serum x64", "serum"),
        ("xferrecords", "xfer"),
        ("xfer records", "xfer"),
        ("fabfilter", "fab filter"),
        ("soundtoys", "sound toys"),
        ("valhalladsp", "valhalla dsp"),
        ("imageline", "image line"),
        # Valhalla camelCase product names (FL stores "Valhalla DSP, LLC ValhallaDelay")
        ("valhalladelay", "valhalla delay"),
        ("valhallavintageverb", "valhalla vintage verb"),
        ("valhallashimmer", "valhalla shimmer"),
        ("valhallaroom", "valhalla room"),
        ("valhallasupermassive", "valhalla supermassive"),
        ("valhallaplate", "valhalla plate"),
    ]
    for old, new in REWRITES:
        if old in s:
            s = s.replace(old, new)

    # 1. Extract Architecture
    arch = None
    if re.search(r'(_x64| x64|\(x64\)| 64bit| 64-bit| 64 bit)', s):
        arch = "x64"
    elif re.search(r'(_x86| x86|\(x86\)| 32bit| 32-bit| 32 bit)', s):
        arch = "x86"
        
    # 2. Strip Junk (prefixes, suffixes, bracket groups)
    # Prefixes - Rule A
    # Also strip "wrapper" prefixes
    s = re.sub(r'^(vst3:|vst2:|vst:|clap:|aax:|fruity wrapper\s+|wrapper\s+)', '', s)
    
    # File extensions - Rule C
    s = re.sub(r'\.(dll|vst3|clap|aaxplugin)$', '', s)
    
    # Arch suffixes - Rule C
    s = re.sub(r'(_x64|_x86|_win64|_win32| x64| x86)$', '', s)
    
    # Bracket groups - Rule B
    # Strip known decoration phrases inside parens
    s = re.sub(r'\s*\((x64|64-bit|bridged|demo|trial|stereo|mono|vst3)\)', '', s)
    # General paren stripping if it looks like junk? 
    # For safety, we keep other parens as they might be part of name "Pro-Q (2)"
    # But let's strip completely if purely technical
    s = re.sub(r'\s*\([^)]*\)$', '', s) # Strip trailing parens aggresively
    
    # 3. Normalize Separators & Whitespace - Rule D (include comma so "DSP, LLC" tokenizes)
    s = re.sub(r'[-_. ,]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    
    # 4. Tokenization & Version Extraction - Rule E
    tokens = set(s.split())
    
    # Version extraction
    version = None
    # Look for trailing version number in the string (e.g. "contact 7", "v10")
    # Exclude c4, m1, l2 etc (single char + digit)
    version_match = re.search(r'\s(v?([0-9]+)(\.[0-9]+)?)$', s)
    if version_match:
        v_full = version_match.group(1)
        v_num = version_match.group(2)
        # Check if it's a note-like token (e.g. C4) or too long to be version
        is_note = False
        last_word = s.split()[-1]
        if len(last_word) == 2 and last_word[0].isalpha() and last_word[1].isdigit():
             is_note = True
             
        if not is_note and len(v_num) < 5: 
            version = v_num
            
    # Filter tokens (STOP_TOKENS + new Rule C words)
    # Rule C extra: mono, stereo, vst, etc if standalone
    rule_c_junk = {"mono", "stereo", "vst", "vst2", "vst3", "aax", "clap"}
    
    filtered_tokens = {t for t in tokens if t not in STOP_TOKENS and t not in rule_c_junk and len(t) > 1}
    # If we filtered everything away (e.g. name was just "VST Plugin"), keep original tokens
    if not filtered_tokens and tokens:
        filtered_tokens = tokens

    # 5. Vendor Identification
    vendor_tokens = set()
    found_vendor = None
    for v_name, v_aliases in VENDOR_ALIASES.items():
        # Check against full string or tokens
        # Create a set of alias tokens for intersection
        for alias in v_aliases | {v_name}:
            alias_parts = set(alias.split())
            if alias_parts.issubset(tokens):
                vendor_tokens.update(alias_parts)
                found_vendor = v_name
                break
        if found_vendor:
            break
            
    # Tokens without vendor
    tokens_no_vendor = filtered_tokens - vendor_tokens
    if not tokens_no_vendor:
        tokens_no_vendor = filtered_tokens # fallback

    # 6. Product Key Resolution
    product_key = None
    
    # Token rewrite rules (simple map before alias lookup)
    # E.g. nativeinstruments -> native instruments is handled by alias map usually
    # But specific weird ones:
    for k in ("kontakt5", "kontakt6", "kontakt7", "kontakt8"):
        if k in s.replace(" ", ""):
            s = s.replace(k, k.replace("kontakt", "kontakt ").strip())
    
    # Check full string first against aliases (s has spaces; aliases may have hyphens e.g. "pro-q 3")
    def _norm(s: str) -> str:
        return s.replace("-", " ")
    for p_key, p_aliases in PRODUCT_ALIASES.items():
        if s in p_aliases or s in {_norm(a) for a in p_aliases}:
            product_key = p_key
            break
    if not product_key:
        # Check if any alias is contained in string (broad check); normalize hyphens so "pro q 3" matches "pro-q 3"
        for p_key, p_aliases in PRODUCT_ALIASES.items():
            for alias in p_aliases:
                alias_norm = f" {_norm(alias)} "
                if alias_norm in f" {s} " or f" {alias} " in f" {s} ":
                    product_key = p_key
                    break
            if product_key:
                break
    
    return CanonicalName(
        raw=raw,
        canon=s,
        tokens=filtered_tokens,
        tokens_no_vendor=tokens_no_vendor,
        vendor_tokens=vendor_tokens,
        version=version,
        arch=arch,
        product_key=product_key or s # default to full string if no alias
    )



def strip_vendor(tokens: Set[str]) -> Set[str]:
    """Remove known vendor tokens from a token set."""
    # This logic is integrated into canonicalize, but provided as helper if needed
    for v_aliases in VENDOR_ALIASES.values():
        for alias in v_aliases:
            parts = set(alias.split())
            if parts.issubset(tokens):
                return tokens - parts
    return tokens


# --- Indexing ---

def build_installed_index(installed_rows: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Build a multi-key index of installed plugins.
    Keys: product_key, canon_no_vendor, raw_canon, token_signature
    """
    index = {}
    
    def add_entry(key: str, row: Dict):
        if not key: return
        if key not in index:
            index[key] = []
        # Check for dupes
        if row not in index[key]:
            index[key].append(row)

    for row in installed_rows:
        name = row.get("name", "")
        if not name: continue
        
        cn = canonicalize(name)
        row['_canon'] = cn # Store for scoring later
        
        # 1. Product Key (High confidence)
        if cn.product_key:
            add_entry(cn.product_key, row)
            
        # 2. Canonical Name (Full)
        add_entry(cn.canon, row)
        
        # 3. Canonical without Vendor
        if cn.tokens_no_vendor:
            no_vendor = " ".join(sorted(cn.tokens_no_vendor))
            add_entry(no_vendor, row)
            
        # 4. Token Signature (sorted joined tokens)
        sig = " ".join(sorted(cn.tokens))
        add_entry(sig, row)

        # 5. Each token from tokens_no_vendor (so "Nexus" ref finds installed "Nexus")
        for t in (cn.tokens_no_vendor or cn.tokens):
            if t and len(t) > 1:
                add_entry(t, row)
        
        # 6. Raw Name (Lower)
        add_entry(name.lower(), row)

        # 7. Kontakt: index .nki / CONTENT.NI libraries under "kontakt" so refs to Kontakt match the family
        plugin_type_tag = (row.get("plugin_type_tag") or "").strip()
        if plugin_type_tag.startswith("CONTENT.NI") or (row.get("content_related") and (row.get("path") or "").lower().endswith((".nki", ".nkm", ".nksn", ".nksr", ".nksf", ".nicnt"))):
            add_entry("kontakt", row)

    return index


# --- Matching Logic ---

def resolve_reference(
    ref_name: str, 
    ref_path: Optional[str], 
    installed_index: Dict[str, List[Dict]],
    all_installed_rows: List[Dict] # Passed for fallback iteration if index misses
) -> MatchResult:
    """
    Resolve a referenced plugin name to an installed plugin.
    Hardened strategy: Exact -> ProductKey -> Token Narrowing.
    Ref name is normalized first (strip FL instance/param suffixes) so old DB rows still match.
    """
    ref_name = normalize_reference_name(ref_name or "")
    ref = canonicalize(ref_name)
    
    candidates = []
    seen_ids = set()

    def add_candidates(rows):
        for row in rows:
            rid = row.get('path', str(row))
            if rid not in seen_ids:
                candidates.append(row)
                seen_ids.add(rid)
    
    # 1. Exact Canon Match
    if ref.canon in installed_index:
        add_candidates(installed_index[ref.canon])

    # 2. Exact Product Key Match
    if ref.product_key and ref.product_key in installed_index:
        add_candidates(installed_index[ref.product_key])

    # 2b. Single-token lookup (e.g. ref "Nexus" -> installed "Nexus")
    for token in (ref.tokens_no_vendor or ref.tokens):
        if token and len(token) > 1 and token in installed_index:
            add_candidates(installed_index[token])
        
    # 3. Token Narrowing (if few candidates)
    # Prefer: at least one non-generic token in common
    if len(candidates) < 5 and ref.tokens_no_vendor:
        for row in all_installed_rows:
            inst_cn = row.get('_canon')
            if not inst_cn:
                inst_cn = canonicalize(row['name'])
                row['_canon'] = inst_cn
            overlap = ref.tokens_no_vendor & inst_cn.tokens_no_vendor
            strong_overlap = {t for t in overlap if t not in GENERIC_TOKENS}
            if strong_overlap:
                add_candidates([row])

    # 4. Fallback: if still no candidates, any installed with any token overlap (incl. generic)
    # So we get something to score; score will be capped at 0.65 if only generic overlap
    if not candidates and ref.tokens_no_vendor:
        for row in all_installed_rows:
            inst_cn = row.get('_canon') or canonicalize(row['name'])
            row['_canon'] = inst_cn
            if ref.tokens_no_vendor & inst_cn.tokens_no_vendor:
                add_candidates([row])

    if not candidates:
        return MatchResult("missing", None, 0.0, "No candidates found", 0, [])

    # 4. Score Candidates
    scored_candidates = []
    
    for cand in candidates:
        inst_cn = cand.get('_canon') or canonicalize(cand['name'])
        score = 0.0
        
        # Lane 1: Product Key Match (+0.50, +0.12 bonus so product_key alone can reach MATCHED with weak jaccard)
        if ref.product_key and inst_cn.product_key and ref.product_key == inst_cn.product_key:
            score += 0.62
            
        # Lane 2: Token Similarity (+0.40 * Jaccard) on tokens_no_vendor
        u_tokens = ref.tokens_no_vendor | inst_cn.tokens_no_vendor
        i_tokens = ref.tokens_no_vendor & inst_cn.tokens_no_vendor
        
        if not i_tokens:
             jaccard = 0.0
        else:
             jaccard = len(i_tokens) / len(u_tokens)
        
        score += (0.40 * jaccard)
        
        # Lane 3: Path Evidence
        path_score = 0.0
        if ref_path:
            try:
                # Stem match (+0.30)
                # Reuse canonicalize logic for stem? Or simple strip
                ref_stem = Path(ref_path).stem.lower()
                # strip arch/ext via canonicalize
                ref_stem_cn = canonicalize(ref_stem)
                
                cand_path = (cand.get('path') or '')
                cand_stem = Path(cand_path).stem.lower()
                cand_stem_cn = canonicalize(cand_stem)
                
                if ref_stem_cn.canon == cand_stem_cn.canon:
                     path_score = 0.30
                
                # Vendor folder match (+0.10)
                cand_vendor = (cand.get('vendor') or '').lower()
                if ref.vendor_tokens:
                    for vt in ref.vendor_tokens:
                        if vt in cand_vendor:
                             path_score += 0.10
                             break
            except:
                pass
        score += path_score

        # Version Bonus/Penalty
        if ref.version and inst_cn.version:
            if ref.version == inst_cn.version:
                score += 0.08
            else:
                score -= 0.05
                
        # Sanity Checks / Caps
        # Empty token intersection: cannot match unless path stem match is true
        if not i_tokens and path_score < 0.30:
            score = 0.0

        # Cap if only generic tokens overlap (unless product_key matched — then trust it)
        overlap_tokens = ref.tokens_no_vendor & inst_cn.tokens_no_vendor
        non_generic_overlap = {t for t in overlap_tokens if t not in GENERIC_TOKENS}
        product_key_matched = ref.product_key and inst_cn.product_key and ref.product_key == inst_cn.product_key

        if not product_key_matched and not non_generic_overlap and not path_score > 0.2:
            # If no path match and only generic overlap -> Cap at 0.65 (Unknown)
            if score > 0.65:
                score = 0.65

        # Clamp
        score = min(1.0, max(0.0, score))
        
        scored_candidates.append({
            "candidate": cand,
            "score": score,
            "match_name": inst_cn.canon
        })

    # Sort by score desc
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    top_3 = [x["candidate"] for x in scored_candidates[:3]]
    best = scored_candidates[0]
    best_score = best["score"]
    best_cand = best["candidate"]
    
    # 5. Thresholds & Separation
    THRESHOLD_MATCH = 0.78
    THRESHOLD_AMBIGUOUS = 0.60
    SEPARATION_REQ = 0.08
    
    separation = 1.0
    if len(scored_candidates) > 1:
        separation = best_score - scored_candidates[1]["score"]
        
    status = "missing"
    reason = "Low score"
    
    if best_score >= THRESHOLD_MATCH and separation >= SEPARATION_REQ:
        status = "matched"
        reason = "High confidence & separation"
    elif best_score >= THRESHOLD_AMBIGUOUS:
        status = "ambiguous"
        reason = f"Ambiguous (score {best_score:.2f}, sep {separation:.2f})"
    else:
        status = "missing"
        reason = f"Best score {best_score:.2f} < threshold"

    return MatchResult(status, best_cand, best_score, reason, len(candidates), top_3)


