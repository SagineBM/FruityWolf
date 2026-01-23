import sys
import os
import time

# Add parent dir to path so we can import FruityWolf
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.classifier.engine import ProjectClassifier, ProjectState

def test_classifier():
    classifier = ProjectClassifier()
    print("Initializing Classifier Test...")
    
    # Mock Signals
    scenarios = [
        {
            "name": "Empty Project",
            "data": {},
            "state": ProjectState.BROKEN_OR_EMPTY,
            "needs_render": False
        },
        {
            "name": "Micro Idea (New, no content)",
            "data": {
                "has_flp": True, 
                "backup_count": 0, 
                "samples_count": 0,
                "project_modified_age_hours": 2,
                "folder_size_mb": 5,
                "has_render_root": False
            },
            "state": ProjectState.MICRO_IDEA,
            "needs_render": True
        },
        {
            "name": "Idea (Some backups, some samples)",
            "data": {
                "has_flp": True, 
                "backup_count": 2, 
                "samples_count": 5,
                "project_modified_age_hours": 48,
                "has_render_root": False
            },
            "state": ProjectState.IDEA,
            "needs_render": True
        },
        {
            "name": "WIP (Heavy activity)",
            "data": {
                "has_flp": True,
                "backup_count": 10,
                "samples_count": 20,
                "audio_folder_count": 5,
                "has_render_root": False
            },
            "state": ProjectState.WIP,
            "needs_render": True
        },
        {
            "name": "Preview Ready (Good render)",
            "data": {
                "has_flp": True,
                "has_render_root": True,
                "render_duration_s": 120,
                "backup_count": 10
            },
            "state": ProjectState.PREVIEW_READY,
            "needs_render": False
        },
        {
            "name": "Advanced (Stems present)",
            "data": {
                "has_flp": True,
                "has_render_root": True,
                "render_duration_s": 180,
                "stems_count": 12
            },
            "state": ProjectState.ADVANCED,
            "needs_render": False
        },
        {
            "name": "Needs Render Check (Tiny Render)",
            "data": {
                "has_flp": True,
                "has_render_root": True,
                "render_duration_s": 10, # < 20s
            },
            "state": ProjectState.MICRO_IDEA, # Or similar depending on content
            "needs_render": True # Should be True because render < 20s
        }
    ]
    
    print("\n--- Running Tests ---")
    all_passed = True
    for s in scenarios:
        result = classifier.classify(s['data'])
        
        # Check State
        state_match = result.state == s.get('state', result.state)
        # Check Needs Render
        render_match = result.needs_render == s.get('needs_render', result.needs_render)
        
        passed = state_match and render_match
        if not passed: all_passed = False
        
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {s['name']}")
        print(f"    Got State: {result.state} (Exp: {s.get('state')})")
        print(f"    Got NeedsRender: {result.needs_render} (Exp: {s.get('needs_render')})")
        print(f"    Score: {result.render_priority_score}")
        print(f"    Reasons: {result.reasons}")

    if all_passed:
        print("\nSUCCESS: All tests passed!")
        sys.exit(0)
    else:
        print("\nFAILURE: Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_classifier()
