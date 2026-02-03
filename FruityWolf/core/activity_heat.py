"""
Activity Heat Calculation
"""

import time
import math
from typing import Dict, Any, Optional

def calculate_activity_heat(
    flp_mtime: Optional[int],
    last_opened_at: Optional[int],
    last_rendered_at: Optional[int],
    open_count: int,
    play_count: int,
    last_played_ts: Optional[int] = None
) -> dict:
    """
    Compute Activity Heat signals.
    
    Returns:
        dict: {
            'score': int (0-100),
            'label': str (Cold/Warm/Hot),
            'last_touch_ts': int
        }
    """
    # 1. Determine last touch
    timestamps = [ts for ts in [flp_mtime, last_opened_at, last_rendered_at, last_played_ts] if ts]
    last_touch_ts = max(timestamps) if timestamps else 0
    
    # 2. Recency Component
    # Formula: 40 * exp(-days_since_last_touch / 30)
    # Reduced max recency from 50 to 40 so "just touched" doesn't automatically mean Warm (threshold 40)
    recency = 0
    if last_touch_ts > 0:
        now = time.time()
        days_since = max(0, (now - last_touch_ts) / 86400.0)
        recency = 40 * math.exp(-days_since / 30.0)
    
    # 3. Engagement Component
    # Formula: min(60, play_count*5 + open_count*3)
    # Boost: If we have last_played_ts but 0 count, assume at least 1 historical play
    effective_play_count = play_count
    if effective_play_count == 0 and last_played_ts:
        effective_play_count = 1
        
    engagement = min(60, (effective_play_count * 5) + (open_count * 3))
    
    # 4. Total Heat Score
    score = int(min(100, max(0, recency + engagement)))
    
    # 5. Label
    # Adjusted thresholds:
    # 0-35: Cold (Need some engagement or very recent touch)
    # 36-75: Warm (Recent touch + some engagement)
    # 76-100: Hot (High engagement)
    if score <= 35:
        label = "Cold"
    elif score <= 75:
        label = "Warm"
    else:
        label = "Hot"
        
    return {
        'score': score,
        'label': label,
        'last_touch_ts': last_touch_ts,
        'recency': int(recency),
        'engagement': int(engagement)
    }

def get_heat_color(label: str) -> str:
    """Get color hex for heat label."""
    if label == "Hot":
        return "#f43f5e" # Rose-500
    elif label == "Warm":
        return "#f59e0b" # Amber-500
    return "#64748b" # Slate-500 (Cold)
