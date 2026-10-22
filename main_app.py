import os
import sys
import time
import socket
import subprocess
import threading
import webbrowser
import urllib.request
from pathlib import Path

import json
import shutil
import zipfile
import logging
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

# Set BASE_DIR (Supports both standalone Python and PyInstaller Frozen EXE, including inside dist/)
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).resolve().parent
    if (exe_dir / "run.py").exists() or (exe_dir / "manage.py").exists():
        BASE_DIR = exe_dir
    elif (exe_dir.parent / "run.py").exists() or (exe_dir.parent / "manage.py").exists():
        BASE_DIR = exe_dir.parent
    else:
        BASE_DIR = exe_dir
else:
    BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

try:
    import customtkinter as ctk
    from tkinter import messagebox
except ImportError:
    import tkinter as ctk
    from tkinter import messagebox

# Configure Appearance
try:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except Exception:
    pass

def get_resource_path(relative_path):
    """Get absolute path to resource, supports normal dev, relative, and PyInstaller frozen onefile"""
    try:
        base_path = Path(sys._MEIPASS)
        p = base_path / relative_path
        if p.exists():
            return p
    except Exception:
        pass
    p = BASE_DIR / relative_path
    if p.exists():
        return p
    return None

CONFIG_FILE = BASE_DIR / "dmc_config.txt"
ENV_FILE = BASE_DIR / ".env"
ICON_FILE = get_resource_path("dms/static/dms/img/favicon.ico") or (BASE_DIR / "favicon.ico")
LOGO_FILE = get_resource_path("dms/static/dms/img/logo.png") or (BASE_DIR / "logo.png")
ICON_SERVER_FILE = get_resource_path("dms/static/dms/img/icon_server.png") or (BASE_DIR / "dms/static/dms/img/icon_server.png")
ICON_DB_FILE = get_resource_path("dms/static/dms/img/icon_database.png") or (BASE_DIR / "dms/static/dms/img/icon_database.png")
ICON_DESKTOP_FILE = get_resource_path("dms/static/dms/img/icon_desktop.png") or (BASE_DIR / "dms/static/dms/img/icon_desktop.png")


def safe_replace_file(src_path, dst_path):
    """
    Safely replaces dst_path with src_path on Windows, even if dst_path is a currently running executable.
    On Windows, running executables can be renamed but not overwritten directly.
    """
    src = Path(src_path)
    dst = Path(dst_path)
    if not src.exists():
        return False
    try:
        shutil.copy2(src, dst)
        return True
    except PermissionError:
        try:
            old_file = dst.with_name(dst.name + ".old")
            if old_file.exists():
                try:
                    old_file.unlink()
                except Exception:
                    pass
            dst.rename(old_file)
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            logger.warning(f"Failed to replace {dst} using rename fallback: {e}")
            return False
    except Exception as e:
        logger.warning(f"Failed to copy {src} to {dst}: {e}")
        return False


# Clean up any leftover .old files from previous updates
for old_name in ["DMC_System.exe.old", "DMC_System_Client.exe.old"]:
    for d in [BASE_DIR, BASE_DIR / "dist"]:
        old_f = d / old_name
        if old_f.exists():
            try:
                old_f.unlink()
            except Exception:
                pass


def get_local_version_data():
    """Reads local version info from current_version.json or git."""
    for loc in [BASE_DIR / "current_version.json", BASE_DIR / "dist" / "current_version.json"]:
        if loc.exists():
            try:
                with open(loc, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    if (BASE_DIR / ".git").is_dir():
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=2)
            if r.returncode == 0:
                return {"sha": r.stdout.strip(), "timestamp": "", "message": "", "version": ""}
        except Exception:
            pass
    return {"sha": "", "timestamp": "", "message": "", "version": ""}


def save_local_version_data(sha, message="", timestamp="", version=""):
    """Saves local version info to current_version.json."""
    try:
        data = {
            "sha": sha or "",
            "version": version or time.strftime("%Y%m%d.%H%M%S"),
            "message": message or "",
            "timestamp": timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(BASE_DIR / "current_version.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if (BASE_DIR / "dist").is_dir():
            with open(BASE_DIR / "dist" / "current_version.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def check_github_update_status():
    """
    Checks GitHub to see if PUSH_TO_GITHUB has pushed a new update for DMC_System.exe.
    Prioritizes raw.githubusercontent.com for dist/current_version.json (NO rate limit!),
    with fallback to api.github.com.
    """
    local_data = get_local_version_data()
    local_sha = (local_data.get('sha') or '').strip()
    local_ts = (local_data.get('timestamp') or '').strip()
    local_ver = (local_data.get('version') or '').strip()

    # 1. Primary: Check raw current_version.json in dist/ (NO rate limit!)
    try:
        raw_url = f'https://raw.githubusercontent.com/SayanndaraKH/DMC_System/main/dist/current_version.json?t={int(time.time())}'
        req = urllib.request.Request(
            raw_url,
            headers={
                'User-Agent': 'DMC-UpdateChecker/1.0',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            remote_sha = (data.get('sha') or '').strip()
            remote_ts = (data.get('timestamp') or '').strip()
            remote_ver = (data.get('version') or '').strip()
            commit_msg = (data.get('message') or '').strip().split('\n')[0]

            has_update = False
            if remote_sha and local_sha:
                has_update = (remote_sha != local_sha)
            elif remote_ver and local_ver:
                has_update = (remote_ver != local_ver)
            elif remote_ts and local_ts:
                has_update = (remote_ts > local_ts)
            elif remote_sha or remote_ts:
                has_update = True

            return {
                'has_update': has_update,
                'remote_sha': remote_sha or remote_ver or remote_ts,
                'commit_msg': commit_msg or 'កំណែទម្រង់ថ្មី',
                'commit_date': remote_ts,
                'error': None
            }
    except Exception:
        pass

    # 2. Secondary fallback: Check GitHub API commits/main
    try:
        url = f'https://api.github.com/repos/SayanndaraKH/DMC_System/commits/main?t={int(time.time())}'
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'DMC-UpdateChecker/1.0',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            remote_sha = data.get('sha', '').strip()
            commit_msg = data.get('commit', {}).get('message', '').strip().split('\n')[0]
            commit_date = data.get('commit', {}).get('committer', {}).get('date', '')
            has_update = bool(remote_sha and (remote_sha != local_sha))
            return {
                'has_update': has_update,
                'remote_sha': remote_sha,
                'commit_msg': commit_msg,
                'commit_date': commit_date,
                'error': None
            }
    except Exception as e:
        return {
            'has_update': False,
            'remote_sha': '',
            'commit_msg': '',
            'commit_date': '',
            'error': str(e)
        }


def free_port_8000():
    if sys.platform == "win32":
        try:
            cmd = f'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {{ if ($_ -ne {os.getpid()}) {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }} }}"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

_waitress_started = False

def start_embedded_server():
    global _waitress_started
    if _waitress_started:
        return
    _waitress_started = True

    def _serve():
        try:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dms_project.settings')
            os.environ['USE_LOCAL_SQLITE'] = 'False'
            import django
            django.setup()

            # Auto-migrate database on start
            try:
                from django.core.management import call_command
                call_command('migrate', interactive=False)
            except Exception:
                pass

            from waitress import serve
            from dms_project.wsgi import application
            serve(application, host='0.0.0.0', port=8000, threads=8, _quiet=True)
        except Exception as e:
            print(f"Waitress server error: {e}")

    t = threading.Thread(target=_serve, daemon=True)
    t.start()


class DMCMainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("សូមស្វាគមន៍មកកាន់កម្មវិធីគ្រប់គ្រងធនធានមនុស្ស - DMC Desktop Control Center")
        self.center_window(920, 750)

        # Strictly lock window dimensions to prevent any resizing or maximizing
        self.resizable(False, False)
        self.maxsize(920, 750)
        self.minsize(920, 750)

        # Set Icon if available
        if ICON_FILE and ICON_FILE.exists():
            try:
                self.iconbitmap(str(ICON_FILE))
            except Exception:
                pass
        if LOGO_FILE and LOGO_FILE.exists():
            try:
                self._icon_photo = ImageTk.PhotoImage(Image.open(LOGO_FILE))
                self.wm_iconphoto(True, self._icon_photo)
            except Exception:
                pass

        # Network Info
        self.hostname = socket.gethostname()
        self.lan_ip = self.detect_lan_ip()
        self.target_url = self.load_target_url()

        # Database Mode
        self.db_mode = self.detect_db_mode()

        # State flags
        self.has_auto_launched = False
        self.is_monitoring = True
        self._has_new_update = False
        self._remote_sha = None
        self._remote_msg = None
        self._is_updating = False

        # UI Components
        self.create_widgets()

        # Start live background GitHub update checker
        threading.Thread(target=self._start_update_polling, daemon=True).start()

        # Background server auto-start & auto-launch Form 2
        threading.Thread(target=self.auto_start_and_launch_form2, daemon=True).start()

        # Live background health-check loop
        self.monitor_thread = threading.Thread(target=self.monitor_server_status, daemon=True)
        self.monitor_thread.start()

    def center_window(self, width=920, height=750):
        """Centers the window perfectly on the primary display and fixes dimensions."""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, int((screen_width - width) / 2))
        y = max(0, int((screen_height - height) / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def detect_lan_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def detect_db_mode(self):
        if ENV_FILE.exists():
            try:
                with open(ENV_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("USE_LOCAL_SQLITE="):
                            val = line.split("=", 1)[1].strip().lower()
                            if val in ["true", "1", "yes"]:
                                return "LOCAL_SQLITE"
            except Exception:
                pass
        return "NEON_CLOUD"

    def load_target_url(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    url = f.read().strip()
                    if url.startswith("http"):
                        if "/login" not in url:
                            url = url.rstrip("/") + "/login/"
                        return url
            except Exception:
                pass
        return "http://127.0.0.1:8000/login/"

    def save_target_url(self, url):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(url.strip())
        except Exception:
            pass

    def check_url_online(self, url, timeout=1.0):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DMC-Checker'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 302)
        except Exception:
            return False

    def auto_start_and_launch_form2(self):
        """
        Background health checker & server auto-starter.
        Ensures the embedded Waitress server is running in the background,
        updates the status badge, but DOES NOT open the browser automatically.
        The web interface will ONLY open when the user clicks 'បើកដំណើរការប្រព័ន្ធ'.
        """
        if not self.check_url_online("http://127.0.0.1:8000/", timeout=0.5):
            self.after(0, lambda: self.status_badge.configure(
                text="⏳ កំពុងចាប់ផ្តើម Server...",
                text_color="#facc15",
                fg_color="#713f12"
            ))
            self.start_server()

        # Wait up to 30 seconds for server to be responsive
        start_wait = time.time()
        server_ready = False
        while time.time() - start_wait < 30:
            if self.check_url_online("http://127.0.0.1:8000/", timeout=0.5):
                server_ready = True
                break
            time.sleep(0.5)

        if server_ready:
            self.after(0, lambda: self.status_badge.configure(
                text="🟢 កំពុងដំណើរការ (Online)",
                text_color="#4ade80",
                fg_color="#14532d"
            ))
        else:
            self.after(0, lambda: self.status_badge.configure(
                text="⚠️ ចាប់ផ្តើម Server យឺត (Connecting...)",
                text_color="#f87171",
                fg_color="#7f1d1d"
            ))
            self.after(0, self.deiconify)

    def create_widgets(self):
        # 1. Header Frame with Official Logo & Welcome Banner
        header = ctk.CTkFrame(self, corner_radius=14, fg_color="#1e293b", border_width=1, border_color="#334155")
        header.pack(fill="x", padx=20, pady=(16, 10))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(anchor="center", pady=12, padx=16)

        # Load & display logo
        self.logo_ctk = None
        if LOGO_FILE and LOGO_FILE.exists():
            try:
                pil_logo = Image.open(LOGO_FILE)
                self.logo_ctk = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(75, 75))
            except Exception:
                self.logo_ctk = None

        if self.logo_ctk:
            logo_lbl = ctk.CTkLabel(header_inner, image=self.logo_ctk, text="")
            logo_lbl.pack(side="left", padx=(0, 18))

        text_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        text_box.pack(side="left", fill="both")

        welcome_lbl = ctk.CTkLabel(
            text_box,
            text="សូមស្វាគមន៍មកកាន់កម្មវិធីគ្រប់គ្រងធនធានមនុស្ស",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=18, weight="bold"),
            text_color="#38bdf8"
        )
        welcome_lbl.pack(anchor="w", pady=(0, 2))

        title_lbl = ctk.CTkLabel(
            text_box,
            text="ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMC System)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold"),
            text_color="#f1f5f9"
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            text_box,
            text="DMC Python Main Form Application • Windows Desktop Control Center",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        sub_lbl.pack(anchor="w")

        # Load 3 representative Google Material icons
        self.icon_server_ctk = None
        self.icon_db_ctk = None
        self.icon_desktop_ctk = None

        if ICON_SERVER_FILE and ICON_SERVER_FILE.exists():
            try:
                pil_s = Image.open(ICON_SERVER_FILE)
                self.icon_server_ctk = ctk.CTkImage(light_image=pil_s, dark_image=pil_s, size=(58, 58))
            except Exception:
                pass

        if ICON_DB_FILE and ICON_DB_FILE.exists():
            try:
                pil_db = Image.open(ICON_DB_FILE)
                self.icon_db_ctk = ctk.CTkImage(light_image=pil_db, dark_image=pil_db, size=(58, 58))
            except Exception:
                pass

        if ICON_DESKTOP_FILE and ICON_DESKTOP_FILE.exists():
            try:
                pil_desk = Image.open(ICON_DESKTOP_FILE)
                self.icon_desktop_ctk = ctk.CTkImage(light_image=pil_desk, dark_image=pil_desk, size=(58, 58))
            except Exception:
                pass

        # 2. Status & Network Overview: 3-Column Layout (3 Panels with Large Google Icons centered)
        status_card = ctk.CTkFrame(self, fg_color="transparent")
        status_card.pack(fill="x", padx=20, pady=(4, 6))
        status_card.grid_columnconfigure((0, 1, 2), weight=1, uniform="status_col")

        # Column 1: Server Status Panel
        col1 = ctk.CTkFrame(status_card, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        col1.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        if self.icon_server_ctk:
            ctk.CTkLabel(col1, image=self.icon_server_ctk, text="").pack(anchor="center", pady=(12, 4))

        ctk.CTkLabel(
            col1,
            text="⚡ ស្ថានភាពប្រព័ន្ធ (Server)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=12, weight="bold"),
            text_color="#f1f5f9"
        ).pack(anchor="center", pady=(0, 6))

        self.status_badge = ctk.CTkLabel(
            col1,
            text="⏳ កំពុងដំណើរការ...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            fg_color="#334155",
            corner_radius=8,
            padx=14,
            pady=4
        )
        self.status_badge.pack(anchor="center", pady=(0, 12))

        # Column 2: Database Mode Panel
        col2 = ctk.CTkFrame(status_card, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        col2.grid(row=0, column=1, sticky="nsew", padx=3, pady=0)

        if self.icon_db_ctk:
            ctk.CTkLabel(col2, image=self.icon_db_ctk, text="").pack(anchor="center", pady=(12, 4))

        ctk.CTkLabel(
            col2,
            text="🗄️ មូលទិន្នន័យ (Database)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=12, weight="bold"),
            text_color="#f1f5f9"
        ).pack(anchor="center", pady=(0, 6))

        self.db_badge = ctk.CTkLabel(
            col2,
            text="🟢 បានភ្ជាប់ជោគជ័យ (Connected)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4ade80",
            fg_color="#14532d",
            corner_radius=8,
            padx=14,
            pady=4
        )
        self.db_badge.pack(anchor="center", pady=(0, 12))

        # Column 3: Application Mode Panel
        col3 = ctk.CTkFrame(status_card, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        col3.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=0)

        if self.icon_desktop_ctk:
            ctk.CTkLabel(col3, image=self.icon_desktop_ctk, text="").pack(anchor="center", pady=(12, 4))

        ctk.CTkLabel(
            col3,
            text="💻 ទម្រង់ដំណើរការ (Mode)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=12, weight="bold"),
            text_color="#f1f5f9"
        ).pack(anchor="center", pady=(0, 6))

        self.mode_badge = ctk.CTkLabel(
            col3,
            text="💻 Desktop Application",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a7f3d0",
            fg_color="#064e3b",
            corner_radius=8,
            padx=14,
            pady=4
        )
        self.mode_badge.pack(anchor="center", pady=(0, 12))

        # 3. Primary Hero Launch Action Button (Form 2)
        launch_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        launch_frame.pack(fill="x", padx=20, pady=10)

        self.btn_open = ctk.CTkButton(
            launch_frame,
            text="🚀 បើកដំណើរការប្រព័ន្ធ (Open DMC System Window)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=16, weight="bold"),
            height=52,
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=10,
            command=self.launch_app_window
        )
        self.btn_open.pack(fill="x")

        # 4. Management & Controls (Server Controls)
        mgmt_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1e293b")
        mgmt_frame.pack(fill="x", padx=20, pady=(2, 8))

        mgmt_title = ctk.CTkLabel(
            mgmt_frame,
            text="⚙️ ការគ្រប់គ្រងដំណើរការប្រព័ន្ធ (Server Controls)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        mgmt_title.pack(anchor="w", padx=16, pady=(8, 4))

        # Server Actions (Start, Restart, Stop)
        srv_grid = ctk.CTkFrame(mgmt_frame, fg_color="transparent")
        srv_grid.pack(fill="x", padx=16, pady=(4, 10))

        btn_start = ctk.CTkButton(
            srv_grid,
            text="▶️ Start Server",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#15803d",
            hover_color="#166534",
            height=34,
            command=self.start_server
        )
        btn_start.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_restart = ctk.CTkButton(
            srv_grid,
            text="🔄 Restart Server",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            height=34,
            command=self.restart_server
        )
        btn_restart.pack(side="left", fill="x", expand=True, padx=4)

        btn_stop = ctk.CTkButton(
            srv_grid,
            text="🛑 Stop Server",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=34,
            command=self.stop_server
        )
        btn_stop.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Auto-Update from GitHub Button (with smart update indicator)
        update_row = ctk.CTkFrame(mgmt_frame, fg_color="transparent")
        update_row.pack(fill="x", padx=16, pady=(0, 6))

        self.btn_update = ctk.CTkButton(
            update_row,
            text="🔍 កំពុងពិនិត្យមើលកំណែថ្មី...",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            height=38,
            command=self.handle_update_click
        )
        self.btn_update.pack(fill="x", expand=True)

        self.update_notice_label = ctk.CTkLabel(
            update_row,
            text="",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=11),
            text_color="#94a3b8"
        )
        self.update_notice_label.pack(anchor="center", pady=(3, 0))

        # In-App Progress Bar Container (Displays percentage, status, and completion without closing window)
        self.progress_frame = ctk.CTkFrame(mgmt_frame, fg_color="#0f172a", corner_radius=8)
        
        self.progress_info_row = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.progress_info_row.pack(fill="x", padx=12, pady=(8, 2))
        
        self.progress_status_label = ctk.CTkLabel(
            self.progress_info_row,
            text="⏳ កំពុងរៀបចំទាញយក Update...",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=11),
            text_color="#94a3b8"
        )
        self.progress_status_label.pack(side="left")
        
        self.progress_pct_label = ctk.CTkLabel(
            self.progress_info_row,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8"
        )
        self.progress_pct_label.pack(side="right")
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=10,
            corner_radius=5,
            progress_color="#38bdf8",
            fg_color="#334155"
        )
        self.progress_bar.pack(fill="x", padx=12, pady=(2, 8))
        self.progress_bar.set(0.0)

        # 5. Footer / Copyright & Telegram Link Frame
        footer_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        footer_card.pack(fill="x", padx=20, pady=(4, 12))

        footer_inner = ctk.CTkFrame(footer_card, fg_color="transparent")
        footer_inner.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            footer_inner,
            text="រក្សាសិទ្ធិដោយ៖ លោក យ៉ន សាយ៉ាន់ដារ៉ា • មន្ត្រីទទួលបន្ទុកការងារធនធានមនុស្ស",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=12, weight="bold"),
            text_color="#f1f5f9",
            wraplength=880,
            justify="center"
        ).pack(anchor="center", pady=(0, 4))

        def open_telegram():
            try:
                import webbrowser
                webbrowser.open_new_tab("https://t.me/sydadmin168")
            except Exception:
                pass

        btn_tg = ctk.CTkButton(
            footer_inner,
            text="✈️ Telegram: https://t.me/sydadmin168 (ចុចដើម្បីភ្ជាប់ទំនាក់ទំនង)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=12, weight="bold"),
            text_color="#ffffff",
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=30,
            corner_radius=8,
            command=open_telegram
        )
        btn_tg.pack(anchor="center", pady=(2, 0))

    def monitor_server_status(self):
        """Background thread that pings target_url to update status badge live."""
        while self.is_monitoring:
            is_up = self.check_url_online(self.target_url) or self.check_url_online("http://127.0.0.1:8000/")
            if is_up:
                self.after(0, lambda: self.status_badge.configure(
                    text="🟢 កំពុងដំណើរការ (Online)",
                    text_color="#4ade80",
                    fg_color="#14532d"
                ))
            else:
                self.after(0, lambda: self.status_badge.configure(
                    text="🔴 មិនទាន់ដំណើរការ (Offline)",
                    text_color="#f87171",
                    fg_color="#7f1d1d"
                ))
            time.sleep(3)

    def reset_to_localhost(self):
        local_url = "http://127.0.0.1:8000/"
        self.target_url = local_url
        if hasattr(self, 'url_entry') and self.url_entry:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, local_url)
        self.save_target_url(local_url)

    def save_url_from_entry(self):
        if not hasattr(self, 'url_entry') or not self.url_entry:
            return
        new_url = self.url_entry.get().strip()
        if not new_url.startswith("http://") and not new_url.startswith("https://"):
            new_url = "http://" + new_url
        if ":8000" not in new_url and not new_url.startswith("https://"):
            parts = new_url.split("://", 1)
            scheme = parts[0]
            rest = parts[1].strip("/")
            if "/" in rest:
                h, p = rest.split("/", 1)
                if ":" not in h:
                    new_url = f"{scheme}://{h}:8000/{p}"
            else:
                if ":" not in rest:
                    new_url = f"{scheme}://{rest}:8000/"
        if not new_url.endswith("/"):
            new_url += "/"
        self.target_url = new_url
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, new_url)
        self.save_target_url(new_url)

    def launch_app_window(self):
        url = self.target_url
        if not url:
            url = "http://127.0.0.1:8000/login/"
        # Use 127.0.0.1 locally to avoid Windows hostname lookup delay
        if self.hostname in url:
            url = url.replace(self.hostname, "127.0.0.1")
        if "desktop-cil0etl" in url.lower() and self.hostname.lower() != "desktop-cil0etl":
            url = "http://127.0.0.1:8000/login/"

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        if ":8000" not in url and not url.startswith("https://"):
            parts = url.split("://", 1)
            scheme = parts[0]
            rest = parts[1].strip("/")
            if "/" in rest:
                h, p = rest.split("/", 1)
                if ":" not in h:
                    url = f"{scheme}://{h}:8000/{p}"
            else:
                if ":" not in rest:
                    url = f"{scheme}://{rest}:8000/"

        if "/login" not in url:
            url = url.rstrip("/") + "/login/"

        # Look for Edge or Chrome
        edge_candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]
        edge_path = next((p for p in edge_candidates if os.path.exists(p)), None)

        chrome_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_path = next((p for p in chrome_candidates if os.path.exists(p)), None)

        # Get primary screen size
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Cache-busting URL to ensure Edge/Chrome loads the absolute latest form & templates
        cache_bust_url = f"{url}{'&' if '?' in url else '?'}v={int(time.time())}"

        # Force Windows to maximize the process window
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 3  # SW_SHOWMAXIMIZED

        browser_args = [
            f"--app={cache_bust_url}",
            "--start-maximized",
            f"--window-size={sw},{sh}",
            "--window-position=0,0",
        ]

        browser_cmd = None
        if edge_path:
            browser_cmd = [edge_path] + browser_args
        elif chrome_path:
            browser_cmd = [chrome_path] + browser_args

        browser_pid = None
        if browser_cmd:
            try:
                proc = subprocess.Popen(browser_cmd, startupinfo=startupinfo)
                browser_pid = proc.pid
            except Exception:
                browser_cmd = None

        if not browser_cmd:
            webbrowser.open(url)

        # Strictly keep the Control Center at fixed size and send behind Form 2
        self.send_to_back()
        self.maximize_browser_window(browser_pid=browser_pid)

    def send_to_back(self):
        """
        Ensures the Control Center strictly stays behind the main application window (Form 2)
        while maintaining its fixed compact 860x680 size.
        """
        try:
            self.lower()
            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                HWND_BOTTOM = 1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010
                tk_hwnd = self.winfo_id()
                root_hwnd = user32.GetAncestor(tk_hwnd, 2) or tk_hwnd
                user32.SetWindowPos(root_hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception:
            pass

    def maximize_browser_window(self, browser_pid=None):
        """
        Background daemon that searches for the opened DMC Web App window (Form 2)
        and forcefully maximizes it via Windows Win32 API, bringing it to foreground,
        while strictly leaving the Control Center window unchanged and behind.
        """
        def _worker():
            try:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                SW_MAXIMIZE = 3
                current_pid = os.getpid()
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

                def enum_cb(hwnd, lparam):
                    if not user32.IsWindowVisible(hwnd):
                        return True

                    # 1. CRITICAL: Never touch any window from our own launcher process!
                    proc_id = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
                    if proc_id.value == current_pid:
                        return True

                    # 2. Skip any Tkinter window class
                    class_buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buf, 256)
                    class_name = class_buf.value
                    if "Tk" in class_name:
                        return True

                    # 3. Check window title
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title_lower = buff.value.lower()

                        is_browser_proc = (browser_pid is not None and proc_id.value == browser_pid)
                        is_target_title = any(kw in title_lower for kw in (
                            "dms", "dmc", "គ្រប់គ្រងធនធានមនុស្ស", "127.0.0.1", "localhost", "ចូលប្រើប្រាស់ប្រព័ន្ធ", "ផ្ទាំងបញ្ជា"
                        ))

                        if is_browser_proc or is_target_title:
                            user32.ShowWindow(hwnd, SW_MAXIMIZE)
                            user32.SetForegroundWindow(hwnd)
                            # Reinforce that Control Center stays strictly behind
                            self.after(50, self.send_to_back)
                            return False
                    return True

                for _ in range(40):
                    time.sleep(0.2)
                    if not user32.EnumWindows(WNDENUMPROC(enum_cb), 0):
                        break
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def copy_lan_url(self):
        url = f"http://{self.hostname}:8000/"
        self.clipboard_clear()
        self.clipboard_append(url)
        self.url_btn.configure(text=f"✅ បានចម្លង: {url}!")
        self.after(2000, lambda: self.url_btn.configure(text=f"📋 {url} (ចុចចម្លង Link)"))

    def switch_to_neon(self):
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if "USE_LOCAL_SQLITE=" in content:
                lines = [line if not line.startswith("USE_LOCAL_SQLITE=") else "USE_LOCAL_SQLITE=False" for line in content.splitlines()]
                content = "\n".join(lines) + "\n"
            else:
                content += "\nUSE_LOCAL_SQLITE=False\n"
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        self.db_mode = "NEON_CLOUD"
        self.db_badge.configure(text="⚡ Neon Cloud PostgreSQL", text_color="#38bdf8", fg_color="#0369a1")
        self.restart_server()

    def switch_to_sqlite(self):
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if "USE_LOCAL_SQLITE=" in content:
                lines = [line if not line.startswith("USE_LOCAL_SQLITE=") else "USE_LOCAL_SQLITE=True" for line in content.splitlines()]
                content = "\n".join(lines) + "\n"
            else:
                content += "\nUSE_LOCAL_SQLITE=True\n"
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        self.db_mode = "LOCAL_SQLITE"
        self.db_badge.configure(text="📁 Local SQLite (db.sqlite3)", text_color="#facc15", fg_color="#713f12")
        self.restart_server()

    def start_server(self):
        free_port_8000()
        time.sleep(0.5)
        start_embedded_server()

    def restart_server(self):
        self.stop_server()
        time.sleep(1)
        self.start_server()

    def stop_server(self):
        free_port_8000()
        self.status_badge.configure(text="🔴 មិនទាន់ដំណើរការ (Offline)", text_color="#f87171", fg_color="#7f1d1d")

    def _start_update_polling(self):
        # Initial check
        time.sleep(2)
        self._check_and_update_button_state()
        while not getattr(self, '_stop_polling', False):
            time.sleep(30)
            if not getattr(self, '_is_updating', False):
                self._check_and_update_button_state()

    def _check_and_update_button_state(self):
        res = check_github_update_status()
        self._has_new_update = res['has_update']
        self._remote_sha = res['remote_sha']
        self._remote_msg = res['commit_msg']

        def _apply():
            if getattr(self, '_is_updating', False):
                return
            if res['has_update']:
                self.btn_update.configure(
                    state="normal",
                    text="✨ មានកំណែទម្រង់ថ្មី! (ចុចដើម្បី Update ពី GitHub)",
                    fg_color="#7c3aed",
                    hover_color="#6d28d9",
                    text_color="#ffffff"
                )
                short_msg = res['commit_msg'][:50] if res['commit_msg'] else 'កំណែទម្រង់ថ្មី'
                self.update_notice_label.configure(
                    text=f"🔔 មានកំណែថ្មីពី PUSH_TO_GITHUB៖ «{short_msg}»",
                    text_color="#c084fc"
                )
            elif res['error']:
                self.btn_update.configure(
                    state="normal",
                    text="🔄 ពិនិត្យមើល Update ពី GitHub",
                    fg_color="#334155",
                    hover_color="#475569",
                    text_color="#94a3b8"
                )
                self.update_notice_label.configure(
                    text="ℹ️ មិនទាន់អាចភ្ជាប់ GitHub បាន (Offline)",
                    text_color="#64748b"
                )
            else:
                self.btn_update.configure(
                    state="normal",
                    text="✅ កំណែចុងក្រោយបំផុត (Up-to-Date)",
                    fg_color="#1e293b",
                    hover_color="#334155",
                    text_color="#94a3b8"
                )
                self.update_notice_label.configure(
                    text="ℹ️ ប្រព័ន្ធរបស់អ្នកជាកំណែចុងក្រោយបំផុត មិនទាន់មានកំណែថ្មីពី PUSH_TO_GITHUB ឡើយ",
                    text_color="#64748b"
                )
        self.after(0, _apply)

    def handle_update_click(self):
        if getattr(self, '_is_updating', False):
            return

        if getattr(self, '_has_new_update', False):
            self.trigger_auto_update()
        else:
            self.btn_update.configure(
                text="🔍 កំពុងពិនិត្យលើ GitHub...",
                state="disabled"
            )
            def _check():
                res = check_github_update_status()
                self._check_and_update_button_state()
                if not res.get('has_update', False):
                    msg = (
                        "✅ ប្រព័ន្ធរបស់អ្នកកំពុងដំណើរការលើកំណែចុងក្រោយបំផុត (Up-to-Date) រួចរាល់ហើយ!\n\n"
                        "ពុំទាន់មានកំណែទម្រង់ថ្មីនៅលើ GitHub ឡើយ។\n"
                        "លុះត្រាតែ Admin ចុច «PUSH_TO_GITHUB» ជោគជ័យ ទើបប៊ូតុងនេះបង្ហាញកំណែទម្រង់ថ្មីសម្រាប់ធ្វើបច្ចុប្បន្នភាព (Update)។"
                    )
                    self.after(0, lambda: messagebox.showinfo("ស្ថានភាពកំណែប្រព័ន្ធ (Version Status)", msg))
            threading.Thread(target=_check, daemon=True).start()

    def trigger_auto_update(self):
        """
        Triggers in-app auto update from GitHub without closing the window.
        Shows progress bar, percentage, status, and restarts the server cleanly.
        """
        if getattr(self, '_is_updating', False):
            return
        self._is_updating = True

        self.btn_update.configure(
            state="disabled",
            text="⏳ កំពុងដំណើរការ Update ពី GitHub... សូមរង់ចាំ!",
            fg_color="#4c1d95"
        )
        self.progress_frame.pack(fill="x", padx=16, pady=(0, 10))
        self.update_progress_ui(0.05, "⏳ កំពុងពិនិត្យមើលការតភ្ជាប់ទៅកាន់ GitHub...", "5%")

        threading.Thread(target=self._run_in_app_update, daemon=True).start()

    def update_progress_ui(self, fraction, message, pct_text=None):
        def _apply():
            try:
                self.progress_bar.set(fraction)
                self.progress_status_label.configure(text=message)
                pct = pct_text if pct_text is not None else f"{int(fraction * 100)}%"
                self.progress_pct_label.configure(text=pct)
                if fraction >= 1.0:
                    self.progress_bar.configure(progress_color="#22c55e")
                    self.progress_pct_label.configure(text_color="#4ade80")
                else:
                    self.progress_bar.configure(progress_color="#38bdf8")
                    self.progress_pct_label.configure(text_color="#38bdf8")
            except Exception:
                pass
        self.after(0, _apply)

    def _run_in_app_update(self):
        import shutil
        import urllib.request
        import os
        import sys
        import time
        import subprocess

        try:
            self.update_progress_ui(0.05, "⏳ កំពុងពិនិត្យមើលការតភ្ជាប់ទៅកាន់ GitHub...", "5%")

            # 1. Fetch remote version info from dist/current_version.json
            remote_version_info = {}
            try:
                ver_url = f"https://raw.githubusercontent.com/SayanndaraKH/DMC_System/main/dist/current_version.json?t={int(time.time())}"
                req = urllib.request.Request(ver_url, headers={'User-Agent': 'DMC-AutoUpdater/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    remote_version_info = json.loads(resp.read().decode('utf-8'))
            except Exception:
                pass

            # 2. Determine target executable path
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                target_exe = Path(sys.executable).resolve()
            else:
                target_exe = BASE_DIR / "dist" / "DMC_System.exe"

            target_dir = target_exe.parent
            target_dir.mkdir(parents=True, exist_ok=True)

            # Temp download file (placed on the same drive/folder as target_exe for instant atomic move)
            temp_new_exe = target_dir / "DMC_System.exe.new"
            if temp_new_exe.exists():
                try:
                    temp_new_exe.unlink()
                except Exception:
                    pass

            # 3. Download ONLY dist/DMC_System.exe from GitHub
            self.update_progress_ui(0.10, "📥 កំពុងចាប់ផ្តើមទាញយក file DMC_System.exe ពី dist...", "10%")
            exe_urls = [
                "https://raw.githubusercontent.com/SayanndaraKH/DMC_System/main/dist/DMC_System.exe",
                "https://github.com/SayanndaraKH/DMC_System/raw/main/dist/DMC_System.exe"
            ]

            download_success = False
            last_err = None

            for url in exe_urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={
                            'User-Agent': 'DMC-AutoUpdater/1.0',
                            'Accept': '*/*'
                        }
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        total_size = resp.headers.get("Content-Length")
                        total_size = int(total_size) if total_size and total_size.isdigit() else None
                        downloaded = 0
                        chunk_size = 128 * 1024  # 128 KB chunks for smooth, fast transfer

                        with open(temp_new_exe, "wb") as f_out:
                            while True:
                                chunk = resp.read(chunk_size)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    # Progress 10% to 85% during download
                                    frac = min(0.85, 0.10 + (downloaded / total_size) * 0.75)
                                    mb_down = downloaded / (1024 * 1024)
                                    mb_tot = total_size / (1024 * 1024)
                                    self.update_progress_ui(
                                        frac,
                                        f"📥 កំពុងទាញយក DMC_System.exe... ({mb_down:.1f} MB / {mb_tot:.1f} MB)",
                                        f"{int(frac * 100)}%"
                                    )
                                else:
                                    mb_down = downloaded / (1024 * 1024)
                                    frac = min(0.85, 0.10 + (downloaded / (95 * 1024 * 1024)) * 0.75)
                                    self.update_progress_ui(
                                        frac,
                                        f"📥 កំពុងទាញយក DMC_System.exe... ({mb_down:.1f} MB)",
                                        f"{int(frac * 100)}%"
                                    )

                        # Verify downloaded file size
                        if temp_new_exe.exists() and temp_new_exe.stat().st_size > 10 * 1024 * 1024:
                            download_success = True
                            break
                        else:
                            raise Exception("Downloaded file is too small or incomplete.")
                except Exception as e:
                    last_err = e
                    if temp_new_exe.exists():
                        try:
                            temp_new_exe.unlink()
                        except Exception:
                            pass
                    continue

            if not download_success:
                raise Exception(f"មិនអាចទាញយក file exe ពី GitHub បានឡើយ: {last_err}")

            # 4. Verification
            self.update_progress_ui(0.88, "🔍 កំពុងផ្ទៀងផ្ទាត់ទំហំ និងសុពលភាពនៃ File...", "88%")
            time.sleep(0.5)

            # 5. File replacement
            self.update_progress_ui(0.92, "🔄 កំពុងជំនួស File DMC_System.exe ថ្មី...", "92%")

            # Also update current_version.json locally
            saved_sha = remote_version_info.get("sha") or getattr(self, '_remote_sha', '')
            saved_msg = remote_version_info.get("message") or getattr(self, '_remote_msg', '')
            saved_ts = remote_version_info.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")
            saved_ver = remote_version_info.get("version") or time.strftime("%Y%m%d.%H%M%S")
            save_local_version_data(saved_sha, saved_msg, saved_ts, saved_ver)

            # Handle file replacement based on execution mode
            root_exe = BASE_DIR / "DMC_System.exe"
            dist_exe = BASE_DIR / "dist" / "DMC_System.exe"

            if is_frozen:
                # App is running as DMC_System.exe
                # Windows allows renaming running executable, then copying new one over
                old_exe = target_exe.with_name(target_exe.name + ".old")
                if old_exe.exists():
                    try:
                        old_exe.unlink()
                    except Exception:
                        pass

                replaced_directly = False
                try:
                    target_exe.rename(old_exe)
                    shutil.copy2(temp_new_exe, target_exe)
                    temp_new_exe.unlink(missing_ok=True)
                    replaced_directly = True
                except Exception as e:
                    logger.warning(f"Could not rename running exe directly: {e}")

                # Also sync root and dist exe if they are accessible and different
                for sibling in [root_exe, dist_exe]:
                    if sibling.exists() and sibling.resolve() != target_exe.resolve():
                        try:
                            shutil.copy2(target_exe if replaced_directly else temp_new_exe, sibling)
                        except Exception:
                            pass

                # Create detached restart script that guarantees clean swap & relaunch
                restart_bat = target_dir / "restart_after_update.bat"
                bat_code = f"""@echo off
timeout /t 2 /nobreak >nul
if exist "{temp_new_exe}" (
    copy /y "{temp_new_exe}" "{target_exe}" >nul
    del /f /q "{temp_new_exe}" >nul
)
if exist "{old_exe}" del /f /q "{old_exe}" >nul
start "" "{target_exe}"
del "%~f0" & exit
"""
                try:
                    with open(restart_bat, "w", encoding="utf-8") as bf:
                        bf.write(bat_code)
                except Exception:
                    pass

                self.update_progress_ui(1.0, "✅ Update DMC_System.exe ជោគជ័យ ១០០%! កម្មវិធីនឹង Restart ក្នុងពេលបន្តិចទៀត...", "100%")
                self._has_new_update = False

                def _do_restart():
                    time.sleep(2)
                    try:
                        if restart_bat.exists():
                            subprocess.Popen(
                                ["cmd.exe", "/c", str(restart_bat)],
                                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                                close_fds=True
                            )
                    except Exception as re:
                        logger.warning(f"Failed to spawn restart script: {re}")
                    # Exit the old process cleanly
                    self.after(200, lambda: self.destroy())
                    self.after(500, lambda: os._exit(0))

                threading.Thread(target=_do_restart, daemon=True).start()

            else:
                # App is running as python script in dev mode (e.g. python main_app.py)
                try:
                    shutil.copy2(temp_new_exe, dist_exe)
                    shutil.copy2(temp_new_exe, root_exe)
                    temp_new_exe.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to copy exe in dev mode: {e}")

                # Restart embedded server
                self.update_progress_ui(0.96, "⚙️ កំពុង Restart Server...", "96%")
                self.restart_server()

                self.update_progress_ui(1.0, "✅ Update DMC_System.exe ពី dist ជោគជ័យ ១០០%!", "100%")
                self._has_new_update = False

                def _on_finish():
                    self._is_updating = False
                    self.btn_update.configure(
                        state="normal",
                        text="✅ កំណែចុងក្រោយបំផុត (Up-to-Date)",
                        fg_color="#1e293b",
                        hover_color="#334155",
                        text_color="#94a3b8"
                    )
                    self.update_notice_label.configure(
                        text="✅ បាន Update File DMC_System.exe ពី dist ជោគជ័យ ១០០%!",
                        text_color="#4ade80"
                    )
                self.after(0, _on_finish)

        except Exception as e:
            logger.error(f"Auto-update error: {e}")
            self.update_progress_ui(0.0, f"⚠️ បរាជ័យក្នុងការ Update: {str(e)}", "Error")
            def _on_err():
                self._is_updating = False
                self.btn_update.configure(
                    state="normal",
                    text="⚠️ Update មិនជោគជ័យ - ចុចដើម្បីសាកល្បងឡើងវិញ",
                    fg_color="#dc2626",
                    hover_color="#b91c1c"
                )
            self.after(0, _on_err)

    def destroy(self):
        self.is_monitoring = False
        super().destroy()


if __name__ == "__main__":
    app = DMCMainApp()
    app.mainloop()
