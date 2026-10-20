import os
import sys
import time
import socket
import subprocess
import threading
import webbrowser
import urllib.request
from pathlib import Path

from PIL import Image, ImageTk

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
except ImportError:
    import tkinter as ctk

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
        self.center_window(860, 630)

        # Strictly lock window dimensions to prevent any resizing or maximizing
        self.resizable(False, False)
        self.maxsize(860, 630)
        self.minsize(860, 630)

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

        # UI Components
        self.create_widgets()

        # Background server auto-start & auto-launch Form 2
        threading.Thread(target=self.auto_start_and_launch_form2, daemon=True).start()

        # Live background health-check loop
        self.monitor_thread = threading.Thread(target=self.monitor_server_status, daemon=True)
        self.monitor_thread.start()

    def center_window(self, width=860, height=600):
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

        # 2. Status & Network Overview Card
        status_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#0f172a")
        status_card.pack(fill="x", padx=20, pady=6)

        # Row 1: Server Status
        row1 = ctk.CTkFrame(status_card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            row1,
            text="ស្ថានភាពប្រព័ន្ធ (Server Status):",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold")
        ).pack(side="left")

        self.status_badge = ctk.CTkLabel(
            row1,
            text="⏳ កំពុងដំណើរការ...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            fg_color="#334155",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right")

        # Row 2: Database Mode
        row2 = ctk.CTkFrame(status_card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            row2,
            text="មូលទិន្នន័យ (Database Connected):",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold")
        ).pack(side="left")

        self.db_badge = ctk.CTkLabel(
            row2,
            text="🟢 បានភ្ជាប់ជោគជ័យ (Connected)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4ade80",
            fg_color="#14532d",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.db_badge.pack(side="right")

        # Row 3: Application Mode
        row3 = ctk.CTkFrame(status_card, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(6, 12))

        ctk.CTkLabel(
            row3,
            text="ទម្រង់ដំណើរការ (Application Mode):",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold")
        ).pack(side="left")

        self.mode_badge = ctk.CTkLabel(
            row3,
            text="💻 Windows Desktop Application",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a7f3d0",
            fg_color="#064e3b",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.mode_badge.pack(side="right")

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

        # Auto-Update from GitHub Button (for User PC and Admin PC)
        update_row = ctk.CTkFrame(mgmt_frame, fg_color="transparent")
        update_row.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_update = ctk.CTkButton(
            update_row,
            text="🔄 ទាញយក Update ពី GitHub (Auto-Update User PC)",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=13, weight="bold"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            height=36,
            command=self.trigger_auto_update
        )
        self.btn_update.pack(fill="x", expand=True)

        # 5. Footer / Copyright & Telegram Link Frame
        footer_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        footer_card.pack(fill="x", padx=20, pady=(4, 12))

        footer_inner = ctk.CTkFrame(footer_card, fg_color="transparent")
        footer_inner.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            footer_inner,
            text="រក្សាសិទ្ធិដោយ៖ លោក យ៉ន សាយ៉ាន់ដារ៉ា មន្ត្រីទទួលបន្ទុកការងារធនធានមនុស្ស",
            font=ctk.CTkFont(family="Khmer OS Siemreap", size=12, weight="bold"),
            text_color="#f1f5f9"
        ).pack(anchor="center", pady=(0, 3))

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

    def trigger_auto_update(self):
        """
        Triggers UPDATE_USER_PC.bat to pull latest form & code from GitHub,
        replaces all files, and restarts the application cleanly.
        """
        try:
            self.btn_update.configure(
                text="⏳ កំពុងដំណើរការ Update ពី GitHub... សូមរង់ចាំ!",
                fg_color="#4c1d95"
            )
            self.update()
        except Exception:
            pass

        update_bat = BASE_DIR / "UPDATE_USER_PC.bat"
        if not update_bat.exists():
            update_bat = Path(__file__).resolve().parent / "UPDATE_USER_PC.bat"

        self.stop_server()
        try:
            if update_bat.exists():
                subprocess.Popen(
                    ["cmd.exe", "/c", str(update_bat)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(BASE_DIR)
                )
            else:
                cmd = 'git fetch origin main && git reset --hard origin/main && pause'
                subprocess.Popen(
                    ["cmd.exe", "/c", cmd],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(BASE_DIR)
                )
        except Exception as e:
            print(f"Error launching update: {e}")

        time.sleep(0.5)
        self.destroy()
        sys.exit(0)

    def destroy(self):
        self.is_monitoring = False
        super().destroy()


if __name__ == "__main__":
    app = DMCMainApp()
    app.mainloop()
