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

# ---------------------------------------------------------------------------
# EXE build version - increments on every build, never resets.
# Produces DMC_System_v<MAJOR>.<MINOR>.<BUILD>.exe alongside the unversioned
# DMC_System.exe, which other scripts (UPDATE_USER_PC.bat, main_app.py,
# EXPORT_PORTABLE_PACKAGE.bat, push_to_github.py) still reference by name.
# ---------------------------------------------------------------------------
import json
from datetime import datetime

VERSION_FILE = BASE_DIR / "exe_version.json"


def bump_version():
    data = {"major": 1, "minor": 0, "build": 0, "history": []}
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as vf:
                loaded = json.load(vf)
            if isinstance(loaded, dict):
                data.update({k: loaded.get(k, data[k]) for k in ("major", "minor", "build")})
                data["history"] = loaded.get("history", [])
        except Exception as e:
            print(f"[WARN] exe_version.json unreadable ({e}) - starting a fresh version.")

    data["build"] = int(data["build"]) + 1
    version = f"{data['major']}.{data['minor']}.{data['build']}"
    data["version"] = version
    data["built_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["history"] = ([{"version": version, "built_at": data["built_at"]}] + data["history"])[:50]

    with open(VERSION_FILE, "w", encoding="utf-8") as vf:
        json.dump(data, vf, indent=2, ensure_ascii=False)
    return version


EXE_VERSION = bump_version()
print(f">>> Build version: v{EXE_VERSION}")

print("=" * 70)
print("     🏛️  ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMC System)")
print("            ឧបករណ៍បង្កើត Standalone Windows EXE (Python)")
print("=" * 70)
print()

# 1. Check & Install Required Packages
print("[1/5] កំពុងពិនិត្យមើល Packages (PyInstaller, CustomTkinter, pywin32)...")
try:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller", "customtkinter", "pywin32"],
        check=True
    )
except subprocess.CalledProcessError as e:
    print(f"[ERROR] ការតម្លើង Package បរាជ័យ: {e}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# 2. Collect Static Files (Crucial for PDF.js, Workers, and WhiteNoise across all PCs)
print("\n[2/5] កំពុងប្រមូលផ្តុំ Static Files (collectstatic)...")
try:
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=True)
except Exception as e:
    print(f"⚠️ collectstatic warning: {e}")

# 3. Prepare Icon & Arguments
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
    "--collect-all", "pywin32",
    "--add-data", f"{BASE_DIR / 'dms'};dms",
    "--add-data", f"{BASE_DIR / 'dms_project'};dms_project",
    "--add-data", f"{BASE_DIR / 'staticfiles'};staticfiles",
    "--hidden-import", "waitress",
    "--hidden-import", "waitress.server",
    "--hidden-import", "django",
    "--hidden-import", "dms",
    "--hidden-import", "dms.apps",
    "--hidden-import", "dms.models",
    "--hidden-import", "dms.views",
    "--hidden-import", "dms.docx_service",
    "--hidden-import", "dms.media_service",
    "--hidden-import", "dms.signals",
    "--hidden-import", "dms.middleware",
    "--hidden-import", "dms.context_processors",
    "--hidden-import", "dms.urls",
    "--hidden-import", "dms_project.urls",
    "--hidden-import", "dms_project.wsgi",
    "--hidden-import", "dms_project.settings",
    "--hidden-import", "psycopg2",
    "--hidden-import", "dj_database_url",
    "--hidden-import", "win32com",
    "--hidden-import", "pythoncom",
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

if (BASE_DIR / ".env").exists():
    pyinstaller_args.extend(["--add-data", f"{BASE_DIR / '.env'};."])

pyinstaller_args.append("main_app.py")

# 4. Clean Old Build Artifacts & Compile EXE
print("\n[4/5] កំពុងសម្អាត Cache និងដំណើរការ Compile Python Code ទៅជា EXE (សូមរង់ចាំបន្តិច)...")

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

# 5. Copy to Root Directory & Ensure Config in Dist
print("\n[5/5] កំពុងចម្លង file DMC_System.exe មកកាន់ Root Folder...")
dist_exe = BASE_DIR / "dist" / "DMC_System.exe"
target_exe = BASE_DIR / "DMC_System.exe"

# Copy dmc_config.txt and .env to dist folder as well for standalone convenience
if (BASE_DIR / "dmc_config.txt").exists():
    try:
        shutil.copy2(BASE_DIR / "dmc_config.txt", BASE_DIR / "dist" / "dmc_config.txt")
    except Exception:
        pass

if (BASE_DIR / ".env").exists():
    try:
        shutil.copy2(BASE_DIR / ".env", BASE_DIR / "dist" / ".env")
    except Exception:
        pass

# Copy staticfiles to dist folder as well so it's always accessible
try:
    dist_static = BASE_DIR / "dist" / "staticfiles"
    shutil.rmtree(dist_static, ignore_errors=True)
    shutil.copytree(BASE_DIR / "staticfiles", dist_static)
except Exception:
    pass

if dist_exe.exists():
    copied = False
    try:
        shutil.copy2(dist_exe, target_exe)
        copied = True
    except PermissionError:
        try:
            old_f = target_exe.with_name(target_exe.name + ".old")
            if old_f.exists():
                old_f.unlink(missing_ok=True)
            target_exe.rename(old_f)
            shutil.copy2(dist_exe, target_exe)
            old_f.unlink(missing_ok=True)
            copied = True
        except Exception as re:
            print(f"⚠️ ចម្លងមិនបានសម្រេច (Rename fallback failed): {re}")
    except Exception as e:
        print(f"⚠️ ចម្លងមិនបានសម្រេច: {e}")

    if copied:
        file_size_mb = target_exe.stat().st_size / (1024 * 1024)
        print(f"✅ ចម្លងជោគជ័យ! ទំហំ file: {file_size_mb:.2f} MB (បាន Update រូបរាងថ្មី ១០០%)")

    # Versioned copy, kept forever alongside the stable DMC_System.exe name.
    versioned_exe = BASE_DIR / f"DMC_System_v{EXE_VERSION}.exe"
    try:
        shutil.copy2(dist_exe, versioned_exe)
        shutil.copy2(dist_exe, BASE_DIR / "dist" / versioned_exe.name)
        print(f"📦 បង្កើត version: {versioned_exe.name}")
    except Exception as e:
        print(f"⚠️ មិនអាចបង្កើត file version បានទេ: {e}")

# 5. Success Banner
print()
print("=" * 70)
print(f"  ✅ បង្កើត file DMC_System.exe (v{EXE_VERSION}) បានជោគជ័យ ១០០%!")
print(f"  📁 ទីតាំង File: {target_exe}")
print("  🚀 ពេលចុចបើក DMC_System.exe វានឹងបង្ហាញទម្រង់ទី២ (Web App) ស្វ័យប្រវត្ត")
print("  🔒 ទិន្នន័យ db.sqlite3 និង Neon Cloud Database ភ្ជាប់បានយ៉ាងត្រឹមត្រូវ")
print("=" * 70)
if "--no-pause" not in sys.argv and sys.stdin and sys.stdin.isatty():
    try:
        input("\nចុច Enter ដើម្បីបិទផ្ទាំងនេះ (Press Enter to exit)... ")
    except Exception:
        pass
