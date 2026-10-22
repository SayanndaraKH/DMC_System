import os
import sys
import time
import re
import subprocess
import webbrowser
import urllib.request
from pathlib import Path

# Force UTF-8 encoding on Windows console
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
CLOUDFLARED_EXE = BASE_DIR / "cloudflared.exe"


def check_and_download_cloudflared():
    if CLOUDFLARED_EXE.exists() and CLOUDFLARED_EXE.stat().st_size > 10 * 1024 * 1024:
        return True

    print("📥 កំពុងទាញយកកម្មវិធី Cloudflare Tunnel Engine (cloudflared.exe)...")
    download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try:
        cmd = ["curl.exe", "-L", "-o", str(CLOUDFLARED_EXE), download_url]
        res = subprocess.run(cmd, check=True)
        if CLOUDFLARED_EXE.exists() and CLOUDFLARED_EXE.stat().st_size > 10 * 1024 * 1024:
            print("✅ បានទាញយក cloudflared.exe ដោយជោគជ័យ!")
            return True
    except Exception as e:
        print(f"❌ មិនអាចទាញយក cloudflared.exe: {e}")
        return False
    return False


def is_django_running():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', 8000)) == 0


def update_android_app_url(tunnel_url):
    """
    Updates MainActivity.java with the public Cloudflare Tunnel URL so the APK
    connects to this URL without requiring local IP.
    """
    main_activity = BASE_DIR / "android_app" / "app" / "src" / "main" / "java" / "com" / "dmc" / "system" / "MainActivity.java"
    if not main_activity.exists():
        return

    try:
        content = main_activity.read_text(encoding="utf-8")
        if not tunnel_url.endswith("/"):
            tunnel_url += "/"
        content = re.sub(
            r'private static final String DEFAULT_URL = "[^"]+";',
            f'private static final String DEFAULT_URL = "{tunnel_url}";',
            content
        )
        main_activity.write_text(content, encoding="utf-8")
    except Exception:
        pass


def update_ip_txt(tunnel_url):
    ip_file = BASE_DIR / "IP.txt"
    try:
        content = (
            "====================================================================\n"
            "🌐 អាសយដ្ឋាន CLOUDFLARE PUBLIC INTERNET TUNNEL (សម្រាប់ទូរស័ព្ទដៃ):\n"
            "   (អាចប្រើលើទូរស័ព្ទដៃគ្រប់ទីកន្លែង ទោះប្រើ Wi-Fi ផ្សេង ឬ 4G/5G ក៏ដោយ)\n"
            "====================================================================\n"
            f"👉 {tunnel_url}\n"
            "====================================================================\n\n"
            "🔹 សម្រាប់ប្រើលើកុំព្យូទ័រផ្ទាល់ (Localhost):\n"
            "👉 http://127.0.0.1:8000/\n"
        )
        ip_file.write_text(content, encoding="utf-8")
    except Exception:
        pass


def main():
    print("=" * 76)
    print("  🌐 ប្រព័ន្ធ DMC SYSTEM - ដំណើរការ CLOUDFLARE INTERNET TUNNEL (ជម្រើសទី ២)")
    print("     បើកអាសយដ្ឋាន HTTPS សាធារណៈសម្រាប់ទូរស័ព្ទដៃ (Wi-Fi, 4G, 5G គ្រប់ទីកន្លែង)")
    print("=" * 76)
    print()

    # 1. Ensure cloudflared is present
    if not check_and_download_cloudflared():
        input("\nចុច Enter ដើម្បីចាកចេញ... ")
        sys.exit(1)

    # 2. Check if local Django server is running
    if not is_django_running():
        print("⚠️ [ដំណឹង] មិនទាន់ឃើញ DMC System Server (Port 8000) ដំណើរការនៅឡើយទេ។")
        print("🚀 កំពុងដំណើរការបើក DMC System Server ជាស្វ័យប្រវត្ត...")
        start_bat = BASE_DIR / "RUN_DMS.bat"
        if start_bat.exists():
            subprocess.Popen([str(start_bat)], shell=True)
            print("⏳ កំពុងរង់ចាំ Server ចាប់ផ្តើម...")
            for _ in range(20):
                time.sleep(1)
                if is_django_running():
                    break
        if not is_django_running():
            print("❌ មិនអាចបើក Server បានឡើយ សូមចុច RUN_DMS.bat ជាមុនសិន។")
            input("\nចុច Enter ដើម្បីចាកចេញ... ")
            sys.exit(1)

    print("✅ DMC System Web Server (Port 8000) កំពុងដំណើរការជាធម្មតា។")
    print("\n🚀 កំពុងបង្កើតផ្លូវតភ្ជាប់ Cloudflare Secure HTTPS Tunnel ទៅកាន់អ៊ីនធឺណិត...")

    # Launch cloudflared process
    proc = subprocess.Popen(
        [str(CLOUDFLARED_EXE), "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    tunnel_url = None
    url_pattern = re.compile(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com')

    start_t = time.time()
    while time.time() - start_t < 40:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            match = url_pattern.search(line)
            if match:
                tunnel_url = match.group(0)
                break

    if not tunnel_url:
        print("❌ មិនអាចទាញយក Tunnel URL បានឡើយ សូមពិនិត្យមើលការតភ្ជាប់អ៊ីនធឺណិត។")
        input("\nចុច Enter ដើម្បីចាកចេញ... ")
        sys.exit(1)

    # Save to files
    update_ip_txt(tunnel_url)
    update_android_app_url(tunnel_url)
    (BASE_DIR / "current_tunnel_url.txt").write_text(tunnel_url, encoding="utf-8")

    print()
    print("=" * 76)
    print("  🎉 [ជោគជ័យ ១០០%] CLOUDFLARE PUBLIC TUNNEL ត្រូវបានបង្កើតរួចរាល់!")
    print("=" * 76)
    print()
    print(f"  👉 អាសយដ្ឋាន HTTPS សាធារណៈសម្រាប់ទូរស័ព្ទដៃ៖")
    print(f"     🔗 {tunnel_url}")
    print()
    print("  📱 របៀបប្រើប្រាស់លើទូរស័ព្ទដៃ (Wi-Fi ណាក៏បាន / 4G / 5G / គ្រប់ទីកន្លែង)៖")
    print("  --------------------------------------------------------------------------")
    print("  ១. បើកកម្មវិធី Google Chrome លើទូរស័ព្ទដៃ រួចវាយអាសយដ្ឋាន Link ខាងលើ។")
    print("  ២. ឬនៅលើ APK៖ ចុច «ប្តូរលេខ IP Server» រួចដាក់ Link ខាងលើចូល។")
    print("  ៣. ឬចុច BUILD_ANDROID_APK.bat ដើម្បីបង្កើត APK ថ្មីដែលមាន Link នេះស្រាប់!")
    print("=" * 76)
    print("  📌 ចំណាំ៖ សូមកុំបិទផ្ទាំងខ្មៅនេះ (កុំបិទ Window នេះ) ដើម្បីឲ្យផ្លូវ Tunnel បន្តដំណើរការ។")
    print("=" * 76)
    print()

    # Keep tunnel process alive and print status
    try:
        while proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 បានបិទដំណើរការ Cloudflare Tunnel។")
        proc.terminate()


if __name__ == "__main__":
    main()
