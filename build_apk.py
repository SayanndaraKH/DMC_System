import os
import sys
import webbrowser
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    # Set Windows console code page to 65001 (UTF-8)
    try:
        os.system("chcp 65001 >nul")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)


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


def print_banner():
    print("=" * 74)
    print("  📱 ប្រព័ន្ធគ្រប់គ្រងធនធានមនុស្ស (DMC System) - ជំនួយការបង្កើត & ដំឡើង APK")
    print("     DMC System Android Mobile App Builder & Cloud Assistant")
    print("=" * 74)
    print()


def run_push_to_github():
    print("\n🚀 [ជំហានទី១] កំពុងដំណើរការ Push កូដ និង Android Project ទៅកាន់ GitHub...")
    push_script = BASE_DIR / "push_to_github.py"
    if push_script.exists():
        try:
            res = subprocess.run([sys.executable, str(push_script), "Build Android APK Workflow Trigger"])
            if res.returncode == 0:
                print("\n" + "=" * 74)
                print("  ✅ [ជោគជ័យ] កូដត្រូវបានបញ្ជូនទៅ GitHub រួចរាល់!")
                print("  ☁️  GitHub Actions Cloud កំពុងដំណើរការ compile បង្កើត file DMC_System.apk")
                print("  📥 លោកអ្នកអាចចូលទៅកាន់ GitHub -> Tab «Actions» ដើម្បីទាញយក file APK។")
                print("=" * 74)
                
                # Try to get repo remote URL and open Actions in browser
                try:
                    remote_res = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True)
                    remote_url = remote_res.stdout.strip()
                    if remote_url:
                        # Convert git@github.com:user/repo.git to https://github.com/user/repo
                        if remote_url.startswith("git@github.com:"):
                            clean_url = "https://github.com/" + remote_url.replace("git@github.com:", "").replace(".git", "")
                        else:
                            clean_url = remote_url.replace(".git", "")
                        actions_url = f"{clean_url}/actions"
                        print(f"\n👉 អាសយដ្ឋាន Actions: {actions_url}")
                        choice = input("តើអ្នកចង់បើកទំព័រ GitHub Actions ក្នុង Browser ឥឡូវនេះដែរឬទេ? (y/n): ").strip().lower()
                        if choice in ['y', 'yes', 'បាទ', 'ចាស']:
                            webbrowser.open(actions_url)
                except Exception:
                    pass
            else:
                print("\n❌ មានបញ្ហាក្នុងការ Push ទៅកាន់ GitHub សូមពិនិត្យមើលសារខាងលើ។")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print("❌ រកមិនឃើញ file push_to_github.py ឡើយ!")


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
    while True:
        clear_screen()
        print_banner()
        lan_ip = get_lan_ip()
        print(f"  🌐 អាសយដ្ឋានបណ្តាញ Wi-Fi បច្ចុប្បន្ន: http://{lan_ip}:8000/")
        print("--------------------------------------------------------------------------")
        print("  [1] 📱 បើកឧបករណ៍មើលសាកល្បងលើទូរស័ព្ទ (Mobile Preview Simulator)")
        print("  [2] 🚀 បង្កើត APK តាមរយៈ GitHub Actions Cloud (ណែនាំខ្លាំង - ស្រួលបំផុត)")
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
            print("\nកំពុងបើកឧបករណ៍មើលសាកល្បងលើទូរស័ព្ទ...")
            webbrowser.open("http://127.0.0.1:8000/mobile-preview/")
            input("\nចុច Enter ដើម្បីត្រឡប់ទៅម៉ឺនុយដើម... ")
        elif opt == "2":
            run_push_to_github()
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
