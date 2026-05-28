import sys
import os

def verify_system_requirements():
    """
    Checks if all mandatory Python dependencies are installed and available
    before initializing the main program to avoid cryptic runtime tracebacks.
    """
    dependencies = {
        "cv2": "opencv-python",
        "mediapipe": "mediapipe",
        "pyautogui": "pyautogui",
        "customtkinter": "customtkinter",
        "PIL": "pillow (Pillow)",
        "screeninfo": "screeninfo"
    }
    
    missing = []
    for module, pkg_name in dependencies.items():
        try:
            mod = __import__(module)
            if module == "mediapipe" and not hasattr(mod, "solutions"):
                raise ImportError("mediapipe.solutions is missing")
        except ImportError:
            missing.append(pkg_name)
            
    if missing:
        print("\n" + "="*60)
        print(" ERROR: MISSING REQUIRED PYTHON PACKAGES")
        print("="*60)
        print("The following libraries are required but could not be imported:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nTO RESOLVE:")
        print("1. Make sure your Python Virtual Environment is activated:")
        print("   PowerShell:  .\\.venv\\Scripts\\Activate.ps1")
        print("   CMD:         .\\.venv\\Scripts\\activate.bat")
        print("2. Run the pip installer command:")
        print("   pip install -r requirements.txt")
        print("="*60 + "\n")
        return False
        
    return True

def main():
    # Auto-activate/respawn in virtual environment if running outside of it
    venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
    is_venv = (sys.prefix != sys.base_prefix) or ("VIRTUAL_ENV" in os.environ) or (os.environ.get("AUTO_VENV_ACTIVE") == "1")
    
    if not is_venv and os.path.isdir(venv_dir):
        # Choose the right executable based on OS
        if os.name == "nt":
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")
            
        if os.path.exists(venv_python):
            import subprocess
            print(f"[*] Detected local virtual environment (.venv). Re-running application inside it...")
            try:
                env = os.environ.copy()
                env["AUTO_VENV_ACTIVE"] = "1"
                result = subprocess.run([venv_python] + sys.argv, env=env, check=False)
                sys.exit(result.returncode)
            except Exception as e:
                print(f"[!] Failed to auto-switch to virtual environment: {e}")

    # 1. Assert dependency sanity
    if not verify_system_requirements():
        sys.exit(1)
        
    print("[*] Booting Neural Gesture Control HUD...")
    
    # 2. Lazy-load imports after checking dependency integrity
    from gesture_engine import GestureEngine
    from gui import GestureControlGUI
    
    # 3. Initialize background gesture engine
    engine = GestureEngine()
    
    # 4. Initialize sleek user interface dashboard
    app = GestureControlGUI(engine)
    
    # 5. Direct program flow to UI main loop
    app.mainloop()

if __name__ == "__main__":
    main()
