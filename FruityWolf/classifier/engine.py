import json
import logging
import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ProjectState:
    # System states
    BROKEN_OR_EMPTY = "BROKEN_OR_EMPTY"
    
    # 5 Stages (Evidence-based)
    MICRO_IDEA = "MICRO_IDEA"       # Stage 1
    IDEA = "IDEA"                   # Stage 2
    WIP = "WIP"                     # Stage 3
    PREVIEW_READY = "PREVIEW_READY" # Stage 4
    ADVANCED = "ADVANCED"           # Stage 5
    
    ORDERED = [
        BROKEN_OR_EMPTY, 
        MICRO_IDEA, 
        IDEA, 
        WIP, 
        PREVIEW_READY, 
        ADVANCED
    ]

@dataclass
class ClassificationResult:
    state: str
    needs_render: bool
    render_priority_score: int
    reasons: List[str]
    signals: Dict[str, Any]

class ProjectClassifier:
    """
    Evidence-based classifier for FL Studio projects.
    Derived from user-defined 'Truth Book' rules.
    """
    
    # Thresholds
    MIN_VALID_RENDER_DURATION = 20  # seconds
    MICRO_IDEA_SIZE_MB = 15
    MICRO_IDEA_SAMPLES = 3
    SKETCH_SAMPLES_MIN = 5
    WIP_SAMPLES_MIN = 15
    WIP_BACKUPS_MIN = 5
    ADVANCED_STEMS_MIN = 8
    
    KEYWORDS_DOWNGRADE = ["test", "practice", "demo", "try", "idea", "sketch"]
    KEYWORDS_FINISH = ["finish", "render", "wip", "final"]
    
    def classify(self, signals: Dict[str, Any]) -> ClassificationResult:
        """
        Classify a project based on collected signals.
        
        Signals expected:
        - has_flp (bool)
        - has_render_root (bool)
        - render_duration_s (float)
        - backup_count (int)
        - backup_latest_age_hours (float)
        - samples_count (int)
        - audio_folder_count (int)
        - stems_count (int)
        - project_modified_age_hours (float)
        - flp_size_kb (float)
        - folder_size_mb (float)
        - has_only_backup (bool)
        - project_name (str)
        - tags (list)
        """
        reasons = []
        
        # 1. Determine "Needs Render" Status
        needs_render = self._evaluate_needs_render(signals, reasons)
        
        # 2. Determine Stage (0-5)
        state = self._evaluate_stage(signals, reasons)
        
        # 3. Calculate Render Priority Score
        score = self._calculate_render_priority(signals, needs_render, state)
        
        return ClassificationResult(
            state=state,
            needs_render=needs_render,
            render_priority_score=score,
            reasons=reasons,
            signals=signals
        )

    def _evaluate_needs_render(self, s: Dict, reasons: List[str]) -> bool:
        """Evaluate if the project needs a render based on Tier 1 rules."""
        has_flp = s.get("has_flp", False)
        has_root_render = s.get("has_render_root", False)
        duration = s.get("render_duration_s", 0)
        stems_count = s.get("stems_count", 0)
        
        # Rule 1: Has usable render => RENDER_OK
        if has_root_render:
            if duration >= self.MIN_VALID_RENDER_DURATION:
                return False  # Does NOT need render
            else:
                reasons.append(f"Render snippet only ({int(duration)}s < {self.MIN_VALID_RENDER_DURATION}s)")
                return True # Needs FULL render
        
        # Rule 2: No root render but FLP exists => NEEDS_RENDER
        if has_flp and not has_root_render:
            reasons.append("NLP exists but no root render")
            return True
            
        # Rule 4: Stems exist but no root render => NEEDS_RENDER
        if stems_count > 0 and not has_root_render:
            reasons.append("Has stems but no root preview")
            return True
            
        return False

    def _evaluate_stage(self, s: Dict, reasons: List[str]) -> str:
        """Determine project stage based on evidence."""
        has_flp = s.get("has_flp", False)
        backups = s.get("backup_count", 0)
        samples = s.get("samples_count", 0)
        folder_mb = s.get("folder_size_mb", 0)
        has_only_backup = s.get("has_only_backup", False)
        proj_age = s.get("project_modified_age_hours", 0)
        render_duration = s.get("render_duration_s", 0)
        audio_folder = s.get("audio_folder_count", 0)
        has_root_render = s.get("has_render_root", False)
        stems = s.get("stems_count", 0)
        render_name = s.get("render_name", "").lower() if s.get("has_render_root") else ""
        
        # Stage 5: ADVANCED
        # Trigger: Stems >= 8 OR render name suggests mix/master OR multiple renders (not reliably tracked yet)
        is_mix_proof = any(x in render_name for x in ["mix", "master", "final", "v2", "v3"])
        if stems >= self.ADVANCED_STEMS_MIN or is_mix_proof:
            reasons.append(f"Advanced: {stems} stems or mix proof")
            return ProjectState.ADVANCED
            
        # Stage 4: PREVIEW READY
        # Trigger: Usable root render exists
        if has_root_render and render_duration >= self.MIN_VALID_RENDER_DURATION:
            # reasons.append("Preview Ready: Usable render found")
            return ProjectState.PREVIEW_READY
            
        # Stage 3: WIP ARRANGEMENT
        # Trigger: Backups >= 5 AND lots of content AND no usable render
        has_content = samples >= self.WIP_SAMPLES_MIN or audio_folder >= 10
        if backups >= self.WIP_BACKUPS_MIN and has_content:
            reasons.append("WIP: Significant work detected (backups/samples)")
            return ProjectState.WIP
            
        # Stage 1: MICRO IDEA (Check before Stage 2 to catch "early" ones)
        # Trigger: FLP but minimal content OR new only backup OR tiny render
        is_tiny_render = has_root_render and render_duration < self.MIN_VALID_RENDER_DURATION
        is_minimal = has_flp and backups == 0 and samples <= self.MICRO_IDEA_SAMPLES and folder_mb < self.MICRO_IDEA_SIZE_MB
        is_very_new = has_only_backup and proj_age < 24
        
        if is_minimal or is_very_new or is_tiny_render:
            reasons.append("Micro Idea: Minimal evidence found")
            return ProjectState.MICRO_IDEA

        # Stage 2: IDEA / SKETCH
        # Trigger: Backups >= 1 AND some content AND no usable render
        # If we fall through from Stage 3 and it's not Micro, it's likely Stage 2 if it has SOMETHING.
        has_some_content = samples >= self.SKETCH_SAMPLES_MIN or audio_folder >= 3
        if backups >= 1 and has_some_content:
            reasons.append("Idea: Some structures/backups found")
            return ProjectState.IDEA

        # Default / Fallback
        if not has_flp and backups == 0 and not has_root_render:
             return ProjectState.BROKEN_OR_EMPTY
             
        # If has FLP but doesn't match above, default to Idea or Micro?
        # Likely Idea if it didn't match Micro criteria (e.g. > 15MB but < 5 backups)
        return ProjectState.IDEA

    def _calculate_render_priority(self, s: Dict, needs_render: bool, state: str) -> int:
        """Calculate Render Priority Score (0-100)."""
        if not needs_render and state in [ProjectState.PREVIEW_READY, ProjectState.ADVANCED]:
            # If already has render, priority is low unless user requested update
            # But the user logic implies this score helps decide WHAT to render.
            # If it doesn't need render, score should be low?
            # actually user provided formula: +30 if has_flp and no usable root render
            pass
            
        score = 0
        has_flp = s.get("has_flp", False)
        has_root_render = s.get("has_render_root", False)
        render_duration = s.get("render_duration_s", 0)
        usable_render = has_root_render and render_duration >= self.MIN_VALID_RENDER_DURATION
        
        backups = s.get("backup_count", 0)
        samples = s.get("samples_count", 0)
        audio_folder = s.get("audio_folder_count", 0)
        proj_age = s.get("project_modified_age_hours", 0) # hours
        proj_name = s.get("project_name", "").lower()
        folder_mb = s.get("folder_size_mb", 0)
        tags = s.get("tags", [])
        
        # +30 if has_flp and no usable root render
        if has_flp and not usable_render:
            score += 30
            
        # +15 if backup_count >= 5
        if backups >= 5:
            score += 15
            
        # +10 if samples_count >= 10
        if samples >= 10:
            score += 10
            
        # +10 if audio_folder_count >= 5
        if audio_folder >= 5:
            score += 10
            
        # +20 if project modified in last 7 days (7 * 24 = 168 hours)
        if proj_age < 168:
            score += 20
            
        # -25 if project name contains: test, practice, demo
        if any(x in proj_name for x in self.KEYWORDS_DOWNGRADE):
            score -= 25
            
        # -20 if folder is tiny: < 10MB
        if folder_mb < 10:
            score -= 20
            
        # +20 if user tagged: finish, render, wip
        # We need to pass tags in signals
        if any(t in tags for t in self.KEYWORDS_FINISH):
            score += 20
            
        return max(0, min(100, score))

