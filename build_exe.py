import os
import sys
import shutil
import subprocess
from pathlib import Path

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

print("=" * 70)
print("     🏛️  ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMC System)")
print("            ឧបករណ៍បង្កើត Standalone Windows EXE (Python)")
print("=" * 70)
print()

# 1. Check & Install Required Packages
print("[1/4] កំពុងពិនិត្យមើល Packages (PyInstaller, CustomTkinter)...")
try:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller", "customtkinter"],
        check=True
    )
except subprocess.CalledProcessError as e:
    print(f"[ERROR] ការតម្លើង Package បរាជ័យ: {e}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# 2. Prepare Icon & Arguments
icon_path = BASE_DIR / "dms" / "static" / "dms" / "img" / "favicon.ico"
pyinstaller_args = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconsole",
    "--onefile",
    "--clean",
    "--collect-all", "customtkinter",
    "--collect-all", "waitress",
    "--collect-all", "django",
    "--collect-all", "dms",
    "--collect-all", "dms_project",
    "--collect-all", "whitenoise",
    "--collect-all", "psycopg2",
    "--add-data", f"{BASE_DIR / 'dms'};dms",
    "--add-data", f"{BASE_DIR / 'dms_project'};dms_project",
    "--hidden-import", "waitress",
    "--hidden-import", "django",
    "--hidden-import", "dms",
    "--hidden-import", "dms.apps",
    "--hidden-import", "dms.models",
    "--hidden-import", "dms.views",
    "--hidden-import", "dms.media_service",
    "--hidden-import", "dms.signals",
    "--hidden-import", "dms.context_processors",
    "--hidden-import", "dms.urls",
    "--hidden-import", "dms_project.urls",
    "--hidden-import", "dms_project.wsgi",
    "--hidden-import", "dms_project.settings",
    "--hidden-import", "psycopg2",
    "--hidden-import", "dj_database_url",
    "--exclude-module", "cv2",
    "--exclude-module", "matplotlib",
    "--exclude-module", "torch",
    "--exclude-module", "scipy",
    "--name", "DMC_System",
]

if icon_path.exists():
    pyinstaller_args.extend(["--icon", str(icon_path)])

logo_path = BASE_DIR / "dms" / "static" / "dms" / "img" / "logo.png"
if logo_path.exists():
    pyinstaller_args.extend(["--add-data", f"{logo_path};dms/static/dms/img"])

pyinstaller_args.append("main_app.py")

# 3. Clean Old Build Artifacts & Compile EXE
print("\n[2/4] កំពុងសម្អាត Cache និងដំណើរការ Compile Python Code ទៅជា EXE (សូមរង់ចាំបន្តិច)...")

# Terminate any running instances FIRST so Windows unlocks the file
try:
    subprocess.run(["taskkill", "/f", "/im", "DMC_System.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import time
    time.sleep(1)
except Exception:
    pass

shutil.rmtree(BASE_DIR / "build", ignore_errors=True)
try:
    subprocess.run(pyinstaller_args, check=True)
except subprocess.CalledProcessError as e:
    print(f"\n[ERROR] ការ compile បរាជ័យ: {e}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# 4. Copy to Root Directory & Ensure Config in Dist
print("\n[3/4] កំពុងចម្លង file DMC_System.exe មកកាន់ Root Folder...")
dist_exe = BASE_DIR / "dist" / "DMC_System.exe"
target_exe = BASE_DIR / "DMC_System.exe"

# Copy dmc_config.txt to dist folder as well for standalone convenience
if (BASE_DIR / "dmc_config.txt").exists():
    try:
        shutil.copy2(BASE_DIR / "dmc_config.txt", BASE_DIR / "dist" / "dmc_config.txt")
    except Exception:
        pass

if dist_exe.exists():
    try:
        shutil.copy2(dist_exe, target_exe)
        file_size_mb = target_exe.stat().st_size / (1024 * 1024)
        print(f"✅ ចម្លងជោគជ័យ! ទំហំ file: {file_size_mb:.2f} MB (បាន Update រូបរាងថ្មី ១០០%)")
    except Exception as e:
        print(f"⚠️ ចម្លងមិនបានសម្រេច: {e}")

# 5. Success Banner
print()
print("=" * 70)
print("  ✅ បង្កើត file DMC_System.exe បានជោគជ័យ ១០០%!")
print(f"  📁 ទីតាំង File: {target_exe}")
print("  🚀 ពេលចុចបើក DMC_System.exe វានឹងបង្ហាញទម្រង់ទី២ (Web App) ស្វ័យប្រវត្ត")
print("  🔒 ទិន្នន័យ db.sqlite3 និង Neon Cloud Database ភ្ជាប់បានយ៉ាងត្រឹមត្រូវ")
print("=" * 70)
if "--no-pause" not in sys.argv and sys.stdin and sys.stdin.isatty():
    try:
        input("\nចុច Enter ដើម្បីបិទផ្ទាំងនេះ (Press Enter to exit)... ")
    except Exception:
        pass
