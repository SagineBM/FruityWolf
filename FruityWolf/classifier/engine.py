import json
import logging
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
RULES_DIR = Path(__file__).parent.parent / "resources" / "rules"

class ProjectState:
    # System states - matched to project_states.json IDs for compatibility
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
    
    @staticmethod
    def format_action_id(action_id: str) -> str:
        if not action_id: return ""
        return action_id.replace("_", " ").title()

@dataclass
class ClassificationResult:
    """Full classification result for a project."""
    state_id: str
    state_confidence: float
    state_reasons: List[str]
    
    score: int
    score_breakdown: Dict[str, int]
    
    next_action_id: str
    next_action_meta: Dict[str, Any]
    next_action_reasons: List[str]
    
    signals: Dict[str, Dict[str, Any]]  # { "raw": {}, "derived": {} }
    
    ruleset_hash: str
    classified_at_ts: int = field(default_factory=lambda: int(time.time()))
    
    # Backward compatibility properties if needed
    @property
    def state(self): return self.state_id
    
    @property
    def needs_render(self): 
        # Derived from action or state
        return self.next_action_id in ["render_preview_30s", "render_full_preview"]
        
    @property
    def render_priority_score(self): return self.score
    
    @property
    def reasons(self): return self.state_reasons + self.next_action_reasons

class ProjectClassifier:
    """
    Data-driven classifier engine.
    Loads rules from JSON and evaluates projects against them.
    """
    
    def __init__(self):
        self._rules = {}
        self._rules_hash = ""
        self.load_rules()
        
    def load_rules(self):
        """Load all rule JSONs and compute version hash."""
        try:
            self._rules = {
                "signals": self._load_json("signals.json"),
                "states": self._load_json("project_states.json"),
                "scoring": self._load_json("scoring_rules.json"),
                "actions": self._load_json("next_actions.json"),
            }
            
            # Compute hash of all rules combined
            hasher = hashlib.sha256()
            for key in sorted(self._rules.keys()):
                hasher.update(json.dumps(self._rules[key], sort_keys=True).encode('utf-8'))
            self._rules_hash = hasher.hexdigest()[:16] # Short hash is enough
            
            logger.info(f"Rules loaded. Hash: {self._rules_hash}")
            
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            self._rules = {}
            
    def _load_json(self, name: str) -> Dict:
        path = RULES_DIR / name
        if not path.exists():
            logger.warning(f"Rule file not found: {path}")
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {name}: {e}")
            return {}
            
    @property
    def rules_hash(self) -> str:
        return self._rules_hash

    def classify(self, signals_raw: Dict[str, Any], signals_derived: Dict[str, Any]) -> ClassificationResult:
        """
        Classify project using raw and derived signals.
        """
        # 1. Flatten signals for rule evaluation
        # Priority: Derived overrides Raw (if name collision, though they should be distinct)
        combined_signals = signals_raw.copy()
        combined_signals.update(signals_derived)
        
        # 2. Determine State
        state_id, state_reasons = self._evaluate_state(combined_signals)
        
        # 3. Calculate Score
        score, score_breakdown = self._evaluate_score(combined_signals)
        
        # 4. Determine Next Action
        action_id, action_reasons = self._evaluate_next_action(state_id, combined_signals)
        
        return ClassificationResult(
            state_id=state_id,
            state_confidence=1.0, # Deterministic rules = 100% confidence
            state_reasons=state_reasons,
            score=score,
            score_breakdown=score_breakdown,
            next_action_id=action_id,
            next_action_meta={}, # Payload for advanced UI
            next_action_reasons=action_reasons,
            signals={"raw": signals_raw, "derived": signals_derived},
            ruleset_hash=self._rules_hash
        )
        
    def _evaluate_state(self, signals: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Determine lifecycle state."""
        states = self._rules.get("states", {}).get("states", [])
        
        for state_def in states:
            state_id = state_def["id"]
            conditions = state_def.get("conditions", [])
            
            # No conditions usually implies a catch-all or default if placed last
            # In our JSON, IDEA has empty conditions but we rely on loop order.
            # If empty conditions, does it match always?
            # Convention: Empty conditions list = MATCH ALL (True)
            if not conditions:
                return state_id, ["Matched default state"]
                
            # Check conditions
            if self._check_conditions(conditions, signals):
                reasons = []
                for cond in conditions:
                    if "or" in cond:
                        reasons.append(f"Matched complex criteria for {state_id}")
                    elif "and" in cond:
                        reasons.append(f"Matched complex criteria for {state_id}")
                    else:
                        # Human readable signal check
                        sig = cond.get('signal', '?')
                        op = cond.get('op', 'eq')
                        val = cond.get('value', '?')
                        reasons.append(f"{sig} {op} {val}")
                return state_id, reasons
                
        return "UNKNOWN", ["No state matched"]

    def _evaluate_score(self, signals: Dict[str, Any]) -> Tuple[int, Dict[str, int]]:
        """Calculate completion score."""
        rule_def = self._rules.get("scoring", {})
        score = rule_def.get("base_score", 0)
        modifiers = rule_def.get("modifiers", [])
        breakdown = {}
        
        for mod in modifiers:
            if self._check_condition_single(mod["condition"], signals):
                amount = mod["score"]
                mod_id = mod["id"]
                score += amount
                breakdown[mod_id] = amount
                
        # Clamping
        bounds = rule_def.get("bounds", {"min": 0, "max": 100})
        score = max(bounds["min"], min(bounds["max"], score))
        
        return score, breakdown

    def _evaluate_next_action(self, state_id: str, signals: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Determine next action based on state."""
        actions_map = self._rules.get("actions", {}).get("actions", {})
        
        # Simple Logic: Map State -> Action directly
        action_def = actions_map.get(state_id)
        if not action_def:
            action_def = actions_map.get("default", {"id": "open_project"})
            
        return action_def["id"], [f"Suggested for {state_id}"]

    def _check_conditions(self, conditions: List[Dict], signals: Dict) -> bool:
        """Check a list of conditions. Returns True if ALL match (AND)."""
        for cond in conditions:
            if not self._check_condition_single(cond, signals):
                return False
        return True

    def _check_condition_single(self, cond: Dict, signals: Dict) -> bool:
        """Evaluate a single condition object."""
        # Logical operators
        if "and" in cond:
            return self._check_conditions(cond["and"], signals)
        if "or" in cond:
            for sub_cond in cond["or"]:
                if self._check_condition_single(sub_cond, signals):
                    return True
            return False
        if "not" in cond:
            return not self._check_condition_single(cond["not"], signals)
            
        # Signal comparison
        sig_name = cond.get("signal")
        if not sig_name: return False
        
        op = cond.get("op", "eq")
        target_val = cond.get("value")
        
        actual_val = signals.get(sig_name)
        
        # Defaults if signal missing
        if actual_val is None:
            # Try to find default in definitions
            raw_def = self._rules.get("signals", {}).get("raw", {}).get(sig_name)
            derived_def = self._rules.get("signals", {}).get("derived", {}).get(sig_name)
            sig_def = raw_def or derived_def
            
            if sig_def:
                actual_val = sig_def["default"]
            else:
                # Type safe zeros
                if isinstance(target_val, bool): actual_val = False
                elif isinstance(target_val, (int, float)): actual_val = 0
                elif isinstance(target_val, list): actual_val = []
                else: actual_val = ""

        return self._compare(actual_val, op, target_val)

    def _compare(self, actual: Any, op: str, target: Any) -> bool:
        try:
            if op == "eq": return actual == target
            if op == "neq": return actual != target
            if op == "gt": return float(actual) > float(target)
            if op == "gte": return float(actual) >= float(target)
            if op == "lt": return float(actual) < float(target)
            if op == "lte": return float(actual) <= float(target)
            if op == "contains": return target in actual
            if op == "contains_any":
                # Intersection of lists
                if not isinstance(actual, list): return False
                return bool(set(actual) & set(target))
            if op == "not_contains": return target not in actual
            
        except Exception as e:
            # logger.debug(f"Comparison error: {e}")
            return False
        return False
