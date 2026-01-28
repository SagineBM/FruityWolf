"""
Design Tokens for FruityWolf.
Centralized colors, radii, and typography.
"""

from dataclasses import dataclass

@dataclass
class ThemeColors:
    # Backgrounds
    bg_base: str
    bg_sidebar: str
    bg_player: str
    bg_card: str
    bg_input: str
    
    # Borders
    border_subtle: str
    border_focus: str
    
    # Text
    text_main: str
    text_muted: str
    text_dim: str
    
    # Accents
    accent_primary: str
    accent_secondary: str
    accent_success: str
    accent_warning: str
    accent_error: str
    accent_purple: str

DARK_THEME = ThemeColors(
    bg_base="#0c1117",
    bg_sidebar="#111820",
    bg_player="#151d28",
    bg_card="#1e2836",
    bg_input="#1e2836",
    
    border_subtle="#1e293b",
    border_focus="#38bdf8",
    
    text_main="#f1f5f9",
    text_muted="#94a3b8",
    text_dim="#64748b",
    
    accent_primary="#38bdf8",     # Sky Blue
    accent_secondary="#0ea5e9",   # Ocean Blue
    accent_success="#22c55e",     # Green
    accent_warning="#f59e0b",     # Amber
    accent_error="#ef4444",       # Red
    accent_purple="#a78bfa"       # Violet
)

# Design Consts
RADIUS_LG = "16px"
RADIUS_MD = "12px"
RADIUS_SM = "8px"
RADIUS_PILL = "22px"

FONT_MAIN = "'Segoe UI', 'Inter', -apple-system, sans-serif"
FONT_MONO = "'Consolas', 'Monaco', monospace"
