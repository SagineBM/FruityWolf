"""
Verify Environment

Checks that the Python environment is correctly set up for FruityWolf.
"""

import sys
import importlib
import platform

REQUIRED_MODULES = [
    "PySide6",
    "vlc",
    "numpy",
    "soundfile",
    "librosa",
    "mutagen",
    "watchdog",
    "PIL"
]

def check_python_version():
    print(f"Python Version: {sys.version.split()[0]}")
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11+ is required.")
        return False
    if sys.version_info >= (3, 12):
        print("WARNING: Python 3.12+ might have compatibility issues with librosa/numba.")
    return True

def check_modules():
    all_good = True
    print("\nChecking dependencies...")
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
            print(f"  [OK] {module}")
        except ImportError:
            print(f"  [MISSING] {module}")
            all_good = False
        except Exception as e:
            print(f"  [ERROR] {module}: {e}")
            all_good = False
    return all_good

def main():
    print("="*60)
    print(f"FruityWolf Environment Verification ({platform.system()})")
    print("="*60)
    
    v_ok = check_python_version()
    m_ok = check_modules()
    
    print("\n" + "="*60)
    if v_ok and m_ok:
        print("SUCCESS: Environment is ready!")
        sys.exit(0)
    else:
        print("FAILURE: Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
