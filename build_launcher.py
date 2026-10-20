import os
import sys
import subprocess
from pathlib import Path

# In PyInstaller frozen onefile EXE, sys.executable is the path to Build.exe in the project folder
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

os.chdir(BASE_DIR)


def safe_input(prompt="\nPress Enter to exit..."):
    try:
        input(prompt)
    except Exception:
        pass


def find_python():
    """Finds the real Python executable installed on the system."""
    # 1. Check project venv
    venv_py = BASE_DIR / "venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)

    # 2. Check current sys.executable if running as a normal python script
    if not getattr(sys, 'frozen', False) and "python" in Path(sys.executable).name.lower():
        return sys.executable

    # 3. Check PATH via 'where python.exe'
    try:
        res = subprocess.run(["where", "python.exe"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line and "windowsapps" not in line.lower() and os.path.exists(line):
                return line
    except Exception:
        pass

    # 4. Check standard Windows Python installation directories
    local_app = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        r"C:\Program Files\Python311\python.exe",
        r"C:\Program Files\Python312\python.exe",
        r"C:\Program Files\Python310\python.exe",
        r"C:\Program Files\Python313\python.exe",
        os.path.join(local_app, "Programs", "Python", "Python311", "python.exe"),
        os.path.join(local_app, "Programs", "Python", "Python312", "python.exe"),
        os.path.join(local_app, "Programs", "Python", "Python310", "python.exe"),
        os.path.join(local_app, "Programs", "Python", "Python313", "python.exe"),
        r"C:\Python311\python.exe",
        r"C:\Python312\python.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c

    return "python.exe"


def main():
    build_script = BASE_DIR / "build_exe.py"
    if not build_script.exists():
        print(f"Error: {build_script} not found.")
        print(f"Current Directory: {BASE_DIR}")
        safe_input()
        return

    py_exe = find_python()
    print(f"[INFO] Using Python: {py_exe}")
    print(f"[INFO] Running build: {build_script}")
    print("-" * 65)

    try:
        result = subprocess.run([py_exe, str(build_script)])
        if result.returncode != 0:
            print(f"\n[ERROR] Build finished with exit code {result.returncode}")
            safe_input()
    except Exception as e:
        print(f"\n[ERROR] Failed to run build_exe.py: {e}")
        safe_input()


if __name__ == "__main__":
    main()
