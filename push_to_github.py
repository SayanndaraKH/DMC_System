import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

print("=" * 72)
print("     🏛️  ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMC System)")
print("       ឧបករណ៍បញ្ជូនទម្រង់ថ្មី ទិន្នន័យ និងរូបភាព/ឯកសារយោងទៅកាន់ GITHUB")
print("=" * 72)
print()


def find_git():
    """Locates the git executable on the system."""
    candidates = [
        "git",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ]
    for c in candidates:
        if c == "git" or os.path.exists(c):
            try:
                res = subprocess.run([c, "--version"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    return c, res.stdout.strip()
            except Exception:
                pass
    return None, None


def main():
    git_bin, git_ver = find_git()
    if not git_bin:
        print("❌ [កំហុស] រកមិនឃើញ Git លើកុំព្យូទ័រនេះឡើយ! សូមដំឡើង Git ជាមុនសិន។")
        input("\nចុច Enter ដើម្បីចាកចេញ... ")
        sys.exit(1)

    print(f"[1/4] រកឃើញ Git: {git_ver}")

    # Ensure dist/DMC_System.exe is synced to root if present
    dist_exe = BASE_DIR / "dist" / "DMC_System.exe"
    target_exe = BASE_DIR / "DMC_System.exe"
    if dist_exe.exists():
        try:
            shutil.copy2(dist_exe, target_exe)
            print("  + បាន Sync File DMC_System.exe រួចរាល់")
        except Exception:
            pass

    # Step 2: Check git status
    print("\n[2/4] កំពុងពិនិត្យមើលស្ថានភាព File ដែលបានកែប្រែ (Git Status)...")
    status_res = subprocess.run([git_bin, "status", "-s"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    status_out = (status_res.stdout or "").strip()

    if status_out:
        print("-" * 50)
        print(status_out)
        print("-" * 50)
    else:
        print("  ℹ️ គ្មាន File ថ្មីដែលត្រូវបានកែប្រែទេ (All files up to date)")

    # Step 3: Add and Commit automatically
    print("\n[3/4] កំពុងបន្ថែម File និង Commit ដោយស្វ័យប្រវត្ត...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    custom_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if custom_args and custom_args[0].strip():
        commit_msg = custom_args[0].strip()
    else:
        commit_msg = f"Auto Update DMC System: {timestamp}"

    # Write version info file so client PCs immediately know the update version
    try:
        version_data = {
            "timestamp": timestamp,
            "message": commit_msg
        }
        with open(BASE_DIR / "current_version.json", "w", encoding="utf-8") as vf:
            json.dump(version_data, vf, indent=2, ensure_ascii=False)
        if (BASE_DIR / "dist").is_dir():
            with open(BASE_DIR / "dist" / "current_version.json", "w", encoding="utf-8") as vf:
                json.dump(version_data, vf, indent=2, ensure_ascii=False)
    except Exception:
        pass

    subprocess.run([git_bin, "add", "-A"], check=True)

    # Commit only if there are staged changes
    diff_res = subprocess.run([git_bin, "diff", "--cached", "--quiet"])
    if diff_res.returncode != 0:
        commit_res = subprocess.run([git_bin, "commit", "-m", commit_msg], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if commit_res.returncode == 0:
            print(f"  + បាន Commit ជោគជ័យ: «{commit_msg}»")
        else:
            print(f"  [Notice] Commit output: {(commit_res.stdout or commit_res.stderr or '').strip()}")
    else:
        print("  + មិនមានការផ្លាស់ប្តូរថ្មីសម្រាប់ Commit ឡើយ (Working tree clean)")

    # Step 4: Push to GitHub
    print("\n[4/4] កំពុងបញ្ជូនទៅកាន់ GitHub (git push origin main)...")
    push_res = subprocess.run([git_bin, "push", "-u", "origin", "main"], capture_output=True, text=True, encoding="utf-8", errors="replace")

    if push_res.returncode == 0:
        # Update current_version.json with the exact pushed commit SHA
        try:
            head_sha = subprocess.run([git_bin, "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
            version_data = {
                "sha": head_sha,
                "timestamp": timestamp,
                "message": commit_msg
            }
            with open(BASE_DIR / "current_version.json", "w", encoding="utf-8") as vf:
                json.dump(version_data, vf, indent=2, ensure_ascii=False)
            if (BASE_DIR / "dist").is_dir():
                with open(BASE_DIR / "dist" / "current_version.json", "w", encoding="utf-8") as vf:
                    json.dump(version_data, vf, indent=2, ensure_ascii=False)
        except Exception:
            pass

        print()
        print("=" * 72)
        print("  ✅ [ជោគជ័យ ១០០%] ទិន្នន័យ កូដថ្មី និង File Media ត្រូវបានបញ្ជូនទៅ GitHub រួចរាល់!")
        print()
        print("  📌 នៅលើ User PC:")
        print("     ប៊ូតុង Update ក្នុង Form នឹងបង្ហាញភ្លាមៗថា៖ «✨ មានកំណែទម្រង់ថ្មី! ចុចដើម្បី Update»")
        print("     ពេល User ចុចលើវា នោះប្រព័ន្ធនឹងទាញយកកូដ និងទម្រង់ថ្មីនេះមកជំនួសស្វ័យប្រវត្ត!")
        print("=" * 72)
    else:
        print()
        print("=" * 72)
        print("  ❌ [បញ្ហាក្នុងការ Push] សូមពិនិត្យមើលសារខាងក្រោម៖")
        print("-" * 50)
        print(push_res.stderr.strip() or push_res.stdout.strip())
        print("=" * 72)

    if "--no-pause" not in sys.argv and sys.stdin and sys.stdin.isatty():
        try:
            input("\nចុច Enter ដើម្បីបិទផ្ទាំងនេះ (Press Enter to exit)... ")
        except Exception:
            pass


if __name__ == "__main__":
    main()
