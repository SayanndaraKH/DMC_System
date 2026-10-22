import os
import sys
import time
import json
import re
import shutil
import webbrowser
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        os.system("chcp 65001 >nul")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
GITHUB_REPO = "SayanndaraKH/DMC_System"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def get_lan_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def sync_android_main_activity(lan_ip):
    """
    Updates MainActivity.java with the latest LAN IP and a unique build timestamp
    to ensure GitHub Actions always detects an android_app change and builds a fresh APK.
    """
    main_activity = BASE_DIR / "android_app" / "app" / "src" / "main" / "java" / "com" / "dmc" / "system" / "MainActivity.java"
    if not main_activity.exists():
        print(f"⚠️ រកមិនឃើញ file {main_activity}")
        return False

    try:
        content = main_activity.read_text(encoding="utf-8")
        # 1. Update DEFAULT_URL
        content = re.sub(
            r'private static final String DEFAULT_URL = "http://[^"]+";',
            f'private static final String DEFAULT_URL = "http://{lan_ip}:8000/";',
            content
        )
        # 2. Update dialog placeholder
        content = re.sub(
            r'\(ឧទាហរណ៍៖ http://[^"]+\)៖',
            f'(ឧទាហរណ៍៖ http://{lan_ip}:8000/)៖',
            content
        )
        # 3. Add or update build timestamp trigger comment at the bottom
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trigger_pattern = r'// Auto-Build Trigger: [^\n]+'
        new_trigger = f'// Auto-Build Trigger: {timestamp_str}'
        if re.search(trigger_pattern, content):
            content = re.sub(trigger_pattern, new_trigger, content)
        else:
            content = content.rstrip() + f"\n\n{new_trigger}\n"

        main_activity.write_text(content, encoding="utf-8")
        print(f"  + បានកំណត់ Server URL ក្នុង APK: http://{lan_ip}:8000/")
        return True
    except Exception as e:
        print(f"⚠️ កំហុសក្នុងការកែប្រែ MainActivity.java: {e}")
        return False


def download_file_with_progress(url, dest_path):
    """Downloads a file with a live progress indicator."""
    req = urllib.request.Request(url, headers={'User-Agent': 'DMC-System-APK-Builder'})
    with urllib.request.urlopen(req, timeout=45) as response, open(dest_path, 'wb') as out_file:
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 128 * 1024
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            downloaded += len(chunk)
            out_file.write(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                mb_down = downloaded / (1024 * 1024)
                mb_tot = total_size / (1024 * 1024)
                print(f"\r   📥 កំពុងទាញយក: {percent:.1f}% ({mb_down:.1f} MB / {mb_tot:.1f} MB)...", end='', flush=True)
    print()


def auto_build_and_download_apk():
    """
    Full automated pipeline:
    1. Prepares Android project with current active LAN IP.
    2. Pushes to GitHub to trigger GitHub Actions Cloud builder.
    3. Monitors Cloud build in real-time until completion.
    4. Automatically pulls and downloads DMC_System.apk directly into dist/ folder.
    5. Opens Windows File Explorer highlighting the new APK!
    """
    print("=" * 76)
    print("  📱 ប្រព័ន្ធគ្រប់គ្រងធនធានមនុស្ស (DMC System) - AUTO BUILD APK INTO DIST")
    print("     ដំណើរការបង្កើត File APK ចូលក្នុង dist/ ដោយស្វ័យប្រវត្ត ១០០%")
    print("=" * 76)
    print()

    lan_ip = get_lan_ip()
    print(f"🌐 អាសយដ្ឋាន Server Wi-Fi បច្ចុប្បន្ន: http://{lan_ip}:8000/")
    print(f"📂 ទីតាំងគោលដៅ: {BASE_DIR / 'dist' / 'DMC_System.apk'}")
    print()

    # Step 1: Configure Android project with current IP
    print("🚀 [ជំហានទី១/៣] កំពុងរៀបចំកូដ Android Project និងបញ្ចូលលេខ IP បច្ចុប្បន្ន...")
    sync_android_main_activity(lan_ip)

    # Step 2: Push to GitHub to trigger GitHub Actions
    push_script = BASE_DIR / "push_to_github.py"
    if not push_script.exists():
        print("❌ រកមិនឃើញ file push_to_github.py ឡើយ!")
        return False

    print("\n📤 កំពុងបញ្ជូនកូដទៅកាន់ GitHub ដើម្បីដំណើរការ GitHub Actions Cloud Build...")
    commit_msg = f"🚀 Auto-Build Android APK: Sync Server IP http://{lan_ip}:8000/"
    push_res = subprocess.run([sys.executable, str(push_script), commit_msg, "--no-pause"])
    if push_res.returncode != 0:
        print("\n❌ [បរាជ័យ] មិនអាច Push ទៅកាន់ GitHub បានឡើយ សូមពិនិត្យមើលការតភ្ជាប់អ៊ីនធឺណិត។")
        return False

    # Step 3: Monitor GitHub Actions Cloud Build
    print("\n" + "=" * 76)
    print("  ☁️  [ជំហានទី២/៣] GitHub Actions Cloud កំពុង Compile & Build file DMC_System.apk...")
    print("      (ដំណើរការ Cloud ជាធម្មតាត្រូវការពេលប្រហែល ៤០ ទៅ ៦០ វិនាទី)")
    print("=" * 76)

    start_time = time.time()
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs?branch=main&per_page=5"
    build_success = False
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    spin_idx = 0

    # Wait a few seconds for GitHub to register the new run
    time.sleep(6)

    max_wait_seconds = 240  # 4 minutes timeout
    while time.time() - start_time < max_wait_seconds:
        elapsed = int(time.time() - start_time)
        spin_char = spinner[spin_idx % len(spinner)]
        spin_idx += 1

        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "DMC-System-APK-Builder"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                runs = data.get("workflow_runs", [])

                matching_run = None
                for r in runs:
                    if r.get("name") == "📱 Build DMC System Android APK":
                        matching_run = r
                        break

                if matching_run:
                    status = matching_run.get("status")  # queued, in_progress, completed
                    conclusion = matching_run.get("conclusion")  # success, failure, etc.

                    mins, secs = divmod(elapsed, 60)
                    time_display = f"{mins:02d}:{secs:02d}"

                    if status == "completed":
                        if conclusion == "success":
                            print(f"\r  ✅ [{time_display}] GitHub Actions Cloud បាន Compile APK ជោគជ័យ ១០០%!                 ")
                            build_success = True
                            break
                        else:
                            print(f"\r  ❌ [{time_display}] Cloud Build បានបញ្ចប់ដោយលទ្ធផល: {conclusion}                  ")
                            break
                    else:
                        status_kh = "កំពុងដំណើរការ Compile" if status == "in_progress" else "រង់ចាំចាប់ផ្តើម"
                        print(f"\r  {spin_char} [{time_display}] ស្ថានភាព Cloud: {status_kh} ({status})...", end='', flush=True)
                else:
                    mins, secs = divmod(elapsed, 60)
                    print(f"\r  {spin_char} [{mins:02d}:{secs:02d}] កំពុងរង់ចាំ GitHub Actions ចាប់ផ្តើម...", end='', flush=True)
        except Exception:
            pass

        time.sleep(4)

    if not build_success:
        print("\n⚠️ មិនអាចរង់ចាំដល់ Cloud បញ្ចប់បានឡើយ ឬដំណើរការលើសពេលកំណត់។")
        print("   សូមចូលទៅកាន់ https://github.com/SayanndaraKH/DMC_System/actions ដើម្បីពិនិត្យមើល។")
        return False

    # Step 4: Download / Sync DMC_System.apk directly into dist/
    print("\n" + "=" * 76)
    print("  📥 [ជំហានទី៣/៣] កំពុងទាញយក file DMC_System.apk ដាក់ចូលក្នុង dist/ ដោយស្វ័យប្រវត្ត...")
    print("=" * 76)

    dist_folder = BASE_DIR / "dist"
    dist_folder.mkdir(parents=True, exist_ok=True)
    dist_apk = dist_folder / "DMC_System.apk"

    # Wait 3 seconds for GitHub branch commit to settle
    time.sleep(3)

    # 1. Pull changes directly via git
    try:
        subprocess.run(["git", "pull", "--no-rebase", "origin", "main"], capture_output=True, text=True, timeout=30)
    except Exception:
        pass

    # 2. Directly ensure latest APK is downloaded using cache-busting timestamp
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/dist/DMC_System.apk?t={int(time.time())}"
    need_download = True
    if dist_apk.exists() and dist_apk.stat().st_size > 1024 * 1024:
        # Check if file was modified recently (within last 4 minutes)
        if time.time() - dist_apk.stat().st_mtime < 240:
            need_download = False
            print("  + បាន Sync យក File ពី GitHub ដោយជោគជ័យ!")

    if need_download:
        try:
            print(f"  + កំពុងទាញយកផ្ទាល់ពី GitHub Cloud Server...")
            download_file_with_progress(raw_url, dist_apk)
        except Exception as e:
            print(f"  ⚠️ មិនអាចទាញយកតាម direct URL: {e}")

    # Verify final APK file
    if dist_apk.exists() and dist_apk.stat().st_size > 500 * 1024:
        size_mb = dist_apk.stat().st_size / (1024 * 1024)
        mtime_str = datetime.fromtimestamp(dist_apk.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        print()
        print("=" * 76)
        print("  🎉 [ជោគជ័យ ១០០%] FILE APK ត្រូវបានបង្កើត និងដាក់ចូលក្នុង DIST រួចរាល់!")
        print("=" * 76)
        print(f"  📁 ទីតាំង File APK : {dist_apk}")
        print(f"  📦 ទំហំ File      : {size_mb:.2f} MB")
        print(f"  🌐 Server URL ក្នុង APK: http://{lan_ip}:8000/")
        print(f"  ⏱️ ម៉ោងបង្កើត      : {mtime_str}")
        print("=" * 76)
        print()
        print("  📱 ឥឡូវនេះ លោកអ្នកអាចចម្លង file «dist/DMC_System.apk» ទៅដំឡើងលើទូរស័ព្ទដៃបានភ្លាមៗ!")
        print()

        # Open File Explorer and highlight the file
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{dist_apk}"')
        except Exception:
            pass
        return True
    else:
        print("\n❌ មិនអាចស្វែងរក ឬទាញយក file dist/DMC_System.apk បានឡើយ។")
        return False


def show_mobile_setup():
    lan_ip = get_lan_ip()
    print("\n" + "=" * 74)
    print("  📲 វិធីដំឡើងជា App លើទូរស័ព្ទដៃផ្ទាល់ (WebAPK PWA - ងាយស្រួល & លឿនបំផុត)")
    print("=" * 74)
    print(f"  1. សូមប្រាកដថាទូរស័ព្ទដៃ និងកុំព្យូទ័រនេះ ភ្ជាប់ Wi-Fi តែមួយ។")
    print(f"  2. បើកកម្មវិធី Google Chrome លើទូរស័ព្ទដៃ រួចវាយអាសយដ្ឋាន៖")
    print(f"     👉 http://{lan_ip}:8000/   ឬ   http://syd.local:8000/")
    print(f"  3. Chrome នឹងលោតប៊ូតុង «បន្ថែមទៅអេក្រង់ដើម / Install DMC System App»")
    print(f"     ចុច Install នោះទូរស័ព្ទនឹងមាន Icon App DMC System លើអេក្រង់ដូច App ពិត ១០០%!")
    print("=" * 74)


def main():
    # If called with --auto or --build (e.g. from BUILD_ANDROID_APK.bat), execute directly!
    if "--auto" in sys.argv or "--build" in sys.argv:
        success = auto_build_and_download_apk()
        if not success:
            sys.exit(1)
        return

    while True:
        clear_screen()
        lan_ip = get_lan_ip()
        print("=" * 74)
        print("  📱 ប្រព័ន្ធគ្រប់គ្រងធនធានមនុស្ស (DMC System) - ជំនួយការបង្កើត & ដំឡើង APK")
        print("     DMC System Android Mobile App Builder & Cloud Assistant")
        print("=" * 74)
        print(f"  🌐 អាសយដ្ឋានបណ្តាញ Wi-Fi បច្ចុប្បន្ន: http://{lan_ip}:8000/")
        print("--------------------------------------------------------------------------")
        print("  [1] 🚀 បង្កើត File APK ចូលក្នុង dist/ ដោយស្វ័យប្រវត្ត (Auto Build into dist/)")
        print("  [2] 📱 បើកឧបករណ៍មើលសាកល្បងលើទូរស័ព្ទ (Mobile Preview Simulator)")
        print("  [3] 📲 របៀបដំឡើង DMC System លើទូរស័ព្ទភ្លាមៗ (WebAPK PWA មិនបាច់ Build)")
        print("  [4] 📂 បើកថតកូដប្រភព Android Studio Project (android_app/)")
        print("  [5] 🌐 មើលអាសយដ្ឋានភ្ជាប់ទូរស័ព្ទ (IP.txt)")
        print("  [0] ចាកចេញ (Exit)")
        print("--------------------------------------------------------------------------")

        try:
            opt = input("\n👉 សូមជ្រើសរើសជម្រើសមួយ [0-5]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 សូមអរគុណ! បានចាកចេញពីកម្មវិធី។")
            break

        if opt == "1":
            auto_build_and_download_apk()
            input("\nចុច Enter ដើម្បីត្រឡប់ទៅម៉ឺនុយដើម... ")
        elif opt == "2":
            print("\nកំពុងបើកឧបករណ៍មើលសាកល្បងលើទូរស័ព្ទ...")
            webbrowser.open("http://127.0.0.1:8000/mobile-preview/")
            input("\nចុច Enter ដើម្បីត្រឡប់ទៅម៉ឺនុយដើម... ")
        elif opt == "3":
            show_mobile_setup()
            input("\nចុច Enter ដើម្បីត្រឡប់ទៅម៉ឺនុយដើម... ")
        elif opt == "4":
            android_folder = BASE_DIR / "android_app"
            if android_folder.is_dir():
                os.system(f'explorer "{android_folder}"')
            else:
                print("❌ មិនទាន់រកឃើញថត android_app ឡើយ")
            input("\nចុច Enter ដើម្បីត្រឡប់ទៅម៉ឺនុយដើម... ")
        elif opt == "5":
            ip_file = BASE_DIR / "IP.txt"
            if ip_file.exists():
                print("\n" + ip_file.read_text(encoding="utf-8", errors="replace"))
            else:
                print(f"IP: http://{lan_ip}:8000/")
            input("\nចុច Enter ដើម្បីត្រឡប់ទៅម៉ឺនុយដើម... ")
        elif opt == "0":
            print("\n👋 សូមអរគុណ! បានចាកចេញពីកម្មវិធី។")
            break
        else:
            print("\n⚠️ ជម្រើសមិនត្រឹមត្រូវ សូមបញ្ចូលលេខពី 0 ដល់ 5។")
            input("ចុច Enter ដើម្បីសាកល្បងម្តងទៀត... ")


if __name__ == "__main__":
    main()
